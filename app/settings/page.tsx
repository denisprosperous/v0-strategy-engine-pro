"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  Settings,
  Bot,
  Shield,
  TrendingUp,
  Zap,
  Database,
  Globe,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Copy,
  ExternalLink,
} from "lucide-react"
import Link from "next/link"

interface ConfigStatus {
  exchanges: Record<string, boolean>
  ai: Record<string, boolean>
  telegram: boolean
  database: boolean
}

export default function SettingsPage() {
  const [configStatus, setConfigStatus] = useState<ConfigStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({})
  const [activeTab, setActiveTab] = useState("exchanges")

  // Form state for API keys (these would normally be stored securely)
  const [formData, setFormData] = useState({
    // Trading Settings
    tradingMode: "demo",
    defaultStopLoss: "2",
    defaultTakeProfit: "6",
    maxDailyLoss: "1000",
    maxPositionSize: "10000",

    // Telegram
    telegramBotToken: "",
    telegramWebhookUrl: "",
    telegramChatId: "",
  })

  useEffect(() => {
    fetchConfigStatus()
  }, [])

  const fetchConfigStatus = async () => {
    try {
      const response = await fetch("/api/config/status")
      if (response.ok) {
        const data = await response.json()
        setConfigStatus(data)
      }
    } catch (error) {
      console.error("Failed to fetch config status:", error)
    } finally {
      setLoading(false)
    }
  }

  const toggleSecretVisibility = (key: string) => {
    setShowSecrets((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const StatusBadge = ({ configured }: { configured: boolean }) => (
    <Badge variant={configured ? "default" : "secondary"} className={configured ? "bg-green-500" : ""}>
      {configured ? (
        <>
          <CheckCircle2 className="h-3 w-3 mr-1" />
          Connected
        </>
      ) : (
        <>
          <XCircle className="h-3 w-3 mr-1" />
          Not Configured
        </>
      )}
    </Badge>
  )

  const exchanges = [
    { id: "bitget", name: "Bitget", description: "Copy Trading Leader", testnet: true, priority: 1 },
    { id: "kraken", name: "Kraken", description: "Most Secure US Exchange", testnet: true, priority: 2 },
    { id: "phemex", name: "Phemex", description: "Contract Trading Specialist", testnet: true, priority: 3 },
    { id: "binance", name: "Binance", description: "World's Largest Exchange", testnet: true, priority: 4 },
    { id: "coinbase", name: "Coinbase", description: "Most Trusted US Exchange", testnet: true, priority: 5 },
    { id: "okx", name: "OKX", description: "Top 3 Global Exchange", testnet: true, priority: 6 },
    { id: "bybit", name: "Bybit", description: "Derivatives Leader", testnet: true, priority: 7 },
    { id: "kucoin", name: "KuCoin", description: "Altcoin Paradise", testnet: true, priority: 8 },
    { id: "gate", name: "Gate.io", description: "Wide Asset Selection", testnet: false, priority: 9 },
    { id: "huobi", name: "Huobi/HTX", description: "Asian Market Leader", testnet: false, priority: 10 },
    { id: "mexc", name: "MEXC", description: "Low Fee Exchange", testnet: false, priority: 11 },
  ]

  const aiProviders = [
    { id: "openai", name: "OpenAI", model: "GPT-4o", description: "Primary AI Model", priority: 1 },
    { id: "grok", name: "Grok (xAI)", model: "grok-4-latest", description: "Fast Reasoning", priority: 2 },
    { id: "groq", name: "Groq", model: "llama-3.3-70b", description: "Ultra-Fast Inference", priority: 3 },
    { id: "google", name: "Google Gemini", model: "gemini-2.0-flash", description: "Multimodal AI", priority: 4 },
    { id: "perplexity", name: "Perplexity", model: "sonar-large", description: "Real-time Search", priority: 5 },
    { id: "cohere", name: "Cohere", model: "command-r-plus", description: "Enterprise AI", priority: 6 },
    { id: "huggingface", name: "HuggingFace", model: "Llama-3.3-70B", description: "Open Source", priority: 7 },
  ]

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/dashboard" className="text-muted-foreground hover:text-foreground">
                ← Back to Dashboard
              </Link>
              <Separator orientation="vertical" className="h-6" />
              <div className="flex items-center gap-2">
                <Settings className="h-6 w-6 text-primary" />
                <h1 className="text-2xl font-bold">Settings & API Configuration</h1>
              </div>
            </div>
            <Button onClick={fetchConfigStatus} variant="outline" size="sm">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh Status
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Status Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Exchanges</p>
                  <p className="text-2xl font-bold">
                    {configStatus ? Object.values(configStatus.exchanges).filter(Boolean).length : 0}/11
                  </p>
                </div>
                <Globe className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">AI Providers</p>
                  <p className="text-2xl font-bold">
                    {configStatus ? Object.values(configStatus.ai).filter(Boolean).length : 0}/7
                  </p>
                </div>
                <Zap className="h-8 w-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Telegram Bot</p>
                  <p className="text-2xl font-bold">{configStatus?.telegram ? "Active" : "Inactive"}</p>
                </div>
                <Bot className="h-8 w-8 text-cyan-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Database</p>
                  <p className="text-2xl font-bold">{configStatus?.database ? "Connected" : "Disconnected"}</p>
                </div>
                <Database className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Important Notice */}
        <Alert className="mb-8 border-amber-500 bg-amber-500/10">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          <AlertTitle>API Keys Setup Instructions</AlertTitle>
          <AlertDescription>
            <p className="mb-2">
              To configure your API keys securely, add them as Environment Variables in the Vercel Dashboard or in the{" "}
              <strong>Vars</strong> section of the v0 sidebar.
            </p>
            <p className="text-sm text-muted-foreground">
              Never expose API keys in client-side code. All keys are stored securely on the server.
            </p>
          </AlertDescription>
        </Alert>

        {/* Configuration Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid grid-cols-5 w-full max-w-2xl">
            <TabsTrigger value="exchanges">Exchanges</TabsTrigger>
            <TabsTrigger value="ai">AI Models</TabsTrigger>
            <TabsTrigger value="telegram">Telegram</TabsTrigger>
            <TabsTrigger value="trading">Trading</TabsTrigger>
            <TabsTrigger value="risk">Risk</TabsTrigger>
          </TabsList>

          {/* Exchanges Tab */}
          <TabsContent value="exchanges" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Globe className="h-5 w-5" />
                  Exchange API Configuration
                </CardTitle>
                <CardDescription>
                  Configure your exchange API keys. Your primary exchanges (Bitget, Kraken, Phemex) are highlighted.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {exchanges.map((exchange) => (
                  <div
                    key={exchange.id}
                    className={`p-4 rounded-lg border ${exchange.priority <= 3 ? "border-primary bg-primary/5" : ""}`}
                  >
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold">{exchange.name}</h3>
                          {exchange.priority <= 3 && (
                            <Badge variant="outline" className="text-xs">
                              Primary
                            </Badge>
                          )}
                          {exchange.testnet && (
                            <Badge variant="secondary" className="text-xs">
                              Testnet Available
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">{exchange.description}</p>
                      </div>
                      <StatusBadge configured={configStatus?.exchanges?.[exchange.id] || false} />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <Label className="text-xs text-muted-foreground">Environment Variable</Label>
                        <div className="flex items-center gap-2 mt-1">
                          <code className="text-xs bg-muted px-2 py-1 rounded">
                            {exchange.id.toUpperCase()}_API_KEY
                          </code>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0"
                            onClick={() => copyToClipboard(`${exchange.id.toUpperCase()}_API_KEY`)}
                          >
                            <Copy className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                      <div>
                        <Label className="text-xs text-muted-foreground">Secret Variable</Label>
                        <div className="flex items-center gap-2 mt-1">
                          <code className="text-xs bg-muted px-2 py-1 rounded">
                            {exchange.id.toUpperCase()}_API_SECRET
                          </code>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0"
                            onClick={() => copyToClipboard(`${exchange.id.toUpperCase()}_API_SECRET`)}
                          >
                            <Copy className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    </div>

                    {["bitget", "okx", "kucoin"].includes(exchange.id) && (
                      <div className="mt-4">
                        <Label className="text-xs text-muted-foreground">Passphrase Variable</Label>
                        <div className="flex items-center gap-2 mt-1">
                          <code className="text-xs bg-muted px-2 py-1 rounded">
                            {exchange.id.toUpperCase()}_PASSPHRASE
                          </code>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0"
                            onClick={() => copyToClipboard(`${exchange.id.toUpperCase()}_PASSPHRASE`)}
                          >
                            <Copy className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          </TabsContent>

          {/* AI Models Tab */}
          <TabsContent value="ai" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  AI/LLM Provider Configuration
                </CardTitle>
                <CardDescription>
                  Configure your AI model API keys for market analysis, sentiment detection, and trading signals.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {aiProviders.map((provider) => (
                  <div
                    key={provider.id}
                    className={`p-4 rounded-lg border ${
                      provider.priority <= 3 ? "border-purple-500 bg-purple-500/5" : ""
                    }`}
                  >
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold">{provider.name}</h3>
                          <Badge variant="outline" className="text-xs">
                            {provider.model}
                          </Badge>
                          {provider.priority <= 3 && <Badge className="text-xs bg-purple-500">Recommended</Badge>}
                        </div>
                        <p className="text-sm text-muted-foreground">{provider.description}</p>
                      </div>
                      <StatusBadge configured={configStatus?.ai?.[provider.id] || false} />
                    </div>

                    <div>
                      <Label className="text-xs text-muted-foreground">Environment Variable</Label>
                      <div className="flex items-center gap-2 mt-1">
                        <code className="text-xs bg-muted px-2 py-1 rounded">
                          {provider.id === "openai"
                            ? "OPENAI_API_KEY"
                            : provider.id === "grok"
                              ? "XAI_API_KEY"
                              : provider.id === "google"
                                ? "GOOGLE_API_KEY"
                                : provider.id === "huggingface"
                                  ? "HUGGINGFACE_TOKEN"
                                  : `${provider.id.toUpperCase()}_API_KEY`}
                        </code>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                          onClick={() =>
                            copyToClipboard(
                              provider.id === "openai"
                                ? "OPENAI_API_KEY"
                                : provider.id === "grok"
                                  ? "XAI_API_KEY"
                                  : provider.id === "google"
                                    ? "GOOGLE_API_KEY"
                                    : provider.id === "huggingface"
                                      ? "HUGGINGFACE_TOKEN"
                                      : `${provider.id.toUpperCase()}_API_KEY`,
                            )
                          }
                        >
                          <Copy className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}

                <Separator />

                <div className="space-y-4">
                  <h4 className="font-semibold">AI Model Selection</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <Label>Primary Model</Label>
                      <Select defaultValue="openai">
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="openai">OpenAI GPT-4o</SelectItem>
                          <SelectItem value="grok">Grok (xAI)</SelectItem>
                          <SelectItem value="groq">Groq Llama-3.3</SelectItem>
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-muted-foreground mt-1">Env: AI_PRIMARY_MODEL</p>
                    </div>
                    <div>
                      <Label>Fallback Model</Label>
                      <Select defaultValue="groq">
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="groq">Groq Llama-3.3</SelectItem>
                          <SelectItem value="grok">Grok (xAI)</SelectItem>
                          <SelectItem value="google">Google Gemini</SelectItem>
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-muted-foreground mt-1">Env: AI_FALLBACK_MODEL</p>
                    </div>
                    <div>
                      <Label>Sentiment Model</Label>
                      <Select defaultValue="perplexity">
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="perplexity">Perplexity (Web Search)</SelectItem>
                          <SelectItem value="openai">OpenAI GPT-4o</SelectItem>
                          <SelectItem value="cohere">Cohere</SelectItem>
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-muted-foreground mt-1">Env: AI_SENTIMENT_MODEL</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Telegram Tab */}
          <TabsContent value="telegram" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bot className="h-5 w-5" />
                  Telegram Bot Configuration
                </CardTitle>
                <CardDescription>Configure your Telegram bot for real-time alerts and trade execution.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <Alert>
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>Setup Instructions</AlertTitle>
                  <AlertDescription>
                    <ol className="list-decimal list-inside space-y-1 mt-2 text-sm">
                      <li>Create a bot with @BotFather on Telegram</li>
                      <li>Copy the bot token provided</li>
                      <li>Set the environment variables below</li>
                      <li>Deploy your app to get the webhook URL</li>
                      <li>Call /api/telegram/setup to register the webhook</li>
                    </ol>
                  </AlertDescription>
                </Alert>

                <div className="space-y-4">
                  <div className="p-4 rounded-lg border">
                    <div className="flex items-center justify-between mb-2">
                      <Label>Bot Token</Label>
                      <StatusBadge configured={configStatus?.telegram || false} />
                    </div>
                    <div className="flex items-center gap-2">
                      <code className="text-sm bg-muted px-3 py-2 rounded flex-1">TELEGRAM_BOT_TOKEN</code>
                      <Button variant="ghost" size="sm" onClick={() => copyToClipboard("TELEGRAM_BOT_TOKEN")}>
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      Get this from @BotFather after creating your bot
                    </p>
                  </div>

                  <div className="p-4 rounded-lg border">
                    <Label>Webhook URL</Label>
                    <div className="flex items-center gap-2 mt-2">
                      <code className="text-sm bg-muted px-3 py-2 rounded flex-1">TELEGRAM_WEBHOOK_URL</code>
                      <Button variant="ghost" size="sm" onClick={() => copyToClipboard("TELEGRAM_WEBHOOK_URL")}>
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      Set to: https://your-domain.vercel.app/api/telegram/webhook
                    </p>
                  </div>

                  <div className="p-4 rounded-lg border">
                    <Label>Chat ID (Optional)</Label>
                    <div className="flex items-center gap-2 mt-2">
                      <code className="text-sm bg-muted px-3 py-2 rounded flex-1">TELEGRAM_CHAT_ID</code>
                      <Button variant="ghost" size="sm" onClick={() => copyToClipboard("TELEGRAM_CHAT_ID")}>
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      Your Telegram user ID for receiving alerts. Get it by messaging @userinfobot
                    </p>
                  </div>

                  <div className="p-4 rounded-lg border">
                    <Label>Webhook Secret (Optional)</Label>
                    <div className="flex items-center gap-2 mt-2">
                      <code className="text-sm bg-muted px-3 py-2 rounded flex-1">TELEGRAM_WEBHOOK_SECRET</code>
                      <Button variant="ghost" size="sm" onClick={() => copyToClipboard("TELEGRAM_WEBHOOK_SECRET")}>
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      A random string for webhook verification (recommended for security)
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Trading Tab */}
          <TabsContent value="trading" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  Trading Configuration
                </CardTitle>
                <CardDescription>Professional trading settings based on industry standards.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div>
                      <Label>Trading Mode</Label>
                      <Select defaultValue="demo">
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="demo">Demo (Paper Trading)</SelectItem>
                          <SelectItem value="paper">Paper (Simulated)</SelectItem>
                          <SelectItem value="live">Live (Real Money)</SelectItem>
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-muted-foreground mt-1">Env: TRADING_MODE (demo | paper | live)</p>
                    </div>

                    <div>
                      <Label>Default Trade Size ($)</Label>
                      <Input type="number" defaultValue="100" />
                      <p className="text-xs text-muted-foreground mt-1">Env: DEFAULT_TRADE_SIZE=100</p>
                    </div>

                    <div>
                      <Label>Demo Initial Balance ($)</Label>
                      <Input type="number" defaultValue="10000" />
                      <p className="text-xs text-muted-foreground mt-1">Env: DEMO_INITIAL_BALANCE=10000</p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <Label>Default Stop Loss (%)</Label>
                      <Input type="number" defaultValue="2" step="0.1" />
                      <p className="text-xs text-muted-foreground mt-1">Env: DEFAULT_STOP_LOSS=0.02</p>
                    </div>

                    <div>
                      <Label>Default Take Profit (%)</Label>
                      <Input type="number" defaultValue="6" step="0.1" />
                      <p className="text-xs text-muted-foreground mt-1">Env: DEFAULT_TAKE_PROFIT=0.06</p>
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <Label>Enable Demo Mode</Label>
                        <p className="text-xs text-muted-foreground">Env: ENABLE_DEMO_MODE=true</p>
                      </div>
                      <Switch defaultChecked />
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <Label>Enable Backtesting</Label>
                        <p className="text-xs text-muted-foreground">Env: ENABLE_BACKTESTING=true</p>
                      </div>
                      <Switch defaultChecked />
                    </div>
                  </div>
                </div>

                <Separator />

                <div>
                  <h4 className="font-semibold mb-4">Backtesting Date Range</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Start Date</Label>
                      <Input type="date" defaultValue="2024-01-01" />
                      <p className="text-xs text-muted-foreground mt-1">Env: BACKTEST_START_DATE=2024-01-01</p>
                    </div>
                    <div>
                      <Label>End Date</Label>
                      <Input type="date" defaultValue="2024-12-31" />
                      <p className="text-xs text-muted-foreground mt-1">Env: BACKTEST_END_DATE=2024-12-31</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Risk Management Tab */}
          <TabsContent value="risk" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Risk Management (Professional Standards)
                </CardTitle>
                <CardDescription>Industry-standard risk parameters used by top trading institutions.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="space-y-4">
                    <h4 className="font-semibold text-sm">Position Limits</h4>
                    <div>
                      <Label>Max Position Size ($)</Label>
                      <Input type="number" defaultValue="10000" />
                      <p className="text-xs text-muted-foreground mt-1">MAX_POSITION_SIZE=10000</p>
                    </div>
                    <div>
                      <Label>Max Open Trades</Label>
                      <Input type="number" defaultValue="10" />
                      <p className="text-xs text-muted-foreground mt-1">MAX_OPEN_TRADES=10</p>
                    </div>
                    <div>
                      <Label>Max Concurrent Trades</Label>
                      <Input type="number" defaultValue="5" />
                      <p className="text-xs text-muted-foreground mt-1">MAX_CONCURRENT_TRADES=5</p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h4 className="font-semibold text-sm">Loss Limits</h4>
                    <div>
                      <Label>Max Daily Loss ($)</Label>
                      <Input type="number" defaultValue="1000" />
                      <p className="text-xs text-muted-foreground mt-1">MAX_DAILY_LOSS=1000</p>
                    </div>
                    <div>
                      <Label>Max Drawdown (%)</Label>
                      <Input type="number" defaultValue="15" />
                      <p className="text-xs text-muted-foreground mt-1">MAX_DRAWDOWN=0.15</p>
                    </div>
                    <div>
                      <Label>Trade Cooldown (ms)</Label>
                      <Input type="number" defaultValue="30000" />
                      <p className="text-xs text-muted-foreground mt-1">TRADE_COOLDOWN_MS=30000</p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h4 className="font-semibold text-sm">Advanced Risk</h4>
                    <div>
                      <Label>Kelly Fraction</Label>
                      <Input type="number" defaultValue="0.25" step="0.05" />
                      <p className="text-xs text-muted-foreground mt-1">KELLY_FRACTION=0.25</p>
                    </div>
                    <div>
                      <Label>Max Volatility (%)</Label>
                      <Input type="number" defaultValue="5" />
                      <p className="text-xs text-muted-foreground mt-1">MAX_VOLATILITY=0.05</p>
                    </div>
                    <div>
                      <Label>Risk-Free Rate (%)</Label>
                      <Input type="number" defaultValue="5" />
                      <p className="text-xs text-muted-foreground mt-1">RISK_FREE_RATE=0.05</p>
                    </div>
                  </div>
                </div>

                <Separator />

                <div>
                  <h4 className="font-semibold mb-4">Phi (Golden Ratio) Strategy</h4>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <Label>Risk Per Trade (%)</Label>
                      <Input type="number" defaultValue="1.618" step="0.001" />
                      <p className="text-xs text-muted-foreground mt-1">PHI_RISK_PER_TRADE=0.01618</p>
                    </div>
                    <div>
                      <Label>Max Drawdown (%)</Label>
                      <Input type="number" defaultValue="6.18" step="0.01" />
                      <p className="text-xs text-muted-foreground mt-1">PHI_MAX_DRAWDOWN=0.0618</p>
                    </div>
                    <div>
                      <Label>ATR Multiplier</Label>
                      <Input type="number" defaultValue="1.618" step="0.001" />
                      <p className="text-xs text-muted-foreground mt-1">PHI_ATR_MULTIPLIER=1.618</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Quick Reference */}
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Quick Setup Reference</CardTitle>
            <CardDescription>
              Copy these environment variables to your Vercel project or v0 Vars section
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="bg-muted p-4 rounded-lg overflow-x-auto">
              <pre className="text-xs">
                {`# Required for Live Trading
BITGET_API_KEY=your_key
BITGET_API_SECRET=your_secret
BITGET_PASSPHRASE=your_passphrase
KRAKEN_API_KEY=your_key
KRAKEN_PRIVATE_KEY=your_key
PHEMEX_API_KEY=your_key
PHEMEX_API_SECRET=your_secret

# Required for AI Features
OPENAI_API_KEY=your_key
XAI_API_KEY=your_key
GROQ_API_KEY=your_key

# Telegram (Optional but Recommended)
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_WEBHOOK_URL=https://your-domain.vercel.app/api/telegram/webhook

# Professional Trading Settings (Pre-configured)
TRADING_MODE=demo
DEFAULT_STOP_LOSS=0.02
DEFAULT_TAKE_PROFIT=0.06
MAX_DAILY_LOSS=1000
MAX_POSITION_SIZE=10000`}
              </pre>
            </div>
            <div className="flex gap-2 mt-4">
              <Button
                variant="outline"
                onClick={() =>
                  copyToClipboard(`BITGET_API_KEY=your_key
BITGET_API_SECRET=your_secret
BITGET_PASSPHRASE=your_passphrase
KRAKEN_API_KEY=your_key
KRAKEN_PRIVATE_KEY=your_key
PHEMEX_API_KEY=your_key
PHEMEX_API_SECRET=your_secret
OPENAI_API_KEY=your_key
XAI_API_KEY=your_key
GROQ_API_KEY=your_key
TELEGRAM_BOT_TOKEN=your_token
TRADING_MODE=demo
DEFAULT_STOP_LOSS=0.02
DEFAULT_TAKE_PROFIT=0.06
MAX_DAILY_LOSS=1000
MAX_POSITION_SIZE=10000`)
                }
              >
                <Copy className="h-4 w-4 mr-2" />
                Copy All Variables
              </Button>
              <Button asChild>
                <Link href="/dashboard">
                  Go to Dashboard
                  <ExternalLink className="h-4 w-4 ml-2" />
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
