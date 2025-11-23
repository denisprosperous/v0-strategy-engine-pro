"""Smart Scheduler & Fail-Safe Logic

This module provides intelligent scheduling and fail-safe protections for trading signal execution:
- Rate limiting (min 5min between trades, symbol-aware)
- Consecutive skip threshold (skip after 5+ failures on a symbol)
- Order book depth checking (optional hook)
- Network latency measurement for live execution

Author: v0-strategy-engine-pro
Version: 1.0
"""

import time
from typing import Dict, Optional
from collections import defaultdict


class SmartScheduler:
    def __init__(self, min_interval_sec: int = 300, max_consecutive_skips: int = 5):
        self.min_interval_sec = min_interval_sec
        self.max_consecutive_skips = max_consecutive_skips
        self.last_execution: Dict[str, float] = {}  # symbol -> last execution timestamp
        self.consecutive_skips: Dict[str, int] = defaultdict(int)
        self.latency_log: Dict[str, float] = defaultdict(float)  # symbol -> ms
    
    def can_execute(self, symbol: str, now: Optional[float] = None) -> bool:
        now = now or time.time()
        last_exec = self.last_execution.get(symbol, 0)
        return now - last_exec >= self.min_interval_sec

    def record_execution(self, symbol: str, now: Optional[float] = None):
        now = now or time.time()
        self.last_execution[symbol] = now
        self.consecutive_skips[symbol] = 0

    def record_skip(self, symbol: str):
        self.consecutive_skips[symbol] += 1

    def should_skip(self, symbol: str) -> bool:
        return self.consecutive_skips[symbol] >= self.max_consecutive_skips

    def check_order_book_depth(self, order_book: dict, required_depth_pct: float = 0.01) -> bool:
        # Dummy implementation for spot/futures. Real implementation should
        # check if the top X% of depth can fill the order size with slippage constraint
        bids = order_book.get('bids', [])
        asks = order_book.get('asks', [])
        if not bids or not asks:
            return False
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        spread = abs(best_ask - best_bid)
        return spread / best_ask < required_depth_pct

    def measure_latency(self, endpoint_fn, *args, **kwargs) -> float:
        """Measures API latency (ms) and stores in latency log."""
        symbol = kwargs.get('symbol', 'UNKNOWN')
        start = time.time()
        endpoint_fn(*args, **kwargs)
        end = time.time()
        latency_ms = (end - start) * 1000
        self.latency_log[symbol] = latency_ms
        return latency_ms

    def get_next_execution_time(self, symbol: str) -> float:
        last_exec = self.last_execution.get(symbol, 0)
        return last_exec + self.min_interval_sec

    def get_latency(self, symbol: str) -> float:
        return self.latency_log.get(symbol, 0.0)

    def get_state(self, symbol: str) -> dict:
        return {
            'last_execution': self.last_execution.get(symbol, 0),
            'consecutive_skips': self.consecutive_skips.get(symbol, 0),
            'latency_ms': self.latency_log.get(symbol, 0.0),
            'next_execution_time': self.get_next_execution_time(symbol)
        }

# Example usage
if __name__ == '__main__':
    scheduler = SmartScheduler(min_interval_sec=300, max_consecutive_skips=5)
    symbol = 'BTCUSDT'
    now = time.time()
    # Simulate execution
    assert scheduler.can_execute(symbol, now)
    scheduler.record_execution(symbol, now)
    assert not scheduler.can_execute(symbol, now)
    # Simulate skips
    for _ in range(5):
        scheduler.record_skip(symbol)
    assert scheduler.should_skip(symbol)
    # Check dummy order book
    order_book = {'bids': [(50000, 1)], 'asks': [(50010, 1)]}
    assert scheduler.check_order_book_depth(order_book)
