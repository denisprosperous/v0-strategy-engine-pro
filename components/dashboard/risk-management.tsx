"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Switch } from "@/components/ui/switch"
import { Slider } from "@/components/ui/slider"
import { AlertTriangle, Shield, Settings } from "lucide-react"

const riskMetrics = {
  portfolioValue: 12450.67,
  dailyPnL: 234.56,
  maxDailyLoss: 1000,
  currentDrawdown: 125.5,
  maxDrawdown: 500,
  openPositions: 5,
  maxPositions: 10,
  riskPerTrade: 1.5,
  totalRiskExposure: 7.5,
  maxRiskExposure: 15,
  volatilityScore: 68,
  correlationRisk: 42,
}

const riskSettings = {
  maxDailyLoss: 1000,
  maxPositionSize: 2000,
  maxOpenTrades: 10,
  stopLossEnabled: true,
  trailingStopEnabled: true,
  riskPerTrade: 1.5,
  correlationLimit: 0.7,
  volatilityThreshold: 80,
}

const alerts = [
  {
    id: 1,
    type: "warning",
    message: "Daily P&L approaching 75% of maximum allowed loss",
    timestamp: "2024-01-15 14:30:25",
    severity: "medium",
  },
  {
    id: 2,
    type: "info",
    message: "Portfolio correlation risk increased to 42%",
    timestamp: "2024-01-15 13:45:12",
    severity: "low",
  },
  {
    id: 3,
    type: "success",
    message: "All positions have stop-loss orders active",
    timestamp: "2024-01-15 12:20:08",
    severity: "low",
  },
]

