// Database schema definitions for the trading system
export interface User {
  id: string
  username: string
  email: string
  password_hash: string
  role: "admin" | "trader" | "viewer"
  telegram_id?: string
  api_keys: {
    binance?: { key: string; secret: string }
    bybit?: { key: string; secret: string }
  }
  settings: {
    risk_tolerance: number
    max_daily_loss: number
    default_position_size: number
    auto_trading_enabled: boolean
  }
  created_at: Date
  updated_at: Date
}

export interface Trade {
  id: string
  user_id: string
  strategy_id: string
  symbol: string
  side: "buy" | "sell"
  entry_price: number
  exit_price?: number
  quantity: number
  stop_loss?: number
  take_profit?: number
  status: "open" | "closed" | "cancelled"
  pnl?: number
  fees: number
  execution_time: Date
  close_time?: Date
  broker: "binance" | "bybit"
  metadata: {
    sentiment_score?: number
    technical_signals?: Record<string, any>
    risk_score?: number
  }
}

export interface Strategy {
  id: string
  name: string
  description: string
  type: "breakout" | "mean_reversion" | "momentum" | "sentiment" | "hybrid"
  parameters: Record<string, any>
  performance_metrics: {
    total_trades: number
    win_rate: number
    avg_pnl: number
    max_drawdown: number
    sharpe_ratio: number
  }
  is_active: boolean
  created_by: string
  created_at: Date
  updated_at: Date
}

export interface MarketData {
  id: string
  symbol: string
  timestamp: Date
  open: number
  high: number
  low: number
  close: number
  volume: number
  source: "binance" | "bybit" | "coinbase"
}

export interface SentimentData {
  id: string
  symbol: string
  timestamp: Date
  source: "twitter" | "reddit" | "news"
  sentiment_score: number // -1 to 1
  confidence: number // 0 to 1
  text_sample: string
  metadata: Record<string, any>
}

export interface TradeSignal {
  id: string
  strategy_id: string
  symbol: string
  signal_type: "buy" | "sell" | "hold"
  strength: number // 0 to 1
  price_target?: number
  stop_loss?: number
  take_profit?: number
  reasoning: string
  created_at: Date
  executed: boolean
}
