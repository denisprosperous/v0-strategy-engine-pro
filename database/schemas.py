"""Enhanced Database Schemas - Phase 1

Comprehensive data models supporting Cryptocurrency, Forex, and Stock assets.
Supports unified asset interface across all trading classes.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import uuid

from pydantic import BaseModel, Field, validator
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


# ============================================================================
# ENUMS - Asset Class Classification
# ============================================================================

class AssetClass(str, Enum):
    """Asset class classification for unified handling."""
    CRYPTO = "crypto"
    FOREX = "forex"
    STOCK = "stock"


class TradingPair(str, Enum):
    """Common trading pair categories."""
    CRYPTO_CRYPTO = "crypto_crypto"  # BTC/ETH
    CRYPTO_FIAT = "crypto_fiat"      # BTC/USD
    MAJOR_PAIRS = "major_pairs"      # EUR/USD, GBP/USD
    MINOR_PAIRS = "minor_pairs"      # EUR/GBP, AUD/USD
    EXOTIC_PAIRS = "exotic_pairs"    # USD/TRY, USD/MXN
    STOCK_INDEX = "stock_index"      # Indices like S&P 500
    INDIVIDUAL_STOCK = "individual_stock"  # AAPL, MSFT


class SignalType(str, Enum):
    """Trade signal types."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class MarketSentiment(str, Enum):
    """Overall market sentiment classification."""
    VERY_BEARISH = "very_bearish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    BULLISH = "bullish"
    VERY_BULLISH = "very_bullish"


# ============================================================================
# PYDANTIC MODELS - Data Validation and Serialization
# ============================================================================

class OHLCVData(BaseModel):
    """Candlestick OHLCV data for any asset class."""
    timestamp: datetime = Field(..., description="Candle timestamp")
    open: float = Field(..., gt=0, description="Opening price")
    high: float = Field(..., gt=0, description="Highest price")
    low: float = Field(..., gt=0, description="Lowest price")
    close: float = Field(..., gt=0, description="Closing price")
    volume: float = Field(..., ge=0, description="Trading volume")
    
    @validator('high')
    def high_ge_low(cls, v, values):
        if 'low' in values and v < values['low']:
            raise ValueError('high must be >= low')
        return v


class AssetMetadata(BaseModel):
    """Unified asset metadata for all asset classes."""
    symbol: str = Field(..., description="Asset symbol/ticker")
    asset_class: AssetClass = Field(..., description="Asset classification")
    name: str = Field(..., description="Asset full name")
    exchange: str = Field(..., description="Primary exchange")
    
    # Asset-specific metadata
    cryptocurrency_info: Optional[Dict[str, Any]] = Field(
        None, 
        description="Crypto-specific: market cap, circulating supply, etc."
    )
    forex_info: Optional[Dict[str, Any]] = Field(
        None,
        description="Forex-specific: base/quote currencies, pip size, etc."
    )
    stock_info: Optional[Dict[str, Any]] = Field(
        None,
        description="Stock-specific: sector, industry, market cap, etc."
    )
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class TechnicalIndicators(BaseModel):
    """Technical analysis indicators for signal generation."""
    rsi: Optional[float] = Field(None, ge=0, le=100, description="Relative Strength Index")
    macd: Optional[float] = Field(None, description="MACD value")
    macd_signal: Optional[float] = Field(None, description="MACD signal line")
    macd_histogram: Optional[float] = Field(None, description="MACD histogram")
    
    sma_20: Optional[float] = Field(None, description="20-period Simple Moving Average")
    sma_50: Optional[float] = Field(None, description="50-period Simple Moving Average")
    sma_200: Optional[float] = Field(None, description="200-period Simple Moving Average")
    
    ema_12: Optional[float] = Field(None, description="12-period Exponential Moving Average")
    ema_26: Optional[float] = Field(None, description="26-period Exponential Moving Average")
    
    bollinger_upper: Optional[float] = Field(None, description="Bollinger Bands upper band")
    bollinger_middle: Optional[float] = Field(None, description="Bollinger Bands middle band")
    bollinger_lower: Optional[float] = Field(None, description="Bollinger Bands lower band")
    
    atr: Optional[float] = Field(None, description="Average True Range")
    adx: Optional[float] = Field(None, ge=0, le=100, description="Average Directional Index")
    
    stoch_k: Optional[float] = Field(None, ge=0, le=100, description="Stochastic %K")
    stoch_d: Optional[float] = Field(None, ge=0, le=100, description="Stochastic %D")
    
    obv: Optional[float] = Field(None, description="On-Balance Volume")
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TradeSignal(BaseModel):
    """Intelligent trade signal with recommendations."""
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    asset_symbol: str = Field(..., description="Asset to trade")
    asset_class: AssetClass = Field(...)
    
    signal_type: SignalType = Field(..., description="Buy/Sell/Hold signal")
    confidence: float = Field(..., ge=0, le=1, description="Signal confidence 0-1")
    
    current_price: float = Field(..., gt=0)
    entry_price: float = Field(..., gt=0, description="Recommended entry point")
    
    # Multi-level take profit targets
    take_profit_1: float = Field(..., gt=0, description="First take profit level (50% of position)")
    take_profit_2: Optional[float] = Field(None, gt=0, description="Second take profit level (30% of position)")
    take_profit_3: Optional[float] = Field(None, gt=0, description="Third take profit level (20% of position)")
    
    # Stop loss levels
    stop_loss: float = Field(..., gt=0, description="Hard stop loss level")
    trailing_stop_percentage: Optional[float] = Field(
        None, ge=0, le=10,
        description="Trailing stop percentage for exit optimization"
    )
    
    # Performance metrics
    risk_reward_ratio: float = Field(..., gt=0, description="Risk/reward ratio")
    profitability_score: float = Field(..., ge=0, le=100, description="Expected profitability 0-100")
    success_percentage: float = Field(..., ge=0, le=100, description="Historical success rate %")
    
    # Timing and recommendation
    recommended_timeframe: str = Field(..., description="Suggested timeframe (1h, 4h, 1d, etc)")
    market_sentiment: MarketSentiment = Field(...)
    
    technical_indicators: TechnicalIndicators = Field(...)
    
    # Supporting analysis
    analysis_reason: str = Field(..., description="Why this signal was generated")
    pair_analysis: str = Field(..., description="Detailed pair analysis")
    
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Signal validity period")


