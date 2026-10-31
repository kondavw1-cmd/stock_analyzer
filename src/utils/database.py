import os
import logging
import numpy as np
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

url: str = os.environ.get("SUPABASE_URL")
# logger.info("SUPABASE_URL: {os.environ.get('SUPABASE_URL')}")
key: str = os.environ.get("SUPABASE_KEY")
# logger.info("SUPABASE_KEY: {os.environ.get('SUPABASE_KEY')}")

from datetime import datetime

supabase: Client = None
if url and key:
    try:
        supabase = create_client(url, key)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")


def save_dataframe_to_sql(df: pd.DataFrame, table_name: str, if_exists: str = "replace"):
    """Saves a pandas DataFrame to Supabase using the REST API client with NaN cleaning."""
    if df is None or df.empty:
        logger.warning(f"DataFrame for table '{table_name}' is empty. Skipping upload.")
        return

    if not supabase:
        logger.error("Supabase client is not initialized. Check your SUPABASE_URL and SUPABASE_KEY.")
        return

    try:
        # Step 1: Clean DataFrame to make it fully JSON compliant
        # Replace NaN, NaT, infinite values, and empty strings with None (SQL NULL)
        df_clean = df.replace(r'^\s*$', None, regex=True)
        df_clean = df_clean.replace({np.nan: None, pd.NaT: None, np.inf: None, -np.inf: None, "": None})
        
        # Convert any remaining invalid/null floats
        df_clean = df_clean.astype(object).where(pd.notnull(df_clean), None)

        # Before calling save_dataframe_to_sql
        run_timestamp = datetime.now().strftime('%Y-%m-%d')
        df_clean["Last Updated At"] = run_timestamp

        # If it's a brand new record, you can also inject "Created At" if not already present
        if "Created At" not in df_clean.columns:
            df_clean["Created At"] = run_timestamp

        # Convert DataFrame records to a list of dictionaries
        records = df_clean.to_dict(orient="records")

        # If 'replace' is requested, clear the table first
        if if_exists == "replace":
            try:
                supabase.table(table_name).delete().neq("id", -1).execute()
            except Exception:
                pass  # If table doesn't have an 'id' column or is empty, proceed

        # Insert records in chunks of 500 to respect payload limits
        chunk_size = 500
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            response = supabase.table(table_name).upsert(chunk).execute()
            
        logger.info(f"[Success] Successfully synced {len(records)} rows to Supabase table '{table_name}' via REST API.")

    except Exception as e:
        logger.error(f"Failed to save DataFrame to Supabase table '{table_name}': {e}")
        raise

def process_action_history(current_df: pd.DataFrame) -> pd.DataFrame:
    """
    Manages rolling 4-week ACTION history:
    - Current week: Day 1 to Day 5
    - Past weeks: Week 2, Week 3, Week 4 (representing past Friday actions)
    """
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    current_weekday = today.weekday()  # 0 = Monday, 4 = Friday, etc.
    
    # Map weekday (0-4) to Day column name
    day_mapping = {0: "Day 1", 1: "Day 2", 2: "Day 3", 3: "Day 4", 4: "Day 5"}
    current_day_col = day_mapping.get(current_weekday, "Day 5") # Default to Day 5 if run on weekends

    # 1. Fetch existing history from Supabase
    existing_data = []
    try:
        # To this (fetches everything cleanly):
        response = supabase.table("universe_of_750_stocks_scores").select("*").execute()
        if response.data:
            existing_data = response.data
    except Exception as e:
        print(f"Could not fetch existing action history: {e}")

    history_map = {item["Instrument"]: item for item in existing_data}

    # 2. Initialize history columns if not present
    for col in ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Week 2", "Week 3", "Week 4"]:
        if col not in current_df.columns:
            current_df[col] = None

    # 3. Iterate through current df and merge/shift historical actions
    updated_rows = []
    for _, row in current_df.iterrows():
        instrument = row["Instrument"]
        new_action = row["ACTION"]
        
        hist = history_map.get(instrument, {})
        last_run_date = hist.get("Last Run Date")
        
        # Determine if this is a new week compared to the last run
        is_new_week = False
        if last_run_date:
            last_date_obj = datetime.strptime(last_run_date, "%Y-%m-%d")
            # If current week number or year is greater, it's a new week
            if today.isocalendar()[1] > last_date_obj.isocalendar()[1] or today.year > last_date_obj.year:
                is_new_week = True

        if is_new_week:
            # Shift old week's Friday (Day 5 or latest active day) into Week 2, and cascade
            last_friday_action = hist.get("Day 5") or hist.get("Day 4") or hist.get("Day 3") or hist.get("Day 2") or hist.get("Day 1")
            
            row["Week 4"] = hist.get("Week 3")
            row["Week 3"] = hist.get("Week 2")
            row["Week 2"] = last_friday_action
            
            # Reset current week days for the new week
            row["Day 1"] = new_action if current_day_col == "Day 1" else None
            row["Day 2"] = new_action if current_day_col == "Day 2" else None
            row["Day 3"] = new_action if current_day_col == "Day 3" else None
            row["Day 4"] = new_action if current_day_col == "Day 4" else None
            row["Day 5"] = new_action if current_day_col == "Day 5" else None
        else:
            # Same week: retain previous historical columns
            row["Week 4"] = hist.get("Week 4")
            row["Week 3"] = hist.get("Week 3")
            row["Week 2"] = hist.get("Week 2")
            row["Day 1"] = hist.get("Day 1")
            row["Day 2"] = hist.get("Day 2")
            row["Day 3"] = hist.get("Day 3")
            row["Day 4"] = hist.get("Day 4")
            row["Day 5"] = hist.get("Day 5")
            
            # Update the specific day column for today's run
            row[current_day_col] = new_action

        row["Last Run Date"] = today_str
        updated_rows.append(row)

    return pd.DataFrame(updated_rows)