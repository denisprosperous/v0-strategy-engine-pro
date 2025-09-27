// API endpoint for dashboard analytics
import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { supabase } from "@/lib/config/database"
import { logger } from "@/lib/utils/logger"

async function getAnalyticsHandler(req: AuthenticatedRequest) {
  try {
    if (!req.user) {
      return NextResponse.json({ error: "User not authenticated" }, { status: 401 })
    }

    // Get user's trades for analytics
    const { data: trades, error: tradesError } = await supabase
      .from("trades")
      .select("*")
      .eq("user_id", req.user.userId)
      .order("execution_time", { ascending: false })

    if (tradesError) throw tradesError

    // Get user's strategies
    const { data: strategies, error: strategiesError } = await supabase
      .from("strategies")
      .select("*")
      .eq("created_by", req.user.userId)

    if (strategiesError) throw strategiesError

    // Calculate analytics
    const totalTrades = trades?.length || 0
    const openTrades = trades?.filter((t) => t.status === "open").length || 0
    const closedTrades = trades?.filter((t) => t.status === "closed") || []

    const totalPnL = closedTrades.reduce((sum, trade) => sum + (trade.pnl || 0), 0)
    const winningTrades = closedTrades.filter((t) => (t.pnl || 0) > 0).length
    const winRate = closedTrades.length > 0 ? (winningTrades / closedTrades.length) * 100 : 0

    const activeStrategies = strategies?.filter((s) => s.is_active).length || 0

    // Get today's trades for daily P&L
    const today = new Date().toISOString().split("T")[0]
    const todayTrades = closedTrades.filter((t) => t.close_time && t.close_time.toString().startsWith(today))
    const dailyPnL = todayTrades.reduce((sum, trade) => sum + (trade.pnl || 0), 0)

    // Calculate portfolio value (simplified)
    const portfolioValue = 10000 + totalPnL // Base amount + total P&L

    const analytics = {
      portfolio: {
        totalValue: portfolioValue,
        totalPnL,
        dailyPnL,
        pnlPercentage: portfolioValue > 0 ? (totalPnL / (portfolioValue - totalPnL)) * 100 : 0,
      },
      trading: {
        totalTrades,
        openTrades,
        winRate,
        activeStrategies,
      },
      performance: {
        bestTrade: Math.max(...closedTrades.map((t) => t.pnl || 0), 0),
        worstTrade: Math.min(...closedTrades.map((t) => t.pnl || 0), 0),
        avgTradeSize:
          closedTrades.length > 0
            ? closedTrades.reduce((sum, t) => sum + t.entry_price * t.quantity, 0) / closedTrades.length
            : 0,
      },
    }

    return NextResponse.json({ success: true, analytics })
  } catch (error) {
    logger.error("Failed to fetch analytics", { error, userId: req.user?.userId })
    return NextResponse.json({ error: "Failed to fetch analytics" }, { status: 500 })
  }
}

export const GET = withAuth(getAnalyticsHandler)
