import type { BaseBroker } from "./base-broker"
import { BinanceBroker } from "./binance-broker"
import { BitgetBroker } from "./bitget-broker"
import { KrakenBroker } from "./kraken-broker"
import { CoinbaseBroker } from "./coinbase-broker"
import { OKXBroker } from "./okx-broker"
import { config } from "@/lib/config/environment"

export type SupportedExchange =
  | "binance"
  | "bitget"
  | "kraken"
  | "coinbase"
  | "okx"
  | "bybit"
  | "kucoin"
  | "gate"
  | "huobi"
  | "mexc"

export interface BrokerConfig {
  apiKey: string
  apiSecret: string
  passphrase?: string
  testnet?: boolean
}

export interface ExchangeInfo {
  id: SupportedExchange
  name: string
  logo: string
  testnetUrl?: string
  mainnetUrl: string
  wsUrl: string
  supported: boolean
  features: string[]
}

export const SUPPORTED_EXCHANGES: ExchangeInfo[] = [
  {
    id: "binance",
    name: "Binance",
    logo: "/exchanges/binance.svg",
    testnetUrl: "https://testnet.binance.vision",
    mainnetUrl: "https://api.binance.com",
    wsUrl: "wss://stream.binance.com:9443/ws",
    supported: true,
    features: ["spot", "futures", "margin", "websocket"],
  },
  {
    id: "bitget",
    name: "Bitget",
    logo: "/exchanges/bitget.svg",
    mainnetUrl: "https://api.bitget.com",
    wsUrl: "wss://ws.bitget.com/spot/v1/stream",
    supported: true,
    features: ["spot", "futures", "copy-trading", "websocket"],
  },
  {
    id: "kraken",
    name: "Kraken",
    logo: "/exchanges/kraken.svg",
    mainnetUrl: "https://api.kraken.com",
    wsUrl: "wss://ws.kraken.com",
    supported: true,
    features: ["spot", "margin", "staking", "websocket"],
  },
  {
    id: "coinbase",
    name: "Coinbase",
    logo: "/exchanges/coinbase.svg",
    testnetUrl: "https://api-public.sandbox.exchange.coinbase.com",
    mainnetUrl: "https://api.exchange.coinbase.com",
    wsUrl: "wss://ws-feed.exchange.coinbase.com",
    supported: true,
    features: ["spot", "advanced-trade", "websocket"],
  },
  {
    id: "okx",
    name: "OKX",
    logo: "/exchanges/okx.svg",
    testnetUrl: "https://www.okx.com",
    mainnetUrl: "https://www.okx.com",
    wsUrl: "wss://ws.okx.com:8443/ws/v5/public",
    supported: true,
    features: ["spot", "futures", "margin", "options", "websocket"],
  },
  {
    id: "bybit",
    name: "Bybit",
    logo: "/exchanges/bybit.svg",
    testnetUrl: "https://api-testnet.bybit.com",
    mainnetUrl: "https://api.bybit.com",
    wsUrl: "wss://stream.bybit.com/v5/public/spot",
    supported: true,
    features: ["spot", "futures", "copy-trading", "websocket"],
  },
  {
    id: "kucoin",
    name: "KuCoin",
    logo: "/exchanges/kucoin.svg",
    testnetUrl: "https://openapi-sandbox.kucoin.com",
    mainnetUrl: "https://api.kucoin.com",
    wsUrl: "wss://ws-api.kucoin.com",
    supported: true,
    features: ["spot", "futures", "margin", "websocket"],
  },
  {
    id: "gate",
    name: "Gate.io",
    logo: "/exchanges/gate.svg",
    mainnetUrl: "https://api.gateio.ws",
    wsUrl: "wss://api.gateio.ws/ws/v4/",
    supported: true,
    features: ["spot", "futures", "margin", "websocket"],
  },
  {
    id: "huobi",
    name: "Huobi",
    logo: "/exchanges/huobi.svg",
    mainnetUrl: "https://api.huobi.pro",
    wsUrl: "wss://api.huobi.pro/ws",
    supported: true,
    features: ["spot", "futures", "margin", "websocket"],
  },
  {
    id: "mexc",
    name: "MEXC",
    logo: "/exchanges/mexc.svg",
    mainnetUrl: "https://api.mexc.com",
    wsUrl: "wss://wbs.mexc.com/ws",
    supported: true,
    features: ["spot", "futures", "websocket"],
  },
]

class BrokerFactory {
  private brokers: Map<string, BaseBroker> = new Map()
  private connectionStatus: Map<string, boolean> = new Map()

