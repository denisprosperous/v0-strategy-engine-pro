"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Play, Pause, Settings, Bot } from "lucide-react"

const strategies = [
  {
    id: "breakout-scalping",
    name: "Breakout Scalping",
    description: "Identifies and trades breakout patterns with tight stop losses",
    status: "active",
    performance: {
      totalTrades: 45,
      winRate: 78.5,
      totalPnL: 1250.67,
      avgTrade: 27.79,
      maxDrawdown: -125.5,
    },
    settings: {
      riskPerTrade: 1.5,
      maxPositions: 3,
      timeframe: "5m",
      assets: ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
    },
  },
  {
    id: "mean-reversion",
    name: "Mean Reversion",
    description: "Trades oversold/overbought conditions with statistical analysis",
    status: "active",
    performance: {
      totalTrades: 32,
      winRate: 65.2,
      totalPnL: 890.45,
      avgTrade: 27.83,
      maxDrawdown: -89.2,
    },
    settings: {
      riskPerTrade: 1.0,
      maxPositions: 2,
      timeframe: "15m",
      assets: ["ETH/USDT", "AVAX/USDT"],
    },
  },
  {
    id: "momentum-sentiment",
    name: "Momentum + Sentiment",
    description: "Combines technical momentum with social sentiment analysis",
    status: "paused",
    performance: {
      totalTrades: 28,
      winRate: 82.1,
      totalPnL: 567.89,
      avgTrade: 20.28,
      maxDrawdown: -45.3,
    },
    settings: {
      riskPerTrade: 0.8,
      maxPositions: 2,
      timeframe: "1h",
      assets: ["SOL/USDT", "MATIC/USDT"],
    },
  },
  {
    id: "news-scalping",
    name: "News Event Scalping",
    description: "Reacts to news events and market announcements",
    status: "inactive",
    performance: {
      totalTrades: 15,
      winRate: 73.3,
      totalPnL: 234.56,
      avgTrade: 15.64,
      maxDrawdown: -67.8,
    },
    settings: {
      riskPerTrade: 2.0,
      maxPositions: 1,
      timeframe: "1m",
      assets: ["BTC/USDT"],
    },
  },
]

