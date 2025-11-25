"""
Trading Mode Manager

Unified trading mode system supporting multiple execution strategies:
- MANUAL: User-initiated trades via Telegram or web dashboard
- SEMI_AUTO: Signal alerts with user confirmation required
- FULL_AUTO: Automatic execution of validated signals

Integrates with:
- signal_generation/execution_engine_integrated.py
- telegram_integration/alert_manager.py
- Web dashboard (future integration)

Features:
- Mode switching (manual/semi-auto/full-auto)
- User confirmation flows for semi-auto mode
- Manual trade commands via Telegram
- Web dashboard API endpoints for manual trading
- Signal routing based on active mode
- Trade execution with user preferences

Usage:
    manager = TradingModeManager()
    await manager.start()
    
    # Switch to semi-auto mode
    await manager.set_mode(TradingMode.SEMI_AUTO)
    
    # Process incoming signal
    await manager.handle_signal(trading_signal)
    
    # Manual trade via Telegram
    await manager.execute_manual_trade(
        symbol="BTC/USDT",
        direction="long",
        size=1000
    )

Author: v0-strategy-engine-pro
Version: 1.0 (RUN 13)
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

# Import execution engine
try:
    from signal_generation.execution_engine_integrated import (
        IntegratedExecutionEngine,
        TradingSignal,
        SignalDirection
    )
except ImportError:
    from execution_engine_integrated import (
        IntegratedExecutionEngine,
        TradingSignal,
        SignalDirection
    )

# Import Telegram integration
try:
    from telegram_integration.alert_manager import AlertManager
    from telegram_integration import initialize_telegram_alerts
except ImportError:
    AlertManager = None
    initialize_telegram_alerts = None


logger = logging.getLogger(__name__)


class TradingMode(Enum):
    """Trading execution modes."""
    MANUAL = 'manual'  # User initiates all trades
    SEMI_AUTO = 'semi_auto'  # Signals sent, user confirms
    FULL_AUTO = 'full_auto'  # Automatic execution


class TradeSource(Enum):
    """Source of trade request."""
    TELEGRAM = 'telegram'  # User command via Telegram
    WEB_DASHBOARD = 'web'  # User action on web dashboard
    SIGNAL_AUTO = 'signal_auto'  # Automatic from signal
    SIGNAL_CONFIRMED = 'signal_confirmed'  # User confirmed signal


@dataclass
class PendingSignal:
    """Signal awaiting user confirmation in semi-auto mode."""
    signal: TradingSignal
    timestamp: datetime
    message_id: Optional[int] = None
    timeout_seconds: int = 300  # 5 minutes default
    
    def is_expired(self) -> bool:
        """Check if signal confirmation has expired."""
        elapsed = (datetime.utcnow() - self.timestamp).total_seconds()
        return elapsed > self.timeout_seconds


@dataclass
class ManualTradeRequest:
    """Manual trade request from user."""
    symbol: str
    direction: str  # 'long' or 'short'
    size: float
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    source: TradeSource = TradeSource.TELEGRAM
    user_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class TradingModeManager:
    """
    Unified trading mode manager.
    
    Manages all trading execution modes and user interactions:
    - Routes signals based on active mode
    - Handles user confirmations for semi-auto
    - Processes manual trade requests
    - Integrates with Telegram and web dashboard
    """
    
    def __init__(
        self,
        default_mode: TradingMode = TradingMode.SEMI_AUTO,
        execution_engine: Optional[IntegratedExecutionEngine] = None,
        alert_manager: Optional[AlertManager] = None
    ):
        """
        Initialize trading mode manager.
        
        Args:
            default_mode: Initial trading mode
            execution_engine: Execution engine instance (optional)
            alert_manager: Telegram alert manager (optional)
        """
        # Trading mode
        self.current_mode = default_mode
        self.mode_history: List[Dict] = []
        
        # Components
        self.execution_engine = execution_engine
        self.alert_manager = alert_manager
        
        # Pending signals (semi-auto mode)
        self.pending_signals: Dict[str, PendingSignal] = {}
        
        # Manual trade queue
        self.manual_trade_queue: List[ManualTradeRequest] = []
        
        # Configuration
        self.semi_auto_timeout = int(os.getenv('SEMI_AUTO_TIMEOUT', '300'))
        self.require_confirmation = True
        
        # State
        self.is_running = False
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            'signals_received': 0,
            'signals_executed': 0,
            'signals_rejected': 0,
            'signals_expired': 0,
            'manual_trades': 0,
            'mode_switches': 0
        }
        
        logger.info(f"TradingModeManager initialized - Mode: {default_mode.value}")
    
    async def start(self) -> None:
        """Start the trading mode manager."""
        if self.is_running:
            logger.warning("TradingModeManager already running")
            return
        
        try:
            # Initialize execution engine if not provided
            if self.execution_engine is None:
                self.execution_engine = IntegratedExecutionEngine()
                logger.info("Created new IntegratedExecutionEngine")
            
            # Initialize Telegram alerts if not provided
            if self.alert_manager is None and initialize_telegram_alerts:
                self.alert_manager = await initialize_telegram_alerts(
                    entry_callback=self._handle_entry_confirmation,
                    exit_callback=self._handle_exit_confirmation
                )
                await self.alert_manager.start()
                logger.info("Initialized Telegram alert manager")
            
            # Start cleanup task for expired signals
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self.is_running = True
            logger.info("TradingModeManager started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start TradingModeManager: {e}", exc_info=True)
            raise
    
    async def stop(self) -> None:
        """Stop the trading mode manager."""
        if not self.is_running:
            return
        
        try:
            # Cancel cleanup task
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Stop alert manager
            if self.alert_manager:
                await self.alert_manager.stop()
            
            self.is_running = False
            logger.info("TradingModeManager stopped")
            
        except Exception as e:
            logger.error(f"Error stopping TradingModeManager: {e}", exc_info=True)
    
    # ==================== MODE MANAGEMENT ====================
    
    async def set_mode(self, mode: TradingMode, user_id: Optional[str] = None) -> bool:
        """Switch trading mode.
        
        Args:
            mode: New trading mode
            user_id: User who requested the change
        
        Returns:
            Success status
        """
        old_mode = self.current_mode
        self.current_mode = mode
        
        # Record mode change
        self.mode_history.append({
            'from_mode': old_mode.value,
            'to_mode': mode.value,
            'timestamp': datetime.utcnow(),
            'user_id': user_id
        })
        
        self.stats['mode_switches'] += 1
        
        logger.info(f"Trading mode switched: {old_mode.value} → {mode.value}")
        
        # Send Telegram notification
        if self.alert_manager:
            await self._send_mode_notification(old_mode, mode)
        
        return True
    
    def get_mode(self) -> TradingMode:
        """Get current trading mode."""
        return self.current_mode
    
    # ==================== SIGNAL HANDLING ====================
    
    async def handle_signal(self, signal: TradingSignal) -> bool:
        """Handle incoming trading signal based on current mode.
        
        Args:
            signal: Trading signal from signal generator
        
        Returns:
            Success status
        """
        self.stats['signals_received'] += 1
        
        logger.info(
            f"Signal received: {signal.symbol} {signal.direction.value} "
            f"@ {signal.entry_price:.2f} (Mode: {self.current_mode.value})"
        )
        
        if self.current_mode == TradingMode.FULL_AUTO:
            # Execute immediately
            return await self._execute_signal_auto(signal)
        
        elif self.current_mode == TradingMode.SEMI_AUTO:
            # Send alert and wait for confirmation
            return await self._send_signal_for_confirmation(signal)
        
        else:  # MANUAL mode
            # Just log the signal, don't execute
            logger.info(f"Signal logged (manual mode): {signal.symbol}")
            return True
    
    async def _execute_signal_auto(self, signal: TradingSignal) -> bool:
        """Execute signal automatically (FULL_AUTO mode)."""
        try:
            success, error_msg, trade = self.execution_engine.execute_signal(signal)
            
            if success:
                self.stats['signals_executed'] += 1
                logger.info(f"Signal executed automatically: {signal.symbol}")
                
                # Send confirmation to Telegram
                if self.alert_manager:
                    await self._send_execution_confirmation(signal, trade)
                
                return True
            else:
                self.stats['signals_rejected'] += 1
                logger.warning(f"Signal execution failed: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing signal: {e}", exc_info=True)
            return False
    
    async def _send_signal_for_confirmation(self, signal: TradingSignal) -> bool:
        """Send signal to user for confirmation (SEMI_AUTO mode)."""
        try:
            # Create pending signal
            signal_id = f"{signal.symbol}_{signal.timestamp.timestamp()}"
            pending = PendingSignal(
                signal=signal,
                timestamp=datetime.utcnow(),
                timeout_seconds=self.semi_auto_timeout
            )
            
            # Send Telegram alert
            if self.alert_manager:
                message_id = await self._send_confirmation_alert(signal)
                pending.message_id = message_id
            
            # Store pending signal
            self.pending_signals[signal_id] = pending
            
            logger.info(
                f"Signal sent for confirmation: {signal.symbol} "
                f"(timeout: {self.semi_auto_timeout}s)"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending signal for confirmation: {e}", exc_info=True)
            return False
    
    # ==================== MANUAL TRADING ====================
    
    async def execute_manual_trade(
        self,
        symbol: str,
        direction: str,
        size: float,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        source: TradeSource = TradeSource.TELEGRAM,
        user_id: Optional[str] = None
    ) -> bool:
        """Execute a manual trade from user command.
        
        Supports both Telegram commands and web dashboard requests.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            direction: 'long' or 'short'
            size: Position size
            entry_price: Optional entry price (market if None)
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price
            source: Source of request (TELEGRAM or WEB_DASHBOARD)
            user_id: User who initiated the trade
        
        Returns:
            Success status
        """
        try:
            logger.info(
                f"Manual trade request: {symbol} {direction} {size} "
                f"(source: {source.value})"
            )
            
            # Create manual trade request
            trade_request = ManualTradeRequest(
                symbol=symbol,
                direction=direction,
                size=size,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                source=source,
                user_id=user_id
            )
            
            # Convert to TradingSignal format
            signal = self._manual_request_to_signal(trade_request)
            
            # Execute trade
            success, error_msg, trade = self.execution_engine.execute_signal(signal)
            
            if success:
                self.stats['manual_trades'] += 1
                logger.info(f"Manual trade executed: {symbol}")
                
                # Send confirmation
                if self.alert_manager and source == TradeSource.TELEGRAM:
                    await self._send_manual_trade_confirmation(signal, trade)
                
                return True
            else:
                logger.warning(f"Manual trade failed: {error_msg}")
                
                # Send error notification
                if self.alert_manager and source == TradeSource.TELEGRAM:
                    await self._send_trade_error(symbol, error_msg)
                
                return False
                
        except Exception as e:
            logger.error(f"Error executing manual trade: {e}", exc_info=True)
            return False
    
    def _manual_request_to_signal(self, request: ManualTradeRequest) -> TradingSignal:
        """Convert manual trade request to TradingSignal."""
        # Use market price if no entry specified
        entry = request.entry_price or 0.0  # Will be filled by execution engine
        
        # Default stop loss and take profit if not specified
        sl = request.stop_loss or (entry * 0.98 if request.direction == 'long' else entry * 1.02)
        tp = request.take_profit or (entry * 1.03 if request.direction == 'long' else entry * 0.97)
        
        direction = SignalDirection.LONG if request.direction.lower() == 'long' else SignalDirection.SHORT
        
        return TradingSignal(
            symbol=request.symbol,
            direction=direction,
            entry_price=entry,
            stop_loss=sl,
            take_profit_1=tp,
            take_profit_2=tp * 1.5 if request.direction == 'long' else tp * 0.5,
            confidence=1.0,  # Manual trades have full confidence
            score=100.0,
            execution_tier='FULL'
        )
    
    # ==================== HELPER METHODS ====================
    
    async def _cleanup_loop(self):
        """Background task to cleanup expired signals."""
        while self.is_running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Find expired signals
                expired = [
                    signal_id for signal_id, pending in self.pending_signals.items()
                    if pending.is_expired()
                ]
                
                # Remove expired signals
                for signal_id in expired:
                    pending = self.pending_signals.pop(signal_id)
                    self.stats['signals_expired'] += 1
                    logger.info(f"Signal expired: {pending.signal.symbol}")
                    
                    # Notify user
                    if self.alert_manager:
                        await self._send_expiration_notification(pending.signal)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)
    
    async def _handle_entry_confirmation(self, signal_id: str, confirmed: bool):
        """Handle user confirmation for entry signal."""
        if signal_id not in self.pending_signals:
            logger.warning(f"Confirmation for unknown signal: {signal_id}")
            return
        
        pending = self.pending_signals.pop(signal_id)
        
        if confirmed:
            logger.info(f"Signal confirmed by user: {pending.signal.symbol}")
            await self._execute_signal_auto(pending.signal)
        else:
            self.stats['signals_rejected'] += 1
            logger.info(f"Signal rejected by user: {pending.signal.symbol}")
    
    async def _handle_exit_confirmation(self, trade_id: str, percentage: float):
        """Handle user confirmation for exit signal."""
        logger.info(f"Exit confirmed: {trade_id} - {percentage}%")
        # TODO: Implement exit logic
    
    def get_stats(self) -> Dict:
        """Get trading statistics."""
        return {
            **self.stats,
            'current_mode': self.current_mode.value,
            'pending_signals': len(self.pending_signals),
            'manual_queue': len(self.manual_trade_queue)
        }


# ========== SEGMENT 1 END ==========
# Lines: ~490
# 
# SEGMENT 2 will include:
# - Telegram alert formatting methods
# - Web dashboard API integration
# - Configuration management
# - Example usage and testing
# - Integration documentation      
