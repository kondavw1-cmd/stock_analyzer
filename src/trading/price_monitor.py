import sys
from pathlib import Path

# Ensure project root is in sys.path when executed directly
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import os
import time
import argparse
import logging
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from src.utils.supabase_client import get_supabase_client
from src.utils.notifications import broadcast_trade_signal

# --- CONFIGURE STRUCTURED LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("price_monitor")

def run_intraday_monitors():
    """Runs hourly intraday (60m) checks for stop-losses, EMA 5/13/26, and true max historical ATH."""
    start_time = time.time()
    logger.info("==================================================")
    logger.info("Starting INTRADAY price monitoring check (60m)...")
    logger.info("==================================================")
    
    supabase = get_supabase_client()
    stats = {
        "positions_checked": 0,
        "sl_triggered": 0,
        "ema_triggered": 0,
        "universe_checked": 0,
        "ath_triggered": 0
    }
    
    # --- 1. COLLECT TICKERS FROM SUPABASE ---
    logger.info("Fetching open positions and universe watchlist from Supabase...")
    
    try:
        # A. Open Positions (for Stop-Loss & EMA monitoring)
        open_response = supabase.table("open_partial_journal").select("*").execute()
        open_df = pd.DataFrame(open_response.data) if open_response.data else pd.DataFrame()
        
        open_positions = {}
        if not open_df.empty:
            for _, row in open_df.iterrows():
                raw_inst = str(row.get("Instrument", "")).strip()
                if not raw_inst:
                    continue
                clean_ticker = raw_inst.replace(".NS", "").upper()
                avg_cost = float(row.get("Avg. cost", 0.0))
                defined_sl = float(row.get("Defined SL [RISK]", avg_cost * 0.95))
                
                open_positions[clean_ticker] = {
                    "avg_cost": avg_cost,
                    "defined_sl": defined_sl
                }
        logger.info(f"Loaded {len(open_positions)} open positions from 'open_partial_journal'.")

        # B. Universe Stock Scans (for ATH breakout monitoring where ACTION == '+ADD')
        universe_response = supabase.table("universe_of_750_stocks_scores").select("Instrument").eq("ACTION", "+ADD").execute()
        universe_tickers = []
        if universe_response.data:
            for row in universe_response.data:
                raw_inst = str(row.get("Instrument", "")).strip()
                if not raw_inst:
                    continue
                clean_ticker = raw_inst.replace(".NS", "").upper()
                universe_tickers.append(clean_ticker)
        logger.info(f"Loaded {len(universe_tickers)} universe watchlist stocks with '+ADD' status.")

    except Exception as db_err:
        logger.error(f"Failed to fetch data from Supabase: {db_err}", exc_info=True)
        return

    # Combine all unique tickers for batch intraday download
    all_unique_tickers = list(set(list(open_positions.keys()) + universe_tickers))
    
    if not all_unique_tickers:
        logger.warning("No active stocks found across journals or universe to monitor. Exiting.")
        return

    tickers_yf = [f"{ticker}.NS" for ticker in all_unique_tickers]
    logger.info(f"Preparing batch download for {len(tickers_yf)} unique instrument(s)...")

    try:
        # --- 2. BATCH INTRADAY DOWNLOAD (for LTP & EMAs) ---
        logger.info("Initiating yfinance batch download (period='5d', interval='60m')...")
        download_start = time.time()
        
        batch_data = yf.download(
            tickers=tickers_yf, 
            period="5d", 
            interval="60m", 
            group_by="ticker", 
            auto_adjust=False,
            threads=True, 
            progress=False
        )
        logger.info(f"Batch download completed in {time.time() - download_start:.2f} seconds.")

        def get_intraday_metrics(yf_sym):
            try:
                if len(tickers_yf) == 1:
                    df = batch_data
                else:
                    df = batch_data[yf_sym]
                
                if df is None or df.empty or "Close" not in df.columns:
                    return None, None
                
                close_series = df["Close"].dropna()
                if len(close_series) < 26:
                    return None, None

                current_close = float(close_series.iloc[-1])
                ema_5 = float(close_series.ewm(span=5, adjust=False).mean().iloc[-1])
                ema_13 = float(close_series.ewm(span=13, adjust=False).mean().iloc[-1])
                ema_26 = float(close_series.ewm(span=26, adjust=False).mean().iloc[-1])
                
                return current_close, {"EMA_5": ema_5, "EMA_13": ema_13, "EMA_26": ema_26}
            except Exception as metric_err:
                logger.debug(f"Error computing intraday metrics for {yf_sym}: {metric_err}")
                return None, None

        # --- 3. EVALUATE STOP-LOSS & EMA ALERTS (Open Positions) ---
        logger.info("--- Evaluating Open Positions (Intraday Stop-Loss & EMAs) ---")
        for ticker, meta in open_positions.items():
            yf_sym = f"{ticker}.NS"
            stats["positions_checked"] += 1
            
            current_close, emas = get_intraday_metrics(yf_sym)
            
            if current_close is None or emas is None:
                logger.warning(f"[{ticker}] Insufficient intraday historical data or empty dataframe.")
                continue
                
            defined_sl = meta["defined_sl"]
            logger.info(
                f"Position -> {ticker}: Close=₹{current_close:.2f} | SL=₹{defined_sl:.2f} | "
                f"EMA5=₹{emas['EMA_5']:.2f} | EMA13=₹{emas['EMA_13']:.2f} | EMA26=₹{emas['EMA_26']:.2f}"
            )

            # A. Check Stop-Loss Breach
            if current_close <= defined_sl:
                logger.warning(f"🚨 ALERT [{ticker}]: Intraday close (₹{current_close:.2f}) breached SL threshold (₹{defined_sl:.2f})!")
                stats["sl_triggered"] += 1
                broadcast_trade_signal(
                    ticker=ticker,
                    action="EXIT / INTRADAY STOP-LOSS BREACH",
                    price=current_close,
                    target=defined_sl
                )

            # B. Check EMA Breakdown Alerts
            if current_close < emas["EMA_5"] and current_close < emas["EMA_13"] and current_close < emas["EMA_26"]:
                logger.warning(f"🚨 ALERT [{ticker}]: Intraday price closed below all EMAs (5/13/26)!")
                stats["ema_triggered"] += 1
                broadcast_trade_signal(
                    ticker=ticker,
                    action="INTRADAY EMA BREAKDOWN (5/13/26)",
                    price=current_close,
                    target=emas["EMA_26"]
                )

        # --- 4. EVALUATE TRUE HISTORICAL ATH BREAKOUT ALERTS (Universe +ADD) ---
        logger.info("--- Evaluating Universe Watchlist (True Historical ATH Breakouts) ---")
        for ticker in universe_tickers:
            yf_sym = f"{ticker}.NS"
            stats["universe_checked"] += 1
            
            try:
                # Get current intraday close first
                current_close, _ = get_intraday_metrics(yf_sym)
                if current_close is None:
                    continue

                # Fetch TRUE historical max daily data to compute accurate All-Time High
                ticker_obj = yf.Ticker(yf_sym)
                hist_max = ticker_obj.history(period="max", auto_adjust=False)
                
                if hist_max is None or hist_max.empty or "High" not in hist_max.columns:
                    continue

                # Exclude the very last incomplete day if needed, or take absolute max High across all history
                ath_price = float(hist_max["High"].max())

                if np.isnan(ath_price):
                    continue

                logger.info(f"Universe -> {ticker}: Current Close=₹{current_close:.2f} | True ATH Ref=₹{ath_price:.2f}")

                if current_close >= ath_price:
                    logger.warning(f"🚨 ALERT [{ticker}]: Intraday price (₹{current_close:.2f}) hit/exceeded True ATH (₹{ath_price:.2f})!")
                    stats["ath_triggered"] += 1
                    broadcast_trade_signal(
                        ticker=ticker,
                        action="INTRADAY ATH BREAKOUT",
                        price=current_close,
                        target=ath_price
                    )
            except Exception as ath_err:
                logger.debug(f"Error checking historical ATH for {ticker}: {ath_err}")

    except Exception as e:
        logger.error(f"Critical error during intraday batch processing: {e}", exc_info=True)

    elapsed_time = time.time() - start_time
    logger.info("==================================================")
    logger.info("Intraday Price Monitoring Summary:")
    logger.info(f" • Open Positions Scanned : {stats['positions_checked']}")
    logger.info(f" • Stop-Loss Breaches     : {stats['sl_triggered']}")
    logger.info(f" • EMA Breakdowns         : {stats['ema_triggered']}")
    logger.info(f" • Universe Stocks Scanned: {stats['universe_checked']}")
    logger.info(f" • ATH Breakouts Detected : {stats['ath_triggered']}")
    logger.info(f" • Total Execution Time   : {elapsed_time:.2f} seconds")
    logger.info("==================================================")


