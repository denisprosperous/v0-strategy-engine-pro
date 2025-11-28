"use client"

import { useState, useEffect } from "react"
import { useSearchParams } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { useAuth } from "@/lib/hooks/use-auth"
import { DashboardSidebar } from "@/components/dashboard/dashboard-sidebar"
import { PortfolioOverview } from "@/components/dashboard/portfolio-overview"
import { TradeHistory } from "@/components/dashboard/trade-history"
import { StrategyManager } from "@/components/dashboard/strategy-manager"
import { MarketData } from "@/components/dashboard/market-data"
import { RiskManagement } from "@/components/dashboard/risk-management"
import { AdminPanel } from "@/components/dashboard/admin-panel"
import { LiveTradingPanel } from "@/components/dashboard/live-trading-panel"
import { BacktestingPanel } from "@/components/dashboard/backtesting-panel"
import { MultiExchangePanel } from "@/components/dashboard/multi-exchange-panel"
import { TrendingUp, Activity, DollarSign, Target, RefreshCw, AlertCircle, Bot, Zap, Globe } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

interface PortfolioData {
  totalValue: number
  totalPnL: number
  pnlPercentage: number
  openTrades: number
  winRate: number
  activeStrategies: number
}

interface BotStatus {
  configured: boolean
  webhookSet: boolean
  botUsername?: string
}

