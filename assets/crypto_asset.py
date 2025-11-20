"""Cryptocurrency Asset Implementation - Phase 1

Crypto-specific implementation of BaseAsset for trading crypto pairs
on exchanges like Binance, Bybit, OKX, Kraken, etc.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from abc import abstractmethod

from assets.base_asset import BaseAsset, PriceData, DataSource
from database.schemas import (
    AssetClass, AssetMetadata, OHLCVData,
    TechnicalIndicators, MarketSentiment, SignalType
)


logger = logging.getLogger(__name__)


class CryptoAsset(BaseAsset):
    """Cryptocurrency asset implementation.
    
    Handles all crypto-specific operations including:
    - Real-time price fetching from multiple exchanges
    - OHLCV data retrieval from exchange APIs
    - Technical indicator calculations
    - Market sentiment analysis for crypto pairs
    - Balance/portfolio management
    """
    
    SUPPORTED_EXCHANGES = {
        "binance": "BINANCE",
        "bybit": "BYBIT",
        "okx": "OKX",
        "kraken": "KRAKEN",
        "coinbase": "COINBASE",
        "huobi": "HUOBI",
        "gate.io": "GATE"
    }
    
    # Crypto-specific timeframes
    SUPPORTED_TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
    
    def __init__(
        self,
        metadata: AssetMetadata,
        exchange_api: Optional[Any] = None,
        use_websocket: bool = False
    ):
        """Initialize CryptoAsset.
        
        Args:
            metadata: Asset metadata with crypto info
            exchange_api: Exchange API client instance
            use_websocket: Whether to use WebSocket for real-time data
        """
        super().__init__(metadata)
        self.exchange_api = exchange_api
        self.use_websocket = use_websocket
        self._validate_crypto_metadata()
    
    def _validate_crypto_metadata(self) -> None:
        """Validate that metadata contains crypto-specific info."""
        if self.metadata.asset_class != AssetClass.CRYPTO:
            raise ValueError(f"Expected CRYPTO asset class, got {self.metadata.asset_class}")
        
        if not self.metadata.cryptocurrency_info:
            logger.warning(f"Crypto metadata empty for {self.symbol}")
    
    async def get_current_price(self) -> PriceData:
        """Fetch current crypto price from exchange.
        
        Returns:
            PriceData with current bid/ask and last price
        """
        try:
            if self.exchange_api is None:
                raise RuntimeError(f"Exchange API not configured for {self.symbol}")
            
            # Fetch from exchange API (implementation depends on exchange)
            ticker = await self.exchange_api.fetch_ticker(self.symbol)
            
            price_data = PriceData(
                current_price=ticker['last'],
                bid_price=ticker['bid'],
                ask_price=ticker['ask'],
                timestamp=datetime.utcfromtimestamp(ticker['timestamp'] / 1000),
                source=DataSource.EXCHANGE_API if not self.use_websocket else DataSource.WEBSOCKET
            )
            
            self.cache_price(price_data)
            return price_data
            
        except Exception as e:
            logger.error(f"Error fetching price for {self.symbol}: {e}")
            # Try cache
            cached = self.get_cached_price()
            if cached:
                return cached
            raise
    
    async def get_ohlcv_data(
        self,
        timeframe: str,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[OHLCVData]:
        """Fetch OHLCV candlestick data from exchange.
        
        Args:
            timeframe: Candlestick timeframe (1m, 5m, 1h, 4h, 1d, etc)
            limit: Number of candles to fetch
            since: Start date for historical data
            
        Returns:
            List of OHLCV candles sorted by time ascending
        """
        if timeframe not in self.SUPPORTED_TIMEFRAMES:
            raise ValueError(f"Unsupported timeframe: {timeframe}. Supported: {self.SUPPORTED_TIMEFRAMES}")
        
        try:
            if self.exchange_api is None:
                raise RuntimeError(f"Exchange API not configured for {self.symbol}")
            
            # Fetch OHLCV from exchange
            since_ms = None
            if since:
                since_ms = int(since.timestamp() * 1000)
            
            ohlcv_raw = await self.exchange_api.fetch_ohlcv(
                self.symbol,
                timeframe=timeframe,
                limit=limit,
                since=since_ms
            )
            
            # Convert to OHLCVData objects
            ohlcv_data = []
            for candle in ohlcv_raw:
                ohlcv = OHLCVData(
                    timestamp=datetime.utcfromtimestamp(candle[0] / 1000),
                    open=float(candle[1]),
                    high=float(candle[2]),
                    low=float(candle[3]),
                    close=float(candle[4]),
                    volume=float(candle[5])
                )
                ohlcv_data.append(ohlcv)
            
            # Cache by timeframe
            self.cache_ohlcv(ohlcv_data, timeframe)
            return ohlcv_data
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {self.symbol} {timeframe}: {e}")
            # Try cache
            cached = self.get_cached_ohlcv(timeframe)
            if cached:
                return cached
            raise
    
    async def calculate_technical_indicators(
        self,
        ohlcv_data: List[OHLCVData]
    ) -> TechnicalIndicators:
        """Calculate technical indicators for crypto asset.
        
        Args:
            ohlcv_data: List of OHLCV candles
            
        Returns:
            TechnicalIndicators with calculated values
        """
        if len(ohlcv_data) < 20:
            raise ValueError(f"Need at least 20 candles for indicators, got {len(ohlcv_data)}")
        
        # Extract close prices for calculations
        closes = [candle.close for candle in ohlcv_data]
        volumes = [candle.volume for candle in ohlcv_data]
        
        # Calculate indicators using technical analysis library (TA-Lib)
        # This is a simplified version - real implementation would use ta-lib or pandas_ta
        indicators = TechnicalIndicators(
            # RSI (Relative Strength Index)
            rsi=self._calculate_rsi(closes),
            
            # MACD
            macd=self._calculate_macd(closes),
            
            # Moving Averages
            sma_20=self._calculate_sma(closes, 20),
            sma_50=self._calculate_sma(closes, 50),
            sma_200=self._calculate_sma(closes, 200),
            
            # EMA
            ema_12=self._calculate_ema(closes, 12),
            ema_26=self._calculate_ema(closes, 26),
            
            # Bollinger Bands
            bollinger_middle=self._calculate_sma(closes, 20),
            
            # ATR
            atr=self._calculate_atr(ohlcv_data),
            
            timestamp=datetime.utcnow()
        )
        
        return indicators
    
    async def get_market_sentiment(self) -> MarketSentiment:
        """Determine market sentiment for crypto asset.
        
        Returns:
            MarketSentiment classification
        """
        try:
            # Get recent price action
            ohlcv = await self.get_ohlcv_data("1h", limit=24)
            if not ohlcv:
                return MarketSentiment.NEUTRAL
            
            # Calculate simple momentum
            first_close = ohlcv[0].close
            last_close = ohlcv[-1].close
            momentum = ((last_close - first_close) / first_close) * 100
            
            # Classify sentiment based on momentum
            if momentum > 10:
                return MarketSentiment.VERY_BULLISH
            elif momentum > 3:
                return MarketSentiment.BULLISH
            elif momentum < -10:
                return MarketSentiment.VERY_BEARISH
            elif momentum < -3:
                return MarketSentiment.BEARISH
            else:
                return MarketSentiment.NEUTRAL
                
        except Exception as e:
            logger.error(f"Error calculating sentiment for {self.symbol}: {e}")
            return MarketSentiment.NEUTRAL
    
    async def validate_trading_pair(self, pair: str) -> bool:
        """Validate if trading pair is supported.
        
        Args:
            pair: Trading pair (e.g., 'BTC/USD', 'ETH/USDT')
            
        Returns:
            True if pair is valid and tradeable
        """
        try:
            if not self.exchange_api:
                return True  # Assume valid if no exchange configured
            
            symbols = await self.exchange_api.fetch_symbols()
            return pair in symbols
            
        except Exception as e:
            logger.error(f"Error validating pair {pair}: {e}")
            return False
    
    async def get_balance(self, exchange_key: Optional[str] = None) -> float:
        """Get balance for this crypto asset.
        
        Args:
            exchange_key: Optional API key identifier
            
        Returns:
            Available balance in this crypto
        """
        try:
            if not self.exchange_api:
                raise RuntimeError("Exchange API not configured")
            
            balance = await self.exchange_api.fetch_balance()
            base_symbol = self.symbol.split('/')[0]  # Get BTC from BTC/USDT
            
            return balance.get(base_symbol, {}).get('free', 0.0)
            
        except Exception as e:
            logger.error(f"Error fetching balance for {self.symbol}: {e}")
            return 0.0
    
    # ========================================================================
    # HELPER METHODS for Technical Analysis
    # ========================================================================
    
    def _calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        """Simple Moving Average."""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Exponential Moving Average (simplified)."""
        if len(prices) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = sum(prices[-period:]) / period
        for price in prices[-period:]:
            ema = price * multiplier + ema * (1 - multiplier)
        return ema
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Relative Strength Index."""
        if len(prices) < period + 1:
            return None
        
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [c if c > 0 else 0 for c in changes]
        losses = [-c if c < 0 else 0 for c in changes]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100 if avg_gain > 0 else 50
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: List[float]) -> Optional[float]:
        """MACD (simplified)."""
        ema12 = self._calculate_ema(prices, 12)
        ema26 = self._calculate_ema(prices, 26)
        if ema12 is None or ema26 is None:
            return None
        return ema12 - ema26
    
    def _calculate_atr(self, ohlcv_data: List[OHLCVData], period: int = 14) -> Optional[float]:
        """Average True Range."""
        if len(ohlcv_data) < period:
            return None
        
        true_ranges = []
        for i in range(1, len(ohlcv_data)):
            high_low = ohlcv_data[i].high - ohlcv_data[i].low
            high_prev = abs(ohlcv_data[i].high - ohlcv_data[i-1].close)
            low_prev = abs(ohlcv_data[i].low - ohlcv_data[i-1].close)
            true_range = max(high_low, high_prev, low_prev)
            true_ranges.append(true_range)
        
        return sum(true_ranges[-period:]) / period
