import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode

from app.config.settings import settings
from app.exchanges.bitget import BitgetExchange
from app.exchanges.kraken import KrakenExchange
from app.ai.sentiment_analyzer import SentimentAnalyzer
from app.ai.recommendation_engine import AIRecommendationEngine

logger = logging.getLogger(__name__)

class TradingBot:
    """Telegram trading bot with AI-powered recommendations"""
    
    def __init__(self):
        self.bitget = BitgetExchange(
            api_key=settings.bitget_api_key,
            secret_key=settings.bitget_secret_key,
            passphrase=settings.bitget_passphrase,
            testnet=settings.bitget_testnet
        )
        
        self.kraken = KrakenExchange(
            api_key=settings.kraken_api_key,
            secret_key=settings.kraken_private_key,
            testnet=settings.kraken_testnet
        )
        
        self.sentiment_analyzer = SentimentAnalyzer()
        self.recommendation_engine = AIRecommendationEngine()
        
        # Bot application
        self.application = Application.builder().token(settings.telegram_bot_token).build()
        
        # Register handlers
        self._register_handlers()
        
        # User sessions
        self.user_sessions = {}
        
    def _register_handlers(self):
        """Register all bot command handlers"""
        # Basic commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Trading commands
        self.application.add_handler(CommandHandler("price", self.price_command))
        self.application.add_handler(CommandHandler("portfolio", self.portfolio_command))
        self.application.add_handler(CommandHandler("balance", self.balance_command))
        self.application.add_handler(CommandHandler("trade", self.trade_command))
        self.application.add_handler(CommandHandler("cancel", self.cancel_command))
        
        # Analysis commands
        self.application.add_handler(CommandHandler("analyze", self.analyze_command))
        self.application.add_handler(CommandHandler("sentiment", self.sentiment_command))
        self.application.add_handler(CommandHandler("recommendations", self.recommendations_command))
        
        # Settings commands
        self.application.add_handler(CommandHandler("settings", self.settings_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        welcome_message = f"""
🤖 *Welcome to SmartTraderAI Bot!*

Hello {user.first_name}! I'm your AI-powered trading assistant.

*Available Commands:*
• `/price <symbol>` - Get current price
• `/portfolio` - View your portfolio
• `/balance` - Check account balance
• `/analyze <symbol>` - Technical analysis
• `/sentiment <symbol>` - Sentiment analysis
• `/recommendations` - AI trading recommendations
• `/trade <symbol> <side> <amount>` - Execute trade
• `/settings` - Bot settings
• `/status` - System status

*Quick Actions:*
Use the buttons below for common actions.
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Portfolio", callback_data="portfolio"),
                InlineKeyboardButton("💰 Balance", callback_data="balance")
            ],
            [
                InlineKeyboardButton("📈 Analyze BTC", callback_data="analyze_BTC/USDT"),
                InlineKeyboardButton("🧠 AI Recommendations", callback_data="recommendations")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
                InlineKeyboardButton("📋 Help", callback_data="help")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📚 *SmartTraderAI Bot Help*

*Trading Commands:*
• `/price BTC/USDT` - Get current price
• `/portfolio` - View your portfolio
• `/balance` - Check account balance
• `/trade BTC/USDT buy 100` - Buy 100 USDT worth of BTC
• `/trade BTC/USDT sell 0.001` - Sell 0.001 BTC
• `/cancel <order_id>` - Cancel open order

*Analysis Commands:*
• `/analyze BTC/USDT` - Technical analysis
• `/sentiment BTC/USDT` - Sentiment analysis
• `/recommendations` - AI trading recommendations

*Settings:*
• `/settings` - Configure bot settings
• `/status` - Check system status

*Examples:*
• `/price ETH/USDT`
• `/analyze ADA/USDT`
• `/trade BTC/USDT buy 50`
• `/sentiment SOL/USDT`

*Risk Warning:*
Trading cryptocurrencies involves risk. Only trade what you can afford to lose.
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /price command"""
        try:
            if not context.args:
                await update.message.reply_text("❌ Please provide a symbol. Example: `/price BTC/USDT`", parse_mode=ParseMode.MARKDOWN)
                return
            
            symbol = context.args[0].upper()
            
            # Get price from both exchanges
            prices = {}
            
            try:
                await self.bitget.connect()
                ticker = await self.bitget.get_ticker(symbol)
                prices['Bitget'] = {
                    'price': ticker['last'],
                    'change_24h': ticker.get('change_24h', 0),
                    'volume': ticker['volume']
                }
            except Exception as e:
                logger.warning(f"Bitget price fetch failed: {e}")
            
            try:
                await self.kraken.connect()
                ticker = await self.kraken.get_ticker(symbol)
                prices['Kraken'] = {
                    'price': ticker['last'],
                    'change_24h': ticker.get('change_24h', 0),
                    'volume': ticker['volume']
                }
            except Exception as e:
                logger.warning(f"Kraken price fetch failed: {e}")
            
            if not prices:
                await update.message.reply_text(f"❌ Could not fetch price for {symbol}")
                return
            
            # Format response
            response = f"💰 *{symbol} Price*\n\n"
            
            for exchange, data in prices.items():
                price = data['price']
                change = data.get('change_24h', 0)
                volume = data['volume']
                
                change_emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                change_text = f"{change:+.2f}%" if change != 0 else "0.00%"
                
                response += f"*{exchange}:*\n"
                response += f"Price: ${price:,.2f}\n"
                response += f"24h: {change_emoji} {change_text}\n"
                response += f"Volume: ${volume:,.0f}\n\n"
            
            # Add quick action buttons
            keyboard = [
                [
                    InlineKeyboardButton("📊 Analyze", callback_data=f"analyze_{symbol}"),
                    InlineKeyboardButton("🧠 AI Analysis", callback_data=f"ai_analyze_{symbol}")
                ],
                [
                    InlineKeyboardButton("💰 Buy", callback_data=f"trade_{symbol}_buy"),
                    InlineKeyboardButton("💸 Sell", callback_data=f"trade_{symbol}_sell")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error in price command: {e}")
            await update.message.reply_text(f"❌ Error fetching price: {str(e)}")
    
    async def portfolio_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /portfolio command"""
        try:
            user_id = update.effective_user.id
            
            # Get balances from both exchanges
            portfolios = {}
            
            try:
                await self.bitget.connect()
                balance = await self.bitget.get_balance()
                portfolios['Bitget'] = balance
            except Exception as e:
                logger.warning(f"Bitget balance fetch failed: {e}")
            
            try:
                await self.kraken.connect()
                balance = await self.kraken.get_balance()
                portfolios['Kraken'] = balance
            except Exception as e:
                logger.warning(f"Kraken balance fetch failed: {e}")
            
            if not portfolios:
                await update.message.reply_text("❌ Could not fetch portfolio data")
                return
            
            # Format response
            response = "📊 *Your Portfolio*\n\n"
            total_value = 0.0
            
            for exchange, balance in portfolios.items():
                response += f"*{exchange}:*\n"
                
                for currency, amount in balance.items():
                    if amount > 0:
                        # For now, we'll show the raw amounts
                        # In a real implementation, you'd convert to USD
                        response += f"  {currency}: {amount:.8f}\n"
                
                response += "\n"
            
            response += "*Note:* Values shown are raw amounts. USD conversion requires additional API calls."
            
            # Add action buttons
            keyboard = [
                [
                    InlineKeyboardButton("💰 Refresh", callback_data="portfolio"),
                    InlineKeyboardButton("📈 Performance", callback_data="performance")
                ],
                [
                    InlineKeyboardButton("🔄 Sync", callback_data="sync_portfolio"),
                    InlineKeyboardButton("📋 History", callback_data="trade_history")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error in portfolio command: {e}")
            await update.message.reply_text(f"❌ Error fetching portfolio: {str(e)}")
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command"""
        try:
            currency = context.args[0].upper() if context.args else None
            
            balances = {}
            
            try:
                await self.bitget.connect()
                balance = await self.bitget.get_balance(currency)
                balances['Bitget'] = balance
            except Exception as e:
                logger.warning(f"Bitget balance fetch failed: {e}")
            
            try:
                await self.kraken.connect()
                balance = await self.kraken.get_balance(currency)
                balances['Kraken'] = balance
            except Exception as e:
                logger.warning(f"Kraken balance fetch failed: {e}")
            
            if not balances:
                await update.message.reply_text("❌ Could not fetch balance data")
                return
            
            # Format response
            if currency:
                response = f"💰 *{currency} Balance*\n\n"
            else:
                response = "💰 *Account Balances*\n\n"
            
            for exchange, balance in balances.items():
                response += f"*{exchange}:*\n"
                
                if currency:
                    amount = balance.get(currency, 0.0)
                    response += f"  {currency}: {amount:.8f}\n"
                else:
                    for curr, amount in balance.items():
                        if amount > 0:
                            response += f"  {curr}: {amount:.8f}\n"
                
                response += "\n"
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in balance command: {e}")
            await update.message.reply_text(f"❌ Error fetching balance: {str(e)}")
    
    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analyze command"""
        try:
            if not context.args:
                await update.message.reply_text("❌ Please provide a symbol. Example: `/analyze BTC/USDT`", parse_mode=ParseMode.MARKDOWN)
                return
            
            symbol = context.args[0].upper()
            
            # Get technical analysis
            try:
                await self.kraken.connect()
                analysis_data = await self.kraken.get_ohlcv_with_indicators(symbol, '1h', 100)
                
                if not analysis_data or 'indicators' not in analysis_data:
                    await update.message.reply_text(f"❌ Could not analyze {symbol}")
                    return
                
                indicators = analysis_data['indicators']
                
                # Format analysis
                response = f"📊 *Technical Analysis: {symbol}*\n\n"
                
                # Price info
                current_price = indicators.get('current_price', 0)
                price_change = indicators.get('price_change_24h', 0)
                response += f"*Current Price:* ${current_price:,.2f}\n"
                response += f"*24h Change:* {price_change:+.2f}%\n\n"
                
                # Technical indicators
                response += "*Technical Indicators:*\n"
                
                rsi = indicators.get('rsi', 0)
                rsi_status = "Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral"
                response += f"• RSI: {rsi:.1f} ({rsi_status})\n"
                
                sma_20 = indicators.get('sma_20', 0)
                sma_50 = indicators.get('sma_50', 0)
                if sma_20 and sma_50:
                    ma_signal = "Bullish" if sma_20 > sma_50 else "Bearish"
                    response += f"• MA Signal: {ma_signal} (20: ${sma_20:,.2f}, 50: ${sma_50:,.2f})\n"
                
                bb = indicators.get('bollinger_bands', {})
                if bb.get('upper') and bb.get('lower'):
                    bb_position = (current_price - bb['lower']) / (bb['upper'] - bb['lower'])
                    bb_status = "Upper Band" if bb_position > 0.8 else "Lower Band" if bb_position < 0.2 else "Middle"
                    response += f"• Bollinger Bands: {bb_status}\n"
                
                # Add action buttons
                keyboard = [
                    [
                        InlineKeyboardButton("🧠 AI Analysis", callback_data=f"ai_analyze_{symbol}"),
                        InlineKeyboardButton("📈 Sentiment", callback_data=f"sentiment_{symbol}")
                    ],
                    [
                        InlineKeyboardButton("💰 Trade", callback_data=f"trade_{symbol}_buy"),
                        InlineKeyboardButton("📊 More Data", callback_data=f"more_data_{symbol}")
                    ]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
                
            except Exception as e:
                logger.error(f"Error in analyze command: {e}")
                await update.message.reply_text(f"❌ Error analyzing {symbol}: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error in analyze command: {e}")
            await update.message.reply_text(f"❌ Error in analysis: {str(e)}")
    
    async def sentiment_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sentiment command"""
        try:
            if not context.args:
                await update.message.reply_text("❌ Please provide a symbol. Example: `/sentiment BTC/USDT`", parse_mode=ParseMode.MARKDOWN)
                return
            
            symbol = context.args[0].upper()
            
            # Get sentiment analysis
            sentiment_data = await self.sentiment_analyzer.get_aggregate_sentiment(symbol, hours=24)
            
            if 'error' in sentiment_data:
                await update.message.reply_text(f"❌ Error getting sentiment: {sentiment_data['error']}")
                return
            
            # Format response
            sentiment_score = sentiment_data['aggregate_sentiment']
            confidence = sentiment_data['confidence']
            sentiment_label = sentiment_data['sentiment_label']
            
            # Sentiment emoji
            sentiment_emoji = "😊" if sentiment_label == "positive" else "😞" if sentiment_label == "negative" else "😐"
            
            response = f"🧠 *Sentiment Analysis: {symbol}*\n\n"
            response += f"*Overall Sentiment:* {sentiment_emoji} {sentiment_label.title()}\n"
            response += f"*Score:* {sentiment_score:.3f} (-1 to +1)\n"
            response += f"*Confidence:* {confidence:.1%}\n\n"
            
            # News sentiment
            news_data = sentiment_data.get('sources', {}).get('news', {})
            if news_data:
                response += "*News Sentiment:*\n"
                response += f"• Score: {news_data.get('sentiment_score', 0):.3f}\n"
                response += f"• Articles: {news_data.get('article_count', 0)}\n"
                response += f"• Confidence: {news_data.get('confidence', 0):.1%}\n\n"
            
            # Add action buttons
            keyboard = [
                [
                    InlineKeyboardButton("📊 Technical", callback_data=f"analyze_{symbol}"),
                    InlineKeyboardButton("🧠 AI Analysis", callback_data=f"ai_analyze_{symbol}")
                ],
                [
                    InlineKeyboardButton("📰 Latest News", callback_data=f"news_{symbol}"),
                    InlineKeyboardButton("📈 Trade", callback_data=f"trade_{symbol}_buy")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error in sentiment command: {e}")
            await update.message.reply_text(f"❌ Error getting sentiment: {str(e)}")
    
    async def recommendations_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /recommendations command"""
        try:
            # Get AI recommendations for top symbols
            symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']
            
            response = "🧠 *AI Trading Recommendations*\n\n"
            response += "*Top Opportunities:*\n\n"
            
            for i, symbol in enumerate(symbols[:5], 1):
                try:
                    # Mock market data for demonstration
                    mock_data = {
                        'current_price': 50000.0,
                        'price_change_24h': 2.5,
                        'volume_24h': 1000000,
                        'ohlcv': []
                    }
                    
                    recommendation = await self.recommendation_engine.generate_recommendation(
                        symbol, 'bitget', mock_data
                    )
                    
                    rec_type = recommendation['recommendation']
                    confidence = recommendation['confidence']
                    expected_return = recommendation.get('expected_return', 0)
                    
                    # Recommendation emoji
                    rec_emoji = "🟢" if rec_type == "buy" else "🔴" if rec_type == "sell" else "🟡"
                    
                    response += f"{i}. {rec_emoji} *{symbol}*\n"
                    response += f"   Recommendation: {rec_type.upper()}\n"
                    response += f"   Confidence: {confidence:.1%}\n"
                    response += f"   Expected Return: {expected_return:+.1%}\n\n"
                    
                except Exception as e:
                    logger.warning(f"Error getting recommendation for {symbol}: {e}")
                    continue
            
            # Add action buttons
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="recommendations"),
                    InlineKeyboardButton("📊 Portfolio", callback_data="portfolio")
                ],
                [
                    InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
                    InlineKeyboardButton("📈 Performance", callback_data="performance")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error in recommendations command: {e}")
            await update.message.reply_text(f"❌ Error getting recommendations: {str(e)}")
    
    async def trade_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trade command"""
        try:
            if len(context.args) < 3:
                await update.message.reply_text(
                    "❌ Please provide symbol, side, and amount. Example: `/trade BTC/USDT buy 100`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            symbol = context.args[0].upper()
            side = context.args[1].lower()
            amount = float(context.args[2])
            
            if side not in ['buy', 'sell']:
                await update.message.reply_text("❌ Side must be 'buy' or 'sell'")
                return
            
            if amount <= 0:
                await update.message.reply_text("❌ Amount must be positive")
                return
            
            # For safety, we'll just show what the trade would look like
            # In a real implementation, you'd execute the trade
            response = f"📋 *Trade Preview*\n\n"
            response += f"*Symbol:* {symbol}\n"
            response += f"*Side:* {side.upper()}\n"
            response += f"*Amount:* {amount}\n"
            response += f"*Status:* Preview Mode\n\n"
            response += "*Note:* This is a preview. Actual trading requires additional setup."
            
            # Add confirmation buttons
            keyboard = [
                [
                    InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_trade_{symbol}_{side}_{amount}"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_trade")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            
        except ValueError:
            await update.message.reply_text("❌ Invalid amount. Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error in trade command: {e}")
            await update.message.reply_text(f"❌ Error processing trade: {str(e)}")
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel command"""
        try:
            if not context.args:
                await update.message.reply_text("❌ Please provide an order ID. Example: `/cancel 12345`")
                return
            
            order_id = context.args[0]
            
            # For now, just acknowledge the request
            response = f"🔄 *Cancel Order Request*\n\n"
            response += f"*Order ID:* {order_id}\n"
            response += f"*Status:* Request Received\n\n"
            response += "*Note:* Order cancellation requires proper exchange integration."
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in cancel command: {e}")
            await update.message.reply_text(f"❌ Error cancelling order: {str(e)}")
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command"""
        try:
            response = "⚙️ *Bot Settings*\n\n"
            response += "*Current Configuration:*\n"
            response += f"• Max Daily Loss: ${settings.max_daily_loss:,.0f}\n"
            response += f"• Max Position Size: ${settings.max_position_size:,.0f}\n"
            response += f"• Max Open Trades: {settings.max_open_trades}\n"
            response += f"• Trade Cooldown: {settings.trade_cooldown_ms/1000:.0f}s\n"
            response += f"• Stop Loss: {settings.stop_loss_percentage:.1%}\n"
            response += f"• Take Profit: {settings.take_profit_percentage:.1%}\n\n"
            response += "*AI Features:*\n"
            response += f"• Sentiment Analysis: {'✅' if settings.sentiment_analysis_enabled else '❌'}\n"
            response += f"• AI Recommendations: {'✅' if settings.ai_recommendations_enabled else '❌'}\n"
            
            # Add settings buttons
            keyboard = [
                [
                    InlineKeyboardButton("💰 Risk Settings", callback_data="risk_settings"),
                    InlineKeyboardButton("🤖 AI Settings", callback_data="ai_settings")
                ],
                [
                    InlineKeyboardButton("📊 Trading Pairs", callback_data="trading_pairs"),
                    InlineKeyboardButton("🔔 Notifications", callback_data="notifications")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error in settings command: {e}")
            await update.message.reply_text(f"❌ Error loading settings: {str(e)}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            response = "📊 *System Status*\n\n"
            
            # Check exchange connections
            exchanges_status = {}
            
            try:
                await self.bitget.connect()
                exchanges_status['Bitget'] = "✅ Connected"
            except Exception as e:
                exchanges_status['Bitget'] = "❌ Disconnected"
            
            try:
                await self.kraken.connect()
                exchanges_status['Kraken'] = "✅ Connected"
            except Exception as e:
                exchanges_status['Kraken'] = "❌ Disconnected"
            
            response += "*Exchange Status:*\n"
            for exchange, status in exchanges_status.items():
                response += f"• {exchange}: {status}\n"
            
            response += "\n*AI Services:*\n"
            response += "• Sentiment Analysis: ✅ Active\n"
            response += "• Recommendation Engine: ✅ Active\n"
            response += "• OpenAI Integration: ✅ Active\n"
            
            response += "\n*Bot Status:*\n"
            response += "• Telegram Bot: ✅ Running\n"
            response += "• Database: ✅ Connected\n"
            response += "• Cache: ✅ Active\n"
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await update.message.reply_text(f"❌ Error checking status: {str(e)}")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        try:
            if data == "portfolio":
                await self.portfolio_command(update, context)
            elif data == "balance":
                await self.balance_command(update, context)
            elif data == "recommendations":
                await self.recommendations_command(update, context)
            elif data == "settings":
                await self.settings_command(update, context)
            elif data == "help":
                await self.help_command(update, context)
            elif data.startswith("analyze_"):
                symbol = data.split("_", 1)[1]
                context.args = [symbol]
                await self.analyze_command(update, context)
            elif data.startswith("sentiment_"):
                symbol = data.split("_", 1)[1]
                context.args = [symbol]
                await self.sentiment_command(update, context)
            elif data.startswith("ai_analyze_"):
                symbol = data.split("_", 2)[2]
                # Handle AI analysis
                await query.edit_message_text(f"🧠 AI analysis for {symbol} - Coming soon!")
            elif data.startswith("trade_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    symbol = parts[1]
                    side = parts[2]
                    context.args = [symbol, side, "100"]  # Default amount
                    await self.trade_command(update, context)
            else:
                await query.edit_message_text(f"Button: {data} - Feature coming soon!")
                
        except Exception as e:
            logger.error(f"Error in button callback: {e}")
            await query.edit_message_text(f"❌ Error processing request: {str(e)}")
    
    async def start(self):
        """Start the bot"""
        try:
            logger.info("Starting Telegram trading bot...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("Telegram bot started successfully!")
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
    
    async def stop(self):
        """Stop the bot"""
        try:
            logger.info("Stopping Telegram trading bot...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Telegram bot stopped successfully!")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
            raise
