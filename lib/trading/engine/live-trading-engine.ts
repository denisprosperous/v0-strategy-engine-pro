// Enhanced live trading engine with real-time capabilities
import type { BaseBroker } from "../brokers/base-broker"
import type { BaseStrategy } from "../strategies/base-strategy"
import { supabase } from "@/lib/config/database"
import { logger } from "@/lib/utils/logger"
import type { MarketData, Trade, TradeSignal, Strategy } from "@/lib/database/schema"

export interface LiveTradingConfig {
  userId: string
  maxConcurrentTrades: number
  maxDailyLoss: number
  riskPerTrade: number
  cooldownPeriod: number
  autoTrading: boolean
  demoMode: boolean
  enabledExchanges: string[]
  tradingPairs: string[]
}

export class LiveTradingEngine {
  private brokers: Map<string, BaseBroker> = new Map()
  private strategies: Map<string, { strategy: BaseStrategy; config: Strategy }> = new Map()
  private config: LiveTradingConfig
  private activeTrades: Map<string, Trade> = new Map()
  private dailyPnL = 0
  private lastTradeTime = 0
  private isRunning = false
  private marketDataInterval: NodeJS.Timeout | null = null
  private monitoringInterval: NodeJS.Timeout | null = null

  constructor(config: LiveTradingConfig) {
    this.config = config
  }

  async initialize(): Promise<void> {
    try {
      // Load user's active strategies
      await this.loadUserStrategies()

      // Load active trades
      await this.loadActiveTrades()

      // Calculate current daily P&L
      await this.calculateDailyPnL()

      logger.info("Live trading engine initialized", {
        userId: this.config.userId,
        strategiesCount: this.strategies.size,
        activeTradesCount: this.activeTrades.size,
      })
    } catch (error) {
      logger.error("Failed to initialize live trading engine", { error, userId: this.config.userId })
      throw error
    }
  }

  async start(): Promise<void> {
    if (this.isRunning) return

    try {
      // Connect all brokers
      for (const [name, broker] of this.brokers) {
        await broker.connect()
        logger.info(`Connected to ${name} broker`)
      }

      this.isRunning = true

      // Start market data collection
      this.startMarketDataCollection()

      // Start trade monitoring
      this.startTradeMonitoring()

      logger.info("Live trading engine started", {
        userId: this.config.userId,
        demoMode: this.config.demoMode,
      })
    } catch (error) {
      logger.error("Failed to start live trading engine", { error, userId: this.config.userId })
      throw error
    }
  }

