"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { useToast } from "@/hooks/use-toast"
import { Play, Square, Activity, AlertTriangle, Loader2 } from "lucide-react"

interface EngineStatus {
  isRunning: boolean
  activeTrades: number
  activeStrategies: number
  dailyPnL: number
  connectedBrokers: string[]
  config: {
    demoMode: boolean
    autoTrading: boolean
    maxConcurrentTrades: number
    maxDailyLoss: number
  }
}

export function LiveTradingPanel() {
  const [engineStatus, setEngineStatus] = useState<EngineStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [demoMode, setDemoMode] = useState(true)
  const { toast } = useToast()

  useEffect(() => {
    fetchEngineStatus()
    const interval = setInterval(fetchEngineStatus, 5000) // Update every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchEngineStatus = async () => {
    try {
      const response = await fetch("/api/trading/engine/status")
      const data = await response.json()

      if (data.status) {
        setEngineStatus(data.status)
      } else {
        setEngineStatus(null)
      }
    } catch (error) {
      console.error("Failed to fetch engine status:", error)
    }
  }

  const startEngine = async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/trading/engine/start", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          demoMode,
          tradingPairs: ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || "Failed to start engine")
      }

      setEngineStatus(data.status)
      toast({
        title: "Success",
        description: data.message,
      })
    } catch (error) {
      console.error("Failed to start engine:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to start trading engine",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const stopEngine = async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/trading/engine/stop", {
        method: "POST",
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || "Failed to stop engine")
      }

      setEngineStatus(null)
      toast({
        title: "Success",
        description: data.message,
      })
    } catch (error) {
      console.error("Failed to stop engine:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to stop trading engine",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const getRiskLevel = (dailyPnL: number, maxDailyLoss: number) => {
    const riskPercentage = (Math.abs(dailyPnL) / maxDailyLoss) * 100
    if (riskPercentage > 80) return { level: "high", color: "text-red-500" }
    if (riskPercentage > 50) return { level: "medium", color: "text-yellow-500" }
    return { level: "low", color: "text-green-500" }
  }

  return (
    <div className="space-y-6">
      {/* Engine Control Panel */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center space-x-2">
                <Activity className="w-5 h-5" />
                <span>Live Trading Engine</span>
              </CardTitle>
              <CardDescription>Control your automated trading system</CardDescription>
            </div>
            <div className="flex items-center space-x-2">
              {engineStatus?.isRunning ? (
                <Badge className="bg-green-500/10 text-green-500 border-green-500/20">
                  <Activity className="w-3 h-3 mr-1" />
                  Running
                </Badge>
              ) : (
                <Badge variant="secondary">Stopped</Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Demo Mode Toggle */}
          <div className="flex items-center justify-between p-4 rounded-lg border">
            <div>
              <h4 className="font-medium">Demo Mode</h4>
              <p className="text-sm text-muted-foreground">Trade with virtual money for testing</p>
            </div>
            <Switch checked={demoMode} onCheckedChange={setDemoMode} disabled={engineStatus?.isRunning} />
          </div>

          {/* Engine Controls */}
          <div className="flex space-x-2">
            {!engineStatus?.isRunning ? (
              <Button onClick={startEngine} disabled={loading} className="flex-1">
                {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Play className="w-4 h-4 mr-2" />}
                Start Trading Engine
              </Button>
            ) : (
              <Button onClick={stopEngine} disabled={loading} variant="destructive" className="flex-1">
                {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Square className="w-4 h-4 mr-2" />}
                Stop Trading Engine
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Engine Status */}
      {engineStatus && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Active Trades</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{engineStatus.activeTrades}</div>
              <div className="text-xs text-muted-foreground">of {engineStatus.config.maxConcurrentTrades} max</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Daily P&L</CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${engineStatus.dailyPnL >= 0 ? "text-green-500" : "text-red-500"}`}>
                {engineStatus.dailyPnL >= 0 ? "+" : ""}${engineStatus.dailyPnL.toFixed(2)}
              </div>
              <div className="text-xs text-muted-foreground">
                {engineStatus.config.demoMode ? "Demo" : "Live"} trading
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Risk Level</CardTitle>
            </CardHeader>
            <CardContent>
              <div
                className={`text-2xl font-bold ${getRiskLevel(engineStatus.dailyPnL, engineStatus.config.maxDailyLoss).color}`}
              >
                {getRiskLevel(engineStatus.dailyPnL, engineStatus.config.maxDailyLoss).level.toUpperCase()}
              </div>
              <div className="text-xs text-muted-foreground">
                ${Math.abs(engineStatus.dailyPnL).toFixed(2)} / ${engineStatus.config.maxDailyLoss} limit
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Connected Brokers</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{engineStatus.connectedBrokers.length}</div>
              <div className="text-xs text-muted-foreground">{engineStatus.connectedBrokers.join(", ") || "None"}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Risk Warning */}
      {!demoMode && (
        <Card className="border-yellow-500/20 bg-yellow-500/5">
          <CardContent className="pt-6">
            <div className="flex items-start space-x-3">
              <AlertTriangle className="w-5 h-5 text-yellow-500 mt-0.5" />
              <div>
                <h4 className="font-medium text-yellow-500">Live Trading Warning</h4>
                <p className="text-sm text-muted-foreground mt-1">
                  You are about to trade with real money. Please ensure you understand the risks involved and have
                  configured appropriate risk management settings.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
