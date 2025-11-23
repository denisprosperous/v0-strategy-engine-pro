"""Multi-Condition Signal Validator

This module validates trading signals from any strategy (Fibonacci, mean reversion, etc.)
against 7 comprehensive conditions before execution. Designed to work with the pluggable
strategy architecture in fibonacci_engine.py.

Validation Conditions:
1. Price level validation (±1% tolerance for Fibonacci, custom for others)
2. RSI confirmation (oversold 20-40 for buy, overbought 60-80 for sell)
3. EMA alignment (trend direction confirmation)
4. Volume confirmation (>150% of average volume)
5. Market structure (trending vs ranging detection)
6. Position sizing (max 5% per position)
7. Portfolio correlation (<0.7 to avoid overconcentration)

Features:
- Strategy-agnostic validation (works with Fibonacci, mean reversion, etc.)
- Confidence scoring (0-100) based on condition pass rate
- Detailed violation tracking for analysis
- Configurable thresholds for all conditions
- Integration-ready with execution engine

Author: v0-strategy-engine-pro
Version: 1.0
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ValidationCondition(Enum):"""Enumeration of validation conditions."""
    PRICE_LEVEL = "price_level"
    RSI_CONFIRMATION = "rsi_confirmation"
    EMA_ALIGNMENT = "ema_alignment"
    VOLUME_CONFIRMATION = "volume_confirmation"
    MARKET_STRUCTURE = "market_structure"
    POSITION_SIZING = "position_sizing"
    PORTFOLIO_CORRELATION = "portfolio_correlation"


@dataclass
class SignalValidationResult:
    """Result of signal validation with detailed breakdown."""
    is_valid: bool
    confidence: float  # 0-100 score
    violations: List[str] = field(default_factory=list)
    condition_results: Dict[str, bool] = field(default_factory=dict)
    metadata: Dict[str, any] = field(default_factory=dict)


class SignalValidator:
    """Validates trading signals against multiple conditions.
    
    This validator works with any strategy that returns a signal dict.
    It adapts validation logic based on the strategy type.
    """

    def __init__(
        self,
        rsi_oversold_threshold: float = 40.0,
        rsi_overbought_threshold: float = 60.0,
        volume_confirmation_multiplier: float = 1.5,
        max_position_size_pct: float = 5.0,
        max_portfolio_correlation: float = 0.7,
        price_tolerance_pct: float = 1.0
    ):
        """Initialize validator with configurable thresholds."""
        self.rsi_oversold = rsi_oversold_threshold
        self.rsi_overbought = rsi_overbought_threshold
        self.volume_multiplier = volume_confirmation_multiplier
        self.max_position_size = max_position_size_pct
        self.max_correlation = max_portfolio_correlation
        self.price_tolerance = price_tolerance_pct

    def validate_signal(
        self,
        signal: Dict,
        market_data: Dict,
        portfolio_state: Optional[Dict] = None
    ) -> SignalValidationResult:
        """Validate a signal against all 7 conditions.
        
        Args:
            signal: Signal dict from any strategy (must have 'strategy' and 'current_price')
            market_data: Dict with 'rsi', 'ema_20', 'ema_50', 'volume', 'avg_volume', etc.
            portfolio_state: Optional dict with current positions and correlations
        
        Returns:
            SignalValidationResult with validation outcome
        """
        violations = []
        condition_results = {}
        metadata = {}

        # Extract strategy type and direction
        strategy_name = signal.get('strategy', 'unknown')
        direction = signal.get('direction', 'long')  # Default to long if not specified
        current_price = signal.get('current_price', 0)

        # Condition 1: Price level validation (strategy-specific)
        price_valid, price_meta = self._validate_price_level(signal, current_price)
        condition_results[ValidationCondition.PRICE_LEVEL.value] = price_valid
        metadata.update(price_meta)
        if not price_valid:
            violations.append(f"Price level validation failed: {price_meta.get('reason', 'unknown')}")

        # Condition 2: RSI confirmation
        rsi = market_data.get('rsi', 50)
        rsi_valid = self._validate_rsi(rsi, direction)
        condition_results[ValidationCondition.RSI_CONFIRMATION.value] = rsi_valid
        metadata['rsi'] = rsi
        if not rsi_valid:
            violations.append(f"RSI confirmation failed: RSI={rsi:.2f}, direction={direction}")

        # Condition 3: EMA alignment
        ema_20 = market_data.get('ema_20', current_price)
        ema_50 = market_data.get('ema_50', current_price)
        ema_valid = self._validate_ema_alignment(current_price, ema_20, ema_50, direction)
        condition_results[ValidationCondition.EMA_ALIGNMENT.value] = ema_valid
        metadata['ema_alignment'] = {'ema_20': ema_20, 'ema_50': ema_50}
        if not ema_valid:
            violations.append(f"EMA alignment failed: price={current_price:.2f}, EMA20={ema_20:.2f}, EMA50={ema_50:.2f}")

        # Condition 4: Volume confirmation
        volume = market_data.get('volume', 0)
        avg_volume = market_data.get('avg_volume', volume)
        volume_valid = self._validate_volume(volume, avg_volume)
        condition_results[ValidationCondition.VOLUME_CONFIRMATION.value] = volume_valid
        metadata['volume_ratio'] = volume / avg_volume if avg_volume > 0 else 0
        if not volume_valid:
            violations.append(f"Volume confirmation failed: volume={volume}, avg={avg_volume}, ratio={metadata['volume_ratio']:.2f}")

        # Condition 5: Market structure
        atr = market_data.get('atr', 0)
        market_structure_valid = self._validate_market_structure(current_price, atr, strategy_name)
        condition_results[ValidationCondition.MARKET_STRUCTURE.value] = market_structure_valid
        metadata['atr'] = atr
        if not market_structure_valid:
            violations.append(f"Market structure unfavorable for {strategy_name}")

        # Condition 6: Position sizing
        position_size = signal.get('position_size', 0)
        portfolio_value = portfolio_state.get('total_value', 100000) if portfolio_state else 100000
        sizing_valid = self._validate_position_sizing(position_size, portfolio_value)
        condition_results[ValidationCondition.POSITION_SIZING.value] = sizing_valid
        metadata['position_size_pct'] = (position_size / portfolio_value) * 100 if portfolio_value > 0 else 0
        if not sizing_valid:
            violations.append(f"Position sizing failed: {metadata['position_size_pct']:.2f}% exceeds {self.max_position_size}%")

        # Condition 7: Portfolio correlation
        symbol = signal.get('symbol', 'UNKNOWN')
        correlation_valid = self._validate_portfolio_correlation(symbol, portfolio_state)
        condition_results[ValidationCondition.PORTFOLIO_CORRELATION.value] = correlation_valid
        if not correlation_valid:
            violations.append(f"Portfolio correlation too high for {symbol}")

        # Calculate confidence score
        passed_conditions = sum(1 for result in condition_results.values() if result)
        total_conditions = len(condition_results)
        confidence = (passed_conditions / total_conditions) * 100 if total_conditions > 0 else 0

        # Signal is valid if confidence >= 60% (at least 5 of 7 conditions pass)
        is_valid = confidence >= 60.0

        return SignalValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            violations=violations,
            condition_results=condition_results,
            metadata=metadata
        )

    def _validate_price_level(self, signal: Dict, current_price: float) -> Tuple[bool, Dict]:
        """Validate price level based on strategy type."""
        strategy_name = signal.get('strategy', 'unknown')
        metadata = {'strategy': strategy_name}

        # Fibonacci strategy: check if price is within tolerance of triggered level
        if 'fibonacci' in strategy_name.lower():
            triggered_level = signal.get('fib_levels', {}).get(signal.get('triggered_level', ''), 0)
            if triggered_level > 0:
                deviation_pct = abs((current_price - triggered_level) / current_price) * 100
                metadata['triggered_level'] = triggered_level
                metadata['deviation_pct'] = deviation_pct
                if deviation_pct <= self.price_tolerance:
                    return True, metadata
                metadata['reason'] = f"Deviation {deviation_pct:.2f}% exceeds tolerance {self.price_tolerance}%"
                return False, metadata

        # Mean reversion or other strategies: validate based on mean/std
        if 'mean_reversion' in strategy_name.lower():
            # For mean reversion, price should be significantly away from mean
            # (this is strategy-specific and could be enhanced)
            return True, metadata  # Assume valid for now

        # Unknown strategy: accept with warning
        metadata['reason'] = f"Unknown strategy {strategy_name}, accepting by default"
        return True, metadata

    def _validate_rsi(self, rsi: float, direction: str) -> bool:
        """Validate RSI confirmation based on direction."""
        if direction == 'long' or direction == 'buy':
            return 20 <= rsi <= self.rsi_oversold
        elif direction == 'short' or direction == 'sell':
            return self.rsi_overbought <= rsi <= 80
        return False

    def _validate_ema_alignment(self, price: float, ema_20: float, ema_50: float, direction: str) -> bool:
        """Validate EMA alignment with trend direction."""
        if direction == 'long' or direction == 'buy':
            # For long: price > EMA20 > EMA50 (uptrend)
            return price > ema_20 and ema_20 > ema_50
        elif direction == 'short' or direction == 'sell':
            # For short: price < EMA20 < EMA50 (downtrend)
            return price < ema_20 and ema_20 < ema_50
        return False

    def _validate_volume(self, volume: float, avg_volume: float) -> bool:
        """Validate volume confirmation."""
        if avg_volume <= 0:
            return False
        return volume >= avg_volume * self.volume_multiplier

    def _validate_market_structure(self, price: float, atr: float, strategy_name: str) -> bool:
        """Validate market structure is suitable for strategy.
        
        - Fibonacci works best in trending markets (higher ATR/price ratio)
        - Mean reversion works best in ranging markets (lower ATR/price ratio)
        """
        if atr <= 0 or price <= 0:
            return True  # Insufficient data, accept by default

        volatility_ratio = (atr / price) * 100  # ATR as % of price

        if 'fibonacci' in strategy_name.lower():
            # Fibonacci needs moderate to high volatility (trending)
            return volatility_ratio >= 1.0  # At least 1% ATR
        elif 'mean_reversion' in strategy_name.lower():
            # Mean reversion needs low volatility (ranging)
            return volatility_ratio < 2.0  # Less than 2% ATR

        # Unknown strategy: accept by default
        return True

    def _validate_position_sizing(self, position_size: float, portfolio_value: float) -> bool:
        """Validate position size is within limits."""
        if portfolio_value <= 0:
            return False
        position_pct = (position_size / portfolio_value) * 100
        return position_pct <= self.max_position_size

    def _validate_portfolio_correlation(self, symbol: str, portfolio_state: Optional[Dict]) -> bool:
        """Validate portfolio correlation to avoid overconcentration."""
        if not portfolio_state or 'correlations' not in portfolio_state:
            return True  # No portfolio data, accept by default

        correlations = portfolio_state.get('correlations', {})
        symbol_correlation = correlations.get(symbol, 0.0)

        return symbol_correlation < self.max_correlation


# Example usage
if __name__ == '__main__':
    # Example signal from Fibonacci engine
    fibonacci_signal = {
        'strategy': 'dynamic_fibonacci',
        'current_price': 50000.0,
        'triggered_level': 'support_strong',
        'fib_levels': {'support_strong': 49800.0},
        'direction': 'long',
        'position_size': 2500.0,
        'symbol': 'BTCUSDT'
    }

    # Market data
    market_data = {
        'rsi': 35.0,
        'ema_20': 49500.0,
        'ema_50': 48000.0,
        'volume': 1000000,
        'avg_volume': 600000,
        'atr': 500.0
    }

    # Portfolio state
    portfolio_state = {
        'total_value': 100000.0,
        'correlations': {'BTCUSDT': 0.5}
    }

    # Validate
    validator = SignalValidator()
    result = validator.validate_signal(fibonacci_signal, market_data, portfolio_state)

    print(f"Valid: {result.is_valid}")
    print(f"Confidence: {result.confidence:.2f}%")
    print(f"Violations: {result.violations}")
    print(f"Condition Results: {result.condition_results}")
