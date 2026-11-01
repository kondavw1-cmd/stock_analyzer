DROP TABLE IF EXISTS public.universe_of_750_stocks_scores;

CREATE TABLE public.universe_of_750_stocks_scores (
    "Instrument" TEXT PRIMARY KEY NOT NULL,
    "LTP" NUMERIC,
    "Sector" TEXT,
    "Broad Based Index" TEXT,
    "Market CAP" TEXT,
    "Upcoming Event Date" TEXT,
    "Upcoming Event Name" TEXT,
    "Volatility_%" NUMERIC,
    "Sharpe_Ratio" NUMERIC,
    "ATH (P-66%)" NUMERIC NOT NULL,
    "ATP (P-75%)" NUMERIC NOT NULL,
    "Nifty 500 [OTP] (P-82%)" NUMERIC NOT NULL,
    "Sector Index (P-82%)" NUMERIC NOT NULL,
    "Allowed Investment" NUMERIC NOT NULL,
    "Allowed Shares" INTEGER NOT NULL,
    "REMARKS" TEXT,
    "REVISION SCORE" NUMERIC NOT NULL,
    "ACTION" TEXT NOT NULL,
    "Monday" TEXT,
    "Tuesday" TEXT,
    "Wensday" TEXT,
    "Thursday" TEXT,
    "Friday" TEXT,
    "Week 2" TEXT,
    "Week 3" TEXT,
    "Week 4" TEXT,
    "Created At" VARCHAR(10) NOT NULL,                    -- Format: "YYYY-MM-DD"
    "Last Updated At" VARCHAR(10) NOT NULL                   -- Format: "YYYY-MM-DD"
);