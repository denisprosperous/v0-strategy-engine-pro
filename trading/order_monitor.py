"""
Order Monitor - Enhanced Order Monitoring & Performance Tracking
Real-time order status polling, slippage tracking, and execution metrics

Author: v0-strategy-engine-pro
License: MIT
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from collections import defaultdict
import json

from .execution_models import ExecutionOrder, ExecutionStatus, ExecutionMetrics


class OrderMonitor:
    """
    Enhanced order monitoring with performance analytics
    Tracks slippage, execution speed, and fill rates
    """
    
    def __init__(
        self,
        redis_conn=None,
        logger: Optional[logging.Logger] = None
    ):
        self.redis = redis_conn
        self.logger = logger or logging.getLogger(__name__)
        
        # Monitoring state
        self.active_monitors: Dict[str, asyncio.Task] = {}
        self.order_metrics: Dict[str, Dict] = {}
        
        # Performance tracking
        self.execution_metrics = ExecutionMetrics()
        self.slippage_history: List[float] = []
        self.latency_history: List[float] = []
        
        # Exchange status mappings
        self.status_mappings = self._initialize_status_mappings()
    
    def _initialize_status_mappings(self) -> Dict[str, Dict[str, ExecutionStatus]]:
        """
        Initialize exchange-specific status mappings
        Different exchanges use different status strings
        """
        return {
            "binance": {
                "NEW": ExecutionStatus.ACKNOWLEDGED,
                "PARTIALLY_FILLED": ExecutionStatus.PARTIALLY_FILLED,
                "FILLED": ExecutionStatus.FULLY_FILLED,
                "CANCELED": ExecutionStatus.CANCELLED,
                "PENDING_CANCEL": ExecutionStatus.CANCELLATION_PENDING,
                "REJECTED": ExecutionStatus.REJECTED,
                "EXPIRED": ExecutionStatus.EXPIRED,
            },
            "bybit": {
                "Created": ExecutionStatus.ACKNOWLEDGED,
                "New": ExecutionStatus.ACKNOWLEDGED,
                "PartiallyFilled": ExecutionStatus.PARTIALLY_FILLED,
                "Filled": ExecutionStatus.FULLY_FILLED,
                "Cancelled": ExecutionStatus.CANCELLED,
                "Rejected": ExecutionStatus.REJECTED,
            },
            "okx": {
                "live": ExecutionStatus.ACKNOWLEDGED,
                "partially_filled": ExecutionStatus.PARTIALLY_FILLED,
                "filled": ExecutionStatus.FULLY_FILLED,
                "canceled": ExecutionStatus.CANCELLED,
            },
            "kucoin": {
                "active": ExecutionStatus.ACKNOWLEDGED,
                "done": ExecutionStatus.FULLY_FILLED,
            },
            # Add more exchanges as needed
        }
    
    def map_exchange_status(
        self,
        exchange_name: str,
        raw_status: str
    ) -> ExecutionStatus:
        """
        Map exchange-specific status to unified ExecutionStatus
        
        Args:
            exchange_name: Name of the exchange (e.g., "binance")
            raw_status: Raw status string from exchange
            
        Returns:
            Unified ExecutionStatus enum
        """
        exchange_map = self.status_mappings.get(
            exchange_name.lower(),
            {}
        )
        
        # Try direct mapping
        mapped_status = exchange_map.get(raw_status)
        if mapped_status:
            return mapped_status
        
        # Fallback to fuzzy matching
        raw_lower = raw_status.lower()
        if "fill" in raw_lower and "partial" in raw_lower:
            return ExecutionStatus.PARTIALLY_FILLED
        elif "fill" in raw_lower:
            return ExecutionStatus.FULLY_FILLED
        elif "cancel" in raw_lower:
            return ExecutionStatus.CANCELLED
        elif "reject" in raw_lower:
            return ExecutionStatus.REJECTED
        elif "expire" in raw_lower:
            return ExecutionStatus.EXPIRED
        
        # Default to acknowledged if unknown
        self.logger.warning(
            f"Unknown status '{raw_status}' for {exchange_name}, "
            f"defaulting to ACKNOWLEDGED"
        )
        return ExecutionStatus.ACKNOWLEDGED
    
    async def monitor_order(
        self,
        order: ExecutionOrder,
        exchange,
        timeout_seconds: int = 300,
        max_polls: int = 1000
    ) -> ExecutionOrder:
        """
        Monitor order with exponential backoff polling
        
        Args:
            order: Order to monitor
            exchange: Exchange adapter instance
            timeout_seconds: Maximum monitoring duration
            max_polls: Maximum number of status checks
            
        Returns:
            Updated ExecutionOrder with final status
        """
        start_time = datetime.utcnow()
        poll_count = 0
        initial_backoff = 0.5  # Start with 500ms
        max_backoff = 5.0  # Cap at 5 seconds
        current_backoff = initial_backoff
        
        # Track order start metrics
        order_start_metrics = {
            "start_time": start_time,
            "expected_price": order.price,
            "polls": 0,
        }
        
        try:
            while poll_count < max_polls:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                
                # Check timeout
                if elapsed > timeout_seconds:
                    self.logger.warning(
                        f"Order {order.order_id} timed out after {elapsed:.2f}s"
                    )
                    order.status = ExecutionStatus.EXPIRED
                    self._record_timeout(order, elapsed)
                    break
                
                # Fetch order status from exchange
                try:
                    exchange_order = await exchange.get_order(
                        order.order_id,
                        order.symbol
                    )
                    
                    # Map exchange status to unified status
                    previous_status = order.status
                    order.status = self.map_exchange_status(
                        exchange.get_exchange_name(),
                        exchange_order.status.value
                    )
                    
                    # Update fill information
                    previous_filled = order.filled_quantity
                    order.filled_quantity = exchange_order.filled_amount
                    order.average_filled_price = exchange_order.filled_price
                    order.total_commission = exchange_order.commission
                    
                    # Check for status changes
                    if order.status != previous_status:
                        self.logger.info(
                            f"Order {order.order_id} status: "
                            f"{previous_status.value} -> {order.status.value}"
                        )
                    
                    # Calculate slippage on fill
                    if order.filled_quantity > previous_filled:
                        slippage = self.calculate_slippage(order)
                        self.slippage_history.append(slippage)
                        self.logger.info(
                            f"Order {order.order_id} partial fill: "
                            f"{order.filled_quantity}/{order.quantity}, "
                            f"slippage: {slippage:.4f}%"
                        )
                    
                    # Check terminal states
                    if order.status in [
                        ExecutionStatus.FULLY_FILLED,
                        ExecutionStatus.CANCELLED,
                        ExecutionStatus.REJECTED,
                        ExecutionStatus.EXPIRED
                    ]:
                        order.filled_at = datetime.utcnow()
                        execution_time = (order.filled_at - start_time).total_seconds()
                        
                        # Record execution metrics
                        self._record_execution(order, execution_time)
                        
                        self.logger.info(
                            f"Order {order.order_id} completed: "
                            f"{order.status.value} in {execution_time:.2f}s"
                        )
                        break
                    
                    # Dynamic backoff based on status
                    if order.status == ExecutionStatus.PARTIALLY_FILLED:
                        # Poll faster during active fills
                        current_backoff = max(initial_backoff, current_backoff * 0.8)
                    else:
                        # Exponential backoff for pending orders
                        current_backoff = min(max_backoff, current_backoff * 1.2)
                    
                except Exception as poll_error:
                    self.logger.error(
                        f"Poll error for {order.order_id}: {poll_error}"
                    )
                    # Use max backoff on errors
                    current_backoff = max_backoff
                
                # Wait before next poll
                await asyncio.sleep(current_backoff)
                poll_count += 1
                order_start_metrics["polls"] = poll_count
                
                # Cache updated order status
                if self.redis:
                    self._cache_order_status(order)
            
            # Max polls reached
            if poll_count >= max_polls:
                self.logger.warning(
                    f"Order {order.order_id} reached max polls ({max_polls})"
                )
        
        finally:
            # Clean up monitoring task
            if order.order_id in self.active_monitors:
                del self.active_monitors[order.order_id]
        
        return order
    
    def calculate_slippage(self, order: ExecutionOrder) -> float:
        """
        Calculate slippage percentage
        
        Slippage = (Actual Price - Expected Price) / Expected Price * 100
        For buys: positive slippage = paid more
        For sells: positive slippage = received less
        
        Args:
            order: Order with fill information
            
        Returns:
            Slippage percentage (positive = unfavorable)
        """
        if not order.average_filled_price or not order.price:
            return 0.0
        
        expected_price = order.price
        actual_price = order.average_filled_price
        
        if order.side.upper() == "BUY":
            # Paying more than expected is unfavorable
            slippage_pct = ((actual_price - expected_price) / expected_price) * 100
        else:  # SELL
            # Receiving less than expected is unfavorable
            slippage_pct = ((expected_price - actual_price) / expected_price) * 100
        
        return slippage_pct
    
    def get_execution_speed_metrics(self) -> Dict:
        """
        Get execution speed statistics
        
        Returns:
            Dictionary with latency metrics in milliseconds
        """
        if not self.latency_history:
            return {
                "avg_latency_ms": 0.0,
                "min_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
                "sample_size": 0,
            }
        
        sorted_latencies = sorted(self.latency_history)
        n = len(sorted_latencies)
        
        return {
            "avg_latency_ms": sum(sorted_latencies) / n * 1000,
            "min_latency_ms": sorted_latencies[0] * 1000,
            "max_latency_ms": sorted_latencies[-1] * 1000,
            "p50_latency_ms": sorted_latencies[int(n * 0.5)] * 1000,
            "p95_latency_ms": sorted_latencies[int(n * 0.95)] * 1000,
            "p99_latency_ms": sorted_latencies[int(n * 0.99)] * 1000,
            "sample_size": n,
        }
    
    def get_slippage_metrics(self) -> Dict:
        """
        Get slippage statistics
        
        Returns:
            Dictionary with slippage metrics in percentage
        """
        if not self.slippage_history:
            return {
                "avg_slippage_pct": 0.0,
                "min_slippage_pct": 0.0,
                "max_slippage_pct": 0.0,
                "positive_slippage_rate": 0.0,
                "sample_size": 0,
            }
        
        n = len(self.slippage_history)
        positive_count = sum(1 for s in self.slippage_history if s > 0)
        
        return {
            "avg_slippage_pct": sum(self.slippage_history) / n,
            "min_slippage_pct": min(self.slippage_history),
            "max_slippage_pct": max(self.slippage_history),
            "positive_slippage_rate": (positive_count / n) * 100,
            "sample_size": n,
        }
    
    def _record_execution(self, order: ExecutionOrder, execution_time: float):
        """Record execution metrics"""
        self.execution_metrics.total_orders += 1
        
        if order.status == ExecutionStatus.FULLY_FILLED:
            self.execution_metrics.successful_orders += 1
            self.execution_metrics.total_quantity_executed += order.filled_quantity
            self.execution_metrics.total_commission_paid += order.total_commission
            
            # Track latency
            self.latency_history.append(execution_time)
            
            # Update average metrics
            n = self.execution_metrics.successful_orders
            self.execution_metrics.avg_fill_time = (
                (self.execution_metrics.avg_fill_time * (n - 1) + execution_time * 1000) / n
            )
        elif order.status == ExecutionStatus.CANCELLED:
            self.execution_metrics.cancelled_orders += 1
        else:
            self.execution_metrics.failed_orders += 1
    
    def _record_timeout(self, order: ExecutionOrder, elapsed: float):
        """Record timeout event"""
        self.execution_metrics.failed_orders += 1
        self.logger.warning(
            f"Order timeout: {order.order_id} after {elapsed:.2f}s"
        )
    
    def _cache_order_status(self, order: ExecutionOrder):
        """Cache order status in Redis"""
        if not self.redis:
            return
        
        try:
            key = f"order_status:{order.order_id}"
            self.redis.setex(
                key,
                300,  # 5 minute TTL
                json.dumps({
                    "status": order.status.value,
                    "filled": order.filled_quantity,
                    "avg_price": order.average_filled_price,
                    "updated_at": datetime.utcnow().isoformat(),
                }, default=str)
            )
        except Exception as e:
            self.logger.error(f"Cache error: {e}")
    
    def get_metrics_summary(self) -> Dict:
        """
        Get comprehensive metrics summary
        
        Returns:
            Dictionary with all performance metrics
        """
        return {
            "execution": self.execution_metrics.to_dict(),
            "slippage": self.get_slippage_metrics(),
            "speed": self.get_execution_speed_metrics(),
        }
    
    def reset_metrics(self):
        """Reset all tracking metrics"""
        self.execution_metrics = ExecutionMetrics()
        self.slippage_history.clear()
        self.latency_history.clear()
        self.logger.info("Metrics reset")
