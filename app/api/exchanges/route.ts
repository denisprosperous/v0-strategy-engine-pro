import type { NextRequest } from "next/server"
import { ExchangeManager, type ExchangeConfig } from "@/lib/trading/exchange/exchange-manager"

// Global exchange managers per user
const userExchangeManagers = new Map<string, ExchangeManager>()

export async function GET(request: NextRequest) {
  try {
    const userId = "user_123" // In real app, get from authentication
    const searchParams = request.nextUrl.searchParams
    const action = searchParams.get("action")

    let exchangeManager = userExchangeManagers.get(userId)
    if (!exchangeManager) {
      exchangeManager = new ExchangeManager(userId)
      userExchangeManagers.set(userId, exchangeManager)
    }

    switch (action) {
      case "status":
        const statuses = exchangeManager.getAllExchangeStatuses()
        return Response.json({
          success: true,
          exchanges: statuses,
          connected: exchangeManager.getConnectedExchanges(),
        })

      case "balance":
        const aggregatedBalance = await exchangeManager.getAggregatedBalance()
        return Response.json({
          success: true,
          balance: aggregatedBalance,
        })

      case "best_price":
        const symbol = searchParams.get("symbol")
        const side = searchParams.get("side") as "buy" | "sell"

        if (!symbol || !side) {
          return Response.json({ error: "Symbol and side are required" }, { status: 400 })
        }

        const bestPrice = await exchangeManager.getBestPrice(symbol, side)
        return Response.json({
          success: true,
          bestPrice,
        })

      default:
        return Response.json({
          success: true,
          exchanges: exchangeManager.getConnectedExchanges(),
        })
    }
  } catch (error) {
    console.error("[v0] Error in exchanges API:", error)
    return Response.json(
      {
        error: "Exchange operation failed",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 },
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const userId = "user_123" // In real app, get from authentication
    const { action, ...data } = await request.json()

    let exchangeManager = userExchangeManagers.get(userId)
    if (!exchangeManager) {
      exchangeManager = new ExchangeManager(userId)
      userExchangeManagers.set(userId, exchangeManager)
    }

    switch (action) {
      case "initialize":
        const { exchanges } = data
        await exchangeManager.initialize(exchanges)
        return Response.json({
          success: true,
          message: "Exchange manager initialized",
        })

      case "add_exchange":
        const { config } = data as { config: ExchangeConfig }
        await exchangeManager.addExchange(config)
        return Response.json({
          success: true,
          message: `Exchange ${config.name} added successfully`,
        })

      case "remove_exchange":
        const { exchangeName } = data
        await exchangeManager.removeExchange(exchangeName)
        return Response.json({
          success: true,
          message: `Exchange ${exchangeName} removed successfully`,
        })

      case "execute_order":
        const { exchangeName: orderExchange, order } = data
        const result = await exchangeManager.executeOrder(orderExchange, order)
        return Response.json({
          success: true,
          order: result,
          message: "Order executed successfully",
        })

      case "execute_arbitrage":
        const { symbol, buyExchange, sellExchange, quantity } = data
        const arbitrageResult = await exchangeManager.executeArbitrage(symbol, buyExchange, sellExchange, quantity)
        return Response.json({
          success: true,
          result: arbitrageResult,
          message: "Arbitrage executed successfully",
        })

      default:
        return Response.json(
          {
            error: "Invalid action",
          },
          { status: 400 },
        )
    }
  } catch (error) {
    console.error("[v0] Error in exchanges API:", error)
    return Response.json(
      {
        error: "Exchange operation failed",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 },
    )
  }
}
