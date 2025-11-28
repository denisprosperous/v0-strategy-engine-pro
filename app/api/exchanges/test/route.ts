import { NextResponse } from "next/server"
import { brokerFactory, SUPPORTED_EXCHANGES, type SupportedExchange } from "@/lib/trading/brokers/broker-factory"

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const exchange = searchParams.get("exchange") as SupportedExchange | null

    if (exchange) {
      // Test single exchange
      const result = await brokerFactory.testConnection(exchange)
      const exchangeInfo = SUPPORTED_EXCHANGES.find((e) => e.id === exchange)

      return NextResponse.json({
        success: true,
        exchange,
        name: exchangeInfo?.name,
        ...result,
        features: exchangeInfo?.features || [],
      })
    }

    // Test all exchanges
    const results = await brokerFactory.testAllConnections()
    const configuredExchanges = brokerFactory.getConfiguredExchanges()

    // Enhanced response with exchange details
    const detailedResults = Object.entries(results).map(([id, status]) => {
      const info = SUPPORTED_EXCHANGES.find((e) => e.id === id)
      return {
        id,
        name: info?.name || id,
        ...status,
        configured: configuredExchanges.includes(id as SupportedExchange),
        features: info?.features || [],
      }
    })

    return NextResponse.json({
      success: true,
      exchanges: detailedResults,
      summary: {
        total: SUPPORTED_EXCHANGES.length,
        connected: detailedResults.filter((e) => e.connected).length,
        configured: configuredExchanges.length,
      },
      timestamp: Date.now(),
    })
  } catch (error) {
    console.error("Error testing exchange connections:", error)
    return NextResponse.json({ success: false, error: "Failed to test connections" }, { status: 500 })
  }
}
