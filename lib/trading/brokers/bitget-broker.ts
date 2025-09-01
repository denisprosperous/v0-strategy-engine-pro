import crypto from "crypto"
import { BaseBroker, type OrderRequest, type OrderResponse, type BalanceResponse, type SymbolFilters } from "./base-broker"
import { config } from "@/lib/config/environment"
import { logger } from "@/lib/utils/logger"

export class BitgetBroker extends BaseBroker {
  private apiKey: string
  private apiSecret: string
  private passphrase: string
  private baseUrl: string

  constructor() {
    super()
    this.apiKey = config.bitget.apiKey!
    this.apiSecret = config.bitget.apiSecret!
    this.passphrase = config.bitget.passphrase!
    this.baseUrl = config.bitget.testnet ? "https://api.bitget.com" : "https://api.bitget.com"
  }

  private sign(timestamp: string, method: string, requestPath: string, body = ""): string {
    const message = timestamp + method + requestPath + body
    return crypto.createHmac("sha256", this.apiSecret).update(message).digest("base64")
  }

  private getHeaders(method: string, requestPath: string, body = "") {
    const timestamp = Date.now().toString()
    const sign = this.sign(timestamp, method, requestPath, body)

    return {
      "ACCESS-KEY": this.apiKey,
      "ACCESS-SIGN": sign,
      "ACCESS-TIMESTAMP": timestamp,
      "ACCESS-PASSPHRASE": this.passphrase,
      "Content-Type": "application/json",
    }
  }

  async getBalance(): Promise<BalanceResponse> {
    try {
      const requestPath = "/api/spot/v1/account/assets"
      const headers = this.getHeaders("GET", requestPath)

      const response = await fetch(`${this.baseUrl}${requestPath}`, {
        method: "GET",
        headers,
      })

      const data = await response.json()

      if (data.code !== "00000") {
        throw new Error(`Bitget API error: ${data.msg}`)
      }

      const balances = data.data.map((asset: any) => ({
        asset: asset.coinName,
        free: Number.parseFloat(asset.available),
        locked: Number.parseFloat(asset.frozen),
        total: Number.parseFloat(asset.available) + Number.parseFloat(asset.frozen),
      }))

      return { success: true, balances }
    } catch (error) {
      logger.error("Bitget balance fetch error", { error })
      return { success: false, error: error instanceof Error ? error.message : "Unknown error" }
    }
  }

  async placeOrder(order: OrderRequest): Promise<OrderResponse> {
    try {
      const filters = await this.getSymbolInfo(order.symbol)
      order = this.normalizeOrder(filters, order)
      const requestPath = "/api/spot/v1/trade/orders"
      const body = JSON.stringify({
        symbol: order.symbol,
        side: order.side,
        orderType: order.type,
        force: "normal",
        price: order.price?.toString(),
        size: order.quantity.toString(),
      })

      const headers = this.getHeaders("POST", requestPath, body)

      const response = await fetch(`${this.baseUrl}${requestPath}`, {
        method: "POST",
        headers,
        body,
      })

      const data = await response.json()

      if (data.code !== "00000") {
        throw new Error(`Bitget order error: ${data.msg}`)
      }

      return {
        success: true,
        orderId: data.data.orderId,
        status: "NEW",
        executedQty: 0,
        fills: [],
      }
    } catch (error) {
      logger.error("Bitget order placement error", { error })
      return {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      }
    }
  }

  async cancelOrder(symbol: string, orderId: string): Promise<{ success: boolean; error?: string }> {
    try {
      const requestPath = "/api/spot/v1/trade/cancel-order"
      const body = JSON.stringify({
        symbol,
        orderId,
      })

      const headers = this.getHeaders("POST", requestPath, body)

      const response = await fetch(`${this.baseUrl}${requestPath}`, {
        method: "POST",
        headers,
        body,
      })

      const data = await response.json()

      if (data.code !== "00000") {
        throw new Error(`Bitget cancel error: ${data.msg}`)
      }

      return { success: true }
    } catch (error) {
      logger.error("Bitget order cancellation error", { error })
      return { success: false, error: error instanceof Error ? error.message : "Unknown error" }
    }
  }

  async getOrderStatus(symbol: string, orderId: string): Promise<any> {
    try {
      const requestPath = `/api/spot/v1/trade/orderInfo?symbol=${symbol}&orderId=${orderId}`
      const headers = this.getHeaders("GET", requestPath)

      const response = await fetch(`${this.baseUrl}${requestPath}`, {
        method: "GET",
        headers,
      })

      const data = await response.json()

      if (data.code !== "00000") {
        throw new Error(`Bitget status error: ${data.msg}`)
      }

      return data.data
    } catch (error) {
      logger.error("Bitget order status error", { error })
      throw error
    }
  }

  async getSymbolInfo(symbol: string): Promise<SymbolFilters> {
    try {
      const requestPath = "/api/spot/v1/public/products"
      const response = await fetch(`${this.baseUrl}${requestPath}`)
      const data = await response.json()
      if (data.code !== "00000") throw new Error(`Bitget symbol error: ${data.msg}`)
      const s = data.data.find((x: any) => x.symbol === symbol)
      if (!s) throw new Error(`Symbol not found: ${symbol}`)
      return {
        symbol: s.symbol,
        baseAsset: s.baseCoin,
        quoteAsset: s.quoteCoin,
        minQty: parseFloat(s.minTradeNum),
        stepSize: parseFloat(s.quantityPrecision ? `1e-${s.quantityPrecision}` : "0.000001"),
        tickSize: parseFloat(s.pricePrecision ? `1e-${s.pricePrecision}` : "0.000001"),
        minNotional: parseFloat(s.minTradeAmount || "5"),
        pricePrecision: s.pricePrecision || 6,
        quantityPrecision: s.quantityPrecision || 6,
      }
    } catch (error) {
      logger.error("Bitget getSymbolInfo error", { symbol, error })
      throw error
    }
  }
}
