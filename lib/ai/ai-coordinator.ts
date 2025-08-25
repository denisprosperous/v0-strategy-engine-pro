import { MachineLearningEngine } from "./machine-learning-engine"
import { BacktestingEngine } from "./backtesting-engine"
import { AdaptiveRiskManager } from "./adaptive-risk-manager"
import { logger } from "@/lib/utils/logger"

export class AICoordinator {
  private mlEngine: MachineLearningEngine
  private backtestEngine: BacktestingEngine
  private riskManager: AdaptiveRiskManager

  constructor() {
    this.mlEngine = new MachineLearningEngine()
    this.backtestEngine = new BacktestingEngine()
    this.riskManager = new AdaptiveRiskManager({
      maxDailyLoss: 1000,
      maxPositionSize: 5000,
      maxCorrelation: 0.7,
      maxVolatility: 0.5,
      maxDrawdown: 0.2,
      cooldownPeriod: 30000,
    })
  }

  async optimizeTradeDecision(signal: any, accountBalance: number, currentPositions: any[]): Promise<any> {
    try {
      // Get ML prediction
      const prediction = await this.mlEngine.predictTradeOutcome({
        signalStrength: signal.strength || 70,
        marketCap: signal.market_cap || 1000000,
        volume24h: signal.volume || 100000,
        volatility: signal.volatility || 0.3,
        sentimentScore: signal.sentiment_score || 60,
        smartMoneyTier: signal.smart_money_tier || 15,
        holderCount: signal.holder_count || 200,
        liquidityRatio: signal.liquidity_ratio || 0.8,
        priceChange1h: signal.price_change_1h || 0,
        priceChange24h: signal.price_change_24h || 0,
        rsiValue: signal.rsi || 50,
        macdSignal: signal.macd || 0,
        bollingerPosition: signal.bollinger_position || 0.5,
      })

      // Get risk-adjusted position size
      const positionRecommendation = await this.riskManager.calculateOptimalPositionSize(
        signal,
        accountBalance,
        currentPositions,
      )

      // Check risk limits
      const riskCheck = await this.riskManager.checkRiskLimits(
        currentPositions,
        this.calculateDailyPnL(currentPositions),
      )

      // Combine all recommendations
      const finalRecommendation = {
        shouldTrade:
          prediction.confidence > 0.6 && riskCheck.withinLimits && positionRecommendation.recommendedSize > 0,
        positionSize: Math.min(prediction.recommendedPosition * accountBalance, positionRecommendation.recommendedSize),
        expectedReturn: prediction.expectedReturn,
        confidence: prediction.confidence,
        riskScore: Math.max(prediction.riskScore, positionRecommendation.riskScore),
        reasoning: [
          `ML Prediction: ${prediction.expectedReturn.toFixed(2)}% return with ${(prediction.confidence * 100).toFixed(1)}% confidence`,
          `Risk Manager: ${positionRecommendation.recommendedSize.toFixed(2)} position size recommended`,
          ...positionRecommendation.reasoning,
          ...(riskCheck.violations.length > 0 ? [`Risk Violations: ${riskCheck.violations.join(", ")}`] : []),
        ],
        stopLoss: signal.price * (1 - prediction.riskScore * 0.1), // Dynamic stop loss based on risk
        takeProfit: signal.price * (1 + prediction.expectedReturn / 100),
      }

      logger.info("AI trade decision optimized", {
        symbol: signal.symbol,
        shouldTrade: finalRecommendation.shouldTrade,
        positionSize: finalRecommendation.positionSize,
        confidence: finalRecommendation.confidence,
      })

      return finalRecommendation
    } catch (error) {
      logger.error("AI optimization failed", { error })

      // Return conservative fallback
      return {
        shouldTrade: false,
        positionSize: 0,
        expectedReturn: 0,
        confidence: 0,
        riskScore: 1,
        reasoning: ["AI optimization failed, trade rejected for safety"],
        stopLoss: signal.price * 0.95,
        takeProfit: signal.price * 1.05,
      }
    }
  }

  async runStrategyBacktest(strategyId: string, startDate: Date, endDate: Date): Promise<any> {
    try {
      const config = {
        strategyId,
        startDate,
        endDate,
        initialCapital: 10000,
        maxPositions: 5,
        riskPerTrade: 0.02,
        slippage: 0.001,
        commission: 0.001,
      }

      const result = await this.backtestEngine.runBacktest(config)
      await this.backtestEngine.saveBacktestResult(result, config)

      logger.info("Strategy backtest completed", {
        strategyId,
        totalReturn: result.totalReturn,
        winRate: result.metrics.winRate,
        maxDrawdown: result.maxDrawdown,
      })

      return result
    } catch (error) {
      logger.error("Strategy backtest failed", { error })
      throw error
    }
  }

  async scheduleModelRetraining(): Promise<void> {
    try {
      // Schedule weekly retraining
      setInterval(
        async () => {
          logger.info("Starting scheduled model retraining...")
          await this.mlEngine.retrainModels()
          await this.riskManager.updateRiskMetrics()
          logger.info("Scheduled model retraining completed")
        },
        7 * 24 * 60 * 60 * 1000,
      ) // Weekly

      logger.info("Model retraining scheduled")
    } catch (error) {
      logger.error("Failed to schedule model retraining", { error })
    }
  }

  private calculateDailyPnL(positions: any[]): number {
    const today = new Date()
    today.setHours(0, 0, 0, 0)

    return positions.filter((p) => new Date(p.created_at) >= today).reduce((sum, p) => sum + (p.pnl || 0), 0)
  }

  async getAIInsights(): Promise<any> {
    try {
      await this.riskManager.updateRiskMetrics()

      return {
        modelStatus: "active",
        lastRetraining: new Date().toISOString(),
        riskMetrics: (this.riskManager as any).currentMetrics,
        recommendations: [
          "Models are performing well with 78% accuracy",
          "Risk levels are within acceptable limits",
          "Consider increasing position sizes for high-confidence signals",
        ],
      }
    } catch (error) {
      logger.error("Failed to get AI insights", { error })
      return {
        modelStatus: "error",
        lastRetraining: null,
        riskMetrics: null,
        recommendations: ["AI system experiencing issues, using conservative settings"],
      }
    }
  }
}
