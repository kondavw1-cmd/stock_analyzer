import datetime
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def parse_upcoming_event(calendar_data):
    """Parses yfinance calendar data to find the nearest upcoming corporate event."""
    today = datetime.date.today()
    event_date = "TBD"
    event_name = "Board Meeting"

    if calendar_data is None:
        return event_date, event_name

    if isinstance(calendar_data, pd.DataFrame):
        try:
            if not calendar_data.empty:
                calendar_data = calendar_data.iloc[:, 0].to_dict()
            else:
                return event_date, event_name
        except Exception:
            return event_date, event_name

    if not isinstance(calendar_data, dict):
        return event_date, event_name

    norm_cal = {str(k).lower().strip(): v for k, v in calendar_data.items()}

    earnings_val = norm_cal.get("earnings date") or norm_cal.get("earnings_date")
    if earnings_val:
        target_date = (
            earnings_val[0]
            if isinstance(earnings_val, list) and len(earnings_val) > 0
            else earnings_val
        )
        if hasattr(target_date, "date"):
            target_date = target_date.date()
        elif isinstance(target_date, str):
            try:
                target_date = datetime.datetime.strptime(
                    target_date, "%Y-%m-%d"
                ).date()
            except ValueError:
                target_date = None

        if isinstance(target_date, datetime.date) and target_date >= today:
            return target_date.strftime("%Y-%m-%d"), "Earnings Call"

    ex_div = norm_cal.get("ex-dividend date") or norm_cal.get("ex_dividend_date")
    if ex_div:
        if hasattr(ex_div, "date"):
            ex_div = ex_div.date()
        elif isinstance(ex_div, str):
            try:
                ex_div = datetime.datetime.strptime(ex_div, "%Y-%m-%d").date()
            except ValueError:
                ex_div = None

        if isinstance(ex_div, datetime.date) and ex_div >= today:
            return ex_div.strftime("%Y-%m-%d"), "Dividend Ex-Date"

    return event_date, event_name


def get_market_cap_tier_inr(market_cap):
    """Categorizes asset size based on SEBI-equivalent INR thresholds."""
    if market_cap is None or pd.isna(market_cap):
        return "N/A"
    try:
        market_cap = float(market_cap)
    except (ValueError, TypeError):
        return "N/A"

    if market_cap >= 1000000000000:
        return "Mega Cap"
    elif market_cap >= 850000000000:
        return "Large Cap"
    elif market_cap >= 220000000000:
        return "Mid Cap"
    else:
        return "Small Cap"


def calculate_holding_duration_in_weeks(entry_time, exit_time=None) -> str:
    """
    Computes holding duration in weeks given entry and exit times.
    If exit_time is None (for open positions), it uses the current time.
    """
    if pd.isna(entry_time) or not entry_time:
        return ""
    
    try:
        # Convert to datetime objects if they are strings
        dt_entry = pd.to_datetime(entry_time, dayfirst=True, errors='coerce')
        if pd.isna(dt_entry):
            return ""
            
        if exit_time is not None and not pd.isna(exit_time) and str(exit_time).strip() != "":
            dt_exit = pd.to_datetime(exit_time, dayfirst=True, errors='coerce')
            if pd.isna(dt_exit):
                dt_exit = datetime.now()
        else:
            dt_exit = datetime.now()  # For open trades
            
        # Calculate delta in days
        delta_days = (dt_exit - dt_entry).days
        if delta_days < 0:
            delta_days = 0
            
        # Convert to weeks
        weeks = delta_days / 7.0
        
        # Format output cleanly
        if weeks == int(weeks):
            return f"{int(weeks)} weeks"
        else:
            return f"{weeks:.1f} weeks"
        
    except Exception as e:
        return ""

def _clean_ticker_series(series: pd.Series) -> pd.Series:
    """Safely cleans ticker strings by removing exchange suffixes, spaces, and converting to uppercase."""
    if series is None or series.empty:
        return pd.Series(dtype=str)
    return (
        series.astype(str)
        .str.replace(".NS", "", regex=False)
        .str.replace(".BO", "", regex=False)
        .str.upper()
        .str.strip()
    )

