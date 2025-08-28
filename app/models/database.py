from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import json
from typing import Optional, Dict, Any

from app.config.settings import settings

# Create database engine
engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    """User model for authentication and management"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    telegram_id = Column(String(50), unique=True, index=True)
    role = Column(String(20), default="trader")  # admin, trader, viewer
    is_active = Column(Boolean, default=True)
    api_keys = Column(JSON, default={})
    settings = Column(JSON, default={})
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    trades = relationship("Trade", back_populates="user")
    strategies = relationship("Strategy", back_populates="user")

class Strategy(Base):
    """Trading strategy model"""
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    strategy_type = Column(String(50), nullable=False)  # breakout, mean_reversion, momentum, sentiment
    parameters = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    performance_metrics = Column(JSON, default={})
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="strategies")
    trades = relationship("Trade", back_populates="strategy")

class Trade(Base):
    """Trade execution model"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    exchange = Column(String(20), nullable=False)  # bitget, kraken
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # buy, sell
    order_type = Column(String(20), default="market")  # market, limit, stop
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    status = Column(String(20), default="open")  # open, closed, cancelled, filled
    pnl = Column(Float, default=0.0)
    fees = Column(Float, default=0.0)
    exchange_order_id = Column(String(100))
    metadata = Column(JSON, default={})
    executed_at = Column(DateTime, default=func.now())
    closed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="trades")
    strategy = relationship("Strategy", back_populates="trades")

class MarketData(Base):
    """Market data storage model"""
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, index=True)
    exchange = Column(String(20), nullable=False)
    symbol = Column(String(20), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    timeframe = Column(String(10), nullable=False)  # 1m, 5m, 15m, 1h, 4h, 1d
    
    __table_args__ = (
        # Create composite index for better query performance
        {'sqlite_on_conflict': 'REPLACE'}
    )

class SentimentData(Base):
    """Sentiment analysis data model"""
    __tablename__ = "sentiment_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False)
    source = Column(String(20), nullable=False)  # twitter, reddit, news
    sentiment_score = Column(Float, nullable=False)  # -1 to 1
    confidence = Column(Float, nullable=False)  # 0 to 1
    text_sample = Column(Text)
    metadata = Column(JSON, default={})
    timestamp = Column(DateTime, default=func.now())

class TradeSignal(Base):
    """Trading signal model"""
    __tablename__ = "trade_signals"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    signal_type = Column(String(10), nullable=False)  # buy, sell, hold
    strength = Column(Float, nullable=False)  # 0 to 1
    price_target = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    reasoning = Column(Text)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=func.now())
    executed = Column(Boolean, default=False)

class AIRecommendation(Base):
    """AI-generated trading recommendations"""
    __tablename__ = "ai_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False)
    recommendation_type = Column(String(20), nullable=False)  # buy, sell, hold
    confidence = Column(Float, nullable=False)  # 0 to 1
    reasoning = Column(Text)
    risk_score = Column(Float)  # 0 to 1
    expected_return = Column(Float)
    time_horizon = Column(String(20))  # short, medium, long
    factors = Column(JSON, default={})  # technical, sentiment, fundamental factors
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime)

class Portfolio(Base):
    """Portfolio tracking model"""
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    exchange = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    average_price = Column(Float, nullable=False)
    current_price = Column(Float)
    current_value = Column(Float)
    pnl = Column(Float, default=0.0)
    pnl_percentage = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class PerformanceLog(Base):
    """Performance tracking model"""
    __tablename__ = "performance_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    period = Column(String(20), nullable=False)  # daily, weekly, monthly
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    total_fees = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    metrics = Column(JSON, default={})
    created_at = Column(DateTime, default=func.now())

class SystemLog(Base):
    """System logging model"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(10), nullable=False)  # info, warning, error, critical
    component = Column(String(50), nullable=False)  # trading_engine, telegram_bot, ai_engine
    message = Column(Text, nullable=False)
    metadata = Column(JSON, default={})
    timestamp = Column(DateTime, default=func.now())

# Database utility functions
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def drop_db():
    """Drop all database tables (use with caution)"""
    Base.metadata.drop_all(bind=engine)

# Create tables on import
init_db()
