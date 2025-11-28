import { EventEmitter } from "events"

export interface MarketData {
  symbol: string
  price: number
  volume: number
  timestamp: number
  bid: number
  ask: number
  change24h: number
  exchange: string
}

export interface OrderBookData {
  symbol: string
  bids: [number, number][]
  asks: [number, number][]
  timestamp: number
  exchange: string
}

export interface TradeData {
  symbol: string
  price: number
  quantity: number
  timestamp: number
  isBuyerMaker: boolean
  exchange: string
}

type ExchangeType =
  | "binance"
  | "bitget"
  | "kraken"
  | "coinbase"
  | "okx"
  | "bybit"
  | "kucoin"
  | "gate"
  | "huobi"
  | "mexc"

const EXCHANGE_WS_URLS: Record<ExchangeType, string> = {
  binance: "wss://stream.binance.com:9443/ws",
  bitget: "wss://ws.bitget.com/spot/v1/stream",
  kraken: "wss://ws.kraken.com",
  coinbase: "wss://ws-feed.exchange.coinbase.com",
  okx: "wss://ws.okx.com:8443/ws/v5/public",
  bybit: "wss://stream.bybit.com/v5/public/spot",
  kucoin: "wss://ws-api-spot.kucoin.com",
  gate: "wss://api.gateio.ws/ws/v4/",
  huobi: "wss://api.huobi.pro/ws",
  mexc: "wss://wbs.mexc.com/ws",
}

export class WebSocketManager extends EventEmitter {
  private connections: Map<string, WebSocket> = new Map()
  private subscriptions: Map<string, Set<string>> = new Map()
  private reconnectAttempts: Map<string, number> = new Map()
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private heartbeatIntervals: Map<string, NodeJS.Timeout> = new Map()
  private lastPrices: Map<string, MarketData> = new Map()

  constructor() {
    super()
    this.setMaxListeners(100)
  }

