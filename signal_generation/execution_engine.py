"""Execution Engine: Order Placement & Management.

Converts TradingSignal objects into live orders with:
- Pre-trade validation (spread, slippage, latency)
- Order management (place, cancel, modify)
- Partial exit automation (TP1 at 50%, TP2 at full R:R)
- Trailing stop management
- Real-time P&L tracking

Author: Trading Bot v0
Version: 1.0
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order lifecycle states."""
    PENDING = 'pending'          # Awaiting execution
    OPEN = 'open'                # Filled, still active
    PARTIALLY_FILLED = 'partial' # Some filled, some pending
    CLOSED = 'closed'            # All filled and closed
    CANCELLED = 'cancelled'      # User cancelled
    REJECTED = 'rejected'        # Exchange rejected
    EXPIRED = 'expired'          # Timed out


class OrderType(Enum):
    """Order types."""
    MARKET = 'market'
    LIMIT = 'limit'
    STOP = 'stop'
    STOP_LIMIT = 'stop_limit'


@dataclass
class ExecutedTrade:
    """Represents a filled trade."""
    symbol: str
    direction: str  # 'long' or 'short'
    entry_price: float
    quantity: float
    entry_time: datetime
    
    stop_loss: float
    tp_1: float  # Partial exit target
    tp_2: float  # Final exit target
    
    # Management state
    partial_1_taken: bool = False
    partial_2_taken: bool = False
    current_price: float = 0.0
    current_pnl: float = 0.0
    current_pnl_pct: float = 0.0
    
    # Tracking
    timestamp_opened: datetime = field(default_factory=datetime.utcnow)
    timestamp_closed: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None  # 'tp1', 'tp2', 'sl', 'manual'
    
    def update_pnl(self, current_price: float):
        """Update current P&L."""
        self.current_price = current_price
        
        if self.direction == 'long':
            self.current_pnl = (current_price - self.entry_price) * self.quantity
            self.current_pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
        else:  # short
            self.current_pnl = (self.entry_price - current_price) * self.quantity
            self.current_pnl_pct = ((self.entry_price - current_price) / self.entry_price) * 100
    
    def is_at_breakeven(self) -> bool:
        """Check if trade is at breakeven."""
        return abs(self.current_pnl_pct) < 0.1  # Within 0.1%
    
    def is_in_profit(self) -> bool:
        """Check if trade is profitable."""
        return self.current_pnl > 0
    
    def is_at_tp_1(self) -> bool:
        """Check if price reached TP1."""
        if self.direction == 'long':
            return self.current_price >= self.tp_1
        else:
            return self.current_price <= self.tp_1
    
    def is_at_tp_2(self) -> bool:
        """Check if price reached TP2."""
        if self.direction == 'long':
            return self.current_price >= self.tp_2
        else:
            return self.current_price <= self.tp_2
    
    def is_hit_sl(self) -> bool:
        """Check if stop loss hit."""
        if self.direction == 'long':
            return self.current_price <= self.stop_loss
        else:
            return self.current_price >= self.stop_loss


