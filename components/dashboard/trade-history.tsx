"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Search, Download, TrendingUp, TrendingDown } from "lucide-react"

const trades = [
  {
    id: "TXN001",
    timestamp: "2024-01-15 14:30:25",
    symbol: "BTC/USDT",
    type: "BUY",
    amount: 0.25,
    entryPrice: 43250.0,
    exitPrice: 43375.5,
    pnl: 31.38,
    status: "closed",
    strategy: "Breakout Scalping",
  },
  {
    id: "TXN002",
    timestamp: "2024-01-15 13:45:12",
    symbol: "ETH/USDT",
    type: "SELL",
    amount: 2.5,
    entryPrice: 2650.0,
    exitPrice: 2632.1,
    pnl: -44.75,
    status: "closed",
    strategy: "Mean Reversion",
  },
  {
    id: "TXN003",
    timestamp: "2024-01-15 12:20:08",
    symbol: "SOL/USDT",
    type: "BUY",
    amount: 15,
    entryPrice: 98.5,
    exitPrice: null,
    pnl: 89.75,
    status: "open",
    strategy: "Momentum + Sentiment",
  },
  {
    id: "TXN004",
    timestamp: "2024-01-15 11:15:33",
    symbol: "AVAX/USDT",
    type: "BUY",
    amount: 8,
    entryPrice: 35.2,
    exitPrice: null,
    pnl: 12.8,
    status: "open",
    strategy: "News Event Scalping",
  },
  {
    id: "TXN005",
    timestamp: "2024-01-15 10:30:45",
    symbol: "MATIC/USDT",
    type: "SELL",
    amount: 100,
    entryPrice: 0.85,
    exitPrice: 0.88,
    pnl: 3.0,
    status: "closed",
    strategy: "Breakout Scalping",
  },
]

export function TradeHistory() {
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")
  const [typeFilter, setTypeFilter] = useState("all")

  const filteredTrades = trades.filter((trade) => {
    const matchesSearch =
      trade.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
      trade.id.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = statusFilter === "all" || trade.status === statusFilter
    const matchesType = typeFilter === "all" || trade.type.toLowerCase() === typeFilter

    return matchesSearch && matchesStatus && matchesType
  })

  const totalPnL = filteredTrades.reduce((sum, trade) => sum + trade.pnl, 0)
  const winningTrades = filteredTrades.filter((trade) => trade.pnl > 0).length
  const winRate = filteredTrades.length > 0 ? (winningTrades / filteredTrades.length) * 100 : 0

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${totalPnL >= 0 ? "text-green-500" : "text-red-500"}`}>
              {totalPnL >= 0 ? "+" : ""}${totalPnL.toFixed(2)}
            </div>
            <div className="flex items-center text-xs text-muted-foreground mt-1">
              {totalPnL >= 0 ? (
                <TrendingUp className="w-3 h-3 mr-1 text-green-500" />
              ) : (
                <TrendingDown className="w-3 h-3 mr-1 text-red-500" />
              )}
              {filteredTrades.length} trades
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{winRate.toFixed(1)}%</div>
            <div className="text-xs text-muted-foreground mt-1">
              {winningTrades} winning / {filteredTrades.length} total
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Open Positions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{filteredTrades.filter((t) => t.status === "open").length}</div>
            <div className="text-xs text-muted-foreground mt-1">Active trades</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Search */}
      <Card>
        <CardHeader>
          <CardTitle>Trade History</CardTitle>
          <CardDescription>Complete record of all trading activity</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 mb-6">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
              <Input
                placeholder="Search by symbol or trade ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-32">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="open">Open</SelectItem>
                <SelectItem value="closed">Closed</SelectItem>
              </SelectContent>
            </Select>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-full sm:w-32">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="buy">Buy</SelectItem>
                <SelectItem value="sell">Sell</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" size="sm">
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
          </div>

          {/* Trades Table */}
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Trade ID</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Entry Price</TableHead>
                  <TableHead>Exit Price</TableHead>
                  <TableHead>P&L</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Strategy</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTrades.map((trade) => (
                  <TableRow key={trade.id}>
                    <TableCell className="font-medium">{trade.id}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{trade.timestamp}</TableCell>
                    <TableCell className="font-medium">{trade.symbol}</TableCell>
                    <TableCell>
                      <Badge variant={trade.type === "BUY" ? "default" : "secondary"}>{trade.type}</Badge>
                    </TableCell>
                    <TableCell>{trade.amount}</TableCell>
                    <TableCell>${trade.entryPrice.toFixed(2)}</TableCell>
                    <TableCell>{trade.exitPrice ? `$${trade.exitPrice.toFixed(2)}` : "-"}</TableCell>
                    <TableCell className={trade.pnl >= 0 ? "text-green-500" : "text-red-500"}>
                      {trade.pnl >= 0 ? "+" : ""}${trade.pnl.toFixed(2)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={trade.status === "open" ? "default" : "outline"}>{trade.status}</Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{trade.strategy}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
