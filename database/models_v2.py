"""Enhanced ORM Models - Phase 2.1

Enhanced database models supporting Crypto, Forex, and Stock assets.
Includes encryption support for sensitive fields.
Features audit trails, versioning, and comprehensive analytics.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, JSON, 
    ForeignKey, Enum as SQLEnum, Text, Index, UniqueConstraint,
    BigInteger, DECIMAL
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from encrypted_fields import EncryptedString, EncryptedJSON, EncryptionHelper

Base = declarative_base()

# ============================================================================
# ENUMS
# ============================================================================

class AssetClass(str, Enum):
    """Asset classification."""
    CRYPTO = "crypto"
    FOREX = "forex"
    STOCK = "stock"

class SignalType(str, Enum):
    """Trade signal types."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"

class MarketSentiment(str, Enum):
    """Market sentiment levels."""
    VERY_BEARISH = "very_bearish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    BULLISH = "bullish"
    VERY_BULLISH = "very_bullish"

class TradeStatus(str, Enum):
    """Trade execution status."""
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    CLOSED = "closed"
    FAILED = "failed"

# ============================================================================
# BASE MODELS - Mixins
# ============================================================================

class TimestampMixin:
    """Adds timestamp tracking to models."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class AuditMixin:
    """Adds audit trail tracking."""
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
    audit_log = Column(JSON, default=dict, nullable=False)

class MetadataMixin:
    """Adds flexible metadata storage."""
    metadata = Column(JSON, default=dict, nullable=False)

# ============================================================================
# CORE MODELS
# ============================================================================

class User(Base, TimestampMixin, AuditMixin):
    """Enhanced User model with encryption support."""
    __tablename__ = 'users_v2'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    
    # Encrypted sensitive fields
    hashed_password = Column(EncryptedString, nullable=False)
    api_keys = Column(EncryptedJSON, default=dict, nullable=False)
    
    is_active = Column(Boolean, default=True, index=True)
    is_admin = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0)
    
    # Security settings
    two_factor_enabled = Column(Boolean, default=False)
    totp_secret = Column(EncryptedString, nullable=True)
    
    # Relationships
    strategies = relationship("Strategy", back_populates="owner", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    performance_metrics = relationship("PerformanceMetrics", back_populates="user")
    
    __table_args__ = (
        Index('idx_user_active', 'is_active', 'created_at'),
    )

class UserSession(Base, TimestampMixin):
    """Secure user session management."""
    __tablename__ = 'user_sessions_v2'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey('users_v2.id'), nullable=False, index=True)
    
    # Encrypted token
    access_token = Column(EncryptedString, nullable=False)
    refresh_token = Column(EncryptedString, nullable=True)
    
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    expires_at = Column(DateTime, nullable=False, index=True)
    last_activity = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True, index=True)
    
    user = relationship("User", back_populates="sessions")
    
    __table_args__ = (
        Index('idx_session_token_active', 'access_token', 'is_active'),
        Index('idx_session_expires', 'expires_at'),
    )

class Asset(Base, TimestampMixin, MetadataMixin):
    """Unified asset model supporting all asset classes."""
    __tablename__ = 'assets_v2'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    symbol = Column(String, nullable=False, index=True)
    asset_class = Column(SQLEnum(AssetClass), nullable=False, index=True)
    name = Column(String, nullable=False)
    exchange = Column(String, nullable=False, index=True)
    
    # Precision and trading parameters
    price_precision = Column(Integer, default=8)
    amount_precision = Column(Integer, default=8)
    min_order_amount = Column(DECIMAL(20, 8), nullable=True)
    max_order_amount = Column(DECIMAL(20, 8), nullable=True)
    
    # Asset-specific data
    crypto_metadata = Column(JSON, nullable=True)
    forex_metadata = Column(JSON, nullable=True)
    stock_metadata = Column(JSON, nullable=True)
    
    is_active = Column(Boolean, default=True, index=True)
    is_tradable = Column(Boolean, default=True, index=True)
    
    # Relationships
    market_data = relationship("MarketData", back_populates="asset", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="asset")
    signals = relationship("Signal", back_populates="asset")
    
    __table_args__ = (
        UniqueConstraint('symbol', 'asset_class', 'exchange', name='uq_asset_symbol_class'),
        Index('idx_asset_search', 'asset_class', 'is_active', 'is_tradable'),
    )

class MarketData(Base, TimestampMixin):
    """OHLCV market data for assets."""
    __tablename__ = 'market_data_v2'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    asset_id = Column(String, ForeignKey('assets_v2.id'), nullable=False, index=True)
    
    timeframe = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    open_price = Column(DECIMAL(20, 8), nullable=False)
    high_price = Column(DECIMAL(20, 8), nullable=False)
    low_price = Column(DECIMAL(20, 8), nullable=False)
    close_price = Column(DECIMAL(20, 8), nullable=False)
    volume = Column(DECIMAL(20, 8), nullable=False)
    
    # Technical indicators
    rsi = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    bollinger_upper = Column(DECIMAL(20, 8), nullable=True)
    bollinger_lower = Column(DECIMAL(20, 8), nullable=True)
    
    asset = relationship("Asset", back_populates="market_data")
    
    __table_args__ = (
        UniqueConstraint('asset_id', 'timeframe', 'timestamp', name='uq_market_data'),
        Index('idx_market_data_search', 'asset_id', 'timeframe', 'timestamp'),
    )

class Strategy(Base, TimestampMixin, AuditMixin, MetadataMixin):
    """Trading strategy configuration."""
    __tablename__ = 'strategies_v2'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey('users_v2.id'), nullable=False, index=True)
    
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    strategy_type = Column(String, nullable=False)
    config = Column(EncryptedJSON, default=dict, nullable=False)
    
    risk_params = Column(JSON, default=dict, nullable=False)
    max_drawdown = Column(Float, default=0.2)
    max_daily_loss = Column(Float, nullable=True)
    position_size_pct = Column(Float, default=0.05)
    
    is_active = Column(Boolean, default=False, index=True)
    is_public = Column(Boolean, default=False)
    
    owner = relationship("User", back_populates="strategies")
    trades = relationship("Trade", back_populates="strategy")
    performance_metrics = relationship("PerformanceMetrics", back_populates="strategy")
    
    __table_args__ = (
        Index('idx_strategy_search', 'user_id', 'is_active', 'is_public'),
    )

class Signal(Base, TimestampMixin, MetadataMixin):
    """Trading signal with comprehensive analysis."""
    __tablename__ = 'signals_v2'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    asset_id = Column(String, ForeignKey('assets_v2.id'), nullable=False, index=True)
    
    signal_type = Column(SQLEnum(SignalType), nullable=False, index=True)
    confidence = Column(Float, default=0.5)
    
    current_price = Column(DECIMAL(20, 8), nullable=False)
    entry_price = Column(DECIMAL(20, 8), nullable=False)
    target_price = Column(DECIMAL(20, 8), nullable=False)
    stop_loss = Column(DECIMAL(20, 8), nullable=False)
    
    risk_reward_ratio = Column(Float, nullable=False)
    profitability_score = Column(Float, default=0)
    
    market_sentiment = Column(SQLEnum(MarketSentiment), nullable=False)
    timeframe = Column(String, nullable=False)
    
    analysis = Column(Text, nullable=True)
    
    is_active = Column(Boolean, default=True, index=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    
    asset = relationship("Asset", back_populates="signals")
    
    __table_args__ = (
        Index('idx_signal_search', 'asset_id', 'is_active', 'created_at'),
    )

class Trade(Base, TimestampMixin, AuditMixin):
    """Executed trades with full audit trail."""
    __tablename__ = 'trades_v2'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey('users_v2.id'), nullable=False, index=True)
    strategy_id = Column(String, ForeignKey('strategies_v2.id'), nullable=True, index=True)
    asset_id = Column(String, ForeignKey('assets_v2.id'), nullable=False, index=True)
    
    status = Column(SQLEnum(TradeStatus), default=TradeStatus.PENDING, index=True)
    
    entry_price = Column(DECIMAL(20, 8), nullable=False)
    exit_price = Column(DECIMAL(20, 8), nullable=True)
    quantity = Column(DECIMAL(20, 8), nullable=False)
    
    commission = Column(DECIMAL(20, 8), default=0)
    pnl = Column(DECIMAL(20, 8), nullable=True)
    pnl_percentage = Column(Float, nullable=True)
    
    opened_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    closed_at = Column(DateTime, nullable=True, index=True)
    duration_seconds = Column(Integer, nullable=True)
    
    notes = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="trades")
    strategy = relationship("Strategy", back_populates="trades")
    asset = relationship("Asset", back_populates="trades")
    
    __table_args__ = (
        Index('idx_trade_search', 'user_id', 'strategy_id', 'status', 'opened_at'),
    )

class PerformanceMetrics(Base, TimestampMixin):
    """Aggregated performance metrics."""
    __tablename__ = 'performance_metrics_v2'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey('users_v2.id'), nullable=False, index=True)
    strategy_id = Column(String, ForeignKey('strategies_v2.id'), nullable=True, index=True)
    
    period = Column(String, nullable=False)  # 'daily', 'weekly', 'monthly', 'all_time'
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=False, index=True)
    
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0)  # 0-1
    
    total_pnl = Column(DECIMAL(20, 8), default=0)
    max_drawdown = Column(Float, default=0)
    
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    
    avg_win = Column(DECIMAL(20, 8), nullable=True)
    avg_loss = Column(DECIMAL(20, 8), nullable=True)
    largest_win = Column(DECIMAL(20, 8), nullable=True)
    largest_loss = Column(DECIMAL(20, 8), nullable=True)
    
    user = relationship("User", back_populates="performance_metrics")
    strategy = relationship("Strategy", back_populates="performance_metrics")
    
    __table_args__ = (
        Index('idx_metrics_search', 'user_id', 'strategy_id', 'period', 'start_date'),
    )
