"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useToast } from "@/hooks/use-toast"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { Play, Loader2, BarChart3 } from "lucide-react"

interface BacktestConfig {
  strategyId: string
  startDate: string
  endDate: string
  initialBalance: number
  symbols: string[]
  commission: number
  slippage: number
  maxPositions: number
  riskPerTrade: number
}

interface BacktestResults {
  performance: {
    totalTrades: number
    winRate: number
    netPnL: number
    maxDrawdownPercent: number
    sharpeRatio: number
    profitFactor: number
  }
  equity: Array<{ date: string; balance: number; drawdown: number }>
  monthlyReturns: Array<{ month: string; return: number; trades: number }>
}

const strategies = [
  { id: "breakout-scalping", name: "Breakout Scalping" },
  { id: "mean-reversion", name: "Mean Reversion" },
  { id: "momentum-sentiment", name: "Momentum + Sentiment" },
  { id: "news-scalping", name: "News Event Scalping" },
]

const tradingPairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"]

export function BacktestingPanel() {
  const [config, setConfig] = useState<BacktestConfig>({
    strategyId: "",
    startDate: "2024-01-01",
    endDate: "2024-12-31",
    initialBalance: 10000,
    symbols: ["BTCUSDT", "ETHUSDT"],
    commission: 0.001,
    slippage: 0.0005,
    maxPositions: 5,
    riskPerTrade: 0.02,
  })
  const [results, setResults] = useState<BacktestResults | null>(null)
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()

  const runBacktest = async () => {
    if (!config.strategyId) {
      toast({
        title: "Error",
        description: "Please select a strategy",
        variant: "destructive",
      })
      return
    }

    setLoading(true)
    try {
      const response = await fetch("/api/backtesting/run", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(config),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || "Failed to run backtest")
      }

      setResults(data.backtest.results)
      toast({
        title: "Success",
        description: "Backtest completed successfully",
      })
    } catch (error) {
      console.error("Backtest error:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to run backtest",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const updateConfig = (key: keyof BacktestConfig, value: any) => {
    setConfig((prev) => ({ ...prev, [key]: value }))
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(value)
  }

  const formatPercentage = (value: number) => {
    return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <BarChart3 className="w-5 h-5" />
            <span>Strategy Backtesting</span>
          </CardTitle>
          <CardDescription>Test your strategies against historical data</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="config" className="space-y-4">
            <TabsList>
              <TabsTrigger value="config">Configuration</TabsTrigger>
              <TabsTrigger value="results" disabled={!results}>
                Results
              </TabsTrigger>
              <TabsTrigger value="analysis" disabled={!results}>
                Analysis
              </TabsTrigger>
            </TabsList>

            <TabsContent value="config" className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="strategy">Strategy</Label>
                  <Select value={config.strategyId} onValueChange={(value) => updateConfig("strategyId", value)}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a strategy" />
                    </SelectTrigger>
                    <SelectContent>
                      {strategies.map((strategy) => (
                        <SelectItem key={strategy.id} value={strategy.id}>
                          {strategy.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="initialBalance">Initial Balance ($)</Label>
                  <Input
                    id="initialBalance"
                    type="number"
                    value={config.initialBalance}
                    onChange={(e) => updateConfig("initialBalance", Number(e.target.value))}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="startDate">Start Date</Label>
                  <Input
                    id="startDate"
                    type="date"
                    value={config.startDate}
                    onChange={(e) => updateConfig("startDate", e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="endDate">End Date</Label>
                  <Input
                    id="endDate"
                    type="date"
                    value={config.endDate}
                    onChange={(e) => updateConfig("endDate", e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="commission">Commission (%)</Label>
                  <Input
                    id="commission"
                    type="number"
                    step="0.001"
                    value={config.commission}
                    onChange={(e) => updateConfig("commission", Number(e.target.value))}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="riskPerTrade">Risk Per Trade (%)</Label>
                  <Input
                    id="riskPerTrade"
                    type="number"
                    step="0.01"
                    value={config.riskPerTrade * 100}
                    onChange={(e) => updateConfig("riskPerTrade", Number(e.target.value) / 100)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Trading Pairs</Label>
                <div className="flex flex-wrap gap-2">
                  {tradingPairs.map((pair) => (
                    <Badge
                      key={pair}
                      variant={config.symbols.includes(pair) ? "default" : "outline"}
                      className="cursor-pointer"
                      onClick={() => {
                        const newSymbols = config.symbols.includes(pair)
                          ? config.symbols.filter((s) => s !== pair)
                          : [...config.symbols, pair]
                        updateConfig("symbols", newSymbols)
                      }}
                    >
                      {pair}
                    </Badge>
                  ))}
                </div>
              </div>

              <Button onClick={runBacktest} disabled={loading} className="w-full">
                {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Play className="w-4 h-4 mr-2" />}
                {loading ? "Running Backtest..." : "Run Backtest"}
              </Button>
            </TabsContent>

            <TabsContent value="results" className="space-y-4">
              {results && (
                <>
                  {/* Performance Metrics */}
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                    <Card>
                      <CardContent className="pt-6">
                        <div className="text-2xl font-bold">{results.performance.totalTrades}</div>
                        <div className="text-xs text-muted-foreground">Total Trades</div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardContent className="pt-6">
                        <div className="text-2xl font-bold">{results.performance.winRate.toFixed(1)}%</div>
                        <div className="text-xs text-muted-foreground">Win Rate</div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardContent className="pt-6">
                        <div
                          className={`text-2xl font-bold ${results.performance.netPnL >= 0 ? "text-green-500" : "text-red-500"}`}
                        >
                          {formatCurrency(results.performance.netPnL)}
                        </div>
                        <div className="text-xs text-muted-foreground">Net P&L</div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardContent className="pt-6">
                        <div className="text-2xl font-bold text-red-500">
                          {results.performance.maxDrawdownPercent.toFixed(1)}%
                        </div>
                        <div className="text-xs text-muted-foreground">Max Drawdown</div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardContent className="pt-6">
                        <div className="text-2xl font-bold">{results.performance.sharpeRatio.toFixed(2)}</div>
                        <div className="text-xs text-muted-foreground">Sharpe Ratio</div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardContent className="pt-6">
                        <div className="text-2xl font-bold">{results.performance.profitFactor.toFixed(2)}</div>
                        <div className="text-xs text-muted-foreground">Profit Factor</div>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Equity Curve */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Equity Curve</CardTitle>
                      <CardDescription>Portfolio value over time</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={results.equity}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="date" />
                            <YAxis />
                            <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                            <Line type="monotone" dataKey="balance" stroke="#8884d8" strokeWidth={2} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </CardContent>
                  </Card>
                </>
              )}
            </TabsContent>

            <TabsContent value="analysis" className="space-y-4">
              {results && (
                <>
                  {/* Monthly Returns */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Monthly Returns</CardTitle>
                      <CardDescription>Performance breakdown by month</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {results.monthlyReturns.map((month) => (
                          <div key={month.month} className="flex items-center justify-between p-2 rounded border">
                            <span className="font-medium">{month.month}</span>
                            <div className="flex items-center space-x-4">
                              <span className="text-sm text-muted-foreground">{month.trades} trades</span>
                              <span className={`font-medium ${month.return >= 0 ? "text-green-500" : "text-red-500"}`}>
                                {formatPercentage(month.return)}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Performance Summary */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Performance Summary</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <div className="flex justify-between">
                            <span>Total Return:</span>
                            <span
                              className={`font-medium ${results.performance.netPnL >= 0 ? "text-green-500" : "text-red-500"}`}
                            >
                              {formatPercentage((results.performance.netPnL / config.initialBalance) * 100)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>Annualized Return:</span>
                            <span className="font-medium">
                              {formatPercentage(
                                ((results.performance.netPnL / config.initialBalance) * 100 * 365) /
                                  Math.max(
                                    1,
                                    (new Date(config.endDate).getTime() - new Date(config.startDate).getTime()) /
                                      (1000 * 60 * 60 * 24),
                                  ),
                              )}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>Best Month:</span>
                            <span className="font-medium text-green-500">
                              {formatPercentage(Math.max(...results.monthlyReturns.map((m) => m.return)))}
                            </span>
                          </div>
                        </div>
                        <div className="space-y-2">
                          <div className="flex justify-between">
                            <span>Worst Month:</span>
                            <span className="font-medium text-red-500">
                              {formatPercentage(Math.min(...results.monthlyReturns.map((m) => m.return)))}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>Volatility:</span>
                            <span className="font-medium">
                              {Math.sqrt(
                                results.monthlyReturns.reduce(
                                  (acc, m) =>
                                    acc +
                                    Math.pow(
                                      m.return -
                                        results.monthlyReturns.reduce((a, b) => a + b.return, 0) /
                                          results.monthlyReturns.length,
                                      2,
                                    ),
                                  0,
                                ) / results.monthlyReturns.length,
                              ).toFixed(2)}
                              %
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>Calmar Ratio:</span>
                            <span className="font-medium">
                              {results.performance.maxDrawdownPercent > 0
                                ? (
                                    ((results.performance.netPnL / config.initialBalance) * 100) /
                                    results.performance.maxDrawdownPercent
                                  ).toFixed(2)
                                : "N/A"}
                            </span>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}
