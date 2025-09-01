// Binance broker implementation
import { BaseBroker, type OrderRequest, type OrderResponse, type PositionInfo, type BalanceInfo, type SymbolFilters } from "./base-broker"
import { logger } from "@/lib/utils/logger"
import crypto from "crypto"

export class BinanceBroker extends BaseBroker {
  private baseUrl: string
  private wsUrl: string
  private ws: WebSocket | null = null
  private priceSubscriptions = new Map<string, (price: number) => void>()

  constructor(apiKey: string, apiSecret: string, testnet = false) {
    super(apiKey, apiSecret, testnet)
    this.baseUrl = testnet ? "https://testnet.binance.vision/api/v3" : "https://api.binance.com/api/v3"
    this.wsUrl = testnet ? "wss://testnet.binance.vision/ws" : "wss://stream.binance.com:9443/ws"
  }

  private createSignature(queryString: string): string {
    return crypto.createHmac("sha256", this.apiSecret).update(queryString).digest("hex")
  }

  private async makeRequest(endpoint: string, method = "GET", params: any = {}, signed = false) {
    const timestamp = Date.now()
    let queryString = new URLSearchParams({ ...params, timestamp: timestamp.toString() }).toString()

    if (signed) {
      const signature = this.createSignature(queryString)
      queryString += `&signature=${signature}`
    }

    const url = `${this.baseUrl}${endpoint}${queryString ? "?" + queryString : ""}`

    const headers: HeadersInit = {
      "X-MBX-APIKEY": this.apiKey,
      "Content-Type": "application/json",
    }

    try {
      const response = await fetch(url, { method, headers })

      if (!response.ok) {
        const error = await response.text()
        throw new Error(`Binance API error: ${error}`)
      }

      return await response.json()
    } catch (error) {
      logger.error("Binance API request failed", { endpoint, error })
      throw error
    }
  }

  async connect(): Promise<void> {
    try {
      // Test connection
      await this.makeRequest("/ping")
      logger.info("Connected to Binance API")

      // Initialize WebSocket for real-time data
      this.ws = new WebSocket(this.wsUrl)

      this.ws.onopen = () => {
        logger.info("Binance WebSocket connected")
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.e === "24hrTicker") {
            const callback = this.priceSubscriptions.get(data.s)
            if (callback) {
              callback(Number.parseFloat(data.c))
            }
          }
        } catch (error) {
          logger.error("WebSocket message parsing error", { error })
        }
      }

