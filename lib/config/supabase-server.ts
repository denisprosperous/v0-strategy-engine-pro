import { Redis } from "@upstash/redis"

// Initialize Redis client
const redis = new Redis({
  url: process.env.UPSTASH_KV_KV_REST_API_URL || process.env.KV_REST_API_URL || "",
  token: process.env.UPSTASH_KV_KV_REST_API_TOKEN || process.env.KV_REST_API_TOKEN || "",
})

// Query result interface
interface QueryResult<T> {
  data: T | null
  error: Error | null
}

// Query builder that mimics Supabase API
class RedisQueryBuilder<T = Record<string, unknown>> {
  private tableName: string
  private filters: Array<{ column: string; operator: string; value: unknown }> = []
  private orFilters: string[] = []
  private orderByColumn: string | null = null
  private orderAscending = true
  private limitCount: number | null = null
  private updateData: Partial<T> | null = null
  private insertData: T | T[] | null = null
  private isDelete = false

  constructor(tableName: string) {
    this.tableName = tableName
  }

  select(_columns = "*") {
    return this
  }

  insert(data: T | T[]) {
    this.insertData = data
    return this
  }

  update(data: Partial<T>) {
    this.updateData = { ...data, updated_at: new Date().toISOString() } as Partial<T>
    return this
  }

  upsert(data: T | T[]) {
    this.insertData = data
    return this
  }

  delete() {
    this.isDelete = true
    return this
  }

  eq(column: string, value: unknown) {
    this.filters.push({ column, operator: "eq", value })
    return this
  }

  neq(column: string, value: unknown) {
    this.filters.push({ column, operator: "neq", value })
    return this
  }

  gt(column: string, value: unknown) {
    this.filters.push({ column, operator: "gt", value })
    return this
  }

  gte(column: string, value: unknown) {
    this.filters.push({ column, operator: "gte", value })
    return this
  }

  lt(column: string, value: unknown) {
    this.filters.push({ column, operator: "lt", value })
    return this
  }

  lte(column: string, value: unknown) {
    this.filters.push({ column, operator: "lte", value })
    return this
  }

  or(query: string) {
    this.orFilters.push(query)
    return this
  }

  order(column: string, options?: { ascending?: boolean }) {
    this.orderByColumn = column
    this.orderAscending = options?.ascending ?? true
    return this
  }

  limit(count: number) {
    this.limitCount = count
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
      if (this.insertData) {
        const result = await this.executeInsert()
        return { data: result.data ? [result.data] : [], error: result.error }
      }

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

      if (this.isDelete && this.filters.length > 0) {
        const idsToDelete = await this.getFilteredIds()
        for (const id of idsToDelete) {
          await redis.del(`${this.tableName}:${id}`)
          await redis.srem(`${this.tableName}:_index`, id)
        }
        return { data: [], error: null }
      }

      const ids = await this.getFilteredIds()
      let results: T[] = []

      for (const id of ids) {
        const record = await redis.hgetall(`${this.tableName}:${id}`)
        if (record && Object.keys(record).length > 0) {
          results.push(record as T)
        }
      }

      results = this.applyFilters(results)
      if (this.orFilters.length > 0) {
        results = this.applyOrFilters(results)
      }

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

      if (this.limitCount !== null) {
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
        if (filter.column === "id") return [filter.value as string]
        const indexedFields = ["user_id", "email", "username", "status", "symbol", "strategy_id", "created_by"]
        if (indexedFields.includes(filter.column)) {
          const indexedIds = await redis.smembers(`${this.tableName}:_idx:${filter.column}:${filter.value}`)
          if (indexedIds.length > 0) return indexedIds as string[]
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
            return value !== null && Number(value) > Number(filter.value)
          case "gte":
            return value !== null && Number(value) >= Number(filter.value)
          case "lt":
            return value !== null && Number(value) < Number(filter.value)
          case "lte":
            return value !== null && Number(value) <= Number(filter.value)
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
        const conditions = orQuery.split(",")
        return conditions.some((condition) => {
          const parts = condition.split(".")
          if (parts.length >= 3) {
            const column = parts[0]
            const operator = parts[1]
            const value = parts.slice(2).join(".")
            const recordValue = (record as Record<string, unknown>)[column]
            if (operator === "eq") return recordValue === value || String(recordValue) === value
          }
          return false
        })
      })
    })
  }

  async single(): Promise<QueryResult<T>> {
    const result = await this.executeQuery()
    if (result.error) return { data: null, error: result.error }
    if (!result.data || result.data.length === 0) return { data: null, error: new Error("No rows returned") }
    return { data: result.data[0], error: null }
  }

  async maybeSingle(): Promise<QueryResult<T | null>> {
    const result = await this.executeQuery()
    if (result.error) return { data: null, error: result.error }
    return { data: result.data?.[0] || null, error: null }
  }

  then<TResult>(onfulfilled?: (value: QueryResult<T[]>) => TResult): Promise<TResult> {
    return this.executeQuery().then(onfulfilled!)
  }
}

// Supabase-compatible server client backed by Redis
class RedisSupabaseServer {
  from<T = Record<string, unknown>>(table: string): RedisQueryBuilder<T> {
    return new RedisQueryBuilder<T>(table)
  }
}

export const supabaseServer = new RedisSupabaseServer()
export default supabaseServer
