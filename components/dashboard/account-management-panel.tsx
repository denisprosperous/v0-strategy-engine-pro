"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { useToast } from "@/hooks/use-toast"
import {
  Wallet,
  Plus,
  RefreshCw,
  RotateCcw,
  Eye,
  EyeOff,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
} from "lucide-react"

interface TradingAccount {
  id: string
  account_type: "demo" | "live"
  account_name: string
  balance: number
  currency: string
  broker: string
  is_active: boolean
  created_at: string
}

interface AccountBalance {
  total_balance: number
  available_balance: number
  reserved_balance: number
  unrealized_pnl: number
  currency: string
  last_updated: string
}

interface AccountWithBalance extends TradingAccount {
  balance: AccountBalance
}

export default function AccountManagementPanel() {
  const [accounts, setAccounts] = useState<AccountWithBalance[]>([])
  const [selectedAccount, setSelectedAccount] = useState<string>("")
  const [loading, setLoading] = useState(false)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showApiKeys, setShowApiKeys] = useState<Record<string, boolean>>({})
  const { toast } = useToast()

  // New account form state
  const [newAccountForm, setNewAccountForm] = useState({
    accountName: "",
    broker: "",
    apiKey: "",
    apiSecret: "",
    passphrase: "",
  })

  useEffect(() => {
    fetchAccounts()
  }, [])

  const fetchAccounts = async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/accounts")
      const data = await response.json()

      if (data.success) {
        setAccounts(data.accounts)
        if (data.accounts.length > 0 && !selectedAccount) {
          setSelectedAccount(data.accounts[0].id)
        }
      }
    } catch (error) {
      console.error("[v0] Error fetching accounts:", error)
      toast({
        title: "Error",
        description: "Failed to fetch accounts",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const createLiveAccount = async () => {
    if (!newAccountForm.accountName || !newAccountForm.broker || !newAccountForm.apiKey || !newAccountForm.apiSecret) {
      toast({
        title: "Error",
        description: "Please fill in all required fields",
        variant: "destructive",
      })
      return
    }

    setLoading(true)
    try {
      const response = await fetch("/api/accounts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "create_live_account",
          accountName: newAccountForm.accountName,
          broker: newAccountForm.broker,
          apiCredentials: {
            api_key: newAccountForm.apiKey,
            api_secret: newAccountForm.apiSecret,
            passphrase: newAccountForm.passphrase || undefined,
          },
        }),
      })

      const data = await response.json()

      if (data.success) {
        toast({
          title: "Success",
          description: data.message,
        })
        setShowCreateDialog(false)
        setNewAccountForm({
          accountName: "",
          broker: "",
          apiKey: "",
          apiSecret: "",
          passphrase: "",
        })
        fetchAccounts()
      } else {
        throw new Error(data.error || "Failed to create account")
      }
    } catch (error) {
      console.error("[v0] Error creating account:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to create live account",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const resetDemoAccount = async (accountId: string) => {
    setLoading(true)
    try {
      const response = await fetch("/api/accounts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "reset_demo_account",
          accountId,
        }),
      })

      const data = await response.json()

      if (data.success) {
        toast({
          title: "Success",
          description: data.message,
        })
        fetchAccounts()
      } else {
        throw new Error(data.error || "Failed to reset account")
      }
    } catch (error) {
      console.error("[v0] Error resetting account:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to reset demo account",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const syncLiveBalance = async (accountId: string) => {
    setLoading(true)
    try {
      const response = await fetch("/api/accounts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "sync_live_balance",
          accountId,
        }),
      })

      const data = await response.json()

      if (data.success) {
        toast({
          title: "Success",
          description: data.message,
        })
        fetchAccounts()
      } else {
        throw new Error(data.error || "Failed to sync balance")
      }
    } catch (error) {
      console.error("[v0] Error syncing balance:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to sync balance",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const selectedAccountData = accounts.find((acc) => acc.id === selectedAccount)

  return (
    <div className="space-y-6">
      {/* Account Selection */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Wallet className="h-5 w-5" />
                Trading Accounts
              </CardTitle>
              <CardDescription>Manage your demo and live trading accounts</CardDescription>
            </div>
            <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Live Account
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create Live Trading Account</DialogTitle>
                  <DialogDescription>Connect your exchange API keys to enable live trading</DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="accountName">Account Name</Label>
                    <Input
                      id="accountName"
                      placeholder="My Binance Account"
                      value={newAccountForm.accountName}
                      onChange={(e) => setNewAccountForm((prev) => ({ ...prev, accountName: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="broker">Exchange</Label>
                    <Select
                      value={newAccountForm.broker}
                      onValueChange={(value) => setNewAccountForm((prev) => ({ ...prev, broker: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select exchange" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="binance">Binance</SelectItem>
                        <SelectItem value="bitget">Bitget</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="apiKey">API Key</Label>
                    <Input
                      id="apiKey"
                      type="password"
                      placeholder="Your API key"
                      value={newAccountForm.apiKey}
                      onChange={(e) => setNewAccountForm((prev) => ({ ...prev, apiKey: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="apiSecret">API Secret</Label>
                    <Input
                      id="apiSecret"
                      type="password"
                      placeholder="Your API secret"
                      value={newAccountForm.apiSecret}
                      onChange={(e) => setNewAccountForm((prev) => ({ ...prev, apiSecret: e.target.value }))}
                    />
                  </div>
                  {newAccountForm.broker === "bitget" && (
                    <div className="space-y-2">
                      <Label htmlFor="passphrase">Passphrase (Optional)</Label>
                      <Input
                        id="passphrase"
                        type="password"
                        placeholder="API passphrase"
                        value={newAccountForm.passphrase}
                        onChange={(e) => setNewAccountForm((prev) => ({ ...prev, passphrase: e.target.value }))}
                      />
                    </div>
                  )}
                  <Button onClick={createLiveAccount} disabled={loading} className="w-full">
                    Create Account
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Select Account</Label>
              <Select value={selectedAccount} onValueChange={setSelectedAccount}>
                <SelectTrigger>
                  <SelectValue placeholder="Select trading account" />
                </SelectTrigger>
                <SelectContent>
                  {accounts.map((account) => (
                    <SelectItem key={account.id} value={account.id}>
                      <div className="flex items-center gap-2">
                        <Badge variant={account.account_type === "demo" ? "secondary" : "default"}>
                          {account.account_type}
                        </Badge>
                        {account.account_name} ({account.broker})
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Account Details */}
      {selectedAccountData && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <DollarSign className="h-4 w-4" />
                Total Balance
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${selectedAccountData.balance.total_balance.toLocaleString()}</div>
              <div className="text-xs text-muted-foreground">{selectedAccountData.balance.currency}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Activity className="h-4 w-4" />
                Available
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                ${selectedAccountData.balance.available_balance.toLocaleString()}
              </div>
              <div className="text-xs text-muted-foreground">Ready to trade</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Reserved</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-yellow-600">
                ${selectedAccountData.balance.reserved_balance.toLocaleString()}
              </div>
              <div className="text-xs text-muted-foreground">In open positions</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Unrealized P&L</CardTitle>
            </CardHeader>
            <CardContent>
              <div
                className={`text-2xl font-bold flex items-center gap-1 ${
                  selectedAccountData.balance.unrealized_pnl >= 0 ? "text-green-600" : "text-red-600"
                }`}
              >
                {selectedAccountData.balance.unrealized_pnl >= 0 ? (
                  <TrendingUp className="h-4 w-4" />
                ) : (
                  <TrendingDown className="h-4 w-4" />
                )}
                ${Math.abs(selectedAccountData.balance.unrealized_pnl).toLocaleString()}
              </div>
              <div className="text-xs text-muted-foreground">Open positions</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Account Actions */}
      {selectedAccountData && (
        <Card>
          <CardHeader>
            <CardTitle>Account Actions</CardTitle>
            <CardDescription>Manage your selected trading account</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {selectedAccountData.account_type === "live" && (
                <Button onClick={() => syncLiveBalance(selectedAccountData.id)} disabled={loading} variant="outline">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Sync Balance
                </Button>
              )}

              {selectedAccountData.account_type === "demo" && (
                <Button onClick={() => resetDemoAccount(selectedAccountData.id)} disabled={loading} variant="outline">
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Reset Demo Account
                </Button>
              )}

              <Button
                onClick={() =>
                  setShowApiKeys((prev) => ({
                    ...prev,
                    [selectedAccountData.id]: !prev[selectedAccountData.id],
                  }))
                }
                variant="outline"
              >
                {showApiKeys[selectedAccountData.id] ? (
                  <EyeOff className="h-4 w-4 mr-2" />
                ) : (
                  <Eye className="h-4 w-4 mr-2" />
                )}
                {showApiKeys[selectedAccountData.id] ? "Hide" : "Show"} Details
              </Button>
            </div>

            {showApiKeys[selectedAccountData.id] && (
              <div className="mt-4 p-4 bg-muted rounded-lg">
                <h4 className="font-medium mb-2">Account Details</h4>
                <div className="space-y-2 text-sm">
                  <div>
                    <strong>Account ID:</strong> {selectedAccountData.id}
                  </div>
                  <div>
                    <strong>Type:</strong> {selectedAccountData.account_type}
                  </div>
                  <div>
                    <strong>Broker:</strong> {selectedAccountData.broker}
                  </div>
                  <div>
                    <strong>Created:</strong> {new Date(selectedAccountData.created_at).toLocaleDateString()}
                  </div>
                  <div>
                    <strong>Last Updated:</strong> {new Date(selectedAccountData.balance.last_updated).toLocaleString()}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
