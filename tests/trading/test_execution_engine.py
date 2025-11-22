"""
Execution Engine Test Suite
Comprehensive tests for trading execution functionality

Author: v0-strategy-engine-pro
License: MIT
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from trading.execution_engine import (
    ExecutionEngine,
    TradingSignal,
    SignalAction,
)
from trading.execution_models import (
    ExecutionOrder,
    ExecutionStatus,
    ExecutionMode,
)
from trading.order_manager import OrderManager
from trading.position_tracker import PositionTracker
from trading.risk_guard import RiskGuard
from trading.order_monitor import OrderMonitor


class MockExchange:
    """Mock exchange adapter for testing"""
    
    def __init__(self, name="binance"):
        self.name = name
        self.orders = {}
        self.next_order_id = 1000
    
    def get_exchange_name(self) -> str:
        return self.name
    
    async def place_order(self, order: ExecutionOrder) -> dict:
        order_id = f"TEST_{self.next_order_id}"
        self.next_order_id += 1
        self.orders[order_id] = {"id": order_id, "status": "acknowledged"}
        return {"id": order_id, "status": "success"}
    
    async def get_order(self, order_id: str, symbol: str):
        mock_order = Mock()
        mock_order.status = Mock()
        mock_order.status.value = "filled"
        mock_order.filled_amount = 0.01
        mock_order.filled_price = 50000.0
        mock_order.commission = 0.001
        return mock_order
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        return True


class TestExecutionEngine:
    @pytest.fixture
    def setup_engine(self):
        mock_exchange = MockExchange("binance")
        exchanges = {"binance": mock_exchange}
        
        engine = ExecutionEngine(
            exchanges=exchanges,
            order_manager=OrderManager(),
            position_tracker=PositionTracker(),
            risk_guard=RiskGuard(),
            order_monitor=OrderMonitor(),
            execution_mode=ExecutionMode.PAPER,
        )
        
        return engine, mock_exchange
    
    @pytest.mark.asyncio
    async def test_signal_validation(self, setup_engine):
        engine, _ = setup_engine
        
        valid_signal = TradingSignal(
            symbol="BTCUSDT",
            action=SignalAction.BUY,
            quantity=0.01,
        )
        assert engine._validate_signal(valid_signal)
        
        invalid_signal = TradingSignal(
            symbol="",
            action=SignalAction.BUY,
            quantity=0,
        )
        assert not engine._validate_signal(invalid_signal)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
