#!/usr/bin/env python3
"""
Utility Functions for Telegram Bot

Provides helper functions for:
- Mode validation and normalization
- Message formatting
- Error handling
- Response parsing

Author: v0-strategy-engine-pro
Version: 1.0.0
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def validate_trading_mode(mode: str) -> bool:
    """
    Validate trading mode value.
    
    Args:
        mode: Trading mode to validate
        
    Returns:
        True if valid, False otherwise
    """
    valid_modes = ['auto', 'manual', 'semi-auto']
    return mode.lower() in valid_modes


def normalize_trading_mode(mode: str) -> str:
    """
    Normalize trading mode to backend-compatible format.
    
    Converts shorthand "semi" to "semi-auto" for backend compatibility.
    
    Args:
        mode: Trading mode input
        
    Returns:
        Normalized mode string
        
    Raises:
        ValueError: If mode is invalid
    """
    mode_lower = mode.lower().strip()
    
    # Convert shorthand to full format
    if mode_lower == 'semi':
        return 'semi-auto'
    
    # Validate and return
    if mode_lower in ['auto', 'manual', 'semi-auto']:
        return mode_lower
    
    raise ValueError(f"Invalid trading mode: {mode}. Must be 'auto', 'manual', or 'semi-auto'")


def format_error_message(error_data: Dict[str, Any]) -> str:
    """
    Format error data into user-friendly message.
    
    Args:
        error_data: Error dictionary from API client
        
    Returns:
        Formatted error message
    """
    if "error" not in error_data:
        return "An unknown error occurred"
    
    message = f"\u274c **Error**: {error_data['error']}\n\n"
    
    if "details" in error_data:
        message += f"**Details**: {error_data['details']}\n"
    
    if "error_code" in error_data:
        message += f"\n_Error Code: {error_data['error_code']}_"
    
    return message


def format_bot_status(status_data: Dict[str, Any]) -> str:
    """
    Format bot status into readable message.
    
    Args:
        status_data: Status dictionary from API
        
    Returns:
        Formatted status message
    """
    if "error" in status_data:
        return format_error_message(status_data)
    
    status_icon = "\u2705" if status_data.get("is_running") else "\u26d4"
    mode = status_data.get("mode", "unknown").upper()
    ai_status = "Enabled" if status_data.get("ai_enabled") else "Disabled"
    
    message = f"{status_icon} **Bot Status**\n\n"
    message += f"**Running**: {status_data.get('is_running', False)}\n"
    message += f"**Mode**: {mode}\n"
    message += f"**AI**: {ai_status}\n"
    message += f"**Active Signals**: {status_data.get('active_signals', 0)}\n"
    message += f"**Open Positions**: {status_data.get('open_positions', 0)}\n"
    
    if "connected_exchanges" in status_data:
        exchanges = ", ".join(status_data["connected_exchanges"])
        message += f"**Exchanges**: {exchanges}\n"
    
    return message


def format_portfolio(balances: list) -> str:
    """
    Format portfolio balances into readable message.
    
    Args:
        balances: List of balance dictionaries
        
    Returns:
        Formatted portfolio message
    """
    if isinstance(balances, dict) and "error" in balances:
        return format_error_message(balances)
    
    message = "\ud83d\udcb0 **Portfolio Balances**\n\n"
    
    total_value = 0
    for balance in balances:
        asset = balance.get("asset", "???")
        total = balance.get("total", 0)
        free = balance.get("free", 0)
        locked = balance.get("locked", 0)
        usd_value = balance.get("usd_value", 0)
        
        total_value += usd_value
        
        message += f"**{asset}**\n"
        message += f"  Total: {total:.8f}\n"
        message += f"  Free: {free:.8f}\n"
        message += f"  Locked: {locked:.8f}\n"
        message += f"  Value: ${usd_value:,.2f}\n\n"
    
    message += f"\n\ud83d\udcca **Total Portfolio Value**: ${total_value:,.2f}"
    
    return message


def format_signals(signals: list) -> str:
    """
    Format trading signals into readable message.
    
    Args:
        signals: List of signal dictionaries
        
    Returns:
        Formatted signals message
    """
    if isinstance(signals, dict) and "error" in signals:
        return format_error_message(signals)
    
    if not signals:
        return "\ud83d\udce1 No recent signals found."
    
    message = "\ud83d\udce1 **Recent Trading Signals**\n\n"
    
    for signal in signals[:5]:  # Limit to 5 signals
        symbol = signal.get("symbol", "???")
        direction = signal.get("direction", "???").upper()
        tier = signal.get("tier", "?")
        confidence = signal.get("confidence", 0) * 100
        status = signal.get("status", "unknown").upper()
        
        direction_icon = "\ud83d\udcc8" if direction == "LONG" else "\ud83d\udcc9"
        status_icon = "\u2705" if status == "ACTIVE" else "\u2714"
        
        message += f"{direction_icon} **{symbol}** - {direction}\n"
        message += f"  Tier: {tier} | Confidence: {confidence:.1f}%\n"
        message += f"  Entry: ${signal.get('entry_price', 0):,.2f}\n"
        message += f"  TP1: ${signal.get('take_profit_1', 0):,.2f}\n"
        message += f"  SL: ${signal.get('stop_loss', 0):,.2f}\n"
        message += f"  Status: {status_icon} {status}\n\n"
    
    return message


def format_performance(metrics: Dict[str, Any]) -> str:
    """
    Format performance metrics into readable message.
    
    Args:
        metrics: Performance metrics dictionary
        
    Returns:
        Formatted performance message
    """
    if "error" in metrics:
        return format_error_message(metrics)
    
    message = "\ud83d\udcc8 **Performance Metrics**\n\n"
    
    total_pnl = metrics.get("total_pnl", 0)
    total_pnl_pct = metrics.get("total_pnl_pct", 0)
    pnl_icon = "\ud83d\udfe2" if total_pnl >= 0 else "\ud83d\udd34"
    
    message += f"{pnl_icon} **Total P&L**: ${total_pnl:,.2f} ({total_pnl_pct:+.2f}%)\n"
    message += f"**Daily P&L**: ${metrics.get('daily_pnl', 0):,.2f} ({metrics.get('daily_pnl_pct', 0):+.2f}%)\n\n"
    
    message += f"**Win Rate**: {metrics.get('win_rate', 0):.1f}%\n"
    message += f"**Total Trades**: {metrics.get('total_trades', 0)}\n"
    message += f"  Winning: {metrics.get('winning_trades', 0)}\n"
    message += f"  Losing: {metrics.get('losing_trades', 0)}\n\n"
    
    message += f"**Sharpe Ratio**: {metrics.get('sharpe_ratio', 0):.2f}\n"
    message += f"**Max Drawdown**: {metrics.get('max_drawdown', 0):.2f}%\n"
    
    return message


def format_ai_analysis(analysis: Dict[str, Any]) -> str:
    """
    Format AI analysis into readable message.
    
    Args:
        analysis: AI analysis dictionary
        
    Returns:
        Formatted analysis message
    """
    if "error" in analysis:
        return format_error_message(analysis)
    
    symbol = analysis.get("symbol", "Market")
    trend = analysis.get("trend", "neutral").upper()
    strength = analysis.get("strength", 0)
    
    trend_icon = "\ud83d\udcc8" if trend == "BULLISH" else "\ud83d\udcc9" if trend == "BEARISH" else "\u27a1\ufe0f"
    
    message = f"\ud83e\udd16 **AI Analysis - {symbol}**\n\n"
    message += f"{trend_icon} **Trend**: {trend} (Strength: {strength}/10)\n"
    message += f"**Recommendation**: {analysis.get('recommendation', 'hold').upper()}\n"
    message += f"**Confidence**: {analysis.get('confidence', 0)*100:.1f}%\n\n"
    
    if "indicators" in analysis:
        message += "**Indicators**:\n"
        for indicator, data in analysis["indicators"].items():
            signal = data.get("signal", "neutral")
            message += f"  {indicator.upper()}: {signal}\n"
        message += "\n"
    
    if "summary" in analysis:
        message += f"**Summary**: {analysis['summary']}"
    
    return message


def format_sentiment(sentiment: Dict[str, Any]) -> str:
    """
    Format sentiment analysis into readable message.
    
    Args:
        sentiment: Sentiment dictionary
        
    Returns:
        Formatted sentiment message
    """
    if "error" in sentiment:
        return format_error_message(sentiment)
    
    symbol = sentiment.get("symbol", "Market")
    overall = sentiment.get("overall_sentiment", "neutral").upper()
    score = sentiment.get("sentiment_score", 0) * 100
    
    sentiment_icon = "\ud83d\ude0a" if overall == "POSITIVE" else "\ud83d\ude41" if overall == "NEGATIVE" else "\ud83d\ude10"
    
    message = f"{sentiment_icon} **Sentiment Analysis - {symbol}**\n\n"
    message += f"**Overall**: {overall} ({score:.1f}%)\n"
    message += f"**Fear & Greed Index**: {sentiment.get('fear_greed_index', 50)} - {sentiment.get('fear_greed_label', 'Neutral')}\n\n"
    
    if "sources" in sentiment:
        message += "**Sources**:\n"
        for source, data in sentiment["sources"].items():
            sent_score = data.get("sentiment", 0) * 100
            volume = data.get("volume", 0)
            message += f"  {source.title()}: {sent_score:.0f}% ({volume:,} mentions)\n"
        message += "\n"
    
    if "summary" in sentiment:
        message += f"**Summary**: {sentiment['summary']}"
    
    return message


def parse_command_args(text: str) -> tuple:
    """
    Parse command and arguments from message text.
    
    Args:
        text: Message text
        
    Returns:
        Tuple of (command, args_list)
    """
    parts = text.strip().split()
    if not parts:
        return ("", [])
    
    command = parts[0].lstrip("/").lower()
    args = parts[1:] if len(parts) > 1 else []
    
    return (command, args)
