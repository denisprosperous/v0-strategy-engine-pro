import { redis } from "@/lib/config/database"
import { config } from "@/lib/config/environment"

// Professional trading settings with recommended ranges
export interface TradingSettings {
  // Risk Management
  defaultStopLoss: number
  defaultTakeProfit: number
  maxDailyLoss: number
  maxPositionSize: number
  maxOpenTrades: number

  // Trading Mode
  tradingMode: "demo" | "paper" | "live"
  demoEnabled: boolean
  demoInitialBalance: number

  // Backtesting
  backtestEnabled: boolean
  backtestStartDate: string
  backtestEndDate: string

  // Trade Settings
  defaultTradeSize: number

  // AI Models
  aiPrimaryModel: string
  aiFallbackModel: string
  aiSentimentModel: string

  // Logging
  logLevel: "debug" | "info" | "warn" | "error"
  enableStructuredLogs: boolean
  enableProfiling: boolean

  // Performance
  dbPoolSize: number
  dbMaxOverflow: number
  dataRefreshInterval: number
}

// Professional recommended settings with explanations
export const SETTING_RECOMMENDATIONS: Record<
  keyof TradingSettings,
  {
    min?: number
    max?: number
    recommended: number | string | boolean
    description: string
    riskLevel: "low" | "medium" | "high"
  }
> = {
  defaultStopLoss: {
    min: 0.005,
    max: 0.05,
    recommended: 0.02,
    description: "Stop loss percentage (2% is industry standard for professional traders)",
    riskLevel: "medium",
  },
  defaultTakeProfit: {
    min: 0.01,
    max: 0.2,
    recommended: 0.06,
    description: "Take profit percentage (6% gives 1:3 risk/reward ratio)",
    riskLevel: "medium",
  },
  maxDailyLoss: {
    min: 100,
    max: 5000,
    recommended: 500,
    description: "Maximum daily loss before trading stops ($500 protects capital)",
    riskLevel: "low",
  },
  maxPositionSize: {
    min: 100,
    max: 10000,
    recommended: 2000,
    description: "Maximum position size per trade ($2000 limits single-trade risk)",
    riskLevel: "medium",
  },
  maxOpenTrades: {
    min: 1,
    max: 20,
    recommended: 5,
    description: "Maximum concurrent open trades (5 balances opportunity vs risk)",
    riskLevel: "medium",
  },
  tradingMode: {
    recommended: "demo",
    description: "Trading mode - start with demo, then paper, then live",
    riskLevel: "low",
  },
  demoEnabled: {
    recommended: true,
    description: "Enable demo trading for testing strategies",
    riskLevel: "low",
  },
  demoInitialBalance: {
    min: 1000,
    max: 100000,
    recommended: 10000,
    description: "Demo account starting balance ($10k simulates realistic trading)",
    riskLevel: "low",
  },
  backtestEnabled: {
    recommended: true,
    description: "Enable backtesting to validate strategies before live trading",
    riskLevel: "low",
  },
  backtestStartDate: {
    recommended: "2024-01-01",
    description: "Backtest start date (1 year of data recommended)",
    riskLevel: "low",
  },
  backtestEndDate: {
    recommended: "2024-12-31",
    description: "Backtest end date",
    riskLevel: "low",
  },
  defaultTradeSize: {
    min: 50,
    max: 5000,
    recommended: 200,
    description: "Default trade size ($200 = 2% of $10k account)",
    riskLevel: "medium",
  },
  aiPrimaryModel: {
    recommended: "openai",
    description: "Primary AI for analysis (OpenAI GPT-4o is most accurate)",
    riskLevel: "low",
  },
  aiFallbackModel: {
    recommended: "groq",
    description: "Fallback AI when primary fails (Groq is fastest)",
    riskLevel: "low",
  },
  aiSentimentModel: {
    recommended: "perplexity",
    description: "AI for sentiment analysis (Perplexity has real-time web access)",
    riskLevel: "low",
  },
  logLevel: {
    recommended: "info",
    description: "Logging verbosity (info for production, debug for development)",
    riskLevel: "low",
  },
  enableStructuredLogs: {
    recommended: true,
    description: "Use JSON structured logs for better parsing",
    riskLevel: "low",
  },
  enableProfiling: {
    recommended: false,
    description: "Performance profiling (disable in production for performance)",
    riskLevel: "low",
  },
  dbPoolSize: {
    min: 5,
    max: 50,
    recommended: 10,
    description: "Database connection pool size (10 handles typical load)",
    riskLevel: "low",
  },
  dbMaxOverflow: {
    min: 5,
    max: 100,
    recommended: 20,
    description: "Maximum overflow connections for peak loads",
    riskLevel: "low",
  },
  dataRefreshInterval: {
    min: 1,
    max: 60,
    recommended: 5,
    description: "Data refresh interval in seconds (5s balances freshness vs API limits)",
    riskLevel: "low",
  },
}

