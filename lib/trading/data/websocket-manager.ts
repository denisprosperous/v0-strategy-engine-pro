import { EventEmitter } from "events"

export interface MarketData {
  symbol: string
  price: number
  volume: number
  timestamp: number
  bid: number
  ask: number
  change24h: number
}

export interface OrderBookData {
  symbol: string
  bids: [number, number][]
  asks: [number, number][]
  timestamp: number
}

export class WebSocketManager extends EventEmitter {
  private connections: Map<string, WebSocket> = new Map()
  private subscriptions: Map<string, Set<string>> = new Map()
  private reconnectAttempts: Map<string, number> = new Map()
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000

  constructor() {
    super()
    this.setMaxListeners(100)
  }

  async connect(exchange: string, url: string): Promise<void> {
    if (this.connections.has(exchange)) {
      return
    }

    const ws = new WebSocket(url)
    this.connections.set(exchange, ws)
    this.reconnectAttempts.set(exchange, 0)

    ws.onopen = () => {
      console.log(`[v0] WebSocket connected to ${exchange}`)
      this.emit("connected", exchange)
      this.reconnectAttempts.set(exchange, 0)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this.handleMessage(exchange, data)
      } catch (error) {
        console.error(`[v0] Error parsing WebSocket message from ${exchange}:`, error)
      }
    }

    ws.onclose = () => {
      console.log(`[v0] WebSocket disconnected from ${exchange}`)
      this.connections.delete(exchange)
      this.emit("disconnected", exchange)
      this.handleReconnect(exchange, url)
    }

    ws.onerror = (error) => {
      console.error(`[v0] WebSocket error from ${exchange}:`, error)
      this.emit("error", exchange, error)
    }
  }

  private handleMessage(exchange: string, data: any): void {
    switch (data.type || data.e) {
      case "ticker":
      case "24hrTicker":
        this.emit("marketData", this.parseMarketData(exchange, data))
        break
      case "depth":
      case "depthUpdate":
        this.emit("orderBook", this.parseOrderBook(exchange, data))
        break
      case "trade":
      case "aggTrade":
        this.emit("trade", this.parseTrade(exchange, data))
        break
      default:
        console.log(`[v0] Unknown message type from ${exchange}:`, data.type || data.e)
    }
  }

  private parseMarketData(exchange: string, data: any): MarketData {
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
        }
      case "bitget":
        return {
          symbol: data.instId,
          price: Number.parseFloat(data.last),
          volume: Number.parseFloat(data.vol24h),
          timestamp: Number.parseInt(data.ts),
          bid: Number.parseFloat(data.bidPx),
          ask: Number.parseFloat(data.askPx),
          change24h: Number.parseFloat(data.change24h),
        }
      default:
        throw new Error(`Unknown exchange: ${exchange}`)
    }
  }

  private parseOrderBook(exchange: string, data: any): OrderBookData {
    switch (exchange) {
      case "binance":
        return {
          symbol: data.s,
          bids: data.b?.map((bid: string[]) => [Number.parseFloat(bid[0]), Number.parseFloat(bid[1])]) || [],
          asks: data.a?.map((ask: string[]) => [Number.parseFloat(ask[0]), Number.parseFloat(ask[1])]) || [],
          timestamp: data.E,
        }
      case "bitget":
        return {
          symbol: data.arg.instId,
          bids:
            data.data[0]?.bids?.map((bid: string[]) => [Number.parseFloat(bid[0]), Number.parseFloat(bid[1])]) || [],
          asks:
            data.data[0]?.asks?.map((ask: string[]) => [Number.parseFloat(ask[0]), Number.parseFloat(ask[1])]) || [],
          timestamp: Number.parseInt(data.data[0]?.ts || Date.now()),
        }
      default:
        throw new Error(`Unknown exchange: ${exchange}`)
    }
  }

  private parseTrade(exchange: string, data: any) {
    switch (exchange) {
      case "binance":
        return {
          symbol: data.s,
          price: Number.parseFloat(data.p),
          quantity: Number.parseFloat(data.q),
          timestamp: data.T,
          isBuyerMaker: data.m,
        }
      case "bitget":
        return {
          symbol: data.arg.instId,
          price: Number.parseFloat(data.data[0].px),
          quantity: Number.parseFloat(data.data[0].sz),
          timestamp: Number.parseInt(data.data[0].ts),
          isBuyerMaker: data.data[0].side === "sell",
        }
      default:
        throw new Error(`Unknown exchange: ${exchange}`)
    }
  }

  subscribe(exchange: string, channel: string, symbol: string): void {
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
          args: [
            {
              channel: channel,
              instId: symbol,
            },
          ],
        }
        break
      default:
        throw new Error(`Unknown exchange: ${exchange}`)
    }

    ws.send(JSON.stringify(subscribeMessage))
    console.log(`[v0] Subscribed to ${channel} for ${symbol} on ${exchange}`)
  }

  unsubscribe(exchange: string, channel: string, symbol: string): void {
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
      case "bitget":
        unsubscribeMessage = {
          op: "unsubscribe",
          args: [
            {
              channel: channel,
              instId: symbol,
            },
          ],
        }
        break
      default:
        throw new Error(`Unknown exchange: ${exchange}`)
    }

    ws.send(JSON.stringify(unsubscribeMessage))
    console.log(`[v0] Unsubscribed from ${channel} for ${symbol} on ${exchange}`)
  }

  private async handleReconnect(exchange: string, url: string): Promise<void> {
    const attempts = this.reconnectAttempts.get(exchange) || 0
    if (attempts >= this.maxReconnectAttempts) {
      console.error(`[v0] Max reconnection attempts reached for ${exchange}`)
      this.emit("maxReconnectAttemptsReached", exchange)
      return
    }

    this.reconnectAttempts.set(exchange, attempts + 1)
    const delay = this.reconnectDelay * Math.pow(2, attempts)

    console.log(`[v0] Reconnecting to ${exchange} in ${delay}ms (attempt ${attempts + 1})`)
    setTimeout(() => {
      this.connect(exchange, url)
    }, delay)
  }

  disconnect(exchange: string): void {
    const ws = this.connections.get(exchange)
    if (ws) {
      ws.close()
      this.connections.delete(exchange)
    }
  }

  disconnectAll(): void {
    for (const [exchange, ws] of this.connections) {
      ws.close()
    }
    this.connections.clear()
    this.subscriptions.clear()
  }

  isConnected(exchange: string): boolean {
    const ws = this.connections.get(exchange)
    return ws?.readyState === WebSocket.OPEN
  }
}

export const wsManager = new WebSocketManager()
