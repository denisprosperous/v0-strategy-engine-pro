-- Script to initialize market data and sentiment services
-- This would typically be run as a background service

-- Create indexes for better performance on market data queries
CREATE INDEX IF NOT EXISTS idx_market_data_symbol_time ON market_data(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_data_symbol_time ON sentiment_data(symbol, timestamp DESC);

-- Create materialized view for latest prices
CREATE MATERIALIZED VIEW IF NOT EXISTS latest_prices AS
SELECT DISTINCT ON (symbol) 
  symbol,
  close as price,
  volume,
  timestamp
FROM market_data 
ORDER BY symbol, timestamp DESC;

-- Create materialized view for latest sentiment
CREATE MATERIALIZED VIEW IF NOT EXISTS latest_sentiment AS
SELECT DISTINCT ON (symbol)
  symbol,
  sentiment_score,
  confidence,
  source,
  timestamp
FROM sentiment_data
ORDER BY symbol, timestamp DESC;

-- Refresh materialized views (would be done periodically)
REFRESH MATERIALIZED VIEW latest_prices;
REFRESH MATERIALIZED VIEW latest_sentiment;
