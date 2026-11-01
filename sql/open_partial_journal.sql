DROP TABLE IF EXISTS public.open_partial_journal;

CREATE TABLE public.open_partial_journal (
    "Instrument" TEXT NOT NULL,
    "Status" TEXT NOT NULL,
    "Entry Date" TEXT NOT NULL,
    "Holding Duration" TEXT NOT NULL,
    "Qty." INTEGER NOT NULL,
    "Avg. cost" NUMERIC NOT NULL,
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
    "Last Updated At" VARCHAR(10) NOT NULL,                   -- Format: "YYYY-MM-DD"
    -- Define a composite primary key using multiple columns
    CONSTRAINT pk_open_partial_journal PRIMARY KEY ("Instrument", "Status", "Entry Date", "Qty.", "Avg. cost")
);