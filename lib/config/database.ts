import { Redis } from "@upstash/redis"

// Initialize Redis client using environment variables
const redis = new Redis({
  url: process.env.UPSTASH_KV_KV_REST_API_URL || process.env.KV_REST_API_URL || "",
  token: process.env.UPSTASH_KV_KV_REST_API_TOKEN || process.env.KV_REST_API_TOKEN || "",
})

// Data access layer that uses Redis for persistence
export const db = {
  // Users
  async getUser(userId: string) {
    const user = await redis.hgetall(`user:${userId}`)
    return user && Object.keys(user).length > 0 ? user : null
  },

  async getUserByUsername(username: string) {
    const userId = await redis.get(`username:${username}`)
    if (!userId) return null
    return this.getUser(userId as string)
  },

  async getUserByEmail(email: string) {
    const userId = await redis.get(`email:${email}`)
    if (!userId) return null
    return this.getUser(userId as string)
  },

  async createUser(user: {
    id: string
    username: string
    email: string
    passwordHash: string
    role?: string
  }) {
    const userData = {
      ...user,
      role: user.role || "trader",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      settings: JSON.stringify({
        riskTolerance: 0.5,
        maxDailyLoss: 1000,
        defaultPositionSize: 100,
        autoTradingEnabled: false,
      }),
    }
    await redis.hset(`user:${user.id}`, userData)
    await redis.set(`username:${user.username}`, user.id)
    await redis.set(`email:${user.email}`, user.id)
    await redis.sadd("users", user.id)
    return userData
  },

  async updateUser(userId: string, updates: Record<string, any>) {
    updates.updatedAt = new Date().toISOString()
    await redis.hset(`user:${userId}`, updates)
    return this.getUser(userId)
  },

  // Trades
  async getTrades(userId: string, options?: { status?: string; limit?: number }) {
    const tradeIds = await redis.smembers(`user:${userId}:trades`)
    if (!tradeIds.length) return []

    const trades = await Promise.all(
      tradeIds.map(async (id) => {
        const trade = await redis.hgetall(`trade:${id}`)
        return trade && Object.keys(trade).length > 0 ? { id, ...trade } : null
      }),
    )

    let filteredTrades = trades.filter(Boolean) as any[]

    if (options?.status) {
      filteredTrades = filteredTrades.filter((t) => t.status === options.status)
    }

    // Sort by executionTime descending
    filteredTrades.sort((a, b) => new Date(b.executionTime || 0).getTime() - new Date(a.executionTime || 0).getTime())

    if (options?.limit) {
      filteredTrades = filteredTrades.slice(0, options.limit)
    }

    return filteredTrades
  },

  async createTrade(trade: {
    id: string
    userId: string
    symbol: string
    side: string
    entryPrice: number
    quantity: number
    broker: string
    strategyId?: string
    stopLoss?: number
    takeProfit?: number
  }) {
    const tradeData = {
      ...trade,
      status: "open",
      pnl: 0,
      fees: 0,
      executionTime: new Date().toISOString(),
    }
    await redis.hset(`trade:${trade.id}`, tradeData)
    await redis.sadd(`user:${trade.userId}:trades`, trade.id)
    await redis.sadd("trades", trade.id)
    return tradeData
  },

  async updateTrade(tradeId: string, updates: Record<string, any>) {
    await redis.hset(`trade:${tradeId}`, updates)
    return redis.hgetall(`trade:${tradeId}`)
  },

  async closeTrade(tradeId: string, exitPrice: number, fees = 0) {
    const trade = (await redis.hgetall(`trade:${tradeId}`)) as any
    if (!trade) return null

    const entryPrice = Number.parseFloat(trade.entryPrice)
    const quantity = Number.parseFloat(trade.quantity)
    const pnl =
      trade.side === "buy" ? (exitPrice - entryPrice) * quantity - fees : (entryPrice - exitPrice) * quantity - fees

    const updates = {
      status: "closed",
      exitPrice,
      pnl,
      fees,
      closeTime: new Date().toISOString(),
    }
    await redis.hset(`trade:${tradeId}`, updates)
    return { ...trade, ...updates }
  },

  // Strategies
  async getStrategies(userId: string) {
    const strategyIds = await redis.smembers(`user:${userId}:strategies`)
    if (!strategyIds.length) return []

    const strategies = await Promise.all(
      strategyIds.map(async (id) => {
        const strategy = await redis.hgetall(`strategy:${id}`)
        return strategy && Object.keys(strategy).length > 0 ? { id, ...strategy } : null
      }),
    )

    return strategies.filter(Boolean)
  },

  async createStrategy(strategy: {
    id: string
    userId: string
    name: string
    type: string
    description?: string
    parameters?: Record<string, any>
  }) {
    const strategyData = {
      ...strategy,
      parameters: JSON.stringify(strategy.parameters || {}),
      isActive: false,
      performanceMetrics: JSON.stringify({
        totalTrades: 0,
        winRate: 0,
        avgPnl: 0,
        maxDrawdown: 0,
        sharpeRatio: 0,
      }),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    await redis.hset(`strategy:${strategy.id}`, strategyData)
    await redis.sadd(`user:${strategy.userId}:strategies`, strategy.id)
    await redis.sadd("strategies", strategy.id)
    return strategyData
  },

  async updateStrategy(strategyId: string, updates: Record<string, any>) {
    updates.updatedAt = new Date().toISOString()
    if (updates.parameters && typeof updates.parameters === "object") {
      updates.parameters = JSON.stringify(updates.parameters)
    }
    if (updates.performanceMetrics && typeof updates.performanceMetrics === "object") {
      updates.performanceMetrics = JSON.stringify(updates.performanceMetrics)
    }
    await redis.hset(`strategy:${strategyId}`, updates)
    return redis.hgetall(`strategy:${strategyId}`)
  },

  // Market Data Cache
  async cacheMarketData(symbol: string, data: any, ttlSeconds = 60) {
    await redis.setex(`market:${symbol}`, ttlSeconds, JSON.stringify(data))
  },

  async getCachedMarketData(symbol: string) {
    const data = await redis.get(`market:${symbol}`)
    return data ? JSON.parse(data as string) : null
  },

  // Portfolio
  async getPortfolio(userId: string) {
    const portfolio = await redis.hgetall(`portfolio:${userId}`)
    return portfolio && Object.keys(portfolio).length > 0 ? portfolio : null
  },

  async updatePortfolio(userId: string, updates: Record<string, any>) {
    await redis.hset(`portfolio:${userId}`, {
      ...updates,
      updatedAt: new Date().toISOString(),
    })
    return this.getPortfolio(userId)
  },

  // Analytics
  async getAnalytics(userId: string) {
    const trades = await this.getTrades(userId)
    const strategies = await this.getStrategies(userId)

    const closedTrades = trades.filter((t: any) => t.status === "closed")
    const openTrades = trades.filter((t: any) => t.status === "open")

    const totalPnL = closedTrades.reduce((sum: number, t: any) => sum + Number.parseFloat(t.pnl || 0), 0)
    const winningTrades = closedTrades.filter((t: any) => Number.parseFloat(t.pnl || 0) > 0)
    const winRate = closedTrades.length > 0 ? (winningTrades.length / closedTrades.length) * 100 : 0

    const activeStrategies = strategies.filter((s: any) => s.isActive === "true" || s.isActive === true)

    return {
      portfolio: {
        totalPnL,
        dailyPnL: 0, // Calculate from today's trades
        pnlPercentage: 0,
      },
      trading: {
        totalTrades: trades.length,
        openTrades: openTrades.length,
        winRate,
        activeStrategies: activeStrategies.length,
      },
      performance: {
        bestTrade:
          closedTrades.length > 0 ? Math.max(...closedTrades.map((t: any) => Number.parseFloat(t.pnl || 0))) : 0,
        worstTrade:
          closedTrades.length > 0 ? Math.min(...closedTrades.map((t: any) => Number.parseFloat(t.pnl || 0))) : 0,
        avgTradeSize:
          closedTrades.length > 0
            ? closedTrades.reduce(
                (sum: number, t: any) =>
                  sum + Number.parseFloat(t.entryPrice || 0) * Number.parseFloat(t.quantity || 0),
                0,
              ) / closedTrades.length
            : 0,
      },
    }
  },
}

// Export redis for direct access if needed
export { redis }

// Legacy support - export as supabase for compatibility
// This allows gradual migration
export const supabase = {
  from: (table: string) => ({
    select: () => ({
      eq: () => ({
        order: () => Promise.resolve({ data: [], error: null }),
        single: () => Promise.resolve({ data: null, error: null }),
      }),
      single: () => Promise.resolve({ data: null, error: null }),
    }),
    insert: () => ({
      select: () => ({
        single: () => Promise.resolve({ data: null, error: null }),
      }),
    }),
    update: () => ({
      eq: () => Promise.resolve({ data: null, error: null }),
    }),
    delete: () => ({
      eq: () => Promise.resolve({ error: null }),
    }),
  }),
}
