import type { TradingAccount, AccountTransaction, AccountBalance } from "@/lib/database/schema"

export class AccountManager {
  private accounts: Map<string, TradingAccount> = new Map()
  private balances: Map<string, AccountBalance> = new Map()

  constructor(private userId: string) {}

  async initializeAccounts(): Promise<void> {
    try {
      // Load user accounts from database
      const userAccounts = await this.loadUserAccounts()

      // If no accounts exist, create default demo account
      if (userAccounts.length === 0) {
        await this.createDefaultDemoAccount()
      }

      // Load account balances
      for (const account of userAccounts) {
        this.accounts.set(account.id, account)
        const balance = await this.loadAccountBalance(account.id)
        this.balances.set(account.id, balance)
      }

      console.log(`[v0] Initialized ${userAccounts.length} accounts for user ${this.userId}`)
    } catch (error) {
      console.error("[v0] Failed to initialize accounts:", error)
      throw error
    }
  }

  private async createDefaultDemoAccount(): Promise<TradingAccount> {
    const demoAccount: TradingAccount = {
      id: `demo_${this.userId}_${Date.now()}`,
      user_id: this.userId,
      account_type: "demo",
      account_name: "Demo Trading Account",
      balance: 100000, // $100,000 demo balance
      currency: "USD",
      broker: "demo",
      is_active: true,
      created_at: new Date(),
      updated_at: new Date(),
    }

    // Save to database (simulated)
    await this.saveAccount(demoAccount)

    // Create initial balance record
    const initialBalance: AccountBalance = {
      account_id: demoAccount.id,
      total_balance: 100000,
      available_balance: 100000,
      reserved_balance: 0,
      unrealized_pnl: 0,
      currency: "USD",
      last_updated: new Date(),
    }

    await this.saveAccountBalance(initialBalance)

    // Record initial deposit transaction
    await this.recordTransaction({
      id: `tx_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      account_id: demoAccount.id,
      transaction_type: "deposit",
      amount: 100000,
      currency: "USD",
      description: "Initial demo account funding",
      timestamp: new Date(),
    })

    return demoAccount
  }

  async createLiveAccount(
    accountName: string,
    broker: "binance" | "bitget",
    apiCredentials: { api_key: string; api_secret: string; passphrase?: string },
  ): Promise<TradingAccount> {
    const liveAccount: TradingAccount = {
      id: `live_${this.userId}_${Date.now()}`,
      user_id: this.userId,
      account_type: "live",
      account_name: accountName,
      balance: 0, // Will be fetched from broker
      currency: "USDT",
      broker,
      api_credentials: apiCredentials,
      is_active: true,
      created_at: new Date(),
      updated_at: new Date(),
    }

    // Validate API credentials by fetching balance
    try {
      const brokerBalance = await this.fetchBrokerBalance(broker, apiCredentials)
      liveAccount.balance = brokerBalance.total

      await this.saveAccount(liveAccount)

      const initialBalance: AccountBalance = {
        account_id: liveAccount.id,
        total_balance: brokerBalance.total,
        available_balance: brokerBalance.available,
        reserved_balance: brokerBalance.reserved,
        unrealized_pnl: brokerBalance.unrealized_pnl || 0,
        currency: "USDT",
        last_updated: new Date(),
      }

      await this.saveAccountBalance(initialBalance)
      this.accounts.set(liveAccount.id, liveAccount)
      this.balances.set(liveAccount.id, initialBalance)

      return liveAccount
    } catch (error) {
      throw new Error(`Failed to validate API credentials: ${error}`)
    }
  }

  getUserAccounts(): TradingAccount[] {
    return Array.from(this.accounts.values())
  }

  getAccount(accountId: string): TradingAccount | undefined {
    return this.accounts.get(accountId)
  }

  getAccountBalance(accountId: string): AccountBalance | undefined {
    return this.balances.get(accountId)
  }

  async updateAccountBalance(accountId: string, balanceUpdate: Partial<AccountBalance>): Promise<void> {
    const currentBalance = this.balances.get(accountId)
    if (!currentBalance) {
      throw new Error(`Account balance not found: ${accountId}`)
    }

    const updatedBalance: AccountBalance = {
      ...currentBalance,
      ...balanceUpdate,
      last_updated: new Date(),
    }

    this.balances.set(accountId, updatedBalance)
    await this.saveAccountBalance(updatedBalance)
  }

  async recordTransaction(transaction: AccountTransaction): Promise<void> {
    // Save transaction to database
    await this.saveTransaction(transaction)

    // Update account balance based on transaction
    const balance = this.balances.get(transaction.account_id)
    if (balance) {
      let balanceChange = 0

      switch (transaction.transaction_type) {
        case "deposit":
        case "trade_profit":
          balanceChange = transaction.amount
          break
        case "withdrawal":
        case "trade_loss":
        case "fee":
          balanceChange = -transaction.amount
          break
        case "demo_reset":
          // Reset demo account to initial balance
          await this.updateAccountBalance(transaction.account_id, {
            total_balance: 100000,
            available_balance: 100000,
            reserved_balance: 0,
            unrealized_pnl: 0,
          })
          return
      }

      await this.updateAccountBalance(transaction.account_id, {
        total_balance: balance.total_balance + balanceChange,
        available_balance: balance.available_balance + balanceChange,
      })
    }
  }

  async resetDemoAccount(accountId: string): Promise<void> {
    const account = this.accounts.get(accountId)
    if (!account || account.account_type !== "demo") {
      throw new Error("Can only reset demo accounts")
    }

    await this.recordTransaction({
      id: `tx_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      account_id: accountId,
      transaction_type: "demo_reset",
      amount: 100000,
      currency: "USD",
      description: "Demo account reset to initial balance",
      timestamp: new Date(),
    })
  }

