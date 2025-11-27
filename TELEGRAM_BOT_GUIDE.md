# 🤖 Telegram Bot Integration Guide

## Overview

The **v0-strategy-engine-pro** Telegram bot provides a mobile-friendly interface to monitor and control your trading bot. Access real-time portfolio data, AI analysis, trading signals, and performance metrics directly from Telegram.

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- FastAPI backend running (see main README)
- Telegram account

### Setup Steps

#### 1. Create Your Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow prompts to choose a name and username
4. Save your bot token (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Backend API URL
API_URL=http://localhost:8000

# Admin Credentials (for backend authentication)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme

# JWT Secret (must match backend)
JWT_SECRET_KEY=your-secret-key-change-in-production
```

⚠️ **Security Warning**: Change default credentials in production!

#### 3. Install Dependencies

```bash
pip install python-telegram-bot aiohttp
```

#### 4. Start the Backend

```bash
# In terminal 1
cd api
python main.py
```

Backend will run on http://localhost:8000

#### 5. Start the Telegram Bot

```bash
# In terminal 2
cd telegram_integration
python bot.py
```

#### 6. Start Chatting

Open Telegram, find your bot, and send `/start`!

---

## 📱 Available Commands

### 📊 Portfolio & Trading

| Command | Description | Example |
|---------|-------------|--------|
| `/status` | View bot status and overview | `/status` |
| `/portfolio` | View portfolio balances | `/portfolio` |
| `/signals` | Get recent trading signals | `/signals` |
| `/performance` | View performance metrics | `/performance` |

### ⚙️ Bot Control

| Command | Description | Example |
|---------|-------------|--------|
| `/startbot` | Start the trading bot | `/startbot` |
| `/stopbot` | Stop the trading bot | `/stopbot` |
| `/mode` | Set trading mode | `/mode semi` |

**Trading Modes:**
- `auto` - Fully automated trading
- `manual` - Manual confirmation required for all trades
- `semi` / `semi-auto` - AI suggestions with user confirmation

### 🤖 AI Features

| Command | Description | Example |
|---------|-------------|--------|
| `/ai_analysis` | Get AI market analysis | `/ai_analysis BTC/USDT` |
| `/sentiment` | Get sentiment analysis | `/sentiment BTC` |

### ℹ️ Information

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and introduction |
| `/help` | Show all available commands |

---

## 🏗️ Architecture

### Component Overview

```
Telegram Bot (telegram_integration/)
    │
    ├── bot.py              - Main bot initialization
    ├── handlers.py         - Command handlers
    ├── api_client.py       - Backend API communication
    └── utils.py            - Formatting and validation
          |
          ↓
    FastAPI Backend (api/)
          |
          ↓
    Trading Engine
```

### Key Features

#### 1. **Singleton API Client**
- Single session for all API requests
- Automatic authentication on startup
- Token management and caching

#### 2. **Comprehensive Error Handling**
- User-friendly error messages
- Detailed troubleshooting guidance
- Connection error recovery

#### 3. **Mode Normalization**
- Converts `"semi"` to `"semi-auto"` automatically
- Validates all trading modes before sending to backend

#### 4. **Message Formatting**
- Beautiful emoji-enhanced messages
- Markdown formatting for readability
- Consistent response structure

---

## 🔧 Troubleshooting

### Bot Not Responding

**Problem**: Bot doesn't respond to commands

**Solutions**:
1. Check bot is running: `ps aux | grep bot.py`
2. Verify bot token in `.env`
3. Check logs for errors: `tail -f logs/bot.log`
4. Restart bot: `python telegram_integration/bot.py`

### Authentication Failed

**Problem**: "Authentication failed" error

**Solutions**:
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `.env`
3. Ensure credentials match backend configuration
4. Restart both backend and bot

### Cannot Connect to Backend

**Problem**: "Cannot connect to trading backend" error

**Solutions**:
1. **Check backend is running**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Verify API_URL**:
   - Should be `http://localhost:8000` for local development
   - Check `.env` file

3. **Check firewall**:
   - Ensure port 8000 is not blocked
   - For remote backend, check network connectivity

4. **Check logs**:
   ```bash
   # Backend logs
   tail -f logs/api.log
   
   # Bot logs
   tail -f logs/bot.log
   ```

### AI Endpoints Not Found (404 Error)

**Problem**: `/ai_analysis` or `/sentiment` returns "not found"

**Solutions**:
1. **Update backend code**: Ensure you have the latest `api/main.py` with AI endpoints
2. **Restart backend**: `python api/main.py`
3. **Verify endpoints**:
   ```bash
   curl http://localhost:8000/api/ai/analyze
   curl http://localhost:8000/api/ai/sentiment
   ```

### Mode Command Not Working

**Problem**: `/mode semi` fails

**Solutions**:
1. Bot automatically normalizes `"semi"` to `"semi-auto"`
2. Try full mode name: `/mode semi-auto`
3. Valid modes: `auto`, `manual`, `semi-auto`

---

## 🔐 Security Best Practices

### 1. **Environment Variables**
```bash
# NEVER commit .env file
echo ".env" >> .gitignore

# Use strong secrets in production
JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

### 2. **Change Default Credentials**
```bash
# In production, update .env:
ADMIN_USERNAME=your_secure_username
ADMIN_PASSWORD=your_strong_password_here
```

### 3. **Restrict Bot Access**
- Use Telegram's bot privacy settings
- Consider implementing user whitelist
- Monitor bot logs for suspicious activity

### 4. **HTTPS in Production**
```bash
# Use HTTPS for production backend
API_URL=https://your-secure-domain.com
```

### 5. **Rate Limiting**
- Bot includes basic rate limiting
- Consider adding user-level rate limits
- Monitor for abuse in logs

---

## 📚 Development Guide

### Adding New Commands

#### 1. Create Handler Function

In `telegram_integration/handlers.py`:

```python
async def my_new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mynewcommand."""
    logger.info(f"User {update.effective_user.username} used mynewcommand")
    
    await update.message.chat.send_action("typing")
    
    # Get data from API
    data = await api_client.some_endpoint()
    
    # Format and send
    message = format_my_data(data)
    await update.message.reply_text(message, parse_mode="Markdown")
```

#### 2. Register Handler

In `telegram_integration/bot.py`, add to `register_handlers()`:

```python
self.application.add_handler(CommandHandler("mynewcommand", handlers.my_new_command))
```

#### 3. Add Formatting Function (Optional)

In `telegram_integration/utils.py`:

```python
def format_my_data(data: Dict[str, Any]) -> str:
    """Format my data into readable message."""
    if "error" in data:
        return format_error_message(data)
    
    message = "🎯 **My Data**\n\n"
    message += f"Value: {data.get('value')}\n"
    return message
```

#### 4. Update Help Command

Add to help text in `handlers.py`:

```python
"/mynewcommand - Description of what it does\n"
```

### Adding New API Endpoints

If you need a new backend endpoint, add to `api/main.py` and `telegram_integration/api_client.py`.

---

## 🧪 Testing

### Manual Testing

1. Start backend and bot
2. Send each command to bot
3. Verify responses
4. Test error cases (stop backend, invalid inputs, etc.)

### Test Checklist

- [ ] `/start` - Welcome message displays
- [ ] `/help` - All commands listed
- [ ] `/status` - Bot status shows
- [ ] `/portfolio` - Balances display correctly
- [ ] `/signals` - Recent signals show
- [ ] `/performance` - Metrics display
- [ ] `/mode auto` - Mode changes
- [ ] `/mode semi` - Normalized to semi-auto
- [ ] `/ai_analysis` - Analysis displays
- [ ] `/sentiment BTC` - Sentiment shows
- [ ] Backend offline - Error message helpful
- [ ] Invalid credentials - Auth error clear

---

## 📞 Support & Resources

### Getting Help

1. **Check logs**: `tail -f logs/bot.log`
2. **Review this guide**: Especially troubleshooting section
3. **Check backend docs**: Main `README.md`
4. **Verify environment**: All variables in `.env`

### Useful Links

- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

### Common Issues on GitHub

- Check Issues tab for similar problems
- Search for your error message
- Include logs when reporting bugs

---

## 🎯 Next Steps

1. ✅ Set up and test basic commands
2. 📊 Customize message formatting in `utils.py`
3. 🔐 Change default credentials
4. 🚀 Deploy to production (use HTTPS and secure .env)
5. 📈 Monitor usage and optimize
6. 🆕 Add custom commands for your needs

---

## 📝 File Structure

```
telegram_integration/
├── bot.py              # Main bot initialization & lifecycle
├── handlers.py         # All command handler functions
├── api_client.py       # Backend API communication (singleton)
├── utils.py            # Formatting, validation, helpers
├── alert_manager.py    # Alert management (existing)
├── bot_config.py       # Configuration (existing)
├── sniper_bot.py       # Sniper functionality (existing)
└── webhook_handler.py  # Webhook support (existing)
```

---

## ✨ Features Summary

✅ **Complete Command Set** - All trading operations via Telegram  
✅ **AI Integration** - Market analysis and sentiment tracking  
✅ **Robust Error Handling** - Clear, actionable error messages  
✅ **Singleton API Client** - Efficient session management  
✅ **Mode Normalization** - Automatic conversion of shorthand modes  
✅ **Beautiful Formatting** - Emoji-enhanced, readable messages  
✅ **Authentication** - Secure backend communication  
✅ **Graceful Shutdown** - Proper cleanup on exit  
✅ **Comprehensive Logging** - Easy debugging and monitoring  

---

**Happy Trading! 🚀📈**