export function RiskManagement() {
  const [settings, setSettings] = useState(riskSettings)

  const getRiskLevel = (percentage: number) => {
    if (percentage >= 80) return { level: "High", color: "text-red-500", bg: "bg-red-500" }
    if (percentage >= 60) return { level: "Medium", color: "text-yellow-500", bg: "bg-yellow-500" }
    return { level: "Low", color: "text-green-500", bg: "bg-green-500" }
  }

  const dailyLossPercentage = (Math.abs(riskMetrics.dailyPnL) / riskMetrics.maxDailyLoss) * 100
  const drawdownPercentage = (riskMetrics.currentDrawdown / riskMetrics.maxDrawdown) * 100
  const positionPercentage = (riskMetrics.openPositions / riskMetrics.maxPositions) * 100
  const riskExposurePercentage = (riskMetrics.totalRiskExposure / riskMetrics.maxRiskExposure) * 100

  const dailyLossRisk = getRiskLevel(dailyLossPercentage)
  const drawdownRisk = getRiskLevel(drawdownPercentage)
  const exposureRisk = getRiskLevel(riskExposurePercentage)

  return (
    <div className="space-y-6">
      {/* Risk Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Daily P&L Risk</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-2">
              <span className="text-2xl font-bold">{dailyLossPercentage.toFixed(1)}%</span>
              <Badge className={`${dailyLossRisk.color} bg-transparent border-current`}>{dailyLossRisk.level}</Badge>
            </div>
            <Progress value={dailyLossPercentage} className="mb-2" />
            <div className="text-xs text-muted-foreground">
              ${Math.abs(riskMetrics.dailyPnL)} / ${riskMetrics.maxDailyLoss} max
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Drawdown Risk</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-2">
              <span className="text-2xl font-bold">{drawdownPercentage.toFixed(1)}%</span>
              <Badge className={`${drawdownRisk.color} bg-transparent border-current`}>{drawdownRisk.level}</Badge>
            </div>
            <Progress value={drawdownPercentage} className="mb-2" />
            <div className="text-xs text-muted-foreground">
              ${riskMetrics.currentDrawdown} / ${riskMetrics.maxDrawdown} max
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Position Usage</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-2">
              <span className="text-2xl font-bold">{positionPercentage.toFixed(0)}%</span>
              <Badge variant="outline">
                {riskMetrics.openPositions}/{riskMetrics.maxPositions}
              </Badge>
            </div>
            <Progress value={positionPercentage} className="mb-2" />
            <div className="text-xs text-muted-foreground">Open positions</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Risk Exposure</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-2">
              <span className="text-2xl font-bold">{riskExposurePercentage.toFixed(1)}%</span>
              <Badge className={`${exposureRisk.color} bg-transparent border-current`}>{exposureRisk.level}</Badge>
            </div>
            <Progress value={riskExposurePercentage} className="mb-2" />
            <div className="text-xs text-muted-foreground">
              {riskMetrics.totalRiskExposure}% / {riskMetrics.maxRiskExposure}% max
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Settings className="w-5 h-5" />
              <span>Risk Settings</span>
            </CardTitle>
            <CardDescription>Configure risk management parameters</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-sm font-medium">Stop Loss Protection</label>
                  <p className="text-xs text-muted-foreground">Automatically set stop losses</p>
                </div>
                <Switch
                  checked={settings.stopLossEnabled}
                  onCheckedChange={(checked) => setSettings((prev) => ({ ...prev, stopLossEnabled: checked }))}
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <label className="text-sm font-medium">Trailing Stop</label>
                  <p className="text-xs text-muted-foreground">Enable trailing stop losses</p>
                </div>
                <Switch
                  checked={settings.trailingStopEnabled}
                  onCheckedChange={(checked) => setSettings((prev) => ({ ...prev, trailingStopEnabled: checked }))}
                />
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="text-sm font-medium">Max Daily Loss</label>
                  <span className="text-sm">${settings.maxDailyLoss}</span>
                </div>
                <Slider
                  value={[settings.maxDailyLoss]}
                  onValueChange={([value]) => setSettings((prev) => ({ ...prev, maxDailyLoss: value }))}
                  max={5000}
                  min={100}
                  step={100}
                  className="w-full"
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="text-sm font-medium">Risk Per Trade</label>
                  <span className="text-sm">{settings.riskPerTrade}%</span>
                </div>
                <Slider
                  value={[settings.riskPerTrade]}
                  onValueChange={([value]) => setSettings((prev) => ({ ...prev, riskPerTrade: value }))}
                  max={5}
                  min={0.1}
                  step={0.1}
                  className="w-full"
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="text-sm font-medium">Max Open Trades</label>
                  <span className="text-sm">{settings.maxOpenTrades}</span>
                </div>
                <Slider
                  value={[settings.maxOpenTrades]}
                  onValueChange={([value]) => setSettings((prev) => ({ ...prev, maxOpenTrades: value }))}
                  max={20}
                  min={1}
                  step={1}
                  className="w-full"
                />
              </div>
            </div>

            <Button className="w-full">Save Settings</Button>
          </CardContent>
        </Card>

        {/* Risk Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5" />
              <span>Risk Alerts</span>
            </CardTitle>
            <CardDescription>Recent risk management notifications</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {alerts.map((alert) => (
                <div key={alert.id} className="flex items-start space-x-3 p-3 rounded-lg border">
                  <div
                    className={`w-2 h-2 rounded-full mt-2 ${
                      alert.severity === "high"
                        ? "bg-red-500"
                        : alert.severity === "medium"
                          ? "bg-yellow-500"
                          : "bg-green-500"
                    }`}
                  ></div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{alert.message}</p>
                    <p className="text-xs text-muted-foreground mt-1">{alert.timestamp}</p>
                  </div>
                  <Badge
                    variant={
                      alert.severity === "high" ? "destructive" : alert.severity === "medium" ? "secondary" : "outline"
                    }
                  >
                    {alert.severity}
                  </Badge>
                </div>
              ))}
            </div>

            <div className="mt-6 p-4 rounded-lg bg-muted/50">
              <div className="flex items-center space-x-2 mb-2">
                <Shield className="w-4 h-4 text-green-500" />
                <span className="text-sm font-medium">Risk Status: Protected</span>
              </div>
              <p className="text-xs text-muted-foreground">
                All risk management systems are active and monitoring your portfolio.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Advanced Risk Metrics */}
      <Card>
        <CardHeader>
          <CardTitle>Advanced Risk Metrics</CardTitle>
          <CardDescription>Detailed risk analysis and correlations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center p-4 rounded-lg bg-muted/50">
              <div className="text-2xl font-bold">{riskMetrics.volatilityScore}</div>
              <div className="text-sm text-muted-foreground">Volatility Score</div>
              <Progress value={riskMetrics.volatilityScore} className="mt-2" />
            </div>
            <div className="text-center p-4 rounded-lg bg-muted/50">
              <div className="text-2xl font-bold">{riskMetrics.correlationRisk}%</div>
              <div className="text-sm text-muted-foreground">Correlation Risk</div>
              <Progress value={riskMetrics.correlationRisk} className="mt-2" />
            </div>
            <div className="text-center p-4 rounded-lg bg-muted/50">
              <div className="text-2xl font-bold">0.85</div>
              <div className="text-sm text-muted-foreground">Sharpe Ratio</div>
              <div className="text-xs text-green-500 mt-1">Excellent</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
