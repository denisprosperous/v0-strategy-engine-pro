"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, BarChart, Bar } from "recharts"
import { TrendingUp, TrendingDown, Search, RefreshCw } from "lucide-react"

const marketData = [
  { symbol: "BTC/USDT", price: 43250.67, change: 2.45, volume: "1.2B", sentiment: 78 },
  { symbol: "ETH/USDT", price: 2650.34, change: -1.23, volume: "890M", sentiment: 65 },
  { symbol: "SOL/USDT", price: 98.56, change: 5.67, volume: "234M", sentiment: 82 },
  { symbol: "AVAX/USDT", price: 35.23, change: 1.89, volume: "156M", sentiment: 71 },
  { symbol: "MATIC/USDT", price: 0.87, change: -0.45, volume: "89M", sentiment: 58 },
  { symbol: "ADA/USDT", price: 0.52, change: 3.21, volume: "67M", sentiment: 69 },
]

const priceHistory = [
  { time: "00:00", BTC: 42800, ETH: 2620, SOL: 95 },
  { time: "04:00", BTC: 43100, ETH: 2640, SOL: 97 },
  { time: "08:00", BTC: 42950, ETH: 2635, SOL: 96 },
  { time: "12:00", BTC: 43200, ETH: 2655, SOL: 98 },
  { time: "16:00", BTC: 43350, ETH: 2648, SOL: 99 },
  { time: "20:00", BTC: 43250, ETH: 2650, SOL: 98.5 },
]

const volumeData = [
  { symbol: "BTC", volume: 1200 },
  { symbol: "ETH", volume: 890 },
  { symbol: "SOL", volume: 234 },
  { symbol: "AVAX", volume: 156 },
  { symbol: "MATIC", volume: 89 },
  { symbol: "ADA", volume: 67 },
]

export function MarketData() {
  const [searchTerm, setSearchTerm] = useState("")
  const [selectedAsset, setSelectedAsset] = useState("BTC")
  const [isRefreshing, setIsRefreshing] = useState(false)

  const filteredData = marketData.filter((item) => item.symbol.toLowerCase().includes(searchTerm.toLowerCase()))

  const refreshData = async () => {
    setIsRefreshing(true)
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))
    setIsRefreshing(false)
  }

  const getSentimentColor = (sentiment: number) => {
    if (sentiment >= 70) return "text-green-500"
    if (sentiment >= 50) return "text-yellow-500"
    return "text-red-500"
  }

  const getSentimentBadge = (sentiment: number) => {
    if (sentiment >= 70) return <Badge className="bg-green-500/10 text-green-500 border-green-500/20">Bullish</Badge>
    if (sentiment >= 50) return <Badge className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20">Neutral</Badge>
    return <Badge className="bg-red-500/10 text-red-500 border-red-500/20">Bearish</Badge>
  }

  return (
    <div className="space-y-6">
      {/* Market Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Market Cap</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$1.67T</div>
            <div className="flex items-center text-xs text-green-500">
              <TrendingUp className="w-3 h-3 mr-1" />
              +2.4% (24h)
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">24h Volume</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$89.2B</div>
            <div className="flex items-center text-xs text-red-500">
              <TrendingDown className="w-3 h-3 mr-1" />
              -5.1% (24h)
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">BTC Dominance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">52.3%</div>
            <div className="text-xs text-muted-foreground">+0.2% from yesterday</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Fear & Greed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">67</div>
            <div className="text-xs text-green-500">Greed</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Price Charts */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Price Charts</CardTitle>
                <CardDescription>24-hour price movements</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={refreshData} disabled={isRefreshing}>
                <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <ChartContainer
              config={{
                BTC: { label: "Bitcoin", color: "hsl(var(--chart-1))" },
                ETH: { label: "Ethereum", color: "hsl(var(--chart-2))" },
                SOL: { label: "Solana", color: "hsl(var(--chart-3))" },
              }}
              className="h-[300px]"
            >
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={priceHistory}>
                  <XAxis dataKey="time" />
                  <YAxis />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Line type="monotone" dataKey="BTC" stroke="hsl(var(--chart-1))" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="ETH" stroke="hsl(var(--chart-2))" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="SOL" stroke="hsl(var(--chart-3))" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </ChartContainer>
          </CardContent>
        </Card>

        {/* Volume Chart */}
        <Card>
          <CardHeader>
            <CardTitle>24h Volume</CardTitle>
            <CardDescription>Trading volume by asset</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer
              config={{
                volume: { label: "Volume (M)", color: "hsl(var(--chart-4))" },
              }}
              className="h-[300px]"
            >
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={volumeData}>
                  <XAxis dataKey="symbol" />
                  <YAxis />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar dataKey="volume" fill="hsl(var(--chart-4))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartContainer>
          </CardContent>
        </Card>
      </div>

      {/* Market Data Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Market Data</CardTitle>
              <CardDescription>Real-time prices and sentiment analysis</CardDescription>
            </div>
            <div className="relative w-64">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
              <Input
                placeholder="Search assets..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {filteredData.map((item, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center space-x-4">
                  <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
                    <span className="text-sm font-medium">{item.symbol.split("/")[0].slice(0, 2)}</span>
                  </div>
                  <div>
                    <h4 className="font-medium">{item.symbol}</h4>
                    <p className="text-sm text-muted-foreground">Vol: {item.volume}</p>
                  </div>
                </div>

                <div className="text-right">
                  <div className="font-medium">${item.price.toLocaleString()}</div>
                  <div className={`text-sm flex items-center ${item.change >= 0 ? "text-green-500" : "text-red-500"}`}>
                    {item.change >= 0 ? (
                      <TrendingUp className="w-3 h-3 mr-1" />
                    ) : (
                      <TrendingDown className="w-3 h-3 mr-1" />
                    )}
                    {item.change >= 0 ? "+" : ""}
                    {item.change}%
                  </div>
                </div>

                <div className="text-right">
                  <div className={`text-sm font-medium ${getSentimentColor(item.sentiment)}`}>{item.sentiment}%</div>
                  {getSentimentBadge(item.sentiment)}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
