import { NextResponse } from "next/server"

interface ExchangeTestResult {
  name: string
  connected: boolean
  latency: number
  endpoint: string
  error?: string
}

export async function GET() {
  const exchanges = [
    { name: "Binance", url: "https://api.binance.com/api/v3/ping" },
    { name: "Bitget", url: "https://api.bitget.com/api/v2/public/time" },
    { name: "Kraken", url: "https://api.kraken.com/0/public/Time" },
    { name: "Coinbase", url: "https://api.coinbase.com/v2/time" },
    { name: "OKX", url: "https://www.okx.com/api/v5/public/time" },
    { name: "Bybit", url: "https://api.bybit.com/v5/market/time" },
    { name: "KuCoin", url: "https://api.kucoin.com/api/v1/timestamp" },
    { name: "Gate.io", url: "https://api.gateio.ws/api/v4/spot/time" },
    { name: "Huobi", url: "https://api.huobi.pro/v1/common/timestamp" },
    { name: "MEXC", url: "https://api.mexc.com/api/v3/ping" },
  ]

  const results: ExchangeTestResult[] = []

  for (const exchange of exchanges) {
    const start = Date.now()
    try {
      const response = await fetch(exchange.url, {
        method: "GET",
        signal: AbortSignal.timeout(10000),
      })

      results.push({
        name: exchange.name,
        connected: response.ok,
        latency: Date.now() - start,
        endpoint: exchange.url,
      })
    } catch (error) {
      results.push({
        name: exchange.name,
        connected: false,
        latency: Date.now() - start,
        endpoint: exchange.url,
        error: error instanceof Error ? error.message : "Connection failed",
      })
    }
  }

  const connectedCount = results.filter((r) => r.connected).length
  const totalLatency = results.reduce((sum, r) => sum + r.latency, 0)

  return NextResponse.json({
    timestamp: new Date().toISOString(),
    summary: {
      total: exchanges.length,
      connected: connectedCount,
      failed: exchanges.length - connectedCount,
      averageLatency: Math.round(totalLatency / exchanges.length),
    },
    exchanges: results,
  })
}
