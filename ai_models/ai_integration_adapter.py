"""
AI Integration Adapter

Bridges the AI ensemble orchestrator with the main trading pipeline.
Provides simplified interface for signal generation to leverage AI analysis.

Integration Points:
- signal_generation/signal_engine.py
- trading_mode_manager.py
- signal_generation/execution_engine_integrated.py

Author: v0-strategy-engine-pro
Version: 1.0 - Segment 3
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

try:
    from .ensemble_orchestrator import EnsembleOrchestrator, EnsembleResult
except ImportError:
    from ensemble_orchestrator import EnsembleOrchestrator, EnsembleResult

logger = logging.getLogger(__name__)


@dataclass
class AISignalEnhancement:
    """AI-enhanced signal data to augment technical analysis."""
    ai_signal: str  # BUY, SELL, HOLD
    ai_confidence: float  # 0.0-1.0
    ai_sentiment_score: Optional[float] = None  # -1.0 to 1.0
    ai_risk_level: Optional[str] = None  # LOW, MEDIUM, HIGH
    ensemble_consensus: bool = False
    provider_count: int = 0
    execution_time_ms: float = 0.0
    
    def should_boost_signal(self) -> bool:
        """Determine if AI analysis should boost signal confidence."""
        return (
            self.ai_confidence >= 0.7 and
            self.ensemble_consensus and
            self.provider_count >= 2
        )
    
    def should_block_signal(self) -> bool:
        """Determine if AI analysis should block signal execution."""
        return (
            self.ai_signal == "HOLD" and
            self.ai_confidence >= 0.8 and
            self.ai_risk_level == "HIGH"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ai_signal": self.ai_signal,
            "ai_confidence": self.ai_confidence,
            "ai_sentiment_score": self.ai_sentiment_score,
            "ai_risk_level": self.ai_risk_level,
            "ensemble_consensus": self.ensemble_consensus,
            "provider_count": self.provider_count,
            "execution_time_ms": self.execution_time_ms
        }


class AIIntegrationAdapter:
    """
    Adapter class to integrate AI ensemble with trading pipeline.
    
    Provides simplified interface for:
    - Enhancing technical signals with AI analysis
    - Risk assessment for position sizing
    - Sentiment analysis for market context
    """
    
    def __init__(
        self,
        enable_ai: bool = True,
        min_providers: int = 2,
        min_confidence: float = 0.6,
        cache_ttl: int = 300
    ):
        """
        Initialize AI integration adapter.
        
        Args:
            enable_ai: Enable/disable AI integration globally
            min_providers: Minimum providers required for consensus
            min_confidence: Minimum confidence threshold
            cache_ttl: Cache time-to-live in seconds
        """
        self.enable_ai = enable_ai
        self.min_providers = min_providers
        self.min_confidence = min_confidence
        self.cache_ttl = cache_ttl
        
        # Initialize ensemble orchestrator
        self.orchestrator: Optional[EnsembleOrchestrator] = None
        
        # Statistics
        self.stats = {
            "signals_enhanced": 0,
            "signals_boosted": 0,
            "signals_blocked": 0,
            "risk_assessments": 0,
            "sentiment_analyses": 0,
            "errors": 0
        }
        
        logger.info(f"AIIntegrationAdapter initialized (enabled={enable_ai})")
    
    async def initialize(self) -> bool:
        """
        Initialize the AI ensemble orchestrator.
        
        Returns:
            Success status
        """
        if not self.enable_ai:
            logger.info("AI integration disabled - skipping initialization")
            return False
        
        try:
            # Load API keys from environment
            api_keys = {
                "openai": os.getenv("OPENAI_API_KEY", ""),
                "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
                "gemini": os.getenv("GOOGLE_API_KEY", ""),
                "grok": os.getenv("XAI_API_KEY", "")
            }
            
            # Filter out empty keys
            api_keys = {k: v for k, v in api_keys.items() if v}
            
            if not api_keys:
                logger.warning("No AI API keys found - AI features disabled")
                self.enable_ai = False
                return False
            
            # Initialize orchestrator
            self.orchestrator = EnsembleOrchestrator(
                api_keys=api_keys,
                min_providers=self.min_providers,
                min_confidence=self.min_confidence,
                enable_parallel=True
            )
            
            logger.info(
                f"AI ensemble initialized with {len(api_keys)} providers: "
                f"{', '.join(api_keys.keys())}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AI ensemble: {e}", exc_info=True)
            self.enable_ai = False
            self.stats["errors"] += 1
            return False
    
    async def enhance_signal(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        technical_indicators: Dict[str, Any],
        timeframe: str = "1h"
    ) -> Optional[AISignalEnhancement]:
        """
        Enhance technical trading signal with AI analysis.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            market_data: Current market data (price, volume, etc.)
            technical_indicators: Technical indicator values
            timeframe: Chart timeframe
        
        Returns:
            AISignalEnhancement or None if AI disabled/error
        """
        if not self.enable_ai or not self.orchestrator:
            return None
        
        try:
            # Generate ensemble trading signal
            result: EnsembleResult = await self.orchestrator.generate_trading_signal_ensemble(
                symbol=symbol,
                market_data=market_data,
                technical_indicators=technical_indicators,
                timeframe=timeframe
            )
            
            # Convert to enhancement object
            enhancement = AISignalEnhancement(
                ai_signal=result.consensus_signal,
                ai_confidence=result.confidence,
                ai_sentiment_score=result.sentiment_score,
                ai_risk_level=result.risk_level,
                ensemble_consensus=result.confidence >= self.min_confidence,
                provider_count=len(result.provider_responses),
                execution_time_ms=result.execution_time_ms
            )
            
            # Update statistics
            self.stats["signals_enhanced"] += 1
            if enhancement.should_boost_signal():
                self.stats["signals_boosted"] += 1
            if enhancement.should_block_signal():
                self.stats["signals_blocked"] += 1
            
            logger.debug(
                f"AI signal: {symbol} {enhancement.ai_signal} "
                f"(confidence={enhancement.ai_confidence:.2f}, "
                f"providers={enhancement.provider_count})"
            )
            
            return enhancement
            
        except Exception as e:
            logger.error(f"Error enhancing signal for {symbol}: {e}", exc_info=True)
            self.stats["errors"] += 1
            return None
    
    async def analyze_sentiment(
        self,
        text: str,
        market_context: Optional[Dict] = None
    ) -> Tuple[float, str]:
        """
        Analyze market sentiment from text (news, social media, etc.).
        
        Args:
            text: Text to analyze
            market_context: Optional market context data
        
        Returns:
            Tuple of (sentiment_score, risk_level)
            sentiment_score: -1.0 (bearish) to 1.0 (bullish)
            risk_level: "LOW", "MEDIUM", or "HIGH"
        """
        if not self.enable_ai or not self.orchestrator:
            return 0.0, "MEDIUM"
        
        try:
            result: EnsembleResult = await self.orchestrator.analyze_sentiment_ensemble(
                text=text,
                market_context=market_context
            )
            
            self.stats["sentiment_analyses"] += 1
            
            sentiment_score = result.sentiment_score or 0.0
            risk_level = result.risk_level or "MEDIUM"
            
            logger.debug(
                f"Sentiment analysis: score={sentiment_score:.2f}, "
                f"risk={risk_level}"
            )
            
            return sentiment_score, risk_level
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}", exc_info=True)
            self.stats["errors"] += 1
            return 0.0, "MEDIUM"
    
    async def assess_risk(
        self,
        symbol: str,
        position_data: Dict[str, Any],
        market_conditions: Dict[str, Any]
    ) -> Tuple[str, float]:
        """
        Assess risk level for trade/position.
        
        Args:
            symbol: Trading symbol
            position_data: Position information (size, entry, etc.)
            market_conditions: Current market conditions
        
        Returns:
            Tuple of (risk_level, confidence)
            risk_level: "LOW", "MEDIUM", or "HIGH"
            confidence: 0.0-1.0
        """
        if not self.enable_ai or not self.orchestrator:
            return "MEDIUM", 0.5
        
        try:
            result: EnsembleResult = await self.orchestrator.assess_risk_ensemble(
                symbol=symbol,
                position_data=position_data,
                market_conditions=market_conditions
            )
            
            self.stats["risk_assessments"] += 1
            
            risk_level = result.risk_level or "MEDIUM"
            confidence = result.confidence
            
            logger.debug(
                f"Risk assessment for {symbol}: {risk_level} "
                f"(confidence={confidence:.2f})"
            )
            
            return risk_level, confidence
            
        except Exception as e:
            logger.error(f"Error assessing risk for {symbol}: {e}", exc_info=True)
            self.stats["errors"] += 1
            return "MEDIUM", 0.5
    
    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        stats = dict(self.stats)
        stats["ai_enabled"] = self.enable_ai
        stats["orchestrator_initialized"] = self.orchestrator is not None
        
        if self.orchestrator:
            stats["orchestrator_stats"] = self.orchestrator.get_orchestrator_stats()
            stats["provider_stats"] = self.orchestrator.get_provider_stats()
        
        return stats
    
    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = {
            "signals_enhanced": 0,
            "signals_boosted": 0,
            "signals_blocked": 0,
            "risk_assessments": 0,
            "sentiment_analyses": 0,
            "errors": 0
        }
        
        if self.orchestrator:
            self.orchestrator.reset_all_stats()


# ========== USAGE EXAMPLE ==========

"""
Example: Integrate with Signal Engine

