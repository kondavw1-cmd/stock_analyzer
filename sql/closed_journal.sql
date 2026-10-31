DROP TABLE IF EXISTS public.closed_journal;

CREATE TABLE public.closed_journal (
    "Instrument" TEXT,
    "Status" TEXT,
    "Entry Date" TEXT,
    "Exit Date" TEXT,
    "Holding Duration" TEXT,
    "Qty" INTEGER,
    "Avg. Buy Cost" NUMERIC,
    "Avg. Sell Cost" NUMERIC,
    "Buy Value" NUMERIC,
    "Sell Value" NUMERIC,
    "Gross PnL" NUMERIC,
    "Total Charges" NUMERIC,
    "Net Pnl" NUMERIC,
    "Net Pnl Pct" NUMERIC,
    "Market CAP" TEXT,
    "ATH (P-66%)" NUMERIC,
    "ATP (P-75%)" NUMERIC,
    "Nifty 500 [OTP] (P-82%)" NUMERIC,
    "Sector Index (P-82%)" NUMERIC,
    "REVISION SCORE" NUMERIC,
    "ACTION" TEXT,
    "Created At" VARCHAR(10) NOT NULL,                    -- Format: "YYYY-MM-DD"
    "Last Updated At" VARCHAR(10) NOT NULL                   -- Format: "YYYY-MM-DD"
);