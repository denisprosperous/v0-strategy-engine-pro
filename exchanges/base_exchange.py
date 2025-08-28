import abc
import pandas as pd
from typing import Optional, Dict, List
from dataclasses import dataclass

@dataclass
class Order:
    """Data class representing a trading order"""
    symbol: str
    order_type: str  # 'market', 'limit', 'stop_loss', 'take_profit'
    side: str  # 'buy' or 'sell'
    amount: float
    price: Optional[float] = None
    order_id: Optional[str] = None
    status: Optional[str] = None  # 'open', 'filled', 'canceled', 'rejected'
    timestamp: Optional[int] = None

class BaseExchange(abc.ABC):
    """Abstract base class for all exchange integrations"""
    
    def __init__(self, api_key: str, secret_key: str, passphrase: Optional[str] = None):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.exchange = None  # Will be set in concrete implementations
    
    @abc.abstractmethod
    def get_price(self, symbol: str) -> float:
        """Get the latest price for a trading pair"""
        pass
    
    @abc.abstractmethod
    def get_historical_data(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """Get historical OHLCV data"""
        pass
    
    @abc.abstractmethod
    def place_order(self, order: Order) -> Dict:
        """Place a new order"""
        pass
    
    @abc.abstractmethod
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order"""
        pass
    
    @abc.abstractmethod
    def get_balance(self, asset: str) -> float:
        """Get balance for a specific asset"""
        pass
    
    @abc.abstractmethod
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders"""
        pass
    
    @abc.abstractmethod
    def get_order_status(self, order_id: str, symbol: str) -> Order:
        """Get status of a specific order"""
        pass
    
    # New advanced methods
    @abc.abstractmethod
    def get_funding_rate(self, symbol: str) -> float:
        """Get current funding rate (for perpetual contracts)"""
        pass
    
    @abc.abstractmethod
    def get_liquidation_price(self, symbol: str, side: str, amount: float) -> float:
        """Calculate liquidation price for a position"""
        pass
    
    @abc.abstractmethod
    def get_order_book(self, symbol: str, depth: int = 10) -> Dict:
        """Get order book depth"""
        pass
    
    @abc.abstractmethod
    def get_leverage(self, symbol: str) -> float:
        """Get current leverage for a symbol"""
        pass
    
    @abc.abstractmethod
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for a symbol"""
        pass
    
    # Utility methods
    def format_symbol(self, symbol: str) -> str:
        """Format symbol according to exchange requirements"""
        return symbol.replace('/', '')
    
    def parse_symbol(self, symbol: str) -> str:
        """Parse exchange-specific symbol to standard format"""
        return symbol
    
    def get_exchange_name(self) -> str:
        """Get exchange name"""
        return self.__class__.__name__.replace('API', '').lower()
