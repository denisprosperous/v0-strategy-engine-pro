"""Dynamic Fibonacci Strategy Engine

This module calculates dynamic Fibonacci retracement/extension levels adjusted for volatility, with a plug-in interface for combining multiple strategies when Fibonacci conditions are not met.

Features:
- ATR-volatility adjusted dynamic Fibonacci retracement levels
- Pluggable strategy container for alternative signal logic
- Traditional levels: 0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%
- Support for both long and short contexts

Author: v0-strategy-engine-pro
Version: 1.0
"""

import numpy as np
from typing import Dict, Optional, List, Callable


class DynamicFibonacciEngine:
    """Calculates and manages dynamic Fibonacci levels."""

    FIB_LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]

    def __init__(self, atr_period: int = 14, volatility_factor: float = 1.0):
        self.atr_period = atr_period
        self.volatility_factor = volatility_factor
        # List of (name, func) alternative strategies (return signal dict or None)
        self.alternative_strategies: List[Callable[..., Optional[dict]]] = []

    def calculate_atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> float:
        if len(highs) < self.atr_period:
            return float(np.mean(highs - lows))
        tr = np.zeros(len(highs))
        tr[0] = highs[0] - lows[0]
        for i in range(1, len(highs)):
            h_l = highs[i] - lows[i]
            h_c = abs(highs[i] - closes[i-1])
            l_c = abs(lows[i] - closes[i-1])
            tr[i] = max(h_l, h_c, l_c)
        atr = float(np.mean(tr[-self.atr_period:]))
        return atr

    def calculate_dynamic_levels(
        self,
        high: float,
        low: float,
        close: float,
        atr_value: float
    ) -> Dict[str, float]:
        """Calculates volatility-adjusted dynamic Fibonacci levels."""
        base_range = high - low
        volatility_range = base_range * (1 + (atr_value / close) * self.volatility_factor)
        levels = {
            'support_strong': high - (volatility_range * 0.618),
            'support_medium': high - (volatility_range * 0.382),
            'support_weak': high - (volatility_range * 0.236),
            'resistance_weak': high + (volatility_range * 0.236),
            'resistance_medium': high + (volatility_range * 0.382),
            'resistance_strong': high + (volatility_range * 0.618),
        }
        # Add all standard retracement levels (fine-grained API)
        for fib in self.FIB_LEVELS:
            levels[f"fibonacci_{int(fib*1000):03d}"] = high - volatility_range * fib
        return levels

    def get_signal(
        self,
        ohlc_slice: np.ndarray,
        direction: str = 'long'
    ) -> Optional[dict]:
        """
        Primary entry point for generating signals.
        Returns a dict or None.
        Attempts Fibonacci; if not triggered, tries subsequent alternative strategies.
        """
        highs = ohlc_slice[:, 1]
        lows = ohlc_slice[:, 2]
        closes = ohlc_slice[:, 3]
        high = float(np.max(highs))
        low = float(np.min(lows))
        close = float(closes[-1])
        atr = self.calculate_atr(highs, lows, closes)
        levels = self.calculate_dynamic_levels(high, low, close, atr)

        # Core Fibonacci logic—trigger if price is within 1% of a strong Fib level
        price = close
        fib_triggered = False
        for lv_name in ['support_strong','resistance_strong','support_medium','resistance_medium']:
            lv = levels[lv_name]
            if abs((price - lv) / price) < 0.01:
                fib_triggered = True
                break

        if fib_triggered:
            return {
                'strategy': 'dynamic_fibonacci',
                'fib_levels': levels,
                'current_price': price,
                'atr': atr,
                'triggered_level': lv_name,
                'confidence': 0.85,  # Placeholder—tie to validator/scorer in integration
            }
        # Try alternatives (in order of registration)
        for alt_fn in self.alternative_strategies:
            signal = alt_fn(ohlc_slice, direction=direction)
            if signal is not None:
                return {**signal, 'strategy': f'alternative:{alt_fn.__name__}'}
        # None triggered
        return None

    def register_alternative_strategy(self, strategy_fn: Callable[[np.ndarray,str],Optional[dict]]):
        """Register or append a fallback strategy handler."""
        self.alternative_strategies.append(strategy_fn)

# Example placeholder strategy

def mean_reversion_strategy(ohlc_slice: np.ndarray, direction: str = 'long') -> Optional[dict]:
    closes = ohlc_slice[:,3]
    mean = np.mean(closes[-20:])
    std = np.std(closes[-20:])
    price = closes[-1]
    if direction == 'long' and price < mean - 1.5 * std:
        return {
            'triggered_level': 'mean_reversion',
            'confidence': 0.65,
        }
    if direction == 'short' and price > mean + 1.5 * std:
        return {
            'triggered_level': 'mean_reversion',
            'confidence': 0.65,
        }
    return None

# Usage (in pipeline):
# fib_engine = DynamicFibonacciEngine()
# fib_engine.register_alternative_strategy(mean_reversion_strategy)
# signal = fib_engine.get_signal(your_ohlc_data)
