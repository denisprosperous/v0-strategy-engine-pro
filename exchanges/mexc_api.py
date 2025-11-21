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
