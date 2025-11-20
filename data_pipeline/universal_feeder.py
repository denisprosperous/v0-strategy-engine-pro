"""Universal Data Pipeline Feeder - Phase 1

Unified data fetching and management system supporting all asset classes
(Crypto, Forex, Stocks) with caching, error handling, and performance optimization.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from assets.base_asset import BaseAsset
from assets.crypto_asset import CryptoAsset
from assets.forex_asset import ForexAsset
from assets.stock_asset import StockAsset
from database.schemas import OHLCVData, AssetClass, AssetMetadata


logger = logging.getLogger(__name__)


class DataQuality(str, Enum):
    """Data quality levels."""
    EXCELLENT = "excellent"  # <1% missing data
    GOOD = "good"  # 1-5% missing
    ACCEPTABLE = "acceptable"  # 5-10% missing
    DEGRADED = "degraded"  # >10% missing


class UniversalDataFeeder:
    """Unified data pipeline for all asset classes.
    
    Manages OHLCV data fetching, caching, and synchronization
    across Crypto, Forex, and Stock assets.
    """
    
    def __init__(self, cache_ttl: int = 300):
        """Initialize data feeder.
        
        Args:
            cache_ttl: Cache time-to-live in seconds
        """
        self.cache_ttl = cache_ttl
        self._asset_cache: Dict[str, BaseAsset] = {}
        self._ohlcv_cache: Dict[str, Dict[str, Any]] = {}
        self._last_update: Dict[str, datetime] = {}
        self._quality_metrics: Dict[str, DataQuality] = {}
    
    def register_asset(self, symbol: str, asset: BaseAsset) -> None:
        """Register asset with feeder.
        
        Args:
            symbol: Asset symbol
            asset: Asset instance
        """
        self._asset_cache[symbol] = asset
        logger.info(f"Registered {asset.asset_class.value} asset: {symbol}")
    
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
        use_cache: bool = True
    ) -> List[OHLCVData]:
        """Fetch OHLCV data for any asset.
        
        Args:
            symbol: Asset symbol
            timeframe: Candle timeframe
            limit: Number of candles
            use_cache: Use cache if valid
            
        Returns:
            List of OHLCV candles
        """
        cache_key = f"{symbol}_{timeframe}"
        
        # Check cache
        if use_cache and self._is_cache_valid(cache_key):
            logger.debug(f"Using cached OHLCV for {symbol} {timeframe}")
            return self._ohlcv_cache[cache_key]['data']
        
        # Get asset
        asset = self._asset_cache.get(symbol)
        if not asset:
            raise ValueError(f"Asset not registered: {symbol}")
        
        try:
            # Fetch fresh data
            ohlcv_data = await asset.get_ohlcv_data(
                timeframe=timeframe,
                limit=limit
            )
            
            # Cache it
            self._cache_ohlcv(cache_key, ohlcv_data)
            
            # Update quality metrics
            self._update_quality(cache_key, ohlcv_data)
            
            return ohlcv_data
            
        except Exception as e:
            logger.error(f"Error fetching {symbol} {timeframe}: {e}")
            # Try cached version even if expired
            if cache_key in self._ohlcv_cache:
                logger.warning(f"Using expired cache for {symbol}")
                return self._ohlcv_cache[cache_key]['data']
            raise
    
    async def fetch_multi_timeframe(
        self,
        symbol: str,
        timeframes: List[str]
    ) -> Dict[str, List[OHLCVData]]:
        """Fetch OHLCV data for multiple timeframes.
        
        Args:
            symbol: Asset symbol
            timeframes: List of timeframes
            
        Returns:
            Dict mapping timeframe to OHLCV data
        """
        tasks = [
            self.fetch_ohlcv(symbol, tf)
            for tf in timeframes
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        output = {}
        for tf, result in zip(timeframes, results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching {symbol} {tf}: {result}")
            else:
                output[tf] = result
        
        return output
    
    async def fetch_current_price(self, symbol: str):
        """Fetch current price for asset.
        
        Args:
            symbol: Asset symbol
            
        Returns:
            PriceData with current price
        """
        asset = self._asset_cache.get(symbol)
        if not asset:
            raise ValueError(f"Asset not registered: {symbol}")
        
        return await asset.get_current_price()
    
    async def calculate_indicators(
        self,
        symbol: str,
        timeframe: str
    ):
        """Calculate technical indicators for asset.
        
        Args:
            symbol: Asset symbol
            timeframe: Timeframe for analysis
            
        Returns:
            TechnicalIndicators
        """
        asset = self._asset_cache.get(symbol)
        if not asset:
            raise ValueError(f"Asset not registered: {symbol}")
        
        ohlcv_data = await self.fetch_ohlcv(symbol, timeframe, limit=200)
        return await asset.calculate_technical_indicators(ohlcv_data)
    
    def get_data_quality(self, symbol: str) -> DataQuality:
        """Get data quality for symbol.
        
        Args:
            symbol: Asset symbol
            
        Returns:
            DataQuality level
        """
        return self._quality_metrics.get(symbol, DataQuality.ACCEPTABLE)
    
    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """Clear cache for symbol(s).
        
        Args:
            symbol: Optional symbol to clear, or None for all
        """
        if symbol:
            self._ohlcv_cache.pop(symbol, None)
            self._last_update.pop(symbol, None)
        else:
            self._ohlcv_cache.clear()
            self._last_update.clear()
        
        logger.info(f"Cache cleared for {symbol or 'all assets'}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Cache stats dict
        """
        return {
            "cached_assets": len(self._asset_cache),
            "cached_ohlcv": len(self._ohlcv_cache),
            "quality_levels": dict(self._quality_metrics)
        }
    
    # Private helper methods
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid.
        
        Args:
            cache_key: Cache key
            
        Returns:
            True if cache is valid
        """
        if cache_key not in self._last_update:
            return False
        
        age = datetime.utcnow() - self._last_update[cache_key]
        return age.total_seconds() < self.cache_ttl
    
    def _cache_ohlcv(self, cache_key: str, data: List[OHLCVData]) -> None:
        """Store OHLCV data in cache.
        
        Args:
            cache_key: Cache key
            data: OHLCV data
        """
        self._ohlcv_cache[cache_key] = {
            'data': data,
            'timestamp': datetime.utcnow(),
            'count': len(data)
        }
        self._last_update[cache_key] = datetime.utcnow()
    
    def _update_quality(self, cache_key: str, data: List[OHLCVData]) -> None:
        """Update data quality metrics.
        
        Args:
            cache_key: Cache key
            data: OHLCV data
        """
        if not data:
            self._quality_metrics[cache_key] = DataQuality.DEGRADED
            return
        
        # Simple quality check: ensure no duplicate timestamps
        timestamps = [c.timestamp for c in data]
        unique_count = len(set(timestamps))
        quality_ratio = unique_count / len(data)
        
        if quality_ratio > 0.99:
            quality = DataQuality.EXCELLENT
        elif quality_ratio > 0.95:
            quality = DataQuality.GOOD
        elif quality_ratio > 0.90:
            quality = DataQuality.ACCEPTABLE
        else:
            quality = DataQuality.DEGRADED
        
        self._quality_metrics[cache_key] = quality
