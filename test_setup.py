#!/usr/bin/env python3
"""
Test script to verify SmartTraderAI setup
"""

import asyncio
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_configuration():
    """Test configuration loading"""
    try:
        from app.config.settings import settings
        logger.info("✅ Configuration loaded successfully")
        
        # Test required settings
        required_settings = [
            'telegram_bot_token',
            'bitget_api_key',
            'bitget_secret_key',
            'bitget_passphrase',
            'kraken_api_key',
            'kraken_private_key',
            'openai_api_key',
            'huggingface_token'
        ]
        
        missing_settings = []
        for setting in required_settings:
            if not getattr(settings, setting, None):
                missing_settings.append(setting)
        
        if missing_settings:
            logger.warning(f"⚠️ Missing settings: {missing_settings}")
        else:
            logger.info("✅ All required settings are configured")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        return False

async def test_database():
    """Test database connection"""
    try:
        from app.models.database import init_db, get_db
        
        # Initialize database
        init_db()
        logger.info("✅ Database initialized successfully")
        
        # Test database session
        db = next(get_db())
        logger.info("✅ Database connection successful")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False

async def test_exchanges():
    """Test exchange connections"""
    try:
        from app.exchanges.bitget import BitgetExchange
        from app.exchanges.kraken import KrakenExchange
        from app.config.settings import settings
        
        # Test Bitget
        logger.info("Testing Bitget connection...")
        bitget = BitgetExchange(
            api_key=settings.bitget_api_key,
            secret_key=settings.bitget_secret_key,
            passphrase=settings.bitget_passphrase,
            testnet=settings.bitget_testnet
        )
        
        await bitget.connect()
        balance = await bitget.get_balance()
        logger.info(f"✅ Bitget connected successfully. Balance keys: {list(balance.keys())[:3]}")
        
        # Test Kraken
        logger.info("Testing Kraken connection...")
        kraken = KrakenExchange(
            api_key=settings.kraken_api_key,
            secret_key=settings.kraken_private_key,
            testnet=settings.kraken_testnet
        )
        
        await kraken.connect()
        balance = await kraken.get_balance()
        logger.info(f"✅ Kraken connected successfully. Balance keys: {list(balance.keys())[:3]}")
        
        # Cleanup
        await bitget.disconnect()
        await kraken.disconnect()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Exchange test failed: {e}")
        return False

async def test_ai_services():
    """Test AI services"""
    try:
        from app.ai.sentiment_analyzer import SentimentAnalyzer
        from app.ai.recommendation_engine import AIRecommendationEngine
        
        # Test sentiment analyzer
        logger.info("Testing sentiment analyzer...")
        sentiment_analyzer = SentimentAnalyzer()
        
        # Test text sentiment analysis
        test_text = "Bitcoin is showing strong bullish momentum with positive market sentiment."
        sentiment = await sentiment_analyzer.analyze_text_sentiment(test_text, "test")
        logger.info(f"✅ Sentiment analysis successful: {sentiment['sentiment_label']}")
        
        # Test recommendation engine
        logger.info("Testing recommendation engine...")
        recommendation_engine = AIRecommendationEngine()
        
        # Mock market data
        mock_data = {
            'current_price': 50000.0,
            'price_change_24h': 2.5,
            'volume_24h': 1000000,
            'ohlcv': []
        }
        
        recommendation = await recommendation_engine.generate_recommendation(
            'BTC/USDT', 'bitget', mock_data
        )
        logger.info(f"✅ Recommendation engine successful: {recommendation['recommendation']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ AI services test failed: {e}")
        return False

async def test_telegram_bot():
    """Test Telegram bot initialization"""
    try:
        from app.telegram.bot import TradingBot
        
        logger.info("Testing Telegram bot initialization...")
        bot = TradingBot()
        logger.info("✅ Telegram bot initialized successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Telegram bot test failed: {e}")
        return False

async def run_all_tests():
    """Run all tests"""
    logger.info("🧪 Starting SmartTraderAI setup tests...")
    logger.info("=" * 50)
    
    tests = [
        ("Configuration", test_configuration),
        ("Database", test_database),
        ("Exchanges", test_exchanges),
        ("AI Services", test_ai_services),
        ("Telegram Bot", test_telegram_bot)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Testing {test_name}...")
        try:
            result = await test_func()
            results[test_name] = result
            if result:
                logger.info(f"✅ {test_name} test passed")
            else:
                logger.error(f"❌ {test_name} test failed")
        except Exception as e:
            logger.error(f"❌ {test_name} test failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 Test Results Summary:")
    logger.info("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! SmartTraderAI is ready to run.")
        logger.info("Run 'python main.py' to start the application.")
    else:
        logger.warning("⚠️ Some tests failed. Please check the configuration and try again.")
    
    return passed == total

def main():
    """Main function"""
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Test runner failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
