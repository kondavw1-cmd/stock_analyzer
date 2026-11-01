DROP TABLE IF EXISTS public.closed_journal;

CREATE TABLE public.closed_journal (
    "Instrument" TEXT NOT NULL,
    "Status" TEXT NOT NULL,
    "Entry Date" TEXT NOT NULL,
    "Exit Date" TEXT NOT NULL,
    "Holding Duration" TEXT NOT NULL,
    "Qty" INTEGER NOT NULL,
    "Avg. Buy Cost" NUMERIC NOT NULL,
    "Avg. Sell Cost" NUMERIC NOT NULL,
    "Buy Value" NUMERIC NOT NULL,
    "Sell Value" NUMERIC NOT NULL,
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
    "Last Updated At" VARCHAR(10) NOT NULL,                   -- Format: "YYYY-MM-DD"
    -- Define a composite primary key using multiple columns
    CONSTRAINT pk_closed_journal PRIMARY KEY ("Instrument", "Status", "Entry Date", "Exit Date", "Qty", "Avg. Buy Cost")
);