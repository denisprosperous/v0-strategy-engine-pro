#!/usr/bin/env python3
"""
Main Telegram Bot

Handles bot initialization, authentication, and command routing.

Author: v0-strategy-engine-pro
Version: 1.0.0
"""

import logging
import os
import sys
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram_integration.api_client import api_client
from telegram_integration import handlers
from telegram_integration.utils import format_error_message

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TradingBot:
    """
    Main trading bot class.
    
    Manages bot lifecycle, authentication, and command registration.
    """
    
    def __init__(self):
        """Initialize the bot."""
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
        
        self.admin_username = os.getenv("ADMIN_USERNAME", "admin")
        self.admin_password = os.getenv("ADMIN_PASSWORD", "changeme")
        
        self.application = None
        logger.info("Trading bot initialized")
    
    async def authenticate_backend(self):
        """
        Authenticate with backend API on startup.
        
        Returns:
            bool: True if authentication successful
        """
        logger.info("Authenticating with backend API...")
        
        result = await api_client.authenticate(
            self.admin_username,
            self.admin_password
        )
        
        if result.get("success"):
            logger.info("\u2705 Successfully authenticated with backend")
            return True
        else:
            logger.error(f"\u274c Authentication failed: {result}")
            return False
    
    def register_handlers(self):
        """
        Register all command and message handlers.
        """
        # Command handlers
        self.application.add_handler(CommandHandler("start", handlers.start_command))
        self.application.add_handler(CommandHandler("help", handlers.help_command))
        self.application.add_handler(CommandHandler("status", handlers.status_command))
        self.application.add_handler(CommandHandler("portfolio", handlers.portfolio_command))
        self.application.add_handler(CommandHandler("signals", handlers.signals_command))
        self.application.add_handler(CommandHandler("performance", handlers.performance_command))
        self.application.add_handler(CommandHandler("startbot", handlers.start_bot_command))
        self.application.add_handler(CommandHandler("stopbot", handlers.stop_bot_command))
        self.application.add_handler(CommandHandler("mode", handlers.mode_command))
        self.application.add_handler(CommandHandler("ai_analysis", handlers.ai_analysis_command))
        self.application.add_handler(CommandHandler("sentiment", handlers.sentiment_command))
        
        # Message handler for non-commands
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message)
        )
        
        logger.info("All command handlers registered")
    
    async def post_init(self, application: Application):
        """
        Post-initialization tasks.
        
        Args:
            application: The telegram application
        """
        logger.info("Running post-initialization tasks...")
        
        # Authenticate with backend
        authenticated = await self.authenticate_backend()
        
        if not authenticated:
            logger.warning(
                "Failed to authenticate with backend. "
                "Bot will start but some features may not work."
            )
    
    async def post_shutdown(self, application: Application):
        """
        Post-shutdown cleanup tasks.
        
        Args:
            application: The telegram application
        """
        logger.info("Running post-shutdown cleanup...")
        
        # Close API client session
        await api_client.close()
        
        logger.info("Cleanup complete")
    
    def run(self):
        """
        Start the bot.
        """
        logger.info("\ud83d\ude80 Starting Telegram Trading Bot...")
        
        # Create application
        self.application = (
            Application.builder()
            .token(self.token)
            .post_init(self.post_init)
            .post_shutdown(self.post_shutdown)
            .build()
        )
        
        # Register handlers
        self.register_handlers()
        
        # Start bot
        logger.info("\ud83e\udd16 Bot is now running. Press Ctrl+C to stop.")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """
    Main entry point.
    """
    try:
        bot = TradingBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("\ud83d\uded1 Bot stopped by user")
    except Exception as e:
        logger.error(f"\u274c Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
