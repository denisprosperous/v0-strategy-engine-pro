import type { BaseBroker } from "../brokers/base-broker"
import { BinanceBroker } from "../brokers/binance-broker"
import { BitgetBroker } from "../brokers/bitget-broker"
import { CoinbaseBroker } from "../brokers/coinbase-broker"
import { OKXBroker } from "../brokers/okx-broker"
import { KrakenBroker } from "../brokers/kraken-broker"
import { logger } from "@/lib/utils/logger"

export interface ExchangeConfig {
  name: string
  displayName: string
  apiKey: string
  apiSecret: string
  passphrase?: string
  testnet?: boolean
  enabled: boolean
  features: {
    spot: boolean
    futures: boolean
    margin: boolean
    websocket: boolean
  }
  tradingPairs: string[]
  fees: {
    maker: number
    taker: number
  }
}

export interface ExchangeStatus {
  name: string
  connected: boolean
  lastPing: Date | null
  errorCount: number
  tradingPairs: string[]
  balance: any[]
}

export class ExchangeManager {
  private brokers: Map<string, BaseBroker> = new Map()
  private configs: Map<string, ExchangeConfig> = new Map()
  private status: Map<string, ExchangeStatus> = new Map()
  private healthCheckInterval: NodeJS.Timeout | null = null

  constructor(private userId: string) {}

  async initialize(exchangeConfigs: ExchangeConfig[]): Promise<void> {
    try {
      for (const config of exchangeConfigs) {
        if (config.enabled) {
          await this.addExchange(config)
        }
      }

      // Start health monitoring
      this.startHealthMonitoring()

      logger.info(`Exchange manager initialized for user ${this.userId}`, {
        exchanges: Array.from(this.brokers.keys()),
      })
    } catch (error) {
      logger.error("Failed to initialize exchange manager", { error, userId: this.userId })
      throw error
    }
  }

  async addExchange(config: ExchangeConfig): Promise<void> {
    try {
      const broker = this.createBroker(config)
      await broker.connect()

      this.brokers.set(config.name, broker)
      this.configs.set(config.name, config)
      this.status.set(config.name, {
        name: config.name,
        connected: true,
        lastPing: new Date(),
        errorCount: 0,
        tradingPairs: config.tradingPairs,
        balance: [],
      })

      logger.info(`Added exchange ${config.name}`, { userId: this.userId })
    } catch (error) {
      logger.error(`Failed to add exchange ${config.name}`, { error, userId: this.userId })
      throw error
    }
  }

  async removeExchange(exchangeName: string): Promise<void> {
    const broker = this.brokers.get(exchangeName)
    if (broker) {
      await broker.disconnect()
      this.brokers.delete(exchangeName)
      this.configs.delete(exchangeName)
      this.status.delete(exchangeName)

      logger.info(`Removed exchange ${exchangeName}`, { userId: this.userId })
    }
  }

  private createBroker(config: ExchangeConfig): BaseBroker {
    switch (config.name.toLowerCase()) {
      case "binance":
        return new BinanceBroker(config.apiKey, config.apiSecret, config.testnet)
      case "bitget":
        return new BitgetBroker(config.apiKey, config.apiSecret, config.testnet)
      case "coinbase":
        return new CoinbaseBroker(config.apiKey, config.apiSecret, config.testnet)
      case "okx":
        if (!config.passphrase) {
          throw new Error("OKX requires a passphrase")
        }
        return new OKXBroker(config.apiKey, config.apiSecret, config.passphrase, config.testnet)
      case "kraken":
        return new KrakenBroker(config.apiKey, config.apiSecret, config.testnet)
      default:
        throw new Error(`Unsupported exchange: ${config.name}`)
    }
  }

  getConnectedExchanges(): string[] {
    return Array.from(this.brokers.keys()).filter((name) => this.status.get(name)?.connected)
  }

  getBroker(exchangeName: string): BaseBroker | undefined {
    return this.brokers.get(exchangeName)
  }

  getExchangeStatus(exchangeName: string): ExchangeStatus | undefined {
    return this.status.get(exchangeName)
  }

  getAllExchangeStatuses(): ExchangeStatus[] {
    return Array.from(this.status.values())
  }

  async executeOrder(exchangeName: string, order: any): Promise<any> {
    const broker = this.brokers.get(exchangeName)
    if (!broker) {
      throw new Error(`Exchange ${exchangeName} not found`)
    }

    const status = this.status.get(exchangeName)
    if (!status?.connected) {
      throw new Error(`Exchange ${exchangeName} is not connected`)
    }

    try {
      const result = await broker.placeOrder(order)
      logger.info(`Order executed on ${exchangeName}`, { orderId: result.orderId, userId: this.userId })
      return result
    } catch (error) {
      this.incrementErrorCount(exchangeName)
      logger.error(`Failed to execute order on ${exchangeName}`, { error, userId: this.userId })
      throw error
    }
  }

