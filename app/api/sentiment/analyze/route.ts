// API endpoint for sentiment analysis
import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { sentimentAnalyzer } from "@/lib/sentiment/analyzer"
import { logger } from "@/lib/utils/logger"

async function getSentimentHandler(req: AuthenticatedRequest) {
  try {
    const { searchParams } = new URL(req.url)
    const symbol = searchParams.get("symbol")

    if (!symbol) {
      return NextResponse.json({ error: "Symbol parameter is required" }, { status: 400 })
    }

    const sentiment = await sentimentAnalyzer.getSentiment(symbol)

    return NextResponse.json({
      symbol,
      sentiment: sentiment.score,
      confidence: sentiment.confidence,
      sources: sentiment.sources,
      timestamp: sentiment.timestamp,
      interpretation: this.interpretSentiment(sentiment.score),
    })
  } catch (error) {
    logger.error("Sentiment analysis failed", { error })
    return NextResponse.json({ error: "Failed to analyze sentiment" }, { status: 500 })
  }
}

function interpretSentiment(score: number): string {
  if (score > 0.3) return "Very Bullish"
  if (score > 0.1) return "Bullish"
  if (score > -0.1) return "Neutral"
  if (score > -0.3) return "Bearish"
  return "Very Bearish"
}

export const GET = withAuth(getSentimentHandler)
