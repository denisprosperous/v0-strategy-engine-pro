"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, PieChart, Pie, Cell } from "recharts"

const portfolioData = [
  { time: "00:00", value: 10000 },
  { time: "04:00", value: 10250 },
  { time: "08:00", value: 10100 },
  { time: "12:00", value: 10800 },
  { time: "16:00", value: 11200 },
  { time: "20:00", value: 12450 },
]

const positionData = [
  { name: "BTC/USDT", value: 35, color: "hsl(var(--chart-1))" },
  { name: "ETH/USDT", value: 25, color: "hsl(var(--chart-2))" },
  { name: "SOL/USDT", value: 20, color: "hsl(var(--chart-3))" },
  { name: "AVAX/USDT", value: 12, color: "hsl(var(--chart-4))" },
  { name: "Others", value: 8, color: "hsl(var(--chart-5))" },
]

const recentTrades = [
  { symbol: "BTC/USDT", type: "BUY", amount: 0.25, price: 43250, pnl: 125.5, status: "open" },
  { symbol: "ETH/USDT", type: "SELL", amount: 2.5, price: 2650, pnl: -45.2, status: "closed" },
  { symbol: "SOL/USDT", type: "BUY", amount: 15, price: 98.5, pnl: 89.75, status: "open" },
  { symbol: "AVAX/USDT", type: "BUY", amount: 8, price: 35.2, pnl: 12.8, status: "open" },
]

export function PortfolioOverview() {
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Simulate loading
    const timer = setTimeout(() => setIsLoading(false), 1000)
    return () => clearTimeout(timer)
  }, [])

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader>
              <div className="h-4 bg-muted rounded w-1/3"></div>
              <div className="h-3 bg-muted rounded w-1/2"></div>
            </CardHeader>
            <CardContent>
              <div className="h-32 bg-muted rounded"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Portfolio Performance Chart */}
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Portfolio Performance</CardTitle>
          <CardDescription>24-hour portfolio value trend</CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer
            config={{
              value: {
                label: "Portfolio Value",
                color: "hsl(var(--chart-1))",
              },
            }}
            className="h-[300px]"
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={portfolioData}>
                <XAxis dataKey="time" />
                <YAxis />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="hsl(var(--chart-1))"
                  strokeWidth={2}
                  dot={{ fill: "hsl(var(--chart-1))", strokeWidth: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartContainer>
        </CardContent>
      </Card>

      {/* Position Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Position Distribution</CardTitle>
          <CardDescription>Current portfolio allocation</CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer
            config={{
              value: {
                label: "Allocation %",
              },
            }}
            className="h-[250px]"
          >
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={positionData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {positionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <ChartTooltip content={<ChartTooltipContent />} />
              </PieChart>
            </ResponsiveContainer>
          </ChartContainer>
          <div className="mt-4 space-y-2">
            {positionData.map((item, index) => (
              <div key={index} className="flex items-center justify-between text-sm">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></div>
                  <span>{item.name}</span>
                </div>
                <span className="font-medium">{item.value}%</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Recent Trades */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Trades</CardTitle>
          <CardDescription>Latest trading activity</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {recentTrades.map((trade, index) => (
              <div key={index} className="flex items-center justify-between p-3 rounded-lg border">
                <div className="flex items-center space-x-3">
                  <div className={`w-2 h-2 rounded-full ${trade.type === "BUY" ? "bg-green-500" : "bg-red-500"}`}></div>
                  <div>
                    <p className="font-medium text-sm">{trade.symbol}</p>
                    <p className="text-xs text-muted-foreground">
                      {trade.type} {trade.amount} @ ${trade.price}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`text-sm font-medium ${trade.pnl >= 0 ? "text-green-500" : "text-red-500"}`}>
                    {trade.pnl >= 0 ? "+" : ""}${trade.pnl}
                  </p>
                  <Badge variant={trade.status === "open" ? "default" : "secondary"} className="text-xs">
                    {trade.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
          <Button variant="outline" className="w-full mt-4 bg-transparent">
            View All Trades
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
