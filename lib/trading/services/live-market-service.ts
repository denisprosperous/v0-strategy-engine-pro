import { BinanceBroker } from "../brokers/binance-broker"
import { BitgetBroker } from "../brokers/bitget-broker"
import { KrakenBroker } from "../brokers/kraken-broker"
import { db } from "@/lib/config/database"
import { config } from "@/lib/config/environment"

export interface LiveMarketData {
  symbol: string
  price: number
  change24h: number
  volume24h: number
  high24h: number
  low24h: number
  bid: number
  ask: number
  timestamp: number
  exchange: string
}

export interface PortfolioData {
  totalValue: number
  totalPnL: number
  pnlPercentage: number
  openTrades: number
  winRate: number
  activeStrategies: number
  balances: { asset: string; free: number; locked: number; usdValue: number }[]
}

class LiveMarketService {
  private brokers: Map<string, any> = new Map()
  private priceCache: Map<string, { data: LiveMarketData; timestamp: number }> = new Map()
  private cacheTTL = 5000 // 5 seconds cache

  constructor() {
    this.initializeBrokers()
  }

  private initializeBrokers() {
    // Initialize Binance (public endpoints work without API keys)
    if (config.binance.apiKey) {
      this.brokers.set(
        "binance",
        new BinanceBroker(config.binance.apiKey, config.binance.apiSecret || "", config.binance.testnet),
      )
    }

    // Initialize Bitget
    if (config.bitget.apiKey) {
      this.brokers.set("bitget", new BitgetBroker())
    }

    // Initialize Kraken
    if (config.kraken.apiKey) {
      this.brokers.set("kraken", new KrakenBroker())
    }
  }

  async getPrice(symbol: string, exchange = "binance"): Promise<number> {
    const cacheKey = `${exchange}:${symbol}`
    const cached = this.priceCache.get(cacheKey)

    if (cached && Date.now() - cached.timestamp < this.cacheTTL) {
      return cached.data.price
    }

    try {
      // Use public API endpoints that don't require authentication
      let price = 0

      switch (exchange.toLowerCase()) {
        case "binance":
          const binanceResponse = await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${symbol}`)
          const binanceData = await binanceResponse.json()
          price = Number.parseFloat(binanceData.price)
          break

        case "bitget":
          const bitgetResponse = await fetch(`https://api.bitget.com/api/spot/v1/market/ticker?symbol=${symbol}`)
          const bitgetData = await bitgetResponse.json()
          price = Number.parseFloat(bitgetData.data?.close || 0)
          break

        case "kraken":
          const krakenResponse = await fetch(`https://api.kraken.com/0/public/Ticker?pair=${symbol}`)
          const krakenData = await krakenResponse.json()
          const krakenPair = Object.values(krakenData.result || {})[0] as any
          price = Number.parseFloat(krakenPair?.c?.[0] || 0)
          break

        default:
          throw new Error(`Unknown exchange: ${exchange}`)
      }

      // Update cache
      this.priceCache.set(cacheKey, {
        data: {
          symbol,
          price,
          change24h: 0,
          volume24h: 0,
          high24h: 0,
          low24h: 0,
          bid: 0,
          ask: 0,
          timestamp: Date.now(),
          exchange,
        },
        timestamp: Date.now(),
      })

      return price
    } catch (error) {
      console.error(`Error fetching price for ${symbol} from ${exchange}:`, error)
      return 0
    }
  }

  async getMarketData(symbol: string, exchange = "binance"): Promise<LiveMarketData | null> {
    const cacheKey = `${exchange}:${symbol}:full`
    const cached = this.priceCache.get(cacheKey)

    if (cached && Date.now() - cached.timestamp < this.cacheTTL) {
      return cached.data
    }

    try {
      let marketData: LiveMarketData

      switch (exchange.toLowerCase()) {
        case "binance":
          const response = await fetch(`https://api.binance.com/api/v3/ticker/24hr?symbol=${symbol}`)
          const data = await response.json()
          marketData = {
            symbol: data.symbol,
            price: Number.parseFloat(data.lastPrice),
            change24h: Number.parseFloat(data.priceChangePercent),
            volume24h: Number.parseFloat(data.volume),
            high24h: Number.parseFloat(data.highPrice),
            low24h: Number.parseFloat(data.lowPrice),
            bid: Number.parseFloat(data.bidPrice),
            ask: Number.parseFloat(data.askPrice),
            timestamp: Date.now(),
            exchange: "binance",
          }
          break

        case "bitget":
          const bitgetRes = await fetch(`https://api.bitget.com/api/spot/v1/market/ticker?symbol=${symbol}`)
          const bitgetData = await bitgetRes.json()
          const ticker = bitgetData.data
          marketData = {
            symbol: ticker?.symbol || symbol,
            price: Number.parseFloat(ticker?.close || 0),
            change24h: Number.parseFloat(ticker?.changeUtc24h || 0) * 100,
            volume24h: Number.parseFloat(ticker?.usdtVol || 0),
            high24h: Number.parseFloat(ticker?.high24h || 0),
            low24h: Number.parseFloat(ticker?.low24h || 0),
            bid: Number.parseFloat(ticker?.buyOne || 0),
            ask: Number.parseFloat(ticker?.sellOne || 0),
            timestamp: Date.now(),
            exchange: "bitget",
          }
          break

        default:
          return null
      }

      // Update cache
      this.priceCache.set(cacheKey, { data: marketData, timestamp: Date.now() })

      // Also cache to Redis for persistence
      await db.cacheMarketData(symbol, marketData, 60)

      return marketData
    } catch (error) {
      console.error(`Error fetching market data for ${symbol}:`, error)
      return null
    }
  }

