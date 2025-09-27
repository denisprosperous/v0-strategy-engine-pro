"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { useToast } from "@/hooks/use-toast"
import { Brain, TrendingUp, Settings, Loader2 } from "lucide-react"

interface FibonacciLevel {
  level: number
  price: number
  strength: number
  type: "support" | "resistance"
}

interface StrategyInsights {
  fibonacciLevels: FibonacciLevel[]
  modelWeights: Record<string, number>
  adaptiveParameters: Record<string, number>
  performanceMetrics: {
    totalTrades: number
    winRate: number
    avgReturn: number
    sharpeRatio: number
  }
  patternHistorySize: number
}

interface OptimizationConfig {
  symbol: string
  startDate: string
  endDate: string
  optimizationTargets: string[]
  parameterRanges: {
    lookbackPeriod: [number, number]
    minPatternStrength: [number, number]
    sentimentWeight: [number, number]
  }
}

export function FibonacciMLPanel() {
  const [insights, setInsights] = useState<StrategyInsights | null>(null)
  const [optimizationConfig, setOptimizationConfig] = useState<OptimizationConfig>({
    symbol: "BTCUSDT",
    startDate: "2024-01-01",
    endDate: "2024-12-31",
    optimizationTargets: ["winRate", "sharpeRatio"],
    parameterRanges: {
      lookbackPeriod: [20, 100],
      minPatternStrength: [0.5, 0.9],
      sentimentWeight: [0.1, 0.5],
    },
  })
  const [optimizationResults, setOptimizationResults] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()

  useEffect(() => {
    // Simulate loading strategy insights
    const mockInsights: StrategyInsights = {
      fibonacciLevels: [
        { level: 0.618, price: 42500, strength: 0.85, type: "support" },
        { level: 0.382, price: 45200, strength: 0.72, type: "resistance" },
        { level: 0.5, price: 43850, strength: 0.68, type: "support" },
        { level: 0.236, price: 46100, strength: 0.55, type: "resistance" },
        { level: 0.786, price: 41200, strength: 0.48, type: "support" },
      ],
      modelWeights: {
        trendStrength: 0.25,
        volatility: 0.15,
        volume: 0.1,
        fibonacciAlignment: 0.3,
        sentimentScore: 0.2,
      },
      adaptiveParameters: {
        stopLossMultiplier: 1.2,
        takeProfitMultiplier: 1.1,
        positionSizeMultiplier: 0.9,
        minPatternStrength: 0.7,
      },
      performanceMetrics: {
        totalTrades: 156,
        winRate: 68.5,
        avgReturn: 2.3,
        sharpeRatio: 1.42,
      },
      patternHistorySize: 892,
    }
    setInsights(mockInsights)
  }, [])

  const runOptimization = async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/strategies/fibonacci-ml/optimize", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(optimizationConfig),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || "Failed to run optimization")
      }

      setOptimizationResults(data.optimization.results)
      toast({
        title: "Success",
        description: "Strategy optimization completed successfully",
      })
    } catch (error) {
      console.error("Optimization error:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to run optimization",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(value)
  }

  const getStrengthColor = (strength: number) => {
    if (strength >= 0.8) return "text-green-500"
    if (strength >= 0.6) return "text-yellow-500"
    return "text-red-500"
  }

  const getLevelTypeColor = (type: string) => {
    return type === "support"
      ? "bg-green-500/10 text-green-500 border-green-500/20"
      : "bg-red-500/10 text-red-500 border-red-500/20"
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Brain className="w-5 h-5" />
            <span>Fibonacci ML Strategy</span>
          </CardTitle>
          <CardDescription>Advanced Fibonacci strategy with machine learning enhancements</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="insights" className="space-y-4">
            <TabsList>
              <TabsTrigger value="insights">Strategy Insights</TabsTrigger>
              <TabsTrigger value="fibonacci">Fibonacci Levels</TabsTrigger>
              <TabsTrigger value="ml">ML Model</TabsTrigger>
              <TabsTrigger value="optimization">Optimization</TabsTrigger>
            </TabsList>

            <TabsContent value="insights" className="space-y-4">
              {insights && (
                <>
                  {/* Performance Metrics */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <Card>
                      <CardContent className="pt-6">
                        <div className="text-2xl font-bold">{insights.performanceMetrics.totalTrades}</div>
                        <div className="text-xs text-muted-foreground">Total Trades</div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardContent className="pt-6">
                        <div className="text-2xl font-bold text-green-500">{insights.performanceMetrics.winRate}%</div>
                        <div className="text-xs text-muted-foreground">Win Rate</div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardContent className="pt-6">
                        <div className="text-2xl font-bold">{insights.performanceMetrics.avgReturn}%</div>
                        <div className="text-xs text-muted-foreground">Avg Return</div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardContent className="pt-6">
                        <div className="text-2xl font-bold">{insights.performanceMetrics.sharpeRatio}</div>
                        <div className="text-xs text-muted-foreground">Sharpe Ratio</div>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Adaptive Parameters */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Adaptive Parameters</CardTitle>
                      <CardDescription>Self-adjusting strategy parameters based on performance</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 gap-4">
                        {Object.entries(insights.adaptiveParameters).map(([key, value]) => (
                          <div key={key} className="flex justify-between items-center p-3 rounded border">
                            <span className="text-sm font-medium capitalize">{key.replace(/([A-Z])/g, " $1")}</span>
                            <span className="font-bold">{value.toFixed(2)}</span>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </>
              )}
            </TabsContent>

            <TabsContent value="fibonacci" className="space-y-4">
              {insights && (
                <Card>
                  <CardHeader>
                    <CardTitle>Current Fibonacci Levels</CardTitle>
                    <CardDescription>Active support and resistance levels with strength indicators</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {insights.fibonacciLevels.map((level, index) => (
                        <div key={index} className="flex items-center justify-between p-4 rounded border">
                          <div className="flex items-center space-x-3">
                            <Badge className={getLevelTypeColor(level.type)}>{level.type}</Badge>
                            <div>
                              <div className="font-medium">{(level.level * 100).toFixed(1)}% Level</div>
                              <div className="text-sm text-muted-foreground">{formatCurrency(level.price)}</div>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className={`font-bold ${getStrengthColor(level.strength)}`}>
                              {(level.strength * 100).toFixed(0)}%
                            </div>
                            <div className="text-xs text-muted-foreground">Strength</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="ml" className="space-y-4">
              {insights && (
                <>
                  {/* Model Weights */}
                  <Card>
                    <CardHeader>
                      <CardTitle>ML Model Weights</CardTitle>
                      <CardDescription>Feature importance in the machine learning model</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {Object.entries(insights.modelWeights).map(([feature, weight]) => (
                          <div key={feature} className="space-y-2">
                            <div className="flex justify-between text-sm">
                              <span className="capitalize">{feature.replace(/([A-Z])/g, " $1")}</span>
                              <span className="font-medium">{(weight * 100).toFixed(1)}%</span>
                            </div>
                            <Progress value={weight * 100} className="h-2" />
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Learning Progress */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Learning Progress</CardTitle>
                      <CardDescription>Model training and adaptation metrics</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="text-center p-4 rounded border">
                          <div className="text-2xl font-bold">{insights.patternHistorySize}</div>
                          <div className="text-xs text-muted-foreground">Patterns Learned</div>
                        </div>
                        <div className="text-center p-4 rounded border">
                          <div className="text-2xl font-bold">
                            {Math.min(100, (insights.patternHistorySize / 1000) * 100).toFixed(0)}%
                          </div>
                          <div className="text-xs text-muted-foreground">Training Progress</div>
                        </div>
                        <div className="text-center p-4 rounded border">
                          <div className="text-2xl font-bold">
                            {insights.performanceMetrics.totalTrades > 50 ? "Active" : "Learning"}
                          </div>
                          <div className="text-xs text-muted-foreground">Model Status</div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </>
              )}
            </TabsContent>

            <TabsContent value="optimization" className="space-y-4">
              {/* Optimization Configuration */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Settings className="w-5 h-5" />
                    <span>Parameter Optimization</span>
                  </CardTitle>
                  <CardDescription>Optimize strategy parameters using historical data</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="symbol">Symbol</Label>
                      <Select
                        value={optimizationConfig.symbol}
                        onValueChange={(value) => setOptimizationConfig((prev) => ({ ...prev, symbol: value }))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="BTCUSDT">BTC/USDT</SelectItem>
                          <SelectItem value="ETHUSDT">ETH/USDT</SelectItem>
                          <SelectItem value="SOLUSDT">SOL/USDT</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="startDate">Start Date</Label>
                      <Input
                        id="startDate"
                        type="date"
                        value={optimizationConfig.startDate}
                        onChange={(e) => setOptimizationConfig((prev) => ({ ...prev, startDate: e.target.value }))}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="endDate">End Date</Label>
                      <Input
                        id="endDate"
                        type="date"
                        value={optimizationConfig.endDate}
                        onChange={(e) => setOptimizationConfig((prev) => ({ ...prev, endDate: e.target.value }))}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Optimization Targets</Label>
                    <div className="flex flex-wrap gap-2">
                      {["winRate", "sharpeRatio", "netPnL", "maxDrawdown"].map((target) => (
                        <Badge
                          key={target}
                          variant={optimizationConfig.optimizationTargets.includes(target) ? "default" : "outline"}
                          className="cursor-pointer"
                          onClick={() => {
                            const newTargets = optimizationConfig.optimizationTargets.includes(target)
                              ? optimizationConfig.optimizationTargets.filter((t) => t !== target)
                              : [...optimizationConfig.optimizationTargets, target]
                            setOptimizationConfig((prev) => ({ ...prev, optimizationTargets: newTargets }))
                          }}
                        >
                          {target}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <Button onClick={runOptimization} disabled={loading} className="w-full">
                    {loading ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <TrendingUp className="w-4 h-4 mr-2" />
                    )}
                    {loading ? "Running Optimization..." : "Run Optimization"}
                  </Button>
                </CardContent>
              </Card>

              {/* Optimization Results */}
              {optimizationResults && (
                <Card>
                  <CardHeader>
                    <CardTitle>Optimization Results</CardTitle>
                    <CardDescription>Best parameter combinations found</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="p-4 rounded border bg-green-500/5">
                        <h4 className="font-medium text-green-500 mb-2">Best Parameters</h4>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          {Object.entries(optimizationResults.bestParameters).map(([key, value]) => (
                            <div key={key} className="flex justify-between">
                              <span className="capitalize">{key.replace(/([A-Z])/g, " $1")}:</span>
                              <span className="font-medium">{Number(value).toFixed(3)}</span>
                            </div>
                          ))}
                        </div>
                        <div className="mt-2 pt-2 border-t">
                          <div className="flex justify-between">
                            <span>Optimization Score:</span>
                            <span className="font-bold text-green-500">{optimizationResults.bestScore.toFixed(3)}</span>
                          </div>
                        </div>
                      </div>

                      <div className="text-sm text-muted-foreground">
                        Tested {optimizationResults.totalCombinations} parameter combinations
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}
