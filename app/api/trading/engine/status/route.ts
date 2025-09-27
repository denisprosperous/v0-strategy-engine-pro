// API endpoint to get trading engine status
import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"

// Import the global engine instances
declare global {
  var userEngines: Map<string, any>
}

async function getEngineStatusHandler(req: AuthenticatedRequest) {
  try {
    if (!req.user) {
      return NextResponse.json({ error: "User not authenticated" }, { status: 401 })
    }

    // Get engine instance for this user
    const engine = global.userEngines?.get(req.user.userId)

    if (!engine) {
      return NextResponse.json({
        isRunning: false,
        message: "No trading engine running",
      })
    }

    const status = engine.getStatus()

    return NextResponse.json({
      success: true,
      status,
    })
  } catch (error) {
    return NextResponse.json({ error: "Failed to get engine status" }, { status: 500 })
  }
}

export const GET = withAuth(getEngineStatusHandler)
