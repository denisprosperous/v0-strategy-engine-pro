import { supabase } from "@/lib/config/database"
import { logger } from "@/lib/utils/logger"

export interface BacktestConfig {
  strategyId: string
  startDate: Date
  endDate: Date
  initialCapital: number
  maxPositions: number
  riskPerTrade: number
  slippage: number
  commission: number
}

export interface BacktestResult {
  totalReturn: number
  annualizedReturn: number
  maxDrawdown: number
  sharpeRatio: number
  winRate: number
  totalTrades: number
  avgTradeReturn: number
  profitFactor: number
  equityCurve: { date: Date; value: number }[]
  trades: BacktestTrade[]
  metrics: BacktestMetrics
}

export interface BacktestTrade {
  entryDate: Date
  exitDate: Date
  symbol: string
  side: "buy" | "sell"
  entryPrice: number
  exitPrice: number
  quantity: number
  pnl: number
  pnlPercent: number
  holdingPeriod: number
  exitReason: string
}

export interface BacktestMetrics {
  totalTrades: number
  winningTrades: number
  losingTrades: number
  winRate: number
  avgWin: number
  avgLoss: number
  largestWin: number
  largestLoss: number
  consecutiveWins: number
  consecutiveLosses: number
  profitFactor: number
  recoveryFactor: number
  calmarRatio: number
}

export class BacktestingEngine {
  private historicalData: Map<string, any[]> = new Map()

  async runBacktest(config: BacktestConfig): Promise<BacktestResult> {
    try {
      logger.info("Starting backtest", { config })

      // Load historical data
      await this.loadHistoricalData(config.startDate, config.endDate)

      // Initialize backtest state
      const state = this.initializeBacktestState(config)

      // Run simulation
      const result = await this.simulateStrategy(config, state)

      // Calculate metrics
      const metrics = this.calculateMetrics(result.trades)

      // Generate equity curve
      const equityCurve = this.generateEquityCurve(result.trades, config.initialCapital)

      logger.info("Backtest completed", {
        totalReturn: result.totalReturn,
        winRate: metrics.winRate,
        maxDrawdown: result.maxDrawdown,
      })

      return {
        ...result,
        metrics,
        equityCurve,
      }
    } catch (error) {
      logger.error("Backtest failed", { error })
      throw error
    }
  }

  private async loadHistoricalData(startDate: Date, endDate: Date): Promise<void> {
    try {
      // In production, this would load from a time-series database
      // For now, we'll simulate historical data
      const symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT"]

      for (const symbol of symbols) {
        const data = this.generateMockHistoricalData(symbol, startDate, endDate)
        this.historicalData.set(symbol, data)
      }

      logger.info("Historical data loaded", {
        symbols: symbols.length,
        dateRange: { startDate, endDate },
      })
    } catch (error) {
      logger.error("Failed to load historical data", { error })
      throw error
    }
  }

  private generateMockHistoricalData(symbol: string, startDate: Date, endDate: Date): any[] {
    const data = []
    const currentDate = new Date(startDate)
    let price = 100 // Starting price

    while (currentDate <= endDate) {
      // Generate realistic price movement
      const change = (Math.random() - 0.5) * 0.1 // ±5% max change
      price *= 1 + change

      const volume = Math.random() * 1000000 + 100000

      data.push({
        timestamp: new Date(currentDate),
        open: price * (1 + (Math.random() - 0.5) * 0.02),
        high: price * (1 + Math.random() * 0.03),
        low: price * (1 - Math.random() * 0.03),
        close: price,
        volume,
        symbol,
      })

      currentDate.setHours(currentDate.getHours() + 1) // Hourly data
    }

    return data
  }

  private initializeBacktestState(config: BacktestConfig): any {
    return {
      capital: config.initialCapital,
      positions: new Map(),
      trades: [],
      currentDate: new Date(config.startDate),
      maxCapital: config.initialCapital,
      drawdown: 0,
      maxDrawdown: 0,
    }
  }

