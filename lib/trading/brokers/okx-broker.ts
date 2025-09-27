// OKX exchange broker implementation
import { BaseBroker, type OrderRequest, type OrderResponse, type PositionInfo, type BalanceInfo } from "./base-broker"
import { logger } from "@/lib/utils/logger"
import crypto from "crypto"

export class OKXBroker extends BaseBroker {
  private baseUrl: string
  private wsUrl: string
  private ws: WebSocket | null = null
  private priceSubscriptions = new Map<string, (price: number) => void>()
  private passphrase: string

  constructor(apiKey: string, apiSecret: string, passphrase: string, testnet = false) {
    super(apiKey, apiSecret, testnet)
    this.passphrase = passphrase
    this.baseUrl = testnet ? "https://www.okx.com" : "https://www.okx.com"
    this.wsUrl = testnet ? "wss://wspap.okx.com:8443/ws/v5/public?brokerId=9999" : "wss://ws.okx.com:8443/ws/v5/public"
  }

  private createSignature(timestamp: string, method: string, requestPath: string, body = ""): string {
    const message = timestamp + method + requestPath + body
    return crypto.createHmac("sha256", this.apiSecret).update(message).digest("base64")
  }

  private async makeRequest(endpoint: string, method = "GET", body: any = null) {
    const timestamp = new Date().toISOString()
    const requestPath = endpoint
    const bodyString = body ? JSON.stringify(body) : ""

    const signature = this.createSignature(timestamp, method, requestPath, bodyString)

    const headers: HeadersInit = {
      "OK-ACCESS-KEY": this.apiKey,
      "OK-ACCESS-SIGN": signature,
      "OK-ACCESS-TIMESTAMP": timestamp,
      "OK-ACCESS-PASSPHRASE": this.passphrase,
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
        throw new Error(`OKX API error: ${error}`)
      }

      const result = await response.json()
      if (result.code !== "0") {
        throw new Error(`OKX API error: ${result.msg}`)
      }

      return result.data
    } catch (error) {
      logger.error("OKX API request failed", { endpoint, error })
      throw error
    }
  }

  async connect(): Promise<void> {
    try {
      // Test connection by getting server time
      await this.makeRequest("/api/v5/public/time")
      logger.info("Connected to OKX API")

      // Initialize WebSocket for real-time data
      this.ws = new WebSocket(this.wsUrl)

      this.ws.onopen = () => {
        logger.info("OKX WebSocket connected")
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.arg?.channel === "tickers" && data.data) {
            const ticker = data.data[0]
            const callback = this.priceSubscriptions.get(ticker.instId)
            if (callback) {
              callback(Number.parseFloat(ticker.last))
            }
          }
        } catch (error) {
          logger.error("WebSocket message parsing error", { error })
        }
      }

      this.ws.onerror = (error) => {
        logger.error("OKX WebSocket error", { error })
      }
    } catch (error) {
      logger.error("Failed to connect to OKX", { error })
      throw error
    }
  }

  async disconnect(): Promise<void> {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    logger.info("Disconnected from OKX")
  }

  async placeOrder(order: OrderRequest): Promise<OrderResponse> {
    try {
      const orderData = {
        instId: order.symbol,
        tdMode: "cash", // Trading mode: cash for spot
        side: order.side,
        ordType: order.type === "market" ? "market" : "limit",
        sz: order.quantity.toString(),
        ...(order.price && { px: order.price.toString() }),
      }

      const result = await this.makeRequest("/api/v5/trade/order", "POST", [orderData])
      const orderResult = result[0]

      return {
        orderId: orderResult.ordId,
        symbol: orderResult.instId,
        side: orderResult.side as "buy" | "sell",
        quantity: Number.parseFloat(orderResult.sz),
        price: Number.parseFloat(orderResult.px || "0"),
        status: this.mapOrderStatus(orderResult.state),
        executedQuantity: Number.parseFloat(orderResult.fillSz || "0"),
        executedPrice: Number.parseFloat(orderResult.avgPx || "0"),
        fees: Number.parseFloat(orderResult.fee || "0"),
        timestamp: new Date(Number.parseInt(orderResult.cTime)),
      }
    } catch (error) {
      logger.error("Failed to place OKX order", { order, error })
      throw error
    }
  }

  async cancelOrder(symbol: string, orderId: string): Promise<boolean> {
    try {
      await this.makeRequest("/api/v5/trade/cancel-order", "POST", [
        {
          instId: symbol,
          ordId: orderId,
        },
      ])
      return true
    } catch (error) {
      logger.error("Failed to cancel OKX order", { symbol, orderId, error })
      return false
    }
  }

  async getOrderStatus(symbol: string, orderId: string): Promise<OrderResponse> {
    try {
      const result = await this.makeRequest(`/api/v5/trade/order?instId=${symbol}&ordId=${orderId}`)
      const order = result[0]

      return {
        orderId: order.ordId,
        symbol: order.instId,
        side: order.side as "buy" | "sell",
        quantity: Number.parseFloat(order.sz),
        price: Number.parseFloat(order.px),
        status: this.mapOrderStatus(order.state),
        executedQuantity: Number.parseFloat(order.fillSz || "0"),
        executedPrice: Number.parseFloat(order.avgPx || "0"),
        fees: Number.parseFloat(order.fee || "0"),
        timestamp: new Date(Number.parseInt(order.cTime)),
      }
    } catch (error) {
      logger.error("Failed to get OKX order status", { symbol, orderId, error })
      throw error
    }
  }

  async getBalance(): Promise<BalanceInfo[]> {
    try {
      const result = await this.makeRequest("/api/v5/account/balance")
      const balances = result[0]?.details || []

      return balances
        .filter((balance: any) => Number.parseFloat(balance.availBal) > 0)
        .map((balance: any) => ({
          asset: balance.ccy,
          free: Number.parseFloat(balance.availBal),
          locked: Number.parseFloat(balance.frozenBal || "0"),
          total: Number.parseFloat(balance.bal),
        }))
    } catch (error) {
      logger.error("Failed to get OKX balance", { error })
      throw error
    }
  }

  async getPositions(): Promise<PositionInfo[]> {
    try {
      const result = await this.makeRequest("/api/v5/account/positions")

      return result
        .filter((position: any) => Number.parseFloat(position.pos) !== 0)
        .map((position: any) => ({
          symbol: position.instId,
          side: Number.parseFloat(position.pos) > 0 ? "long" : "short",
          size: Math.abs(Number.parseFloat(position.pos)),
          entryPrice: Number.parseFloat(position.avgPx),
          markPrice: Number.parseFloat(position.markPx),
          unrealizedPnl: Number.parseFloat(position.upl),
          percentage: Number.parseFloat(position.uplRatio) * 100,
        }))
    } catch (error) {
      logger.error("Failed to get OKX positions", { error })
      throw error
    }
  }

  async getPrice(symbol: string): Promise<number> {
    try {
      const result = await this.makeRequest(`/api/v5/market/ticker?instId=${symbol}`)
      return Number.parseFloat(result[0].last)
    } catch (error) {
      logger.error("Failed to get OKX price", { symbol, error })
      throw error
    }
  }

  subscribeToPrice(symbol: string, callback: (price: number) => void): void {
    this.priceSubscriptions.set(symbol, callback)

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          op: "subscribe",
          args: [
            {
              channel: "tickers",
              instId: symbol,
            },
          ],
        }),
      )
    }
  }

  unsubscribeFromPrice(symbol: string): void {
    this.priceSubscriptions.delete(symbol)

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          op: "unsubscribe",
          args: [
            {
              channel: "tickers",
              instId: symbol,
            },
          ],
        }),
      )
    }
  }

  private mapOrderStatus(status: string): OrderResponse["status"] {
    const statusMap: Record<string, OrderResponse["status"]> = {
      live: "new",
      filled: "filled",
      partially_filled: "partially_filled",
      canceled: "cancelled",
      mmp_canceled: "cancelled",
    }
    return statusMap[status] || "new"
  }
}
