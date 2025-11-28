# 🚀 Telegram Bot - Quick Reference

## ⚡ Quick Start (30 seconds)

\`\`\`bash
# 1. Install
pip install python-telegram-bot==20.7 aiohttp==3.9.1

# 2. Get token from @BotFather on Telegram

# 3. Set & Run
export TELEGRAM_BOT_TOKEN="your_token"
python bot.py
\`\`\`

---

## 📝 Commands Cheat Sheet

### Bot Control
\`\`\`
/start          - Welcome message
/help           - Show all commands
/status         - Bot status + controls
\`\`\`

### Trading Control (Admin Only)
\`\`\`
/start_trading  - Start bot
/stop_trading   - Stop bot
/mode [mode]    - Set mode: auto | manual | semi
\`\`\`

### Portfolio
\`\`\`
/balance        - Account balance
/portfolio      - Open positions
/exchanges      - Connected exchanges
\`\`\`

### Signals & Analysis
\`\`\`
/signals [n]    - Show n recent signals
/analyze [sym]  - AI analysis for symbol
/sentiment [sym]- Sentiment for symbol
\`\`\`

### Performance
\`\`\`
/performance    - Performance metrics
/trades [n]     - Show n recent trades
\`\`\`

---

## ⚙️ Configuration

### Minimal (.env)
\`\`\`bash
TELEGRAM_BOT_TOKEN=your_token
\`\`\`

### Secure (.env)
\`\`\`bash
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_ALLOWED_USERS=your_user_id
TELEGRAM_ADMIN_USERS=your_user_id
\`\`\`

**Get your user ID:** Message `@userinfobot` on Telegram

---

## 🔒 Security Levels

| Level | Access | Commands |
|-------|--------|----------|
| **Admin** | Full | All commands including start/stop trading |
| **User** | Limited | Status, balance, signals, performance |
| **Unauthorized** | None | Access denied message |

---

## 🐞 Troubleshooting

**Bot not responding?**
\`\`\`bash
# Check token
echo $TELEGRAM_BOT_TOKEN

# Check logs
tail -f telegram_bot.log
\`\`\`

**Permission denied?**
\`\`\`bash
# Add your user ID to .env
TELEGRAM_ALLOWED_USERS=123456789
\`\`\`

**API connection failed?**
\`\`\`bash
# Start backend first
python api/main.py

# Then start bot
python bot.py
\`\`\`

---

## 📚 Files Overview

| File | Purpose |
|------|--------|
| `bot.py` (root) | Entry point |
| `telegram_integration/bot.py` | Main runner |
| `telegram_integration/config.py` | Configuration |
| `telegram_integration/handlers.py` | Command handlers |
| `telegram_integration/api_client.py` | API integration |
| `telegram_integration/utils.py` | Helpers |
| `telegram_integration/TELEGRAM_BOT_README.md` | Full docs |

---

## 🚀 Deploy to Production

\`\`\`bash
# 1. Set webhook
TELEGRAM_WEBHOOK_URL=https://your-domain.com
TELEGRAM_WEBHOOK_PORT=8443

# 2. Configure security
TELEGRAM_ALLOWED_USERS=id1,id2,id3
TELEGRAM_ADMIN_USERS=id1

# 3. Enable HTTPS
# (webhook requires HTTPS)

# 4. Run
python bot.py
\`\`\`

---

## 📄 Full Documentation

See: **[TELEGRAM_BOT_README.md](TELEGRAM_BOT_README.md)** for complete guide.

---

**Need help?** Check the full README or open an issue!
