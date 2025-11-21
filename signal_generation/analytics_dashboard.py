"""
Analytics Dashboard Module - Real-time Trade & Performance Tracking
Provides comprehensive live dashboard, performance metrics, trade history drill-down,
risk tracking, signal statistics, and real-time updates integrated with execution engine.

Tier-based win rates: Tier1 ≥80%, Tier2 ≥75%, Tier3 ≥67%
Expected profit factor: ≥2.5 overall
Max drawdown: ≤10%
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
import statistics


class SessionWindow(Enum):
    """Trading session windows aligned with liquidity peaks"""
    LONDON_OPEN = "08:00"  # 08:00 UTC
    NY_OPEN = "13:00"      # 13:00 UTC
    MID_SESSION = "17:00"  # 17:00 UTC
    HOURLY_CRYPTO = "hourly"


@dataclass
class DashboardTile:
    """Individual dashboard metric tile"""
    name: str
    value: float
    unit: str = "%"
    status: str = "normal"  # "normal", "warning", "critical"
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TradeMetrics:
    """Aggregated trade performance metrics"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    avg_return_per_trade: float = 0.0
    
    def calculate_metrics(self, trades: List['TradeRecord']) -> None:
        """Recalculate all metrics from trade list"""
        if not trades:
            return
        
        self.total_trades = len(trades)
        self.winning_trades = sum(1 for t in trades if t.pnl > 0)
        self.losing_trades = sum(1 for t in trades if t.pnl < 0)
        self.total_profit = sum(t.pnl for t in trades if t.pnl > 0)
        self.total_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
        
        if self.total_trades > 0:
            self.win_rate = (self.winning_trades / self.total_trades) * 100
        
        if self.total_loss > 0:
            self.profit_factor = self.total_profit / self.total_loss
        else:
            self.profit_factor = float('inf') if self.total_profit > 0 else 0.0
        
        if len(trades) > 1:
            returns = [t.pnl_pct for t in trades]
            if all(r is not None for r in returns):
                mean_return = statistics.mean(returns)
                stdev = statistics.stdev(returns) if len(returns) > 1 else 0
                sharpe_denominator = stdev if stdev != 0 else 1
                self.sharpe_ratio = (mean_return * 252 / sharpe_denominator) if sharpe_denominator else 0
        
        # Calculate max drawdown (peak-to-trough)
        cumulative_pnl = 0
        peak = 0
        max_dd = 0
        for trade in trades:
            cumulative_pnl += trade.pnl
            peak = max(peak, cumulative_pnl)
            drawdown = peak - cumulative_pnl
            max_dd = max(max_dd, drawdown)
        self.max_drawdown = max_dd
        
        if self.total_trades > 0:
            self.avg_return_per_trade = (self.total_profit - self.total_loss) / self.total_trades


@dataclass
class TradeRecord:
    """Individual trade record for history tracking"""
    trade_id: str
    symbol: str
    tier: int
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_pct: float
    timeframe: str
    asset_class: str  # "crypto", "forex", "stocks"
    session_window: str
    entry_time: datetime
    exit_time: datetime
    status: str = "closed"  # "open", "partial", "closed"


