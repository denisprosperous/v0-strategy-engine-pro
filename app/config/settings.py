import os
from typing import Optional, Dict, Any
from pydantic import BaseSettings, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config.env")

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    database_url: str = Field(default="sqlite:///./trading_bot.db", env="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # JWT
    jwt_secret: str = Field(..., env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiry: int = Field(default=3600, env="JWT_EXPIRY")
    
    # Telegram
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: Optional[str] = Field(default=None, env="TELEGRAM_WEBHOOK_URL")
    
    # Bitget Exchange
    bitget_api_key: str = Field(..., env="BITGET_API_KEY")
    bitget_secret_key: str = Field(..., env="BITGET_SECRET_KEY")
    bitget_passphrase: str = Field(..., env="BITGET_PASSPHRASE")
    bitget_testnet: bool = Field(default=False, env="BITGET_TESTNET")
    
    # Kraken Exchange
    kraken_api_key: str = Field(..., env="KRAKEN_API_KEY")
    kraken_private_key: str = Field(..., env="KRAKEN_PRIVATE_KEY")
    kraken_testnet: bool = Field(default=False, env="KRAKEN_TESTNET")
    
    # AI & ML
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    huggingface_token: str = Field(..., env="HUGGINGFACE_TOKEN")
    
    # News & Sentiment
    mediastack_api_key: str = Field(..., env="MEDIASTACK_API_KEY")
    currents_api_key: str = Field(..., env="CURRENTS_API_KEY")
    rapidapi_key: str = Field(..., env="RAPIDAPI_KEY")
    
    # Risk Management
    max_daily_loss: float = Field(default=1000.0, env="MAX_DAILY_LOSS")
    max_position_size: float = Field(default=1000.0, env="MAX_POSITION_SIZE")
    max_open_trades: int = Field(default=5, env="MAX_OPEN_TRADES")
    trade_cooldown_ms: int = Field(default=30000, env="TRADE_COOLDOWN_MS")
    stop_loss_percentage: float = Field(default=0.02, env="STOP_LOSS_PERCENTAGE")
    take_profit_percentage: float = Field(default=0.05, env="TAKE_PROFIT_PERCENTAGE")
    
    # Model Configuration
    model_update_interval_hours: int = Field(default=24, env="MODEL_UPDATE_INTERVAL_HOURS")
    sentiment_analysis_enabled: bool = Field(default=True, env="SENTIMENT_ANALYSIS_ENABLED")
    ai_recommendations_enabled: bool = Field(default=True, env="AI_RECOMMENDATIONS_ENABLED")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    
    # Security
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")
    bcrypt_rounds: int = Field(default=12, env="BCRYPT_ROUNDS")
    
    # Trading Pairs Configuration
    default_trading_pairs: Dict[str, Any] = {
        "crypto": [
            {"symbol": "BTC/USDT", "exchange": "bitget", "min_volume": 1000000},
            {"symbol": "ETH/USDT", "exchange": "bitget", "min_volume": 500000},
            {"symbol": "BNB/USDT", "exchange": "bitget", "min_volume": 200000},
            {"symbol": "ADA/USDT", "exchange": "bitget", "min_volume": 100000},
            {"symbol": "SOL/USDT", "exchange": "bitget", "min_volume": 150000},
            {"symbol": "DOT/USDT", "exchange": "bitget", "min_volume": 80000},
            {"symbol": "MATIC/USDT", "exchange": "bitget", "min_volume": 120000},
            {"symbol": "LINK/USDT", "exchange": "bitget", "min_volume": 60000},
            {"symbol": "UNI/USDT", "exchange": "bitget", "min_volume": 40000},
            {"symbol": "AVAX/USDT", "exchange": "bitget", "min_volume": 90000}
        ],
        "forex": [
            {"symbol": "EUR/USD", "exchange": "kraken", "min_volume": 5000000},
            {"symbol": "GBP/USD", "exchange": "kraken", "min_volume": 3000000},
            {"symbol": "USD/JPY", "exchange": "kraken", "min_volume": 4000000},
            {"symbol": "USD/CHF", "exchange": "kraken", "min_volume": 2000000},
            {"symbol": "AUD/USD", "exchange": "kraken", "min_volume": 1500000}
        ]
    }
    
    # Strategy Configuration
    strategies: Dict[str, Any] = {
        "breakout": {
            "enabled": True,
            "timeframe": "1h",
            "volume_threshold": 1.5,
            "price_change_threshold": 0.02,
            "stop_loss_pct": 0.015,
            "take_profit_pct": 0.03
        },
        "mean_reversion": {
            "enabled": True,
            "timeframe": "4h",
            "rsi_period": 14,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.025
        },
        "momentum": {
            "enabled": True,
            "timeframe": "15m",
            "momentum_period": 20,
            "sentiment_weight": 0.3,
            "stop_loss_pct": 0.018,
            "take_profit_pct": 0.035
        },
        "sentiment": {
            "enabled": True,
            "timeframe": "5m",
            "volatility_threshold": 2.0,
            "news_sentiment_threshold": 0.6,
            "stop_loss_pct": 0.01,
            "take_profit_pct": 0.02
        }
    }
    
    class Config:
        env_file = "config.env"
        case_sensitive = False

# Global settings instance
settings = Settings()

# Validate critical settings
def validate_settings():
    """Validate that all critical settings are properly configured"""
    required_fields = [
        'jwt_secret', 'telegram_bot_token', 'bitget_api_key', 
        'bitget_secret_key', 'bitget_passphrase', 'kraken_api_key',
        'kraken_private_key', 'openai_api_key', 'huggingface_token'
    ]
    
    missing_fields = []
    for field in required_fields:
        if not getattr(settings, field, None):
            missing_fields.append(field)
    
    if missing_fields:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_fields)}")
    
    return True

# Validate on import
try:
    validate_settings()
except ValueError as e:
    print(f"Configuration Error: {e}")
    print("Please check your config.env file and ensure all required variables are set.")
    raise
