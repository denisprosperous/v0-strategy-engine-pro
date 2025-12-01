// =============================================================================
// Phemex Exchange Broker Implementation
// =============================================================================
// Phemex - Professional contract trading platform
// API Documentation: https://github.com/phemex/phemex-api-docs

import { BaseBroker, type OrderResult, type Position, type BalanceInfo, type OrderBook } from "./base-broker"
import { config } from "@/lib/config/environment"
import crypto from "crypto"

export class PhemexBroker extends BaseBroker {
  private apiKey: string
  private apiSecret: string
  private baseUrl: string
  private wsUrl: string

  constructor() {
    super()
    this.apiKey = config.phemex.apiKey
    this.apiSecret = config.phemex.apiSecret
    this.baseUrl = config.phemex.baseUrl
    this.wsUrl = config.phemex.wsUrl
  }

  private generateSignature(path: string, queryString: string, expiry: number): string {
    const message = path + queryString + expiry.toString()
    return crypto.createHmac("sha256", this.apiSecret).update(message).digest("hex")
  }

  private async makeRequest(
    method: string,
    path: string,
    params: Record<string, any> = {},
    signed = false,
  ): Promise<any> {
    const url = new URL(path, this.baseUrl)
    let queryString = ""

    if (method === "GET" && Object.keys(params).length > 0) {
      queryString = new URLSearchParams(params).toString()
      url.search = queryString
    }

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    }

    if (signed && this.apiKey && this.apiSecret) {
      const expiry = Math.floor(Date.now() / 1000) + 60 // 60 seconds expiry
      const signature = this.generateSignature(path, queryString, expiry)

      headers["x-phemex-access-token"] = this.apiKey
      headers["x-phemex-request-expiry"] = expiry.toString()
      headers["x-phemex-request-signature"] = signature
    }

