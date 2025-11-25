"""
Configuration Settings Module

Centralized configuration management for v0 Strategy Engine Pro.
Loads and validates all environment variables with type safety.

Usage:
    from config.settings import settings
    
    api_key = settings.binance_api_key
    trading_mode = settings.trading_mode
"""

import os
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class TradingModeEnum(str, Enum):
    """Trading mode options"""
    MANUAL = "manual"
    SEMI_AUTO = "semi_auto"
    AUTO = "auto"
    PAPER_TRADING = "paper_trading"
    DEMO = "demo"
    BACKTEST = "backtest"


class AppEnvironment(str, Enum):
    """Application environment"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class ExchangeCredentials:
    """Exchange API credentials"""
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None
    
    @property
    def is_configured(self) -> bool:
        """Check if minimum credentials are provided"""
        return bool(self.api_key and self.api_secret)


@dataclass
class Settings:
    """
    Application settings loaded from environment variables.
    
    All settings are loaded from .env file or environment variables.
    Provides validation and type safety.
    """
    
    # ========== Application Settings ==========
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    debug: bool = False
    secret_key: str = ""
    
    # ========== Trading Configuration ==========
    trading_mode: TradingModeEnum = TradingModeEnum.MANUAL
    default_trade_size: float = 100.0
    max_position_size: float = 1000.0
    max_daily_loss: float = 500.0
    stop_loss_percentage: float = 2.0
    take_profit_percentage: float = 5.0
    max_positions: int = 10
    position_size_percent: float = 2.0
    max_daily_trades: int = 50
    
    # ========== Paper Trading Settings ==========
    enable_paper_trading: bool = False
    paper_trading_initial_balance: float = 10000.0
    paper_trading_maker_fee: float = 0.001
    paper_trading_taker_fee: float = 0.002
    paper_trading_slippage: float = 0.001
    
    # ========== Demo Mode Settings ==========
    enable_demo_mode: bool = False
    demo_initial_balance: float = 10000.0
    demo_reset_daily: bool = False
    demo_track_performance: bool = True
    
    # ========== Backtesting Settings ==========
    enable_backtesting: bool = False
    backtest_start_date: str = "2023-01-01"
    backtest_end_date: str = "2024-12-31"
    backtest_initial_capital: float = 10000.0
    backtest_symbols: List[str] = field(default_factory=lambda: ["BTC/USDT", "ETH/USDT"])
    backtest_timeframe: str = "1h"
    
    # ========== Telegram Configuration ==========
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_use_webhook: bool = False
    telegram_webhook_url: Optional[str] = None
    telegram_webhook_port: int = 8443
    
    # ========== Database Configuration ==========
    database_url: str = "sqlite:///./trading_engine.db"
    db_encryption_key: Optional[str] = None
    
    # ========== Redis Configuration ==========
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_url: Optional[str] = None
    
    # ========== Exchange Credentials ==========
    binance: ExchangeCredentials = field(default_factory=ExchangeCredentials)
    bitget: ExchangeCredentials = field(default_factory=ExchangeCredentials)
    bybit: ExchangeCredentials = field(default_factory=ExchangeCredentials)
    gateio: ExchangeCredentials = field(default_factory=ExchangeCredentials)
    huobi: ExchangeCredentials = field(default_factory=ExchangeCredentials)
    kraken: ExchangeCredentials = field(default_factory=ExchangeCredentials)
    kucoin: ExchangeCredentials = field(default_factory=ExchangeCredentials)
    mexc: ExchangeCredentials = field(default_factory=ExchangeCredentials)
    okx: ExchangeCredentials = field(default_factory=ExchangeCredentials)
    phemex: ExchangeCredentials = field(default_factory=ExchangeCredentials)
    
    # ========== AI Model Configuration ==========
    ai_primary_model: str = "openai"
    ai_fallback_model: str = "anthropic"
    ai_sentiment_model: str = "perplexity"
    ai_signal_model: str = "openai"
    ai_risk_model: str = "anthropic"
    
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    xai_grok_api_key: Optional[str] = None
    xai_grok_api_tier: str = "free"
    perplexity_api_key: Optional[str] = None
    cohere_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    
    # ========== Logging Configuration ==========
    log_level: str = "INFO"
    log_file: str = "./logs/trading_engine.log"
    enable_structured_logs: bool = True
    
    # ========== API Server Configuration ==========
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    
    def __post_init__(self):
        """Validate settings after initialization"""
        self._validate_trading_mode()
        self._validate_exchanges()
        self._validate_telegram()
    
    def _validate_trading_mode(self):
        """Validate trading mode configuration"""
        if self.trading_mode == TradingModeEnum.DEMO:
            if not self.enable_demo_mode:
                logger.warning("Trading mode is 'demo' but ENABLE_DEMO_MODE is false. Enabling demo mode.")
                self.enable_demo_mode = True
        
        if self.trading_mode == TradingModeEnum.BACKTEST:
            if not self.enable_backtesting:
                logger.warning("Trading mode is 'backtest' but ENABLE_BACKTESTING is false. Enabling backtesting.")
                self.enable_backtesting = True
    
    def _validate_exchanges(self):
        """Validate exchange configurations"""
        configured_exchanges = [
            name for name in ['binance', 'bitget', 'bybit', 'gateio', 'huobi',
                              'kraken', 'kucoin', 'mexc', 'okx', 'phemex']
            if getattr(self, name).is_configured
        ]
        
        if not configured_exchanges:
            logger.warning(
                "No exchanges configured! Please set API credentials in .env file. "
                "See .env.example for configuration template."
            )
        else:
            logger.info(f"Configured exchanges: {', '.join(configured_exchanges)}")
    
    def _validate_telegram(self):
        """Validate Telegram configuration"""
        if self.telegram_use_webhook and not self.telegram_webhook_url:
            logger.error("TELEGRAM_USE_WEBHOOK is true but TELEGRAM_WEBHOOK_URL is not set!")
            raise ValueError("Webhook URL required when webhook mode is enabled")
    
    @classmethod
    def load_from_env(cls) -> 'Settings':
        """
        Load settings from environment variables.
        
        Returns:
            Settings instance with values from environment
        """
        # Helper function to get boolean
        def get_bool(key: str, default: bool = False) -> bool:
            value = os.getenv(key, str(default)).lower()
            return value in ('true', '1', 'yes', 'on')
        
        # Helper function to get int
        def get_int(key: str, default: int = 0) -> int:
            try:
                return int(os.getenv(key, default))
            except (ValueError, TypeError):
                return default
        
        # Helper function to get float
        def get_float(key: str, default: float = 0.0) -> float:
            try:
                return float(os.getenv(key, default))
            except (ValueError, TypeError):
                return default
        
        # Helper function to get list
        def get_list(key: str, default: List[str] = None) -> List[str]:
            value = os.getenv(key, '')
            if not value:
                return default or []
            return [item.strip() for item in value.split(',')]
        
        # Create exchange credentials
        def get_exchange_creds(name: str) -> ExchangeCredentials:
            prefix = name.upper()
            return ExchangeCredentials(
                api_key=os.getenv(f"{prefix}_API_KEY"),
                api_secret=os.getenv(f"{prefix}_API_SECRET"),
                passphrase=os.getenv(f"{prefix}_PASSPHRASE")
            )
        
        return cls(
            # Application
            app_env=AppEnvironment(os.getenv('APP_ENV', 'development')),
            debug=get_bool('DEBUG', False),
            secret_key=os.getenv('SECRET_KEY', ''),
            
            # Trading
            trading_mode=TradingModeEnum(os.getenv('TRADING_MODE', 'manual')),
            default_trade_size=get_float('DEFAULT_TRADE_SIZE', 100.0),
            max_position_size=get_float('MAX_POSITION_SIZE', 1000.0),
            max_daily_loss=get_float('MAX_DAILY_LOSS', 500.0),
            stop_loss_percentage=get_float('STOP_LOSS_PERCENTAGE', 2.0),
            take_profit_percentage=get_float('TAKE_PROFIT_PERCENTAGE', 5.0),
            max_positions=get_int('MAX_POSITIONS', 10),
            position_size_percent=get_float('POSITION_SIZE_PERCENT', 2.0),
            max_daily_trades=get_int('MAX_DAILY_TRADES', 50),
            
            # Paper Trading
            enable_paper_trading=get_bool('ENABLE_PAPER_TRADING', False),
            paper_trading_initial_balance=get_float('PAPER_TRADING_INITIAL_BALANCE', 10000.0),
            paper_trading_maker_fee=get_float('PAPER_TRADING_MAKER_FEE', 0.001),
            paper_trading_taker_fee=get_float('PAPER_TRADING_TAKER_FEE', 0.002),
            paper_trading_slippage=get_float('PAPER_TRADING_SLIPPAGE', 0.001),
            
            # Demo Mode
            enable_demo_mode=get_bool('ENABLE_DEMO_MODE', False),
            demo_initial_balance=get_float('DEMO_INITIAL_BALANCE', 10000.0),
            demo_reset_daily=get_bool('DEMO_RESET_DAILY', False),
            demo_track_performance=get_bool('DEMO_TRACK_PERFORMANCE', True),
            
            # Backtesting
            enable_backtesting=get_bool('ENABLE_BACKTESTING', False),
            backtest_start_date=os.getenv('BACKTEST_START_DATE', '2023-01-01'),
            backtest_end_date=os.getenv('BACKTEST_END_DATE', '2024-12-31'),
            backtest_initial_capital=get_float('BACKTEST_INITIAL_CAPITAL', 10000.0),
            backtest_symbols=get_list('BACKTEST_SYMBOLS', ['BTC/USDT', 'ETH/USDT']),
            backtest_timeframe=os.getenv('BACKTEST_TIMEFRAME', '1h'),
            
            # Telegram
            telegram_bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
            telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID'),
            telegram_use_webhook=get_bool('TELEGRAM_USE_WEBHOOK', False),
            telegram_webhook_url=os.getenv('TELEGRAM_WEBHOOK_URL'),
            telegram_webhook_port=get_int('TELEGRAM_WEBHOOK_PORT', 8443),
            
            # Database
            database_url=os.getenv('DATABASE_URL', 'sqlite:///./trading_engine.db'),
            db_encryption_key=os.getenv('DB_ENCRYPTION_KEY'),
            
            # Redis
            redis_host=os.getenv('REDIS_HOST', 'localhost'),
            redis_port=get_int('REDIS_PORT', 6379),
            redis_db=get_int('REDIS_DB', 0),
            redis_password=os.getenv('REDIS_PASSWORD'),
            redis_url=os.getenv('REDIS_URL'),
            
            # Exchanges
            binance=get_exchange_creds('binance'),
            bitget=get_exchange_creds('bitget'),
            bybit=get_exchange_creds('bybit'),
            gateio=get_exchange_creds('gateio'),
            huobi=get_exchange_creds('huobi'),
            kraken=get_exchange_creds('kraken'),
            kucoin=get_exchange_creds('kucoin'),
            mexc=get_exchange_creds('mexc'),
            okx=get_exchange_creds('okx'),
            phemex=get_exchange_creds('phemex'),
            
            # AI Models
            ai_primary_model=os.getenv('AI_PRIMARY_MODEL', 'openai'),
            ai_fallback_model=os.getenv('AI_FALLBACK_MODEL', 'anthropic'),
            ai_sentiment_model=os.getenv('AI_SENTIMENT_MODEL', 'perplexity'),
            ai_signal_model=os.getenv('AI_SIGNAL_MODEL', 'openai'),
            ai_risk_model=os.getenv('AI_RISK_MODEL', 'anthropic'),
            
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
            google_api_key=os.getenv('GOOGLE_API_KEY'),
            xai_grok_api_key=os.getenv('XAI_GROK_API_KEY'),
            xai_grok_api_tier=os.getenv('XAI_GROK_API_TIER', 'free'),
            perplexity_api_key=os.getenv('PERPLEXITY_API_KEY'),
            cohere_api_key=os.getenv('COHERE_API_KEY'),
            mistral_api_key=os.getenv('MISTRAL_API_KEY'),
            groq_api_key=os.getenv('GROQ_API_KEY'),
            
            # Logging
            log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            log_file=os.getenv('LOG_FILE', './logs/trading_engine.log'),
            enable_structured_logs=get_bool('ENABLE_STRUCTURED_LOGS', True),
            
            # API Server
            api_host=os.getenv('API_HOST', '0.0.0.0'),
            api_port=get_int('API_PORT', 8000),
            api_reload=get_bool('API_RELOAD', True)
        )


# ========== Global Settings Instance ==========

# Load settings on module import
settings = Settings.load_from_env()

logger.info(f"Settings loaded: app_env={settings.app_env.value}, trading_mode={settings.trading_mode.value}")
