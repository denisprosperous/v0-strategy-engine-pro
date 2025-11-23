"""Unit tests for Multi-Condition Signal Validator (Run 5)

Covers all 7 validation conditions:
1. Price level validation (Fibonacci and other strategies)
2. RSI confirmation (long/short)
3. EMA alignment (trend direction)
4. Volume confirmation
5. Market structure (trending vs ranging)
6. Position sizing
7. Portfolio correlation

Tests strategy-agnostic validation and confidence scoring.

Author: v0-strategy-engine-pro
Version: 1.0
"""

import pytest
from signal_generation.signal_validator import (
    SignalValidator,
    SignalValidationResult,
    ValidationCondition
)


class TestSignalValidator:
    """Test suite for SignalValidator."""

    def setup_method(self):
        """Initialize validator with default settings."""
        self.validator = SignalValidator()
        self.base_signal = {
            'strategy': 'dynamic_fibonacci',
            'current_price': 50000.0,
            'triggered_level': 'support_strong',
            'fib_levels': {'support_strong': 49800.0},
            'direction': 'long',
            'position_size': 2500.0,
            'symbol': 'BTCUSDT'
        }
        self.base_market_data = {
            'rsi': 35.0,
            'ema_20': 49500.0,
            'ema_50': 48000.0,
            'volume': 1000000,
            'avg_volume': 600000,
            'atr': 500.0
        }
        self.base_portfolio = {
            'total_value': 100000.0,
            'correlations': {'BTCUSDT': 0.5}
        }

    # Test 1: All conditions pass (perfect signal)
    def test_all_conditions_pass(self):
        """Test signal with all conditions passing."""
        result = self.validator.validate_signal(
            self.base_signal,
            self.base_market_data,
            self.base_portfolio
        )
        assert result.is_valid
        assert result.confidence == 100.0
        assert len(result.violations) == 0
        assert all(result.condition_results.values())

    # Test 2: Price level validation fails (Fibonacci)
    def test_price_level_fails_fibonacci(self):
        """Test Fibonacci signal with price too far from level."""
        signal = self.base_signal.copy()
        signal['current_price'] = 51000.0  # 2% away from support_strong (49800)
        result = self.validator.validate_signal(signal, self.base_market_data, self.base_portfolio)
        assert not result.condition_results[ValidationCondition.PRICE_LEVEL.value]
        assert any('Price level validation failed' in v for v in result.violations)

    # Test 3: RSI confirmation fails (long signal with high RSI)
    def test_rsi_fails_long_signal(self):
        """Test long signal with RSI too high (not oversold)."""
        market_data = self.base_market_data.copy()
        market_data['rsi'] = 65.0  # Too high for long entry
        result = self.validator.validate_signal(self.base_signal, market_data, self.base_portfolio)
        assert not result.condition_results[ValidationCondition.RSI_CONFIRMATION.value]
        assert any('RSI confirmation failed' in v for v in result.violations)

    # Test 4: RSI confirmation passes (short signal with high RSI)
    def test_rsi_passes_short_signal(self):
        """Test short signal with RSI in overbought zone."""
        signal = self.base_signal.copy()
        signal['direction'] = 'short'
        market_data = self.base_market_data.copy()
        market_data['rsi'] = 70.0  # Good for short entry
        result = self.validator.validate_signal(signal, market_data, self.base_portfolio)
        assert result.condition_results[ValidationCondition.RSI_CONFIRMATION.value]

    # Test 5: EMA alignment fails (price below EMA in long signal)
    def test_ema_alignment_fails_long(self):
        """Test long signal with price below EMA (downtrend)."""
        signal = self.base_signal.copy()
        signal['current_price'] = 47000.0  # Below both EMAs
        result = self.validator.validate_signal(signal, self.base_market_data, self.base_portfolio)
        assert not result.condition_results[ValidationCondition.EMA_ALIGNMENT.value]
        assert any('EMA alignment failed' in v for v in result.violations)

    # Test 6: EMA alignment passes (short signal with proper downtrend)
    def test_ema_alignment_passes_short(self):
        """Test short signal with price below EMAs (downtrend)."""
        signal = self.base_signal.copy()
        signal['direction'] = 'short'
        signal['current_price'] = 47000.0
        market_data = self.base_market_data.copy()
        market_data['ema_20'] = 48000.0
        market_data['ema_50'] = 49000.0
        result = self.validator.validate_signal(signal, market_data, self.base_portfolio)
        assert result.condition_results[ValidationCondition.EMA_ALIGNMENT.value]

    # Test 7: Volume confirmation fails
    def test_volume_confirmation_fails(self):
        """Test signal with insufficient volume."""
        market_data = self.base_market_data.copy()
        market_data['volume'] = 500000  # Below 1.5x average (600k * 1.5 = 900k)
        result = self.validator.validate_signal(self.base_signal, market_data, self.base_portfolio)
        assert not result.condition_results[ValidationCondition.VOLUME_CONFIRMATION.value]
        assert any('Volume confirmation failed' in v for v in result.violations)

    # Test 8: Volume confirmation passes
    def test_volume_confirmation_passes(self):
        """Test signal with sufficient volume."""
        market_data = self.base_market_data.copy()
        market_data['volume'] = 1200000  # Above 1.5x average
        result = self.validator.validate_signal(self.base_signal, market_data, self.base_portfolio)
        assert result.condition_results[ValidationCondition.VOLUME_CONFIRMATION.value]

    # Test 9: Market structure fails (Fibonacci in low volatility)
    def test_market_structure_fails_fibonacci_low_volatility(self):
        """Test Fibonacci signal in low volatility (ranging market)."""
        market_data = self.base_market_data.copy()
        market_data['atr'] = 100.0  # Only 0.2% of price (too low)
        result = self.validator.validate_signal(self.base_signal, market_data, self.base_portfolio)
        assert not result.condition_results[ValidationCondition.MARKET_STRUCTURE.value]
        assert any('Market structure unfavorable' in v for v in result.violations)

    # Test 10: Market structure passes (mean reversion in low volatility)
    def test_market_structure_passes_mean_reversion_low_volatility(self):
        """Test mean reversion signal in low volatility (ideal)."""
        signal = self.base_signal.copy()
        signal['strategy'] = 'alternative:mean_reversion_strategy'
        market_data = self.base_market_data.copy()
        market_data['atr'] = 500.0  # 1% volatility (good for mean reversion)
        result = self.validator.validate_signal(signal, market_data, self.base_portfolio)
        assert result.condition_results[ValidationCondition.MARKET_STRUCTURE.value]

    # Test 11: Position sizing fails
    def test_position_sizing_fails(self):
        """Test signal with position size exceeding limit."""
        signal = self.base_signal.copy()
        signal['position_size'] = 7000.0  # 7% of portfolio (exceeds 5%)
        result = self.validator.validate_signal(signal, self.base_market_data, self.base_portfolio)
        assert not result.condition_results[ValidationCondition.POSITION_SIZING.value]
        assert any('Position sizing failed' in v for v in result.violations)

    # Test 12: Position sizing passes
    def test_position_sizing_passes(self):
        """Test signal with position size within limit."""
        signal = self.base_signal.copy()
        signal['position_size'] = 4000.0  # 4% of portfolio (within 5%)
        result = self.validator.validate_signal(signal, self.base_market_data, self.base_portfolio)
        assert result.condition_results[ValidationCondition.POSITION_SIZING.value]

    # Test 13: Portfolio correlation fails
    def test_portfolio_correlation_fails(self):
        """Test signal with high portfolio correlation."""
        portfolio = self.base_portfolio.copy()
        portfolio['correlations'] = {'BTCUSDT': 0.85}  # Exceeds 0.7 limit
        result = self.validator.validate_signal(self.base_signal, self.base_market_data, portfolio)
        assert not result.condition_results[ValidationCondition.PORTFOLIO_CORRELATION.value]
        assert any('Portfolio correlation too high' in v for v in result.violations)

    # Test 14: Portfolio correlation passes
    def test_portfolio_correlation_passes(self):
        """Test signal with acceptable portfolio correlation."""
        portfolio = self.base_portfolio.copy()
        portfolio['correlations'] = {'BTCUSDT': 0.5}  # Within 0.7 limit
        result = self.validator.validate_signal(self.base_signal, self.base_market_data, portfolio)
        assert result.condition_results[ValidationCondition.PORTFOLIO_CORRELATION.value]

    # Test 15: Confidence scoring (5 of 7 conditions pass = 71%)
    def test_confidence_scoring_partial_pass(self):
        """Test confidence score with 5 of 7 conditions passing."""
        signal = self.base_signal.copy()
        signal['position_size'] = 7000.0  # Fail position sizing
        market_data = self.base_market_data.copy()
        market_data['rsi'] = 65.0  # Fail RSI
        result = self.validator.validate_signal(signal, market_data, self.base_portfolio)
        # 5 pass, 2 fail = 71.43%
        assert 70 <= result.confidence <= 72
        assert result.is_valid  # Still valid (>= 60%)

    # Test 16: Confidence scoring below threshold (invalid signal)
    def test_confidence_scoring_below_threshold(self):
        """Test signal with confidence below 60% (invalid)."""
        signal = self.base_signal.copy()
        signal['position_size'] = 7000.0  # Fail position sizing
        signal['current_price'] = 51000.0  # Fail price level
        market_data = self.base_market_data.copy()
        market_data['rsi'] = 65.0  # Fail RSI
        market_data['volume'] = 500000  # Fail volume
        result = self.validator.validate_signal(signal, market_data, self.base_portfolio)
        # Only 3 of 7 pass = 42.86%
        assert result.confidence < 60
        assert not result.is_valid

    # Test 17: Unknown strategy (accepts by default)
    def test_unknown_strategy_accepts(self):
        """Test signal from unknown strategy (should accept)."""
        signal = self.base_signal.copy()
        signal['strategy'] = 'unknown_strategy_xyz'
        result = self.validator.validate_signal(signal, self.base_market_data, self.base_portfolio)
        assert result.condition_results[ValidationCondition.PRICE_LEVEL.value]  # Should pass

    # Test 18: Mean reversion strategy price validation
    def test_mean_reversion_strategy_price_validation(self):
        """Test mean reversion strategy price validation."""
        signal = self.base_signal.copy()
        signal['strategy'] = 'alternative:mean_reversion_strategy'
        result = self.validator.validate_signal(signal, self.base_market_data, self.base_portfolio)
        assert result.condition_results[ValidationCondition.PRICE_LEVEL.value]  # Should pass

    # Test 19: No portfolio state (accepts by default)
    def test_no_portfolio_state(self):
        """Test validation without portfolio state."""
        result = self.validator.validate_signal(self.base_signal, self.base_market_data, None)
        assert result.condition_results[ValidationCondition.PORTFOLIO_CORRELATION.value]  # Should pass

    # Test 20: Custom thresholds
    def test_custom_thresholds(self):
        """Test validator with custom thresholds."""
        validator = SignalValidator(
            rsi_oversold_threshold=30.0,
            volume_confirmation_multiplier=2.0,
            max_position_size_pct=3.0
        )
        # RSI 35 should now fail (above 30)
        result = validator.validate_signal(self.base_signal, self.base_market_data, self.base_portfolio)
        assert not result.condition_results[ValidationCondition.RSI_CONFIRMATION.value]

    # Test 21: Metadata tracking
    def test_metadata_tracking(self):
        """Test that metadata is properly tracked."""
        result = self.validator.validate_signal(self.base_signal, self.base_market_data, self.base_portfolio)
        assert 'strategy' in result.metadata
        assert 'rsi' in result.metadata
        assert 'ema_alignment' in result.metadata
        assert 'volume_ratio' in result.metadata
        assert 'atr' in result.metadata
        assert 'position_size_pct' in result.metadata

    # Test 22: Edge case - zero values
    def test_edge_case_zero_values(self):
        """Test validation with zero values in market data."""
        market_data = self.base_market_data.copy()
        market_data['avg_volume'] = 0
        market_data['atr'] = 0
        result = self.validator.validate_signal(self.base_signal, market_data, self.base_portfolio)
        # Should handle gracefully (fail volume, pass market structure)
        assert not result.condition_results[ValidationCondition.VOLUME_CONFIRMATION.value]
        assert result.condition_results[ValidationCondition.MARKET_STRUCTURE.value]

    # Test 23: Integration with Fibonacci engine output
    def test_integration_fibonacci_engine_output(self):
        """Test validation of real Fibonacci engine output."""
        fibonacci_signal = {
            'strategy': 'dynamic_fibonacci',
            'fib_levels': {
                'support_strong': 49300.0,
                'support_medium': 49700.0,
                'resistance_weak': 50300.0
            },
            'current_price': 49350.0,
            'atr': 500.0,
            'triggered_level': 'support_strong',
            'confidence': 0.85,
            'direction': 'long',
            'position_size': 3000.0,
            'symbol': 'BTCUSDT'
        }
        result = self.validator.validate_signal(fibonacci_signal, self.base_market_data, self.base_portfolio)
        assert isinstance(result, SignalValidationResult)
        assert result.confidence >= 0
        assert result.confidence <= 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
