// =============================================================================
// Configuration Status API - Shows all configured services
// =============================================================================

import { NextResponse } from "next/server"
import {
  config,
  validateEnvironment,
  getConfiguredExchanges,
  getConfiguredAIProviders,
  getTradingMode,
} from "@/lib/config/environment"
import { brokerFactory, SUPPORTED_EXCHANGES } from "@/lib/trading/brokers/broker-factory"

export async function GET() {
  try {
    const validation = validateEnvironment()
    const configuredExchanges = getConfiguredExchanges()
    const configuredAI = getConfiguredAIProviders()
    const tradingMode = getTradingMode()

    // Test exchange connections
    const exchangeStatus: Record<string, { configured: boolean; connected: boolean; latency?: number }> = {}

    for (const exchange of SUPPORTED_EXCHANGES) {
      const isConfigured = configuredExchanges.includes(exchange.id)
      let connectionResult = { connected: false, latency: 0 }

      // Test public API connection for all exchanges
      try {
        connectionResult = await brokerFactory.testConnection(exchange.id)
      } catch {
        // Connection test failed
      }

      exchangeStatus[exchange.id] = {
        configured: isConfigured,
        connected: connectionResult.connected,
        latency: connectionResult.latency,
      }
    }

    // Count connected exchanges
    const connectedExchanges = Object.values(exchangeStatus).filter((s) => s.connected).length

    return NextResponse.json({
      success: true,
      timestamp: new Date().toISOString(),

      // Overall Status
      status: {
        valid: validation.valid,
        tradingMode,
        readyForLiveTrading: tradingMode === "live" && configuredExchanges.length > 0,
      },

      // Environment Validation
      validation: {
        warnings: validation.warnings,
        errors: validation.errors,
      },

      // Exchange Configuration
      exchanges: {
        total: SUPPORTED_EXCHANGES.length,
        configured: configuredExchanges.length,
        connected: connectedExchanges,
        list: configuredExchanges,
        status: exchangeStatus,
      },

      // AI Providers
      ai: {
        total: 11,
        configured: configuredAI.length,
        list: configuredAI,
        primary: config.ai.primaryModel,
        fallback: config.ai.fallbackModel,
      },

      // Telegram Bot
      telegram: {
        configured: Boolean(config.telegram.botToken),
        username: config.telegram.botUsername,
      },

      // Redis/Database
      database: {
        configured: Boolean(config.redis.url || config.database.url),
        type: "Upstash Redis",
      },

      // Risk Management Settings
      risk: {
        maxPositionSize: config.risk.maxPositionSize,
        maxDailyLoss: config.risk.maxDailyLoss,
        maxOpenTrades: config.risk.maxOpenTrades,
        defaultStopLoss: `${config.risk.defaultStopLoss * 100}%`,
        defaultTakeProfit: `${config.risk.defaultTakeProfit * 100}%`,
      },

      // Trading Settings
      trading: {
        mode: config.trading.mode,
        demoEnabled: config.trading.demoEnabled,
        demoBalance: config.trading.demoInitialBalance,
        defaultTradeSize: config.trading.defaultTradeSize,
      },

      // Required Environment Variables
      requiredEnvVars: {
        database: {
          UPSTASH_KV_KV_REST_API_URL: Boolean(process.env.UPSTASH_KV_KV_REST_API_URL),
          UPSTASH_KV_KV_REST_API_TOKEN: Boolean(process.env.UPSTASH_KV_KV_REST_API_TOKEN),
        },
        auth: {
          JWT_SECRET: Boolean(process.env.JWT_SECRET),
        },
        telegram: {
          TELEGRAM_BOT_TOKEN: Boolean(process.env.TELEGRAM_BOT_TOKEN),
        },
        exchanges: {
          BITGET_API_KEY: Boolean(process.env.BITGET_API_KEY),
          KRAKEN_API_KEY: Boolean(process.env.KRAKEN_API_KEY),
          PHEMEX_API_KEY: Boolean(process.env.PHEMEX_API_KEY),
        },
        ai: {
          OPENAI_API_KEY: Boolean(process.env.OPENAI_API_KEY),
          GROQ_API_KEY: Boolean(process.env.GROQ_API_KEY),
        },
      },
    })
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Failed to get configuration status",
      },
      { status: 500 },
    )
  }
}