def run_weekly_monitors():
    """Runs weekly timeframe checks (resampled from daily) for stop-losses, EMA 5/13/26, and ATH."""
    start_time = time.time()
    logger.info("==================================================")
    logger.info("Starting WEEKLY timeframe price monitoring check...")
    logger.info("==================================================")
    
    supabase = get_supabase_client()
    stats = {
        "positions_checked": 0,
        "sl_triggered": 0,
        "ema_triggered": 0,
        "universe_checked": 0,
        "ath_triggered": 0
    }
    
    # --- 1. COLLECT TICKERS FROM SUPABASE ---
    logger.info("Fetching open positions and universe watchlist from Supabase...")
    
    try:
        open_response = supabase.table("open_partial_journal").select("*").execute()
        open_df = pd.DataFrame(open_response.data) if open_response.data else pd.DataFrame()
        
        open_positions = {}
        if not open_df.empty:
            for _, row in open_df.iterrows():
                raw_inst = str(row.get("Instrument", "")).strip()
                if not raw_inst:
                    continue
                clean_ticker = raw_inst.replace(".NS", "").upper()
                avg_cost = float(row.get("Avg. cost", 0.0))
                defined_sl = float(row.get("Defined SL [RISK]", avg_cost * 0.95))
                
                open_positions[clean_ticker] = {
                    "avg_cost": avg_cost,
                    "defined_sl": defined_sl
                }
        logger.info(f"Loaded {len(open_positions)} open positions from database.")

        universe_response = supabase.table("universe_of_750_stocks_scores").select("Instrument").eq("ACTION", "+ADD").execute()
        universe_tickers = []
        if universe_response.data:
            for row in universe_response.data:
                raw_inst = str(row.get("Instrument", "")).strip()
                if not raw_inst:
                    continue
                universe_tickers.append(raw_inst.replace(".NS", "").upper())
        logger.info(f"Loaded {len(universe_tickers)} universe watchlist stocks with '+ADD' status.")

    except Exception as db_err:
        logger.error(f"Failed to fetch data from Supabase: {db_err}", exc_info=True)
        return

    all_unique_tickers = list(set(list(open_positions.keys()) + universe_tickers))
    
    if not all_unique_tickers:
        logger.warning("No active stocks found across journals or universe to monitor. Exiting.")
        return

    tickers_yf = [f"{ticker}.NS" for ticker in all_unique_tickers]
    logger.info(f"Preparing batch download for {len(tickers_yf)} unique instrument(s)...")

    try:
        # --- 2. BATCH DAILY DOWNLOAD (for Weekly Resampling) ---
        logger.info("Initiating yfinance daily batch download (period='2y', interval='1d') for weekly resampling...")
        download_start = time.time()
        
        batch_data = yf.download(
            tickers=tickers_yf, 
            period="2y",          
            interval="1d",        
            group_by="ticker", 
            auto_adjust=False,    
            threads=True, 
            progress=False
        )
        logger.info(f"Batch download completed in {time.time() - download_start:.2f} seconds.")

        def get_resampled_weekly_metrics(yf_sym):
            try:
                if len(tickers_yf) == 1:
                    df = batch_data
                else:
                    df = batch_data[yf_sym]
                
                if df is None or df.empty or "Close" not in df.columns or "High" not in df.columns:
                    return None, None, None
                
                weekly_df = pd.DataFrame()
                weekly_df['Close'] = df['Close'].resample('W-FRI').last()
                weekly_df['High'] = df['High'].resample('W-FRI').max()
                weekly_df = weekly_df.dropna()

                close_series = weekly_df["Close"]
                high_series = weekly_df["High"]
                
                if len(close_series) < 26:
                    return None, None, None

                current_close = float(close_series.iloc[-1])
                ema_5 = float(close_series.ewm(span=5, adjust=False).mean().iloc[-1])
                ema_13 = float(close_series.ewm(span=13, adjust=False).mean().iloc[-1])
                ema_26 = float(close_series.ewm(span=26, adjust=False).mean().iloc[-1])
                weekly_ath = float(high_series.max())
                
                return current_close, {"EMA_5": ema_5, "EMA_13": ema_13, "EMA_26": ema_26}, weekly_ath
            except Exception as metric_err:
                logger.debug(f"Error computing resampled weekly metrics for {yf_sym}: {metric_err}")
                return None, None, None

        # --- 3. EVALUATE STOP-LOSS & WEEKLY EMA ALERTS (Open Positions) ---
        logger.info("--- Evaluating Open Positions (Weekly Resampled Stop-Loss & EMAs) ---")
        for ticker, meta in open_positions.items():
            yf_sym = f"{ticker}.NS"
            stats["positions_checked"] += 1
            
            current_close, emas, _ = get_resampled_weekly_metrics(yf_sym)
            
            if current_close is None or emas is None:
                logger.warning(f"[{ticker}] Insufficient weekly historical data or empty dataframe.")
                continue
                
            defined_sl = meta["defined_sl"]
            logger.info(
                f"Position -> {ticker}: Close=₹{current_close:.2f} | SL=₹{defined_sl:.2f} | "
                f"W-EMA5=₹{emas['EMA_5']:.2f} | W-EMA13=₹{emas['EMA_13']:.2f} | W-EMA26=₹{emas['EMA_26']:.2f}"
            )

            if current_close <= defined_sl:
                logger.warning(f"🚨 ALERT [{ticker}]: Weekly close (₹{current_close:.2f}) breached SL threshold (₹{defined_sl:.2f})!")
                stats["sl_triggered"] += 1
                broadcast_trade_signal(
                    ticker=ticker,
                    action="EXIT / WEEKLY STOP-LOSS BREACH",
                    price=current_close,
                    target=defined_sl
                )

            if current_close < emas["EMA_5"] and current_close < emas["EMA_13"] and current_close < emas["EMA_26"]:
                logger.warning(f"🚨 ALERT [{ticker}]: Weekly close closed below all EMAs (5/13/26)!")
                stats["ema_triggered"] += 1
                broadcast_trade_signal(
                    ticker=ticker,
                    action="WEEKLY EMA BREAKDOWN (5/13/26)",
                    price=current_close,
                    target=emas["EMA_26"]
                )

        # --- 4. EVALUATE WEEKLY ATH BREAKOUT ALERTS (Universe +ADD) ---
        logger.info("--- Evaluating Universe Watchlist (Weekly ATH Breakouts) ---")
        for ticker in universe_tickers:
            yf_sym = f"{ticker}.NS"
            stats["universe_checked"] += 1
            
            current_close, _, weekly_ath = get_resampled_weekly_metrics(yf_sym)
            
            if current_close is None or np.isnan(weekly_ath):
                logger.debug(f"[{ticker}] Skipped due to missing weekly data.")
                continue

            logger.info(f"Universe -> {ticker}: Close=₹{current_close:.2f} | Weekly ATH Ref=₹{weekly_ath:.2f}")

            if current_close >= weekly_ath:
                logger.warning(f"🚨 ALERT [{ticker}]: Weekly close (₹{current_close:.2f}) hit/exceeded Weekly ATH (₹{weekly_ath:.2f})!")
                stats["ath_triggered"] += 1
                broadcast_trade_signal(
                    ticker=ticker,
                    action="WEEKLY ATH BREAKOUT",
                    price=current_close,
                    target=weekly_ath
                )

    except Exception as e:
        logger.error(f"Critical error during weekly batch processing: {e}", exc_info=True)

    elapsed_time = time.time() - start_time
    logger.info("==================================================")
    logger.info("Weekly Price Monitoring Summary:")
    logger.info(f" • Open Positions Scanned : {stats['positions_checked']}")
    logger.info(f" • Stop-Loss Breaches     : {stats['sl_triggered']}")
    logger.info(f" • EMA Breakdowns         : {stats['ema_triggered']}")
    logger.info(f" • Universe Stocks Scanned: {stats['universe_checked']}")
    logger.info(f" • ATH Breakouts Detected : {stats['ath_triggered']}")
    logger.info(f" • Total Execution Time   : {elapsed_time:.2f} seconds")
    logger.info("==================================================")


def main():
    parser = argparse.ArgumentParser(description="Run stock price alerts monitor.")
    parser.add_argument(
        "--timeframe", 
        type=str, 
        choices=["intraday", "weekly"], 
        default="intraday",
        help="Specify whether to run intraday (60m) or weekly checks."
    )
    args = parser.parse_args()

    if args.timeframe == "weekly":
        run_weekly_monitors()
    else:
        run_intraday_monitors()


if __name__ == "__main__":
    main()