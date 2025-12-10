"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Settings,
  Shield,
  TrendingUp,
  Brain,
  Database,
  RefreshCw,
  Save,
  AlertTriangle,
  CheckCircle,
  Info,
} from "lucide-react"
import Link from "next/link"

interface TradingSettings {
  defaultStopLoss: number
  defaultTakeProfit: number
  maxDailyLoss: number
  maxPositionSize: number
  maxOpenTrades: number
  tradingMode: "demo" | "paper" | "live"
  demoEnabled: boolean
  demoInitialBalance: number
  backtestEnabled: boolean
  backtestStartDate: string
  backtestEndDate: string
  defaultTradeSize: number
  aiPrimaryModel: string
  aiFallbackModel: string
  aiSentimentModel: string
  logLevel: "debug" | "info" | "warn" | "error"
  enableStructuredLogs: boolean
  enableProfiling: boolean
  dbPoolSize: number
  dbMaxOverflow: number
  dataRefreshInterval: number
}

interface Recommendation {
  min?: number
  max?: number
  recommended: number | string | boolean
  description: string
  riskLevel: "low" | "medium" | "high"
}

interface RiskFactor {
  name: string
  risk: "low" | "medium" | "high"
  note: string
}

export default function TradingSettingsPage() {
  const [settings, setSettings] = useState<TradingSettings | null>(null)
  const [recommendations, setRecommendations] = useState<Record<string, Recommendation>>({})
  const [riskAssessment, setRiskAssessment] = useState<{
    overallRisk: "low" | "medium" | "high"
    factors: RiskFactor[]
  } | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)
  const [pendingChanges, setPendingChanges] = useState<Partial<TradingSettings>>({})

  useEffect(() => {
    loadSettings()
  }, [])

  async function loadSettings() {
    try {
      const response = await fetch("/api/settings")
      const data = await response.json()

      if (data.success) {
        setSettings(data.settings)
        setRecommendations(data.recommendations)
        setRiskAssessment(data.riskAssessment)
      }
    } catch (error) {
      console.error("Failed to load settings:", error)
      setMessage({ type: "error", text: "Failed to load settings" })
    } finally {
      setLoading(false)
    }
  }

  async function saveSettings() {
    if (Object.keys(pendingChanges).length === 0) {
      setMessage({ type: "error", text: "No changes to save" })
      return
    }

    setSaving(true)
    try {
      const response = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ updates: pendingChanges }),
      })

      const data = await response.json()

      if (data.success) {
        setSettings(data.settings)
        setRiskAssessment(data.riskAssessment)
        setPendingChanges({})
        setMessage({ type: "success", text: "Settings saved successfully!" })
      } else {
        setMessage({ type: "error", text: data.errors?.join(", ") || data.error })
      }
    } catch (error) {
      setMessage({ type: "error", text: "Failed to save settings" })
    } finally {
      setSaving(false)
    }
  }

  async function resetDefaults() {
    setSaving(true)
    try {
      const response = await fetch("/api/settings", { method: "DELETE" })
      const data = await response.json()

      if (data.success) {
        setSettings(data.settings)
        setRiskAssessment(data.riskAssessment)
        setPendingChanges({})
        setMessage({ type: "success", text: "Settings reset to professional defaults!" })
      }
    } catch (error) {
      setMessage({ type: "error", text: "Failed to reset settings" })
    } finally {
      setSaving(false)
    }
  }

  function updateSetting<K extends keyof TradingSettings>(key: K, value: TradingSettings[K]) {
    setPendingChanges((prev) => ({ ...prev, [key]: value }))
    setSettings((prev) => (prev ? { ...prev, [key]: value } : null))
  }

  if (loading || !settings) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const riskColor = {
    low: "text-green-500",
    medium: "text-yellow-500",
    high: "text-red-500",
  }

  const riskBg = {
    low: "bg-green-500/10 border-green-500/20",
    medium: "bg-yellow-500/10 border-yellow-500/20",
    high: "bg-red-500/10 border-red-500/20",
  }

  return (
    <div className="container mx-auto py-8 px-4 max-w-6xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">Trading Settings</h1>
          <p className="text-muted-foreground mt-1">Configure your trading parameters with professional defaults</p>
        </div>
        <div className="flex gap-2">
          <Link href="/settings">
            <Button variant="outline">
              <Settings className="h-4 w-4 mr-2" />
              API Keys
            </Button>
          </Link>
          <Button variant="outline" onClick={resetDefaults} disabled={saving}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Reset Defaults
          </Button>
          <Button onClick={saveSettings} disabled={saving || Object.keys(pendingChanges).length === 0}>
            <Save className="h-4 w-4 mr-2" />
            {saving ? "Saving..." : "Save Changes"}
          </Button>
        </div>
      </div>

      {message && (
        <Alert className={`mb-6 ${message.type === "success" ? "border-green-500/50" : "border-red-500/50"}`}>
          {message.type === "success" ? (
            <CheckCircle className="h-4 w-4 text-green-500" />
          ) : (
            <AlertTriangle className="h-4 w-4 text-red-500" />
          )}
          <AlertDescription>{message.text}</AlertDescription>
        </Alert>
      )}

      {/* Risk Assessment Card */}
      {riskAssessment && (
        <Card className={`mb-6 ${riskBg[riskAssessment.overallRisk]}`}>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <Shield className={`h-5 w-5 ${riskColor[riskAssessment.overallRisk]}`} />
              Risk Assessment:{" "}
              <span className={`capitalize ${riskColor[riskAssessment.overallRisk]}`}>
                {riskAssessment.overallRisk}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {riskAssessment.factors.map((factor, i) => (
                <div key={i} className="flex items-start gap-2">
                  <Badge
                    variant={factor.risk === "low" ? "default" : factor.risk === "medium" ? "secondary" : "destructive"}
                  >
                    {factor.risk}
                  </Badge>
                  <div>
                    <div className="font-medium text-sm">{factor.name}</div>
                    <div className="text-xs text-muted-foreground">{factor.note}</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="risk" className="space-y-6">
        <TabsList className="grid grid-cols-4 w-full max-w-2xl">
          <TabsTrigger value="risk">
            <Shield className="h-4 w-4 mr-2" />
            Risk
          </TabsTrigger>
          <TabsTrigger value="trading">
            <TrendingUp className="h-4 w-4 mr-2" />
            Trading
          </TabsTrigger>
          <TabsTrigger value="ai">
            <Brain className="h-4 w-4 mr-2" />
            AI Models
          </TabsTrigger>
          <TabsTrigger value="system">
            <Database className="h-4 w-4 mr-2" />
            System
          </TabsTrigger>
        </TabsList>

        {/* Risk Management Tab */}
        <TabsContent value="risk">
          <div className="grid md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Stop Loss & Take Profit</CardTitle>
                <CardDescription>Professional traders use 1:3 risk/reward ratio</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <Label>Stop Loss: {(settings.defaultStopLoss * 100).toFixed(1)}%</Label>
                    <Badge variant="outline">{recommendations.defaultStopLoss?.riskLevel}</Badge>
                  </div>
                  <Slider
                    value={[settings.defaultStopLoss * 100]}
                    onValueChange={([v]) => updateSetting("defaultStopLoss", v / 100)}
                    min={0.5}
                    max={5}
                    step={0.1}
                  />
                  <p className="text-xs text-muted-foreground">{recommendations.defaultStopLoss?.description}</p>
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between">
                    <Label>Take Profit: {(settings.defaultTakeProfit * 100).toFixed(1)}%</Label>
                    <Badge variant="outline">
                      R:R {(settings.defaultTakeProfit / settings.defaultStopLoss).toFixed(1)}:1
                    </Badge>
                  </div>
                  <Slider
                    value={[settings.defaultTakeProfit * 100]}
                    onValueChange={([v]) => updateSetting("defaultTakeProfit", v / 100)}
                    min={1}
                    max={20}
                    step={0.5}
                  />
                  <p className="text-xs text-muted-foreground">{recommendations.defaultTakeProfit?.description}</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Position Limits</CardTitle>
                <CardDescription>Control exposure and protect capital</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label>Max Daily Loss ($)</Label>
                  <Input
                    type="number"
                    value={settings.maxDailyLoss}
                    onChange={(e) => updateSetting("maxDailyLoss", Number(e.target.value))}
                    min={100}
                    max={5000}
                  />
                  <p className="text-xs text-muted-foreground">{recommendations.maxDailyLoss?.description}</p>
                </div>

                <div className="space-y-2">
                  <Label>Max Position Size ($)</Label>
                  <Input
                    type="number"
                    value={settings.maxPositionSize}
                    onChange={(e) => updateSetting("maxPositionSize", Number(e.target.value))}
                    min={100}
                    max={10000}
                  />
                  <p className="text-xs text-muted-foreground">{recommendations.maxPositionSize?.description}</p>
                </div>

                <div className="space-y-2">
                  <Label>Max Open Trades</Label>
                  <Input
                    type="number"
                    value={settings.maxOpenTrades}
                    onChange={(e) => updateSetting("maxOpenTrades", Number(e.target.value))}
                    min={1}
                    max={20}
                  />
                  <p className="text-xs text-muted-foreground">{recommendations.maxOpenTrades?.description}</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Trading Tab */}
        <TabsContent value="trading">
          <div className="grid md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Trading Mode</CardTitle>
                <CardDescription>Start with demo, graduate to paper, then live</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label>Mode</Label>
                  <Select
                    value={settings.tradingMode}
                    onValueChange={(v) => updateSetting("tradingMode", v as "demo" | "paper" | "live")}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="demo">Demo (Virtual Money)</SelectItem>
                      <SelectItem value="paper">Paper (Simulated)</SelectItem>
                      <SelectItem value="live">Live (Real Funds)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label>Enable Demo Mode</Label>
                    <p className="text-xs text-muted-foreground">Allow demo trading</p>
                  </div>
                  <Switch checked={settings.demoEnabled} onCheckedChange={(v) => updateSetting("demoEnabled", v)} />
                </div>

                <div className="space-y-2">
                  <Label>Demo Initial Balance ($)</Label>
                  <Input
                    type="number"
                    value={settings.demoInitialBalance}
                    onChange={(e) => updateSetting("demoInitialBalance", Number(e.target.value))}
                    min={1000}
                    max={100000}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Default Trade Size ($)</Label>
                  <Input
                    type="number"
                    value={settings.defaultTradeSize}
                    onChange={(e) => updateSetting("defaultTradeSize", Number(e.target.value))}
                    min={50}
                    max={5000}
                  />
                  <p className="text-xs text-muted-foreground">{recommendations.defaultTradeSize?.description}</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Backtesting</CardTitle>
                <CardDescription>Test strategies on historical data</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Enable Backtesting</Label>
                    <p className="text-xs text-muted-foreground">Validate strategies before trading</p>
                  </div>
                  <Switch
                    checked={settings.backtestEnabled}
                    onCheckedChange={(v) => updateSetting("backtestEnabled", v)}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Start Date</Label>
                  <Input
                    type="date"
                    value={settings.backtestStartDate}
                    onChange={(e) => updateSetting("backtestStartDate", e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label>End Date</Label>
                  <Input
                    type="date"
                    value={settings.backtestEndDate}
                    onChange={(e) => updateSetting("backtestEndDate", e.target.value)}
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* AI Models Tab */}
        <TabsContent value="ai">
          <Card>
            <CardHeader>
              <CardTitle>AI Model Configuration</CardTitle>
              <CardDescription>Configure which AI models to use for trading analysis</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid md:grid-cols-3 gap-6">
                <div className="space-y-2">
                  <Label>Primary AI Model</Label>
                  <Select value={settings.aiPrimaryModel} onValueChange={(v) => updateSetting("aiPrimaryModel", v)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="openai">OpenAI GPT-4o (Most Accurate)</SelectItem>
                      <SelectItem value="anthropic">Anthropic Claude</SelectItem>
                      <SelectItem value="google">Google Gemini</SelectItem>
                      <SelectItem value="grok">xAI Grok</SelectItem>
                      <SelectItem value="groq">Groq (Fastest)</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">Used for main trading analysis</p>
                </div>

                <div className="space-y-2">
                  <Label>Fallback AI Model</Label>
                  <Select value={settings.aiFallbackModel} onValueChange={(v) => updateSetting("aiFallbackModel", v)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="groq">Groq (Fastest)</SelectItem>
                      <SelectItem value="openai">OpenAI GPT-4o</SelectItem>
                      <SelectItem value="grok">xAI Grok</SelectItem>
                      <SelectItem value="anthropic">Anthropic Claude</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">Used when primary fails</p>
                </div>

                <div className="space-y-2">
                  <Label>Sentiment Analysis Model</Label>
                  <Select value={settings.aiSentimentModel} onValueChange={(v) => updateSetting("aiSentimentModel", v)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="perplexity">Perplexity (Real-time Web)</SelectItem>
                      <SelectItem value="openai">OpenAI GPT-4o</SelectItem>
                      <SelectItem value="grok">xAI Grok</SelectItem>
                      <SelectItem value="cohere">Cohere</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">Used for market sentiment</p>
                </div>
              </div>

              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  Ensure you have configured API keys for your selected models in the{" "}
                  <Link href="/settings" className="underline">
                    API Settings
                  </Link>{" "}
                  page.
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        </TabsContent>

        {/* System Tab */}
        <TabsContent value="system">
          <div className="grid md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Logging & Monitoring</CardTitle>
                <CardDescription>Configure logging for debugging and monitoring</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label>Log Level</Label>
                  <Select
                    value={settings.logLevel}
                    onValueChange={(v) => updateSetting("logLevel", v as "debug" | "info" | "warn" | "error")}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="debug">Debug (Most Verbose)</SelectItem>
                      <SelectItem value="info">Info (Recommended)</SelectItem>
                      <SelectItem value="warn">Warning</SelectItem>
                      <SelectItem value="error">Error Only</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label>Structured Logs (JSON)</Label>
                    <p className="text-xs text-muted-foreground">Better for log aggregation</p>
                  </div>
                  <Switch
                    checked={settings.enableStructuredLogs}
                    onCheckedChange={(v) => updateSetting("enableStructuredLogs", v)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label>Performance Profiling</Label>
                    <p className="text-xs text-muted-foreground">Enable for debugging only</p>
                  </div>
                  <Switch
                    checked={settings.enableProfiling}
                    onCheckedChange={(v) => updateSetting("enableProfiling", v)}
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Database & Performance</CardTitle>
                <CardDescription>Optimize for your usage patterns</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label>Database Pool Size</Label>
                  <Input
                    type="number"
                    value={settings.dbPoolSize}
                    onChange={(e) => updateSetting("dbPoolSize", Number(e.target.value))}
                    min={5}
                    max={50}
                  />
                  <p className="text-xs text-muted-foreground">{recommendations.dbPoolSize?.description}</p>
                </div>

                <div className="space-y-2">
                  <Label>Max Overflow Connections</Label>
                  <Input
                    type="number"
                    value={settings.dbMaxOverflow}
                    onChange={(e) => updateSetting("dbMaxOverflow", Number(e.target.value))}
                    min={5}
                    max={100}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Data Refresh Interval (seconds)</Label>
                  <Input
                    type="number"
                    value={settings.dataRefreshInterval}
                    onChange={(e) => updateSetting("dataRefreshInterval", Number(e.target.value))}
                    min={1}
                    max={60}
                  />
                  <p className="text-xs text-muted-foreground">{recommendations.dataRefreshInterval?.description}</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Pending Changes Indicator */}
      {Object.keys(pendingChanges).length > 0 && (
        <div className="fixed bottom-6 right-6 bg-primary text-primary-foreground px-4 py-2 rounded-lg shadow-lg flex items-center gap-3">
          <span>{Object.keys(pendingChanges).length} unsaved changes</span>
          <Button size="sm" variant="secondary" onClick={saveSettings} disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </Button>
        </div>
      )}
    </div>
  )
}
