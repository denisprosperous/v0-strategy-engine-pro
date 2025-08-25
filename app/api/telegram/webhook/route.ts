// Telegram webhook endpoint
import { type NextRequest, NextResponse } from "next/server"
import { tradingBot } from "@/lib/telegram/bot"
import { logger } from "@/lib/utils/logger"

export async function POST(req: NextRequest) {
  try {
    const update = await req.json()

    // Verify webhook (optional but recommended)
    const telegramToken = process.env.TELEGRAM_BOT_TOKEN
    if (!telegramToken) {
      return NextResponse.json({ error: "Bot token not configured" }, { status: 500 })
    }

    // Process the update
    await tradingBot.handleWebhook(update)

    return NextResponse.json({ ok: true })
  } catch (error) {
    logger.error("Telegram webhook error", { error })
    return NextResponse.json({ error: "Webhook processing failed" }, { status: 500 })
  }
}

// Health check endpoint
export async function GET() {
  return NextResponse.json({
    status: "ok",
    timestamp: new Date().toISOString(),
  })
}
