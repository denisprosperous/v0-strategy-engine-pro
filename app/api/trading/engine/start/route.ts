// API endpoint to start the live trading engine
import { NextResponse } from "next/server"
import { withAuth, type AuthenticatedRequest } from "@/lib/auth/middleware"
import { LiveTradingEngine } from "@/lib/trading/engine/live-trading-engine"
import { BinanceBroker } from "@/lib/trading/brokers/binance-broker"
import { supabase } from "@/lib/config/database"
import { logger } from "@/lib/utils/logger"

// Global engine instances per user
const userEngines = new Map<string, LiveTradingEngine>()

async function startEngineHandler(req: AuthenticatedRequest) {
  try {
    if (!req.user) {
      return NextResponse.json({ error: "User not authenticated" }, { status: 401 })
    }

    const { demoMode = true, tradingPairs = ["BTCUSDT", "ETHUSDT"] } = await req.json()

    // Check if engine is already running for this user
    if (userEngines.has(req.user.userId)) {
      return NextResponse.json(
        {
          error: "Trading engine is already running",
          status: userEngines.get(req.user.userId)?.getStatus(),
        },
        { status: 400 },
      )
    }

    // Get user settings
    const { data: user, error: userError } = await supabase
      .from("users")
      .select("settings, api_keys")
      .eq("id", req.user.userId)
      .single()

    if (userError || !user) {
      return NextResponse.json({ error: "User not found" }, { status: 404 })
    }

    // Create engine configuration
    const engineConfig = {
      userId: req.user.userId,
      maxConcurrentTrades: user.settings?.max_concurrent_trades || 5,
      maxDailyLoss: user.settings?.max_daily_loss || 1000,
      riskPerTrade: user.settings?.risk_per_trade || 0.02,
      cooldownPeriod: user.settings?.cooldown_period || 30000, // 30 seconds
      autoTrading: user.settings?.auto_trading_enabled || false,
      demoMode,
      enabledExchanges: ["binance"],
      tradingPairs,
    }

    // Create and initialize engine
    const engine = new LiveTradingEngine(engineConfig)

    // Add brokers (in demo mode, we can use test credentials)
    if (!demoMode && user.api_keys?.binance?.key && user.api_keys?.binance?.secret) {
      const binanceBroker = new BinanceBroker(
        user.api_keys.binance.key,
        user.api_keys.binance.secret,
        false, // Use live trading
      )
      engine.addBroker("binance", binanceBroker)
    } else {
      // Demo mode - use test credentials or mock broker
      const demoBroker = new BinanceBroker(
        "demo_key",
        "demo_secret",
        true, // Use testnet
      )
      engine.addBroker("binance_demo", demoBroker)
    }

    // Initialize and start engine
    await engine.initialize()
    await engine.start()

    // Store engine instance
    userEngines.set(req.user.userId, engine)

    logger.info("Live trading engine started", {
      userId: req.user.userId,
      demoMode,
      tradingPairs,
    })

    return NextResponse.json({
      success: true,
      message: `Live trading engine started in ${demoMode ? "demo" : "live"} mode`,
      status: engine.getStatus(),
    })
  } catch (error) {
    logger.error("Failed to start trading engine", { error, userId: req.user?.userId })
    return NextResponse.json({ error: "Failed to start trading engine" }, { status: 500 })
  }
}

export const POST = withAuth(startEngineHandler)