export function StrategyManager() {
  const [selectedStrategy, setSelectedStrategy] = useState(strategies[0])

  const toggleStrategy = (strategyId: string) => {
    // In a real app, this would make an API call
    console.log(`Toggling strategy: ${strategyId}`)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "bg-green-500"
      case "paused":
        return "bg-yellow-500"
      case "inactive":
        return "bg-gray-500"
      default:
        return "bg-gray-500"
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <Badge className="bg-green-500/10 text-green-500 border-green-500/20">Active</Badge>
      case "paused":
        return <Badge className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20">Paused</Badge>
      case "inactive":
        return <Badge variant="secondary">Inactive</Badge>
      default:
        return <Badge variant="secondary">Unknown</Badge>
    }
  }

  return (
    <div className="space-y-6">
      {/* Strategy Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Active Strategies</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{strategies.filter((s) => s.status === "active").length}</div>
            <div className="text-xs text-muted-foreground mt-1">of {strategies.length} total</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Combined P&L</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">
              +${strategies.reduce((sum, s) => sum + s.performance.totalPnL, 0).toFixed(2)}
            </div>
            <div className="text-xs text-muted-foreground mt-1">All strategies</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Avg Win Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(strategies.reduce((sum, s) => sum + s.performance.winRate, 0) / strategies.length).toFixed(1)}%
            </div>
            <div className="text-xs text-muted-foreground mt-1">Across all strategies</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Trades</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {strategies.reduce((sum, s) => sum + s.performance.totalTrades, 0)}
            </div>
            <div className="text-xs text-muted-foreground mt-1">This month</div>
          </CardContent>
        </Card>
      </div>

      {/* Strategy List and Details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Strategy List */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Strategies</CardTitle>
            <CardDescription>Manage your trading strategies</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {strategies.map((strategy) => (
              <div
                key={strategy.id}
                className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                  selectedStrategy.id === strategy.id ? "border-primary bg-primary/5" : "hover:bg-muted/50"
                }`}
                onClick={() => setSelectedStrategy(strategy)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <div className={`w-2 h-2 rounded-full ${getStatusColor(strategy.status)}`}></div>
                    <h4 className="font-medium text-sm">{strategy.name}</h4>
                  </div>
                  {getStatusBadge(strategy.status)}
                </div>
                <p className="text-xs text-muted-foreground mb-3">{strategy.description}</p>
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Win Rate</span>
                  <span className="font-medium">{strategy.performance.winRate}%</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">P&L</span>
                  <span
                    className={`font-medium ${strategy.performance.totalPnL >= 0 ? "text-green-500" : "text-red-500"}`}
                  >
                    {strategy.performance.totalPnL >= 0 ? "+" : ""}${strategy.performance.totalPnL}
                  </span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Strategy Details */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center space-x-2">
                  <Bot className="w-5 h-5" />
                  <span>{selectedStrategy.name}</span>
                </CardTitle>
                <CardDescription>{selectedStrategy.description}</CardDescription>
              </div>
              <div className="flex items-center space-x-2">
                {getStatusBadge(selectedStrategy.status)}
                <Button variant="outline" size="sm" onClick={() => toggleStrategy(selectedStrategy.id)}>
                  {selectedStrategy.status === "active" ? (
                    <>
                      <Pause className="w-4 h-4 mr-2" />
                      Pause
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-2" />
                      Start
                    </>
                  )}
                </Button>
                <Button variant="outline" size="sm">
                  <Settings className="w-4 h-4 mr-2" />
                  Configure
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="performance" className="space-y-4">
              <TabsList>
                <TabsTrigger value="performance">Performance</TabsTrigger>
                <TabsTrigger value="settings">Settings</TabsTrigger>
              </TabsList>

              <TabsContent value="performance" className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="text-center p-4 rounded-lg bg-muted/50">
                    <div className="text-2xl font-bold">{selectedStrategy.performance.totalTrades}</div>
                    <div className="text-xs text-muted-foreground">Total Trades</div>
                  </div>
                  <div className="text-center p-4 rounded-lg bg-muted/50">
                    <div className="text-2xl font-bold">{selectedStrategy.performance.winRate}%</div>
                    <div className="text-xs text-muted-foreground">Win Rate</div>
                  </div>
                  <div className="text-center p-4 rounded-lg bg-muted/50">
                    <div
                      className={`text-2xl font-bold ${
                        selectedStrategy.performance.totalPnL >= 0 ? "text-green-500" : "text-red-500"
                      }`}
                    >
                      {selectedStrategy.performance.totalPnL >= 0 ? "+" : ""}${selectedStrategy.performance.totalPnL}
                    </div>
                    <div className="text-xs text-muted-foreground">Total P&L</div>
                  </div>
                  <div className="text-center p-4 rounded-lg bg-muted/50">
                    <div className="text-2xl font-bold">${selectedStrategy.performance.avgTrade}</div>
                    <div className="text-xs text-muted-foreground">Avg Trade</div>
                  </div>
                  <div className="text-center p-4 rounded-lg bg-muted/50">
                    <div className="text-2xl font-bold text-red-500">
                      ${Math.abs(selectedStrategy.performance.maxDrawdown)}
                    </div>
                    <div className="text-xs text-muted-foreground">Max Drawdown</div>
                  </div>
                </div>

                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Win Rate Progress</span>
                      <span>{selectedStrategy.performance.winRate}%</span>
                    </div>
                    <Progress value={selectedStrategy.performance.winRate} />
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="settings" className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium">Risk Per Trade</span>
                      <span className="text-sm">{selectedStrategy.settings.riskPerTrade}%</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium">Max Positions</span>
                      <span className="text-sm">{selectedStrategy.settings.maxPositions}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium">Timeframe</span>
                      <span className="text-sm">{selectedStrategy.settings.timeframe}</span>
                    </div>
                  </div>
                  <div className="space-y-3">
                    <div>
                      <span className="text-sm font-medium">Trading Assets</span>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {selectedStrategy.settings.assets.map((asset, index) => (
                          <Badge key={index} variant="outline" className="text-xs">
                            {asset}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
