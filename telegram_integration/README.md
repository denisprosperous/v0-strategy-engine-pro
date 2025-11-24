# 📱 Telegram Integration for Institutional Sniper

## Overview

Complete Telegram bot integration for real-time institutional sniper alerts with semi-autonomous trading confirmation gates.

## Features

✅ **Real-Time Alerts**
- Entry signals when institutional accumulation detected
- Exit signals when profit targets or stop losses hit
- Position updates and P&L tracking

✅ **User Confirmation Gates**
- Inline buttons for instant approval/rejection
- Customizable trade sizes
- 60-second confirmation window

✅ **Dual Operation Modes**
- **Polling**: Self-contained, no external server needed
- **Webhook**: Production-ready for cloud deployments

✅ **Production Features**
- Rate limiting and spam protection
- Error handling and retry logic
- Alert history tracking
- Metrics and analytics

---

## 🚀 Quick Start

### 1. Create Your Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the prompts
3. Save your **Bot Token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Your Chat ID

1. Search for `@userinfobot` on Telegram
2. Send `/start`
3. Save your **Chat ID** (numeric, e.g., `987654321`)

### 3. Configure Environment Variables

Add to your `.env` file:

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Optional (defaults shown)
TELEGRAM_USE_WEBHOOK=false
TELEGRAM_CONFIRMATION_TIMEOUT=60
TELEGRAM_ALERT_COOLDOWN=5
TELEGRAM_MAX_PENDING=5
```

### 4. Install Dependencies

```bash
pip install python-telegram-bot==20.7
```

---

## 📖 Usage Examples

### Basic Integration (Polling Mode)

```python
import asyncio
from telegram_integration import initialize_telegram_alerts

# Define callbacks
async def on_buy_confirmed(token_address: str, size_usd: float):
    print(f"Executing buy: {token_address} for ${size_usd}")
    # Execute your buy logic here
    # e.g., call your DEX swap function

async def on_sell_confirmed(token_address: str, percentage: int):
    print(f"Executing sell: {token_address} {percentage}%")
    # Execute your sell logic here

# Initialize
async def main():
    alert_manager = await initialize_telegram_alerts(
        entry_callback=on_buy_confirmed,
        exit_callback=on_sell_confirmed
    )
    
    # Send an entry alert
    await alert_manager.send_entry_alert(
        token_address="0x1234567890abcdef",
        token_symbol="PEPE",
        pool_address="0xabcdef123456",
        dex_name="Uniswap V3",
        liquidity_usd=500000.0,
        institutional_count=5,
        tier1_count=2,
        tier2_count=3,
        confidence=0.85,
        aggregate_buy_volume=150000.0,
        recommended_size_usd=300.0,
        entry_price=0.00001234,
        stop_loss_price=0.00001100,
        initial_target_price=0.00001500,
    )
    
    # Keep bot running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
```

### Integration with Institutional Sniper

```python
from institutional_sniper.detector import InstitutionalDetector
from telegram_integration import get_alert_manager

class InstitutionalSniperWithTelegram:
    def __init__(self):
        self.detector = InstitutionalDetector()
        self.alert_manager = get_alert_manager()
    
    async def on_institutional_entry_detected(self, signal_data):
        """Called when institutional entry signal detected"""
        
        # Send Telegram alert
        confirmation_id = await self.alert_manager.send_entry_alert(
            token_address=signal_data['token_address'],
            token_symbol=signal_data['symbol'],
            pool_address=signal_data['pool_address'],
            dex_name=signal_data['dex'],
            liquidity_usd=signal_data['liquidity'],
            institutional_count=signal_data['entity_count'],
            tier1_count=signal_data['tier1_count'],
            tier2_count=signal_data['tier2_count'],
            confidence=signal_data['confidence'],
            aggregate_buy_volume=signal_data['buy_volume'],
            recommended_size_usd=signal_data['recommended_size'],
            entry_price=signal_data['entry_price'],
            stop_loss_price=signal_data['stop_loss'],
            initial_target_price=signal_data['target'],
        )
        
        return confirmation_id
