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
    apiKey: process.env.BITGET_API_KEY || "bg_fe79979849aa59d99719eec52b6d1b8c",
    apiSecret: process.env.BITGET_API_SECRET || "aef1207a95c75afff9a1d47d83f34ad9cb007e86973ea54feeebfe9a696b0fc4",
    passphrase: process.env.BITGET_PASSPHRASE || "V4axZOr8RAL94CklbDZoZa1E1WVoeBR6",
    testnet: process.env.BITGET_TESTNET === "true",
  },

  kraken: {
    apiKey: process.env.KRAKEN_API_KEY || "9Iz2QHeCmB2ofT8fepeb3yeCjp4te8i5nEo4jz/ps/oempYyBbCzWIpy",
    privateKey:
      process.env.KRAKEN_PRIVATE_KEY ||
      "pWxh/WKnVeNqnqaKgyDikZSzEsLtxXjGMBLBsZPr8/73l0nlLoZFYmvqx0Ql5zO8egzou3pZMQOYSCGplYB0Ag==",
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
    botToken: process.env.TELEGRAM_BOT_TOKEN || "7893667413:AAESqhx7CopR5aGmJduadf-EK83k9yDHPTI",
    webhookUrl: process.env.TELEGRAM_WEBHOOK_URL,
    botUsername: "smart_neuralbot",
  },

  // External APIs
  apis: {
    newsApi: process.env.NEWS_API_KEY || "0772a2d7e16020fc5a65482655fcf297",
    currentsApi: process.env.CURRENTS_API_KEY || "O6uIVd-L_82zb3_nfK23Bvzl4GbjFHW9QHDlOtxNnEbOXMwe",
    rapidApiKey: process.env.RAPIDAPI_KEY || "b2476f4726msh396ea7bc6562ac8p16eb73jsn9bd0afb26b93",
    twitterBearer: process.env.TWITTER_BEARER_TOKEN,
    redditClientId: process.env.REDDIT_CLIENT_ID,
    redditClientSecret: process.env.REDDIT_CLIENT_SECRET,
    openaiApiKey:
      process.env.OPENAI_API_KEY ||
      "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",
    huggingfaceToken: process.env.HUGGINGFACE_TOKEN || "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",
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
    openaiApiKey:
      process.env.OPENAI_API_KEY ||
      "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",
    huggingfaceToken: process.env.HUGGINGFACE_TOKEN || "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",
    modelUpdateInterval: Number.parseInt(process.env.MODEL_UPDATE_INTERVAL_HOURS || "24"),
  },
}

// Validate required environment variables
export function validateEnvironment() {
  const required = ["DATABASE_URL", "JWT_SECRET", "TELEGRAM_BOT_TOKEN"]

  const missing = required.filter((key) => !process.env[key])

  if (missing.length > 0) {
    throw new Error(`Missing required environment variables: ${missing.join(", ")}`)
  }
}
