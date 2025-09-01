// Core trading engine that orchestrates strategy execution and order management
import type { BaseBroker } from "../brokers/base-broker"
import type { BaseStrategy } from "../strategies/base-strategy"
import { supabaseServer } from "@/lib/config/supabase-server"
import { logger } from "@/lib/utils/logger"
import type { MarketData, Trade, TradeSignal } from "@/lib/database/schema"

export interface TradingEngineConfig {
  maxConcurrentTrades: number
  maxDailyLoss: number
  riskPerTrade: number
  cooldownPeriod: number
  autoTrading: boolean
  perAssetRiskBudgetPct?: number // e.g., 0.2 of total risk can be in one asset
}

export class TradingEngine {
  private broker: BaseBroker
  private strategies: Map<string, BaseStrategy> = new Map()
  private config: TradingEngineConfig
  private activeTrades: Map<string, Trade> = new Map()
  private dailyPnL = 0
  private lastTradeTime = 0
  private isRunning = false

  constructor(broker: BaseBroker, config: TradingEngineConfig) {
    this.broker = broker
    this.config = config
  }

  async start(): Promise<void> {
    if (this.isRunning) return

    try {
      await this.broker.connect()
      this.isRunning = true

      // Load active trades from database
      await this.loadActiveTrades()

      // Start monitoring loop
      this.startMonitoring()

      logger.info("Trading engine started", { config: this.config })
    } catch (error) {
      logger.error("Failed to start trading engine", { error })
      throw error
    }
  }

  async stop(): Promise<void> {
    this.isRunning = false
    await this.broker.disconnect()
    logger.info("Trading engine stopped")
  }

  addStrategy(id: string, strategy: BaseStrategy): void {
    this.strategies.set(id, strategy)
    logger.info("Strategy added to engine", { strategyId: id, name: strategy.getName() })
  }

  removeStrategy(id: string): void {
    this.strategies.delete(id)
    logger.info("Strategy removed from engine", { strategyId: id })
  }

  async processMarketData(marketData: MarketData): Promise<void> {
    if (!this.isRunning || !this.config.autoTrading) return

    // Check daily loss limit
    if (this.dailyPnL < -this.config.maxDailyLoss) {
      logger.warn("Daily loss limit reached, stopping trading", { dailyPnL: this.dailyPnL })
      return
    }

    // Check cooldown period
    const now = Date.now()
    if (now - this.lastTradeTime < this.config.cooldownPeriod) {
      return
    }

    // Update all strategies with new market data
    for (const [id, strategy] of this.strategies) {
      try {
        strategy.onMarketData(marketData)

        // Get market context
        const context = await this.getMarketContext(marketData.symbol)

        // Analyze for signals
        const signal = strategy.analyze([marketData], context)

        if (signal && this.shouldExecuteSignal(signal)) {
          await this.executeSignal(signal, id)
        }
      } catch (error) {
        logger.error("Strategy processing error", { strategyId: id, error })
      }
    }
  }

  private async executeSignal(signal: TradeSignal, strategyId: string): Promise<void> {
    try {
      // Check if we can place more trades
      if (this.activeTrades.size >= this.config.maxConcurrentTrades) {
        logger.info("Max concurrent trades reached, skipping signal", { signal })
        return
      }

      // Get account balance
      const balances = await this.broker.getBalance()
      const baseAsset = this.getBaseAsset(signal.symbol)
      const balance = balances.find((b) => b.asset === baseAsset)

      if (!balance || balance.free < 10) {
        // Minimum balance check
        logger.warn("Insufficient balance for trade", { signal, balance })
        return
      }

      // Calculate position size
      const currentPrice = await this.broker.getPrice(signal.symbol)
      let positionSize = this.calculatePositionSize(balance.free, currentPrice, signal)

      // Per-asset risk budget: cap exposure per symbol
      if (this.config.perAssetRiskBudgetPct) {
        const existingExposure = Array.from(this.activeTrades.values())
          .filter((t) => t.symbol === signal.symbol)
          .reduce((sum, t) => sum + t.entry_price * t.quantity, 0)
        const maxExposure = balance.free * this.config.perAssetRiskBudgetPct
        const plannedExposure = currentPrice * positionSize
        if (existingExposure + plannedExposure > maxExposure) {
          positionSize = Math.max(0, (maxExposure - existingExposure) / currentPrice)
          if (positionSize * currentPrice < 5) {
            logger.info("Per-asset budget prevents new position", { symbol: signal.symbol })
            return
          }
        }
      }

      // Place order
      const order = await this.broker.placeOrder({
        symbol: signal.symbol,
        side: signal.signal_type === "buy" ? "buy" : "sell",
        type: "market",
        quantity: positionSize,
      })

      // Create trade record
      const trade: Trade = {
        id: `trade_${Date.now()}`,
        user_id: "system", // Will be replaced with actual user ID
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
        broker: "binance", // Will be dynamic based on broker
        metadata: {
          signal_strength: signal.strength,
          reasoning: signal.reasoning,
        },
      }

      // Save to database
      await supabaseServer.from("trades").insert(trade)

      // Add to active trades
      this.activeTrades.set(trade.id, trade)
      this.lastTradeTime = Date.now()

      // Mark signal as executed
      await supabaseServer.from("trade_signals").update({ executed: true }).eq("id", signal.id)

      logger.info("Trade executed successfully", { trade, signal })

      // Notify strategy
      const strategy = this.strategies.get(strategyId)
      if (strategy) {
        strategy.onTrade(signal, true)
      }
    } catch (error) {
      logger.error("Failed to execute signal", { signal, error })

      // Notify strategy of failed execution
      const strategy = this.strategies.get(strategyId)
      if (strategy) {
        strategy.onTrade(signal, false)
      }
    }
  }

