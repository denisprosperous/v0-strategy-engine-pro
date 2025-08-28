import { supabase } from "@/lib/config/database"
import { logger } from "@/lib/utils/logger"

export interface RiskMetrics {
  winRate: number
  avgWin: number
  avgLoss: number
  sharpeRatio: number
  maxDrawdown: number
  volatility: number
  correlationRisk: number
}

export interface PositionSizeRecommendation {
  recommendedSize: number
  maxSize: number
  riskScore: number
  kellyFraction: number
  confidenceLevel: number
  reasoning: string[]
}

export interface RiskLimits {
  maxDailyLoss: number
  maxPositionSize: number
  maxCorrelation: number
  maxVolatility: number
  maxDrawdown: number
  cooldownPeriod: number
}

export class AdaptiveRiskManager {
  private riskLimits: RiskLimits
  private currentMetrics: RiskMetrics
  private recentTrades: any[] = []

  constructor(limits: RiskLimits) {
    this.riskLimits = limits
    this.currentMetrics = this.initializeMetrics()
    this.loadRecentTrades()
  }

  async calculateOptimalPositionSize(
    signal: any,
    accountBalance: number,
    currentPositions: any[],
  ): Promise<PositionSizeRecommendation> {
    try {
      // Update metrics with recent performance
      await this.updateRiskMetrics()

      // Calculate Kelly Criterion position size
      const kellyFraction = this.calculateKellyFraction()

      // Apply risk adjustments
      const riskAdjustments = this.calculateRiskAdjustments(signal, currentPositions)

      // Calculate base position size
      const baseSize = accountBalance * kellyFraction * 0.5 // Use half-Kelly for safety

      // Apply all risk adjustments
      const adjustedSize = baseSize * riskAdjustments.totalAdjustment

      // Apply hard limits
      const finalSize = Math.min(
        adjustedSize,
        this.riskLimits.maxPositionSize,
        accountBalance * 0.1, // Never risk more than 10% on single trade
      )

      const recommendation: PositionSizeRecommendation = {
        recommendedSize: Math.max(0, finalSize),
        maxSize: this.riskLimits.maxPositionSize,
        riskScore: riskAdjustments.riskScore,
        kellyFraction,
        confidenceLevel: riskAdjustments.confidence,
        reasoning: riskAdjustments.reasoning,
      }

      logger.info("Position size calculated", {
        signal: signal.symbol,
        recommendedSize: recommendation.recommendedSize,
        riskScore: recommendation.riskScore,
      })

      return recommendation
    } catch (error) {
      logger.error("Position size calculation failed", { error })

      // Return conservative fallback
      return {
        recommendedSize: accountBalance * 0.01, // 1% fallback
        maxSize: this.riskLimits.maxPositionSize,
        riskScore: 0.8,
        kellyFraction: 0.02,
        confidenceLevel: 0.3,
        reasoning: ["Error in calculation, using conservative fallback"],
      }
    }
  }

  private calculateKellyFraction(): number {
    const { winRate, avgWin, avgLoss } = this.currentMetrics

    if (winRate <= 0 || avgWin <= 0 || avgLoss <= 0) {
      return 0.02 // Conservative default
    }

    // Kelly formula: f = (bp - q) / b
    // where b = odds (avgWin/avgLoss), p = win rate, q = loss rate
    const odds = avgWin / avgLoss
    const lossProbability = 1 - winRate

    const kellyFraction = (odds * winRate - lossProbability) / odds

    // Apply safety constraints
    return Math.max(0, Math.min(0.25, kellyFraction)) // Cap at 25%
  }

