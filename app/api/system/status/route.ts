import { NextResponse } from "next/server"
import { redis } from "@/lib/config/database"

export async function GET() {
  const status = {
    application: {
      name: "Neural Trading Bot",
      version: "1.0.0",
      environment: process.env.NODE_ENV || "development",
      ready: true,
    },
    features: {
      authentication: {
        enabled: true,
        provider: "JWT + Redis",
        status: "operational",
      },
      trading: {
        enabled: true,
        modes: ["demo", "live", "backtest"],
        status: "operational",
      },
      exchanges: {
        supported: ["Binance", "Bitget", "Kraken", "Coinbase", "OKX", "Bybit", "KuCoin", "Gate.io", "Huobi", "MEXC"],
        configured: [] as string[],
      },
      strategies: {
        available: [
          "Fibonacci Retracement",
          "Fibonacci ML Enhanced",
          "Smart Money",
          "Mean Reversion",
          "Momentum",
          "Grid Trading",
        ],
        status: "operational",
      },
      telegram: {
        enabled: !!process.env.TELEGRAM_BOT_TOKEN,
        status: process.env.TELEGRAM_BOT_TOKEN ? "configured" : "not_configured",
      },
      ai: {
        enabled: true,
        features: ["Trade prediction", "Risk assessment", "Strategy optimization", "Sentiment analysis"],
        status: "operational",
      },
    },
    database: {
      type: "Redis (Upstash)",
      connected: false,
      latency: 0,
    },
    deployment: {
      platform: "Vercel",
      region: process.env.VERCEL_REGION || "unknown",
      ready: false,
      checklist: {
        database_connected: false,
        env_vars_set: false,
        health_check_passing: false,
      },
    },
  }

  // Check which exchanges are configured
  const exchangeKeys = [
    { name: "Binance", key: "BINANCE_API_KEY" },
    { name: "Bitget", key: "BITGET_API_KEY" },
    { name: "Kraken", key: "KRAKEN_API_KEY" },
    { name: "Coinbase", key: "COINBASE_API_KEY" },
    { name: "OKX", key: "OKX_API_KEY" },
    { name: "Bybit", key: "BYBIT_API_KEY" },
    { name: "KuCoin", key: "KUCOIN_API_KEY" },
    { name: "Gate.io", key: "GATEIO_API_KEY" },
    { name: "Huobi", key: "HUOBI_API_KEY" },
    { name: "MEXC", key: "MEXC_API_KEY" },
  ]

  status.features.exchanges.configured = exchangeKeys.filter((e) => !!process.env[e.key]).map((e) => e.name)

  // Check database connection
  try {
    const start = Date.now()
    await redis.ping()
    status.database.connected = true
    status.database.latency = Date.now() - start
    status.deployment.checklist.database_connected = true
  } catch {
    status.database.connected = false
  }

  // Check required environment variables
  const requiredVars = ["UPSTASH_KV_KV_REST_API_URL", "UPSTASH_KV_KV_REST_API_TOKEN", "JWT_SECRET"]
  status.deployment.checklist.env_vars_set = requiredVars.every((v) => !!process.env[v])

  // Overall health check
  status.deployment.checklist.health_check_passing =
    status.deployment.checklist.database_connected && status.deployment.checklist.env_vars_set

  status.deployment.ready = status.deployment.checklist.health_check_passing

  return NextResponse.json(status)
}
