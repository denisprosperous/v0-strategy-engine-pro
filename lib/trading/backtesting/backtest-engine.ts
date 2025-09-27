// Comprehensive backtesting engine for strategy validation
import type { BaseStrategy } from "../strategies/base-strategy"
import type { MarketData, TradeSignal } from "@/lib/database/schema"
import { logger } from "@/lib/utils/logger"

export interface BacktestConfig {
  startDate: Date
  endDate: Date
  initialBalance: number
  commission: number // Percentage fee per trade
  slippage: number // Price slippage percentage
  maxPositions: number
  riskPerTrade: number
  symbols: string[]
}

export interface BacktestTrade {
  id: string
  symbol: string
  side: "buy" | "sell"
  entryPrice: number
  exitPrice: number
  quantity: number
  entryTime: Date
  exitTime: Date
  pnl: number
  fees: number
  reason: "take_profit" | "stop_loss" | "strategy_exit" | "end_of_test"
  signalStrength: number
}

export interface BacktestResults {
  trades: BacktestTrade[]
  performance: {
    totalTrades: number
    winningTrades: number
    losingTrades: number
    winRate: number
    totalPnL: number
    totalFees: number
    netPnL: number
    maxDrawdown: number
    maxDrawdownPercent: number
    sharpeRatio: number
    profitFactor: number
    avgWinningTrade: number
    avgLosingTrade: number
    largestWin: number
    largestLoss: number
    consecutiveWins: number
    consecutiveLosses: number
  }
  equity: Array<{ date: Date; balance: number; drawdown: number }>
  monthlyReturns: Array<{ month: string; return: number; trades: number }>
}

export class BacktestEngine {
  private strategy: BaseStrategy
  private config: BacktestConfig
  private currentBalance: number
  private peakBalance: number
  private trades: BacktestTrade[] = []
  private openPositions: Map<string, BacktestTrade> = new Map()
  private equityCurve: Array<{ date: Date; balance: number; drawdown: number }> = []

  constructor(strategy: BaseStrategy, config: BacktestConfig) {
    this.strategy = strategy
    this.config = config
    this.currentBalance = config.initialBalance
    this.peakBalance = config.initialBalance
  }

  async runBacktest(historicalData: MarketData[]): Promise<BacktestResults> {
    logger.info("Starting backtest", {
      strategy: this.strategy.getName(),
      startDate: this.config.startDate,
      endDate: this.config.endDate,
      dataPoints: historicalData.length,
    })

    // Reset state
    this.currentBalance = this.config.initialBalance
    this.peakBalance = this.config.initialBalance
    this.trades = []
    this.openPositions.clear()
    this.equityCurve = []

    // Sort data by timestamp
    const sortedData = historicalData.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())

    // Process each data point
    for (let i = 0; i < sortedData.length; i++) {
      const currentData = sortedData[i]
      const historicalSlice = sortedData.slice(0, i + 1)

      // Update strategy with new data
      this.strategy.onMarketData(currentData)

      // Check for exit signals on open positions
      await this.checkExitConditions(currentData)

      // Get market context
      const context = this.getMarketContext(historicalSlice)

      // Analyze for new signals
      const signal = this.strategy.analyze(historicalSlice, context)

      if (signal && this.shouldExecuteSignal(signal, currentData)) {
        await this.executeSignal(signal, currentData)
      }

      // Record equity curve
      this.recordEquity(currentData.timestamp)
    }

    // Close any remaining open positions
    await this.closeAllPositions(sortedData[sortedData.length - 1])

    // Calculate final results
    const results = this.calculateResults()

    logger.info("Backtest completed", {
      strategy: this.strategy.getName(),
      totalTrades: results.performance.totalTrades,
      winRate: results.performance.winRate,
      netPnL: results.performance.netPnL,
    })