  async getMultipleMarketData(symbols: string[], exchange = "binance"): Promise<LiveMarketData[]> {
    const results = await Promise.all(symbols.map((symbol) => this.getMarketData(symbol, exchange)))
    return results.filter((data): data is LiveMarketData => data !== null)
  }

  async getPortfolioValue(userId: string): Promise<PortfolioData> {
    // Get user's trades and calculate portfolio
    const analytics = await db.getAnalytics(userId)
    const trades = await db.getTrades(userId, { status: "open" })

    // Calculate total value from open positions
    let totalValue = 0
    const openPositions = []

    for (const trade of trades) {
      const currentPrice = await this.getPrice(trade.symbol as string, trade.broker as string)
      const entryPrice = Number.parseFloat(trade.entryPrice as string)
      const quantity = Number.parseFloat(trade.quantity as string)
      const positionValue = currentPrice * quantity
      const unrealizedPnL =
        trade.side === "buy" ? (currentPrice - entryPrice) * quantity : (entryPrice - currentPrice) * quantity

      totalValue += positionValue
      openPositions.push({
        ...trade,
        currentPrice,
        positionValue,
        unrealizedPnL,
      })
    }

    return {
      totalValue,
      totalPnL: analytics.portfolio.totalPnL,
      pnlPercentage: totalValue > 0 ? (analytics.portfolio.totalPnL / totalValue) * 100 : 0,
      openTrades: analytics.trading.openTrades,
      winRate: analytics.trading.winRate,
      activeStrategies: analytics.trading.activeStrategies,
      balances: [],
    }
  }

  async getExchangeBalance(exchange: string): Promise<{ asset: string; free: number; locked: number }[]> {
    const broker = this.brokers.get(exchange.toLowerCase())
    if (!broker) {
      console.warn(`Broker not configured for ${exchange}`)
      return []
    }

    try {
      const balance = await broker.getBalance()
      if (balance.success) {
        return balance.balances
      }
      return []
    } catch (error) {
      console.error(`Error fetching balance from ${exchange}:`, error)
      return []
    }
  }

  async testExchangeConnection(exchange: string): Promise<{ connected: boolean; message: string }> {
    try {
      switch (exchange.toLowerCase()) {
        case "binance":
          const binanceRes = await fetch("https://api.binance.com/api/v3/ping")
          return { connected: binanceRes.ok, message: binanceRes.ok ? "Connected" : "Failed to connect" }

        case "bitget":
          const bitgetRes = await fetch("https://api.bitget.com/api/spot/v1/public/time")
          return { connected: bitgetRes.ok, message: bitgetRes.ok ? "Connected" : "Failed to connect" }

        case "kraken":
          const krakenRes = await fetch("https://api.kraken.com/0/public/Time")
          return { connected: krakenRes.ok, message: krakenRes.ok ? "Connected" : "Failed to connect" }

        case "coinbase":
          const coinbaseRes = await fetch("https://api.exchange.coinbase.com/time")
          return { connected: coinbaseRes.ok, message: coinbaseRes.ok ? "Connected" : "Failed to connect" }

        case "okx":
          const okxRes = await fetch("https://www.okx.com/api/v5/public/time")
          return { connected: okxRes.ok, message: okxRes.ok ? "Connected" : "Failed to connect" }

        case "bybit":
          const bybitRes = await fetch("https://api.bybit.com/v5/market/time")
          return { connected: bybitRes.ok, message: bybitRes.ok ? "Connected" : "Failed to connect" }

        case "kucoin":
          const kucoinRes = await fetch("https://api.kucoin.com/api/v1/timestamp")
          return { connected: kucoinRes.ok, message: kucoinRes.ok ? "Connected" : "Failed to connect" }

        case "gate":
          const gateRes = await fetch("https://api.gateio.ws/api/v4/spot/time")
          return { connected: gateRes.ok, message: gateRes.ok ? "Connected" : "Failed to connect" }

        case "huobi":
          const huobiRes = await fetch("https://api.huobi.pro/v1/common/timestamp")
          return { connected: huobiRes.ok, message: huobiRes.ok ? "Connected" : "Failed to connect" }

        case "mexc":
          const mexcRes = await fetch("https://api.mexc.com/api/v3/time")
          return { connected: mexcRes.ok, message: mexcRes.ok ? "Connected" : "Failed to connect" }

        default:
          return { connected: false, message: `Unknown exchange: ${exchange}` }
      }
    } catch (error) {
      return { connected: false, message: error instanceof Error ? error.message : "Connection failed" }
    }
  }

  async testAllExchangeConnections(): Promise<Record<string, { connected: boolean; message: string }>> {
    const exchanges = ["binance", "bitget", "kraken", "coinbase", "okx", "bybit", "kucoin", "gate", "huobi", "mexc"]
    const results: Record<string, { connected: boolean; message: string }> = {}

    await Promise.all(
      exchanges.map(async (exchange) => {
        results[exchange] = await this.testExchangeConnection(exchange)
      }),
    )

    return results
  }
}

export const liveMarketService = new LiveMarketService()