      this.ws.onerror = (error) => {
        logger.error("Binance WebSocket error", { error })
      }
    } catch (error) {
      logger.error("Failed to connect to Binance", { error })
      throw error
    }
  }

  async disconnect(): Promise<void> {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    logger.info("Disconnected from Binance")
  }

  async placeOrder(order: OrderRequest): Promise<OrderResponse> {
    try {
      // Fetch symbol filters and normalize order to comply with exchange rules
      const filters = await this.getSymbolInfo(order.symbol)
      order = this.normalizeOrder(filters, order)
      const params = {
        symbol: order.symbol,
        side: order.side.toUpperCase(),
        type: order.type.toUpperCase(),
        quantity: order.quantity.toString(),
        ...(order.price && { price: order.price.toString() }),
        ...(order.stopPrice && { stopPrice: order.stopPrice.toString() }),
        timeInForce: order.timeInForce || "GTC",
      }

      const result = await this.makeRequest("/order", "POST", params, true)

      return {
        orderId: result.orderId.toString(),
        symbol: result.symbol,
        side: result.side.toLowerCase() as "buy" | "sell",
        quantity: Number.parseFloat(result.origQty),
        price: Number.parseFloat(result.price || result.stopPrice || "0"),
        status: this.mapOrderStatus(result.status),
        executedQuantity: Number.parseFloat(result.executedQty),
        executedPrice: Number.parseFloat(result.cummulativeQuoteQty) / Number.parseFloat(result.executedQty) || 0,
        fees: 0, // Will be calculated from fills
        timestamp: new Date(result.transactTime),
      }
    } catch (error) {
      logger.error("Failed to place Binance order", { order, error })
      throw error
    }
  }

  async cancelOrder(symbol: string, orderId: string): Promise<boolean> {
    try {
      await this.makeRequest("/order", "DELETE", { symbol, orderId }, true)
      return true
    } catch (error) {
      logger.error("Failed to cancel Binance order", { symbol, orderId, error })
      return false
    }
  }

  async getOrderStatus(symbol: string, orderId: string): Promise<OrderResponse> {
    try {
      const result = await this.makeRequest("/order", "GET", { symbol, orderId }, true)

      return {
        orderId: result.orderId.toString(),
        symbol: result.symbol,
        side: result.side.toLowerCase() as "buy" | "sell",
        quantity: Number.parseFloat(result.origQty),
        price: Number.parseFloat(result.price),
        status: this.mapOrderStatus(result.status),
        executedQuantity: Number.parseFloat(result.executedQty),
        executedPrice: Number.parseFloat(result.cummulativeQuoteQty) / Number.parseFloat(result.executedQty) || 0,
        fees: 0,
        timestamp: new Date(result.time),
      }
    } catch (error) {
      logger.error("Failed to get Binance order status", { symbol, orderId, error })
      throw error
    }
  }

  async getBalance(): Promise<BalanceInfo[]> {
    try {
      const result = await this.makeRequest("/account", "GET", {}, true)

      return result.balances
        .filter((balance: any) => Number.parseFloat(balance.free) > 0 || Number.parseFloat(balance.locked) > 0)
        .map((balance: any) => ({
          asset: balance.asset,
          free: Number.parseFloat(balance.free),
          locked: Number.parseFloat(balance.locked),
          total: Number.parseFloat(balance.free) + Number.parseFloat(balance.locked),
        }))
    } catch (error) {
      logger.error("Failed to get Binance balance", { error })
      throw error
    }
  }

  async getPositions(): Promise<PositionInfo[]> {
    // Binance spot doesn't have positions, return empty array
    // For futures, this would query the futures API
    return []
  }

  async getPrice(symbol: string): Promise<number> {
    try {
      const result = await this.makeRequest("/ticker/price", "GET", { symbol })
      return Number.parseFloat(result.price)
    } catch (error) {
      logger.error("Failed to get Binance price", { symbol, error })
      throw error
    }
  }

  async getSymbolInfo(symbol: string): Promise<SymbolFilters> {
    try {
      const info = await this.makeRequest("/exchangeInfo", "GET")
      const s = info.symbols.find((x: any) => x.symbol === symbol)
      if (!s) throw new Error(`Symbol not found: ${symbol}`)
      const lot = s.filters.find((f: any) => f.filterType === "LOT_SIZE")
      const price = s.filters.find((f: any) => f.filterType === "PRICE_FILTER")
      const notional = s.filters.find((f: any) => f.filterType === "NOTIONAL") || { minNotional: 10 }
      return {
        symbol: s.symbol,
        baseAsset: s.baseAsset,
        quoteAsset: s.quoteAsset,
        minQty: parseFloat(lot.minQty),
        stepSize: parseFloat(lot.stepSize),
        tickSize: parseFloat(price.tickSize),
        minNotional: parseFloat(notional.minNotional || "10"),
        pricePrecision: s.quotePrecision,
        quantityPrecision: s.baseAssetPrecision,
      }
    } catch (error) {
      logger.error("Failed to fetch symbol info", { symbol, error })
      throw error
    }
  }

  subscribeToPrice(symbol: string, callback: (price: number) => void): void {
    this.priceSubscriptions.set(symbol, callback)

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          method: "SUBSCRIBE",
          params: [`${symbol.toLowerCase()}@ticker`],
          id: Date.now(),
        }),
      )
    }
  }

  unsubscribeFromPrice(symbol: string): void {
    this.priceSubscriptions.delete(symbol)

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          method: "UNSUBSCRIBE",
          params: [`${symbol.toLowerCase()}@ticker`],
          id: Date.now(),
        }),
      )
    }
  }

  private mapOrderStatus(status: string): OrderResponse["status"] {
    const statusMap: Record<string, OrderResponse["status"]> = {
      NEW: "new",
      FILLED: "filled",
      PARTIALLY_FILLED: "partially_filled",
      CANCELED: "cancelled",
      REJECTED: "rejected",
    }
    return statusMap[status] || "new"
  }
}
