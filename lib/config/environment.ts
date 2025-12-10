// =============================================================================
// v0 Strategy Engine Pro - Environment Configuration
// =============================================================================
// Industry-standard configuration for professional trading operations
// All values are based on best practices from top trading platforms

export const config = {
  // =========================================================================
  // Application Settings
  // =========================================================================
  app: {
    name: "v0 Strategy Engine Pro",
    version: "2.0.0",
    env: process.env.NODE_ENV || "development",
    debug: process.env.DEBUG === "true" || process.env.NODE_ENV === "development",
    baseUrl: process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
    region: process.env.VERCEL_REGION || "iad1",
    pythonApiUrl: process.env.PYTHON_API_URL || "",
  },

  // =========================================================================
  // Database - Upstash Redis (Primary Storage)
  // =========================================================================
  database: {
    url: process.env.UPSTASH_KV_KV_REST_API_URL || process.env.DATABASE_URL,
    token: process.env.UPSTASH_KV_KV_REST_API_TOKEN,
    redisUrl: process.env.UPSTASH_KV_REDIS_URL || process.env.REDIS_URL,
  },

  // =========================================================================
  // JWT Authentication - Industry Standard Security
  // =========================================================================
  auth: {
    jwtSecret: process.env.JWT_SECRET || "change-this-in-production-to-a-secure-random-string",
    jwtExpiry: process.env.JWT_EXPIRY || "24h",
    jwtRefreshExpiry: "7d",
    bcryptRounds: Number.parseInt(process.env.BCRYPT_ROUNDS || "12"),
    sessionTimeout: 86400000, // 24 hours in milliseconds
    maxLoginAttempts: 5,
    lockoutDuration: 900000, // 15 minutes in milliseconds
  },

  // =========================================================================
  // Exchange Configurations (All 11 Supported Exchanges)
  // =========================================================================

  // 1. Binance - World's Largest Exchange
  binance: {
    apiKey: process.env.BINANCE_API_KEY || "",
    apiSecret: process.env.BINANCE_API_SECRET || "",
    testnet: process.env.BINANCE_TESTNET === "true",
    baseUrl: process.env.BINANCE_TESTNET === "true" ? "https://testnet.binance.vision" : "https://api.binance.com",
    wsUrl:
      process.env.BINANCE_TESTNET === "true" ? "wss://testnet.binance.vision/ws" : "wss://stream.binance.com:9443/ws",
    rateLimit: Number.parseInt(process.env.BINANCE_RATE_LIMIT || "1200"), // requests per minute
  },

  // 2. Bitget - Copy Trading Leader
  bitget: {
    apiKey: process.env.BITGET_API_KEY || "",
    apiSecret: process.env.BITGET_API_SECRET || "",
    passphrase: process.env.BITGET_PASSPHRASE || "",
    testnet: process.env.BITGET_TESTNET === "true",
    baseUrl: "https://api.bitget.com",
    wsUrl: "wss://ws.bitget.com/spot/v1/stream",
    rateLimit: Number.parseInt(process.env.BITGET_RATE_LIMIT || "600"),
  },

  // 3. Kraken - Most Secure US Exchange
  kraken: {
    apiKey: process.env.KRAKEN_API_KEY || "",
    privateKey: process.env.KRAKEN_PRIVATE_KEY || "",
    testnet: process.env.KRAKEN_TESTNET === "true",
    baseUrl: "https://api.kraken.com",
    wsUrl: "wss://ws.kraken.com",
    rateLimit: Number.parseInt(process.env.KRAKEN_RATE_LIMIT || "60"),
  },

  // 4. Coinbase - Most Trusted US Exchange
  coinbase: {
    apiKey: process.env.COINBASE_API_KEY || "",
    apiSecret: process.env.COINBASE_API_SECRET || "",
    testnet: process.env.COINBASE_TESTNET === "true",
    baseUrl:
      process.env.COINBASE_TESTNET === "true"
        ? "https://api-public.sandbox.exchange.coinbase.com"
        : "https://api.exchange.coinbase.com",
    wsUrl:
      process.env.COINBASE_TESTNET === "true"
        ? "wss://ws-feed-public.sandbox.exchange.coinbase.com"
        : "wss://ws-feed.exchange.coinbase.com",
    rateLimit: 30,
  },

  // 5. OKX - Top 3 Global Exchange
  okx: {
    apiKey: process.env.OKX_API_KEY || "",
    apiSecret: process.env.OKX_API_SECRET || "",
    passphrase: process.env.OKX_PASSPHRASE || "",
    testnet: process.env.OKX_TESTNET === "true",
    baseUrl: process.env.OKX_TESTNET === "true" ? "https://www.okx.com" : "https://www.okx.com",
    wsUrl: "wss://ws.okx.com:8443/ws/v5/public",
    rateLimit: Number.parseInt(process.env.OKX_RATE_LIMIT || "60"),
  },

  // 6. Bybit - Derivatives Leader
  bybit: {
    apiKey: process.env.BYBIT_API_KEY || "",
    apiSecret: process.env.BYBIT_API_SECRET || "",
    testnet: process.env.BYBIT_TESTNET === "true",
    baseUrl: process.env.BYBIT_TESTNET === "true" ? "https://api-testnet.bybit.com" : "https://api.bybit.com",
    wsUrl:
      process.env.BYBIT_TESTNET === "true"
        ? "wss://stream-testnet.bybit.com/v5/public/spot"
        : "wss://stream.bybit.com/v5/public/spot",
    rateLimit: 120,
  },

  // 7. KuCoin - Altcoin Paradise
  kucoin: {
    apiKey: process.env.KUCOIN_API_KEY || "",
    apiSecret: process.env.KUCOIN_API_SECRET || "",
    passphrase: process.env.KUCOIN_PASSPHRASE || "",
    testnet: process.env.KUCOIN_TESTNET === "true",
    baseUrl: process.env.KUCOIN_TESTNET === "true" ? "https://openapi-sandbox.kucoin.com" : "https://api.kucoin.com",
    wsUrl: "wss://ws-api.kucoin.com",
    rateLimit: 1800,
  },

  // 8. Gate.io - Wide Asset Selection
  gate: {
    apiKey: process.env.GATE_API_KEY || "",
    apiSecret: process.env.GATE_API_SECRET || "",
    testnet: false,
    baseUrl: "https://api.gateio.ws",
    wsUrl: "wss://api.gateio.ws/ws/v4/",
    rateLimit: 900,
  },

  // 9. Huobi/HTX - Asian Market Leader
  huobi: {
    apiKey: process.env.HUOBI_API_KEY || "",
    apiSecret: process.env.HUOBI_API_SECRET || "",
    testnet: false,
    baseUrl: "https://api.huobi.pro",
    wsUrl: "wss://api.huobi.pro/ws",
    rateLimit: 100,
  },

  // 10. MEXC - Low Fee Exchange
  mexc: {
    apiKey: process.env.MEXC_API_KEY || "",
    apiSecret: process.env.MEXC_API_SECRET || "",
    testnet: false,
    baseUrl: "https://api.mexc.com",
    wsUrl: "wss://wbs.mexc.com/ws",
    rateLimit: 500,
  },

  // 11. Phemex - Contract Trading Specialist
  phemex: {
    apiKey: process.env.PHEMEX_API_KEY || "",
    apiSecret: process.env.PHEMEX_API_SECRET || "",
    testnet: process.env.PHEMEX_TESTNET === "true",
    baseUrl: process.env.PHEMEX_TESTNET === "true" ? "https://testnet-api.phemex.com" : "https://api.phemex.com",
    wsUrl: process.env.PHEMEX_TESTNET === "true" ? "wss://testnet-api.phemex.com/ws" : "wss://phemex.com/ws",
    rateLimit: 500,
  },

  // =========================================================================
  // Telegram Bot Configuration
  // =========================================================================
  telegram: {
    botToken: process.env.TELEGRAM_BOT_TOKEN || "",
    webhookUrl: process.env.TELEGRAM_WEBHOOK_URL || "",
    botUsername: process.env.TELEGRAM_BOT_USERNAME || "strategyengine",
    chatId: process.env.TELEGRAM_CHAT_ID || "",
    alertCooldown: 5000, // 5 seconds between alerts
    confirmationTimeout: 60000, // 60 seconds for trade confirmation
    maxPendingAlerts: 10,
  },

  // =========================================================================
  // AI/LLM Provider Configuration
  // =========================================================================
  ai: {
    primaryModel: process.env.AI_PRIMARY_MODEL || "openai", // Best for complex analysis
    fallbackModel: process.env.AI_FALLBACK_MODEL || "groq", // Fast fallback
    sentimentModel: process.env.AI_SENTIMENT_MODEL || "perplexity", // Real-time sentiment

    // OpenAI (GPT-4, GPT-4o)
    openai: {
      apiKey: process.env.OPENAI_API_KEY || "",
      model: process.env.OPENAI_MODEL || "gpt-4o",
      maxTokens: 4096,
      temperature: 0.7,
    },

    // Anthropic Claude
    anthropic: {
      apiKey: process.env.ANTHROPIC_API_KEY || "",
      model: "claude-sonnet-4-20250514",
      maxTokens: 4096,
    },

    // Google Gemini
    google: {
      apiKey: process.env.GOOGLE_API_KEY || process.env.GEMINI_API_KEY || "",
      model: "gemini-2.0-flash",
      maxTokens: 8192,
    },

    // xAI Grok
    grok: {
      apiKey: process.env.XAI_API_KEY || process.env.XAI_GROK_API_KEY || "",
      model: "grok-4-latest",
      maxTokens: 4096,
    },

    // Groq (Ultra-fast inference) - Already integrated
    groq: {
      apiKey: process.env.GROQ_API_KEY || "",
      model: "llama-3.3-70b-versatile",
      maxTokens: 8192,
    },

    // Perplexity (Real-time web search)
    perplexity: {
      apiKey: process.env.PERPLEXITY_API_KEY || "",
      model: "llama-3.1-sonar-large-128k-online",
      maxTokens: 4096,
    },

    // Cohere
    cohere: {
      apiKey: process.env.COHERE_API_KEY || "",
      model: "command-r-plus",
      maxTokens: 4096,
    },

    // Mistral AI
    mistral: {
      apiKey: process.env.MISTRAL_API_KEY || "",
      model: "mistral-large-latest",
      maxTokens: 4096,
    },

    // HuggingFace
    huggingface: {
      token: process.env.HUGGINGFACE_TOKEN || "",
      model: "meta-llama/Llama-3.3-70B-Instruct",
    },

    // DeepSeek
    deepseek: {
      apiKey: process.env.DEEPSEEK_API_KEY || "",
      model: "deepseek-chat",
      maxTokens: 4096,
    },

    // Together AI
    together: {
      apiKey: process.env.TOGETHER_API_KEY || "",
      model: "meta-llama/Llama-3.3-70B-Instruct-Turbo",
      maxTokens: 4096,
    },

    // Model update interval
    modelUpdateInterval: Number.parseInt(process.env.MODEL_UPDATE_INTERVAL_HOURS || "24"),

    // Ensemble voting configuration
    ensembleVoting: {
      enabled: true,
      minConsensus: 0.6, // 60% agreement required
      providers: ["openai", "groq", "grok"],
    },
  },

  // =========================================================================
  // Risk Management - Professional Trading Standards
  // =========================================================================
  risk: {
    // Position Sizing
    maxPositionSize: Number.parseFloat(process.env.MAX_POSITION_SIZE || "2000"), // $2000 max per position
    maxPositionPercent: 0.02, // 2% of portfolio per trade (industry standard)

    // Loss Limits
    maxDailyLoss: Number.parseFloat(process.env.MAX_DAILY_LOSS || "500"), // $500 max daily loss (conservative)
    maxDailyLossPercent: 0.05, // 5% max daily loss
    maxDrawdown: Number.parseFloat(process.env.MAX_DRAWDOWN || "0.10"), // 10% max drawdown

    // Trade Limits
    maxOpenTrades: Number.parseInt(process.env.MAX_OPEN_TRADES || "5"), // Max 5 concurrent trades
    maxConcurrentTrades: Number.parseInt(process.env.MAX_CONCURRENT_TRADES || "5"),
    cooldownPeriod: Number.parseInt(process.env.TRADE_COOLDOWN_MS || "60000"), // 1 minute between trades

    // Stop Loss / Take Profit
    defaultStopLoss: Number.parseFloat(process.env.DEFAULT_STOP_LOSS || "0.02"), // 2% stop loss
    defaultTakeProfit: Number.parseFloat(process.env.DEFAULT_TAKE_PROFIT || "0.06"), // 6% take profit (1:3 ratio)
    trailingStopEnabled: true,
    trailingStopPercent: 0.015, // 1.5%

    // Kelly Criterion
    kellyFraction: Number.parseFloat(process.env.KELLY_FRACTION || "0.25"), // Quarter Kelly (conservative)

    // Phi (Golden Ratio) Risk
    phiRiskPerTrade: Number.parseFloat(process.env.PHI_RISK_PER_TRADE || "0.01618"), // 1.618% (golden ratio)
    phiMaxDrawdown: Number.parseFloat(process.env.PHI_MAX_DRAWDOWN || "0.0618"), // 6.18% (golden ratio)
    phiAtrMultiplier: Number.parseFloat(process.env.PHI_ATR_MULTIPLIER || "1.618"), // ATR multiplier

    // Pattern Day Trading Protection
    pdtMaxDayTrades: Number.parseInt(process.env.PDT_MAX_DAY_TRADES || "3"), // Max 3 day trades in 5 days
    pdtMinAccountValue: Number.parseInt(process.env.PDT_MIN_ACCOUNT_VALUE || "25000"), // $25k PDT threshold
    pdtDayTradeWindow: Number.parseInt(process.env.PDT_DAY_TRADE_WINDOW || "5"), // 5 day rolling window

    // Volatility Controls
    maxVolatility: Number.parseFloat(process.env.MAX_VOLATILITY || "0.05"), // Pause if >5% daily volatility
    volatilityWindow: Number.parseInt(process.env.VOLATILITY_WINDOW || "24"), // 24 hour window
    volatilityPauseDuration: Number.parseInt(process.env.VOLATILITY_PAUSE_DURATION || "3600000"), // 1 hour pause
  },

  // =========================================================================
  // Trading Configuration - Professional Defaults
  // =========================================================================
  trading: {
    mode: (process.env.TRADING_MODE as "demo" | "paper" | "live") || "demo",

    // Demo/Paper Trading - Start with realistic balance
    demoEnabled: process.env.ENABLE_DEMO_MODE !== "false",
    demoInitialBalance: Number.parseFloat(process.env.DEMO_INITIAL_BALANCE || "10000"), // $10k demo balance

    // Backtesting - Full year by default
    backtestEnabled: process.env.ENABLE_BACKTESTING !== "false", // Enabled by default
    backtestStartDate: process.env.BACKTEST_START_DATE || "2024-01-01",
    backtestEndDate: process.env.BACKTEST_END_DATE || "2024-12-31",

    defaultTradeSize: Number.parseFloat(process.env.DEFAULT_TRADE_SIZE || "200"), // $200 per trade
    defaultLeverage: 1, // No leverage by default (safety first)

    // Slippage
    maxSlippage: 0.003, // 0.3% max slippage (tighter for professional trading)

    // Order Types
    preferredOrderType: "limit", // Limit orders for better fills
    limitOrderTimeout: 30000, // 30 seconds

    // Target Performance (realistic professional targets)
    targetTradesPerYear: Number.parseInt(process.env.TARGET_TRADES_PER_YEAR || "250"), // ~1 trade/day
    targetWinRate: 0.55, // 55% win rate target
    targetRiskReward: 3.0, // 1:3 risk/reward ratio
  },

  // =========================================================================
  // Smart Money Strategy Configuration
  // =========================================================================
  smartMoney: {
    walletAddress: process.env.SMART_MONEY_WALLET_ADDRESS || "",
    maxTradeSize: Number.parseFloat(process.env.SMART_MONEY_MAX_TRADE || "5000"),
    minTradeSize: Number.parseFloat(process.env.SMART_MONEY_MIN_TRADE || "100"),
    stopLoss: Number.parseFloat(process.env.SMART_MONEY_STOP_LOSS || "0.03"), // 3%
    takeProfit1: Number.parseFloat(process.env.SMART_MONEY_TAKE_PROFIT_1 || "0.05"), // 5%
    takeProfit2: Number.parseFloat(process.env.SMART_MONEY_TAKE_PROFIT_2 || "0.10"), // 10%
    cooldown: Number.parseInt(process.env.SMART_MONEY_COOLDOWN || "300000"), // 5 minutes
  },

  // =========================================================================
  // High Frequency Trading Configuration
  // =========================================================================
  highFrequency: {
    enabled: false, // Disabled by default - requires specialized setup
    scanInterval: Number.parseInt(process.env.HF_SCAN_INTERVAL || "100"), // 100ms
    maxConcurrentTrades: Number.parseInt(process.env.MAX_CONCURRENT_TRADES || "3"),
    positionSize: Number.parseFloat(process.env.HF_POSITION_SIZE || "50"),
    microScalpSize: Number.parseFloat(process.env.MICRO_SCALP_SIZE || "25"),
  },

  // =========================================================================
  // External Data APIs
  // =========================================================================
  apis: {
    // News & Sentiment
    newsApi: process.env.NEWS_API_KEY || "",
    currentsApi: process.env.CURRENTS_API_KEY || "",
    mediastack: process.env.MEDIASTACK_API_KEY || "",

    // Social Media
    twitterBearer: process.env.TWITTER_BEARER_TOKEN || "",
    redditClientId: process.env.REDDIT_CLIENT_ID || "",
    redditClientSecret: process.env.REDDIT_CLIENT_SECRET || "",

    // Market Data
    alphaVantage: process.env.ALPHA_VANTAGE_API_KEY || "",
    twelveData: process.env.TWELVE_DATA_API_KEY || "",
    rapidApi: process.env.RAPIDAPI_KEY || "",

    // Blockchain Data
    debank: process.env.DEBANK_API_KEY || "",
    dexscreener: process.env.DEXSCREENER_API_KEY || "",
  },

  // =========================================================================
  // Redis Cache Configuration
  // =========================================================================
  redis: {
    url: process.env.UPSTASH_KV_KV_REST_API_URL || process.env.REDIS_URL || "",
    token: process.env.UPSTASH_KV_KV_REST_API_TOKEN || "",
    // Cache TTLs (in seconds)
    priceCacheTTL: 5, // 5 seconds for price data
    orderBookCacheTTL: 2, // 2 seconds for order book
    balanceCacheTTL: 30, // 30 seconds for balance
    tradeCacheTTL: 60, // 1 minute for trade history
    analyticsCacheTTL: 300, // 5 minutes for analytics
  },

  // =========================================================================
  // Logging & Monitoring - Professional Standards
  // =========================================================================
  logging: {
    level: (process.env.LOG_LEVEL as "debug" | "info" | "warn" | "error") || "info",
    structuredLogs: process.env.ENABLE_STRUCTURED_LOGS !== "false", // JSON logs by default
    logFile: process.env.LOG_FILE || "logs/trading.log",
    enableProfiling: process.env.ENABLE_PROFILING === "true", // Performance profiling

    // Log retention
    maxLogSize: "10m", // 10MB per file
    maxLogFiles: 5, // Keep 5 rotated files

    // Metrics collection
    metricsInterval: 60000, // Collect metrics every minute
    enableTraceId: true, // Trace request IDs
  },

  // =========================================================================
  // Database & Performance - Professional Settings
  // =========================================================================
  performance: {
    dbPoolSize: Number.parseInt(process.env.DB_POOL_SIZE || "10"), // 10 connections
    dbMaxOverflow: Number.parseInt(process.env.DB_MAX_OVERFLOW || "20"), // 20 overflow connections

    // Data refresh intervals
    dataRefreshInterval: Number.parseInt(process.env.DATA_REFRESH_INTERVAL || "5"), // 5 seconds
    priceUpdateInterval: 1000, // 1 second for price updates
    portfolioRefreshInterval: 30000, // 30 seconds for portfolio

    // Caching
    cacheTtl: 60, // 60 second cache TTL
    maxCacheSize: 1000, // Max 1000 cached items
  },
}

