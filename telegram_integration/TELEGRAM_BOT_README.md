# 🤖 Telegram Bot Interface - Complete Guide

## 🎉 Overview

Professional Telegram bot interface for **Strategy Engine Pro** trading system.

**Features:**
- ✅ Full async operation with `python-telegram-bot` v20
- ✅ 14 command handlers for complete bot control
- ✅ Secure authentication & user permissions
- ✅ Interactive inline keyboards
- ✅ Real-time trading status & metrics
- ✅ Portfolio & balance monitoring
- ✅ AI analysis & signal notifications
- ✅ Admin-only trading controls
- ✅ Error handling & logging
- ✅ Support for polling & webhook modes

---

## 📦 Installation

### 1. Install Dependencies

\`\`\`bash
pip install -r telegram_integration/requirements.txt
\`\`\`

### 2. Get Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow instructions
3. Copy your bot token (format: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)
4. **IMPORTANT:** Keep this token secret!

### 3. Configure Environment Variables

Create or update your `.env` file:

\`\`\`bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Optional - API Configuration
TRADING_API_URL=http://localhost:8000/api

# Optional - Security
TELEGRAM_ALLOWED_USERS=123456789,987654321  # Comma-separated user IDs
TELEGRAM_ADMIN_USERS=123456789              # Admin user IDs

# Optional - Bot Behavior
TELEGRAM_POLLING_TIMEOUT=30
TELEGRAM_COMMAND_TIMEOUT=60
TELEGRAM_RATE_LIMIT=true

# Optional - Notifications
ENABLE_TRADE_NOTIFICATIONS=true
ENABLE_SIGNAL_NOTIFICATIONS=true
ENABLE_ERROR_NOTIFICATIONS=true

# Optional - Webhook Mode (Production)
TELEGRAM_WEBHOOK_URL=https://your-domain.com
TELEGRAM_WEBHOOK_PORT=8443
\`\`\`

### 4. Get Your Telegram User ID

To restrict bot access:

1. Message `@userinfobot` on Telegram
2. It will reply with your user ID
3. Add to `TELEGRAM_ALLOWED_USERS` in `.env`

---

## 🚀 Quick Start

### Method 1: Direct Run

\`\`\`bash
# Set your token
export TELEGRAM_BOT_TOKEN="your_token_here"

# Run the bot
python -m telegram_integration.bot
\`\`\`

### Method 2: With Backend API

**Terminal 1 - Start Backend:**
\`\`\`bash
python api/main.py
\`\`\`

**Terminal 2 - Start Bot:**
\`\`\`bash
python -m telegram_integration.bot
\`\`\`

### Method 3: Integrated (Recommended)

\`\`\`bash
# Run both backend and bot together
python main.py --with-telegram
\`\`\`

---

## 📚 Commands Reference

### 👉 Bot Control

| Command | Description | Admin Only |
|---------|-------------|------------|
| `/start` | Welcome message & quick start | No |
| `/help` | List all commands | No |
| `/status` | Show bot & system status | No |

### 👉 Trading Control

| Command | Description | Admin Only |
|---------|-------------|------------|
| `/start_trading` | Start automated trading | ✅ Yes |
| `/stop_trading` | Stop all trading | ✅ Yes |
| `/mode [mode]` | Set trading mode (auto/manual/semi) | ✅ Yes |

### 👉 Portfolio & Balance

| Command | Description | Admin Only |
|---------|-------------|------------|
| `/balance [exchange]` | View account balance | No |
| `/portfolio` | View open positions | No |
| `/exchanges` | List connected exchanges | No |

### 👉 Signals & Analysis

| Command | Description | Admin Only |
|---------|-------------|------------|
| `/signals [limit]` | Show recent trading signals | No |
| `/analyze [symbol]` | AI market analysis | No |
| `/sentiment [symbol]` | Sentiment analysis | No |

### 👉 Performance

| Command | Description | Admin Only |
|---------|-------------|------------|
| `/performance` | Show performance metrics | No |
| `/trades [limit]` | Show recent trade history | No |

---

## 🛡️ Security Features

### User Authentication

**Allow specific users only:**
\`\`\`bash
TELEGRAM_ALLOWED_USERS=123456789,987654321
\`\`\`

**Set admin users:**
\`\`\`bash
TELEGRAM_ADMIN_USERS=123456789
\`\`\`

**Open to all (not recommended):**
\`\`\`bash
# Don't set TELEGRAM_ALLOWED_USERS
\`\`\`

### Admin vs Regular Users

**Admin users can:**
- Start/stop trading
- Change trading modes
- All regular user commands

**Regular users can:**
- View status, balance, portfolio
- Check signals and performance
- Request AI analysis

---

## ⚙️ Configuration

### Polling vs Webhook Mode

**Polling Mode (Development):**
- Default mode
- Bot actively checks for updates
- Easy to set up locally
- No need for public domain

**Webhook Mode (Production):**
\`\`\`bash
TELEGRAM_WEBHOOK_URL=https://your-domain.com
TELEGRAM_WEBHOOK_PORT=8443
\`\`\`
- More efficient
- Requires HTTPS domain
- Telegram pushes updates to your server

### Rate Limiting

Protect your bot from spam:
\`\`\`bash
TELEGRAM_RATE_LIMIT=true
\`\`\`

### Notifications

Control what gets notified:
\`\`\`bash
ENABLE_TRADE_NOTIFICATIONS=true      # New trades
ENABLE_SIGNAL_NOTIFICATIONS=true     # New signals
ENABLE_ERROR_NOTIFICATIONS=true      # Errors
\`\`\`

---

## 📝 Usage Examples

### Example 1: Check Status

\`\`\`
User: /status
Bot: 🤖 Bot Status

     🟢 Status: RUNNING
     ⚙️ Mode: SEMI-AUTO
     🧠 AI: ENABLED
     
     🏛️ Exchanges: Binance, Bybit
     🚦 Active Signals: 3
     💼 Open Positions: 2
     
     [⏸️ Stop Trading] [🔄 Refresh]
\`\`\`

### Example 2: View Signals

\`\`\`
User: /signals 5
Bot: 🚦 Trading Signal

     🟢 BTC/USDT - LONG
     Tier: 1 | Confidence: 85.0%
     
     🎯 Entry: 42000.00
     ⛔ Stop Loss: 41160.00
     ✅ TP1: 43680.00
     🌟 TP2: 44520.00
     
     Status: ACTIVE
     
     📊 Showing 1 of 5 signals
     
     [◀️ Previous] [Next ▶️]
\`\`\`

### Example 3: Change Mode

\`\`\`
User: /mode
Bot: ⚙️ Select Trading Mode
     
     🤖 Auto: Fully automated
     👤 Manual: Manual approval required
     ⚖️ Semi-Auto: AI suggestions with approval
     
     [🤖 Auto] [👤 Manual] [⚖️ Semi-Auto]

User: *clicks Semi-Auto*
Bot: ✅ Mode Changed
     
     Trading mode set to: SEMI-AUTO
\`\`\`

### Example 4: View Performance

\`\`\`
User: /performance
Bot: 📈 Performance Metrics

     🟢 Total P&L: $1,250.50 (12.51%)
     📅 Daily P&L: $125.75 (1.26%)
     
     🎯 Win Rate: 72.50%
     📊 Total Trades: 100
       ✅ Winning: 72
       ❌ Losing: 28
     
     📉 Sharpe Ratio: 2.35
     ⚠️ Max Drawdown: 8.50%
\`\`\`

---

## 🪧 Troubleshooting

### Bot Not Responding

**Check token:**
\`\`\`bash
echo $TELEGRAM_BOT_TOKEN
\`\`\`

**Check logs:**
\`\`\`bash
tail -f telegram_bot.log
\`\`\`

**Test connection:**
\`\`\`python
import asyncio
from telegram import Bot

async def test():
    bot = Bot("YOUR_TOKEN")
    print(await bot.get_me())

asyncio.run(test())
\`\`\`

### Permission Denied

1. Get your user ID from `@userinfobot`
2. Add to `TELEGRAM_ALLOWED_USERS` or `TELEGRAM_ADMIN_USERS`
3. Restart bot

### API Connection Failed

1. Check backend is running: `curl http://localhost:8000/health`
2. Verify `TRADING_API_URL` in `.env`
3. Check firewall/network settings

