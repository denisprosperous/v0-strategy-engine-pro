"""Forex Asset Implementation - Phase 1

Forex-specific implementation for trading foreign exchange pairs.
Supports major FX brokers and data providers.
"""

import logging
from datetime import datetime
from typing import Optional, List

from assets.base_asset import BaseAsset, PriceData, DataSource
from database.schemas import (
    AssetClass, AssetMetadata, OHLCVData,
    TechnicalIndicators, MarketSentiment
)

logger = logging.getLogger(__name__)


class ForexAsset(BaseAsset):
    """Forex (Foreign Exchange) asset implementation.
    
    Handles forex pair trading with:
    - Real-time forex quotes
    - Major, minor, and exotic pair support
    - Pip-based calculations
    - Economic calendar integration
    - Central bank sentiment tracking
    """
    
    SUPPORTED_BROKERS = {
        "oanda": "OANDA",
        "fxcm": "FXCM",
        "ib": "Interactive Brokers",
        "saxo": "Saxo Bank",
        "ic_markets": "IC Markets",
        "pepperstone": "Pepperstone"
    }
    
    FOREX_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
    
    # Pip sizes for different pairs
    PIP_SIZES = {
        "EURUSD": 0.0001,
        "GBPUSD": 0.0001,
        "USDJPY": 0.01,
        "AUDUSD": 0.0001,
        "USDCAD": 0.0001,
        "NZDUSD": 0.0001,
        "USDCHF": 0.0001,
        "EURJPY": 0.01,
        "GBPJPY": 0.01,
        "EURCAD": 0.0001,
    }
    
    def __init__(
        self,
        metadata: AssetMetadata,
        broker_api: Optional[object] = None,
        use_economic_calendar: bool = True
    ):
        """Initialize ForexAsset.
        
        Args:
            metadata: Forex pair metadata
            broker_api: Broker API client
            use_economic_calendar: Include economic events in analysis
        """
        super().__init__(metadata)
        self.broker_api = broker_api
        self.use_economic_calendar = use_economic_calendar
        self.pip_size = self._get_pip_size()
    
    def _get_pip_size(self) -> float:
        """Get pip size for this forex pair."""
        pair = self.symbol.replace("/", "")
        return self.PIP_SIZES.get(pair, 0.0001)
    
    async def get_current_price(self) -> PriceData:
        """Fetch current forex quote.
        
        Returns:
            PriceData with bid/ask spreads
        """
        try:
            if not self.broker_api:
                raise RuntimeError(f"Broker API not configured for {self.symbol}")
            
            quote = await self.broker_api.get_quote(self.symbol)
            
            price_data = PriceData(
                current_price=(quote['bid'] + quote['ask']) / 2,
                bid_price=quote['bid'],
                ask_price=quote['ask'],
                timestamp=datetime.utcnow(),
                source=DataSource.EXCHANGE_API
            )
            
            # Calculate spread in pips
            spread_pips = (quote['ask'] - quote['bid']) / self.pip_size
            logger.debug(f"{self.symbol} spread: {spread_pips:.1f} pips")
            
            self.cache_price(price_data)
            return price_data
            
        except Exception as e:
            logger.error(f"Error fetching forex price {self.symbol}: {e}")
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
        """Fetch OHLCV for forex pair.
        
        Args:
            timeframe: Candle timeframe
            limit: Number of candles
            since: Start date
            
        Returns:
            List of OHLCV data
        """
        if timeframe not in self.FOREX_TIMEFRAMES:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        
        try:
            if not self.broker_api:
                raise RuntimeError("Broker API not configured")
            
            candles = await self.broker_api.get_candles(
                self.symbol,
                granularity=timeframe,
                count=limit,
                from_time=since
            )
            
            ohlcv_data = []
            for candle in candles:
                ohlcv = OHLCVData(
                    timestamp=candle['time'],
                    open=float(candle['open']),
                    high=float(candle['high']),
                    low=float(candle['low']),
                    close=float(candle['close']),
                    volume=float(candle.get('volume', 0))
                )
                ohlcv_data.append(ohlcv)
            
            self.cache_ohlcv(ohlcv_data, timeframe)
            return ohlcv_data
            
        except Exception as e:
            logger.error(f"Error fetching forex OHLCV {self.symbol}: {e}")
            cached = self.get_cached_ohlcv(timeframe)
            if cached:
                return cached
            raise
    
    async def calculate_technical_indicators(
        self,
        ohlcv_data: List[OHLCVData]
    ) -> TechnicalIndicators:
        """Calculate forex-specific technical indicators.
        
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
            timestamp=datetime.utcnow()
        )
        
        return indicators
    
    async def get_market_sentiment(self) -> MarketSentiment:
        """Determine forex market sentiment.
        
        Returns:
            MarketSentiment
        """
        try:
            ohlcv = await self.get_ohlcv_data("1d", limit=10)
            if not ohlcv:
                return MarketSentiment.NEUTRAL
            
            momentum = ((ohlcv[-1].close - ohlcv[0].close) / ohlcv[0].close) * 100
            
            if momentum > 2:
                return MarketSentiment.BULLISH
            elif momentum < -2:
                return MarketSentiment.BEARISH
            else:
                return MarketSentiment.NEUTRAL
                
        except Exception as e:
            logger.error(f"Error forex sentiment {self.symbol}: {e}")
            return MarketSentiment.NEUTRAL
    
    async def validate_trading_pair(self, pair: str) -> bool:
        """Validate forex pair is tradeable.
        
        Args:
            pair: Trading pair
            
        Returns:
            True if valid
        """
        try:
            if not self.broker_api:
                return True
            
            instruments = await self.broker_api.get_instruments()
            return pair in instruments
            
        except Exception as e:
            logger.error(f"Error validating forex pair {pair}: {e}")
            return False
    
    async def get_balance(self, exchange_key: Optional[str] = None) -> float:
        """Get account balance in quote currency.
        
        Args:
            exchange_key: API key identifier
            
        Returns:
            Account balance
        """
        try:
            if not self.broker_api:
                raise RuntimeError("Broker API not configured")
            
            account = await self.broker_api.get_account()
            return float(account.get('balance', 0))
            
        except Exception as e:
            logger.error(f"Error fetching forex balance: {e}")
            return 0.0
    
    def calculate_position_size(self, risk_amount: float, stop_loss_pips: float) -> float:
        """Calculate position size based on risk.
        
        Args:
            risk_amount: Amount willing to risk
            stop_loss_pips: Stop loss in pips
            
        Returns:
            Position size in units
        """
        pip_value = self.pip_size  # Base pip value
        position_size = risk_amount / (stop_loss_pips * pip_value)
        return position_size
    
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
