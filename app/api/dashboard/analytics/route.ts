// API endpoint for dashboard analytics
import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { db } from "@/lib/config/database"
import { liveMarketService } from "@/lib/trading/services/live-market-service"
import { logger } from "@/lib/utils/logger"

async function getAnalyticsHandler(req: AuthenticatedRequest) {
  try {
    if (!req.user) {
      return NextResponse.json({ error: "User not authenticated" }, { status: 401 })
    }

    // Get analytics from Redis-based data layer
    const analytics = await db.getAnalytics(req.user.userId)

    // Get live portfolio value
    const portfolioData = await liveMarketService.getPortfolioValue(req.user.userId)

    // Merge analytics with live data
    const mergedAnalytics = {
      portfolio: {
        totalValue: portfolioData.totalValue,
        totalPnL: analytics.portfolio.totalPnL,
        dailyPnL: analytics.portfolio.dailyPnL,
        pnlPercentage: portfolioData.pnlPercentage,
      },
      trading: {
        totalTrades: analytics.trading.totalTrades,
        openTrades: portfolioData.openTrades,
        winRate: portfolioData.winRate,
        activeStrategies: portfolioData.activeStrategies,
      },
      performance: analytics.performance,
    }

    return NextResponse.json({ success: true, analytics: mergedAnalytics })
  } catch (error) {
    logger.error("Failed to fetch analytics", { error, userId: req.user?.userId })
    return NextResponse.json({ error: "Failed to fetch analytics" }, { status: 500 })
  }
}

export const GET = withAuth(getAnalyticsHandler)
