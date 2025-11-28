import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { pythonApiClient } from "@/lib/api/python-api-client"
import { db } from "@/lib/config/database"
import { liveMarketService } from "@/lib/trading/services/live-market-service"
import { brokerFactory } from "@/lib/trading/brokers/broker-factory"

async function getUnifiedStatusHandler(req: AuthenticatedRequest) {
  try {
    if (!req.user) {
      return NextResponse.json({ error: "User not authenticated" }, { status: 401 })
    }

    // Check if Python backend is available
    const pythonAvailable = await pythonApiClient.isAvailable()

    // Get data from multiple sources
    const [exchangeConnections, analytics, portfolioValue] = await Promise.all([
      brokerFactory.testAllConnections(),
      db.getAnalytics(req.user.userId),
      liveMarketService.getPortfolioValue(req.user.userId),
    ])

    // Try to get Python backend status if available
    let pythonStatus = null
    if (pythonAvailable) {
      const statusResponse = await pythonApiClient.getBotStatus()
      if (statusResponse.success) {
        pythonStatus = statusResponse.data
      }
    }

    // Count connected exchanges
    const connectedExchanges = Object.entries(exchangeConnections)
      .filter(([_, status]) => status.connected)
      .map(([exchange]) => exchange)

    const unifiedStatus = {
      // System status
      system: {
        nextjsStatus: "operational",
        pythonBackendAvailable: pythonAvailable,
        pythonBackendStatus: pythonStatus?.is_running ? "running" : "stopped",
        timestamp: new Date().toISOString(),
      },

      // Trading status
      trading: {
        isRunning: pythonStatus?.is_running || false,
        mode: pythonStatus?.mode || "manual",
        aiEnabled: pythonStatus?.ai_enabled || false,
        activeSignals: pythonStatus?.active_signals || 0,
        openPositions: analytics.trading.openTrades,
      },

      // Exchange connections
      exchanges: {
        connected: connectedExchanges,
        total: Object.keys(exchangeConnections).length,
        details: exchangeConnections,
      },

      // Portfolio summary
      portfolio: {
        totalValue: portfolioValue.totalValue,
        totalPnL: portfolioValue.totalPnL,
        pnlPercentage: portfolioValue.pnlPercentage,
        winRate: portfolioValue.winRate,
      },

      // Performance metrics
      performance: {
        totalTrades: analytics.trading.totalTrades,
        activeStrategies: analytics.trading.activeStrategies,
        bestTrade: analytics.performance.bestTrade,
        worstTrade: analytics.performance.worstTrade,
      },
    }

    return NextResponse.json({
      success: true,
      status: unifiedStatus,
    })
  } catch (error) {
    console.error("Error getting unified status:", error)
    return NextResponse.json({ error: "Failed to get unified status" }, { status: 500 })
  }
}

export const GET = withAuth(getUnifiedStatusHandler)
