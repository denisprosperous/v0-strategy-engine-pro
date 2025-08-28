// API endpoint for real-time price data
import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { marketDataAggregator } from "@/lib/market-data/aggregator"
import { logger } from "@/lib/utils/logger"

async function getPriceHandler(req: AuthenticatedRequest) {
  try {
    const { searchParams } = new URL(req.url)
    const symbol = searchParams.get("symbol")

    if (!symbol) {
      return NextResponse.json({ error: "Symbol parameter is required" }, { status: 400 })
    }

    const price = await marketDataAggregator.getPrice(symbol)

    return NextResponse.json({
      symbol,
      price,
      timestamp: new Date().toISOString(),
    })
  } catch (error) {
    logger.error("Price fetch failed", { error })
    return NextResponse.json({ error: "Failed to fetch price" }, { status: 500 })
  }
}

export const GET = withAuth(getPriceHandler)
