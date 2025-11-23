"""Unit tests for Smart Scheduler & Fail-Safe Logic (Run 6)

Covers:
- Rate limiting between trades (symbol-aware)
- Consecutive skip logic
- Order book depth check
- Network latency logging
- Scheduler state management

Author: v0-strategy-engine-pro
Version: 1.0
"""

import time
import pytest
from signal_generation.smart_scheduler import SmartScheduler

class TestSmartScheduler:
    def setup_method(self):
        self.scheduler = SmartScheduler(min_interval_sec=300, max_consecutive_skips=5)
        self.symbol = 'BTCUSDT'

    def test_rate_limiting(self):
        now = time.time()
        assert self.scheduler.can_execute(self.symbol, now)
        self.scheduler.record_execution(self.symbol, now)
        assert not self.scheduler.can_execute(self.symbol, now)
        # Fast-forward 301s
        future = now + 301
        assert self.scheduler.can_execute(self.symbol, future)

    def test_consecutive_skip_threshold(self):
        for _ in range(5):
            self.scheduler.record_skip(self.symbol)
        assert self.scheduler.should_skip(self.symbol)

    def test_record_execution_resets_skips(self):
        for _ in range(5):
            self.scheduler.record_skip(self.symbol)
        assert self.scheduler.should_skip(self.symbol)
        # Recording execution resets skip count
        self.scheduler.record_execution(self.symbol)
        assert not self.scheduler.should_skip(self.symbol)
        assert self.scheduler.consecutive_skips[self.symbol] == 0

    def test_order_book_depth_check_pass(self):
        order_book = {'bids': [(50000, 1)], 'asks': [(50100, 1)]}
        assert self.scheduler.check_order_book_depth(order_book, required_depth_pct=0.02)

    def test_order_book_depth_check_fail(self):
        order_book = {'bids': [(50000, 1)], 'asks': [(51000, 1)]}  # 2% spread
        assert not self.scheduler.check_order_book_depth(order_book, required_depth_pct=0.01)

    def test_latency_logging(self):
        def dummy_call(symbol=None):
            time.sleep(0.01)
        latency = self.scheduler.measure_latency(dummy_call, symbol=self.symbol)
        assert latency > 0
        assert self.scheduler.get_latency(self.symbol) == pytest.approx(latency, rel=0.1)

    def test_scheduler_state(self):
        now = time.time()
        self.scheduler.record_execution(self.symbol, now)
        self.scheduler.record_skip(self.symbol)
        state = self.scheduler.get_state(self.symbol)
        assert 'last_execution' in state
        assert 'consecutive_skips' in state
        assert 'latency_ms' in state
        assert 'next_execution_time' in state

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
