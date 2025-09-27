// Advanced Fibonacci strategy with machine learning enhancements
import { BaseStrategy, type StrategyConfig, type MarketContext } from "./base-strategy"
import type { MarketData, TradeSignal } from "@/lib/database/schema"
import { logger } from "@/lib/utils/logger"

interface FibonacciMLConfig extends StrategyConfig {
  fibonacciLevels: number[]
  lookbackPeriod: number
  minPatternStrength: number
  adaptiveSizing: boolean
  mlModelEnabled: boolean
  sentimentWeight: number
  volatilityAdjustment: boolean
}

interface FibonacciLevel {
  level: number
  price: number
  strength: number
  type: "support" | "resistance"
}

interface PatternFeatures {
  trendStrength: number
  volatility: number
  volume: number
  fibonacciAlignment: number
  sentimentScore: number
  timeOfDay: number
  dayOfWeek: number
  marketRegime: "trending" | "ranging" | "volatile"
}

interface MLPrediction {
  probability: number
  confidence: number
  expectedReturn: number
  riskScore: number
}

export class FibonacciMLStrategy extends BaseStrategy {
  private config: FibonacciMLConfig
  private fibonacciLevels: FibonacciLevel[] = []
  private patternHistory: PatternFeatures[] = []
  private modelWeights: Map<string, number> = new Map()
  private adaptiveParameters: Map<string, number> = new Map()
  private performanceMetrics: {
    totalTrades: number
    winRate: number
    avgReturn: number
    sharpeRatio: number
  } = { totalTrades: 0, winRate: 0, avgReturn: 0, sharpeRatio: 0 }

  constructor(config: FibonacciMLConfig) {
    super(config)
    this.config = {
      fibonacciLevels: [0.236, 0.382, 0.5, 0.618, 0.786],
      lookbackPeriod: 50,
      minPatternStrength: 0.7,
      adaptiveSizing: true,
      mlModelEnabled: true,
      sentimentWeight: 0.3,
      volatilityAdjustment: true,
      ...config,
    }
    this.initializeMLModel()
  }

  getName(): string {
    return "Fibonacci ML Strategy"
  }

  getDescription(): string {
    return "Advanced Fibonacci retracement strategy with machine learning enhancements, adaptive position sizing, and pattern recognition"
  }

  analyze(marketData: MarketData[], context: MarketContext): TradeSignal | null {
    if (marketData.length < this.config.lookbackPeriod) {
      return null
    }

    try {
      // Calculate Fibonacci levels
      this.calculateFibonacciLevels(marketData)

      // Extract pattern features
      const features = this.extractPatternFeatures(marketData, context)

      // Get ML prediction if enabled
      let mlPrediction: MLPrediction | null = null
      if (this.config.mlModelEnabled) {
        mlPrediction = this.getMachineLearningPrediction(features)
      }

      // Analyze Fibonacci patterns
      const fibonacciSignal = this.analyzeFibonacciPatterns(marketData, context)

      if (!fibonacciSignal) return null

      // Enhance signal with ML insights
      const enhancedSignal = this.enhanceSignalWithML(fibonacciSignal, mlPrediction, features)

      // Apply adaptive position sizing
      if (this.config.adaptiveSizing) {
        enhancedSignal.quantity = this.calculateAdaptivePositionSize(enhancedSignal, features, context)
      }

      // Update pattern history for learning
      this.updatePatternHistory(features)

      return enhancedSignal
    } catch (error) {
      logger.error("Error in Fibonacci ML strategy analysis", { error })
      return null
    }
  }

  private initializeMLModel(): void {
    // Initialize model weights with default values
    this.modelWeights.set("trendStrength", 0.25)
    this.modelWeights.set("volatility", 0.15)
    this.modelWeights.set("volume", 0.1)
    this.modelWeights.set("fibonacciAlignment", 0.3)
    this.modelWeights.set("sentimentScore", this.config.sentimentWeight)
    this.modelWeights.set("timeOfDay", 0.05)
    this.modelWeights.set("dayOfWeek", 0.05)
    this.modelWeights.set("marketRegime", 0.1)

    // Initialize adaptive parameters
    this.adaptiveParameters.set("stopLossMultiplier", 1.0)
    this.adaptiveParameters.set("takeProfitMultiplier", 1.0)
    this.adaptiveParameters.set("positionSizeMultiplier", 1.0)
    this.adaptiveParameters.set("minPatternStrength", this.config.minPatternStrength)

    logger.info("Fibonacci ML model initialized", {
      weights: Object.fromEntries(this.modelWeights),
      parameters: Object.fromEntries(this.adaptiveParameters),
    })
  }

