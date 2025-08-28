-- Seed initial trading strategies
INSERT INTO strategies (name, description, type, parameters) VALUES
(
  'Breakout Scalper',
  'High-frequency breakout strategy targeting 1-5 minute timeframes',
  'breakout',
  '{
    "timeframe": "1m",
    "volume_threshold": 1.5,
    "price_change_threshold": 0.02,
    "stop_loss_pct": 0.01,
    "take_profit_pct": 0.03,
    "max_positions": 3
  }'
),
(
  'Mean Reversion RSI',
  'Mean reversion strategy using RSI oversold/overbought conditions',
  'mean_reversion',
  '{
    "timeframe": "5m",
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "stop_loss_pct": 0.015,
    "take_profit_pct": 0.025,
    "max_positions": 2
  }'
),
(
  'Momentum + Sentiment',
  'Combines price momentum with social sentiment analysis',
  'hybrid',
  '{
    "timeframe": "15m",
    "momentum_period": 20,
    "sentiment_weight": 0.3,
    "min_sentiment_confidence": 0.7,
    "stop_loss_pct": 0.02,
    "take_profit_pct": 0.04,
    "max_positions": 2
  }'
),
(
  'News Event Scalper',
  'Rapid response to news events and market volatility spikes',
  'sentiment',
  '{
    "timeframe": "1m",
    "volatility_threshold": 2.0,
    "news_sentiment_threshold": 0.6,
    "quick_exit_time": 300,
    "stop_loss_pct": 0.008,
    "take_profit_pct": 0.02,
    "max_positions": 5
  }'
);
