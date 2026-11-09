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
@st.cache_resource
def load_supabase():
    return get_supabase_client()

supabase = load_supabase()

# --- DATA FETCHING WITH CACHING ---
@st.cache_data(ttl=300) # Cache data for 5 minutes
def fetch_table_data(table_name: str) -> pd.DataFrame:
    """Fetches all records from a specified Supabase table into a pandas DataFrame."""
    try:
        response = supabase.table(table_name).select("*").execute()
        if response.data:
            return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching table '{table_name}': {e}")
    return pd.DataFrame()

# --- HELPER FUNCTION FOR COLUMN FILTERING ---
def render_filtered_dataframe(df: pd.DataFrame, tab_key: str, default_show: list = None):
    """Renders a multiselect column filter and a dataframe."""
    if df.empty:
        return df

    all_columns = df.columns.tolist()
    if default_show is None:
        default_show = all_columns

    # Filter out columns that don't exist in the dataframe
    valid_defaults = [c for c in default_show if c in all_columns]

    selected_columns = st.multiselect(
        "Customize Visible Columns",
        options=all_columns,
        default=valid_defaults if valid_defaults else all_columns,
        key=f"col_filter_{tab_key}"
    )

    display_df = df[selected_columns] if selected_columns else df
    return display_df

# --- MAIN UI ---
st.title("📊 Stock Analyzer Dashboard")
st.markdown("---")

# Load datasets from your Supabase tables
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
        
        # Add column filtering
        open_journal_default_cols = [c for c in ["Instrument", "Status", "Holding Duration", "Qty.", "Avg. cost", "LTP", "Invested", "Cur. val", "REVISION SCORE", "ACTION"] if c in closed_journal_df.columns]
        filtered_open_df = render_filtered_dataframe(open_journal_df, tab_key="open_journal", default_show=open_journal_default_cols)
        
        st.dataframe(filtered_open_df, use_container_width=True, hide_index=True)
    else:
        st.info("No open journal records found in Supabase.")

# --- TAB 2: Closed Journal ---
with tab2:
    st.subheader("Historical Closed Journal")
    if not closed_journal_df.empty:
        st.metric(label="Total Closed Trades", value=len(closed_journal_df))
        # Filter rows strictly where ACTION equals '+ADD'
        filtered_closed = closed_journal_df[closed_journal_df["ACTION"] == "+ADD"].copy().drop_duplicates(subset="Instrument")
        
        # Add column filtering
        closed_journal_default_cols = [c for c in ["Instrument", "Status", "Sector", "Exit Date", "REVISION SCORE", "ACTION"] if c in filtered_closed.columns]
        filtered_closed_df = render_filtered_dataframe(filtered_closed, tab_key="closed_journal", default_show=closed_journal_default_cols)
        
        st.dataframe(filtered_closed_df, use_container_width=True, height=500, hide_index=True)
    else:
        st.info("No closed journal records found in Supabase.")

# --- TAB 3: Universe 750 (Filtered for ACTION = '+ADD' + Editable Remarks) ---
# --- TAB 3: Universe 750 (Filtered for ACTION = '+ADD' + Editable Remarks) ---
with tab3:
    st.subheader("Universe Stock Scans — Action: `+ADD`")
    
    if not universe_750_df.empty:
        if "ACTION" in universe_750_df.columns:
            # Filter rows strictly where ACTION equals '+ADD'
            filtered_universe = universe_750_df[universe_750_df["ACTION"] == "+ADD"].copy()
            
            st.metric(label="Filtered Stock Opportunities (+ADD)", value=len(filtered_universe))
            
            if not filtered_universe.empty:
                # Add column filtering with smart defaults
                default_cols = [c for c in ["Instrument", "Run Date", "LTP", "Sector", "Market CAP", "REVISION SCORE", "REMARKS"] if c in universe_750_df.columns]
                display_df = render_filtered_dataframe(filtered_universe, tab_key="universe_750", default_show=default_cols)

                st.markdown("---")
                
                # --- SAVE BUTTON PLACED AT THE TOP ---
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.info("💡 Double-click the **REMARKS** column cells to edit notes, then click save.")
                with col2:
                    save_clicked = st.button("💾 Save to Database", type="primary", use_container_width=True)

                # Configure editable columns (lock identity keys, make REMARKS editable)
                column_config = {}
                if "Instrument" in display_df.columns:
                    column_config["Instrument"] = st.column_config.TextColumn("Instrument", disabled=True)
                if "Run Date" in display_df.columns:
                    column_config["Run Date"] = st.column_config.TextColumn("Run Date", disabled=True)
                if "REMARKS" in display_df.columns:
                    column_config["REMARKS"] = st.column_config.TextColumn("REMARKS", help="Double-click to edit remarks", required=False)

                edited_df = st.data_editor(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config=column_config,
                    key="universe_remarks_editor",
                    height=450
                )

                # Handle Save Action when clicked
                if save_clicked:
                    try:
                        # Merge edited remarks back into the complete filtered_universe dataset 
                        # using composite primary keys ("Instrument", "Run Date") so no columns are lost!
                        if "REMARKS" in edited_df.columns:
                            # Create a mapping dictionary of (Instrument, Run Date) -> new REMARKS value
                            remarks_updates = {}
                            for _, row in edited_df.iterrows():
                                key = (row.get("Instrument"), row.get("Run Date"))
                                remarks_updates[key] = row.get("REMARKS")

                            # Apply updates back to the full dataset rows
                            for idx, row in filtered_universe.iterrows():
                                key = (row.get("Instrument"), row.get("Run Date"))
                                if key in remarks_updates:
                                    filtered_universe.loc[idx, "REMARKS"] = remarks_updates[key]

                        # Push the complete records containing all required schema columns to Supabase
                        records_to_update = filtered_universe.to_dict(orient="records")
                        supabase.table("universe_of_750_stocks_scores").upsert(records_to_update).execute()
                        
                        st.success("Successfully updated remarks and synced with Supabase!")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Failed to save changes to Supabase: {e}")
            else:
                st.warning("Found universe records, but none currently have an ACTION value of '+ADD'.")
        else:
            st.error("The 'ACTION' column was not found in the universe dataset schema.")
            st.dataframe(universe_750_df, use_container_width=True)
    else:
        st.info("No universe data found in Supabase.")