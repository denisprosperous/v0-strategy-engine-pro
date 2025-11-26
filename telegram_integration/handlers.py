#!/usr/bin/env python3
"""
Telegram Bot Command Handlers

Implements all command handlers for the Telegram bot interface.
Includes authentication checks, API integration, and formatted responses.

Author: v0-strategy-engine-pro
Version: 1.0
"""

import logging
from typing import List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from telegram_integration.api_client import get_client
from telegram_integration.utils import (
    check_user_permission,
    check_admin_permission,
    send_error_message,
    send_success_message,
    format_balance_message,
    format_signal_message,
    format_performance_message,
    format_status_message,
    validate_trading_mode,
)

logger = logging.getLogger(__name__)


# ========== AUTHENTICATION & WELCOME ==========

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command - Welcome message.
    """
    user = update.effective_user
    
    if not check_user_permission(update):
        await update.message.reply_text(
            "❌ *Access Denied*\n\n"
            "You are not authorized to use this bot.\n"
            "Please contact the administrator.",
            parse_mode='Markdown'
        )
        return
    
    welcome_text = (
        f"👋 Welcome *{user.first_name}*!\n\n"
        "🤖 *Strategy Engine Pro Bot*\n"
        "Your AI-powered trading assistant\n\n"
        "Use /help to see all available commands.\n"
        "Use /status to check bot status.\n\n"
        "⚡ Quick Actions:\n"
        "/balance - Check portfolio\n"
        "/signals - View recent signals\n"
        "/performance - View metrics\n"
    )
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')
    logger.info(f"User {user.id} ({user.username}) started bot")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /help command - List all commands.
    """
    if not check_user_permission(update):
        await send_error_message(update, context, "Access denied")
        return
    
    help_text = (
        "📚 *Available Commands*\n\n"
        "👉 *Bot Control*\n"
        "/start - Start the bot\n"
        "/help - Show this message\n"
        "/status - Bot and system status\n\n"
        "👉 *Trading Control*\n"
        "/start\\_trading - Start automated trading\n"
        "/stop\\_trading - Stop all trading\n"
        "/mode [auto|manual|semi] - Set trading mode\n\n"
        "👉 *Portfolio & Balance*\n"
        "/balance [exchange] - View account balance\n"
        "/portfolio - View open positions\n"
        "/exchanges - List connected exchanges\n\n"
        "👉 *Signals & Analysis*\n"
        "/signals [limit] - Recent trading signals\n"
        "/analyze [symbol] - AI market analysis\n"
        "/sentiment [symbol] - Sentiment analysis\n\n"
        "👉 *Performance*\n"
        "/performance - Performance metrics\n"
        "/trades [limit] - Recent trade history\n\n"
        "💡 *Tip:* Commands with [parameters] are optional"
    )
    
    await update.message.reply_text(help_text, parse_mode='MarkdownV2')


# ========== BOT STATUS & CONTROL ==========

async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /status command - Show bot status.
    """
    if not check_user_permission(update):
        await send_error_message(update, context, "Access denied")
        return
    
    # Show loading message
    loading_msg = await update.message.reply_text("⌛ Loading status...")
    
    try:
        client = get_client()
        status_data = await client.get_status()
        
        if "error" in status_data:
            await loading_msg.edit_text(
                f"❌ Error: {status_data['error']}"
            )
            return
        
        message = format_status_message(status_data)
        
        # Add control buttons
        keyboard = []
        if status_data.get('is_running'):
            keyboard.append([InlineKeyboardButton("⏸️ Stop Trading", callback_data="stop_trading")])
        else:
            keyboard.append([InlineKeyboardButton("▶️ Start Trading", callback_data="start_trading")])
        
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_status")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    except Exception as e:
        logger.error(f"Error in status_handler: {e}")
        await loading_msg.edit_text(f"❌ Error: {str(e)}")


async def start_trading_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start_trading command - Start the bot.
    """
    if not check_user_permission(update):
        await send_error_message(update, context, "Access denied")
        return
    
    if not check_admin_permission(update):
        await send_error_message(update, context, "This command requires admin privileges")
        return
    
    loading_msg = await update.message.reply_text("⌛ Starting trading bot...")
    
    try:
        client = get_client()
        result = await client.start_trading()
        
        if "error" in result:
            await loading_msg.edit_text(f"❌ Error: {result['error']}")
        else:
            await loading_msg.edit_text(
                "✅ *Trading Started*\n\n"
                "The bot is now actively trading.\n"
                "Use /status to monitor.",
                parse_mode='Markdown'
            )
            logger.info(f"Trading started by user {update.effective_user.id}")
    
    except Exception as e:
        logger.error(f"Error starting trading: {e}")
        await loading_msg.edit_text(f"❌ Error: {str(e)}")


