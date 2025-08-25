"use client"

import { useState } from "react"
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
import { TrendingUp, Activity, DollarSign, Target } from "lucide-react"

export default function DashboardPage() {
  const { user, loading } = useAuth()
  const [activeTab, setActiveTab] = useState("overview")
  const [portfolioData, setPortfolioData] = useState({
    totalValue: 12450.67,
    totalPnL: 2450.67,
    pnlPercentage: 24.5,
    openTrades: 5,
    winRate: 78.5,
    activeStrategies: 3,
  })

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
              <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">
                <Activity className="w-3 h-3 mr-1" />
                Live
              </Badge>
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
                <div className="text-2xl font-bold">${portfolioData.totalValue.toLocaleString()}</div>
                <div className="flex items-center text-xs text-green-500">
                  <TrendingUp className="w-3 h-3 mr-1" />+{portfolioData.pnlPercentage}% from last month
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-500">+${portfolioData.totalPnL.toLocaleString()}</div>
                <div className="text-xs text-muted-foreground">{portfolioData.openTrades} open trades</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
                <Target className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{portfolioData.winRate}%</div>
                <Progress value={portfolioData.winRate} className="mt-2" />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Active Strategies</CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{portfolioData.activeStrategies}</div>
                <div className="text-xs text-muted-foreground">2 performing above target</div>
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
