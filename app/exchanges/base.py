from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

class ExchangeInterface(ABC):
    """Base interface for all exchange implementations"""
    
    def __init__(self, api_key: str, secret_key: str, passphrase: str = None, testnet: bool = False):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.testnet = testnet
        self.is_connected = False
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the exchange"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the exchange"""
        pass
    
    @abstractmethod
    async def get_balance(self, currency: str = None) -> Dict[str, float]:
        """Get account balance"""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get current ticker information"""
        pass
    
    @abstractmethod
    async def get_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[Dict[str, Any]]:
        """Get OHLCV data"""
        pass
    
    @abstractmethod
    async def place_order(self, symbol: str, side: str, order_type: str, 
                         quantity: float, price: float = None, 
                         stop_loss: float = None, take_profit: float = None) -> Dict[str, Any]:
        """Place a new order"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order"""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Get order status"""
        pass
    
    @abstractmethod
    async def get_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get open orders"""
        pass
    
    @abstractmethod
    async def get_trade_history(self, symbol: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get trade history"""
        pass
    
    @abstractmethod
    async def get_markets(self) -> List[Dict[str, Any]]:
        """Get available markets"""
        pass
    
    def validate_symbol(self, symbol: str) -> bool:
        """Validate symbol format"""
        if not symbol or '/' not in symbol:
            return False
        return True
    
    def validate_quantity(self, quantity: float) -> bool:
        """Validate quantity"""
        return quantity > 0
    
    def validate_price(self, price: float) -> bool:
        """Validate price"""
        return price > 0
    
    async def health_check(self) -> bool:
        """Check if exchange is healthy"""
        try:
            await self.get_markets()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

class ExchangeError(Exception):
    """Base exception for exchange errors"""
    pass

class OrderError(ExchangeError):
    """Exception for order-related errors"""
    pass

class ConnectionError(ExchangeError):
    """Exception for connection errors"""
    pass

class RateLimitError(ExchangeError):
    """Exception for rate limit errors"""
    pass