const SETTINGS_KEY = "trading:settings:custom"

// Get current settings (Redis overrides > env vars > defaults)
export async function getSettings(): Promise<TradingSettings> {
  // Get custom overrides from Redis
  let customSettings: Partial<TradingSettings> = {}

  try {
    const stored = await redis.get(SETTINGS_KEY)
    if (stored) {
      customSettings = typeof stored === "string" ? JSON.parse(stored) : stored
    }
  } catch (error) {
    console.error("Failed to load custom settings from Redis:", error)
  }

  // Merge: defaults < env vars < Redis overrides
  const settings: TradingSettings = {
    defaultStopLoss: customSettings.defaultStopLoss ?? config.risk.defaultStopLoss,
    defaultTakeProfit: customSettings.defaultTakeProfit ?? config.risk.defaultTakeProfit,
    maxDailyLoss: customSettings.maxDailyLoss ?? config.risk.maxDailyLoss,
    maxPositionSize: customSettings.maxPositionSize ?? config.risk.maxPositionSize,
    maxOpenTrades: customSettings.maxOpenTrades ?? config.risk.maxOpenTrades,
    tradingMode: customSettings.tradingMode ?? config.trading.mode,
    demoEnabled: customSettings.demoEnabled ?? config.trading.demoEnabled,
    demoInitialBalance: customSettings.demoInitialBalance ?? config.trading.demoInitialBalance,
    backtestEnabled: customSettings.backtestEnabled ?? config.trading.backtestEnabled,
    backtestStartDate: customSettings.backtestStartDate ?? config.trading.backtestStartDate,
    backtestEndDate: customSettings.backtestEndDate ?? config.trading.backtestEndDate,
    defaultTradeSize: customSettings.defaultTradeSize ?? config.trading.defaultTradeSize,
    aiPrimaryModel: customSettings.aiPrimaryModel ?? config.ai.primaryModel,
    aiFallbackModel: customSettings.aiFallbackModel ?? config.ai.fallbackModel,
    aiSentimentModel: customSettings.aiSentimentModel ?? config.ai.sentimentModel,
    logLevel: customSettings.logLevel ?? config.logging.level,
    enableStructuredLogs: customSettings.enableStructuredLogs ?? config.logging.structuredLogs,
    enableProfiling: customSettings.enableProfiling ?? config.logging.enableProfiling,
    dbPoolSize: customSettings.dbPoolSize ?? config.performance.dbPoolSize,
    dbMaxOverflow: customSettings.dbMaxOverflow ?? config.performance.dbMaxOverflow,
    dataRefreshInterval: customSettings.dataRefreshInterval ?? config.performance.dataRefreshInterval,
  }

  return settings
}

// Update settings (stores in Redis)
export async function updateSettings(updates: Partial<TradingSettings>): Promise<TradingSettings> {
  // Validate settings
  const errors = validateSettings(updates)
  if (errors.length > 0) {
    throw new Error(`Invalid settings: ${errors.join(", ")}`)
  }

  // Get current settings
  const current = await getSettings()

  // Merge updates
  const newSettings = { ...current, ...updates }

  // Store in Redis
  await redis.set(SETTINGS_KEY, JSON.stringify(newSettings))

  return newSettings
}

// Reset to recommended defaults
export async function resetToDefaults(): Promise<TradingSettings> {
  const defaults: TradingSettings = {
    defaultStopLoss: SETTING_RECOMMENDATIONS.defaultStopLoss.recommended as number,
    defaultTakeProfit: SETTING_RECOMMENDATIONS.defaultTakeProfit.recommended as number,
    maxDailyLoss: SETTING_RECOMMENDATIONS.maxDailyLoss.recommended as number,
    maxPositionSize: SETTING_RECOMMENDATIONS.maxPositionSize.recommended as number,
    maxOpenTrades: SETTING_RECOMMENDATIONS.maxOpenTrades.recommended as number,
    tradingMode: SETTING_RECOMMENDATIONS.tradingMode.recommended as "demo" | "paper" | "live",
    demoEnabled: SETTING_RECOMMENDATIONS.demoEnabled.recommended as boolean,
    demoInitialBalance: SETTING_RECOMMENDATIONS.demoInitialBalance.recommended as number,
    backtestEnabled: SETTING_RECOMMENDATIONS.backtestEnabled.recommended as boolean,
    backtestStartDate: SETTING_RECOMMENDATIONS.backtestStartDate.recommended as string,
    backtestEndDate: SETTING_RECOMMENDATIONS.backtestEndDate.recommended as string,
    defaultTradeSize: SETTING_RECOMMENDATIONS.defaultTradeSize.recommended as number,
    aiPrimaryModel: SETTING_RECOMMENDATIONS.aiPrimaryModel.recommended as string,
    aiFallbackModel: SETTING_RECOMMENDATIONS.aiFallbackModel.recommended as string,
    aiSentimentModel: SETTING_RECOMMENDATIONS.aiSentimentModel.recommended as string,
    logLevel: SETTING_RECOMMENDATIONS.logLevel.recommended as "debug" | "info" | "warn" | "error",
    enableStructuredLogs: SETTING_RECOMMENDATIONS.enableStructuredLogs.recommended as boolean,
    enableProfiling: SETTING_RECOMMENDATIONS.enableProfiling.recommended as boolean,
    dbPoolSize: SETTING_RECOMMENDATIONS.dbPoolSize.recommended as number,
    dbMaxOverflow: SETTING_RECOMMENDATIONS.dbMaxOverflow.recommended as number,
    dataRefreshInterval: SETTING_RECOMMENDATIONS.dataRefreshInterval.recommended as number,
  }

  await redis.set(SETTINGS_KEY, JSON.stringify(defaults))

  return defaults
}

