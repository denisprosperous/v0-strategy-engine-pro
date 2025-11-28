import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { tradingBot } from "@/lib/telegram/bot"

async function setupWebhookHandler(req: AuthenticatedRequest) {
  try {
    if (!req.user || req.user.role !== "admin") {
      return NextResponse.json({ error: "Admin access required" }, { status: 403 })
    }

    const telegramToken = process.env.TELEGRAM_BOT_TOKEN
    if (!telegramToken) {
      return NextResponse.json({ error: "Telegram bot token not configured" }, { status: 500 })
    }

    const webhookUrl = process.env.TELEGRAM_WEBHOOK_URL || `${process.env.NEXT_PUBLIC_APP_URL}/api/telegram/webhook`

    // Set webhook via Telegram API
    const response = await fetch(`https://api.telegram.org/bot${telegramToken}/setWebhook`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: webhookUrl,
        allowed_updates: ["message", "callback_query"],
        drop_pending_updates: true,
      }),
    })

    const result = await response.json()

    if (result.ok) {
      return NextResponse.json({
        success: true,
        message: "Webhook configured successfully",
        webhookUrl,
      })
    } else {
      return NextResponse.json(
        {
          success: false,
          error: result.description,
        },
        { status: 500 },
      )
    }
  } catch (error) {
    console.error("Failed to setup webhook:", error)
    return NextResponse.json({ error: "Failed to setup webhook" }, { status: 500 })
  }
}

// Get webhook info
async function getWebhookInfoHandler(req: AuthenticatedRequest) {
  try {
    const telegramToken = process.env.TELEGRAM_BOT_TOKEN
    if (!telegramToken) {
      return NextResponse.json({
        configured: false,
        error: "Bot token not configured",
      })
    }

    const response = await fetch(`https://api.telegram.org/bot${telegramToken}/getWebhookInfo`)
    const result = await response.json()

    const botStatus = tradingBot.getStatus()

    return NextResponse.json({
      configured: true,
      botStatus,
      webhook: result.result,
    })
  } catch (error) {
    return NextResponse.json({ error: "Failed to get webhook info" }, { status: 500 })
  }
}

export const POST = withAuth(setupWebhookHandler)
export const GET = withAuth(getWebhookInfoHandler)
