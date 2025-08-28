// Core Telegram bot implementation
import TelegramBot from "node-telegram-bot-api"
import { config } from "@/lib/config/environment"
import { supabase } from "@/lib/config/database"
import { logger } from "@/lib/utils/logger"
import { marketDataAggregator } from "@/lib/market-data/aggregator"
import { sentimentAnalyzer } from "@/lib/sentiment/analyzer"
import { BinanceBroker } from "@/lib/trading/brokers/binance-broker"

export interface TelegramUser {
  id: number
  username?: string
  first_name: string
  last_name?: string
}

export class TradingTelegramBot {
  private bot: TelegramBot
  private userSessions = new Map<number, any>()
  private isRunning = false

  constructor() {
    if (!config.telegram.botToken) {
      throw new Error("Telegram bot token not configured")
    }

    this.bot = new TelegramBot(config.telegram.botToken, { polling: false })
    this.setupCommands()
    this.setupCallbacks()
  }

  async start(): Promise<void> {
    if (this.isRunning) return

    try {
      if (config.telegram.webhookUrl) {
        // Production: Use webhook
        await this.bot.setWebHook(config.telegram.webhookUrl)
        logger.info("Telegram bot webhook set", { url: config.telegram.webhookUrl })
      } else {
        // Development: Use polling
        await this.bot.startPolling()
        logger.info("Telegram bot polling started")
      }

      this.isRunning = true
      logger.info("Telegram trading bot started")
    } catch (error) {
      logger.error("Failed to start Telegram bot", { error })
      throw error
    }
  }

  async stop(): Promise<void> {
    if (!this.isRunning) return

    try {
      await this.bot.stopPolling()
      this.isRunning = false
      logger.info("Telegram trading bot stopped")
    } catch (error) {
      logger.error("Failed to stop Telegram bot", { error })
    }
  }

  async handleWebhook(update: any): Promise<void> {
    try {
      await this.bot.processUpdate(update)
    } catch (error) {
      logger.error("Webhook processing failed", { error, update })
    }
  }

  private setupCommands(): void {
    // Start command
    this.bot.onText(/\/start/, async (msg) => {
      await this.handleStartCommand(msg)
    })

    // Help command
    this.bot.onText(/\/help/, async (msg) => {
      await this.handleHelpCommand(msg)
    })

    // Register command
    this.bot.onText(/\/register/, async (msg) => {
      await this.handleRegisterCommand(msg)
    })

    // Balance command
    this.bot.onText(/\/balance/, async (msg) => {
      await this.handleBalanceCommand(msg)
    })

    // Price command
    this.bot.onText(/\/price (.+)/, async (msg, match) => {
      await this.handlePriceCommand(msg, match?.[1])
    })

    // Trade command
    this.bot.onText(/\/trade/, async (msg) => {
      await this.handleTradeCommand(msg)
    })

    // Status command
    this.bot.onText(/\/status/, async (msg) => {
      await this.handleStatusCommand(msg)
    })

    // Sentiment command
    this.bot.onText(/\/sentiment (.+)/, async (msg, match) => {
      await this.handleSentimentCommand(msg, match?.[1])
    })

    // Portfolio command
    this.bot.onText(/\/portfolio/, async (msg) => {
      await this.handlePortfolioCommand(msg)
    })

    // Settings command
    this.bot.onText(/\/settings/, async (msg) => {
      await this.handleSettingsCommand(msg)
    })

    // Auto trading toggle
    this.bot.onText(/\/auto (on|off)/, async (msg, match) => {
      await this.handleAutoTradingCommand(msg, match?.[1] as "on" | "off")
    })
  }

  private setupCallbacks(): void {
    // Handle callback queries from inline keyboards
    this.bot.on("callback_query", async (callbackQuery) => {
      try {
        await this.handleCallbackQuery(callbackQuery)
      } catch (error) {
        logger.error("Callback query handling failed", { error, callbackQuery })
      }
    })

    // Handle errors
    this.bot.on("polling_error", (error) => {
      logger.error("Telegram bot polling error", { error })
    })

    this.bot.on("webhook_error", (error) => {
      logger.error("Telegram bot webhook error", { error })
    })
  }

