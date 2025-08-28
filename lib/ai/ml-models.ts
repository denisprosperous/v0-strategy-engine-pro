import { openai } from "@ai-sdk/openai"
import { generateObject, generateText } from "ai"
import { z } from "zod"
import { config } from "@/lib/config/environment"

export class TradingMLModels {
  private openaiClient = openai(config.ai.openaiApiKey)

  async predictTradeOutcome(signalData: any): Promise<{
    probability: number
    confidence: number
    reasoning: string
  }> {
    try {
      const { object } = await generateObject({
        model: this.openaiClient("gpt-4"),
        schema: z.object({
          probability: z.number().min(0).max(1),
          confidence: z.number().min(0).max(1),
          reasoning: z.string(),
        }),
        prompt: `Analyze this trading signal and predict the probability of a profitable outcome:
        
        Token: ${signalData.tokenName} (${signalData.tokenSymbol})
        Market Cap: $${signalData.marketCap}
        Smart Money Wallet: ${signalData.smartMoneyWallet}
        Investment Size: $${signalData.usdValue}
        DEX: ${signalData.dex}
        Alpha Score: ${signalData.alphaScore}
        
        Consider market conditions, token fundamentals, and smart money behavior patterns.`,
      })

      return object
    } catch (error) {
      console.error("[v0] ML prediction error:", error)
      return { probability: 0.5, confidence: 0.1, reasoning: "Prediction failed" }
    }
  }

  async optimizePositionSize(
    signalData: any,
    portfolioValue: number,
    riskTolerance: number,
  ): Promise<{
    recommendedSize: number
    kellyFraction: number
    maxRisk: number
  }> {
    try {
      const prediction = await this.predictTradeOutcome(signalData)

      // Kelly Criterion calculation
      const winProbability = prediction.probability
      const avgWin = 0.25 // 25% average win
      const avgLoss = 0.15 // 15% average loss

      const kellyFraction = (winProbability * avgWin - (1 - winProbability) * avgLoss) / avgWin
      const adjustedKelly = Math.max(0, Math.min(kellyFraction * riskTolerance, 0.1)) // Cap at 10%

      const recommendedSize = portfolioValue * adjustedKelly
      const maxRisk = recommendedSize * 0.15 // 15% stop loss

      return {
        recommendedSize,
        kellyFraction: adjustedKelly,
        maxRisk,
      }
    } catch (error) {
      console.error("[v0] Position sizing error:", error)
      return {
        recommendedSize: portfolioValue * 0.01,
        kellyFraction: 0.01,
        maxRisk: portfolioValue * 0.0015,
      }
    }
  }

  async generateMarketInsights(marketData: any[]): Promise<string> {
    try {
      const { text } = await generateText({
        model: this.openaiClient("gpt-4"),
        prompt: `Analyze current market conditions and provide trading insights:
        
        Market Data: ${JSON.stringify(marketData.slice(0, 10))}
        
        Provide insights on:
        1. Overall market sentiment
        2. Key opportunities
        3. Risk factors to watch
        4. Recommended strategy adjustments`,
      })

      return text
    } catch (error) {
      console.error("[v0] Market insights error:", error)
      return "Market analysis temporarily unavailable"
    }
  }
}
