// Market data aggregation service for multiple exchanges
import { supabaseServer } from "@/lib/config/supabase-server"
import { logger } from "@/lib/utils/logger"

export interface PriceData {
  symbol: string
  price: number
  volume: number
  change24h: number
  timestamp: Date
  source: string
}

export interface CandleData {
  symbol: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  timestamp: Date
  timeframe: string
}

export class MarketDataAggregator {
  private subscribers = new Map<string, Set<(data: PriceData) => void>>()
  private priceCache = new Map<string, PriceData>()
  private isRunning = false
  private updateInterval: NodeJS.Timeout | null = null

  async start(): Promise<void> {
    if (this.isRunning) return

    this.isRunning = true
    logger.info("Market data aggregator started")

    // Start real-time price updates
    this.startPriceUpdates()

    // Start historical data collection
    this.startHistoricalDataCollection()
  }

  async stop(): Promise<void> {
    this.isRunning = false

    if (this.updateInterval) {
      clearInterval(this.updateInterval)
      this.updateInterval = null
    }

    logger.info("Market data aggregator stopped")
  }

  subscribe(symbol: string, callback: (data: PriceData) => void): void {
    if (!this.subscribers.has(symbol)) {
      this.subscribers.set(symbol, new Set())
    }
    this.subscribers.get(symbol)!.add(callback)

    // Send cached data immediately if available
    const cached = this.priceCache.get(symbol)
    if (cached) {
      callback(cached)
    }
  }

  unsubscribe(symbol: string, callback: (data: PriceData) => void): void {
    const symbolSubscribers = this.subscribers.get(symbol)
    if (symbolSubscribers) {
      symbolSubscribers.delete(callback)
      if (symbolSubscribers.size === 0) {
        this.subscribers.delete(symbol)
      }
    }
  }

  async getPrice(symbol: string): Promise<number> {
    const cached = this.priceCache.get(symbol)
    if (cached && Date.now() - cached.timestamp.getTime() < 10000) {
      return cached.price
    }

    // Fetch fresh price from multiple sources
    const prices = await Promise.allSettled([this.fetchBinancePrice(symbol), this.fetchCoinGeckoPrice(symbol)])

    const validPrices = prices
      .filter((result): result is PromiseFulfilledResult<number> => result.status === "fulfilled")
      .map((result) => result.value)

    if (validPrices.length === 0) {
      throw new Error(`Unable to fetch price for ${symbol}`)
    }

    // Use average of available prices
    return validPrices.reduce((sum, price) => sum + price, 0) / validPrices.length
  }

  async getHistoricalData(symbol: string, timeframe: string, limit = 100): Promise<CandleData[]> {
    try {
      // First try to get from database
      const { data: dbData, error } = await supabaseServer
        .from("market_data")
        .select("*")
        .eq("symbol", symbol)
        .order("timestamp", { ascending: false })
        .limit(limit)

      if (!error && dbData && dbData.length > 0) {
        return dbData.map((d) => ({
          symbol: d.symbol,
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
          volume: d.volume,
          timestamp: new Date(d.timestamp),
          timeframe,
        }))
      }

      // Fallback to external API
      return await this.fetchBinanceKlines(symbol, timeframe, limit)
    } catch (error) {
      logger.error("Failed to get historical data", { symbol, timeframe, error })
      throw error
    }
  }

  private startPriceUpdates(): void {
    this.updateInterval = setInterval(async () => {
      if (!this.isRunning) return

      const symbols = Array.from(this.subscribers.keys())
      if (symbols.length === 0) return

      try {
        await this.updatePrices(symbols)
      } catch (error) {
        logger.error("Price update failed", { error })
      }
    }, 5000) // Update every 5 seconds
  }

