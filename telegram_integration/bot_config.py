"""
Telegram Bot Configuration
Manages bot settings, credentials, and environment variables
"""

import os
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class TelegramBotConfig:
    """Telegram bot configuration"""
    
    # Bot credentials
    bot_token: str
    chat_id: str
    
    # Operation mode
    use_webhook: bool = False
    webhook_url: Optional[str] = None
    webhook_port: int = 8443
    
    # Alert settings
    confirmation_timeout: int = 60  # seconds
    alert_cooldown: int = 5  # seconds
    max_pending_confirmations: int = 5
    
    # Retry settings
    max_retries: int = 3
    retry_delay: int = 2  # seconds
    
    # Message settings
    enable_notifications: bool = True
    enable_preview: bool = False
    
    @classmethod
    def from_env(cls) -> 'TelegramBotConfig':
        """
        Load configuration from environment variables
        
        Required environment variables:
        - TELEGRAM_BOT_TOKEN: Bot API token from @BotFather
        - TELEGRAM_CHAT_ID: Your chat ID (get from @userinfobot)
        
        Optional:
        - TELEGRAM_USE_WEBHOOK: 'true' to enable webhook mode
        - TELEGRAM_WEBHOOK_URL: Webhook URL if webhook mode enabled
        - TELEGRAM_WEBHOOK_PORT: Webhook port (default: 8443)
        """
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
        if not chat_id:
            raise ValueError("TELEGRAM_CHAT_ID environment variable not set")
        
        use_webhook = os.getenv('TELEGRAM_USE_WEBHOOK', 'false').lower() == 'true'
        webhook_url = os.getenv('TELEGRAM_WEBHOOK_URL')
        webhook_port = int(os.getenv('TELEGRAM_WEBHOOK_PORT', '8443'))
        
        if use_webhook and not webhook_url:
            logger.warning("Webhook mode enabled but no TELEGRAM_WEBHOOK_URL set, falling back to polling")
            use_webhook = False
        
        return cls(
            bot_token=bot_token,
            chat_id=chat_id,
            use_webhook=use_webhook,
            webhook_url=webhook_url,
            webhook_port=webhook_port,
            confirmation_timeout=int(os.getenv('TELEGRAM_CONFIRMATION_TIMEOUT', '60')),
            alert_cooldown=int(os.getenv('TELEGRAM_ALERT_COOLDOWN', '5')),
            max_pending_confirmations=int(os.getenv('TELEGRAM_MAX_PENDING', '5')),
        )
    
    def validate(self) -> bool:
        """Validate configuration"""
        if not self.bot_token or len(self.bot_token) < 10:
            logger.error("Invalid bot token")
            return False
        
        if not self.chat_id:
            logger.error("Invalid chat ID")
            return False
        
        if self.use_webhook and not self.webhook_url:
            logger.error("Webhook mode requires webhook URL")
            return False
        
        return True
    
    def __repr__(self) -> str:
        """Safe string representation (hides sensitive data)"""
        return f"""TelegramBotConfig(
    bot_token='***{self.bot_token[-6:]}',
    chat_id='{self.chat_id}',
    mode='{'webhook' if self.use_webhook else 'polling'}',
    webhook_url='{self.webhook_url if self.use_webhook else 'N/A'}'
)"""


class BotConfigManager:
    """Manages bot configuration lifecycle"""
    
    _instance = None
    _config: Optional[TelegramBotConfig] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_config(cls) -> TelegramBotConfig:
        """Get current configuration (singleton)"""
        if cls._config is None:
            cls._config = TelegramBotConfig.from_env()
            if not cls._config.validate():
                raise ValueError("Invalid Telegram bot configuration")
            logger.info(f"Telegram config loaded: {cls._config}")
        return cls._config
    
    @classmethod
    def set_config(cls, config: TelegramBotConfig) -> None:
        """Set custom configuration"""
        if not config.validate():
            raise ValueError("Invalid configuration")
        cls._config = config
        logger.info("Custom Telegram config set")
    
    @classmethod
    def reset(cls) -> None:
        """Reset configuration (mainly for testing)"""
        cls._config = None


# Example .env file content:
"""
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321

# Optional: Webhook mode (default: polling)
# TELEGRAM_USE_WEBHOOK=true
# TELEGRAM_WEBHOOK_URL=https://yourdomain.com/telegram/webhook
# TELEGRAM_WEBHOOK_PORT=8443

# Optional: Alert settings
# TELEGRAM_CONFIRMATION_TIMEOUT=60
# TELEGRAM_ALERT_COOLDOWN=5
# TELEGRAM_MAX_PENDING=5
"""
