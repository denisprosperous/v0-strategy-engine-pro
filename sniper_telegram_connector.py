"""
Sniper Telegram Connector

Bridges the institutional sniper signal generator with Telegram integration.
Converts EntrySignal/ExitSignal from institutional_sniper to Telegram alerts.
Handles user confirmations and executes trade callbacks.

Usage:
    connector = SniperTelegramConnector()
    await connector.start()
    
    # When signal is detected
    await connector.handle_entry_signal(entry_signal)
"""

import asyncio
import logging
from typing import Callable, Optional, Awaitable
from decimal import Decimal

from institutional_sniper.signal_generator import (
    EntrySignal,
    ExitSignal,
    InstitutionalSniperSignalGenerator
)
from telegram_integration import initialize_telegram_alerts, AlertManager

logger = logging.getLogger(__name__)


class SniperTelegramConnector:
    """
    Connector between Institutional Sniper and Telegram Integration
    
    Responsibilities:
    - Convert sniper signals to telegram alert format
    - Manage alert manager lifecycle
    - Handle position tracking
    - Execute trade callbacks when user confirms
    """
    
    def __init__(
        self,
        on_buy: Optional[Callable[[str, float], Awaitable[None]]] = None,
        on_sell: Optional[Callable[[str, float], Awaitable[None]]] = None
    ):
        """
        Initialize connector
        
        Args:
            on_buy: Async callback when user confirms buy (token_address, size_usd)
            on_sell: Async callback when user confirms sell (token_address, percentage)
        """
        self.alert_manager: Optional[AlertManager] = None
        self.on_buy = on_buy or self._default_buy_callback
        self.on_sell = on_sell or self._default_sell_callback
        self.active_positions = {}  # Track positions for exit signals
        self.is_running = False
        
        logger.info("SniperTelegramConnector initialized")
    
    async def start(self) -> None:
        """Start the connector and telegram integration"""
        if self.is_running:
            logger.warning("Connector already running")
            return
        
        try:
            # Initialize telegram alerts with callbacks
            self.alert_manager = await initialize_telegram_alerts(
                entry_callback=self.on_buy,
                exit_callback=self.on_sell
            )
            
            await self.alert_manager.start()
            self.is_running = True
            
            logger.info("SniperTelegramConnector started successfully")
        
        except Exception as e:
            logger.error(f"Failed to start connector: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the connector"""
        if not self.is_running:
            return
        
        if self.alert_manager:
            await self.alert_manager.stop()
        
        self.is_running = False
        logger.info("SniperTelegramConnector stopped")
    
    async def handle_entry_signal(self, signal: EntrySignal) -> None:
        """
        Process entry signal from institutional sniper
        
        Args:
            signal: EntrySignal from InstitutionalSniperSignalGenerator
        """
        if not self.is_running:
            logger.error("Connector not running, cannot handle signal")
            return
        
        try:
            # Extract data from signal
            token_data = signal.token_data
            inst_signal = signal.institutional_signal
            scam_report = signal.scam_report
            
            # Prepare alert data
            token_address = getattr(token_data, 'address', 'Unknown')
            token_symbol = getattr(token_data, 'symbol', 'Unknown')
            token_name = getattr(token_data, 'name', 'Unknown Token')
            
            # Get institutional metrics
            wallet_address = getattr(inst_signal, 'wallet_address', 'Unknown')
            buy_amount_usd = float(getattr(inst_signal, 'buy_amount_usd', 0))
            
            # Calculate sniper score (0-100)
            sniper_score = signal.confidence * 100
            
            # Get wallet performance (if available)
            win_rate = getattr(inst_signal, 'win_rate', 0.0)
            avg_profit = getattr(inst_signal, 'avg_profit', 0.0)
            total_trades = getattr(inst_signal, 'total_trades', 0)
            
            # Recommended position size
            recommended_size = signal.recommended_entry.get('amount', 100)
            
            # Send telegram alert
            await self.alert_manager.send_entry_alert(
                token_address=token_address,
                token_symbol=token_symbol,
                token_name=token_name,
                wallet_address=wallet_address,
                buy_amount_usd=buy_amount_usd,
                sniper_score=sniper_score,
                win_rate=win_rate,
                avg_profit=avg_profit,
                total_trades=total_trades,
                recommended_size_usd=recommended_size
            )
            
            # Track position for future exit signals
            self.active_positions[token_address] = {
                'symbol': token_symbol,
                'entry_signal': signal,
                'entry_price': signal.recommended_entry.get('stop_loss', 0),
                'size_usd': recommended_size
            }
            
            logger.info(
                f"Entry signal sent for {token_symbol} ({token_address}) "
                f"- Score: {sniper_score:.1f}%"
            )
        
        except Exception as e:
            logger.error(f"Error handling entry signal: {e}", exc_info=True)
    
    async def handle_exit_signal(self, signal: ExitSignal) -> None:
        """
        Process exit signal from institutional sniper
        
        Args:
            signal: ExitSignal from InstitutionalSniperSignalGenerator
        """
        if not self.is_running:
            logger.error("Connector not running, cannot handle signal")
            return
        
        try:
            # Find token address from active positions
            token_address = None
            for addr, pos in self.active_positions.items():
                if pos['symbol'] == signal.symbol:
                    token_address = addr
                    break
            
            if not token_address:
                logger.warning(f"No active position found for {signal.symbol}")
                return
            
            position = self.active_positions[token_address]
            
            # Send exit alert
            await self.alert_manager.send_exit_alert(
                token_address=token_address,
                token_symbol=signal.symbol,
                position_size_usd=float(position['size_usd']),
                entry_price=float(signal.entry_price),
                current_price=float(signal.current_price),
                profit_loss_usd=float(signal.pnl_percentage * position['size_usd'] / 100),
                profit_loss_percent=float(signal.pnl_percentage),
                hold_time_minutes=0,  # Calculate if needed
                reason=signal.reason,
                recommended_percentage=signal.recommended_percentage
            )
            
            logger.info(
                f"Exit signal sent for {signal.symbol} ({token_address}) "
                f"- P&L: {signal.pnl_percentage:+.1f}%"
            )
        
        except Exception as e:
            logger.error(f"Error handling exit signal: {e}", exc_info=True)
    
    async def _default_buy_callback(self, token_address: str, size_usd: float) -> None:
        """
        Default buy callback (logs only)
        Users should override this with actual trade execution
        """
        logger.info(f"[DEFAULT CALLBACK] Buy signal confirmed: {token_address} for ${size_usd}")
        logger.warning("No custom buy callback provided - implement actual trading logic")
    
    async def _default_sell_callback(self, token_address: str, percentage: float) -> None:
        """
        Default sell callback (logs only)
        Users should override this with actual trade execution
        """
        logger.info(f"[DEFAULT CALLBACK] Sell signal confirmed: {token_address} - {percentage}%")
        logger.warning("No custom sell callback provided - implement actual trading logic")
        
        # Remove from active positions if selling 100%
        if percentage >= 100 and token_address in self.active_positions:
            del self.active_positions[token_address]


# Convenience function for quick setup
async def create_sniper_telegram_bot(
    on_buy: Optional[Callable[[str, float], Awaitable[None]]] = None,
    on_sell: Optional[Callable[[str, float], Awaitable[None]]] = None
) -> SniperTelegramConnector:
    """
    Create and start a sniper telegram connector
    
    Args:
        on_buy: Async callback when user confirms buy (token_address, size_usd)
        on_sell: Async callback when user confirms sell (token_address, percentage)
    
    Returns:
        Running SniperTelegramConnector instance
    
    Example:
        async def execute_buy(token_address: str, size_usd: float):
            # Your buy logic here
            print(f"Buying {token_address} for ${size_usd}")
        
        connector = await create_sniper_telegram_bot(on_buy=execute_buy)
    """
    connector = SniperTelegramConnector(on_buy=on_buy, on_sell=on_sell)
    await connector.start()
    return connector


if __name__ == "__main__":
    # Example usage
    async def main():
        # Define custom callbacks
        async def my_buy_logic(token_address: str, size_usd: float):
            print(f"\n=== EXECUTING BUY ===")
            print(f"Token: {token_address}")
            print(f"Size: ${size_usd}")
            # Implement actual trading logic here
        
        async def my_sell_logic(token_address: str, percentage: float):
            print(f"\n=== EXECUTING SELL ===")
            print(f"Token: {token_address}")
            print(f"Percentage: {percentage}%")
            # Implement actual trading logic here
        
        # Create and start connector
        connector = await create_sniper_telegram_bot(
            on_buy=my_buy_logic,
            on_sell=my_sell_logic
        )
        
        print("Sniper Telegram Connector running...")
        print("Press Ctrl+C to stop")
        
        try:
            # Keep running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            await connector.stop()
    
    asyncio.run(main())
