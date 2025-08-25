// API endpoint for historical market data
import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { marketDataAggregator } from "@/lib/market-data/aggregator"
import { logger } from "@/lib/utils/logger"

async function getHistoricalDataHandler(req: AuthenticatedRequest) {
  try {
    const { searchParams } = new URL(req.url)
    const symbol = searchParams.get("symbol")
    const timeframe = searchParams.get("timeframe") || "1h"
    const limit = Number.parseInt(searchParams.get("limit") || "100")

    if (!symbol) {
      return NextResponse.json({ error: "Symbol parameter is required" }, { status: 400 })
    }

    if (limit > 1000) {
      return NextResponse.json({ error: "Limit cannot exceed 1000" }, { status: 400 })
    }

    const data = await marketDataAggregator.getHistoricalData(symbol, timeframe, limit)

    return NextResponse.json({
      symbol,
      timeframe,
      data,
      count: data.length,
    })
  } catch (error) {
    logger.error("Historical data fetch failed", { error })
    return NextResponse.json({ error: "Failed to fetch historical data" }, { status: 500 })
  }
}

export const GET = withAuth(getHistoricalDataHandler)
