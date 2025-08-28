// Database configuration and connection setup
import { createClient } from "@supabase/supabase-js"

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseKey)

// Database table creation SQL
export const createTablesSQL = `
-- Users table
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) DEFAULT 'trader' CHECK (role IN ('admin', 'trader', 'viewer')),
  telegram_id VARCHAR(50),
  api_keys JSONB DEFAULT '{}',
  settings JSONB DEFAULT '{
    "risk_tolerance": 0.5,
    "max_daily_loss": 1000,
    "default_position_size": 100,
    "auto_trading_enabled": false
  }',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Strategies table
CREATE TABLE IF NOT EXISTS strategies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100) NOT NULL,
  description TEXT,
  type VARCHAR(50) NOT NULL CHECK (type IN ('breakout', 'mean_reversion', 'momentum', 'sentiment', 'hybrid')),
  parameters JSONB DEFAULT '{}',
  performance_metrics JSONB DEFAULT '{
    "total_trades": 0,
    "win_rate": 0,
    "avg_pnl": 0,
    "max_drawdown": 0,
    "sharpe_ratio": 0
  }',
  is_active BOOLEAN DEFAULT true,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trades table
CREATE TABLE IF NOT EXISTS trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) NOT NULL,
  strategy_id UUID REFERENCES strategies(id),
  symbol VARCHAR(20) NOT NULL,
  side VARCHAR(10) NOT NULL CHECK (side IN ('buy', 'sell')),
  entry_price DECIMAL(20, 8) NOT NULL,
  exit_price DECIMAL(20, 8),
  quantity DECIMAL(20, 8) NOT NULL,
  stop_loss DECIMAL(20, 8),
  take_profit DECIMAL(20, 8),
  status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'closed', 'cancelled')),
  pnl DECIMAL(20, 8),
  fees DECIMAL(20, 8) DEFAULT 0,
  execution_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  close_time TIMESTAMP WITH TIME ZONE,
  broker VARCHAR(20) NOT NULL,
  metadata JSONB DEFAULT '{}',
  INDEX idx_trades_user_id (user_id),
  INDEX idx_trades_symbol (symbol),
  INDEX idx_trades_status (status)
);

-- Market data table
CREATE TABLE IF NOT EXISTS market_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol VARCHAR(20) NOT NULL,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  open DECIMAL(20, 8) NOT NULL,
  high DECIMAL(20, 8) NOT NULL,
  low DECIMAL(20, 8) NOT NULL,
  close DECIMAL(20, 8) NOT NULL,
  volume DECIMAL(20, 8) NOT NULL,
  source VARCHAR(20) NOT NULL,
  INDEX idx_market_data_symbol_timestamp (symbol, timestamp),
  UNIQUE KEY unique_market_data (symbol, timestamp, source)
);

-- Sentiment data table
CREATE TABLE IF NOT EXISTS sentiment_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol VARCHAR(20) NOT NULL,
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  source VARCHAR(20) NOT NULL CHECK (source IN ('twitter', 'reddit', 'news')),
  sentiment_score DECIMAL(3, 2) NOT NULL CHECK (sentiment_score BETWEEN -1 AND 1),
  confidence DECIMAL(3, 2) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  text_sample TEXT,
  metadata JSONB DEFAULT '{}',
  INDEX idx_sentiment_symbol_timestamp (symbol, timestamp)
);

-- Trade signals table
CREATE TABLE IF NOT EXISTS trade_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id UUID REFERENCES strategies(id) NOT NULL,
  symbol VARCHAR(20) NOT NULL,
  signal_type VARCHAR(10) NOT NULL CHECK (signal_type IN ('buy', 'sell', 'hold')),
  strength DECIMAL(3, 2) NOT NULL CHECK (strength BETWEEN 0 AND 1),
  price_target DECIMAL(20, 8),
  stop_loss DECIMAL(20, 8),
  take_profit DECIMAL(20, 8),
  reasoning TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  executed BOOLEAN DEFAULT false,
  INDEX idx_signals_strategy_symbol (strategy_id, symbol)
);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_strategies_updated_at BEFORE UPDATE ON strategies FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
`
