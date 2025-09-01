// Base strategy class for all trading strategies
import type { MarketData, TradeSignal } from "@/lib/database/schema"

export interface StrategyConfig {
  timeframe: string
  maxPositions: number
  stopLossPct: number
  takeProfitPct: number
  [key: string]: any
}

export interface TechnicalIndicators {
  rsi?: number
  macd?: { macd: number; signal: number; histogram: number }
  bollinger?: { upper: number; middle: number; lower: number }
  ema?: number
  sma?: number
  emaFast?: number
  emaSlow?: number
  volume?: number
  volatility?: number
  atr?: number
  adx?: number
}

export interface MarketContext {
  currentPrice: number
  volume: number
  volatility: number
  trend: "bullish" | "bearish" | "sideways"
  sentimentScore?: number
}

export abstract class BaseStrategy {
  protected config: StrategyConfig
  protected indicators: TechnicalIndicators = {}
  protected historicalData: MarketData[] = []
  protected openPositions = 0

  constructor(config: StrategyConfig) {
    this.config = config
  }

  // Abstract methods that must be implemented by each strategy
  abstract getName(): string
  abstract getDescription(): string
  abstract analyze(marketData: MarketData[], context: MarketContext): TradeSignal | null

  // Optional methods that can be overridden
  onTrade(signal: TradeSignal, executed: boolean): void {
    // Default implementation - can be overridden
  }

  onMarketData(data: MarketData): void {
    this.historicalData.push(data)
    // Keep only last 1000 candles to prevent memory issues
    if (this.historicalData.length > 1000) {
      this.historicalData = this.historicalData.slice(-1000)
    }
    this.updateIndicators()
  }

  // Technical indicator calculations
  protected updateIndicators(): void {
    if (this.historicalData.length < 20) return

    const closes = this.historicalData.map((d) => d.close)
    const highs = this.historicalData.map((d) => d.high)
    const lows = this.historicalData.map((d) => d.low)
    const volumes = this.historicalData.map((d) => d.volume)

    // RSI calculation
    this.indicators.rsi = this.calculateRSI(closes, 14)

    // Simple Moving Average
    this.indicators.sma = this.calculateSMA(closes, 20)

    // Exponential Moving Average
    this.indicators.ema = this.calculateEMA(closes, 20)
    this.indicators.emaFast = this.calculateEMA(closes, 12)
    this.indicators.emaSlow = this.calculateEMA(closes, 26)

    // Bollinger Bands
    this.indicators.bollinger = this.calculateBollingerBands(closes, 20, 2)

    // MACD
    this.indicators.macd = this.calculateMACD(closes)

    // Volume average
    this.indicators.volume = this.calculateSMA(volumes, 20)

    // Volatility (standard deviation of returns)
    this.indicators.volatility = this.calculateVolatility(closes, 20)

    // ATR and ADX
    this.indicators.atr = this.calculateATR(highs, lows, closes, 14)
    this.indicators.adx = this.calculateADX(highs, lows, closes, 14)
  }

  protected calculateRSI(prices: number[], period = 14): number {
    if (prices.length < period + 1) return 50

    const gains: number[] = []
    const losses: number[] = []

    for (let i = 1; i < prices.length; i++) {
      const change = prices[i] - prices[i - 1]
      gains.push(change > 0 ? change : 0)
      losses.push(change < 0 ? Math.abs(change) : 0)
    }

    const avgGain = gains.slice(-period).reduce((a, b) => a + b, 0) / period
    const avgLoss = losses.slice(-period).reduce((a, b) => a + b, 0) / period

    if (avgLoss === 0) return 100
    const rs = avgGain / avgLoss
    return 100 - 100 / (1 + rs)
  }

  protected calculateSMA(prices: number[], period: number): number {
    if (prices.length < period) return prices[prices.length - 1]
    const slice = prices.slice(-period)
    return slice.reduce((a, b) => a + b, 0) / period
  }

  protected calculateEMA(prices: number[], period: number): number {
    if (prices.length < period) return prices[prices.length - 1]

    const multiplier = 2 / (period + 1)
    let ema = this.calculateSMA(prices.slice(0, period), period)

    for (let i = period; i < prices.length; i++) {
      ema = prices[i] * multiplier + ema * (1 - multiplier)
    }

    return ema
  }

  protected calculateBollingerBands(prices: number[], period: number, stdDev: number) {
    const sma = this.calculateSMA(prices, period)
    const slice = prices.slice(-period)
    const variance = slice.reduce((acc, price) => acc + Math.pow(price - sma, 2), 0) / period
    const standardDeviation = Math.sqrt(variance)

    return {
      upper: sma + standardDeviation * stdDev,
      middle: sma,
      lower: sma - standardDeviation * stdDev,
    }
  }

