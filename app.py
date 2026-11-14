import streamlit as st
import pandas as pd
import plotly.express as px
from src.utils.supabase_client import get_supabase_client
import requests


# ==========================================
# 1. STREAMLIT CONFIG & STYLING
# ==========================================
st.set_page_config(
    page_title="Stock Analyzer & Portfolio Dashboard",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Automated Portfolio & Trading Summary Dashboard")
st.markdown("---")

# ==========================================
# 2. SUPABASE CONNECTION SETUP
# ==========================================
@st.cache_resource
def load_supabase():
    return get_supabase_client()

supabase = load_supabase()

# ==========================================
# 3. DATA FETCHING UTILITIES
# ==========================================
@st.cache_data(ttl=600)
def fetch_table_data(table_name: str) -> pd.DataFrame:
    if not supabase:
        return pd.DataFrame()
    try:
        response = supabase.table(table_name).select("*").execute()
        data = response.data
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception as e:
        st.warning(f"Error fetching table '{table_name}': {e}")
        return pd.DataFrame()

# Load Dataframes from Supabase tables
open_df = fetch_table_data("open_partial_journal")
closed_df = fetch_table_data("closed_journal")
universe_df = fetch_table_data("universe_of_750_stocks_scores")
sector_history_df = fetch_table_data("sector_momentum_history")
industry_history_df = fetch_table_data("industry_momentum_history")

# ==========================================
# 4. TOP KPI METRICS BANNER
# ==========================================
total_invested = open_df["Invested"].sum() if not open_df.empty and "Invested" in open_df.columns else 0.0
total_current_val = open_df["Cur. val"].sum() if not open_df.empty and "Cur. val" in open_df.columns else 0.0
total_open_pnl = open_df["P&L"].sum() if not open_df.empty and "P&L" in open_df.columns else 0.0
total_realized_pnl = closed_df["Net Pnl"].sum() if not closed_df.empty and "Net Pnl" in closed_df.columns else 0.0
active_positions_count = len(open_df) if not open_df.empty else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Active Positions", f"{active_positions_count}")
col2.metric("Total Invested", f"₹{total_invested:,.2f}")
col3.metric("Current Value", f"₹{total_current_val:,.2f}")
col4.metric("Open P&L", f"₹{total_open_pnl:,.2f}", delta_color="normal" if total_open_pnl >= 0 else "inverse")
col5.metric("Realized P&L", f"₹{total_realized_pnl:,.2f}", delta_color="normal" if total_realized_pnl >= 0 else "inverse")

st.markdown("---")

# ==========================================
# 5. MULTI-TAB NAVIGATION
# ==========================================
tab_open, tab_closed, tab_universe, tab_momentum = st.tabs([
    "📂 Open Positions", 
    "📜 Closed Trade History", 
    "🔍 750 Stock Universe", 
    "📊 Multi-Tier Momentum & Rotation"
])

# --- TAB 1: OPEN POSITIONS ---
with tab_open:
    st.subheader("Active Open & Partial Positions")
    if not open_df.empty:
        st.dataframe(open_df, use_container_width=True, hide_index=True)
    else:
        st.info("No active open positions found in Supabase.")

# --- TAB 2: CLOSED TRADE HISTORY ---
with tab_closed:
    st.subheader("Historical Closed Trades & Charges")
    if not closed_df.empty:
        st.dataframe(closed_df, use_container_width=True, hide_index=True)
    else:
        st.info("No closed trade history found in Supabase.")

# --- TAB 3: STOCK UNIVERSE ---
with tab_universe:
    st.subheader("750-Stock Universe Scorer & Opportunities")
    if not universe_df.empty:
        search_query = st.text_input("Search Symbol or Sector in Universe", "").upper()
        filtered_univ = universe_df
        if search_query:
            filtered_univ = universe_df[
                universe_df["Instrument"].str.upper().str.contains(search_query, na=False) |
                universe_df["Sector"].str.upper().str.contains(search_query, na=False)
            ]
        st.dataframe(filtered_univ, use_container_width=True, hide_index=True)
    else:
        st.info("Universe scored table is empty or not loaded.")

# --- TAB 4: MULTI-TIER MOMENTUM & ROTATION HEATMAP ---
with tab_momentum:
    st.subheader("Multi-Tier Institutional Momentum & Rotation")
    
# Tooltip / Guide Expander explaining how to use Tab 4
    with st.expander("ℹ️ How to Read This Dashboard & Momentum Guide", expanded=False):
        st.markdown("""
        This tab tracks institutional capital rotation across macro sectors and micro industries. Use the filters below to switch tiers and inspect underlying market strengths.
        
        **🧠 Attribute Reference Guide:**
        * **Total Stocks (`total_stocks`):** Total count of instruments tracked within the specific sector or industry group (`len(group)`).
        * **Action Buys (`action_buys`):** Total number of stocks in the group currently flagged with the `+ADD` execution trigger. Higher counts signal aggressive institutional accumulation.
        * **Average Sharpe Ratio (`avg_sharpe`):** Mean risk-adjusted return metric (`Sharpe_Ratio`) across the group's constituents. Higher scores mean better return per unit of volatility.
        * **Average Review Score (`avg_review_score`):** Mean fundamental and technical score (`Review_Score`) assigned by your scoring engine.
        * **Relative Strength / Sector Return (`relative_strength`):** The average sector year return (`Sector_Year_Return`) used as a proxy for relative strength against broader market baselines *(Sector view only)*.
        * **Sector Alpha (`sector_alpha`):** Mean excess return generated by the sector compared to the benchmark (`Sector_Alpha`). Positive values indicate macro outperformance *(Sector view only)*.
        * **Avg Distance from ATH (`avg_distance_from_ath`):** Mean percentage distance from All-Time Highs (`Distance_From_ATH_%`). Scores closer to 0% indicate structural market leadership and imminent breakouts.
        """)

    tier_choice = st.radio("Select Analysis Tier", ["Sector Macro View", "Industry Micro View"], horizontal=True)
    st.markdown("---")
    
    if tier_choice == "Sector Macro View":
        st.markdown("#### 🔥 Sector Momentum Heatmap & Capital Flows")
        if not sector_history_df.empty:
            col_metric, col_mode, col_sort = st.columns([2, 2, 1])
            with col_metric:
                metric = st.selectbox(
                    "Sector Metric",
                    options=["action_buys", "sector_alpha", "relative_strength", "avg_sharpe", "avg_review_score", "avg_distance_from_ath"],
                    format_func=lambda x: x.replace("_", " ").title(),
                    key="sector_metric_sel"
                )
            with col_mode:
                view_mode = st.radio(
                    "View Mode", 
                    ["Absolute Values", "Week-over-Week Change (Delta)"], 
                    horizontal=True,
                    key="sector_mode_sel"
                )
            with col_sort:
                top_n = st.slider("Top N Sectors", min_value=5, max_value=20, value=12, key="sector_topn_sel")

            df_clean = sector_history_df.copy()
            df_clean["snapshot_date"] = pd.to_datetime(df_clean["snapshot_date"]).dt.strftime("%Y-%m-%d")
            
            pivot_df = df_clean.pivot_table(
                index="sector",
                columns="snapshot_date",
                values=metric,
                aggfunc="mean"
            ).fillna(0)

            pivot_df = pivot_df.reindex(sorted(pivot_df.columns), axis=1)

            if view_mode == "Week-over-Week Change (Delta)" and len(pivot_df.columns) > 1:
                pivot_df = pivot_df.diff(axis=1).fillna(0)

            latest_date = pivot_df.columns[-1]
            pivot_df = pivot_df.sort_values(by=latest_date, ascending=False).head(top_n)

            fig = px.imshow(
                pivot_df,
                labels=dict(x="Snapshot Date", y="Sector", color=metric.replace("_", " ").title()),
                x=pivot_df.columns,
                y=pivot_df.index,
                color_continuous_scale="RdYlGn",
                text_auto=".2f" if metric in ["sector_alpha", "relative_strength", "avg_sharpe"] else ".0f",
                aspect="auto"
            )

            fig.update_layout(
                height=max(450, len(pivot_df) * 32),
                xaxis_side="top",
                xaxis_title="",
                yaxis_title="",
                xaxis=dict(type="category")  # <-- Forces discrete category labels
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sector history snapshot data found in 'sector_momentum_history'. Run your pipeline to populate snapshots.")
            
    else:
        st.markdown("#### 🔬 Industry Momentum Heatmap & Sub-Niche Rotation")
        if not industry_history_df.empty:
            ind_df = industry_history_df.copy()
            ind_df["sector_industry"] = ind_df["sector"] + " ➔ " + ind_df["industry"]
            
            col_metric, col_mode, col_sort = st.columns([2, 2, 1])
            with col_metric:
                metric = st.selectbox(
                    "Industry Metric",
                    options=["action_buys", "avg_review_score", "avg_sharpe", "avg_distance_from_ath"],
                    format_func=lambda x: x.replace("_", " ").title(),
                    key="industry_metric_sel"
                )
            with col_mode:
                view_mode = st.radio(
                    "View Mode", 
                    ["Absolute Values", "Week-over-Week Change (Delta)"], 
                    horizontal=True,
                    key="industry_mode_sel"
                )
            with col_sort:
                top_n = st.slider("Top N Industries", min_value=5, max_value=25, value=15, key="industry_topn_sel")

            ind_df["snapshot_date"] = pd.to_datetime(ind_df["snapshot_date"]).dt.strftime("%Y-%m-%d")
            
            pivot_df = ind_df.pivot_table(
                index="sector_industry",
                columns="snapshot_date",
                values=metric,
                aggfunc="mean"
            ).fillna(0)

            pivot_df = pivot_df.reindex(sorted(pivot_df.columns), axis=1)

            if view_mode == "Week-over-Week Change (Delta)" and len(pivot_df.columns) > 1:
                pivot_df = pivot_df.diff(axis=1).fillna(0)

            latest_date = pivot_df.columns[-1]
            pivot_df = pivot_df.sort_values(by=latest_date, ascending=False).head(top_n)

            fig = px.imshow(
                pivot_df,
                labels=dict(x="Snapshot Date", y="Sector / Industry", color=metric.replace("_", " ").title()),
                x=pivot_df.columns,
                y=pivot_df.index,
                color_continuous_scale="RdYlGn",
                text_auto=".2f" if metric == "avg_sharpe" else ".0f",
                aspect="auto"
            )

            fig.update_layout(
                height=max(500, len(pivot_df) * 28),
                xaxis_side="top",
                xaxis_title="",
                yaxis_title="",
                xaxis=dict(type="category")  # <-- Forces discrete category labels
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No industry history snapshot data found in 'industry_momentum_history'. Run your pipeline to populate industry snapshots.")

# ==========================================
# 6. SIDEBAR CONTROLS
# ==========================================
with st.sidebar:
    st.header("⚙️ Dashboard Controls")
    if st.button("🔄 Refresh Cache"):
        st.cache_data.clear()
        st.success("Cache cleared! Reloading data...")
        st.rerun()

    # 2. Latest Data Snapshot Date (for your database metrics)
    if not sector_history_df.empty and "snapshot_date" in sector_history_df.columns:
        latest_snapshot = sector_history_df["snapshot_date"].max()
        st.success(f"📊 **Supabase Snapshot Date:**\n{latest_snapshot}")
    else:
        st.warning("📊 **Supabase Snapshot Date:** None found")



# ==========================================
# GITHUB WORKFLOW TRIGGER UTILITY
# ==========================================
@st.cache_data(ttl=60) # Cache for 1 minute to avoid rate limits
def get_last_github_workflow_run(workflow_filename):
    try:
        gh_secrets = st.secrets["github"]
        headers = {
            "Authorization": f"Bearer {gh_secrets['token']}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        url = f"https://api.github.com/repos/{gh_secrets['owner']}/{gh_secrets['repo']}/actions/workflows/{workflow_filename}/runs?per_page=1"
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            runs = response.json().get("workflow_runs", [])
            if runs:
                run = runs[0]
                created_at = run.get("updated_at") or run.get("created_at")
                dt = pd.to_datetime(created_at).tz_convert('Asia/Kolkata')
                timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S IST")
                
                status = run.get("status")
                conclusion = run.get("conclusion")
                run_url = run.get("html_url", "#") # <-- Extract the direct URL to the run
                
                if status == "completed":
                    if conclusion == "success":
                        status_badge = "🟢 Success"
                    elif conclusion == "failure":
                        status_badge = "🔴 Failed"
                    else:
                        status_badge = f"⚪ {conclusion.title() if conclusion else 'Completed'}"
                elif status == "in_progress":
                    status_badge = "🟡 In Progress..."
                else:
                    status_badge = f"🔵 {status.title()}"
                    
                return timestamp_str, status_badge, run_url
                
        return "Unknown", "⚪ Unknown", "#"
    except Exception as e:
        return "Error fetching", "❌ Error", "#"
    
def trigger_github_workflow(workflow_filename):
    try:
        gh_secrets = st.secrets["github"]
        headers = {
            "Authorization": f"Bearer {gh_secrets['token']}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        url = f"https://api.github.com/repos/{gh_secrets['owner']}/{gh_secrets['repo']}/actions/workflows/{workflow_filename}/dispatches"
        
        payload = {"ref": "main"}
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 204:
            return True, f"Successfully triggered '{workflow_filename}'! 🚀"
        else:
            return False, f"Failed to trigger: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"Error connecting to GitHub API: {e}"

# ==========================================
# SIDEBAR CONTROLS WITH CLICKABLE LINKS
# ==========================================
with st.sidebar:
    st.markdown("---")
    st.header("⚙️ Pipeline Controls")
    
    # 1. Main Pipeline Status & Run Link
    main_time, main_status, main_url = get_last_github_workflow_run(st.secrets["github"]["workflow_main"])
    st.markdown("📦 **Main Pipeline (`main_pipeline.yml`)**")
    st.caption(f"Status: {main_status}\n\nTime: {main_time}")
    if main_url != "#":
        st.markdown(f"<a href='{main_url}' target='_blank'>🔗 View Main Run on GitHub</a>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 2. Intraday Monitor Status & Run Link
    monitor_time, monitor_status, monitor_url = get_last_github_workflow_run(st.secrets["github"]["workflow_monitor"])
    st.markdown("⚡ **Daily Price Monitor Pipeline (`daily_monitor_pipline.yml`)**")
    st.caption(f"Status: {monitor_status}\n\nTime: {monitor_time}")
    if monitor_url != "#":
        st.markdown(f"<a href='{monitor_url}' target='_blank'>🔗 View Monitor Run on GitHub</a>", unsafe_allow_html=True)
    
    # 3. Workflow Selector & Trigger Button
    st.markdown("**Trigger Remote Workflow**")
    selected_workflow_label = st.selectbox(
        "Select Pipeline", 
        ["Main Pipeline (main_pipeline.yml)", "Daily Price Monitor (daily_monitor_pipline.yml)"]
    )
    
    target_workflow = (
        st.secrets["github"]["workflow_main"] 
        if "main_pipeline.yml" in selected_workflow_label 
        else st.secrets["github"]["workflow_monitor"]
    )
    
    if st.button("🚀 Run Selected Pipeline", type="primary"):
        with st.spinner(f"Dispatching {target_workflow} to GitHub..."):
            success, message = trigger_github_workflow(target_workflow)
            if success:
                st.success(message)
            else:
                st.error(message)