### Commands Not Showing in Menu

Bot commands are set automatically on startup. If not showing:
1. Restart bot
2. Type `/start` to refresh
3. Check logs for errors

---

## 💻 Development

### File Structure

\`\`\`
telegram_integration/
├── __init__.py           # Package initialization
├── bot.py                # Main bot runner
├── config.py             # Configuration & env loading
├── handlers.py           # All command handlers
├── api_client.py         # Trading API client
├── utils.py              # Helper functions
├── requirements.txt      # Dependencies
└── TELEGRAM_BOT_README.md # This file
\`\`\`

### Adding New Commands

1. **Create handler in `handlers.py`:**
\`\`\`python
async def my_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_user_permission(update):
        await send_error_message(update, context, "Access denied")
        return
    
    await update.message.reply_text("Hello!")
\`\`\`

2. **Register in `bot.py`:**
\`\`\`python
self.application.add_handler(CommandHandler("mycommand", my_command_handler))
\`\`\`

3. **Add to command list:**
\`\`\`python
BotCommand("mycommand", "Description of command")
\`\`\`

### Testing

\`\`\`bash
# Run bot in test mode
python -m pytest tests/test_telegram_bot.py

# Test specific command
python -m telegram_integration.bot --test-mode
\`\`\`

---

## 🚀 Deployment

### Docker Deployment

\`\`\`dockerfile
# Add to Dockerfile
COPY telegram_integration/ /app/telegram_integration/
RUN pip install -r telegram_integration/requirements.txt

CMD ["python", "-m", "telegram_integration.bot"]
\`\`\`

### Systemd Service

\`\`\`ini
[Unit]
Description=Trading Bot Telegram Interface
After=network.target

[Service]
Type=simple
User=trader
WorkingDirectory=/opt/trading-bot
Environment="TELEGRAM_BOT_TOKEN=your_token"
ExecStart=/usr/bin/python3 -m telegram_integration.bot
Restart=always

[Install]
WantedBy=multi-user.target
\`\`\`

### Production Checklist

- [ ] Set strong `TELEGRAM_BOT_TOKEN`
- [ ] Configure `TELEGRAM_ALLOWED_USERS`
- [ ] Set `TELEGRAM_ADMIN_USERS`
- [ ] Enable HTTPS for webhook
- [ ] Set up monitoring & alerts
- [ ] Configure log rotation
- [ ] Test all commands
- [ ] Set up backup bot token

---

## 📊 Monitoring

### Logs

Bot logs to:
- Console (stdout)
- `telegram_bot.log` file

**View live logs:**
\`\`\`bash
tail -f telegram_bot.log
\`\`\`

**Search logs:**
\`\`\`bash
grep "ERROR" telegram_bot.log
\`\`\`

### Metrics to Monitor

- Bot uptime
- Command response times
- API connection status
- Error rates
- User activity

---

## 🎓 Best Practices

1. **Never commit tokens** - Use `.env` file
2. **Restrict user access** - Set `TELEGRAM_ALLOWED_USERS`
3. **Limit admin users** - Only trusted users
4. **Enable rate limiting** - Prevent spam
5. **Monitor logs** - Catch errors early
6. **Test before deploy** - Verify all commands
7. **Use webhook in production** - More efficient
8. **Keep dependencies updated** - Security patches

---

## 🔗 Resources

- [Telegram Bot API Docs](https://core.telegram.org/bots/api)
- [python-telegram-bot Docs](https://docs.python-telegram-bot.org/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Strategy Engine Pro Repo](https://github.com/denisprosperous/v0-strategy-engine-pro)

---

## ❓ FAQ

**Q: Can multiple users use the bot simultaneously?**
A: Yes, the bot handles multiple users concurrently.

**Q: How do I get notified of new signals?**
A: Automatic notifications will be implemented in Phase 2.

**Q: Can I use this on a phone?**
A: Yes! Telegram works on all devices.

**Q: Is this secure?**
A: Yes, with proper configuration (user restrictions, admin controls, HTTPS webhook).

**Q: Can I customize the messages?**
A: Yes, edit formatting functions in `utils.py`.

---

## 🎉 Next Steps

1. **Test the bot** - Try all commands
2. **Customize settings** - Adjust to your needs
3. **Integrate with backend** - Connect to live trading
4. **Add notifications** - Real-time signal alerts
5. **Extend functionality** - Add custom commands

---

**Status:** ✅ **COMPLETE & READY TO USE**

**Author:** v0-strategy-engine-pro  
**Version:** 1.0  
**Last Updated:** 2025-01-26
