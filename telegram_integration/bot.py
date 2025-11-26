#!/usr/bin/env python3
"""
Telegram Bot Main Runner

Main entry point for the Telegram bot. Handles bot initialization,
command registration, and polling/webhook setup.

Follows Telegram Bot API best practices and includes:
- Async operation with python-telegram-bot
- Command handler registration
- Bot command menu setup
- Error handling and logging
- Graceful shutdown

Author: v0-strategy-engine-pro
Version: 1.0
"""

import asyncio
import logging
import sys
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# Import configuration
from telegram_integration.config import get_config

# Import handlers (will be implemented in next step)
from telegram_integration.handlers import (
    start_handler,
    help_handler,
    status_handler,
    start_trading_handler,
    stop_trading_handler,
    mode_handler,
    exchanges_handler,
    balance_handler,
    portfolio_handler,
    analyze_handler,
    sentiment_handler,
    signals_handler,
    performance_handler,
    trades_handler,
    error_handler,
    button_callback_handler,
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('telegram_bot.log')
    ]
)
logger = logging.getLogger(__name__)


class TelegramBot:
    """
    Main Telegram Bot class.
    
    Manages bot lifecycle, command registration, and message handling.
    """
    
    def __init__(self):
        """Initialize the bot with configuration."""
        self.config = get_config()
        self.application = None
        logger.info("Telegram Bot initializing...")
    
    async def setup_commands(self):
        """
        Register bot commands with Telegram.
        
        This creates the command menu that users see when typing /
        """
        commands = [
            BotCommand("start", "Start interacting with bot"),
            BotCommand("help", "List all commands"),
            BotCommand("status", "Show system and bot status"),
            BotCommand("start_trading", "Start automated trading"),
            BotCommand("stop_trading", "Stop all trading"),
            BotCommand("mode", "Set trading mode: auto, manual, semi"),
            BotCommand("exchanges", "List connected exchanges"),
            BotCommand("balance", "View account balance"),
            BotCommand("portfolio", "View current positions"),
            BotCommand("analyze", "Market analysis with AI"),
            BotCommand("sentiment", "Get sentiment analysis"),
            BotCommand("signals", "Show recent signals"),
            BotCommand("performance", "Show performance metrics"),
            BotCommand("trades", "Show recent trades"),
        ]
        
        await self.application.bot.set_my_commands(commands)
        logger.info(f"Registered {len(commands)} bot commands")
    
    def setup_handlers(self):
        """
        Register all command and message handlers.
        """
        # Command handlers
        self.application.add_handler(CommandHandler("start", start_handler))
        self.application.add_handler(CommandHandler("help", help_handler))
        self.application.add_handler(CommandHandler("status", status_handler))
        self.application.add_handler(CommandHandler("start_trading", start_trading_handler))
        self.application.add_handler(CommandHandler("stop_trading", stop_trading_handler))
        self.application.add_handler(CommandHandler("mode", mode_handler))
        self.application.add_handler(CommandHandler("exchanges", exchanges_handler))
        self.application.add_handler(CommandHandler("balance", balance_handler))
        self.application.add_handler(CommandHandler("portfolio", portfolio_handler))
        self.application.add_handler(CommandHandler("analyze", analyze_handler))
        self.application.add_handler(CommandHandler("sentiment", sentiment_handler))
        self.application.add_handler(CommandHandler("signals", signals_handler))
        self.application.add_handler(CommandHandler("performance", performance_handler))
        self.application.add_handler(CommandHandler("trades", trades_handler))
        
        # Callback query handler for inline buttons
        self.application.add_handler(CallbackQueryHandler(button_callback_handler))
        
        # Error handler
        self.application.add_error_handler(error_handler)
        
        logger.info("All handlers registered successfully")
    
    async def post_init(self, application):
        """
        Post-initialization hook.
        
        Called after the application is initialized but before polling starts.
        """
        await self.setup_commands()
        logger.info("Bot post-initialization complete")
    
    async def run(self):
        """
        Start the bot.
        
        Uses either polling or webhook mode based on configuration.
        """
        # Build application
        self.application = (
            ApplicationBuilder()
            .token(self.config.bot_token)
            .post_init(self.post_init)
            .build()
        )
        
        # Setup handlers
        self.setup_handlers()
        
        logger.info("="*60)
        logger.info("🤖 Strategy Engine Pro Telegram Bot")
        logger.info("="*60)
        logger.info(f"Mode: {('Webhook' if self.config.use_webhook else 'Polling')}")
        logger.info(f"API: {self.config.api_base_url}")
        logger.info("="*60)
        
        if self.config.use_webhook:
            # Webhook mode (production)
            logger.info(f"Starting webhook on {self.config.webhook_url}:{self.config.webhook_port}")
            await self.application.run_webhook(
                listen="0.0.0.0",
                port=self.config.webhook_port,
                url_path="telegram",
                webhook_url=f"{self.config.webhook_url}/telegram"
            )
        else:
            # Polling mode (development)
            logger.info("Starting polling mode...")
            logger.info("Bot is ready! Waiting for commands...")
            logger.info("Press Ctrl+C to stop")
            await self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )


async def main():
    """
    Main entry point.
    """
    try:
        bot = TelegramBot()
        await bot.run()
    except KeyboardInterrupt:
        logger.info("\n⏸️  Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown complete")