  private async updatePrices(symbols: string[]): Promise<void> {
    const pricePromises = symbols.map(async (symbol) => {
      try {
        const price = await this.getPrice(symbol)
        const priceData: PriceData = {
          symbol,
          price,
          volume: 0, // Would be fetched from API
          change24h: 0, // Would be calculated
          timestamp: new Date(),
          source: "aggregated",
        }

        this.priceCache.set(symbol, priceData)

        // Notify subscribers
        const subscribers = this.subscribers.get(symbol)
        if (subscribers) {
          subscribers.forEach((callback) => callback(priceData))
        }

        return priceData
      } catch (error) {
        logger.error("Failed to update price", { symbol, error })
        return null
      }
    })

    await Promise.allSettled(pricePromises)
  }

  private async fetchBinancePrice(symbol: string): Promise<number> {
    try {
      const response = await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${symbol}`)
      if (!response.ok) throw new Error("Binance API error")

      const data = await response.json()
      return Number.parseFloat(data.price)
    } catch (error) {
      logger.debug("Binance price fetch failed", { symbol, error })
      throw error
    }
  }

  private async fetchCoinGeckoPrice(symbol: string): Promise<number> {
    try {
      // Convert symbol to CoinGecko format (e.g., BTCUSDT -> bitcoin)
      const coinId = this.symbolToCoinGeckoId(symbol)
      const response = await fetch(`https://api.coingecko.com/api/v3/simple/price?ids=${coinId}&vs_currencies=usd`)

      if (!response.ok) throw new Error("CoinGecko API error")

      const data = await response.json()
      return data[coinId]?.usd || 0
    } catch (error) {
      logger.debug("CoinGecko price fetch failed", { symbol, error })
      throw error
    }
  }

  private async fetchBinanceKlines(symbol: string, timeframe: string, limit: number): Promise<CandleData[]> {
    try {
      const interval = this.timeframeToInterval(timeframe)
      const response = await fetch(
        `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=${limit}`,
      )

      if (!response.ok) throw new Error("Binance klines API error")

      const data = await response.json()
      return data.map((kline: any[]) => ({
        symbol,
        open: Number.parseFloat(kline[1]),
        high: Number.parseFloat(kline[2]),
        low: Number.parseFloat(kline[3]),
        close: Number.parseFloat(kline[4]),
        volume: Number.parseFloat(kline[5]),
        timestamp: new Date(kline[0]),
        timeframe,
      }))
    } catch (error) {
      logger.error("Failed to fetch Binance klines", { symbol, timeframe, error })
      throw error
    }
  }

  private startHistoricalDataCollection(): void {
    // Collect and store historical data every hour
    setInterval(
      async () => {
        if (!this.isRunning) return

        const symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT"] // Popular symbols

        for (const symbol of symbols) {
          try {
            const candles = await this.fetchBinanceKlines(symbol, "1h", 1)
            if (candles.length > 0) {
              await this.storeMarketData(candles[0])
            }
          } catch (error) {
            logger.error("Historical data collection failed", { symbol, error })
          }
        }
      },
      60 * 60 * 1000,
    ) // Every hour
  }

  private async storeMarketData(candle: CandleData): Promise<void> {
    try {
      await supabaseServer.from("market_data").upsert({
        symbol: candle.symbol,
        timestamp: candle.timestamp.toISOString(),
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
        volume: candle.volume,
        source: "binance",
      })
    } catch (error) {
      logger.error("Failed to store market data", { candle, error })
    }
  }

  private symbolToCoinGeckoId(symbol: string): string {
    const mapping: Record<string, string> = {
      BTCUSDT: "bitcoin",
      ETHUSDT: "ethereum",
      ADAUSDT: "cardano",
      SOLUSDT: "solana",
      DOTUSDT: "polkadot",
      LINKUSDT: "chainlink",
    }
    return mapping[symbol] || "bitcoin"
  }

  private timeframeToInterval(timeframe: string): string {
    const mapping: Record<string, string> = {
      "1m": "1m",
      "5m": "5m",
      "15m": "15m",
      "1h": "1h",
      "4h": "4h",
      "1d": "1d",
    }
    return mapping[timeframe] || "1h"
  }
}

// Singleton instance
export const marketDataAggregator = new MarketDataAggregator()
