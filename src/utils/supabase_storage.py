import os
from datetime import datetime, timedelta
from supabase import create_client
import pandas as pd

from src.utils.supabase_client import get_supabase_client
supabase = get_supabase_client()

BUCKET_NAME = "stock-reports"
FOLDER_NAME = "daily-reports"

import logging

logger = logging.getLogger(__name__)

def upload_report_and_prune(local_file_path: str) -> str:
    """
    Uploads the latest Excel report to Supabase Storage, prunes reports 
    older than 5 days, and returns a 24-hour signed download URL.
    """
    if not os.path.exists(local_file_path):
        print(f"[ERROR] Local report not found at {local_file_path}")
        return None

    today_str = datetime.now().strftime("%Y-%m-%d")
    file_name = f"stock_report_{today_str}.xlsx"
    storage_path = f"{FOLDER_NAME}/{file_name}"

    try:
        # 1. Upload new Excel file (upsert replaces if ran multiple times in a day)
        print(f"[INFO] Uploading {file_name} to Supabase Storage ({BUCKET_NAME})...")
        with open(local_file_path, "rb") as f:
            supabase.storage.from_(BUCKET_NAME).upload(
                path=storage_path,
                file=f,
                file_options={
                    "upsert": "true", 
                    "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                }
            )

        # 2. Enforce 5-Day Rolling Retention Policy
        print("[INFO] Enforcing 5-day history retention policy...")
        files = supabase.storage.from_(BUCKET_NAME).list(FOLDER_NAME)
        cutoff_date = datetime.utcnow() - timedelta(days=5)
        files_to_delete = []

        for file in files:
            created_at_str = file.get("created_at")
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
                if created_at < cutoff_date:
                    old_file_name = file.get("name")
                    files_to_delete.append(f"{FOLDER_NAME}/{old_file_name}")

        if files_to_delete:
            supabase.storage.from_(BUCKET_NAME).remove(files_to_delete)
            print(f"[INFO] Purged {len(files_to_delete)} report(s) older than 5 days: {files_to_delete}")
        else:
            print("[INFO] No outdated reports found beyond the 5-day threshold.")

        logger.info(f"[INFO] Supabase Storage operation success: {local_file_path}")
        return True

    except Exception as e:
        print(f"[ERROR] Supabase Storage operation failed: {e}")
        return None

def export_and_upload_report_and_prune(df_scored_results: pd.DataFrame,
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
        email_success = upload_report_and_prune(local_filepath)
        
        if email_success:
            # 3. Clean up local file after dispatch
            if os.path.exists(local_filepath):
                os.remove(local_filepath)
            return True
        else:
            logger.error("Upload sheet to Supabase Storage is failed. Local file retained.")
            return False

    except Exception as e:
        logger.error(f"Error during export and upload workflow: {e}")
        return False
