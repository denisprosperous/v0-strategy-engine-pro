import asyncio
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from enum import Enum

from signals.signal_system import TradingSignal, SignalManager
from risk_management.manager import RiskManager
from exchanges.base_exchange import BaseExchange, Order

class TradingMode(Enum):
    AUTO = "auto"
    MANUAL = "manual"
    SEMI_AUTO = "semi_auto"
    PAPER_TRADING = "paper_trading"
    BACKTEST = "backtest"

@dataclass
class TradingConfig:
    """Trading configuration parameters"""
    mode: TradingMode
    max_positions: int = 10
    position_size_pct: float = 0.02  # 2% per position
    stop_loss_pct: float = 0.02  # 2% stop loss
    take_profit_pct: float = 0.06  # 6% take profit
    max_daily_trades: int = 50
    trading_hours: Dict[str, List[int]] = None  # Trading hours by day
    confirmation_required: bool = False
    auto_rebalance: bool = False
    rebalance_frequency: str = "daily"  # daily, weekly, monthly

class TradingModeManager:
    """Manages different trading modes and their behaviors"""
    
    def __init__(self, exchanges: List[BaseExchange], risk_manager: RiskManager, signal_manager: SignalManager):
        self.exchanges = exchanges
        self.risk_manager = risk_manager
        self.signal_manager = signal_manager
        self.config = TradingConfig(mode=TradingMode.MANUAL)
        self.logger = logging.getLogger(__name__)
        
        # Trading state
        self.is_trading = False
        self.current_positions = {}
        self.daily_trade_count = 0
        self.last_rebalance = datetime.now()
        
        # Callbacks for manual mode
        self.signal_callback = None
        self.execution_callback = None
        
        # Performance tracking
        self.trade_history = []
        self.performance_metrics = {}
    
    def set_mode(self, mode: TradingMode, config: Optional[TradingConfig] = None):
        """Set trading mode and configuration"""
        self.config.mode = mode
        if config:
            self.config = config
        
        self.logger.info(f"Trading mode set to: {mode.value}")
        
        # Stop current trading if switching modes
        if self.is_trading:
            self.stop_trading()
    
    def start_trading(self):
        """Start trading based on current mode"""
        if self.is_trading:
            self.logger.warning("Trading already active")
            return
        
        self.is_trading = True
        self.logger.info(f"Started trading in {self.config.mode.value} mode")
        
        if self.config.mode == TradingMode.AUTO:
            asyncio.create_task(self.auto_trading_loop())
        elif self.config.mode == TradingMode.SEMI_AUTO:
            asyncio.create_task(self.semi_auto_trading_loop())
        elif self.config.mode == TradingMode.PAPER_TRADING:
            asyncio.create_task(self.paper_trading_loop())
    
    def stop_trading(self):
        """Stop all trading activities"""
        self.is_trading = False
        self.logger.info("Trading stopped")
    
    async def auto_trading_loop(self):
        """Fully automated trading loop"""
        while self.is_trading:
            try:
                # Check trading hours
                if not self.is_trading_hours():
                    await asyncio.sleep(300)  # 5 minutes
                    continue
                
                # Check daily limits
                if self.daily_trade_count >= self.config.max_daily_trades:
                    self.logger.info("Daily trade limit reached")
                    await asyncio.sleep(3600)  # 1 hour
                    continue
                
                # Get market data for all symbols
                symbols = self.get_trading_symbols()
                market_data = await self.get_market_data(symbols)
                
                # Generate signals
                signals = await self.signal_manager.get_top_signals(symbols, market_data, limit=5)
                
                # Process signals
                for signal in signals:
                    if not self.is_trading:
                        break
                    
                    await self.process_signal_auto(signal, market_data.get(signal.symbol))
                
                # Auto rebalancing
                if self.config.auto_rebalance and self.should_rebalance():
                    await self.rebalance_portfolio()
                
                await asyncio.sleep(60)  # 1 minute delay
                
            except Exception as e:
                self.logger.error(f"Error in auto trading loop: {e}")
                await asyncio.sleep(300)  # 5 minutes on error
    
    async def semi_auto_trading_loop(self):
        """Semi-automated trading with confirmation"""
        while self.is_trading:
            try:
                # Check trading hours
                if not self.is_trading_hours():
                    await asyncio.sleep(300)
                    continue
                
                # Get market data and signals
                symbols = self.get_trading_symbols()
                market_data = await self.get_market_data(symbols)
                signals = await self.signal_manager.get_top_signals(symbols, market_data, limit=3)
                
                # Send signals for confirmation
                for signal in signals:
                    if not self.is_trading:
                        break
                    
                    if self.signal_callback:
                        await self.signal_callback(signal)
                    
                    # Wait for confirmation (timeout after 5 minutes)
                    confirmation = await self.wait_for_confirmation(signal, timeout=300)
                    
                    if confirmation:
                        await self.process_signal_auto(signal, market_data.get(signal.symbol))
                
                await asyncio.sleep(120)  # 2 minutes delay
                
            except Exception as e:
                self.logger.error(f"Error in semi-auto trading loop: {e}")
                await asyncio.sleep(300)
    
    async def paper_trading_loop(self):
        """Paper trading mode for testing strategies"""
        while self.is_trading:
            try:
                # Similar to auto trading but without real execution
                symbols = self.get_trading_symbols()
                market_data = await self.get_market_data(symbols)
                signals = await self.signal_manager.get_top_signals(symbols, market_data, limit=5)
                
                for signal in signals:
                    if not self.is_trading:
                        break
                    
                    await self.process_signal_paper(signal, market_data.get(signal.symbol))
                
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error in paper trading loop: {e}")
                await asyncio.sleep(300)
    
    async def process_signal_auto(self, signal: TradingSignal, market_data: Optional[pd.DataFrame]):
        """Process signal in automatic mode"""
        try:
            # Risk checks
            if not self.risk_manager.check_drawdown():
                self.logger.warning("Maximum drawdown exceeded, skipping signal")
                return
            
            if not self.risk_manager.check_daily_loss():
                self.logger.warning("Daily loss limit exceeded, skipping signal")
                return
            
            # Position size calculation
            current_price = market_data['close'].iloc[-1] if market_data is not None else 0
            if current_price == 0:
                self.logger.warning("No price data available for signal")
                return
            
            stop_loss_price = current_price * (1 - self.config.stop_loss_pct) if signal.direction == 'buy' else current_price * (1 + self.config.stop_loss_pct)
            position_size = self.risk_manager.calculate_position_size(current_price, stop_loss_price, signal.symbol, "auto")
            
            if position_size <= 0:
                self.logger.warning("Position size too small, skipping signal")
                return
            
            # Execute trade
            order = Order(
                symbol=signal.symbol,
                order_type='market',
                side=signal.direction,
                amount=position_size,
                price=current_price
            )
            
            # Execute on primary exchange
            primary_exchange = self.exchanges[0]
            result = primary_exchange.place_order(order)
            
            if result:
                self.daily_trade_count += 1
                self.logger.info(f"Auto trade executed: {signal.symbol} {signal.direction} {position_size}")
                
                # Update position tracking
                self.current_positions[signal.symbol] = {
                    'side': signal.direction,
                    'amount': position_size,
                    'entry_price': current_price,
                    'stop_loss': stop_loss_price,
                    'take_profit': current_price * (1 + self.config.take_profit_pct) if signal.direction == 'buy' else current_price * (1 - self.config.take_profit_pct),
                    'timestamp': datetime.now(),
                    'signal': signal
                }
                
                # Add to trade history
                self.trade_history.append({
                    'symbol': signal.symbol,
                    'side': signal.direction,
                    'amount': position_size,
                    'price': current_price,
                    'timestamp': datetime.now(),
                    'mode': 'auto',
                    'signal_confidence': signal.confidence
                })
            
        except Exception as e:
            self.logger.error(f"Error processing auto signal: {e}")
    
    async def process_signal_paper(self, signal: TradingSignal, market_data: Optional[pd.DataFrame]):
        """Process signal in paper trading mode"""
        try:
            current_price = market_data['close'].iloc[-1] if market_data is not None else 0
            if current_price == 0:
                return
            
            # Simulate position size calculation
            position_size = 1000 / current_price  # Simulate $1000 position
            
            # Simulate trade execution
            self.logger.info(f"Paper trade: {signal.symbol} {signal.direction} {position_size:.4f} @ {current_price}")
            
            # Update paper trading positions
            self.current_positions[signal.symbol] = {
                'side': signal.direction,
                'amount': position_size,
                'entry_price': current_price,
                'timestamp': datetime.now(),
                'signal': signal,
                'paper_trade': True
            }
            
            # Add to trade history
            self.trade_history.append({
                'symbol': signal.symbol,
                'side': signal.direction,
                'amount': position_size,
                'price': current_price,
                'timestamp': datetime.now(),
                'mode': 'paper',
                'signal_confidence': signal.confidence
            })
            
        except Exception as e:
            self.logger.error(f"Error processing paper signal: {e}")
    
    async def manual_trade(self, symbol: str, side: str, amount: float, price: Optional[float] = None):
        """Execute manual trade"""
        try:
            if not self.is_trading:
                self.logger.warning("Trading not active")
                return False
            
            # Risk checks
            if not self.risk_manager.check_drawdown():
                self.logger.warning("Maximum drawdown exceeded")
                return False
            
            # Create order
            order = Order(
                symbol=symbol,
                order_type='market' if price is None else 'limit',
                side=side,
                amount=amount,
                price=price
            )
            
            # Execute on primary exchange
            primary_exchange = self.exchanges[0]
            result = primary_exchange.place_order(order)
            
            if result:
                self.daily_trade_count += 1
                self.logger.info(f"Manual trade executed: {symbol} {side} {amount}")
                
                # Update position tracking
                self.current_positions[symbol] = {
                    'side': side,
                    'amount': amount,
                    'entry_price': price or result.get('price', 0),
                    'timestamp': datetime.now(),
                    'manual_trade': True
                }
                
                # Add to trade history
                self.trade_history.append({
                    'symbol': symbol,
                    'side': side,
                    'amount': amount,
                    'price': price or result.get('price', 0),
                    'timestamp': datetime.now(),
                    'mode': 'manual'
                })
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error executing manual trade: {e}")
            return False
    
    async def wait_for_confirmation(self, signal: TradingSignal, timeout: int = 300) -> bool:
        """Wait for manual confirmation of signal"""
        # This would integrate with the Telegram bot or web interface
        # For now, return True after a short delay
        await asyncio.sleep(5)
        return True
    
    def is_trading_hours(self) -> bool:
        """Check if current time is within trading hours"""
        if not self.config.trading_hours:
            return True  # Always trade if no hours specified
        
        now = datetime.now()
        day = now.strftime('%A').lower()
        hour = now.hour
        
        if day in self.config.trading_hours:
            return hour in self.config.trading_hours[day]
        
        return True
    
    def should_rebalance(self) -> bool:
        """Check if portfolio should be rebalanced"""
        if not self.config.auto_rebalance:
            return False
        
        if self.config.rebalance_frequency == "daily":
            return (datetime.now() - self.last_rebalance).days >= 1
        elif self.config.rebalance_frequency == "weekly":
            return (datetime.now() - self.last_rebalance).days >= 7
        elif self.config.rebalance_frequency == "monthly":
            return (datetime.now() - self.last_rebalance).days >= 30
        
        return False
    
    async def rebalance_portfolio(self):
        """Rebalance portfolio based on strategy"""
        try:
            self.logger.info("Starting portfolio rebalancing")
            
            # Get current positions
            positions = self.current_positions.copy()
            
            # Calculate target allocations (simplified)
            total_value = sum(pos['amount'] * pos['entry_price'] for pos in positions.values())
            target_allocation = total_value / len(positions) if positions else 0
            
            # Rebalance positions
            for symbol, position in positions.items():
                current_value = position['amount'] * position['entry_price']
                target_value = target_allocation
                
                if abs(current_value - target_value) / current_value > 0.1:  # 10% threshold
                    # Calculate adjustment
                    if current_value > target_value:
                        # Sell excess
                        excess_amount = (current_value - target_value) / position['entry_price']
                        await self.manual_trade(symbol, 'sell', excess_amount)
                    else:
                        # Buy more
                        deficit_amount = (target_value - current_value) / position['entry_price']
                        await self.manual_trade(symbol, 'buy', deficit_amount)
            
            self.last_rebalance = datetime.now()
            self.logger.info("Portfolio rebalancing completed")
            
        except Exception as e:
            self.logger.error(f"Error during portfolio rebalancing: {e}")
    
    def get_trading_symbols(self) -> List[str]:
        """Get list of symbols to trade"""
        # This would be configurable
        return ['BTC/USDT', 'ETH/USDT', 'ADA/USDT', 'DOT/USDT', 'LINK/USDT']
    
    async def get_market_data(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """Get market data for symbols"""
        market_data = {}
        
        for symbol in symbols:
            try:
                # Get data from primary exchange
                exchange = self.exchanges[0]
                data = exchange.get_historical_data(symbol, '1h', 100)
                market_data[symbol] = data
            except Exception as e:
                self.logger.error(f"Error getting market data for {symbol}: {e}")
        
        return market_data
    
    def get_trading_status(self) -> Dict:
        """Get current trading status"""
        return {
            'mode': self.config.mode.value,
            'is_trading': self.is_trading,
            'daily_trades': self.daily_trade_count,
            'open_positions': len(self.current_positions),
            'last_rebalance': self.last_rebalance.isoformat(),
            'performance': self.calculate_performance()
        }
    
    def calculate_performance(self) -> Dict:
        """Calculate trading performance metrics"""
        if not self.trade_history:
            return {}
        
        total_trades = len(self.trade_history)
        winning_trades = len([t for t in self.trade_history if t.get('pnl', 0) > 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_pnl = sum(t.get('pnl', 0) for t in self.trade_history)
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_trade_pnl': total_pnl / total_trades if total_trades > 0 else 0
        }
    
    def set_signal_callback(self, callback: Callable):
        """Set callback for signal notifications"""
        self.signal_callback = callback
    
    def set_execution_callback(self, callback: Callable):
        """Set callback for trade execution notifications"""
        self.execution_callback = callback