  async syncLiveAccountBalance(accountId: string): Promise<void> {
    const account = this.accounts.get(accountId)
    if (!account || account.account_type !== "live" || !account.api_credentials) {
      throw new Error("Invalid live account for balance sync")
    }

    try {
      const brokerBalance = await this.fetchBrokerBalance(account.broker, account.api_credentials)

      await this.updateAccountBalance(accountId, {
        total_balance: brokerBalance.total,
        available_balance: brokerBalance.available,
        reserved_balance: brokerBalance.reserved,
        unrealized_pnl: brokerBalance.unrealized_pnl || 0,
      })

      console.log(`[v0] Synced balance for account ${accountId}:`, brokerBalance)
    } catch (error) {
      console.error(`[v0] Failed to sync balance for account ${accountId}:`, error)
      throw error
    }
  }

  private async loadUserAccounts(): Promise<TradingAccount[]> {
    // Simulate loading from database
    // In real implementation, this would query the database
    return []
  }

  private async loadAccountBalance(accountId: string): Promise<AccountBalance> {
    // Simulate loading from database
    return {
      account_id: accountId,
      total_balance: 100000,
      available_balance: 100000,
      reserved_balance: 0,
      unrealized_pnl: 0,
      currency: "USD",
      last_updated: new Date(),
    }
  }

  private async saveAccount(account: TradingAccount): Promise<void> {
    // Simulate saving to database
    console.log(`[v0] Saved account:`, account.id)
  }

  private async saveAccountBalance(balance: AccountBalance): Promise<void> {
    // Simulate saving to database
    console.log(`[v0] Saved balance for account:`, balance.account_id)
  }

  private async saveTransaction(transaction: AccountTransaction): Promise<void> {
    // Simulate saving to database
    console.log(`[v0] Saved transaction:`, transaction.id)
  }

  private async fetchBrokerBalance(
    broker: string,
    credentials: { api_key: string; api_secret: string; passphrase?: string },
  ): Promise<{ total: number; available: number; reserved: number; unrealized_pnl?: number }> {
    // Simulate fetching balance from broker API
    // In real implementation, this would call the actual broker API
    return {
      total: 10000,
      available: 8000,
      reserved: 2000,
      unrealized_pnl: 150,
    }
  }
}