  getBroker(exchange: SupportedExchange): BaseBroker | null {
    // Check if broker already exists
    if (this.brokers.has(exchange)) {
      return this.brokers.get(exchange) || null
    }

    // Create new broker based on exchange
    let broker: BaseBroker | null = null

    switch (exchange) {
      case "binance":
        if (config.binance.apiKey) {
          broker = new BinanceBroker(config.binance.apiKey, config.binance.apiSecret || "", config.binance.testnet)
        }
        break

      case "bitget":
        if (config.bitget.apiKey) {
          broker = new BitgetBroker()
        }
        break

      case "kraken":
        if (config.kraken.apiKey) {
          broker = new KrakenBroker()
        }
        break

      case "coinbase":
        if (config.coinbase?.apiKey) {
          broker = new CoinbaseBroker(config.coinbase.apiKey, config.coinbase.apiSecret || "", false)
        }
        break

      case "okx":
        if (config.okx?.apiKey) {
          broker = new OKXBroker(config.okx.apiKey, config.okx.apiSecret || "", config.okx.passphrase || "", false)
        }
        break

      // Add placeholder for other exchanges - they use similar patterns
      case "bybit":
      case "kucoin":
      case "gate":
      case "huobi":
      case "mexc":
        // These would follow similar patterns to the above
        // For now, return null to indicate not configured
        console.log(`${exchange} broker not yet fully implemented`)
        break
    }

    if (broker) {
      this.brokers.set(exchange, broker)
    }

    return broker
  }

  async testConnection(
    exchange: SupportedExchange,
  ): Promise<{ connected: boolean; message: string; latency?: number }> {
    const startTime = Date.now()

    try {
      const exchangeInfo = SUPPORTED_EXCHANGES.find((e) => e.id === exchange)
      if (!exchangeInfo) {
        return { connected: false, message: "Exchange not supported" }
      }

      // Test public endpoint
      let testUrl = ""
      switch (exchange) {
        case "binance":
          testUrl = `${exchangeInfo.mainnetUrl}/api/v3/ping`
          break
        case "bitget":
          testUrl = `${exchangeInfo.mainnetUrl}/api/spot/v1/public/time`
          break
        case "kraken":
          testUrl = `${exchangeInfo.mainnetUrl}/0/public/Time`
          break
        case "coinbase":
          testUrl = `${exchangeInfo.mainnetUrl}/time`
          break
        case "okx":
          testUrl = `${exchangeInfo.mainnetUrl}/api/v5/public/time`
          break
        case "bybit":
          testUrl = `${exchangeInfo.mainnetUrl}/v5/market/time`
          break
        case "kucoin":
          testUrl = `${exchangeInfo.mainnetUrl}/api/v1/timestamp`
          break
        case "gate":
          testUrl = `${exchangeInfo.mainnetUrl}/api/v4/spot/time`
          break
        case "huobi":
          testUrl = `${exchangeInfo.mainnetUrl}/v1/common/timestamp`
          break
        case "mexc":
          testUrl = `${exchangeInfo.mainnetUrl}/api/v3/time`
          break
      }

      const response = await fetch(testUrl, {
        method: "GET",
        signal: AbortSignal.timeout(5000),
      })

      const latency = Date.now() - startTime

      if (response.ok) {
        this.connectionStatus.set(exchange, true)
        return { connected: true, message: "Connected", latency }
      } else {
        this.connectionStatus.set(exchange, false)
        return { connected: false, message: `HTTP ${response.status}`, latency }
      }
    } catch (error) {
      this.connectionStatus.set(exchange, false)
      return {
        connected: false,
        message: error instanceof Error ? error.message : "Connection failed",
      }
    }
  }

  async testAllConnections(): Promise<
    Record<SupportedExchange, { connected: boolean; message: string; latency?: number }>
  > {
    const results: Record<string, { connected: boolean; message: string; latency?: number }> = {}

    await Promise.all(
      SUPPORTED_EXCHANGES.map(async (exchange) => {
        results[exchange.id] = await this.testConnection(exchange.id)
      }),
    )

    return results as Record<SupportedExchange, { connected: boolean; message: string; latency?: number }>
  }

  getConnectionStatus(exchange: SupportedExchange): boolean {
    return this.connectionStatus.get(exchange) || false
  }

  getAllConnectionStatuses(): Record<SupportedExchange, boolean> {
    const statuses: Record<string, boolean> = {}
    for (const exchange of SUPPORTED_EXCHANGES) {
      statuses[exchange.id] = this.connectionStatus.get(exchange.id) || false
    }
    return statuses as Record<SupportedExchange, boolean>
  }

  getConfiguredExchanges(): SupportedExchange[] {
    const configured: SupportedExchange[] = []

    if (config.binance.apiKey) configured.push("binance")
    if (config.bitget.apiKey) configured.push("bitget")
    if (config.kraken.apiKey) configured.push("kraken")
    if (config.coinbase?.apiKey) configured.push("coinbase")
    if (config.okx?.apiKey) configured.push("okx")
    if (config.bybit?.apiKey) configured.push("bybit")
    if (config.kucoin?.apiKey) configured.push("kucoin")
    if (config.gate?.apiKey) configured.push("gate")
    if (config.huobi?.apiKey) configured.push("huobi")
    if (config.mexc?.apiKey) configured.push("mexc")

    return configured
  }

  async disconnectAll(): Promise<void> {
    for (const [exchange, broker] of this.brokers) {
      try {
        await broker.disconnect()
      } catch (error) {
        console.error(`Error disconnecting ${exchange}:`, error)
      }
    }
    this.brokers.clear()
    this.connectionStatus.clear()
  }
}

export const brokerFactory = new BrokerFactory()