  protected calculateMACD(prices: number[]) {
    const ema12 = this.calculateEMA(prices, 12)
    const ema26 = this.calculateEMA(prices, 26)
    const macd = ema12 - ema26

    // For signal line, we'd need to calculate EMA of MACD values
    // Simplified version here
    const signal = macd * 0.9 // Approximation

    return {
      macd,
      signal,
      histogram: macd - signal,
    }
  }

  protected calculateATR(highs: number[], lows: number[], closes: number[], period = 14): number {
    if (highs.length < period + 1) return 0
    const trs: number[] = []
    for (let i = 1; i < highs.length; i++) {
      const high = highs[i]
      const low = lows[i]
      const prevClose = closes[i - 1]
      const tr = Math.max(high - low, Math.abs(high - prevClose), Math.abs(low - prevClose))
      trs.push(tr)
    }
    // Wilder's smoothing
    const initial = trs.slice(0, period).reduce((a, b) => a + b, 0) / period
    let atr = initial
    for (let i = period; i < trs.length; i++) {
      atr = (atr * (period - 1) + trs[i]) / period
    }
    return atr
  }

  protected calculateADX(highs: number[], lows: number[], closes: number[], period = 14): number {
    if (highs.length < period + 2) return 0
    const dmPlus: number[] = []
    const dmMinus: number[] = []
    const tr: number[] = []
    for (let i = 1; i < highs.length; i++) {
      const upMove = highs[i] - highs[i - 1]
      const downMove = lows[i - 1] - lows[i]
      dmPlus.push(upMove > downMove && upMove > 0 ? upMove : 0)
      dmMinus.push(downMove > upMove && downMove > 0 ? downMove : 0)
      const thisTr = Math.max(
        highs[i] - lows[i],
        Math.abs(highs[i] - closes[i - 1]),
        Math.abs(lows[i] - closes[i - 1]),
      )
      tr.push(thisTr)
    }
    const smooth = (arr: number[]) => {
      const smoothed: number[] = []
      let val = arr.slice(0, period).reduce((a, b) => a + b, 0)
      smoothed.push(val)
      for (let i = period; i < arr.length; i++) {
        val = val - val / period + arr[i]
        smoothed.push(val)
      }
      return smoothed
    }
    const trN = smooth(tr)
    const dmPlusN = smooth(dmPlus)
    const dmMinusN = smooth(dmMinus)
    const diPlus = dmPlusN.map((v, i) => (trN[i] ? (100 * v) / trN[i] : 0))
    const diMinus = dmMinusN.map((v, i) => (trN[i] ? (100 * v) / trN[i] : 0))
    const dx = diPlus.map((v, i) => {
      const m = diMinus[i]
      const denom = v + m
      return denom ? (100 * Math.abs(v - m)) / denom : 0
    })
    const adx = dx.slice(period - 1).reduce((a, b) => a + b, 0) / (dx.length - (period - 1))
    return adx || 0
  }

  protected isTrending(): boolean {
    const adx = this.indicators.adx || 0
    const emaFast = this.indicators.emaFast || 0
    const emaSlow = this.indicators.emaSlow || 0
    return adx > 20 && emaFast > emaSlow
  }

  protected isRanging(): boolean {
    const adx = this.indicators.adx || 0
    return adx < 18
  }

  protected calculateVolatility(prices: number[], period: number): number {
    if (prices.length < period + 1) return 0

    const returns = []
    for (let i = 1; i < prices.length; i++) {
      returns.push((prices[i] - prices[i - 1]) / prices[i - 1])
    }

    const recentReturns = returns.slice(-period)
    const mean = recentReturns.reduce((a, b) => a + b, 0) / period
    const variance = recentReturns.reduce((acc, ret) => acc + Math.pow(ret - mean, 2), 0) / period

    return Math.sqrt(variance) * Math.sqrt(252) // Annualized volatility
  }

  // Risk management helpers
  protected shouldTrade(signal: TradeSignal, context: MarketContext): boolean {
    // Check if we're at max positions
    if (this.openPositions >= this.config.maxPositions) {
      return false
    }

    // Check volatility limits
    if (this.indicators.volatility && this.indicators.volatility > 0.5) {
      return false // Too volatile
    }

    // Check signal strength
    if (signal.strength < 0.6) {
      return false // Signal not strong enough
    }

    return true
  }

  protected calculatePositionSize(balance: number, price: number, riskPct = 0.02): number {
    const riskAmount = balance * riskPct
    const stopLossDistance = price * this.config.stopLossPct
    return Math.min(riskAmount / stopLossDistance, (balance * 0.1) / price) // Max 10% of balance
  }
}
