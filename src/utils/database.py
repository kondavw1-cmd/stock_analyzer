import os
import logging
import numpy as np
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

from datetime import datetime

supabase: Client = None
if url and key:
    try:
        supabase = create_client(url, key)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")

def _fetch_all_existing_data(table_name):
    """Fetches all rows and all columns from Supabase."""
    existing_data = []
    existing_instruments = dict()
    try:
        response = supabase.table(table_name).select("*").execute()
        if response.data:
            existing_data = response.data
            existing_instruments = {item["Instrument"]:item["Created At"] for item in existing_data}
        return existing_instruments, {item["Instrument"]: item for item in existing_data}
    except Exception as e:
        print(f"[WARNING] Could not fetch existing data: {e}")

def save_dataframe_to_sql(df: pd.DataFrame, table_name: str):
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
        # Generate full ISO timestamp string
        run_timestamp = datetime.now().strftime('%Y-%m-%d')
        df_clean["Last Updated At"] = run_timestamp

        if table_name in ["universe_of_750_stocks_scores"]:
            # If it's a brand new record, you can also inject "Created At" if not already present
            instrument_kyes, _ = _fetch_all_existing_data(table_name)
            if len(instrument_kyes)==0:
                    df_clean["Created At"] = run_timestamp
            else:
                for instrument, created_at in instrument_kyes.items():
                    if instrument not in df_clean["Instrument"].values:
                        df_clean["Created At"] = run_timestamp
                    else:
                        df_clean["Created At"] = created_at
    
        # Convert DataFrame records to a list of dictionaries
        records = df_clean.to_dict(orient="records")

        # Insert records in chunks of 500 to respect payload limits
        chunk_size = 500
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            response = supabase.table(table_name).upsert(chunk).execute()
            
        logger.info(f"[Success] Successfully synced {len(records)} rows to Supabase table '{table_name}' via REST API.")

    except Exception as e:
        logger.error(f"Failed to save DataFrame to Supabase table '{table_name}': {e}")
        raise

def process_action_history(current_df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """
    Manages rolling 4-week ACTION history:
    - Current week: Monday to Friday
    - Past weeks: Week 2, Week 3, Week 4 (representing past Friday actions)
    """
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    current_weekday = today.weekday()  # 0 = Monday, 4 = Friday, etc.
    
    # Map weekday (0-4) to Day column name
    day_mapping = {0: "Monday", 1: "Tuesday", 2: "Wensday", 3: "Thursday", 4: "Friday"}
    current_day_col = day_mapping.get(current_weekday, "Friday") # Default to Friday if run on weekends

    _, history_map = _fetch_all_existing_data(table_name)

    # 2. Initialize history columns if not present
    for col in ["Monday", "Tuesday", "Wensday", "Thursday", "Friday", "Week 2", "Week 3", "Week 4"]:
        if col not in current_df.columns:
            current_df[col] = None

    # 3. Iterate through current df and merge/shift historical actions
    updated_rows = []
    for _, row in current_df.iterrows():
        instrument = row["Instrument"]
        new_action = row["ACTION"]
        
        hist = history_map.get(instrument, {})
        last_run_date = hist.get("Last Updated At")
        
        # Determine if this is a new week compared to the last run
        is_new_week = False
        if last_run_date:
            last_date_obj = datetime.strptime(last_run_date, "%Y-%m-%d")
            # If current week number or year is greater, it's a new week
            if today.isocalendar()[1] > last_date_obj.isocalendar()[1] or today.year > last_date_obj.year:
                is_new_week = True

        if is_new_week:
            # Shift old week's Friday (Friday or latest active day) into Week 2, and cascade
            last_friday_action = hist.get("Friday") or hist.get("Thursday") or hist.get("Wensday") or hist.get("Tuesday") or hist.get("Monday")
            
            row["Week 4"] = hist.get("Week 3")
            row["Week 3"] = hist.get("Week 2")
            row["Week 2"] = last_friday_action
            
            # Reset current week days for the new week
            row["Monday"] = new_action if current_day_col == "Monday" else None
            row["Tuesday"] = new_action if current_day_col == "Tuesday" else None
            row["Wensday"] = new_action if current_day_col == "Wensday" else None
            row["Thursday"] = new_action if current_day_col == "Thursday" else None
            row["Friday"] = new_action if current_day_col == "Friday" else None
        else:
            # Same week: retain previous historical columns
            row["Week 4"] = hist.get("Week 4")
            row["Week 3"] = hist.get("Week 3")
            row["Week 2"] = hist.get("Week 2")
            row["Monday"] = hist.get("Monday")
            row["Tuesday"] = hist.get("Tuesday")
            row["Wensday"] = hist.get("Wensday")
            row["Thursday"] = hist.get("Thursday")
            row["Friday"] = hist.get("Friday")
            
            # Update the specific day column for today's run
            row[current_day_col] = new_action

        row["Last Updated At"] = today_str
        updated_rows.append(row)

    return pd.DataFrame(updated_rows)