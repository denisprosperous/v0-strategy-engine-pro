"""
Institutional Sniper Telegram Bot
Complete integration for real-time signal alerts, user confirmation, and execution feedback
Supports both polling and webhook modes with config-based switching
"""

import asyncio
import logging
import json
from typing import Optional, Dict, List, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import TelegramError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Alert types from institutional sniper system"""
    ENTRY_SIGNAL = "entry_signal"
    EXIT_SIGNAL = "exit_signal"
    POSITION_UPDATE = "position_update"
    ERROR_ALERT = "error_alert"
    SYSTEM_STATUS = "system_status"


@dataclass
class EntryAlertData:
    """Entry signal alert data"""
    token_address: str
    token_symbol: str
    pool_address: str
    dex_name: str
    liquidity_usd: float
    institutional_count: int
    tier1_count: int
    tier2_count: int
    confidence: float
    aggregate_buy_volume: float
    recommended_size_usd: float
    entry_price: float
    stop_loss_price: float
    initial_target_price: float
    timestamp: datetime


@dataclass
class ExitAlertData:
    """Exit signal alert data"""
    token_address: str
    token_symbol: str
    current_price: float
    entry_price: float
    pnl_percentage: float
    pnl_usd: float
    reason: str
    recommended_sell_percentage: int
    timestamp: datetime


class InstitutionalSniperBot:
    """
    Production-grade Telegram bot for institutional sniper strategy
    Features:
    - Real-time entry/exit alerts with inline action buttons
    - User confirmation gates (semi-autonomous)
    - Position management and P&L tracking
    - Webhook/polling mode support
    - Comprehensive error handling and logging
    """

    def __init__(self, token: str, user_chat_id: str, use_webhook: bool = False, webhook_url: Optional[str] = None):
        """
        Initialize Telegram bot

        Args:
            token: Telegram bot API token
            user_chat_id: Chat ID where alerts will be sent
            use_webhook: Enable webhook mode (False = polling)
            webhook_url: Webhook URL for receiving updates (if use_webhook=True)
        """
        self.token = token
        self.user_chat_id = int(user_chat_id)
        self.use_webhook = use_webhook
        self.webhook_url = webhook_url

        # Application setup
        self.app = Application.builder().token(token).build()

        # State tracking
        self.pending_confirmations: Dict[str, Dict[str, Any]] = {}
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        self.alert_history: List[Dict[str, Any]] = []
        self.last_alert_time = {}

        # Configuration
        self.confirmation_timeout = 60  # seconds
        self.alert_cooldown = 5  # seconds (prevent spam)
        self.max_pending_confirmations = 5

        # Handlers setup
        self._setup_handlers()

        logger.info(f"Institutional Sniper Bot initialized (webhook_mode={use_webhook})")

    def _setup_handlers(self):
        """Register command and callback handlers"""
        # Commands
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("positions", self.cmd_positions))
        self.app.add_handler(CommandHandler("help", self.cmd_help))

        # Callback handlers (button presses)
        self.app.add_handler(CallbackQueryHandler(self.handle_button_press))

        # Message handlers
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_input))

    # SEGMENT 2/3: Command Handlers & Alert Methods
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        await context.bot.send_message(
            chat_id=self.user_chat_id,
            text="""
🎯 **Institutional Sniper Bot Started**

I'm now monitoring institutional smart money accumulation on DEXes.

When institutional entities are detected accumulating a token:
1. You'll receive an entry alert with key metrics
2. Click buttons to approve/reject/edit purchase size
3. I'll track the position and send exit alerts

**Available Commands:**
/status - Current system status
/positions - View active positions
/help - Show help

