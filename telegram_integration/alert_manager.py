"""
Telegram Alert Manager
Orchestrates alert sending, tracking, and callback execution for the institutional sniper
"""

import asyncio
import logging
from typing import Optional, Dict, Callable, Any
from datetime import datetime
from dataclasses import asdict

from .sniper_bot import InstitutionalSniperBot, EntryAlertData, ExitAlertData, AlertType
from .bot_config import BotConfigManager

logger = logging.getLogger(__name__)


class AlertManager:
    """
    High-level alert management for institutional sniper strategy
    
    Features:
    - Async alert dispatching
    - Callback registration and execution
    - Alert history and metrics
    - Rate limiting and deduplication
    """
    
    def __init__(self, bot: Optional[InstitutionalSniperBot] = None):
        """Initialize alert manager with optional bot instance"""
        self.bot = bot
        self.callbacks: Dict[str, Callable] = {}
        self.alert_metrics = {
            'total_sent': 0,
            'entry_alerts': 0,
            'exit_alerts': 0,
            'confirmations': 0,
            'rejections': 0,
        }
        self.is_running = False
        logger.info("AlertManager initialized")
    
    async def initialize(self) -> None:
        """Initialize bot if not provided"""
        if self.bot is None:
            config = BotConfigManager.get_config()
            self.bot = InstitutionalSniperBot(
                token=config.bot_token,
                user_chat_id=config.chat_id,
                use_webhook=config.use_webhook,
                webhook_url=config.webhook_url
            )
            logger.info("Bot instance created from config")
        self.is_running = True
    
    def register_callback(self, callback_type: str, handler: Callable) -> None:
        """
        Register callback handler for alert confirmations
        
        Args:
            callback_type: 'entry' or 'exit'
            handler: Async function to call on user confirmation
        """
        self.callbacks[callback_type] = handler
        logger.info(f"Registered {callback_type} callback")
    
    async def send_entry_alert(
        self,
        token_address: str,
        token_symbol: str,
        pool_address: str,
        dex_name: str,
        liquidity_usd: float,
        institutional_count: int,
        tier1_count: int,
        tier2_count: int,
        confidence: float,
        aggregate_buy_volume: float,
        recommended_size_usd: float,
        entry_price: float,
        stop_loss_price: float,
        initial_target_price: float,
    ) -> Optional[str]:
        """
        Send entry alert to Telegram
        
        Returns:
            Confirmation ID if alert sent successfully
        """
        if not self.is_running or not self.bot:
            logger.error("AlertManager not initialized")
            return None
        
        alert_data = EntryAlertData(
            token_address=token_address,
            token_symbol=token_symbol,
            pool_address=pool_address,
            dex_name=dex_name,
            liquidity_usd=liquidity_usd,
            institutional_count=institutional_count,
            tier1_count=tier1_count,
            tier2_count=tier2_count,
            confidence=confidence,
            aggregate_buy_volume=aggregate_buy_volume,
            recommended_size_usd=recommended_size_usd,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            initial_target_price=initial_target_price,
            timestamp=datetime.now()
        )
        
        callback = self.callbacks.get('entry')
        confirmation_id = await self.bot.send_entry_alert(alert_data, callback)
        
        if confirmation_id:
            self.alert_metrics['total_sent'] += 1
            self.alert_metrics['entry_alerts'] += 1
            logger.info(f"Entry alert sent: {token_symbol}")
        
        return confirmation_id
    
    async def send_exit_alert(
        self,
        token_address: str,
        token_symbol: str,
        current_price: float,
        entry_price: float,
        pnl_percentage: float,
        pnl_usd: float,
        reason: str,
        recommended_sell_percentage: int = 100,
    ) -> Optional[str]:
        """
        Send exit alert to Telegram
        
        Returns:
            Confirmation ID if alert sent successfully
        """
        if not self.is_running or not self.bot:
            logger.error("AlertManager not initialized")
            return None
        
        alert_data = ExitAlertData(
            token_address=token_address,
            token_symbol=token_symbol,
            current_price=current_price,
            entry_price=entry_price,
            pnl_percentage=pnl_percentage,
            pnl_usd=pnl_usd,
            reason=reason,
            recommended_sell_percentage=recommended_sell_percentage,
            timestamp=datetime.now()
        )
        
        callback = self.callbacks.get('exit')
        confirmation_id = await self.bot.send_exit_alert(alert_data, callback)
        
        if confirmation_id:
            self.alert_metrics['total_sent'] += 1
            self.alert_metrics['exit_alerts'] += 1
            logger.info(f"Exit alert sent: {token_symbol} (P&L: {pnl_percentage:+.1f}%)")
        
        return confirmation_id
    
    async def send_status_message(self, message: str) -> None:
        """Send status/info message to user"""
        if not self.bot:
            return
        
        try:
            await self.bot.app.bot.send_message(
                chat_id=self.bot.user_chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info("Status message sent")
        except Exception as e:
            logger.error(f"Failed to send status message: {e}")
    
    async def send_error_alert(self, error_message: str, context: Optional[str] = None) -> None:
        """Send error alert to user"""
        if not self.bot:
            return
        
        alert_text = f"⚠️ **ERROR**\n\n{error_message}"
        if context:
            alert_text += f"\n\n**Context:** {context}"
        
        try:
            await self.bot.app.bot.send_message(
                chat_id=self.bot.user_chat_id,
                text=alert_text,
                parse_mode='Markdown'
            )
            logger.warning(f"Error alert sent: {error_message}")
        except Exception as e:
            logger.error(f"Failed to send error alert: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get alert metrics"""
        return {
            **self.alert_metrics,
            'pending_confirmations': len(self.bot.pending_confirmations) if self.bot else 0,
            'active_positions': len(self.bot.active_positions) if self.bot else 0,
        }
    
    async def start(self) -> None:
        """Start the alert manager and bot"""
        await self.initialize()
        if self.bot:
            logger.info("Starting Telegram bot...")
            asyncio.create_task(self.bot.run())
    
    async def stop(self) -> None:
        """Stop the alert manager gracefully"""
        self.is_running = False
        if self.bot:
            await self.bot.stop()
        logger.info("AlertManager stopped")


# Singleton instance
_alert_manager_instance: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get global AlertManager instance (singleton)"""
    global _alert_manager_instance
    if _alert_manager_instance is None:
        _alert_manager_instance = AlertManager()
    return _alert_manager_instance


async def initialize_telegram_alerts(
    entry_callback: Optional[Callable] = None,
    exit_callback: Optional[Callable] = None
) -> AlertManager:
    """
    Initialize Telegram alert system with callbacks
    
    Args:
        entry_callback: Async function(token_address, size_usd) called on buy confirmation
        exit_callback: Async function(token_address, percentage) called on sell confirmation
    
    Returns:
        Initialized AlertManager instance
    """
    manager = get_alert_manager()
    await manager.initialize()
    
    if entry_callback:
        manager.register_callback('entry', entry_callback)
    if exit_callback:
        manager.register_callback('exit', exit_callback)
    
    logger.info("Telegram alert system initialized")
    return manager
