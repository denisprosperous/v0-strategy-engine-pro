import { type NextRequest, NextResponse } from "next/server"
import { TradingMLModels } from "@/lib/ai/ml-models"
import { AdaptiveLearningEngine } from "@/lib/ai/adaptive-learning"
import { authMiddleware } from "@/lib/auth/middleware"

export async function POST(request: NextRequest) {
  try {
    const authResult = await authMiddleware(request)
    if (!authResult.success) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { signalData, portfolioValue, riskTolerance } = await request.json()

    const mlModels = new TradingMLModels()
    const learningEngine = new AdaptiveLearningEngine()

    // Get ML predictions and position sizing
    const [prediction, positionSize] = await Promise.all([
      mlModels.predictTradeOutcome(signalData),
      mlModels.optimizePositionSize(signalData, portfolioValue, riskTolerance),
    ])

    return NextResponse.json({
      prediction,
      positionSize,
      timestamp: new Date().toISOString(),
    })
  } catch (error) {
    console.error("[v0] AI optimization error:", error)
    return NextResponse.json({ error: "Optimization failed" }, { status: 500 })
  }
}
