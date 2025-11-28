"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useRealtimePrices } from "@/lib/hooks/use-realtime-prices"
import { TrendingUp, TrendingDown, Wifi, WifiOff, Activity } from "lucide-react"
import { cn } from "@/lib/utils"

interface RealtimeTickerProps {
  symbols?: string[]
  exchange?: "binance" | "bitget" | "okx" | "bybit" | "coinbase" | "kraken"
}

export function RealtimeTicker({
  symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"],
  exchange = "binance",
}: RealtimeTickerProps) {
  const { prices, isConnected, error } = useRealtimePrices({
    symbols,
    exchange,
    autoConnect: true,
  })

  const [previousPrices, setPreviousPrices] = useState<Map<string, number>>(new Map())
  const [priceFlash, setPriceFlash] = useState<Map<string, "up" | "down" | null>>(new Map())

  // Flash effect when price changes
  useEffect(() => {
    const newFlashes = new Map<string, "up" | "down" | null>()

    prices.forEach((data, symbol) => {
      const prevPrice = previousPrices.get(symbol)
      if (prevPrice !== undefined && prevPrice !== data.price) {
        newFlashes.set(symbol, data.price > prevPrice ? "up" : "down")

        // Clear flash after animation
        setTimeout(() => {
          setPriceFlash((prev) => {
            const updated = new Map(prev)
            updated.set(symbol, null)
            return updated
          })
        }, 500)
      }
    })

    if (newFlashes.size > 0) {
      setPriceFlash((prev) => new Map([...prev, ...newFlashes]))
    }

    // Update previous prices
    const newPrevPrices = new Map<string, number>()
    prices.forEach((data, symbol) => {
      newPrevPrices.set(symbol, data.price)
    })
    setPreviousPrices(newPrevPrices)
  }, [prices])

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Real-time Prices
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              {exchange.toUpperCase()}
            </Badge>
            {isConnected ? (
              <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">
                <Wifi className="w-3 h-3 mr-1" />
                Live
              </Badge>
            ) : (
              <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/20">
                <WifiOff className="w-3 h-3 mr-1" />
                {error || "Disconnected"}
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {symbols.map((symbol) => {
            const data = prices.get(symbol)
            const flash = priceFlash.get(symbol)

            return (
              <div
                key={symbol}
                className={cn(
                  "p-3 rounded-lg border transition-colors",
                  flash === "up" && "bg-green-500/10 border-green-500/30",
                  flash === "down" && "bg-red-500/10 border-red-500/30",
                  !flash && "bg-muted/50",
                )}
              >
                <div className="text-sm font-medium text-muted-foreground">{symbol.replace("USDT", "")}</div>
                <div
                  className={cn(
                    "text-lg font-bold font-mono",
                    flash === "up" && "text-green-500",
                    flash === "down" && "text-red-500",
                  )}
                >
                  {data?.price
                    ? `$${data.price.toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: data.price < 1 ? 6 : 2,
                      })}`
                    : "---"}
                </div>
                {data?.change24h !== undefined && (
                  <div
                    className={cn(
                      "text-xs flex items-center gap-1",
                      data.change24h >= 0 ? "text-green-500" : "text-red-500",
                    )}
                  >
                    {data.change24h >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                    {data.change24h >= 0 ? "+" : ""}
                    {data.change24h.toFixed(2)}%
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
