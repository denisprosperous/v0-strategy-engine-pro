-- Added database schema for AI learning and risk management
-- AI Learning and Risk Management Tables

-- Model performance tracking
CREATE TABLE IF NOT EXISTS model_performance (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    model_version VARCHAR(50) NOT NULL,
    performance_metrics JSONB NOT NULL,
    training_data_size INTEGER,
    validation_accuracy DECIMAL(5,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Backtest results storage
CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    strategy_id VARCHAR(100) NOT NULL,
    config JSONB NOT NULL,
    result JSONB NOT NULL,
    total_return DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    sharpe_ratio DECIMAL(10,4),
    win_rate DECIMAL(5,4),
    total_trades INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Strategy performance tracking
CREATE TABLE IF NOT EXISTS strategy_performance (
    id SERIAL PRIMARY KEY,
    strategy_id VARCHAR(100) NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    total_pnl DECIMAL(15,2) DEFAULT 0,
    max_drawdown DECIMAL(10,4) DEFAULT 0,
    sharpe_ratio DECIMAL(10,4) DEFAULT 0,
    win_rate DECIMAL(5,4) DEFAULT 0,
    avg_trade_duration INTERVAL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Risk metrics tracking
CREATE TABLE IF NOT EXISTS risk_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    portfolio_value DECIMAL(15,2),
    daily_pnl DECIMAL(15,2),
    max_drawdown DECIMAL(10,4),
    volatility DECIMAL(10,4),
    var_95 DECIMAL(15,2), -- Value at Risk 95%
    correlation_risk DECIMAL(5,4),
    position_concentration DECIMAL(5,4),
    leverage_ratio DECIMAL(10,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ML training data features
CREATE TABLE IF NOT EXISTS ml_features (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES trade_signals(id),
    trade_id INTEGER REFERENCES trades(id),
    features JSONB NOT NULL, -- All input features
    target_return DECIMAL(10,4), -- Actual return achieved
    target_success BOOLEAN, -- Whether trade was successful
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Kelly Criterion calculations
CREATE TABLE IF NOT EXISTS kelly_calculations (
    id SERIAL PRIMARY KEY,
    strategy_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    win_rate DECIMAL(5,4) NOT NULL,
    avg_win DECIMAL(10,4) NOT NULL,
    avg_loss DECIMAL(10,4) NOT NULL,
    kelly_fraction DECIMAL(10,4) NOT NULL,
    recommended_position_size DECIMAL(10,4) NOT NULL,
    confidence_level DECIMAL(5,4) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Adaptive learning weights
CREATE TABLE IF NOT EXISTS adaptive_weights (
    id SERIAL PRIMARY KEY,
    strategy_id VARCHAR(100) NOT NULL,
    factor_name VARCHAR(100) NOT NULL,
    weight_value DECIMAL(10,6) NOT NULL,
    performance_correlation DECIMAL(10,6),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(strategy_id, factor_name)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_model_performance_timestamp ON model_performance(timestamp);
CREATE INDEX IF NOT EXISTS idx_backtest_results_strategy ON backtest_results(strategy_id);
CREATE INDEX IF NOT EXISTS idx_strategy_performance_strategy ON strategy_performance(strategy_id);
CREATE INDEX IF NOT EXISTS idx_risk_metrics_timestamp ON risk_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_ml_features_signal ON ml_features(signal_id);
CREATE INDEX IF NOT EXISTS idx_kelly_calculations_strategy ON kelly_calculations(strategy_id);
CREATE INDEX IF NOT EXISTS idx_adaptive_weights_strategy ON adaptive_weights(strategy_id);

-- Insert initial adaptive weights for strategies
INSERT INTO adaptive_weights (strategy_id, factor_name, weight_value) VALUES
('breakout-scalping', 'smart_money_quality', 0.40),
('breakout-scalping', 'trade_characteristics', 0.30),
('breakout-scalping', 'token_state', 0.30),
('mean-reversion', 'smart_money_quality', 0.35),
('mean-reversion', 'trade_characteristics', 0.35),
('mean-reversion', 'token_state', 0.30),
('momentum-sentiment', 'smart_money_quality', 0.30),
('momentum-sentiment', 'trade_characteristics', 0.25),
('momentum-sentiment', 'token_state', 0.45)
ON CONFLICT (strategy_id, factor_name) DO NOTHING;

-- Create function to update strategy performance
CREATE OR REPLACE FUNCTION update_strategy_performance()
RETURNS TRIGGER AS $$
BEGIN
    -- Update strategy performance when a trade is closed
    IF NEW.status = 'closed' AND OLD.status != 'closed' THEN
        INSERT INTO strategy_performance (
            strategy_id,
            period_start,
            period_end,
            total_trades,
            winning_trades,
            total_pnl
        )
        SELECT 
            NEW.strategy_id,
            DATE_TRUNC('day', NEW.created_at),
            DATE_TRUNC('day', NEW.created_at) + INTERVAL '1 day',
            1,
            CASE WHEN NEW.pnl > 0 THEN 1 ELSE 0 END,
            NEW.pnl
        ON CONFLICT (strategy_id, period_start) DO UPDATE SET
            total_trades = strategy_performance.total_trades + 1,
            winning_trades = strategy_performance.winning_trades + CASE WHEN NEW.pnl > 0 THEN 1 ELSE 0 END,
            total_pnl = strategy_performance.total_pnl + NEW.pnl,
            win_rate = (strategy_performance.winning_trades + CASE WHEN NEW.pnl > 0 THEN 1 ELSE 0 END)::DECIMAL / 
                      (strategy_performance.total_trades + 1);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic performance tracking
DROP TRIGGER IF EXISTS trigger_update_strategy_performance ON trades;
CREATE TRIGGER trigger_update_strategy_performance
    AFTER UPDATE ON trades
    FOR EACH ROW
    EXECUTE FUNCTION update_strategy_performance();
