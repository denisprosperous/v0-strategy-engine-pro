import type { NextRequest } from "next/server"
import { wsManager } from "@/lib/trading/data/websocket-manager"

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const action = searchParams.get("action")
  const exchange = searchParams.get("exchange")
  const symbol = searchParams.get("symbol")
  const channel = searchParams.get("channel")

  if (!exchange || !symbol) {
    return Response.json({ error: "Exchange and symbol are required" }, { status: 400 })
  }

  try {
    switch (action) {
      case "connect":
        const wsUrls = {
          binance: "wss://stream.binance.com:9443/ws",
          bitget: "wss://ws.bitget.com/spot/v1/stream",
        }

        const url = wsUrls[exchange as keyof typeof wsUrls]
        if (!url) {
          return Response.json({ error: "Unsupported exchange" }, { status: 400 })
        }

        await wsManager.connect(exchange, url)
        return Response.json({ success: true, message: `Connected to ${exchange}` })

      case "subscribe":
        if (!channel) {
          return Response.json({ error: "Channel is required for subscription" }, { status: 400 })
        }
        wsManager.subscribe(exchange, channel, symbol)
        return Response.json({ success: true, message: `Subscribed to ${channel} for ${symbol}` })

      case "unsubscribe":
        if (!channel) {
          return Response.json({ error: "Channel is required for unsubscription" }, { status: 400 })
        }
        wsManager.unsubscribe(exchange, channel, symbol)
        return Response.json({ success: true, message: `Unsubscribed from ${channel} for ${symbol}` })

      case "disconnect":
        wsManager.disconnect(exchange)
        return Response.json({ success: true, message: `Disconnected from ${exchange}` })

      case "status":
        const isConnected = wsManager.isConnected(exchange)
        return Response.json({ connected: isConnected, exchange })

      default:
        return Response.json({ error: "Invalid action" }, { status: 400 })
    }
  } catch (error) {
    console.error("[v0] WebSocket API error:", error)
    return Response.json(
      {
        error: "Internal server error",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 },
    )
  }
}
