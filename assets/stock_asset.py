"""Stock Asset Implementation - Phase 1

Stock/Equity-specific implementation for trading individual stocks,
ETFs, and indices on major stock exchanges.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict

from assets.base_asset import BaseAsset, PriceData, DataSource
from database.schemas import (
    AssetClass, AssetMetadata, OHLCVData,
    TechnicalIndicators, MarketSentiment
)

logger = logging.getLogger(__name__)


class StockAsset(BaseAsset):
    """Stock/Equity asset implementation.
    
    Handles equity trading with:
    - Individual stock price tracking
    - ETF and index support
    - Dividend and corporate action handling
    - Stock-specific technical analysis
    - Earnings calendar integration
    """
    
    SUPPORTED_EXCHANGES = {
        "nasdaq": "NASDAQ",
        "nyse": "NYSE",
        "lse": "LSE",
        "jse": "JSE",
        "asx": "ASX",
        "tse": "TSE"
    }
    
    STOCK_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
    
    def __init__(
        self,
        metadata: AssetMetadata,
        broker_api: Optional[object] = None,
        include_earnings: bool = True
    ):
        """Initialize StockAsset.
        
        Args:
            metadata: Stock metadata
            broker_api: Broker API client
            include_earnings: Track earnings calendar
        """
        super().__init__(metadata)
        self.broker_api = broker_api
        self.include_earnings = include_earnings
        self._validate_stock_metadata()
    
    def _validate_stock_metadata(self) -> None:
        """Validate stock metadata."""
        if self.metadata.asset_class != AssetClass.STOCK:
            raise ValueError(f"Expected STOCK, got {self.metadata.asset_class}")
    
    async def get_current_price(self) -> PriceData:
        """Fetch current stock price.
        
        Returns:
            PriceData with current quote
        """
        try:
            if not self.broker_api:
                raise RuntimeError(f"Broker API not configured")
            
            quote = await self.broker_api.get_quote(self.symbol)
            
            price_data = PriceData(
                current_price=quote['last'],
                bid_price=quote.get('bid'),
                ask_price=quote.get('ask'),
                timestamp=datetime.utcnow(),
                source=DataSource.EXCHANGE_API
            )
            
            self.cache_price(price_data)
            return price_data
            
        except Exception as e:
            logger.error(f"Error fetching stock price {self.symbol}: {e}")
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
        """Fetch OHLCV for stock.
        
        Args:
            timeframe: Candle timeframe
            limit: Number of candles
            since: Start date
            
        Returns:
            List of OHLCV data
        """
        if timeframe not in self.STOCK_TIMEFRAMES:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        
        try:
            if not self.broker_api:
                raise RuntimeError("Broker API not configured")
            
            bars = await self.broker_api.get_bars(
                self.symbol,
                timeframe=timeframe,
                limit=limit,
                start=since
            )
            
            ohlcv_data = []
            for bar in bars:
                ohlcv = OHLCVData(
                    timestamp=bar['timestamp'],
                    open=float(bar['open']),
                    high=float(bar['high']),
                    low=float(bar['low']),
                    close=float(bar['close']),
                    volume=float(bar['volume'])
                )
                ohlcv_data.append(ohlcv)
            
            self.cache_ohlcv(ohlcv_data, timeframe)
            return ohlcv_data
            
        except Exception as e:
            logger.error(f"Error fetching stock OHLCV {self.symbol}: {e}")
            cached = self.get_cached_ohlcv(timeframe)
            if cached:
                return cached
            raise
    
    async def calculate_technical_indicators(
        self,
        ohlcv_data: List[OHLCVData]
    ) -> TechnicalIndicators:
        """Calculate stock-specific technical indicators.
        
        Args:
            ohlcv_data: OHLCV candles
            
        Returns:
            TechnicalIndicators
        """
        if len(ohlcv_data) < 20:
            raise ValueError(f"Need 20+ candles, got {len(ohlcv_data)}")
        
        closes = [c.close for c in ohlcv_data]
        
        indicators = TechnicalIndicators(
            rsi=self._calculate_rsi(closes),
            macd=self._calculate_macd(closes),
            sma_20=self._calculate_sma(closes, 20),
            sma_50=self._calculate_sma(closes, 50),
            sma_200=self._calculate_sma(closes, 200),
            ema_12=self._calculate_ema(closes, 12),
            ema_26=self._calculate_ema(closes, 26),
            atr=self._calculate_atr(ohlcv_data),
            adx=self._calculate_adx(ohlcv_data),
            timestamp=datetime.utcnow()
        )
        
        return indicators
    
    async def get_market_sentiment(self) -> MarketSentiment:
        """Determine stock market sentiment.
        
        Returns:
            MarketSentiment
        """
        try:
            ohlcv = await self.get_ohlcv_data("1d", limit=20)
            if not ohlcv:
                return MarketSentiment.NEUTRAL
            
            # Calculate RSI-based sentiment
            closes = [c.close for c in ohlcv]
            rsi = self._calculate_rsi(closes)
            
            if rsi and rsi > 70:
                return MarketSentiment.VERY_BULLISH
            elif rsi and rsi > 55:
                return MarketSentiment.BULLISH
            elif rsi and rsi < 30:
                return MarketSentiment.VERY_BEARISH
            elif rsi and rsi < 45:
                return MarketSentiment.BEARISH
            else:
                return MarketSentiment.NEUTRAL
                
        except Exception as e:
            logger.error(f"Error stock sentiment {self.symbol}: {e}")
            return MarketSentiment.NEUTRAL
    
    async def validate_trading_pair(self, pair: str) -> bool:
        """Validate stock symbol.
        
        Args:
            pair: Stock symbol
            
        Returns:
            True if valid
        """
        try:
            if not self.broker_api:
                return True
            
            assets = await self.broker_api.get_assets()
            return pair in assets
            
        except Exception as e:
            logger.error(f"Error validating stock {pair}: {e}")
            return False
    
    async def get_balance(self, exchange_key: Optional[str] = None) -> float:
        """Get portfolio balance in account currency.
        
        Args:
            exchange_key: API key identifier
            
        Returns:
            Account balance
        """
        try:
            if not self.broker_api:
                raise RuntimeError("Broker API not configured")
            
            account = await self.broker_api.get_account()
            return float(account.get('buying_power', 0))
            
        except Exception as e:
            logger.error(f"Error fetching account balance: {e}")
            return 0.0
    
    # Helper methods for technical analysis
    def _calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        if len(prices) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = sum(prices[-period:]) / period
        for price in prices[-period:]:
            ema = price * multiplier + ema * (1 - multiplier)
        return ema
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
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
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: List[float]) -> Optional[float]:
        ema12 = self._calculate_ema(prices, 12)
        ema26 = self._calculate_ema(prices, 26)
        if ema12 is None or ema26 is None:
            return None
        return ema12 - ema26
    
    def _calculate_atr(self, ohlcv_data: List[OHLCVData], period: int = 14) -> Optional[float]:
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
    
    def _calculate_adx(self, ohlcv_data: List[OHLCVData], period: int = 14) -> Optional[float]:
        """Average Directional Index (simplified)."""
        if len(ohlcv_data) < period:
            return None
        # Placeholder: real ADX requires complex DI calculations
        return None
