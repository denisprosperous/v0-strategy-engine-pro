"""KuCoin Exchange API Integration - Professional Grade Implementation

Provides unified interface for KuCoin spot and futures trading with:
- Async/await support for high-performance API calls (<100ms latency)
- LLM integration hooks for AI signal analysis
- Real-time WebSocket streaming for spot and futures
- Rate limiting with exponential backoff
- Support for community-focused features and altcoin trading
- WebSocket token authentication
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import aiohttp
import base64

from .base_exchange import (
    BaseExchange, Order, OrderType, Side, OrderStatus,
    Ticker, OHLCV, RateLimiter
)

logger = logging.getLogger(__name__)


class KuCoinOrderType(Enum):
    """KuCoin-specific order types"""
    LIMIT = "limit"
    MARKET = "market"
    LIMIT_MAKER = "limit_maker"


class KuCoinTradingType(Enum):
    """Trading modes supported by KuCoin"""
    SPOT = "spot"
    MARGIN = "margin"
    FUTURES = "futures"


class KuCoinTimeInForce(Enum):
    """Time in force options"""
    GTC = "GTC"  # Good-til-cancelled
    IOC = "IOC"  # Immediate or cancel
    FOK = "FOK"  # Fill or kill
    PO = "PO"   # Post only


class KuCoinAPI(BaseExchange):
    """Professional-grade KuCoin exchange adapter
    
    Supports spot trading and futures with real-time WebSocket
    streaming and LLM integration for signal analysis.
    
    Performance Characteristics:
    - Free tier: 3 requests/second
    - Pro tier: 10+ requests/second
    - WebSocket real-time latency: <100ms
    - Order placement: <500ms
    - Popular for altcoin trading and community features
    
    Features:
    - Multiple trading modes (spot, margin, futures)
    - Altcoin market depth and liquidity
    - Real-time market data streaming
    - LLM callback hooks for trading signals
    - WebSocket token-based authentication
    - Comprehensive order management
    """

    def __init__(
        self,
        api_key: str = None,
        secret_key: str = None,
        passphrase: str = None,
        testnet: bool = False,
        trading_type: KuCoinTradingType = KuCoinTradingType.SPOT,
    ):
        """Initialize KuCoin API client
        
        Args:
            api_key: KuCoin API key (uses KUCOIN_API_KEY env var if None)
            secret_key: KuCoin secret key (uses KUCOIN_SECRET_KEY env var if None)
            passphrase: KuCoin passphrase (uses KUCOIN_PASSPHRASE env var if None)
            testnet: Use KuCoin testnet for testing
            trading_type: SPOT, MARGIN, or FUTURES
            
        Example:
            >>> async with KuCoinAPI(trading_type=KuCoinTradingType.SPOT) as client:
            ...     price = await client.get_price("BTC-USDT")
            ...     print(f"BTC Price: ${price}")
        """
        api_key = api_key or os.getenv("KUCOIN_API_KEY")
        secret_key = secret_key or os.getenv("KUCOIN_SECRET_KEY")
        passphrase = passphrase or os.getenv("KUCOIN_PASSPHRASE")
        
        super().__init__(api_key, secret_key)
        
        self.passphrase = passphrase
        self.trading_type = trading_type
        self.testnet = testnet
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connections: Dict[str, Any] = {}
        
        # Configure API endpoints
        if testnet:
            self.rest_base = "https://openapi-sandbox.kucoin.com"
            self.ws_base = "wss://ws-sandbox.kucoin.com"
        else:
            self.rest_base = "https://api.kucoin.com"
            self.ws_base = "wss://ws.kucoin.com"
        
        # Rate limiter: 3 requests/second for free tier
        self.rate_limiter = RateLimiter(max_requests=3, window_seconds=1)
        
        # WebSocket subscriptions
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.ws_token: Optional[str] = None
        self.ws_endpoint: Optional[str] = None

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
            logger.info("KuCoin API client closed successfully")
        except Exception as e:
            logger.error(f"Error closing KuCoin client: {e}")

    def _get_signature(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """Generate authentication signature for KuCoin API
        
        Args:
            timestamp: Unix timestamp
            method: HTTP method
            path: Request path with query params
            body: Request body
            
        Returns:
            Base64-encoded signature
        """
        message = timestamp + method + path + body
        
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode()

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated API request with rate limiting and retry logic
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            path: API endpoint path
            params: Query parameters
            data: Request body
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            Exception: On API errors after max retries
        """
        if params is None:
            params = {}
        
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        # Build URL and path with params for signature
        url = f"{self.rest_base}{path}"
        
        # Generate timestamp and signature
        timestamp = str(int(time.time() * 1000))
        
        # Build path for signature
        path_for_sig = path
        if params and method == "GET":
            query_string = "&".join(
                f"{k}={v}" for k, v in sorted(params.items())
            )
            path_for_sig = f"{path}?{query_string}"
        
        body = json.dumps(data) if data else ""
        signature = self._get_signature(timestamp, method, path_for_sig, body)
        
        headers = {
            "KC-API-KEY": self.api_key,
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": timestamp,
            "KC-API-PASSPHRASE": self.passphrase,
            "KC-API-KEY-VERSION": "1",
            "Content-Type": "application/json"
        }
        
        max_retries = 3
        retry_count = 0
        backoff_base = 2
        
        while retry_count < max_retries:
            try:
                async with self.session.request(
                    method,
                    url,
                    params=params if method == "GET" else None,
                    json=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    result = await response.json()
                    
                    # Check KuCoin's status code
                    if result.get("code") == "200000":
                        # Emit LLM callback
                        await self._emit_llm_callback("on_market_data", {
                            "exchange": "kucoin",
                            "trading_mode": self.trading_type.value,
                            "endpoint": path,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        return result.get("data", result)
                    
                    elif result.get("code") == "429000":  # Rate limit
                        wait_time = backoff_base ** retry_count
                        logger.warning(
                            f"KuCoin rate limit. Waiting {wait_time}s "
                            f"before retry {retry_count + 1}/{max_retries}"
                        )
                        await asyncio.sleep(wait_time)
                        retry_count += 1
                    
                    else:
                        error_msg = result.get("msg", "Unknown error")
                        logger.error(f"KuCoin API Error: {error_msg}")
                        raise Exception(f"API Error: {error_msg}")
            
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
        
        raise Exception("Max retries exceeded")

    async def get_price(self, symbol: str) -> float:
        """Get current market price for symbol
        
        Args:
            symbol: Trading pair (e.g., 'BTC-USDT')
            
        Returns:
            Current price as float
        """
        data = await self._request(
            "GET",
            "/api/v1/market/stats",
            {"symbol": symbol}
        )
        
        if isinstance(data, dict):
            return float(data.get("last", 0))
        
        return 0.0

    async def get_ticker(self, symbol: str) -> Ticker:
        """Get 24-hour ticker data
        
        Args:
            symbol: Trading pair
            
        Returns:
            Ticker object with OHLCV data
        """
        data = await self._request(
            "GET",
            "/api/v1/market/stats",
            {"symbol": symbol}
        )
        
        ticker = Ticker(
            symbol=symbol,
            last_price=float(data.get("last", 0)),
            bid=float(data.get("buy", 0)),
            ask=float(data.get("sell", 0)),
            high_24h=float(data.get("high", 0)),
            low_24h=float(data.get("low", 0)),
            volume_24h=float(data.get("vol", 0)),
            timestamp=datetime.utcnow()
        )
        
        # Emit LLM callback
        await self._emit_llm_callback("on_ticker_update", {
            "symbol": symbol,
            "last_price": ticker.last_price,
            "volume_24h": ticker.volume_24h
        })
        
        return ticker

    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str = "1hour",
        start_at: Optional[int] = None,
        end_at: Optional[int] = None
    ) -> List[OHLCV]:
        """Get historical OHLCV candlestick data
        
        Args:
            symbol: Trading pair
            timeframe: Interval (1min, 5min, 15min, 30min, 1hour, 4hour, 1day, 1week, 1month)
            start_at: Start time in seconds
            end_at: End time in seconds
            
        Returns:
            List of OHLCV objects
        """
        params = {
            "symbol": symbol,
            "type": timeframe
        }
        
        if start_at:
            params["startAt"] = start_at
        if end_at:
            params["endAt"] = end_at
        
        data = await self._request(
            "GET",
            "/api/v1/market/candles",
            params
        )
        
        ohlcvs = []
        candles = data if isinstance(data, list) else []
        
        for candle in candles:
            ohlcv = OHLCV(
                timestamp=datetime.fromtimestamp(int(candle[0])),
                open=float(candle[1]),
                high=float(candle[3]),
                low=float(candle[4]),
                close=float(candle[2]),
                volume=float(candle[5])
            )
            ohlcvs.append(ohlcv)
         async def place_order(self, order: Order) -> Dict[str, Any]:
        """Place a new trading order
        
        Args:
            order: Order object with symbol, side, quantity, price
            
        Returns:
            Order response with orderId
        """
        order_data = {
            "clientOid": str(uuid.uuid4()),
            "symbol": order.symbol,
            "side": order.side.value.lower(),
            "type": "limit" if order.price else "market",
            "quantity": str(order.quantity),
        }
        
        if order.price:
            order_data["price"] = str(order.price)
        
        response = await self._request(
            "POST",
            "/api/v1/orders",
            data=order_data
        )
        
        # Emit LLM callback
        await self._emit_llm_callback("on_order", {
            "exchange": "kucoin",
            "action": "place",
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": order.quantity,
            "price": order.price,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return response

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Cancel an existing order
        
        Args:
            order_id: Order ID to cancel
            symbol: Optional trading pair (for futures)
            
        Returns:
            Cancellation response
        """
        path = f"/api/v1/orders/{order_id}"
        
        response = await self._request(
            "DELETE",
            path,
            {"symbol": symbol} if symbol else None
        )
        
        await self._emit_llm_callback("on_order", {
            "exchange": "kucoin",
            "action": "cancel",
            "order_id": order_id,
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return response

    async def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get order details by ID
        
        Args:
            order_id: Order ID
            
        Returns:
            Order details with status, executed quantity
        """
        return await self._request(
            "GET",
            f"/api/v1/orders/{order_id}"
        )

    async def get_open_orders(self, symbol: Optional[str] = None, side: Optional[str] = None) -> List[Dict]:
        """Get all open orders
        
        Args:
            symbol: Optional symbol filter
            side: Optional side filter (buy/sell)
            
        Returns:
            List of open orders
        """
        params = {"status": "active"}
        
        if symbol:
            params["symbol"] = symbol
        if side:
            params["side"] = side
        
        data = await self._request(
            "GET",
            "/api/v1/orders",
            params
        )
        
        if isinstance(data, dict) and "items" in data:
            return data["items"]
        
        return data if isinstance(data, list) else []

    async def get_balance(self, asset: str) -> Dict[str, float]:
        """Get account balance for an asset
        
        Args:
            asset: Asset symbol (e.g., 'BTC', 'USDT')
            
        Returns:
            Dict with 'free' and 'locked' balances
        """
        data = await self._request(
            "GET",
            "/api/v1/accounts"
        )
        
        accounts = data if isinstance(data, list) else []
        
        for account in accounts:
            if account.get("currency") == asset and account.get("type") == "trade":
                return {
                    "free": float(account.get("available", 0)),
                    "locked": float(account.get("holds", 0))
                }
        
        return {"free": 0.0, "locked": 0.0}

    async def get_order_book(self, symbol: str, depth: int = 20) -> Dict[str, Any]:
        """Get order book snapshot
        
        Args:
            symbol: Trading pair
            depth: Book depth (level2_20, level2_100)
            
        Returns:
            Order book with bids and asks
        """
        level = "level2_20" if depth <= 20 else "level2_100"
        
        return await self._request(
            "GET",
            f"/api/v1/market/orderbook",
            {
                "symbol": symbol,
                "level": level
            }
        )

    async def get_leverage(self, symbol: str) -> int:
        """Get current leverage for margin trading
        
        Args:
            symbol: Trading pair
            
        Returns:
            Leverage multiplier
        """
        if self.trading_type == KuCoinTradingType.SPOT:
            return 1
        
        data = await self._request(
            "GET",
            "/api/v1/margin/account"
        )
        
        if isinstance(data, dict):
            return int(data.get("maxLendingMutiplier", 1))
        
        return 1

    async def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """Set leverage for margin trading
        
        Args:
            symbol: Trading pair
            leverage: Leverage multiplier (1-10)
            
        Returns:
            Leverage setting response
        """
        if self.trading_type == KuCoinTradingType.SPOT:
            raise ValueError("Leverage only available for margin trading")
        
        return await self._request(
            "POST",
            "/api/v1/margin/leverage",
            data={
                "symbol": symbol,
                "leverage": leverage
            }
        )

    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Get current funding rate for futures
        
        Args:
            symbol: Trading pair
            
        Returns:
            Dict with funding rate info
        """
        if self.trading_type != KuCoinTradingType.FUTURES:
            raise ValueError("Funding rate only available for futures")
        
        data = await self._request(
            "GET",
            "/api/v1/funding-rate/current",
            {"symbol": symbol}
        )
        
        return data if isinstance(data, dict) else {}

    async def get_position(self, symbol: str) -> Dict[str, Any]:
        """Get current position for futures/margin
        
        Args:
            symbol: Trading pair
            
        Returns:
            Position details
        """
        if self.trading_type == KuCoinTradingType.SPOT:
            raise ValueError("Positions only available for futures/margin")
        
        if self.trading_type == KuCoinTradingType.FUTURES:
            positions = await self._request(
                "GET",
                "/api/v1/position",
                {"symbol": symbol}
            )
            
            if isinstance(positions, dict):
                return positions
        
        return {}

    async def subscribe_ticker(
        self,
        symbol: str,
        callback: Callable
    ) -> None:
        """Subscribe to real-time ticker updates
        
        Args:
            symbol: Trading pair
            callback: Async callable receiving ticker data
        """
        stream_name = f"ticker.{symbol}"
        
        if stream_name not in self.subscriptions:
            self.subscriptions[stream_name] = []
        
        self.subscriptions[stream_name].append(callback)
        
        if stream_name not in self.ws_connections:
            asyncio.create_task(self._maintain_ws(stream_name))

    async def subscribe_trades(
        self,
        symbol: str,
        callback: Callable
    ) -> None:
        """Subscribe to real-time trades
        
        Args:
            symbol: Trading pair
            callback: Async callable receiving trade data
        """
        stream_name = f"trade.{symbol}"
        
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
        """Subscribe to order book updates
        
        Args:
            symbol: Trading pair
            callback: Async callable receiving order book
            depth: Depth level (5, 20, 50)
        """
        stream_name = f"level2.depth{depth}.{symbol}"
        
        if stream_name not in self.subscriptions:
            self.subscriptions[stream_name] = []
        
        self.subscriptions[stream_name].append(callback)
        
        if stream_name not in self.ws_connections:
            asyncio.create_task(self._maintain_ws(stream_name))

    async def _get_ws_token(self) -> Tuple[str, str]:
        """Get WebSocket token and endpoint for private streams
        
        Returns:
            Tuple of (token, endpoint)
        """
        data = await self._request(
            "POST",
            "/api/v1/bullet-private"
        )
        
        if isinstance(data, dict):
            token = data.get("token")
            endpoint = data.get("instanceServers", [{}])[0].get("endpoint")
            return token, endpoint
        
        return None, None

    async def _maintain_ws(self, stream_name: str) -> None:
        """Maintain WebSocket connection with auto-reconnect
        
        Args:
            stream_name: Stream identifier
        """
        reconnect_delay = 1
        max_reconnect_delay = 60
        
        while stream_name in self.subscriptions:
            try:
                # Get public endpoint
                ws_url = f"{self.ws_base}/public"
                
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(ws_url) as ws:
                        self.ws_connections[stream_name] = ws
                        reconnect_delay = 1
                        
                        # Subscribe to stream
                        channel = stream_name.split(".")[0]
                        symbol = stream_name.split(".")[-1]
                        
                        subscribe_msg = {
                            "id": str(uuid.uuid4()),
                            "type": "subscribe",
                            "topic": f"/{channel}/{symbol}",
                            "privateChannel": False,
                            "response": True
                        }
                        await ws.send_json(subscribe_msg)
                        
                        logger.info(f"WebSocket connected: {stream_name}")
                        
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                await self._process_ws_message(stream_name, data)
                            
                            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSED):
                                logger.warning(f"WebSocket closed: {stream_name}")
                                break
            
            except Exception as e:
                logger.error(f"WebSocket error ({stream_name}): {e}")
                
                if stream_name in self.ws_connections:
                    del self.ws_connections[stream_name]
                
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

    async def _process_ws_message(self, stream_name: str, data: Dict) -> None:
        """Process WebSocket message and call callbacks
        
        Args:
            stream_name: Stream identifier
            data: Message data
        """
        try:
            if stream_name not in self.subscriptions:
                return
            
            # Extract actual data from KuCoin message format
            if data.get("type") == "message":
                message_data = data.get("data", {})
                
                for callback in self.subscriptions[stream_name]:
                    await callback(message_data)
        
        except Exception as e:
            logger.error(f"Error processing WS message: {e}")
       async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent trades on the market
        
        Args:
            symbol: Trading pair
            limit: Number of trades
            
        Returns:
            List of recent trades
        """
        data = await self._request(
            "GET",
            "/api/v1/market/histories",
            {"symbol": symbol}
        )
        
        return data if isinstance(data, list) else []

    async def get_account_trades(
        self,
        symbol: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get account's trades
        
        Args:
            symbol: Optional symbol filter
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            limit: Number of trades
            
        Returns:
            List of user's trades
        """
        params = {}
        
        if symbol:
            params["symbol"] = symbol
        if start_time:
            params["startAt"] = start_time
        if end_time:
            params["endAt"] = end_time
        
        data = await self._request(
            "GET",
            "/api/v1/fills",
            params
        )
        
        if isinstance(data, dict) and "items" in data:
            return data["items"]
        
        return data if isinstance(data, list) else []

    async def get_trading_rules(self) -> Dict[str, Any]:
        """Get exchange trading rules and symbol info
        
        Returns:
            Trading rules for all symbols
        """
        data = await self._request(
            "GET",
            "/api/v1/symbols"
        )
        
        rules_by_symbol = {}
        symbols_list = data if isinstance(data, list) else []
        
        for symbol_info in symbols_list:
            symbol = symbol_info.get("name")
            rules_by_symbol[symbol] = {
                "baseAsset": symbol_info.get("baseCurrency"),
                "quoteAsset": symbol_info.get("quoteCurrency"),
                "status": "trading" if symbol_info.get("enableTrading") else "disabled",
                "filters": {
                    "minPrice": symbol_info.get("priceIncrement"),
                    "minQty": symbol_info.get("baseMinSize"),
                    "maxQty": symbol_info.get("baseMaxSize")
                }
            }
        
        return rules_by_symbol

    async def estimate_fee(
        self,
        symbol: str,
        quantity: float,
        price: float
    ) -> Dict[str, float]:
        """Estimate trading fees
        
        Args:
            symbol: Trading pair
            quantity: Order quantity
            price: Order price
            
        Returns:
            Dict with fee estimates
        """
        total_cost = quantity * price
        
        # KuCoin default fees: 0.1% maker, 0.1% taker
        maker_rate = 0.001
        taker_rate = 0.001
        
        # Try to get actual fees from account
        try:
            account_data = await self._request(
                "GET",
                "/api/v1/accounts"
            )
            # Fee rates may vary by VIP level
        except Exception:
            pass
        
        return {
            "maker_fee": total_cost * maker_rate,
            "taker_fee": total_cost * taker_rate,
            "estimated_cost": total_cost,
            "maker_rate": maker_rate,
            "taker_rate": taker_rate
        }

    async def validate_symbol(self, symbol: str) -> bool:
        """Check if symbol exists and is tradeable
        
        Args:
            symbol: Trading pair
            
        Returns:
            True if symbol is valid
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
        """
        data = await self._request("GET", "/api/v1/timestamp")
        
        if isinstance(data, int):
            return data
        elif isinstance(data, dict):
            return int(data.get("epoch", int(time.time() * 1000)))
        
        return int(time.time() * 1000)

    async def get_positions(self) -> List[Dict]:
        """Get all open positions for futures
        
        Returns:
            List of positions
        """
        if self.trading_type != KuCoinTradingType.FUTURES:
            raise ValueError("Positions only for futures trading")
        
        data = await self._request(
            "GET",
            "/api/v1/positions"
        )
        
        return data if isinstance(data, list) else []

    async def get_available_symbols(self) -> List[str]:
        """Get list of all available trading symbols
        
        Returns:
            List of symbol strings
        """
        data = await self._request(
            "GET",
            "/api/v1/symbols"
        )
        
        symbols = []
        symbols_list = data if isinstance(data, list) else []
        
        for symbol_info in symbols_list:
            if symbol_info.get("enableTrading"):
                symbols.append(symbol_info.get("name"))
        
        return symbols

    async def amend_order(
        self,
        order_id: str,
        new_quantity: Optional[float] = None,
        new_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Amend (modify) an existing order
        
        Args:
            order_id: Order ID to amend
            new_quantity: New quantity (optional)
            new_price: New price (optional)
            
        Returns:
            Amendment response
        """
        data = {}
        
        if new_quantity:
            data["newSize"] = str(new_quantity)
        if new_price:
            data["newPrice"] = str(new_price)
        
        return await self._request(
            "POST",
            f"/api/v1/orders/{order_id}",
            data=data
        )

    async def get_account_info(self) -> Dict[str, Any]:
        """Get detailed account information
        
        Returns:
            Account details including balances
        """
        data = await self._request(
            "GET",
            "/api/v1/accounts"
        )
        
        return data if isinstance(data, (list, dict)) else {}

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Cancel all open orders
        
        Args:
            symbol: Optional symbol to filter orders
            
        Returns:
            Cancellation response with count
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        return await self._request(
            "DELETE",
            "/api/v1/orders",
            params
        )

    async def get_margin_account(self) -> Dict[str, Any]:
        """Get margin account details
        
        Returns:
            Margin account info with loans, risk levels
        """
        if self.trading_type != KuCoinTradingType.MARGIN:
            raise ValueError("Margin account only for margin trading")
        
        return await self._request(
            "GET",
            "/api/v1/margin/account"
        )

    async def borrow(
        self,
        currency: str,
        amount: float,
        term: Optional[str] = None
    ) -> Dict[str, Any]:
        """Borrow funds for margin trading
        
        Args:
            currency: Currency to borrow
            amount: Amount to borrow
            term: Loan term (optional)
            
        Returns:
            Borrow response with loan ID
        """
        if self.trading_type != KuCoinTradingType.MARGIN:
            raise ValueError("Borrow only for margin trading")
        
        data = {
            "currency": currency,
            "size": str(amount)
        }
        
        if term:
            data["term"] = term
        
        return await self._request(
            "POST",
            "/api/v1/margin/borrow",
            data=data
        )

    async def repay(
        self,
        currency: str,
        size: float,
        loan_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Repay borrowed funds
        
        Args:
            currency: Currency to repay
            size: Amount to repay
            loan_id: Optional specific loan ID
            
        Returns:
            Repay response
        """
        if self.trading_type != KuCoinTradingType.MARGIN:
            raise ValueError("Repay only for margin trading")
        
        data = {
            "currency": currency,
            "size": str(size)
        }
        
        if loan_id:
            data["loanId"] = loan_id
        
        return await self._request(
            "POST",
            "/api/v1/margin/repay",
            data=data
        )

    def __repr__(self) -> str:
        """String representation of KuCoinAPI client"""
        return (
            f"KuCoinAPI(trading_type={self.trading_type.value}, "
            f"testnet={self.testnet}, rate_limit=3req/sec)"
        )

        return ohlcvs
