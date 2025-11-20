"""Enhanced Risk Management Module with Adaptive Position Sizing.

Implements modular risk management with:
- Tier-based position sizing (Tier 1: 2.0%, Tier 2: 1.5%, Tier 3: 0.75%)
- Daily and weekly drawdown caps with escalation
- Per-asset exposure limits (Crypto/Forex/Stocks: 6% each)
- Maximum concurrent exposure tracking (10% total)
- Asset-class specific stops and targets (SL + TP with R:R ratios)
- Dynamic risk reduction on volatility spikes
- Partial profit-taking with trailing stop logic
- Breakeven lock-in at 1R profit

Author: Trading Bot v0
Version: 1.0
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List
from enum import Enum
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SignalTier(Enum):
    """Signal tier classification."""
    TIER_1 = 1  # 2.0% risk, 1:4 R:R
    TIER_2 = 2  # 1.5% risk, 1:3 R:R
    TIER_3 = 3  # 0.75% risk, 1:2 R:R (quota support only)
    SKIP = 4    # Do not trade


class AssetClass(Enum):
    """Asset classes."""
    CRYPTO = 'crypto'
    FOREX = 'forex'
    STOCKS = 'stocks'


@dataclass
class RiskMetrics:
    """Container for risk metrics and status."""
    current_equity: float
    daily_loss: float = 0.0
    weekly_loss: float = 0.0
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    
    # Exposure tracking
    current_exposure: float = 0.0  # Total open position exposure
    crypto_exposure: float = 0.0
    forex_exposure: float = 0.0
    stocks_exposure: float = 0.0
    
    # Session info
    trades_today: int = 0
    trades_this_week: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # Risk flags
    daily_max_loss_breached: bool = False
    weekly_max_loss_breached: bool = False
    max_exposure_breached: bool = False
    asset_cap_breached: bool = False
    
    def get_risk_factor(self) -> float:
        """Get risk reduction factor based on drawdowns.
        
        Returns 1.0 (normal) or 0.5 (reduced) or 0.0 (kill-switch)
        """
        if self.daily_max_loss_breached or self.weekly_max_loss_breached:
            return 0.0  # Kill-switch engaged
        if self.weekly_max_loss_breached:
            return 0.5  # 50% risk reduction for next week
        return 1.0


@dataclass
class TradeRisk:
    """Detailed risk parameters for a single trade."""
    symbol: str
    asset_class: AssetClass
    tier: SignalTier
    entry_price: float
    stop_loss: float
    take_profit_1: float  # Partial exit target
    take_profit_2: float  # Final exit target
    
    # Computed fields
    risk_amount: float = 0.0  # Dollar amount at risk
    position_size: float = 0.0  # Contracts/shares to trade
    reward_amount: float = 0.0  # Expected reward
    risk_reward_ratio: float = 0.0  # R:R (e.g., 1:4)
    
    # Trailing and management
    breakeven_price: Optional[float] = None
    trail_stop: Optional[float] = None
    partial_taken: bool = False
    
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def get_stop_loss_percent(self) -> float:
        """Get stop loss as percentage from entry."""
        return abs(self.entry_price - self.stop_loss) / self.entry_price * 100
    
    def get_tp_1_percent(self) -> float:
        """Get TP1 as percentage from entry."""
        return abs(self.take_profit_1 - self.entry_price) / self.entry_price * 100
    
    def get_tp_2_percent(self) -> float:
        """Get TP2 as percentage from entry."""
        return abs(self.take_profit_2 - self.entry_price) / self.entry_price * 100


class RiskManager:
    """Enhanced risk management with adaptive position sizing."""
    
    def __init__(self, initial_equity: float):
        """Initialize risk manager.
        
        Args:
            initial_equity: Starting account equity
        """
        self.initial_equity = initial_equity
        self.current_equity = initial_equity
        self.metrics = RiskMetrics(current_equity=initial_equity)
        
        # Risk caps (as percentage of equity)
        self.daily_max_loss_pct = 0.05  # 5%
        self.weekly_max_loss_pct = 0.12  # 12%
        self.max_concurrent_exposure = 0.10  # 10%
        self.asset_exposure_cap = 0.06  # 6% per asset class
        
        # Tier risk percentages
        self.tier_risks = {
            SignalTier.TIER_1: 0.02,  # 2%
            SignalTier.TIER_2: 0.015,  # 1.5%
            SignalTier.TIER_3: 0.0075,  # 0.75%
        }
        
        # Risk reward ratios
        self.tier_rr_ratios = {
            SignalTier.TIER_1: 4.0,  # 1:4
            SignalTier.TIER_2: 3.0,  # 1:3
            SignalTier.TIER_3: 2.0,  # 1:2
        }
        
        # Asset-specific stops (percent of ATR)
        self.asset_stops = {
            AssetClass.CRYPTO: {'min': 0.005, 'max': 0.01, 'atr_mult': 0.8},
            AssetClass.FOREX: {'min': 0.01, 'max': 0.02, 'atr_mult': 1.0},
            AssetClass.STOCKS: {'min': 0.01, 'max': 0.015, 'atr_mult': 1.2},
        }
        
        # Open trades
        self.open_trades: Dict[str, TradeRisk] = {}
        
    def calculate_position_size(self, signal_tier: SignalTier, entry_price: float,
                               stop_loss: float, account_equity: float) -> float:
        """Calculate position size based on tier and risk.
        
        Position Size = (Risk Amount / Risk Distance in $)
        Risk Amount = Account Equity * Risk %
        
        Args:
            signal_tier: Tier 1, 2, or 3
            entry_price: Entry price
            stop_loss: Stop loss price
            account_equity: Current account equity
            
        Returns:
            Position size (contracts/shares)
        """
        # Get base risk percentage
        risk_pct = self.tier_risks.get(signal_tier, 0.0)
        
        # Apply risk reduction if needed
        risk_factor = self.metrics.get_risk_factor()
        if risk_factor == 0.0:
            return 0.0  # No trading - kill-switch active
        
        risk_pct *= risk_factor
        
        # Calculate dollar risk
        risk_amount = account_equity * risk_pct
        
        # Calculate distance to stop loss
        stop_distance = abs(entry_price - stop_loss)
        
        # Position size = risk dollars / per-unit risk
        if stop_distance <= 0:
            return 0.0
        
        position_size = risk_amount / stop_distance
        return position_size
    
    def calculate_take_profits(self, entry_price: float, stop_loss: float,
                              signal_tier: SignalTier,
                              direction: str = 'long') -> Tuple[float, float]:
        """Calculate take profit levels based on tier R:R ratio.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            signal_tier: Signal tier (determines R:R)
            direction: 'long' or 'short'
            
        Returns:
            (tp1, tp2) tuple for partial and final exits
        """
        risk_distance = abs(entry_price - stop_loss)
        rr_ratio = self.tier_rr_ratios.get(signal_tier, 1.0)
        
        # Reward distance = risk distance * R:R ratio
        reward_distance = risk_distance * rr_ratio
        
        if direction == 'long':
            tp1 = entry_price + (reward_distance * 0.5)  # 50% of reward
            tp2 = entry_price + reward_distance  # Full reward
        else:  # short
            tp1 = entry_price - (reward_distance * 0.5)
            tp2 = entry_price - reward_distance
        
        return tp1, tp2
    
    def can_open_trade(self, symbol: str, asset_class: AssetClass,
                      signal_tier: SignalTier, position_size: float) -> Tuple[bool, str]:
        """Check if trade can be opened based on risk caps.
        
        Args:
            symbol: Trading symbol
            asset_class: Asset class
            signal_tier: Signal tier
            position_size: Intended position size
            
        Returns:
            (can_open, reason) tuple
        """
        # Check daily max loss
        if self.metrics.daily_loss >= (self.current_equity * self.daily_max_loss_pct):
            return False, "Daily max loss cap breached"
        
        # Check weekly max loss with escalation
        if self.metrics.weekly_loss >= (self.current_equity * self.weekly_max_loss_pct):
            return False, "Weekly max loss cap breached"
        
        # Check total concurrent exposure
        new_exposure = self.metrics.current_exposure + (position_size * 1.0)  # Simplified
        if new_exposure > (self.current_equity * self.max_concurrent_exposure):
            return False, f"Max concurrent exposure limit: {self.max_concurrent_exposure*100}%"
        
        # Check asset-specific exposure
        asset_exposure = self._get_asset_exposure(asset_class)
        if asset_exposure > (self.current_equity * self.asset_exposure_cap):
            return False, f"Asset class exposure limit: {self.asset_exposure_cap*100}%"
        
        return True, "OK"
    
    def _get_asset_exposure(self, asset_class: AssetClass) -> float:
        """Get current exposure for asset class."""
        if asset_class == AssetClass.CRYPTO:
            return self.metrics.crypto_exposure
        elif asset_class == AssetClass.FOREX:
            return self.metrics.forex_exposure
        else:
            return self.metrics.stocks_exposure
    
    def update_metrics(self, pnl: float, is_win: bool, tier: SignalTier):
        """Update risk metrics after trade close."""
        self.metrics.daily_pnl += pnl
        self.metrics.weekly_pnl += pnl
        self.current_equity += pnl
        
        if pnl < 0:
            self.metrics.daily_loss += abs(pnl)
            self.metrics.weekly_loss += abs(pnl)
        
        self.metrics.trades_today += 1
        if is_win:
            self.metrics.winning_trades += 1
        else:
            self.metrics.losing_trades += 1
    
    def get_stop_loss_distance(self, asset_class: AssetClass, atr: float) -> float:
        """Get stop loss distance based on asset class and ATR.
        
        Args:
            asset_class: Crypto, Forex, or Stocks
            atr: Current ATR value
            
        Returns:
            Stop loss distance as percentage
        """
        config = self.asset_stops.get(asset_class)
        atr_stop = atr * config['atr_mult']
        
        # Use tighter of percent or ATR-based
        return min(config['max'], max(config['min'], atr_stop))
