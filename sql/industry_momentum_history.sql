DROP TABLE IF EXISTS public.industry_momentum_history;

CREATE TABLE IF NOT EXISTS industry_momentum_history (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    sector TEXT NOT NULL,
    industry TEXT NOT NULL,
    total_stocks INT NOT NULL DEFAULT 0,
    action_buys INT NOT NULL DEFAULT 0,
    avg_sharpe NUMERIC(10, 3) DEFAULT 0.0,
    avg_review_score NUMERIC(10, 2) DEFAULT 0.0,
    avg_distance_from_ath NUMERIC(10, 2) DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensures a unique record per sector, industry, and snapshot date for clean upserts
    CONSTRAINT unique_industry_snapshot UNIQUE (snapshot_date, sector, industry)
);

-- Create an index on snapshot_date for fast chronological querying in Streamlit
CREATE INDEX IF NOT EXISTS idx_industry_momentum_date 
ON industry_momentum_history(snapshot_date DESC);