// Environment Variables Display Configuration
// Shows which env vars are set and their values (safe display)

export interface EnvVarConfig {
  name: string
  value: string
  isSecret: boolean
  category: "system" | "trading" | "ai" | "exchange" | "telegram" | "database"
  description: string
}

export function getEnvironmentVariables(): EnvVarConfig[] {
  return [
    // System
    {
      name: "VERCEL_REGION",
      value: process.env.VERCEL_REGION || "iad1",
      isSecret: false,
      category: "system",
      description: "Vercel deployment region (iad1 = US East)",
    },
    {
      name: "PYTHON_API_URL",
      value: process.env.PYTHON_API_URL || "(not set - using Next.js API)",
      isSecret: false,
      category: "system",
      description: "Optional Python backend URL",
    },
    {
      name: "DEBUG",
      value: process.env.DEBUG || "false",
      isSecret: false,
      category: "system",
      description: "Enable debug mode",
    },
    {
      name: "LOG_LEVEL",
      value: process.env.LOG_LEVEL || "info",
      isSecret: false,
      category: "system",
      description: "Logging level (debug, info, warn, error)",
    },

    // Trading
    {
      name: "TRADING_MODE",
      value: process.env.TRADING_MODE || "demo",
      isSecret: false,
      category: "trading",
      description: "Trading mode (demo or live)",
    },
    {
      name: "ENABLE_DEMO_MODE",
      value: process.env.ENABLE_DEMO_MODE || "true",
      isSecret: false,
      category: "trading",
      description: "Enable demo trading mode",
    },
    {
      name: "DEMO_INITIAL_BALANCE",
      value: process.env.DEMO_INITIAL_BALANCE || "10000",
      isSecret: false,
      category: "trading",
      description: "Initial balance for demo account",
    },
    {
      name: "DEFAULT_STOP_LOSS",
      value: process.env.DEFAULT_STOP_LOSS || "0.02",
      isSecret: false,
      category: "trading",
      description: "Default stop loss percentage (2%)",
    },
    {
      name: "DEFAULT_TAKE_PROFIT",
      value: process.env.DEFAULT_TAKE_PROFIT || "0.06",
      isSecret: false,
      category: "trading",
      description: "Default take profit percentage (6%)",
    },
    {
      name: "MAX_DAILY_LOSS",
      value: process.env.MAX_DAILY_LOSS || "500",
      isSecret: false,
      category: "trading",
      description: "Maximum daily loss limit ($)",
    },
    {
      name: "MAX_POSITION_SIZE",
      value: process.env.MAX_POSITION_SIZE || "2000",
      isSecret: false,
      category: "trading",
      description: "Maximum position size ($)",
    },
    {
      name: "MAX_OPEN_TRADES",
      value: process.env.MAX_OPEN_TRADES || "5",
      isSecret: false,
      category: "trading",
      description: "Maximum concurrent open trades",
    },
    {
      name: "TRADE_COOLDOWN_MS",
      value: process.env.TRADE_COOLDOWN_MS || "60000",
      isSecret: false,
      category: "trading",
      description: "Cooldown between trades (ms)",
    },
    {
      name: "DEFAULT_TRADE_SIZE",
      value: process.env.DEFAULT_TRADE_SIZE || "100",
      isSecret: false,
      category: "trading",
      description: "Default trade size ($)",
    },

    // Backtesting
    {
      name: "ENABLE_BACKTESTING",
      value: process.env.ENABLE_BACKTESTING || "true",
      isSecret: false,
      category: "trading",
      description: "Enable backtesting feature",
    },
    {
      name: "BACKTEST_START_DATE",
      value: process.env.BACKTEST_START_DATE || "2024-01-01",
      isSecret: false,
      category: "trading",
      description: "Backtest start date",
    },
    {
      name: "BACKTEST_END_DATE",
      value: process.env.BACKTEST_END_DATE || "2024-12-31",
      isSecret: false,
      category: "trading",
      description: "Backtest end date",
    },

    // AI Models
    {
      name: "AI_PRIMARY_MODEL",
      value: process.env.AI_PRIMARY_MODEL || "openai",
      isSecret: false,
      category: "ai",
      description: "Primary AI model for analysis",
    },
    {
      name: "AI_FALLBACK_MODEL",
      value: process.env.AI_FALLBACK_MODEL || "groq",
      isSecret: false,
      category: "ai",
      description: "Fallback AI model",
    },
    {
      name: "AI_SENTIMENT_MODEL",
      value: process.env.AI_SENTIMENT_MODEL || "perplexity",
      isSecret: false,
      category: "ai",
      description: "AI model for sentiment analysis",
    },
    {
      name: "OPENAI_API_KEY",
      value: process.env.OPENAI_API_KEY ? "✓ Configured" : "✗ Not set",
      isSecret: true,
      category: "ai",
      description: "OpenAI API key",
    },
    {
      name: "XAI_API_KEY",
      value: process.env.XAI_API_KEY ? "✓ Configured" : "✗ Not set",
      isSecret: true,
      category: "ai",
      description: "Grok (xAI) API key",
    },
    {
      name: "GROQ_API_KEY",
      value: process.env.GROQ_API_KEY ? "✓ Configured" : "✗ Not set",
      isSecret: true,
      category: "ai",
      description: "Groq API key",
    },
    {
      name: "GOOGLE_API_KEY",
      value: process.env.GOOGLE_API_KEY ? "✓ Configured" : "✗ Not set",
      isSecret: true,
      category: "ai",
      description: "Google Gemini API key",
    },
    {
      name: "PERPLEXITY_API_KEY",
      value: process.env.PERPLEXITY_API_KEY ? "✓ Configured" : "✗ Not set",
      isSecret: true,
      category: "ai",
      description: "Perplexity API key",
    },
    {
      name: "COHERE_API_KEY",
      value: process.env.COHERE_API_KEY ? "✓ Configured" : "✗ Not set",
      isSecret: true,
      category: "ai",
      description: "Cohere API key",
    },
    {
      name: "HUGGINGFACE_TOKEN",
      value: process.env.HUGGINGFACE_TOKEN ? "✓ Configured" : "✗ Not set",
      isSecret: true,
      category: "ai",
      description: "HuggingFace API token",
    },

    // Exchanges - Testnet flags
    {
      name: "BITGET_TESTNET",
      value: process.env.BITGET_TESTNET || "true",
      isSecret: false,
      category: "exchange",
      description: "Use Bitget testnet",
    },
    {
      name: "KRAKEN_TESTNET",
      value: process.env.KRAKEN_TESTNET || "true",
      isSecret: false,
      category: "exchange",
      description: "Use Kraken testnet",
    },
    {
      name: "PHEMEX_TESTNET",
      value: process.env.PHEMEX_TESTNET || "true",
      isSecret: false,
      category: "exchange",
      description: "Use Phemex testnet",
    },
    {
      name: "BINANCE_TESTNET",
      value: process.env.BINANCE_TESTNET || "true",
      isSecret: false,
      category: "exchange",
      description: "Use Binance testnet",
    },
    {
      name: "COINBASE_TESTNET",
      value: process.env.COINBASE_TESTNET || "true",
      isSecret: false,
      category: "exchange",
      description: "Use Coinbase testnet",
    },
    {
      name: "OKX_TESTNET",
      value: process.env.OKX_TESTNET || "true",
      isSecret: false,
      category: "exchange",
      description: "Use OKX testnet",
    },
    {
      name: "BYBIT_TESTNET",
      value: process.env.BYBIT_TESTNET || "true",
      isSecret: false,
      category: "exchange",
      description: "Use Bybit testnet",
    },
    {
      name: "KUCOIN_TESTNET",
      value: process.env.KUCOIN_TESTNET || "true",
      isSecret: false,
      category: "exchange",
      description: "Use KuCoin testnet",
    },

    // Exchange API Keys
    {
      name: "BITGET_API_KEY",
      value: process.env.BITGET_API_KEY ? "✓ Configured" : "✗ Not set",
      isSecret: true,
      category: "exchange",
      description: "Bitget API key",
    },
    {
      name: "KRAKEN_API_KEY",
      value: process.env.KRAKEN_API_KEY ? "✓ Configured" : "✗ Not set",
      isSecret: true,
      category: "exchange",
      description: "Kraken API key",
    },
    {
      name: "PHEMEX_API_KEY",
      value: process.env.PHEMEX_API_KEY ? "✓ Configured" : "✗ Not set",
      isSecret: true,
      category: "exchange",
      description: "Phemex API key",
    },

    // Telegram
    {
      name: "TELEGRAM_BOT_TOKEN",
      value: process.env.TELEGRAM_BOT_TOKEN ? "✓ Configured" : "✗ Not set",
      isSecret: true,
      category: "telegram",
      description: "Telegram bot token from @BotFather",
    },
    {
      name: "TELEGRAM_WEBHOOK_URL",
      value: process.env.TELEGRAM_WEBHOOK_URL || "(auto-configured on deploy)",
      isSecret: false,
      category: "telegram",
      description: "Telegram webhook URL",
    },

    // Database
    {
      name: "UPSTASH_REDIS_REST_URL",
      value: process.env.KV_REST_API_URL ? "✓ Configured" : "✗ Not set",
      isSecret: true,
      category: "database",
      description: "Upstash Redis REST URL",
    },
    {
      name: "UPSTASH_REDIS_REST_TOKEN",
      value: process.env.KV_REST_API_TOKEN ? "✓ Configured" : "✗ Not set",
      isSecret: true,
      category: "database",
      description: "Upstash Redis REST token",
    },
    {
      name: "DATA_REFRESH_INTERVAL",
      value: process.env.DATA_REFRESH_INTERVAL || "60",
      isSecret: false,
      category: "database",
      description: "Data refresh interval (seconds)",
    },
    {
      name: "DB_POOL_SIZE",
      value: process.env.DB_POOL_SIZE || "10",
      isSecret: false,
      category: "database",
      description: "Database connection pool size",
    },
    {
      name: "DB_MAX_OVERFLOW",
      value: process.env.DB_MAX_OVERFLOW || "20",
      isSecret: false,
      category: "database",
      description: "Database max overflow connections",
    },
  ]
}

export function getEnvVarsByCategory() {
  const vars = getEnvironmentVariables()
  return {
    system: vars.filter((v) => v.category === "system"),
    trading: vars.filter((v) => v.category === "trading"),
    ai: vars.filter((v) => v.category === "ai"),
    exchange: vars.filter((v) => v.category === "exchange"),
    telegram: vars.filter((v) => v.category === "telegram"),
    database: vars.filter((v) => v.category === "database"),
  }
}
