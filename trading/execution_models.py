"""\nExecution Models - Trading Engine Data Structures\nDefines order states, position tracking, and execution metrics\n\nAuthor: v0-strategy-engine-pro\nLicense: MIT\n"""\n\nfrom dataclasses import dataclass, field\nfrom datetime import datetime\nfrom enum import Enum\nfrom typing import Optional, Dict, List, Any\nimport uuid\n\n\nclass ExecutionMode(Enum):\n    """Trading execution mode"""\n    LIVE = "live"\n    PAPER = "paper"\n    DEMO = "demo"\n\n\nclass ExecutionStatus(Enum):\n    """Order execution status"""\n    QUEUED = "queued"\n    SUBMITTED = "submitted"\n    ACKNOWLEDGED = "acknowledged"\n    PARTIALLY_FILLED = "partially_filled"\n    FULLY_FILLED = "fully_filled"\n    CANCELLATION_PENDING = "cancellation_pending"\n    CANCELLED = "cancelled"\n    REJECTED = "rejected"\n    FAILED = "failed"\n    EXPIRED = "expired"


class PositionSide(Enum):
    """Position direction"""
    LONG = "long"
    SHORT = "short"


class OrderType(Enum):
    """Order type classification"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"
    BRACKET = "bracket"


@dataclass
class ExecutionOrder:
    """Enhanced order with execution tracking"""
    
    # Core order data
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Execution metadata
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    exchange: str = "binance"
    execution_mode: ExecutionMode = ExecutionMode.LIVE
    status: ExecutionStatus = ExecutionStatus.QUEUED
    
    # Tracking
    created_at: datetime = field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    
    # Fill information
    filled_quantity: float = 0.0
    average_filled_price: Optional[float] = None
    total_commission: float = 0.0
    
    # Risk management
    strategy_id: Optional[str] = None
    signal_id: Optional[str] = None
    parent_order_id: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "type": self.order_type,
            "quantity": self.quantity,
            "price": self.price,
            "stop_price": self.stop_price,
            "status": self.status.value,
            "filled": self.filled_quantity,
            "avg_price": self.average_filled_price,
            "commission": self.total_commission,
            "exchange": self.exchange,
            "created_at": self.created_at.isoformat(),
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
        }


@dataclass
class Position:
    """Active trading position"""
    
    symbol: str
    side: str
    quantity: float
    entry_price: float
    entry_time: datetime = field(default_factory=datetime.utcnow)
    
    # Current state
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    
    # Risk parameters
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    trailing_stop_pct: Optional[float] = None
    
    # Metadata
    exchange: str = "binance"
    orders: List[str] = field(default_factory=list)
    
    def calculate_pnl(self, current_price: float) -> tuple:
        """Calculate unrealized PnL"""
        self.current_price = current_price
        
        if self.side.upper() == "LONG":
            pnl = (current_price - self.entry_price) * self.quantity
        else:
            pnl = (self.entry_price - current_price) * self.quantity
        
        pnl_pct = (pnl / (self.entry_price * self.quantity)) * 100 if self.entry_price > 0 else 0
        
        self.unrealized_pnl = pnl
        self.unrealized_pnl_pct = pnl_pct
        
        return pnl, pnl_pct
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
            "stop_loss": self.stop_loss_price,
            "take_profit": self.take_profit_price,
            "entry_time": self.entry_time.isoformat(),
        }


@dataclass
class ExecutionMetrics:
    """Track execution performance and statistics"""
    
    total_orders: int = 0
    successful_orders: int = 0
    failed_orders: int = 0
    cancelled_orders: int = 0
    
    total_quantity_executed: float = 0.0
    total_commission_paid: float = 0.0
    
    # Timing metrics (milliseconds)
    avg_order_latency: float = 0.0
    avg_fill_time: float = 0.0
    
    # Slippage tracking
    total_slippage: float = 0.0
    avg_slippage_pct: float = 0.0
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            "total_orders": self.total_orders,
            "successful_orders": self.successful_orders,
            "failed_orders": self.failed_orders,
            "cancelled_orders": self.cancelled_orders,
            "success_rate": (self.successful_orders / self.total_orders * 100) if self.total_orders > 0 else 0,
            "total_quantity": self.total_quantity_executed,
            "total_commission": self.total_commission_paid,
            "avg_latency_ms": self.avg_order_latency,
            "avg_fill_time_ms": self.avg_fill_time,
            "total_slippage": self.total_slippage,
            "avg_slippage_pct": self.avg_slippage_pct,
            "created_at": self.created_at.isoformat(),
        }