// =========================================================================
// Environment Validation
// =========================================================================
export function validateEnvironment(): { valid: boolean; warnings: string[]; errors: string[] } {
  const warnings: string[] = []
  const errors: string[] = []

  // Check Redis connection (required)
  if (!config.redis.url && !config.database.url) {
    warnings.push("No Redis/Database connection configured. Using in-memory storage.")
  }

  // Check for at least one exchange configured
  const configuredExchanges = getConfiguredExchanges()
  if (configuredExchanges.length === 0) {
    warnings.push("No exchange API keys configured. Demo mode only.")
  }

  // Check for at least one AI provider
  const hasAI = config.ai.openai.apiKey || config.ai.groq.apiKey || config.ai.grok.apiKey
  if (!hasAI) {
    warnings.push("No AI API keys configured. AI features will be limited.")
  }

  // Check Telegram
  if (!config.telegram.botToken) {
    warnings.push("Telegram bot token not configured. Telegram alerts disabled.")
  }

  // Check JWT secret in production
  if (config.app.env === "production" && config.auth.jwtSecret.includes("change-this")) {
    errors.push("JWT_SECRET must be changed in production!")
  }

  return {
    valid: errors.length === 0,
    warnings,
    errors,
  }
}

// =========================================================================
// Helper Functions
// =========================================================================
export function getConfiguredExchanges(): string[] {
  const exchanges: string[] = []

  if (config.binance.apiKey) exchanges.push("binance")
  if (config.bitget.apiKey) exchanges.push("bitget")
  if (config.kraken.apiKey) exchanges.push("kraken")
  if (config.coinbase.apiKey) exchanges.push("coinbase")
  if (config.okx.apiKey) exchanges.push("okx")
  if (config.bybit.apiKey) exchanges.push("bybit")
  if (config.kucoin.apiKey) exchanges.push("kucoin")
  if (config.gate.apiKey) exchanges.push("gate")
  if (config.huobi.apiKey) exchanges.push("huobi")
  if (config.mexc.apiKey) exchanges.push("mexc")
  if (config.phemex.apiKey) exchanges.push("phemex")

  return exchanges
}

export function getConfiguredAIProviders(): string[] {
  const providers: string[] = []

  if (config.ai.openai.apiKey) providers.push("openai")
  if (config.ai.anthropic.apiKey) providers.push("anthropic")
  if (config.ai.google.apiKey) providers.push("google")
  if (config.ai.grok.apiKey) providers.push("grok")
  if (config.ai.groq.apiKey) providers.push("groq")
  if (config.ai.perplexity.apiKey) providers.push("perplexity")
  if (config.ai.cohere.apiKey) providers.push("cohere")
  if (config.ai.mistral.apiKey) providers.push("mistral")
  if (config.ai.huggingface.token) providers.push("huggingface")
  if (config.ai.deepseek.apiKey) providers.push("deepseek")
  if (config.ai.together.apiKey) providers.push("together")

  return providers
}

export function isExchangeConfigured(exchange: string): boolean {
  return getConfiguredExchanges().includes(exchange.toLowerCase())
}

export function getTradingMode(): "demo" | "paper" | "live" {
  if (config.trading.mode === "live" && getConfiguredExchanges().length > 0) {
    return "live"
  }
  if (config.trading.mode === "paper") {
    return "paper"
  }
  return "demo"
}
