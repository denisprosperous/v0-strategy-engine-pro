// API endpoint to start a trading strategy
import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { supabase } from "@/lib/config/database"
import { logger } from "@/lib/utils/logger"

async function startStrategyHandler(req: AuthenticatedRequest) {
  try {
    const { strategyId } = await req.json()

    if (!req.user) {
      return NextResponse.json({ error: "User not authenticated" }, { status: 401 })
    }

    if (!strategyId) {
      return NextResponse.json({ error: "Strategy ID is required" }, { status: 400 })
    }

    // Check if strategy exists and belongs to user
    const { data: strategy, error: strategyError } = await supabase
      .from("strategies")
      .select("*")
      .eq("id", strategyId)
      .eq("created_by", req.user.userId)
      .single()

    if (strategyError || !strategy) {
      return NextResponse.json({ error: "Strategy not found" }, { status: 404 })
    }

    // Update strategy status to active
    const { data: updatedStrategy, error: updateError } = await supabase
      .from("strategies")
      .update({
        is_active: true,
        updated_at: new Date().toISOString(),
      })
      .eq("id", strategyId)
      .select()
      .single()

    if (updateError) {
      throw updateError
    }

    // Log strategy start
    logger.info("Strategy started", {
      strategyId,
      userId: req.user.userId,
      strategyName: strategy.name,
    })

    return NextResponse.json({
      success: true,
      message: `Strategy "${strategy.name}" started successfully`,
      strategy: updatedStrategy,
    })
  } catch (error) {
    logger.error("Failed to start strategy", { error, userId: req.user?.userId })
    return NextResponse.json({ error: "Failed to start strategy" }, { status: 500 })
  }
}

export const POST = withAuth(startStrategyHandler)
