import {
  BaseBroker,
  type OrderRequest,
  type OrderResponse,
  type PositionInfo,
  type BalanceInfo,
  type SymbolFilters,
} from "./base-broker"
import { logger } from "@/lib/utils/logger"
import crypto from "crypto"

export class BybitBroker extends BaseBroker {
  private baseUrl: string
  private wsUrl: string
  private ws: WebSocket | null = null
  private priceSubscriptions = new Map<string, (price: number) => void>()

  constructor(apiKey: string, apiSecret: string, testnet = false) {
    super(apiKey, apiSecret, testnet)
    this.baseUrl = testnet ? "https://api-testnet.bybit.com" : "https://api.bybit.com"
    this.wsUrl = testnet ? "wss://stream-testnet.bybit.com/v5/public/spot" : "wss://stream.bybit.com/v5/public/spot"
  }

  private createSignature(timestamp: string, params: string): string {
    const message = timestamp + this.apiKey + "5000" + params
    return crypto.createHmac("sha256", this.apiSecret).update(message).digest("hex")
  }

  private async makeRequest(endpoint: string, method = "GET", params: any = {}) {
    const timestamp = Date.now().toString()
    const queryString = method === "GET" ? new URLSearchParams(params).toString() : ""
    const bodyString = method === "POST" ? JSON.stringify(params) : ""

    const signature = this.createSignature(timestamp, method === "GET" ? queryString : bodyString)

    const headers: HeadersInit = {
      "X-BAPI-API-KEY": this.apiKey,
      "X-BAPI-SIGN": signature,
      "X-BAPI-TIMESTAMP": timestamp,
      "X-BAPI-RECV-WINDOW": "5000",
      "Content-Type": "application/json",
    }

    const url = `${this.baseUrl}${endpoint}${queryString ? "?" + queryString : ""}`

    try {
      const response = await fetch(url, {
        method,
        headers,
        body: method === "POST" ? bodyString : undefined,
      })

      const result = await response.json()

      if (result.retCode !== 0) {
        throw new Error(`Bybit API error: ${result.retMsg}`)
      }

      return result.result
    } catch (error) {
      logger.error("Bybit API request failed", { endpoint, error })
      throw error
    }
  }

  async connect(): Promise<void> {
    try {
      await this.makeRequest("/v5/market/time")
      logger.info("Connected to Bybit API")

      this.ws = new WebSocket(this.wsUrl)

      this.ws.onopen = () => {
        logger.info("Bybit WebSocket connected")
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.topic?.startsWith("tickers.") && data.data) {
            const symbol = data.topic.replace("tickers.", "")
            const callback = this.priceSubscriptions.get(symbol)
            if (callback) {
              callback(Number.parseFloat(data.data.lastPrice))
            }
          }
        } catch (error) {
          logger.error("WebSocket message parsing error", { error })
        }
      }