  private async simulateStrategy(config: BacktestConfig, state: any): Promise<any> {
    const trades: BacktestTrade[] = []
    let totalReturn = 0

    // Get strategy signals for the backtest period
    const signals = await this.getStrategySignals(config.strategyId, config.startDate, config.endDate)

    for (const signal of signals) {
      // Check if we can open a new position
      if (state.positions.size >= config.maxPositions) continue

      // Calculate position size
      const positionSize = this.calculatePositionSize(state.capital, signal.price, config.riskPerTrade, signal.stopLoss)

      // Simulate trade execution
      const trade = await this.simulateTrade(signal, positionSize, config)

      if (trade) {
        trades.push(trade)

        // Update state
        state.capital += trade.pnl
        totalReturn += trade.pnlPercent

        // Update drawdown
        if (state.capital > state.maxCapital) {
          state.maxCapital = state.capital
          state.drawdown = 0
        } else {
          state.drawdown = (state.maxCapital - state.capital) / state.maxCapital
          state.maxDrawdown = Math.max(state.maxDrawdown, state.drawdown)
        }
      }
    }

    return {
      totalReturn: (state.capital - config.initialCapital) / config.initialCapital,
      maxDrawdown: state.maxDrawdown,
      trades,
    }
  }

  private async getStrategySignals(strategyId: string, startDate: Date, endDate: Date): Promise<any[]> {
    // In production, this would fetch actual strategy signals from the database
    // For now, we'll generate mock signals
    const signals = []
    const currentDate = new Date(startDate)

    while (currentDate <= endDate) {
      // Generate random signals (about 1 per day)
      if (Math.random() < 0.04) {
        // 4% chance per hour = ~1 signal per day
        const symbol = ["BTCUSDT", "ETHUSDT", "SOLUSDT"][Math.floor(Math.random() * 3)]
        const historicalData = this.historicalData.get(symbol)

        if (historicalData) {
          const dataPoint = historicalData.find(
            (d) => Math.abs(d.timestamp.getTime() - currentDate.getTime()) < 60 * 60 * 1000,
          )

          if (dataPoint) {
            signals.push({
              timestamp: new Date(currentDate),
              symbol,
              side: Math.random() > 0.5 ? "buy" : "sell",
              price: dataPoint.close,
              stopLoss: dataPoint.close * (Math.random() > 0.5 ? 0.95 : 1.05),
              takeProfit: dataPoint.close * (Math.random() > 0.5 ? 1.1 : 0.9),
              strength: Math.random() * 100,
            })
          }
        }
      }

      currentDate.setHours(currentDate.getHours() + 1)
    }

    return signals
  }

  private async simulateTrade(
    signal: any,
    positionSize: number,
    config: BacktestConfig,
  ): Promise<BacktestTrade | null> {
    try {
      const historicalData = this.historicalData.get(signal.symbol)
      if (!historicalData) return null

      const entryIndex = historicalData.findIndex((d) => d.timestamp.getTime() >= signal.timestamp.getTime())

      if (entryIndex === -1) return null

      const entryData = historicalData[entryIndex]
      const entryPrice = entryData.close * (1 + config.slippage) // Apply slippage

      // Simulate holding period and exit
      let exitIndex = entryIndex + 1
      let exitReason = "time_limit"
      let exitPrice = entryPrice

      // Look for exit conditions
      for (let i = entryIndex + 1; i < Math.min(entryIndex + 168, historicalData.length); i++) {
        // Max 1 week hold
        const currentData = historicalData[i]

        // Check stop loss
        if (signal.side === "buy" && currentData.low <= signal.stopLoss) {
          exitIndex = i
          exitPrice = signal.stopLoss
          exitReason = "stop_loss"
          break
        }

        // Check take profit
        if (signal.side === "buy" && currentData.high >= signal.takeProfit) {
          exitIndex = i
          exitPrice = signal.takeProfit
          exitReason = "take_profit"
          break
        }
      }

      // If no exit condition met, exit at current price
      if (exitReason === "time_limit") {
        exitPrice = historicalData[exitIndex].close
      }

      // Apply slippage and commission
      exitPrice *= 1 - config.slippage
      const commission = (entryPrice + exitPrice) * positionSize * config.commission

      // Calculate P&L
      const pnl =
        signal.side === "buy"
          ? (exitPrice - entryPrice) * positionSize - commission
          : (entryPrice - exitPrice) * positionSize - commission

      const pnlPercent = pnl / (entryPrice * positionSize)

      return {
        entryDate: entryData.timestamp,
        exitDate: historicalData[exitIndex].timestamp,
        symbol: signal.symbol,
        side: signal.side,
        entryPrice,
        exitPrice,
        quantity: positionSize,
        pnl,
        pnlPercent,
        holdingPeriod: exitIndex - entryIndex,
        exitReason,
      }
    } catch (error) {
      logger.error("Trade simulation failed", { error, signal })
      return null
    }
  }

