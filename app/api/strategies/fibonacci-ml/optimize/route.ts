// API endpoint for Fibonacci ML strategy optimization
import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { FibonacciMLStrategy } from "@/lib/trading/strategies/fibonacci-ml-strategy"
import { BacktestEngine } from "@/lib/trading/backtesting/backtest-engine"
import { supabase } from "@/lib/config/database"
import { logger } from "@/lib/utils/logger"

interface OptimizationRequest {
  symbol: string
  startDate: string
  endDate: string
  optimizationTargets: string[] // ['winRate', 'sharpeRatio', 'maxDrawdown']
  parameterRanges: {
    lookbackPeriod: [number, number]
    minPatternStrength: [number, number]
    sentimentWeight: [number, number]
  }
}

async function optimizeStrategyHandler(req: AuthenticatedRequest) {
  try {
    if (!req.user) {
      return NextResponse.json({ error: "User not authenticated" }, { status: 401 })
    }

    const body: OptimizationRequest = await req.json()
    const { symbol, startDate, endDate, optimizationTargets, parameterRanges } = body

    // Get historical data
    const { data: marketData, error: dataError } = await supabase
      .from("market_data")
      .select("*")
      .eq("symbol", symbol)
      .gte("timestamp", startDate)
      .lte("timestamp", endDate)
      .order("timestamp", { ascending: true })

    if (dataError || !marketData?.length) {
      return NextResponse.json({ error: "No historical data found" }, { status: 404 })
    }

    // Parameter optimization using grid search
    const optimizationResults = await runParameterOptimization(marketData, parameterRanges, optimizationTargets)

    // Save optimization results
    const { data: savedOptimization, error: saveError } = await supabase
      .from("strategy_optimizations")
      .insert({
        user_id: req.user.userId,
        strategy_type: "fibonacci-ml",
        symbol,
        optimization_config: {
          startDate,
          endDate,
          targets: optimizationTargets,
          parameterRanges,
        },
        results: optimizationResults,
        created_at: new Date().toISOString(),
      })
      .select()
      .single()

    if (saveError) {
      logger.error("Failed to save optimization results", { saveError })
    }

    logger.info("Strategy optimization completed", {
      userId: req.user.userId,
      symbol,
      bestParameters: optimizationResults.bestParameters,
      bestScore: optimizationResults.bestScore,
    })

    return NextResponse.json({
      success: true,
      optimization: {
        id: savedOptimization?.id,
        results: optimizationResults,
      },
    })
  } catch (error) {
    logger.error("Strategy optimization failed", { error, userId: req.user?.userId })
    return NextResponse.json({ error: "Strategy optimization failed" }, { status: 500 })
  }
}

async function runParameterOptimization(
  marketData: any[],
  parameterRanges: OptimizationRequest["parameterRanges"],
  targets: string[],
): Promise<any> {
  const results: any[] = []
  let bestScore = Number.NEGATIVE_INFINITY
  let bestParameters: any = null

  // Grid search parameters
  const lookbackPeriods = generateRange(parameterRanges.lookbackPeriod[0], parameterRanges.lookbackPeriod[1], 5)
  const patternStrengths = generateRange(
    parameterRanges.minPatternStrength[0],
    parameterRanges.minPatternStrength[1],
    5,
  )
  const sentimentWeights = generateRange(parameterRanges.sentimentWeight[0], parameterRanges.sentimentWeight[1], 5)

  for (const lookbackPeriod of lookbackPeriods) {
    for (const minPatternStrength of patternStrengths) {
      for (const sentimentWeight of sentimentWeights) {
        try {
          // Create strategy with current parameters
          const strategy = new FibonacciMLStrategy({
            timeframe: "1h",
            maxPositions: 3,
            stopLossPct: 0.02,
            takeProfitPct: 0.04,
            lookbackPeriod,
            minPatternStrength,
            sentimentWeight,
            adaptiveSizing: true,
            mlModelEnabled: true,
            volatilityAdjustment: true,
            fibonacciLevels: [0.236, 0.382, 0.5, 0.618, 0.786],
          })

          // Run backtest
          const backtestConfig = {
            startDate: new Date(marketData[0].timestamp),
            endDate: new Date(marketData[marketData.length - 1].timestamp),
            initialBalance: 10000,
            commission: 0.001,
            slippage: 0.0005,
            maxPositions: 3,
            riskPerTrade: 0.02,
            symbols: [marketData[0].symbol],
          }

          const backtestEngine = new BacktestEngine(strategy, backtestConfig)
          const backtestResults = await backtestEngine.runBacktest(marketData)

          // Calculate optimization score
          const score = calculateOptimizationScore(backtestResults.performance, targets)

          const result = {
            parameters: {
              lookbackPeriod,
              minPatternStrength,
              sentimentWeight,
            },
            performance: backtestResults.performance,
            score,
          }

          results.push(result)

          if (score > bestScore) {
            bestScore = score
            bestParameters = result.parameters
          }
        } catch (error) {
          logger.error("Error in parameter combination", { error, lookbackPeriod, minPatternStrength, sentimentWeight })
        }
      }
    }
  }

  return {
    bestParameters,
    bestScore,
    allResults: results.sort((a, b) => b.score - a.score).slice(0, 20), // Top 20 results
    totalCombinations: results.length,
  }
}

function generateRange(min: number, max: number, steps: number): number[] {
  const range: number[] = []
  const stepSize = (max - min) / (steps - 1)

  for (let i = 0; i < steps; i++) {
    range.push(min + i * stepSize)
  }

  return range
}

function calculateOptimizationScore(performance: any, targets: string[]): number {
  let score = 0
  const weights = {
    winRate: 0.3,
    sharpeRatio: 0.3,
    netPnL: 0.2,
    maxDrawdown: 0.2,
  }

  for (const target of targets) {
    switch (target) {
      case "winRate":
        score += (performance.winRate / 100) * weights.winRate
        break
      case "sharpeRatio":
        score += Math.max(0, Math.min(1, performance.sharpeRatio / 2)) * weights.sharpeRatio
        break
      case "netPnL":
        score += Math.max(0, Math.min(1, performance.netPnL / 5000)) * weights.netPnL
        break
      case "maxDrawdown":
        score += Math.max(0, 1 - performance.maxDrawdownPercent / 50) * weights.maxDrawdown
        break
    }
  }

  return score
}

export const POST = withAuth(optimizeStrategyHandler)
