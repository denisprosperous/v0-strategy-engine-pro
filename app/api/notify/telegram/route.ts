import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { tradingBot } from "@/lib/telegram/bot"

async function notifyHandler(req: AuthenticatedRequest) {
  try {
    if (!req.user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    const body = await req.json()
    const { telegramId, message } = body
    if (!telegramId || !message) return NextResponse.json({ error: "Missing fields" }, { status: 400 })

    await tradingBot["bot" as any].sendMessage(parseInt(telegramId, 10), message, { parse_mode: "Markdown" })
    return NextResponse.json({ success: true })
  } catch (error) {
    return NextResponse.json({ error: "Notify failed" }, { status: 500 })
  }
}

export const POST = withAuth(notifyHandler)
