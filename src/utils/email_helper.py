import os
import logging
from datetime import datetime
import pandas as pd
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger(__name__)

def send_report_via_email(local_filepath: str, filename: str) -> bool:
    """
    Directly attaches and sends the generated Excel report via Gmail API.
    """
    if not local_filepath or not os.path.exists(local_filepath):
        logger.error(f"Missing file path for email attachment: {local_filepath}")
        return False

    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        
        token_path = "token.json"
        creds = None
        
        if os.environ.get("GDRIVE_TOKEN_JSON"):
            import json
            token_info = json.loads(os.environ.get("GDRIVE_TOKEN_JSON"))
            creds = Credentials.from_authorized_user_info(token_info, ['https://www.googleapis.com/auth/gmail.send'])
        elif os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, ['https://www.googleapis.com/auth/gmail.send'])
            
        if not creds:
            logger.error("Gmail authentication credentials not found.")
            return False

        service = build('gmail', 'v1', credentials=creds)

        # Build clean email message for sheet delivery
        message = MIMEMultipart()
        message['To'] = ["kondavw1@gmail.com", "g.sure1992@gmail.com"]
        message['Subject'] = f'Portfolio Analyzer Report - {datetime.now().strftime("%Y-%m-%d")}'

        # Minimal body text since the sheet is the primary payload
        body = f"Automated 750-stock portfolio analyzer report attached: {filename}"
        message.attach(MIMEText(body, 'plain'))

        # Attach Excel file
        with open(local_filepath, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename= {filename}")
        message.attach(part)

        # Encode and send
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        service.users().messages().send(userId="me", body={'raw': raw_message}).execute()
        
        logger.info(f"Successfully shared sheet via email: {filename}")
        return True

    except Exception as e:
        logger.error(f"Failed to send sheet via email: {e}")
        return False

def export_and_email_report(
    df_scored_results: pd.DataFrame,
    universe_750_df: pd.DataFrame,
    open_journal_df: pd.DataFrame = None,
    closed_journal_df: pd.DataFrame = None,
    local_dir: str = "data"
) -> bool:
    """
    1. Formats and saves the multi-tab Excel report locally.
    2. Emails the sheet as an attachment.
    3. Cleans up the local copy upon successful dispatch.
    """
    os.makedirs(local_dir, exist_ok=True)
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"Portfolio_Analyzer_Universe_{date_str}.xlsx"
    local_filepath = os.path.join(local_dir, filename)

    try:
        from src.utils.excel_generator import export_to_excel_direct
        
        # 1. Write and format file locally
        export_to_excel_direct(
            output_path=local_filepath,
            df_scored_results=df_scored_results,
            universe_750_df=universe_750_df,
            open_journal_df=open_journal_df,
            closed_journal_df=closed_journal_df
        )

        # 2. Send Sheet via Email
        email_success = send_report_via_email(local_filepath, filename)
        
        if email_success:
            # 3. Clean up local file after dispatch
            if os.path.exists(local_filepath):
                os.remove(local_filepath)
            return True
        else:
            logger.error("Email sheet delivery failed. Local file retained.")
            return False

    except Exception as e:
        logger.error(f"Error during export and email workflow: {e}")
        return False