  private calculateFibonacciLevels(marketData: MarketData[]): void {
    const recentData = marketData.slice(-this.config.lookbackPeriod)
    const high = Math.max(...recentData.map((d) => d.high))
    const low = Math.min(...recentData.map((d) => d.low))
    const range = high - low

    this.fibonacciLevels = this.config.fibonacciLevels.map((level) => {
      const price = high - range * level
      const strength = this.calculateLevelStrength(price, recentData)
      const type = this.determineLevelType(price, recentData)

      return {
        level,
        price,
        strength,
        type,
      }
    })

    // Sort by strength
    this.fibonacciLevels.sort((a, b) => b.strength - a.strength)
  }

  private calculateLevelStrength(price: number, data: MarketData[]): number {
    let touchCount = 0
    let bounceCount = 0
    const tolerance = price * 0.005 // 0.5% tolerance

    for (let i = 1; i < data.length; i++) {
      const current = data[i]
      const previous = data[i - 1]

      // Check if price touched the level
      if (
        (current.low <= price + tolerance && current.low >= price - tolerance) ||
        (current.high <= price + tolerance && current.high >= price - tolerance)
      ) {
        touchCount++

        // Check if it bounced
        if ((previous.close < price && current.close > price) || (previous.close > price && current.close < price)) {
          bounceCount++
        }
      }
    }

    // Strength based on touch count and bounce rate
    const bounceRate = touchCount > 0 ? bounceCount / touchCount : 0
    return Math.min(1.0, touchCount * 0.1 + bounceRate * 0.9)
  }

  private determineLevelType(price: number, data: MarketData[]): "support" | "resistance" {
    const currentPrice = data[data.length - 1].close
    const recentPrices = data.slice(-10).map((d) => d.close)
    const avgPrice = recentPrices.reduce((a, b) => a + b, 0) / recentPrices.length

    return price < avgPrice ? "support" : "resistance"
  }

  private extractPatternFeatures(marketData: MarketData[], context: MarketContext): PatternFeatures {
    const recentData = marketData.slice(-20)
    const prices = recentData.map((d) => d.close)
    const volumes = recentData.map((d) => d.volume)

    // Calculate trend strength
    const trendStrength = this.calculateTrendStrength(prices)

    // Calculate volatility
    const volatility = this.calculateVolatility(prices, 20)

    // Calculate volume profile
    const avgVolume = volumes.reduce((a, b) => a + b, 0) / volumes.length
    const currentVolume = volumes[volumes.length - 1]
    const volumeRatio = avgVolume > 0 ? currentVolume / avgVolume : 1

    // Calculate Fibonacci alignment
    const fibonacciAlignment = this.calculateFibonacciAlignment(context.currentPrice)

    // Time-based features
    const now = new Date()
    const timeOfDay = now.getHours() / 24 // Normalized to 0-1
    const dayOfWeek = now.getDay() / 7 // Normalized to 0-1

    // Market regime detection
    const marketRegime = this.detectMarketRegime(prices, volatility)

    return {
      trendStrength,
      volatility,
      volume: volumeRatio,
      fibonacciAlignment,
      sentimentScore: context.sentimentScore || 0,
      timeOfDay,
      dayOfWeek,
      marketRegime,
    }
  }

  private calculateTrendStrength(prices: number[]): number {
    if (prices.length < 10) return 0

    const shortEMA = this.calculateEMA(prices, 5)
    const longEMA = this.calculateEMA(prices, 20)

    // Trend strength based on EMA separation and slope
    const separation = Math.abs(shortEMA - longEMA) / longEMA
    const slope = this.calculateSlope(prices.slice(-10))

    return Math.min(1.0, separation * 10 + Math.abs(slope) * 100)
  }

