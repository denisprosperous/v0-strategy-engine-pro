#!/usr/bin/env python3
"""
Binance Exchange Integration

Complete implementation of Binance API wrapper with:
- Spot trading
- Futures trading
- Market data streaming
- Order management
- Account management

Author: v0-strategy-engine-pro
Version: 1.0
"""

import ccxt
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)


@dataclass
class OrderResult:
    """Order execution result."""
    success: bool
    order_id: Optional[str] = None
    symbol: str = ""
    side: str = ""
    type: str = ""
    price: float = 0.0
    amount: float = 0.0
    filled: float = 0.0
    status: str = ""
    error: Optional[str] = None
    timestamp: datetime = None


@dataclass
class Balance:
    """Account balance."""
    asset: str
    free: float
    locked: float
    total: float


class BinanceExchange:
    """
    Binance exchange integration.
    
    Supports:
    - Spot trading
    - Futures trading (USDT-M)
    - Real-time market data
    - Order management
    - Position management
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = False,
        futures: bool = False
    ):
        """
        Initialize Binance exchange.
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Use testnet for paper trading
            futures: Enable futures trading
        """
        self.api_key = api_key or os.getenv('BINANCE_API_KEY')
        self.api_secret = api_secret or os.getenv('BINANCE_SECRET_KEY')
        self.testnet = testnet
        self.futures = futures
        
        # Initialize CCXT exchange
        if futures:
            self.exchange = ccxt.binanceusdm({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',
                    'adjustForTimeDifference': True
                }
            })
        else:
            self.exchange = ccxt.binance({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'enableRateLimit': True,
                'options': {
                    'adjustForTimeDifference': True
                }
            })
        
        if testnet:
            self.exchange.set_sandbox_mode(True)
        
        self.is_connected = False
        
        logger.info(
            f"Binance exchange initialized "
            f"(testnet={testnet}, futures={futures})"
        )
    
    async def connect(self) -> bool:
        """
        Connect to Binance and verify credentials.
        
        Returns:
            Success status
        """
        try:
            # Test connection by fetching balance
            await self.exchange.fetch_balance()
            self.is_connected = True
            logger.info("✅ Connected to Binance successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Binance: {e}")
            self.is_connected = False
            return False
    
    async def get_balance(self, asset: str = "USDT") -> Optional[Balance]:
        """
        Get account balance for specific asset.
        
        Args:
            asset: Asset symbol (e.g., 'USDT', 'BTC')
        
        Returns:
            Balance object or None
        """
        try:
            balance_data = await self.exchange.fetch_balance()
            
            if asset in balance_data['total']:
                return Balance(
                    asset=asset,
                    free=float(balance_data['free'].get(asset, 0)),
                    locked=float(balance_data['used'].get(asset, 0)),
                    total=float(balance_data['total'].get(asset, 0))
                )
            
            return Balance(asset=asset, free=0.0, locked=0.0, total=0.0)
            
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return None
    
    async def get_all_balances(self) -> List[Balance]:
        """
        Get all non-zero balances.
        
        Returns:
            List of Balance objects
        """
        try:
            balance_data = await self.exchange.fetch_balance()
            balances = []
            
            for asset, total in balance_data['total'].items():
                if float(total) > 0:
                    balances.append(Balance(
                        asset=asset,
                        free=float(balance_data['free'].get(asset, 0)),
                        locked=float(balance_data['used'].get(asset, 0)),
                        total=float(total)
                    ))
            
            return balances
            
        except Exception as e:
            logger.error(f"Error fetching balances: {e}")
            return []
    
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Get current ticker data for symbol.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
        
        Returns:
            Ticker data dictionary
        """
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'bid': float(ticker['bid']),
                'ask': float(ticker['ask']),
                'last': float(ticker['last']),
                'volume': float(ticker['quoteVolume']),
                'change': float(ticker['percentage']),
                'timestamp': ticker['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None
    
    async def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float
    ) -> OrderResult:
        """
        Create market order.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            side: 'buy' or 'sell'
            amount: Order amount in base currency
        
        Returns:
            OrderResult object
        """
        try:
            logger.info(f"Creating market order: {side} {amount} {symbol}")
            
            order = await self.exchange.create_market_order(
                symbol=symbol,
                side=side,
                amount=amount
            )
            
            return OrderResult(
                success=True,
                order_id=order['id'],
                symbol=symbol,
                side=side,
                type='market',
                price=float(order.get('average', 0)),
                amount=amount,
                filled=float(order.get('filled', 0)),
                status=order['status'],
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error creating market order: {e}")
            return OrderResult(
                success=False,
                symbol=symbol,
                side=side,
                type='market',
                error=str(e),
                timestamp=datetime.utcnow()
            )
    
    async def create_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float
    ) -> OrderResult:
        """
        Create limit order.
        
        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Order amount
            price: Limit price
        
        Returns:
            OrderResult object
        """
        try:
            logger.info(
                f"Creating limit order: {side} {amount} {symbol} @ {price}"
            )
            
            order = await self.exchange.create_limit_order(
                symbol=symbol,
                side=side,
                amount=amount,
                price=price
            )
            
            return OrderResult(
                success=True,
                order_id=order['id'],
                symbol=symbol,
                side=side,
                type='limit',
                price=price,
                amount=amount,
                filled=float(order.get('filled', 0)),
                status=order['status'],
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error creating limit order: {e}")
            return OrderResult(
                success=False,
                symbol=symbol,
                side=side,
                type='limit',
                price=price,
                error=str(e),
                timestamp=datetime.utcnow()
            )
    
    async def create_stop_loss_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        stop_price: float,
        limit_price: Optional[float] = None
    ) -> OrderResult:
        """
        Create stop loss order.
        
        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Order amount
            stop_price: Stop trigger price
            limit_price: Optional limit price (stop-limit)
        
        Returns:
            OrderResult object
        """
        try:
            if limit_price:
                # Stop-limit order
                order = await self.exchange.create_order(
                    symbol=symbol,
                    type='STOP_LOSS_LIMIT',
                    side=side,
                    amount=amount,
                    price=limit_price,
                    params={'stopPrice': stop_price}
                )
            else:
                # Stop-market order
                order = await self.exchange.create_order(
                    symbol=symbol,
                    type='STOP_LOSS',
                    side=side,
                    amount=amount,
                    params={'stopPrice': stop_price}
                )
            
            return OrderResult(
                success=True,
                order_id=order['id'],
                symbol=symbol,
                side=side,
                type='stop_loss',
                price=stop_price,
                amount=amount,
                status=order['status'],
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error creating stop loss order: {e}")
            return OrderResult(
                success=False,
                symbol=symbol,
                side=side,
                type='stop_loss',
                error=str(e),
                timestamp=datetime.utcnow()
            )
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel open order.
        
        Args:
            order_id: Order ID
            symbol: Trading pair
        
        Returns:
            Success status
        """
        try:
            await self.exchange.cancel_order(order_id, symbol)
            logger.info(f"✅ Cancelled order {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def get_order_status(
        self,
        order_id: str,
        symbol: str
    ) -> Optional[Dict]:
        """
        Get order status.
        
        Args:
            order_id: Order ID
            symbol: Trading pair
        
        Returns:
            Order status dictionary
        """
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            
            return {
                'id': order['id'],
                'symbol': order['symbol'],
                'type': order['type'],
                'side': order['side'],
                'price': float(order.get('price', 0)),
                'amount': float(order['amount']),
                'filled': float(order['filled']),
                'remaining': float(order['remaining']),
                'status': order['status'],
                'timestamp': order['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error fetching order status: {e}")
            return None
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get all open orders.
        
        Args:
            symbol: Optional symbol filter
        
        Returns:
            List of open orders
        """
        try:
            orders = await self.exchange.fetch_open_orders(symbol)
            
            return [{
                'id': order['id'],
                'symbol': order['symbol'],
                'type': order['type'],
                'side': order['side'],
                'price': float(order.get('price', 0)),
                'amount': float(order['amount']),
                'filled': float(order['filled']),
                'status': order['status'],
                'timestamp': order['timestamp']
            } for order in orders]
            
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            return []
    
    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: int = 100
    ) -> Optional[List]:
        """
        Get OHLCV candlestick data.
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
            limit: Number of candles
        
        Returns:
            List of [timestamp, open, high, low, close, volume]
        """
        try:
            ohlcv = await self.exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                limit=limit
            )
            
            return ohlcv
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV: {e}")
            return None
    
    async def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get current position (futures only).
        
        Args:
            symbol: Trading pair
        
        Returns:
            Position dictionary
        """
        if not self.futures:
            logger.warning("Positions only available in futures mode")
            return None
        
        try:
            positions = await self.exchange.fetch_positions([symbol])
            
            if positions:
                pos = positions[0]
                return {
                    'symbol': pos['symbol'],
                    'side': pos['side'],
                    'size': float(pos['contracts']),
                    'entry_price': float(pos['entryPrice']),
                    'mark_price': float(pos['markPrice']),
                    'unrealized_pnl': float(pos['unrealizedPnl']),
                    'leverage': float(pos['leverage']),
                    'liquidation_price': float(pos.get('liquidationPrice', 0))
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching position: {e}")
            return None
    
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Set leverage for futures trading.
        
        Args:
            symbol: Trading pair
            leverage: Leverage multiplier (1-125)
        
        Returns:
            Success status
        """
        if not self.futures:
            logger.warning("Leverage only available in futures mode")
            return False
        
        try:
            await self.exchange.set_leverage(leverage, symbol)
            logger.info(f"✅ Set leverage to {leverage}x for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting leverage: {e}")
            return False
    
    async def close(self):
        """Close exchange connection."""
        if self.exchange:
            await self.exchange.close()
            self.is_connected = False
            logger.info("Binance connection closed")


# ========== USAGE EXAMPLE ==========

async def example_usage():
    """Example of using BinanceExchange."""
    
    # Initialize exchange
    exchange = BinanceExchange(testnet=True)  # Use testnet for safety
    
    # Connect
    if not await exchange.connect():
        print("Failed to connect")
        return
    
    # Get balance
    balance = await exchange.get_balance("USDT")
    print(f"USDT Balance: {balance.total}")
    
    # Get ticker
    ticker = await exchange.get_ticker("BTC/USDT")
    print(f"BTC/USDT: ${ticker['last']}")
    
    # Create market buy order
    order = await exchange.create_market_order(
        symbol="BTC/USDT",
        side="buy",
        amount=0.001
    )
    
    if order.success:
        print(f"✅ Order placed: {order.order_id}")
        
        # Set stop loss
        sl_order = await exchange.create_stop_loss_order(
            symbol="BTC/USDT",
            side="sell",
            amount=0.001,
            stop_price=ticker['last'] * 0.98  # 2% stop loss
        )
    
    # Close connection
    await exchange.close()


if __name__ == "__main__":
    asyncio.run(example_usage())
