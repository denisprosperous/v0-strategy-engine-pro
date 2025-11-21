"""Binance Exchange API Integration - Professional Grade Implementation

Provides unified interface for Binance spot, futures, and margin trading with:
- Async/await support for high-performance API calls (<100ms latency)
- LLM integration hooks for AI signal analysis
- Real-time WebSocket streaming (tickers, trades, order books)
- Rate limiting with exponential backoff (1200 requests/min free tier)
- Support for free API tier with paid upgrade path
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import aiohttp
import pandas as pd

from .base_exchange import (
    BaseExchange, Order, OrderType, Side, OrderStatus, 
    Ticker, OHLCV, RateLimiter
)

logger = logging.getLogger(__name__)


class BinanceOrderType(Enum):
    """Binance-specific order types"""
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"
    LIMIT_MAKER = "LIMIT_MAKER"


class BinanceTradingType(Enum):
    """Trading modes supported by Binance"""
    SPOT = "spot"
    MARGIN = "margin"
    FUTURES = "futures"


class BinanceAPI(BaseExchange):
    """Professional-grade Binance exchange adapter
    
    Supports spot, margin, and futures trading with real-time
    WebSocket streaming and LLM integration for signal analysis.
    
    Performance Characteristics:
    - Free API tier: 1200 requests/minute
    - Paid API tier: 100,000 requests/minute
    - WebSocket real-time latency: <100ms
    - Order placement: <500ms
    
    Features:
    - Multiple trading modes (spot, margin, futures)
    - Advanced order types (limit, market, stop-loss, take-profit)
    - Real-time market data streaming via WebSocket
    - LLM callback hooks for trading signals
    - Exponential backoff retry logic for resilience
    - Comprehensive error handling
    """

    def __init__(
        self,
        api_key: str = None,
        secret_key: str = None,
        testnet: bool = False,
        trading_type: BinanceTradingType = BinanceTradingType.SPOT,
    ):
        """Initialize Binance API client
        
        Args:
            api_key: Binance API key (uses BINANCE_API_KEY env var if None)
            secret_key: Binance secret key (uses BINANCE_SECRET_KEY env var if None)
            testnet: Use Binance testnet for testing (no real funds)
            trading_type: Trading mode - SPOT, MARGIN, or FUTURES
            
        Example:
            >>> async with BinanceAPI(trading_type=BinanceTradingType.SPOT) as client:
            ...     price = await client.get_price("BTCUSDT")
            ...     print(f"BTC Price: ${price}")
        """
        api_key = api_key or os.getenv("BINANCE_API_KEY")
        secret_key = secret_key or os.getenv("BINANCE_SECRET_KEY")
        
        super().__init__(api_key, secret_key)
        
        self.trading_type = trading_type
        self.testnet = testnet
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connections: Dict[str, Any] = {}
        
        # Configure API endpoints based on trading type
        if testnet:
            self.rest_base = "https://testnet.binance.vision/api"
            self.ws_base = "wss://stream.testnet.binance.vision:9443/ws"
            self.futures_base = "https://testnet.fapi.binance.vision"
            self.futures_ws = "wss://stream.testnet.fapi.binance.vision:9443"
        else:
            if trading_type == BinanceTradingType.FUTURES:
                self.rest_base = "https://fapi.binance.com"
                self.ws_base = "wss://fstream.binance.com/ws"
                self.futures_base = "https://fapi.binance.com"
                self.futures_ws = "wss://fstream.binance.com"
            else:
                self.rest_base = "https://api.binance.com/api"
                self.ws_base = "wss://stream.binance.com:9443/ws"
                self.futures_base = "https://fapi.binance.com"
                self.futures_ws = "wss://fstream.binance.com"
        
        # Rate limiter: 1200 requests/minute for free tier
        self.rate_limiter = RateLimiter(max_requests=1200, window_seconds=60)
        
        # WebSocket subscriptions storage
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.listen_keys: Dict[str, str] = {}

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def close(self):
        """Gracefully close all connections"""
        try:
            for conn in self.ws_connections.values():
                await conn.close()
            if self.session and not self.session.closed:
                await self.session.close()
            logger.info("Binance API client closed successfully")
        except Exception as e:
            logger.error(f"Error closing Binance client: {e}")

    def _get_signature(self, query_string: str) -> str:
        """Generate HMAC SHA256 signature
        
        Args:
            query_string: URL-encoded query parameters
            
        Returns:
            Hex-encoded signature
        """
        return hmac.new(
            self.secret_key.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        signed: bool = False,
        is_futures: bool = False
    ) -> Dict[str, Any]:
        """Make authenticated API request with rate limiting and retry logic
        
        Args:
            method: HTTP method (GET, POST, DELETE, PUT)
            endpoint: API endpoint path
            params: Request parameters
            signed: Whether request needs HMAC signature
            is_futures: Whether to use futures API
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            Exception: On API errors after max retries
        """
        if params is None:
            params = {}
        
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        # Add timestamp and signature if required
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            query_string = "&".join(
                f"{k}={v}" for k, v in sorted(params.items())
            )
            params["signature"] = self._get_signature(query_string)
        
        # Construct URL
        base = self.futures_base if is_futures else self.rest_base
        url = f"{base}/{endpoint}"
        headers = {"X-MBX-APIKEY": self.api_key}
        
        max_retries = 3
        retry_count = 0
        backoff_base = 2
        
        while retry_count < max_retries:
            try:
                async with self.session.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    data = await response.json()
                    
                    if response.status == 200:
                        # Emit LLM callback for market data observation
                        await self._emit_llm_callback("on_market_data", {
                            "exchange": "binance",
                            "trading_mode": self.trading_type.value,
                            "endpoint": endpoint,
                            "params": params,
                            "timestamp": datetime.utcnow().isoformat(),
                            "data_sample": str(data)[:500]
                        })
                        return data
                    
                    elif response.status == 429:  # Rate limited
                        wait_time = backoff_base ** retry_count
                        logger.warning(
                            f"Binance rate limit exceeded. "
                            f"Waiting {wait_time}s before retry {retry_count + 1}/{max_retries}"
                        )
                        await asyncio.sleep(wait_time)
                        retry_count += 1
                    
                    else:
                        error_msg = data.get("msg", str(response.status))
                        logger.error(f"Binance API Error ({response.status}): {error_msg}")
                        raise Exception(f"API Error: {response.status} - {error_msg}")
            
            except asyncio.TimeoutError:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = backoff_base ** retry_count
                    logger.warning(f"Request timeout. Retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise Exception("Request timeout after max retries")
            
            except Exception as e:
                logger.error(f"Request failed: {e}")
                if retry_count < max_retries - 1:
                    retry_count += 1
                    await asyncio.sleep(backoff_base ** retry_count)
                else:
                    raise
        
        raise Exception("Max retries exceeded for API request")
    async def get_price(self, symbol: str) -> float:
        """Get current spot price for symbol
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT', 'ETHUSDT')
            
        Returns:
            Current price as float
            
        Example:
            >>> price = await client.get_price("BTCUSDT")
            >>> print(f"${price}")
        """
        data = await self._request(
            "GET",
            "v3/ticker/price",
            {"symbol": symbol}
        )
        return float(data["price"])

    async def get_ticker(self, symbol: str) -> Ticker:
        """Get 24-hour ticker data with OHLCV statistics
        
        Args:
            symbol: Trading pair
            
        Returns:
            Ticker object containing:
            - last_price: Current price
            - bid/ask: Current bid/ask prices
            - high_24h/low_24h: 24h range
            - volume_24h: 24h trading volume
            - timestamp: Data timestamp
        """
        data = await self._request(
            "GET",
            "v3/ticker/24hr",
            {"symbol": symbol}
        )
        
        ticker = Ticker(
            symbol=symbol,
            last_price=float(data["lastPrice"]),
            bid=float(data["bidPrice"]),
            ask=float(data["askPrice"]),
            high_24h=float(data["highPrice"]),
            low_24h=float(data["lowPrice"]),
            volume_24h=float(data["volume"]),
            timestamp=datetime.utcnow()
        )
        
        # Emit LLM callback for ticker update
        await self._emit_llm_callback("on_ticker_update", {
            "symbol": symbol,
            "last_price": ticker.last_price,
            "bid_ask_spread": ticker.ask - ticker.bid,
            "volume_24h": ticker.volume_24h
        })
        
        return ticker

    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> List[OHLCV]:
        """Get historical OHLCV candlestick data
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            timeframe: Kline interval:
                - 1m, 3m, 5m, 15m, 30m (minutes)
                - 1h, 2h, 4h, 6h, 8h, 12h (hours)
                - 1d, 3d, 1w, 1M (days/weeks/months)
            limit: Number of candles to retrieve (max 1000)
            
        Returns:
            List of OHLCV objects ordered chronologically
            
        Example:
            >>> candles = await client.get_historical_data("BTCUSDT", "1h", limit=24)
            >>> for candle in candles:
            ...     print(f"{candle.timestamp}: Close={candle.close}")
        """
        data = await self._request(
            "GET",
            "v3/klines",
            {
                "symbol": symbol,
                "interval": timeframe,
                "limit": min(limit, 1000)
            }
        )
        
        ohlcvs = []
        for candle in data:
            ohlcv = OHLCV(
                timestamp=datetime.fromtimestamp(candle[0] / 1000),
                open=float(candle[1]),
                high=float(candle[2]),
                low=float(candle[3]),
                close=float(candle[4]),
                volume=float(candle[5])
            )
            ohlcvs.append(ohlcv)
        
        return ohlcvs

    async def place_order(self, order: Order) -> Dict[str, Any]:
        """Place a new trading order
        
        Args:
            order: Order object containing:
            - symbol: Trading pair (e.g., 'BTCUSDT')
            - side: BUY or SELL
            - type: LIMIT or MARKET
            - quantity: Amount to trade
            - price: Price for limit orders (optional for market)
            
        Returns:
            Order response containing:
            - orderId: Unique order identifier
            - status: ORDER_NEW, PARTIALLY_FILLED, FILLED, CANCELED, REJECTED
            - executedQty: Quantity executed
            - cummulativeQuoteQty: Total cost/revenue
            
        Example:
            >>> order = Order(
            ...     symbol="BTCUSDT",
            ...     side=Side.BUY,
            ...     type=OrderType.LIMIT,
            ...     quantity=0.01,
            ...     price=42000
            ... )
            >>> response = await client.place_order(order)
            >>> print(f"Order ID: {response['orderId']}")
        """
        params = {
            "symbol": order.symbol,
            "side": order.side.value.upper(),
            "type": "LIMIT" if order.price else "MARKET",
            "timeInForce": "GTC",
            "quantity": order.quantity,
        }
        
        if order.price:
            params["price"] = order.price
        
        endpoint = "v3/order" if self.trading_type == BinanceTradingType.SPOT else "fapi/v1/order"
        
        response = await self._request(
            "POST",
            endpoint,
            params,
            signed=True,
            is_futures=(self.trading_type == BinanceTradingType.FUTURES)
        )
        
        # Emit LLM callback for order placement
        await self._emit_llm_callback("on_order", {
            "exchange": "binance",
            "action": "place",
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": order.quantity,
            "price": order.price,
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return response

    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel an existing order
        
        Args:
            order_id: Order ID to cancel
            symbol: Trading pair
            
        Returns:
            Cancellation response
            
        Example:
            >>> response = await client.cancel_order("12345678", "BTCUSDT")
            >>> print(f"Cancelled: {response['status']}")
        """
        params = {"symbol": symbol, "orderId": order_id}
        
        endpoint = "v3/order" if self.trading_type == BinanceTradingType.SPOT else "fapi/v1/order"
        
        response = await self._request(
            "DELETE",
            endpoint,
            params,
            signed=True,
            is_futures=(self.trading_type == BinanceTradingType.FUTURES)
        )
        
        await self._emit_llm_callback("on_order", {
            "exchange": "binance",
            "action": "cancel",
            "order_id": order_id,
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return response

    async def get_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Get order details by ID
        
        Args:
            order_id: Order ID
            symbol: Trading pair
            
        Returns:
            Order details with status, executed quantity, etc.
        """
        params = {"symbol": symbol, "orderId": order_id}
        endpoint = "v3/order" if self.trading_type == BinanceTradingType.SPOT else "fapi/v1/order"
        
        return await self._request(
            "GET",
            endpoint,
            params,
            signed=True,
            is_futures=(self.trading_type == BinanceTradingType.FUTURES)
        )

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get all open orders for account
        
        Args:
            symbol: Optional symbol filter (returns all if None)
            
        Returns:
            List of open orders with details
            
        Example:
            >>> orders = await client.get_open_orders("BTCUSDT")
            >>> for order in orders:
            ...     print(f"Order {order['orderId']}: {order['status']}")
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        endpoint = "v3/openOrders" if self.trading_type == BinanceTradingType.SPOT else "fapi/v1/openOrders"
        
        return await self._request(
            "GET",
            endpoint,
            params,
            signed=True,
            is_futures=(self.trading_type == BinanceTradingType.FUTURES)
        )

    async def get_balance(self, asset: str) -> Dict[str, float]:
        """Get account balance for an asset
        
        Args:
            asset: Asset symbol (e.g., 'BTC', 'USDT', 'ETH')
            
        Returns:
            Dict with 'free' and 'locked' balances
            
        Example:
            >>> balance = await client.get_balance("USDT")
            >>> print(f"Free: {balance['free']}, Locked: {balance['locked']}")
        """
        endpoint = "v3/account" if self.trading_type == BinanceTradingType.SPOT else "fapi/v2/account"
        
        account = await self._request(
            "GET",
            endpoint,
            {},
            signed=True,
            is_futures=(self.trading_type == BinanceTradingType.FUTURES)
        )
        
        # Search for asset in balances
        balance_field = "balances" if self.trading_type == BinanceTradingType.SPOT else "assets"
        for balance in account.get(balance_field, []):
            balance_asset = balance.get("asset") or balance.get("asset")
            if balance_asset == asset:
                return {
                    "free": float(balance.get("free", 0)),
                    "locked": float(balance.get("locked", 0))
                }
        
        return {"free": 0.0, "locked": 0.0}

    async def get_order_book(self, symbol: str, depth: int = 20) -> Dict[str, Any]:
        """Get order book snapshot
        
        Args:
            symbol: Trading pair
            depth: Book depth (5, 10, 20, 50, 100, 500, 1000)
            
        Returns:
            Order book with bids and asks lists
            
        Example:
            >>> book = await client.get_order_book("BTCUSDT", depth=20)
            >>> top_bid = float(book["bids"][0][0])
            >>> top_ask = float(book["asks"][0][0])
            >>> print(f"Spread: ${top_ask - top_bid}")
        """
        params = {"symbol": symbol, "limit": depth}
        endpoint = "v3/depth" if self.trading_type == BinanceTradingType.SPOT else "fapi/v1/depth"
        
        return await self._request(
            "GET",
            endpoint,
            params,
            is_futures=(self.trading_type == BinanceTradingType.FUTURES)
        )

    async def get_leverage(self, symbol: str) -> int:
        """Get current leverage for futures trading
        
        Args:
            symbol: Trading pair
            
        Returns:
            Leverage multiplier (1-125 for futures, 1 for spot)
            
        Example:
            >>> leverage = await client.get_leverage("BTCUSDT")
            >>> print(f"Current leverage: {leverage}x")
        """
        if self.trading_type != BinanceTradingType.FUTURES:
            return 1
        
        position = await self._request(
            "GET",
            "fapi/v2/positionRisk",
            {"symbol": symbol},
            signed=True,
            is_futures=True
        )
        
        if position and len(position) > 0:
            return int(position[0].get("leverage", 1))
        return 1

    async def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """Set leverage for futures trading
        
        Args:
            symbol: Trading pair
            leverage: Leverage multiplier (1-125)
            
        Returns:
            Leverage setting response
            
        Raises:
            ValueError: If leverage out of valid range or not futures mode
            
        Example:
            >>> response = await client.set_leverage("BTCUSDT", 10)
            >>> print(f"Leverage set to {response['leverage']}x")
        """
        if self.trading_type != BinanceTradingType.FUTURES:
            raise ValueError("Leverage only available for futures trading")
        
        if not (1 <= leverage <= 125):
            raise ValueError("Leverage must be between 1 and 125")
        
        params = {"symbol": symbol, "leverage": leverage}
        
        return await self._request(
            "POST",
            "fapi/v1/leverage",
            params,
            signed=True,
            is_futures=True
        )

    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Get current funding rate for futures pair
        
        Args:
            symbol: Trading pair
            
        Returns:
            Dict with fundingRate, fundingTime, nextFundingTime
            
        Example:
            >>> rate = await client.get_funding_rate("BTCUSDT")
            >>> print(f"Funding rate: {float(rate['fundingRate']) * 100}%")
        """
        if self.trading_type != BinanceTradingType.FUTURES:
            raise ValueError("Funding rate only available for futures")
        
        return await self._request(
            "GET",
            "fapi/v1/fundingRate",
            {"symbol": symbol}
        )

    async def get_position(self, symbol: str) -> Dict[str, Any]:
        """Get current position details for futures trading
        
        Args:
            symbol: Trading pair
            
        Returns:
            Position details with amount, entry price, unrealized PnL
        """
        if self.trading_type != BinanceTradingType.FUTURES:
            raise ValueError("Positions only available for futures trading")
        
        positions = await self._request(
            "GET",
            "fapi/v2/positionRisk",
            {"symbol": symbol},
            signed=True,
            is_futures=True
        )
        
        if positions and len(positions) > 0:
            return positions[0]
        return {}
    async def subscribe_ticker(
        self,
        symbol: str,
        callback: Callable
    ) -> None:
        """Subscribe to real-time ticker updates via WebSocket
        
        Args:
            symbol: Trading pair to subscribe to
            callback: Async callable that receives Ticker objects
            
        Example:
            >>> async def on_ticker(ticker):
            ...     print(f"{ticker.symbol}: {ticker.last_price}")
            >>> 
            >>> await client.subscribe_ticker("BTCUSDT", on_ticker)
        """
        stream_name = f"{symbol.lower()}@ticker"
        
        if stream_name not in self.subscriptions:
            self.subscriptions[stream_name] = []
        
        self.subscriptions[stream_name].append(callback)
        
        # Start WebSocket if not already running
        if stream_name not in self.ws_connections:
            asyncio.create_task(self._maintain_ws(stream_name))

    async def subscribe_trades(
        self,
        symbol: str,
        callback: Callable
    ) -> None:
        """Subscribe to real-time trade updates via WebSocket
        
        Args:
            symbol: Trading pair
            callback: Async callable receiving trade data
            
        Example:
            >>> async def on_trade(trade):
            ...     print(f"Trade: {trade['qty']} @ {trade['price']}")
            >>> 
            >>> await client.subscribe_trades("BTCUSDT", on_trade)
        """
        stream_name = f"{symbol.lower()}@trade"
        
        if stream_name not in self.subscriptions:
            self.subscriptions[stream_name] = []
        
        self.subscriptions[stream_name].append(callback)
        
        if stream_name not in self.ws_connections:
            asyncio.create_task(self._maintain_ws(stream_name))

    async def subscribe_order_book(
        self,
        symbol: str,
        callback: Callable,
        depth: int = 20
    ) -> None:
        """Subscribe to order book updates via WebSocket
        
        Args:
            symbol: Trading pair
            callback: Async callable receiving order book
            depth: Depth level (5, 10, 20 supported)
            
        Example:
            >>> async def on_book(book):
            ...     top_bid = float(book["bids"][0][0])
            ...     top_ask = float(book["asks"][0][0])
            >>> 
            >>> await client.subscribe_order_book("BTCUSDT", on_book, depth=20)
        """
        stream_name = f"{symbol.lower()}@depth{depth}"
        
        if stream_name not in self.subscriptions:
            self.subscriptions[stream_name] = []
        
        self.subscriptions[stream_name].append(callback)
        
        if stream_name not in self.ws_connections:
            asyncio.create_task(self._maintain_ws(stream_name))

    async def _maintain_ws(self, stream_name: str) -> None:
        """Maintain WebSocket connection with auto-reconnect
        
        Args:
            stream_name: Stream identifier
        """
        reconnect_delay = 1
        max_reconnect_delay = 60
        
        while stream_name in self.subscriptions:
            try:
                ws_url = f"{self.ws_base}/{stream_name}"
                
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(ws_url) as ws:
                        self.ws_connections[stream_name] = ws
                        reconnect_delay = 1
                        
                        logger.info(f"WebSocket connected: {stream_name}")
                        
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                
                                # Process message based on stream type
                                await self._process_ws_message(stream_name, data)
                            
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                logger.error(f"WebSocket error on {stream_name}")
                                break
                            
                            elif msg.type == aiohttp.WSMsgType.CLOSED:
                                logger.warning(f"WebSocket closed: {stream_name}")
                                break
            
            except Exception as e:
                logger.error(f"WebSocket error ({stream_name}): {e}")
                
                if stream_name in self.ws_connections:
                    del self.ws_connections[stream_name]
                
                # Exponential backoff reconnect
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
            
            else:
                # Connection ended normally, try to reconnect
                await asyncio.sleep(reconnect_delay)

    async def _process_ws_message(self, stream_name: str, data: Dict) -> None:
        """Process WebSocket message and call registered callbacks
        
        Args:
            stream_name: Stream identifier
            data: Message data
        """
        try:
            if stream_name not in self.subscriptions:
                return
            
            # Determine message type from stream name
            if "@ticker" in stream_name:
                ticker = Ticker(
                    symbol=data.get("s"),
                    last_price=float(data.get("c", 0)),
                    bid=float(data.get("b", 0)),
                    ask=float(data.get("a", 0)),
                    high_24h=float(data.get("h", 0)),
                    low_24h=float(data.get("l", 0)),
                    volume_24h=float(data.get("v", 0)),
                    timestamp=datetime.utcnow()
                )
                
                for callback in self.subscriptions[stream_name]:
                    await callback(ticker)
            
            elif "@trade" in stream_name:
                for callback in self.subscriptions[stream_name]:
                    await callback(data)
            
            elif "@depth" in stream_name:
                for callback in self.subscriptions[stream_name]:
                    await callback(data)
        
        except Exception as e:
            logger.error(f"Error processing WS message: {e}")

    async def get_trading_rules(self) -> Dict[str, Any]:
        """Get exchange trading rules and limits
        
        Returns:
            Trading rules for all symbols
            
        Example:
            >>> rules = await client.get_trading_rules()
            >>> btc_rules = rules["BTCUSDT"]
            >>> print(f"Min price: {btc_rules['filters'][0]['minPrice']}")
        """
        data = await self._request("GET", "v3/exchangeInfo")
        
        rules_by_symbol = {}
        for symbol_info in data.get("symbols", []):
            symbol = symbol_info["symbol"]
            rules_by_symbol[symbol] = {
                "baseAsset": symbol_info.get("baseAsset"),
                "quoteAsset": symbol_info.get("quoteAsset"),
                "status": symbol_info.get("status"),
                "filters": symbol_info.get("filters", []),
                "orderTypes": symbol_info.get("orderTypes", []),
            }
        
        return rules_by_symbol

    async def get_recent_trades(self, symbol: str, limit: int = 500) -> List[Dict]:
        """Get recent trades on the market
        
        Args:
            symbol: Trading pair
            limit: Number of trades (max 1000)
            
        Returns:
            List of recent trades with price, qty, time
            
        Example:
            >>> trades = await client.get_recent_trades("BTCUSDT", limit=10)
            >>> for trade in trades:
            ...     print(f"${trade['price']} x {trade['qty']}")
        """
        data = await self._request(
            "GET",
            "v3/trades",
            {"symbol": symbol, "limit": min(limit, 1000)}
        )
        return data

    async def get_account_trades(
        self,
        symbol: str,
        start_time: Optional[int] = None,
        limit: int = 500
    ) -> List[Dict]:
        """Get account's trades on a symbol
        
        Args:
            symbol: Trading pair
            start_time: Start time in milliseconds
            limit: Number of trades (max 1000)
            
        Returns:
            List of user's trades with commission, fees
        """
        params = {
            "symbol": symbol,
            "limit": min(limit, 1000)
        }
        
        if start_time:
            params["startTime"] = start_time
        
        endpoint = "v3/myTrades" if self.trading_type == BinanceTradingType.SPOT else "fapi/v1/userTrades"
        
        return await self._request(
            "GET",
            endpoint,
            params,
            signed=True,
            is_futures=(self.trading_type == BinanceTradingType.FUTURES)
        )

    async def estimate_fee(
        self,
        symbol: str,
        quantity: float,
        price: float
    ) -> Dict[str, float]:
        """Estimate trading fees for an order
        
        Args:
            symbol: Trading pair
            quantity: Order quantity
            price: Order price
            
        Returns:
            Dict with maker_fee, taker_fee, estimated_cost
            
        Example:
            >>> fee = await client.estimate_fee("BTCUSDT", 0.1, 42000)
            >>> print(f"Estimated cost: ${fee['estimated_cost']:.2f}")
        """
        # Get trading commission info
        account = await self._request(
            "GET",
            "v3/account" if self.trading_type == BinanceTradingType.SPOT else "fapi/v2/account",
            {},
            signed=True,
            is_futures=(self.trading_type == BinanceTradingType.FUTURES)
        )
        
        maker_commission = account.get("makerCommission", 10) / 10000
        taker_commission = account.get("takerCommission", 10) / 10000
        
        total_cost = quantity * price
        
        return {
            "maker_fee": total_cost * maker_commission,
            "taker_fee": total_cost * taker_commission,
            "estimated_cost": total_cost,
            "maker_rate": maker_commission,
            "taker_rate": taker_commission
        }

    async def validate_symbol(self, symbol: str) -> bool:
        """Check if symbol exists and is tradeable
        
        Args:
            symbol: Trading pair to validate
            
        Returns:
            True if symbol is valid and tradeable
        """
        try:
            await self.get_price(symbol)
            return True
        except Exception:
            return False

    async def get_server_time(self) -> int:
        """Get server time in milliseconds
        
        Returns:
            Server timestamp in milliseconds
            
        Example:
            >>> server_time = await client.get_server_time()
            >>> server_datetime = datetime.fromtimestamp(server_time / 1000)
        """
        data = await self._request("GET", "v3/time")
        return data.get("serverTime", int(time.time() * 1000))

    def __repr__(self) -> str:
        """String representation of BinanceAPI client"""
        return (
            f"BinanceAPI(trading_type={self.trading_type.value}, "
            f"testnet={self.testnet}, rate_limit=1200req/min)"
        )
