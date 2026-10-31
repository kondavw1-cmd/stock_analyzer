DROP TABLE IF EXISTS public.universe_of_750_stocks_scores;

CREATE TABLE public.universe_of_750_stocks_scores (
    "Instrument" TEXT,
    "LTP" NUMERIC,
    "Sector" TEXT,
    "Broad Based Index" TEXT,
    "Market CAP" TEXT,
    "Upcoming Event Date" TEXT,
    "Upcoming Event Name" TEXT,
    "Volatility_%" NUMERIC,
    "Sharpe_Ratio" NUMERIC,
    "ATH (P-66%)" NUMERIC,
    "ATP (P-75%)" NUMERIC,
    "Nifty 500 [OTP] (P-82%)" NUMERIC,
    "Sector Index (P-82%)" NUMERIC,
    "REVISION SCORE" NUMERIC,
    "ACTION" TEXT,
    "Allowed Investment" NUMERIC,
    "Allowed Shares" INTEGER,
    "REMARKS" TEXT,
    "Created At" VARCHAR(10) NOT NULL,                    -- Format: "YYYY-MM-DD"
    "Last Updated At" VARCHAR(10) NOT NULL                   -- Format: "YYYY-MM-DD"
);