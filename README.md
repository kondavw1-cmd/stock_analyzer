portfolio_analyzer/
│
├── .github/
│   └── workflows/
│       ├── daily_pipeline.yml       # EOD cron trigger (runs full analysis & Supabase save)
│       └── intraday_alert.yml       # Intraday 30-min price monitor (checks live prices)
│
├── data/
│   └── cache/                       # Local temporary cache directory (ignored by git)
│
├── src/
│   ├── __init__.py
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── database.py              # Supabase PostgreSQL engine & helper functions
│   │   ├── notifications.py         # Discord Webhook & Gmail SMTP alert dispatcher
│   │   └── excel_generator.py       # Multi-tab formatted Excel generator utility
│   │
│   ├── data_engine/
│   │   ├── __init__.py
│   │   ├── yahoo_fetcher.py         # Multi-threaded yfinance price history fetcher
│   │   └── tradebook_parser.py      # Zerodha tradebook & FIFO batching parser
│   │
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── technical_indicators.py  # ATH, ATP, OTP, and momentum calculations
│   │   └── scoring_engine.py        # Quantitative scoring & risk allocation logic
│   │
│   └── trading/
│       ├── __init__.py
│       └── price_monitor.py         # Real-time live price checker against target prices
│
├── app.py                           # Streamlit Cloud dashboard UI (reads/writes to Supabase)
├── main.py                          # Main entry point for EOD daily pipeline execution
├── monitor_live.py                  # Main entry point for intraday price watcher workflow
├── .env.example                     # Environment template for local development
├── .gitignore                       # Git ignore file (cache, secrets, .env)
├── README.md                        # Project documentation & setup instructions
└── requirements.txt                 # Python dependencies list