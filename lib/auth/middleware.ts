// Authentication middleware for API routes
import { type NextRequest, NextResponse } from "next/server"
import { verifyToken, extractTokenFromHeader, type JWTPayload } from "./jwt"
import { logger } from "@/lib/utils/logger"

export interface AuthenticatedRequest extends NextRequest {
  user?: JWTPayload
}

export function withAuth(handler: (req: AuthenticatedRequest) => Promise<NextResponse>) {
  return async (req: AuthenticatedRequest): Promise<NextResponse> => {
    try {
      const authHeader = req.headers.get("authorization")
      const token = extractTokenFromHeader(authHeader)

      if (!token) {
        return NextResponse.json({ error: "Authentication required" }, { status: 401 })
      }

      const user = await verifyToken(token)
      if (!user) {
        return NextResponse.json({ error: "Invalid or expired token" }, { status: 401 })
      }

      req.user = user
      return handler(req)
    } catch (error) {
      logger.error("Authentication middleware error", { error })
      return NextResponse.json({ error: "Authentication failed" }, { status: 500 })
    }
  }
}

export function withRole(roles: string[]) {
  return (handler: (req: AuthenticatedRequest) => Promise<NextResponse>) =>
    withAuth(async (req: AuthenticatedRequest): Promise<NextResponse> => {
      if (!req.user || !roles.includes(req.user.role)) {
        return NextResponse.json({ error: "Insufficient permissions" }, { status: 403 })
      }

      return handler(req)
    })
}

// Rate limiting middleware
const rateLimitMap = new Map<string, { count: number; resetTime: number }>()

export function withRateLimit(maxRequests = 100, windowMs: number = 15 * 60 * 1000) {
  return (handler: (req: NextRequest) => Promise<NextResponse>) =>
    async (req: NextRequest): Promise<NextResponse> => {
      const ip = req.ip || req.headers.get("x-forwarded-for") || "unknown"
      const now = Date.now()
      const windowStart = now - windowMs

      // Clean up old entries
      for (const [key, value] of rateLimitMap.entries()) {
        if (value.resetTime < windowStart) {
          rateLimitMap.delete(key)
        }
      }

      const current = rateLimitMap.get(ip) || { count: 0, resetTime: now + windowMs }

      if (current.count >= maxRequests && current.resetTime > now) {
        return NextResponse.json({ error: "Rate limit exceeded" }, { status: 429 })
      }

      current.count++
      rateLimitMap.set(ip, current)

      return handler(req)
    }
}

export async function authMiddleware(req: NextRequest): Promise<{
  success: boolean
  user?: JWTPayload
  error?: string
}> {
  try {
    const authHeader = req.headers.get("authorization")
    const token = extractTokenFromHeader(authHeader)

    if (!token) {
      return { success: false, error: "Authentication required" }
    }

    const user = await verifyToken(token)
    if (!user) {
      return { success: false, error: "Invalid or expired token" }
    }

    return { success: true, user }
  } catch (error) {
    logger.error("Authentication middleware error", { error })
    return { success: false, error: "Authentication failed" }
  }
}
