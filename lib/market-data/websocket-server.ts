// WebSocket server for real-time market data streaming
import { WebSocketServer } from "ws"
import { marketDataAggregator } from "./aggregator"
import { sentimentAnalyzer } from "../sentiment/analyzer"
import { logger } from "@/lib/utils/logger"

interface WebSocketClient {
  ws: any
  subscriptions: Set<string>
  userId?: string
}

export class MarketDataWebSocketServer {
  private wss: WebSocketServer | null = null
  private clients = new Map<string, WebSocketClient>()
  private isRunning = false

  async start(port = 8080): Promise<void> {
    if (this.isRunning) return

    this.wss = new WebSocketServer({ port })
    this.isRunning = true

    this.wss.on("connection", (ws, req) => {
      const clientId = this.generateClientId()
      const client: WebSocketClient = {
        ws,
        subscriptions: new Set(),
      }

      this.clients.set(clientId, client)
      logger.info("WebSocket client connected", { clientId })

      ws.on("message", (message) => {
        try {
          const data = JSON.parse(message.toString())
          this.handleClientMessage(clientId, data)
        } catch (error) {
          logger.error("Invalid WebSocket message", { clientId, error })
        }
      })

      ws.on("close", () => {
        this.clients.delete(clientId)
        logger.info("WebSocket client disconnected", { clientId })
      })

      ws.on("error", (error) => {
        logger.error("WebSocket client error", { clientId, error })
        this.clients.delete(clientId)
      })

      // Send welcome message
      ws.send(
        JSON.stringify({
          type: "welcome",
          clientId,
          timestamp: new Date().toISOString(),
        }),
      )
    })

    logger.info("Market data WebSocket server started", { port })
  }

  async stop(): Promise<void> {
    if (!this.isRunning || !this.wss) return

    this.wss.close()
    this.clients.clear()
    this.isRunning = false

    logger.info("Market data WebSocket server stopped")
  }

  private handleClientMessage(clientId: string, message: any): void {
    const client = this.clients.get(clientId)
    if (!client) return

    switch (message.type) {
      case "subscribe_price":
        this.handlePriceSubscription(clientId, message.symbol)
        break

      case "unsubscribe_price":
        this.handlePriceUnsubscription(clientId, message.symbol)
        break

      case "subscribe_sentiment":
        this.handleSentimentSubscription(clientId, message.symbol)
        break

      case "get_historical":
        this.handleHistoricalDataRequest(clientId, message)
        break

      default:
        logger.warn("Unknown WebSocket message type", { clientId, type: message.type })
    }
  }

  private handlePriceSubscription(clientId: string, symbol: string): void {
    const client = this.clients.get(clientId)
    if (!client) return

    client.subscriptions.add(`price:${symbol}`)

    // Subscribe to market data aggregator
    marketDataAggregator.subscribe(symbol, (priceData) => {
      if (client.ws.readyState === 1) {
        // WebSocket.OPEN
        client.ws.send(
          JSON.stringify({
            type: "price_update",
            symbol,
            price: priceData.price,
            volume: priceData.volume,
            change24h: priceData.change24h,
            timestamp: priceData.timestamp,
          }),
        )
      }
    })

    logger.info("Client subscribed to price updates", { clientId, symbol })
  }

  private handlePriceUnsubscription(clientId: string, symbol: string): void {
    const client = this.clients.get(clientId)
    if (!client) return

    client.subscriptions.delete(`price:${symbol}`)
    // Note: We'd need to track callbacks to properly unsubscribe from aggregator

    logger.info("Client unsubscribed from price updates", { clientId, symbol })
  }

  private handleSentimentSubscription(clientId: string, symbol: string): void {
    const client = this.clients.get(clientId)
    if (!client) return

    client.subscriptions.add(`sentiment:${symbol}`)

    // Send current sentiment immediately
    sentimentAnalyzer
      .getSentiment(symbol)
      .then((sentiment) => {
        if (client.ws.readyState === 1) {
          client.ws.send(
            JSON.stringify({
              type: "sentiment_update",
              symbol,
              score: sentiment.score,
              confidence: sentiment.confidence,
              sources: sentiment.sources,
              timestamp: sentiment.timestamp,
            }),
          )
        }
      })
      .catch((error) => {
        logger.error("Failed to get sentiment for WebSocket client", { clientId, symbol, error })
      })

    logger.info("Client subscribed to sentiment updates", { clientId, symbol })
  }

  private async handleHistoricalDataRequest(clientId: string, message: any): Promise<void> {
    const client = this.clients.get(clientId)
    if (!client) return

    try {
      const { symbol, timeframe = "1h", limit = 100 } = message
      const data = await marketDataAggregator.getHistoricalData(symbol, timeframe, limit)

      client.ws.send(
        JSON.stringify({
          type: "historical_data",
          symbol,
          timeframe,
          data,
          requestId: message.requestId,
        }),
      )
    } catch (error) {
      client.ws.send(
        JSON.stringify({
          type: "error",
          message: "Failed to fetch historical data",
          requestId: message.requestId,
        }),
      )
    }
  }

  private generateClientId(): string {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  broadcast(message: any): void {
    const messageStr = JSON.stringify(message)

    for (const [clientId, client] of this.clients) {
      if (client.ws.readyState === 1) {
        // WebSocket.OPEN
        try {
          client.ws.send(messageStr)
        } catch (error) {
          logger.error("Failed to broadcast to client", { clientId, error })
          this.clients.delete(clientId)
        }
      }
    }
  }
}

// Singleton instance
export const marketDataWS = new MarketDataWebSocketServer()
