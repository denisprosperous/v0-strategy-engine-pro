import ccxt.async_support as ccxt
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

from app.exchanges.base import ExchangeInterface, ExchangeError, OrderError, ConnectionError

logger = logging.getLogger(__name__)

class KrakenExchange(ExchangeInterface):
    """Kraken exchange implementation"""
    
    def __init__(self, api_key: str, secret_key: str, passphrase: str = None, testnet: bool = False):
        super().__init__(api_key, secret_key, passphrase, testnet)
        
        # Initialize CCXT Kraken exchange
        self.exchange = ccxt.kraken({
            'apiKey': api_key,
            'secret': secret_key,
            'sandbox': testnet,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # or 'future' for futures trading
            }
        })
        
        self.exchange_name = "kraken"
        
    async def connect(self) -> bool:
        """Connect to Kraken exchange"""
        try:
            await self.exchange.load_markets()
            self.is_connected = True
            logger.info("Successfully connected to Kraken exchange")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Kraken: {e}")
            self.is_connected = False
            raise ConnectionError(f"Failed to connect to Kraken: {e}")
    
    async def disconnect(self) -> bool:
        """Disconnect from Kraken exchange"""
        try:
            await self.exchange.close()
            self.is_connected = False
            logger.info("Disconnected from Kraken exchange")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from Kraken: {e}")
            return False
    
    async def get_balance(self, currency: str = None) -> Dict[str, float]:
        """Get account balance"""
        try:
            balance = await self.exchange.fetch_balance()
            
            if currency:
                return {currency: balance.get(currency, {}).get('free', 0.0)}
            
            # Return all balances with free amount
            return {curr: data.get('free', 0.0) for curr, data in balance.items() if data.get('free', 0.0) > 0}
            
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise ExchangeError(f"Failed to fetch balance: {e}")
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get current ticker information"""
        try:
            if not self.validate_symbol(symbol):
                raise ValueError(f"Invalid symbol format: {symbol}")
            
            ticker = await self.exchange.fetch_ticker(symbol)
            
            return {
                'symbol': ticker['symbol'],
                'last': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'high': ticker['high'],
                'low': ticker['low'],
                'volume': ticker['baseVolume'],
                'timestamp': ticker['timestamp'],
                'datetime': ticker['datetime']
            }
            
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            raise ExchangeError(f"Failed to fetch ticker: {e}")
    
    async def get_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[Dict[str, Any]]:
        """Get OHLCV data"""
        try:
            if not self.validate_symbol(symbol):
                raise ValueError(f"Invalid symbol format: {symbol}")
            
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            return [
                {
                    'timestamp': candle[0],
                    'datetime': datetime.fromtimestamp(candle[0] / 1000).isoformat(),
                    'open': candle[1],
                    'high': candle[2],
                    'low': candle[3],
                    'close': candle[4],
                    'volume': candle[5]
                }
                for candle in ohlcv
            ]
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            raise ExchangeError(f"Failed to fetch OHLCV: {e}")
    
    async def place_order(self, symbol: str, side: str, order_type: str, 
                         quantity: float, price: float = None, 
                         stop_loss: float = None, take_profit: float = None) -> Dict[str, Any]:
        """Place a new order"""
        try:
            if not self.validate_symbol(symbol):
                raise ValueError(f"Invalid symbol format: {symbol}")
            
            if not self.validate_quantity(quantity):
                raise ValueError(f"Invalid quantity: {quantity}")
            
            # Prepare order parameters
            order_params = {
                'symbol': symbol,
                'type': order_type,
                'side': side,
                'amount': quantity,
            }
            
            if price and order_type in ['limit', 'stop']:
                order_params['price'] = price
            
            # Kraken specific parameters
            if stop_loss:
                order_params['stopLoss'] = stop_loss
            
            if take_profit:
                order_params['takeProfit'] = take_profit
            
            # Place the order
            order = await self.exchange.create_order(**order_params)
            
            logger.info(f"Order placed successfully: {order['id']} - {symbol} {side} {quantity}")
            
            return {
                'id': order['id'],
                'symbol': order['symbol'],
                'side': order['side'],
                'type': order['type'],
                'amount': order['amount'],
                'price': order.get('price'),
                'status': order['status'],
                'timestamp': order['timestamp'],
                'datetime': order['datetime']
            }
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            raise OrderError(f"Failed to place order: {e}")
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order"""
        try:
            if not self.validate_symbol(symbol):
                raise ValueError(f"Invalid symbol format: {symbol}")
            
            result = await self.exchange.cancel_order(order_id, symbol)
            
            if result:
                logger.info(f"Order cancelled successfully: {order_id}")
                return True
            else:
                logger.warning(f"Failed to cancel order: {order_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            raise OrderError(f"Failed to cancel order: {e}")
    
    async def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Get order status"""
        try:
            if not self.validate_symbol(symbol):
                raise ValueError(f"Invalid symbol format: {symbol}")
            
            order = await self.exchange.fetch_order(order_id, symbol)
            
            return {
                'id': order['id'],
                'symbol': order['symbol'],
                'side': order['side'],
                'type': order['type'],
                'amount': order['amount'],
                'filled': order['filled'],
                'remaining': order['remaining'],
                'price': order.get('price'),
                'cost': order.get('cost'),
                'status': order['status'],
                'timestamp': order['timestamp'],
                'datetime': order['datetime']
            }
            
        except Exception as e:
            logger.error(f"Error fetching order status for {order_id}: {e}")
            raise ExchangeError(f"Failed to fetch order status: {e}")
    
    async def get_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get open orders"""
        try:
            orders = await self.exchange.fetch_open_orders(symbol)
            
            return [
                {
                    'id': order['id'],
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'type': order['type'],
                    'amount': order['amount'],
                    'filled': order['filled'],
                    'remaining': order['remaining'],
                    'price': order.get('price'),
                    'status': order['status'],
                    'timestamp': order['timestamp'],
                    'datetime': order['datetime']
                }
                for order in orders
            ]
            
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            raise ExchangeError(f"Failed to fetch open orders: {e}")
    
    async def get_trade_history(self, symbol: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get trade history"""
        try:
            trades = await self.exchange.fetch_my_trades(symbol, limit=limit)
            
            return [
                {
                    'id': trade['id'],
                    'symbol': trade['symbol'],
                    'side': trade['side'],
                    'amount': trade['amount'],
                    'price': trade['price'],
                    'cost': trade['cost'],
                    'fee': trade.get('fee'),
                    'timestamp': trade['timestamp'],
                    'datetime': trade['datetime']
                }
                for trade in trades
            ]
            
        except Exception as e:
            logger.error(f"Error fetching trade history: {e}")
            raise ExchangeError(f"Failed to fetch trade history: {e}")
    
    async def get_markets(self) -> List[Dict[str, Any]]:
        """Get available markets"""
        try:
            markets = self.exchange.markets
            
            return [
                {
                    'symbol': market['symbol'],
                    'base': market['base'],
                    'quote': market['quote'],
                    'type': market['type'],
                    'spot': market.get('spot', False),
                    'future': market.get('future', False),
                    'active': market.get('active', True),
                    'precision': market.get('precision', {}),
                    'limits': market.get('limits', {})
                }
                for market in markets.values()
                if market.get('active', True)
            ]
            
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            raise ExchangeError(f"Failed to fetch markets: {e}")
    
    async def get_trading_pairs(self) -> List[str]:
        """Get list of trading pairs"""
        try:
            markets = await self.get_markets()
            return [market['symbol'] for market in markets if market['spot']]
        except Exception as e:
            logger.error(f"Error fetching trading pairs: {e}")
            return []
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """Get order book for a symbol"""
        try:
            if not self.validate_symbol(symbol):
                raise ValueError(f"Invalid symbol format: {symbol}")
            
            order_book = await self.exchange.fetch_order_book(symbol, limit)
            
            return {
                'symbol': symbol,
                'bids': order_book['bids'],
                'asks': order_book['asks'],
                'timestamp': order_book['timestamp'],
                'datetime': order_book['datetime']
            }
            
        except Exception as e:
            logger.error(f"Error fetching order book for {symbol}: {e}")
            raise ExchangeError(f"Failed to fetch order book: {e}")
    
    async def get_24h_stats(self, symbol: str) -> Dict[str, Any]:
        """Get 24-hour statistics for a symbol"""
        try:
            if not self.validate_symbol(symbol):
                raise ValueError(f"Invalid symbol format: {symbol}")
            
            ticker = await self.get_ticker(symbol)
            
            return {
                'symbol': symbol,
                'last_price': ticker['last'],
                'high_24h': ticker['high'],
                'low_24h': ticker['low'],
                'volume_24h': ticker['volume'],
                'price_change_24h': ticker.get('last', 0) - ticker.get('open', 0),
                'price_change_percent_24h': ((ticker.get('last', 0) - ticker.get('open', 0)) / ticker.get('open', 1)) * 100 if ticker.get('open') else 0
            }
            
        except Exception as e:
            logger.error(f"Error fetching 24h stats for {symbol}: {e}")
            raise ExchangeError(f"Failed to fetch 24h stats: {e}")
    
    async def get_ohlcv_with_indicators(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> Dict[str, Any]:
        """Get OHLCV data with technical indicators"""
        try:
            ohlcv_data = await self.get_ohlcv(symbol, timeframe, limit)
            
            if not ohlcv_data:
                return {}
            
            # Calculate basic indicators
            closes = [candle['close'] for candle in ohlcv_data]
            highs = [candle['high'] for candle in ohlcv_data]
            lows = [candle['low'] for candle in ohlcv_data]
            volumes = [candle['volume'] for candle in ohlcv_data]
            
            # Simple Moving Averages
            sma_20 = sum(closes[-20:]) / min(20, len(closes)) if len(closes) >= 20 else None
            sma_50 = sum(closes[-50:]) / min(50, len(closes)) if len(closes) >= 50 else None
            
            # RSI calculation
            rsi = self._calculate_rsi(closes, period=14) if len(closes) >= 14 else None
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(closes, period=20) if len(closes) >= 20 else (None, None, None)
            
            return {
                'ohlcv': ohlcv_data,
                'indicators': {
                    'sma_20': sma_20,
                    'sma_50': sma_50,
                    'rsi': rsi,
                    'bollinger_bands': {
                        'upper': bb_upper,
                        'middle': bb_middle,
                        'lower': bb_lower
                    },
                    'current_price': closes[-1] if closes else None,
                    'price_change_24h': (closes[-1] - closes[-24]) / closes[-24] * 100 if len(closes) >= 24 else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating indicators for {symbol}: {e}")
            return {}
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index)"""
        if len(prices) < period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2) -> tuple:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return None, None, None
        
        recent_prices = prices[-period:]
        sma = sum(recent_prices) / period
        
        # Calculate standard deviation
        variance = sum((price - sma) ** 2 for price in recent_prices) / period
        std = variance ** 0.5
        
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        return upper_band, sma, lower_band
