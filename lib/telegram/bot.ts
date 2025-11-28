// Core Telegram bot implementation - Updated to use Redis database
import TelegramBot from "node-telegram-bot-api"
import { config } from "@/lib/config/environment"
import { db, redis } from "@/lib/config/database"
import { logger } from "@/lib/utils/logger"
import { liveMarketService } from "@/lib/trading/services/live-market-service"
import { BinanceBroker } from "@/lib/trading/brokers/binance-broker"

export interface TelegramUser {
  id: number
  username?: string
  first_name: string
  last_name?: string
}

export class TradingTelegramBot {
  private bot: TelegramBot | null = null
  private userSessions = new Map<number, any>()
  private isRunning = false
  private initialized = false

  constructor() {
    // Lazy initialization - don't throw if token missing
    if (config.telegram.botToken) {
      this.initialize()
    }
  }

  private initialize(): void {
    if (this.initialized || !config.telegram.botToken) return

    try {
      this.bot = new TelegramBot(config.telegram.botToken, { polling: false })
      this.setupCommands()
      this.setupCallbacks()
      this.initialized = true
      logger.info("Telegram bot initialized")
    } catch (error) {
      logger.error("Failed to initialize Telegram bot", { error })
    }
  }

  async start(): Promise<void> {
    if (!this.bot) {
      this.initialize()
    }

    if (!this.bot || this.isRunning) return

    try {
      if (config.telegram.webhookUrl) {
        await this.bot.setWebHook(config.telegram.webhookUrl)
        logger.info("Telegram bot webhook set", { url: config.telegram.webhookUrl })
      } else {
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
    if (!this.bot || !this.isRunning) return

    try {
      await this.bot.stopPolling()
      this.isRunning = false
      logger.info("Telegram trading bot stopped")
    } catch (error) {
      logger.error("Failed to stop Telegram bot", { error })
    }
  }

  async handleWebhook(update: any): Promise<void> {
    if (!this.bot) {
      this.initialize()
    }

    if (!this.bot) {
      logger.error("Telegram bot not initialized")
      return
    }

    try {
      await this.bot.processUpdate(update)
    } catch (error) {
      logger.error("Webhook processing failed", { error, update })
    }
  }

  private setupCommands(): void {
    if (!this.bot) return

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

    // Market data command
    this.bot.onText(/\/market/, async (msg) => {
      await this.handleMarketCommand(msg)
    })

    // Exchanges status command
    this.bot.onText(/\/exchanges/, async (msg) => {
      await this.handleExchangesCommand(msg)
    })
  }

  private setupCallbacks(): void {
    if (!this.bot) return

    this.bot.on("callback_query", async (callbackQuery) => {
      try {
        await this.handleCallbackQuery(callbackQuery)
      } catch (error) {
        logger.error("Callback query handling failed", { error, callbackQuery })
      }
    })

    this.bot.on("polling_error", (error) => {
      logger.error("Telegram bot polling error", { error })
    })

    this.bot.on("webhook_error", (error) => {
      logger.error("Telegram bot webhook error", { error })
    })
  }

  private async handleStartCommand(msg: TelegramBot.Message): Promise<void> {
    if (!this.bot) return
    const chatId = msg.chat.id
    const user = msg.from

    if (!user) return

    const welcomeMessage = `
*Welcome to Strategy Engine Pro!*

I'm your AI-powered trading assistant. Here's what I can do:

*Market Data*
/price BTCUSDT - Get current price
/market - Top cryptocurrency prices
/exchanges - Check exchange connections

*Trading*
/balance - Check your balance
/trade - Execute manual trades
/portfolio - View your positions
/status - Trading status & PnL

*Settings*
/settings - Configure your preferences
/auto on/off - Toggle auto trading
/register - Link your account

*Help*
/help - Show all commands

Ready to start? Use /register to link your account!
    `

    await this.bot.sendMessage(chatId, welcomeMessage, {
      parse_mode: "Markdown",
      reply_markup: {
        inline_keyboard: [
          [
            { text: "Check Price", callback_data: "quick_price_BTCUSDT" },
            { text: "Balance", callback_data: "quick_balance" },
          ],
          [
            { text: "Portfolio", callback_data: "quick_portfolio" },
            { text: "Settings", callback_data: "quick_settings" },
          ],
          [{ text: "Market Overview", callback_data: "quick_market" }],
        ],
      },
    })

    logger.info("Start command handled", { userId: user.id, username: user.username })
  }

  private async handleHelpCommand(msg: TelegramBot.Message): Promise<void> {
    if (!this.bot) return
    const chatId = msg.chat.id

    const helpMessage = `
*Available Commands*

*Market Data:*
/price SYMBOL - Get current price
/market - Top 10 cryptocurrency prices
/exchanges - Check exchange status

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
Use inline keyboard buttons for faster access.

*Examples:*
- /price ETHUSDT
- /price SOLUSDT
- /auto on
    `

    await this.bot.sendMessage(chatId, helpMessage, { parse_mode: "Markdown" })
  }

  private async handleRegisterCommand(msg: TelegramBot.Message): Promise<void> {
    if (!this.bot) return
    const chatId = msg.chat.id
    const user = msg.from

    if (!user) return

    try {
      const existingUserId = await redis.get(`telegram:${user.id}`)

      if (existingUserId) {
        const existingUser = await db.getUser(existingUserId as string)
        if (existingUser) {
          await this.bot.sendMessage(
            chatId,
            `You're already registered as *${existingUser.username}*!\n\nYou can start using trading commands.`,
            { parse_mode: "Markdown" },
          )
          return
        }
      }

      const registrationCode = this.generateRegistrationCode(user.id)

      // Store registration code in Redis with expiry
      await redis.setex(`telegram_reg:${registrationCode}`, 3600, user.id.toString())

      const registerMessage = `
*Account Registration*

To link your Telegram account with the trading platform:

1. Visit: ${process.env.NEXT_PUBLIC_APP_URL || "https://your-app.com"}/auth/register
2. Create your account
3. In the Telegram ID field, enter: \`${user.id}\`

Or use this registration code: \`${registrationCode}\`

This code expires in 1 hour.
      `

      await this.bot.sendMessage(chatId, registerMessage, {
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [
            [
              {
                text: "Open Registration",
                url: `${process.env.NEXT_PUBLIC_APP_URL || "https://your-app.com"}/auth/register?telegram=${user.id}`,
              },
            ],
          ],
        },
      })
    } catch (error) {
      logger.error("Registration command failed", { error, userId: user.id })
      await this.bot.sendMessage(chatId, "Registration failed. Please try again later.")
    }
  }

  private async handleBalanceCommand(msg: TelegramBot.Message): Promise<void> {
    if (!this.bot) return
    const chatId = msg.chat.id
    const user = msg.from

    if (!user) return

    try {
      const dbUser = await this.getRegisteredUser(user.id)
      if (!dbUser) {
        await this.sendNotRegisteredMessage(chatId)
        return
      }

      let apiKeys = dbUser.apiKeys || dbUser.api_keys
      if (typeof apiKeys === "string") {
        try {
          apiKeys = JSON.parse(apiKeys)
        } catch {
          apiKeys = {}
        }
      }

      if (!apiKeys?.binance?.key) {
        await this.bot.sendMessage(
          chatId,
          "*API Keys Not Configured*\n\nPlease configure your exchange API keys in the web dashboard to check your balance.",
          { parse_mode: "Markdown" },
        )
        return
      }

      const broker = new BinanceBroker(apiKeys.binance.key, apiKeys.binance.secret, config.binance.testnet)

      await broker.connect()
      const balances = await broker.getBalance()
      await broker.disconnect()

      const significantBalances = balances.filter((b) => b.total > 0.001)

      if (significantBalances.length === 0) {
        await this.bot.sendMessage(chatId, "*Account Balance*\n\nNo significant balances found.", {
          parse_mode: "Markdown",
        })
        return
      }

      let balanceMessage = "*Account Balance*\n\n"

      for (const balance of significantBalances.slice(0, 10)) {
        const total = balance.total.toFixed(8)
        const free = balance.free.toFixed(8)

        balanceMessage += `*${balance.asset}*\n`
        balanceMessage += `  Total: ${total}\n`
        balanceMessage += `  Available: ${free}\n\n`
      }

      await this.bot.sendMessage(chatId, balanceMessage, { parse_mode: "Markdown" })
    } catch (error) {
      logger.error("Balance command failed", { error, userId: user.id })
      await this.bot.sendMessage(chatId, "Failed to fetch balance. Please check your API keys.")
    }
  }

  private async handlePriceCommand(msg: TelegramBot.Message, symbol?: string): Promise<void> {
    if (!this.bot) return
    const chatId = msg.chat.id

    if (!symbol) {
      await this.bot.sendMessage(chatId, "*Price Check*\n\nUsage: /price SYMBOL\n\nExample: /price BTCUSDT", {
        parse_mode: "Markdown",
      })
      return
    }

    try {
      const marketData = await liveMarketService.getMarketData(symbol.toUpperCase(), "binance")

      if (!marketData) {
        await this.bot.sendMessage(chatId, `Failed to fetch price for ${symbol}. Please check the symbol.`)
        return
      }

      const changeEmoji = marketData.change24h >= 0 ? "+" : ""
      const trendEmoji = marketData.change24h >= 0 ? "up" : "down"

      const priceMessage = `
*${symbol.toUpperCase()}*

Current Price: *$${marketData.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })}*
24h Change: ${changeEmoji}${marketData.change24h.toFixed(2)}% ${trendEmoji === "up" ? "green" : "red"}
24h High: $${marketData.high24h.toLocaleString()}
24h Low: $${marketData.low24h.toLocaleString()}
Volume: ${marketData.volume24h.toLocaleString()}

Updated: ${new Date().toLocaleTimeString()}
      `

      await this.bot.sendMessage(chatId, priceMessage, {
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [
            [
              { text: "Refresh", callback_data: `refresh_price_${symbol}` },
              { text: "Trade", callback_data: `trade_${symbol}` },
            ],
          ],
        },
      })
    } catch (error) {
      logger.error("Price command failed", { error, symbol })
      await this.bot.sendMessage(chatId, `Failed to fetch price for ${symbol}. Please check the symbol.`)
    }
  }

