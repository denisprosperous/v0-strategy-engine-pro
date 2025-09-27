// JWT token utilities for authentication - Edge Runtime compatible
import { SignJWT, jwtVerify } from "jose"
import { config } from "@/lib/config/environment"

export interface JWTPayload {
  userId: string
  username: string
  email: string
  role: "admin" | "trader" | "viewer"
  iat?: number
  exp?: number
}

function getJWTSecret(): Uint8Array {
  const secret = config.auth.jwtSecret
  if (!secret || secret === "your-super-secret-jwt-key") {
    throw new Error("JWT_SECRET environment variable is required and must be set to a secure value")
  }
  return new TextEncoder().encode(secret)
}

export async function signToken(payload: Omit<JWTPayload, "iat" | "exp">): Promise<string> {
  try {
    const jwt = await new SignJWT(payload)
      .setProtectedHeader({ alg: "HS256" })
      .setIssuedAt()
      .setExpirationTime(config.auth.jwtExpiry)
      .sign(getJWTSecret())

    return jwt
  } catch (error) {
    console.error("[v0] JWT signing error:", error)
    throw new Error("Failed to sign JWT token")
  }
}

export async function verifyToken(token: string): Promise<JWTPayload | null> {
  try {
    if (!token) {
      return null
    }

    const { payload } = await jwtVerify(token, getJWTSecret())
    return payload as JWTPayload
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
