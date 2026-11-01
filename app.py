import streamlit as st
import pandas as pd
from src.utils.supabase_client import get_supabase_client

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Stock Trading Dashboard",
    page_icon="📈",
    layout="wide"
)

# --- SUPABASE CONNECTION ---
# --- CACHED SUPABASE INITIALIZATION ---
@st.cache_resource
def load_supabase():
    return get_supabase_client()

supabase = load_supabase()

# --- DATA FETCHING WITH CACHING ---
@st.cache_data(ttl=300) # Cache data for 5 minutes to reduce API hits
def fetch_table_data(table_name: str) -> pd.DataFrame:
    """Fetches all records from a specified Supabase table into a pandas DataFrame."""
    try:
        response = supabase.table(table_name).select("*").execute()
        if response.data:
            return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching table '{table_name}': {e}")
    return pd.DataFrame()

# --- MAIN UI ---
st.title("📊 Stock Analyzer Dashboard")
st.markdown("---")

# Load datasets from your Supabase tables
# (Update table names if your actual Supabase tables differ slightly)
open_journal_df = fetch_table_data("open_partial_journal")
closed_journal_df = fetch_table_data("closed_journal")
universe_750_df = fetch_table_data("universe_of_750_stocks_scores")

# --- CREATE THREE TABS ---
tab1, tab2, tab3 = st.tabs([
    "📂 Open Journal", 
    "📁 Closed Journal", 
    "🎯 Universe (+ADD Signals)"
])

# --- TAB 1: Open Journal ---
with tab1:
    st.subheader("Active Open Positions & Journal")
    if not open_journal_df.empty:
        st.metric(label="Total Open Positions", value=len(open_journal_df))
        st.dataframe(open_journal_df, use_container_width=True, hide_index=True)
    else:
        st.info("No open journal records found in Supabase.")

# --- TAB 2: Closed Journal ---
with tab2:
    st.subheader("Historical Closed Journal")
    if not closed_journal_df.empty:
        st.metric(label="Total Closed Trades", value=len(closed_journal_df))
        st.dataframe(closed_journal_df, use_container_width=True, hide_index=True)
    else:
        st.info("No closed journal records found in Supabase.")

# --- TAB 3: Universe 750 (Filtered for ACTION = '+ADD') ---
with tab3:
    st.subheader("Universe Stock Scans — Action: `+ADD`")
    
    if not universe_750_df.empty:
        if "ACTION" in universe_750_df.columns:
            # Filter rows strictly where ACTION equals '+ADD'
            filtered_universe = universe_750_df[universe_750_df["ACTION"] == "+ADD"].copy()
            
            st.metric(label="Filtered Stock Opportunities (+ADD)", value=len(filtered_universe))
            
            if not filtered_universe.empty:
                st.dataframe(filtered_universe, use_container_width=True, hide_index=True)
            else:
                st.warning("Found universe records, but none currently have an ACTION value of '+ADD'.")
        else:
            st.error("The 'ACTION' column was not found in the universe dataset schema.")
            st.dataframe(universe_750_df, use_container_width=True)
    else:
        st.info("No universe data found in Supabase.")