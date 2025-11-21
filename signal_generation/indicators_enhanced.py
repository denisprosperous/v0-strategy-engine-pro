"""Enhanced Technical Indicators for Signal Generation.

Fast, efficient indicator calculations optimized for:
- RSI (Relative Strength Index) - Oversold/Overbought detection
- EMA (Exponential Moving Averages) - Trend confirmation (20, 50, 200)
- Volume Analysis - Volume surge confirmation and averages
- ATR (Average True Range) - Volatility and stop loss sizing

Supports all asset classes: Crypto, Forex, Stocks

Author: Trading Bot v0
Version: 1.0
"""

import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """High-performance indicator calculations for trading signals."""
    
    def __init__(self):
        self.cache = {}  # Per-symbol indicator cache
    
    # ===================== RSI CALCULATION =====================
    
    def calculate_rsi(self, closes: np.ndarray, period: int = 14) -> float:
        """Calculate Relative Strength Index.
        
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        
        Args:
            closes: Array of closing prices
            period: RSI period (default 14)
            
        Returns:
            RSI value (0-100)
        """
        if len(closes) < period + 1:
            return 50.0  # Neutral if insufficient data
        
        # Calculate price changes
        deltas = np.diff(closes[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Calculate average gain/loss (SMA for initial)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    def calculate_rsi_smoothed(self, closes: np.ndarray, period: int = 14) -> float:
        """Calculate RSI using Wilder's smoothing (more accurate).
        
        Better for real-time trading as it uses EMA-like smoothing.
        """
        if len(closes) < period + 1:
            return 50.0
        
        # Initial values
        deltas = np.diff(closes[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # First average
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        # Wilder's smoothing (alpha = 1/period)
        alpha = 1.0 / period
        for i in range(period, len(gains)):
            avg_gain = avg_gain * (1 - alpha) + gains[i] * alpha
            avg_loss = avg_loss * (1 - alpha) + losses[i] * alpha
        
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    # ===================== EMA CALCULATION =====================
    
    def calculate_ema(self, closes: np.ndarray, period: int) -> float:
        """Calculate Exponential Moving Average.
        
        EMA = Close * multiplier + EMA(prev) * (1 - multiplier)
        multiplier = 2 / (period + 1)
        
        Args:
            closes: Array of closing prices
            period: EMA period
            
        Returns:
            Current EMA value
        """
        if len(closes) < period:
            return float(np.mean(closes))  # SMA if insufficient data
        
        multiplier = 2.0 / (period + 1)
        ema = float(closes[0])
        
        for close in closes[1:]:
            ema = close * multiplier + ema * (1 - multiplier)
        
        return ema
    
    def calculate_emas(self, closes: np.ndarray,
                       periods: list = [20, 50, 200]) -> dict:
        """Calculate multiple EMAs efficiently.
        
        Args:
            closes: Array of closing prices
            periods: List of EMA periods
            
        Returns:
            Dict {period: ema_value}
        """
        emas = {}
        for period in periods:
            emas[period] = self.calculate_ema(closes, period)
        return emas
    
    def calculate_ema_series(self, closes: np.ndarray, period: int) -> np.ndarray:
        """Calculate full EMA series (all candles).
        
        Useful for visualization and trend analysis.
        """
        if len(closes) < period:
            return closes.copy()
        
        multiplier = 2.0 / (period + 1)
        ema_series = np.zeros(len(closes))
        ema_series[0] = closes[0]
        
        for i in range(1, len(closes)):
            ema_series[i] = closes[i] * multiplier + ema_series[i-1] * (1 - multiplier)
        
        return ema_series
    
    # ===================== VOLUME ANALYSIS =====================
    
    def calculate_volume_ratio(self, volumes: np.ndarray, period: int = 20) -> float:
        """Calculate current volume as ratio to average.
        
        Returns: current_volume / avg_volume
        
        Args:
            volumes: Array of volume values
            period: Period for average (default 20)
            
        Returns:
            Volume ratio (e.g., 1.5 = 50% above average)
        """
        if len(volumes) < period:
            avg_vol = np.mean(volumes)
        else:
            avg_vol = np.mean(volumes[-period:])
        
        if avg_vol == 0:
            return 1.0
        
        current_vol = volumes[-1]
        ratio = current_vol / avg_vol
        
        return float(ratio)
    
    def calculate_volume_avg(self, volumes: np.ndarray, period: int = 20) -> float:
        """Calculate average volume over period.
        
        Args:
            volumes: Array of volume values
            period: Period for average
            
        Returns:
            Average volume
        """
        if len(volumes) < period:
            return float(np.mean(volumes))
        return float(np.mean(volumes[-period:]))
    
    def is_volume_spike(self, volumes: np.ndarray, threshold: float = 1.5) -> bool:
        """Check if current volume is above threshold.
        
        Args:
            volumes: Array of volume values
            threshold: Spike threshold (default 1.5x)
            
        Returns:
            True if current volume > threshold * avg
        """
        ratio = self.calculate_volume_ratio(volumes, period=20)
        return ratio >= threshold
    
    # ===================== ATR CALCULATION =====================
    
    def calculate_atr(self, highs: np.ndarray, lows: np.ndarray,
                     closes: np.ndarray, period: int = 14) -> float:
        """Calculate Average True Range for volatility.
        
        TR = max(H-L, |H-C_prev|, |L-C_prev|)
        ATR = SMA(TR, period)
        
        Args:
            highs: Array of high prices
            lows: Array of low prices
            closes: Array of close prices
            period: ATR period (default 14)
            
        Returns:
            Current ATR value
        """
        if len(highs) < period:
            return float(np.mean(highs - lows))
        
        # Calculate True Range
        tr = np.zeros(len(highs))
        tr[0] = highs[0] - lows[0]
        
        for i in range(1, len(highs)):
            h_l = highs[i] - lows[i]
            h_c = abs(highs[i] - closes[i-1])
            l_c = abs(lows[i] - closes[i-1])
            tr[i] = max(h_l, h_c, l_c)
        
        # Calculate ATR (SMA of TR)
        atr = float(np.mean(tr[-period:]))
        return atr
    
    def calculate_atr_smoothed(self, highs: np.ndarray, lows: np.ndarray,
                              closes: np.ndarray, period: int = 14) -> float:
        """Calculate ATR using Wilder's smoothing (more accurate)."""
        if len(highs) < period:
            return float(np.mean(highs - lows))
        
        # Calculate True Range
        tr = np.zeros(len(highs))
        tr[0] = highs[0] - lows[0]
        
        for i in range(1, len(highs)):
            h_l = highs[i] - lows[i]
            h_c = abs(highs[i] - closes[i-1])
            l_c = abs(lows[i] - closes[i-1])
            tr[i] = max(h_l, h_c, l_c)
        
        # Wilder's smoothing
        atr = float(np.mean(tr[:period]))
        alpha = 1.0 / period
        for i in range(period, len(tr)):
            atr = atr * (1 - alpha) + tr[i] * alpha
        
        return atr
    
    # ===================== COMPOSITE CALCULATION =====================
    
    def calculate_all_indicators(self, ohlcv: np.ndarray) -> dict:
        """Calculate all required indicators in one efficient pass.
        
        Args:
            ohlcv: Array of [O, H, L, C, V] data
            
        Returns:
            Dict with all indicator values
        """
        opens = ohlcv[:, 0]
        highs = ohlcv[:, 1]
        lows = ohlcv[:, 2]
        closes = ohlcv[:, 3]
        volumes = ohlcv[:, 4]
        
        indicators = {
            'rsi': self.calculate_rsi_smoothed(closes, period=14),
            'ema_20': self.calculate_ema(closes, period=20),
            'ema_50': self.calculate_ema(closes, period=50),
            'ema_200': self.calculate_ema(closes, period=200),
            'atr': self.calculate_atr_smoothed(highs, lows, closes, period=14),
            'volume_ratio': self.calculate_volume_ratio(volumes, period=20),
            'volume_avg': self.calculate_volume_avg(volumes, period=20),
            'current_price': closes[-1],
            'current_volume': volumes[-1],
        }
        
        return indicators
    
    # ===================== VALIDATION & HELPERS =====================
    
    def validate_ema_alignment(self, ema_20: float, ema_50: float,
                              ema_200: float, direction: str = 'long') -> bool:
        """Validate EMA alignment for trend.
        
        Args:
            ema_20, ema_50, ema_200: EMA values
            direction: 'long' or 'short'
            
        Returns:
            True if EMAs properly aligned
        """
        if direction == 'long':
            return ema_20 > ema_50 > ema_200
        else:  # short
            return ema_20 < ema_50 < ema_200
    
    def is_rsi_oversold(self, rsi: float, threshold: int = 30) -> bool:
        """Check if RSI is oversold (for longs)."""
        return rsi < threshold
    
    def is_rsi_overbought(self, rsi: float, threshold: int = 70) -> bool:
        """Check if RSI is overbought (for shorts)."""
        return rsi > threshold
    
    def is_rsi_neutral(self, rsi: float) -> bool:
        """Check if RSI is neutral (no strong signal)."""
        return 40 <= rsi <= 60
    
    def clear_cache(self):
        """Clear indicator cache."""
        self.cache.clear()


# Singleton instance for module-level access
_calculator = IndicatorCalculator()


def calculate_rsi(closes: np.ndarray, period: int = 14) -> float:
    """Module-level RSI calculation."""
    return _calculator.calculate_rsi(closes, period)


def calculate_emas(closes: np.ndarray, periods: list = [20, 50, 200]) -> dict:
    """Module-level EMA calculation."""
    return _calculator.calculate_emas(closes, periods)


def calculate_volume_ratio(volumes: np.ndarray, period: int = 20) -> float:
    """Module-level volume ratio calculation."""
    return _calculator.calculate_volume_ratio(volumes, period)


def calculate_atr(highs: np.ndarray, lows: np.ndarray,
                 closes: np.ndarray, period: int = 14) -> float:
    """Module-level ATR calculation."""
    return _calculator.calculate_atr(highs, lows, closes, period)


def calculate_all_indicators(ohlcv: np.ndarray) -> dict:
    """Module-level composite indicator calculation."""
    return _calculator.calculate_all_indicators(ohlcv)
