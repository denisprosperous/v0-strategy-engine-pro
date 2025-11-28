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

  async updateUser(userId: string, updates: Record<string, unknown>) {
    const newUpdates = { ...updates, updatedAt: new Date().toISOString() }
    await redis.hset(`user:${userId}`, newUpdates)
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

    let filteredTrades = trades.filter(Boolean) as Record<string, unknown>[]

    if (options?.status) {
      filteredTrades = filteredTrades.filter((t) => t.status === options.status)
    }

    filteredTrades.sort(
      (a, b) =>
        new Date((b.executionTime as string) || 0).getTime() - new Date((a.executionTime as string) || 0).getTime(),
    )

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

  async updateTrade(tradeId: string, updates: Record<string, unknown>) {
    await redis.hset(`trade:${tradeId}`, updates)
    return redis.hgetall(`trade:${tradeId}`)
  },

  async closeTrade(tradeId: string, exitPrice: number, fees = 0) {
    const trade = (await redis.hgetall(`trade:${tradeId}`)) as Record<string, unknown>
    if (!trade) return null

    const entryPrice = Number.parseFloat(trade.entryPrice as string)
    const quantity = Number.parseFloat(trade.quantity as string)
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
    parameters?: Record<string, unknown>
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

  async updateStrategy(strategyId: string, updates: Record<string, unknown>) {
    const newUpdates: Record<string, unknown> = { ...updates, updatedAt: new Date().toISOString() }
    if (newUpdates.parameters && typeof newUpdates.parameters === "object") {
      newUpdates.parameters = JSON.stringify(newUpdates.parameters)
    }
    if (newUpdates.performanceMetrics && typeof newUpdates.performanceMetrics === "object") {
      newUpdates.performanceMetrics = JSON.stringify(newUpdates.performanceMetrics)
    }
    await redis.hset(`strategy:${strategyId}`, newUpdates)
    return redis.hgetall(`strategy:${strategyId}`)
  },

  // Market Data Cache
  async cacheMarketData(symbol: string, data: unknown, ttlSeconds = 60) {
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

  async updatePortfolio(userId: string, updates: Record<string, unknown>) {
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

    const closedTrades = trades.filter((t) => t.status === "closed")
    const openTrades = trades.filter((t) => t.status === "open")

    const totalPnL = closedTrades.reduce((sum, t) => sum + Number.parseFloat((t.pnl as string) || "0"), 0)
    const winningTrades = closedTrades.filter((t) => Number.parseFloat((t.pnl as string) || "0") > 0)
    const winRate = closedTrades.length > 0 ? (winningTrades.length / closedTrades.length) * 100 : 0

    const activeStrategies = strategies.filter(
      (s) => (s as Record<string, unknown>).isActive === "true" || (s as Record<string, unknown>).isActive === true,
    )

    return {
      portfolio: {
        totalPnL,
        dailyPnL: 0,
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
          closedTrades.length > 0
            ? Math.max(...closedTrades.map((t) => Number.parseFloat((t.pnl as string) || "0")))
            : 0,
        worstTrade:
          closedTrades.length > 0
            ? Math.min(...closedTrades.map((t) => Number.parseFloat((t.pnl as string) || "0")))
            : 0,
        avgTradeSize:
          closedTrades.length > 0
            ? closedTrades.reduce(
                (sum, t) =>
                  sum +
                  Number.parseFloat((t.entryPrice as string) || "0") * Number.parseFloat((t.quantity as string) || "0"),
                0,
              ) / closedTrades.length
            : 0,
      },
    }
  },
}

// Export redis for direct access if needed
export { redis }

interface QueryResult<T> {
  data: T | null
  error: Error | null
}

interface QueryBuilder<T = Record<string, unknown>> {
  select: (columns?: string) => QueryBuilder<T>
  insert: (data: T | T[]) => QueryBuilder<T>
  update: (data: Partial<T>) => QueryBuilder<T>
  upsert: (data: T | T[]) => QueryBuilder<T>
  delete: () => QueryBuilder<T>
  eq: (column: string, value: unknown) => QueryBuilder<T>
  neq: (column: string, value: unknown) => QueryBuilder<T>
  gt: (column: string, value: unknown) => QueryBuilder<T>
  gte: (column: string, value: unknown) => QueryBuilder<T>
  lt: (column: string, value: unknown) => QueryBuilder<T>
  lte: (column: string, value: unknown) => QueryBuilder<T>
  or: (query: string) => QueryBuilder<T>
  order: (column: string, options?: { ascending?: boolean }) => QueryBuilder<T>
  limit: (count: number) => QueryBuilder<T>
  range: (from: number, to: number) => QueryBuilder<T>
  single: () => Promise<QueryResult<T>>
  maybeSingle: () => Promise<QueryResult<T | null>>
  then: <TResult>(onfulfilled?: (value: QueryResult<T[]>) => TResult) => Promise<TResult>
}

class RedisQueryBuilder<T = Record<string, unknown>> implements QueryBuilder<T> {
  private tableName: string
  private filters: Array<{ column: string; operator: string; value: unknown }> = []
  private orFilters: string[] = []
  private selectedColumns = "*"
  private orderByColumn: string | null = null
  private orderAscending = true
  private limitCount: number | null = null
  private rangeFrom = 0
  private rangeTo: number | null = null
  private updateData: Partial<T> | null = null
  private insertData: T | T[] | null = null
  private isDelete = false
  private isUpsert = false

  constructor(tableName: string) {
    this.tableName = tableName
  }

  select(columns = "*"): QueryBuilder<T> {
    this.selectedColumns = columns
    return this
  }

  insert(data: T | T[]): QueryBuilder<T> {
    this.insertData = data
    return this
  }

  update(data: Partial<T>): QueryBuilder<T> {
    this.updateData = { ...data, updated_at: new Date().toISOString() } as Partial<T>
    return this
  }

  upsert(data: T | T[]): QueryBuilder<T> {
    this.insertData = data
    this.isUpsert = true
    return this
  }

  delete(): QueryBuilder<T> {
    this.isDelete = true
    return this
  }

  eq(column: string, value: unknown): QueryBuilder<T> {
    this.filters.push({ column, operator: "eq", value })
    return this
  }

  neq(column: string, value: unknown): QueryBuilder<T> {
    this.filters.push({ column, operator: "neq", value })
    return this
  }

  gt(column: string, value: unknown): QueryBuilder<T> {
    this.filters.push({ column, operator: "gt", value })
    return this
  }

  gte(column: string, value: unknown): QueryBuilder<T> {
    this.filters.push({ column, operator: "gte", value })
    return this
  }

  lt(column: string, value: unknown): QueryBuilder<T> {
    this.filters.push({ column, operator: "lt", value })
    return this
  }

  lte(column: string, value: unknown): QueryBuilder<T> {
    this.filters.push({ column, operator: "lte", value })
    return this
  }

  or(query: string): QueryBuilder<T> {
    this.orFilters.push(query)
    return this
  }

  order(column: string, options?: { ascending?: boolean }): QueryBuilder<T> {
    this.orderByColumn = column
    this.orderAscending = options?.ascending ?? true
    return this
  }

  limit(count: number): QueryBuilder<T> {
    this.limitCount = count
    return this
  }

  range(from: number, to: number): QueryBuilder<T> {
    this.rangeFrom = from
    this.rangeTo = to
    return this
  }

  private async executeInsert(): Promise<QueryResult<T>> {
    try {
      const items = Array.isArray(this.insertData) ? this.insertData : [this.insertData]
      const results: T[] = []

      for (const item of items) {
        const record = item as Record<string, unknown>
        const id = record.id || crypto.randomUUID()
        const data = {
          ...record,
          id,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }

        await redis.hset(`${this.tableName}:${id}`, data)
        await redis.sadd(`${this.tableName}:_index`, id)

        // Index common fields
        const indexFields = ["user_id", "email", "username", "status", "symbol", "strategy_id", "created_by"]
        for (const field of indexFields) {
          if (data[field]) {
            await redis.sadd(`${this.tableName}:_idx:${field}:${data[field]}`, id)
          }
        }

        results.push(data as T)
      }

      return {
        data: (Array.isArray(this.insertData) ? results : results[0]) as T,
        error: null,
      }
    } catch (error) {
      return { data: null, error: error as Error }
    }
  }

  private async executeQuery(): Promise<QueryResult<T[]>> {
    try {
      // Handle inserts
      if (this.insertData && !this.isUpsert) {
        const result = await this.executeInsert()
        return {
          data: result.data ? [result.data] : [],
          error: result.error,
        }
      }

      // Handle upserts
      if (this.insertData && this.isUpsert) {
        const items = Array.isArray(this.insertData) ? this.insertData : [this.insertData]
        const results: T[] = []

        for (const item of items) {
          const record = item as Record<string, unknown>
          const id = record.id || crypto.randomUUID()
          const existing = await redis.hgetall(`${this.tableName}:${id}`)
          const data = {
            ...existing,
            ...record,
            id,
            updated_at: new Date().toISOString(),
            created_at: (existing as Record<string, unknown>)?.created_at || new Date().toISOString(),
          }

          await redis.hset(`${this.tableName}:${id}`, data)
          await redis.sadd(`${this.tableName}:_index`, id)
          results.push(data as T)
        }

        return { data: results, error: null }
      }

      // Handle updates
      if (this.updateData && this.filters.length > 0) {
        const idsToUpdate = await this.getFilteredIds()
        const results: T[] = []

        for (const id of idsToUpdate) {
          const existing = await redis.hgetall(`${this.tableName}:${id}`)
          if (existing) {
            const updated = { ...existing, ...this.updateData }
            await redis.hset(`${this.tableName}:${id}`, updated as Record<string, unknown>)
            results.push(updated as T)
          }
        }

        return { data: results, error: null }
      }

      // Handle deletes
      if (this.isDelete && this.filters.length > 0) {
        const idsToDelete = await this.getFilteredIds()

        for (const id of idsToDelete) {
          await redis.del(`${this.tableName}:${id}`)
          await redis.srem(`${this.tableName}:_index`, id)
        }

        return { data: [], error: null }
      }

      // Handle selects
      const ids = await this.getFilteredIds()
      let results: T[] = []

      for (const id of ids) {
        const record = await redis.hgetall(`${this.tableName}:${id}`)
        if (record && Object.keys(record).length > 0) {
          results.push(record as T)
        }
      }

      // Apply additional filters
      results = this.applyFilters(results)

      // Apply OR filters
      if (this.orFilters.length > 0) {
        results = this.applyOrFilters(results)
      }

      // Apply ordering
      if (this.orderByColumn) {
        results.sort((a, b) => {
          const aVal = (a as Record<string, unknown>)[this.orderByColumn!]
          const bVal = (b as Record<string, unknown>)[this.orderByColumn!]

          if (aVal === bVal) return 0
          if (aVal === null || aVal === undefined) return 1
          if (bVal === null || bVal === undefined) return -1

          const comparison = aVal < bVal ? -1 : 1
          return this.orderAscending ? comparison : -comparison
        })
      }

      // Apply range/limit
      if (this.rangeTo !== null) {
        results = results.slice(this.rangeFrom, this.rangeTo + 1)
      } else if (this.limitCount !== null) {
        results = results.slice(0, this.limitCount)
      }

      return { data: results, error: null }
    } catch (error) {
      console.error(`[Redis Query Error] ${this.tableName}:`, error)
      return { data: [], error: error as Error }
    }
  }

  private async getFilteredIds(): Promise<string[]> {
    for (const filter of this.filters) {
      if (filter.operator === "eq") {
        if (filter.column === "id") {
          return [filter.value as string]
        }

        const indexedFields = ["user_id", "email", "username", "status", "symbol", "strategy_id", "created_by"]
        if (indexedFields.includes(filter.column)) {
          const indexedIds = await redis.smembers(`${this.tableName}:_idx:${filter.column}:${filter.value}`)
          if (indexedIds.length > 0) {
            return indexedIds as string[]
          }
        }
      }
    }

    const allIds = await redis.smembers(`${this.tableName}:_index`)
    return allIds as string[]
  }

  private applyFilters(records: T[]): T[] {
    return records.filter((record) => {
      return this.filters.every((filter) => {
        const value = (record as Record<string, unknown>)[filter.column]

        switch (filter.operator) {
          case "eq":
            return value === filter.value || String(value) === String(filter.value)
          case "neq":
            return value !== filter.value
          case "gt":
            return value !== null && value !== undefined && Number(value) > Number(filter.value)
          case "gte":
            return value !== null && value !== undefined && Number(value) >= Number(filter.value)
          case "lt":
            return value !== null && value !== undefined && Number(value) < Number(filter.value)
          case "lte":
            return value !== null && value !== undefined && Number(value) <= Number(filter.value)
          default:
            return true
        }
      })
    })
  }

  private applyOrFilters(records: T[]): T[] {
    if (this.orFilters.length === 0) return records

    return records.filter((record) => {
      return this.orFilters.some((orQuery) => {
        // Parse OR query like "username.eq.john,email.eq.john@example.com"
        const conditions = orQuery.split(",")
        return conditions.some((condition) => {
          const parts = condition.split(".")
          if (parts.length >= 3) {
            const column = parts[0]
            const operator = parts[1]
            const value = parts.slice(2).join(".")
            const recordValue = (record as Record<string, unknown>)[column]

            if (operator === "eq") {
              return recordValue === value || String(recordValue) === value
            }
          }
          return false
        })
      })
    })
  }

  async single(): Promise<QueryResult<T>> {
    const result = await this.executeQuery()
    if (result.error) {
      return { data: null, error: result.error }
    }
    if (!result.data || result.data.length === 0) {
      return { data: null, error: new Error("No rows returned") }
    }
    return { data: result.data[0], error: null }
  }

  async maybeSingle(): Promise<QueryResult<T | null>> {
    const result = await this.executeQuery()
    if (result.error) {
      return { data: null, error: result.error }
    }
    return { data: result.data?.[0] || null, error: null }
  }

  then<TResult>(onfulfilled?: (value: QueryResult<T[]>) => TResult): Promise<TResult> {
    return this.executeQuery().then(onfulfilled!)
  }
}

// Supabase-compatible client using Redis
export const supabase = {
  from: <T = Record<string, unknown>>(table: string): QueryBuilder<T> => {
    return new RedisQueryBuilder<T>(table)
  },
}
