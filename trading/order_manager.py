"""
Order Manager - Complete Order Lifecycle Management
Handles: placement, monitoring, cancellation, tracking across all exchanges

Author: v0-strategy-engine-pro
License: MIT
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import json
from .execution_models import ExecutionOrder, ExecutionStatus


class OrderManager:
    """Manages complete order lifecycle across all exchanges"""
    
    def __init__(
        self,
        redis_conn=None,
        db_session=None,
        logger: Optional[logging.Logger] = None
    ):
        self.redis = redis_conn
        self.db = db_session
        self.logger = logger or logging.getLogger(__name__)
        
        # Order tracking
        self.orders: Dict[str, ExecutionOrder] = {}
        self.exchange_order_map: Dict[str, str] = {}
        
        # Monitoring
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.order_callbacks: Dict[str, List[Callable]] = {
            "on_filled": [],
            "on_partial_fill": [],
            "on_cancelled": [],
            "on_rejected": [],
            "on_timeout": [],
        }
    
    def validate_order(self, order: ExecutionOrder) -> bool:
        """Validate order before submission"""
        if not order.symbol or len(order.symbol) < 2:
            raise ValueError(f"Invalid symbol: {order.symbol}")
        
        if order.quantity <= 0:
            raise ValueError(f"Invalid quantity: {order.quantity}")
        
        if order.side.upper() not in ["BUY", "SELL"]:
            raise ValueError(f"Invalid side: {order.side}")
        
        if order.order_type.upper() == "LIMIT" and order.price is None:
            raise ValueError("Limit orders require a price")
        
        if order.order_type.upper() in ["STOP_LOSS", "TAKE_PROFIT"] and order.stop_price is None:
            raise ValueError(f"{order.order_type} orders require a stop_price")
        
        return True
    
    async def place_order(
        self,
        order: ExecutionOrder,
        exchange,
    ) -> Optional[ExecutionOrder]:
        """
        Place order on exchange with comprehensive error handling
        Returns: ExecutionOrder with exchange order_id or None if failed
        """
        try:
            # Validate order
            self.validate_order(order)
            
            # Update status
            order.status = ExecutionStatus.SUBMITTED
            order.submitted_at = datetime.utcnow()
            
            self.logger.info(
                f"Placing order: {order.symbol} {order.side} "
                f"{order.quantity} @ {order.price or 'MARKET'}"
            )
            
            # Submit to exchange
            response = await exchange.place_order(order)
            
            if response and response.get("id"):
                order.order_id = response["id"]
                order.status = ExecutionStatus.ACKNOWLEDGED
                
                # Track in memory
                self.orders[order.order_id] = order
                self.exchange_order_map[f"{exchange.get_exchange_name()}:{order.order_id}"] = order.order_id
                
                # Cache in Redis
                if self.redis:
                    self._cache_order(order)
                
                # Start monitoring
                if not order.order_type.upper() == "MARKET":
                    asyncio.create_task(
                        self._monitor_order(order, exchange)
                    )
                
                self.logger.info(f"Order {order.order_id} placed successfully")
                return order
            else:
                order.status = ExecutionStatus.REJECTED
                self.logger.error(f"Exchange rejected order: {response}")
                await self._emit_callback("on_rejected", order)
                return None
                
        except Exception as e:
            order.status = ExecutionStatus.FAILED
            self.logger.error(f"Order placement failed: {e}", exc_info=True)
            await self._emit_callback("on_rejected", order)
            return None
    
    async def _monitor_order(
        self,
        order: ExecutionOrder,
        exchange,
        timeout_seconds: int = 300
    ):
        """Monitor order status until filled or timeout"""
        start_time = datetime.utcnow()
        poll_count = 0
        
        while order.status not in [ExecutionStatus.FULLY_FILLED, ExecutionStatus.CANCELLED]:
            try:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > timeout_seconds:
                    self.logger.warning(f"Order {order.order_id} timeout")
                    await self.cancel_order(order, exchange)
                    await self._emit_callback("on_timeout", order)
                    break
                
                # Fetch order status
                exchange_order = await exchange.get_order(order.order_id, order.symbol)
                previous_filled = order.filled_quantity
                order.filled_quantity = exchange_order.filled_amount
                order.average_filled_price = exchange_order.filled_price
                order.total_commission = exchange_order.commission
                
                # Update status
                status_map = {
                    "pending": ExecutionStatus.QUEUED,
                    "open": ExecutionStatus.ACKNOWLEDGED,
                    "partially_filled": ExecutionStatus.PARTIALLY_FILLED,
                    "filled": ExecutionStatus.FULLY_FILLED,
                    "canceled": ExecutionStatus.CANCELLED,
                    "rejected": ExecutionStatus.REJECTED,
                }
                order.status = status_map.get(exchange_order.status.value, order.status)
                
                # Trigger callbacks
                if order.filled_quantity > previous_filled:
                    if order.status == ExecutionStatus.FULLY_FILLED:
                        order.filled_at = datetime.utcnow()
                        await self._emit_callback("on_filled", order)
                    else:
                        await self._emit_callback("on_partial_fill", order)
                
                # Cache update
                if self.redis:
                    self._cache_order(order)
                
                # Dynamic poll interval
                poll_interval = 1.0 if order.status in [
                    ExecutionStatus.ACKNOWLEDGED,
                    ExecutionStatus.PARTIALLY_FILLED
                ] else 5.0
                
                poll_count += 1
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                self.logger.error(f"Monitor error: {e}")
                await asyncio.sleep(2)
    
    async def cancel_order(
        self,
        order: ExecutionOrder,
        exchange
    ) -> bool:
        """Cancel order on exchange"""
        try:
            order.status = ExecutionStatus.CANCELLATION_PENDING
            success = await exchange.cancel_order(order.order_id, order.symbol)
            
            if success:
                order.status = ExecutionStatus.CANCELLED
                await self._emit_callback("on_cancelled", order)
                self.logger.info(f"Order {order.order_id} cancelled")
            
            if self.redis:
                self._cache_order(order)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Cancel error: {e}")
            return False
    
    def _cache_order(self, order: ExecutionOrder):
        """Cache order in Redis"""
        try:
            key = f"order:{order.order_id}"
            self.redis.setex(
                key,
                3600,
                json.dumps(order.to_dict(), default=str)
            )
        except Exception as e:
            self.logger.error(f"Cache error: {e}")
    
    async def _emit_callback(self, event: str, order: ExecutionOrder):
        """Trigger registered callbacks"""
        if event in self.order_callbacks:
            for callback in self.order_callbacks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(order)
                    else:
                        callback(order)
                except Exception as e:
                    self.logger.error(f"Callback error: {e}")
    
    def register_callback(self, event: str, callback: Callable):
        """Register callback for order events"""
        if event in self.order_callbacks:
            self.order_callbacks[event].append(callback)
    
    def get_order(self, order_id: str) -> Optional[ExecutionOrder]:
        """Retrieve order by ID"""
        return self.orders.get(order_id)