  private calculateSlope(prices: number[]): number {
    if (prices.length < 2) return 0

    const n = prices.length
    const sumX = (n * (n - 1)) / 2
    const sumY = prices.reduce((a, b) => a + b, 0)
    const sumXY = prices.reduce((sum, price, index) => sum + index * price, 0)
    const sumX2 = prices.reduce((sum, _, index) => sum + index * index, 0)

    return (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX)
  }

  private calculateFibonacciAlignment(currentPrice: number): number {
    if (this.fibonacciLevels.length === 0) return 0

    // Find the closest Fibonacci level
    let minDistance = Number.POSITIVE_INFINITY
    let closestLevel: FibonacciLevel | null = null

    for (const level of this.fibonacciLevels) {
      const distance = Math.abs(currentPrice - level.price) / currentPrice
      if (distance < minDistance) {
        minDistance = distance
        closestLevel = level
      }
    }

    if (!closestLevel) return 0

    // Alignment score based on distance and level strength
    const distanceScore = Math.max(0, 1 - minDistance * 100) // Closer = higher score
    return distanceScore * closestLevel.strength
  }

  private detectMarketRegime(prices: number[], volatility: number): "trending" | "ranging" | "volatile" {
    const trendStrength = this.calculateTrendStrength(prices)

    if (volatility > 0.3) return "volatile"
    if (trendStrength > 0.6) return "trending"
    return "ranging"
  }

  private getMachineLearningPrediction(features: PatternFeatures): MLPrediction {
    // Simple linear model for demonstration
    // In production, this would use a trained ML model
    let score = 0
    let confidence = 0

    // Calculate weighted score
    score += features.trendStrength * (this.modelWeights.get("trendStrength") || 0)
    score += (1 - features.volatility) * (this.modelWeights.get("volatility") || 0) // Lower volatility is better
    score += Math.min(features.volume, 2) * (this.modelWeights.get("volume") || 0) // Cap volume impact
    score += features.fibonacciAlignment * (this.modelWeights.get("fibonacciAlignment") || 0)
    score += features.sentimentScore * (this.modelWeights.get("sentimentScore") || 0)

    // Time-based adjustments
    const timeWeight = this.modelWeights.get("timeOfDay") || 0
    const dayWeight = this.modelWeights.get("dayOfWeek") || 0

    // Prefer trading during active hours (9 AM - 4 PM UTC)
    const activeHours = features.timeOfDay >= 0.375 && features.timeOfDay <= 0.667 ? 1 : 0.5
    score += activeHours * timeWeight

    // Prefer weekdays over weekends
    const weekdayBonus = features.dayOfWeek >= 0.143 && features.dayOfWeek <= 0.714 ? 1 : 0.3
    score += weekdayBonus * dayWeight

    // Market regime adjustment
    const regimeWeight = this.modelWeights.get("marketRegime") || 0
    const regimeScore = features.marketRegime === "trending" ? 1 : features.marketRegime === "ranging" ? 0.7 : 0.3
    score += regimeScore * regimeWeight

    // Calculate confidence based on feature consistency
    confidence = this.calculatePredictionConfidence(features)

    // Calculate expected return and risk
    const expectedReturn = score * 0.02 // 2% max expected return
    const riskScore = features.volatility * (1 - confidence)

    return {
      probability: Math.max(0, Math.min(1, score)),
      confidence,
      expectedReturn,
      riskScore,
    }
  }

  private calculatePredictionConfidence(features: PatternFeatures): number {
    // Confidence based on feature alignment and historical performance
    let confidence = 0.5 // Base confidence

    // Higher confidence with strong Fibonacci alignment
    confidence += features.fibonacciAlignment * 0.3

    // Higher confidence with clear trend
    confidence += features.trendStrength * 0.2

    // Lower confidence with high volatility
    confidence -= features.volatility * 0.2

    // Adjust based on historical performance
    if (this.performanceMetrics.totalTrades > 10) {
      const performanceBonus = (this.performanceMetrics.winRate - 0.5) * 0.3
      confidence += performanceBonus
    }

    return Math.max(0.1, Math.min(0.95, confidence))
  }

