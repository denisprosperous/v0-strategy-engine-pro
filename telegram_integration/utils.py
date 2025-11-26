#!/usr/bin/env python3
"""
Utility Functions for Telegram Bot

Helper functions for formatting messages, validating input,
and common operations.

Author: v0-strategy-engine-pro
Version: 1.0
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from telegram_integration.config import get_config

logger = logging.getLogger(__name__)


def format_timestamp(timestamp: str) -> str:
    """
    Format ISO timestamp to readable string.
    
    Args:
        timestamp: ISO format timestamp
        
    Returns:
        Formatted timestamp string
    """
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        return timestamp


def format_currency(amount: float, symbol: str = "$") -> str:
    """
    Format currency amount.
    
    Args:
        amount: Amount to format
        symbol: Currency symbol
        
    Returns:
        Formatted currency string
    """
    return f"{symbol}{amount:,.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format percentage value.
    
    Args:
        value: Percentage value
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    return f"{value:.{decimals}f}%"


def format_balance_message(balances: List[Dict[str, Any]]) -> str:
    """
    Format balance data into readable message.
    
    Args:
        balances: List of balance dictionaries
        
    Returns:
        Formatted message string
    """
    if not balances:
        return "⚠️ No balance data available"
    
    message = "💰 *Portfolio Balances*\n\n"
    
    total_value = 0
    for balance in balances:
        asset = balance.get('asset', 'UNKNOWN')
        total = balance.get('total', 0)
        free = balance.get('free', 0)
        locked = balance.get('locked', 0)
        usd_value = balance.get('usd_value', 0)
        
        total_value += usd_value
        
        message += f"*{asset}*\n"
        message += f"  Total: `{total:.8f}`\n"
        message += f"  Free: `{free:.8f}`\n"
        if locked > 0:
            message += f"  Locked: `{locked:.8f}`\n"
        message += f"  Value: `{format_currency(usd_value)}`\n\n"
    
    message += f"─" * 30 + "\n"
    message += f"*Total Portfolio Value:* `{format_currency(total_value)}`"
    
    return message


def format_signal_message(signal: Dict[str, Any]) -> str:
    """
    Format trading signal into readable message.
    
    Args:
        signal: Signal dictionary
        
    Returns:
        Formatted message string
    """
    symbol = signal.get('symbol', 'UNKNOWN')
    direction = signal.get('direction', 'unknown').upper()
    tier = signal.get('tier', 0)
    confidence = signal.get('confidence', 0) * 100
    entry = signal.get('entry_price', 0)
    stop_loss = signal.get('stop_loss', 0)
    tp1 = signal.get('take_profit_1', 0)
    tp2 = signal.get('take_profit_2', 0)
    status = signal.get('status', 'unknown')
    
    # Emoji based on direction
    direction_emoji = "🟢" if direction == "LONG" else "🔴"
    
    message = f"🚦 *Trading Signal*\n\n"
    message += f"{direction_emoji} *{symbol}* - {direction}\n"
    message += f"Tier: `{tier}` | Confidence: `{confidence:.1f}%`\n\n"
    message += f"🎯 Entry: `{entry:.8f}`\n"
    message += f"⛔ Stop Loss: `{stop_loss:.8f}`\n"
    message += f"✅ TP1: `{tp1:.8f}`\n"
    message += f"🌟 TP2: `{tp2:.8f}`\n\n"
    message += f"Status: `{status.upper()}`"
    
    return message


def format_performance_message(metrics: Dict[str, Any]) -> str:
    """
    Format performance metrics into readable message.
    
    Args:
        metrics: Performance metrics dictionary
        
    Returns:
        Formatted message string
    """
    total_pnl = metrics.get('total_pnl', 0)
    total_pnl_pct = metrics.get('total_pnl_pct', 0)
    daily_pnl = metrics.get('daily_pnl', 0)
    daily_pnl_pct = metrics.get('daily_pnl_pct', 0)
    win_rate = metrics.get('win_rate', 0)
    total_trades = metrics.get('total_trades', 0)
    winning = metrics.get('winning_trades', 0)
    losing = metrics.get('losing_trades', 0)
    sharpe = metrics.get('sharpe_ratio', 0)
    drawdown = metrics.get('max_drawdown', 0)
    
    # Emoji based on PnL
    pnl_emoji = "🟢" if total_pnl > 0 else "🔴"
    
    message = f"📈 *Performance Metrics*\n\n"
    message += f"{pnl_emoji} *Total P&L:* `{format_currency(total_pnl)}` ({format_percentage(total_pnl_pct)})\n"
    message += f"📅 *Daily P&L:* `{format_currency(daily_pnl)}` ({format_percentage(daily_pnl_pct)})\n\n"
    message += f"🎯 *Win Rate:* `{format_percentage(win_rate)}`\n"
    message += f"📊 *Total Trades:* `{total_trades}`\n"
    message += f"  ✅ Winning: `{winning}`\n"
    message += f"  ❌ Losing: `{losing}`\n\n"
    message += f"📉 *Sharpe Ratio:* `{sharpe:.2f}`\n"
    message += f"⚠️ *Max Drawdown:* `{format_percentage(drawdown)}`"
    
    return message


def format_status_message(status: Dict[str, Any]) -> str:
    """
    Format bot status into readable message.
    
    Args:
        status: Status dictionary
        
    Returns:
        Formatted message string
    """
    is_running = status.get('is_running', False)
    mode = status.get('mode', 'unknown')
    ai_enabled = status.get('ai_enabled', False)
    exchanges = status.get('connected_exchanges', [])
    active_signals = status.get('active_signals', 0)
    open_positions = status.get('open_positions', 0)
    
    # Status emoji
    status_emoji = "🟢" if is_running else "🔴"
    
    message = f"🤖 *Bot Status*\n\n"
    message += f"{status_emoji} Status: `{'RUNNING' if is_running else 'STOPPED'}`\n"
    message += f"⚙️ Mode: `{mode.upper()}`\n"
    message += f"🧠 AI: `{'ENABLED' if ai_enabled else 'DISABLED'}`\n\n"
    message += f"🏛️ Exchanges: `{', '.join(exchanges) if exchanges else 'None'}`\n"
    message += f"🚦 Active Signals: `{active_signals}`\n"
    message += f"💼 Open Positions: `{open_positions}`"
    
    return message


def validate_trading_mode(mode: str) -> bool:
    """
    Validate trading mode value.
    
    Args:
        mode: Trading mode to validate
        
    Returns:
        True if valid, False otherwise
    """
    valid_modes = ['auto', 'manual', 'semi-auto', 'semi']
    return mode.lower() in valid_modes


def check_user_permission(update: Update) -> bool:
    """
    Check if user has permission to use the bot.
    
    Args:
        update: Telegram update object
        
    Returns:
        True if user is allowed, False otherwise
    """
    config = get_config()
    user_id = update.effective_user.id
    
    if not config.is_user_allowed(user_id):
        logger.warning(f"Unauthorized access attempt by user {user_id}")
        return False
    
    return True


def check_admin_permission(update: Update) -> bool:
    """
    Check if user has admin permissions.
    
    Args:
        update: Telegram update object
        
    Returns:
        True if user is admin, False otherwise
    """
    config = get_config()
    user_id = update.effective_user.id
    return config.is_admin(user_id)


async def send_error_message(update: Update, context: ContextTypes.DEFAULT_TYPE, error_msg: str):
    """
    Send formatted error message to user.
    
    Args:
        update: Telegram update object
        context: Callback context
        error_msg: Error message to send
    """
    message = f"❌ *Error*\n\n{error_msg}"
    await update.message.reply_text(message, parse_mode='Markdown')


async def send_success_message(update: Update, context: ContextTypes.DEFAULT_TYPE, success_msg: str):
    """
    Send formatted success message to user.
    
    Args:
        update: Telegram update object
        context: Callback context
        success_msg: Success message to send
    """
    message = f"✅ *Success*\n\n{success_msg}"
    await update.message.reply_text(message, parse_mode='Markdown')


def escape_markdown(text: str) -> str:
    """
    Escape special characters for Markdown.
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text
    """
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text
