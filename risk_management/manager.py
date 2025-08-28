import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

@dataclass
class RiskParameters:
    """Risk management parameters"""
    max_position_size: float = 0.05  # 5% of portfolio per position
    max_portfolio_risk: float = 0.02  # 2% risk per trade
    max_drawdown: float = 0.15  # 15% max drawdown
    max_open_trades: int = 10
    max_daily_loss: float = 0.05  # 5% daily loss limit
    correlation_threshold: float = 0.7  # Max correlation between positions
    volatility_threshold: float = 0.5  # Max volatility for position
    leverage_limit: float = 3.0  # Max leverage
    stop_loss_pct: float = 0.02  # 2% stop loss
    take_profit_pct: float = 0.06  # 6% take profit

class RiskManager:
    """Advanced risk management system"""
    
    def __init__(self, initial_balance: float, risk_params: RiskParameters = None):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.risk_params = risk_params or RiskParameters()
        self.positions = []
        self.trade_history = []
        self.daily_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_balance = initial_balance
        
        # Risk metrics tracking
        self.var_95 = 0.0  # 95% Value at Risk
        self.var_99 = 0.0  # 99% Value at Risk
        self.volatility = 0.0
        self.sharpe_ratio = 0.0
        self.correlation_matrix = pd.DataFrame()
        
        self.logger = logging.getLogger(__name__)
    
    def calculate_position_size(self, entry_price: float, stop_loss_price: float, 
                               symbol: str, exchange: str) -> float:
        """Calculate optimal position size based on risk parameters"""
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss_price)
        
        if risk_per_share == 0:
            self.logger.warning(f"Invalid stop loss for {symbol}")
            return 0.0
        
        # Calculate dollar risk
        dollar_risk = self.current_balance * self.risk_params.max_portfolio_risk
        
        # Calculate position size based on risk
        position_size = dollar_risk / risk_per_share
        
        # Apply position size limits
        max_position_value = self.current_balance * self.risk_params.max_position_size
        max_position_size = max_position_value / entry_price
        
        position_size = min(position_size, max_position_size)
        
        # Check open trades limit
        if len(self.get_open_positions()) >= self.risk_params.max_open_trades:
            self.logger.warning(f"Maximum open trades limit reached for {symbol}")
            return 0.0
        
        # Check correlation limits
        if not self.check_correlation_limits(symbol):
            self.logger.warning(f"Correlation limit exceeded for {symbol}")
            return 0.0
        
        # Check volatility limits
        if not self.check_volatility_limits(symbol):
            self.logger.warning(f"Volatility limit exceeded for {symbol}")
            return 0.0
        
        return position_size
    
    def check_drawdown(self) -> bool:
        """Check if current drawdown exceeds limits"""
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        current_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
        self.max_drawdown = max(self.max_drawdown, current_drawdown)
        
        if current_drawdown > self.risk_params.max_drawdown:
            self.logger.critical(f"Maximum drawdown exceeded: {current_drawdown:.2%}")
            return False
        
        return True
    
    def check_daily_loss(self) -> bool:
        """Check if daily loss limit exceeded"""
        daily_loss_pct = abs(self.daily_pnl) / self.initial_balance
        
        if daily_loss_pct > self.risk_params.max_daily_loss:
            self.logger.critical(f"Daily loss limit exceeded: {daily_loss_pct:.2%}")
            return False
        
        return True
    
    def check_correlation_limits(self, new_symbol: str) -> bool:
        """Check if new position would exceed correlation limits"""
        if len(self.positions) == 0:
            return True
        
        # Calculate correlation with existing positions
        correlations = []
        for position in self.positions:
            if position['symbol'] != new_symbol:
                # This would require historical price data
                # For now, use a simplified check
                correlation = self.calculate_correlation(new_symbol, position['symbol'])
                correlations.append(correlation)
        
        if correlations and max(correlations) > self.risk_params.correlation_threshold:
            return False
        
        return True
    
    def check_volatility_limits(self, symbol: str) -> bool:
        """Check if symbol volatility is within limits"""
        # Calculate historical volatility
        volatility = self.calculate_volatility(symbol)
        
        if volatility > self.risk_params.volatility_threshold:
            return False
        
        return True
    
    def calculate_correlation(self, symbol1: str, symbol2: str) -> float:
        """Calculate correlation between two symbols"""
        # This would require historical price data
        # For now, return a random correlation
        return np.random.uniform(0, 1)
    
    def calculate_volatility(self, symbol: str) -> float:
        """Calculate historical volatility for a symbol"""
        # This would require historical price data
        # For now, return a random volatility
        return np.random.uniform(0, 1)
    
    def update_risk_metrics(self) -> None:
        """Update risk metrics based on current positions"""
        if not self.trade_history:
            return
        
        # Calculate returns
        returns = pd.Series([trade['pnl'] for trade in self.trade_history])
        
        # Calculate VaR
        self.var_95 = np.percentile(returns, 5)
        self.var_99 = np.percentile(returns, 1)
        
        # Calculate volatility
        self.volatility = returns.std()
        
        # Calculate Sharpe ratio
        if self.volatility > 0:
            self.sharpe_ratio = returns.mean() / self.volatility
        
        # Update correlation matrix
        self.update_correlation_matrix()
    
    def update_correlation_matrix(self) -> None:
        """Update correlation matrix for all positions"""
        if len(self.positions) < 2:
            return
        
        # This would require historical price data for all symbols
        # For now, create a dummy correlation matrix
        symbols = [pos['symbol'] for pos in self.positions]
        n = len(symbols)
        
        # Create random correlation matrix
        corr_matrix = np.random.uniform(-1, 1, (n, n))
        np.fill_diagonal(corr_matrix, 1)  # Diagonal should be 1
        
        self.correlation_matrix = pd.DataFrame(corr_matrix, index=symbols, columns=symbols)
    
    def add_position(self, symbol: str, side: str, amount: float, 
                    entry_price: float, stop_loss: float, take_profit: float) -> None:
        """Add a new position to tracking"""
        position = {
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'entry_time': datetime.now(),
            'pnl': 0.0,
            'status': 'open'
        }
        
        self.positions.append(position)
        self.logger.info(f"Added position: {symbol} {side} {amount} @ {entry_price}")
    
    def update_position(self, symbol: str, current_price: float) -> None:
        """Update position PnL and check stop loss/take profit"""
        for position in self.positions:
            if position['symbol'] == symbol and position['status'] == 'open':
                # Calculate PnL
                if position['side'] == 'buy':
                    position['pnl'] = (current_price - position['entry_price']) * position['amount']
                else:
                    position['pnl'] = (position['entry_price'] - current_price) * position['amount']
                
                # Check stop loss
                if position['side'] == 'buy' and current_price <= position['stop_loss']:
                    position['status'] = 'stopped_out'
                    self.logger.warning(f"Stop loss triggered for {symbol}")
                elif position['side'] == 'sell' and current_price >= position['stop_loss']:
                    position['status'] = 'stopped_out'
                    self.logger.warning(f"Stop loss triggered for {symbol}")
                
                # Check take profit
                if position['side'] == 'buy' and current_price >= position['take_profit']:
                    position['status'] = 'take_profit'
                    self.logger.info(f"Take profit triggered for {symbol}")
                elif position['side'] == 'sell' and current_price <= position['take_profit']:
                    position['status'] = 'take_profit'
                    self.logger.info(f"Take profit triggered for {symbol}")
    
    def close_position(self, symbol: str, exit_price: float) -> float:
        """Close a position and return PnL"""
        for position in self.positions:
            if position['symbol'] == symbol and position['status'] == 'open':
                # Calculate final PnL
                if position['side'] == 'buy':
                    pnl = (exit_price - position['entry_price']) * position['amount']
                else:
                    pnl = (position['entry_price'] - exit_price) * position['amount']
                
                # Update position
                position['status'] = 'closed'
                position['exit_price'] = exit_price
                position['exit_time'] = datetime.now()
                position['pnl'] = pnl
                
                # Update balance and metrics
                self.current_balance += pnl
                self.daily_pnl += pnl
                
                # Add to trade history
                self.trade_history.append({
                    'symbol': symbol,
                    'side': position['side'],
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'amount': position['amount'],
                    'pnl': pnl,
                    'entry_time': position['entry_time'],
                    'exit_time': position['exit_time']
                })
                
                self.logger.info(f"Closed position: {symbol} PnL: {pnl:.2f}")
                return pnl
        
        return 0.0
    
    def get_open_positions(self) -> List[Dict]:
        """Get all open positions"""
        return [pos for pos in self.positions if pos['status'] == 'open']
    
    def get_risk_report(self) -> Dict:
        """Generate comprehensive risk report"""
        return {
            'current_balance': self.current_balance,
            'total_pnl': self.current_balance - self.initial_balance,
            'max_drawdown': self.max_drawdown,
            'daily_pnl': self.daily_pnl,
            'open_positions': len(self.get_open_positions()),
            'var_95': self.var_95,
            'var_99': self.var_99,
            'volatility': self.volatility,
            'sharpe_ratio': self.sharpe_ratio,
            'risk_limits': {
                'max_drawdown': self.risk_params.max_drawdown,
                'max_daily_loss': self.risk_params.max_daily_loss,
                'max_position_size': self.risk_params.max_position_size,
                'max_open_trades': self.risk_params.max_open_trades
            }
        }
    
    def reset_daily_metrics(self) -> None:
        """Reset daily metrics (call at start of new day)"""
        self.daily_pnl = 0.0
        self.logger.info("Daily metrics reset")
    
    def emergency_stop(self) -> None:
        """Emergency stop - close all positions"""
        self.logger.critical("EMERGENCY STOP ACTIVATED - Closing all positions")
        
        for position in self.get_open_positions():
            # This would trigger immediate market orders to close positions
            self.logger.warning(f"Emergency closing position: {position['symbol']}")
            
        # Reset risk parameters to conservative levels
        self.risk_params.max_position_size = 0.01  # 1%
        self.risk_params.max_portfolio_risk = 0.005  # 0.5%
        self.risk_params.max_open_trades = 1
