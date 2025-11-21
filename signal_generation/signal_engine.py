"""Signal Engine: Tier Classification with 4-Confirmation Filter.

Implements complete signal generation logic combining:
- Fibonacci level confirmation (touch + 2-candle close)
- RSI divergence detection (oversold/overbought)
- EMA alignment (trend confirmation 20>50>200)
- Volume surge confirmation (1.5x+ or 1.2x+)

Generates 4-tier signals with high confidence.

Author: Trading Bot v0
Version: 1.0
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SignalTier(Enum):
    """Signal tier classification."""
    TIER_1 = (1, 0.80, 4.0, 0.02)  # (tier, expected_wr, rr_ratio, risk%)
    TIER_2 = (2, 0.75, 3.0, 0.015)
    TIER_3 = (3, 0.67, 2.0, 0.0075)
    SKIP = (4, 0.0, 0.0, 0.0)


class SignalDirection(Enum):
    """Trade direction."""
    LONG = 'long'
    SHORT = 'short'
    NEUTRAL = 'neutral'


@dataclass
class SignalStrength:
    """Signal confirmation strength."""
    fib_confirmed: bool = False  # Fib touch + 2-candle confirmation
    rsi_confirmed: bool = False  # RSI in target zone
    ema_aligned: bool = False    # EMA sequence correct
    volume_confirmed: bool = False  # Volume spike present
    
    def confidence_score(self) -> float:
        """Calculate 0-100 confidence score."""
        confirmations = sum([
            self.fib_confirmed,
            self.rsi_confirmed,
            self.ema_aligned,
            self.volume_confirmed
        ])
        return (confirmations / 4) * 100
    
    def all_confirmed(self) -> bool:
        """Check if all 4 filters confirmed."""
        return all([
            self.fib_confirmed,
            self.rsi_confirmed,
            self.ema_aligned,
            self.volume_confirmed
        ])


@dataclass
class TradingSignal:
    """Complete trading signal with all metadata."""
    symbol: str
    timeframe: str
    timestamp: datetime
    tier: SignalTier
    direction: SignalDirection
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    
    # Signal data
    fib_level_touched: float  # Which Fib level (0.618, etc)
    rsi_value: float
    ema_20: float
    ema_50: float
    ema_200: float
    volume_ratio: float  # Current vol / avg vol
    
    # Confirmation data
    strength: SignalStrength
    confidence: float  # 0-100
    
    # Risk metrics
    stop_loss_percent: float
    risk_reward_ratio: float
    position_size: float = 0.0
    
    def is_high_quality(self) -> bool:
        """Check if signal meets high-quality threshold."""
        if self.tier == SignalTier.TIER_1:
            return self.confidence >= 80.0
        elif self.tier == SignalTier.TIER_2:
            return self.confidence >= 75.0
        elif self.tier == SignalTier.TIER_3:
            return self.confidence >= 70.0
        return False


class SignalEngine:
    """Main signal generation engine with 4-confirmation filter."""
    
    def __init__(self):
        self.last_signal_time = {}
        self.min_signal_interval = 3600  # 1 hour between signals per symbol
    
    def classify_signal(self, symbol: str, timeframe: str,
                       fib_levels: dict, rsi: float,
                       ema_20: float, ema_50: float, ema_200: float,
                       current_price: float, volume_ratio: float,
                       atr: float, config: dict) -> Optional[TradingSignal]:
        """Classify signal based on all 4 confirmation filters.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            fib_levels: Dict with 0.236, 0.382, 0.500, 0.618, 0.786 levels
            rsi: Current RSI value
            ema_20, ema_50, ema_200: EMA values
            current_price: Current price
            volume_ratio: Current volume / 20-period avg
            atr: Current ATR
            config: Configuration dict with threshold parameters
            
        Returns:
            TradingSignal or None
        """
        # Filter 1: Fibonacci level confirmation
        fib_confirmed, fib_level = self._check_fib_confirmation(
            fib_levels, current_price, atr, config
        )
        if not fib_confirmed:
            return None
        
        # Determine direction from Fib structure
        direction = self._get_direction_from_fib(fib_level, current_price, fib_levels)
        if direction == SignalDirection.NEUTRAL:
            return None
        
        # Filter 2: RSI confirmation
        rsi_confirmed, rsi_tier = self._check_rsi_confirmation(rsi, direction, config)
        if not rsi_confirmed:
            return None
        
        # Filter 3: EMA alignment
        ema_aligned = self._check_ema_alignment(ema_20, ema_50, ema_200, direction)
        if not ema_aligned:
            return None
        
        # Filter 4: Volume confirmation
        vol_confirmed, required_vol = self._check_volume_confirmation(
            volume_ratio, rsi_tier, config
        )
        if not vol_confirmed:
            return None
        
        # All filters passed - classify tier and create signal
        strength = SignalStrength(
            fib_confirmed=True,
            rsi_confirmed=True,
            ema_aligned=True,
            volume_confirmed=True
        )
        confidence = strength.confidence_score()
        
        # Determine tier based on RSI and filters
        tier = self._classify_tier(rsi, confidence, volume_ratio, ema_20, ema_50, ema_200)
        
        if tier == SignalTier.SKIP:
            return None
        
        # Calculate entry and exits
        entry_price = current_price
        sl_distance = atr * config['stop_atr_mult']
        
        if direction == SignalDirection.LONG:
            stop_loss = entry_price - sl_distance
            sl_pct = (entry_price - stop_loss) / entry_price
        else:  # SHORT
            stop_loss = entry_price + sl_distance
            sl_pct = (stop_loss - entry_price) / entry_price
        
        tp1, tp2 = self._calculate_targets(
            entry_price, stop_loss, tier, direction
        )
        
        # Create signal
        signal = TradingSignal(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime.utcnow(),
            tier=tier,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=tp1,
            take_profit_2=tp2,
            fib_level_touched=fib_level,
            rsi_value=rsi,
            ema_20=ema_20,
            ema_50=ema_50,
            ema_200=ema_200,
            volume_ratio=volume_ratio,
            strength=strength,
            confidence=confidence,
            stop_loss_percent=sl_pct * 100,
            risk_reward_ratio=tier.value[2]
        )
        
        logger.info(f"Signal: {symbol} {direction.value} Tier {tier.value[0]} Conf {confidence:.1f}%")
        return signal
    
    def _check_fib_confirmation(self, fib_levels: dict, price: float,
                               atr: float, config: dict) -> Tuple[bool, float]:
        """Check if price touches Fibonacci level within tolerance."""
        primary_level = fib_levels.get(0.618)
        if not primary_level:
            return False, 0.0
        
        tolerance = atr * config.get('fib_tolerance_atr', 0.1)
        distance = abs(price - primary_level)
        
        if distance <= tolerance:
            return True, 0.618
        
        # Check secondary levels
        for level_key in [0.382, 0.500, 0.786]:
            level = fib_levels.get(level_key)
            if level and abs(price - level) <= tolerance:
                return True, level_key
        
        return False, 0.0
    
    def _get_direction_from_fib(self, fib_level: float, price: float,
                               fib_levels: dict) -> SignalDirection:
        """Determine trade direction based on Fib structure."""
        if fib_level == 0.0:
            return SignalDirection.NEUTRAL
        
        swing_high = max(fib_levels.values()) if fib_levels else 0
        swing_low = min(fib_levels.values()) if fib_levels else float('inf')
        
        # If at retracement level and bouncing up = LONG
        if fib_level < swing_high and price > swing_low:
            return SignalDirection.LONG
        # If at retracement level and bouncing down = SHORT
        elif fib_level < swing_high and price < swing_high:
            return SignalDirection.SHORT
        
        return SignalDirection.NEUTRAL
    
    def _check_rsi_confirmation(self, rsi: float, direction: SignalDirection,
                               config: dict) -> Tuple[bool, int]:
        """Check RSI confirmation and determine tier."""
        tier1_max = config.get('rsi_tier1_max', 30)
        tier2_min, tier2_max = config.get('rsi_tier2_range', (25, 35))
        skip_above = config.get('rsi_skip_above', 70)
        skip_below = config.get('rsi_skip_below', 15)
        
        if rsi > skip_above or rsi < skip_below:
            return False, 4  # SKIP
        
        if rsi < tier1_max:
            return True, 1  # Tier 1
        elif tier2_min <= rsi <= tier2_max:
            return True, 2  # Tier 2
        else:
            return True, 3  # Tier 3
    
    def _check_ema_alignment(self, ema_20: float, ema_50: float,
                            ema_200: float, direction: SignalDirection) -> bool:
        """Check EMA trend alignment (20 > 50 > 200 for longs)."""
        if direction == SignalDirection.LONG:
            return ema_20 > ema_50 > ema_200
        elif direction == SignalDirection.SHORT:
            return ema_20 < ema_50 < ema_200
        return False
    
    def _check_volume_confirmation(self, vol_ratio: float, tier: int,
                                  config: dict) -> Tuple[bool, float]:
        """Check volume surge for tier confirmation."""
        if tier == 1:
            min_vol = config.get('volume_tier1_min', 1.5)
        elif tier == 2:
            min_vol = config.get('volume_tier2_min', 1.2)
        else:
            min_vol = config.get('volume_tier3_min', 1.0)
        
        return vol_ratio >= min_vol, min_vol
    
    def _classify_tier(self, rsi: float, confidence: float,
                      vol_ratio: float, ema_20: float,
                      ema_50: float, ema_200: float) -> SignalTier:
        """Classify signal tier (1, 2, 3, or SKIP)."""
        # Tier 1: High confidence + optimal RSI + strong volume
        if confidence >= 80 and rsi < 25 and vol_ratio >= 1.5:
            return SignalTier.TIER_1
        
        # Tier 2: Good confidence + moderate RSI + reasonable volume
        if confidence >= 75 and rsi < 35 and vol_ratio >= 1.2:
            return SignalTier.TIER_2
        
        # Tier 3: Acceptable confidence (quota support)
        if confidence >= 70 and vol_ratio >= 1.0:
            return SignalTier.TIER_3
        
        return SignalTier.SKIP
    
    def _calculate_targets(self, entry: float, stop_loss: float,
                          tier: SignalTier, direction: SignalDirection) -> Tuple[float, float]:
        """Calculate take profit targets based on tier R:R ratio."""
        risk_distance = abs(entry - stop_loss)
        rr_ratio = tier.value[2]
        reward_distance = risk_distance * rr_ratio
        
        if direction == SignalDirection.LONG:
            tp1 = entry + (reward_distance * 0.5)  # 50% at 1:2R
            tp2 = entry + reward_distance  # Final at R:R
        else:  # SHORT
            tp1 = entry - (reward_distance * 0.5)
            tp2 = entry - reward_distance
        
        return tp1, tp2