  async connect(exchange: ExchangeType, customUrl?: string): Promise<void> {
    if (this.connections.has(exchange)) {
      console.log(`[v0] Already connected to ${exchange}`)
      return
    }

    const url = customUrl || EXCHANGE_WS_URLS[exchange]
    if (!url) {
      throw new Error(`No WebSocket URL for exchange: ${exchange}`)
    }

    return new Promise((resolve, reject) => {
      try {
        const ws = new WebSocket(url)

        const timeout = setTimeout(() => {
          if (ws.readyState !== WebSocket.OPEN) {
            ws.close()
            reject(new Error(`Connection timeout for ${exchange}`))
          }
        }, 10000)

        ws.onopen = () => {
          clearTimeout(timeout)
          console.log(`[v0] WebSocket connected to ${exchange}`)
          this.connections.set(exchange, ws)
          this.reconnectAttempts.set(exchange, 0)
          this.emit("connected", exchange)
          this.startHeartbeat(exchange)
          resolve()
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            this.handleMessage(exchange, data)
          } catch (error) {
            // Some messages might be binary or pings
            if (typeof event.data === "string" && event.data !== "pong") {
              console.error(`[v0] Error parsing WebSocket message from ${exchange}:`, error)
            }
          }
        }

        ws.onclose = (event) => {
          clearTimeout(timeout)
          console.log(`[v0] WebSocket disconnected from ${exchange}:`, event.code, event.reason)
          this.connections.delete(exchange)
          this.stopHeartbeat(exchange)
          this.emit("disconnected", exchange)

          // Auto-reconnect if not intentional close
          if (event.code !== 1000) {
            this.handleReconnect(exchange, url)
          }
        }

        ws.onerror = (error) => {
          console.error(`[v0] WebSocket error from ${exchange}:`, error)
          this.emit("error", exchange, error)
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  private startHeartbeat(exchange: ExchangeType): void {
    const interval = setInterval(() => {
      const ws = this.connections.get(exchange)
      if (ws && ws.readyState === WebSocket.OPEN) {
        // Send ping based on exchange
        switch (exchange) {
          case "binance":
            // Binance handles pings automatically
            break
          case "okx":
            ws.send("ping")
            break
          case "bybit":
            ws.send(JSON.stringify({ op: "ping" }))
            break
          case "huobi":
            ws.send(JSON.stringify({ ping: Date.now() }))
            break
          default:
            // Generic ping
            ws.send("ping")
        }
      }
    }, 20000)

    this.heartbeatIntervals.set(exchange, interval)
  }

  private stopHeartbeat(exchange: string): void {
    const interval = this.heartbeatIntervals.get(exchange)
    if (interval) {
      clearInterval(interval)
      this.heartbeatIntervals.delete(exchange)
    }
  }

  private handleMessage(exchange: ExchangeType, data: any): void {
    // Handle pong responses
    if (data === "pong" || data.op === "pong" || data.pong) {
      return
    }

    // Route to appropriate parser based on exchange and message type
    const messageType = this.getMessageType(exchange, data)

    switch (messageType) {
      case "ticker":
        const marketData = this.parseMarketData(exchange, data)
        if (marketData) {
          this.lastPrices.set(`${exchange}:${marketData.symbol}`, marketData)
          this.emit("marketData", marketData)
        }
        break
      case "orderbook":
        const orderBook = this.parseOrderBook(exchange, data)
        if (orderBook) {
          this.emit("orderBook", orderBook)
        }
        break
      case "trade":
        const trade = this.parseTrade(exchange, data)
        if (trade) {
          this.emit("trade", trade)
        }
        break
      default:
        // Unknown message type, log for debugging
        if (process.env.NODE_ENV === "development") {
          console.log(`[v0] Unknown message type from ${exchange}:`, data.type || data.e || "unknown")
        }
    }
  }

  private getMessageType(exchange: ExchangeType, data: any): "ticker" | "orderbook" | "trade" | "unknown" {
    switch (exchange) {
      case "binance":
        if (data.e === "24hrTicker" || data.e === "ticker") return "ticker"
        if (data.e === "depthUpdate" || data.e === "depth") return "orderbook"
        if (data.e === "trade" || data.e === "aggTrade") return "trade"
        break
      case "bitget":
        if (data.action === "snapshot" && data.arg?.channel === "ticker") return "ticker"
        if (data.arg?.channel === "books") return "orderbook"
        if (data.arg?.channel === "trade") return "trade"
        break
      case "okx":
        if (data.arg?.channel === "tickers") return "ticker"
        if (data.arg?.channel === "books") return "orderbook"
        if (data.arg?.channel === "trades") return "trade"
        break
      case "bybit":
        if (data.topic?.startsWith("tickers")) return "ticker"
        if (data.topic?.startsWith("orderbook")) return "orderbook"
        if (data.topic?.startsWith("publicTrade")) return "trade"
        break
      case "coinbase":
        if (data.type === "ticker") return "ticker"
        if (data.type === "l2update" || data.type === "snapshot") return "orderbook"
        if (data.type === "match") return "trade"
        break
      case "kraken":
        if (Array.isArray(data) && data[2] === "ticker") return "ticker"
        if (Array.isArray(data) && data[2]?.includes("book")) return "orderbook"
        if (Array.isArray(data) && data[2] === "trade") return "trade"
        break
    }
    return "unknown"
  }

  private parseMarketData(exchange: ExchangeType, data: any): MarketData | null {
    try {
      switch (exchange) {
        case "binance":
          return {
            symbol: data.s,
            price: Number.parseFloat(data.c),
            volume: Number.parseFloat(data.v),
            timestamp: data.E,
            bid: Number.parseFloat(data.b),
            ask: Number.parseFloat(data.a),
            change24h: Number.parseFloat(data.P),
            exchange: "binance",
          }
        case "bitget":
          const bitgetTicker = data.data?.[0]
          if (!bitgetTicker) return null
          return {
            symbol: bitgetTicker.instId,
            price: Number.parseFloat(bitgetTicker.last),
            volume: Number.parseFloat(bitgetTicker.vol24h),
            timestamp: Number.parseInt(bitgetTicker.ts),
            bid: Number.parseFloat(bitgetTicker.bidPx),
            ask: Number.parseFloat(bitgetTicker.askPx),
            change24h: Number.parseFloat(bitgetTicker.changeUtc24h) * 100,
            exchange: "bitget",
          }
        case "okx":
          const okxTicker = data.data?.[0]
          if (!okxTicker) return null
          return {
            symbol: okxTicker.instId,
            price: Number.parseFloat(okxTicker.last),
            volume: Number.parseFloat(okxTicker.vol24h),
            timestamp: Number.parseInt(okxTicker.ts),
            bid: Number.parseFloat(okxTicker.bidPx),
            ask: Number.parseFloat(okxTicker.askPx),
            change24h: Number.parseFloat(okxTicker.sodUtc0)
              ? ((Number.parseFloat(okxTicker.last) - Number.parseFloat(okxTicker.sodUtc0)) /
                  Number.parseFloat(okxTicker.sodUtc0)) *
                100
              : 0,
            exchange: "okx",
          }
        case "bybit":
          const bybitTicker = data.data
          if (!bybitTicker) return null
          return {
            symbol: bybitTicker.symbol,
            price: Number.parseFloat(bybitTicker.lastPrice),
            volume: Number.parseFloat(bybitTicker.volume24h),
            timestamp: Number.parseInt(bybitTicker.ts || Date.now()),
            bid: Number.parseFloat(bybitTicker.bid1Price),
            ask: Number.parseFloat(bybitTicker.ask1Price),
            change24h: Number.parseFloat(bybitTicker.price24hPcnt) * 100,
            exchange: "bybit",
          }
        case "coinbase":
          return {
            symbol: data.product_id,
            price: Number.parseFloat(data.price),
            volume: Number.parseFloat(data.volume_24h || 0),
            timestamp: new Date(data.time).getTime(),
            bid: Number.parseFloat(data.best_bid || data.price),
            ask: Number.parseFloat(data.best_ask || data.price),
            change24h: 0, // Coinbase ticker doesn't include 24h change
            exchange: "coinbase",
          }
        default:
          return null
      }
    } catch (error) {
      console.error(`[v0] Error parsing market data from ${exchange}:`, error)
      return null
    }
  }

  private parseOrderBook(exchange: ExchangeType, data: any): OrderBookData | null {
    try {
      switch (exchange) {
        case "binance":
          return {
            symbol: data.s,
            bids: data.b?.map((bid: string[]) => [Number.parseFloat(bid[0]), Number.parseFloat(bid[1])]) || [],
            asks: data.a?.map((ask: string[]) => [Number.parseFloat(ask[0]), Number.parseFloat(ask[1])]) || [],
            timestamp: data.E,
            exchange: "binance",
          }
        case "okx":
          const okxBook = data.data?.[0]
          if (!okxBook) return null
          return {
            symbol: data.arg.instId,
            bids: okxBook.bids?.map((bid: string[]) => [Number.parseFloat(bid[0]), Number.parseFloat(bid[1])]) || [],
            asks: okxBook.asks?.map((ask: string[]) => [Number.parseFloat(ask[0]), Number.parseFloat(ask[1])]) || [],
            timestamp: Number.parseInt(okxBook.ts || Date.now()),
            exchange: "okx",
          }
        default:
          return null
      }
    } catch (error) {
      console.error(`[v0] Error parsing order book from ${exchange}:`, error)
      return null
    }
  }

  private parseTrade(exchange: ExchangeType, data: any): TradeData | null {
    try {
      switch (exchange) {
        case "binance":
          return {
            symbol: data.s,
            price: Number.parseFloat(data.p),
            quantity: Number.parseFloat(data.q),
            timestamp: data.T,
            isBuyerMaker: data.m,
            exchange: "binance",
          }
        case "okx":
          const okxTrade = data.data?.[0]
          if (!okxTrade) return null
          return {
            symbol: data.arg.instId,
            price: Number.parseFloat(okxTrade.px),
            quantity: Number.parseFloat(okxTrade.sz),
            timestamp: Number.parseInt(okxTrade.ts),
            isBuyerMaker: okxTrade.side === "sell",
            exchange: "okx",
          }
        default:
          return null
      }
    } catch (error) {
      console.error(`[v0] Error parsing trade from ${exchange}:`, error)
      return null
    }
  }

  subscribe(exchange: ExchangeType, channel: string, symbol: string): void {
    const ws = this.connections.get(exchange)
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.error(`[v0] WebSocket not connected to ${exchange}`)
      return
    }

    const subscriptionKey = `${exchange}:${channel}:${symbol}`
    if (!this.subscriptions.has(subscriptionKey)) {
      this.subscriptions.set(subscriptionKey, new Set())
    }

    let subscribeMessage: any
    switch (exchange) {
      case "binance":
        subscribeMessage = {
          method: "SUBSCRIBE",
          params: [`${symbol.toLowerCase()}@${channel}`],
          id: Date.now(),
        }
        break
      case "bitget":
        subscribeMessage = {
          op: "subscribe",
          args: [{ channel, instId: symbol }],
        }
        break
      case "okx":
        subscribeMessage = {
          op: "subscribe",
          args: [{ channel, instId: symbol }],
        }
        break
      case "bybit":
        subscribeMessage = {
          op: "subscribe",
          args: [`${channel}.${symbol}`],
        }
        break
      case "coinbase":
        subscribeMessage = {
          type: "subscribe",
          product_ids: [symbol],
          channels: [channel],
        }
        break
      case "kraken":
        subscribeMessage = {
          event: "subscribe",
          pair: [symbol],
          subscription: { name: channel },
        }
        break
      default:
        console.error(`[v0] Unsupported exchange for subscription: ${exchange}`)
        return
    }

    ws.send(JSON.stringify(subscribeMessage))
    console.log(`[v0] Subscribed to ${channel} for ${symbol} on ${exchange}`)
  }

  unsubscribe(exchange: ExchangeType, channel: string, symbol: string): void {
    const ws = this.connections.get(exchange)
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return
    }

    const subscriptionKey = `${exchange}:${channel}:${symbol}`
    this.subscriptions.delete(subscriptionKey)

    let unsubscribeMessage: any
    switch (exchange) {
      case "binance":
        unsubscribeMessage = {
          method: "UNSUBSCRIBE",
          params: [`${symbol.toLowerCase()}@${channel}`],
          id: Date.now(),
        }
        break
      case "okx":
        unsubscribeMessage = {
          op: "unsubscribe",
          args: [{ channel, instId: symbol }],
        }
        break
      case "bybit":
        unsubscribeMessage = {
          op: "unsubscribe",
          args: [`${channel}.${symbol}`],
        }
        break
      case "coinbase":
        unsubscribeMessage = {
          type: "unsubscribe",
          product_ids: [symbol],
          channels: [channel],
        }
        break
      default:
        return
    }

    ws.send(JSON.stringify(unsubscribeMessage))
    console.log(`[v0] Unsubscribed from ${channel} for ${symbol} on ${exchange}`)
  }

  private async handleReconnect(exchange: ExchangeType, url: string): Promise<void> {
    const attempts = this.reconnectAttempts.get(exchange) || 0
    if (attempts >= this.maxReconnectAttempts) {
      console.error(`[v0] Max reconnection attempts reached for ${exchange}`)
      this.emit("maxReconnectAttemptsReached", exchange)
      return
    }

    this.reconnectAttempts.set(exchange, attempts + 1)
    const delay = this.reconnectDelay * Math.pow(2, attempts)

    console.log(`[v0] Reconnecting to ${exchange} in ${delay}ms (attempt ${attempts + 1})`)
    setTimeout(async () => {
      try {
        await this.connect(exchange, url)
        // Resubscribe to previous subscriptions
        this.resubscribeAll(exchange)
      } catch (error) {
        console.error(`[v0] Reconnection failed for ${exchange}:`, error)
      }
    }, delay)
  }

  private resubscribeAll(exchange: ExchangeType): void {
    for (const [key] of this.subscriptions) {
      const [ex, channel, symbol] = key.split(":")
      if (ex === exchange) {
        this.subscribe(exchange, channel, symbol)
      }
    }
  }

  getLastPrice(exchange: string, symbol: string): MarketData | undefined {
    return this.lastPrices.get(`${exchange}:${symbol}`)
  }

  getAllLastPrices(): Map<string, MarketData> {
    return new Map(this.lastPrices)
  }

  disconnect(exchange: string): void {
    const ws = this.connections.get(exchange)
    if (ws) {
      ws.close(1000, "Intentional disconnect")
      this.connections.delete(exchange)
      this.stopHeartbeat(exchange)
    }
  }

  disconnectAll(): void {
    for (const [exchange, ws] of this.connections) {
      ws.close(1000, "Intentional disconnect")
      this.stopHeartbeat(exchange)
    }
    this.connections.clear()
    this.subscriptions.clear()
    this.lastPrices.clear()
  }

  isConnected(exchange: string): boolean {
    const ws = this.connections.get(exchange)
    return ws?.readyState === WebSocket.OPEN
  }

  getConnectedExchanges(): string[] {
    return Array.from(this.connections.keys()).filter((ex) => this.isConnected(ex))
  }

  getConnectionStats(): Record<string, { connected: boolean; subscriptions: number }> {
    const stats: Record<string, { connected: boolean; subscriptions: number }> = {}

    for (const exchange of Object.keys(EXCHANGE_WS_URLS)) {
      const subscriptionCount = Array.from(this.subscriptions.keys()).filter((key) =>
        key.startsWith(`${exchange}:`),
      ).length

      stats[exchange] = {
        connected: this.isConnected(exchange),
        subscriptions: subscriptionCount,
      }
    }

    return stats
  }
}

export const wsManager = new WebSocketManager()
