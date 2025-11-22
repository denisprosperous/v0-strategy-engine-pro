"""
Position Tracker - Real-time Position Management
Handles: position opening, tracking, PnL calculation, risk monitoring

Author: v0-strategy-engine-pro
License: MIT
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
from .execution_models import Position, ExecutionOrder, ExecutionStatus


class PositionTracker:
    """Manages active positions across all symbols and exchanges"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.positions: Dict[str, Position] = {}  # symbol -> Position
        self.position_history: List[Position] = []
    
    def open_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        exchange: str = "binance"
    ) -> Position:
        """
        Open a new position
        Returns: Position object
        """
        if symbol in self.positions:
            self.logger.warning(f"Position already exists for {symbol}")
            return self.positions[symbol]
        
        position = Position(
            symbol=symbol,
            side=side.upper(),
            quantity=quantity,
            entry_price=entry_price,
            stop_loss_price=stop_loss,
            take_profit_price=take_profit,
            exchange=exchange
        )
        
        self.positions[symbol] = position
        self.logger.info(
            f"Opened {side} position: {symbol} "
            f"x{quantity} @ {entry_price}"
        )
        return position
    
    def close_position(self, symbol: str, exit_price: float) -> Optional[Dict]:
        """
        Close an existing position
        Returns: Position summary with PnL
        """
        if symbol not in self.positions:
            self.logger.warning(f"No position for {symbol}")
            return None
        
        position = self.positions[symbol]
        
        # Calculate realized PnL
        if position.side.upper() == "LONG":
            realized_pnl = (exit_price - position.entry_price) * position.quantity
        else:
            realized_pnl = (position.entry_price - exit_price) * position.quantity
        
        realized_pnl_pct = (realized_pnl / (position.entry_price * position.quantity)) * 100
        
        # Store in history
        self.position_history.append(position)
        
        # Remove from active
        del self.positions[symbol]
        
        self.logger.info(
            f"Closed {position.side} position: {symbol} "
            f"PnL: {realized_pnl:.2f} ({realized_pnl_pct:.2f}%)"
        )
        
        return {
            "symbol": symbol,
            "side": position.side,
            "quantity": position.quantity,
            "entry_price": position.entry_price,
            "exit_price": exit_price,
            "realized_pnl": realized_pnl,
            "realized_pnl_pct": realized_pnl_pct,
            "duration": (datetime.utcnow() - position.entry_time).total_seconds(),
        }
    
    def update_position_price(self, symbol: str, current_price: float) -> Optional[Tuple]:
        """
        Update current price and recalculate unrealized PnL
        Returns: (unrealized_pnl, unrealized_pnl_pct) or None
        """
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        pnl, pnl_pct = position.calculate_pnl(current_price)
        return pnl, pnl_pct
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Retrieve position by symbol"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> List[Position]:
        """Get all active positions"""
        return list(self.positions.values())
    
    def get_portfolio_pnl(self) -> Tuple[float, float]:
        """
        Calculate total portfolio unrealized PnL
        Returns: (total_pnl, total_pnl_pct)
        """
        if not self.positions:
            return 0.0, 0.0
        
        total_pnl = sum(p.unrealized_pnl for p in self.positions.values())
        total_notional = sum(p.entry_price * p.quantity for p in self.positions.values())
        total_pnl_pct = (total_pnl / total_notional * 100) if total_notional > 0 else 0.0
        
        return total_pnl, total_pnl_pct
    
    def get_position_count(self) -> int:
        """Get number of active positions"""
        return len(self.positions)
    
    def update_stop_loss(self, symbol: str, new_stop_loss: float) -> bool:
        """Update stop loss for a position"""
        if symbol not in self.positions:
            return False
        
        self.positions[symbol].stop_loss_price = new_stop_loss
        self.logger.info(f"Updated SL for {symbol} to {new_stop_loss}")
        return True
    
    def update_take_profit(self, symbol: str, new_take_profit: float) -> bool:
        """Update take profit for a position"""
        if symbol not in self.positions:
            return False
        
        self.positions[symbol].take_profit_price = new_take_profit
        self.logger.info(f"Updated TP for {symbol} to {new_take_profit}")
        return True
    
    def get_losing_positions(self, threshold_pct: float = 0.0) -> List[Position]:
        """Get all positions with losses exceeding threshold"""
        return [
            p for p in self.positions.values()
            if p.unrealized_pnl_pct < threshold_pct
        ]
    
    def get_winning_positions(self, threshold_pct: float = 0.0) -> List[Position]:
        """Get all positions with gains exceeding threshold"""
        return [
            p for p in self.positions.values()
            if p.unrealized_pnl_pct >= threshold_pct
        ]
    
    def get_position_stats(self) -> Dict:
        """Get comprehensive position statistics"""
        positions = self.get_all_positions()
        if not positions:
            return {"active_positions": 0}
        
        total_pnl, total_pnl_pct = self.get_portfolio_pnl()
        winning = self.get_winning_positions()
        losing = self.get_losing_positions()
        
        return {
            "active_positions": len(positions),
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "winning_positions": len(winning),
            "losing_positions": len(losing),
            "avg_win": sum(p.unrealized_pnl for p in winning) / len(winning) if winning else 0,
            "avg_loss": sum(p.unrealized_pnl for p in losing) / len(losing) if losing else 0,
            "positions": [p.to_dict() for p in positions]
        }