  private calculatePositionSize(capital: number, price: number, riskPerTrade: number, stopLoss: number): number {
    const riskAmount = capital * riskPerTrade
    const stopDistance = Math.abs(price - stopLoss)
    return Math.min(riskAmount / stopDistance, (capital * 0.1) / price) // Max 10% of capital
  }

  private calculateMetrics(trades: BacktestTrade[]): BacktestMetrics {
    if (trades.length === 0) {
      return {
        totalTrades: 0,
        winningTrades: 0,
        losingTrades: 0,
        winRate: 0,
        avgWin: 0,
        avgLoss: 0,
        largestWin: 0,
        largestLoss: 0,
        consecutiveWins: 0,
        consecutiveLosses: 0,
        profitFactor: 0,
        recoveryFactor: 0,
        calmarRatio: 0,
      }
    }

    const winningTrades = trades.filter((t) => t.pnl > 0)
    const losingTrades = trades.filter((t) => t.pnl < 0)

    const totalWins = winningTrades.reduce((sum, t) => sum + t.pnl, 0)
    const totalLosses = Math.abs(losingTrades.reduce((sum, t) => sum + t.pnl, 0))

    return {
      totalTrades: trades.length,
      winningTrades: winningTrades.length,
      losingTrades: losingTrades.length,
      winRate: winningTrades.length / trades.length,
      avgWin: winningTrades.length > 0 ? totalWins / winningTrades.length : 0,
      avgLoss: losingTrades.length > 0 ? totalLosses / losingTrades.length : 0,
      largestWin: Math.max(...trades.map((t) => t.pnl)),
      largestLoss: Math.min(...trades.map((t) => t.pnl)),
      consecutiveWins: this.calculateMaxConsecutive(trades, true),
      consecutiveLosses: this.calculateMaxConsecutive(trades, false),
      profitFactor: totalLosses > 0 ? totalWins / totalLosses : 0,
      recoveryFactor: 0, // Would need drawdown data
      calmarRatio: 0, // Would need annualized return and max drawdown
    }
  }

  private calculateMaxConsecutive(trades: BacktestTrade[], winning: boolean): number {
    let maxConsecutive = 0
    let currentConsecutive = 0

    for (const trade of trades) {
      if ((winning && trade.pnl > 0) || (!winning && trade.pnl < 0)) {
        currentConsecutive++
        maxConsecutive = Math.max(maxConsecutive, currentConsecutive)
      } else {
        currentConsecutive = 0
      }
    }

    return maxConsecutive
  }

  private generateEquityCurve(trades: BacktestTrade[], initialCapital: number): { date: Date; value: number }[] {
    const curve = [{ date: trades[0]?.entryDate || new Date(), value: initialCapital }]
    let currentValue = initialCapital

    for (const trade of trades) {
      currentValue += trade.pnl
      curve.push({ date: trade.exitDate, value: currentValue })
    }

    return curve
  }

  async saveBacktestResult(result: BacktestResult, config: BacktestConfig): Promise<void> {
    try {
      await supabase.from("backtest_results").insert({
        strategy_id: config.strategyId,
        config: config,
        result: result,
        created_at: new Date().toISOString(),
      })

      logger.info("Backtest result saved", { strategyId: config.strategyId })
    } catch (error) {
      logger.error("Failed to save backtest result", { error })
    }
  }
}
