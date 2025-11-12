// User registration API endpoint
import { type NextRequest, NextResponse } from "next/server"
import { supabaseServer } from "@/lib/config/supabase-server"
import { hashPassword, validatePassword } from "@/lib/auth/password"
import { signToken } from "@/lib/auth/jwt"
import { withRateLimit } from "@/lib/auth/middleware"
import { logger } from "@/lib/utils/logger"

interface RegisterRequest {
  username: string
  email: string
  password: string
  telegramId?: string
}

async function registerHandler(req: NextRequest) {
  try {
    const body: RegisterRequest = await req.json()
    const { username, email, password, telegramId } = body

    // Validate input
    if (!username || !email || !password) {
      return NextResponse.json({ error: "Username, email, and password are required" }, { status: 400 })
    }

    // Validate password strength
    const passwordValidation = validatePassword(password)
    if (!passwordValidation.valid) {
      return NextResponse.json(
        { error: "Password validation failed", details: passwordValidation.errors },
        { status: 400 },
      )
    }

    // Check if user already exists
    const { data: existingUser } = await supabaseServer
      .from("users")
      .select("id")
      .or(`username.eq.${username},email.eq.${email}`)
      .single()

    if (existingUser) {
      return NextResponse.json({ error: "Username or email already exists" }, { status: 409 })
    }

    // Hash password and create user
    const passwordHash = await hashPassword(password)

    const { data: newUser, error } = await supabaseServer
      .from("users")
      .insert({
        username,
        email,
        password_hash: passwordHash,
        telegram_id: telegramId,
        role: "trader", // Default role
      })
      .select("id, username, email, role")
      .single()

    if (error) {
      logger.error("User registration failed", { error, username, email })
      return NextResponse.json({ error: "Registration failed" }, { status: 500 })
    }

    // Generate JWT token
    const token = await signToken({
      userId: newUser.id,
      username: newUser.username,
      email: newUser.email,
      role: newUser.role,
    })

    logger.info("User registered successfully", { userId: newUser.id, username })

    const res = NextResponse.json({
      success: true,
      token,
      user: {
        id: newUser.id,
        username: newUser.username,
        email: newUser.email,
        role: newUser.role,
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
    logger.error("Registration endpoint error", { error })
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export const POST = withRateLimit(5, 15 * 60 * 1000)(registerHandler) // 5 requests per 15 minutes
