"""Integrated Execution Engine: Complete Signal-to-Trade Pipeline.

Orchestrates the complete signal generation and execution flow:
1. Fibonacci Engine → Detect signals from dynamic Fibonacci levels
2. Signal Validator → Multi-condition validation (technical, volume, etc.)
3. Smart Scheduler → Timing optimization and fail-safe logic
4. Signal Scorer → 5-component scoring system with execution tiers
5. Execution Engine → Order placement with partial exits and management

Author: v0-strategy-engine-pro
Version: 1.0 (Run #8)
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List, Any
from enum import Enum
from datetime import datetime
import logging
import numpy as np

# Import all signal generation modules
try:
    from signal_generation.fibonacci_engine import DynamicFibonacciEngine
    from signal_generation.signal_validator import SignalValidator, ValidationResult
    from signal_generation.smart_scheduler import SmartScheduler, ScheduleResult
    from signal_generation.signal_scorer import SignalScorer, SignalScore, ExecutionTier
except ImportError:
    # Fallback imports for testing
    from fibonacci_engine import DynamicFibonacciEngine
    from signal_validator import SignalValidator, ValidationResult
    from smart_scheduler import SmartScheduler, ScheduleResult
    from signal_scorer import SignalScorer, SignalScore, ExecutionTier

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order lifecycle states."""
    PENDING = 'pending'
    OPEN = 'open'
    PARTIALLY_FILLED = 'partial'
    CLOSED = 'closed'
    CANCELLED = 'cancelled'
    REJECTED = 'rejected'
    EXPIRED = 'expired'


class SignalDirection(Enum):
    """Signal direction."""
    LONG = 'long'
    SHORT = 'short'


@dataclass
 class TradingSignal:
    """Standardized trading signal format."""
    symbol: str
    direction: SignalDirection
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 0.0
    score: float = 0.0
    execution_tier: str = 'SKIP'
    

@dataclass
class ExecutedTrade:
    """Represents an executed trade with management state."""
    symbol: str
    direction: str
    entry_price: float
    quantity: float
    entry_time: datetime
    
    stop_loss: float
    tp_1: float
    tp_2: float
    
    # Management
    partial_1_taken: bool = False
    partial_2_taken: bool = False
    current_price: float = 0.0
    current_pnl: float = 0.0
    current_pnl_pct: float = 0.0
    
    # Tracking
    timestamp_opened: datetime = field(default_factory=datetime.utcnow)
    timestamp_closed: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    
    def update_pnl(self, current_price: float):
        """Update P&L based on current price."""
        self.current_price = current_price
        
        if self.direction == 'long':
            self.current_pnl = (current_price - self.entry_price) * self.quantity
            self.current_pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
        else:
            self.current_pnl = (self.entry_price - current_price) * self.quantity
            self.current_pnl_pct = ((self.entry_price - current_price) / self.entry_price) * 100
    
    def is_at_tp_1(self) -> bool:
        if self.direction == 'long':
            return self.current_price >= self.tp_1
        return self.current_price <= self.tp_1
    
    def is_at_tp_2(self) -> bool:
        if self.direction == 'long':
            return self.current_price >= self.tp_2
        return self.current_price <= self.tp_2
    
    def is_hit_sl(self) -> bool:
        if self.direction == 'long':
            return self.current_price <= self.stop_loss
        return self.current_price >= self.stop_loss


