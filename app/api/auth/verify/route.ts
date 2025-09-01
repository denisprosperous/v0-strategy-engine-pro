// Token verification API endpoint
import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { supabaseServer } from "@/lib/config/supabase-server"
import { logger } from "@/lib/utils/logger"

async function verifyHandler(req: AuthenticatedRequest) {
  try {
    if (!req.user) {
      return NextResponse.json({ error: "No user found in request" }, { status: 401 })
    }

    // Fetch fresh user data from database
    const { data: user, error } = await supabaseServer
      .from("users")
      .select("id, username, email, role, telegram_id, settings")
      .eq("id", req.user.userId)
      .single()

    if (error || !user) {
      logger.warn("Token verification failed - user not found", { userId: req.user.userId })
      return NextResponse.json({ error: "User not found" }, { status: 404 })
    }

    return NextResponse.json({
      success: true,
      user: {
        id: user.id,
        username: user.username,
        email: user.email,
        role: user.role,
        telegramId: user.telegram_id,
        settings: user.settings,
      },
    })
  } catch (error) {
    logger.error("Token verification error", { error })
    return NextResponse.json({ error: "Verification failed" }, { status: 500 })
  }
}

export const GET = withAuth(verifyHandler)
