// API endpoint to stop the live trading engine
import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { logger } from "@/lib/utils/logger"

// Import the global engine instances
declare global {
  var userEngines: Map<string, any>
}

async function stopEngineHandler(req: AuthenticatedRequest) {
  try {
    if (!req.user) {
      return NextResponse.json({ error: "User not authenticated" }, { status: 401 })
    }

    // Get engine instance for this user
    const engine = global.userEngines?.get(req.user.userId)

    if (!engine) {
      return NextResponse.json({ error: "No trading engine running" }, { status: 400 })
    }

    // Stop the engine
    await engine.stop()

    // Remove from global instances
    global.userEngines?.delete(req.user.userId)

    logger.info("Live trading engine stopped", { userId: req.user.userId })

    return NextResponse.json({
      success: true,
      message: "Live trading engine stopped successfully",
    })
  } catch (error) {
    logger.error("Failed to stop trading engine", { error, userId: req.user?.userId })
    return NextResponse.json({ error: "Failed to stop trading engine" }, { status: 500 })
  }
}

export const POST = withAuth(stopEngineHandler)
