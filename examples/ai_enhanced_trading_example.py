#!/usr/bin/env python3
"""
AI-Enhanced Trading Bot - Complete Example

Demonstrates full integration of AI ensemble with trading pipeline:
- Configuration loading
- AI initialization
- Signal generation with AI enhancement
- Risk assessment
- Statistics monitoring

Author: v0-strategy-engine-pro
Version: 1.0 - Segment 3 Complete
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from signal_generation.signal_engine_ai_enhanced import AIEnhancedSignalEngine
    from signal_generation.signal_engine import SignalTier, SignalDirection
    from ai_models.ai_config import AIConfigManager
    from ai_models.ai_integration_adapter import AIIntegrationAdapter
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all modules are properly installed")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ai_trading_bot.log')
    ]
)

logger = logging.getLogger(__name__)


class AITradingBot:
    """
    Complete AI-enhanced trading bot example.
    
    Features:
    - AI ensemble integration
    - Signal generation with enhancement
    - Risk assessment
    - Statistics tracking
    """
    
    def __init__(self, enable_ai: bool = True):
        """
        Initialize trading bot.
        
        Args:
            enable_ai: Enable AI enhancement
        """
        self.enable_ai = enable_ai
        self.signal_engine: Optional[AIEnhancedSignalEngine] = None
        self.config_manager: Optional[AIConfigManager] = None
        self.is_initialized = False
        
        logger.info("🤖 AI Trading Bot initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize all components.
        
        Returns:
            Success status
        """
        try:
            logger.info("🔧 Initializing components...")
            
            # Load configuration
            self.config_manager = AIConfigManager()
            config = self.config_manager.get_config()
            
            logger.info(f"📋 Configuration loaded:")
            logger.info(f"   - AI Enabled: {config.ai_enabled}")
            logger.info(f"   - Min Providers: {config.min_providers}")
            logger.info(f"   - Min Confidence: {config.min_confidence}")
            
            # Initialize signal engine
            self.signal_engine = AIEnhancedSignalEngine(
                enable_ai=self.enable_ai and config.ai_enabled,
                ai_min_confidence=config.min_confidence
            )
            
            # Initialize AI if enabled
            if self.enable_ai and config.ai_enabled:
                logger.info("🤖 Initializing AI ensemble...")
                ai_ready = await self.signal_engine.initialize_ai()
                
                if ai_ready:
                    api_keys = self.config_manager.get_api_keys()
                    logger.info(f"✅ AI ensemble ready with {len(api_keys)} providers:")
                    for provider in api_keys.keys():
                        logger.info(f"   - {provider}")
                else:
                    logger.warning("⚠️  AI initialization failed - running without AI")
            else:
                logger.info("ℹ️  AI enhancement disabled")
            
            self.is_initialized = True
            logger.info("✅ All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}", exc_info=True)
            return False
    
    async def generate_signal(
        self,
        symbol: str = "BTC/USDT",
        timeframe: str = "1h",
        # Market data
        current_price: float = 42000,
        volume_ratio: float = 1.6,
        atr: float = 350,
        volume: Optional[float] = 1250000,
        # Technical indicators
        rsi: float = 28.5,
        ema_20: float = 42100,
        ema_50: float = 41800,
        ema_200: float = 41000,
        # Fibonacci levels
        fib_levels: Optional[dict] = None
    ):
        """
        Generate trading signal with AI enhancement.
        
        Args:
            symbol: Trading symbol
            timeframe: Chart timeframe
            current_price: Current price
            volume_ratio: Volume ratio
            atr: Average True Range
            volume: Current volume
            rsi: RSI value
            ema_20: 20-period EMA
            ema_50: 50-period EMA
            ema_200: 200-period EMA
            fib_levels: Fibonacci retracement levels
        
        Returns:
            Trading signal or None
        """
        if not self.is_initialized:
            logger.error("Bot not initialized. Call initialize() first.")
            return None
        
        if fib_levels is None:
            fib_levels = {0.618: current_price, 0.382: current_price * 1.024, 0.786: current_price * 0.976}
        
        # Signal engine configuration
        config = {
            'fib_tolerance_atr': 0.1,
            'rsi_tier1_max': 30,
            'rsi_tier2_range': (25, 35),
            'rsi_skip_above': 70,
            'rsi_skip_below': 15,
            'volume_tier1_min': 1.5,
            'volume_tier2_min': 1.2,
            'volume_tier3_min': 1.0,
            'stop_atr_mult': 2.0
        }
        
        logger.info(f"📊 Generating signal for {symbol} @ ${current_price:,.2f}")
        
        try:
            # Generate AI-enhanced signal
            signal = await self.signal_engine.classify_signal_with_ai(
                symbol=symbol,
                timeframe=timeframe,
                fib_levels=fib_levels,
                rsi=rsi,
                ema_20=ema_20,
                ema_50=ema_50,
                ema_200=ema_200,
                current_price=current_price,
                volume_ratio=volume_ratio,
                atr=atr,
                config=config,
                volume=volume
            )
            
            if signal:
                self._print_signal(signal)
            else:
                logger.info("❌ No signal generated (filters not met or AI blocked)")
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Error generating signal: {e}", exc_info=True)
            return None
    
    def _print_signal(self, signal):
        """Print formatted signal information."""
        print("\n" + "="*60)
        print("📈 TRADING SIGNAL GENERATED")
        print("="*60)
        
        print(f"\n🎯 Basic Info:")
        print(f"   Symbol:      {signal.symbol}")
        print(f"   Direction:   {signal.direction.value.upper()}")
        print(f"   Tier:        {signal.tier.value[0]}")
        print(f"   Confidence:  {signal.confidence:.1f}%")
        print(f"   Timestamp:   {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        print(f"\n💰 Price Levels:")
        print(f"   Entry:       ${signal.entry_price:,.2f}")
        print(f"   Stop Loss:   ${signal.stop_loss:,.2f} ({signal.stop_loss_percent:.2f}%)")
        print(f"   TP1:         ${signal.take_profit_1:,.2f}")
        print(f"   TP2:         ${signal.take_profit_2:,.2f}")
        print(f"   R:R Ratio:   1:{signal.risk_reward_ratio:.1f}")
        
        print(f"\n📊 Technical Indicators:")
        print(f"   RSI:         {signal.rsi_value:.1f}")
        print(f"   EMA 20:      ${signal.ema_20:,.2f}")
        print(f"   EMA 50:      ${signal.ema_50:,.2f}")
        print(f"   EMA 200:     ${signal.ema_200:,.2f}")
        print(f"   Fib Level:   {signal.fib_level_touched}")
        print(f"   Volume:      {signal.volume_ratio:.2f}x")
        
        # AI metadata if available
        if hasattr(signal, 'ai_metadata') and signal.ai_metadata:
            ai_meta = signal.ai_metadata
            print(f"\n🤖 AI Enhancement:")
            print(f"   AI Signal:      {ai_meta.get('ai_signal', 'N/A')}")
            print(f"   AI Confidence:  {ai_meta.get('ai_confidence', 0):.2f}")
            print(f"   AI Risk:        {ai_meta.get('ai_risk_level', 'N/A')}")
            print(f"   Sentiment:      {ai_meta.get('ai_sentiment_score', 0):.2f}")
            print(f"   Consensus:      {'✅' if ai_meta.get('ensemble_consensus') else '❌'}")
            print(f"   Providers:      {ai_meta.get('provider_count', 0)}")
            print(f"   Latency:        {ai_meta.get('execution_time_ms', 0):.1f}ms")
        
        print("\n" + "="*60 + "\n")
    
    def print_statistics(self):
        """Print bot statistics."""
        if not self.is_initialized or not self.signal_engine:
            logger.warning("Bot not initialized")
            return
        
        stats = self.signal_engine.get_ai_stats()
        
        print("\n" + "="*60)
        print("📊 BOT STATISTICS")
        print("="*60)
        
        print(f"\nAI Status:")
        print(f"   Enabled:        {stats.get('ai_enabled', False)}")
        print(f"   Initialized:    {stats.get('ai_initialized', False)}")
        
        print(f"\nSignal Statistics:")
        print(f"   AI Enhanced:    {stats.get('signals_ai_enhanced', 0)}")
        print(f"   AI Boosted:     {stats.get('signals_ai_boosted', 0)}")
        print(f"   AI Blocked:     {stats.get('signals_ai_blocked', 0)}")
        print(f"   AI Neutral:     {stats.get('signals_ai_neutral', 0)}")
        
        if 'adapter_stats' in stats:
            adapter_stats = stats['adapter_stats']
            print(f"\nAdapter Statistics:")
            print(f"   Risk Assessments:  {adapter_stats.get('risk_assessments', 0)}")
            print(f"   Sentiment Analyses: {adapter_stats.get('sentiment_analyses', 0)}")
            print(f"   Errors:            {adapter_stats.get('errors', 0)}")
        
        print("\n" + "="*60 + "\n")


async def main():
    """Main execution function."""
    print("\n" + "="*60)
    print("🚀 AI-ENHANCED TRADING BOT")
    print("="*60 + "\n")
    
    # Initialize bot
    bot = AITradingBot(enable_ai=True)
    
    success = await bot.initialize()
    
    if not success:
        print("❌ Failed to initialize bot. Check logs for details.")
        return
    
    print("\n" + "-"*60)
    print("EXAMPLE 1: Generate Signal with Default Parameters")
    print("-"*60 + "\n")
    
    # Example 1: Default parameters
    signal1 = await bot.generate_signal()
    
    await asyncio.sleep(1)  # Brief pause
    
    print("\n" + "-"*60)
    print("EXAMPLE 2: Generate Signal with Custom Parameters")
    print("-"*60 + "\n")
    
    # Example 2: Custom parameters (strong bullish setup)
    signal2 = await bot.generate_signal(
        symbol="ETH/USDT",
        current_price=2200,
        rsi=22.5,  # Strong oversold
        ema_20=2210,
        ema_50=2180,
        ema_200=2100,
        volume_ratio=2.1,  # Strong volume surge
        atr=45,
        fib_levels={0.618: 2200, 0.382: 2280, 0.786: 2150}
    )
    
    await asyncio.sleep(1)
    
    print("\n" + "-"*60)
    print("EXAMPLE 3: Generate Signal (Potential AI Block)")
    print("-"*60 + "\n")
    
    # Example 3: Risky setup (may be blocked by AI)
    signal3 = await bot.generate_signal(
        symbol="SOL/USDT",
        current_price=95,
        rsi=72,  # Overbought
        ema_20=96,
        ema_50=94,
        ema_200=92,
        volume_ratio=0.8,  # Low volume
        atr=3.5
    )
    
    # Print statistics
    bot.print_statistics()
    
    print("\n✅ Demo completed successfully!\n")


def check_environment():
    """Check if required environment variables are set."""
    required_vars = {
        'OPENAI_API_KEY': 'OpenAI',
        'ANTHROPIC_API_KEY': 'Anthropic (Claude)',
        'GOOGLE_API_KEY': 'Google (Gemini)',
        'XAI_API_KEY': 'xAI (Grok)'
    }
    
    print("\n🔍 Checking Environment Variables...\n")
    
    found_count = 0
    for var, name in required_vars.items():
        value = os.getenv(var)
        if value:
            masked = value[:8] + "..." if len(value) > 8 else "***"
            print(f"   ✅ {name:20s} ({var}): {masked}")
            found_count += 1
        else:
            print(f"   ❌ {name:20s} ({var}): Not set")
    
    print(f"\n📊 Found {found_count}/{len(required_vars)} API keys\n")
    
    if found_count == 0:
        print("⚠️  WARNING: No AI API keys found!")
        print("   The bot will run without AI enhancement.")
        print("\n   To enable AI, set at least one API key:")
        print("   export OPENAI_API_KEY='your-key-here'")
        print("\n   See docs/AI_INTEGRATION_GUIDE.md for details.\n")
    elif found_count < len(required_vars):
        print(f"ℹ️  INFO: Running with {found_count} provider(s).")
        print("   Add more API keys for better AI consensus.\n")
    else:
        print("✅ All providers configured!\n")
    
    return found_count > 0


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🤖 AI-ENHANCED TRADING BOT - EXAMPLE LAUNCHER")
    print("="*60)
    
    # Check environment
    has_api_keys = check_environment()
    
    if not has_api_keys:
        response = input("Continue without AI? (y/n): ").strip().lower()
        if response != 'y':
            print("\n👋 Exiting. Set up API keys and try again.\n")
            sys.exit(0)
    
    try:
        # Run main async function
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Shutting down...\n")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
