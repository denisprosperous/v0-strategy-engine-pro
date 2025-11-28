"use client"

import { useState, useEffect } from "react"
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
import { TrendingUp, Activity, DollarSign, Target, RefreshCw, AlertCircle } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

interface PortfolioData {
  totalValue: number
  totalPnL: number
  pnlPercentage: number
  openTrades: number
  winRate: number
  activeStrategies: number
}

export default function DashboardPage() {
  const { user, loading } = useAuth()
  const { toast } = useToast()
  const [activeTab, setActiveTab] = useState("overview")
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

  useEffect(() => {
    if (user) {
      fetchDashboardData()

      // Poll for updates every 30 seconds
      const interval = setInterval(fetchDashboardData, 30000)
      return () => clearInterval(interval)
    }
  }, [user])

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

  if (!user) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Card className="w-96">
          <CardHeader>
            <CardTitle>Access Denied</CardTitle>
            <CardDescription>Please log in to access the dashboard.</CardDescription>
          </CardHeader>
        </Card>
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
              <p className="text-muted-foreground">Welcome back, {user.username}</p>
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
              <Button variant="outline" size="sm">
                Settings
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
            <TabsList className="grid w-full grid-cols-6">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="trades">Trades</TabsTrigger>
              <TabsTrigger value="strategies">Strategies</TabsTrigger>
              <TabsTrigger value="market">Market</TabsTrigger>
              <TabsTrigger value="risk">Risk</TabsTrigger>
              {user.role === "admin" && <TabsTrigger value="admin">Admin</TabsTrigger>}
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

            <TabsContent value="market" className="space-y-4">
              <MarketData />
            </TabsContent>

            <TabsContent value="risk" className="space-y-4">
              <RiskManagement />
            </TabsContent>

            {user.role === "admin" && (
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