export default function DashboardPage() {
  const { user, loading } = useAuth()
  const { toast } = useToast()
  const searchParams = useSearchParams()
  const tabFromUrl = searchParams.get("tab")
  const [activeTab, setActiveTab] = useState(tabFromUrl || "overview")
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [dataLoading, setDataLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [portfolioData, setPortfolioData] = useState<PortfolioData>({
    totalValue: 0,
    totalPnL: 0,
    pnlPercentage: 0,
    openTrades: 0,
    winRate: 0,
    activeStrategies: 0,
  })
  const [botStatus, setBotStatus] = useState<BotStatus>({ configured: false, webhookSet: false })

  useEffect(() => {
    if (tabFromUrl) {
      setActiveTab(tabFromUrl)
    }
    fetchDashboardData()
    const interval = setInterval(fetchDashboardData, 30000)
    return () => clearInterval(interval)
  }, [tabFromUrl])

  const fetchDashboardData = async () => {
    try {
      setIsRefreshing(true)
      setError(null)

      const response = await fetch("/api/dashboard/analytics", {
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
      })

      if (!response.ok) {
        throw new Error("Failed to fetch dashboard data")
      }

      const data = await response.json()

      if (data.success && data.analytics) {
        setPortfolioData({
          totalValue: data.analytics.portfolio?.totalValue || 0,
          totalPnL: data.analytics.portfolio?.totalPnL || 0,
          pnlPercentage: data.analytics.portfolio?.pnlPercentage || 0,
          openTrades: data.analytics.trading?.openTrades || 0,
          winRate: data.analytics.trading?.winRate || 0,
          activeStrategies: data.analytics.trading?.activeStrategies || 0,
        })
      }
    } catch (err) {
      console.error("Error fetching dashboard data:", err)
      setError(err instanceof Error ? err.message : "Failed to load data")
      toast({
        title: "Error",
        description: "Failed to fetch dashboard data. Using cached values.",
        variant: "destructive",
      })
    } finally {
      setIsRefreshing(false)
      setDataLoading(false)
    }
  }

  const handleRefresh = () => {
    fetchDashboardData()
    toast({
      title: "Refreshing",
      description: "Fetching latest data...",
    })
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-background">
      <DashboardSidebar activeTab={activeTab} onTabChange={setActiveTab} />

      <main className="flex-1 overflow-auto">
        <div className="container mx-auto p-6 space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Trading Dashboard</h1>
              <p className="text-muted-foreground">Welcome back{user ? `, ${user.username}` : ""}</p>
            </div>
            <div className="flex items-center space-x-2">
              {error && (
                <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/20">
                  <AlertCircle className="w-3 h-3 mr-1" />
                  Connection Issue
                </Badge>
              )}
              <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">
                <Activity className="w-3 h-3 mr-1" />
                Live
              </Badge>
              <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isRefreshing}>
                <RefreshCw className={`w-4 h-4 mr-1 ${isRefreshing ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </div>
          </div>

          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Portfolio</CardTitle>
                <DollarSign className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {dataLoading ? (
                  <div className="h-8 w-24 bg-muted animate-pulse rounded" />
                ) : (
                  <>
                    <div className="text-2xl font-bold">${portfolioData.totalValue.toLocaleString()}</div>
                    <div
                      className={`flex items-center text-xs ${portfolioData.pnlPercentage >= 0 ? "text-green-500" : "text-red-500"}`}
                    >
                      <TrendingUp className="w-3 h-3 mr-1" />
                      {portfolioData.pnlPercentage >= 0 ? "+" : ""}
                      {portfolioData.pnlPercentage.toFixed(2)}% from last month
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {dataLoading ? (
                  <div className="h-8 w-24 bg-muted animate-pulse rounded" />
                ) : (
                  <>
                    <div
                      className={`text-2xl font-bold ${portfolioData.totalPnL >= 0 ? "text-green-500" : "text-red-500"}`}
                    >
                      {portfolioData.totalPnL >= 0 ? "+" : ""}${portfolioData.totalPnL.toLocaleString()}
                    </div>
                    <div className="text-xs text-muted-foreground">{portfolioData.openTrades} open trades</div>
                  </>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
                <Target className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {dataLoading ? (
                  <div className="h-8 w-24 bg-muted animate-pulse rounded" />
                ) : (
                  <>
                    <div className="text-2xl font-bold">{portfolioData.winRate.toFixed(1)}%</div>
                    <Progress value={portfolioData.winRate} className="mt-2" />
                  </>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Active Strategies</CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {dataLoading ? (
                  <div className="h-8 w-24 bg-muted animate-pulse rounded" />
                ) : (
                  <>
                    <div className="text-2xl font-bold">{portfolioData.activeStrategies}</div>
                    <div className="text-xs text-muted-foreground">
                      {portfolioData.activeStrategies > 0 ? "Strategies running" : "No active strategies"}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Main Content Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
            <TabsList className="flex flex-wrap h-auto gap-1">
              <TabsTrigger value="overview" className="gap-1">
                <Activity className="w-4 h-4" />
                Overview
              </TabsTrigger>
              <TabsTrigger value="trades" className="gap-1">
                <TrendingUp className="w-4 h-4" />
                Trades
              </TabsTrigger>
              <TabsTrigger value="strategies" className="gap-1">
                <Target className="w-4 h-4" />
                Strategies
              </TabsTrigger>
              <TabsTrigger value="live" className="gap-1">
                <Zap className="w-4 h-4" />
                Live Trading
              </TabsTrigger>
              <TabsTrigger value="backtest" className="gap-1">
                <Activity className="w-4 h-4" />
                Backtest
              </TabsTrigger>
              <TabsTrigger value="exchanges" className="gap-1">
                <Globe className="w-4 h-4" />
                Exchanges
              </TabsTrigger>
              <TabsTrigger value="market" className="gap-1">
                <DollarSign className="w-4 h-4" />
                Market
              </TabsTrigger>
              <TabsTrigger value="risk" className="gap-1">
                <AlertCircle className="w-4 h-4" />
                Risk
              </TabsTrigger>
              <TabsTrigger value="telegram" className="gap-1">
                <Bot className="w-4 h-4" />
                Telegram
              </TabsTrigger>
              {user?.role === "admin" && <TabsTrigger value="admin">Admin</TabsTrigger>}
            </TabsList>

            <TabsContent value="overview" className="space-y-4">
              <PortfolioOverview />
            </TabsContent>

            <TabsContent value="trades" className="space-y-4">
              <TradeHistory />
            </TabsContent>

            <TabsContent value="strategies" className="space-y-4">
              <StrategyManager />
            </TabsContent>

            <TabsContent value="live" className="space-y-4">
              <LiveTradingPanel />
            </TabsContent>

            <TabsContent value="backtest" className="space-y-4">
              <BacktestingPanel />
            </TabsContent>

            <TabsContent value="exchanges" className="space-y-4">
              <MultiExchangePanel />
            </TabsContent>

            <TabsContent value="market" className="space-y-4">
              <MarketData />
            </TabsContent>

            <TabsContent value="risk" className="space-y-4">
              <RiskManagement />
            </TabsContent>

            <TabsContent value="telegram" className="space-y-4">
              <TelegramBotPanel botStatus={botStatus} />
            </TabsContent>

            {user?.role === "admin" && (
              <TabsContent value="admin" className="space-y-4">
                <AdminPanel />
              </TabsContent>
            )}
          </Tabs>
        </div>
      </main>
    </div>
  )
}

function TelegramBotPanel({ botStatus }: { botStatus: BotStatus }) {
  const { toast } = useToast()
  const [loading, setLoading] = useState(false)

  const setupWebhook = async () => {
    try {
      setLoading(true)
      const response = await fetch("/api/telegram/setup", { method: "POST" })
      const data = await response.json()
      if (data.success) {
        toast({ title: "Success", description: "Telegram webhook configured" })
      } else {
        toast({ title: "Error", description: data.error, variant: "destructive" })
      }
    } catch {
      toast({ title: "Error", description: "Failed to setup webhook", variant: "destructive" })
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="w-5 h-5" />
            Telegram Bot Status
          </CardTitle>
          <CardDescription>Control your trading bot via Telegram</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
              <span className="text-sm font-medium">Bot Token</span>
              <Badge variant={botStatus.configured ? "default" : "secondary"}>
                {botStatus.configured ? "Configured" : "Not Set"}
              </Badge>
            </div>
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
              <span className="text-sm font-medium">Webhook</span>
              <Badge variant={botStatus.webhookSet ? "default" : "secondary"}>
                {botStatus.webhookSet ? "Active" : "Inactive"}
              </Badge>
            </div>
          </div>

          {botStatus.botUsername && (
            <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <p className="text-sm">
                Bot Username: <strong>@{botStatus.botUsername}</strong>
              </p>
              <p className="text-xs text-muted-foreground mt-1">Search for this bot on Telegram to start using it</p>
            </div>
          )}

          {!botStatus.configured && (
            <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
              <p className="text-sm font-medium text-yellow-600 dark:text-yellow-400">Telegram Bot Token Required</p>
              <p className="text-xs text-muted-foreground mt-1">
                Add TELEGRAM_BOT_TOKEN to your environment variables to enable the Telegram bot. Get a token from
                @BotFather on Telegram.
              </p>
            </div>
          )}

          <div className="flex gap-2">
            <Button onClick={setupWebhook} disabled={!botStatus.configured}>
              Setup Webhook
            </Button>
            <Button variant="outline" onClick={() => {}}>
              Refresh Status
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Available Commands</CardTitle>
          <CardDescription>Commands you can use with the Telegram bot</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2">
            {[
              { cmd: "/start", desc: "Initialize bot and show welcome message" },
              { cmd: "/status", desc: "View current portfolio and trading status" },
              { cmd: "/balance", desc: "Check account balance across exchanges" },
              { cmd: "/trades", desc: "View recent and open trades" },
              { cmd: "/strategies", desc: "List and manage trading strategies" },
              { cmd: "/market", desc: "Get current market prices" },
              { cmd: "/exchanges", desc: "Check exchange connection status" },
              { cmd: "/alert", desc: "Set price alerts" },
              { cmd: "/help", desc: "Show all available commands" },
            ].map(({ cmd, desc }) => (
              <div key={cmd} className="flex items-center justify-between py-2 border-b last:border-0">
                <code className="text-sm font-mono bg-muted px-2 py-1 rounded">{cmd}</code>
                <span className="text-sm text-muted-foreground">{desc}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
