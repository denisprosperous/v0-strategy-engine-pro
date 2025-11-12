// Breakout trading strategy implementation
import { BaseStrategy, type StrategyConfig, type MarketContext } from "./base-strategy"
import type { MarketData, TradeSignal } from "@/lib/database/schema"

interface BreakoutConfig extends StrategyConfig {
  volumeThreshold: number
  priceChangeThreshold: number
  lookbackPeriod: number
  atrMultiplierSL: number
  atrMultiplierTP: number
}

export class BreakoutStrategy extends BaseStrategy {
  private config: BreakoutConfig

  constructor(config: BreakoutConfig) {
    super(config)
    this.config = config
  }

  getName(): string {
    return "Breakout Strategy"
  }

  getDescription(): string {
    return "Identifies price breakouts above resistance or below support with volume confirmation"
  }

  analyze(marketData: MarketData[], context: MarketContext): TradeSignal | null {
    if (marketData.length < this.config.lookbackPeriod) {
      return null
    }

    const recent = marketData.slice(-this.config.lookbackPeriod)
    const current = marketData[marketData.length - 1]

    // Calculate support and resistance levels
    const highs = recent.map((d) => d.high)
    const lows = recent.map((d) => d.low)
    const volumes = recent.map((d) => d.volume)

    const resistance = Math.max(...highs)
    const support = Math.min(...lows)
    const avgVolume = volumes.reduce((a, b) => a + b, 0) / volumes.length

    // Check for breakout conditions
    const priceChange = (current.close - current.open) / current.open
    const volumeIncrease = current.volume / avgVolume

    // Gate by regime: prefer trending conditions
    if (!this.isTrending()) return null

    // Bullish breakout
    if (
      current.close > resistance &&
      priceChange > this.config.priceChangeThreshold &&
      volumeIncrease > this.config.volumeThreshold
    ) {
      const strength = Math.min(
        (priceChange / this.config.priceChangeThreshold) * 0.4 +
          (volumeIncrease / this.config.volumeThreshold) * 0.3 +
          (this.indicators.rsi ? ((this.indicators.rsi - 50) / 50) * 0.3 : 0),
        1.0,
      )

      const atr = this.indicators.atr || current.close * 0.01
      return {
        id: `breakout_${Date.now()}`,
        strategy_id: "breakout",
        symbol: current.symbol,
        signal_type: "buy",
        strength,
        price_target: current.close + atr * this.config.atrMultiplierTP,
        stop_loss: current.close - atr * this.config.atrMultiplierSL,
        take_profit: current.close + atr * this.config.atrMultiplierTP,
        reasoning: `Bullish breakout above resistance ${resistance.toFixed(4)} with ${volumeIncrease.toFixed(1)}x volume`,
        created_at: new Date(),
        executed: false,
      }
    }

    // Bearish breakout (breakdown)
    if (
      current.close < support &&
      priceChange < -this.config.priceChangeThreshold &&
      volumeIncrease > this.config.volumeThreshold
    ) {
      const strength = Math.min(
        (Math.abs(priceChange) / this.config.priceChangeThreshold) * 0.4 +
          (volumeIncrease / this.config.volumeThreshold) * 0.3 +
          (this.indicators.rsi ? ((50 - this.indicators.rsi) / 50) * 0.3 : 0),
        1.0,
      )

      const atr = this.indicators.atr || current.close * 0.01
      return {
        id: `breakout_${Date.now()}`,
        strategy_id: "breakout",
        symbol: current.symbol,
        signal_type: "sell",
        strength,
        price_target: current.close - atr * this.config.atrMultiplierTP,
        stop_loss: current.close + atr * this.config.atrMultiplierSL,
        take_profit: current.close - atr * this.config.atrMultiplierTP,
        reasoning: `Bearish breakdown below support ${support.toFixed(4)} with ${volumeIncrease.toFixed(1)}x volume`,
        created_at: new Date(),
        executed: false,
      }
    }

    return null
  }
}
