#!/usr/bin/env python3
"""
Backtesting Engine

Comprehensive backtesting system for strategy validation:
- Historical data backtesting
- Performance metrics calculation
- Risk analysis
- Trade simulation
- Report generation

Author: v0-strategy-engine-pro
Version: 1.0
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class BacktestTrade:
    """Individual backtest trade."""
    entry_time: datetime
    exit_time: datetime
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_pct: float
    fees: float
    duration_hours: float
    tier: int
    confidence: float


@dataclass
class BacktestMetrics:
    """Backtest performance metrics."""
    # Returns
    total_return: float
    total_return_pct: float
    annualized_return: float
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # Profit metrics
    gross_profit: float
    gross_loss: float
    net_profit: float
    profit_factor: float
    
    # Risk metrics
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    
    # Average metrics
    avg_win: float
    avg_loss: float
    avg_win_pct: float
    avg_loss_pct: float
    largest_win: float
    largest_loss: float
    
    # Time metrics
    avg_trade_duration_hours: float
    total_time_in_market_pct: float
    
    # Additional
    expectancy: float
    recovery_factor: float
    risk_reward_ratio: float


class BacktestEngine:
    """
    Backtesting engine for strategy validation.
    """
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission: float = 0.001,  # 0.1%
        slippage: float = 0.0005  # 0.05%
    ):
        """
        Initialize backtest engine.
        
        Args:
            initial_capital: Starting capital
            commission: Trading commission rate
            slippage: Slippage rate
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        
        self.trades: List[BacktestTrade] = []
        self.equity_curve: List[float] = [initial_capital]
        self.timestamps: List[datetime] = []
        
        logger.info(
            f"Backtest engine initialized: "
            f"${initial_capital:,.2f} capital, "
            f"{commission*100:.2f}% commission"
        )
    
    def add_trade(
        self,
        entry_time: datetime,
        exit_time: datetime,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        size: float,
        tier: int = 2,
        confidence: float = 0.75
    ) -> BacktestTrade:
        """
        Add trade to backtest.
        
        Args:
            entry_time: Entry timestamp
            exit_time: Exit timestamp
            symbol: Trading symbol
            side: 'long' or 'short'
            entry_price: Entry price
            exit_price: Exit price
            size: Position size
            tier: Signal tier
            confidence: Signal confidence
        
        Returns:
            BacktestTrade object
        """
        # Calculate PnL
        if side == 'long':
            pnl_before_fees = (exit_price - entry_price) * size
        else:  # short
            pnl_before_fees = (entry_price - exit_price) * size
        
        # Calculate fees
        entry_fees = entry_price * size * self.commission
        exit_fees = exit_price * size * self.commission
        slippage_cost = (entry_price + exit_price) * size * self.slippage
        total_fees = entry_fees + exit_fees + slippage_cost
        
        # Net PnL
        net_pnl = pnl_before_fees - total_fees
        pnl_pct = (net_pnl / (entry_price * size)) * 100
        
        # Duration
        duration = (exit_time - entry_time).total_seconds() / 3600
        
        trade = BacktestTrade(
            entry_time=entry_time,
            exit_time=exit_time,
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            exit_price=exit_price,
            size=size,
            pnl=net_pnl,
            pnl_pct=pnl_pct,
            fees=total_fees,
            duration_hours=duration,
            tier=tier,
            confidence=confidence
        )
        
        self.trades.append(trade)
        
        # Update equity curve
        if self.equity_curve:
            new_equity = self.equity_curve[-1] + net_pnl
            self.equity_curve.append(new_equity)
            self.timestamps.append(exit_time)
        
        return trade
    
    def calculate_metrics(self) -> BacktestMetrics:
        """
        Calculate comprehensive backtest metrics.
        
        Returns:
            BacktestMetrics object
        """
        if not self.trades:
            logger.warning("No trades to analyze")
            return None
        
        # Basic stats
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.pnl > 0)
        losing_trades = sum(1 for t in self.trades if t.pnl <= 0)
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # PnL stats
        gross_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self.trades if t.pnl < 0))
        net_profit = sum(t.pnl for t in self.trades)
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Returns
        total_return = self.equity_curve[-1] - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        # Annualized return
        if self.timestamps:
            days = (self.timestamps[-1] - self.timestamps[0]).days
            years = days / 365.25 if days > 0 else 1
            annualized_return = (total_return_pct / years) if years > 0 else 0
        else:
            annualized_return = 0
        
        # Drawdown
        equity_series = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_series)
        drawdown = equity_series - running_max
        max_drawdown = abs(drawdown.min())
        max_drawdown_pct = (max_drawdown / self.initial_capital) * 100
        
        # Risk-adjusted returns
        returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
        
        if len(returns) > 1:
            sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
            
            # Sortino ratio (only downside deviation)
            downside_returns = returns[returns < 0]
            downside_std = np.std(downside_returns) if len(downside_returns) > 0 else np.std(returns)
            sortino_ratio = (np.mean(returns) / downside_std) * np.sqrt(252) if downside_std > 0 else 0
        else:
            sharpe_ratio = 0
            sortino_ratio = 0
        
        # Calmar ratio
        calmar_ratio = annualized_return / max_drawdown_pct if max_drawdown_pct > 0 else 0
        
        # Average metrics
        wins = [t.pnl for t in self.trades if t.pnl > 0]
        losses = [t.pnl for t in self.trades if t.pnl < 0]
        
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        
        wins_pct = [t.pnl_pct for t in self.trades if t.pnl > 0]
        losses_pct = [t.pnl_pct for t in self.trades if t.pnl < 0]
        
        avg_win_pct = np.mean(wins_pct) if wins_pct else 0
        avg_loss_pct = np.mean(losses_pct) if losses_pct else 0
        
        largest_win = max(wins) if wins else 0
        largest_loss = min(losses) if losses else 0
        
        # Time metrics
        durations = [t.duration_hours for t in self.trades]
        avg_duration = np.mean(durations) if durations else 0
        
        total_time = (self.timestamps[-1] - self.timestamps[0]).total_seconds() / 3600 if len(self.timestamps) > 1 else 1
        time_in_market = sum(durations)
        time_in_market_pct = (time_in_market / total_time) * 100 if total_time > 0 else 0
        
        # Expectancy
        expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)
        
        # Recovery factor
        recovery_factor = net_profit / max_drawdown if max_drawdown > 0 else 0
        
        # Risk-reward ratio
        risk_reward_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        return BacktestMetrics(
            total_return=total_return,
            total_return_pct=total_return_pct,
            annualized_return=annualized_return,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            net_profit=net_profit,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            avg_win=avg_win,
            avg_loss=avg_loss,
            avg_win_pct=avg_win_pct,
            avg_loss_pct=avg_loss_pct,
            largest_win=largest_win,
            largest_loss=largest_loss,
            avg_trade_duration_hours=avg_duration,
            total_time_in_market_pct=time_in_market_pct,
            expectancy=expectancy,
            recovery_factor=recovery_factor,
            risk_reward_ratio=risk_reward_ratio
        )
    
    def generate_report(self) -> str:
        """
        Generate text report of backtest results.
        
        Returns:
            Formatted report string
        """
        metrics = self.calculate_metrics()
        
        if not metrics:
            return "No trades to report"
        
        report = [
            "\n" + "="*80,
            "📊 BACKTEST RESULTS",
            "="*80,
            "\n💰 Returns:",
            f"   Total Return:        ${metrics.total_return:,.2f} ({metrics.total_return_pct:.2f}%)",
            f"   Annualized Return:   {metrics.annualized_return:.2f}%",
            f"   Initial Capital:     ${self.initial_capital:,.2f}",
            f"   Final Capital:       ${self.equity_curve[-1]:,.2f}",
            
            "\n📈 Trade Statistics:",
            f"   Total Trades:        {metrics.total_trades}",
            f"   Winning Trades:      {metrics.winning_trades} ({metrics.win_rate:.2f}%)",
            f"   Losing Trades:       {metrics.losing_trades} ({100-metrics.win_rate:.2f}%)",
            f"   Profit Factor:       {metrics.profit_factor:.2f}",
            
            "\n💸 Profit/Loss:",
            f"   Gross Profit:        ${metrics.gross_profit:,.2f}",
            f"   Gross Loss:          ${metrics.gross_loss:,.2f}",
            f"   Net Profit:          ${metrics.net_profit:,.2f}",
            f"   Average Win:         ${metrics.avg_win:.2f} ({metrics.avg_win_pct:.2f}%)",
            f"   Average Loss:        ${metrics.avg_loss:.2f} ({metrics.avg_loss_pct:.2f}%)",
            f"   Largest Win:         ${metrics.largest_win:.2f}",
            f"   Largest Loss:        ${metrics.largest_loss:.2f}",
            
            "\n⚠️  Risk Metrics:",
            f"   Max Drawdown:        ${metrics.max_drawdown:,.2f} ({metrics.max_drawdown_pct:.2f}%)",
            f"   Sharpe Ratio:        {metrics.sharpe_ratio:.2f}",
            f"   Sortino Ratio:       {metrics.sortino_ratio:.2f}",
            f"   Calmar Ratio:        {metrics.calmar_ratio:.2f}",
            f"   Recovery Factor:     {metrics.recovery_factor:.2f}",
            
            "\n⏱️  Time Metrics:",
            f"   Avg Trade Duration:  {metrics.avg_trade_duration_hours:.1f} hours",
            f"   Time in Market:      {metrics.total_time_in_market_pct:.1f}%",
            
            "\n🎯 Performance:",
            f"   Expectancy:          ${metrics.expectancy:.2f}",
            f"   Risk/Reward Ratio:   1:{metrics.risk_reward_ratio:.2f}",
            
            "\n" + "="*80 + "\n"
        ]
        
        return "\n".join(report)
    
    def export_results(self, filepath: str):
        """
        Export backtest results to JSON file.
        
        Args:
            filepath: Output file path
        """
        metrics = self.calculate_metrics()
        
        results = {
            "parameters": {
                "initial_capital": self.initial_capital,
                "commission": self.commission,
                "slippage": self.slippage
            },
            "metrics": asdict(metrics) if metrics else {},
            "trades": [asdict(t) for t in self.trades],
            "equity_curve": self.equity_curve,
            "timestamps": [t.isoformat() for t in self.timestamps]
        }
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"✅ Results exported to {filepath}")


# ========== USAGE EXAMPLE ==========

if __name__ == "__main__":
    # Initialize backtest
    backtest = BacktestEngine(initial_capital=10000, commission=0.001)
    
    # Simulate some trades
    start_time = datetime(2024, 1, 1)
    
    for i in range(100):
        entry_time = start_time + timedelta(days=i*2)
        exit_time = entry_time + timedelta(hours=12)
        
        # Random trade with 70% win rate
        if np.random.random() < 0.7:
            exit_price = 42000 * 1.03  # 3% profit
        else:
            exit_price = 42000 * 0.98  # 2% loss
        
        backtest.add_trade(
            entry_time=entry_time,
            exit_time=exit_time,
            symbol="BTC/USDT",
            side="long",
            entry_price=42000,
            exit_price=exit_price,
            size=0.1,
            tier=1,
            confidence=0.8
        )
    
    # Generate report
    print(backtest.generate_report())
    
    # Export results
    backtest.export_results("backtest_results.json")
