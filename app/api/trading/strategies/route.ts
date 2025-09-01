// API endpoints for strategy management
import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { supabaseServer } from "@/lib/config/supabase-server"
import { logger } from "@/lib/utils/logger"

// Get all strategies
async function getStrategiesHandler(req: AuthenticatedRequest) {
  try {
    const { data: strategies, error } = await supabaseServer
      .from("strategies")
      .select("*")
      .eq("is_active", true)
      .order("created_at", { ascending: false })

    if (error) throw error

    return NextResponse.json({ strategies })
  } catch (error) {
    logger.error("Failed to fetch strategies", { error })
    return NextResponse.json({ error: "Failed to fetch strategies" }, { status: 500 })
  }
}

// Create or update strategy
async function manageStrategyHandler(req: AuthenticatedRequest) {
  try {
    const body = await req.json()
    const { id, name, description, type, parameters, is_active } = body

    if (!req.user) {
      return NextResponse.json({ error: "User not authenticated" }, { status: 401 })
    }

    if (id) {
      // Update existing strategy
      const { data: strategy, error } = await supabaseServer
        .from("strategies")
        .update({
          name,
          description,
          type,
          parameters,
          is_active,
          updated_at: new Date().toISOString(),
        })
        .eq("id", id)
        .eq("created_by", req.user.userId) // Ensure user owns the strategy
        .select()
        .single()

      if (error) throw error

      logger.info("Strategy updated", { strategyId: id, userId: req.user.userId })
      return NextResponse.json({ success: true, strategy })
    } else {
      // Create new strategy
      const { data: strategy, error } = await supabaseServer
        .from("strategies")
        .insert({
          name,
          description,
          type,
          parameters,
          is_active: is_active ?? true,
          created_by: req.user.userId,
        })
        .select()
        .single()

      if (error) throw error

      logger.info("Strategy created", { strategyId: strategy.id, userId: req.user.userId })
      return NextResponse.json({ success: true, strategy })
    }
  } catch (error) {
    logger.error("Strategy management failed", { error })
    return NextResponse.json({ error: "Strategy management failed" }, { status: 500 })
  }
}

export const GET = withAuth(getStrategiesHandler)
export const POST = withAuth(manageStrategyHandler)
