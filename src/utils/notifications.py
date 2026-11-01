import email.message
import logging
import os
import smtplib
import requests
import pandas as pd

logger = logging.getLogger(__name__)


import os
import requests
import pandas as pd
from tabulate import tabulate

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def send_discord_embed(title: str, dataframe: pd.DataFrame, color_int: int):
    """
    Sends a dataframe formatted as a clean, non-wrapping markdown table inside a Discord Embed.
    """
    if dataframe is None or dataframe.empty or not DISCORD_WEBHOOK_URL:
        return

    # Use tabulate to format a clean grid table ("presto" or "simple" fit best in Discord)
    table_str = tabulate(dataframe, headers="keys", tablefmt="double_outline", showindex=False)
    description = f"```\n{table_str}\n```"

    payload = {
        "embeds": [
            {
                "title": title,
                "description": description,
                "color": color_int,
            }
        ]
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        if response.status_code==204:
            logger.info(f"[DISCORD ALERT SUCCESS] {title}")
    except Exception as e:
        print(f"Failed to send Discord embed: {e}")

def send_filtered_table_notifications(open_df: pd.DataFrame, closed_df: pd.DataFrame, universe_df: pd.DataFrame):
    
    # 1. Open-Partial-Journal (Action != '+ADD')
    if open_df is not None and not open_df.empty and "ACTION" in open_df.columns:
        filtered_open = open_df[open_df["ACTION"] != "+ADD"].drop_duplicates(subset=["Instrument"])
        if not filtered_open.empty:
            cols = ["Instrument", "REVISION SCORE", "ACTION"]
            sub = filtered_open[[c for c in cols if c in filtered_open.columns]].copy()
            send_discord_embed("⚠️ Open / Partial Journal (Action != +ADD)", sub, color_int=16753920)

    # 2. Closed_Journal (Action == '+ADD')
    if closed_df is not None and not closed_df.empty and "ACTION" in closed_df.columns:
        filtered_closed = closed_df[closed_df["ACTION"] == "+ADD"].drop_duplicates(subset=["Instrument"])
        if not filtered_closed.empty:
            cols = ["Instrument", "REVISION SCORE", "ACTION"]
            sub = filtered_closed[[c for c in cols if c in filtered_closed.columns]].copy()
            send_discord_embed("🟢 Closed Journal (Action == +ADD)", sub, color_int=3066993)

    # 3. Universe of 750 Stocks (Action == '+ADD') - Renaming long headers for compact tabular fit
    if universe_df is not None and not universe_df.empty and "ACTION" in universe_df.columns:
        filtered_universe = universe_df[universe_df["ACTION"] == "+ADD"].drop_duplicates(subset=["Instrument"])
        if not filtered_universe.empty:
            cols = [
                "Instrument", "REVISION SCORE", "ACTION"
            ]
            sub = filtered_universe[[c for c in cols if c in filtered_universe.columns]].copy()
            
            send_discord_embed("🚀 Universe Stock Alerts (Action == +ADD)", sub, color_int=2067276)

def send_discord_alert(title: str, description: str, is_error: bool = False):
    """Sends a rich-embed push notification to Discord via Webhook URL."""

    if not DISCORD_WEBHOOK_URL:
        logger.warning("DISCORD_WEBHOOK_URL not found in environment. Skipping Discord alert.")
        return

    # Color code: Red for error/failure (15158332), Green for success (3066993)
    color = 15158332 if is_error else 3066993

    payload = {
        "embeds": [
            {
                "title": title,
                "description": description,
                "color": color,
                "footer": {"text": "Portfolio Cloud Automation Engine"}
            }
        ]
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code == 204:
            logger.info("Discord alert sent successfully.")
        else:
            logger.error(f"Failed to send Discord alert: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error sending Discord notification: {e}", exc_info=True)


def send_email_alert(subject: str, body: str, is_error: bool = False):
    """Sends a detailed email alert using Gmail SMTP and GitHub Secrets."""
    sender_email = os.getenv("MAIL_SENDER")
    sender_password = os.getenv("MAIL_PASSWORD")
    receiver_email = os.getenv("MAIL_RECEIVER")

    if not sender_email or not sender_password or not receiver_email:
        logger.warning("Email credentials (MAIL_SENDER/PASSWORD/RECEIVER) not found. Skipping email alert.")
        return

    try:
        msg = email.message.EmailMessage()
        msg["Subject"] = f"🔴 [FAILURE] Portfolio Analyzer" if is_error else f"🟢 [SUCCESS] Portfolio Analyzer"
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg.set_content(body)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)

        logger.info(f"Email alert sent successfully to {receiver_email}")
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}", exc_info=True)


def notify_pipeline_status(status: str, details: str, is_error: bool = False):
    """Unified dispatcher for pipeline notifications across Discord and Email."""
    title = "❌ Pipeline Failure" if is_error else "✅ Pipeline Success"
    
    # Send instant Discord push notification
    send_discord_alert(title=title, description=details, is_error=is_error)

    # # Send detailed email report
    # subject = "Pipeline Failure" if is_error else "Pipeline Success"
    # send_email_alert(subject=subject, body=details, is_error=is_error)


def broadcast_trade_signal(ticker: str, action: str, price: float, target: float):
    """Specialized Discord embed for real-time buy/sell execution signals from the intraday monitor."""
    is_buy = "BUY" in action.upper() or "ADD" in action.upper()
    color = 3066993 if is_buy else 15158332
    
    title = f"🚨 TRADING SIGNAL: {action.upper()} ({ticker})"
    description = (
        f"**Ticker:** `{ticker}`\n"
        f"**Live LTP:** `₹{price:.2f}`\n"
        f"**Target Threshold:** `₹{target:.2f}`\n"
        f"**Action Required:** Review setup and execute."
    )
    
    if not DISCORD_WEBHOOK_URL:
        return

    payload = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": color,
            "footer": {"text": "Intraday Price Watcher Engine"}
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Failed to broadcast trade signal: {e}", exc_info=True)