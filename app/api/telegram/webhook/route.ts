import { type NextRequest, NextResponse } from "next/server"
import { tradingBot } from "@/lib/telegram/bot"
import { logger } from "@/lib/utils/logger"

export async function POST(req: NextRequest) {
  try {
    // Verify bot token is configured
    const telegramToken = process.env.TELEGRAM_BOT_TOKEN
    if (!telegramToken) {
      logger.warn("Telegram webhook called but bot token not configured")
      return NextResponse.json({ error: "Bot token not configured" }, { status: 500 })
    }

    // Optional: Verify the request is from Telegram
    // You can add a secret token to your webhook URL for verification
    const secretToken = req.headers.get("x-telegram-bot-api-secret-token")
    const expectedSecret = process.env.TELEGRAM_WEBHOOK_SECRET

    if (expectedSecret && secretToken !== expectedSecret) {
      logger.warn("Telegram webhook: Invalid secret token")
      return NextResponse.json({ error: "Invalid secret" }, { status: 403 })
    }

    const update = await req.json()

    // Log incoming update for debugging
    logger.debug("Telegram webhook received", {
      updateId: update.update_id,
      type: update.message ? "message" : update.callback_query ? "callback" : "other",
    })

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
  const status = tradingBot.getStatus()

  return NextResponse.json({
    status: "ok",
    bot: status,
    timestamp: new Date().toISOString(),
  })
}