  async getAggregatedBalance(): Promise<Record<string, { total: number; exchanges: Record<string, number> }>> {
    const aggregatedBalance: Record<string, { total: number; exchanges: Record<string, number> }> = {}

    for (const [exchangeName, broker] of this.brokers) {
      try {
        const balances = await broker.getBalance()

        for (const balance of balances) {
          if (!aggregatedBalance[balance.asset]) {
            aggregatedBalance[balance.asset] = { total: 0, exchanges: {} }
          }

          aggregatedBalance[balance.asset].total += balance.total
          aggregatedBalance[balance.asset].exchanges[exchangeName] = balance.total
        }
      } catch (error) {
        logger.error(`Failed to get balance from ${exchangeName}`, { error, userId: this.userId })
        this.incrementErrorCount(exchangeName)
      }
    }

    return aggregatedBalance
  }

  async getBestPrice(symbol: string, side: "buy" | "sell"): Promise<{ exchange: string; price: number } | null> {
    const prices: { exchange: string; price: number }[] = []

    for (const [exchangeName, broker] of this.brokers) {
      try {
        const config = this.configs.get(exchangeName)
        if (config?.tradingPairs.includes(symbol)) {
          const price = await broker.getPrice(symbol)
          prices.push({ exchange: exchangeName, price })
        }
      } catch (error) {
        logger.error(`Failed to get price from ${exchangeName}`, { error, symbol, userId: this.userId })
        this.incrementErrorCount(exchangeName)
      }
    }

    if (prices.length === 0) {
      return null
    }

    // For buy orders, find the lowest price (best for buyer)
    // For sell orders, find the highest price (best for seller)
    const bestPrice = prices.reduce((best, current) => {
      if (side === "buy") {
        return current.price < best.price ? current : best
      } else {
        return current.price > best.price ? current : best
      }
    })

    return bestPrice
  }

  async executeArbitrage(
    symbol: string,
    buyExchange: string,
    sellExchange: string,
    quantity: number,
  ): Promise<{ buyOrder: any; sellOrder: any }> {
    const buyBroker = this.brokers.get(buyExchange)
    const sellBroker = this.brokers.get(sellExchange)

    if (!buyBroker || !sellBroker) {
      throw new Error("One or both exchanges not available for arbitrage")
    }

    try {
      // Execute both orders simultaneously
      const [buyOrder, sellOrder] = await Promise.all([
        buyBroker.placeOrder({
          symbol,
          side: "buy",
          type: "market",
          quantity,
        }),
        sellBroker.placeOrder({
          symbol,
          side: "sell",
          type: "market",
          quantity,
        }),
      ])

      logger.info("Arbitrage executed", {
        symbol,
        buyExchange,
        sellExchange,
        quantity,
        buyOrderId: buyOrder.orderId,
        sellOrderId: sellOrder.orderId,
        userId: this.userId,
      })

      return { buyOrder, sellOrder }
    } catch (error) {
      logger.error("Failed to execute arbitrage", { error, symbol, userId: this.userId })
      throw error
    }
  }

  private startHealthMonitoring(): void {
    this.healthCheckInterval = setInterval(async () => {
      for (const [exchangeName, broker] of this.brokers) {
        try {
          // Simple health check by getting server time or ping
          await broker.getPrice("BTCUSDT") // Use a common pair for health check

          const status = this.status.get(exchangeName)
          if (status) {
            status.connected = true
            status.lastPing = new Date()
          }
        } catch (error) {
          logger.warn(`Health check failed for ${exchangeName}`, { error, userId: this.userId })
          this.incrementErrorCount(exchangeName)

          const status = this.status.get(exchangeName)
          if (status && status.errorCount > 5) {
            status.connected = false
          }
        }
      }
    }, 30000) // Check every 30 seconds
  }

  private incrementErrorCount(exchangeName: string): void {
    const status = this.status.get(exchangeName)
    if (status) {
      status.errorCount++
    }
  }

  async shutdown(): Promise<void> {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval)
    }

    for (const [exchangeName, broker] of this.brokers) {
      try {
        await broker.disconnect()
        logger.info(`Disconnected from ${exchangeName}`, { userId: this.userId })
      } catch (error) {
        logger.error(`Failed to disconnect from ${exchangeName}`, { error, userId: this.userId })
      }
    }

    this.brokers.clear()
    this.configs.clear()
    this.status.clear()
  }
}
