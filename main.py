import datetime
import logging
import os
import shutil
import traceback
import pandas as pd

from dotenv import load_dotenv
load_dotenv()  # Loads variables from your local .env file

import warnings

# Suppress all warnings coming from yfinance internals
warnings.filterwarnings("ignore", module="yfinance.*")

from config.settings import (
    ALLOCATION_PCT,
    TOTAL_CAPITAL,
    CURRENT_RUN_DATE,
    DEBUG_TICKERS,
)
from src.analytics.scoring_engine import (
    apply_grading_and_scoring_matrices,
    compute_risk_return_metrics,
)
from src.data_engine.market_data import (
    download_historical_data_and_compute_returns,
    process_universe_metadata,
)
from src.data_engine.yahoo_fetcher import fetch_nifty_750_universe
from src.data_engine.tradebook_parser import (
    process_closed_tradebook,
    process_open_partial_tradebook,
)
from src.utils.helpers import (
    build_universe_750_scores_df,
    enrich_closed_journal_df,
    enrich_open_journal_df,
)
from src.utils.email_helper import export_and_email_report
from src.utils.database import (
    save_dataframe_to_sql,
    process_action_history,
)
from src.utils.notifications import (
    notify_pipeline_status,
    # After your dataframes are processed and synced to Supabase:
    send_filtered_table_notifications,
)
from src.utils.cli import parse_arguments

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger("PortfolioEngine")

CACHE_DIR = "data/cache"
UNIVERSE_CACHE = os.path.join(CACHE_DIR, "checkpoint_universe.pkl")
METADATA_CACHE = os.path.join(CACHE_DIR, "checkpoint_metadata.pkl")
RETURNS_CACHE = os.path.join(CACHE_DIR, "checkpoint_returns.pkl")
SCORES_CACHE = os.path.join(CACHE_DIR, "checkpoint_scored_results.csv")


