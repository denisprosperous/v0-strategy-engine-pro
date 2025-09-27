"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { useToast } from "@/hooks/use-toast"
import { Building2, Plus, Zap, AlertCircle, CheckCircle, XCircle } from "lucide-react"

interface ExchangeStatus {
  name: string
  connected: boolean
  lastPing: string | null
  errorCount: number
  tradingPairs: string[]
  balance: any[]
}

interface AggregatedBalance {
  [asset: string]: {
    total: number
    exchanges: Record<string, number>
  }
}

export default function MultiExchangePanel() {
  const [exchanges, setExchanges] = useState<ExchangeStatus[]>([])
  const [aggregatedBalance, setAggregatedBalance] = useState<AggregatedBalance>({})
  const [loading, setLoading] = useState(false)
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [bestPrices, setBestPrices] = useState<Record<string, any>>({})
  const { toast } = useToast()

  // New exchange form state
  const [newExchangeForm, setNewExchangeForm] = useState({
    name: "",
    displayName: "",
    apiKey: "",
    apiSecret: "",
    passphrase: "",
    testnet: false,
    enabled: true,
  })

  const supportedExchanges = [
    { value: "binance", label: "Binance", requiresPassphrase: false },
    { value: "bitget", label: "Bitget", requiresPassphrase: false },
    { value: "coinbase", label: "Coinbase Pro", requiresPassphrase: true },
    { value: "okx", label: "OKX", requiresPassphrase: true },
    { value: "kraken", label: "Kraken", requiresPassphrase: false },
  ]

  const popularPairs = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]

  useEffect(() => {
    fetchExchangeStatus()
    fetchAggregatedBalance()
    fetchBestPrices()

    const interval = setInterval(() => {
      fetchExchangeStatus()
      fetchBestPrices()
    }, 10000) // Update every 10 seconds

    return () => clearInterval(interval)
  }, [])

  const fetchExchangeStatus = async () => {
    try {
      const response = await fetch("/api/exchanges?action=status")
      const data = await response.json()

      if (data.success) {
        setExchanges(data.exchanges)
      }
    } catch (error) {
      console.error("[v0] Error fetching exchange status:", error)
    }
  }

  const fetchAggregatedBalance = async () => {
    try {
      const response = await fetch("/api/exchanges?action=balance")
      const data = await response.json()

      if (data.success) {
        setAggregatedBalance(data.balance)
      }
    } catch (error) {
      console.error("[v0] Error fetching aggregated balance:", error)
    }
  }

  const fetchBestPrices = async () => {
    const prices: Record<string, any> = {}

    for (const pair of popularPairs) {
      try {
        const [buyResponse, sellResponse] = await Promise.all([
          fetch(`/api/exchanges?action=best_price&symbol=${pair}&side=buy`),
          fetch(`/api/exchanges?action=best_price&symbol=${pair}&side=sell`),
        ])

        const buyData = await buyResponse.json()
        const sellData = await sellResponse.json()

        if (buyData.success && sellData.success) {
          prices[pair] = {
            buy: buyData.bestPrice,
            sell: sellData.bestPrice,
            spread: sellData.bestPrice?.price - buyData.bestPrice?.price || 0,
          }
        }
      } catch (error) {
        console.error(`[v0] Error fetching best prices for ${pair}:`, error)
      }
    }

    setBestPrices(prices)
  }

  const addExchange = async () => {
    if (!newExchangeForm.name || !newExchangeForm.apiKey || !newExchangeForm.apiSecret) {
      toast({
        title: "Error",
        description: "Please fill in all required fields",
        variant: "destructive",
      })
      return
    }

    const selectedExchange = supportedExchanges.find((ex) => ex.value === newExchangeForm.name)
    if (selectedExchange?.requiresPassphrase && !newExchangeForm.passphrase) {
      toast({
        title: "Error",
        description: `${selectedExchange.label} requires a passphrase`,
        variant: "destructive",
      })
      return
    }

    setLoading(true)
    try {
      const config = {
        name: newExchangeForm.name,
        displayName: newExchangeForm.displayName || selectedExchange?.label || newExchangeForm.name,
        apiKey: newExchangeForm.apiKey,
        apiSecret: newExchangeForm.apiSecret,
        passphrase: newExchangeForm.passphrase || undefined,
        testnet: newExchangeForm.testnet,
        enabled: newExchangeForm.enabled,
        features: {
          spot: true,
          futures: false,
          margin: false,
          websocket: true,
        },
        tradingPairs: popularPairs,
        fees: {
          maker: 0.001,
          taker: 0.001,
        },
      }

      const response = await fetch("/api/exchanges", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "add_exchange",
          config,
        }),
      })

      const data = await response.json()

      if (data.success) {
        toast({
          title: "Success",
          description: data.message,
        })
        setShowAddDialog(false)
        setNewExchangeForm({
          name: "",
          displayName: "",
          apiKey: "",
          apiSecret: "",
          passphrase: "",
          testnet: false,
          enabled: true,
        })
        fetchExchangeStatus()
        fetchAggregatedBalance()
      } else {
        throw new Error(data.error || "Failed to add exchange")
      }
    } catch (error) {
      console.error("[v0] Error adding exchange:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to add exchange",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const executeArbitrage = async (symbol: string, buyExchange: string, sellExchange: string) => {
    setLoading(true)
    try {
      const response = await fetch("/api/exchanges", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "execute_arbitrage",
          symbol,
          buyExchange,
          sellExchange,
          quantity: 0.01, // Small test amount
        }),
      })

      const data = await response.json()

      if (data.success) {
        toast({
          title: "Success",
          description: data.message,
        })
      } else {
        throw new Error(data.error || "Failed to execute arbitrage")
      }
    } catch (error) {
      console.error("[v0] Error executing arbitrage:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to execute arbitrage",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const getConnectionStatusIcon = (connected: boolean, errorCount: number) => {
    if (connected && errorCount === 0) {
      return <CheckCircle className="h-4 w-4 text-green-500" />
    } else if (connected && errorCount > 0) {
      return <AlertCircle className="h-4 w-4 text-yellow-500" />
    } else {
      return <XCircle className="h-4 w-4 text-red-500" />
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Multi-Exchange Trading
              </CardTitle>
              <CardDescription>
                Manage multiple exchange connections and execute cross-exchange strategies
              </CardDescription>
            </div>
            <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Exchange
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add Exchange Connection</DialogTitle>
                  <DialogDescription>Connect a new exchange to expand your trading capabilities</DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="exchange">Exchange</Label>
                    <Select
                      value={newExchangeForm.name}
                      onValueChange={(value) => setNewExchangeForm((prev) => ({ ...prev, name: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select exchange" />
                      </SelectTrigger>
                      <SelectContent>
                        {supportedExchanges.map((exchange) => (
                          <SelectItem key={exchange.value} value={exchange.value}>
                            {exchange.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="displayName">Display Name (Optional)</Label>
                    <Input
                      id="displayName"
                      placeholder="My Binance Account"
                      value={newExchangeForm.displayName}
                      onChange={(e) => setNewExchangeForm((prev) => ({ ...prev, displayName: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="apiKey">API Key</Label>
                    <Input
                      id="apiKey"
                      type="password"
                      placeholder="Your API key"
                      value={newExchangeForm.apiKey}
                      onChange={(e) => setNewExchangeForm((prev) => ({ ...prev, apiKey: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="apiSecret">API Secret</Label>
                    <Input
                      id="apiSecret"
                      type="password"
                      placeholder="Your API secret"
                      value={newExchangeForm.apiSecret}
                      onChange={(e) => setNewExchangeForm((prev) => ({ ...prev, apiSecret: e.target.value }))}
                    />
                  </div>
                  {supportedExchanges.find((ex) => ex.value === newExchangeForm.name)?.requiresPassphrase && (
                    <div className="space-y-2">
                      <Label htmlFor="passphrase">Passphrase</Label>
                      <Input
                        id="passphrase"
                        type="password"
                        placeholder="API passphrase"
                        value={newExchangeForm.passphrase}
                        onChange={(e) => setNewExchangeForm((prev) => ({ ...prev, passphrase: e.target.value }))}
                      />
                    </div>
                  )}
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="testnet"
                      checked={newExchangeForm.testnet}
                      onCheckedChange={(checked) => setNewExchangeForm((prev) => ({ ...prev, testnet: checked }))}
                    />
                    <Label htmlFor="testnet">Use Testnet</Label>
                  </div>
                  <Button onClick={addExchange} disabled={loading} className="w-full">
                    Add Exchange
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
      </Card>

      {/* Exchange Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {exchanges.map((exchange) => (
          <Card key={exchange.name}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center justify-between">
                <span className="capitalize">{exchange.name}</span>
                {getConnectionStatusIcon(exchange.connected, exchange.errorCount)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Status:</span>
                  <Badge variant={exchange.connected ? "default" : "destructive"}>
                    {exchange.connected ? "Connected" : "Disconnected"}
                  </Badge>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Trading Pairs:</span>
                  <span>{exchange.tradingPairs.length}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Errors:</span>
                  <span className={exchange.errorCount > 0 ? "text-red-500" : "text-green-500"}>
                    {exchange.errorCount}
                  </span>
                </div>
                {exchange.lastPing && (
                  <div className="flex justify-between text-sm">
                    <span>Last Ping:</span>
                    <span>{new Date(exchange.lastPing).toLocaleTimeString()}</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Aggregated Balance */}
      {Object.keys(aggregatedBalance).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Aggregated Balance</CardTitle>
            <CardDescription>Your total balance across all connected exchanges</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(aggregatedBalance)
                .filter(([_, data]) => data.total > 0.01)
                .map(([asset, data]) => (
                  <div key={asset} className="p-4 border rounded-lg">
                    <div className="font-semibold text-lg">{asset}</div>
                    <div className="text-2xl font-bold">{data.total.toFixed(6)}</div>
                    <div className="text-sm text-muted-foreground mt-2">
                      {Object.entries(data.exchanges).map(([exchange, amount]) => (
                        <div key={exchange} className="flex justify-between">
                          <span className="capitalize">{exchange}:</span>
                          <span>{amount.toFixed(6)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Best Prices & Arbitrage Opportunities */}
      {Object.keys(bestPrices).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              Best Prices & Arbitrage
            </CardTitle>
            <CardDescription>Real-time price comparison across exchanges</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {Object.entries(bestPrices).map(([symbol, data]) => (
                <div key={symbol} className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold">{symbol}</h4>
                    {data.spread > 0 && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => executeArbitrage(symbol, data.buy?.exchange, data.sell?.exchange)}
                        disabled={loading || !data.buy || !data.sell}
                      >
                        <Zap className="h-3 w-3 mr-1" />
                        Arbitrage
                      </Button>
                    )}
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <div className="text-muted-foreground">Best Buy</div>
                      {data.buy ? (
                        <div>
                          <div className="font-semibold text-green-600">${data.buy.price.toFixed(2)}</div>
                          <div className="text-xs capitalize">{data.buy.exchange}</div>
                        </div>
                      ) : (
                        <div className="text-muted-foreground">N/A</div>
                      )}
                    </div>
                    <div>
                      <div className="text-muted-foreground">Best Sell</div>
                      {data.sell ? (
                        <div>
                          <div className="font-semibold text-red-600">${data.sell.price.toFixed(2)}</div>
                          <div className="text-xs capitalize">{data.sell.exchange}</div>
                        </div>
                      ) : (
                        <div className="text-muted-foreground">N/A</div>
                      )}
                    </div>
                    <div>
                      <div className="text-muted-foreground">Spread</div>
                      <div className={`font-semibold ${data.spread > 0 ? "text-yellow-600" : "text-muted-foreground"}`}>
                        {data.spread > 0 ? `$${data.spread.toFixed(2)}` : "N/A"}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
