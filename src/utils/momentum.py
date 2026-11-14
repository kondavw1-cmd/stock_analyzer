import pandas as pd
from datetime import datetime

def compute_momentum_snapshots_df(df_scored_results: pd.DataFrame):
    """
    Aggregates df_scored_results into sector and industry DataFrames 
    ready for database ingestion via save_dataframe_to_sql.
    """
    if df_scored_results is None or df_scored_results.empty:
        return pd.DataFrame(), pd.DataFrame()

    today_str = datetime.now().strftime("%Y-%m-%d")

    # ==========================================
    # 1. SECTOR MOMENTUM AGGREGATION
    # ==========================================
    sector_rows = []
    if "Sector" in df_scored_results.columns:
        for sector, group in df_scored_results.groupby("Sector"):
            sector_rows.append({
                "snapshot_date": today_str,
                "sector": sector,
                "total_stocks": int(len(group)),
                "action_buys": int((group["ACTION"] == "+ADD").sum()) if "ACTION" in group.columns else 0,
                "avg_sharpe": round(float(group["Sharpe_Ratio"].mean()), 3) if "Sharpe_Ratio" in group.columns else 0.0,
                "avg_review_score": round(float(group["Review_Score"].mean()), 2) if "Review_Score" in group.columns else 0.0,
                "relative_strength": round(float(group["Sector_Year_Return"].mean()), 2) if "Sector_Year_Return" in group.columns else 0.0,
                "sector_alpha": round(float(group["Sector_Alpha"].mean()), 2) if "Sector_Alpha" in group.columns else 0.0,
                "avg_distance_from_ath": round(float(group["Distance_From_ATH_%"].mean()), 2) if "Distance_From_ATH_%" in group.columns else 0.0
            })

    sector_df = pd.DataFrame(sector_rows)

    # ==========================================
    # 2. INDUSTRY MOMENTUM AGGREGATION
    # ==========================================
    industry_rows = []
    if "Sector" in df_scored_results.columns and "Industry" in df_scored_results.columns:
        for (sector, industry), group in df_scored_results.groupby(["Sector", "Industry"]):
            industry_rows.append({
                "snapshot_date": today_str,
                "sector": sector,
                "industry": industry,
                "total_stocks": int(len(group)),
                "action_buys": int((group["ACTION"] == "+ADD").sum()) if "ACTION" in group.columns else 0,
                "avg_sharpe": round(float(group["Sharpe_Ratio"].mean()), 3) if "Sharpe_Ratio" in group.columns else 0.0,
                "avg_review_score": round(float(group["Review_Score"].mean()), 2) if "Review_Score" in group.columns else 0.0,
                "avg_distance_from_ath": round(float(group["Distance_From_ATH_%"].mean()), 2) if "Distance_From_ATH_%" in group.columns else 0.0
            })

    industry_df = pd.DataFrame(industry_rows)

    return sector_df, industry_df