  private async handleStartCommand(msg: TelegramBot.Message): Promise<void> {
    const chatId = msg.chat.id
    const user = msg.from

    if (!user) return

    const welcomeMessage = `
🤖 *Welcome to AI Trading Bot!*

I'm your personal trading assistant. Here's what I can do:

📊 *Market Data*
• /price BTCUSDT - Get current price
• /sentiment BTCUSDT - Market sentiment analysis

💰 *Trading*
• /balance - Check your balance
• /trade - Execute manual trades
• /portfolio - View your positions
• /status - Trading status & PnL

⚙️ *Settings*
• /settings - Configure your preferences
• /auto on/off - Toggle auto trading
• /register - Link your account

📚 *Help*
• /help - Show all commands

Ready to start trading? Use /register to link your account!
    `

    await this.bot.sendMessage(chatId, welcomeMessage, {
      parse_mode: "Markdown",
      reply_markup: {
        inline_keyboard: [
          [
            { text: "📊 Check Price", callback_data: "quick_price_BTCUSDT" },
            { text: "💰 Balance", callback_data: "quick_balance" },
          ],
          [
            { text: "📈 Portfolio", callback_data: "quick_portfolio" },
            { text: "⚙️ Settings", callback_data: "quick_settings" },
          ],
        ],
      },
    })

    logger.info("Start command handled", { userId: user.id, username: user.username })
  }

  private async handleHelpCommand(msg: TelegramBot.Message): Promise<void> {
    const chatId = msg.chat.id

    const helpMessage = `
📚 *Available Commands*

*Market Data:*
/price SYMBOL - Get current price (e.g., /price BTCUSDT)
/sentiment SYMBOL - Market sentiment analysis

*Trading:*
/balance - Check account balance
/trade - Execute manual trades
/portfolio - View open positions
/status - Trading status & daily PnL

*Account Management:*
/register - Link Telegram to your account
/settings - Configure trading preferences
/auto on/off - Toggle automatic trading

*Quick Actions:*
Use the inline keyboard buttons for faster access to common functions.

*Examples:*
• /price ETHUSDT
• /sentiment BTCUSDT
• /auto on
• /trade

Need help? Contact support or check our documentation.
    `

    await this.bot.sendMessage(chatId, helpMessage, { parse_mode: "Markdown" })
  }

