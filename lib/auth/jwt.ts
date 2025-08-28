// JWT token utilities for authentication
import jwt from "jsonwebtoken"
import { config } from "@/lib/config/environment"

export interface JWTPayload {
  userId: string
  username: string
  email: string
  role: "admin" | "trader" | "viewer"
  iat?: number
  exp?: number
}

function getJWTSecret(): string {
  const secret = config.auth.jwtSecret
  if (!secret || secret === "your-super-secret-jwt-key") {
    throw new Error("JWT_SECRET environment variable is required and must be set to a secure value")
  }
  return secret
}

export function signToken(payload: Omit<JWTPayload, "iat" | "exp">): string {
  try {
    return jwt.sign(payload, getJWTSecret(), {
      expiresIn: config.auth.jwtExpiry,
    })
  } catch (error) {
    console.error("[v0] JWT signing error:", error)
    throw new Error("Failed to sign JWT token")
  }
}

export function verifyToken(token: string): JWTPayload | null {
  try {
    if (!token) {
      return null
    }
    const decoded = jwt.verify(token, getJWTSecret()) as JWTPayload
    return decoded
  } catch (error) {
    console.error("[v0] JWT verification error:", error)
    return null
  }
}

export function extractTokenFromHeader(authHeader: string | null): string | null {
  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    return null
  }
  return authHeader.substring(7)
}
