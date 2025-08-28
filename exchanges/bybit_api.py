import ccxt
import pandas as pd
from typing import Optional, Dict, List
from .base_exchange import BaseExchange, Order
from datetime import datetime

class BybitAPI(BaseExchange):
    """Concrete implementation for Bybit exchange"""
    
    def __init__(self, api_key: str, secret_key: str, passphrase: Optional[str] = None):
        super().__init__(api_key, secret_key, passphrase)
        self.exchange = ccxt.bybit({
            'apiKey': self.api_key,
            'secret': self.secret_key,
            'options': {
                'defaultType': 'spot',  # Can be 'spot', 'swap', 'future'
                'adjustForTimeDifference': True,
            },
            'enableRateLimit': True
        })
        self.exchange.load_markets()

    def get_price(self, symbol: str) -> float:
        ticker = self.exchange.fetch_ticker(symbol)
        return float(ticker['last'])

    def get_historical_data(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

    def place_order(self, order: Order) -> Dict:
        params = {}
        if order.order_type == 'limit':
            result = self.exchange.create_order(
                symbol=order.symbol,
                type=order.order_type,
                side=order.side,
                amount=order.amount,
                price=order.price,
                params=params
            )
        else:
            result = self.exchange.create_order(
                symbol=order.symbol,
                type=order.order_type,
                side=order.side,
                amount=order.amount,
                params=params
            )
        
        return {
            'order_id': result['id'],
            'symbol': result['symbol'],
            'status': result['status'],
            'filled': result['filled'],
            'remaining': result['remaining'],
            'fee': result['fee']
        }

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        try:
            result = self.exchange.cancel_order(order_id, symbol)
            return result['status'] == 'canceled'
        except Exception as e:
            print(f"Error canceling order: {e}")
            return False

    def get_balance(self, asset: str) -> float:
        balance = self.exchange.fetch_balance()
        return float(balance['free'].get(asset.upper(), 0.0))

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        orders = self.exchange.fetch_open_orders(symbol) if symbol else self.exchange.fetch_open_orders()
        return [
            Order(
                symbol=o['symbol'],
                order_type=o['type'],
                side=o['side'],
                amount=o['amount'],
                price=o['price'],
                order_id=o['id'],
                status=o['status'],
                timestamp=o['timestamp']
            ) for o in orders
        ]

    def get_order_status(self, order_id: str, symbol: str) -> Order:
        order = self.exchange.fetch_order(order_id, symbol)
        return Order(
            symbol=order['symbol'],
            order_type=order['type'],
            side=order['side'],
            amount=order['amount'],
            price=order['price'],
            order_id=order['id'],
            status=order['status'],
            timestamp=order['timestamp']
        )

    # Advanced methods implementation
    def get_funding_rate(self, symbol: str) -> float:
        if 'USDT' in symbol:  # Perpetual contracts
            funding_rate = self.exchange.fetch_funding_rate(symbol)
            return float(funding_rate['fundingRate'])
        return 0.0

    def get_liquidation_price(self, symbol: str, side: str, amount: float) -> float:
        # Bybit provides liquidation price directly
        positions = self.exchange.fetch_positions([symbol])
        if positions:
            return float(positions[0]['liquidationPrice'])
        
        # Fallback calculation if position doesn't exist
        ticker = self.exchange.fetch_ticker(symbol)
        last_price = float(ticker['last'])
        return last_price * 0.9 if side == 'long' else last_price * 1.1

    def get_order_book(self, symbol: str, depth: int = 10) -> Dict:
        return self.exchange.fetch_order_book(symbol, limit=depth)

    def get_leverage(self, symbol: str) -> float:
        positions = self.exchange.fetch_positions([symbol])
        return float(positions[0]['leverage']) if positions else 1.0

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        try:
            self.exchange.set_leverage(leverage, symbol)
            return True
        except Exception as e:
            print(f"Error setting leverage: {e}")
            return False

    # Bybit-specific methods
    def get_position_mode(self) -> str:
        """Get position mode (one-way or hedge mode)"""
        return self.exchange.fetch_position_mode()

    def get_position_info(self, symbol: str) -> Dict:
        """Get detailed position information"""
        return self.exchange.fetch_position(symbol)
