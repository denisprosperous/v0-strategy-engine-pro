// Coinbase Advanced Trade API broker implementation
import { BaseBroker, type OrderRequest, type OrderResponse, type PositionInfo, type BalanceInfo } from "./base-broker"
import { logger } from "@/lib/utils/logger"
import crypto from "crypto"

export class CoinbaseBroker extends BaseBroker {
  private baseUrl: string
  private wsUrl: string
  private ws: WebSocket | null = null
  private priceSubscriptions = new Map<string, (price: number) => void>()

  constructor(apiKey: string, apiSecret: string, testnet = false) {
    super(apiKey, apiSecret, testnet)
    this.baseUrl = testnet ? "https://api-public.sandbox.exchange.coinbase.com" : "https://api.exchange.coinbase.com"
    this.wsUrl = testnet ? "wss://ws-feed-public.sandbox.exchange.coinbase.com" : "wss://ws-feed.exchange.coinbase.com"
  }

  private createSignature(timestamp: string, method: string, requestPath: string, body = ""): string {
    const message = timestamp + method + requestPath + body
    return crypto.createHmac("sha256", Buffer.from(this.apiSecret, "base64")).update(message).digest("base64")
  }

  private async makeRequest(endpoint: string, method = "GET", body: any = null) {
    const timestamp = Math.floor(Date.now() / 1000).toString()
    const requestPath = endpoint
    const bodyString = body ? JSON.stringify(body) : ""

    const signature = this.createSignature(timestamp, method, requestPath, bodyString)

    const headers: HeadersInit = {
      "CB-ACCESS-KEY": this.apiKey,
      "CB-ACCESS-SIGN": signature,
      "CB-ACCESS-TIMESTAMP": timestamp,
      "CB-ACCESS-PASSPHRASE": "your-passphrase", // This should be provided separately
      "Content-Type": "application/json",
    }

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method,
        headers,
        body: bodyString || undefined,
      })

      if (!response.ok) {
        const error = await response.text()
        throw new Error(`Coinbase API error: ${error}`)
      }

      return await response.json()
    } catch (error) {
      logger.error("Coinbase API request failed", { endpoint, error })
      throw error
    }
  }

  async connect(): Promise<void> {
    try {
      // Test connection by getting server time
      await this.makeRequest("/time")
      logger.info("Connected to Coinbase API")

      // Initialize WebSocket for real-time data
      this.ws = new WebSocket(this.wsUrl)

      this.ws.onopen = () => {
        logger.info("Coinbase WebSocket connected")
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === "ticker" && data.product_id) {
            const callback = this.priceSubscriptions.get(data.product_id)
            if (callback) {
              callback(Number.parseFloat(data.price))
            }
          }
        } catch (error) {
          logger.error("WebSocket message parsing error", { error })
        }
      }

      this.ws.onerror = (error) => {
        logger.error("Coinbase WebSocket error", { error })
      }
    } catch (error) {
      logger.error("Failed to connect to Coinbase", { error })
      throw error
    }
  }

  async disconnect(): Promise<void> {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    logger.info("Disconnected from Coinbase")
  }

  async placeOrder(order: OrderRequest): Promise<OrderResponse> {
    try {
      const orderData = {
        product_id: order.symbol,
        side: order.side,
        order_configuration: {
          [order.type === "market" ? "market_market_ioc" : "limit_limit_gtc"]: {
            ...(order.type === "market"
              ? { quote_size: (order.quantity * (order.price || 0)).toString() }
              : { base_size: order.quantity.toString(), limit_price: order.price?.toString() }),
          },
        },
      }

      const result = await this.makeRequest("/api/v3/brokerage/orders", "POST", orderData)

      return {
        orderId: result.order_id,
        symbol: result.product_id,
        side: result.side as "buy" | "sell",
        quantity: Number.parseFloat(result.order_configuration?.limit_limit_gtc?.base_size || "0"),
        price: Number.parseFloat(result.order_configuration?.limit_limit_gtc?.limit_price || "0"),
        status: this.mapOrderStatus(result.status),
        executedQuantity: Number.parseFloat(result.filled_size || "0"),
        executedPrice: Number.parseFloat(result.average_filled_price || "0"),
        fees: Number.parseFloat(result.total_fees || "0"),
        timestamp: new Date(result.created_time),
      }
    } catch (error) {
      logger.error("Failed to place Coinbase order", { order, error })
      throw error
    }
  }

  async cancelOrder(symbol: string, orderId: string): Promise<boolean> {
    try {
      await this.makeRequest(`/api/v3/brokerage/orders/batch_cancel`, "POST", {
        order_ids: [orderId],
      })
      return true
    } catch (error) {
      logger.error("Failed to cancel Coinbase order", { symbol, orderId, error })
      return false
    }
  }

  async getOrderStatus(symbol: string, orderId: string): Promise<OrderResponse> {
    try {
      const result = await this.makeRequest(`/api/v3/brokerage/orders/historical/${orderId}`)

      return {
        orderId: result.order_id,
        symbol: result.product_id,
        side: result.side as "buy" | "sell",
        quantity: Number.parseFloat(result.order_configuration?.limit_limit_gtc?.base_size || "0"),
        price: Number.parseFloat(result.order_configuration?.limit_limit_gtc?.limit_price || "0"),
        status: this.mapOrderStatus(result.status),
        executedQuantity: Number.parseFloat(result.filled_size || "0"),
        executedPrice: Number.parseFloat(result.average_filled_price || "0"),
        fees: Number.parseFloat(result.total_fees || "0"),
        timestamp: new Date(result.created_time),
      }
    } catch (error) {
      logger.error("Failed to get Coinbase order status", { symbol, orderId, error })
      throw error
    }
  }

  async getBalance(): Promise<BalanceInfo[]> {
    try {
      const result = await this.makeRequest("/api/v3/brokerage/accounts")

      return result.accounts
        .filter((account: any) => Number.parseFloat(account.available_balance.value) > 0)
        .map((account: any) => ({
          asset: account.currency,
          free: Number.parseFloat(account.available_balance.value),
          locked: Number.parseFloat(account.hold.value || "0"),
          total: Number.parseFloat(account.available_balance.value) + Number.parseFloat(account.hold.value || "0"),
        }))
    } catch (error) {
      logger.error("Failed to get Coinbase balance", { error })
      throw error
    }
  }

  async getPositions(): Promise<PositionInfo[]> {
    // Coinbase doesn't have positions for spot trading
    return []
  }

  async getPrice(symbol: string): Promise<number> {
    try {
      const result = await this.makeRequest(`/api/v3/brokerage/products/${symbol}/ticker`)
      return Number.parseFloat(result.price)
    } catch (error) {
      logger.error("Failed to get Coinbase price", { symbol, error })
      throw error
    }
  }

  subscribeToPrice(symbol: string, callback: (price: number) => void): void {
    this.priceSubscriptions.set(symbol, callback)

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          type: "subscribe",
          product_ids: [symbol],
          channels: ["ticker"],
        }),
      )
    }
  }

  unsubscribeFromPrice(symbol: string): void {
    this.priceSubscriptions.delete(symbol)

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          type: "unsubscribe",
          product_ids: [symbol],
          channels: ["ticker"],
        }),
      )
    }
  }

  private mapOrderStatus(status: string): OrderResponse["status"] {
    const statusMap: Record<string, OrderResponse["status"]> = {
      OPEN: "new",
      FILLED: "filled",
      CANCELLED: "cancelled",
      EXPIRED: "cancelled",
      FAILED: "rejected",
      UNKNOWN: "new",
    }
    return statusMap[status] || "new"
  }
}
