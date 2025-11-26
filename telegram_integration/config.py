#!/usr/bin/env python3
"""
Telegram Bot Configuration Module

Securely loads Telegram bot configuration from environment variables.
Follows best practices for secret management and API security.

Author: v0-strategy-engine-pro
Version: 1.0
"""

import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TelegramConfig:
    """
    Configuration class for Telegram Bot integration.
    
    Loads all necessary configuration from environment variables
    with appropriate validation and fallbacks.
    """
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        # Core bot configuration
        self.bot_token = self._get_telegram_token()
        self.api_base_url = os.getenv("TRADING_API_URL", "http://localhost:8000/api")
        
        # Security settings
        self.allowed_user_ids = self._parse_allowed_users()
        self.admin_user_ids = self._parse_admin_users()
        
        # Bot behavior settings
        self.polling_timeout = int(os.getenv("TELEGRAM_POLLING_TIMEOUT", "30"))
        self.command_timeout = int(os.getenv("TELEGRAM_COMMAND_TIMEOUT", "60"))
        self.rate_limit_enabled = os.getenv("TELEGRAM_RATE_LIMIT", "true").lower() == "true"
        
        # Notification settings
        self.enable_trade_notifications = os.getenv("ENABLE_TRADE_NOTIFICATIONS", "true").lower() == "true"
        self.enable_signal_notifications = os.getenv("ENABLE_SIGNAL_NOTIFICATIONS", "true").lower() == "true"
        self.enable_error_notifications = os.getenv("ENABLE_ERROR_NOTIFICATIONS", "true").lower() == "true"
        
        # Webhook settings (if using webhook mode instead of polling)
        self.webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL", "")
        self.webhook_port = int(os.getenv("TELEGRAM_WEBHOOK_PORT", "8443"))
        self.use_webhook = bool(self.webhook_url)
        
        logger.info("Telegram configuration loaded successfully")
        logger.info(f"Bot mode: {'Webhook' if self.use_webhook else 'Polling'}")
        logger.info(f"API URL: {self.api_base_url}")
    
    def _get_telegram_token(self) -> str:
        """
        Get Telegram bot token from environment.
        
        Returns:
            str: Telegram bot token
            
        Raises:
            RuntimeError: If token is not found in environment
        """
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN not found in environment variables. \n"
                "Please set it using: export TELEGRAM_BOT_TOKEN='your-token-here' \n"
                "Get your token from @BotFather on Telegram."
            )
        return token
    
    def _parse_allowed_users(self) -> Optional[list]:
        """
        Parse allowed user IDs from environment.
        
        Returns:
            Optional[list]: List of allowed user IDs, or None if not set (allows all)
        """
        users_str = os.getenv("TELEGRAM_ALLOWED_USERS", "")
        if not users_str:
            logger.warning("No TELEGRAM_ALLOWED_USERS set - bot accessible to all users")
            return None
        
        try:
            user_ids = [int(uid.strip()) for uid in users_str.split(",") if uid.strip()]
            logger.info(f"Allowed users configured: {len(user_ids)} user(s)")
            return user_ids
        except ValueError as e:
            logger.error(f"Error parsing TELEGRAM_ALLOWED_USERS: {e}")
            return None
    
    def _parse_admin_users(self) -> list:
        """
        Parse admin user IDs from environment.
        
        Returns:
            list: List of admin user IDs
        """
        admins_str = os.getenv("TELEGRAM_ADMIN_USERS", "")
        if not admins_str:
            logger.warning("No TELEGRAM_ADMIN_USERS set - no admin privileges")
            return []
        
        try:
            admin_ids = [int(uid.strip()) for uid in admins_str.split(",") if uid.strip()]
            logger.info(f"Admin users configured: {len(admin_ids)} user(s)")
            return admin_ids
        except ValueError as e:
            logger.error(f"Error parsing TELEGRAM_ADMIN_USERS: {e}")
            return []
    
    def is_user_allowed(self, user_id: int) -> bool:
        """
        Check if user is allowed to use the bot.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if user is allowed, False otherwise
        """
        if self.allowed_user_ids is None:
            return True
        return user_id in self.allowed_user_ids or user_id in self.admin_user_ids
    
    def is_admin(self, user_id: int) -> bool:
        """
        Check if user has admin privileges.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if user is admin, False otherwise
        """
        return user_id in self.admin_user_ids


# Global configuration instance
_config_instance: Optional[TelegramConfig] = None


def get_config() -> TelegramConfig:
    """
    Get or create global configuration instance.
    
    Returns:
        TelegramConfig: Configuration instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = TelegramConfig()
    return _config_instance


def get_telegram_token() -> str:
    """
    Convenience function to get Telegram bot token.
    
    Returns:
        str: Telegram bot token
    """
    return get_config().bot_token
