import ccxt
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime
import json
import asyncio
import aiohttp
from .base_exchange import BaseExchange, Order


class MEXCAPI(BaseExchange):
    """Concrete implementation for MEXC exchange"""
    
    def __init__(self, api_key: str, secret_key: str, passphrase: Optional[str] = None):
        super().__init__(api_key, secret_key, passphrase)
        self.exchange = ccxt.mexc({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'defaultCurrency': 'USDT',
                'warnOnFetchOpenOrdersWithoutSymbol': False,
                'fetchTradingFees': True,
                'fetchMyTradesMethod': 'private',
                'createMarketBuyOrderRequiresPrice': False,
            }
        })
        
        self.trading_mode = 'spot'
        self.ws = None
        self.ws_url = 'wss://wbs.mexc.com/raw/ws'
        self.rest_url = 'https://api.mexc.com'
        self.rate_limiter = {'requests': 0, 'reset_time': 0}
        self.max_requests_per_minute = 1200

    async def connect_websocket(self) -> None:
        """Establish WebSocket connection to MEXC with authentication."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            connector = aiohttp.TCPConnector(
                ssl=False,
                limit_per_host=10,
                ttl_dns_cache=300
            )
            
            self.session = aiohttp.ClientSession(connector=connector)
            self.ws = await self.session.ws_connect(
                self.ws_url,
                headers=headers,
                heartbeat=30,
                receive_timeout=60
            )
            
            self.on_signal("websocket_connected", {"exchange": "MEXC", "timestamp": datetime.now().isoformat()})
            
        except Exception as e:
            self.on_risk_alert(f"WebSocket connection failed: {str(e)}")
            if self.session:
                await self.session.close()
            raise

    async def disconnect_websocket(self) -> None:
        """Gracefully close WebSocket connection and cleanup."""
        try:
            if self.ws:
                await self.ws.close()
            if self.session:
                await self.session.close()
            self.on_signal("websocket_disconnected", {"exchange": "MEXC", "timestamp": datetime.now().isoformat()})
        except Exception as e:
            self.on_risk_alert(f"WebSocket disconnection error: {str(e)}")

    async def request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                     signed: bool = False, data: Optional[Dict] = None) -> Dict:
        """Make authenticated or unauthenticated request to MEXC API."""
        try:
            await self._apply_rate_limit()
            
            headers = {'Content-Type': 'application/json'}
            
            if signed:
                headers['X-MEXC-APIKEY'] = self.api_key
                timestamp = str(int(datetime.now().timestamp() * 1000))
                headers['X-MEXC-TIMESTAMP'] = timestamp
                
                import hmac
                import hashlib
                
                query_string = '&'.join([f"{k}={v}" for k, v in (params or {}).items()])
                signature_str = f"{timestamp}{method}{endpoint}{query_string}"
                
                signature = hmac.new(
                    self.secret_key.encode(),
                    signature_str.encode(),
                    hashlib.sha256
                ).hexdigest()
                
                headers['X-MEXC-SIGN'] = signature
            
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    endpoint,
                    params=params,
                    json=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        self.on_risk_alert("Rate limit exceeded, applying exponential backoff")
                        await asyncio.sleep(5)
                        return await self.request(method, endpoint, params, signed, data)
                    else:
                        error_data = await response.text()
                        self.on_risk_alert(f"API Error {response.status}: {error_data}")
                        return {}
                        
        except asyncio.TimeoutError:
            self.on_risk_alert("Request timeout, retrying...")
            await asyncio.sleep(2)
            return await self.request(method, endpoint, params, signed, data)
        except Exception as e:
            self.on_risk_alert(f"Request failed: {str(e)}")
            return {}

    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting - 1200 requests per minute."""
        import time
        current_time = time.time()
        
        if current_time - self.rate_limiter['reset_time'] >= 60:
            self.rate_limiter['requests'] = 0
            self.rate_limiter['reset_time'] = current_time
        
        if self.rate_limiter['requests'] >= self.max_requests_per_minute * 0.9:
            wait_time = min(60 - (current_time - self.rate_limiter['reset_time']), 5)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                self.rate_limiter['requests'] = 0
                self.rate_limiter['reset_time'] = time.time()
        
        self.rate_limiter['requests'] += 1

    async def get_balance(self) -> Dict:
        """Retrieve account balance and asset information."""
        try:
            balance = self.exchange.fetch_balance()
            
            formatted_balance = {}
            for asset, balances in balance.items():
                if asset not in ['free', 'used', 'total']:
                    formatted_balance[asset] = {
                        'free': float(balances.get('free', 0)),
                        'used': float(balances.get('used', 0)),
                        'total': float(balances.get('total', 0))
                    }
            
            self.on_signal("balance_updated", formatted_balance)
            return formatted_balance
            
        except Exception as e:
            self.on_risk_alert(f"Failed to fetch balance: {str(e)}")
            return {}

    async def get_current_price(self, symbol: str) -> float:
        """Get current market price for a symbol."""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            price = float(ticker.get('last', 0))
            
            self.on_market_data("price_update", {
                "symbol": symbol,
                "price": price,
                "bid": ticker.get('bid'),
                "ask": ticker.get('ask'),
                "timestamp": ticker.get('timestamp')
            })
            
            return price
            
        except Exception as e:
            self.on_risk_alert(f"Failed to get price for {symbol}: {str(e)}")
            return 0.0

    async def get_24h_volume(self, symbol: str) -> Dict:
        """Get 24-hour trading volume and price change."""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            
            volume_info = {
                'symbol': symbol,
                'volume_24h': float(ticker.get('quoteVolume', 0)),
                'volume_base_24h': float(ticker.get('baseVolume', 0)),
                'price_change_24h': float(ticker.get('change', 0)),
                'price_change_percent_24h': float(ticker.get('percentage', 0)),
                'high_24h': float(ticker.get('high', 0)),
                'low_24h': float(ticker.get('low', 0)),
                'bid': float(ticker.get('bid', 0)),
                'ask': float(ticker.get('ask', 0))
            }
            
            self.on_market_data("volume_update", volume_info)
            return volume_info
            
        except Exception as e:
            self.on_risk_alert(f"Failed to get 24h volume for {symbol}: {str(e)}")
            return {}

    async def get_klines(self, symbol: str, timeframe: str = '1h', 
                        limit: int = 100) -> pd.DataFrame:
        """Fetch OHLCV (candlestick) data."""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=min(limit, 1000))
            
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['symbol'] = symbol
            
            return df
            
        except Exception as e:
            self.on_risk_alert(f"Failed to fetch klines for {symbol}: {str(e)}")
            return pd.DataFrame()

    async def subscribe_ticker(self, symbol: str) -> None:
        """Subscribe to real-time ticker updates for a symbol."""
        if not self.ws:
            await self.connect_websocket()
        
        channel = f"spot@public.deals.v3.api@{symbol}@100ms"
        subscription = {
            "method": "SUBSCRIPTION",
            "params": {
                "channels": [channel]
            }
        }
        
        await self.ws.send(json.dumps(subscription))
        self.on_signal("websocket_subscribed", {"symbol": symbol, "type": "ticker"})

    async def subscribe_trades(self, symbol: str) -> None:
        """Subscribe to real-time trade stream."""
        if not self.ws:
            await self.connect_websocket()
        
        channel = f"spot@public.deals.v3.api@{symbol}@raw"
        subscription = {
            "method": "SUBSCRIPTION",
            "params": {
                "channels": [channel]
            }
        }
        
        await self.ws.send(json.dumps(subscription))
        self.on_signal("websocket_subscribed", {"symbol": symbol, "type": "trades"})

    async def subscribe_orderbook(self, symbol: str, depth: int = 20) -> None:
        """Subscribe to real-time order book updates."""
        if not self.ws:
            await self.connect_websocket()
        
        channel = f"spot@public.depth.v3.api@{symbol}@{depth}"
        subscription = {
            "method": "SUBSCRIPTION",
            "params": {
                "channels": [channel]
            }
        }
        
        await self.ws.send(json.dumps(subscription))
        self.on_signal("websocket_subscribed", {"symbol": symbol, "type": "orderbook", "depth": depth})

    async def maintain_websocket(self) -> None:
        """Maintain WebSocket connection and process incoming messages."""
        try:
            async with self.ws:
                async for message in self.ws:
                    try:
                        data = json.loads(message)
                        
                        if data.get("method") == "PUSH":
                            channel = data.get("params", {}).get("channel", "")
                            push_data = data.get("data", {})
                            
                            if "deals" in channel:
                                self.on_market_data("ticker", {
                                    "symbol": push_data.get("s", ""),
                                    "price": float(push_data.get("p", 0)),
                                    "volume": float(push_data.get("v", 0)),
                                    "timestamp": push_data.get("t", 0)
                                })
                            
                            elif "depth" in channel:
                                self.on_market_data("orderbook", {
                                    "symbol": push_data.get("s", ""),
                                    "bids": push_data.get("b", []),
                                    "asks": push_data.get("a", []),
                                    "timestamp": push_data.get("t", 0)
                                })
                    
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        self.on_risk_alert(f"WebSocket message error: {str(e)}")
                        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.on_risk_alert(f"WebSocket error: {str(e)}")
            await asyncio.sleep(5)

    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent trades for a symbol."""
        params = {
            "symbol": symbol,
            "limit": min(limit, 1000)
        }
        
        try:
            response = await self.request(
                "GET",
                f"{self.rest_url}/api/v3/trades",
                params=params
            )
            
            trades = []
            for trade in response:
                trades.append({
                    "id": trade.get("id"),
                    "symbol": symbol,
                    "price": float(trade.get("p", 0)),
                    "quantity": float(trade.get("v", 0)),
                    "time": trade.get("t"),
                    "buyer_maker": trade.get("m", False)
                })
            
            return trades
        except Exception as e:
            self.on_risk_alert(f"Failed to get recent trades: {str(e)}")
            return []

    async def get_account_trades(self, symbol: str, start_time: Optional[int] = None,
                                 end_time: Optional[int] = None, limit: int = 500) -> List[Dict]:
        """Get account trade history."""
        params = {
            "symbol": symbol,
            "limit": min(limit, 1000)
        }
        
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        
        try:
            response = await self.request(
                "GET",
                f"{self.rest_url}/api/v3/myTrades",
                params=params,
                signed=True
            )
            
            trades = []
            for trade in response:
                trades.append({
                    "id": trade.get("id"),
                    "symbol": symbol,
                    "price": float(trade.get("price", 0)),
                    "quantity": float(trade.get("qty", 0)),
                    "commission": float(trade.get("commission", 0)),
                    "commission_asset": trade.get("commissionAsset"),
                    "time": trade.get("time"),
                    "is_buyer": trade.get("isBuyer", False),
                    "is_maker": trade.get("isMaker", False)
                })
            
            return trades
        except Exception as e:
            self.on_risk_alert(f"Failed to get account trades: {str(e)}")
            return []

    async def get_trading_rules(self, symbol: Optional[str] = None) -> Dict:
        """Get trading rules and symbol information."""
        try:
            response = await self.request(
                "GET",
                f"{self.rest_url}/api/v3/exchangeInfo"
            )
            
            rules = {
                "timezone": response.get("timezone"),
                "server_time": response.get("serverTime"),
                "symbols": {}
            }
            
            for sym_info in response.get("symbols", []):
                sym = sym_info.get("symbol")
                if symbol and sym != symbol:
                    continue
                
                rules["symbols"][sym] = {
                    "status": sym_info.get("status"),
                    "base_asset": sym_info.get("baseAsset"),
                    "quote_asset": sym_info.get("quoteAsset"),
                    "base_precision": sym_info.get("baseAssetPrecision"),
                    "quote_precision": sym_info.get("quotePrecision"),
                    "order_types": sym_info.get("orderTypes", []),
                    "filters": sym_info.get("filters", [])
                }
            
            return rules
        except Exception as e:
            self.on_risk_alert(f"Failed to get trading rules: {str(e)}")
            return {}

    async def estimate_trading_fees(self, symbol: str, quantity: float, 
                                   price: float, order_type: str = "spot") -> Dict:
        """Estimate trading fees for an order."""
        try:
            response = await self.request(
                "GET",
                f"{self.rest_url}/api/v3/account",
                signed=True
            )
            
            maker_fee = float(response.get("makerCommission", 0)) / 10000
            taker_fee = float(response.get("takerCommission", 0)) / 10000
            
            notional_value = quantity * price
            
            return {
                "symbol": symbol,
                "order_type": order_type,
                "quantity": quantity,
                "price": price,
                "notional_value": notional_value,
                "maker_fee_rate": maker_fee,
                "taker_fee_rate": taker_fee,
                "estimated_maker_fee": notional_value * maker_fee,
                "estimated_taker_fee": notional_value * taker_fee
            }
        except Exception as e:
            self.on_risk_alert(f"Failed to estimate fees: {str(e)}")
            return {}

    def __str__(self) -> str:
        """String representation of MEXC exchange instance."""
        return f"<MEXC Exchange API: {self.exchange} | Mode: {self.trading_mode}>"
