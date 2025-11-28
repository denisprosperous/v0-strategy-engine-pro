"""
Signal Engine (AI-Enhanced): Tier Classification with AI Ensemble Integration

Extends base signal engine with AI model ensemble integration:
- AI signal confirmation/rejection
- Confidence boosting from AI consensus
- Risk assessment integration
- Sentiment-aware signal filtering

Author: v0-strategy-engine-pro
Version: 2.0 - AI Enhanced (Segment 3)
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from .signal_engine import (
        SignalEngine,
        TradingSignal,
        SignalTier,
        SignalDirection,
        SignalStrength
    )
except ImportError:
    from signal_engine import (
        SignalEngine,
        TradingSignal,
        SignalTier,
        SignalDirection,
        SignalStrength
    )

try:
    from ai_models.ai_integration_adapter import AIIntegrationAdapter, AISignalEnhancement
except ImportError:
    AIIntegrationAdapter = None
    AISignalEnhancement = None

logger = logging.getLogger(__name__)


class AIEnhancedSignalEngine(SignalEngine):
    """
    AI-enhanced signal generation engine.
    
    Extends base SignalEngine with AI ensemble integration:
    - Technical signal generation (base class)
    - AI signal enhancement and validation
    - Confidence adjustment based on AI consensus
    - Risk-based signal filtering
    """
    
    def __init__(self, enable_ai: bool = True, ai_min_confidence: float = 0.6):
        """
        Initialize AI-enhanced signal engine.
        
        Args:
            enable_ai: Enable AI enhancement (requires API keys)
            ai_min_confidence: Minimum AI confidence for signal boost
        """
        super().__init__()
        
        self.enable_ai = enable_ai
        self.ai_min_confidence = ai_min_confidence
        self.ai_adapter: Optional[AIIntegrationAdapter] = None
        self.ai_initialized = False
        
        # AI-specific statistics
        self.ai_stats = {
            "signals_ai_enhanced": 0,
            "signals_ai_boosted": 0,
            "signals_ai_blocked": 0,
            "signals_ai_neutral": 0,
            "ai_initialization_errors": 0
        }
        
        logger.info(f"AIEnhancedSignalEngine initialized (AI={enable_ai})")
    
    async def initialize_ai(self) -> bool:
        """
        Initialize AI integration adapter.
        
        Returns:
            Success status
        """
        if not self.enable_ai or AIIntegrationAdapter is None:
            logger.info("AI integration disabled or unavailable")
            return False
        
        try:
            self.ai_adapter = AIIntegrationAdapter(
                enable_ai=True,
                min_providers=2,
                min_confidence=self.ai_min_confidence
            )
            
            self.ai_initialized = await self.ai_adapter.initialize()
            
            if self.ai_initialized:
                logger.info("AI ensemble successfully initialized")
            else:
                logger.warning("AI ensemble initialization failed")
            
            return self.ai_initialized
            
        except Exception as e:
            logger.error(f"Error initializing AI: {e}", exc_info=True)
            self.ai_stats["ai_initialization_errors"] += 1
            return False
    
    async def classify_signal_with_ai(
        self,
        symbol: str,
        timeframe: str,
        fib_levels: dict,
        rsi: float,
        ema_20: float,
        ema_50: float,
        ema_200: float,
        current_price: float,
        volume_ratio: float,
        atr: float,
        config: dict,
        volume: Optional[float] = None
    ) -> Optional[TradingSignal]:
        """
        Classify signal with AI enhancement.
        
        First generates base technical signal, then enhances with AI analysis.
        
        Args:
            Same as base classify_signal, plus:
            volume: Current volume (optional, for AI context)
        
        Returns:
            Enhanced TradingSignal or None
        """
        # Step 1: Generate base technical signal
        base_signal = self.classify_signal(
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
            config=config
        )
        
        # If no base signal or AI disabled, return base result
        if base_signal is None or not self.ai_initialized:
            return base_signal
        
        # Step 2: Enhance signal with AI analysis
        try:
            ai_enhancement = await self._get_ai_enhancement(
                signal=base_signal,
                volume=volume
            )
            
            if ai_enhancement:
                # Apply AI enhancement logic
                enhanced_signal = self._apply_ai_enhancement(
                    base_signal=base_signal,
                    ai_enhancement=ai_enhancement
                )
                
                return enhanced_signal
            else:
                # AI enhancement failed/unavailable, return base signal
                self.ai_stats["signals_ai_neutral"] += 1
                return base_signal
        
        except Exception as e:
            logger.error(f"Error in AI enhancement: {e}", exc_info=True)
            # Return base signal on error
            return base_signal
    
    async def _get_ai_enhancement(
        self,
        signal: TradingSignal,
        volume: Optional[float] = None
    ) -> Optional[AISignalEnhancement]:
        """
        Get AI enhancement for technical signal.
        
        Args:
            signal: Base technical signal
            volume: Current volume
        
        Returns:
            AISignalEnhancement or None
        """
        if not self.ai_adapter:
            return None
        
        # Prepare market data for AI
        market_data = {
            "price": signal.entry_price,
            "volume_ratio": signal.volume_ratio,
            "volatility": abs(signal.entry_price - signal.stop_loss),
            "trend_direction": signal.direction.value
        }
        
        if volume is not None:
            market_data["volume"] = volume
        
        # Prepare technical indicators for AI
        technical_indicators = {
            "rsi": signal.rsi_value,
            "ema_20": signal.ema_20,
            "ema_50": signal.ema_50,
            "ema_200": signal.ema_200,
            "fib_level": signal.fib_level_touched,
            "volume_ratio": signal.volume_ratio
        }
        
        # Get AI signal enhancement
        ai_enhancement = await self.ai_adapter.enhance_signal(
            symbol=signal.symbol,
            market_data=market_data,
            technical_indicators=technical_indicators,
            timeframe=signal.timeframe
        )
        
        return ai_enhancement
    
    def _apply_ai_enhancement(
        self,
        base_signal: TradingSignal,
        ai_enhancement: AISignalEnhancement
    ) -> Optional[TradingSignal]:
        """
        Apply AI enhancement to base technical signal.
        
        Logic:
        1. If AI strongly disagrees (should_block), reject signal
        2. If AI agrees (should_boost), increase confidence
        3. Otherwise, keep base signal with AI metadata
        
        Args:
            base_signal: Base technical signal
            ai_enhancement: AI enhancement data
        
        Returns:
            Enhanced signal or None if blocked
        """
        self.ai_stats["signals_ai_enhanced"] += 1
        
        # Check if AI blocks signal
        if ai_enhancement.should_block_signal():
            logger.warning(
                f"AI BLOCKED signal: {base_signal.symbol} "
                f"(AI: {ai_enhancement.ai_signal}, "
                f"confidence={ai_enhancement.ai_confidence:.2f}, "
                f"risk={ai_enhancement.ai_risk_level})"
            )
            self.ai_stats["signals_ai_blocked"] += 1
            return None
        
        # Check if AI boosts signal
        if ai_enhancement.should_boost_signal():
            # AI agrees with technical signal - boost confidence
            original_confidence = base_signal.confidence
            
            # Calculate boost based on AI confidence
            boost_amount = (ai_enhancement.ai_confidence - self.ai_min_confidence) * 20
            base_signal.confidence = min(100.0, original_confidence + boost_amount)
            
            logger.info(
                f"AI BOOSTED signal: {base_signal.symbol} "
                f"confidence {original_confidence:.1f}% → {base_signal.confidence:.1f}% "
                f"(AI consensus: {ai_enhancement.provider_count} providers)"
            )
            
            self.ai_stats["signals_ai_boosted"] += 1
        
        # Attach AI metadata to signal
        if not hasattr(base_signal, 'ai_metadata'):
            base_signal.ai_metadata = {}
        
        base_signal.ai_metadata = ai_enhancement.to_dict()
        
        return base_signal
    
    async def assess_signal_risk(
        self,
        signal: TradingSignal,
        position_data: Dict[str, Any],
        market_conditions: Dict[str, Any]
    ) -> tuple[str, float]:
        """
        Assess risk level for a signal using AI.
        
        Args:
            signal: Trading signal to assess
            position_data: Position size and account info
            market_conditions: Current market state
        
        Returns:
            Tuple of (risk_level, confidence)
        """
        if not self.ai_initialized or not self.ai_adapter:
            return "MEDIUM", 0.5
        
        try:
            risk_level, confidence = await self.ai_adapter.assess_risk(
                symbol=signal.symbol,
                position_data=position_data,
                market_conditions=market_conditions
            )
            
            logger.debug(
                f"AI risk assessment for {signal.symbol}: "
                f"{risk_level} (confidence={confidence:.2f})"
            )
            
            return risk_level, confidence
            
        except Exception as e:
            logger.error(f"Error in AI risk assessment: {e}", exc_info=True)
            return "MEDIUM", 0.5
    
    def get_ai_stats(self) -> Dict[str, Any]:
        """Get AI-specific statistics."""
        stats = dict(self.ai_stats)
        stats["ai_enabled"] = self.enable_ai
        stats["ai_initialized"] = self.ai_initialized
        
        if self.ai_adapter:
            stats["adapter_stats"] = self.ai_adapter.get_stats()
        
        return stats
    
    def reset_ai_stats(self) -> None:
        """Reset AI statistics."""
        self.ai_stats = {
            "signals_ai_enhanced": 0,
            "signals_ai_boosted": 0,
            "signals_ai_blocked": 0,
            "signals_ai_neutral": 0,
            "ai_initialization_errors": 0
        }
        
        if self.ai_adapter:
            self.ai_adapter.reset_stats()


# ========== USAGE EXAMPLE ==========

"""
Example: Using AI-Enhanced Signal Engine