  private calculateRiskAdjustments(signal: any, currentPositions: any[]): any {
    const adjustments = {
      totalAdjustment: 1.0,
      riskScore: 0.5,
      confidence: 0.7,
      reasoning: [] as string[],
    }

    // Signal strength adjustment
    if (signal.strength > 80) {
      adjustments.totalAdjustment *= 1.2
      adjustments.reasoning.push("High signal strength (+20%)")
    } else if (signal.strength < 60) {
      adjustments.totalAdjustment *= 0.8
      adjustments.reasoning.push("Low signal strength (-20%)")
    }

    // Volatility adjustment
    if (this.currentMetrics.volatility > this.riskLimits.maxVolatility) {
      adjustments.totalAdjustment *= 0.7
      adjustments.riskScore += 0.2
      adjustments.reasoning.push("High market volatility (-30%)")
    }

    // Drawdown adjustment
    if (this.currentMetrics.maxDrawdown > this.riskLimits.maxDrawdown * 0.8) {
      adjustments.totalAdjustment *= 0.6
      adjustments.riskScore += 0.3
      adjustments.reasoning.push("Approaching max drawdown (-40%)")
    }

    // Correlation adjustment
    const correlationRisk = this.calculateCorrelationRisk(signal.symbol, currentPositions)
    if (correlationRisk > this.riskLimits.maxCorrelation) {
      adjustments.totalAdjustment *= 0.5
      adjustments.riskScore += 0.4
      adjustments.reasoning.push("High correlation risk (-50%)")
    }

    // Recent performance adjustment
    const recentPerformance = this.calculateRecentPerformance()
    if (recentPerformance < -0.1) {
      // Recent 10% loss
      adjustments.totalAdjustment *= 0.7
      adjustments.riskScore += 0.2
      adjustments.reasoning.push("Recent poor performance (-30%)")
    } else if (recentPerformance > 0.2) {
      // Recent 20% gain
      adjustments.totalAdjustment *= 1.1
      adjustments.reasoning.push("Recent strong performance (+10%)")
    }

    // Time-based adjustment (avoid overtrading)
    const timeSinceLastTrade = this.getTimeSinceLastTrade()
    if (timeSinceLastTrade < this.riskLimits.cooldownPeriod) {
      adjustments.totalAdjustment *= 0.5
      adjustments.riskScore += 0.3
      adjustments.reasoning.push("Cooldown period active (-50%)")
    }

    return adjustments
  }

  private calculateCorrelationRisk(symbol: string, currentPositions: any[]): number {
    // Simplified correlation calculation
    // In production, this would use actual correlation matrices
    const sameAssetPositions = currentPositions.filter((p) => p.symbol === symbol)
    const cryptoPositions = currentPositions.filter(
      (p) => p.symbol.includes("BTC") || p.symbol.includes("ETH") || p.symbol.includes("USDT"),
    )

    return Math.min(1, sameAssetPositions.length * 0.5 + cryptoPositions.length * 0.1)
  }

  private calculateRecentPerformance(): number {
    if (this.recentTrades.length === 0) return 0

    const recentTrades = this.recentTrades.slice(-10) // Last 10 trades
    const totalPnL = recentTrades.reduce((sum, trade) => sum + (trade.pnl || 0), 0)
    const totalInvested = recentTrades.reduce((sum, trade) => sum + (trade.invested_amount || 0), 0)

    return totalInvested > 0 ? totalPnL / totalInvested : 0
  }

  private getTimeSinceLastTrade(): number {
    if (this.recentTrades.length === 0) return Number.POSITIVE_INFINITY

    const lastTrade = this.recentTrades[this.recentTrades.length - 1]
    return Date.now() - new Date(lastTrade.created_at).getTime()
  }

  async updateRiskMetrics(): Promise<void> {
    try {
      // Fetch recent trades for metric calculation
      const { data: trades, error } = await supabase
        .from("trades")
        .select("*")
        .gte("created_at", new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString())
        .order("created_at", { ascending: false })

      if (error) throw error

      this.recentTrades = trades || []

      // Calculate updated metrics
      this.currentMetrics = this.calculateMetricsFromTrades(this.recentTrades)

      logger.info("Risk metrics updated", { metrics: this.currentMetrics })
    } catch (error) {
      logger.error("Failed to update risk metrics", { error })
    }
  }

