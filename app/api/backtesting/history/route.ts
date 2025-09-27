// API endpoint to get backtest history
import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { supabase } from "@/lib/config/database"
import { logger } from "@/lib/utils/logger"

async function getBacktestHistoryHandler(req: AuthenticatedRequest) {
  try {
    if (!req.user) {
      return NextResponse.json({ error: "User not authenticated" }, { status: 401 })
    }

    const { searchParams } = new URL(req.url)
    const limit = Number.parseInt(searchParams.get("limit") || "20")
    const offset = Number.parseInt(searchParams.get("offset") || "0")
    const strategyId = searchParams.get("strategyId")

    let query = supabase
      .from("backtests")
      .select(`
        *,
        strategies (
          name,
          type,
          description
        )
      `)
      .eq("user_id", req.user.userId)
      .order("created_at", { ascending: false })
      .range(offset, offset + limit - 1)

    if (strategyId) {
      query = query.eq("strategy_id", strategyId)
    }

    const { data: backtests, error } = await query

    if (error) throw error

    return NextResponse.json({
      success: true,
      backtests: backtests || [],
      pagination: {
        limit,
        offset,
        hasMore: (backtests?.length || 0) === limit,
      },
    })
  } catch (error) {
    logger.error("Failed to fetch backtest history", { error, userId: req.user?.userId })
    return NextResponse.json({ error: "Failed to fetch backtest history" }, { status: 500 })
  }
}

export const GET = withAuth(getBacktestHistoryHandler)
