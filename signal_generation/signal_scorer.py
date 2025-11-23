"""Signal Scoring System: 0-100 Dynamic Scoring with Execution Tiers.

Implements comprehensive signal scoring based on:
- Technical alignment (30 points)
- Volume confirmation (20 points)
- Volatility context (20 points)
- Historical win rate (15 points)
- Market condition (15 points)

Execution Rules:
- Score >= 75: Immediate/full-size execution
- Score 60-74: Reduced-size execution
- Score < 60: Skip trade

Author: Trading Bot v0
Version: 1.0
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ExecutionTier(Enum):
    """Execution size tier based on signal score."""
    FULL = (1.0, 75)  # (size_multiplier, min_score)
    REDUCED = (0.65, 60)
    SKIP = (0.0, 0)


@dataclass
class ScoreComponent:
    """Individual score component with breakdown."""
    name: str
    points: float  # 0-100 contribution
    weight: float  # 0-1 final weight
    reason: str = ""
    
    def weighted_score(self) -> float:
        """Return weighted score contribution."""
        return self.points * self.weight


@dataclass
class SignalScore:
    """Complete signal score with all components."""
    total_score: float  # 0-100
    execution_tier: ExecutionTier
    size_multiplier: float  # 0-1
    components: List[ScoreComponent] = field(default_factory=list)
    breakdown: Dict[str, float] = field(default_factory=dict)
    confidence_level: str = ""  # HIGH, MEDIUM, LOW
    recommendation: str = ""
    
    def __post_init__(self):
        """Auto-calculate confidence level and recommendation."""
        if self.total_score >= 75:
            self.confidence_level = "HIGH"
            self.recommendation = "Execute immediately at full size"
        elif self.total_score >= 60:
            self.confidence_level = "MEDIUM"
            self.recommendation = f"Execute with reduced size ({self.size_multiplier*100:.0f}%)"
        else:
            self.confidence_level = "LOW"
            self.recommendation = "Skip this signal"


class SignalScorer:
    """Main scoring engine for trading signals."""
    
    def __init__(self):
        """Initialize scorer with default thresholds."""
        self.thresholds = {
            # Technical alignment thresholds
            'fib_tolerance': 0.01,  # ±1% Fib tolerance
            'rsi_buy_zone': (20, 40),
            'rsi_sell_zone': (60, 80),
            
            # Volume thresholds
            'min_volume_ratio': 1.0,  # Min volume multiplier
            'strong_volume_ratio': 1.5,  # Strong volume
            
            # ATR volatility
            'low_volatility_atr': 0.5,  # Low volatility multiplier
            'high_volatility_atr': 1.5,  # High volatility multiplier
            
            # Win rate calibration
            'historical_win_rate_min': 0.50,  # 50% win rate min
            'historical_win_rate_optimal': 0.65,  # 65% optimal
        }
        
        # Weights for score components (sum to 1.0)
        self.component_weights = {
            'technical_alignment': 0.30,
            'volume_confirmation': 0.20,
            'volatility_context': 0.20,
            'historical_win_rate': 0.15,
            'market_condition': 0.15,
        }
        
    def score_signal(
        self,
        symbol: str,
        direction: str,  # 'long' or 'short'
        entry_price: float,
        fib_level: float,
        rsi: float,
        ema_20: float,
        ema_50: float,
        ema_200: float,
        volume_ratio: float,
        atr: float,
        historical_win_rate: float = 0.60,
        market_trend: str = "uptrend",  # uptrend, downtrend, ranging
        market_volatility: str = "normal",  # low, normal, high
    ) -> SignalScore:
        """Score a trading signal (0-100).
        
        Args:
            symbol: Trading symbol
            direction: 'long' or 'short'
            entry_price: Entry price
            fib_level: Fibonacci level touched (0.236-0.786)
            rsi: RSI value (0-100)
            ema_20, ema_50, ema_200: EMA values
            volume_ratio: Current volume / avg volume
            atr: Average True Range
            historical_win_rate: Historical win rate (0-1)
            market_trend: Current market trend
            market_volatility: Market volatility level
            
        Returns:
            SignalScore with breakdown
        """
        components = []
        
        # 1. Technical Alignment (30 pts)
        tech_score = self._score_technical_alignment(
            direction, fib_level, rsi, ema_20, ema_50, ema_200
        )
        components.append(ScoreComponent(
            name='Technical Alignment',
            points=tech_score,
            weight=self.component_weights['technical_alignment'],
            reason=f"Fib level: {fib_level}, RSI: {rsi:.1f}, EMA alignment"
        ))
        
        # 2. Volume Confirmation (20 pts)
        vol_score = self._score_volume_confirmation(volume_ratio)
        components.append(ScoreComponent(
            name='Volume Confirmation',
            points=vol_score,
            weight=self.component_weights['volume_confirmation'],
            reason=f"Volume ratio: {volume_ratio:.2f}x avg"
        ))
        
        # 3. Volatility Context (20 pts)
        vol_context_score = self._score_volatility_context(
            atr, market_volatility, direction
        )
        components.append(ScoreComponent(
            name='Volatility Context',
            points=vol_context_score,
            weight=self.component_weights['volatility_context'],
            reason=f"ATR: {atr:.4f}, Market: {market_volatility}"
        ))
        
        # 4. Historical Win Rate (15 pts)
        win_rate_score = self._score_historical_win_rate(historical_win_rate)
        components.append(ScoreComponent(
            name='Historical Win Rate',
            points=win_rate_score,
            weight=self.component_weights['historical_win_rate'],
            reason=f"Win rate: {historical_win_rate*100:.1f}%"
        ))
        
        # 5. Market Condition (15 pts)
        market_score = self._score_market_condition(
            market_trend, direction, rsi
        )
        components.append(ScoreComponent(
            name='Market Condition',
            points=market_score,
            weight=self.component_weights['market_condition'],
            reason=f"Trend: {market_trend}, Direction: {direction}"
        ))
        
        # Calculate total score
        total_score = sum(c.weighted_score() for c in components)
        total_score = np.clip(total_score, 0, 100)
        
        # Determine execution tier
        exec_tier, size_mult = self._get_execution_tier(total_score)
        
        # Build breakdown dict
        breakdown = {c.name: c.weighted_score() for c in components}
        
        return SignalScore(
            total_score=total_score,
            execution_tier=exec_tier,
            size_multiplier=size_mult,
            components=components,
            breakdown=breakdown,
        )
    
    def _score_technical_alignment(self, direction: str, fib_level: float,
                                   rsi: float, ema_20: float, ema_50: float,
                                   ema_200: float) -> float:
        """Score technical setup alignment (0-100)."""
        score = 0.0
        
        # Fib level check (0-30 pts)
        if 0.236 <= fib_level <= 0.786:
            fib_quality = 30.0  # Optimal Fib level
            if fib_level in [0.618, 0.382]:  # Golden/common levels
                fib_quality = 35.0
            score += fib_quality
        
        # RSI confirmation (0-40 pts)
        if direction == 'long':
            if 20 <= rsi < 30:
                score += 40.0  # Tier 1 RSI
            elif 30 <= rsi < 40:
                score += 30.0  # Tier 2 RSI
            elif 40 <= rsi < 50:
                score += 15.0  # Tier 3 RSI
        elif direction == 'short':
            if 70 < rsi <= 80:
                score += 40.0
            elif 60 < rsi <= 70:
                score += 30.0
            elif 50 < rsi <= 60:
                score += 15.0
        
        # EMA alignment (0-30 pts)
        if direction == 'long':
            if ema_20 > ema_50 > ema_200:
                score += 30.0  # Perfect alignment
            elif ema_20 > ema_50:
                score += 15.0  # Partial alignment
        elif direction == 'short':
            if ema_20 < ema_50 < ema_200:
                score += 30.0
            elif ema_20 < ema_50:
                score += 15.0
        
        return min(score, 100.0)
    
    def _score_volume_confirmation(self, volume_ratio: float) -> float:
        """Score volume confirmation (0-100)."""
        if volume_ratio >= self.thresholds['strong_volume_ratio']:
            return 100.0  # Strong volume
        elif volume_ratio >= 1.2:
            return 80.0  # Good volume
        elif volume_ratio >= self.thresholds['min_volume_ratio']:
            return 60.0  # Acceptable volume
        else:
            return 30.0  # Weak volume
    
    def _score_volatility_context(self, atr: float, market_vol: str,
                                  direction: str) -> float:
        """Score volatility appropriateness (0-100)."""
        score = 50.0  # Baseline
        
        if market_vol == 'low':
            # Mean reversion strategies prefer low vol
            score += 15.0
        elif market_vol == 'high':
            # Fibonacci strategies prefer higher vol
            score += 20.0
        
        # ATR bonus for healthy volatility (not too extreme)
        if 0.001 < atr < 10.0:
            score += 15.0
        
        return min(score, 100.0)
    
    def _score_historical_win_rate(self, win_rate: float) -> float:
        """Score based on historical win rate (0-100)."""
        if win_rate >= 0.70:
            return 100.0  # Excellent
        elif win_rate >= 0.65:
            return 85.0  # Good
        elif win_rate >= 0.60:
            return 70.0  # Acceptable
        elif win_rate >= 0.55:
            return 50.0  # Below average
        else:
            return 30.0  # Poor
    
    def _score_market_condition(self, market_trend: str, direction: str,
                               rsi: float) -> float:
        """Score market condition fit (0-100)."""
        score = 50.0  # Baseline
        
        # Trend alignment
        if market_trend == 'uptrend' and direction == 'long':
            score += 25.0
        elif market_trend == 'downtrend' and direction == 'short':
            score += 25.0
        elif market_trend == 'ranging':
            score += 15.0  # Ranging allows both directions
        else:
            score -= 15.0  # Opposite of trend
        
        # RSI extremes adjustment
        if rsi < 20 or rsi > 80:
            score += 10.0  # Extreme RSI = mean reversion opportunity
        
        return np.clip(score, 0, 100.0)
    
    def _get_execution_tier(self, total_score: float) -> Tuple[ExecutionTier, float]:
        """Determine execution tier from score."""
        if total_score >= 75:
            return ExecutionTier.FULL, 1.0
        elif total_score >= 60:
            return ExecutionTier.REDUCED, 0.65
        else:
            return ExecutionTier.SKIP, 0.0
    
    def get_score_distribution(self, signals: List[Dict]) -> Dict:
        """Get statistical distribution of signal scores."""
        if not signals:
            return {}
        
        scores = [s['total_score'] for s in signals]
        return {
            'mean': np.mean(scores),
            'median': np.median(scores),
            'std': np.std(scores),
            'min': np.min(scores),
            'max': np.max(scores),
            'q1': np.percentile(scores, 25),
            'q3': np.percentile(scores, 75),
        }
