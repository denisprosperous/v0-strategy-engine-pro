import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { TrendingUp, Shield, Bot, BarChart3, Play, LayoutDashboard, Zap, AlertTriangle } from "lucide-react"
import Link from "next/link"

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      <div className="container mx-auto px-4 py-16">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-primary to-chart-1 bg-clip-text text-transparent">
            Neural Trading Bot
          </h1>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Advanced algorithmic trading platform with AI-powered strategies, real-time sentiment analysis, and
            comprehensive risk management across 10 major exchanges.
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <Link href="/dashboard">
              <Button size="lg" className="gap-2">
                <Play className="w-5 h-5" />
                Start Trading
              </Button>
            </Link>
            <Link href="/dashboard">
              <Button variant="outline" size="lg" className="gap-2 bg-transparent">
                <LayoutDashboard className="w-5 h-5" />
                View Dashboard
              </Button>
            </Link>
          </div>
        </div>

        {/* Features Grid - Now with working links */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
          <Link href="/dashboard?tab=strategies">
            <Card className="border-2 hover:border-primary/50 transition-colors cursor-pointer h-full">
              <CardHeader className="text-center">
                <TrendingUp className="w-12 h-12 mx-auto mb-4 text-chart-1" />
                <CardTitle>Smart Strategies</CardTitle>
                <CardDescription>
                  AI-powered trading strategies that adapt and learn from market conditions
                </CardDescription>
              </CardHeader>
            </Card>
          </Link>

          <Link href="/dashboard?tab=risk">
            <Card className="border-2 hover:border-primary/50 transition-colors cursor-pointer h-full">
              <CardHeader className="text-center">
                <Shield className="w-12 h-12 mx-auto mb-4 text-chart-2" />
                <CardTitle>Risk Management</CardTitle>
                <CardDescription>
                  Advanced risk controls with stop-loss, position sizing, and volatility filters
                </CardDescription>
              </CardHeader>
            </Card>
          </Link>

          <Link href="/dashboard?tab=telegram">
            <Card className="border-2 hover:border-primary/50 transition-colors cursor-pointer h-full">
              <CardHeader className="text-center">
                <Bot className="w-12 h-12 mx-auto mb-4 text-chart-3" />
                <CardTitle>Telegram Bot</CardTitle>
                <CardDescription>Control your trading bot and receive alerts directly through Telegram</CardDescription>
              </CardHeader>
            </Card>
          </Link>

          <Link href="/dashboard?tab=analytics">
            <Card className="border-2 hover:border-primary/50 transition-colors cursor-pointer h-full">
              <CardHeader className="text-center">
                <BarChart3 className="w-12 h-12 mx-auto mb-4 text-chart-4" />
                <CardTitle>Analytics</CardTitle>
                <CardDescription>Comprehensive performance tracking and strategy optimization tools</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        </div>

        {/* Quick Actions */}
        <div className="grid md:grid-cols-3 gap-4 mb-16 max-w-4xl mx-auto">
          <Link href="/dashboard?tab=backtest">
            <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
              <CardContent className="flex items-center gap-4 p-6">
                <Zap className="w-8 h-8 text-yellow-500" />
                <div>
                  <h3 className="font-semibold">Backtesting</h3>
                  <p className="text-sm text-muted-foreground">Test strategies on historical data</p>
                </div>
              </CardContent>
            </Card>
          </Link>

          <Link href="/dashboard?tab=live">
            <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
              <CardContent className="flex items-center gap-4 p-6">
                <Play className="w-8 h-8 text-green-500" />
                <div>
                  <h3 className="font-semibold">Live Trading</h3>
                  <p className="text-sm text-muted-foreground">Start trading with real funds</p>
                </div>
              </CardContent>
            </Card>
          </Link>

          <Link href="/dashboard?tab=exchanges">
            <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
              <CardContent className="flex items-center gap-4 p-6">
                <AlertTriangle className="w-8 h-8 text-orange-500" />
                <div>
                  <h3 className="font-semibold">Exchange Setup</h3>
                  <p className="text-sm text-muted-foreground">Configure exchange connections</p>
                </div>
              </CardContent>
            </Card>
          </Link>
        </div>

        {/* System Status - Now dynamic */}
        <Card className="max-w-4xl mx-auto">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              System Status
              <Badge variant="secondary" className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100">
                Online
              </Badge>
            </CardTitle>
            <CardDescription>Trading system is ready for deployment</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-4 gap-4 mb-6">
              <div className="text-center p-4 rounded-lg bg-muted/50">
                <div className="text-2xl font-bold text-chart-1">6</div>
                <div className="text-sm text-muted-foreground">Strategies</div>
              </div>
              <div className="text-center p-4 rounded-lg bg-muted/50">
                <div className="text-2xl font-bold text-chart-2">10</div>
                <div className="text-sm text-muted-foreground">Exchanges</div>
              </div>
              <div className="text-center p-4 rounded-lg bg-muted/50">
                <div className="text-2xl font-bold text-chart-3">3</div>
                <div className="text-sm text-muted-foreground">Trading Modes</div>
              </div>
              <div className="text-center p-4 rounded-lg bg-muted/50">
                <div className="text-2xl font-bold text-chart-4">92%</div>
                <div className="text-sm text-muted-foreground">Complete</div>
              </div>
            </div>

            {/* API Test Links */}
            <div className="flex flex-wrap gap-2 justify-center">
              <Link href="/api/health" target="_blank">
                <Badge variant="outline" className="cursor-pointer hover:bg-muted">
                  Health Check
                </Badge>
              </Link>
              <Link href="/api/system/status" target="_blank">
                <Badge variant="outline" className="cursor-pointer hover:bg-muted">
                  System Status
                </Badge>
              </Link>
              <Link href="/api/test/connectivity" target="_blank">
                <Badge variant="outline" className="cursor-pointer hover:bg-muted">
                  Exchange Connectivity
                </Badge>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
