#!/usr/bin/env python3
"""
Telegram Bot Command Handlers

Implements all bot commands and message handlers.

Author: v0-strategy-engine-pro
Version: 1.0.0
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from telegram_integration.api_client import api_client
from telegram_integration.utils import (
    format_error_message,
    format_bot_status,
    format_portfolio,
    format_signals,
    format_performance,
    format_ai_analysis,
    format_sentiment,
    normalize_trading_mode,
    validate_trading_mode,
    parse_command_args
)

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    user = update.effective_user
    logger.info(f"User {user.username} started the bot")
    
    welcome_message = (
        f"\ud83d\udc4b Welcome {user.mention_html()}!\n\n"
        f"I'm your **AI-Enhanced Trading Bot** assistant. I can help you:\n\n"
        f"\ud83d\udcca Monitor your portfolio\n"
        f"\ud83d\udce1 Track trading signals\n"
        f"\ud83d\udcc8 View performance metrics\n"
        f"\ud83e\udd16 Get AI market analysis\n"
        f"\u2699\ufe0f Control bot settings\n\n"
        f"Use /help to see all available commands."
    )
    
    await update.message.reply_html(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /help command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    help_text = (
        "\ud83d\udcda **Available Commands**\n\n"
        
        "**\ud83d\udcca Portfolio & Trading**\n"
        "/status - Bot status and overview\n"
        "/portfolio - View portfolio balances\n"
        "/signals - Recent trading signals\n"
        "/performance - Performance metrics\n\n"
        
        "**\u2699\ufe0f Bot Control**\n"
        "/startbot - Start the trading bot\n"
        "/stopbot - Stop the trading bot\n"
        "/mode [auto|manual|semi] - Set trading mode\n\n"
        
        "**\ud83e\udd16 AI Features**\n"
        "/ai_analysis [symbol] - Get AI market analysis\n"
        "/sentiment [symbol] - Get sentiment analysis\n\n"
        
        "**\u2139\ufe0f Info**\n"
        "/help - Show this help message\n"
    )
    
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /status command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    logger.info(f"User {update.effective_user.username} requested status")
    
    # Send "typing" indicator
    await update.message.chat.send_action("typing")
    
    # Get status from API
    status_data = await api_client.get_bot_status()
    
    # Format and send response
    message = format_bot_status(status_data)
    await update.message.reply_text(message, parse_mode="Markdown")


async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /portfolio command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    logger.info(f"User {update.effective_user.username} requested portfolio")
    
    await update.message.chat.send_action("typing")
    
    # Get portfolio from API
    balances = await api_client.get_portfolio_balances()
    
    # Format and send response
    message = format_portfolio(balances)
    await update.message.reply_text(message, parse_mode="Markdown")


async def signals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /signals command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    logger.info(f"User {update.effective_user.username} requested signals")
    
    await update.message.chat.send_action("typing")
    
    # Get signals from API
    signals = await api_client.get_recent_signals(limit=5)
    
    # Format and send response
    message = format_signals(signals)
    await update.message.reply_text(message, parse_mode="Markdown")


async def performance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /performance command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    logger.info(f"User {update.effective_user.username} requested performance")
    
    await update.message.chat.send_action("typing")
    
    # Get performance metrics from API
    metrics = await api_client.get_performance_metrics()
    
    # Format and send response
    message = format_performance(metrics)
    await update.message.reply_text(message, parse_mode="Markdown")


async def start_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /startbot command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    logger.info(f"User {update.effective_user.username} requested to start bot")
    
    await update.message.chat.send_action("typing")
    
    # Start bot via API
    result = await api_client.start_bot()
    
    if "error" in result:
        message = format_error_message(result)
    else:
        message = "\u2705 **Trading bot started successfully!**\n\nThe bot is now actively monitoring markets and executing trades."
    
    await update.message.reply_text(message, parse_mode="Markdown")


async def stop_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /stopbot command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    logger.info(f"User {update.effective_user.username} requested to stop bot")
    
    await update.message.chat.send_action("typing")
    
    # Stop bot via API
    result = await api_client.stop_bot()
    
    if "error" in result:
        message = format_error_message(result)
    else:
        message = "\u26d4 **Trading bot stopped successfully!**\n\nThe bot has stopped all trading activities."
    
    await update.message.reply_text(message, parse_mode="Markdown")


async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /mode command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    logger.info(f"User {update.effective_user.username} requested mode change")
    
    # Parse arguments
    command, args = parse_command_args(update.message.text)
    
    if not args:
        await update.message.reply_text(
            "\u26a0\ufe0f **Usage**: /mode [auto|manual|semi]\n\n"
            "**Modes**:\n"
            "\u2022 auto - Fully automated trading\n"
            "\u2022 manual - Manual confirmation required\n"
            "\u2022 semi - Semi-automated (AI suggestions)",
            parse_mode="Markdown"
        )
        return
    
    mode_input = args[0]
    
    try:
        # Normalize mode (converts "semi" to "semi-auto")
        mode = normalize_trading_mode(mode_input)
        
        await update.message.chat.send_action("typing")
        
        # Set mode via API
        result = await api_client.set_bot_mode(mode)
        
        if "error" in result:
            message = format_error_message(result)
        else:
            message = f"\u2705 **Trading mode changed to: {mode.upper()}**"
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    except ValueError as e:
        await update.message.reply_text(
            f"\u274c **Error**: {str(e)}\n\n"
            f"Valid modes: auto, manual, semi-auto (or just 'semi')",
            parse_mode="Markdown"
        )


async def ai_analysis_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /ai_analysis command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    logger.info(f"User {update.effective_user.username} requested AI analysis")
    
    # Parse arguments
    command, args = parse_command_args(update.message.text)
    symbol = args[0] if args else None
    
    await update.message.chat.send_action("typing")
    
    # Get AI analysis from API
    analysis = await api_client.get_ai_analysis(symbol)
    
    # Format and send response
    message = format_ai_analysis(analysis)
    await update.message.reply_text(message, parse_mode="Markdown")


async def sentiment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /sentiment command.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    logger.info(f"User {update.effective_user.username} requested sentiment analysis")
    
    # Parse arguments
    command, args = parse_command_args(update.message.text)
    symbol = args[0] if args else None
    
    await update.message.chat.send_action("typing")
    
    # Get sentiment from API
    sentiment = await api_client.get_sentiment(symbol)
    
    # Format and send response
    message = format_sentiment(sentiment)
    await update.message.reply_text(message, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle non-command text messages.
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    logger.info(f"User {update.effective_user.username} sent message: {update.message.text}")
    
    # For now, just acknowledge and suggest using commands
    await update.message.reply_text(
        "\ud83d\udc4b I received your message! \n\n"
        "I work best with commands. Try /help to see what I can do!",
        parse_mode="Markdown"
    )
