// Script to start the Telegram bot service
import { tradingBot } from "../lib/telegram/bot"
import { marketDataAggregator } from "../lib/market-data/aggregator"
import { sentimentAnalyzer } from "../lib/sentiment/analyzer"
import { logger } from "../lib/utils/logger"

async function startTelegramBot() {
  try {
    logger.info("Starting Telegram bot service...")

    // Start market data services first
    await marketDataAggregator.start()
    await sentimentAnalyzer.start()

    // Start the Telegram bot
    await tradingBot.start()

    logger.info("Telegram bot service started successfully")

    // Handle graceful shutdown
    process.on("SIGINT", async () => {
      logger.info("Shutting down Telegram bot service...")

      await tradingBot.stop()
      await marketDataAggregator.stop()
      await sentimentAnalyzer.stop()

      logger.info("Telegram bot service stopped")
      process.exit(0)
    })
  } catch (error) {
    logger.error("Failed to start Telegram bot service", { error })
    process.exit(1)
  }
}

// Start the service if this file is run directly
if (require.main === module) {
  startTelegramBot()
}

export { startTelegramBot }
