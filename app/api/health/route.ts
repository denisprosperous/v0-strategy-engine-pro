import { NextResponse } from "next/server"
import { redis } from "@/lib/config/database"
import { liveMarketService } from "@/lib/trading/services/live-market-service"

interface ComponentStatus {
  name: string
  status: "healthy" | "degraded" | "down"
  latency?: number
  message?: string
}

export async function GET() {
  const components: ComponentStatus[] = []
  const startTime = Date.now()

  // Check Redis connection
  try {
    const redisStart = Date.now()
    await redis.ping()
    components.push({
      name: "Redis Database",
      status: "healthy",
      latency: Date.now() - redisStart,
    })
  } catch (error) {
    components.push({
      name: "Redis Database",
      status: "down",
      message: error instanceof Error ? error.message : "Connection failed",
    })
  }

  // Check Market Data Service
  try {
    const marketStart = Date.now()
    const prices = await liveMarketService.getAllPrices()
    const hasData = Object.keys(prices).length > 0
    components.push({
      name: "Market Data Service",
      status: hasData ? "healthy" : "degraded",
      latency: Date.now() - marketStart,
      message: hasData ? `${Object.keys(prices).length} symbols tracked` : "No price data available",
    })
  } catch (error) {
    components.push({
      name: "Market Data Service",
      status: "degraded",
      message: error instanceof Error ? error.message : "Service unavailable",
    })
  }

  // Check Exchange Connections
  const exchanges = ["binance", "bitget", "kraken", "coinbase", "okx", "bybit", "kucoin", "gateio", "huobi", "mexc"]
  const exchangeStatus: Record<string, string> = {}

  for (const exchange of exchanges) {
    try {
      const response = await fetch(`https://api.${exchange}.com/api/v3/ping`, {
        method: "GET",
        signal: AbortSignal.timeout(5000),
      }).catch(() => null)

      exchangeStatus[exchange] = response?.ok ? "connected" : "unavailable"
    } catch {
      exchangeStatus[exchange] = "unavailable"
    }
  }

  const connectedExchanges = Object.values(exchangeStatus).filter((s) => s === "connected").length
  components.push({
    name: "Exchange Connections",
    status: connectedExchanges >= 3 ? "healthy" : connectedExchanges >= 1 ? "degraded" : "down",
    message: `${connectedExchanges}/${exchanges.length} exchanges connected`,
  })

  // Check Telegram Bot
  const telegramConfigured = !!process.env.TELEGRAM_BOT_TOKEN
  components.push({
    name: "Telegram Bot",
    status: telegramConfigured ? "healthy" : "degraded",
    message: telegramConfigured ? "Configured" : "Bot token not set",
  })

  // Check Environment Variables
  const requiredEnvVars = ["UPSTASH_KV_KV_REST_API_URL", "UPSTASH_KV_KV_REST_API_TOKEN", "JWT_SECRET"]
  const optionalEnvVars = ["TELEGRAM_BOT_TOKEN", "BINANCE_API_KEY", "BITGET_API_KEY", "KRAKEN_API_KEY"]

  const missingRequired = requiredEnvVars.filter((v) => !process.env[v])
  const configuredOptional = optionalEnvVars.filter((v) => !!process.env[v])

  components.push({
    name: "Environment Config",
    status: missingRequired.length === 0 ? "healthy" : "degraded",
    message:
      missingRequired.length === 0
        ? `All required vars set, ${configuredOptional.length}/${optionalEnvVars.length} optional configured`
        : `Missing: ${missingRequired.join(", ")}`,
  })

  // Calculate overall status
  const hasDown = components.some((c) => c.status === "down")
  const hasDegraded = components.some((c) => c.status === "degraded")
  const overallStatus = hasDown ? "down" : hasDegraded ? "degraded" : "healthy"

  return NextResponse.json({
    status: overallStatus,
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    totalLatency: Date.now() - startTime,
    components,
    exchangeStatus,
    version: "1.0.0",
    environment: process.env.NODE_ENV || "development",
  })
}