    return results
  }

  private shouldExecuteSignal(signal: TradeSignal, currentData: MarketData): boolean {
    // Check if we have enough balance
    if (this.currentBalance < 100) return false

    // Check max positions limit
    if (this.openPositions.size >= this.config.maxPositions) return false

    // Check signal strength
    if (signal.strength < 0.6) return false

    // Check if we already have a position in this symbol
    if (this.openPositions.has(signal.symbol)) return false

    return true
  }

  private async executeSignal(signal: TradeSignal, currentData: MarketData): Promise<void> {
    try {
      // Calculate position size
      const positionSize = this.calculatePositionSize(signal, currentData.close)

      if (positionSize <= 0) return

      // Apply slippage
      const slippageAmount = currentData.close * this.config.slippage
      const executionPrice =
        signal.signal_type === "buy" ? currentData.close + slippageAmount : currentData.close - slippageAmount

      // Calculate fees
      const tradeValue = executionPrice * positionSize
      const fees = tradeValue * this.config.commission

      // Check if we have enough balance
      if (tradeValue + fees > this.currentBalance) return

      // Create trade record
      const trade: BacktestTrade = {
        id: `bt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        symbol: signal.symbol,
        side: signal.signal_type === "buy" ? "buy" : "sell",
        entryPrice: executionPrice,
        exitPrice: 0,
        quantity: positionSize,
        entryTime: currentData.timestamp,
        exitTime: new Date(),
        pnl: 0,
        fees,
        reason: "strategy_exit",
        signalStrength: signal.strength,
      }

      // Update balance
      this.currentBalance -= tradeValue + fees

      // Add to open positions
      this.openPositions.set(signal.symbol, trade)

      logger.debug("Backtest trade opened", {
        symbol: signal.symbol,
        side: signal.signal_type,
        price: executionPrice,
        quantity: positionSize,
      })
    } catch (error) {
      logger.error("Failed to execute backtest signal", { error, signal })
    }
  }

  private async checkExitConditions(currentData: MarketData): Promise<void> {
    const position = this.openPositions.get(currentData.symbol)
    if (!position) return

    const currentPrice = currentData.close
    let shouldExit = false
    let exitReason: BacktestTrade["reason"] = "strategy_exit"

    // Check stop loss
    if (position.side === "buy" && currentPrice <= position.entryPrice * 0.98) {
      shouldExit = true
      exitReason = "stop_loss"
    } else if (position.side === "sell" && currentPrice >= position.entryPrice * 1.02) {
      shouldExit = true
      exitReason = "stop_loss"
    }

    // Check take profit
    if (position.side === "buy" && currentPrice >= position.entryPrice * 1.05) {
      shouldExit = true
      exitReason = "take_profit"
    } else if (position.side === "sell" && currentPrice <= position.entryPrice * 0.95) {
      shouldExit = true
      exitReason = "take_profit"
    }

    if (shouldExit) {
      await this.closePosition(position, currentPrice, currentData.timestamp, exitReason)
    }
  }

  private async closePosition(
    position: BacktestTrade,
    exitPrice: number,
    exitTime: Date,
    reason: BacktestTrade["reason"],
  ): Promise<void> {
    // Apply slippage
    const slippageAmount = exitPrice * this.config.slippage
    const actualExitPrice = position.side === "buy" ? exitPrice - slippageAmount : exitPrice + slippageAmount

    // Calculate P&L
    const pnl = this.calculatePnL(position, actualExitPrice)

    // Calculate exit fees
    const exitFees = actualExitPrice * position.quantity * this.config.commission

    // Update trade record
    position.exitPrice = actualExitPrice
    position.exitTime = exitTime
    position.pnl = pnl - exitFees
    position.fees += exitFees
    position.reason = reason

    // Update balance
    const tradeValue = actualExitPrice * position.quantity
    this.currentBalance += tradeValue + position.pnl

    // Update peak balance for drawdown calculation
    if (this.currentBalance > this.peakBalance) {
      this.peakBalance = this.currentBalance
    }

    // Move to completed trades
    this.trades.push(position)
    this.openPositions.delete(position.symbol)

    logger.debug("Backtest trade closed", {
      symbol: position.symbol,
      pnl: position.pnl,
      reason,
    })
  }

  private async closeAllPositions(lastData: MarketData): Promise<void> {
    for (const [symbol, position] of this.openPositions) {
      await this.closePosition(position, lastData.close, lastData.timestamp, "end_of_test")
    }
  }

  private calculatePnL(position: BacktestTrade, exitPrice: number): number {
    const entryValue = position.entryPrice * position.quantity
    const exitValue = exitPrice * position.quantity

    if (position.side === "buy") {
      return exitValue - entryValue
    } else {
      return entryValue - exitValue
    }
  }

  private calculatePositionSize(signal: TradeSignal, currentPrice: number): number {
    // Risk-based position sizing
    const riskAmount = this.currentBalance * this.config.riskPerTrade
    const stopDistance = currentPrice * 0.02 // 2% stop loss
    const maxShares = riskAmount / stopDistance

    // Don't risk more than 10% of balance on a single trade
    const maxTradeValue = this.currentBalance * 0.1
    const maxSharesByValue = maxTradeValue / currentPrice

    return Math.min(maxShares, maxSharesByValue)
  }

  private getMarketContext(historicalData: MarketData[]): any {
    if (historicalData.length === 0) {
      return {
        currentPrice: 0,
        volume: 0,
        volatility: 0,
        trend: "sideways" as const,
      }
    }

    const latest = historicalData[historicalData.length - 1]
    const prices = historicalData.slice(-20).map((d) => d.close)

    return {
      currentPrice: latest.close,
      volume: latest.volume,
      volatility: this.calculateVolatility(prices),
      trend: this.determineTrend(prices),
    }
  }

  private calculateVolatility(prices: number[]): number {
    if (prices.length < 2) return 0

    const returns = []
    for (let i = 1; i < prices.length; i++) {
      returns.push((prices[i] - prices[i - 1]) / prices[i - 1])
    }

    const mean = returns.reduce((a, b) => a + b, 0) / returns.length
    const variance = returns.reduce((acc, ret) => acc + Math.pow(ret - mean, 2), 0) / returns.length

    return Math.sqrt(variance) * Math.sqrt(252) // Annualized volatility
  }

  private determineTrend(prices: number[]): "bullish" | "bearish" | "sideways" {
    if (prices.length < 10) return "sideways"

    const firstHalf = prices.slice(0, Math.floor(prices.length / 2))
    const secondHalf = prices.slice(Math.floor(prices.length / 2))

    const firstAvg = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length
    const secondAvg = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length

    const change = (secondAvg - firstAvg) / firstAvg

    if (change > 0.02) return "bullish"
    if (change < -0.02) return "bearish"
    return "sideways"
  }

  private recordEquity(date: Date): void {
    const drawdown = this.peakBalance > 0 ? (this.peakBalance - this.currentBalance) / this.peakBalance : 0

    this.equityCurve.push({
      date,
      balance: this.currentBalance,
      drawdown,
    })
  }

  private calculateResults(): BacktestResults {
    const winningTrades = this.trades.filter((t) => t.pnl > 0)
    const losingTrades = this.trades.filter((t) => t.pnl < 0)

    const totalPnL = this.trades.reduce((sum, t) => sum + t.pnl, 0)
    const totalFees = this.trades.reduce((sum, t) => sum + t.fees, 0)
    const netPnL = totalPnL - totalFees

    // Calculate drawdown
    const maxDrawdown = Math.max(...this.equityCurve.map((e) => e.drawdown))
    const maxDrawdownPercent = maxDrawdown * 100

    // Calculate Sharpe ratio (simplified)
    const returns = this.equityCurve.map((e, i) => {
      if (i === 0) return 0
      return (e.balance - this.equityCurve[i - 1].balance) / this.equityCurve[i - 1].balance
    })
    const avgReturn = returns.reduce((a, b) => a + b, 0) / returns.length
    const returnStdDev = Math.sqrt(returns.reduce((acc, ret) => acc + Math.pow(ret - avgReturn, 2), 0) / returns.length)
    const sharpeRatio = returnStdDev > 0 ? (avgReturn / returnStdDev) * Math.sqrt(252) : 0

    // Calculate profit factor
    const grossProfit = winningTrades.reduce((sum, t) => sum + t.pnl, 0)
    const grossLoss = Math.abs(losingTrades.reduce((sum, t) => sum + t.pnl, 0))
    const profitFactor = grossLoss > 0 ? grossProfit / grossLoss : 0

    // Calculate consecutive wins/losses
    let consecutiveWins = 0
    let consecutiveLosses = 0
    let currentWinStreak = 0
    let currentLossStreak = 0

    for (const trade of this.trades) {
      if (trade.pnl > 0) {
        currentWinStreak++
        currentLossStreak = 0
        consecutiveWins = Math.max(consecutiveWins, currentWinStreak)
      } else {
        currentLossStreak++
        currentWinStreak = 0
        consecutiveLosses = Math.max(consecutiveLosses, currentLossStreak)
      }
    }

    // Calculate monthly returns
    const monthlyReturns = this.calculateMonthlyReturns()

    return {
      trades: this.trades,
      performance: {
        totalTrades: this.trades.length,
        winningTrades: winningTrades.length,
        losingTrades: losingTrades.length,
        winRate: this.trades.length > 0 ? (winningTrades.length / this.trades.length) * 100 : 0,
        totalPnL,
        totalFees,
        netPnL,
        maxDrawdown: maxDrawdown * this.config.initialBalance,
        maxDrawdownPercent,
        sharpeRatio,
        profitFactor,
        avgWinningTrade: winningTrades.length > 0 ? grossProfit / winningTrades.length : 0,
        avgLosingTrade: losingTrades.length > 0 ? grossLoss / losingTrades.length : 0,
        largestWin: winningTrades.length > 0 ? Math.max(...winningTrades.map((t) => t.pnl)) : 0,
        largestLoss: losingTrades.length > 0 ? Math.min(...losingTrades.map((t) => t.pnl)) : 0,
        consecutiveWins,
        consecutiveLosses,
      },
      equity: this.equityCurve,
      monthlyReturns,
    }
  }

  private calculateMonthlyReturns(): Array<{ month: string; return: number; trades: number }> {
    const monthlyData = new Map<string, { startBalance: number; endBalance: number; trades: number }>()

    for (let i = 0; i < this.equityCurve.length; i++) {
      const point = this.equityCurve[i]
      const monthKey = `${point.date.getFullYear()}-${String(point.date.getMonth() + 1).padStart(2, "0")}`

      if (!monthlyData.has(monthKey)) {
        monthlyData.set(monthKey, {
          startBalance: i > 0 ? this.equityCurve[i - 1].balance : this.config.initialBalance,
          endBalance: point.balance,
          trades: 0,
        })
      } else {
        const data = monthlyData.get(monthKey)!
        data.endBalance = point.balance
      }
    }

    // Count trades per month
    for (const trade of this.trades) {
      const monthKey = `${trade.entryTime.getFullYear()}-${String(trade.entryTime.getMonth() + 1).padStart(2, "0")}`
      const data = monthlyData.get(monthKey)
      if (data) {
        data.trades++
      }
    }

    return Array.from(monthlyData.entries()).map(([month, data]) => ({
      month,
      return: data.startBalance > 0 ? ((data.endBalance - data.startBalance) / data.startBalance) * 100 : 0,
      trades: data.trades,
    }))
  }
}
