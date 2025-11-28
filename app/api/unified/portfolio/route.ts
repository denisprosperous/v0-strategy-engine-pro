import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { pythonApiClient } from "@/lib/api/python-api-client"
import { db } from "@/lib/config/database"
import { liveMarketService } from "@/lib/trading/services/live-market-service"
import { brokerFactory } from "@/lib/trading/brokers/broker-factory"

async function getUnifiedPortfolioHandler(req: AuthenticatedRequest) {
  try {
    if (!req.user) {
      return NextResponse.json({ error: "User not authenticated" }, { status: 401 })
    }

    // Check Python backend availability
    const pythonAvailable = await pythonApiClient.isAvailable()

    // Get balances from Python backend if available
    let pythonBalances: any[] = []
    if (pythonAvailable) {
      const balanceResponse = await pythonApiClient.getPortfolioBalances()
      if (balanceResponse.success && balanceResponse.data) {
        pythonBalances = balanceResponse.data
      }
    }

    // Get balances directly from exchanges
    const exchangeBalances: Record<string, any[]> = {}
    const configuredExchanges = brokerFactory.getConfiguredExchanges()

    await Promise.all(
      configuredExchanges.map(async (exchange) => {
        try {
          const balance = await liveMarketService.getExchangeBalance(exchange)
          if (balance.length > 0) {
            exchangeBalances[exchange] = balance
          }
        } catch (error) {
          console.error(`Failed to get balance from ${exchange}:`, error)
        }
      }),
    )

    // Get trades from Redis database
    const trades = await db.getTrades(req.user.userId)
    const openTrades = trades.filter((t: any) => t.status === "open")
    const closedTrades = trades.filter((t: any) => t.status === "closed")

    // Calculate total portfolio value
    let totalValue = 0
    const allBalances: any[] = []

    // Add Python backend balances
    pythonBalances.forEach((balance) => {
      totalValue += balance.usd_value || 0
      allBalances.push({
        ...balance,
        source: "python_backend",
      })
    })

    // Add exchange balances
    for (const [exchange, balances] of Object.entries(exchangeBalances)) {
      for (const balance of balances) {
        // Get USD value for non-stablecoin assets
        let usdValue = balance.total
        if (!["USDT", "USDC", "BUSD", "DAI"].includes(balance.asset)) {
          try {
            const price = await liveMarketService.getPrice(`${balance.asset}USDT`, exchange)
            usdValue = balance.total * price
          } catch {
            usdValue = 0
          }
        }

        totalValue += usdValue
        allBalances.push({
          ...balance,
          usd_value: usdValue,
          source: exchange,
        })
      }
    }

    // Calculate PnL from closed trades
    const totalPnL = closedTrades.reduce((sum: number, t: any) => sum + Number.parseFloat(t.pnl || 0), 0)

    // Get performance metrics
    const winningTrades = closedTrades.filter((t: any) => Number.parseFloat(t.pnl || 0) > 0)
    const winRate = closedTrades.length > 0 ? (winningTrades.length / closedTrades.length) * 100 : 0

    return NextResponse.json({
      success: true,
      portfolio: {
        totalValue,
        totalPnL,
        pnlPercentage: totalValue > 0 ? (totalPnL / totalValue) * 100 : 0,
        balances: allBalances,
        openTrades: openTrades.length,
        closedTrades: closedTrades.length,
        winRate,
      },
      sources: {
        pythonBackend: pythonAvailable,
        exchanges: Object.keys(exchangeBalances),
        database: true,
      },
    })
  } catch (error) {
    console.error("Error getting unified portfolio:", error)
    return NextResponse.json({ error: "Failed to get portfolio data" }, { status: 500 })
  }
}

export const GET = withAuth(getUnifiedPortfolioHandler)
