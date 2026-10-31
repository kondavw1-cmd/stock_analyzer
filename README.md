# 📈 Stock Analyzer & Portfolio Engine

An automated Python-based financial data engine and portfolio analysis framework designed to process large stock universes (750+ tickers), execute trade journal parsing via FIFO matching, sync state securely to **Supabase**, dispatch multi-tab Excel reports via the **Gmail API**, and push color-coded real-time trade alerts to **Discord**.

---

## 🚀 Key Features

* **Automated Data Processing & Scoring**: Fetches and evaluates technical indicators (`Volatility_%`, `Sharpe_Ratio`, `ATH`, `ATP`, moving averages) across a 750-stock universe.
* **FIFO Trade Journal & PnL Sync**: Parses broker tradebook exports and reconciles open, partial, and closed positions with precise cost basis tracking.
* **Supabase Cloud Sync & Timestamps**: 
  * Strict case-sensitive column schema mapping to prevent schema cache errors (`PGRST204`).
  * Immutable `Created At` timestamps locked on first record insertion via PostgreSQL triggers.
  * Automated database-level triggers to refresh `Last Updated At` on every subsequent pipeline run.
* **Rolling 4-Week Action History**: Tracks historical strategy decisions (`ACTION`) across the current week's daily runs (`Day 1` to `Day 5`) and past Friday roll-overs (`Week 2` to `Week 4`).
* **Multi-Recipient Gmail Dispatch**: Generates formatted, multi-tab Excel workbooks and sends them securely as email attachments to multiple stakeholders via the Gmail API.
* **Color-Coded Discord Embed Alerts**: Pushes clean, non-wrapping tabular notifications (`tabulate(tablefmt="plain")`) filtered by strategy rules, complete with priority-based sidebar color coding.

---

## 🛠️ Tech Stack & Architecture

* **Language**: Python 3.10+
* **Package Manager**: `uv`
* **Data Processing**: `pandas`, `yfinance`, `tabulate`
* **Database & Backend**: Supabase (PostgreSQL with custom triggers and composite keys)
* **Integrations**: Gmail API (OAuth2), Discord Webhooks

---

## 📁 Project Structure

```text
stock_analyzer/
│
├── .venv/                      # Virtual environment
├── config/                     # Core settings and pipeline parameters
│   ├── __init__.py
│   └── settings.py
├── data/                       # Local tradebook exports and raw market CSVs
│   └── tradebook-DIZ015-EQ.csv
├── sql/                        # SQL schemas and trigger functions
├── src/
│   ├── analytics/              # Scoring engine and technical indicators
│   │   ├── __init__.py
│   │   ├── scoring_engine.py
│   │   └── technical_indicators.py
│   ├── data_engine/            # Market data fetchers and tradebook parsers
│   │   ├── __init__.py
│   │   ├── market_data.py
│   │   ├── tradebook_parser.py
│   │   └── yahoo_fetcher.py
│   ├── trading/                # Execution and portfolio modules
│   └── utils/                  # Helper utilities and backend dispatchers
│       ├── __init__.py
│       ├── cli.py
│       ├── database.py         # Supabase upsert logic & history tracking
│       ├── email_helper.py     # Multi-recipient Gmail API dispatcher
│       ├── excel_generator.py  # Multi-tab Excel report builders
│       ├── helpers.py
│       └── notifications.py    # Color-coded tabular Discord embeds
│
├── .env                        # Local environment variables
├── .gitignore
├── .python-version
├── credentials.json            # Google OAuth API credentials
├── gmail_token_generator.py    # Helper script for generating Gmail tokens
├── main.py                     # Main execution pipeline entry point
├── monitor_live.py             # Live market monitoring runner
├── pyproject.toml              # Dependencies and project metadata
├── README.md                   # System documentation
├── requirements.txt            # Deprecated/pip fallback requirements
├── token.json                  # Google OAuth token cache
├── uv_commands_reference_guide.md # CLI reference guide for UV
└── uv.lock                     # UV dependency lockfile
```

---

## 📊 Database Schemas (Supabase)

The pipeline syncs data across three primary PostgreSQL tables with strict case-sensitive column enforcement:

1. **`universe_of_750_stocks_scores`**: Stores technical scores, event calendars, allocation limits, and rolling 4-week action history (`Day 1`–`Day 5`, `Week 2`–`Week 4`).
2. **`open_partial_journal`**: Tracks active and partially exited positions with valuations, risk metrics, and current asset allocations.
3. **`closed_journal`**: Logs closed trades with FIFO buy/sell pricing, gross/net PnL, holding durations, and total charges.

---

## ⚙️ Configuration & Environment Variables

Create a `.env` file in the root directory with the following configuration:

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_role_or_anon_key
DISCORD_WEBHOOK_URL=your_discord_webhook_url
GMAIL_SENDER_EMAIL=your_email@gmail.com
```

---

## 🔔 Discord Alert Rules & Formatting

Discord embeds use `tabulate(tablefmt="plain")` and truncated headers to eliminate text wrapping:

* **Open / Partial Journal**: Filtered for `ACTION != '+ADD'`, highlighted with an **Orange/Yellow** sidebar stripe (`16753920`).
* **Closed Journal**: Filtered for `ACTION == '+ADD'`, highlighted with a **Green** sidebar stripe (`3066993`).
* **Universe Stock Alerts**: Filtered for `ACTION == '+ADD'`, highlighted with a **Bright Green** sidebar stripe (`2067276`).

---

## ▶️ Running the Pipeline

Ensure your environment manager (`uv`) is configured, then execute the main portfolio engine:

```bash
uv run main.py
```

### Execution Flow:
1. **Fetch & Analyze**: Evaluates technical indicators across the stock universe.
2. **Rolling History**: Merges and shifts rolling 4-week `ACTION` metrics.
3. **Supabase Sync**: Upserts DataFrames into database tables while preserving immutable `Created At` timestamps.
4. **Report Generation**: Exports clean multi-tab Excel reports.
5. **Multi-Recipient Emailing**: Dispatches the Excel attachment via Gmail API.
6. **Discord Alerts**: Sends color-coded, tabular status embeds directly to Discord.