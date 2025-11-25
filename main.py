#!/usr/bin/env python3
"""
v0 Strategy Engine Pro - Main Application Entry Point

AI-powered cryptocurrency trading engine with multi-exchange support,
multiple trading modes, and comprehensive signal processing.

Features:
- 10 integrated exchanges (Binance, Bitget, Bybit, Gate.io, Huobi, Kraken, KuCoin, MEXC, OKX, Phemex)
- 6 trading modes (manual, semi_auto, auto, paper_trading, demo, backtest)
- TradingView webhook integration
- Telegram notifications
- AI-powered analysis (11 LLM providers)
- Risk management
- Performance tracking

Usage:
    python main.py

Environment:
    Configure .env file with required credentials
    See .env.example for all options
"""

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Third-party imports
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
log_file = os.getenv('LOG_FILE', './logs/trading_engine.log')

# Create logs directory
Path(log_file).parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Import application components
try:
    # Exchange imports
    from exchanges.binance_api import BinanceAPI
    from exchanges.bitget_api import BitgetAPI
    from exchanges.bybit_api import BybitAPI
    from exchanges.gateio_api import GateioAPI
    from exchanges.huobi_api import HuobiAPI
    from exchanges.kraken_api import KrakenAPI
    from exchanges.kucoin_api import KucoinAPI
    from exchanges.mexc_api import MEXCAPI
    from exchanges.okx_api import OKXAPI
    from exchanges.phemex_api import PhemexAPI
    
    # Trading components
    from trading.mode_manager import TradingModeManager, TradingMode, TradingConfig
    from signals.signal_system import SignalManager
    from risk_management.manager import RiskManager
    
    # Integration components
    from telegram_integration.webhook_handler import TelegramWebhookHandler
    from telegram_integration.alert_manager import AlertManager
    
    logger.info("✅ All core components imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import core components: {e}")
    logger.error("Please ensure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)


class StrategyEnginePro:
    """
    Main application class that orchestrates all trading engine services.
    
    Responsibilities:
    - Initialize and manage all exchange connections
    - Coordinate trading mode manager
    - Handle signal reception and processing
    - Manage Telegram notifications
    - Monitor system health
    - Graceful shutdown
    """
    
    def __init__(self):
        """Initialize the Strategy Engine Pro application"""
        logger.info("🚀 Initializing v0 Strategy Engine Pro...")
        
        # Configuration
        self.trading_mode = TradingMode(os.getenv('TRADING_MODE', 'manual').lower())
        self.app_env = os.getenv('APP_ENV', 'development')
        
        # Components
        self.exchanges: Dict[str, any] = {}
        self.trading_mode_manager: Optional[TradingModeManager] = None
        self.signal_manager: Optional[SignalManager] = None
        self.risk_manager: Optional[RiskManager] = None
        self.alert_manager: Optional[AlertManager] = None
        self.webhook_handler: Optional[TelegramWebhookHandler] = None
        
        # State
        self.is_running = False
        self.background_tasks: List[asyncio.Task] = []
        self.shutdown_event = asyncio.Event()
        
        logger.info(f"📊 Environment: {self.app_env}")
        logger.info(f"🎯 Trading Mode: {self.trading_mode.value}")
    
    async def initialize_exchanges(self) -> None:
        """
        Initialize all configured exchanges.
        
        Reads exchange credentials from environment variables and
        initializes only the exchanges that have valid API keys.
        """
        logger.info("📊 Initializing exchanges...")
        
        # Exchange configurations (name, class, required env vars)
        exchange_configs = [
            ('binance', BinanceAPI, ['BINANCE_API_KEY', 'BINANCE_API_SECRET']),
            ('bitget', BitgetAPI, ['BITGET_API_KEY', 'BITGET_API_SECRET', 'BITGET_PASSPHRASE']),
            ('bybit', BybitAPI, ['BYBIT_API_KEY', 'BYBIT_API_SECRET']),
            ('gateio', GateioAPI, ['GATEIO_API_KEY', 'GATEIO_API_SECRET']),
            ('huobi', HuobiAPI, ['HUOBI_API_KEY', 'HUOBI_API_SECRET']),
            ('kraken', KrakenAPI, ['KRAKEN_API_KEY', 'KRAKEN_API_SECRET']),
            ('kucoin', KucoinAPI, ['KUCOIN_API_KEY', 'KUCOIN_API_SECRET', 'KUCOIN_PASSPHRASE']),
            ('mexc', MEXCAPI, ['MEXC_API_KEY', 'MEXC_API_SECRET']),
            ('okx', OKXAPI, ['OKX_API_KEY', 'OKX_API_SECRET', 'OKX_PASSPHRASE']),
            ('phemex', PhemexAPI, ['PHEMEX_API_KEY', 'PHEMEX_API_SECRET'])
        ]
        
        for exchange_name, exchange_class, required_vars in exchange_configs:
            try:
                # Check if all required variables are set
                if all(os.getenv(var) for var in required_vars):
                    # Get credentials
                    credentials = {var.split('_', 1)[1].lower(): os.getenv(var) for var in required_vars}
                    
                    # Initialize exchange
                    exchange = exchange_class(**credentials)
                    
                    # Test connection (optional, comment out for faster startup)
                    # await exchange.test_connection()
                    
                    self.exchanges[exchange_name] = exchange
                    logger.info(f"✅ {exchange_name.title()} initialized")
                else:
                    logger.info(f"⏭️  {exchange_name.title()} skipped (no credentials)")
            
            except Exception as e:
                logger.warning(f"⚠️  Failed to initialize {exchange_name}: {e}")
        
        if not self.exchanges:
            logger.error("❌ No exchanges initialized! Please configure at least one exchange in .env")
            raise RuntimeError("No exchanges configured")
        
        logger.info(f"✅ Initialized {len(self.exchanges)} exchange(s): {', '.join(self.exchanges.keys())}")
    
    async def initialize_trading_components(self) -> None:
        """
        Initialize trading-related components:
        - Signal Manager
        - Risk Manager
        - Trading Mode Manager
        """
        logger.info("🧠 Initializing trading components...")
        
        try:
            # Initialize Signal Manager
            self.signal_manager = SignalManager()
            logger.info("✅ Signal Manager initialized")
            
            # Initialize Risk Manager
            self.risk_manager = RiskManager(
                max_position_size=float(os.getenv('MAX_POSITION_SIZE', '1000')),
                max_daily_loss=float(os.getenv('MAX_DAILY_LOSS', '500')),
                stop_loss_percentage=float(os.getenv('STOP_LOSS_PERCENTAGE', '2.0')),
                take_profit_percentage=float(os.getenv('TAKE_PROFIT_PERCENTAGE', '5.0'))
            )
            logger.info("✅ Risk Manager initialized")
            
            # Initialize Trading Mode Manager
            trading_config = TradingConfig(
                mode=self.trading_mode,
                max_positions=int(os.getenv('MAX_POSITIONS', '10')),
                position_size_pct=float(os.getenv('POSITION_SIZE_PERCENT', '2.0')) / 100,
                stop_loss_pct=float(os.getenv('STOP_LOSS_PERCENTAGE', '2.0')) / 100,
                take_profit_pct=float(os.getenv('TAKE_PROFIT_PERCENTAGE', '5.0')) / 100,
                max_daily_trades=int(os.getenv('MAX_DAILY_TRADES', '50'))
            )
            
            self.trading_mode_manager = TradingModeManager(
                exchanges=list(self.exchanges.values()),
                risk_manager=self.risk_manager,
                signal_manager=self.signal_manager
            )
            self.trading_mode_manager.set_mode(self.trading_mode, trading_config)
            
            logger.info(f"✅ Trading Mode Manager initialized ({self.trading_mode.value} mode)")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize trading components: {e}")
            raise
    
    async def initialize_communication(self) -> None:
        """
        Initialize communication components:
        - Telegram Alert Manager
        - Webhook Handler (for TradingView signals)
        """
        logger.info("📱 Initializing communication components...")
        
        try:
            # Initialize Alert Manager (Telegram)
            telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
            telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            if telegram_token and telegram_chat_id:
                self.alert_manager = AlertManager()
                logger.info("✅ Telegram Alert Manager initialized")
                
                # Test connection
                # await self.alert_manager.send_message("🚀 v0 Strategy Engine Pro initialized!")
            else:
                logger.warning("⚠️  Telegram not configured (TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing)")
            
            # Initialize Webhook Handler (optional, for production)
            use_webhook = os.getenv('TELEGRAM_USE_WEBHOOK', 'false').lower() == 'true'
            webhook_url = os.getenv('TELEGRAM_WEBHOOK_URL')
            
            if use_webhook and webhook_url:
                self.webhook_handler = TelegramWebhookHandler(
                    webhook_url=webhook_url,
                    port=int(os.getenv('TELEGRAM_WEBHOOK_PORT', '8443')),
                    alert_manager=self.alert_manager
                )
                logger.info("✅ Webhook Handler initialized")
            else:
                logger.info("ℹ️  Webhook mode disabled (using polling)")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize communication: {e}")
            # Don't raise - communication is optional
    
    async def start_services(self) -> None:
        """
        Start all application services and background tasks.
        """
        logger.info("🚀 Starting services...")
        
        try:
            # Start Trading Mode Manager
            self.trading_mode_manager.start_trading()
            logger.info(f"✅ Trading started in {self.trading_mode.value} mode")
            
            # Start background monitoring tasks
            self.background_tasks = [
                asyncio.create_task(self._exchange_health_monitor(), name="exchange_monitor"),
                asyncio.create_task(self._performance_tracker(), name="performance_tracker"),
                asyncio.create_task(self._signal_processor(), name="signal_processor")
            ]
            
            logger.info(f"✅ Started {len(self.background_tasks)} background tasks")
            
            # Start webhook if configured
            if self.webhook_handler:
                asyncio.create_task(self.webhook_handler.start(), name="webhook_handler")
                logger.info("✅ Webhook handler started")
            
            self.is_running = True
            logger.info("🎉 All services started successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to start services: {e}")
            raise
    
    async def _exchange_health_monitor(self) -> None:
        """
        Background task to monitor exchange health and connectivity.
        """
        logger.info("🏥 Exchange health monitor started")
        
        check_interval = 300  # 5 minutes
        
        while self.is_running and not self.shutdown_event.is_set():
            try:
                for name, exchange in self.exchanges.items():
                    try:
                        # Ping exchange or check balance
                        await exchange.test_connection()
                        logger.debug(f"✅ {name.title()} health check passed")
                    except Exception as e:
                        logger.warning(f"⚠️  {name.title()} health check failed: {e}")
                        
                        if self.alert_manager:
                            await self.alert_manager.send_alert(
                                f"⚠️ Exchange Health Alert\n"
                                f"Exchange: {name.title()}\n"
                                f"Status: Connection failed\n"
                                f"Error: {str(e)[:100]}"
                            )
                
                # Wait before next check
                await asyncio.wait_for(
                    self.shutdown_event.wait(),
                    timeout=check_interval
                )
            
            except asyncio.TimeoutError:
                continue  # Normal timeout, continue monitoring
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
                await asyncio.sleep(60)
        
        logger.info("🏥 Exchange health monitor stopped")
    
    async def _performance_tracker(self) -> None:
        """
        Background task to track and log trading performance.
        """
        logger.info("📊 Performance tracker started")
        
        report_interval = 3600  # 1 hour
        
        while self.is_running and not self.shutdown_event.is_set():
            try:
                # Get trading status from mode manager
                status = self.trading_mode_manager.get_trading_status()
                
                # Log performance metrics
                logger.info(
                    f"📈 Performance Report\n"
                    f"Mode: {status['mode']}\n"
                    f"Running: {status['is_trading']}\n"
                    f"Daily Trades: {status['daily_trades']}\n"
                    f"Open Positions: {status['open_positions']}\n"
                    f"Performance: {status.get('performance', {})}"
                )
                
                # Send to Telegram if configured
                if self.alert_manager and status.get('performance'):
                    perf = status['performance']
                    await self.alert_manager.send_message(
                        f"📊 Hourly Report\n"
                        f"Total Trades: {perf.get('total_trades', 0)}\n"
                        f"Win Rate: {perf.get('win_rate', 0):.1%}\n"
                        f"Total P&L: ${perf.get('total_pnl', 0):.2f}"
                    )
                
                # Wait before next report
                await asyncio.wait_for(
                    self.shutdown_event.wait(),
                    timeout=report_interval
                )
            
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in performance tracker: {e}")
                await asyncio.sleep(300)
        
        logger.info("📊 Performance tracker stopped")
    
    async def _signal_processor(self) -> None:
        """
        Background task to process incoming trading signals.
        """
        logger.info("📡 Signal processor started")
        
        while self.is_running and not self.shutdown_event.is_set():
            try:
                # Get pending signals from signal manager
                signals = await self.signal_manager.get_pending_signals()
                
                for signal in signals:
                    try:
                        logger.info(f"📡 Processing signal: {signal.symbol} {signal.direction}")
                        
                        # Process signal based on trading mode
                        if self.trading_mode == TradingMode.AUTO:
                            # Auto mode: Execute immediately
                            await self.trading_mode_manager.process_signal_auto(signal, None)
                        
                        elif self.trading_mode == TradingMode.SEMI_AUTO:
                            # Semi-auto: Send for confirmation
                            if self.alert_manager:
                                await self.alert_manager.send_signal_alert(signal)
                        
                        elif self.trading_mode == TradingMode.MANUAL:
                            # Manual: Just notify
                            if self.alert_manager:
                                await self.alert_manager.send_signal_notification(signal)
                        
                        # Mark signal as processed
                        await self.signal_manager.mark_processed(signal)
                    
                    except Exception as e:
                        logger.error(f"Error processing signal {signal.symbol}: {e}")
                
                # Wait before checking again
                await asyncio.sleep(5)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in signal processor: {e}")
                await asyncio.sleep(10)
        
        logger.info("📡 Signal processor stopped")
    
    async def stop_services(self) -> None:
        """
        Gracefully stop all services and cleanup resources.
        """
        logger.info("🛑 Initiating graceful shutdown...")
        
        try:
            # Set shutdown event
            self.shutdown_event.set()
            self.is_running = False
            
            # Stop trading
            if self.trading_mode_manager:
                self.trading_mode_manager.stop_trading()
                logger.info("✅ Trading stopped")
            
            # Cancel background tasks
            logger.info(f"🔄 Cancelling {len(self.background_tasks)} background tasks...")
            for task in self.background_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
            logger.info("✅ Background tasks stopped")
            
            # Stop webhook handler
            if self.webhook_handler:
                await self.webhook_handler.stop()
                logger.info("✅ Webhook handler stopped")
            
            # Disconnect exchanges
            for name, exchange in self.exchanges.items():
                try:
                    await exchange.disconnect()
                    logger.info(f"✅ {name.title()} disconnected")
                except Exception as e:
                    logger.warning(f"⚠️  Error disconnecting {name}: {e}")
            
            # Send final notification
            if self.alert_manager:
                await self.alert_manager.send_message("🛑 v0 Strategy Engine Pro shutting down...")
            
            logger.info("✅ Graceful shutdown completed")
        
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")
    
    async def run(self) -> None:
        """
        Main application run loop.
        """
        try:
            # Initialize all components
            logger.info("=" * 60)
            logger.info("🚀 v0 STRATEGY ENGINE PRO")
            logger.info("=" * 60)
            
            await self.initialize_exchanges()
            await self.initialize_trading_components()
            await self.initialize_communication()
            
            # Start services
            await self.start_services()
            
            # Keep running
            logger.info("🎉 v0 Strategy Engine Pro is now running!")
            logger.info("Press Ctrl+C to stop")
            logger.info("=" * 60)
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
        
        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal")
        except Exception as e:
            logger.error(f"❌ Application error: {e}", exc_info=True)
        finally:
            await self.stop_services()


# ========== Signal Handlers ==========

def setup_signal_handlers(app: StrategyEnginePro) -> None:
    """
    Setup signal handlers for graceful shutdown.
    
    Args:
        app: StrategyEnginePro instance
    """
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        app.shutdown_event.set()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, signal_handler)


# ========== Main Entry Point ==========

async def main():
    """
    Main entry point for the application.
    """
    # Create application instance
    app = StrategyEnginePro()
    
    # Setup signal handlers
    setup_signal_handlers(app)
    
    # Run application
    await app.run()


if __name__ == "__main__":
    try:
        # Display banner
        print("""
╔══════════════════════════════════════════════════════════╗
║   v0 STRATEGY ENGINE PRO                                 ║
║   AI-Powered Multi-Exchange Trading Engine               ║
╠══════════════════════════════════════════════════════════╣
║   📊 10 Exchanges  |  🤖 6 Trading Modes                 ║
║   📡 AI Analysis   |  📱 Telegram Integration            ║
║   ⚡ Real-time     |  🛡️ Risk Management                 ║
╚══════════════════════════════════════════════════════════╝
        """)
        
        # Run the application
        asyncio.run(main())
    
    except KeyboardInterrupt:
        logger.info("🛑 Application stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("👋 Goodbye!")
