// User login API endpoint
import { type NextRequest, NextResponse } from "next/server"
import { supabase } from "@/lib/config/database"
import { verifyPassword } from "@/lib/auth/password"
import { signToken } from "@/lib/auth/jwt"
import { withRateLimit } from "@/lib/auth/middleware"
import { logger } from "@/lib/utils/logger"

interface LoginRequest {
  username: string
  password: string
}

async function loginHandler(req: NextRequest) {
  try {
    const body: LoginRequest = await req.json()
    const { username, password } = body

    // Validate input
    if (!username || !password) {
      return NextResponse.json({ error: "Username and password are required" }, { status: 400 })
    }

    // Find user by username or email
    const { data: user, error } = await supabase
      .from("users")
      .select("id, username, email, password_hash, role, telegram_id")
      .or(`username.eq.${username},email.eq.${username}`)
      .single()

    if (error || !user) {
      logger.warn("Login attempt with invalid username", { username })
      return NextResponse.json({ error: "Invalid credentials" }, { status: 401 })
    }

    // Verify password
    const isValidPassword = await verifyPassword(password, user.password_hash)
    if (!isValidPassword) {
      logger.warn("Login attempt with invalid password", { userId: user.id, username })
      return NextResponse.json({ error: "Invalid credentials" }, { status: 401 })
    }

    // Generate JWT token
    const token = signToken({
      userId: user.id,
      username: user.username,
      email: user.email,
      role: user.role,
    })

    // Update last login timestamp
    await supabase.from("users").update({ updated_at: new Date().toISOString() }).eq("id", user.id)

    logger.info("User logged in successfully", { userId: user.id, username: user.username })

    return NextResponse.json({
      success: true,
      token,
      user: {
        id: user.id,
        username: user.username,
        email: user.email,
        role: user.role,
        telegramId: user.telegram_id,
      },
    })
  } catch (error) {
    logger.error("Login endpoint error", { error })
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export const POST = withRateLimit(10, 15 * 60 * 1000)(loginHandler) // 10 requests per 15 minutes