class RecommendationBatch(BaseModel):
    """Batch of trading recommendations from analysis engine."""
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    signals: List[TradeSignal] = Field(..., description="Generated trade signals")
    overall_market_sentiment: MarketSentiment
    
    top_opportunities: List[Dict[str, Any]] = Field(
        ...,
        description="Top trading opportunities ranked by profitability"
    )
    risk_warning: Optional[str] = Field(None, description="Market risk warnings if any")


# ============================================================================
# SQLALCHEMY MODELS - Database ORM
# ============================================================================

Base = declarative_base()


class DBAsset(Base):
    """ORM model for asset data."""
    __tablename__ = 'assets'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol = Column(String, unique=True, index=True, nullable=False)
    asset_class = Column(SQLEnum(AssetClass), nullable=False, index=True)
    name = Column(String, nullable=False)
    exchange = Column(String, nullable=False, index=True)
    
    # JSON fields for asset-specific metadata
    crypto_metadata = Column(JSON, nullable=True)
    forex_metadata = Column(JSON, nullable=True)
    stock_metadata = Column(JSON, nullable=True)
    
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DBOHLCV(Base):
    """ORM model for OHLCV candlestick data."""
    __tablename__ = 'ohlcv_data'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_symbol = Column(String, index=True, nullable=False)
    timeframe = Column(String, nullable=False)  # 1m, 5m, 15m, 1h, 4h, 1d, etc
    
    timestamp = Column(DateTime, index=True, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class DBTradeSignal(Base):
    """ORM model for trade signals."""
    __tablename__ = 'trade_signals'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_symbol = Column(String, index=True, nullable=False)
    asset_class = Column(SQLEnum(AssetClass), nullable=False)
    
    signal_type = Column(SQLEnum(SignalType), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    
    entry_price = Column(Float, nullable=False)
    take_profit_1 = Column(Float, nullable=False)
    take_profit_2 = Column(Float, nullable=True)
    take_profit_3 = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=False)
    
    profitability_score = Column(Float, nullable=False)
    success_percentage = Column(Float, nullable=False)
    
    market_sentiment = Column(SQLEnum(MarketSentiment), nullable=False)
    analysis_reason = Column(String, nullable=False)
    pair_analysis = Column(String, nullable=False)
    
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)
    
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DBSession:
    """Database session management."""
    def __init__(self, db_url: str = "sqlite:///strategy_engine.db"):
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
    
    def get_session(self):
        """Get new database session."""
        return self.SessionLocal()
