import { NextResponse } from "next/server"
import { liveMarketService } from "@/lib/trading/services/live-market-service"

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const symbols = searchParams.get("symbols")?.split(",") || ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    const exchange = searchParams.get("exchange") || "binance"

    const marketData = await liveMarketService.getMultipleMarketData(symbols, exchange)

    return NextResponse.json({
      success: true,
      data: marketData,
      timestamp: Date.now(),
    })
  } catch (error) {
    console.error("Error fetching market prices:", error)
    return NextResponse.json({ success: false, error: "Failed to fetch market data" }, { status: 500 })
  }
}
