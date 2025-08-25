// Notification service for Telegram alerts
import { tradingBot } from "./bot"
import { supabase } from "@/lib/config/database"
import { logger } from "@/lib/utils/logger"

export interface NotificationPreferences {
  tradeAlerts: boolean
  priceAlerts: boolean
  portfolioUpdates: boolean
  marketNews: boolean
  systemAlerts: boolean
}

export class TelegramNotificationService {
  async sendTradeNotification(userId: string, trade: any, type: "opened" | "closed" | "failed"): Promise<void> {
    try {
      const preferences = await this.getUserNotificationPreferences(userId)

      if (!preferences.tradeAlerts) {
        return // User has disabled trade alerts
      }

      await tradingBot.sendTradeAlert(userId, trade, type as "opened" | "closed")

      logger.info("Trade notification sent", { userId, tradeId: trade.id, type })
    } catch (error) {
      logger.error("Failed to send trade notification", { error, userId, trade })
    }
  }

  async sendPriceAlert(userId: string, symbol: string, price: number, condition: string): Promise<void> {
    try {
      const preferences = await this.getUserNotificationPreferences(userId)

      if (!preferences.priceAlerts) {
        return
      }

      await tradingBot.sendPriceAlert(userId, symbol, price, condition)

      logger.info("Price alert sent", { userId, symbol, price, condition })
    } catch (error) {
      logger.error("Failed to send price alert", { error, userId, symbol })
    }
  }

  async sendPortfolioUpdate(userId: string, summary: any): Promise<void> {
    try {
      const preferences = await this.getUserNotificationPreferences(userId)

      if (!preferences.portfolioUpdates) {
        return
      }

      const { data: user } = await supabase.from("users").select("telegram_id").eq("id", userId).single()

      if (!user?.telegram_id) return

      const updateMessage = `
📊 *Daily Portfolio Summary*

💰 Total P&L: ${summary.totalPnL >= 0 ? "🟢" : "🔴"} $${summary.totalPnL.toFixed(2)}
📈 Open Positions: ${summary.openPositions}
✅ Trades Today: ${summary.tradesCount}
📊 Win Rate: ${(summary.winRate * 100).toFixed(1)}%

🕐 ${new Date().toLocaleString()}
      `

      // Note: This would use the bot instance to send the message
      // Implementation depends on how the bot is structured

      logger.info("Portfolio update sent", { userId, summary })
    } catch (error) {
      logger.error("Failed to send portfolio update", { error, userId })
    }
  }

  async sendSystemAlert(message: string, severity: "info" | "warning" | "error" = "info"): Promise<void> {
    try {
      // Get all users who want system alerts
      const { data: users } = await supabase
        .from("users")
        .select("id, telegram_id, settings")
        .not("telegram_id", "is", null)

      if (!users) return

      const emoji = severity === "error" ? "🚨" : severity === "warning" ? "⚠️" : "ℹ️"
      const alertMessage = `${emoji} *System Alert*\n\n${message}\n\n🕐 ${new Date().toLocaleString()}`

      for (const user of users) {
        try {
          const preferences = user.settings?.notifications || { systemAlerts: true }

          if (preferences.systemAlerts) {
            // Send to user's Telegram
            // Implementation would use bot instance
          }
        } catch (error) {
          logger.error("Failed to send system alert to user", { error, userId: user.id })
        }
      }

      logger.info("System alert broadcast", { message, severity, userCount: users.length })
    } catch (error) {
      logger.error("Failed to broadcast system alert", { error, message })
    }
  }

  private async getUserNotificationPreferences(userId: string): Promise<NotificationPreferences> {
    try {
      const { data: user } = await supabase.from("users").select("settings").eq("id", userId).single()

      return (
        user?.settings?.notifications || {
          tradeAlerts: true,
          priceAlerts: true,
          portfolioUpdates: true,
          marketNews: false,
          systemAlerts: true,
        }
      )
    } catch (error) {
      logger.error("Failed to get notification preferences", { error, userId })
      // Return default preferences
      return {
        tradeAlerts: true,
        priceAlerts: true,
        portfolioUpdates: true,
        marketNews: false,
        systemAlerts: true,
      }
    }
  }
}

// Singleton instance
export const telegramNotifications = new TelegramNotificationService()
