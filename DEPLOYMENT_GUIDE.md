# 🚀 Deployment Guide - v0-strategy-engine-pro

Comprehensive deployment guide for the trading bot with Telegram integration.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Docker Deployment](#docker-deployment)
4. [Manual Deployment](#manual-deployment)
5. [Telegram Bot Configuration](#telegram-bot-configuration)
6. [Security Setup](#security-setup)
7. [Monitoring & Logging](#monitoring--logging)
8. [Troubleshooting](#troubleshooting)
9. [Production Checklist](#production-checklist)

---

## 🔧 Prerequisites

### System Requirements

- **OS:** Ubuntu 20.04+ / Debian 11+ / CentOS 8+ (or any Linux with Docker support)
- **RAM:** Minimum 2GB, Recommended 4GB+
- **CPU:** 2+ cores recommended
- **Storage:** 20GB+ available space
- **Network:** Stable internet connection with low latency

### Required Software

\`\`\`bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install Docker (recommended)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Install Git
sudo apt install git -y
\`\`\`

### Exchange API Access

1. **Binance:** Create API keys at https://www.binance.com/en/my/settings/api-management
2. **Bitget:** https://www.bitget.com/en/account/newapi
3. **Bybit:** https://www.bybit.com/app/user/api-management
4. **MEXC:** https://www.mexc.com/user/openapi
5. **OKX:** https://www.okx.com/account/my-api
6. **Phemex:** https://phemex.com/account/api-manage

**Important:** Enable only necessary permissions (Read + Trade). Never enable withdrawal permissions.

---

## 🌍 Environment Setup

### 1. Clone Repository

\`\`\`bash
git clone https://github.com/denisprosperous/v0-strategy-engine-pro.git
cd v0-strategy-engine-pro
\`\`\`

### 2. Create Environment File

\`\`\`bash
cp .env.example .env
nano .env  # or use your preferred editor
\`\`\`

### 3. Configure Environment Variables

Edit `.env` with your settings:

\`\`\`bash
# ==========================================
# APPLICATION SETTINGS
# ==========================================
APP_ENV=production
DEBUG=False
LOG_LEVEL=INFO

# ==========================================
# TELEGRAM BOT CONFIGURATION
# ==========================================
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
WEBHOOK_URL=https://yourdomain.com/webhook
WEBHOOK_SECRET_TOKEN=generate_random_secure_token_here
WEBHOOK_PORT=8443

# ==========================================
# EXCHANGE API KEYS (add only what you need)
# ==========================================

# Binance
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
BINANCE_TESTNET=False

# Bitget  
BITGET_API_KEY=your_bitget_api_key
BITGET_API_SECRET=your_bitget_api_secret
BITGET_PASSPHRASE=your_bitget_passphrase

# Bybit
BYBIT_API_KEY=your_bybit_api_key
BYBIT_API_SECRET=your_bybit_api_secret
BYBIT_TESTNET=False

# MEXC
MEXC_API_KEY=your_mexc_api_key
MEXC_API_SECRET=your_mexc_api_secret

# OKX
OKX_API_KEY=your_okx_api_key
OKX_API_SECRET=your_okx_api_secret
OKX_PASSPHRASE=your_okx_passphrase

# Phemex
PHEMEX_API_KEY=your_phemex_api_key
PHEMEX_API_SECRET=your_phemex_api_secret
PHEMEX_TESTNET=False

# ==========================================
# TRADING MODE SETTINGS
# ==========================================
DEFAULT_TRADING_MODE=SEMI_AUTO  # Options: MANUAL, SEMI_AUTO, FULL_AUTO
CONFIRMATION_TIMEOUT_SECONDS=60
MAX_PENDING_SIGNALS=10

# ==========================================
# RISK MANAGEMENT
# ==========================================
MAX_POSITION_SIZE_USD=1000
MAX_LEVERAGE=5
STOP_LOSS_PERCENTAGE=2.0
TAKE_PROFIT_PERCENTAGE=5.0

# ==========================================
# DATABASE (Optional - for production)
# ==========================================
DATABASE_URL=postgresql://user:password@localhost:5432/trading_bot

# ==========================================
# REDIS (Optional - for caching)
# ==========================================
REDIS_URL=redis://localhost:6379/0
\`\`\`

---

## 🐳 Docker Deployment (Recommended)

### Option 1: Using Docker Compose

#### 1. Start Services

\`\`\`bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
\`\`\`

#### 2. Stop Services

\`\`\`bash
docker-compose down
\`\`\`

#### 3. Restart Services

\`\`\`bash
docker-compose restart
\`\`\`

### Option 2: Using Docker Only

\`\`\`bash
# Build image
docker build -t trading-bot:latest .

# Run container
docker run -d \
  --name trading-bot \
  --env-file .env \
  -p 8443:8443 \
  --restart unless-stopped \
  trading-bot:latest

# View logs
docker logs -f trading-bot

# Stop container
docker stop trading-bot

# Remove container
docker rm trading-bot
\`\`\`

---

## 🔨 Manual Deployment (Without Docker)

### 1. Create Virtual Environment

\`\`\`bash
python3.11 -m venv venv
source venv/bin/activate
\`\`\`

### 2. Install Dependencies

\`\`\`bash
pip install --upgrade pip
pip install -r requirements.txt
\`\`\`

### 3. Run Application

\`\`\`bash
# Using the start script
chmod +x start.sh
./start.sh

# Or run directly
python main.py
\`\`\`

### 4. Setup Systemd Service (Production)

Create `/etc/systemd/system/trading-bot.service`:

\`\`\`ini
[Unit]
Description=v0 Strategy Engine Pro - Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/v0-strategy-engine-pro
Environment="PATH=/home/ubuntu/v0-strategy-engine-pro/venv/bin"
EnvironmentFile=/home/ubuntu/v0-strategy-engine-pro/.env
ExecStart=/home/ubuntu/v0-strategy-engine-pro/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/trading-bot/output.log
StandardError=append:/var/log/trading-bot/error.log

[Install]
WantedBy=multi-user.target
\`\`\`

### 5. Enable and Start Service

\`\`\`bash
# Create log directory
sudo mkdir -p /var/log/trading-bot
sudo chown $USER:$USER /var/log/trading-bot

# Reload systemd
sudo systemctl daemon-reload

# Enable service on boot
sudo systemctl enable trading-bot

# Start service
sudo systemctl start trading-bot

# Check status
sudo systemctl status trading-bot

# View logs
sudo journalctl -u trading-bot -f
\`\`\`

---

## 🤖 Telegram Bot Configuration

### 1. Create Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow prompts to name your bot
4. Copy the bot token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
5. Save token in `.env` as `TELEGRAM_BOT_TOKEN`

### 2. Set Webhook URL

**Important:** Telegram requires HTTPS. Use one of these options:

#### Option A: Using Ngrok (for testing)

\`\`\`bash
# Install ngrok
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar -xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/

# Start ngrok tunnel
ngrok http 8443

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Update .env with WEBHOOK_URL=https://abc123.ngrok.io/webhook
\`\`\`

#### Option B: Using Domain with SSL (production)

\`\`\`bash
# Install Certbot for Let's Encrypt
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com

# Configure Nginx reverse proxy
sudo nano /etc/nginx/sites-available/trading-bot
\`\`\`

Add this configuration:

\`\`\`nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location /webhook {
        proxy_pass http://localhost:8443/webhook;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://localhost:8443/health;
    }
}
\`\`\`

\`\`\`bash
# Enable site
sudo ln -s /etc/nginx/sites-available/trading-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
\`\`\`

### 3. Register Webhook with Telegram

\`\`\`bash
# Set webhook
curl -X POST https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yourdomain.com/webhook",
    "secret_token": "your_webhook_secret_token",
    "max_connections": 40,
    "allowed_updates": ["message", "callback_query"]
  }'

# Verify webhook
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
\`\`\`

Expected response:
\`\`\`json
{
  "ok": true,
  "result": {
    "url": "https://yourdomain.com/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0,
    "max_connections": 40
  }
}
\`\`\`

### 4. Test Bot

Send a message to your bot on Telegram:
- `/start` - Should receive welcome message
- `/help` - Should show available commands
- `/mode` - Should show current trading mode

---

## 🔒 Security Setup

### 1. Generate Secure Tokens

\`\`\`bash
# Generate webhook secret token
openssl rand -hex 32

# Generate API secret (if needed)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
\`\`\`

### 2. Firewall Configuration

\`\`\`bash
# Install UFW
sudo apt install ufw -y

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTPS
sudo ufw allow 443/tcp

# Allow webhook port (if not using reverse proxy)
sudo ufw allow 8443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
\`\`\`

### 3. Secure Environment Variables

\`\`\`bash
# Restrict .env file permissions
chmod 600 .env

# Never commit .env to git
echo ".env" >> .gitignore
\`\`\`

### 4. API Key Security Best Practices

- ✅ Enable IP whitelisting on exchange APIs
- ✅ Use separate API keys for different exchanges
- ✅ Never enable withdrawal permissions
- ✅ Set strict rate limits
- ✅ Regularly rotate API keys
- ✅ Monitor API usage for anomalies
- ❌ Never share API keys or commit them to version control

---

## 📊 Monitoring & Logging

### 1. Log Files Location

\`\`\`bash
# Application logs (if using systemd)
/var/log/trading-bot/output.log
/var/log/trading-bot/error.log

# Or check with journalctl
sudo journalctl -u trading-bot -f

# Docker logs
docker logs -f trading-bot
\`\`\`

### 2. Key Metrics to Monitor

- **System Health:**
  - CPU usage: `top` or `htop`
  - Memory usage: `free -h`
  - Disk space: `df -h`
  - Network connectivity: `ping 8.8.8.8`

- **Application Health:**
  - Webhook status: Check `/health` endpoint
  - Trading mode status
  - Pending signals count
  - API rate limit usage

### 3. Set Up Health Check

\`\`\`bash
# Create health check script
cat > /usr/local/bin/check-trading-bot.sh << 'EOF'
#!/bin/bash
RESPONSE=$(curl -s http://localhost:8443/health)
if [[ $RESPONSE == *'"status":"healthy"'* ]]; then
    echo "Bot is healthy"
    exit 0
else
    echo "Bot is unhealthy: $RESPONSE"
    # Send alert (e.g., via email or Telegram)
    exit 1
fi
EOF

chmod +x /usr/local/bin/check-trading-bot.sh

# Add to crontab (check every 5 minutes)
crontab -e
# Add: */5 * * * * /usr/local/bin/check-trading-bot.sh
\`\`\`

### 4. Setup Log Rotation

Create `/etc/logrotate.d/trading-bot`:

\`\`\`
/var/log/trading-bot/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 ubuntu ubuntu
    sharedscripts
}
\`\`\`

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Webhook Not Receiving Updates

\`\`\`bash
# Check webhook status
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo

# Verify SSL certificate
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Check firewall
sudo ufw status

# Test webhook endpoint
curl -X POST https://yourdomain.com/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: your_secret" \
  -d '{"update_id": 123, "message": {}}'
\`\`\`

#### 2. Bot Not Responding

\`\`\`bash
# Check if service is running
sudo systemctl status trading-bot

# Check logs for errors
sudo journalctl -u trading-bot -n 100

# Restart service
sudo systemctl restart trading-bot

# Check application logs
tail -f /var/log/trading-bot/error.log
\`\`\`

#### 3. Exchange API Errors

\`\`\`bash
# Test API connectivity
python3 << 'EOF'
import ccxt
exchange = ccxt.binance({
    'apiKey': 'your_api_key',
    'secret': 'your_api_secret'
})
try:
    balance = exchange.fetch_balance()
    print("API connection successful")
    print(f"Balance: {balance['total']}")
except Exception as e:
    print(f"API Error: {e}")
EOF
\`\`\`

#### 4. Permission Errors

\`\`\`bash
# Fix file permissions
chmod 600 .env
chmod +x start.sh
sudo chown -R $USER:$USER /var/log/trading-bot

# Fix systemd service
sudo systemctl daemon-reload
sudo systemctl restart trading-bot
\`\`\`

#### 5. Docker Container Won't Start

\`\`\`bash
# Check Docker logs
docker logs trading-bot

# Remove and recreate container
docker stop trading-bot
docker rm trading-bot
docker-compose up -d

# Check resource usage
docker stats
\`\`\`

---

## ✅ Production Checklist

### Before Deployment

- [ ] All environment variables configured in `.env`
- [ ] API keys tested and working
- [ ] Telegram bot created and token obtained
- [ ] Domain name configured with SSL certificate
- [ ] Firewall rules configured
- [ ] Webhook URL registered with Telegram
- [ ] Secure tokens generated (webhook secret)
- [ ] File permissions set correctly (`.env` = 600)
- [ ] Log rotation configured
- [ ] Health check script created

### After Deployment

- [ ] Service running: `systemctl status trading-bot`
- [ ] Logs checking: `journalctl -u trading-bot -f`
- [ ] Webhook verified: `/getWebhookInfo` shows correct URL
- [ ] Bot responding to `/start` command
- [ ] Trading mode set correctly
- [ ] Test trade executed successfully (small amount)
- [ ] Alerts received on Telegram
- [ ] Health check endpoint responding
- [ ] Backup strategy in place
- [ ] Monitoring alerts configured

### Security Verification

- [ ] `.env` not in git repository
- [ ] API keys have minimal permissions (no withdrawal)
- [ ] IP whitelisting enabled on exchanges
- [ ] Firewall blocking unnecessary ports
- [ ] SSH key-only authentication
- [ ] Regular security updates: `sudo apt update && sudo apt upgrade`

---

## 📦 Backup & Recovery

### Create Backup

\`\`\`bash
# Backup configuration
tar -czf trading-bot-backup-$(date +%Y%m%d).tar.gz \
  .env \
  trading_mode_manager.py \
  telegram_integration/ \
  signal_generation/

# Store backup securely
mv trading-bot-backup-*.tar.gz ~/backups/
\`\`\`

### Restore from Backup

\`\`\`bash
# Extract backup
tar -xzf trading-bot-backup-YYYYMMDD.tar.gz

# Restart service
sudo systemctl restart trading-bot
\`\`\`

---

## 📞 Support

For issues and questions:

- **GitHub Issues:** https://github.com/denisprosperous/v0-strategy-engine-pro/issues
- **Documentation:** Check README.md and code comments
- **Telegram:** Test commands directly with your bot

---

## 📝 Quick Reference

### Essential Commands

\`\`\`bash
# Start bot
sudo systemctl start trading-bot

# Stop bot
sudo systemctl stop trading-bot

# Restart bot
sudo systemctl restart trading-bot

# View logs
sudo journalctl -u trading-bot -f

# Check webhook
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo

# Health check
curl http://localhost:8443/health
\`\`\`

### Bot Commands

- `/start` - Initialize bot
- `/help` - Show available commands
- `/mode` - Check current trading mode
- `/trade SYMBOL ACTION PRICE SIZE` - Manual trade
- `/stats` - View trading statistics

---

**🎉 Deployment complete! Your trading bot is ready for production.**

Remember to:
1. Start with small position sizes
2. Monitor closely in the first 24 hours
3. Keep API keys secure
4. Regular backups
5. Update software regularly
