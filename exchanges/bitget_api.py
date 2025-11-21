"""Bitget Exchange API Integration - Professional Grade Implementation

Provides unified interface for Bitget spot, margin, and copy trading with:
- Async/await support for high-performance API calls
- LLM integration hooks for AI signal analysis
- Real-time WebSocket streaming
- Rate limiting with exponential backoff
- Copy trading support for strategy replication
- Growing professional exchange
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
import base64

from .base_exchange import (
    BaseExchange, Order, OrderType, Side, OrderStatus,
    Ticker, OHLCV, RateLimiter
)

logger = logging.getLogger(__name__)


class BitgetOrderType(Enum):
    """Bitget-specific order types"""
    LIMIT = "limit"
    MARKET = "market"


class BitgetTradingType(Enum):
    """Trading modes supported by Bitget"""
    SPOT = "spot"
    MARGIN = "margin"
    FUTURES = "futures"


class BitgetAPI(BaseExchange):
    """Professional-grade Bitget exchange adapter
    
    Supports spot, margin, futures, and copy trading with
    real-time WebSocket streaming and LLM integration.
    
    Performance Characteristics:
    - Free tier: 10 requests/second
    - Pro tier: 20+ requests/second
    - WebSocket real-time latency: <100ms
    - Order placement: <500ms
    - Copy trading platform focus
    
    Features:
    - Multiple trading modes (spot, margin, futures)
    - Copy trading support
    - Real-time market data streaming
    - LLM callback hooks
    - Growing professional traders community
    """

    def __init__(
        self,
        api_key: str = None,
        secret_key: str = None,
        passphrase: str = None,
        testnet: bool = False,
        trading_type: BitgetTradingType = BitgetTradingType.SPOT,
    ):
        """Initialize Bitget API client"""
        api_key = api_key or os.getenv("BITGET_API_KEY")
        secret_key = secret_key or os.getenv("BITGET_SECRET_KEY")
        passphrase = passphrase or os.getenv("BITGET_PASSPHRASE")
        
        super().__init__(api_key, secret_key)
        
        self.passphrase = passphrase
        self.trading_type = trading_type
        self.testnet = testnet
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connections: Dict[str, Any] = {}
        
        if testnet:
            self.rest_base = "https://testnet.bitgetapi.com"
            self.ws_base = "wss://ws.bitgetapi.com"
        else:
            self.rest_base = "https://api.bitget.com"
            self.ws_base = "wss://ws.bitget.com"
        
        self.rate_limiter = RateLimiter(max_requests=10, window_seconds=1)
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
            logger.info("Bitget API client closed successfully")
        except Exception as e:
            logger.error(f"Error closing Bitget client: {e}")

    def _get_signature(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """Generate HMAC SHA256 signature"""
        message = f"{timestamp}{method}{path}{body}"
        
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode()

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
        timestamp = str(int(time.time() * 1000))
        
        body = json.dumps(data) if data else ""
        signature = self._get_signature(timestamp, method, endpoint, body)
        
        headers = {
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json"
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
                    result = await response.json()
                    
                    if result.get("code") == "00000":
                        await self._emit_llm_callback("on_market_data", {
                            "exchange": "bitget",
                            "endpoint": endpoint,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        return result.get("data", result)
                    elif result.get("code") == "40429":
                        await asyncio.sleep(2 ** retry_count)
                        retry_count += 1
                    else:
                        raise Exception(f"API Error: {result.get('msg', 'Unknown')}")
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                await asyncio.sleep(2 ** retry_count)
        
        raise Exception("Max retries exceeded")

    async def get_price(self, symbol: str) -> float:
        """Get current price"""
        data = await self._request("GET", f"/api/v2/spot/ticker", {"symbol": symbol})
        
        if isinstance(data, list) and len(data) > 0:
            return float(data[0].get("lastPr", 0))
        
        return 0.0

    async def get_ticker(self, symbol: str) -> Ticker:
        """Get 24-hour ticker"""
        data = await self._request("GET", "/api/v2/spot/ticker", {"symbol": symbol})
        
        ticker_data = data[0] if isinstance(data, list) and len(data) > 0 else data
        
        ticker = Ticker(
            symbol=symbol,
            last_price=float(ticker_data.get("lastPr", 0)),
            bid=float(ticker_data.get("bidPr", 0)),
            ask=float(ticker_data.get("askPr", 0)),
            high_24h=float(ticker_data.get("high24h", 0)),
            low_24h=float(ticker_data.get("low24h", 0)),
            volume_24h=float(ticker_data.get("quoteVolume", 0)),
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
            "/api/v2/spot/candles",
            {
                "symbol": symbol,
                "granularity": timeframe,
                "limit": min(limit, 1000)
            }
        )
        
        ohlcvs = []
        candles = data if isinstance(data, list) else []
        
        for candle in candles:
            ohlcv = OHLCV(
                timestamp=datetime.fromtimestamp(int(candle[0]) / 1000),
                open=float(candle[1]),
                high=float(candle[2]),
                low=float(candle[3]),
                close=float(candle[4]),
                volume=float(candle[5])
            )
            ohlcvs.append(ohlcv)
        
        return ohlcvs

    async def place_order(self, order: Order) -> Dict[str, Any]:
        """Place order"""
        order_data = {
            "symbol": order.symbol,
            "side": order.side.value.lower(),
            "orderType": "limit" if order.price else "market",
            "size": str(order.quantity),
        }
        
        if order.price:
            order_data["price"] = str(order.price)
        
        response = await self._request(
            "POST",
            "/api/v2/spot/orders",
            data=order_data
        )
        
        await self._emit_llm_callback("on_order", {
            "exchange": "bitget",
            "action": "place",
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": order.quantity,
            "price": order.price,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return response

    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel order"""
        response = await self._request(
            "POST",
            "/api/v2/spot/cancel-order",
            data={
                "symbol": symbol,
                "orderId": order_id
            }
        )
        
        await self._emit_llm_callback("on_order", {
            "exchange": "bitget",
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
            "/api/v2/spot/order-info",
            {"symbol": symbol, "orderId": order_id}
        )

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get open orders"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        data = await self._request("GET", "/api/v2/spot/open-orders", params)
        return data if isinstance(data, list) else []

    async def get_balance(self, asset: str) -> Dict[str, float]:
        """Get account balance"""
        data = await self._request("GET", "/api/v2/spot/accounts")
        
        accounts = data if isinstance(data, list) else []
        for account in accounts:
            if account.get("coin") == asset:
                return {
                    "free": float(account.get("available", 0)),
                    "locked": float(account.get("locked", 0))
                }
        
        return {"free": 0.0, "locked": 0.0}

    async def get_order_book(self, symbol: str, depth: int = 20) -> Dict[str, Any]:
        """Get order book"""
        return await self._request(
            "GET",
            "/api/v2/spot/order-book",
            {"symbol": symbol, "limit": depth}
        )

    async def get_leverage(self, symbol: str) -> int:
        """Get leverage"""
        return 1

    async def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """Set leverage"""
        return await self._request(
            "POST",
            "/api/v2/mix/account/set-leverage",
            data={
                "symbol": symbol,
                "leverage": leverage,
                "marginCoin": "USDT"
            }
        )

    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Get funding rate"""
        return await self._request(
            "GET",
            "/api/v2/mix/market/current-fund-rate",
            {"symbol": symbol}
        )

    async def get_position(self, symbol: str) -> Dict[str, Any]:
        """Get position"""
        positions = await self._request(
            "GET",
            "/api/v2/mix/position/single-position",
            {"symbol": symbol, "marginCoin": "USDT"}
        )
        
        if isinstance(positions, list) and len(positions) > 0:
            return positions[0]
        
        return {}
    async def subscribe_ticker(self, symbol: str, callback: Callable) -> None:
        """Subscribe to ticker updates"""
        stream_name = f"ticker.{symbol}"
        if stream_name not in self.subscriptions:
            self.subscriptions[stream_name] = []
        self.subscriptions[stream_name].append(callback)
        if stream_name not in self.ws_connections:
            asyncio.create_task(self._maintain_ws(stream_name))

    async def subscribe_trades(self, symbol: str, callback: Callable) -> None:
        """Subscribe to trades"""
        stream_name = f"trades.{symbol}"
        if stream_name not in self.subscriptions:
            self.subscriptions[stream_name] = []
        self.subscriptions[stream_name].append(callback)
        if stream_name not in self.ws_connections:
            asyncio.create_task(self._maintain_ws(stream_name))

    async def subscribe_order_book(self, symbol: str, callback: Callable, depth: int = 20) -> None:
        """Subscribe to order book"""
        stream_name = f"orderbook.{depth}.{symbol}"
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
                        
                        channel = stream_name.split(".")[0]
                        symbol = stream_name.split(".")[-1]
                        
                        subscribe_msg = {
                            "op": "subscribe",
                            "args": [{
                                "instType": "sp",
                                "channel": channel,
                                "instId": symbol
                            }]
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
            for callback in self.subscriptions[stream_name]:
                await callback(data)
        except Exception as e:
            logger.error(f"Error processing WS message: {e}")

    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent trades"""
        data = await self._request("GET", "/api/v2/spot/trades", {"symbol": symbol, "limit": limit})
        return data if isinstance(data, list) else []

    async def get_account_trades(self, symbol: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get account trades"""
        params = {"limit": limit}
        if symbol:
            params["symbol"] = symbol
        data = await self._request("GET", "/api/v2/spot/account/fills", params)
        return data if isinstance(data, list) else []

    async def get_trading_rules(self) -> Dict[str, Any]:
        """Get trading rules"""
        data = await self._request("GET", "/api/v2/spot/symbols")
        rules_by_symbol = {}
        symbols_list = data if isinstance(data, list) else []
        for symbol_info in symbols_list:
            symbol = symbol_info.get("symbol")
            rules_by_symbol[symbol] = {
                "baseAsset": symbol_info.get("baseCoin"),
                "quoteAsset": symbol_info.get("quoteCoin"),
                "status": symbol_info.get("status"),
                "filters": {
                    "minPrice": symbol_info.get("priceScale"),
                    "minQty": symbol_info.get("quantityScale")
                }
            }
        return rules_by_symbol

    async def estimate_fee(self, symbol: str, quantity: float, price: float) -> Dict[str, float]:
        """Estimate fees"""
        total_cost = quantity * price
        maker_rate = 0.001
        taker_rate = 0.001
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
        data = await self._request("GET", "/api/v2/public/time")
        if isinstance(data, dict):
            return int(data.get("serverTime", int(time.time() * 1000)))
        return int(time.time() * 1000)

    async def get_positions(self) -> List[Dict]:
        """Get all positions"""
        return await self._request("GET", "/api/v2/mix/positions")

    async def get_available_symbols(self) -> List[str]:
        """Get available symbols"""
        data = await self._request("GET", "/api/v2/spot/symbols")
        symbols = []
        symbols_list = data if isinstance(data, list) else []
        for symbol_info in symbols_list:
            if symbol_info.get("status") == "online":
                symbols.append(symbol_info.get("symbol"))
        return symbols

    async def amend_order(self, order_id: str, symbol: str, qty: Optional[float] = None, price: Optional[float] = None) -> Dict[str, Any]:
        """Amend order"""
        data = {"symbol": symbol, "orderId": order_id}
        if qty:
            data["newSize"] = str(qty)
        if price:
            data["newPrice"] = str(price)
        return await self._request("POST", "/api/v2/spot/amend-order", data=data)

    async def get_account_info(self) -> Dict[str, Any]:
        """Get account info"""
        return await self._request("GET", "/api/v2/spot/account")

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Cancel all orders"""
        data = {}
        if symbol:
            data["symbol"] = symbol
        return await self._request("POST", "/api/v2/spot/cancel-orders", data=data)

    async def get_mark_price(self, symbol: str) -> float:
        """Get mark price"""
        data = await self._request("GET", "/api/v2/mix/market/current-mark-price", {"symbol": symbol})
        if isinstance(data, dict):
            return float(data.get("markPrice", 0))
        return 0.0

    async def get_index_price(self, symbol: str) -> float:
        """Get index price"""
        data = await self._request("GET", "/api/v2/mix/market/index-price", {"symbol": symbol})
        if isinstance(data, dict):
            return float(data.get("indexPrice", 0))
        return 0.0

    async def get_copy_trading_history(self, limit: int = 50) -> List[Dict]:
        """Get copy trading history"""
        return await self._request("GET", "/api/v2/spot/copy-orders", {"limit": limit})

    async def follow_trader(self, trader_id: str) -> Dict[str, Any]:
        """Follow a trader for copy trading"""
        return await self._request("POST", "/api/v2/spot/follow-trader", data={"traderId": trader_id})

    async def unfollow_trader(self, trader_id: str) -> Dict[str, Any]:
        """Unfollow a trader"""
        return await self._request("POST", "/api/v2/spot/unfollow-trader", data={"traderId": trader_id})

    async def get_followed_traders(self) -> List[Dict]:
        """Get followed traders"""
        return await self._request("GET", "/api/v2/spot/followed-traders")

    async def set_copy_trading_amount(self, trader_id: str, amount: float) -> Dict[str, Any]:
        """Set copy trading amount"""
        return await self._request(
            "POST",
            "/api/v2/spot/set-copy-amount",
            data={"traderId": trader_id, "amount": str(amount)}
        )

    async def get_margin_account(self) -> Dict[str, Any]:
        """Get margin account info"""
        return await self._request("GET", "/api/v2/spot/margin-account")

    async def borrow_margin(self, coin: str, amount: float) -> Dict[str, Any]:
        """Borrow for margin trading"""
        return await self._request(
            "POST",
            "/api/v2/spot/borrow",
            data={"coin": coin, "amount": str(amount)}
        )

    async def repay_margin(self, coin: str, amount: float) -> Dict[str, Any]:
        """Repay margin loan"""
        return await self._request(
            "POST",
            "/api/v2/spot/repay",
            data={"coin": coin, "amount": str(amount)}
        )

    async def batch_orders(self, orders: List[Order]) -> List[Dict]:
        """Place multiple orders"""
        order_list = []
        for order in orders:
            order_list.append({
                "symbol": order.symbol,
                "side": order.side.value.lower(),
                "orderType": "limit" if order.price else "market",
                "size": str(order.quantity),
                "price": str(order.price) if order.price else None
            })
        return await self._request("POST", "/api/v2/spot/batch-orders", data=order_list)

    def __repr__(self) -> str:
        return (
            f"BitgetAPI(trading_type={self.trading_type.value}, "
            f"testnet={self.testnet}, rate_limit=10req/sec)"
        )
