import datetime
import logging
import os

# =====================================================================
# Global Logging Configuration
# =====================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger("PortfolioEngine")

# Debug & Testing Toggles
DEBUG_MODE = True  # Set to False when running the full production Nifty 750 pipeline
DEBUG_TICKERS = [
    "KMEW.NS",
    "LOTUSDEV.NS",
    "SKYGOLD.NS",
    "SSWL.NS",
    "TFCILTD.NS",
]

CURRENT_RUN_DATE = datetime.date.today().strftime("%Y-%m-%d")

OUTPUT_EXCEL_FILE = os.path.join(
    "data", f"Portfolio_Analysis_Master_{CURRENT_RUN_DATE}.xlsx"
)
BENCHMARK_TICKER = "^CRSLDX"  # Nifty 500 Index
RISK_FREE_RATE_ANNUAL = 0.065  # 6.5% Annual Risk-Free Rate India Baseline
CHUNK_SIZE = 50  # Optimal chunk size to avoid yfinance timeouts
TOTAL_CAPITAL = 150000.0
ALLOCATION_PCT = 0.065

# Mapping of standard sectors to their respective NSE Sectoral Index Symbols
SECTOR_INDEX_MAP = {
    # Financials (Banks, NBFCs, Insurance)
    "FINANCIAL_SERVICES": "^CNXFIN",
    "FINANCIAL": "^CNXFIN",

    # Technology (IT Services, Software)
    "TECHNOLOGY": "^CNXIT",

    # Energy (Oil & Gas, Coal, Petroleum)
    "ENERGY": "^CNXENERGY",

    # Utilities (Power Generation, Transmission, Gas Distribution)
    "UTILITIES": "^CNXENERGY",  # Best fit as Nifty Energy contains major power utilities (NTPC, PowerGrid)

    # Consumer Cyclical (Auto, Auto Ancillaries, Retail)
    "CONSUMER_CYCLICAL": "^CNXAUTO",
    "AUTO": "^CNXAUTO",

    # Consumer Defensive (FMCG, Food, Personal Care)
    "CONSUMER_DEFENSIVE": "^CNXFMCG",
    "FMCG": "^CNXFMCG",

    # Healthcare (Pharma, Hospitals, Diagnostics)
    "HEALTHCARE": "^CNXPHARMA",

    # Industrials (Capital Goods, Engineering, Construction, Logistics)
    "INDUSTRIALS": "^CNXINFRA",  # Nifty Infrastructure is the closest liquid proxy for industrial growth

    # Basic Materials (Metals, Mining, Chemicals, Cement)
    "BASIC_MATERIALS": "^CNXMETAL",  # Nifty Metal is the closest liquid proxy

    # Real Estate (Realty, Developers)
    "REAL_ESTATE": "^CNXREALTY",

    # Communication Services (Telecom, Media, Entertainment)
    "COMMUNICATION_SERVICES": "^CNXIT",  # Often grouped with Tech, or falls back to Nifty 500 if preferred
   
    # Fallback for Conglomerates, Miscellaneous, or Unclassified stocks
    "MISCELLANEOUS": "^CRSLDX",
    "CONGLOMERATES": "^CRSLDX"
}