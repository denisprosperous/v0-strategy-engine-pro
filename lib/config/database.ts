import { Redis } from "@upstash/redis"
import crypto from "crypto"

const redisUrl =
  process.env.UPSTASH_KV_KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL || process.env.KV_REST_API_URL || ""
const redisToken =
  process.env.UPSTASH_KV_KV_REST_API_TOKEN ||
  process.env.UPSTASH_REDIS_REST_TOKEN ||
  process.env.KV_REST_API_TOKEN ||
  ""

// Create Redis client only if credentials are available
const redis = redisUrl && redisToken ? new Redis({ url: redisUrl, token: redisToken }) : null

// Log Redis connection status (only in development)
if (process.env.NODE_ENV === "development") {
  console.log("[v0] Redis configured:", !!redis)
}

// Data access layer that uses Redis for persistence
export const db = {
  // Users
  async getUser(userId: string) {
    if (!redis) return null
    const user = await redis.hgetall(`user:${userId}`)
    return user && Object.keys(user).length > 0 ? user : null
  },

  async getUserByUsername(username: string) {
    if (!redis) return null
    const userId = await redis.get(`username:${username}`)
    if (!userId) return null
    return this.getUser(userId as string)
  },

  async getUserByEmail(email: string) {
    if (!redis) return null
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
    if (!redis) throw new Error("Database not configured")
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
    if (!redis) throw new Error("Database not configured")
    const updateData = {
      ...updates,
      updatedAt: new Date().toISOString(),
    }
    await redis.hset(`user:${userId}`, updateData)
    return this.getUser(userId)
  },

  // Trades
  async createTrade(trade: {
    id: string
    userId: string
    symbol: string
    side: string
    quantity: number
    price: number
    exchange: string
    strategyId?: string
    status?: string
  }) {
    if (!redis) throw new Error("Database not configured")
    const tradeData = {
      ...trade,
      status: trade.status || "open",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    await redis.hset(`trade:${trade.id}`, tradeData)
    await redis.lpush(`user:${trade.userId}:trades`, trade.id)
    await redis.lpush("trades:all", trade.id)
    return tradeData
  },

  async getTrade(tradeId: string) {
    if (!redis) return null
    const trade = await redis.hgetall(`trade:${tradeId}`)
    return trade && Object.keys(trade).length > 0 ? trade : null
  },

  async getUserTrades(userId: string, limit = 50) {
    if (!redis) return []
    const tradeIds = await redis.lrange(`user:${userId}:trades`, 0, limit - 1)
    const trades = await Promise.all(tradeIds.map((id) => this.getTrade(id as string)))
    return trades.filter(Boolean)
  },

  async updateTrade(tradeId: string, updates: Record<string, unknown>) {
    if (!redis) throw new Error("Database not configured")
    const updateData = {
      ...updates,
      updatedAt: new Date().toISOString(),
    }
    await redis.hset(`trade:${tradeId}`, updateData)
    return this.getTrade(tradeId)
  },

  // Strategies
  async createStrategy(strategy: {
    id: string
    userId: string
    name: string
    type: string
    config: Record<string, unknown>
  }) {
    if (!redis) throw new Error("Database not configured")
    const strategyData = {
      ...strategy,
      config: JSON.stringify(strategy.config),
      enabled: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    await redis.hset(`strategy:${strategy.id}`, strategyData)
    await redis.lpush(`user:${strategy.userId}:strategies`, strategy.id)
    return strategyData
  },

  async getStrategy(strategyId: string) {
    if (!redis) return null
    const strategy = await redis.hgetall(`strategy:${strategyId}`)
    if (!strategy || Object.keys(strategy).length === 0) return null
    return {
      ...strategy,
      config: typeof strategy.config === "string" ? JSON.parse(strategy.config) : strategy.config,
    }
  },

  async getUserStrategies(userId: string) {
    if (!redis) return []
    const strategyIds = await redis.lrange(`user:${userId}:strategies`, 0, -1)
    const strategies = await Promise.all(strategyIds.map((id) => this.getStrategy(id as string)))
    return strategies.filter(Boolean)
  },

  async updateStrategy(strategyId: string, updates: Record<string, unknown>) {
    if (!redis) throw new Error("Database not configured")
    const updateData = {
      ...updates,
      config: updates.config ? JSON.stringify(updates.config) : undefined,
      updatedAt: new Date().toISOString(),
    }
    // Remove undefined values
    Object.keys(updateData).forEach((key) => updateData[key] === undefined && delete updateData[key])
    await redis.hset(`strategy:${strategyId}`, updateData)
    return this.getStrategy(strategyId)
  },

  // Analytics
  async recordAnalytics(userId: string, data: Record<string, unknown>) {
    if (!redis) return null
    const analyticsData = {
      ...data,
      userId,
      timestamp: new Date().toISOString(),
    }
    const key = `analytics:${userId}:${Date.now()}`
    await redis.hset(key, analyticsData)
    await redis.lpush(`user:${userId}:analytics`, key)
    await redis.expire(key, 60 * 60 * 24 * 30) // 30 days TTL
    return analyticsData
  },

  async getAnalytics(userId: string, limit = 100) {
    if (!redis) return []
    const keys = await redis.lrange(`user:${userId}:analytics`, 0, limit - 1)
    const analytics = await Promise.all(keys.map((key) => redis.hgetall(key as string)))
    return analytics.filter((a) => a && Object.keys(a).length > 0)
  },

  // Signals (from analysis jobs)
  async getLatestSignals() {
    if (!redis) return {}
    return (await redis.hgetall("signals:latest")) || {}
  },

  async getSignalsForSymbol(symbol: string, limit = 20) {
    if (!redis) return []
    const signals = await redis.zrange(`signals:${symbol}`, -limit, -1)
    return signals.map((s) => (typeof s === "string" ? JSON.parse(s) : s))
  },

  // Market data
  async getMarketPrices() {
    if (!redis) return {}
    return (await redis.hgetall("market:prices")) || {}
  },

  async getLastAnalysisRun() {
    if (!redis) return null
    return await redis.get("analysis:lastRun")
  },

  // Health check
  async healthCheck() {
    if (!redis) return { status: "disconnected", error: "Redis not configured" }
    try {
      await redis.ping()
      return { status: "connected" }
    } catch (error) {
      return { status: "error", error: (error as Error).message }
    }
  },

  // Check if Redis is available
  isConnected() {
    return !!redis
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
