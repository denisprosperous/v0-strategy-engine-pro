"""Unit tests for Dynamic Fibonacci Engine (Segment 4)

Covers:
- Volatility-adjusted dynamic level calculation
- Signal triggering for Fibonacci and alternate logic
- Plug-in/fallback mechanism for combining strategies

Author: v0-strategy-engine-pro
Version: 1.0
"""

import numpy as np
import pytest

from signal_generation.fibonacci_engine import (
    DynamicFibonacciEngine,
    mean_reversion_strategy
)

def gen_ohlc(num, base=50000, rng=1000, noise=1):
    arr = np.zeros((num, 5))
    # [open, high, low, close, volume]
    for i in range(num):
        o = base + np.random.uniform(-rng, rng)
        c = o + np.random.uniform(-noise, noise) * rng / 20
        h = max(o, c) + abs(np.random.uniform(0, rng/2))
        l = min(o, c) - abs(np.random.uniform(0, rng/2))
        arr[i] = [o, h, l, c, np.random.uniform(20, 200)]
    return arr

class TestDynamicFibonacciEngine:
    def setup_method(self):
        self.engine = DynamicFibonacciEngine()

    def test_dynamic_level_basic(self):
        ohlc = gen_ohlc(50)
        highs = ohlc[:, 1]
        lows = ohlc[:, 2]
        closes = ohlc[:, 3]
        high = float(np.max(highs))
        low = float(np.min(lows))
        close = float(closes[-1])
        atr = self.engine.calculate_atr(highs, lows, closes)
        levels = self.engine.calculate_dynamic_levels(high, low, close, atr)
        assert 'support_strong' in levels and 'resistance_strong' in levels
        assert isinstance(levels['support_strong'], float)
        assert abs(levels['fibonacci_500'] - (high - (high-low)*(0.5 + atr/close*self.engine.volatility_factor*0.5))) < 500

    def test_signal_triggers_on_fib(self):
        ohlc = gen_ohlc(60)
        highs = ohlc[:, 1]
        lows = ohlc[:, 2]
        closes = ohlc[:, 3]
        # Price right at a strong fib level (simulate)
        fib_engine = DynamicFibonacciEngine()
        close_price = (np.max(highs) - np.min(lows)) * (1 - 0.618) + np.max(highs)
        ohlc[-1, 3] = close_price
        signal = fib_engine.get_signal(ohlc)
        assert signal is not None
        assert signal['strategy'] == 'dynamic_fibonacci'
        assert signal['triggered_level'] in ['support_strong','resistance_strong','support_medium','resistance_medium']

    def test_signal_alt_strategy_fallback(self):
        ohlc = gen_ohlc(60)
        # Set price away from fib levels but below mean for mean reversion to kick in
        prices = ohlc[-20:, 3]
        mean = np.mean(prices)
        std = np.std(prices)
        ohlc[-1, 3] = mean - 2*std  # Trigger only mean reversion
        fib_engine = DynamicFibonacciEngine()
        fib_engine.register_alternative_strategy(mean_reversion_strategy)
        signal = fib_engine.get_signal(ohlc)
        assert signal is not None
        assert signal['strategy'].startswith('alternative:')
        assert signal['triggered_level'] == 'mean_reversion'

    def test_fallback_returns_none_if_all_fail(self):
        ohlc = gen_ohlc(60)
        # Set far from both fib and mean reversion triggers
        ohlc[-1, 3] = np.mean(ohlc[-20:,3])
        fib_engine = DynamicFibonacciEngine()
        fib_engine.register_alternative_strategy(mean_reversion_strategy)
        signal = fib_engine.get_signal(ohlc)
        assert signal is None

    def test_multiple_alternative_strategies(self):
        # Register two alternates and make 2nd return a signal
        def always_on_strategy(ohlc_slice, direction='long'):
            return {'triggered_level':'always','confidence':1.0}
        ohlc = gen_ohlc(60)
        fib_engine = DynamicFibonacciEngine()
        fib_engine.register_alternative_strategy(mean_reversion_strategy)
        fib_engine.register_alternative_strategy(always_on_strategy)
        signal = fib_engine.get_signal(ohlc)
        assert signal is not None
        assert signal['triggered_level']=='always'
        assert signal['confidence'] == 1.0

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
