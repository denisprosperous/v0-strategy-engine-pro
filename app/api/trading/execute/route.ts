// API endpoint for manual trade execution
import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { BinanceBroker } from "@/lib/trading/brokers/binance-broker"
import { config } from "@/lib/config/environment"
import { supabaseServer } from "@/lib/config/supabase-server"
import { logger } from "@/lib/utils/logger"

interface TradeRequest {
  symbol: string
  side: "buy" | "sell"
  amount: number
  stopLoss?: number
  takeProfit?: number
  orderType?: "market" | "limit"
  price?: number
}

async function executeTradeHandler(req: AuthenticatedRequest) {
  try {
    const body: TradeRequest = await req.json()
    const { symbol, side, amount, stopLoss, takeProfit, orderType = "market", price } = body

    if (!req.user) {
      return NextResponse.json({ error: "User not authenticated" }, { status: 401 })
    }

    // Validate input
    if (!symbol || !side || !amount || amount <= 0) {
      return NextResponse.json({ error: "Invalid trade parameters" }, { status: 400 })
    }

    // Get user's API keys
    const { data: user, error: userError } = await supabaseServer
      .from("users")
      .select("api_keys, settings")
      .eq("id", req.user.userId)
      .single()

    if (userError || !user) {
      return NextResponse.json({ error: "User not found" }, { status: 404 })
    }

    if (!user.api_keys?.binance?.key || !user.api_keys?.binance?.secret) {
      return NextResponse.json({ error: "Binance API keys not configured" }, { status: 400 })
    }

    // Initialize broker with user's API keys
    const broker = new BinanceBroker(user.api_keys.binance.key, user.api_keys.binance.secret, config.binance.testnet)

    await broker.connect()

    try {
      // Check user's balance
      const balances = await broker.getBalance()
      const baseAsset = symbol.replace(/USDT|BUSD|USD$/, "")
      const quoteAsset = symbol.replace(baseAsset, "")

      const relevantBalance =
        side === "buy" ? balances.find((b) => b.asset === quoteAsset) : balances.find((b) => b.asset === baseAsset)

      if (!relevantBalance || relevantBalance.free < amount) {
        return NextResponse.json({ error: "Insufficient balance" }, { status: 400 })
      }

      // Check daily loss limit
      const today = new Date().toISOString().split("T")[0]
      const { data: todayTrades } = await supabaseServer
        .from("trades")
        .select("pnl")
        .eq("user_id", req.user.userId)
        .gte("execution_time", `${today}T00:00:00Z`)
        .not("pnl", "is", null)

      const dailyPnL = todayTrades?.reduce((sum, trade) => sum + (trade.pnl || 0), 0) || 0
      const maxDailyLoss = user.settings?.max_daily_loss || config.risk.maxDailyLoss

      if (dailyPnL < -maxDailyLoss) {
        return NextResponse.json({ error: "Daily loss limit exceeded" }, { status: 403 })
      }

      // Execute the trade
      const order = await broker.placeOrder({
        symbol,
        side,
        type: orderType,
        quantity: amount,
        ...(price && { price }),
      })

      // Create trade record
      const trade = {
        user_id: req.user.userId,
        symbol,
        side,
        entry_price: order.executedPrice || order.price,
        quantity: order.executedQuantity,
        stop_loss: stopLoss,
        take_profit: takeProfit,
        status: order.status === "filled" ? "open" : "pending",
        fees: order.fees,
        execution_time: new Date().toISOString(),
        broker: "binance",
        metadata: {
          order_id: order.orderId,
          manual_trade: true,
        },
      }

      const { data: savedTrade, error: tradeError } = await supabaseServer
        .from("trades")
        .insert(trade)
        .select()
        .single()

      if (tradeError) {
        logger.error("Failed to save trade to database", { tradeError, trade })
        // Trade was executed but not saved - this needs manual intervention
      }

      logger.info("Manual trade executed", {
        userId: req.user.userId,
        trade: savedTrade,
        order,
      })

      return NextResponse.json({
        success: true,
        trade: savedTrade,
        order: {
          orderId: order.orderId,
          status: order.status,
          executedQuantity: order.executedQuantity,
          executedPrice: order.executedPrice,
        },
      })
    } finally {
      await broker.disconnect()
    }
  } catch (error) {
    logger.error("Trade execution failed", { error, userId: req.user?.userId })
    return NextResponse.json({ error: "Trade execution failed" }, { status: 500 })
  }
}

export const POST = withAuth(executeTradeHandler)
