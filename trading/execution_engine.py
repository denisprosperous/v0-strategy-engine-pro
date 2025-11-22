"""
Execution Engine - Core Trading Orchestrator
Manages complete trading lifecycle: signals → orders → positions → closure

Author: v0-strategy-engine-pro
License: MIT
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json

from .execution_models import (
    ExecutionOrder,
    ExecutionStatus,
    ExecutionMode,
    Position,
    PositionSide,
    OrderType,
)
from .order_manager import OrderManager
from .position_tracker import PositionTracker
from .risk_guard import RiskGuard
from .order_monitor import OrderMonitor


class SignalAction(Enum):
    """Trading signal actions"""
    BUY = "buy"
    SELL = "sell"
    CLOSE = "close"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"


class TradingSignal:
    """Trading signal data structure"""
    def __init__(
        self,
        symbol: str,
        action: SignalAction,
        quantity: float,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        strategy_id: Optional[str] = None,
        confidence: float = 0.0,
        metadata: Optional[Dict] = None,
    ):
        self.symbol = symbol
        self.action = action
        self.quantity = quantity
        self.price = price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.strategy_id = strategy_id
        self.confidence = confidence
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()


class ExecutionResult:
    """Result of an execution operation"""
    def __init__(
        self,
        success: bool,
        order: Optional[ExecutionOrder] = None,
        position: Optional[Position] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        self.success = success
        self.order = order
        self.position = position
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "order": self.order.to_dict() if self.order else None,
            "position": self.position.to_dict() if self.position else None,
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class ExecutionEngine:
    """
    Core trading orchestrator
    Coordinates: OrderManager, PositionTracker, RiskGuard, OrderMonitor
    """
    
    def __init__(
        self,
        exchanges: Dict,
        order_manager: OrderManager,
        position_tracker: PositionTracker,
        risk_guard: RiskGuard,
        order_monitor: OrderMonitor,
        execution_mode: ExecutionMode = ExecutionMode.PAPER,
        telegram_bot=None,
        redis_conn=None,
        db_session=None,
        logger: Optional[logging.Logger] = None,
    ):
        self.exchanges = exchanges
        self.order_manager = order_manager
        self.position_tracker = position_tracker
        self.risk_guard = risk_guard
        self.order_monitor = order_monitor
        self.execution_mode = execution_mode
        self.telegram_bot = telegram_bot
        self.redis = redis_conn
        self.db = db_session
        self.logger = logger or logging.getLogger(__name__)
        
        # State tracking
        self.is_running = False
        self.circuit_breaker_active = False
        self.pending_executions: List[asyncio.Task] = []
        
        # Performance tracking
        self.total_signals_processed = 0
        self.successful_executions = 0
        self.failed_executions = 0
        
        self.logger.info(
            f"ExecutionEngine initialized in {execution_mode.value.upper()} mode"
        )
    
    async def start(self):
        """Start the execution engine"""
        self.is_running = True
        self.logger.info("ExecutionEngine started")
        
        if self.telegram_bot:
            await self._send_telegram_alert(
                f"🚀 Trading Engine Started\nMode: {self.execution_mode.value.upper()}"
            )
    
    async def stop(self):
        """Stop the execution engine gracefully"""
        self.is_running = False
        self.logger.info("ExecutionEngine stopping...")
        
        # Wait for pending executions
        if self.pending_executions:
            self.logger.info(f"Waiting for {len(self.pending_executions)} pending executions...")
            await asyncio.gather(*self.pending_executions, return_exceptions=True)
        
        if self.telegram_bot:
            await self._send_telegram_alert(
                f"🛑 Trading Engine Stopped\nProcessed: {self.total_signals_processed} signals"
            )
    
    async def execute_signal(
        self,
        signal: TradingSignal,
        exchange_name: str = "binance"
    ) -> ExecutionResult:
        """
        Execute a trading signal
        
        Complete workflow:
        1. Validate signal
        2. Check circuit breaker
        3. Run risk checks
        4. Convert signal to order
        5. Place order
        6. Monitor execution
        7. Update position
        8. Send notifications
        
        Args:
            signal: Trading signal to execute
            exchange_name: Target exchange
            
        Returns:
            ExecutionResult with order and position details
        """
        self.total_signals_processed += 1
        
        try:
            # 1. Validate signal
            if not self._validate_signal(signal):
                return ExecutionResult(
                    success=False,
                    error="Invalid signal parameters"
                )
            
            # 2. Check circuit breaker
            if self.circuit_breaker_active:
                self.logger.warning("Circuit breaker active - rejecting signal")
                return ExecutionResult(
                    success=False,
                    error="Circuit breaker active"
                )
            
            # 3. Risk checks
            risk_check = await self.risk_guard.check_all_risks(
                symbol=signal.symbol,
                quantity=signal.quantity,
                price=signal.price
            )
            
            if not risk_check["passed"]:
                self.logger.warning(f"Risk check failed: {risk_check['violations']}")
                return ExecutionResult(
                    success=False,
                    error=f"Risk violation: {risk_check['violations']}",
                    metadata=risk_check
                )
            
            # 4. Convert signal to order
            order = self._signal_to_order(signal, exchange_name)
            
            # 5. Place order
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                return ExecutionResult(
                    success=False,
                    error=f"Exchange '{exchange_name}' not found"
                )
            
            placed_order = await self.order_manager.place_order(order, exchange)
            if not placed_order:
                self.failed_executions += 1
                return ExecutionResult(
                    success=False,
                    error="Order placement failed",
                    order=order
                )
            
            # 6. Monitor execution (for non-market orders)
            if order.order_type != OrderType.MARKET.value:
                monitored_order = await self.order_monitor.monitor_order(
                    placed_order,
                    exchange,
                    timeout_seconds=300
                )
            else:
                monitored_order = placed_order
            
            # 7. Update position
            position = None
            if monitored_order.status == ExecutionStatus.FULLY_FILLED:
                position = await self._update_position(monitored_order, signal)
                self.successful_executions += 1
            
            # 8. Send notification
            await self._notify_execution(monitored_order, position, signal)
            
            return ExecutionResult(
                success=True,
                order=monitored_order,
                position=position,
                metadata={
                    "signal_id": signal.strategy_id,
                    "confidence": signal.confidence,
                }
            )
        
        except Exception as e:
            self.logger.error(f"Execution error: {e}", exc_info=True)
            self.failed_executions += 1
            return ExecutionResult(
                success=False,
                error=str(e)
            )
    
    async def close_position(
        self,
        symbol: str,
        exchange_name: str = "binance",
        reason: str = "manual"
    ) -> ExecutionResult:
        """
        Close an open position
        
        Args:
            symbol: Trading pair symbol
            exchange_name: Exchange where position is open
            reason: Reason for closure (manual, stop_loss, take_profit, etc.)
            
        Returns:
            ExecutionResult with closure details
        """
        try:
            # Get position
            position = self.position_tracker.get_position(symbol)
            if not position:
                return ExecutionResult(
                    success=False,
                    error=f"No open position for {symbol}"
                )
            
            # Create closing order (opposite side)
            close_side = "SELL" if position.side.upper() == "LONG" else "BUY"
            
            closing_order = ExecutionOrder(
                symbol=symbol,
                side=close_side,
                order_type="MARKET",
                quantity=position.quantity,
                exchange=exchange_name,
                execution_mode=self.execution_mode,
                metadata={
                    "action": "close_position",
                    "reason": reason,
                }
            )
            
            # Place closing order
            exchange = self.exchanges.get(exchange_name)
            placed_order = await self.order_manager.place_order(closing_order, exchange)
            
            if not placed_order:
                return ExecutionResult(
                    success=False,
                    error="Failed to place closing order"
                )
            
            # Close position in tracker
            closed_position = await self.position_tracker.close_position(
                symbol,
                placed_order.average_filled_price or placed_order.price
            )
            
            # Notify
            await self._send_telegram_alert(
                f"✅ Position Closed\n"
                f"Symbol: {symbol}\n"
                f"Side: {position.side}\n"
                f"PnL: ${closed_position.unrealized_pnl:.2f}\n"
                f"Reason: {reason}"
            )
            
            return ExecutionResult(
                success=True,
                order=placed_order,
                position=closed_position
            )
        
        except Exception as e:
            self.logger.error(f"Close position error: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                error=str(e)
            )
    
    async def emergency_stop_all(self) -> Dict:
        """
        Emergency stop - Cancel all orders and close all positions
        
        Returns:
            Dictionary with results of all operations
        """
        self.logger.critical("EMERGENCY STOP TRIGGERED")
        self.circuit_breaker_active = True
        
        results = {
            "cancelled_orders": [],
            "closed_positions": [],
            "errors": [],
        }
        
        try:
            # Cancel all pending orders
            for order_id, order in self.order_manager.orders.items():
                if order.status in [
                    ExecutionStatus.SUBMITTED,
                    ExecutionStatus.ACKNOWLEDGED,
                    ExecutionStatus.PARTIALLY_FILLED
                ]:
                    try:
                        exchange = self.exchanges.get(order.exchange)
                        cancelled = await self.order_manager.cancel_order(order, exchange)
                        if cancelled:
                            results["cancelled_orders"].append(order_id)
                    except Exception as e:
                        results["errors"].append(f"Cancel {order_id}: {e}")
            
            # Close all open positions
            open_positions = self.position_tracker.get_all_positions()
            for symbol, position in open_positions.items():
                try:
                    result = await self.close_position(symbol, position.exchange, "emergency")
                    if result.success:
                        results["closed_positions"].append(symbol)
                    else:
                        results["errors"].append(f"Close {symbol}: {result.error}")
                except Exception as e:
                    results["errors"].append(f"Close {symbol}: {e}")
            
            # Notify
            await self._send_telegram_alert(
                f"🚨 EMERGENCY STOP EXECUTED\n"
                f"Cancelled Orders: {len(results['cancelled_orders'])}\n"
                f"Closed Positions: {len(results['closed_positions'])}\n"
                f"Errors: {len(results['errors'])}"
            )
        
        except Exception as e:
            self.logger.critical(f"Emergency stop error: {e}", exc_info=True)
            results["errors"].append(f"Critical error: {e}")
        
        return results
    
    def activate_circuit_breaker(self, reason: str = "manual"):
        """Activate circuit breaker to halt trading"""
        self.circuit_breaker_active = True
        self.logger.warning(f"Circuit breaker activated: {reason}")
    
    def deactivate_circuit_breaker(self):
        """Deactivate circuit breaker to resume trading"""
        self.circuit_breaker_active = False
        self.logger.info("Circuit breaker deactivated")
    
    def _validate_signal(self, signal: TradingSignal) -> bool:
        """Validate signal parameters"""
        if not signal.symbol:
            return False
        if signal.quantity <= 0:
            return False
        if signal.action not in SignalAction:
            return False
        return True
    
    def _signal_to_order(self, signal: TradingSignal, exchange: str) -> ExecutionOrder:
        """Convert trading signal to execution order"""
        # Determine order side
        if signal.action in [SignalAction.BUY]:
            side = "BUY"
        elif signal.action in [SignalAction.SELL, SignalAction.CLOSE, SignalAction.CLOSE_LONG]:
            side = "SELL"
        else:
            side = "BUY"  # Default
        
        # Determine order type
        order_type = "LIMIT" if signal.price else "MARKET"
        
        return ExecutionOrder(
            symbol=signal.symbol,
            side=side,
            order_type=order_type,
            quantity=signal.quantity,
            price=signal.price,
            stop_price=signal.stop_loss,
            exchange=exchange,
            execution_mode=self.execution_mode,
            strategy_id=signal.strategy_id,
            metadata=signal.metadata,
        )
    
    async def _update_position(self, order: ExecutionOrder, signal: TradingSignal) -> Position:
        """Update position after order fill"""
        position = await self.position_tracker.open_position(
            symbol=order.symbol,
            side=order.side,
            quantity=order.filled_quantity,
            entry_price=order.average_filled_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            exchange=order.exchange,
        )
        return position
    
    async def _notify_execution(self, order: ExecutionOrder, position: Optional[Position], signal: TradingSignal):
        """Send execution notification"""
        if not self.telegram_bot:
            return
        
        status_emoji = "✅" if order.status == ExecutionStatus.FULLY_FILLED else "⚠️"
        
        message = (
            f"{status_emoji} Order Executed\n"
            f"Symbol: {order.symbol}\n"
            f"Side: {order.side}\n"
            f"Quantity: {order.filled_quantity}\n"
            f"Price: ${order.average_filled_price:.4f}\n"
            f"Status: {order.status.value}\n"
            f"Strategy: {signal.strategy_id or 'N/A'}\n"
            f"Confidence: {signal.confidence:.2%}"
        )
        
        await self._send_telegram_alert(message)
    
    async def _send_telegram_alert(self, message: str):
        """Send Telegram notification"""
        if not self.telegram_bot:
            return
        
        try:
            await self.telegram_bot.send_message(message)
        except Exception as e:
            self.logger.error(f"Telegram error: {e}")
    
    def get_performance_metrics(self) -> Dict:
        """
        Get comprehensive performance metrics
        
        Returns:
            Dictionary with all engine metrics
        """
        return {
            "engine": {
                "mode": self.execution_mode.value,
                "is_running": self.is_running,
                "circuit_breaker_active": self.circuit_breaker_active,
                "total_signals": self.total_signals_processed,
                "successful_executions": self.successful_executions,
                "failed_executions": self.failed_executions,
                "success_rate": (
                    self.successful_executions / self.total_signals_processed * 100
                    if self.total_signals_processed > 0
                    else 0.0
                ),
            },
            "positions": self.position_tracker.get_portfolio_stats(),
            "risk": self.risk_guard.get_risk_status(),
            "monitoring": self.order_monitor.get_metrics_summary(),
        }
