#!/usr/bin/env python3
"""
SmartTraderAI - Main Application Entry Point
AI-powered cryptocurrency trading bot with Telegram interface
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Import application components
from app.config.settings import settings
from app.telegram.bot import TradingBot
from app.ai.sentiment_analyzer import SentimentAnalyzer
from app.ai.recommendation_engine import AIRecommendationEngine
from app.exchanges.bitget import BitgetExchange
from app.exchanges.kraken import KrakenExchange

class SmartTraderAI:
    """Main application class that orchestrates all services"""
    
    def __init__(self):
        self.telegram_bot = None
        self.sentiment_analyzer = None
        self.recommendation_engine = None
        self.bitget_exchange = None
        self.kraken_exchange = None
        self.is_running = False
        self.tasks = []
        
    async def initialize(self):
        """Initialize all application components"""
        try:
            logger.info("🚀 Initializing SmartTraderAI...")
            
            # Initialize exchanges
            logger.info("📊 Initializing exchanges...")
            self.bitget_exchange = BitgetExchange(
                api_key=settings.bitget_api_key,
                secret_key=settings.bitget_secret_key,
                passphrase=settings.bitget_passphrase,
                testnet=settings.bitget_testnet
            )
            
            self.kraken_exchange = KrakenExchange(
                api_key=settings.kraken_api_key,
                secret_key=settings.kraken_private_key,
                testnet=settings.kraken_testnet
            )
            
            # Test exchange connections
            await self._test_exchange_connections()
            
            # Initialize AI components
            logger.info("🧠 Initializing AI components...")
            self.sentiment_analyzer = SentimentAnalyzer()
            self.recommendation_engine = AIRecommendationEngine()
            
            # Initialize Telegram bot
            logger.info("🤖 Initializing Telegram bot...")
            self.telegram_bot = TradingBot()
            
            logger.info("✅ SmartTraderAI initialized successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize SmartTraderAI: {e}")
            raise
    
    async def _test_exchange_connections(self):
        """Test connections to exchanges"""
        try:
            # Test Bitget connection
            logger.info("Testing Bitget connection...")
            await self.bitget_exchange.connect()
            balance = await self.bitget_exchange.get_balance()
            logger.info(f"✅ Bitget connected successfully. Balance keys: {list(balance.keys())[:5]}")
            
            # Test Kraken connection
            logger.info("Testing Kraken connection...")
            await self.kraken_exchange.connect()
            balance = await self.kraken_exchange.get_balance()
            logger.info(f"✅ Kraken connected successfully. Balance keys: {list(balance.keys())[:5]}")
            
        except Exception as e:
            logger.error(f"❌ Exchange connection test failed: {e}")
            raise
    
    async def start_services(self):
        """Start all application services"""
        try:
            logger.info("🚀 Starting SmartTraderAI services...")
            
            # Start Telegram bot
            logger.info("Starting Telegram bot...")
            await self.telegram_bot.start()
            
            # Start background tasks
            self.tasks = [
                asyncio.create_task(self._market_data_monitor()),
                asyncio.create_task(self._sentiment_monitor()),
                asyncio.create_task(self._recommendation_monitor()),
                asyncio.create_task(self._health_check_monitor())
            ]
            
            self.is_running = True
            logger.info("✅ All services started successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to start services: {e}")
            raise
    
    async def stop_services(self):
        """Stop all application services"""
        try:
            logger.info("🛑 Stopping SmartTraderAI services...")
            
            self.is_running = False
            
            # Cancel background tasks
            for task in self.tasks:
                task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
            # Stop Telegram bot
            if self.telegram_bot:
                await self.telegram_bot.stop()
            
            # Disconnect exchanges
            if self.bitget_exchange:
                await self.bitget_exchange.disconnect()
            
            if self.kraken_exchange:
                await self.kraken_exchange.disconnect()
            
            logger.info("✅ All services stopped successfully!")
            
        except Exception as e:
            logger.error(f"❌ Error stopping services: {e}")
    
    async def _market_data_monitor(self):
        """Background task to monitor market data"""
        logger.info("📊 Starting market data monitor...")
        
        while self.is_running:
            try:
                # Monitor top trading pairs
                symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']
                
                for symbol in symbols:
                    try:
                        # Get market data from both exchanges
                        ticker_bitget = await self.bitget_exchange.get_ticker(symbol)
                        ticker_kraken = await self.kraken_exchange.get_ticker(symbol)
                        
                        # Log significant price movements
                        price_change_bitget = ticker_bitget.get('change_24h', 0)
                        price_change_kraken = ticker_kraken.get('change_24h', 0)
                        
                        if abs(price_change_bitget) > 5 or abs(price_change_kraken) > 5:
                            logger.info(f"🚨 Significant price movement detected for {symbol}: "
                                      f"Bitget: {price_change_bitget:+.2f}%, "
                                      f"Kraken: {price_change_kraken:+.2f}%")
                        
                    except Exception as e:
                        logger.warning(f"Error monitoring {symbol}: {e}")
                        continue
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in market data monitor: {e}")
                await asyncio.sleep(30)
    
    async def _sentiment_monitor(self):
        """Background task to monitor sentiment"""
        logger.info("🧠 Starting sentiment monitor...")
        
        while self.is_running:
            try:
                # Monitor sentiment for top symbols
                symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
                
                for symbol in symbols:
                    try:
                        sentiment = await self.sentiment_analyzer.get_aggregate_sentiment(symbol, hours=24)
                        
                        # Log significant sentiment changes
                        sentiment_score = sentiment.get('aggregate_sentiment', 0)
                        if abs(sentiment_score) > 0.5:
                            logger.info(f"📰 Significant sentiment detected for {symbol}: {sentiment_score:+.3f}")
                        
                    except Exception as e:
                        logger.warning(f"Error monitoring sentiment for {symbol}: {e}")
                        continue
                
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in sentiment monitor: {e}")
                await asyncio.sleep(60)
    
    async def _recommendation_monitor(self):
        """Background task to generate and monitor recommendations"""
        logger.info("🎯 Starting recommendation monitor...")
        
        while self.is_running:
            try:
                # Generate recommendations for top symbols
                symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']
                
                for symbol in symbols:
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
                        
                        # Log strong recommendations
                        confidence = recommendation.get('confidence', 0)
                        rec_type = recommendation.get('recommendation', 'hold')
                        
                        if confidence > 0.8 and rec_type != 'hold':
                            logger.info(f"🎯 Strong {rec_type.upper()} recommendation for {symbol}: "
                                      f"Confidence: {confidence:.1%}")
                        
                    except Exception as e:
                        logger.warning(f"Error generating recommendation for {symbol}: {e}")
                        continue
                
                # Wait before next check
                await asyncio.sleep(600)  # Check every 10 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in recommendation monitor: {e}")
                await asyncio.sleep(120)
    
    async def _health_check_monitor(self):
        """Background task to monitor system health"""
        logger.info("🏥 Starting health check monitor...")
        
        while self.is_running:
            try:
                # Check exchange connections
                try:
                    await self.bitget_exchange.health_check()
                    logger.debug("✅ Bitget health check passed")
                except Exception as e:
                    logger.warning(f"⚠️ Bitget health check failed: {e}")
                
                try:
                    await self.kraken_exchange.health_check()
                    logger.debug("✅ Kraken health check passed")
                except Exception as e:
                    logger.warning(f"⚠️ Kraken health check failed: {e}")
                
                # Log system status
                logger.info(f"📊 System Status - Running: {self.is_running}, "
                          f"Active Tasks: {len([t for t in self.tasks if not t.done()])}")
                
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check monitor: {e}")
                await asyncio.sleep(60)
    
    async def run(self):
        """Main application run loop"""
        try:
            # Initialize application
            await self.initialize()
            
            # Start services
            await self.start_services()
            
            # Keep running until interrupted
            logger.info("🎉 SmartTraderAI is now running! Press Ctrl+C to stop.")
            
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"❌ Application error: {e}")
        finally:
            await self.stop_services()

def signal_handler(signum, frame):
    """Handle system signals"""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    sys.exit(0)

async def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run application
    app = SmartTraderAI()
    await app.run()

if __name__ == "__main__":
    try:
        # Run the application
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Application stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
