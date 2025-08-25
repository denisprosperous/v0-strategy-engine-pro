import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { TrendingUp, Shield, Bot, BarChart3 } from "lucide-react"

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      <div className="container mx-auto px-4 py-16">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-primary to-chart-1 bg-clip-text text-transparent">
            AI Trading System
          </h1>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Advanced algorithmic trading platform with AI-powered strategies, real-time sentiment analysis, and
            comprehensive risk management.
          </p>
          <div className="flex gap-4 justify-center">
            <Button size="lg" className="gap-2">
              <Bot className="w-5 h-5" />
              Start Trading
            </Button>
            <Button variant="outline" size="lg" className="gap-2 bg-transparent">
              <BarChart3 className="w-5 h-5" />
              View Dashboard
            </Button>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
          <Card className="border-2 hover:border-primary/50 transition-colors">
            <CardHeader className="text-center">
              <TrendingUp className="w-12 h-12 mx-auto mb-4 text-chart-1" />
              <CardTitle>Smart Strategies</CardTitle>
              <CardDescription>
                AI-powered trading strategies that adapt and learn from market conditions
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="border-2 hover:border-primary/50 transition-colors">
            <CardHeader className="text-center">
              <Shield className="w-12 h-12 mx-auto mb-4 text-chart-2" />
              <CardTitle>Risk Management</CardTitle>
              <CardDescription>
                Advanced risk controls with stop-loss, position sizing, and volatility filters
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="border-2 hover:border-primary/50 transition-colors">
            <CardHeader className="text-center">
              <Bot className="w-12 h-12 mx-auto mb-4 text-chart-3" />
              <CardTitle>Telegram Bot</CardTitle>
              <CardDescription>Control your trading bot and receive alerts directly through Telegram</CardDescription>
            </CardHeader>
          </Card>

          <Card className="border-2 hover:border-primary/50 transition-colors">
            <CardHeader className="text-center">
              <BarChart3 className="w-12 h-12 mx-auto mb-4 text-chart-4" />
              <CardTitle>Analytics</CardTitle>
              <CardDescription>Comprehensive performance tracking and strategy optimization tools</CardDescription>
            </CardHeader>
          </Card>
        </div>

        {/* System Status */}
        <Card className="max-w-4xl mx-auto">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              System Status
              <Badge variant="secondary" className="bg-green-100 text-green-800">
                Online
              </Badge>
            </CardTitle>
            <CardDescription>Core infrastructure and database schema have been initialized</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-chart-1">4</div>
                <div className="text-sm text-muted-foreground">Active Strategies</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-chart-2">0</div>
                <div className="text-sm text-muted-foreground">Open Trades</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-chart-3">Ready</div>
                <div className="text-sm text-muted-foreground">Database Status</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
