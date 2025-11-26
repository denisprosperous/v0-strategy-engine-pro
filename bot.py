#!/usr/bin/env python3
"""
Telegram Trading Bot - Main Entry Point

Convenience wrapper to run the Telegram bot from the project root.

Usage:
    python bot.py

Make sure to set TELEGRAM_BOT_TOKEN environment variable first:
    export TELEGRAM_BOT_TOKEN="your_token_here"

For more information, see: telegram_integration/TELEGRAM_BOT_README.md

Author: v0-strategy-engine-pro
Version: 1.0
"""

import sys
import os
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from telegram_integration.bot import main
    
    if __name__ == "__main__":
        print("="*60)
        print("🤖 Strategy Engine Pro - Telegram Bot")
        print("="*60)
        print()
        print("📄 Documentation: telegram_integration/TELEGRAM_BOT_README.md")
        print("⚙️  Configuration: Set TELEGRAM_BOT_TOKEN in .env")
        print()
        print("Starting bot...")
        print()
        
        asyncio.run(main())

except ImportError as e:
    print("❌ Error: Required dependencies not installed")
    print()
    print("Please install Telegram bot dependencies:")
    print("  pip install -r telegram_integration/requirements.txt")
    print()
    print(f"Details: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Fatal error: {e}")
    sys.exit(1)
