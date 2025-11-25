"""
Telegram Integration Tests

Comprehensive test suite for telegram_integration module including:
- Configuration validation
- Alert formatting and sending
- Button interactions
- Error handling and retries
- Integration with trading callbacks
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from decimal import Decimal

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from telegram_integration.bot_config import TelegramBotConfig, BotConfigManager
from telegram_integration.sniper_bot import (
    SniperTelegramBot,
    AlertType,
    AlertPriority,
    EntryAlert,
    ExitAlert
)
from telegram_integration.alert_manager import AlertManager


class TestBotConfiguration:
    """Test TelegramBotConfig and BotConfigManager"""
    
    def setup_method(self):
        """Reset config before each test"""
        BotConfigManager.reset()
    
    def test_config_from_env_valid(self, monkeypatch):
        """Test config loads from environment variables"""
        monkeypatch.setenv('TELEGRAM_BOT_TOKEN', '123456789:ABCdefGHI')
        monkeypatch.setenv('TELEGRAM_CHAT_ID', '987654321')
        
        config = TelegramBotConfig.from_env()
        
        assert config.bot_token == '123456789:ABCdefGHI'
        assert config.chat_id == '987654321'
        assert config.use_webhook == False
    
    def test_config_missing_token(self, monkeypatch):
        """Test config fails gracefully when token missing"""
        monkeypatch.delenv('TELEGRAM_BOT_TOKEN', raising=False)
        monkeypatch.setenv('TELEGRAM_CHAT_ID', '987654321')
        
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
            TelegramBotConfig.from_env()
    
    def test_config_missing_chat_id(self, monkeypatch):
        """Test config fails when chat ID missing"""
        monkeypatch.setenv('TELEGRAM_BOT_TOKEN', '123456789:ABC')
        monkeypatch.delenv('TELEGRAM_CHAT_ID', raising=False)
        
        with pytest.raises(ValueError, match="TELEGRAM_CHAT_ID"):
            TelegramBotConfig.from_env()
    
    def test_config_webhook_mode(self, monkeypatch):
        """Test webhook configuration"""
        monkeypatch.setenv('TELEGRAM_BOT_TOKEN', '123456789:ABC')
        monkeypatch.setenv('TELEGRAM_CHAT_ID', '987654321')
        monkeypatch.setenv('TELEGRAM_USE_WEBHOOK', 'true')
        monkeypatch.setenv('TELEGRAM_WEBHOOK_URL', 'https://example.com/webhook')
        
        config = TelegramBotConfig.from_env()
        
        assert config.use_webhook == True
        assert config.webhook_url == 'https://example.com/webhook'
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Valid config
        valid_config = TelegramBotConfig(
            bot_token="123456789:ABCdefGHI",
            chat_id="987654321"
        )
        assert valid_config.validate() == True
        
        # Invalid token
        invalid_config = TelegramBotConfig(
            bot_token="short",
            chat_id="987654321"
        )
        assert invalid_config.validate() == False
    
    def test_config_singleton(self, monkeypatch):
        """Test BotConfigManager singleton pattern"""
        monkeypatch.setenv('TELEGRAM_BOT_TOKEN', '123456789:ABC')
        monkeypatch.setenv('TELEGRAM_CHAT_ID', '987654321')
        
        config1 = BotConfigManager.get_config()
        config2 = BotConfigManager.get_config()
        
        assert config1 is config2


class TestAlertFormatting:
    """Test alert message formatting"""
    
    @pytest.fixture
    def mock_bot(self):
        """Create mock bot for testing"""
        config = TelegramBotConfig(
            bot_token="test_token",
            chat_id="test_chat_id"
        )
        with patch('telegram_integration.sniper_bot.Application'):
            bot = SniperTelegramBot(config)
            return bot
    
    def test_entry_alert_formatting(self, mock_bot):
        """Test entry alert message format"""
        alert = EntryAlert(
            alert_type=AlertType.ENTRY,
            priority=AlertPriority.HIGH,
            token_address="0x123abc",
            token_symbol="PEPE",
            token_name="Pepe Coin",
            wallet_address="0xwallet123",
            buy_amount_usd=Decimal('50000'),
            sniper_score=95.5,
            win_rate=0.75,
            avg_profit=0.45,
            total_trades=150,
            timestamp=datetime(2025, 11, 25, 12, 0, 0)
        )
        
        message = mock_bot._format_entry_alert(alert)
        
        assert "🎯 SNIPER ENTRY SIGNAL" in message
        assert "PEPE" in message
        assert "0x123abc" in message
        assert "$50,000" in message
        assert "95.5" in message
        assert "75.0%" in message
    
    def test_exit_alert_formatting(self, mock_bot):
        """Test exit alert message format"""
        alert = ExitAlert(
            alert_type=AlertType.EXIT,
            priority=AlertPriority.MEDIUM,
            token_address="0x123abc",
            token_symbol="PEPE",
            position_size_usd=Decimal('1000'),
            entry_price=Decimal('0.001'),
            current_price=Decimal('0.0015'),
            profit_loss_usd=Decimal('500'),
            profit_loss_percent=50.0,
            hold_time_minutes=120,
            timestamp=datetime(2025, 11, 25, 14, 0, 0)
        )
        
        message = mock_bot._format_exit_alert(alert)
        
        assert "💰 EXIT SIGNAL" in message or "TAKE PROFIT" in message
        assert "PEPE" in message
        assert "+50.0%" in message
        assert "$500" in message


class TestAlertSending:
    """Test alert sending functionality"""
    
    @pytest.fixture
    async def mock_bot(self):
        """Create mock bot with mocked Telegram application"""
        config = TelegramBotConfig(
            bot_token="test_token",
            chat_id="test_chat_id"
        )
        
        with patch('telegram_integration.sniper_bot.Application') as MockApp:
            mock_app_instance = AsyncMock()
            MockApp.builder.return_value.token.return_value.build.return_value = mock_app_instance
            
            bot = SniperTelegramBot(config)
            bot.bot = AsyncMock()
            bot.bot.send_message = AsyncMock()
            
            return bot
    
    @pytest.mark.asyncio
    async def test_send_entry_alert(self, mock_bot):
        """Test sending entry alert"""
        await mock_bot.send_entry_alert(
            token_address="0x123abc",
            token_symbol="PEPE",
            token_name="Pepe Coin",
            wallet_address="0xwallet",
            buy_amount_usd=50000,
            sniper_score=95.5,
            win_rate=0.75,
            avg_profit=0.45,
            total_trades=150
        )
        
        assert mock_bot.bot.send_message.called
    
    @pytest.mark.asyncio
    async def test_send_exit_alert(self, mock_bot):
        """Test sending exit alert"""
        await mock_bot.send_exit_alert(
            token_address="0x123abc",
            token_symbol="PEPE",
            position_size_usd=1000,
            entry_price=0.001,
            current_price=0.0015,
            profit_loss_usd=500,
            profit_loss_percent=50.0,
            hold_time_minutes=120
        )
        
        assert mock_bot.bot.send_message.called
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_bot):
        """Test alert rate limiting"""
        # Send multiple alerts quickly
        for _ in range(3):
            await mock_bot.send_entry_alert(
                token_address="0x123abc",
                token_symbol="PEPE",
                token_name="Test",
                wallet_address="0xwallet",
                buy_amount_usd=10000,
                sniper_score=90,
                win_rate=0.7,
                avg_profit=0.4,
                total_trades=100
            )
        
        # Should be rate limited
        assert mock_bot.alert_cooldown_timer is not None


class TestAlertManager:
    """Test AlertManager high-level orchestration"""
    
    @pytest.fixture
    async def mock_alert_manager(self):
        """Create mock alert manager"""
        entry_callback = AsyncMock()
        exit_callback = AsyncMock()
        
        config = TelegramBotConfig(
            bot_token="test_token",
            chat_id="test_chat_id"
        )
        
        with patch('telegram_integration.alert_manager.SniperTelegramBot'):
            manager = AlertManager(
                config=config,
                entry_callback=entry_callback,
                exit_callback=exit_callback
            )
            manager.bot = AsyncMock()
            manager.bot.send_entry_alert = AsyncMock()
            manager.bot.send_exit_alert = AsyncMock()
            
            return manager
    
    @pytest.mark.asyncio
    async def test_send_entry_alert_via_manager(self, mock_alert_manager):
        """Test sending entry alert through AlertManager"""
        await mock_alert_manager.send_entry_alert(
            token_address="0x123",
            token_symbol="TEST",
            wallet_address="0xwallet",
            buy_amount_usd=10000
        )
        
        assert mock_alert_manager.bot.send_entry_alert.called
    
    @pytest.mark.asyncio
    async def test_manager_lifecycle(self, mock_alert_manager):
        """Test AlertManager start/stop lifecycle"""
        mock_alert_manager.bot.start = AsyncMock()
        mock_alert_manager.bot.stop = AsyncMock()
        
        await mock_alert_manager.start()
        assert mock_alert_manager.is_running
        
        await mock_alert_manager.stop()
        assert not mock_alert_manager.is_running


class TestErrorHandling:
    """Test error handling and retries"""
    
    @pytest.mark.asyncio
    async def test_send_alert_with_retry(self):
        """Test alert sending with retry on failure"""
        config = TelegramBotConfig(
            bot_token="test_token",
            chat_id="test_chat_id",
            max_retries=3
        )
        
        with patch('telegram_integration.sniper_bot.Application'):
            bot = SniperTelegramBot(config)
            bot.bot = AsyncMock()
            
            # Simulate failure then success
            bot.bot.send_message = AsyncMock(
                side_effect=[Exception("Network error"), None]
            )
            
            # Should succeed on retry
            await bot.send_entry_alert(
                token_address="0x123",
                token_symbol="TEST",
                token_name="Test Token",
                wallet_address="0xwallet",
                buy_amount_usd=1000,
                sniper_score=90,
                win_rate=0.7,
                avg_profit=0.4,
                total_trades=50
            )
    
    @pytest.mark.asyncio
    async def test_invalid_config_handling(self):
        """Test handling of invalid configuration"""
        invalid_config = TelegramBotConfig(
            bot_token="short",
            chat_id=""
        )
        
        with pytest.raises(ValueError):
            BotConfigManager.set_config(invalid_config)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