  private async handleMarketCommand(msg: TelegramBot.Message): Promise<void> {
    if (!this.bot) return
    const chatId = msg.chat.id

    try {
      const symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "DOTUSDT"]
      const marketData = await liveMarketService.getMultipleMarketData(symbols, "binance")

      let marketMessage = "*Market Overview*\n\n"

      for (const data of marketData) {
        const changeEmoji = data.change24h >= 0 ? "up" : "down"
        const symbol = data.symbol.replace("USDT", "")
        marketMessage += `*${symbol}*: $${data.price.toLocaleString(undefined, { minimumFractionDigits: 2 })} (${data.change24h >= 0 ? "+" : ""}${data.change24h.toFixed(2)}%) ${changeEmoji === "up" ? "green" : "red"}\n`
      }

      marketMessage += `\nUpdated: ${new Date().toLocaleTimeString()}`

      await this.bot.sendMessage(chatId, marketMessage, {
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [[{ text: "Refresh", callback_data: "refresh_market" }]],
        },
      })
    } catch (error) {
      logger.error("Market command failed", { error })
      await this.bot.sendMessage(chatId, "Failed to fetch market data.")
    }
  }

  private async handleExchangesCommand(msg: TelegramBot.Message): Promise<void> {
    if (!this.bot) return
    const chatId = msg.chat.id

    try {
      await this.bot.sendMessage(chatId, "Checking exchange connections...")

      const results = await liveMarketService.testAllExchangeConnections()

      let statusMessage = "*Exchange Status*\n\n"

      for (const [exchange, status] of Object.entries(results)) {
        const emoji = status.connected ? "green" : "red"
        statusMessage += `${emoji === "green" ? "Connected" : "Disconnected"} *${exchange.charAt(0).toUpperCase() + exchange.slice(1)}*: ${status.message}\n`
      }

      const connectedCount = Object.values(results).filter((r) => r.connected).length
      statusMessage += `\n*${connectedCount}/${Object.keys(results).length}* exchanges connected`

      await this.bot.sendMessage(chatId, statusMessage, { parse_mode: "Markdown" })
    } catch (error) {
      logger.error("Exchanges command failed", { error })
      await this.bot.sendMessage(chatId, "Failed to check exchange status.")
    }
  }

  private async handleTradeCommand(msg: TelegramBot.Message): Promise<void> {
    if (!this.bot) return
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
*Manual Trading*

Choose your trading action:
      `

      await this.bot.sendMessage(chatId, tradeMessage, {
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [
            [
              { text: "Buy", callback_data: "trade_buy" },
              { text: "Sell", callback_data: "trade_sell" },
            ],
            [
              { text: "Quick Buy BTC", callback_data: "quick_buy_BTCUSDT" },
              { text: "Quick Buy ETH", callback_data: "quick_buy_ETHUSDT" },
            ],
            [{ text: "Cancel", callback_data: "cancel_trade" }],
          ],
        },
      })
    } catch (error) {
      logger.error("Trade command failed", { error, userId: user.id })
      await this.bot.sendMessage(chatId, "Trading interface failed to load.")
    }
  }

  private async handleStatusCommand(msg: TelegramBot.Message): Promise<void> {
    if (!this.bot) return
    const chatId = msg.chat.id
    const user = msg.from

    if (!user) return

    try {
      const dbUser = await this.getRegisteredUser(user.id)
      if (!dbUser) {
        await this.sendNotRegisteredMessage(chatId)
        return
      }

      const analytics = await db.getAnalytics(dbUser.id)

      // Parse settings
      let settings = dbUser.settings
      if (typeof settings === "string") {
        try {
          settings = JSON.parse(settings)
        } catch {
          settings = {}
        }
      }

      const statusMessage = `
*Trading Status*

Auto Trading: ${settings?.autoTradingEnabled ? "ON" : "OFF"}

*Today's Performance*
Daily P&L: ${analytics.portfolio.totalPnL >= 0 ? "Profit" : "Loss"} $${Math.abs(analytics.portfolio.totalPnL).toFixed(2)}
Open Positions: ${analytics.trading.openTrades}
Total Trades: ${analytics.trading.totalTrades}
Win Rate: ${analytics.trading.winRate.toFixed(1)}%

*Settings*
Risk per Trade: ${((settings?.riskTolerance || 0.02) * 100).toFixed(1)}%
Max Daily Loss: $${settings?.maxDailyLoss || 1000}

Last Updated: ${new Date().toLocaleTimeString()}
      `

      await this.bot.sendMessage(chatId, statusMessage, {
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [
            [
              { text: "Portfolio", callback_data: "quick_portfolio" },
              { text: "Settings", callback_data: "quick_settings" },
            ],
          ],
        },
      })
    } catch (error) {
      logger.error("Status command failed", { error, userId: user.id })
      await this.bot.sendMessage(chatId, "Failed to fetch trading status.")
    }
  }

  private async handlePortfolioCommand(msg: TelegramBot.Message): Promise<void> {
    if (!this.bot) return
    const chatId = msg.chat.id
    const user = msg.from

    if (!user) return

    try {
      const dbUser = await this.getRegisteredUser(user.id)
      if (!dbUser) {
        await this.sendNotRegisteredMessage(chatId)
        return
      }

      const trades = await db.getTrades(dbUser.id, { status: "open" })

      if (!trades || trades.length === 0) {
        await this.bot.sendMessage(chatId, "*Portfolio*\n\nNo open positions found.\n\nUse /trade to start trading!", {
          parse_mode: "Markdown",
        })
        return
      }

      let portfolioMessage = "*Your Portfolio*\n\n"

      for (const trade of trades.slice(0, 10)) {
        const currentPrice = await liveMarketService.getPrice(
          trade.symbol as string,
          (trade.broker as string) || "binance",
        )
        const unrealizedPnL = this.calculateUnrealizedPnL(trade, currentPrice)
        const pnlStatus = unrealizedPnL >= 0 ? "Profit" : "Loss"

        portfolioMessage += `*${trade.symbol}*\n`
        portfolioMessage += `  ${(trade.side as string).toUpperCase()} ${trade.quantity}\n`
        portfolioMessage += `  Entry: $${Number.parseFloat(trade.entryPrice as string).toFixed(4)}\n`
        portfolioMessage += `  Current: $${currentPrice.toFixed(4)}\n`
        portfolioMessage += `  P&L: ${pnlStatus} $${Math.abs(unrealizedPnL).toFixed(2)}\n\n`
      }

      await this.bot.sendMessage(chatId, portfolioMessage, { parse_mode: "Markdown" })
    } catch (error) {
      logger.error("Portfolio command failed", { error, userId: user.id })
      await this.bot.sendMessage(chatId, "Failed to fetch portfolio.")
    }
  }

  private async handleAutoTradingCommand(msg: TelegramBot.Message, action: "on" | "off"): Promise<void> {
    if (!this.bot) return
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

      let settings = dbUser.settings
      if (typeof settings === "string") {
        try {
          settings = JSON.parse(settings)
        } catch {
          settings = {}
        }
      }

      await db.updateUser(dbUser.id, {
        settings: JSON.stringify({
          ...settings,
          autoTradingEnabled,
        }),
      })

      const statusText = autoTradingEnabled ? "ENABLED" : "DISABLED"

      await this.bot.sendMessage(
        chatId,
        `*Auto Trading ${statusText}*\n\nAutomatic trading is now ${statusText.toLowerCase()}.`,
        { parse_mode: "Markdown" },
      )

      logger.info("Auto trading toggled", { userId: user.id, enabled: autoTradingEnabled })
    } catch (error) {
      logger.error("Auto trading command failed", { error, userId: user.id })
      await this.bot.sendMessage(chatId, "Failed to update auto trading settings.")
    }
  }

  private async handleSettingsCommand(msg: TelegramBot.Message): Promise<void> {
    if (!this.bot) return
    const chatId = msg.chat.id
    const user = msg.from

    if (!user) return

    try {
      const dbUser = await this.getRegisteredUser(user.id)
      if (!dbUser) {
        await this.sendNotRegisteredMessage(chatId)
        return
      }

      let settings = dbUser.settings
      if (typeof settings === "string") {
        try {
          settings = JSON.parse(settings)
        } catch {
          settings = {}
        }
      }

      const settingsMessage = `
*Trading Settings*

Auto Trading: ${settings?.autoTradingEnabled ? "ON" : "OFF"}
Risk per Trade: ${((settings?.riskTolerance || 0.02) * 100).toFixed(1)}%
Max Daily Loss: $${settings?.maxDailyLoss || 1000}
Default Position Size: $${settings?.defaultPositionSize || 100}

Use the buttons below to modify your settings:
      `

      await this.bot.sendMessage(chatId, settingsMessage, {
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [
            [{ text: "Toggle Auto Trading", callback_data: "toggle_auto_trading" }],
            [
              { text: "Risk Settings", callback_data: "risk_settings" },
              { text: "Position Size", callback_data: "position_settings" },
            ],
            [
              {
                text: "API Keys (Web)",
                url: `${process.env.NEXT_PUBLIC_APP_URL || "https://your-app.com"}/dashboard/settings`,
              },
            ],
          ],
        },
      })
    } catch (error) {
      logger.error("Settings command failed", { error, userId: user.id })
      await this.bot.sendMessage(chatId, "Failed to load settings.")
    }
  }

  private async handleCallbackQuery(callbackQuery: TelegramBot.CallbackQuery): Promise<void> {
    if (!this.bot) return
    const chatId = callbackQuery.message?.chat.id
    const data = callbackQuery.data

    if (!chatId || !data) return

    await this.bot.answerCallbackQuery(callbackQuery.id)

    if (data.startsWith("quick_price_")) {
      const symbol = data.replace("quick_price_", "")
      await this.handlePriceCommand({ chat: { id: chatId } } as any, symbol)
    } else if (data.startsWith("refresh_price_")) {
      const symbol = data.replace("refresh_price_", "")
      await this.handlePriceCommand({ chat: { id: chatId } } as any, symbol)
    } else if (data === "quick_balance") {
      await this.handleBalanceCommand({ chat: { id: chatId }, from: callbackQuery.from } as any)
    } else if (data === "quick_portfolio") {
      await this.handlePortfolioCommand({ chat: { id: chatId }, from: callbackQuery.from } as any)
    } else if (data === "quick_settings") {
      await this.handleSettingsCommand({ chat: { id: chatId }, from: callbackQuery.from } as any)
    } else if (data === "quick_market" || data === "refresh_market") {
      await this.handleMarketCommand({ chat: { id: chatId } } as any)
    } else if (data === "toggle_auto_trading") {
      const dbUser = await this.getRegisteredUser(callbackQuery.from.id)
      if (dbUser) {
        let settings = dbUser.settings
        if (typeof settings === "string") {
          try {
            settings = JSON.parse(settings)
          } catch {
            settings = {}
          }
        }
        const currentState = settings?.autoTradingEnabled ? "off" : "on"
        await this.handleAutoTradingCommand(
          { chat: { id: chatId }, from: callbackQuery.from } as any,
          currentState as "on" | "off",
        )
      }
    }
  }

  // Notification methods
  async sendTradeAlert(userId: string, trade: any, type: "opened" | "closed"): Promise<void> {
    if (!this.bot) return

    try {
      const user = await db.getUser(userId)
      if (!user?.telegramId) return

      const action = type === "opened" ? "OPENED" : "CLOSED"
      const emoji = type === "opened" ? "New" : "Closed"

      const alertMessage = `
*Trade ${action}*

Symbol: *${trade.symbol}*
Side: ${trade.side.toUpperCase()}
Amount: ${trade.quantity}
Price: $${trade.entryPrice || trade.exitPrice}
${trade.pnl ? `P&L: ${trade.pnl >= 0 ? "Profit" : "Loss"} $${Math.abs(trade.pnl).toFixed(2)}` : ""}

${new Date().toLocaleString()}
      `

      await this.bot.sendMessage(Number.parseInt(user.telegramId), alertMessage, {
        parse_mode: "Markdown",
      })
    } catch (error) {
      logger.error("Failed to send trade alert", { error, userId, trade })
    }
  }

  async sendPriceAlert(userId: string, symbol: string, price: number, condition: string): Promise<void> {
    if (!this.bot) return

    try {
      const user = await db.getUser(userId)
      if (!user?.telegramId) return

      const alertMessage = `
*Price Alert*

${symbol}: *$${price.toLocaleString()}*
Condition: ${condition}

${new Date().toLocaleString()}
      `

      await this.bot.sendMessage(Number.parseInt(user.telegramId as string), alertMessage, {
        parse_mode: "Markdown",
      })
    } catch (error) {
      logger.error("Failed to send price alert", { error, userId, symbol })
    }
  }

  private async getRegisteredUser(telegramId: number): Promise<any> {
    try {
      const userId = await redis.get(`telegram:${telegramId}`)
      if (!userId) return null
      return db.getUser(userId as string)
    } catch (error) {
      logger.error("Failed to get registered user", { error, telegramId })
      return null
    }
  }

  private async sendNotRegisteredMessage(chatId: number): Promise<void> {
    if (!this.bot) return
    await this.bot.sendMessage(
      chatId,
      "*Account Not Linked*\n\nPlease use /register to link your Telegram account with the trading platform.",
      { parse_mode: "Markdown" },
    )
  }

  private generateRegistrationCode(telegramId: number): string {
    return `TG${telegramId}${Date.now().toString().slice(-4)}`
  }

  private calculateUnrealizedPnL(trade: any, currentPrice: number): number {
    const entryPrice = Number.parseFloat(trade.entryPrice)
    const quantity = Number.parseFloat(trade.quantity)
    const entryValue = entryPrice * quantity
    const currentValue = currentPrice * quantity

    if (trade.side === "buy") {
      return currentValue - entryValue
    } else {
      return entryValue - currentValue
    }
  }

  // Check if bot is configured
  isConfigured(): boolean {
    return !!config.telegram.botToken
  }

  getStatus(): { configured: boolean; running: boolean } {
    return {
      configured: this.isConfigured(),
      running: this.isRunning,
    }
  }
}

// Singleton instance - lazy initialization
let tradingBotInstance: TradingTelegramBot | null = null

export const tradingBot = (() => {
  if (!tradingBotInstance) {
    tradingBotInstance = new TradingTelegramBot()
  }
  return tradingBotInstance
})()