  private calculateMetricsFromTrades(trades: any[]): RiskMetrics {
    if (trades.length === 0) {
      return this.initializeMetrics()
    }

    const completedTrades = trades.filter((t) => t.status === "closed")
    const winningTrades = completedTrades.filter((t) => (t.pnl || 0) > 0)
    const losingTrades = completedTrades.filter((t) => (t.pnl || 0) < 0)

    const winRate = completedTrades.length > 0 ? winningTrades.length / completedTrades.length : 0
    const avgWin =
      winningTrades.length > 0 ? winningTrades.reduce((sum, t) => sum + t.pnl, 0) / winningTrades.length : 0
    const avgLoss =
      losingTrades.length > 0 ? Math.abs(losingTrades.reduce((sum, t) => sum + t.pnl, 0) / losingTrades.length) : 0

    // Calculate returns for Sharpe ratio and volatility
    const returns = completedTrades.map((t) => (t.pnl || 0) / (t.invested_amount || 1))
    const avgReturn = returns.length > 0 ? returns.reduce((sum, r) => sum + r, 0) / returns.length : 0
    const returnVariance =
      returns.length > 0 ? returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length : 0
    const volatility = Math.sqrt(returnVariance)
    const sharpeRatio = volatility > 0 ? avgReturn / volatility : 0

    // Calculate max drawdown
    let maxDrawdown = 0
    let peak = 0
    let currentValue = 0

    for (const trade of completedTrades) {
      currentValue += trade.pnl || 0
      if (currentValue > peak) {
        peak = currentValue
      } else {
        const drawdown = (peak - currentValue) / peak
        maxDrawdown = Math.max(maxDrawdown, drawdown)
      }
    }

    return {
      winRate,
      avgWin,
      avgLoss,
      sharpeRatio,
      maxDrawdown,
      volatility,
      correlationRisk: 0.3, // Would be calculated from position correlations
    }
  }

  private initializeMetrics(): RiskMetrics {
    return {
      winRate: 0.6, // Default assumptions
      avgWin: 100,
      avgLoss: 50,
      sharpeRatio: 1.0,
      maxDrawdown: 0.05,
      volatility: 0.2,
      correlationRisk: 0.3,
    }
  }

  private async loadRecentTrades(): Promise<void> {
    try {
      const { data: trades, error } = await supabase
        .from("trades")
        .select("*")
        .gte("created_at", new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString())
        .order("created_at", { ascending: false })
        .limit(50)

      if (error) throw error

      this.recentTrades = trades || []
    } catch (error) {
      logger.error("Failed to load recent trades", { error })
    }
  }

  async checkRiskLimits(
    currentPositions: any[],
    dailyPnL: number,
  ): Promise<{
    withinLimits: boolean
    violations: string[]
    recommendations: string[]
  }> {
    const violations: string[] = []
    const recommendations: string[] = []

    // Check daily loss limit
    if (dailyPnL < -this.riskLimits.maxDailyLoss) {
      violations.push(`Daily loss limit exceeded: ${dailyPnL} < -${this.riskLimits.maxDailyLoss}`)
      recommendations.push("Stop trading for today")
    }

    // Check max drawdown
    if (this.currentMetrics.maxDrawdown > this.riskLimits.maxDrawdown) {
      violations.push(`Max drawdown exceeded: ${this.currentMetrics.maxDrawdown} > ${this.riskLimits.maxDrawdown}`)
      recommendations.push("Reduce position sizes and review strategy")
    }

    // Check position concentration
    const totalPositionValue = currentPositions.reduce((sum, p) => sum + (p.current_value || 0), 0)
    const largestPosition = Math.max(...currentPositions.map((p) => p.current_value || 0))

    if (largestPosition > totalPositionValue * 0.3) {
      violations.push("Position concentration too high")
      recommendations.push("Diversify positions")
    }

    return {
      withinLimits: violations.length === 0,
      violations,
      recommendations,
    }
  }
}
