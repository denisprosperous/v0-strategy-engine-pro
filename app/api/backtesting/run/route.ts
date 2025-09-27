// API endpoint to run backtests
import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { BacktestEngine } from "@/lib/trading/backtesting/backtest-engine"
import { supabase } from "@/lib/config/database"
import { logger } from "@/lib/utils/logger"

interface BacktestRequest {
  strategyId: string
  startDate: string
  endDate: string
  initialBalance: number
  symbols: string[]
  commission?: number
  slippage?: number
  maxPositions?: number
  riskPerTrade?: number
}

async function runBacktestHandler(req: AuthenticatedRequest) {
  try {
    if (!req.user) {
      return NextResponse.json({ error: "User not authenticated" }, { status: 401 })
    }

    const body: BacktestRequest = await req.json()
    const {
      strategyId,
      startDate,
      endDate,
      initialBalance,
      symbols,
      commission = 0.001, // 0.1% default
      slippage = 0.0005, // 0.05% default
      maxPositions = 5,
      riskPerTrade = 0.02, // 2% default
    } = body

    // Validate input
    if (!strategyId || !startDate || !endDate || !initialBalance || !symbols?.length) {
      return NextResponse.json({ error: "Missing required parameters" }, { status: 400 })
    }

    // Get strategy configuration
    const { data: strategy, error: strategyError } = await supabase
      .from("strategies")
      .select("*")
      .eq("id", strategyId)
      .eq("created_by", req.user.userId)
      .single()

    if (strategyError || !strategy) {
      return NextResponse.json({ error: "Strategy not found" }, { status: 404 })
    }

    // Get historical market data
    const { data: marketData, error: dataError } = await supabase
      .from("market_data")
      .select("*")
      .in("symbol", symbols)
      .gte("timestamp", startDate)
      .lte("timestamp", endDate)
      .order("timestamp", { ascending: true })

    if (dataError) {
      throw dataError
    }

    if (!marketData || marketData.length === 0) {
      return NextResponse.json({ error: "No historical data found for the specified period" }, { status: 404 })
    }

    // Create backtest configuration
    const backtestConfig = {
      startDate: new Date(startDate),
      endDate: new Date(endDate),
      initialBalance,
      commission,
      slippage,
      maxPositions,
      riskPerTrade,
      symbols,
    }

    // Create strategy instance (simplified - in production, you'd instantiate the actual strategy class)
    const strategyInstance = {
      getName: () => strategy.name,
      getDescription: () => strategy.description,
      analyze: () => null, // Simplified for demo
      onMarketData: () => {},
      onTrade: () => {},
    } as any

    // Run backtest
    const backtestEngine = new BacktestEngine(strategyInstance, backtestConfig)
    const results = await backtestEngine.runBacktest(marketData)

    // Save backtest results
    const { data: savedBacktest, error: saveError } = await supabase
      .from("backtests")
      .insert({
        user_id: req.user.userId,
        strategy_id: strategyId,
        config: backtestConfig,
        results,
        created_at: new Date().toISOString(),
      })
      .select()
      .single()

    if (saveError) {
      logger.error("Failed to save backtest results", { saveError })
      // Continue anyway - we can still return the results
    }

    logger.info("Backtest completed", {
      userId: req.user.userId,
      strategyId,
      totalTrades: results.performance.totalTrades,
      winRate: results.performance.winRate,
      netPnL: results.performance.netPnL,
    })

    return NextResponse.json({
      success: true,
      backtest: {
        id: savedBacktest?.id,
        results,
        config: backtestConfig,
      },
    })
  } catch (error) {
    logger.error("Backtest execution failed", { error, userId: req.user?.userId })
    return NextResponse.json({ error: "Backtest execution failed" }, { status: 500 })
  }
}

export const POST = withAuth(runBacktestHandler)
