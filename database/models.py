from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .database import Base
import datetime
from enum import Enum as PyEnum

# Enums for model constraints
class TradeSide(PyEnum):
    BUY = "buy"
    SELL = "sell"

class OrderType(PyEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

class TradeStatus(PyEnum):
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELED = "canceled"
    REJECTED = "rejected"

class SignalType(PyEnum):
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"
    ON_CHAIN = "on_chain"
    SOCIAL = "social"
    FUNDAMENTAL = "fundamental"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    strategies = relationship("Strategy", back_populates="owner")
    trades = relationship("Trade", back_populates="user")
    performance_metrics = relationship("PerformanceMetrics", back_populates="user")
    social_trades = relationship("SocialTrade", back_populates="user")

class Strategy(Base):
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    config = Column(JSON)
    risk_parameters = Column(JSON)
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    owner = relationship("User", back_populates="strategies")
    trades = relationship("Trade", back_populates="strategy")
    performance_metrics = relationship("PerformanceMetrics", back_populates="strategy")

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    exchange = Column(String, index=True)
    symbol = Column(String, index=True)
    side = Column(Enum(TradeSide))
    order_type = Column(Enum(OrderType))
    amount = Column(Float)
    price = Column(Float)
    fee = Column(Float)
    fee_currency = Column(String)
    status = Column(Enum(TradeStatus))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    closed_at = Column(DateTime, index=True)
    pnl = Column(Float)
    pnl_percentage = Column(Float)
    risk_reward_ratio = Column(Float)
    notes = Column(String)
    tags = Column(JSON)  # For categorizing trades
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    strategy = relationship("Strategy", back_populates="trades")
    user = relationship("User", back_populates="trades")
    signals = relationship("TradeSignal", back_populates="trade")
    executions = relationship("TradeExecution", back_populates="trade")
    social_trades = relationship("SocialTrade", back_populates="original_trade")

class TradeSignal(Base):
    __tablename__ = "trade_signals"
    
    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"))
    signal_type = Column(Enum(SignalType))
    signal_strength = Column(Float)
    confidence = Column(Float)
    signal_data = Column(JSON)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    
    # Relationships
    trade = relationship("Trade", back_populates="signals")

class TradeExecution(Base):
    __tablename__ = "trade_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"))
    exchange = Column(String)
    order_id = Column(String)
    executed_price = Column(Float)
    executed_amount = Column(Float)
    fee = Column(Float)
    fee_currency = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    
    # Relationships
    trade = relationship("Trade", back_populates="executions")

class PerformanceMetrics(Base):
    __tablename__ = "performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    period = Column(String)  # 'daily', 'weekly', 'monthly', 'yearly', 'all_time'
    start_date = Column(DateTime, index=True)
    end_date = Column(DateTime, index=True)
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    win_rate = Column(Float)
    total_pnl = Column(Float)
    max_drawdown = Column(Float)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    profit_factor = Column(Float)
    average_holding_period = Column(Float)  # in hours
    average_win = Column(Float)
    average_loss = Column(Float)
    largest_win = Column(Float)
    largest_loss = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    strategy = relationship("Strategy", back_populates="performance_metrics")
    user = relationship("User", back_populates="performance_metrics")

class SocialTrade(Base):
    __tablename__ = "social_trades"
    
    id = Column(Integer, primary_key=True, index=True)
    original_trade_id = Column(Integer, ForeignKey("trades.id"))
    copied_by_user_id = Column(Integer, ForeignKey("users.id"))
    copied_trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    copied_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    status = Column(String)  # 'pending', 'executed', 'failed'
    execution_price = Column(Float, nullable=True)
    execution_pnl = Column(Float, nullable=True)
    
    # Relationships
    original_trade = relationship("Trade", foreign_keys=[original_trade_id])
    copied_by_user = relationship("User", foreign_keys=[copied_by_user_id])
    copied_trade = relationship("Trade", foreign_keys=[copied_trade_id])
    user = relationship("User", back_populates="social_trades")

class MarketDataCache(Base):
    __tablename__ = "market_data_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    timeframe = Column(String)
    data_type = Column(String)  # 'ohlcv', 'orderbook', 'funding_rate', etc.
    data = Column(JSON)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    expires_at = Column(DateTime, index=True)