async def stop_trading_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /stop_trading command - Stop the bot.
    """
    if not check_user_permission(update):
        await send_error_message(update, context, "Access denied")
        return
    
    if not check_admin_permission(update):
        await send_error_message(update, context, "This command requires admin privileges")
        return
    
    loading_msg = await update.message.reply_text("⌛ Stopping trading bot...")
    
    try:
        client = get_client()
        result = await client.stop_trading()
        
        if "error" in result:
            await loading_msg.edit_text(f"❌ Error: {result['error']}")
        else:
            await loading_msg.edit_text(
                "⏹️ *Trading Stopped*\n\n"
                "The bot has stopped trading.\n"
                "Use /start\\_trading to resume.",
                parse_mode='Markdown'
            )
            logger.info(f"Trading stopped by user {update.effective_user.id}")
    
    except Exception as e:
        logger.error(f"Error stopping trading: {e}")
        await loading_msg.edit_text(f"❌ Error: {str(e)}")


async def mode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /mode command - Set trading mode.
    
    Usage: /mode [auto|manual|semi]
    """
    if not check_user_permission(update):
        await send_error_message(update, context, "Access denied")
        return
    
    if not check_admin_permission(update):
        await send_error_message(update, context, "This command requires admin privileges")
        return
    
    # Check if mode argument provided
    if not context.args or len(context.args) == 0:
        # Show mode selection keyboard
        keyboard = [
            [InlineKeyboardButton("🤖 Auto", callback_data="mode_auto")],
            [InlineKeyboardButton("👤 Manual", callback_data="mode_manual")],
            [InlineKeyboardButton("⚖️ Semi-Auto", callback_data="mode_semi-auto")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚙️ *Select Trading Mode*\n\n"
            "🤖 *Auto:* Fully automated\n"
            "👤 *Manual:* Manual approval required\n"
            "⚖️ *Semi-Auto:* AI suggestions with approval",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    mode = context.args[0].lower()
    
    if not validate_trading_mode(mode):
        await send_error_message(
            update,
            context,
            "Invalid mode. Use: auto, manual, or semi"
        )
        return
    
    loading_msg = await update.message.reply_text(f"⌛ Setting mode to {mode}...")
    
    try:
        client = get_client()
        result = await client.set_mode(mode)
        
        if "error" in result:
            await loading_msg.edit_text(f"❌ Error: {result['error']}")
        else:
            await loading_msg.edit_text(
                f"✅ *Mode Changed*\n\n"
                f"Trading mode set to: `{mode.upper()}`",
                parse_mode='Markdown'
            )
            logger.info(f"Mode changed to {mode} by user {update.effective_user.id}")
    
    except Exception as e:
        logger.error(f"Error setting mode: {e}")
        await loading_msg.edit_text(f"❌ Error: {str(e)}")


# ========== PORTFOLIO & BALANCE ==========

async def exchanges_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /exchanges command - List connected exchanges.
    """
    if not check_user_permission(update):
        await send_error_message(update, context, "Access denied")
        return
    
    loading_msg = await update.message.reply_text("⌛ Fetching exchanges...")
    
    try:
        client = get_client()
        result = await client.get_exchanges()
        
        exchanges = result.get('exchanges', [])
        
        if not exchanges:
            await loading_msg.edit_text("⚠️ No exchanges connected")
            return
        
        message = "🏛️ *Connected Exchanges*\n\n"
        for exchange in exchanges:
            message += f"• {exchange}\n"
        
        await loading_msg.edit_text(message, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error fetching exchanges: {e}")
        await loading_msg.edit_text(f"❌ Error: {str(e)}")


async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /balance command - Show account balance.
    
    Usage: /balance [exchange]
    """
    if not check_user_permission(update):
        await send_error_message(update, context, "Access denied")
        return
    
    exchange = context.args[0] if context.args else None
    
    loading_msg = await update.message.reply_text("⌛ Fetching balance...")
    
    try:
        client = get_client()
        balances = await client.get_balance(exchange)
        
        if "error" in balances:
            await loading_msg.edit_text(f"❌ Error: {balances['error']}")
            return
        
        # Handle both list and dict responses
        if isinstance(balances, dict) and 'balances' in balances:
            balances = balances['balances']
        
        if isinstance(balances, list):
            message = format_balance_message(balances)
        else:
            message = "⚠️ Unable to format balance data"
        
        await loading_msg.edit_text(message, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error fetching balance: {e}")
        await loading_msg.edit_text(f"❌ Error: {str(e)}")


async def portfolio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /portfolio command - Show current positions.
    """
    if not check_user_permission(update):
        await send_error_message(update, context, "Access denied")
        return
    
    loading_msg = await update.message.reply_text("⌛ Fetching portfolio...")
    
    try:
        client = get_client()
        portfolio = await client.get_portfolio()
        
        if "error" in portfolio:
            await loading_msg.edit_text(f"❌ Error: {portfolio['error']}")
            return
        
        if isinstance(portfolio, list):
            message = format_balance_message(portfolio)
        else:
            message = "⚠️ No portfolio data available"
        
        await loading_msg.edit_text(message, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error fetching portfolio: {e}")
        await loading_msg.edit_text(f"❌ Error: {str(e)}")


# ========== SIGNALS & ANALYSIS ==========

async def signals_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /signals command - Show recent signals.
    
    Usage: /signals [limit]
    """
    if not check_user_permission(update):
        await send_error_message(update, context, "Access denied")
        return
    
    limit = 5  # Default
    if context.args:
        try:
            limit = int(context.args[0])
            limit = max(1, min(limit, 20))  # Clamp between 1-20
        except ValueError:
            pass
    
    loading_msg = await update.message.reply_text("⌛ Fetching signals...")
    
    try:
        client = get_client()
        signals = await client.get_signals(limit)
        
        if "error" in signals:
            await loading_msg.edit_text(f"❌ Error: {signals['error']}")
            return
        
        if isinstance(signals, list) and len(signals) > 0:
            # Send first signal with full details
            message = format_signal_message(signals[0])
            
            if len(signals) > 1:
                message += f"\n\n📊 Showing 1 of {len(signals)} signals"
            
            # Add navigation buttons if more signals
            keyboard = []
            if len(signals) > 1:
                keyboard.append([
                    InlineKeyboardButton("◀️ Previous", callback_data="signal_prev_0"),
                    InlineKeyboardButton("Next ▶️", callback_data="signal_next_0")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            await loading_msg.edit_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await loading_msg.edit_text("🚦 No active signals")
    
    except Exception as e:
        logger.error(f"Error fetching signals: {e}")
        await loading_msg.edit_text(f"❌ Error: {str(e)}")


async def analyze_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /analyze command - AI market analysis.
    
    Usage: /analyze [symbol]
    """
    if not check_user_permission(update):
        await send_error_message(update, context, "Access denied")
        return
    
    symbol = context.args[0] if context.args else None
    
    loading_msg = await update.message.reply_text("⌛ Running AI analysis...")
    
    try:
        client = get_client()
        analysis = await client.analyze_market(symbol)
        
        if "error" in analysis:
            await loading_msg.edit_text(
                f"🧠 *AI Analysis*\n\n"
                "AI analysis feature is currently being implemented.\n"
                "This will provide comprehensive market insights.",
                parse_mode='Markdown'
            )
        else:
            # Format analysis result
            message = "🧠 *AI Market Analysis*\n\n"
            if symbol:
                message += f"Symbol: `{symbol}`\n\n"
            message += str(analysis)
            
            await loading_msg.edit_text(message, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error in analysis: {e}")
        await loading_msg.edit_text(f"❌ Error: {str(e)}")


async def sentiment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /sentiment command - Sentiment analysis.
    
    Usage: /sentiment [symbol]
    """
    if not check_user_permission(update):
        await send_error_message(update, context, "Access denied")
        return
    
    symbol = context.args[0] if context.args else None
    
    loading_msg = await update.message.reply_text("⌛ Analyzing sentiment...")
    
    try:
        client = get_client()
        sentiment = await client.get_sentiment(symbol)
        
        if "error" in sentiment:
            await loading_msg.edit_text(
                f"📊 *Sentiment Analysis*\n\n"
                "Sentiment analysis feature is currently being implemented.\n"
                "This will provide market sentiment insights.",
                parse_mode='Markdown'
            )
        else:
            message = "📊 *Sentiment Analysis*\n\n"
            if symbol:
                message += f"Symbol: `{symbol}`\n\n"
            message += str(sentiment)
            
            await loading_msg.edit_text(message, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error in sentiment: {e}")
        await loading_msg.edit_text(f"❌ Error: {str(e)}")


# ========== PERFORMANCE & TRADES ==========

async def performance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /performance command - Show performance metrics.
    """
    if not check_user_permission(update):
        await send_error_message(update, context, "Access denied")
        return
    
    loading_msg = await update.message.reply_text("⌛ Loading performance...")
    
    try:
        client = get_client()
        metrics = await client.get_performance()
        
        if "error" in metrics:
            await loading_msg.edit_text(f"❌ Error: {metrics['error']}")
            return
        
        message = format_performance_message(metrics)
        
        await loading_msg.edit_text(message, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error fetching performance: {e}")
        await loading_msg.edit_text(f"❌ Error: {str(e)}")


async def trades_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /trades command - Show recent trades.
    
    Usage: /trades [limit]
    """
    if not check_user_permission(update):
        await send_error_message(update, context, "Access denied")
        return
    
    limit = 10  # Default
    if context.args:
        try:
            limit = int(context.args[0])
            limit = max(1, min(limit, 50))  # Clamp between 1-50
        except ValueError:
            pass
    
    loading_msg = await update.message.reply_text("⌛ Fetching trades...")
    
    try:
        client = get_client()
        result = await client.get_trades(limit)
        
        if "error" in result:
            await loading_msg.edit_text(f"❌ Error: {result['error']}")
            return
        
        trades = result.get('trades', [])
        
        if not trades:
            await loading_msg.edit_text("📋 No recent trades")
            return
        
        message = f"📋 *Recent Trades* (Last {len(trades)})\n\n"
        
        for trade in trades[:limit]:
            symbol = trade.get('symbol', 'UNKNOWN')
            side = trade.get('side', 'unknown').upper()
            pnl = trade.get('pnl', 0)
            pnl_pct = trade.get('pnl_pct', 0)
            
            pnl_emoji = "🟢" if pnl > 0 else "🔴"
            
            message += f"{pnl_emoji} *{symbol}* {side}\n"
            message += f"  P&L: `${pnl:.2f}` ({pnl_pct:+.2f}%)\n\n"
        
        await loading_msg.edit_text(message, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error fetching trades: {e}")
        await loading_msg.edit_text(f"❌ Error: {str(e)}")


# ========== CALLBACK HANDLERS ==========

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle inline keyboard button callbacks.
    """
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # Handle different callback types
    if data == "start_trading":
        # Simulate start_trading command
        update.message = query.message
        await start_trading_handler(update, context)
    
    elif data == "stop_trading":
        # Simulate stop_trading command
        update.message = query.message
        await stop_trading_handler(update, context)
    
    elif data == "refresh_status":
        # Refresh status
        update.message = query.message
        await status_handler(update, context)
    
    elif data.startswith("mode_"):
        mode = data.split("_")[1]
        context.args = [mode]
        update.message = query.message
        await mode_handler(update, context)
    
    elif data.startswith("signal_"):
        # Signal navigation (to be implemented)
        await query.edit_message_text("Signal navigation coming soon...")


# ========== ERROR HANDLER ==========

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle errors in the bot.
    """
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
    
    # Notify user if possible
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ *An error occurred*\n\n"
                "Please try again or contact support.",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error sending error message: {e}")