  private analyzeFibonacciPatterns(marketData: MarketData[], context: MarketContext): TradeSignal | null {
    const currentPrice = context.currentPrice
    const strongLevels = this.fibonacciLevels.filter((level) => level.strength > 0.5)

    if (strongLevels.length === 0) return null

    // Find the most relevant level
    const relevantLevel = strongLevels.find((level) => {
      const distance = Math.abs(currentPrice - level.price) / currentPrice
      return distance < 0.01 // Within 1% of the level
    })

    if (!relevantLevel) return null

    // Determine signal direction
    const signalType = this.determineSignalDirection(relevantLevel, currentPrice, context)
    if (!signalType) return null

    // Calculate stop loss and take profit
    const { stopLoss, takeProfit } = this.calculateExitLevels(currentPrice, signalType, relevantLevel)

    // Calculate signal strength
    const strength = this.calculateSignalStrength(relevantLevel, context)

    if (strength < this.adaptiveParameters.get("minPatternStrength")!) {
      return null
    }

    return {
      id: `fib_ml_${Date.now()}`,
      strategy_id: "fibonacci-ml",
      symbol: marketData[marketData.length - 1].symbol,
      signal_type: signalType,
      strength,
      price_target: signalType === "buy" ? takeProfit : stopLoss,
      stop_loss: stopLoss,
      take_profit: takeProfit,
      reasoning: `Fibonacci ${relevantLevel.type} at ${relevantLevel.level} level (${relevantLevel.price.toFixed(2)}) with strength ${relevantLevel.strength.toFixed(2)}`,
      created_at: new Date(),
      executed: false,
    }
  }

  private determineSignalDirection(
    level: FibonacciLevel,
    currentPrice: number,
    context: MarketContext,
  ): "buy" | "sell" | null {
    const isNearSupport = level.type === "support" && currentPrice <= level.price * 1.005
    const isNearResistance = level.type === "resistance" && currentPrice >= level.price * 0.995

    // Consider trend direction
    const trendDirection = context.trend || "sideways"

    if (isNearSupport && (trendDirection === "bullish" || trendDirection === "sideways")) {
      return "buy"
    }

    if (isNearResistance && (trendDirection === "bearish" || trendDirection === "sideways")) {
      return "sell"
    }

    return null
  }

  private calculateExitLevels(
    currentPrice: number,
    signalType: "buy" | "sell",
    level: FibonacciLevel,
  ): { stopLoss: number; takeProfit: number } {
    const stopLossMultiplier = this.adaptiveParameters.get("stopLossMultiplier") || 1.0
    const takeProfitMultiplier = this.adaptiveParameters.get("takeProfitMultiplier") || 1.0

    let stopLoss: number
    let takeProfit: number

    if (signalType === "buy") {
      // Stop loss below the Fibonacci level
      stopLoss = level.price * (1 - 0.01 * stopLossMultiplier)
      // Take profit at next Fibonacci level or 2:1 risk-reward
      const riskDistance = currentPrice - stopLoss
      takeProfit = currentPrice + riskDistance * 2 * takeProfitMultiplier
    } else {
      // Stop loss above the Fibonacci level
      stopLoss = level.price * (1 + 0.01 * stopLossMultiplier)
      // Take profit at next Fibonacci level or 2:1 risk-reward
      const riskDistance = stopLoss - currentPrice
      takeProfit = currentPrice - riskDistance * 2 * takeProfitMultiplier
    }

    return { stopLoss, takeProfit }
  }

  private calculateSignalStrength(level: FibonacciLevel, context: MarketContext): number {
    let strength = level.strength

    // Boost strength with volume confirmation
    if (context.volume > this.indicators.volume! * 1.2) {
      strength *= 1.2
    }

    // Boost strength with trend alignment
    if (context.trend === "bullish" && level.type === "support") {
      strength *= 1.1
    } else if (context.trend === "bearish" && level.type === "resistance") {
      strength *= 1.1
    }

    // Reduce strength in high volatility
    if (this.indicators.volatility! > 0.3) {
      strength *= 0.8
    }

    return Math.min(1.0, strength)
  }

  private enhanceSignalWithML(
    signal: TradeSignal,
    mlPrediction: MLPrediction | null,
    features: PatternFeatures,
  ): TradeSignal {
    if (!mlPrediction) return signal

    // Adjust signal strength with ML confidence
    signal.strength = (signal.strength + mlPrediction.probability * mlPrediction.confidence) / 2

    // Adjust reasoning with ML insights
    signal.reasoning += ` | ML Prediction: ${(mlPrediction.probability * 100).toFixed(1)}% confidence, Expected Return: ${(mlPrediction.expectedReturn * 100).toFixed(2)}%`

    return signal
  }