  private async loadActiveTrades(): Promise<void> {
    try {
      const { data: trades, error } = await supabaseServer.from("trades").select("*").eq("status", "open")

      if (error) throw error

      for (const trade of trades || []) {
        this.activeTrades.set(trade.id, trade)
      }

      logger.info("Loaded active trades", { count: this.activeTrades.size })
    } catch (error) {
      logger.error("Failed to load active trades", { error })
    }
  }

  private startMonitoring(): void {
    // Monitor active trades every 10 seconds
    const monitorInterval = setInterval(async () => {
      if (!this.isRunning) {
        clearInterval(monitorInterval)
        return
      }

      await this.monitorActiveTrades()
    }, 10000)
  }

  private async monitorActiveTrades(): Promise<void> {
    for (const [tradeId, trade] of this.activeTrades) {
      try {
        const currentPrice = await this.broker.getPrice(trade.symbol)

        // Check stop loss
        if (this.shouldTriggerStopLoss(trade, currentPrice)) {
          await this.closeTrade(tradeId, currentPrice, "stop_loss")
        }
        // Check take profit
        else if (this.shouldTriggerTakeProfit(trade, currentPrice)) {
          await this.closeTrade(tradeId, currentPrice, "take_profit")
        }
      } catch (error) {
        logger.error("Error monitoring trade", { tradeId, error })
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
      // Place closing order
      const closeOrder = await this.broker.placeOrder({
        symbol: trade.symbol,
        side: trade.side === "buy" ? "sell" : "buy",
        type: "market",
        quantity: trade.quantity,
      })

      // Calculate PnL
      const pnl = this.calculatePnL(trade, exitPrice)
      this.dailyPnL += pnl

      // Update trade in database
      await supabaseServer
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

      logger.info("Trade closed", { tradeId, exitPrice, pnl, reason })
    } catch (error) {
      logger.error("Failed to close trade", { tradeId, error })
    }
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
    // Strategy rotation by regime: disable mean reversion in strong trends
    if (signal.strategy_id === "mean_reversion") {
      // Heuristic: skip when many momentum/breakout trades are active
      const trendingActive = Array.from(this.activeTrades.values()).filter(
        (t) => t.strategy_id === "breakout" || t.strategy_id === "momentum",
      ).length
      if (trendingActive > 0) return false
    }

    return signal.strength >= 0.6 && this.activeTrades.size < this.config.maxConcurrentTrades
  }

  private calculatePositionSize(balance: number, price: number, signal: TradeSignal): number {
    const riskAmount = balance * this.config.riskPerTrade
    const stopDistance = Math.abs(price - (signal.stop_loss || price * 0.98))
    return Math.min(riskAmount / stopDistance, (balance * 0.1) / price)
  }

  private async getMarketContext(symbol: string): Promise<any> {
    // Simplified market context - would be enhanced with more data
    const price = await this.broker.getPrice(symbol)
    return {
      currentPrice: price,
      volume: 0,
      volatility: 0,
      trend: "sideways" as const,
    }
  }

  private getBaseAsset(symbol: string): string {
    // Extract base asset from trading pair (e.g., BTCUSDT -> BTC)
    return symbol.replace(/USDT|BUSD|USD|BTC|ETH$/, "")
  }
}
