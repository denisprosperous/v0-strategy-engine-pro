"""Enhanced Fibonacci Analyzer with Dynamic Retracement and Swing Detection.

Implements modular Fibonacci strategy with:
- Fractal-based swing detection (configurable depth)
- Dynamic retracement level computation
- Per-symbol and per-timeframe caching
- Invalidation logic based on ATR multiples
- Tolerances for slippage and market noise

Author: Trading Bot v0
Version: 2.0
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class FibonacciLevel(Enum):
    """Fibonacci retracement levels."""
    LEVEL_236 = 0.236
    LEVEL_382 = 0.382
    LEVEL_500 = 0.500
    LEVEL_618 = 0.618  # Primary level (71-75% bounce rate)
    LEVEL_786 = 0.786


@dataclass
class Swing:
    """Represents a market swing (pivot high or low)."""
    swing_type: str  # 'high' or 'low'
    price: float
    candle_index: int
    timestamp: datetime
    atr: float  # ATR at time of swing
    confidence: float = 0.0  # 0.0-1.0 based on wick size and volume
    
    def is_valid(self, current_price: float, atr: float, invalidation_threshold: float = 0.5) -> bool:
        """Check if swing is still valid based on price movement.
        
        Invalidation occurs when price moves beyond swing by > threshold * ATR.
        """
        distance_from_swing = abs(current_price - self.price)
        invalidation_distance = invalidation_threshold * atr
        return distance_from_swing <= invalidation_distance


@dataclass
class FibonacciLevels:
    """Container for computed Fibonacci retracement levels."""
    symbol: str
    timeframe: str
    swing: Swing
    computed_at: datetime
    
    # Fibonacci levels
    level_236: float = 0.0
    level_382: float = 0.0
    level_500: float = 0.0
    level_618: float = 0.0  # Primary entry target
    level_786: float = 0.0
    
    # Metadata
    swing_range: float = 0.0
    validity: bool = True
    ttl_seconds: int = 3600  # Time-to-live for cached levels
    
    def get_levels_dict(self) -> Dict[str, float]:
        """Return all levels as a dictionary."""
        return {
            '0.236': self.level_236,
            '0.382': self.level_382,
            '0.500': self.level_500,
            '0.618': self.level_618,
            '0.786': self.level_786,
        }
    
    def is_expired(self) -> bool:
        """Check if levels have expired based on TTL."""
        age_seconds = (datetime.utcnow() - self.computed_at).total_seconds()
        return age_seconds > self.ttl_seconds
    
    def update_validity(self, current_price: float, atr: float) -> bool:
        """Update validity status based on current price and ATR."""
        self.validity = self.swing.is_valid(current_price, atr)
        return self.validity


class FibonacciAnalyzer:
    """Enhanced Fibonacci analyzer with dynamic retracement and swing detection."""
    
    def __init__(self, fractal_depth: int = 2):
        """Initialize analyzer.
        
        Args:
            fractal_depth: Number of candles on each side for fractal detection (typically 2)
        """
        self.fractal_depth = fractal_depth
        self.cache: Dict[str, Dict[str, FibonacciLevels]] = {}  # {symbol: {tf: levels}}
        self.swings: Dict[str, Dict[str, List[Swing]]] = {}  # {symbol: {tf: [swings]}}
        
    def detect_swings(self, symbol: str, timeframe: str, ohlcv: np.ndarray, 
                     atr_values: np.ndarray) -> Optional[Swing]:
        """Detect the most recent valid swing using fractal method.
        
        A fractal high: Close > fractal_depth candles on each side
        A fractal low: Close < fractal_depth candles on each side
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (1h, 4h, 1d, etc)
            ohlcv: OHLCV data as numpy array (N, 5) [O,H,L,C,V]
            atr_values: Computed ATR values matching ohlcv rows
            
        Returns:
            Most recent Swing or None if no valid swing detected
        """
        if len(ohlcv) < 2 * self.fractal_depth + 1:
            logger.warning(f"Insufficient data for {symbol} {timeframe}: {len(ohlcv)} candles")
            return None
        
        # Scan from oldest to newest to find most recent swing
        high_swings = []
        low_swings = []
        
        closes = ohlcv[:, 3]  # Close prices
        highs = ohlcv[:, 1]   # High prices
        lows = ohlcv[:, 2]    # Low prices
        
        for i in range(self.fractal_depth, len(closes) - self.fractal_depth):
            # Check for fractal high
            if highs[i] > max(highs[i-self.fractal_depth:i]) and \
               highs[i] > max(highs[i+1:i+self.fractal_depth+1]):
                high_swings.append(Swing(
                    swing_type='high',
                    price=highs[i],
                    candle_index=i,
                    timestamp=datetime.utcnow(),
                    atr=atr_values[i],
                    confidence=0.8
                ))
            
            # Check for fractal low
            if lows[i] < min(lows[i-self.fractal_depth:i]) and \
               lows[i] < min(lows[i+1:i+self.fractal_depth+1]):
                low_swings.append(Swing(
                    swing_type='low',
                    price=lows[i],
                    candle_index=i,
                    timestamp=datetime.utcnow(),
                    atr=atr_values[i],
                    confidence=0.8
                ))
        
        # Combine and get most recent
        all_swings = high_swings + low_swings
        if not all_swings:
            logger.debug(f"No swings detected for {symbol} {timeframe}")
            return None
        
        most_recent = max(all_swings, key=lambda s: s.candle_index)
        self._cache_swing(symbol, timeframe, most_recent)
        return most_recent
    
    def compute_fib_levels(self, symbol: str, timeframe: str, ohlcv: np.ndarray,
                          atr_values: np.ndarray, current_price: float,
                          tolerance_atr: float = 0.1) -> Optional[FibonacciLevels]:
        """Compute Fibonacci retracement levels for current price action.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            ohlcv: OHLCV data
            atr_values: ATR array
            current_price: Current market price
            tolerance_atr: Tolerance in ATR multiples for level width (0.1 = 10% of ATR)
            
        Returns:
            FibonacciLevels object or None
        """
        # Check cache first
        cache_key = f"{symbol}_{timeframe}"
        if cache_key in self.cache and not self.cache[cache_key].is_expired():
            cached = self.cache[cache_key]
            cached.update_validity(current_price, atr_values[-1])
            if cached.validity:
                return cached
        
        # Detect swing
        swing = self.detect_swings(symbol, timeframe, ohlcv, atr_values)
        if not swing:
            return None
        
        current_atr = atr_values[-1]
        
        # Determine if we're computing from high or low
        is_pullback_to_low = current_price < swing.price
        
        if is_pullback_to_low and swing.swing_type == 'high':
            # Pullback from high - compute retracement DOWN from swing high
            range_price = swing.price - current_price
            base_price = swing.price
            direction = -1  # Moving downward
        elif not is_pullback_to_low and swing.swing_type == 'low':
            # Bounce from low - compute retracement UP from swing low
            range_price = current_price - swing.price
            base_price = swing.price
            direction = 1  # Moving upward
        else:
            logger.debug(f"Swing type mismatch for {symbol}: swing={swing.swing_type}, pullback_to_low={is_pullback_to_low}")
            return None
        
        # Compute Fibonacci levels
        levels = FibonacciLevels(
            symbol=symbol,
            timeframe=timeframe,
            swing=swing,
            computed_at=datetime.utcnow(),
            swing_range=range_price
        )
        
        for level in FibonacciLevel:
            fib_price = base_price + (direction * range_price * level.value)
            setattr(levels, f'level_{int(level.value*1000)}', fib_price)
        
        levels.ttl_seconds = 3600  # 1 hour cache
        self._cache_levels(symbol, timeframe, levels)
        
        logger.info(f"Computed Fib levels for {symbol} {timeframe}: 61.8%={levels.level_618:.2f}")
        return levels
    
    def check_level_touch(self, price: float, fib_level: float, tolerance_atr: float,
                         current_atr: float) -> bool:
        """Check if price touches a Fibonacci level within tolerance.
        
        Args:
            price: Current price
            fib_level: Fibonacci level price
            tolerance_atr: Tolerance in ATR multiples
            current_atr: Current ATR value
            
        Returns:
            True if price is within tolerance of level
        """
        tolerance = tolerance_atr * current_atr
        return abs(price - fib_level) <= tolerance
    
    def get_primary_level(self, levels: FibonacciLevels) -> float:
        """Get the primary Fibonacci level (61.8%) - most reliable for entries."""
        return levels.level_618
    
    def _cache_levels(self, symbol: str, timeframe: str, levels: FibonacciLevels):
        """Cache Fibonacci levels."""
        if symbol not in self.cache:
            self.cache[symbol] = {}
        self.cache[f"{symbol}_{timeframe}"] = levels
    
    def _cache_swing(self, symbol: str, timeframe: str, swing: Swing):
        """Cache swing data."""
        if symbol not in self.swings:
            self.swings[symbol] = {}
        if timeframe not in self.swings[symbol]:
            self.swings[symbol][timeframe] = []
        # Keep only recent swings (last 10)
        self.swings[symbol][timeframe].append(swing)
        if len(self.swings[symbol][timeframe]) > 10:
            self.swings[symbol][timeframe].pop(0)
    
    def clear_cache(self, symbol: Optional[str] = None, timeframe: Optional[str] = None):
        """Clear cache entries."""
        if symbol and timeframe:
            key = f"{symbol}_{timeframe}"
            if key in self.cache:
                del self.cache[key]
        elif symbol:
            for key in list(self.cache.keys()):
                if key.startswith(f"{symbol}_"):
                    del self.cache[key]
        else:
            self.cache.clear()
            self.swings.clear()