class AnalyticsDashboard:
    """
    Real-time analytics dashboard aggregating:
    - Live metrics (equity, risk, exposure, loss caps, news filters)
    - Performance metrics (win rate, profit factor, sharpe, drawdown)
    - Trade history with multi-dimensional filtering
    - Risk tracking by asset class
    - Signal statistics by tier
    - Real-time updates from execution & risk management modules
    """
    
    def __init__(self):
        self.closed_trades: List[TradeRecord] = []
        self.open_trades: Dict[str, TradeRecord] = {}
        self.tier_metrics: Dict[int, TradeMetrics] = {1: TradeMetrics(), 2: TradeMetrics(), 3: TradeMetrics()}
        self.overall_metrics = TradeMetrics()
        
        # Dashboard tiles
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.open_risk: float = 0.0
        self.daily_exposure: Dict[str, float] = {"crypto": 0.0, "forex": 0.0, "stocks": 0.0}
        self.daily_loss: float = 0.0
        self.weekly_loss: float = 0.0
        self.loss_cap_status: Dict[str, float] = {"daily_remaining": 5.0, "weekly_remaining": 12.0}
        self.news_filter_status: Dict[str, bool] = {
            "forex_nfp": False, "forex_cpi": False, "forex_fomc": False,
            "stocks_earnings": False, "crypto_funding": False
        }
        
        # Signal statistics
        self.signal_attempts: Dict[int, int] = {1: 0, 2: 0, 3: 0}
        self.signal_success: Dict[int, int] = {1: 0, 2: 0, 3: 0}
        self.signal_skip_reasons: Dict[str, int] = {}
        
        self.last_update = datetime.utcnow()
    
    def add_closed_trade(self, trade: TradeRecord) -> None:
        """Record completed trade and update metrics"""
        self.closed_trades.append(trade)
        self.tier_metrics[trade.tier].calculate_metrics([t for t in self.closed_trades if t.tier == trade.tier])
        self.overall_metrics.calculate_metrics(self.closed_trades)
        
        # Update equity curve
        cumulative_pnl = sum(t.pnl for t in self.closed_trades)
        self.equity_curve.append((datetime.utcnow(), cumulative_pnl))
        
        # Update loss tracking
        if trade.pnl < 0:
            self.daily_loss += abs(trade.pnl)
            self.weekly_loss += abs(trade.pnl)
            self.loss_cap_status["daily_remaining"] = 5.0 - (self.daily_loss / 100)
            self.loss_cap_status["weekly_remaining"] = 12.0 - (self.weekly_loss / 100)
    
    def update_from_execution_engine(self, open_trades: Dict[str, any]) -> None:
        """Sync real-time data from ExecutionEngine"""
        self.open_trades = open_trades
        
        # Calculate current open risk
        self.open_risk = sum(abs(t.current_pnl) for t in open_trades.values())
        
        # Update daily exposure by asset class
        for symbol, trade in open_trades.items():
            ac = trade.asset_class if hasattr(trade, 'asset_class') else "unknown"
            if ac in self.daily_exposure:
                self.daily_exposure[ac] += trade.quantity * trade.entry_price
    
    def update_from_risk_manager(self, daily_loss: float, weekly_loss: float, 
                                 daily_cap: float = 5.0, weekly_cap: float = 12.0) -> None:
        """Sync risk management data"""
        self.daily_loss = daily_loss
        self.weekly_loss = weekly_loss
        self.loss_cap_status["daily_remaining"] = max(0, daily_cap - daily_loss)
        self.loss_cap_status["weekly_remaining"] = max(0, weekly_cap - weekly_loss)
    
    def update_news_filter_status(self, filter_name: str, is_active: bool) -> None:
        """Update news event filter status"""
        if filter_name in self.news_filter_status:
            self.news_filter_status[filter_name] = is_active
    
    def record_signal_attempt(self, tier: int, skip_reason: Optional[str] = None) -> None:
        """Track signal generation attempts"""
        if skip_reason:
            self.signal_skip_reasons[skip_reason] = self.signal_skip_reasons.get(skip_reason, 0) + 1
        else:
            self.signal_attempts[tier] = self.signal_attempts.get(tier, 0) + 1
    
    def record_signal_success(self, tier: int) -> None:
        """Track successful signal execution"""
        self.signal_success[tier] = self.signal_success.get(tier, 0) + 1
    
    def get_live_dashboard_tiles(self) -> Dict[str, DashboardTile]:
        """Return current dashboard tile values"""
        return {
            "equity_curve": DashboardTile("Equity Curve", sum(t.pnl for t in self.closed_trades), "USD"),
            "open_risk": DashboardTile("Open Risk", self.open_risk, "USD"),
            "daily_exposure": DashboardTile("Daily Exposure", sum(self.daily_exposure.values()), "USD"),
            "daily_loss_cap": DashboardTile("Daily Loss Cap Status", 
                                           self.loss_cap_status["daily_remaining"], "%",
                                           "critical" if self.loss_cap_status["daily_remaining"] < 1 else "normal"),
            "weekly_loss_cap": DashboardTile("Weekly Loss Cap Status",
                                            self.loss_cap_status["weekly_remaining"], "%",
                                            "critical" if self.loss_cap_status["weekly_remaining"] < 2 else "normal"),
            "news_filters_active": DashboardTile("Active News Filters", 
                                               sum(1 for v in self.news_filter_status.values() if v), "count"),
        }
    
    def filter_by_tier(self, tier: int) -> List[TradeRecord]:
        """Filter trades by tier (1, 2, or 3)"""
        return [t for t in self.closed_trades if t.tier == tier]
    
    def filter_by_timeframe(self, timeframe: str) -> List[TradeRecord]:
        """Filter trades by timeframe (1h, 4h, 1d, 1w)"""
        return [t for t in self.closed_trades if t.timeframe == timeframe]
    
    def filter_by_asset_class(self, asset_class: str) -> List[TradeRecord]:
        """Filter trades by asset class (crypto, forex, stocks)"""
        return [t for t in self.closed_trades if t.asset_class == asset_class]
    
    def filter_by_session_window(self, window: str) -> List[TradeRecord]:
        """Filter trades by session window (London, NY, Mid, Crypto)"""
        return [t for t in self.closed_trades if t.session_window == window]
    
    def get_drill_down_analysis(self, tier: Optional[int] = None, 
                               timeframe: Optional[str] = None,
                               asset_class: Optional[str] = None,
                               session_window: Optional[str] = None) -> Tuple[List[TradeRecord], TradeMetrics]:
        """Multi-dimensional drill-down with dynamic filtering"""
        filtered = self.closed_trades
        
        if tier is not None:
            filtered = [t for t in filtered if t.tier == tier]
        if timeframe is not None:
            filtered = [t for t in filtered if t.timeframe == timeframe]
        if asset_class is not None:
            filtered = [t for t in filtered if t.asset_class == asset_class]
        if session_window is not None:
            filtered = [t for t in filtered if t.session_window == session_window]
        
        metrics = TradeMetrics()
        metrics.calculate_metrics(filtered)
        return filtered, metrics
    
    def get_risk_tracking(self) -> Dict[str, any]:
        """Return current risk exposure breakdown"""
        return {
            "current_exposure": sum(self.daily_exposure.values()),
            "per_asset_breakdown": self.daily_exposure.copy(),
            "max_exposure_caps": {"crypto": 6.0, "forex": 6.0, "stocks": 6.0},
            "remaining_capacity": {
                "crypto": 6.0 - self.daily_exposure["crypto"],
                "forex": 6.0 - self.daily_exposure["forex"],
                "stocks": 6.0 - self.daily_exposure["stocks"],
            },
            "daily_loss_cap": self.loss_cap_status["daily_remaining"],
            "weekly_loss_cap": self.loss_cap_status["weekly_remaining"],
        }
    
    def get_signal_statistics(self) -> Dict[str, any]:
        """Return signal generation and success statistics"""
        tier_success_rates = {}
        for tier in [1, 2, 3]:
            attempts = self.signal_attempts.get(tier, 0)
            success = self.signal_success.get(tier, 0)
            success_rate = (success / attempts * 100) if attempts > 0 else 0
            tier_success_rates[f"tier_{tier}"] = {
                "attempts": attempts,
                "successful": success,
                "success_rate": success_rate
            }
        
        return {
            "tier_distribution": self.signal_attempts.copy(),
            "success_rates_by_tier": tier_success_rates,
            "skip_reasons": self.signal_skip_reasons.copy(),
            "total_skipped": sum(self.signal_skip_reasons.values()),
        }
    
    def get_performance_metrics(self) -> TradeMetrics:
        """Return overall performance metrics"""
        return self.overall_metrics
    
    def get_tier_metrics(self, tier: int) -> TradeMetrics:
        """Return metrics for specific tier"""
        return self.tier_metrics.get(tier, TradeMetrics())
    
    def reset_daily_metrics(self) -> None:
        """Reset daily metrics (called at end of trading day)"""
        self.daily_loss = 0.0
        self.daily_exposure = {"crypto": 0.0, "forex": 0.0, "stocks": 0.0}
        self.loss_cap_status["daily_remaining"] = 5.0


# Module-level singleton
_dashboard = AnalyticsDashboard()