  private async handleRegisterCommand(msg: TelegramBot.Message): Promise<void> {
    const chatId = msg.chat.id
    const user = msg.from

    if (!user) return

    try {
      // Check if user is already registered
      const { data: existingUser } = await supabase
        .from("users")
        .select("id, username")
        .eq("telegram_id", user.id.toString())
        .single()

      if (existingUser) {
        await this.bot.sendMessage(
          chatId,
          `✅ You're already registered as *${existingUser.username}*!\n\nYou can start using trading commands.`,
          { parse_mode: "Markdown" },
        )
        return
      }

      // Generate registration link or code
      const registrationCode = this.generateRegistrationCode(user.id)

      const registerMessage = `
🔗 *Account Registration*

To link your Telegram account with the trading platform:

1️⃣ Visit: ${process.env.NEXT_PUBLIC_APP_URL || "https://your-app.com"}/auth/register
2️⃣ Create your account
3️⃣ In the Telegram ID field, enter: \`${user.id}\`

Or use this registration code: \`${registrationCode}\`

Once registered, you'll have full access to trading features!
      `

      await this.bot.sendMessage(chatId, registerMessage, {
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [
            [
              {
                text: "🌐 Open Registration",
                url: `${process.env.NEXT_PUBLIC_APP_URL || "https://your-app.com"}/auth/register`,
              },
            ],
          ],
        },
      })
    } catch (error) {
      logger.error("Registration command failed", { error, userId: user.id })
      await this.bot.sendMessage(chatId, "❌ Registration failed. Please try again later.")
    }
  }

  private async handleBalanceCommand(msg: TelegramBot.Message): Promise<void> {
    const chatId = msg.chat.id
    const user = msg.from

    if (!user) return

    try {
      const dbUser = await this.getRegisteredUser(user.id)
      if (!dbUser) {
        await this.sendNotRegisteredMessage(chatId)
        return
      }

      if (!dbUser.api_keys?.binance?.key) {
        await this.bot.sendMessage(
          chatId,
          "⚠️ *API Keys Not Configured*\n\nPlease configure your Binance API keys in the web dashboard to check your balance.",
          { parse_mode: "Markdown" },
        )
        return
      }

      const broker = new BinanceBroker(
        dbUser.api_keys.binance.key,
        dbUser.api_keys.binance.secret,
        config.binance.testnet,
      )

      await broker.connect()
      const balances = await broker.getBalance()
      await broker.disconnect()

      const significantBalances = balances.filter((b) => b.total > 0.001)

      if (significantBalances.length === 0) {
        await this.bot.sendMessage(chatId, "💰 *Account Balance*\n\nNo significant balances found.", {
          parse_mode: "Markdown",
        })
        return
      }

      let balanceMessage = "💰 *Account Balance*\n\n"

      for (const balance of significantBalances.slice(0, 10)) {
        const total = balance.total.toFixed(8)
        const free = balance.free.toFixed(8)
        const locked = balance.locked.toFixed(8)

        balanceMessage += `*${balance.asset}*\n`
        balanceMessage += `  Total: ${total}\n`
        balanceMessage += `  Available: ${free}\n`
        if (balance.locked > 0) {
          balanceMessage += `  Locked: ${locked}\n`
        }
        balanceMessage += "\n"
      }

      await this.bot.sendMessage(chatId, balanceMessage, { parse_mode: "Markdown" })
    } catch (error) {
      logger.error("Balance command failed", { error, userId: user.id })
      await this.bot.sendMessage(chatId, "❌ Failed to fetch balance. Please check your API keys.")
    }
  }

  private async handlePriceCommand(msg: TelegramBot.Message, symbol?: string): Promise<void> {
    const chatId = msg.chat.id

    if (!symbol) {
      await this.bot.sendMessage(chatId, "📊 *Price Check*\n\nUsage: /price SYMBOL\n\nExample: /price BTCUSDT", {
        parse_mode: "Markdown",
      })
      return
    }

    try {
      const price = await marketDataAggregator.getPrice(symbol.toUpperCase())

      const priceMessage = `
📊 *${symbol.toUpperCase()} Price*

💰 Current Price: *$${price.toLocaleString()}*
🕐 Updated: ${new Date().toLocaleTimeString()}

Use /sentiment ${symbol} for market sentiment analysis.
      `

      await this.bot.sendMessage(chatId, priceMessage, {
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [
            [
              { text: "📈 Sentiment", callback_data: `sentiment_${symbol}` },
              { text: "📊 Chart", callback_data: `chart_${symbol}` },
            ],
          ],
        },
      })
    } catch (error) {
      logger.error("Price command failed", { error, symbol })
      await this.bot.sendMessage(chatId, `❌ Failed to fetch price for ${symbol}. Please check the symbol.`)
    }
  }

  private async handleSentimentCommand(msg: TelegramBot.Message, symbol?: string): Promise<void> {
    const chatId = msg.chat.id

    if (!symbol) {
      await this.bot.sendMessage(
        chatId,
        "📈 *Sentiment Analysis*\n\nUsage: /sentiment SYMBOL\n\nExample: /sentiment BTCUSDT",
        { parse_mode: "Markdown" },
      )
      return
    }

    try {
      await this.bot.sendMessage(chatId, "🔍 Analyzing market sentiment...")

      const sentiment = await sentimentAnalyzer.getSentiment(symbol.toUpperCase())

      const sentimentEmoji = this.getSentimentEmoji(sentiment.score)
      const sentimentText = this.getSentimentText(sentiment.score)

      const sentimentMessage = `
📈 *${symbol.toUpperCase()} Sentiment Analysis*

${sentimentEmoji} *${sentimentText}*
📊 Score: ${sentiment.score.toFixed(2)} (-1 to +1)
🎯 Confidence: ${(sentiment.confidence * 100).toFixed(1)}%

📰 Sources: ${sentiment.sources.join(", ")}
🕐 Updated: ${sentiment.timestamp.toLocaleTimeString()}

${this.getSentimentAdvice(sentiment.score)}
      `

      await this.bot.sendMessage(chatId, sentimentMessage, { parse_mode: "Markdown" })
    } catch (error) {
      logger.error("Sentiment command failed", { error, symbol })
      await this.bot.sendMessage(chatId, `❌ Failed to analyze sentiment for ${symbol}.`)
    }
  }

  private async handleTradeCommand(msg: TelegramBot.Message): Promise<void> {
    const chatId = msg.chat.id
    const user = msg.from

    if (!user) return

    try {
      const dbUser = await this.getRegisteredUser(user.id)
      if (!dbUser) {
        await this.sendNotRegisteredMessage(chatId)
        return
      }

      const tradeMessage = `
💼 *Manual Trading*

Choose your trading action:
      `

      await this.bot.sendMessage(chatId, tradeMessage, {
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [
            [
              { text: "🟢 Buy", callback_data: "trade_buy" },
              { text: "🔴 Sell", callback_data: "trade_sell" },
            ],
            [
              { text: "📊 Quick Buy BTC", callback_data: "quick_buy_BTCUSDT" },
              { text: "📊 Quick Buy ETH", callback_data: "quick_buy_ETHUSDT" },
            ],
            [{ text: "❌ Cancel", callback_data: "cancel_trade" }],
          ],
        },
      })
    } catch (error) {
      logger.error("Trade command failed", { error, userId: user.id })
      await this.bot.sendMessage(chatId, "❌ Trading interface failed to load.")
    }
  }

  private async handleStatusCommand(msg: TelegramBot.Message): Promise<void> {
    const chatId = msg.chat.id
    const user = msg.from

    if (!user) return

    try {
      const dbUser = await this.getRegisteredUser(user.id)
      if (!dbUser) {
        await this.sendNotRegisteredMessage(chatId)
        return
      }

      // Get today's trades and PnL
      const today = new Date().toISOString().split("T")[0]
      const { data: todayTrades } = await supabase
        .from("trades")
        .select("*")
        .eq("user_id", dbUser.id)
        .gte("execution_time", `${today}T00:00:00Z`)

      const openTrades = todayTrades?.filter((t) => t.status === "open") || []
      const closedTrades = todayTrades?.filter((t) => t.status === "closed") || []
      const dailyPnL = closedTrades.reduce((sum, trade) => sum + (trade.pnl || 0), 0)

      const statusMessage = `
📊 *Trading Status*

🤖 Auto Trading: ${dbUser.settings?.auto_trading_enabled ? "✅ ON" : "❌ OFF"}

📈 *Today's Performance*
💰 Daily P&L: ${dailyPnL >= 0 ? "🟢" : "🔴"} $${dailyPnL.toFixed(2)}
📊 Open Positions: ${openTrades.length}
✅ Completed Trades: ${closedTrades.length}

⚙️ *Settings*
🎯 Risk per Trade: ${((dbUser.settings?.risk_per_trade || 0.02) * 100).toFixed(1)}%
🛡️ Max Daily Loss: $${dbUser.settings?.max_daily_loss || 1000}

Last Updated: ${new Date().toLocaleTimeString()}
      `

      await this.bot.sendMessage(chatId, statusMessage, {
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [
            [
              { text: "📈 Portfolio", callback_data: "quick_portfolio" },
              { text: "⚙️ Settings", callback_data: "quick_settings" },
            ],
          ],
        },
      })
    } catch (error) {
      logger.error("Status command failed", { error, userId: user.id })
      await this.bot.sendMessage(chatId, "❌ Failed to fetch trading status.")
    }
  }

  private async handlePortfolioCommand(msg: TelegramBot.Message): Promise<void> {
    const chatId = msg.chat.id
    const user = msg.from

    if (!user) return

    try {
      const dbUser = await this.getRegisteredUser(user.id)
      if (!dbUser) {
        await this.sendNotRegisteredMessage(chatId)
        return
      }

      // Get open trades
      const { data: openTrades } = await supabase
        .from("trades")
        .select("*")
        .eq("user_id", dbUser.id)
        .eq("status", "open")
        .order("execution_time", { ascending: false })

      if (!openTrades || openTrades.length === 0) {
        await this.bot.sendMessage(
          chatId,
          "📈 *Portfolio*\n\nNo open positions found.\n\nUse /trade to start trading!",
          { parse_mode: "Markdown" },
        )
        return
      }

      let portfolioMessage = "📈 *Your Portfolio*\n\n"

      for (const trade of openTrades.slice(0, 10)) {
        const currentPrice = await marketDataAggregator.getPrice(trade.symbol)
        const unrealizedPnL = this.calculateUnrealizedPnL(trade, currentPrice)
        const pnlEmoji = unrealizedPnL >= 0 ? "🟢" : "🔴"

        portfolioMessage += `*${trade.symbol}*\n`
        portfolioMessage += `  ${trade.side.toUpperCase()} ${trade.quantity}\n`
        portfolioMessage += `  Entry: $${trade.entry_price.toFixed(4)}\n`
        portfolioMessage += `  Current: $${currentPrice.toFixed(4)}\n`
        portfolioMessage += `  P&L: ${pnlEmoji} $${unrealizedPnL.toFixed(2)}\n\n`
      }

      await this.bot.sendMessage(chatId, portfolioMessage, { parse_mode: "Markdown" })
    } catch (error) {
      logger.error("Portfolio command failed", { error, userId: user.id })
      await this.bot.sendMessage(chatId, "❌ Failed to fetch portfolio.")
    }
  }

  private async handleAutoTradingCommand(msg: TelegramBot.Message, action: "on" | "off"): Promise<void> {
    const chatId = msg.chat.id
    const user = msg.from

    if (!user) return

    try {
      const dbUser = await this.getRegisteredUser(user.id)
      if (!dbUser) {
        await this.sendNotRegisteredMessage(chatId)
        return
      }

      const autoTradingEnabled = action === "on"

      await supabase
        .from("users")
        .update({
          settings: {
            ...dbUser.settings,
            auto_trading_enabled: autoTradingEnabled,
          },
        })
        .eq("id", dbUser.id)

      const statusEmoji = autoTradingEnabled ? "✅" : "❌"
      const statusText = autoTradingEnabled ? "ENABLED" : "DISABLED"

      await this.bot.sendMessage(
        chatId,
        `🤖 *Auto Trading ${statusText}*\n\n${statusEmoji} Automatic trading is now ${statusText.toLowerCase()}.`,
        { parse_mode: "Markdown" },
      )

      logger.info("Auto trading toggled", { userId: user.id, enabled: autoTradingEnabled })
    } catch (error) {
      logger.error("Auto trading command failed", { error, userId: user.id })
      await this.bot.sendMessage(chatId, "❌ Failed to update auto trading settings.")
    }
  }

  private async handleSettingsCommand(msg: TelegramBot.Message): Promise<void> {
    const chatId = msg.chat.id
    const user = msg.from

    if (!user) return

    try {
      const dbUser = await this.getRegisteredUser(user.id)
      if (!dbUser) {
        await this.sendNotRegisteredMessage(chatId)
        return
      }

      const settings = dbUser.settings || {}

      const settingsMessage = `
⚙️ *Trading Settings*

🤖 Auto Trading: ${settings.auto_trading_enabled ? "✅ ON" : "❌ OFF"}
🎯 Risk per Trade: ${((settings.risk_per_trade || 0.02) * 100).toFixed(1)}%
🛡️ Max Daily Loss: $${settings.max_daily_loss || 1000}
💰 Default Position Size: $${settings.default_position_size || 100}

Use the buttons below to modify your settings:
      `

      await this.bot.sendMessage(chatId, settingsMessage, {
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [
            [{ text: "🤖 Toggle Auto Trading", callback_data: "toggle_auto_trading" }],
            [
              { text: "🎯 Risk Settings", callback_data: "risk_settings" },
              { text: "💰 Position Size", callback_data: "position_settings" },
            ],
            [{ text: "🔑 API Keys", callback_data: "api_settings" }],
          ],
        },
      })
    } catch (error) {
      logger.error("Settings command failed", { error, userId: user.id })
      await this.bot.sendMessage(chatId, "❌ Failed to load settings.")
    }
  }

  private async handleCallbackQuery(callbackQuery: TelegramBot.CallbackQuery): Promise<void> {
    const chatId = callbackQuery.message?.chat.id
    const data = callbackQuery.data

    if (!chatId || !data) return

    await this.bot.answerCallbackQuery(callbackQuery.id)

    // Handle different callback actions
    if (data.startsWith("quick_price_")) {
      const symbol = data.replace("quick_price_", "")
      await this.handlePriceCommand({ chat: { id: chatId } } as any, symbol)
    } else if (data === "quick_balance") {
      await this.handleBalanceCommand({ chat: { id: chatId }, from: callbackQuery.from } as any)
    } else if (data === "quick_portfolio") {
      await this.handlePortfolioCommand({ chat: { id: chatId }, from: callbackQuery.from } as any)
    } else if (data === "quick_settings") {
      await this.handleSettingsCommand({ chat: { id: chatId }, from: callbackQuery.from } as any)
    } else if (data.startsWith("sentiment_")) {
      const symbol = data.replace("sentiment_", "")
      await this.handleSentimentCommand({ chat: { id: chatId } } as any, symbol)
    }
    // Add more callback handlers as needed
  }

  // Notification methods
  async sendTradeAlert(userId: string, trade: any, type: "opened" | "closed"): Promise<void> {
    try {
      const { data: user } = await supabase.from("users").select("telegram_id").eq("id", userId).single()

      if (!user?.telegram_id) return

      const emoji = type === "opened" ? "🟢" : "🔴"
      const action = type === "opened" ? "OPENED" : "CLOSED"

      const alertMessage = `
${emoji} *Trade ${action}*

📊 Symbol: *${trade.symbol}*
📈 Side: ${trade.side.toUpperCase()}
💰 Amount: ${trade.quantity}
💵 Price: $${trade.entry_price || trade.exit_price}
${trade.pnl ? `📊 P&L: ${trade.pnl >= 0 ? "🟢" : "🔴"} $${trade.pnl.toFixed(2)}` : ""}

🕐 ${new Date().toLocaleString()}
      `

      await this.bot.sendMessage(Number.parseInt(user.telegram_id), alertMessage, {
        parse_mode: "Markdown",
      })
    } catch (error) {
      logger.error("Failed to send trade alert", { error, userId, trade })
    }
  }

  async sendPriceAlert(userId: string, symbol: string, price: number, condition: string): Promise<void> {
    try {
      const { data: user } = await supabase.from("users").select("telegram_id").eq("id", userId).single()

      if (!user?.telegram_id) return

      const alertMessage = `
🚨 *Price Alert*

📊 ${symbol}: *$${price.toLocaleString()}*
⚠️ Condition: ${condition}

🕐 ${new Date().toLocaleString()}
      `

      await this.bot.sendMessage(Number.parseInt(user.telegram_id), alertMessage, {
        parse_mode: "Markdown",
      })
    } catch (error) {
      logger.error("Failed to send price alert", { error, userId, symbol })
    }
  }

  // Helper methods
  private async getRegisteredUser(telegramId: number): Promise<any> {
    const { data: user } = await supabase.from("users").select("*").eq("telegram_id", telegramId.toString()).single()

    return user
  }

  private async sendNotRegisteredMessage(chatId: number): Promise<void> {
    await this.bot.sendMessage(
      chatId,
      "⚠️ *Account Not Linked*\n\nPlease use /register to link your Telegram account with the trading platform.",
      { parse_mode: "Markdown" },
    )
  }

  private generateRegistrationCode(telegramId: number): string {
    return `TG${telegramId}${Date.now().toString().slice(-4)}`
  }

  private getSentimentEmoji(score: number): string {
    if (score > 0.3) return "🚀"
    if (score > 0.1) return "📈"
    if (score > -0.1) return "➡️"
    if (score > -0.3) return "📉"
    return "💥"
  }

  private getSentimentText(score: number): string {
    if (score > 0.3) return "Very Bullish"
    if (score > 0.1) return "Bullish"
    if (score > -0.1) return "Neutral"
    if (score > -0.3) return "Bearish"
    return "Very Bearish"
  }

  private getSentimentAdvice(score: number): string {
    if (score > 0.3) return "💡 Strong positive sentiment detected. Consider long positions."
    if (score > 0.1) return "💡 Positive sentiment. Good for moderate long positions."
    if (score > -0.1) return "💡 Neutral sentiment. Wait for clearer signals."
    if (score > -0.3) return "💡 Negative sentiment. Consider short positions or wait."
    return "💡 Very negative sentiment. Avoid long positions."
  }

  private calculateUnrealizedPnL(trade: any, currentPrice: number): number {
    const entryValue = trade.entry_price * trade.quantity
    const currentValue = currentPrice * trade.quantity

    if (trade.side === "buy") {
      return currentValue - entryValue
    } else {
      return entryValue - currentValue
    }
  }
}

// Singleton instance
export const tradingBot = new TradingTelegramBot()
