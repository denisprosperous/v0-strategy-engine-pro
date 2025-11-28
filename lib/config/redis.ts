// Upstash Redis client (HTTP-based)
import { Redis } from "@upstash/redis"

const url = process.env.UPSTASH_REDIS_REST_URL || process.env.REDIS_URL
const token = process.env.UPSTASH_REDIS_REST_TOKEN || process.env.REDIS_TOKEN

export const redis = url && token ? new Redis({ url, token }) : null

export function assertRedis() {
  if (!redis) throw new Error("Upstash Redis not configured; set UPSTASH_REDIS_REST_URL and token")
  return redis
}