// Validate settings against recommended ranges
export function validateSettings(settings: Partial<TradingSettings>): string[] {
  const errors: string[] = []

  for (const [key, value] of Object.entries(settings)) {
    const rec = SETTING_RECOMMENDATIONS[key as keyof TradingSettings]
    if (!rec) continue

    if (typeof value === "number" && rec.min !== undefined && value < rec.min) {
      errors.push(`${key} (${value}) is below minimum (${rec.min})`)
    }
    if (typeof value === "number" && rec.max !== undefined && value > rec.max) {
      errors.push(`${key} (${value}) is above maximum (${rec.max})`)
    }
  }

  // Risk/reward ratio validation
  if (settings.defaultStopLoss && settings.defaultTakeProfit) {
    const ratio = settings.defaultTakeProfit / settings.defaultStopLoss
    if (ratio < 1.5) {
      errors.push(`Risk/reward ratio (${ratio.toFixed(2)}) should be at least 1.5:1`)
    }
  }

  return errors
}

// Get risk assessment
export function assessRisk(settings: TradingSettings): {
  overallRisk: "low" | "medium" | "high"
  factors: Array<{ name: string; risk: "low" | "medium" | "high"; note: string }>
} {
  const factors: Array<{ name: string; risk: "low" | "medium" | "high"; note: string }> = []

  // Stop loss assessment
  if (settings.defaultStopLoss <= 0.01) {
    factors.push({ name: "Stop Loss", risk: "high", note: "Very tight stops may cause premature exits" })
  } else if (settings.defaultStopLoss >= 0.05) {
    factors.push({ name: "Stop Loss", risk: "high", note: "Wide stops increase potential losses" })
  } else {
    factors.push({ name: "Stop Loss", risk: "low", note: "Appropriate stop loss level" })
  }

  // Position size assessment
  if (settings.maxPositionSize > 5000) {
    factors.push({ name: "Position Size", risk: "high", note: "Large positions increase risk" })
  } else if (settings.maxPositionSize < 500) {
    factors.push({ name: "Position Size", risk: "low", note: "Conservative position sizing" })
  } else {
    factors.push({ name: "Position Size", risk: "medium", note: "Moderate position sizing" })
  }

  // Concurrent trades assessment
  if (settings.maxOpenTrades > 10) {
    factors.push({ name: "Open Trades", risk: "high", note: "Many concurrent trades increase exposure" })
  } else if (settings.maxOpenTrades <= 3) {
    factors.push({ name: "Open Trades", risk: "low", note: "Conservative trade count" })
  } else {
    factors.push({ name: "Open Trades", risk: "medium", note: "Moderate trade count" })
  }

  // Trading mode assessment
  if (settings.tradingMode === "live") {
    factors.push({ name: "Trading Mode", risk: "high", note: "Live trading with real funds" })
  } else if (settings.tradingMode === "paper") {
    factors.push({ name: "Trading Mode", risk: "medium", note: "Paper trading (simulated)" })
  } else {
    factors.push({ name: "Trading Mode", risk: "low", note: "Demo mode (no real funds)" })
  }

  // Calculate overall risk
  const highCount = factors.filter((f) => f.risk === "high").length
  const mediumCount = factors.filter((f) => f.risk === "medium").length

  let overallRisk: "low" | "medium" | "high" = "low"
  if (highCount >= 2 || (highCount === 1 && mediumCount >= 2)) {
    overallRisk = "high"
  } else if (highCount >= 1 || mediumCount >= 2) {
    overallRisk = "medium"
  }

  return { overallRisk, factors }
}