import asyncio
from signal_generation.signal_engine_ai_enhanced import AIEnhancedSignalEngine

async def main():
    # Initialize AI-enhanced engine
    signal_engine = AIEnhancedSignalEngine(enable_ai=True)
    
    # Initialize AI (requires API keys in environment)
    ai_ready = await signal_engine.initialize_ai()
    
    if ai_ready:
        print("AI ensemble ready")
    else:
        print("Running without AI enhancement")
    
    # Generate signal with AI enhancement
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
    
    signal = await signal_engine.classify_signal_with_ai(
        symbol="BTC/USDT",
        timeframe="1h",
        fib_levels={0.618: 42000, 0.382: 43000, 0.786: 41000},
        rsi=28.5,
        ema_20=42100,
        ema_50=41800,
        ema_200=41000,
        current_price=42000,
        volume_ratio=1.6,
        atr=350,
        config=config,
        volume=1250000  # Optional volume for AI context
    )
    
    if signal:
        print(f"Signal: {signal.symbol} {signal.direction.value}")
        print(f"Tier: {signal.tier.value[0]}")
        print(f"Confidence: {signal.confidence:.1f}%")
        print(f"Entry: ${signal.entry_price:.2f}")
        print(f"Stop Loss: ${signal.stop_loss:.2f}")
        print(f"TP1: ${signal.take_profit_1:.2f}")
        print(f"TP2: ${signal.take_profit_2:.2f}")
        
        if hasattr(signal, 'ai_metadata'):
            print(f"\nAI Enhancement:")
            print(f"  Signal: {signal.ai_metadata['ai_signal']}")
            print(f"  Confidence: {signal.ai_metadata['ai_confidence']:.2f}")
            print(f"  Risk: {signal.ai_metadata['ai_risk_level']}")
            print(f"  Providers: {signal.ai_metadata['provider_count']}")
    else:
        print("No signal generated (or AI blocked)")
    
    # Print statistics
    print(f"\nAI Stats: {signal_engine.get_ai_stats()}")

if __name__ == "__main__":
    asyncio.run(main())
"""