```

---

## 🎛️ Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ Yes | - | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | ✅ Yes | - | Your Telegram chat ID |
| `TELEGRAM_USE_WEBHOOK` | No | `false` | Enable webhook mode |
| `TELEGRAM_WEBHOOK_URL` | Conditional | - | Required if webhook mode enabled |
| `TELEGRAM_WEBHOOK_PORT` | No | `8443` | Webhook server port |
| `TELEGRAM_CONFIRMATION_TIMEOUT` | No | `60` | Seconds to wait for user action |
| `TELEGRAM_ALERT_COOLDOWN` | No | `5` | Seconds between duplicate alerts |
| `TELEGRAM_MAX_PENDING` | No | `5` | Max pending confirmations |

### Webhook Mode (Production)

For production deployments with external servers:

```bash
TELEGRAM_USE_WEBHOOK=true
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/telegram/webhook
TELEGRAM_WEBHOOK_PORT=8443
```

---

## 🔧 API Reference

### AlertManager

Main class for managing Telegram alerts.

#### Methods

**`send_entry_alert(**kwargs) -> Optional[str]`**

Send entry signal alert.

Returns: Confirmation ID if successful

**`send_exit_alert(**kwargs) -> Optional[str]`**

Send exit signal alert.

Returns: Confirmation ID if successful

**`send_status_message(message: str) -> None`**

Send informational status message.

**`send_error_alert(error_message: str, context: Optional[str]) -> None`**

Send error notification.

**`get_metrics() -> Dict`**

Get alert statistics and metrics.

**`register_callback(callback_type: str, handler: Callable) -> None`**

Register entry/exit confirmation handlers.

---

## 📊 Bot Commands

Users can interact with the bot using these commands:

- `/start` - Initialize bot and show welcome message
- `/status` - View system status and metrics
- `/positions` - List active positions and P&L
- `/help` - Show help information

---

## 🔐 Security Best Practices

1. **Never commit tokens**: Use `.env` files and `.gitignore`
2. **Restrict bot access**: Only share bot token with trusted systems
3. **Validate chat IDs**: Ensure alerts only go to your account
4. **Use HTTPS for webhooks**: Required for production webhook mode
5. **Monitor alert metrics**: Track for unusual activity

---

## 🐛 Troubleshooting

### Bot not receiving updates

- Verify `TELEGRAM_BOT_TOKEN` is correct
- Check bot is not blocked
- Ensure network connectivity
- Try restarting in polling mode

### Alerts not sending

- Confirm `TELEGRAM_CHAT_ID` is correct
- Check AlertManager is initialized
- Review logs for rate limiting messages
- Verify environment variables loaded

### Webhook issues

- Ensure `TELEGRAM_WEBHOOK_URL` is publicly accessible
- Verify SSL certificate is valid
- Check firewall allows port 8443
- Test with polling mode first

---

## 📝 Example .env File

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321

# Operation Mode (polling is easier for development)
TELEGRAM_USE_WEBHOOK=false

# Optional: Webhook configuration (production)
# TELEGRAM_USE_WEBHOOK=true
# TELEGRAM_WEBHOOK_URL=https://yourdomain.com/telegram/webhook
# TELEGRAM_WEBHOOK_PORT=8443

# Optional: Alert tuning
TELEGRAM_CONFIRMATION_TIMEOUT=60
TELEGRAM_ALERT_COOLDOWN=5
TELEGRAM_MAX_PENDING=5
```

---

## 📦 Dependencies

Add to `requirements.txt`:

```
python-telegram-bot==20.7
python-dotenv>=1.0.0
```

---

## 🎯 Next Steps

1. ✅ Configure Telegram bot and chat ID
2. ✅ Add environment variables to `.env`
3. ✅ Integrate with institutional sniper detector
4. ✅ Test with polling mode
5. ⬜ Deploy with webhook for production
6. ⬜ Monitor metrics and optimize

---

## 📧 Support

For issues or questions:
- Check logs for error messages
- Review configuration settings
- Test with minimal example first
- Verify all environment variables set

---

**Built for V0 Strategy Engine Pro** 🚀
