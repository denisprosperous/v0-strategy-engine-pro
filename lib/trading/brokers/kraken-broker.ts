import crypto from "crypto"
import { BaseBroker, type OrderRequest, type OrderResponse, type BalanceResponse } from "./base-broker"
import { config } from "@/lib/config/environment"
import { logger } from "@/lib/utils/logger"

export class KrakenBroker extends BaseBroker {
  private apiKey: string
  private privateKey: string
  private baseUrl: string

  constructor() {
    super()
    this.apiKey = config.kraken.apiKey!
    this.privateKey = config.kraken.privateKey!
    this.baseUrl = "https://api.kraken.com"
  }

  private sign(path: string, request: string, secret: string, nonce: string): string {
    const message =
      path +
      crypto
        .createHash("sha256")
        .update(nonce + request)
        .digest()
    const hmac = crypto.createHmac("sha512", Buffer.from(secret, "base64"))
    return hmac.update(message).digest("base64")
  }

  private async makeRequest(endpoint: string, params: Record<string, any> = {}) {
    const nonce = Date.now().toString()
    const request = new URLSearchParams({ nonce, ...params }).toString()
    const signature = this.sign(`/0/private/${endpoint}`, request, this.privateKey, nonce)

    const response = await fetch(`${this.baseUrl}/0/private/${endpoint}`, {
      method: "POST",
      headers: {
        "API-Key": this.apiKey,
        "API-Sign": signature,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: request,
    })

    return response.json()
  }

  async getBalance(): Promise<BalanceResponse> {
    try {
      const data = await this.makeRequest("Balance")

      if (data.error && data.error.length > 0) {
        throw new Error(`Kraken API error: ${data.error.join(", ")}`)
      }

      const balances = Object.entries(data.result).map(([asset, balance]) => ({
        asset: asset,
        free: Number.parseFloat(balance as string),
        locked: 0,
        total: Number.parseFloat(balance as string),
      }))

      return { success: true, balances }
    } catch (error) {
      logger.error("Kraken balance fetch error", { error })
      return { success: false, error: error instanceof Error ? error.message : "Unknown error" }
    }
  }

  async placeOrder(order: OrderRequest): Promise<OrderResponse> {
    try {
      const params = {
        pair: order.symbol,
        type: order.side,
        ordertype: order.type,
        volume: order.quantity.toString(),
        ...(order.price && { price: order.price.toString() }),
      }

      const data = await this.makeRequest("AddOrder", params)

      if (data.error && data.error.length > 0) {
        throw new Error(`Kraken order error: ${data.error.join(", ")}`)
      }

      return {
        success: true,
        orderId: data.result.txid[0],
        status: "NEW",
        executedQty: 0,
        fills: [],
      }
    } catch (error) {
      logger.error("Kraken order placement error", { error })
      return {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      }
    }
  }

  async cancelOrder(symbol: string, orderId: string): Promise<{ success: boolean; error?: string }> {
    try {
      const data = await this.makeRequest("CancelOrder", { txid: orderId })

      if (data.error && data.error.length > 0) {
        throw new Error(`Kraken cancel error: ${data.error.join(", ")}`)
      }

      return { success: true }
    } catch (error) {
      logger.error("Kraken order cancellation error", { error })
      return { success: false, error: error instanceof Error ? error.message : "Unknown error" }
    }
  }

  async getOrderStatus(symbol: string, orderId: string): Promise<any> {
    try {
      const data = await this.makeRequest("QueryOrders", { txid: orderId })

      if (data.error && data.error.length > 0) {
        throw new Error(`Kraken status error: ${data.error.join(", ")}`)
      }

      return data.result[orderId]
    } catch (error) {
      logger.error("Kraken order status error", { error })
      throw error
    }
  }
}
