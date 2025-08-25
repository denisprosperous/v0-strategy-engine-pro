// Mean reversion trading strategy implementation
import { BaseStrategy, type StrategyConfig, type MarketContext } from "./base-strategy"
import type { MarketData, TradeSignal } from "@/lib/database/schema"

interface MeanReversionConfig extends StrategyConfig {
  rsiPeriod: number
  rsiOversold: number
  rsiOverbought: number
  bollingerPeriod: number
  bollingerStdDev: number
}

export class MeanReversionStrategy extends BaseStrategy {
  private config: MeanReversionConfig

  constructor(config: MeanReversionConfig) {
    super(config)
    this.config = config
  }

  getName(): string {
    return "Mean Reversion Strategy"
  }

  getDescription(): string {
    return "Trades based on RSI oversold/overbought conditions and Bollinger Band extremes"
  }

  analyze(marketData: MarketData[], context: MarketContext): TradeSignal | null {
    if (marketData.length < Math.max(this.config.rsiPeriod, this.config.bollingerPeriod)) {
      return null
    }

    const current = marketData[marketData.length - 1]
    const rsi = this.indicators.rsi || 50
    const bollinger = this.indicators.bollinger

    if (!bollinger) return null

    // Bullish mean reversion signal
    if (
      rsi < this.config.rsiOversold &&
      current.close < bollinger.lower &&
      context.trend !== "bearish" // Don't fight strong downtrends
    ) {
      const rsiStrength = (this.config.rsiOversold - rsi) / this.config.rsiOversold
      const bollingerStrength = (bollinger.lower - current.close) / (bollinger.middle - bollinger.lower)
      const strength = Math.min(rsiStrength * 0.6 + bollingerStrength * 0.4, 1.0)

      return {
        id: `mean_reversion_${Date.now()}`,
        strategy_id: "mean_reversion",
        symbol: current.symbol,
        signal_type: "buy",
        strength,
        price_target: bollinger.middle,
        stop_loss: current.close * (1 - this.config.stopLossPct),
        take_profit: current.close * (1 + this.config.takeProfitPct),
        reasoning: `Mean reversion buy: RSI ${rsi.toFixed(1)} oversold, price below lower Bollinger Band`,
        created_at: new Date(),
        executed: false,
      }
    }

    // Bearish mean reversion signal
    if (
      rsi > this.config.rsiOverbought &&
      current.close > bollinger.upper &&
      context.trend !== "bullish" // Don't fight strong uptrends
    ) {
      const rsiStrength = (rsi - this.config.rsiOverbought) / (100 - this.config.rsiOverbought)
      const bollingerStrength = (current.close - bollinger.upper) / (bollinger.upper - bollinger.middle)
      const strength = Math.min(rsiStrength * 0.6 + bollingerStrength * 0.4, 1.0)

      return {
        id: `mean_reversion_${Date.now()}`,
        strategy_id: "mean_reversion",
        symbol: current.symbol,
        signal_type: "sell",
        strength,
        price_target: bollinger.middle,
        stop_loss: current.close * (1 + this.config.stopLossPct),
        take_profit: current.close * (1 - this.config.takeProfitPct),
        reasoning: `Mean reversion sell: RSI ${rsi.toFixed(1)} overbought, price above upper Bollinger Band`,
        created_at: new Date(),
        executed: false,
      }
    }

    return null
  }
}
