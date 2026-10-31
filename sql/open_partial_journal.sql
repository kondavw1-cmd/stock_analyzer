DROP TABLE IF EXISTS public.open_partial_journal;

CREATE TABLE public.open_partial_journal (
    "Instrument" TEXT,
    "Status" TEXT,
    "Entry Date" TEXT,
    "Holding Duration" TEXT,
    "Qty." INTEGER,
    "Avg. cost" NUMERIC,
    "LTP" NUMERIC,
    "Invested" NUMERIC,
    "Cur. val" NUMERIC,
    "P&L" NUMERIC,
    "Net chg." NUMERIC,
    "Day chg." NUMERIC,
    "Allowed Investment" NUMERIC,
    "Allowed Shares" INTEGER,
    "Invested Allocation %" NUMERIC,
    "Current Value Allocation %" NUMERIC,
    "Defined SL [RISK]" NUMERIC,
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