  private calculateAdaptivePositionSize(
    signal: TradeSignal,
    features: PatternFeatures,
    context: MarketContext,
  ): number {
    const baseSize = this.calculatePositionSize(10000, context.currentPrice) // Assuming $10k balance
    const sizeMultiplier = this.adaptiveParameters.get("positionSizeMultiplier") || 1.0

    let adjustedSize = baseSize * sizeMultiplier

    // Reduce size in high volatility
    if (features.volatility > 0.3) {
      adjustedSize *= 0.7
    }

    // Increase size with high confidence
    if (signal.strength > 0.8) {
      adjustedSize *= 1.2
    }

    // Reduce size during off-hours
    if (features.timeOfDay < 0.375 || features.timeOfDay > 0.667) {
      adjustedSize *= 0.8
    }

    return Math.max(0.01, adjustedSize)
  }

  private updatePatternHistory(features: PatternFeatures): void {
    this.patternHistory.push(features)

    // Keep only last 1000 patterns
    if (this.patternHistory.length > 1000) {
      this.patternHistory = this.patternHistory.slice(-1000)
    }
  }

  onTrade(signal: TradeSignal, executed: boolean): void {
    if (executed) {
      this.performanceMetrics.totalTrades++

      // Update adaptive parameters based on performance
      this.updateAdaptiveParameters(signal)

      // Retrain model weights if we have enough data
      if (this.performanceMetrics.totalTrades % 50 === 0) {
        this.retrainModelWeights()
      }
    }

    logger.info("Fibonacci ML strategy trade feedback", {
      signal: signal.id,
      executed,
      totalTrades: this.performanceMetrics.totalTrades,
    })
  }

  private updateAdaptiveParameters(signal: TradeSignal): void {
    // This would be enhanced with actual trade outcome data
    // For now, we'll simulate parameter adaptation

    const currentStrength = this.adaptiveParameters.get("minPatternStrength")!

    // If signal strength was high, we can be more selective
    if (signal.strength > 0.9) {
      this.adaptiveParameters.set("minPatternStrength", Math.min(0.9, currentStrength + 0.01))
    } else if (signal.strength < 0.6) {
      this.adaptiveParameters.set("minPatternStrength", Math.max(0.5, currentStrength - 0.01))
    }

    logger.debug("Updated adaptive parameters", {
      parameters: Object.fromEntries(this.adaptiveParameters),
    })
  }

  private retrainModelWeights(): void {
    // Simplified model retraining based on recent performance
    // In production, this would use proper ML training algorithms

    if (this.patternHistory.length < 100) return

    const recentPatterns = this.patternHistory.slice(-100)

    // Analyze which features correlate with successful patterns
    // This is a simplified version - real implementation would be more sophisticated

    const avgTrendStrength = recentPatterns.reduce((sum, p) => sum + p.trendStrength, 0) / recentPatterns.length
    const avgFibAlignment = recentPatterns.reduce((sum, p) => sum + p.fibonacciAlignment, 0) / recentPatterns.length

    // Adjust weights based on feature importance
    if (avgTrendStrength > 0.7) {
      this.modelWeights.set("trendStrength", Math.min(0.4, this.modelWeights.get("trendStrength")! + 0.05))
    }

    if (avgFibAlignment > 0.6) {
      this.modelWeights.set("fibonacciAlignment", Math.min(0.4, this.modelWeights.get("fibonacciAlignment")! + 0.05))
    }

    logger.info("Model weights retrained", {
      weights: Object.fromEntries(this.modelWeights),
      patternsAnalyzed: recentPatterns.length,
    })
  }

  // Public method to get strategy insights
  getStrategyInsights(): any {
    return {
      fibonacciLevels: this.fibonacciLevels,
      modelWeights: Object.fromEntries(this.modelWeights),
      adaptiveParameters: Object.fromEntries(this.adaptiveParameters),
      performanceMetrics: this.performanceMetrics,
      patternHistorySize: this.patternHistory.length,
    }
  }
}
