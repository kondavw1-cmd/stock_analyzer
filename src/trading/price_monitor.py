import logging
import pandas as pd
import yfinance as yf
from src.utils.database import load_dataframe_from_sql
from src.utils.notifications import broadcast_trade_signal

logger = logging.getLogger(__name__)


def check_intraday_price_alerts():
    logger.info("Starting intraday price monitor check...")
    
    # Load open positions from Supabase table or local source
    open_df = load_dataframe_from_sql("open_partial_journal")
    
    if open_df.empty:
        logger.info("No open positions found in database to monitor.")
        return

    for _, row in open_df.iterrows():
        ticker = str(row.get("Instrument", "")).replace(".NS", "").upper()
        if not ticker:
            continue
            
        yahoo_ticker = f"{ticker}.NS"
        avg_cost = float(row.get("Avg. cost", 0.0))
        defined_sl = float(row.get("Defined SL [RISK]", avg_cost * 0.95))

        try:
            # Fetch latest live quote
            stock = yf.Ticker(yahoo_ticker)
            todays_data = stock.history(period="1d")
            
            if todays_data.empty:
                continue
                
            current_ltp = float(todays_data["Close"].iloc[-1])
            
            logger.info(f"Monitoring {ticker}: LTP = ₹{current_ltp:.2f} | SL Target = ₹{defined_sl:.2f}")

            # Check if price breached stop-loss / target threshold
            if current_ltp <= defined_sl:
                logger.warning(f"ALERT: {ticker} has breached stop-loss threshold!")
                broadcast_trade_signal(
                    ticker=ticker,
                    action="EXIT / STOP-LOSS BREACH",
                    price=current_ltp,
                    target=defined_sl
                )
        except Exception as e:
            logger.error(f"Error checking live price for {ticker}: {e}")

    logger.info("Intraday price monitoring check completed.")