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

# ========== SEGMENT 2 START ==========
# Lines: ~250-300
#
# SEGMENT 2 includes:
# - Telegram alert formatting methods
# - Web dashboard integration helpers  
# - Configuration management
# - Production usage examples
# - Integration documentation


    # ==========================================
    # Telegram Alert Formatting Methods
    # ==========================================

    async def _send_mode_notification(self, old_mode: TradingMode, new_mode: TradingMode) -> None:
        """Send mode change notification to Telegram."""
        try:
            message = (
                f"🔄 *Trading Mode Changed*\n\n"
                f"Previous: `{old_mode.value}`\n"
                f"Current: `{new_mode.value}`\n\n"
            )
            
            if new_mode == TradingMode.MANUAL:
                message += (
                    "📱 *Manual Mode Active*\n"
                    "• All signals require manual execution\n"
                    "• Use `/trade` command or web dashboard\n"
                    "• No automatic execution\n"
                )
            elif new_mode == TradingMode.SEMI_AUTO:
                message += (
                    "⚡ *Semi-Auto Mode Active*\n"
                    "• Signals sent for confirmation\n"
                    f"• {self.config.confirmation_timeout_seconds}s confirmation window\n"
                    "• Reply with percentage to execute\n"
                )
            else:  # FULL_AUTO
                message += (
                    "🤖 *Full-Auto Mode Active*\n"
                    "• Automatic execution enabled\n"
                    "• Signals execute immediately\n"
                    "• Monitor closely\n"
                )
            
            await self.alert_manager.send_alert(
                message=message,
                alert_type="MODE_CHANGE",
                priority="high"
            )
            
        except Exception as e:
            logger.error(f"Failed to send mode notification: {e}")

    async def _send_confirmation_alert(self, signal: PendingSignal) -> None:
        """Send signal confirmation request to Telegram."""
        try:
            sig = signal.signal
            message = (
                f"⚠️ *Trade Confirmation Required*\n\n"
                f"Symbol: `{sig.symbol}`\n"
                f"Action: `{sig.action}`\n"
                f"Strategy: `{sig.strategy_name}`\n"
                f"Confidence: `{sig.confidence:.1%}`\n\n"
                f"💰 *Position Details:*\n"
                f"Entry: `${sig.entry_price:.4f}`\n"
                f"Size: `{sig.position_size_usd:,.2f} USD`\n\n"
                f"⏱️ Expires in: `{self.config.confirmation_timeout_seconds}s`\n\n"
                f"*Reply with percentage (0-100) to execute*\n"
                f"Example: `50` for 50% position size"
            )
            
            await self.alert_manager.send_alert(
                message=message,
                alert_type="TRADE_CONFIRMATION",
                priority="high",
                metadata={"trade_id": signal.trade_id, "symbol": sig.symbol}
            )
            
        except Exception as e:
            logger.error(f"Failed to send confirmation alert: {e}")

    async def _send_execution_confirmation(self, trade_id: str, symbol: str, 
                                          action: str, percentage: float) -> None:
        """Send trade execution confirmation to Telegram."""
        try:
            message = (
                f"✅ *Trade Executed*\n\n"
                f"ID: `{trade_id}`\n"
                f"Symbol: `{symbol}`\n"
                f"Action: `{action}`\n"
                f"Size: `{percentage:.0f}%`\n\n"
                f"Check dashboard for full details"
            )
            
            await self.alert_manager.send_alert(
                message=message,
                alert_type="TRADE_EXECUTED",
                priority="high"
            )
            
        except Exception as e:
            logger.error(f"Failed to send execution confirmation: {e}")

    async def _send_manual_trade_confirmation(self, trade_request: ManualTradeRequest) -> None:
        """Send manual trade execution confirmation to Telegram."""
        try:
            source_icon = "📱" if trade_request.source == TradeSource.TELEGRAM else "🌐"
            message = (
                f"{source_icon} *Manual Trade Submitted*\n\n"
                f"Symbol: `{trade_request.symbol}`\n"
                f"Action: `{trade_request.action}`\n"
                f"Entry: `${trade_request.entry_price:.4f}`\n"
                f"Size: `${trade_request.position_size_usd:,.2f}`\n"
                f"Source: `{trade_request.source.value}`\n\n"
                f"⏳ Executing..."
            )
            
            await self.alert_manager.send_alert(
                message=message,
                alert_type="MANUAL_TRADE",
                priority="medium"
            )
            
        except Exception as e:
            logger.error(f"Failed to send manual trade confirmation: {e}")

    async def _send_trade_error(self, error_msg: str, trade_id: str = None) -> None:
        """Send trade error notification to Telegram."""
        try:
            message = f"❌ *Trade Error*\n\n"
            if trade_id:
                message += f"Trade ID: `{trade_id}`\n"
            message += f"Error: {error_msg}"
            
            await self.alert_manager.send_alert(
                message=message,
                alert_type="TRADE_ERROR",
                priority="high"
            )
            
        except Exception as e:
            logger.error(f"Failed to send trade error alert: {e}")

    async def _send_expiration_notification(self, trade_id: str, symbol: str) -> None:
        """Send signal expiration notification to Telegram."""
        try:
            message = (
                f"⌛ *Signal Expired*\n\n"
                f"Trade ID: `{trade_id}`\n"
                f"Symbol: `{symbol}`\n\n"
                f"No confirmation received within timeout period"
            )
            
            await self.alert_manager.send_alert(
                message=message,
                alert_type="SIGNAL_EXPIRED",
                priority="low"
            )
            
        except Exception as e:
            logger.error(f"Failed to send expiration notification: {e}")


    # ==========================================
    # Web Dashboard Integration Helpers
    # ==========================================

    def get_dashboard_status(self) -> Dict[str, Any]:
        """Get comprehensive status for web dashboard."""
        return {
            'current_mode': self.current_mode.value,
            'is_running': self.is_running,
            'stats': self.get_stats(),
            'mode_history': [
                {'mode': m.value, 'timestamp': t.isoformat()}
                for m, t in self.mode_history
            ],
            'pending_signals_count': len(self.pending_signals),
            'manual_queue_count': len(self.manual_trade_queue)
        }

    async def handle_dashboard_trade(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle manual trade request from web dashboard.
        
        Args:
            trade_data: Dictionary with keys: symbol, action, entry_price, 
                       position_size_usd, stop_loss, take_profit
        
        Returns:
            Dict with success status and message
        """
        try:
            trade_request = ManualTradeRequest(
                symbol=trade_data['symbol'],
                action=trade_data['action'],
                entry_price=trade_data['entry_price'],
                position_size_usd=trade_data['position_size_usd'],
                stop_loss=trade_data.get('stop_loss'),
                take_profit=trade_data.get('take_profit'),
                source=TradeSource.WEB_DASHBOARD,
                metadata=trade_data.get('metadata', {})
            )
            
            await self.execute_manual_trade(trade_request)
            
            return {
                'success': True,
                'message': f'Trade submitted for {trade_data["symbol"]}',
                'trade_id': trade_request.trade_id
            }
            
        except Exception as e:
            logger.error(f"Dashboard trade error: {e}")
            return {
                'success': False,
                'message': str(e)
            }


# ==========================================
# Production Usage Examples
# ==========================================

"""
EXAMPLE 1: Basic Initialization with Signal Integration

from trading_mode_manager import TradingModeManager, TradingModeConfig, TradingMode
from signal_generation.execution_engine_integrated import ExecutionEngine
from telegram_integration.alert_manager import AlertManager

# Initialize dependencies
execution_engine = ExecutionEngine()
alert_manager = AlertManager()

# Configure trading mode manager
config = TradingModeConfig(
    default_mode=TradingMode.SEMI_AUTO,
    confirmation_timeout_seconds=60,
    max_pending_signals=10
)

# Create manager
mode_manager = TradingModeManager(
    execution_engine=execution_engine,
    alert_manager=alert_manager,
    config=config
)

# Start manager
await mode_manager.start()

# Process incoming signal from strategy
signal = await strategy.generate_signal()  # Your signal generation
if signal:
    await mode_manager.process_signal(signal)

# Stop when done
await mode_manager.stop()
"""

"""
EXAMPLE 2: Mode Switching During Runtime

# Start in manual mode for testing
await mode_manager.set_mode(TradingMode.MANUAL)

# Manually execute specific trades via Telegram
# User sends /trade command through Telegram bot
# TradingModeManager.execute_manual_trade() is called

# Switch to semi-auto for confirmation-based trading
await mode_manager.set_mode(TradingMode.SEMI_AUTO)

# Signals now require user confirmation
# User replies with percentage (0-100) to execute

# Once confident, enable full automation
await mode_manager.set_mode(TradingMode.FULL_AUTO)
"""

"""
EXAMPLE 3: Telegram Bot Integration

from telegram import Update
from telegram.ext import ContextTypes

async def handle_trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    \"\"\"Handle /trade command from Telegram.\"\"\"
    # Parse trade parameters from command
    # Example: /trade BTCUSDT buy 50000 1000
    try:
        args = context.args
        symbol = args[0]
        action = args[1]
        entry_price = float(args[2])
        position_size = float(args[3])
        
        trade_request = ManualTradeRequest(
            symbol=symbol,
            action=action,
            entry_price=entry_price,
            position_size_usd=position_size,
            source=TradeSource.TELEGRAM,
            metadata={'user_id': update.effective_user.id}
        )
        
        await mode_manager.execute_manual_trade(trade_request)
        await update.message.reply_text('✅ Trade submitted!')
        
    except Exception as e:
        await update.message.reply_text(f'❌ Error: {e}')


async def handle_confirmation_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    \"\"\"Handle user confirmation percentage reply.\"\"\"
    try:
        # Get most recent pending signal
        text = update.message.text.strip()
        percentage = float(text)
        
        if 0 <= percentage <= 100:
            # Get the most recent pending signal (you'd track this in context)
            trade_id = context.user_data.get('last_pending_signal_id')
            if trade_id:
                await mode_manager.handle_user_confirmation(trade_id, percentage)
                await update.message.reply_text(f'✅ Executing at {percentage}%')
            else:
                await update.message.reply_text('❌ No pending signal found')
        else:
            await update.message.reply_text('❌ Invalid percentage (0-100)')
            
    except ValueError:
        pass  # Not a percentage reply, ignore
    except Exception as e:
        await update.message.reply_text(f'❌ Error: {e}')
"""

"""
EXAMPLE 4: Web Dashboard API Endpoint (FastAPI)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class DashboardTradeRequest(BaseModel):
    symbol: str
    action: str
    entry_price: float
    position_size_usd: float
    stop_loss: float = None
    take_profit: float = None

@app.post("/api/trade/manual")
async def submit_manual_trade(trade: DashboardTradeRequest):
    \"\"\"Submit manual trade from web dashboard.\"\"\"
    result = await mode_manager.handle_dashboard_trade(trade.dict())
    
    if result['success']:
        return result
    else:
        raise HTTPException(status_code=400, detail=result['message'])

@app.get("/api/status")
async def get_status():
    \"\"\"Get trading mode manager status.\"\"\"
    return mode_manager.get_dashboard_status()
"""


# ==========================================
# Integration Documentation
# ==========================================

"""
INTEGRATION CHECKLIST:

1. Signal Generation Integration:
   - Import TradingModeManager in your main execution loop
   - Call mode_manager.process_signal() for each generated signal
   - Ensure signals have all required fields (symbol, action, confidence, etc.)

2. Telegram Bot Setup:
   - Implement /trade command handler for manual trades
   - Implement message handler for confirmation replies (percentage)
   - Store pending signal IDs in user context for confirmation tracking
   - Pass TradeSource.TELEGRAM when creating ManualTradeRequest

3. Web Dashboard Setup (Optional):
   - Create FastAPI endpoints for manual trade submission
   - Use mode_manager.handle_dashboard_trade() for trade processing
   - Use mode_manager.get_dashboard_status() for status display
   - Pass TradeSource.WEB_DASHBOARD when creating trades

4. Mode Configuration:
   - Start with MANUAL mode for testing
   - Move to SEMI_AUTO for confirmation-based trading
   - Enable FULL_AUTO only after thorough testing
   - Adjust confirmation_timeout_seconds based on your needs

5. Error Handling:
   - Monitor logs for execution errors
   - Check alert_manager for Telegram notifications
   - Handle expired signals appropriately
   - Track statistics with get_stats()

6. Production Deployment:
   - Ensure execution_engine is properly initialized
   - Verify alert_manager Telegram credentials
   - Set appropriate confirmation timeouts
   - Monitor manual_trade_queue size
   - Regularly check mode_history for unexpected switches
"""


# ========== SEGMENT 2 END ==========
# Total lines: ~770-780
# File complete with all methods and documentation
