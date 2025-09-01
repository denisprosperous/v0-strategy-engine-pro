// Momentum strategy with ADX gating and ATR risk
import { BaseStrategy, type StrategyConfig, type MarketContext } from "./base-strategy"
import type { MarketData, TradeSignal } from "@/lib/database/schema"

interface MomentumConfig extends StrategyConfig {
  emaFastPeriod: number
  emaSlowPeriod: number
  adxThreshold: number
  atrMultiplierSL: number
  atrMultiplierTP: number
}

export class MomentumStrategy extends BaseStrategy {
  private config: MomentumConfig

  constructor(config: MomentumConfig) {
    super(config)
    this.config = config
  }

  getName(): string {
    return "Momentum Strategy"
  }

  getDescription(): string {
    return "Trades in direction of trend when ADX confirms momentum and EMAs align"
  }

  analyze(marketData: MarketData[], context: MarketContext): TradeSignal | null {
    if (marketData.length < Math.max(this.config.emaFastPeriod, this.config.emaSlowPeriod)) return null
    const current = marketData[marketData.length - 1]

    const adx = this.indicators.adx || 0
    const emaFast = this.indicators.emaFast || current.close
    const emaSlow = this.indicators.emaSlow || current.close

    if (adx < this.config.adxThreshold) return null

    const atr = this.indicators.atr || current.close * 0.01

    // Long when fast above slow and price above fast
    if (emaFast > emaSlow && current.close > emaFast) {
      const strength = Math.min(1, ((adx - this.config.adxThreshold) / 25) * 0.5 + 0.5)
      return {
        id: `momentum_${Date.now()}`,
        strategy_id: "momentum",
        symbol: current.symbol,
        signal_type: "buy",
        strength,
        price_target: current.close + atr * this.config.atrMultiplierTP,
        stop_loss: current.close - atr * this.config.atrMultiplierSL,
        take_profit: current.close + atr * this.config.atrMultiplierTP,
        reasoning: `ADX ${adx.toFixed(1)} and EMA fast>slow, price>fast`,
        created_at: new Date(),
        executed: false,
      }
    }

    // Short when fast below slow and price below fast
    if (emaFast < emaSlow && current.close < emaFast) {
      const strength = Math.min(1, ((adx - this.config.adxThreshold) / 25) * 0.5 + 0.5)
      return {
        id: `momentum_${Date.now()}`,
        strategy_id: "momentum",
        symbol: current.symbol,
        signal_type: "sell",
        strength,
        price_target: current.close - atr * this.config.atrMultiplierTP,
        stop_loss: current.close + atr * this.config.atrMultiplierSL,
        take_profit: current.close - atr * this.config.atrMultiplierTP,
        reasoning: `ADX ${adx.toFixed(1)} and EMA fast<slow, price<fast`,
        created_at: new Date(),
        executed: false,
      }
    }

    return null
  }
}