    try {
      const response = await fetch(url.toString(), {
        method,
        headers,
        body: method !== "GET" ? JSON.stringify(params) : undefined,
        signal: AbortSignal.timeout(10000),
      })

      const data = await response.json()

      if (data.code !== 0) {
        throw new Error(data.msg || "Phemex API error")
      }

      return data.data || data
    } catch (error) {
      console.error("Phemex API error:", error)
      throw error
    }
  }

  async connect(): Promise<boolean> {
    try {
      // Test connection with server time endpoint
      const response = await fetch(`${this.baseUrl}/public/time`, {
        signal: AbortSignal.timeout(5000),
      })
      return response.ok
    } catch {
      return false
    }
  }

  async disconnect(): Promise<void> {
    // Clean up WebSocket connections if any
  }

  async getBalance(): Promise<BalanceInfo> {
    if (!this.apiKey || !this.apiSecret) {
      return {
        total: 0,
        available: 0,
        reserved: 0,
        currency: "USDT",
      }
    }

    try {
      const data = await this.makeRequest("GET", "/accounts/accountPositions", { currency: "USDT" }, true)

      const account = data.account || {}
      const totalBalance = (account.accountBalanceEv || 0) / 100000000
      const availableBalance = (account.availBalanceEv || 0) / 100000000

      return {
        total: totalBalance,
        available: availableBalance,
        reserved: totalBalance - availableBalance,
        currency: "USDT",
      }
    } catch (error) {
      console.error("Failed to get Phemex balance:", error)
      return { total: 0, available: 0, reserved: 0, currency: "USDT" }
    }
  }

  async getPrice(symbol: string): Promise<number> {
    try {
      // Convert symbol format (BTC/USDT -> BTCUSDT)
      const formattedSymbol = symbol.replace("/", "")

      const response = await fetch(`${this.baseUrl}/md/v2/ticker/24hr?symbol=${formattedSymbol}`, {
        signal: AbortSignal.timeout(5000),
      })

      const data = await response.json()

      if (data.result && data.result.lastEp) {
        return data.result.lastEp / 10000 // Scale factor for price
      }

      return 0
    } catch (error) {
      console.error("Failed to get Phemex price:", error)
      return 0
    }
  }

  async placeOrder(
    symbol: string,
    side: "buy" | "sell",
    amount: number,
    price?: number,
    orderType: "market" | "limit" = "market",
  ): Promise<OrderResult> {
    if (!this.apiKey || !this.apiSecret) {
      return {
        success: false,
        orderId: "",
        message: "API credentials not configured",
      }
    }

    try {
      const formattedSymbol = symbol.replace("/", "")

      const params: Record<string, any> = {
        symbol: formattedSymbol,
        side: side === "buy" ? "Buy" : "Sell",
        orderQtyEv: Math.floor(amount * 100000000), // Scale factor
        ordType: orderType === "market" ? "Market" : "Limit",
      }

      if (orderType === "limit" && price) {
        params.priceEp = Math.floor(price * 10000) // Scale factor for price
      }

      const data = await this.makeRequest("POST", "/orders", params, true)

      return {
        success: true,
        orderId: data.orderID || data.clOrdID || "",
        executedPrice: price,
        executedAmount: amount,
        message: "Order placed successfully",
      }
    } catch (error) {
      return {
        success: false,
        orderId: "",
        message: error instanceof Error ? error.message : "Order failed",
      }
    }
  }

  async cancelOrder(orderId: string, symbol: string): Promise<boolean> {
    if (!this.apiKey || !this.apiSecret) {
      return false
    }

    try {
      const formattedSymbol = symbol.replace("/", "")
      await this.makeRequest(
        "DELETE",
        "/orders/cancel",
        {
          orderID: orderId,
          symbol: formattedSymbol,
        },
        true,
      )
      return true
    } catch {
      return false
    }
  }

  async getOpenOrders(symbol?: string): Promise<any[]> {
    if (!this.apiKey || !this.apiSecret) {
      return []
    }

    try {
      const params: Record<string, string> = {}
      if (symbol) {
        params.symbol = symbol.replace("/", "")
      }

      const data = await this.makeRequest("GET", "/orders/activeList", params, true)
      return data.rows || []
    } catch {
      return []
    }
  }

  async getPositions(): Promise<Position[]> {
    if (!this.apiKey || !this.apiSecret) {
      return []
    }

    try {
      const data = await this.makeRequest("GET", "/accounts/accountPositions", { currency: "USDT" }, true)

      const positions = data.positions || []

      return positions
        .filter((p: any) => p.size !== 0)
        .map((p: any) => ({
          symbol: p.symbol,
          side: p.side === "Buy" ? "long" : "short",
          amount: Math.abs(p.size) / 100000000,
          entryPrice: (p.avgEntryPriceEp || 0) / 10000,
          currentPrice: (p.markPriceEp || 0) / 10000,
          unrealizedPnl: (p.unrealisedPnlEv || 0) / 100000000,
          leverage: p.leverage || 1,
        }))
    } catch {
      return []
    }
  }

  async getOrderBook(symbol: string): Promise<OrderBook> {
    try {
      const formattedSymbol = symbol.replace("/", "")

      const response = await fetch(`${this.baseUrl}/md/orderbook?symbol=${formattedSymbol}`, {
        signal: AbortSignal.timeout(5000),
      })

      const data = await response.json()
      const book = data.result?.book || {}

      return {
        bids: (book.bids || []).slice(0, 20).map((b: any) => ({
          price: b[0] / 10000,
          amount: b[1] / 100000000,
        })),
        asks: (book.asks || []).slice(0, 20).map((a: any) => ({
          price: a[0] / 10000,
          amount: a[1] / 100000000,
        })),
        timestamp: Date.now(),
      }
    } catch {
      return { bids: [], asks: [], timestamp: Date.now() }
    }
  }

  async getTradingPairs(): Promise<string[]> {
    try {
      const response = await fetch(`${this.baseUrl}/public/products`, {
        signal: AbortSignal.timeout(5000),
      })

      const data = await response.json()
      const products = data.data?.products || []

      return products
        .filter((p: any) => p.status === "Listed")
        .map((p: any) => {
          const base = p.baseCurrency || p.symbol.replace("USDT", "").replace("USD", "")
          const quote = p.quoteCurrency || (p.symbol.includes("USDT") ? "USDT" : "USD")
          return `${base}/${quote}`
        })
    } catch {
      // Return common pairs as fallback
      return [
        "BTC/USDT",
        "ETH/USDT",
        "XRP/USDT",
        "SOL/USDT",
        "ADA/USDT",
        "DOGE/USDT",
        "AVAX/USDT",
        "DOT/USDT",
        "LINK/USDT",
        "MATIC/USDT",
      ]
    }
  }

  getExchangeName(): string {
    return "Phemex"
  }

  isConfigured(): boolean {
    return Boolean(this.apiKey && this.apiSecret)
  }
}
