// API endpoint for risk management
import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { supabase } from "@/lib/config/database"
import { logger } from "@/lib/utils/logger"

async function getRiskDataHandler(req: AuthenticatedRequest) {
  try {
    if (!req.user) {
      return NextResponse.json({ error: "User not authenticated" }, { status: 401 })
    }

    // Get user settings
    const { data: user, error: userError } = await supabase
      .from("users")
      .select("settings")
      .eq("id", req.user.userId)
      .single()

    if (userError) throw userError

    // Get today's trades for daily loss calculation
    const today = new Date().toISOString().split("T")[0]
    const { data: todayTrades, error: tradesError } = await supabase
      .from("trades")
      .select("pnl")
      .eq("user_id", req.user.userId)
      .gte("execution_time", `${today}T00:00:00Z`)
      .not("pnl", "is", null)

    if (tradesError) throw tradesError

    const dailyPnL = todayTrades?.reduce((sum, trade) => sum + (trade.pnl || 0), 0) || 0
    const maxDailyLoss = user?.settings?.max_daily_loss || 1000
    const riskUsed = (Math.abs(dailyPnL) / maxDailyLoss) * 100

    // Get open positions for exposure calculation
    const { data: openTrades, error: openTradesError } = await supabase
      .from("trades")
      .select("*")
      .eq("user_id", req.user.userId)
      .eq("status", "open")

    if (openTradesError) throw openTradesError

    const totalExposure = openTrades?.reduce((sum, trade) => sum + trade.entry_price * trade.quantity, 0) || 0

    const riskData = {
      dailyLoss: {
        current: Math.abs(dailyPnL),
        limit: maxDailyLoss,
        percentage: Math.min(riskUsed, 100),
        status: riskUsed > 80 ? "high" : riskUsed > 50 ? "medium" : "low",
      },
      exposure: {
        total: totalExposure,
        openPositions: openTrades?.length || 0,
        maxPositions: user?.settings?.max_positions || 10,
      },
      settings: user?.settings || {},
    }

    return NextResponse.json({ success: true, riskData })
  } catch (error) {
    logger.error("Failed to fetch risk data", { error, userId: req.user?.userId })
    return NextResponse.json({ error: "Failed to fetch risk data" }, { status: 500 })
  }
}

async function updateRiskSettingsHandler(req: AuthenticatedRequest) {
  try {
    if (!req.user) {
      return NextResponse.json({ error: "User not authenticated" }, { status: 401 })
    }

    const { settings } = await req.json()

    const { data: updatedUser, error } = await supabase
      .from("users")
      .update({
        settings: {
          ...settings,
          updated_at: new Date().toISOString(),
        },
      })
      .eq("id", req.user.userId)
      .select("settings")
      .single()

    if (error) throw error

    logger.info("Risk settings updated", { userId: req.user.userId, settings })

    return NextResponse.json({
      success: true,
      message: "Risk settings updated successfully",
      settings: updatedUser.settings,
    })
  } catch (error) {
    logger.error("Failed to update risk settings", { error, userId: req.user?.userId })
    return NextResponse.json({ error: "Failed to update risk settings" }, { status: 500 })
  }
}

export const GET = withAuth(getRiskDataHandler)
export const POST = withAuth(updateRiskSettingsHandler)
