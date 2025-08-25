// Centralized logging utility
export enum LogLevel {
  ERROR = 0,
  WARN = 1,
  INFO = 2,
  DEBUG = 3,
}

interface LogEntry {
  timestamp: Date
  level: LogLevel
  message: string
  metadata?: Record<string, any>
  userId?: string
  tradeId?: string
}

class Logger {
  private level: LogLevel

  constructor(level: LogLevel = LogLevel.INFO) {
    this.level = level
  }

  private log(level: LogLevel, message: string, metadata?: Record<string, any>) {
    if (level <= this.level) {
      const entry: LogEntry = {
        timestamp: new Date(),
        level,
        message,
        metadata,
      }

      // In production, send to external logging service
      if (process.env.NODE_ENV === "production") {
        // Send to logging service (e.g., DataDog, LogRocket, etc.)
        this.sendToExternalLogger(entry)
      } else {
        console.log(JSON.stringify(entry, null, 2))
      }
    }
  }

  private sendToExternalLogger(entry: LogEntry) {
    // Implementation for external logging service
    // For now, just console.log in production too
    console.log(JSON.stringify(entry))
  }

  error(message: string, metadata?: Record<string, any>) {
    this.log(LogLevel.ERROR, message, metadata)
  }

  warn(message: string, metadata?: Record<string, any>) {
    this.log(LogLevel.WARN, message, metadata)
  }

  info(message: string, metadata?: Record<string, any>) {
    this.log(LogLevel.INFO, message, metadata)
  }

  debug(message: string, metadata?: Record<string, any>) {
    this.log(LogLevel.DEBUG, message, metadata)
  }

  trade(message: string, tradeId: string, metadata?: Record<string, any>) {
    this.log(LogLevel.INFO, `[TRADE] ${message}`, { ...metadata, tradeId })
  }

  strategy(message: string, strategyId: string, metadata?: Record<string, any>) {
    this.log(LogLevel.INFO, `[STRATEGY] ${message}`, { ...metadata, strategyId })
  }
}

export const logger = new Logger(process.env.NODE_ENV === "development" ? LogLevel.DEBUG : LogLevel.INFO)
