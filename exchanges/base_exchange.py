"""Base Exchange Module - Unified Interface with LLM Integration

Provides abstract base class for all exchange integrations with:
- Unified API across multiple exchanges
- Real-time data streaming support
- LLM integration hooks for AI analysis
- Advanced order types and risk management
- WebSocket support for real-time updates
- Rate limiting and retry logic
"""

import abc
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any, Callable, Tuple
from abc import ABC, abstractmethod
import pandas as pd
import aiohttp
from functools import wraps
from collections import deque


class OrderType(Enum):
    """Supported order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"
    ICEBERG = "iceberg"


class Side(Enum):
    """Trade side"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order status tracking"""
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class Order:
    """Data class representing a trading order"""
    symbol: str
    order_type: OrderType
    side: Side
    amount: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    timestamp: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    filled_amount: float = 0.0
    filled_price: Optional[float] = None
    commission: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert order to dictionary"""
        return {
            'symbol': self.symbol,
            'type': self.order_type.value,
            'side': self.side.value,
            'amount': self.amount,
            'price': self.price,
            'stop_price': self.stop_price,
            'order_id': self.order_id,
            'status': self.status.value,
            'filled': self.filled_amount,
            'filled_price': self.filled_price,
            'commission': self.commission
        }


@dataclass
class Ticker:
    """Real-time ticker data"""
    symbol: str
    bid: float
    ask: float
    last: float
    volume: float
    timestamp: float
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    change_24h: Optional[float] = None
    change_pct_24h: Optional[float] = None


@dataclass
class OHLCV:
    """OHLCV candlestick data"""
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float


class RateLimiter:
    """Rate limiting utility with exponential backoff"""
    
    def __init__(self, calls_per_second: int = 10):
        self.calls_per_second = calls_per_second
        self.timestamps = deque(maxlen=calls_per_second)
        self.retry_attempts = 0
        self.max_retries = 3
        self.base_wait = 0.1
    
    async def wait(self):
        """Rate limit enforcement"""
        if len(self.timestamps) < self.calls_per_second:
            return
        
        oldest = self.timestamps[0]
        wait_time = 1.0 - (datetime.utcnow().timestamp() - oldest)
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        self.timestamps.append(datetime.utcnow().timestamp())
    
    async def execute_with_retry(self, coro):
        """Execute coroutine with retry logic"""
        for attempt in range(self.max_retries):
            try:
                await self.wait()
                return await coro
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                wait_time = self.base_wait * (2 ** attempt)
                logging.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)


class BaseExchange(ABC):
    """Abstract base class for all exchange integrations
    
    Provides unified interface with LLM integration support for:
    - Multi-asset trading (crypto, stocks, forex)
    - Real-time data streaming
    - Advanced order types
    - Risk management
    - AI-powered analysis
    """
    
    def __init__(self, api_key: str, secret_key: str, 
                 passphrase: Optional[str] = None,
                 sandbox: bool = False,
                 calls_per_second: int = 10):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.sandbox = sandbox
        self.rate_limiter = RateLimiter(calls_per_second)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # LLM integration hooks
        self.llm_callbacks: Dict[str, List[Callable]] = {
            'on_signal': [],
            'on_order': [],
            'on_trade': [],
            'on_market_data': [],
            'on_risk_alert': []
        }
        
        # Real-time data
        self.tickers: Dict[str, Ticker] = {}
        self.order_book_cache: Dict[str, Dict] = {}
        self.websocket: Optional[aiohttp.ClientSession] = None
    
    # ==================== Abstract Methods ====================
    
    @abstractmethod
    async def get_price(self, symbol: str) -> float:
        """Get current market price for a symbol"""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """Get real-time ticker data"""
        pass
    
    @abstractmethod
    async def get_historical_data(self, symbol: str, timeframe: str, 
                                 limit: int = 100) -> pd.DataFrame:
        """Get historical OHLCV data for analysis"""
        pass
    
    @abstractmethod
    async def place_order(self, order: Order) -> Dict[str, Any]:
        """Place a new order on the exchange"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order"""
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str, symbol: str) -> Order:
        """Get order status and details"""
        pass
    
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders, optionally filtered by symbol"""
        pass
    
    @abstractmethod
    async def get_balance(self, asset: Optional[str] = None) -> Dict[str, float]:
        """Get account balance for assets"""
        pass
    
    @abstractmethod
    async def get_order_book(self, symbol: str, depth: int = 20) -> Dict[str, Any]:
        """Get order book data for market analysis"""
        pass
    
    # ==================== Leverage & Margin Methods ====================
    
    @abstractmethod
    async def get_leverage(self, symbol: str) -> float:
        """Get current leverage for a symbol (perpetuals)"""
        pass
    
    @abstractmethod
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for trading (perpetuals)"""
        pass
    
    @abstractmethod
    async def get_funding_rate(self, symbol: str) -> float:
        """Get current funding rate (perpetuals)"""
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Dict[str, Any]:
        """Get current position details"""
        pass
    
    # ==================== Real-time Streaming Methods ====================
    
    @abstractmethod
    async def subscribe_ticker(self, symbol: str, callback: Callable):
        """Subscribe to real-time ticker updates"""
        pass
    
    @abstractmethod
    async def subscribe_trades(self, symbol: str, callback: Callable):
        """Subscribe to real-time trade feed"""
        pass
    
    @abstractmethod
    async def subscribe_order_book(self, symbol: str, callback: Callable):
        """Subscribe to order book updates"""
        pass
    
    # ==================== LLM Integration Methods ====================
    
    def register_llm_callback(self, event: str, callback: Callable):
        """Register LLM callback for specific event
        
        Events:
        - on_signal: AI signal generated
        - on_order: Order placed/canceled
        - on_trade: Trade execution
        - on_market_data: Real-time market data
        - on_risk_alert: Risk management alert
        """
        if event in self.llm_callbacks:
            self.llm_callbacks[event].append(callback)
    
    async def emit_llm_event(self, event: str, data: Dict[str, Any]):
        """Emit LLM integration event for AI analysis"""
        if event in self.llm_callbacks:
            tasks = [callback(data) for callback in self.llm_callbacks[event]]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    # ==================== Utility Methods ====================
    
    def format_symbol(self, base: str, quote: str) -> str:
        """Format symbol according to exchange (e.g., BTC/USDT or BTCUSDT)"""
        return f"{base}/{quote}"
    
    def parse_symbol(self, symbol: str) -> Tuple[str, str]:
        """Parse symbol into base and quote currencies"""
        if '/' in symbol:
            return symbol.split('/')
        # Handle formats like BTCUSDT
        if symbol.endswith('USDT'):
            return symbol[:-4], 'USDT'
        if symbol.endswith('USDC'):
            return symbol[:-4], 'USDC'
        if symbol.endswith('USD'):
            return symbol[:-3], 'USD'
        return symbol, 'USD'
    
    def get_exchange_name(self) -> str:
        """Get exchange identifier"""
        return self.__class__.__name__.replace('API', '').lower()
    
    def validate_symbol(self, symbol: str) -> bool:
        """Validate symbol format"""
        if not symbol or len(symbol) < 3:
            return False
        return True
    
    async def close(self):
        """Clean up resources"""
        if self.websocket:
            await self.websocket.close()
    
    def __repr__(self) -> str:
        return f"<{self.get_exchange_name()} Sandbox={self.sandbox}>"