def enrich_open_journal_df(
    open_journal_df: pd.DataFrame, df_scored_results: pd.DataFrame
) -> pd.DataFrame:
    """Enriches open_journal_df with scoring and grading columns from df_scored_results without renaming."""
    if open_journal_df is None or open_journal_df.empty:
        return open_journal_df
    if df_scored_results is None or df_scored_results.empty:
        return open_journal_df

    open_df = open_journal_df.copy()
    scored_df = df_scored_results.copy()

    # Determine instrument / symbol column dynamically
    inst_col = "Instrument" if "Instrument" in open_df.columns else "symbol"
    
    # Create standardized join keys
    open_df["_join_key"] = _clean_ticker_series(open_df[inst_col])
    scored_df["_join_key"] = _clean_ticker_series(scored_df["Ticker"])

    # Drop duplicate join key columns from scored_results if they overlap
    cols_to_merge = [c for c in scored_df.columns if c != inst_col]
    
    # Vectorized left join
    merged_df = open_df.merge(scored_df[cols_to_merge], on="_join_key", how="left")
    
    # Fill missing values with empty strings for consistency
    score_cols = ["Market_Cap_Tier", "ATH_Price_Grade", "ATH_Profit_Grade", "Nifty_Alpha_Grade", "Sector_Alpha_Grade", "Review_Score", "ACTION"]
    for col in score_cols:
        if col in merged_df.columns:
            merged_df[col] = merged_df[col].fillna("")

    # Clean up temp join key and sort
    merged_df = merged_df.drop(columns=["_join_key"])
    return merged_df.sort_values(inst_col)


def enrich_closed_journal_df(
    closed_journal_df: pd.DataFrame, df_scored_results: pd.DataFrame
) -> pd.DataFrame:
    """Enriches closed_journal_df with scoring and grading columns from df_scored_results without renaming."""
    if closed_journal_df is None or closed_journal_df.empty:
        return closed_journal_df
    if df_scored_results is None or df_scored_results.empty:
        return closed_journal_df

    closed_df = closed_journal_df.copy()
    scored_df = df_scored_results.copy()

    symbol_col = "symbol" if "symbol" in closed_df.columns else "Instrument"
    
    closed_df["_join_key"] = _clean_ticker_series(closed_df[symbol_col])
    scored_df["_join_key"] = _clean_ticker_series(scored_df["Ticker"])

    cols_to_merge = [c for c in scored_df.columns if c != symbol_col]
    merged_df = closed_df.merge(scored_df[cols_to_merge], on="_join_key", how="left")

    score_cols = ["Market_Cap_Tier", "ATH_Price_Grade", "ATH_Profit_Grade", "Nifty_Alpha_Grade", "Sector_Alpha_Grade", "Review_Score", "ACTION"]
    for col in score_cols:
        if col in merged_df.columns:
            merged_df[col] = merged_df[col].fillna("")

    return merged_df.drop(columns=["_join_key"])

def build_universe_750_scores_df(
    df_scored_results: pd.DataFrame,
    total_capital: float = 150000.0,
    allocation_pct: float = 0.065,
    open_journal_df: pd.DataFrame = None,
) -> pd.DataFrame:
    """
    Builds the universe 750 scores DataFrame with exact output columns,
    dynamic position sizing, and automated open-trade remark checking.
    """
    if df_scored_results is None or df_scored_results.empty:
        return pd.DataFrame()

    # Extract standardized set of open symbols for remark matching
    open_symbols = set()
    if open_journal_df is not None and not open_journal_df.empty and "Instrument" in open_journal_df.columns:
        open_symbols = set(open_journal_df["Instrument"].astype(str).str.strip().str.upper())

    assembled_rows = []
    for _, row in df_scored_results.iterrows():
        ticker = row.get("Ticker", "")
        ticker_clean = str(ticker).strip().upper()
        stock_price = row.get("Stock_Price", 0.0)
        
        # Calculate allowed investment and shares dynamically
        allowed_inv = (total_capital * allocation_pct) if total_capital > 0 else 0.0
        allowed_shs = int(allowed_inv / stock_price) if stock_price and stock_price > 0 else 0

        # Evaluate remarks based on open positions
        remarks_val = (
            "Already In Trade" if ticker_clean in open_symbols else ""
        )

        row_data = {
            "Instrument": ticker,
            "LTP": stock_price,
            "Sector": row.get("Sector", ""),
            "Broad Based Index": row.get("Board_Based", ""),
            "Market CAP": row.get("Market_Cap_Tier", ""),
            "Upcoming Event Date": row.get("Upcoming_Event_Date", ""),
            "Upcoming Event Name": row.get("Upcoming_Event_Name", ""),
            "Volatility_%": row.get("Volatility_%", 0.0),
            "Sharpe_Ratio": row.get("Sharpe_Ratio", 0.0),
            "ATH (P-66%)": row.get("ATH_Price_Grade", ""),
            "ATP (P-75%)": row.get("ATH_Profit_Grade", ""),
            "Nifty 500 [OTP] (P-82%)": row.get("Nifty_Alpha_Grade", ""),
            "Sector Index (P-82%)": row.get("Sector_Alpha_Grade", ""),
            "REVISION SCORE": row.get("Review_Score", ""),
            "ACTION": row.get("ACTION", ""),
            "Allowed Investment": allowed_inv,
            "Allowed Shares": allowed_shs,
            "REMARKS": remarks_val,
        }
        assembled_rows.append(row_data)

    universe_df = pd.DataFrame(assembled_rows)
    return universe_df.sort_values("Instrument")