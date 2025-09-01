// Environment configuration and validation
export const config = {
  // Database
  database: {
    url: process.env.DATABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL,
    key: process.env.DATABASE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  },

  // JWT Authentication
  auth: {
    jwtSecret: process.env.JWT_SECRET || "your-super-secret-jwt-key",
    jwtExpiry: process.env.JWT_EXPIRY || "24h",
    bcryptRounds: Number.parseInt(process.env.BCRYPT_ROUNDS || "12"),
  },

  // Trading APIs
  bitget: {
    apiKey: process.env.BITGET_API_KEY,
    apiSecret: process.env.BITGET_API_SECRET,
    passphrase: process.env.BITGET_PASSPHRASE,
    testnet: process.env.BITGET_TESTNET === "true",
  },

  kraken: {
    apiKey: process.env.KRAKEN_API_KEY,
    privateKey: process.env.KRAKEN_PRIVATE_KEY,
    testnet: process.env.KRAKEN_TESTNET === "true",
  },

  binance: {
    apiKey: process.env.BINANCE_API_KEY,
    apiSecret: process.env.BINANCE_API_SECRET,
    testnet: process.env.BINANCE_TESTNET === "true",
  },

  bybit: {
    apiKey: process.env.BYBIT_API_KEY,
    apiSecret: process.env.BYBIT_API_SECRET,
    testnet: process.env.BYBIT_TESTNET === "true",
  },

  // Telegram Bot
  telegram: {
    botToken: process.env.TELEGRAM_BOT_TOKEN,
    webhookUrl: process.env.TELEGRAM_WEBHOOK_URL,
    botUsername: process.env.TELEGRAM_BOT_USERNAME || "smart_neuralbot",
  },

  // External APIs
  apis: {
    newsApi: process.env.NEWS_API_KEY,
    currentsApi: process.env.CURRENTS_API_KEY,
    rapidApiKey: process.env.RAPIDAPI_KEY,
    twitterBearer: process.env.TWITTER_BEARER_TOKEN,
    redditClientId: process.env.REDDIT_CLIENT_ID,
    redditClientSecret: process.env.REDDIT_CLIENT_SECRET,
    openaiApiKey: process.env.OPENAI_API_KEY,
    huggingfaceToken: process.env.HUGGINGFACE_TOKEN,
  },

  // Redis Cache
  redis: {
    url: process.env.REDIS_URL || process.env.KV_REST_API_URL,
    token: process.env.REDIS_TOKEN || process.env.KV_REST_API_TOKEN,
  },

  // Risk Management
  risk: {
    maxDailyLoss: Number.parseFloat(process.env.MAX_DAILY_LOSS || "1000"),
    maxPositionSize: Number.parseFloat(process.env.MAX_POSITION_SIZE || "10000"),
    maxOpenTrades: Number.parseInt(process.env.MAX_OPEN_TRADES || "10"),
    cooldownPeriod: Number.parseInt(process.env.TRADE_COOLDOWN_MS || "30000"),
  },

  // AI/ML
  ai: {
    openaiApiKey: process.env.OPENAI_API_KEY,
    huggingfaceToken: process.env.HUGGINGFACE_TOKEN,
    modelUpdateInterval: Number.parseInt(process.env.MODEL_UPDATE_INTERVAL_HOURS || "24"),
  },
}

// Validate required environment variables
export function validateEnvironment() {
  const required = [
    "NEXT_PUBLIC_SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "JWT_SECRET",
    "TELEGRAM_BOT_TOKEN",
  ]

  const missing = required.filter((key) => !process.env[key])

  if (missing.length > 0) {
    throw new Error(`Missing required environment variables: ${missing.join(", ")}`)
  }
}