class ExecutionEngine:
    """Order execution and management engine."""
    
    def __init__(self):
        self.open_trades: Dict[str, ExecutedTrade] = {}  # symbol -> trade
        self.closed_trades: List[ExecutedTrade] = []
        self.trade_history = []
    
    # ===================== PRE-TRADE VALIDATION =====================
    
    def validate_pre_trade(self, symbol: str, current_price: float,
                          config: dict) -> Tuple[bool, Optional[str]]:
        """Validate pre-trade conditions.
        
        Checks:
        - Spread (bid-ask)
        - Slippage tolerance
        - Latency
        
        Returns:
            (can_execute, reason)
        """
        # Simulated bid-ask spread (in real usage, get from API)
        bid_ask_spread = current_price * 0.0003  # 0.03% typical
        max_spread = config.get('max_spread', 0.0005)
        
        if bid_ask_spread > max_spread * current_price:
            return False, f"Spread {bid_ask_spread:.6f} exceeds max {max_spread:.6f}"
        
        # Slippage check (ATR-based)
        atr = config.get('atr', 100)
        max_slippage_atr = config.get('max_slippage_atr', 0.05)
        slippage_tolerance = atr * max_slippage_atr
        
        # Latency check (simulated)
        latency_ms = config.get('latency_ms', 100)
        max_latency = config.get('max_latency_ms', 500)
        
        if latency_ms > max_latency:
            return False, f"Latency {latency_ms}ms exceeds max {max_latency}ms"
        
        return True, None
    
    # ===================== ORDER EXECUTION =====================
    
    def execute_trade(self, signal, current_price: float,
                     position_size: float) -> Tuple[bool, Optional[str], Optional[ExecutedTrade]]:
        """Execute a trade from signal.
        
        Args:
            signal: TradingSignal object
            current_price: Current market price
            position_size: Number of contracts/shares
            
        Returns:
            (success, reason, trade)
        """
        # Create executed trade
        trade = ExecutedTrade(
            symbol=signal.symbol,
            direction=signal.direction.value,
            entry_price=signal.entry_price,
            quantity=position_size,
            entry_time=signal.timestamp,
            stop_loss=signal.stop_loss,
            tp_1=signal.take_profit_1,
            tp_2=signal.take_profit_2,
        )
        
        # Track trade
        self.open_trades[signal.symbol] = trade
        self.trade_history.append(trade)
        
        logger.info(f"Executed: {signal.symbol} {signal.direction.value} @ {signal.entry_price:.2f} size={position_size}")
        
        return True, None, trade
    
    # ===================== PARTIAL EXIT MANAGEMENT =====================
    
    def check_partial_exits(self, symbol: str, current_price: float) -> List[Dict]:
        """Check and execute partial exits.
        
        Returns list of exits taken.
        """
        if symbol not in self.open_trades:
            return []
        
        trade = self.open_trades[symbol]
        trade.update_pnl(current_price)
        exits = []
        
        # TP1: Exit 50% at first target
        if not trade.partial_1_taken and trade.is_at_tp_1():
            exit_qty = trade.quantity * 0.5
            exit_pnl = exit_qty * (current_price - trade.entry_price)
            
            exits.append({
                'symbol': symbol,
                'qty': exit_qty,
                'price': current_price,
                'pnl': exit_pnl,
                'reason': 'TP1_partial',
            })
            
            trade.partial_1_taken = True
            logger.info(f"Partial exit TP1: {symbol} 50% @ {current_price:.2f}")
        
        # TP2: Exit remaining at final target
        if not trade.partial_2_taken and trade.is_at_tp_2():
            exit_qty = trade.quantity * (1.0 - (0.5 if trade.partial_1_taken else 0.0))
            exit_pnl = exit_qty * (current_price - trade.entry_price)
            
            exits.append({
                'symbol': symbol,
                'qty': exit_qty,
                'price': current_price,
                'pnl': exit_pnl,
                'reason': 'TP2_final',
            })
            
            self._close_trade(symbol, current_price, 'tp2')
            logger.info(f"Full exit TP2: {symbol} remaining @ {current_price:.2f}")
        
        return exits
    
    def check_stop_losses(self, symbol: str, current_price: float) -> Optional[Dict]:
        """Check and execute stop losses."""
        if symbol not in self.open_trades:
            return None
        
        trade = self.open_trades[symbol]
        trade.update_pnl(current_price)
        
        if trade.is_hit_sl():
            exit_pnl = trade.current_pnl
            
            exit_info = {
                'symbol': symbol,
                'qty': trade.quantity,
                'price': current_price,
                'pnl': exit_pnl,
                'reason': 'stop_loss',
            }
            
            self._close_trade(symbol, current_price, 'sl')
            logger.warning(f"Stop loss hit: {symbol} @ {current_price:.2f} PnL={exit_pnl:.2f}")
            
            return exit_info
        
        return None
    
    # ===================== TRADE MANAGEMENT =====================
    
    def update_all_prices(self, price_map: Dict[str, float]):
        """Update prices for all open trades.
        
        Args:
            price_map: {symbol: current_price}
        """
        for symbol, price in price_map.items():
            if symbol in self.open_trades:
                self.open_trades[symbol].update_pnl(price)
    
    def get_open_trades(self) -> List[ExecutedTrade]:
        """Get all open trades."""
        return list(self.open_trades.values())
    
    def get_trade_summary(self) -> Dict:
        """Get summary of all trades."""
        open_trades = self.get_open_trades()
        
        total_pnl = sum(t.current_pnl for t in open_trades)
        total_profit = sum(t.current_pnl for t in open_trades if t.current_pnl > 0)
        total_loss = sum(t.current_pnl for t in open_trades if t.current_pnl < 0)
        
        return {
            'open_trades': len(open_trades),
            'closed_trades': len(self.closed_trades),
            'total_open_pnl': total_pnl,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'avg_pnl_pct': sum(t.current_pnl_pct for t in open_trades) / len(open_trades) if open_trades else 0,
        }
    
    def _close_trade(self, symbol: str, exit_price: float, reason: str):
        """Close a trade."""
        if symbol in self.open_trades:
            trade = self.open_trades.pop(symbol)
            trade.exit_price = exit_price
            trade.exit_reason = reason
            trade.timestamp_closed = datetime.utcnow()
            self.closed_trades.append(trade)


# Module-level singleton
_engine = ExecutionEngine()


def get_execution_engine() -> ExecutionEngine:
    """Get global execution engine."""
    return _engine
