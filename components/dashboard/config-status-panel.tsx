"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { CheckCircle, XCircle, AlertTriangle, RefreshCw, Server, Database, Bot, Cpu, Wifi, Shield } from "lucide-react"

interface ConfigStatus {
  success: boolean
  timestamp: string
  status: {
    valid: boolean
    tradingMode: string
    readyForLiveTrading: boolean
  }
  validation: {
    warnings: string[]
    errors: string[]
  }
  exchanges: {
    total: number
    configured: number
    connected: number
    list: string[]
    status: Record<string, { configured: boolean; connected: boolean; latency?: number }>
  }
  ai: {
    total: number
    configured: number
    list: string[]
    primary: string
    fallback: string
  }
  telegram: {
    configured: boolean
    username: string
  }
  database: {
    configured: boolean
    type: string
  }
  risk: {
    maxPositionSize: number
    maxDailyLoss: number
    maxOpenTrades: number
    defaultStopLoss: string
    defaultTakeProfit: string
  }
  trading: {
    mode: string
    demoEnabled: boolean
    demoBalance: number
    defaultTradeSize: number
  }
}

export function ConfigStatusPanel() {
  const [status, setStatus] = useState<ConfigStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStatus = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch("/api/config/status")
      const data = await response.json()
      if (data.success) {
        setStatus(data)
      } else {
        setError(data.error || "Failed to fetch status")
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch status")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
  }, [])

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  if (error || !status) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 gap-4">
          <XCircle className="h-12 w-12 text-destructive" />
          <p className="text-muted-foreground">{error || "Failed to load configuration"}</p>
          <Button onClick={fetchStatus} variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Overall Status */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Server className="h-5 w-5" />
                System Configuration Status
              </CardTitle>
              <CardDescription>Last checked: {new Date(status.timestamp).toLocaleString()}</CardDescription>
            </div>
            <Button onClick={fetchStatus} variant="outline" size="sm">
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="flex items-center gap-3 p-4 rounded-lg bg-muted/50">
              {status.status.valid ? (
                <CheckCircle className="h-8 w-8 text-green-500" />
              ) : (
                <XCircle className="h-8 w-8 text-red-500" />
              )}
              <div>
                <p className="font-medium">System Status</p>
                <p className="text-sm text-muted-foreground">{status.status.valid ? "Valid" : "Issues Found"}</p>
              </div>
            </div>

            <div className="flex items-center gap-3 p-4 rounded-lg bg-muted/50">
              <Badge variant={status.status.tradingMode === "live" ? "default" : "secondary"} className="h-8 px-3">
                {status.status.tradingMode.toUpperCase()}
              </Badge>
              <div>
                <p className="font-medium">Trading Mode</p>
                <p className="text-sm text-muted-foreground">
                  {status.status.readyForLiveTrading ? "Ready for live" : "Demo only"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 p-4 rounded-lg bg-muted/50">
              <Wifi className="h-8 w-8 text-blue-500" />
              <div>
                <p className="font-medium">Exchanges</p>
                <p className="text-sm text-muted-foreground">
                  {status.exchanges.connected}/{status.exchanges.total} connected
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 p-4 rounded-lg bg-muted/50">
              <Cpu className="h-8 w-8 text-purple-500" />
              <div>
                <p className="font-medium">AI Providers</p>
                <p className="text-sm text-muted-foreground">
                  {status.ai.configured}/{status.ai.total} configured
                </p>
              </div>
            </div>
          </div>

          {/* Warnings & Errors */}
          {(status.validation.warnings.length > 0 || status.validation.errors.length > 0) && (
            <div className="mt-4 space-y-2">
              {status.validation.errors.map((err, i) => (
                <div key={i} className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 text-destructive">
                  <XCircle className="h-4 w-4" />
                  <span className="text-sm">{err}</span>
                </div>
              ))}
              {status.validation.warnings.map((warn, i) => (
                <div key={i} className="flex items-center gap-2 p-3 rounded-lg bg-yellow-500/10 text-yellow-600">
                  <AlertTriangle className="h-4 w-4" />
                  <span className="text-sm">{warn}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Tabs defaultValue="exchanges">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="exchanges">Exchanges</TabsTrigger>
          <TabsTrigger value="ai">AI Providers</TabsTrigger>
          <TabsTrigger value="services">Services</TabsTrigger>
          <TabsTrigger value="risk">Risk Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="exchanges" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>
                Exchange Connections ({status.exchanges.connected}/{status.exchanges.total})
              </CardTitle>
              <CardDescription>Real-time connection status for all supported exchanges</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {Object.entries(status.exchanges.status).map(([exchange, info]) => (
                  <div
                    key={exchange}
                    className={`flex items-center justify-between p-3 rounded-lg border ${
                      info.connected ? "border-green-500/30 bg-green-500/5" : "border-border"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {info.connected ? (
                        <CheckCircle className="h-5 w-5 text-green-500" />
                      ) : (
                        <XCircle className="h-5 w-5 text-muted-foreground" />
                      )}
                      <div>
                        <p className="font-medium capitalize">{exchange}</p>
                        <p className="text-xs text-muted-foreground">
                          {info.configured ? "API Configured" : "Public API"}
                        </p>
                      </div>
                    </div>
                    {info.latency && (
                      <Badge variant="outline" className="text-xs">
                        {info.latency}ms
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ai" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>
                AI/LLM Providers ({status.ai.configured}/{status.ai.total})
              </CardTitle>
              <CardDescription>
                Primary: {status.ai.primary} | Fallback: {status.ai.fallback}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {[
                  "openai",
                  "anthropic",
                  "google",
                  "grok",
                  "groq",
                  "perplexity",
                  "cohere",
                  "mistral",
                  "huggingface",
                  "deepseek",
                  "together",
                ].map((provider) => {
                  const isConfigured = status.ai.list.includes(provider)
                  return (
                    <div
                      key={provider}
                      className={`flex items-center gap-3 p-3 rounded-lg border ${
                        isConfigured ? "border-green-500/30 bg-green-500/5" : "border-border"
                      }`}
                    >
                      {isConfigured ? (
                        <CheckCircle className="h-5 w-5 text-green-500" />
                      ) : (
                        <XCircle className="h-5 w-5 text-muted-foreground" />
                      )}
                      <div>
                        <p className="font-medium capitalize">{provider}</p>
                        <p className="text-xs text-muted-foreground">
                          {isConfigured ? "Configured" : "Not configured"}
                        </p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="services" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Core Services</CardTitle>
              <CardDescription>Database, Telegram, and other service status</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div
                  className={`flex items-center gap-3 p-4 rounded-lg border ${
                    status.database.configured ? "border-green-500/30 bg-green-500/5" : "border-border"
                  }`}
                >
                  <Database className="h-8 w-8 text-blue-500" />
                  <div>
                    <p className="font-medium">Database</p>
                    <p className="text-sm text-muted-foreground">
                      {status.database.configured ? status.database.type : "Not configured"}
                    </p>
                  </div>
                  {status.database.configured && <CheckCircle className="ml-auto h-5 w-5 text-green-500" />}
                </div>

                <div
                  className={`flex items-center gap-3 p-4 rounded-lg border ${
                    status.telegram.configured ? "border-green-500/30 bg-green-500/5" : "border-border"
                  }`}
                >
                  <Bot className="h-8 w-8 text-blue-500" />
                  <div>
                    <p className="font-medium">Telegram Bot</p>
                    <p className="text-sm text-muted-foreground">
                      {status.telegram.configured ? `@${status.telegram.username}` : "Not configured"}
                    </p>
                  </div>
                  {status.telegram.configured && <CheckCircle className="ml-auto h-5 w-5 text-green-500" />}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="risk" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Risk Management Settings
              </CardTitle>
              <CardDescription>Industry-standard risk parameters</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <div className="p-4 rounded-lg bg-muted/50">
                  <p className="text-sm text-muted-foreground">Max Position Size</p>
                  <p className="text-2xl font-bold">${status.risk.maxPositionSize.toLocaleString()}</p>
                </div>
                <div className="p-4 rounded-lg bg-muted/50">
                  <p className="text-sm text-muted-foreground">Max Daily Loss</p>
                  <p className="text-2xl font-bold">${status.risk.maxDailyLoss.toLocaleString()}</p>
                </div>
                <div className="p-4 rounded-lg bg-muted/50">
                  <p className="text-sm text-muted-foreground">Max Open Trades</p>
                  <p className="text-2xl font-bold">{status.risk.maxOpenTrades}</p>
                </div>
                <div className="p-4 rounded-lg bg-muted/50">
                  <p className="text-sm text-muted-foreground">Default Stop Loss</p>
                  <p className="text-2xl font-bold">{status.risk.defaultStopLoss}</p>
                </div>
                <div className="p-4 rounded-lg bg-muted/50">
                  <p className="text-sm text-muted-foreground">Default Take Profit</p>
                  <p className="text-2xl font-bold">{status.risk.defaultTakeProfit}</p>
                </div>
                <div className="p-4 rounded-lg bg-muted/50">
                  <p className="text-sm text-muted-foreground">Default Trade Size</p>
                  <p className="text-2xl font-bold">${status.trading.defaultTradeSize}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default ConfigStatusPanel
