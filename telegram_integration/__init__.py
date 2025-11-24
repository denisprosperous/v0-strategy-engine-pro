"""
Telegram Integration Package
Provides Telegram bot functionality for institutional sniper strategy alerts
"""

from .sniper_bot import (
    InstitutionalSniperBot,
    EntryAlertData,
    ExitAlertData,
    AlertType,
)

from .bot_config import (
    TelegramBotConfig,
    BotConfigManager,
)

from .alert_manager import (
    AlertManager,
    get_alert_manager,
    initialize_telegram_alerts,
)

__all__ = [
    # Main bot class
    'InstitutionalSniperBot',
    
    # Data structures
    'EntryAlertData',
    'ExitAlertData',
    'AlertType',
    
    # Configuration
    'TelegramBotConfig',
    'BotConfigManager',
    
    # Alert management
    'AlertManager',
    'get_alert_manager',
    'initialize_telegram_alerts',
]

__version__ = '1.0.0'
__author__ = 'V0 Strategy Engine Team'