class IntegratedExecutionEngine:
    """Integrated execution engine with complete signal pipeline."""
    
    def __init__(self, 
                 base_position_size: float = 1000.0,
                 max_spread: float = 0.0005,
                 max_latency_ms: int = 500):
        """
        Initialize integrated execution engine.
        
        Args:
            base_position_size: Base position size (contracts/USD)
            max_spread: Maximum allowed bid-ask spread
            max_latency_ms: Maximum allowed latency in milliseconds
        """
        # Initialize all modules
        self.fibonacci_engine = DynamicFibonacciEngine(atr_period=14, volatility_factor=1.0)
        self.signal_validator = SignalValidator()
        self.smart_scheduler = SmartScheduler()
        self.signal_scorer = SignalScorer()
        
        # Trading parameters
        self.base_position_size = base_position_size
        self.max_spread = max_spread
        self.max_latency_ms = max_latency_ms
        
        # Trade management
        self.open_trades: Dict[str, ExecutedTrade] = {}
        self.closed_trades: List[ExecutedTrade] = []
        self.trade_history: List[Dict] = []
        
        logger.info("IntegratedExecutionEngine initialized with all modules")
    
    # ===================== PRE-FLIGHT VALIDATION =====================
    
    def pre_flight_check(self) -> Tuple[bool, List[str]]:
        """Validate all modules are operational.
        
        Returns:
            (all_ok, error_messages)
        """
        errors = []
        
        # Check Fibonacci Engine
        if self.fibonacci_engine is None:
            errors.append("Fibonacci Engine not initialized")
        
        # Check Signal Validator
        if self.signal_validator is None:
            errors.append("Signal Validator not initialized")
        
        # Check Smart Scheduler
        if self.smart_scheduler is None:
            errors.append("Smart Scheduler not initialized")
        
        # Check Signal Scorer
        if self.signal_scorer is None:
            errors.append("Signal Scorer not initialized")
        
        if errors:
            logger.error(f"Pre-flight check failed: {errors}")
            return False, errors
        
        logger.info("Pre-flight check passed: All modules operational")
        return True, []
    
    # ===================== SIGNAL GENERATION PIPELINE =====================
    
    def generate_signal(self, 
                       symbol: str,
                       ohlc_data: np.ndarray,
                       market_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """Complete signal generation pipeline.
        
        Pipeline Flow:
        1. Fibonacci Detection
        2. Signal Validation
        3. Timing Scheduling
        4. Signal Scoring
        5. Execution Decision
        
        Args:
            symbol: Trading symbol
            ohlc_data: OHLC array [timestamp, high, low, close, volume]
            market_data: Additional market context (RSI, EMA, ATR, etc.)
        
        Returns:
            TradingSignal or None
        """
        logger.info(f"Starting signal generation pipeline for {symbol}")
        
        # Step 1: Fibonacci Detection
        fib_signal = self.fibonacci_engine.get_signal(ohlc_data, direction='long')
        
        if fib_signal is None:
            logger.debug(f"{symbol}: No Fibonacci signal detected")
            return None
        
        logger.info(f"{symbol}: Fibonacci signal detected - {fib_signal.get('triggered_level')}")
        
        # Step 2: Signal Validation
        validation_result = self.signal_validator.validate_signal(
            signal_data=fib_signal,
            market_data=market_data
        )
        
        if not validation_result.is_valid:
            logger.info(f"{symbol}: Signal validation failed - {validation_result.failed_conditions}")
            return None
        
        logger.info(f"{symbol}: Signal validated - confidence={validation_result.confidence:.2f}")
        
        # Step 3: Timing Scheduling
        schedule_result = self.smart_scheduler.evaluate_timing(
            symbol=symbol,
            signal_data=fib_signal,
            market_conditions=market_data
        )
        
        if not schedule_result.should_execute:
            logger.info(f"{symbol}: Timing not optimal - {schedule_result.reason}")
            return None
        
        logger.info(f"{symbol}: Timing optimal - quality={schedule_result.timing_quality}")
        
        # Step 4: Signal Scoring
        current_price = float(ohlc_data[-1, 3])  # Last close
        
        signal_score = self.signal_scorer.score_signal(
            signal_type='LONG',
            entry_price=current_price,
            market_data=market_data,
            fib_levels=fib_signal.get('fib_levels', {})
        )
        
        logger.info(f"{symbol}: Signal scored - {signal_score.overall_score:.1f}/100 ({signal_score.confidence_level})")
        
        # Step 5: Execution Decision
        if signal_score.execution_tier == ExecutionTier.SKIP:
            logger.info(f"{symbol}: Score too low - SKIP execution (score={signal_score.overall_score:.1f})")
            return None
        
        # Calculate stop loss and take profits
        atr = market_data.get('atr', current_price * 0.02)
        stop_loss = current_price - (2.0 * atr)  # 2 ATR stop
        take_profit_1 = current_price + (1.5 * atr)  # 1.5:1 R:R for TP1
        take_profit_2 = current_price + (3.0 * atr)  # 3:1 R:R for TP2
        
        # Create trading signal
        trading_signal = TradingSignal(
            symbol=symbol,
            direction=SignalDirection.LONG,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            confidence=validation_result.confidence,
            score=signal_score.overall_score,
            execution_tier=signal_score.execution_tier.value
        )
        
        logger.info(f"{symbol}: Trading signal generated - {signal_score.execution_tier.value} tier")
        return trading_signal
    
    # ===================== TRADE EXECUTION =====================
    
    def execute_signal(self, signal: TradingSignal) -> Tuple[bool, Optional[str], Optional[ExecutedTrade]]:
        """Execute a trading signal.
        
        Args:
            signal: TradingSignal to execute
        
        Returns:
            (success, error_message, executed_trade)
        """
        # Determine position size based on execution tier
        if signal.execution_tier == 'FULL':
            position_size = self.base_position_size
        elif signal.execution_tier == 'REDUCED':
            position_size = self.base_position_size * 0.65
        else:
            return False, "Signal marked as SKIP", None
        
        # Pre-trade validation
        can_execute, reason = self._validate_pre_trade(
            symbol=signal.symbol,
            current_price=signal.entry_price
        )
        
        if not can_execute:
            logger.warning(f"{signal.symbol}: Pre-trade validation failed - {reason}")
            return False, reason, None
        
        # Create executed trade
        trade = ExecutedTrade(
            symbol=signal.symbol,
            direction=signal.direction.value,
            entry_price=signal.entry_price,
            quantity=position_size,
            entry_time=signal.timestamp,
            stop_loss=signal.stop_loss,
            tp_1=signal.take_profit_1,
            tp_2=signal.take_profit_2
        )
        
        # Track trade
        self.open_trades[signal.symbol] = trade
        self.trade_history.append({
            'action': 'open',
            'trade': trade,
            'timestamp': datetime.utcnow()
        })
        
        logger.info(f"Executed: {signal.symbol} {signal.direction.value} @ {signal.entry_price:.2f} size={position_size:.2f}")
        
        return True, None, trade
    
    def _validate_pre_trade(self, symbol: str, current_price: float) -> Tuple[bool, Optional[str]]:
        """Validate pre-trade conditions."""
        # Check spread
        bid_ask_spread = current_price * 0.0003  # Simulated 0.03%
        if bid_ask_spread > self.max_spread * current_price:
            return False, f"Spread {bid_ask_spread:.6f} exceeds max {self.max_spread:.6f}"
        
        # Check latency (simulated)
        latency_ms = 100
        if latency_ms > self.max_latency_ms:
            return False, f"Latency {latency_ms}ms exceeds max {self.max_latency_ms}ms"
        
        return True, None
    
    # ===================== TRADE MANAGEMENT =====================
    
    def update_trades(self, price_map: Dict[str, float]):
        """Update all open trades with current prices."""
        for symbol, price in price_map.items():
            if symbol in self.open_trades:
                trade = self.open_trades[symbol]
                trade.update_pnl(price)
                
                # Check partial exits
                self._check_partial_exits(symbol, price)
                
                # Check stop loss
                self._check_stop_loss(symbol, price)
    
    def _check_partial_exits(self, symbol: str, current_price: float):
        """Check and execute partial exits."""
        if symbol not in self.open_trades:
            return
        
        trade = self.open_trades[symbol]
        
        # TP1: 50% exit
        if not trade.partial_1_taken and trade.is_at_tp_1():
            trade.partial_1_taken = True
            logger.info(f"Partial exit TP1: {symbol} 50% @ {current_price:.2f}")
        
        # TP2: Final exit
        if not trade.partial_2_taken and trade.is_at_tp_2():
            self._close_trade(symbol, current_price, 'tp2')
            logger.info(f"Full exit TP2: {symbol} @ {current_price:.2f}")
    
    def _check_stop_loss(self, symbol: str, current_price: float):
        """Check and execute stop loss."""
        if symbol not in self.open_trades:
            return
        
        trade = self.open_trades[symbol]
        
        if trade.is_hit_sl():
            self._close_trade(symbol, current_price, 'sl')
            logger.warning(f"Stop loss hit: {symbol} @ {current_price:.2f}")
    
    def _close_trade(self, symbol: str, exit_price: float, reason: str):
        """Close a trade."""
        if symbol in self.open_trades:
            trade = self.open_trades.pop(symbol)
            trade.exit_price = exit_price
            trade.exit_reason = reason
            trade.timestamp_closed = datetime.utcnow()
            self.closed_trades.append(trade)
            
            self.trade_history.append({
                'action': 'close',
                'trade': trade,
                'timestamp': datetime.utcnow()
            })
    
    # ===================== REPORTING =====================
    
    def get_summary(self) -> Dict:
        """Get execution engine summary."""
        open_trades = list(self.open_trades.values())
        
        total_pnl = sum(t.current_pnl for t in open_trades)
        
        return {
            'open_trades': len(open_trades),
            'closed_trades': len(self.closed_trades),
            'total_open_pnl': total_pnl,
            'avg_pnl_pct': sum(t.current_pnl_pct for t in open_trades) / len(open_trades) if open_trades else 0,
            'modules_active': {
                'fibonacci': self.fibonacci_engine is not None,
                'validator': self.signal_validator is not None,
                'scheduler': self.smart_scheduler is not None,
                'scorer': self.signal_scorer is not None
            }
        }


# Module-level singleton
_integrated_engine = None


def get_integrated_engine() -> IntegratedExecutionEngine:
    """Get global integrated execution engine."""
    global _integrated_engine
    if _integrated_engine is None:
        _integrated_engine = IntegratedExecutionEngine()
    return _integrated_engine
