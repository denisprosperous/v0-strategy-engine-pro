"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Activity, Wifi, WifiOff, TrendingUp, TrendingDown } from "lucide-react"
import { wsManager, type MarketData, type OrderBookData } from "@/lib/trading/data/websocket-manager"

interface ConnectionStatus {
  [exchange: string]: boolean
}

export default function RealTimeDataPanel() {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({})
  const [selectedExchange, setSelectedExchange] = useState("binance")
  const [selectedSymbol, setSelectedSymbol] = useState("BTCUSDT")
  const [marketData, setMarketData] = useState<MarketData | null>(null)
  const [orderBook, setOrderBook] = useState<OrderBookData | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const exchanges = [
    { value: "binance", label: "Binance" },
    { value: "bitget", label: "Bitget" },
  ]

  const popularSymbols = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "ADAUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "DOTUSDT",
    "LINKUSDT",
    "LTCUSDT",
    "BCHUSDT",
  ]

  useEffect(() => {
    const handleMarketData = (data: MarketData) => {
      if (data.symbol === selectedSymbol) {
        setMarketData(data)
      }
    }

    const handleOrderBook = (data: OrderBookData) => {
      if (data.symbol === selectedSymbol) {
        setOrderBook(data)
      }
    }

    const handleConnected = (exchange: string) => {
      setConnectionStatus((prev) => ({ ...prev, [exchange]: true }))
    }

    const handleDisconnected = (exchange: string) => {
      setConnectionStatus((prev) => ({ ...prev, [exchange]: false }))
    }

    wsManager.on("marketData", handleMarketData)
    wsManager.on("orderBook", handleOrderBook)
    wsManager.on("connected", handleConnected)
    wsManager.on("disconnected", handleDisconnected)

    return () => {
      wsManager.off("marketData", handleMarketData)
      wsManager.off("orderBook", handleOrderBook)
      wsManager.off("connected", handleConnected)
      wsManager.off("disconnected", handleDisconnected)
    }
  }, [selectedSymbol])

  const handleConnect = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`/api/market-data/websocket?action=connect&exchange=${selectedExchange}`)
      const result = await response.json()

      if (result.success) {
        // Subscribe to ticker and depth channels
        await fetch(
          `/api/market-data/websocket?action=subscribe&exchange=${selectedExchange}&symbol=${selectedSymbol}&channel=ticker`,
        )
        await fetch(
          `/api/market-data/websocket?action=subscribe&exchange=${selectedExchange}&symbol=${selectedSymbol}&channel=depth`,
        )
      }
    } catch (error) {
      console.error("[v0] Error connecting to WebSocket:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDisconnect = async () => {
    setIsLoading(true)
    try {
      await fetch(`/api/market-data/websocket?action=disconnect&exchange=${selectedExchange}`)
      setMarketData(null)
      setOrderBook(null)
    } catch (error) {
      console.error("[v0] Error disconnecting from WebSocket:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSymbolChange = async (newSymbol: string) => {
    if (connectionStatus[selectedExchange]) {
      // Unsubscribe from old symbol
      await fetch(
        `/api/market-data/websocket?action=unsubscribe&exchange=${selectedExchange}&symbol=${selectedSymbol}&channel=ticker`,
      )
      await fetch(
        `/api/market-data/websocket?action=unsubscribe&exchange=${selectedExchange}&symbol=${selectedSymbol}&channel=depth`,
      )

      // Subscribe to new symbol
      await fetch(
        `/api/market-data/websocket?action=subscribe&exchange=${selectedExchange}&symbol=${newSymbol}&channel=ticker`,
      )
      await fetch(
        `/api/market-data/websocket?action=subscribe&exchange=${selectedExchange}&symbol=${newSymbol}&channel=depth`,
      )
    }

    setSelectedSymbol(newSymbol)
    setMarketData(null)
    setOrderBook(null)
  }

  const isConnected = connectionStatus[selectedExchange] || false
  const priceChange = marketData?.change24h || 0
  const isPriceUp = priceChange > 0

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Real-time Market Data
          </CardTitle>
          <CardDescription>Connect to live market data feeds from multiple exchanges</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="exchange">Exchange</Label>
              <Select value={selectedExchange} onValueChange={setSelectedExchange}>
                <SelectTrigger>
                  <SelectValue placeholder="Select exchange" />
                </SelectTrigger>
                <SelectContent>
                  {exchanges.map((exchange) => (
                    <SelectItem key={exchange.value} value={exchange.value}>
                      {exchange.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="symbol">Trading Pair</Label>
              <Select value={selectedSymbol} onValueChange={handleSymbolChange}>
                <SelectTrigger>
                  <SelectValue placeholder="Select symbol" />
                </SelectTrigger>
                <SelectContent>
                  {popularSymbols.map((symbol) => (
                    <SelectItem key={symbol} value={symbol}>
                      {symbol}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Connection Status</Label>
              <div className="flex items-center gap-2">
                <Badge variant={isConnected ? "default" : "secondary"} className="flex items-center gap-1">
                  {isConnected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
                  {isConnected ? "Connected" : "Disconnected"}
                </Badge>
                {isConnected ? (
                  <Button onClick={handleDisconnect} variant="outline" size="sm" disabled={isLoading}>
                    Disconnect
                  </Button>
                ) : (
                  <Button onClick={handleConnect} size="sm" disabled={isLoading}>
                    Connect
                  </Button>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {marketData && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>{marketData.symbol} Price Data</span>
              <Badge variant={isPriceUp ? "default" : "destructive"} className="flex items-center gap-1">
                {isPriceUp ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                {priceChange.toFixed(2)}%
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold">${marketData.price.toFixed(2)}</div>
                <div className="text-sm text-muted-foreground">Last Price</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-semibold">${marketData.bid.toFixed(2)}</div>
                <div className="text-sm text-muted-foreground">Bid</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-semibold">${marketData.ask.toFixed(2)}</div>
                <div className="text-sm text-muted-foreground">Ask</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-semibold">{marketData.volume.toLocaleString()}</div>
                <div className="text-sm text-muted-foreground">24h Volume</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {orderBook && (
        <Card>
          <CardHeader>
            <CardTitle>Order Book - {orderBook.symbol}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h4 className="font-semibold text-green-600 mb-2">Bids</h4>
                <div className="space-y-1">
                  {orderBook.bids.slice(0, 10).map(([price, quantity], index) => (
                    <div key={index} className="flex justify-between text-sm">
                      <span className="text-green-600">${price.toFixed(2)}</span>
                      <span>{quantity.toFixed(4)}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h4 className="font-semibold text-red-600 mb-2">Asks</h4>
                <div className="space-y-1">
                  {orderBook.asks.slice(0, 10).map(([price, quantity], index) => (
                    <div key={index} className="flex justify-between text-sm">
                      <span className="text-red-600">${price.toFixed(2)}</span>
                      <span>{quantity.toFixed(4)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
