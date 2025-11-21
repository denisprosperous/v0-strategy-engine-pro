import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import json
from dataclasses import dataclass
from functools import lru_cache
from database.models import Trade, PerformanceMetrics, Strategy
from database.database import SessionLocal

# Configure logging for traceability
logger = logging.getLogger(__name__)

@dataclass
class DashboardMetrics:
    """Comprehensive dashboard metrics"""
    total_pnl: float
    total_return: float
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    sortino_ratio: float
    profit_factor: float
    avg_trade_duration: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    current_balance: float
    initial_balance: float

class PerformanceAnalytics:
    """Advanced performance analytics and metrics calculation with optimization"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._cache = {}  # OPTIMIZATION: Cache frequently computed results
    
    def calculate_comprehensive_metrics(self, trades: List[Dict]) -> DashboardMetrics:
        """Calculate comprehensive performance metrics
        
        OPTIMIZATION: Uses vectorized pandas operations instead of loops
        """
        if not trades:
            return DashboardMetrics(
                total_pnl=0.0, total_return=0.0, win_rate=0.0, sharpe_ratio=0.0,
                max_drawdown=0.0, sortino_ratio=0.0, profit_factor=0.0,
                avg_trade_duration=0.0, total_trades=0, winning_trades=0,
                losing_trades=0, avg_win=0.0, avg_loss=0.0, largest_win=0.0,
                largest_loss=0.0, current_balance=0.0, initial_balance=0.0
            )
        
        # OPTIMIZATION: Convert to DataFrame once, reuse for all operations
        df = pd.DataFrame(trades)
        
        # OPTIMIZATION: Vectorized calculations instead of loops
        total_trades = len(df)
        total_pnl = df['pnl'].sum()
        
        # Win/loss analysis - vectorized
        winning_trades = (df['pnl'] > 0).sum()
        losing_trades = (df['pnl'] < 0).sum()
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Average metrics - vectorized
        winning_mask = df['pnl'] > 0
        losing_mask = df['pnl'] < 0
        avg_win = df[winning_mask]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = df[losing_mask]['pnl'].mean() if losing_trades > 0 else 0
        largest_win = df['pnl'].max() if len(df) > 0 else 0
        largest_loss = df['pnl'].min() if len(df) > 0 else 0
        
        # Profit factor - optimized
        gross_profit = df[winning_mask]['pnl'].sum()
        gross_loss = abs(df[losing_mask]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Risk-adjusted returns
        returns = self.calculate_returns(df)
        sharpe_ratio = self.calculate_sharpe_ratio(returns)
        sortino_ratio = self.calculate_sortino_ratio(returns)
        max_drawdown = self.calculate_max_drawdown(returns)
        
        # Trade duration - vectorized
        avg_trade_duration = 0
        if 'entry_time' in df.columns and 'exit_time' in df.columns:
            df['duration'] = pd.to_datetime(df['exit_time']) - pd.to_datetime(df['entry_time'])
            avg_trade_duration = df['duration'].mean().total_seconds() / 3600  # hours
        
        # Balance calculation
        initial_balance = 10000  # Should come from configuration
        current_balance = initial_balance + total_pnl
        total_return = (current_balance - initial_balance) / initial_balance if initial_balance > 0 else 0
        
        return DashboardMetrics(
            total_pnl=total_pnl,
            total_return=total_return,
            win_rate=win_rate,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            sortino_ratio=sortino_ratio,
            profit_factor=profit_factor,
            avg_trade_duration=avg_trade_duration,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            current_balance=current_balance,
            initial_balance=initial_balance
        )
    
    def calculate_returns(self, trades_df: pd.DataFrame) -> pd.Series:
        """Calculate daily returns from trades"""
        if trades_df.empty:
            return pd.Series()
        
        trades_df['date'] = pd.to_datetime(trades_df['timestamp']).dt.date
        daily_pnl = trades_df.groupby('date')['pnl'].sum()
        
        initial_balance = 10000
        cumulative_balance = initial_balance + daily_pnl.cumsum()
        returns = daily_pnl / cumulative_balance.shift(1)
        
        return returns.dropna()
    
    def calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) < 2:
            return 0.0
        
        excess_returns = returns - risk_free_rate / 252
        std_dev = excess_returns.std()
        if std_dev > 0:
            return (excess_returns.mean() / std_dev) * np.sqrt(252)
        return 0.0
    
    def calculate_sortino_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio"""
        if len(returns) < 2:
            return 0.0
        
        excess_returns = returns - risk_free_rate / 252
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0:
            return float('inf')
        
        downside_deviation = downside_returns.std()
        if downside_deviation > 0:
            return (excess_returns.mean() / downside_deviation) * np.sqrt(252)
        return 0.0
    
    def calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown"""
        if len(returns) < 2:
            return 0.0
        
        cumulative_returns = (1 + returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        
        return abs(drawdown.min())
    
    def generate_performance_report(self, trades: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        metrics = self.calculate_comprehensive_metrics(trades)
        grade = self.calculate_performance_grade(metrics)
        risk_assessment = self.assess_risk(metrics)
        strategy_analysis = self.analyze_strategies(trades)
        time_analysis = self.analyze_time_performance(trades)
        
        return {
            'metrics': {
                'total_pnl': metrics.total_pnl,
                'total_return': metrics.total_return,
                'win_rate': metrics.win_rate,
                'sharpe_ratio': metrics.sharpe_ratio,
                'max_drawdown': metrics.max_drawdown,
                'sortino_ratio': metrics.sortino_ratio,
                'profit_factor': metrics.profit_factor,
                'total_trades': metrics.total_trades,
                'winning_trades': metrics.winning_trades,
                'losing_trades': metrics.losing_trades,
                'avg_win': metrics.avg_win,
                'avg_loss': metrics.avg_loss,
                'largest_win': metrics.largest_win,
                'largest_loss': metrics.largest_loss,
                'current_balance': metrics.current_balance,
                'initial_balance': metrics.initial_balance
            },
            'grade': grade,
            'risk_assessment': risk_assessment,
            'strategy_analysis': strategy_analysis,
            'time_analysis': time_analysis,
            'recommendations': self.generate_recommendations(metrics)
        }
    
    def calculate_performance_grade(self, metrics: DashboardMetrics) -> str:
        """Calculate performance grade (A-F)"""
        score = 0
        score += min(30, int(max(0, metrics.win_rate - 0.4) * 150))
        score += min(25, int(max(0, metrics.sharpe_ratio) * 12.5))
        score += min(25, int(max(0, metrics.profit_factor - 1.0) * 25))
        score += max(0, 20 - int(metrics.max_drawdown * 200))
        
        grade_mapping = [
            (100, 'A+'), (85, 'A'), (80, 'A-'), (75, 'B+'),
            (70, 'B'), (65, 'B-'), (60, 'C+'), (55, 'C'),
            (50, 'C-'), (45, 'D+'), (40, 'D'), (0, 'F')
        ]
        
        for threshold, grade in grade_mapping:
            if score >= threshold:
                return grade
        return 'F'
    
    def assess_risk(self, metrics: DashboardMetrics) -> Dict[str, Any]:
        """Assess trading risk"""
        risk_score = 0
        
        if metrics.max_drawdown > 0.20:
            risk_score += 40
        elif metrics.max_drawdown > 0.15:
            risk_score += 30
        elif metrics.max_drawdown > 0.10:
            risk_score += 20
        else:
            risk_score += 10
        
        if metrics.sharpe_ratio < 0.5:
            risk_score += 30
        elif metrics.sharpe_ratio < 1.0:
            risk_score += 20
        elif metrics.sharpe_ratio < 1.5:
            risk_score += 10
        
        if metrics.win_rate < 0.4:
            risk_score += 30
        elif metrics.win_rate < 0.5:
            risk_score += 20
        elif metrics.win_rate < 0.6:
            risk_score += 10
        
        if risk_score >= 70:
            risk_level = 'high'
        elif risk_score >= 40:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'max_drawdown_risk': 'high' if metrics.max_drawdown > 0.15 else 'medium' if metrics.max_drawdown > 0.10 else 'low',
            'volatility_risk': 'high' if metrics.sharpe_ratio < 0.5 else 'medium' if metrics.sharpe_ratio < 1.0 else 'low',
            'win_rate_risk': 'high' if metrics.win_rate < 0.4 else 'medium' if metrics.win_rate < 0.5 else 'low'
        }
    
    def analyze_strategies(self, trades: List[Dict]) -> Dict[str, Any]:
        """Analyze performance by strategy"""
        if not trades:
            return {}
        
        df = pd.DataFrame(trades)
        if 'strategy' in df.columns:
            strategy_performance = df.groupby('strategy').agg({
                'pnl': ['sum', 'mean', 'count'],
                'signal_confidence': 'mean'
            }).round(2)
            
            return {
                'strategy_breakdown': strategy_performance.to_dict(),
                'best_strategy': strategy_performance['pnl']['sum'].idxmax() if len(strategy_performance) > 0 else None,
                'worst_strategy': strategy_performance['pnl']['sum'].idxmin() if len(strategy_performance) > 0 else None
            }
        
        return {}
    
    def analyze_time_performance(self, trades: List[Dict]) -> Dict[str, Any]:
        """Analyze performance over time"""
        if not trades:
            return {}
        
        df = pd.DataFrame(trades)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.day_name()
        
        daily_performance = df.groupby('date')['pnl'].sum()
        hourly_performance = df.groupby('hour')['pnl'].sum()
        dow_performance = df.groupby('day_of_week')['pnl'].sum()
        
        return {
            'daily_performance': daily_performance.to_dict(),
            'hourly_performance': hourly_performance.to_dict(),
            'day_of_week_performance': dow_performance.to_dict(),
            'best_hour': hourly_performance.idxmax() if len(hourly_performance) > 0 else None,
            'worst_hour': hourly_performance.idxmin() if len(hourly_performance) > 0 else None,
            'best_day': dow_performance.idxmax() if len(dow_performance) > 0 else None,
            'worst_day': dow_performance.idxmin() if len(dow_performance) > 0 else None
        }
    
    def generate_recommendations(self, metrics: DashboardMetrics) -> List[str]:
        """Generate trading recommendations based on performance"""
        recommendations = []
        
        if metrics.win_rate < 0.4:
            recommendations.append("Improve entry/exit criteria to increase win rate")
        elif metrics.win_rate > 0.7:
            recommendations.append("Excellent win rate - consider increasing position sizes")
        
        if metrics.max_drawdown > 0.15:
            recommendations.append("Reduce position sizes or improve stop-loss management")
        
        if metrics.profit_factor < 1.2:
            recommendations.append("Focus on improving risk-reward ratio of trades")
        
        if metrics.total_trades < 10:
            recommendations.append("Insufficient data - continue trading to gather more statistics")
        elif metrics.total_trades > 100:
            recommendations.append("Consider reducing trade frequency to focus on quality")
        
        if metrics.sharpe_ratio < 1.0:
            recommendations.append("Diversify strategies to improve risk-adjusted returns")
        
        return recommendations

class DashboardManager:
    """Manages dashboard data and visualizations"""
    
    def __init__(self):
        self.analytics = PerformanceAnalytics()
        self.logger = logging.getLogger(__name__)
    
    def get_dashboard_data(self, user_id: Optional[int] = None, period: str = "all") -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        try:
            db = SessionLocal()
            query = db.query(Trade)
            if user_id:
                query = query.filter(Trade.user_id == user_id)
            
            if period != "all":
                start_date = self.get_start_date(period)
                query = query.filter(Trade.timestamp >= start_date)
            
            trades = query.all()
            trades_data = []
            for trade in trades:
                trades_data.append({
                    'symbol': trade.symbol,
                    'side': trade.side,
                    'amount': trade.amount,
                    'price': trade.price,
                    'pnl': trade.pnl or 0,
                    'timestamp': trade.timestamp.isoformat(),
                    'strategy': trade.strategy.name if trade.strategy else None,
                    'signal_confidence': 0.5
                })
            
            performance_report = self.analytics.generate_performance_report(trades_data)
            
            dashboard_data = {
                'performance': performance_report,
                'recent_trades': self.get_recent_trades(db, user_id),
                'top_performers': self.get_top_performers(trades_data),
                'risk_metrics': self.get_risk_metrics(trades_data),
                'trading_activity': self.get_trading_activity(trades_data),
                'portfolio_allocation': self.get_portfolio_allocation(trades_data)
            }
            
            return dashboard_data
        
        except Exception as e:
            self.logger.error(f"Error getting dashboard data: {e}")
            return {}
        finally:
            db.close()
    
    def get_start_date(self, period: str) -> datetime:
        """Get start date for period filter"""
        now = datetime.now()
        
        if period == "1d":
            return now - timedelta(days=1)
        elif period == "1w":
            return now - timedelta(weeks=1)
        elif period == "1m":
            return now - timedelta(days=30)
        elif period == "3m":
            return now - timedelta(days=90)
        elif period == "6m":
            return now - timedelta(days=180)
        elif period == "1y":
            return now - timedelta(days=365)
        else:
            return datetime.min
    
    def get_recent_trades(self, db, user_id: Optional[int] = None) -> List[Dict]:
        """Get recent trades for dashboard"""
        query = db.query(Trade).order_by(Trade.timestamp.desc()).limit(10)
        if user_id:
            query = query.filter(Trade.user_id == user_id)
        
        trades = query.all()
        return [
            {
                'symbol': trade.symbol,
                'side': trade.side,
                'amount': trade.amount,
                'price': trade.price,
                'pnl': trade.pnl,
                'timestamp': trade.timestamp.isoformat(),
                'status': trade.status
            }
            for trade in trades
        ]
    
    def get_top_performers(self, trades: List[Dict]) -> List[Dict]:
        """Get top performing symbols"""
        if not trades:
            return []
        
        df = pd.DataFrame(trades)
        symbol_performance = df.groupby('symbol')['pnl'].sum().sort_values(ascending=False)
        
        return [
            {
                'symbol': symbol,
                'total_pnl': pnl,
                'trade_count': len(df[df['symbol'] == symbol])
            }
            for symbol, pnl in symbol_performance.head(5).items()
        ]
    
    def get_risk_metrics(self, trades: List[Dict]) -> Dict[str, Any]:
        """Get risk metrics for dashboard"""
        if not trades:
            return {}
        
        df = pd.DataFrame(trades)
        returns = self.analytics.calculate_returns(df)
        
        return {
            'var_95': np.percentile(returns, 5) if len(returns) > 0 else 0,
            'var_99': np.percentile(returns, 1) if len(returns) > 0 else 0,
            'volatility': returns.std() * np.sqrt(252) if len(returns) > 0 else 0,
            'beta': 1.0,
            'correlation': 0.5
        }
    
    def get_trading_activity(self, trades: List[Dict]) -> Dict[str, Any]:
        """Get trading activity metrics"""
        if not trades:
            return {}
        
        df = pd.DataFrame(trades)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        daily_activity = df.groupby(df['timestamp'].dt.date).size()
        hourly_activity = df.groupby(df['timestamp'].dt.hour).size()
        
        return {
            'daily_activity': daily_activity.to_dict(),
            'hourly_activity': hourly_activity.to_dict(),
            'total_trades_today': len(df[df['timestamp'].dt.date == datetime.now().date()]),
            'avg_trades_per_day': len(df) / max(1, (df['timestamp'].max() - df['timestamp'].min()).days)
        }
    
    def get_portfolio_allocation(self, trades: List[Dict]) -> List[Dict]:
        """Get current portfolio allocation"""
        if not trades:
            return []
        
        df = pd.DataFrame(trades)
        
        current_positions = {}
        for _, trade in df.iterrows():
            symbol = trade['symbol']
            if symbol not in current_positions:
                current_positions[symbol] = 0
            
            if trade['side'] == 'buy':
                current_positions[symbol] += trade['amount']
            else:
                current_positions[symbol] -= trade['amount']
        
        total_value = sum(abs(value) for value in current_positions.values())
        
        return [
            {
                'symbol': symbol,
                'allocation': abs(value) / total_value if total_value > 0 else 0,
                'value': abs(value)
            }
            for symbol, value in current_positions.items()
            if abs(value) > 0
        ]

# Module-level singleton
_dashboard = DashboardManager()

def get_dashboard() -> DashboardManager:
    """Get dashboard singleton instance"""
    return _dashboard