      this.ws.onerror = (error) => {
        logger.error("Bybit WebSocket error", { error })
      }
    } catch (error) {
      logger.error("Failed to connect to Bybit", { error })
      throw error
    }
  }

  async disconnect(): Promise<void> {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    logger.info("Disconnected from Bybit")
  }

  async placeOrder(order: OrderRequest): Promise<OrderResponse> {
    try {
      const filters = await this.getSymbolInfo(order.symbol)
      order = this.normalizeOrder(filters, order)

      const orderData = {
        category: "spot",
        symbol: order.symbol,
        side: order.side.charAt(0).toUpperCase() + order.side.slice(1),
        orderType: order.type.charAt(0).toUpperCase() + order.type.slice(1),
        qty: order.quantity.toString(),
        ...(order.price && { price: order.price.toString() }),
        timeInForce: order.timeInForce || "GTC",
      }

      const result = await this.makeRequest("/v5/order/create", "POST", orderData)

      return {
        orderId: result.orderId,
        symbol: order.symbol,
        side: order.side,
        quantity: order.quantity,
        price: order.price || 0,
        status: "new",
        executedQuantity: 0,
        fees: 0,
        timestamp: new Date(),
      }
    } catch (error) {
      logger.error("Failed to place Bybit order", { order, error })
      throw error
    }
  }

  async cancelOrder(symbol: string, orderId: string): Promise<boolean> {
    try {
      await this.makeRequest("/v5/order/cancel", "POST", {
        category: "spot",
        symbol,
        orderId,
      })
      return true
    } catch (error) {
      logger.error("Failed to cancel Bybit order", { symbol, orderId, error })
      return false
    }
  }

  async getOrderStatus(symbol: string, orderId: string): Promise<OrderResponse> {
    try {
      const result = await this.makeRequest("/v5/order/realtime", "GET", {
        category: "spot",
        symbol,
        orderId,
      })

      const order = result.list[0]

      return {
        orderId: order.orderId,
        symbol: order.symbol,
        side: order.side.toLowerCase() as "buy" | "sell",
        quantity: Number.parseFloat(order.qty),
        price: Number.parseFloat(order.price),
        status: this.mapOrderStatus(order.orderStatus),
        executedQuantity: Number.parseFloat(order.cumExecQty),
        executedPrice: Number.parseFloat(order.avgPrice || order.price),
        fees: Number.parseFloat(order.cumExecFee || "0"),
        timestamp: new Date(Number.parseInt(order.createdTime)),
      }
    } catch (error) {
      logger.error("Failed to get Bybit order status", { symbol, orderId, error })
      throw error
    }
  }

  async getBalance(): Promise<BalanceInfo[]> {
    try {
      const result = await this.makeRequest("/v5/account/wallet-balance", "GET", {
        accountType: "UNIFIED",
      })

      const coins = result.list[0]?.coin || []

      return coins
        .filter((coin: any) => Number.parseFloat(coin.walletBalance) > 0)
        .map((coin: any) => ({
          asset: coin.coin,
          free: Number.parseFloat(coin.availableToWithdraw),
          locked: Number.parseFloat(coin.locked || "0"),
          total: Number.parseFloat(coin.walletBalance),
        }))
    } catch (error) {
      logger.error("Failed to get Bybit balance", { error })
      throw error
    }
  }

  async getPositions(): Promise<PositionInfo[]> {
    try {
      const result = await this.makeRequest("/v5/position/list", "GET", {
        category: "linear",
        settleCoin: "USDT",
      })

      return result.list
        .filter((position: any) => Number.parseFloat(position.size) > 0)
        .map((position: any) => ({
          symbol: position.symbol,
          side: position.side.toLowerCase() as "long" | "short",
          size: Number.parseFloat(position.size),
          entryPrice: Number.parseFloat(position.avgPrice),
          markPrice: Number.parseFloat(position.markPrice),
          unrealizedPnl: Number.parseFloat(position.unrealisedPnl),
          percentage: (Number.parseFloat(position.unrealisedPnl) / Number.parseFloat(position.positionValue)) * 100,
        }))
    } catch (error) {
      logger.error("Failed to get Bybit positions", { error })
      throw error
    }
  }

  async getPrice(symbol: string): Promise<number> {
    try {
      const result = await this.makeRequest("/v5/market/tickers", "GET", {
        category: "spot",
        symbol,
      })
      return Number.parseFloat(result.list[0].lastPrice)
    } catch (error) {
      logger.error("Failed to get Bybit price", { symbol, error })
      throw error
    }
  }

  async getSymbolInfo(symbol: string): Promise<SymbolFilters> {
    try {
      const result = await this.makeRequest("/v5/market/instruments-info", "GET", {
        category: "spot",
        symbol,
      })

      const info = result.list[0]

      return {
        symbol: info.symbol,
        baseAsset: info.baseCoin,
        quoteAsset: info.quoteCoin,
        minQty: Number.parseFloat(info.lotSizeFilter.minOrderQty),
        stepSize: Number.parseFloat(info.lotSizeFilter.basePrecision),
        tickSize: Number.parseFloat(info.priceFilter.tickSize),
        minNotional: Number.parseFloat(info.lotSizeFilter.minOrderAmt || "1"),
        pricePrecision: info.priceScale || 8,
        quantityPrecision: info.lotSizeFilter.basePrecision?.split(".")[1]?.length || 8,
      }
    } catch (error) {
      logger.error("Failed to get Bybit symbol info", { symbol, error })
      throw error
    }
  }

  subscribeToPrice(symbol: string, callback: (price: number) => void): void {
    this.priceSubscriptions.set(symbol, callback)

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          op: "subscribe",
          args: [`tickers.${symbol}`],
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
          args: [`tickers.${symbol}`],
        }),
      )
    }
  }

  private mapOrderStatus(status: string): OrderResponse["status"] {
    const statusMap: Record<string, OrderResponse["status"]> = {
      New: "new",
      PartiallyFilled: "partially_filled",
      Filled: "filled",
      Cancelled: "cancelled",
      Rejected: "rejected",
    }
    return statusMap[status] || "new"
  }
}
