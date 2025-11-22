"""
Order Monitor Test Suite

Author: v0-strategy-engine-pro
License: MIT
"""

import pytest
from trading.order_monitor import OrderMonitor
from trading.execution_models import ExecutionOrder, ExecutionStatus


class TestOrderMonitor:
    @pytest.fixture
    def monitor(self):
        return OrderMonitor()
    
    def test_slippage_calculation(self, monitor):
        # Buy order - paying more is unfavorable
        buy_order = ExecutionOrder(
            symbol="BTCUSDT",
            side="BUY",
            order_type="LIMIT",
            quantity=0.01,
            price=50000.0,  # Expected
        )
        buy_order.average_filled_price = 50100.0  # Actual
        
        slippage = monitor.calculate_slippage(buy_order)
        assert slippage > 0  # Unfavorable slippage
        assert abs(slippage - 0.2) < 0.01  # ~0.2%
    
    def test_status_mapping(self, monitor):
        # Binance status mapping
        status = monitor.map_exchange_status("binance", "FILLED")
        assert status == ExecutionStatus.FULLY_FILLED
        
        # Bybit status mapping
        status = monitor.map_exchange_status("bybit", "PartiallyFilled")
        assert status == ExecutionStatus.PARTIALLY_FILLED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
