"""
Risk Guard - Emergency Stop and Fail-Safe Mechanisms
Handles: max drawdown, position limits, emergency stop, circuit breakers

Author: v0-strategy-engine-pro
License: MIT
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from .execution_models import Position


class RiskGuard:
    """Emergency stop and fail-safe mechanisms"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Risk parameters
        self.max_daily_loss_pct = 2.0
        self.max_drawdown_pct = 10.0
        self.max_open_positions = 10
        self.max_position_size_pct = 5.0
        self.max_portfolio_risk_pct = 2.0
        
        # Tracking
        self.daily_loss = 0.0
        self.peak_equity = 0.0
        self.current_equity = 0.0
        self.circuit_breaker_triggered = False
        self.circuit_breaker_time: Optional[datetime] = None
        self.circuit_breaker_cooldown_minutes = 60
    
    def check_position_limits(
        self,
        num_open_positions: int,
        proposed_position_size: float,
        portfolio_value: float
    ) -> tuple:
        """
        Check if proposed position violates limits
        Returns: (is_allowed, reason)
        """
        # Check position count
        if num_open_positions >= self.max_open_positions:
            reason = f"Max positions limit reached: {num_open_positions}/{self.max_open_positions}"
            return False, reason
        
        # Check position size
        position_size_pct = (proposed_position_size / portfolio_value) * 100
        if position_size_pct > self.max_position_size_pct:
            reason = f"Position size {position_size_pct:.2f}% exceeds limit {self.max_position_size_pct}%"
            return False, reason
        
        return True, "OK"
    
    def check_drawdown(
        self,
        current_equity: float,
        peak_equity: Optional[float] = None
    ) -> tuple:
        """
        Check maximum drawdown
        Returns: (is_safe, drawdown_pct)
        """
        if peak_equity is None:
            peak_equity = self.peak_equity
        
        self.current_equity = current_equity
        if current_equity > peak_equity:
            self.peak_equity = current_equity
            peak_equity = current_equity
        
        if peak_equity == 0:
            return True, 0.0
        
        drawdown_pct = ((peak_equity - current_equity) / peak_equity) * 100
        is_safe = drawdown_pct < self.max_drawdown_pct
        
        if not is_safe:
            self.logger.critical(
                f"DRAWDOWN ALERT: {drawdown_pct:.2f}% (limit: {self.max_drawdown_pct}%)"
            )
        
        return is_safe, drawdown_pct
    
    def check_daily_loss(
        self,
        daily_loss: float,
        portfolio_value: float
    ) -> tuple:
        """
        Check daily loss limits
        Returns: (is_safe, loss_pct)
        """
        loss_pct = (daily_loss / portfolio_value) * 100
        is_safe = loss_pct < self.max_daily_loss_pct
        
        if not is_safe:
            self.logger.critical(
                f"DAILY LOSS LIMIT TRIGGERED: {loss_pct:.2f}% (limit: {self.max_daily_loss_pct}%)"
            )
        
        return is_safe, loss_pct
    
    def should_trigger_circuit_breaker(self) -> bool:
        """
        Determine if circuit breaker should be triggered
        Returns: True if should stop trading
        """
        if self.circuit_breaker_triggered:
            if self.circuit_breaker_time:
                elapsed = (datetime.utcnow() - self.circuit_breaker_time).total_seconds() / 60
                if elapsed > self.circuit_breaker_cooldown_minutes:
                    self.logger.info("Circuit breaker cooldown expired")
                    self.circuit_breaker_triggered = False
                    return False
            return True
        
        return False
    
    def trigger_circuit_breaker(self, reason: str = ""):
        """Trigger emergency stop"""
        self.circuit_breaker_triggered = True
        self.circuit_breaker_time = datetime.utcnow()
        self.logger.critical(f"CIRCUIT BREAKER TRIGGERED: {reason}")
    
    def reset_daily_metrics(self):
        """Reset daily metrics at end of day"""
        self.daily_loss = 0.0
        self.logger.info("Daily metrics reset")
    
    def check_all_limits(
        self,
        num_positions: int,
        proposed_size: float,
        portfolio_value: float,
        daily_loss: float
    ) -> Dict:
        """
        Comprehensive risk check
        Returns: dict with all checks
        """
        pos_ok, pos_reason = self.check_position_limits(
            num_positions, proposed_size, portfolio_value
        )
        dd_ok, dd_pct = self.check_drawdown(portfolio_value)
        dl_ok, dl_pct = self.check_daily_loss(daily_loss, portfolio_value)
        cb_ok = not self.should_trigger_circuit_breaker()
        
        return {
            "position_limit_ok": pos_ok,
            "position_limit_reason": pos_reason,
            "drawdown_ok": dd_ok,
            "drawdown_pct": dd_pct,
            "daily_loss_ok": dl_ok,
            "daily_loss_pct": dl_pct,
            "circuit_breaker_ok": cb_ok,
            "all_checks_pass": pos_ok and dd_ok and dl_ok and cb_ok
        }
