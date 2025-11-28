# Configuration Guide

## Overview

This guide explains how to configure v0 Strategy Engine Pro using environment variables. The configuration is split across three files for better organization:

1. **`.env.example`** - Core configuration (database, exchanges, basic settings)
2. **`.env.ai.example`** - AI/LLM model configuration (11 providers)
3. **`.env.backtest.example`** - Backtesting and demo trading configuration

---

## Quick Start

### 1. Copy Configuration Files

\`\`\`bash
# Copy main configuration
cp .env.example .env

# Optional: Copy AI configuration if using AI features
cat .env.ai.example >> .env

# Optional: Copy backtest configuration if using demo/backtest modes
cat .env.backtest.example >> .env
\`\`\`

### 2. Essential Configuration

Edit `.env` and set these required values:

\`\`\`bash
# Telegram bot (required for notifications)
TELEGRAM_BOT_TOKEN=your_actual_bot_token
TELEGRAM_CHAT_ID=your_actual_chat_id

# At least one exchange
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret

# Trading mode
TRADING_MODE=demo  # Start with demo mode (no real money)
\`\`\`

### 3. Start the Engine

\`\`\`bash
python main.py
\`\`\`

---

## Trading Modes Explained

### Comparison Table

| Mode | Real Money | Risk Level | Use Case | Real-Time | Historical |
|------|------------|------------|----------|-----------|------------|
| **Manual** | Yes | User controlled | Manual trading only | ✅ | ❌ |
| **Semi-Auto** | Yes | Medium | Confirm each signal | ✅ | ❌ |
| **Auto** | Yes | High | Fully automated | ✅ | ❌ |
| **Demo** | No | None | Test signals safely | ✅ | ❌ |
| **Paper Trading** | No | None | Same as demo | ✅ | ❌ |
| **Backtest** | No | None | Test strategy on history | ❌ | ✅ |

### Mode Details

#### Manual Mode
\`\`\`bash
TRADING_MODE=manual
\`\`\`
- **Purpose**: Full control over every trade
- **How it works**: Engine sends trade signals via Telegram, you execute manually
- **Best for**: Experienced traders who want automation but maintain control
- **Risk**: Low (you decide each trade)

#### Semi-Auto Mode
\`\`\`bash
TRADING_MODE=semi_auto
\`\`\`
- **Purpose**: Automated signals with manual confirmation
- **How it works**: Engine sends signal, you confirm via Telegram, engine executes
- **Best for**: Traders who want automation but want to approve each trade
- **Risk**: Medium (automatic execution after confirmation)

#### Auto Mode
\`\`\`bash
TRADING_MODE=auto
\`\`\`
- **Purpose**: Fully automated trading
- **How it works**: Engine generates and executes trades automatically
- **Best for**: 24/7 trading without manual intervention
- **Risk**: High (no manual oversight)
- **⚠️ WARNING**: Only use after thorough testing in demo mode!

#### Demo Mode (Recommended for beginners)
\`\`\`bash
TRADING_MODE=demo
ENABLE_DEMO_MODE=true
DEMO_INITIAL_BALANCE=10000
\`\`\`
- **Purpose**: Test trade signals WITHOUT risking real money
- **How it works**: Simulates real trading with virtual funds
- **Best for**: Testing signals, learning the system, strategy validation
- **Risk**: None (virtual money only)
- **👍 RECOMMENDED**: Always start here!

#### Backtest Mode
\`\`\`bash
TRADING_MODE=backtest
ENABLE_BACKTESTING=true
BACKTEST_START_DATE=2023-01-01
BACKTEST_END_DATE=2024-12-31
\`\`\`
- **Purpose**: Test strategy against historical data
- **How it works**: Runs strategy on past data to see what would have happened
- **Best for**: Strategy development, parameter optimization
- **Risk**: None (historical testing only)
- **👍 RECOMMENDED**: Run before going live!

---

## Demo Trading Walkthrough

### What is Demo Trading?

Demo trading lets you **test your trade signals in real-time WITHOUT risking any real money**. It's like a flight simulator for trading.

### Configuration

\`\`\`bash
# Enable demo mode
TRADING_MODE=demo
ENABLE_DEMO_MODE=true

# Virtual capital (not real money!)
DEMO_INITIAL_BALANCE=10000  # Start with $10,000 virtual dollars

# Realistic simulation
DEMO_MAKER_FEE=0.001  # Simulates exchange fees
DEMO_TAKER_FEE=0.002
DEMO_SLIPPAGE=0.001  # Simulates price slippage

# Performance tracking
DEMO_TRACK_PERFORMANCE=true
DEMO_SAVE_HISTORY=true
DEMO_OUTPUT_DIR=./demo_results
\`\`\`

### Demo Trading Workflow

1. **Start engine in demo mode**
   \`\`\`bash
   python main.py
   \`\`\`

2. **Engine receives real market data and generates signals**
   - Just like live trading, but executes with virtual funds

3. **Trades are simulated**
   - Virtual balance increases/decreases based on performance
   - Fees and slippage are simulated

4. **Monitor performance**
   - Check `./demo_results/` for trade history
   - Get daily reports via Telegram

5. **When satisfied with demo results, switch to live**
   \`\`\`bash
   TRADING_MODE=semi_auto  # Or manual for more control
   \`\`\`

### Demo Trading Tips

✅ **Do:**
- Run demo for at least 1-2 weeks before going live
- Test different market conditions (trending, ranging, volatile)
- Verify win rate, profit factor, and drawdown
- Check that risk management rules work correctly

❌ **Don't:**
- Skip demo testing and go straight to live trading
- Assume demo performance = live performance (slippage may differ)
- Overtrade in demo (use realistic position sizes)

---

## Backtesting Walkthrough

### What is Backtesting?

Backtesting tests your strategy against **historical data** to see how it would have performed in the past. This helps validate your strategy before risking real money.

### Configuration

\`\`\`bash
# Enable backtesting
TRADING_MODE=backtest
ENABLE_BACKTESTING=true

# Historical period to test
BACKTEST_START_DATE=2023-01-01  # Start from Jan 1, 2023
BACKTEST_END_DATE=2024-12-31    # End at Dec 31, 2024

# Initial capital (virtual)
BACKTEST_INITIAL_CAPITAL=10000

# Symbols to test
BACKTEST_SYMBOLS=BTC/USDT,ETH/USDT,ADA/USDT

# Timeframe
BACKTEST_TIMEFRAME=1h  # 1-hour candles

# Generate report
BACKTEST_GENERATE_REPORT=true
BACKTEST_OUTPUT_DIR=./backtest_results
\`\`\`

### Running a Backtest

\`\`\`bash
python main.py
\`\`\`

The engine will:
1. Download historical data for specified symbols and period
2. Run your strategy against the data
3. Generate performance report in `./backtest_results/`

### Interpreting Results

 Check the HTML report for:
- **Total Return**: Overall profit/loss percentage
- **Sharpe Ratio**: Risk-adjusted return (>1.0 is good, >2.0 is excellent)
- **Max Drawdown**: Largest peak-to-trough decline (lower is better)
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profit / gross loss (>1.5 is good)

### Strategy Optimization

\`\`\`bash
# Enable optimization
BACKTEST_OPTIMIZE=true
BACKTEST_OPTIMIZATION_METRIC=sharpe_ratio
BACKTEST_OPTIMIZATION_METHOD=genetic
\`\`\`

This will automatically find the best strategy parameters.

---

## AI Model Configuration

### Supported Providers (11 Total)

| Provider | Best For | Cost | Speed |
|----------|----------|------|-------|
| OpenAI (GPT-4) | Complex analysis | $$$ | Medium |
| Anthropic (Claude) | Reasoning | $$$ | Medium |
| Google (Gemini) | Multi-modal | $$ | Fast |
| Grok (xAI) | Real-time | $ (free tier) | Fast |
| Perplexity | Market news | $$ | Fast |
| Groq | Fast inference | $ | Ultra-fast |
| Cohere | Embeddings | $$ | Fast |
| Mistral | Cost-effective | $ | Fast |

### Quick Setup

\`\`\`bash
# Primary model for analysis
AI_PRIMARY_MODEL=openai
OPENAI_API_KEY=sk-your_key_here

# Fallback if primary fails
AI_FALLBACK_MODEL=anthropic
ANTHROPIC_API_KEY=sk-ant-your_key_here

# Task-specific models
AI_SENTIMENT_MODEL=perplexity  # Best for real-time news
PERPLEXITY_API_KEY=your_key_here
\`\`\`

### Free Tier Options

**Grok (xAI)** - Free tier available:
\`\`\`bash
XAI_GROK_API_KEY=your_key
XAI_GROK_API_TIER=free
AI_PRIMARY_MODEL=xai_grok
\`\`\`

For complete AI configuration, see `.env.ai.example`.

---

## Exchange Configuration

### Supported Exchanges (10 Total)

1. Binance
2. Bitget
3. Bybit
4. Gate.io
5. Huobi/HTX
6. Kraken
7. KuCoin
8. MEXC
9. OKX
10. Phemex

### API Key Setup

For each exchange, you need:
1. API Key
2. API Secret
3. Passphrase (for some exchanges)

#### Example: Binance

1. Log into Binance
2. Go to Account → API Management
3. Create new API key
4. Enable trading permissions (but NOT withdrawals for safety)
5. Whitelist your IP address (recommended)
6. Copy credentials to `.env`:

\`\`\`bash
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
\`\`\`

### Security Best Practices

✅ **Do:**
- Use IP whitelisting
- Disable withdrawal permissions
- Use separate API keys for testing and production
- Rotate keys regularly

❌ **Don't:**
- Commit `.env` to Git (already in `.gitignore`)
- Share API keys
- Use same keys across multiple bots
- Enable withdrawal permissions

---

## Risk Management

### Essential Settings

\`\`\`bash
# Position sizing
DEFAULT_TRADE_SIZE=100  # $100 per trade
MAX_POSITION_SIZE=1000  # Never more than $1000 per position

# Loss limits
MAX_DAILY_LOSS=500  # Stop trading if lose $500 in a day
STOP_LOSS_PERCENTAGE=2.0  # 2% stop loss on each trade

# Profit targets
TAKE_PROFIT_PERCENTAGE=5.0  # 5% take profit
\`\`\`

### Recommended Risk Levels

#### Conservative (Recommended for beginners)
\`\`\`bash
DEFAULT_TRADE_SIZE=100
MAX_POSITION_SIZE=500  # 5% of $10k portfolio
MAX_DAILY_LOSS=200  # 2% of $10k portfolio
STOP_LOSS_PERCENTAGE=1.5
TAKE_PROFIT_PERCENTAGE=3.0
\`\`\`

#### Moderate
\`\`\`bash
DEFAULT_TRADE_SIZE=200
MAX_POSITION_SIZE=1000  # 10% of $10k portfolio
MAX_DAILY_LOSS=500  # 5% of $10k portfolio
STOP_LOSS_PERCENTAGE=2.0
TAKE_PROFIT_PERCENTAGE=5.0
\`\`\`

#### Aggressive (⚠️ Higher risk)
\`\`\`bash
DEFAULT_TRADE_SIZE=500
MAX_POSITION_SIZE=2000  # 20% of $10k portfolio
MAX_DAILY_LOSS=1000  # 10% of $10k portfolio
STOP_LOSS_PERCENTAGE=3.0
TAKE_PROFIT_PERCENTAGE=8.0
\`\`\`

---

## Production Deployment Checklist

### Pre-Launch

- [ ] Run backtests on at least 6 months of historical data
- [ ] Demo trade for minimum 2 weeks in current market conditions
- [ ] Verify win rate >50% and profit factor >1.5
- [ ] Test all exchanges connect successfully
- [ ] Verify Telegram notifications work
- [ ] Set appropriate risk limits
- [ ] Enable SSL/TLS for API connections
- [ ] Whitelist server IP on exchange accounts

### Launch Day

- [ ] Start with `TRADING_MODE=semi_auto` (not fully auto)
- [ ] Use small position sizes (50% of intended size)
- [ ] Monitor first 10 trades closely
- [ ] Check trade execution matches signals
- [ ] Verify fees and slippage are acceptable

### Post-Launch

- [ ] Monitor daily performance reports
- [ ] Review trade logs weekly
- [ ] Adjust parameters based on performance
- [ ] Keep emergency stop-loss limits updated
- [ ] Backup configuration files regularly

---

## Troubleshooting

### Common Issues

#### "API connection failed"
\`\`\`bash
# Check:
1. API keys are correct
2. IP is whitelisted on exchange
3. API has trading permissions
4. Exchange is not under maintenance
\`\`\`

#### "Insufficient balance"
\`\`\`bash
# Check:
1. DEFAULT_TRADE_SIZE < account balance
2. Account has enough margin (for futures)
3. Dust amounts blocking trades (min order size)
\`\`\`

#### "Telegram bot not responding"
\`\`\`bash
# Check:
1. TELEGRAM_BOT_TOKEN is correct
2. TELEGRAM_CHAT_ID is correct
3. Bot has permission to send messages
4. /start the bot in Telegram
\`\`\`

#### "Backtest fails to load data"
\`\`\`bash
# Check:
1. BACKTEST_START_DATE < BACKTEST_END_DATE
2. Exchange has historical data for that period
3. Symbol names are correct (e.g., BTC/USDT not BTCUSDT)
4. Internet connection is stable
\`\`\`

---

## Environment Variables Reference

### Quick Reference

\`\`\`bash
# Essential
TRADING_MODE=demo|manual|semi_auto|auto|backtest
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Exchange (at least one required)
BINANCE_API_KEY=key
BINANCE_API_SECRET=secret

# AI (optional)
AI_PRIMARY_MODEL=openai|anthropic|google|xai_grok|perplexity
OPENAI_API_KEY=key

# Risk Management
DEFAULT_TRADE_SIZE=100
MAX_DAILY_LOSS=500
STOP_LOSS_PERCENTAGE=2.0

# Demo Trading
DEMO_INITIAL_BALANCE=10000
DEMO_TRACK_PERFORMANCE=true

# Backtesting
BACKTEST_START_DATE=2023-01-01
BACKTEST_END_DATE=2024-12-31
BACKTEST_INITIAL_CAPITAL=10000
\`\`\`

For complete reference, see:
- `.env.example` - Core configuration
- `.env.ai.example` - AI models
- `.env.backtest.example` - Backtesting & demo

---

## Additional Resources

- [Main README](../README.md)
- [API Documentation](./API.md)
- [Trading Strategies](./STRATEGIES.md)
- [Deployment Guide](./DEPLOYMENT.md)

---

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review configuration files for inline comments
3. Open an issue on GitHub

---

**⚠️ IMPORTANT REMINDERS**

1. **Always start with demo trading** - Never risk real money without testing
2. **Run backtests first** - Validate your strategy on historical data
3. **Use proper risk management** - Never risk more than you can afford to lose
4. **Secure your API keys** - Never commit `.env` to version control
5. **Monitor your bot** - Automated trading requires supervision

---

*Last Updated: November 25, 2025*