from ai_models.ai_integration_adapter import AIIntegrationAdapter
from signal_generation.signal_engine import SignalEngine

# Initialize adapter
ai_adapter = AIIntegrationAdapter(enable_ai=True)
await ai_adapter.initialize()

# In signal generation flow
signal_engine = SignalEngine()

# Generate base technical signal
base_signal = signal_engine.classify_signal(
    symbol="BTC/USDT",
    timeframe="1h",
    fib_levels={0.618: 42000},
    rsi=28.5,
    ema_20=42100,
    ema_50=41800,
    ema_200=41000,
    current_price=42000,
    volume_ratio=1.6,
    atr=350,
    config=config
)

# Enhance with AI analysis
if base_signal:
    market_data = {
        "price": base_signal.entry_price,
        "volume": volume_ratio,
        "volatility": atr
    }
    
    technical_indicators = {
        "rsi": base_signal.rsi_value,
        "ema_20": base_signal.ema_20,
        "ema_50": base_signal.ema_50,
        "ema_200": base_signal.ema_200,
        "fib_level": base_signal.fib_level_touched
    }
    
    ai_enhancement = await ai_adapter.enhance_signal(
        symbol=base_signal.symbol,
        market_data=market_data,
        technical_indicators=technical_indicators,
        timeframe=base_signal.timeframe
    )
    
    if ai_enhancement:
        # Check if AI agrees with technical signal
        if ai_enhancement.should_boost_signal():
            # Increase position size or confidence
            base_signal.confidence = min(100, base_signal.confidence + 10)
            logger.info(f"AI boosted signal confidence to {base_signal.confidence}")
        
        elif ai_enhancement.should_block_signal():
            # Skip signal execution
            logger.warning(f"AI blocked signal due to high risk")
            base_signal = None
        
        # Attach AI metadata
        base_signal.metadata = ai_enhancement.to_dict()

# Proceed with execution if signal not blocked
if base_signal:
    await execute_signal(base_signal)
"""