  async stop(): Promise<void> {
    this.isRunning = false

    // Clear intervals
    if (this.marketDataInterval) {
      clearInterval(this.marketDataInterval)
      this.marketDataInterval = null
    }

    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval)
      this.monitoringInterval = null
    }

    // Disconnect all brokers
    for (const [name, broker] of this.brokers) {
      await broker.disconnect()
      logger.info(`Disconnected from ${name} broker`)
    }

    logger.info("Live trading engine stopped", { userId: this.config.userId })
  }

  addBroker(name: string, broker: BaseBroker): void {
    this.brokers.set(name, broker)
    logger.info("Broker added to live trading engine", { brokerName: name, userId: this.config.userId })
  }

  async addStrategy(strategyId: string, strategy: BaseStrategy): Promise<void> {
    try {
      // Get strategy config from database
      const { data: strategyConfig, error } = await supabase
        .from("strategies")
        .select("*")
        .eq("id", strategyId)
        .eq("created_by", this.config.userId)
        .single()

      if (error || !strategyConfig) {
        throw new Error(`Strategy ${strategyId} not found`)
      }

      this.strategies.set(strategyId, { strategy, config: strategyConfig })
      logger.info("Strategy added to live trading engine", {
        strategyId,
        strategyName: strategy.getName(),
        userId: this.config.userId,
      })
    } catch (error) {
      logger.error("Failed to add strategy", { error, strategyId, userId: this.config.userId })
      throw error
    }
  }

  async removeStrategy(strategyId: string): Promise<void> {
    this.strategies.delete(strategyId)
    logger.info("Strategy removed from live trading engine", { strategyId, userId: this.config.userId })
  }

  private async loadUserStrategies(): Promise<void> {
    try {
      const { data: strategies, error } = await supabase
        .from("strategies")
        .select("*")
        .eq("created_by", this.config.userId)
        .eq("is_active", true)

      if (error) throw error

      // Here you would instantiate the actual strategy classes based on type
      // For now, we'll just store the configs
      for (const strategy of strategies || []) {
        // This would be replaced with actual strategy instantiation
        logger.info("Loaded strategy config", { strategyId: strategy.id, type: strategy.type })
      }
    } catch (error) {
      logger.error("Failed to load user strategies", { error, userId: this.config.userId })
      throw error
    }
  }

  private async loadActiveTrades(): Promise<void> {
    try {
      const { data: trades, error } = await supabase
        .from("trades")
        .select("*")
        .eq("user_id", this.config.userId)
        .eq("status", "open")

      if (error) throw error

      for (const trade of trades || []) {
        this.activeTrades.set(trade.id, trade)
      }

      logger.info("Loaded active trades", {
        count: this.activeTrades.size,
        userId: this.config.userId,
      })
    } catch (error) {
      logger.error("Failed to load active trades", { error, userId: this.config.userId })
      throw error
    }
  }

  private async calculateDailyPnL(): Promise<void> {
    try {
      const today = new Date().toISOString().split("T")[0]
      const { data: todayTrades, error } = await supabase
        .from("trades")
        .select("pnl")
        .eq("user_id", this.config.userId)
        .gte("execution_time", `${today}T00:00:00Z`)
        .not("pnl", "is", null)

      if (error) throw error

      this.dailyPnL = todayTrades?.reduce((sum, trade) => sum + (trade.pnl || 0), 0) || 0

      logger.info("Calculated daily P&L", {
        dailyPnL: this.dailyPnL,
        userId: this.config.userId,
      })
    } catch (error) {
      logger.error("Failed to calculate daily P&L", { error, userId: this.config.userId })
    }
  }

  private startMarketDataCollection(): void {
    // Collect market data every 5 seconds
    this.marketDataInterval = setInterval(async () => {
      if (!this.isRunning) return

      try {
        await this.collectMarketData()
      } catch (error) {
        logger.error("Market data collection error", { error, userId: this.config.userId })
      }
    }, 5000)
  }

  private async collectMarketData(): Promise<void> {
    for (const symbol of this.config.tradingPairs) {
      for (const [brokerName, broker] of this.brokers) {
        try {
          const price = await broker.getPrice(symbol)

          // Create market data record
          const marketData: MarketData = {
            id: `${brokerName}_${symbol}_${Date.now()}`,
            symbol,
            timestamp: new Date(),
            open: price, // Simplified - would need actual OHLC data
            high: price,
            low: price,
            close: price,
            volume: 0, // Would need actual volume data
            source: brokerName as any,
          }

          // Process with all active strategies
          await this.processMarketData(marketData)

          // Store market data
          await supabase.from("market_data").insert(marketData)
        } catch (error) {
          logger.error("Failed to collect market data", {
            error,
            symbol,
            broker: brokerName,
            userId: this.config.userId,
          })
        }
      }
    }
  }

  private async processMarketData(marketData: MarketData): Promise<void> {
    if (!this.config.autoTrading) return

    // Check daily loss limit
    if (this.dailyPnL < -this.config.maxDailyLoss) {
      logger.warn("Daily loss limit reached, skipping trading", {
        dailyPnL: this.dailyPnL,
        userId: this.config.userId,
      })
      return
    }

    // Check cooldown period
    const now = Date.now()
    if (now - this.lastTradeTime < this.config.cooldownPeriod) {
      return
    }

    // Process with each active strategy
    for (const [strategyId, { strategy, config }] of this.strategies) {
      if (!config.is_active) continue

      try {
        strategy.onMarketData(marketData)

        // Get market context
        const context = await this.getMarketContext(marketData.symbol)

        // Analyze for signals
        const signal = strategy.analyze([marketData], context)

        if (signal && this.shouldExecuteSignal(signal)) {
          await this.executeSignal(signal, strategyId)
        }
      } catch (error) {
        logger.error("Strategy processing error", {
          error,
          strategyId,
          userId: this.config.userId,
        })
      }
    }
  }

  private async executeSignal(signal: TradeSignal, strategyId: string): Promise<void> {
    try {
      // Check if we can place more trades
      if (this.activeTrades.size >= this.config.maxConcurrentTrades) {
        logger.info("Max concurrent trades reached", {
          signal,
          userId: this.config.userId,
        })
        return
      }

      // Get the appropriate broker for this symbol
      const broker = this.getBrokerForSymbol(signal.symbol)
      if (!broker) {
        logger.warn("No broker available for symbol", {
          symbol: signal.symbol,
          userId: this.config.userId,
        })
        return
      }

      // Get account balance
      const balances = await broker.getBalance()
      const baseAsset = this.getBaseAsset(signal.symbol)
      const balance = balances.find((b) => b.asset === baseAsset)

      if (!balance || balance.free < 10) {
        logger.warn("Insufficient balance for trade", {
          signal,
          balance,
          userId: this.config.userId,
        })
        return
      }

      // Calculate position size
      const currentPrice = await broker.getPrice(signal.symbol)
      const positionSize = this.calculatePositionSize(balance.free, currentPrice, signal)

      // In demo mode, simulate the trade
      if (this.config.demoMode) {
        await this.simulateTrade(signal, strategyId, positionSize, currentPrice)
        return
      }

      // Place real order
      const order = await broker.placeOrder({
        symbol: signal.symbol,
        side: signal.signal_type === "buy" ? "buy" : "sell",
        type: "market",
        quantity: positionSize,
      })

      // Create trade record
      const trade: Trade = {
        id: `trade_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        user_id: this.config.userId,
        strategy_id: strategyId,
        symbol: signal.symbol,
        side: signal.signal_type === "buy" ? "buy" : "sell",
        entry_price: order.executedPrice || order.price,
        quantity: order.executedQuantity,
        stop_loss: signal.stop_loss,
        take_profit: signal.take_profit,
        status: "open",
        fees: order.fees,
        execution_time: new Date(),
        broker: "binance", // Would be dynamic
        metadata: {
          signal_strength: signal.strength,
          reasoning: signal.reasoning,
          demo_mode: false,
        },
      }

      // Save to database
      await supabase.from("trades").insert(trade)

      // Add to active trades
      this.activeTrades.set(trade.id, trade)
      this.lastTradeTime = Date.now()

      // Mark signal as executed
      await supabase.from("trade_signals").update({ executed: true }).eq("id", signal.id)

      logger.info("Live trade executed", {
        trade,
        signal,
        userId: this.config.userId,
      })

      // Notify strategy
      const strategyData = this.strategies.get(strategyId)
      if (strategyData) {
        strategyData.strategy.onTrade(signal, true)
      }
    } catch (error) {
      logger.error("Failed to execute live trade", {
        error,
        signal,
        userId: this.config.userId,
      })

      // Notify strategy of failed execution
      const strategyData = this.strategies.get(strategyId)
      if (strategyData) {
        strategyData.strategy.onTrade(signal, false)
      }
    }
  }

  private async simulateTrade(
    signal: TradeSignal,
    strategyId: string,
    positionSize: number,
    currentPrice: number,
  ): Promise<void> {
    // Create simulated trade record
    const trade: Trade = {
      id: `demo_trade_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      user_id: this.config.userId,
      strategy_id: strategyId,
      symbol: signal.symbol,
      side: signal.signal_type === "buy" ? "buy" : "sell",
      entry_price: currentPrice,
      quantity: positionSize,
      stop_loss: signal.stop_loss,
      take_profit: signal.take_profit,
      status: "open",
      fees: currentPrice * positionSize * 0.001, // Simulate 0.1% fee
      execution_time: new Date(),
      broker: "demo",
      metadata: {
        signal_strength: signal.strength,
        reasoning: signal.reasoning,
        demo_mode: true,
      },
    }

    // Save to database
    await supabase.from("trades").insert(trade)

    // Add to active trades
    this.activeTrades.set(trade.id, trade)
    this.lastTradeTime = Date.now()

    logger.info("Demo trade simulated", {
      trade,
      signal,
      userId: this.config.userId,
    })
  }

  private startTradeMonitoring(): void {
    // Monitor active trades every 10 seconds
    this.monitoringInterval = setInterval(async () => {
      if (!this.isRunning) return

      try {
        await this.monitorActiveTrades()
      } catch (error) {
        logger.error("Trade monitoring error", { error, userId: this.config.userId })
      }
    }, 10000)
  }

  private async monitorActiveTrades(): Promise<void> {
    for (const [tradeId, trade] of this.activeTrades) {
      try {
        const broker = this.getBrokerForSymbol(trade.symbol)
        if (!broker) continue

        const currentPrice = await broker.getPrice(trade.symbol)

        // Check stop loss
        if (this.shouldTriggerStopLoss(trade, currentPrice)) {
          await this.closeTrade(tradeId, currentPrice, "stop_loss")
        }
        // Check take profit
        else if (this.shouldTriggerTakeProfit(trade, currentPrice)) {
          await this.closeTrade(tradeId, currentPrice, "take_profit")
        }
      } catch (error) {
        logger.error("Error monitoring trade", {
          error,
          tradeId,
          userId: this.config.userId,
        })
      }
    }
  }

  private shouldTriggerStopLoss(trade: Trade, currentPrice: number): boolean {
    if (!trade.stop_loss) return false

    if (trade.side === "buy") {
      return currentPrice <= trade.stop_loss
    } else {
      return currentPrice >= trade.stop_loss
    }
  }

  private shouldTriggerTakeProfit(trade: Trade, currentPrice: number): boolean {
    if (!trade.take_profit) return false

    if (trade.side === "buy") {
      return currentPrice >= trade.take_profit
    } else {
      return currentPrice <= trade.take_profit
    }
  }

  private async closeTrade(tradeId: string, exitPrice: number, reason: string): Promise<void> {
    const trade = this.activeTrades.get(tradeId)
    if (!trade) return

    try {
      // In demo mode, just simulate the close
      if (this.config.demoMode || trade.metadata?.demo_mode) {
        await this.simulateTradeClose(trade, exitPrice, reason)
        return
      }

      // Get broker and place closing order
      const broker = this.getBrokerForSymbol(trade.symbol)
      if (!broker) return

      const closeOrder = await broker.placeOrder({
        symbol: trade.symbol,
        side: trade.side === "buy" ? "sell" : "buy",
        type: "market",
        quantity: trade.quantity,
      })

      // Calculate PnL
      const pnl = this.calculatePnL(trade, exitPrice)
      this.dailyPnL += pnl

      // Update trade in database
      await supabase
        .from("trades")
        .update({
          status: "closed",
          exit_price: exitPrice,
          close_time: new Date().toISOString(),
          pnl: pnl,
        })
        .eq("id", tradeId)

      // Remove from active trades
      this.activeTrades.delete(tradeId)

      logger.info("Live trade closed", {
        tradeId,
        exitPrice,
        pnl,
        reason,
        userId: this.config.userId,
      })
    } catch (error) {
      logger.error("Failed to close live trade", {
        error,
        tradeId,
        userId: this.config.userId,
      })
    }
  }

  private async simulateTradeClose(trade: Trade, exitPrice: number, reason: string): Promise<void> {
    // Calculate PnL
    const pnl = this.calculatePnL(trade, exitPrice)
    this.dailyPnL += pnl

    // Update trade in database
    await supabase
      .from("trades")
      .update({
        status: "closed",
        exit_price: exitPrice,
        close_time: new Date().toISOString(),
        pnl: pnl,
      })
      .eq("id", trade.id)

    // Remove from active trades
    this.activeTrades.delete(trade.id)

    logger.info("Demo trade closed", {
      tradeId: trade.id,
      exitPrice,
      pnl,
      reason,
      userId: this.config.userId,
    })
  }

  private calculatePnL(trade: Trade, exitPrice: number): number {
    const entryValue = trade.entry_price * trade.quantity
    const exitValue = exitPrice * trade.quantity

    if (trade.side === "buy") {
      return exitValue - entryValue - trade.fees
    } else {
      return entryValue - exitValue - trade.fees
    }
  }

  private shouldExecuteSignal(signal: TradeSignal): boolean {
    return signal.strength >= 0.6 && this.activeTrades.size < this.config.maxConcurrentTrades
  }

  private calculatePositionSize(balance: number, price: number, signal: TradeSignal): number {
    const riskAmount = balance * this.config.riskPerTrade
    const stopDistance = Math.abs(price - (signal.stop_loss || price * 0.98))
    return Math.min(riskAmount / stopDistance, (balance * 0.1) / price)
  }

  private async getMarketContext(symbol: string): Promise<any> {
    // Get recent market data for context
    const { data: recentData } = await supabase
      .from("market_data")
      .select("*")
      .eq("symbol", symbol)
      .order("timestamp", { ascending: false })
      .limit(20)

    const latestPrice = recentData?.[0]?.close || 0

    return {
      currentPrice: latestPrice,
      volume: recentData?.[0]?.volume || 0,
      volatility: this.calculateVolatility(recentData?.map((d) => d.close) || []),
      trend: "sideways" as const,
    }
  }

  private calculateVolatility(prices: number[]): number {
    if (prices.length < 2) return 0

    const returns = []
    for (let i = 1; i < prices.length; i++) {
      returns.push((prices[i] - prices[i - 1]) / prices[i - 1])
    }

    const mean = returns.reduce((a, b) => a + b, 0) / returns.length
    const variance = returns.reduce((acc, ret) => acc + Math.pow(ret - mean, 2), 0) / returns.length

    return Math.sqrt(variance) * Math.sqrt(252) // Annualized volatility
  }

  private getBrokerForSymbol(symbol: string): BaseBroker | null {
    // Simple logic - return first available broker
    // In production, this would route based on symbol availability and user preferences
    return this.brokers.values().next().value || null
  }

  private getBaseAsset(symbol: string): string {
    return symbol.replace(/USDT|BUSD|USD|BTC|ETH$/, "")
  }

  // Public methods for external control
  async updateConfig(newConfig: Partial<LiveTradingConfig>): Promise<void> {
    this.config = { ...this.config, ...newConfig }
    logger.info("Live trading engine config updated", {
      userId: this.config.userId,
      changes: newConfig,
    })
  }

  getStatus() {
    return {
      isRunning: this.isRunning,
      activeTrades: this.activeTrades.size,
      activeStrategies: this.strategies.size,
      dailyPnL: this.dailyPnL,
      connectedBrokers: Array.from(this.brokers.keys()),
      config: this.config,
    }
  }
}
