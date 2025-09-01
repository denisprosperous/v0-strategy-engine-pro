// User login API endpoint
import { type NextRequest, NextResponse } from "next/server"
import { supabaseServer } from "@/lib/config/supabase-server"
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
    const { data: user, error } = await supabaseServer
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
    await supabaseServer.from("users").update({ updated_at: new Date().toISOString() }).eq("id", user.id)

    logger.info("User logged in successfully", { userId: user.id, username: user.username })

    const res = NextResponse.json({
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

    // Set HttpOnly auth cookie for middleware-protected routes
    res.cookies.set("auth-token", token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24, // 1 day
    })

    return res
  } catch (error) {
    logger.error("Login endpoint error", { error })
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export const POST = withRateLimit(10, 15 * 60 * 1000)(loginHandler) // 10 requests per 15 minutes
