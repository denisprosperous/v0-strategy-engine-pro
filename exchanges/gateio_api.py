"""Gate.io Exchange API Integration - Professional Grade Implementation

Provides unified interface for Gate.io spot and futures trading with:
- Async/await support for high-performance API calls
- LLM integration hooks for AI signal analysis
- Real-time WebSocket streaming
- Rate limiting with exponential backoff
- Support for alternative exchange trading
- Comprehensive derivatives support
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import aiohttp

from .base_exchange import (
    BaseExchange, Order, OrderType, Side, OrderStatus,
    Ticker, OHLCV, RateLimiter
)

logger = logging.getLogger(__name__)


class GateioOrderType(Enum):
    """Gate.io-specific order types"""
    LIMIT = "limit"
    MARKET = "market"


class GateioTradingType(Enum):
    """Trading modes supported by Gate.io"""
    SPOT = "spot"
    MARGIN = "margin"
    FUTURES = "futures"
    SWAP = "swap"


class GateioAPI(BaseExchange):
    """Professional-grade Gate.io exchange adapter
    
    Supports spot, margin, futures, and swaps with real-time
    WebSocket streaming and LLM integration.
    
    Performance Characteristics:
    - Free tier: 100 requests/minute
    - Pro tier: 1000+ requests/minute
    - WebSocket real-time latency: <100ms
    - Order placement: <500ms
    
    Features:
    - Multiple trading modes (spot, margin, futures, swaps)
    - Derivatives trading support
    - Real-time market data streaming
    - LLM callback hooks
    - Alternative exchange focus
    """

    def __init__(
        self,
        api_key: str = None,
        secret_key: str = None,
        testnet: bool = False,
        trading_type: GateioTradingType = GateioTradingType.SPOT,
    ):
        """Initialize Gate.io API client"""
        api_key = api_key or os.getenv("GATEIO_API_KEY")
        secret_key = secret_key or os.getenv("GATEIO_SECRET_KEY")
        
        super().__init__(api_key, secret_key)
        
        self.trading_type = trading_type
        self.testnet = testnet
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connections: Dict[str, Any] = {}
        
        if testnet:
            self.rest_base = "https://api-testnet.gateio.ws/api/v4"
            self.ws_base = "wss://api-testnet.gateio.ws/ws/v4"
        else:
            self.rest_base = "https://api.gateio.ws/api/v4"
            self.ws_base = "wss://api.gateio.ws/ws/v4"
        
        self.rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
        self.subscriptions: Dict[str, List[Callable]] = {}

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        try:
            for conn in self.ws_connections.values():
                await conn.close()
            if self.session and not self.session.closed:
                await self.session.close()
            logger.info("Gate.io API client closed successfully")
        except Exception as e:
            logger.error(f"Error closing Gate.io client: {e}")

    def _get_signature(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """Generate HMAC SHA512 signature"""
        message = f"{method}\n{path}\n{body}\n{timestamp}"
        
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha512
        ).hexdigest()
        
        return signature

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated API request"""
        if params is None:
            params = {}
        
        await self.rate_limiter.acquire()
        
        url = f"{self.rest_base}{endpoint}"
        timestamp = str(int(time.time()))
        
        # Build query string
        query_string = ""
        if params and method == "GET":
            query_string = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        
        path = endpoint
        if query_string:
            path = f"{endpoint}?{query_string}"
        
        body = json.dumps(data) if data else ""
        signature = self._get_signature(timestamp, method, path, body)
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "KEY": self.api_key,
            "Timestamp": timestamp,
            "SIGN": signature
        }
        
        max_retries = 3
        retry_count = 0
        
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
                    if response.status == 200:
                        result = await response.json()
                        await self._emit_llm_callback("on_market_data", {
                            "exchange": "gateio",
                            "endpoint": endpoint,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        return result
                    elif response.status == 429:
                        await asyncio.sleep(2 ** retry_count)
                        retry_count += 1
                    else:
                        raise Exception(f"API Error: {response.status}")
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                await asyncio.sleep(2 ** retry_count)
        
        raise Exception("Max retries exceeded")

    async def get_price(self, symbol: str) -> float:
        """Get current market price"""
        data = await self._request("GET", f"/spot/tickers", {"currency_pair": symbol})
        
        if isinstance(data, list) and len(data) > 0:
            return float(data[0].get("last", 0))
        return 0.0

    async def get_ticker(self, symbol: str) -> Ticker:
        """Get 24-hour ticker data"""
        data = await self._request("GET", f"/spot/tickers", {"currency_pair": symbol})
        
        ticker_data = data[0] if isinstance(data, list) and len(data) > 0 else data
        
        ticker = Ticker(
            symbol=symbol,
            last_price=float(ticker_data.get("last", 0)),
            bid=float(ticker_data.get("bid", 0)),
            ask=float(ticker_data.get("ask", 0)),
            high_24h=float(ticker_data.get("high_24h", 0)),
            low_24h=float(ticker_data.get("low_24h", 0)),
            volume_24h=float(ticker_data.get("volume", 0)),
            timestamp=datetime.utcnow()
        )
        
        await self._emit_llm_callback("on_ticker_update", {
            "symbol": symbol,
            "last_price": ticker.last_price,
            "volume_24h": ticker.volume_24h
        })
        
        return ticker

    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> List[OHLCV]:
        """Get historical OHLCV data"""
        data = await self._request(
            "GET",
            f"/spot/candlesticks",
            {
                "currency_pair": symbol,
                "interval": timeframe,
                "limit": min(limit, 1000)
            }
        )
        
        ohlcvs = []
        candles = data if isinstance(data, list) else []
        
        for candle in candles:
            ohlcv = OHLCV(
                timestamp=datetime.fromtimestamp(int(candle[0])),
                open=float(candle[1]),
                high=float(candle[2]),
                low=float(candle[3]),
                close=float(candle[4]),
                volume=float(candle[5])
            )
            ohlcvs.append(ohlcv)
        
        return ohlcvs

    async def place_order(self, order: Order) -> Dict[str, Any]:
        """Place a new trading order"""
        order_data = {
            "currency_pair": order.symbol,
            "side": order.side.value.lower(),
            "type": "limit" if order.price else "market",
            "amount": str(order.quantity),
        }
        
        if order.price:
            order_data["price"] = str(order.price)
        
        response = await self._request(
            "POST",
            "/spot/orders",
            data=order_data
        )
        
        await self._emit_llm_callback("on_order", {
            "exchange": "gateio",
            "action": "place",
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": order.quantity,
            "price": order.price,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return response

    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel an existing order"""
        response = await self._request(
            "DELETE",
            f"/spot/orders/{order_id}",
            {"currency_pair": symbol}
        )
        
        await self._emit_llm_callback("on_order", {
            "exchange": "gateio",
            "action": "cancel",
            "order_id": order_id,
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return response

    async def get_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Get order details"""
        return await self._request(
            "GET",
            f"/spot/orders/{order_id}",
            {"currency_pair": symbol}
        )

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get all open orders"""
        params = {"status": "open"}
        if symbol:
            params["currency_pair"] = symbol
        
        return await self._request("GET", "/spot/orders", params)

    async def get_balance(self, asset: str) -> Dict[str, float]:
        """Get account balance"""
        data = await self._request("GET", "/spot/accounts")
        
        accounts = data if isinstance(data, list) else []
        for account in accounts:
            if account.get("currency") == asset:
                return {
                    "free": float(account.get("available", 0)),
                    "locked": float(account.get("locked", 0))
                }
        
        return {"free": 0.0, "locked": 0.0}

    async def get_order_book(self, symbol: str, depth: int = 20) -> Dict[str, Any]:
        """Get order book snapshot"""
        return await self._request(
            "GET",
            "/spot/order_book",
            {"currency_pair": symbol, "limit": depth}
        )

    async def get_leverage(self, symbol: str) -> int:
        """Get current leverage"""
        return 1

    async def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """Set leverage"""
        raise ValueError("Leverage not available for spot trading")

    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Get funding rate for perpetuals"""
        return await self._request(
            "GET",
            f"/perpetual/funding_rate",
            {"settle": "usdt", "contract": symbol}
        )

    async def get_position(self, symbol: str) -> Dict[str, Any]:
        """Get position for perpetuals"""
        return await self._request(
            "GET",
            f"/perpetual/positions",
            {"settle": "usdt", "contract": symbol}
        )
    async def subscribe_ticker(
        self,
        symbol: str,
        callback: Callable
    ) -> None:
        """Subscribe to real-time ticker updates"""
        stream_name = f"spot.tickers.{symbol}"
        
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
        """Subscribe to real-time trades"""
        stream_name = f"spot.trades.{symbol}"
        
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
        """Subscribe to order book updates"""
        stream_name = f"spot.order_book.{depth}.{symbol}"
        
        if stream_name not in self.subscriptions:
            self.subscriptions[stream_name] = []
        
        self.subscriptions[stream_name].append(callback)
        
        if stream_name not in self.ws_connections:
            asyncio.create_task(self._maintain_ws(stream_name))

    async def _maintain_ws(self, stream_name: str) -> None:
        """Maintain WebSocket connection"""
        reconnect_delay = 1
        max_reconnect_delay = 60
        
        while stream_name in self.subscriptions:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(self.ws_base) as ws:
                        self.ws_connections[stream_name] = ws
                        reconnect_delay = 1
                        
                        # Subscribe
                        channel = stream_name.split(".")[1]
                        symbol = stream_name.split(".")[-1]
                        
                        subscribe_msg = {
                            "time": int(time.time()),
                            "channel": channel,
                            "event": "subscribe",
                            "payload": [symbol]
                        }
                        await ws.send_json(subscribe_msg)
                        
                        logger.info(f"WebSocket connected: {stream_name}")
                        
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                await self._process_ws_message(stream_name, data)
                            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSED):
                                break
            
            except Exception as e:
                logger.error(f"WebSocket error ({stream_name}): {e}")
                
                if stream_name in self.ws_connections:
                    del self.ws_connections[stream_name]
                
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

    async def _process_ws_message(self, stream_name: str, data: Dict) -> None:
        """Process WebSocket message"""
        try:
            if stream_name not in self.subscriptions:
                return
            
            message_data = data.get("result", {})
            
            for callback in self.subscriptions[stream_name]:
                await callback(message_data)
        
        except Exception as e:
            logger.error(f"Error processing WS message: {e}")

    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent trades"""
        data = await self._request(
            "GET",
            "/spot/trades",
            {"currency_pair": symbol, "limit": min(limit, 1000)}
        )
        return data if isinstance(data, list) else []

    async def get_account_trades(
        self,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get account trades"""
        params = {"limit": min(limit, 500)}
        if symbol:
            params["currency_pair"] = symbol
        
        return await self._request("GET", "/spot/my_trades", params)

    async def get_trading_rules(self) -> Dict[str, Any]:
        """Get trading rules"""
        data = await self._request("GET", "/spot/currency_pairs")
        
        rules_by_symbol = {}
        symbols_list = data if isinstance(data, list) else []
        
        for symbol_info in symbols_list:
            symbol = symbol_info.get("id")
            rules_by_symbol[symbol] = {
                "baseAsset": symbol_info.get("base"),
                "quoteAsset": symbol_info.get("quote"),
                "status": symbol_info.get("trade_status"),
                "filters": {
                    "minPrice": symbol_info.get("min_base_amount"),
                    "maxQty": symbol_info.get("max_base_amount")
                }
            }
        
        return rules_by_symbol

    async def estimate_fee(
        self,
        symbol: str,
        quantity: float,
        price: float
    ) -> Dict[str, float]:
        """Estimate trading fees"""
        total_cost = quantity * price
        
        # Gate.io default: 0.2% maker, 0.2% taker
        maker_rate = 0.002
        taker_rate = 0.002
        
        return {
            "maker_fee": total_cost * maker_rate,
            "taker_fee": total_cost * taker_rate,
            "estimated_cost": total_cost,
            "maker_rate": maker_rate,
            "taker_rate": taker_rate
        }

    async def validate_symbol(self, symbol: str) -> bool:
        """Validate symbol"""
        try:
            await self.get_price(symbol)
            return True
        except Exception:
            return False

    async def get_server_time(self) -> int:
        """Get server time"""
        data = await self._request("GET", "/spot/time")
        
        if isinstance(data, dict):
            return int(data.get("mstime", int(time.time() * 1000)))
        
        return int(time.time() * 1000)

    async def get_positions(self) -> List[Dict]:
        """Get all positions"""
        return await self._request("GET", "/perpetual/positions", {"settle": "usdt"})

    async def get_available_symbols(self) -> List[str]:
        """Get available symbols"""
        data = await self._request("GET", "/spot/currency_pairs")
        
        symbols = []
        symbols_list = data if isinstance(data, list) else []
        
        for symbol_info in symbols_list:
            if symbol_info.get("trade_status") == "tradable":
                symbols.append(symbol_info.get("id"))
        
        return symbols

    async def amend_order(
        self,
        order_id: str,
        symbol: str,
        qty: Optional[float] = None,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Amend order"""
        data = {
            "currency_pair": symbol
        }
        
        if qty:
            data["amount"] = str(qty)
        if price:
            data["price"] = str(price)
        
        return await self._request(
            "PATCH",
            f"/spot/orders/{order_id}",
            data=data
        )

    async def get_account_info(self) -> Dict[str, Any]:
        """Get account info"""
        return await self._request("GET", "/spot/accounts")

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Cancel all orders"""
        params = {}
        if symbol:
            params["currency_pair"] = symbol
        
        return await self._request("DELETE", "/spot/orders", params)

    async def get_futures_positions(self) -> List[Dict]:
        """Get futures positions"""
        return await self._request(
            "GET",
            "/perpetual/positions",
            {"settle": "usdt"}
        )

    async def set_futures_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """Set futures leverage"""
        return await self._request(
            "POST",
            "/perpetual/positions/{symbol}/leverage",
            data={"leverage": str(leverage)},
            params={"settle": "usdt"}
        )

    async def get_mark_price(self, symbol: str) -> float:
        """Get mark price for perpetuals"""
        data = await self._request(
            "GET",
            "/perpetual/mark_prices",
            {"settle": "usdt", "contract": symbol}
        )
        
        if isinstance(data, list) and len(data) > 0:
            return float(data[0].get("mark_price", 0))
        
        return 0.0

    async def get_index_price(self, symbol: str) -> float:
        """Get index price for perpetuals"""
        data = await self._request(
            "GET",
            "/perpetual/index_prices",
            {"settle": "usdt"}
        )
        
        if isinstance(data, list):
            for item in data:
                if item.get("contract") == symbol:
                    return float(item.get("index_price", 0))
        
        return 0.0

    def __repr__(self) -> str:
        """String representation"""
        return (
            f"GateioAPI(trading_type={self.trading_type.value}, "
            f"testnet={self.testnet}, rate_limit=100req/min)"
        )
    async def get_cross_margin_balance(self) -> Dict[str, Any]:
        """Get cross margin balance"""
        return await self._request("GET", "/margin/accounts", {"account_mode": "cross_margin"})

    async def get_isolated_margin_balance(self) -> Dict[str, Any]:
        """Get isolated margin balance"""
        return await self._request("GET", "/margin/accounts", {"account_mode": "isolated_margin"})

    async def borrow_margin(
        self,
        currency: str,
        amount: float,
        account_mode: str = "cross_margin"
    ) -> Dict[str, Any]:
        """Borrow funds for margin trading"""
        return await self._request(
            "POST",
            "/margin/loans",
            data={
                "currency": currency,
                "amount": str(amount),
                "account_mode": account_mode
            }
        )

    async def repay_margin(
        self,
        currency: str,
        amount: float,
        loan_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Repay margin loan"""
        data = {
            "currency": currency,
            "amount": str(amount)
        }
        
        if loan_id:
            data["loan_id"] = loan_id
        
        return await self._request(
            "POST",
            "/margin/repayments",
            data=data
        )

    async def get_margin_loans(self) -> List[Dict]:
        """Get margin loans"""
        return await self._request("GET", "/margin/loans", {"status": "open"})

    async def get_futures_account(self) -> Dict[str, Any]:
        """Get futures account details"""
        return await self._request(
            "GET",
            "/perpetual/accounts",
            {"settle": "usdt"}
        )

    async def place_futures_order(
        self,
        symbol: str,
        side: str,
        size: float,
        price: Optional[float] = None,
        reduce_only: bool = False
    ) -> Dict[str, Any]:
        """Place futures order"""
        order_data = {
            "contract": symbol,
            "size": int(size),
            "side": side,
            "reduce_only": reduce_only
        }
        
        if price:
            order_data["price"] = str(price)
        
        return await self._request(
            "POST",
            "/perpetual/orders",
            data=order_data,
            params={"settle": "usdt"}
        )

    async def cancel_futures_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel futures order"""
        return await self._request(
            "DELETE",
            f"/perpetual/orders/{order_id}",
            {"settle": "usdt", "contract": symbol}
        )

    async def get_futures_funding_history(
        self,
        symbol: str,
        limit: int = 100
    ) -> List[Dict]:
        """Get futures funding history"""
        return await self._request(
            "GET",
            f"/perpetual/funding_history",
            {
                "settle": "usdt",
                "contract": symbol,
                "limit": min(limit, 1000)
            }
        )

    async def get_swap_tickers(self, settle: str = "usdt") -> List[Dict]:
        """Get swap/futures tickers"""
        return await self._request(
            "GET",
            "/swap/tickers",
            {"settle": settle}
        )

    async def batch_orders(self, orders: List[Order]) -> List[Dict]:
        """Place multiple orders"""
        order_list = []
        for order in orders:
            order_list.append({
                "currency_pair": order.symbol,
                "side": order.side.value.lower(),
                "type": "limit" if order.price else "market",
                "amount": str(order.quantity),
                "price": str(order.price) if order.price else None
            })
        
        return await self._request(
            "POST",
            "/spot/batch_orders",
            data=order_list
        )

    async def get_max_withdrawal(self, currency: str) -> Dict[str, float]:
        """Get maximum withdrawal amount"""
        data = await self._request(
            "GET",
            "/wallet/withdraw_status",
            {"currency": currency}
        )
        
        if isinstance(data, dict):
            return {
                "max_amount": float(data.get("withdraw_fix", 0)) + float(data.get("withdraw_percent", 0))
            }
        
        return {"max_amount": 0.0}

    async def withdraw(
        self,
        currency: str,
        amount: float,
        address: str,
        tag: Optional[str] = None,
        network: Optional[str] = None
    ) -> Dict[str, Any]:
        """Withdraw cryptocurrency"""
        data = {
            "currency": currency,
            "amount": str(amount),
            "address": address
        }
        
        if tag:
            data["memo"] = tag
        if network:
            data["chain"] = network
        
        return await self._request(
            "POST",
            "/withdrawals",
            data=data
        )

    async def get_deposit_address(self, currency: str) -> Dict[str, Any]:
        """Get deposit address"""
        return await self._request(
            "GET",
            "/wallet/deposit_address",
            {"currency": currency}
        )

    async def get_transfer_history(
        self,
        currency: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get transfer history"""
        params = {"limit": min(limit, 500)}
        
        if currency:
            params["currency"] = currency
        
        return await self._request("GET", "/wallet/transfers", params)

    async def internal_transfer(
        self,
        currency: str,
        amount: float,
        from_account: str,
        to_account: str
    ) -> Dict[str, Any]:
        """Internal transfer between accounts"""
        return await self._request(
            "POST",
            "/wallet/transfers",
            data={
                "currency": currency,
                "amount": str(amount),
                "from_account": from_account,
                "to_account": to_account
            }
        )