Stay alert, profits incoming! 🚀
            """,
            parse_mode='Markdown'
        )

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send system status"""
        status_message = f"""
📊 **System Status**

Active Positions: {len(self.active_positions)}
Pending Confirmations: {len(self.pending_confirmations)}
Alerts Sent: {len(self.alert_history)}

Last Alert: {self.alert_history[-1]['timestamp'] if self.alert_history else 'None'}

Bot Mode: {"Webhook" if self.use_webhook else "Polling"}
Status: ✅ Running
        """

        await context.bot.send_message(
            chat_id=self.user_chat_id,
            text=status_message,
            parse_mode='Markdown'
        )

    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """List active positions"""
        if not self.active_positions:
            await context.bot.send_message(
                chat_id=self.user_chat_id,
                text="📭 No active positions"
            )
            return

        positions_text = "📊 **Active Positions**\n\n"
        for token_addr, pos in self.active_positions.items():
            pnl = pos.get('pnl_percentage', 0)
            pnl_emoji = "📈" if pnl > 0 else "📉"
            positions_text += f"{pnl_emoji} {pos['symbol']}: {pnl:+.1f}% (${pos.get('entry_price', 0):.8f})\n"

        await context.bot.send_message(
            chat_id=self.user_chat_id,
            text=positions_text,
            parse_mode='Markdown'
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send help message"""
        help_text = """
🆘 **Help**

**Entry Alerts:**
When I detect institutional buying, you'll see:
- Token info and institutional entity count
- Recommended entry size (1.5% max)
- Stop loss and initial target
- Buttons to BUY / EDIT SIZE / REJECT

Click buttons within 60 seconds.

**Exit Alerts:**
When exit conditions trigger:
- Current P&L and exit reason
- Recommended sell percentage
- Options to SELL / EDIT % / HOLD

**Commands:**
/status - System status
/positions - Active positions
/help - This message
        """

        await context.bot.send_message(
            chat_id=self.user_chat_id,
            text=help_text,
            parse_mode='Markdown'
        )

    async def send_entry_alert(self, alert_data: EntryAlertData, callback_handler: Optional[Callable] = None) -> Optional[str]:
        """
        Send entry signal alert with confirmation buttons

        Args:
            alert_data: Entry alert details
            callback_handler: Function to call on user confirmation

        Returns:
            Confirmation ID or None if rate limited
        """
        # Rate limiting check
        token_key = f"entry_{alert_data.token_address}"
        if token_key in self.last_alert_time:
            time_since_last = (datetime.now() - self.last_alert_time[token_key]).total_seconds()
            if time_since_last < self.alert_cooldown:
                logger.warning(f"Entry alert rate limited for {alert_data.token_symbol}")
                return None

        if len(self.pending_confirmations) >= self.max_pending_confirmations:
            logger.warning("Max pending confirmations reached")
            return None

        # Format alert message
        message = self._format_entry_alert(alert_data)

        # Create inline keyboard
        keyboard = [
            [
                InlineKeyboardButton(
                    f"✅ BUY ${alert_data.recommended_size_usd:.0f}",
                    callback_data=f"buy_{alert_data.token_address}_{alert_data.recommended_size_usd}"
                ),
                InlineKeyboardButton(
                    "✏️ EDIT SIZE",
                    callback_data=f"edit_size_{alert_data.token_address}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "❌ REJECT",
                    callback_data=f"reject_{alert_data.token_address}"
                ),
                InlineKeyboardButton(
                    "📊 CHART",
                    url=f"https://dexscreener.com/ethereum/{alert_data.token_address}"
                ),
            ]
        ]

        try:
            msg = await self.app.bot.send_message(
                chat_id=self.user_chat_id,
                text=message,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard),
                disable_web_page_preview=True
            )

            # Store pending confirmation
            confirmation_id = f"entry_{alert_data.token_address}_{datetime.now().timestamp()}"
            self.pending_confirmations[confirmation_id] = {
                'type': 'entry',
                'token_address': alert_data.token_address,
                'token_symbol': alert_data.token_symbol,
                'size_usd': alert_data.recommended_size_usd,
                'entry_price': alert_data.entry_price,
                'stop_loss': alert_data.stop_loss_price,
                'message_id': msg.message_id,
                'expires_at': datetime.now() + timedelta(seconds=self.confirmation_timeout),
                'callback': callback_handler
            }

            # Track alert
            self.alert_history.append({
                'type': 'entry',
                'token': alert_data.token_symbol,
                'timestamp': datetime.now(),
                'confidence': alert_data.confidence
            })

            self.last_alert_time[token_key] = datetime.now()

            logger.info(f"Entry alert sent for {alert_data.token_symbol} (${alert_data.recommended_size_usd:.0f})")
            return confirmation_id

        except TelegramError as e:
            logger.error(f"Failed to send entry alert: {e}")
            return None

    def _format_entry_alert(self, data: EntryAlertData) -> str:
        """Format entry alert message"""
        return f"""
🚨 <b>INSTITUTIONAL ENTRY DETECTED</b> 🚨

💎 Token: <b>{data.token_symbol}</b>
📍 DEX: {data.dex_name}
💰 Liquidity: ${data.liquidity_usd:,.0f}

<b>Institutional Activity:</b>
• Total Entities: {data.institutional_count}
• Tier 1 (Whales): {data.tier1_count}
• Tier 2 (Smart Money): {data.tier2_count}

<b>Trade Setup:</b>
💵 Entry Price: ${data.entry_price:.8f}
🛑 Stop Loss: ${data.stop_loss_price:.8f} ({((data.stop_loss_price/data.entry_price - 1) * 100):.1f}%)
🎯 Initial Target: ${data.initial_target_price:.8f} ({((data.initial_target_price/data.entry_price - 1) * 100):.1f}%)

<b>Recommended Size: ${data.recommended_size_usd:.0f}</b>
📊 Confidence: {data.confidence * 100:.0f}%
⏰ Detected: {data.timestamp.strftime('%H:%M:%S')}

⚡ <b>Action Required (60s)</b>
        """


# SEGMENT 2/3 COMPLETE
# Next segment will add: exit alerts, button handlers, and utility methods