def main():
    args = parse_arguments()
    
    logger.info("=========================================================")
    logger.info(f"Initializing Portfolio Engine | Mode: {args.mode.upper()}")
    logger.info("=========================================================")

    # Handle cache clearing if requested
    if args.clear_cache and os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)
        logger.info("[CLI] Cleared intermediate cache directory: data/cache/")

    os.makedirs(CACHE_DIR, exist_ok=True)

    try:
        # =====================================================================
        # Step 1. Fetch Universe & Board Map (Debug vs Full)
        # =====================================================================
        if args.mode == "debug":
            logger.info(f"Using DEBUG ticker list ({len(DEBUG_TICKERS)} stocks) for rapid testing.")
            raw_tickers = DEBUG_TICKERS
            ticker_to_board_map = {
                t: ("Nifty 50" if t in ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"] else "Nifty Next 50") 
                for t in raw_tickers
            }
        else:
            if os.path.exists(UNIVERSE_CACHE):
                logger.info("[Checkpoint] Loading Nifty 750 universe from cache...")
                universe_cache_df = pd.read_pickle(UNIVERSE_CACHE)
                raw_tickers = universe_cache_df["raw_tickers"].tolist()
                ticker_to_board_map = universe_cache_df["ticker_to_board_map"].iloc[0]
            else:
                logger.info("Fetching Nifty 750 universe from live sources...")
                raw_tickers, ticker_to_board_map = fetch_nifty_750_universe()
                raw_tickers = list(dict.fromkeys(raw_tickers)) + ["MANINDS.NS", "SSWL.NS", "TFCILTD.NS"]
                pd.to_pickle(
                    pd.DataFrame({"raw_tickers": [raw_tickers], "ticker_to_board_map": [ticker_to_board_map]}),
                    UNIVERSE_CACHE,
                )
                logger.info("[Checkpoint] Saved universe checkpoint.")

        # =====================================================================
        # Step 2. Process Metadata & Financial Statements
        # =====================================================================
        if os.path.exists(METADATA_CACHE):
            logger.info("[Checkpoint] Loading metadata and financial statements from cache...")
            meta_cache_df = pd.read_pickle(METADATA_CACHE)
            valid_tickers = meta_cache_df["valid_tickers"].iloc[0]
            stock_sector_map = meta_cache_df["stock_sector_map"].iloc[0]
            stock_metadata_map = meta_cache_df["stock_metadata_map"].iloc[0]
        else:
            logger.info("Processing metadata & financial statements...")
            valid_tickers, stock_sector_map, stock_metadata_map = process_universe_metadata(raw_tickers, ticker_to_board_map)
            pd.to_pickle(
                pd.DataFrame({
                    "valid_tickers": [valid_tickers],
                    "stock_sector_map": [stock_sector_map],
                    "stock_metadata_map": [stock_metadata_map],
                }),
                METADATA_CACHE,
            )
            logger.info("[Checkpoint] Saved metadata checkpoint.")

        # =====================================================================
        # Step 3. Download Historical Data & Compute Returns
        # =====================================================================
        if os.path.exists(RETURNS_CACHE):
            logger.info("[Checkpoint] Loading historical returns matrix from cache...")
            ret_cache_df = pd.read_pickle(RETURNS_CACHE)
            daily_returns = ret_cache_df["daily_returns"].iloc[0]
            n500_returns = ret_cache_df["n500_returns"].iloc[0]
            n500_variance = ret_cache_df["n500_variance"].iloc[0]
            n500_actual_return_annual = ret_cache_df["n500_actual_return_annual"].iloc[0]
            sector_returns_matrix = ret_cache_df["sector_returns_matrix"].iloc[0]
        else:
            logger.info("Downloading historical data and computing returns matrix...")
            (
                daily_returns,
                n500_returns,
                n500_variance,
                n500_actual_return_annual,
                sector_returns_matrix,
            ) = download_historical_data_and_compute_returns(valid_tickers, stock_sector_map)
            pd.to_pickle(
                pd.DataFrame({
                    "daily_returns": [daily_returns],
                    "n500_returns": [n500_returns],
                    "n500_variance": [n500_variance],
                    "n500_actual_return_annual": [n500_actual_return_annual],
                    "sector_returns_matrix": [sector_returns_matrix],
                }),
                RETURNS_CACHE,
            )
            logger.info("[Checkpoint] Saved historical returns checkpoint.")

        # =====================================================================
        # Step 4 & 5. Risk/Return Calculation & Grading
        # =====================================================================
        if os.path.exists(SCORES_CACHE):
            logger.info("[Checkpoint] Loading scored results from cache...")
            df_scored_results = pd.read_csv(SCORES_CACHE)
        else:
            logger.info("Running risk/return calculation and grading engine...")
            df_results = compute_risk_return_metrics(
                valid_tickers=valid_tickers,
                daily_returns=daily_returns,
                n500_returns=n500_returns,
                n500_variance=n500_variance,
                n500_actual_return_annual=n500_actual_return_annual,
                sector_returns_matrix=sector_returns_matrix,
                stock_metadata_map=stock_metadata_map,
            )
            df_scored_results = apply_grading_and_scoring_matrices(df_results)
            df_scored_results.to_csv(SCORES_CACHE, index=False)
            logger.info("[Checkpoint] Saved scored results checkpoint.")

        df_scored_results = df_scored_results[~df_scored_results["Ticker"].str.contains("GOLDBEES", case=False, na=False)]

        # =====================================================================
        # Step 6. Process Tradebook Journals
        # =====================================================================
        tradebook_path = os.path.join("data", "tradebook-DIZ015-EQ.csv")
        open_journal_df = pd.DataFrame()
        closed_journal_df = pd.DataFrame()

        if os.path.exists(tradebook_path):
            logger.info(f"Processing tradebook data from {tradebook_path}...")
            raw_closed_journal = process_closed_tradebook(csv_filepath=tradebook_path, segment="delivery", exchange="NSE")
            if raw_closed_journal is not None and not raw_closed_journal.empty:
                symbol_col = "symbol" if "symbol" in raw_closed_journal.columns else "Instrument"
                raw_closed_journal = raw_closed_journal[~raw_closed_journal[symbol_col].str.contains("GOLDBEES", case=False, na=False)]
                closed_journal_df = enrich_closed_journal_df(raw_closed_journal, df_scored_results)

            raw_open_journal = process_open_partial_tradebook(csv_filepath=tradebook_path, total_capital=TOTAL_CAPITAL, allocation_pct=ALLOCATION_PCT)
            if raw_open_journal is not None and not raw_open_journal.empty:
                inst_col = "Instrument" if "Instrument" in raw_open_journal.columns else "symbol"
                raw_open_journal = raw_open_journal[~raw_open_journal[inst_col].str.contains("GOLDBEES", case=False, na=False)]
                open_journal_df = enrich_open_journal_df(raw_open_journal, df_scored_results)
        else:
            logger.warning(f"Tradebook CSV not found at '{tradebook_path}'. Skipping journals.")

        # =====================================================================
        # Step 7. Build Universe 750 Scores DataFrame (Cleaned of Temp computations)
        # =====================================================================
        universe_750_df = build_universe_750_scores_df(
            df_scored_results=df_scored_results,
            total_capital=TOTAL_CAPITAL,
            allocation_pct=ALLOCATION_PCT,
            open_journal_df=open_journal_df,
        )

        universe_750_df = universe_750_df[
            ~universe_750_df["Instrument"].str.contains(
                "GOLDBEES", case=False, na=False
            )
        ]

        # =====================================================================
        # Step 8. Export to Multi-Tab Excel Report
        # =====================================================================
        email_delivery_status = export_and_email_report(
            df_scored_results=df_scored_results,
            universe_750_df=universe_750_df,
            open_journal_df=open_journal_df,
            closed_journal_df=closed_journal_df
        )

        export_and_email_report_status = "✅ Email with Attachment is SUCCESS" if email_delivery_status else "❌ Email with Attachment FAILED"

        # =====================================================================
        # Step 9. Sync Dataframes to Supabase PostgreSQL (Conditionally)
        # =====================================================================
        if not args.skip_db:
            logger.info("Syncing processed dataframes to Supabase...")
            save_dataframe_to_sql(universe_750_df, "universe_of_750_stocks_scores", if_exists="replace")
            # 2. Process and inject the rolling 4-week ACTION history
            universe_750_df = process_action_history(universe_750_df)
            if not open_journal_df.empty:
                save_dataframe_to_sql(open_journal_df, "open_partial_journal", if_exists="replace")
            if not closed_journal_df.empty:
                save_dataframe_to_sql(closed_journal_df, "closed_journal", if_exists="replace")
        else:
            logger.info("[CLI] Skipping Supabase DB sync (--skip-db enabled).")

        # =====================================================================
        # Step 10. Dispatch Success Notifications (Conditionally)
        # =====================================================================
        if not args.skip_notifications:
            success_message = (
                f"Successfully completed EOD pipeline run for {CURRENT_RUN_DATE} ({args.mode.upper()} mode).\n"
                f"Processed {len(df_scored_results)} valid tickers.\n"
                f"{export_and_email_report_status}"
            )
            notify_pipeline_status(status="SUCCESS", details=success_message, is_error=False)

            send_filtered_table_notifications(
                open_df=open_journal_df,
                closed_df=closed_journal_df,
                universe_df=universe_750_df
            )
        else:
            logger.info("[CLI] Skipping notifications (--skip-notifications enabled).")

        logger.info("=== Execution Complete Successfully ===")

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"[Error] Pipeline failed during execution: {e}\n{error_trace}", exc_info=True)
        if not args.skip_notifications:
            notify_pipeline_status(status="FAILURE", details=f"Error: {e}\n\nTraceback:\n{error_trace}", is_error=True)
        raise

    finally:
        if args.mode == "debug" and os.path.exists(CACHE_DIR):
            shutil.rmtree(CACHE_DIR)
            logger.info("Cleaned up cache directory.")


if __name__ == "__main__":
    main()