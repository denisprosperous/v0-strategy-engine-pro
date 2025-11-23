"""Unit Tests for Data Validation Pipeline.

Tests Pydantic schemas, validation logic, duplicate detection,
and quality checks for all market data types.

Author: v0-strategy-engine-pro
Version: 1.0
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from pydantic import ValidationError

from data_pipeline.validators import (
    OHLCVCandle,
    TickerData,
    OrderBook,
    OrderBookLevel,
    TradeData,
    DataValidator,
    ValidationLevel,
    get_validator,
    validate_ohlcv
)


class TestOHLCVCandle:
    """Test OHLCV candle validation schema."""
    
    def test_valid_candle(self):
        """Test valid OHLCV candle passes validation."""
        candle = OHLCVCandle(
            timestamp=1700000000000,
            open=Decimal('50000'),
            high=Decimal('51000'),
            low=Decimal('49000'),
            close=Decimal('50500'),
            volume=Decimal('100')
        )
        assert candle.open == Decimal('50000')
        assert candle.high == Decimal('51000')
    
    def test_invalid_timestamp_too_old(self):
        """Test candle with timestamp before 2010 is rejected."""
        with pytest.raises(ValidationError, match="Timestamp too old"):
            OHLCVCandle(
                timestamp=1000000000,  # Year 2001
                open=Decimal('50000'),
                high=Decimal('51000'),
                low=Decimal('49000'),
                close=Decimal('50500'),
                volume=Decimal('100')
            )
    
    def test_invalid_timestamp_future(self):
        """Test candle with future timestamp is rejected."""
        future_ts = int((datetime.now() + timedelta(days=2)).timestamp() * 1000)
        with pytest.raises(ValidationError, match="Timestamp in future"):
            OHLCVCandle(
                timestamp=future_ts,
                open=Decimal('50000'),
                high=Decimal('51000'),
                low=Decimal('49000'),
                close=Decimal('50500'),
                volume=Decimal('100')
            )
    
    def test_negative_price_rejected(self):
        """Test negative prices are rejected."""
        with pytest.raises(ValidationError):
            OHLCVCandle(
                timestamp=1700000000000,
                open=Decimal('-50000'),  # Negative
                high=Decimal('51000'),
                low=Decimal('49000'),
                close=Decimal('50500'),
                volume=Decimal('100')
            )
    
    def test_zero_price_rejected(self):
        """Test zero prices are rejected."""
        with pytest.raises(ValidationError):
            OHLCVCandle(
                timestamp=1700000000000,
                open=Decimal('0'),  # Zero
                high=Decimal('51000'),
                low=Decimal('49000'),
                close=Decimal('50500'),
                volume=Decimal('100')
            )
    
    def test_high_not_highest_rejected(self):
        """Test high must be the highest price."""
        with pytest.raises(ValidationError, match="not the highest"):
            OHLCVCandle(
                timestamp=1700000000000,
                open=Decimal('50000'),
                high=Decimal('49000'),  # Lower than open
                low=Decimal('48000'),
                close=Decimal('49500'),
                volume=Decimal('100')
            )
    
    def test_low_not_lowest_rejected(self):
        """Test low must be the lowest price."""
        with pytest.raises(ValidationError, match="not the lowest"):
            OHLCVCandle(
                timestamp=1700000000000,
                open=Decimal('50000'),
                high=Decimal('51000'),
                low=Decimal('51000'),  # Higher than close
                close=Decimal('50500'),
                volume=Decimal('100')
            )
    
    def test_close_outside_range_rejected(self):
        """Test close must be within high/low range."""
        with pytest.raises(ValidationError, match="outside high/low"):
            OHLCVCandle(
                timestamp=1700000000000,
                open=Decimal('50000'),
                high=Decimal('51000'),
                low=Decimal('49000'),
                close=Decimal('52000'),  # Above high
                volume=Decimal('100')
            )
    
    def test_zero_volume_accepted_with_warning(self):
        """Test zero volume is accepted (but warns)."""
        candle = OHLCVCandle(
            timestamp=1700000000000,
            open=Decimal('50000'),
            high=Decimal('51000'),
            low=Decimal('49000'),
            close=Decimal('50500'),
            volume=Decimal('0')  # Zero volume
        )
        assert candle.volume == Decimal('0')


class TestTickerData:
    """Test ticker data validation schema."""
    
    def test_valid_ticker(self):
        """Test valid ticker passes validation."""
        ticker = TickerData(
            symbol='BTC/USDT',
            timestamp=1700000000000,
            bid=Decimal('50000'),
            ask=Decimal('50010'),
            last=Decimal('50005'),
            volume_24h=Decimal('1000'),
            high_24h=Decimal('51000'),
            low_24h=Decimal('49000')
        )
        assert ticker.symbol == 'BTC/USDT'
    
    def test_bid_greater_than_ask_rejected(self):
        """Test bid >= ask is rejected."""
        with pytest.raises(ValidationError, match="Bid.*Ask"):
            TickerData(
                symbol='BTC/USDT',
                timestamp=1700000000000,
                bid=Decimal('50010'),  # Bid > Ask
                ask=Decimal('50000'),
                last=Decimal('50005'),
                volume_24h=Decimal('1000'),
                high_24h=Decimal('51000'),
                low_24h=Decimal('49000')
            )
    
    def test_last_outside_24h_range_rejected(self):
        """Test last price outside 24h range is rejected."""
        with pytest.raises(ValidationError, match="outside 24h range"):
            TickerData(
                symbol='BTC/USDT',
                timestamp=1700000000000,
                bid=Decimal('50000'),
                ask=Decimal('50010'),
                last=Decimal('52000'),  # Above 24h high
                volume_24h=Decimal('1000'),
                high_24h=Decimal('51000'),
                low_24h=Decimal('49000')
            )
    
    def test_24h_high_less_than_low_rejected(self):
        """Test 24h high < low is rejected."""
        with pytest.raises(ValidationError, match="24h high.*< low"):
            TickerData(
                symbol='BTC/USDT',
                timestamp=1700000000000,
                bid=Decimal('50000'),
                ask=Decimal('50010'),
                last=Decimal('50005'),
                volume_24h=Decimal('1000'),
                high_24h=Decimal('49000'),  # High < Low
                low_24h=Decimal('51000')
            )


class TestOrderBook:
    """Test order book validation schema."""
    
    def test_valid_order_book(self):
        """Test valid order book passes validation."""
        book = OrderBook(
            symbol='BTC/USDT',
            timestamp=1700000000000,
            bids=[
                OrderBookLevel(price=Decimal('50000'), quantity=Decimal('1.5')),
                OrderBookLevel(price=Decimal('49990'), quantity=Decimal('2.0'))
            ],
            asks=[
                OrderBookLevel(price=Decimal('50010'), quantity=Decimal('1.2')),
                OrderBookLevel(price=Decimal('50020'), quantity=Decimal('1.8'))
            ]
        )
        assert len(book.bids) == 2
        assert len(book.asks) == 2
    
    def test_best_bid_greater_than_ask_rejected(self):
        """Test best bid >= best ask is rejected."""
        with pytest.raises(ValidationError, match="Best bid.*best ask"):
            OrderBook(
                symbol='BTC/USDT',
                timestamp=1700000000000,
                bids=[
                    OrderBookLevel(price=Decimal('50020'), quantity=Decimal('1.5'))
                ],
                asks=[
                    OrderBookLevel(price=Decimal('50010'), quantity=Decimal('1.2'))
                ]
            )
    
    def test_empty_bids_or_asks_rejected(self):
        """Test order book must have at least one bid and ask."""
        with pytest.raises(ValidationError):
            OrderBook(
                symbol='BTC/USDT',
                timestamp=1700000000000,
                bids=[],  # Empty
                asks=[
                    OrderBookLevel(price=Decimal('50010'), quantity=Decimal('1.2'))
                ]
            )


class TestTradeData:
    """Test trade data validation schema."""
    
    def test_valid_trade(self):
        """Test valid trade passes validation."""
        trade = TradeData(
            trade_id='12345',
            symbol='BTC/USDT',
            timestamp=1700000000000,
            price=Decimal('50000'),
            quantity=Decimal('1.5'),
            side='buy',
            is_maker=True
        )
        assert trade.trade_id == '12345'
    
    def test_invalid_side_rejected(self):
        """Test invalid side value is rejected."""
        with pytest.raises(ValidationError):
            TradeData(
                trade_id='12345',
                symbol='BTC/USDT',
                timestamp=1700000000000,
                price=Decimal('50000'),
                quantity=Decimal('1.5'),
                side='invalid',  # Must be buy/sell
                is_maker=True
            )


class TestDataValidator:
    """Test DataValidator functionality."""
    
    def test_initialization(self):
        """Test validator initialization."""
        validator = DataValidator(level=ValidationLevel.STRICT)
        assert validator.level == ValidationLevel.STRICT
        assert validator.stats['total_validated'] == 0
    
    def test_validate_ohlcv_batch_all_valid(self):
        """Test batch validation with all valid candles."""
        validator = DataValidator()
        candles = [
            [1700000000000, 50000, 51000, 49000, 50500, 100],
            [1700000060000, 50500, 51500, 50000, 51000, 120],
            [1700000120000, 51000, 52000, 50500, 51500, 150]
        ]
        
        valid, errors = validator.validate_ohlcv_batch(
            candles=candles,
            symbol='BTC/USDT'
        )
        
        assert len(valid) == 3
        assert len(errors) == 0
        assert validator.stats['passed'] == 3
        assert validator.stats['failed'] == 0
    
    def test_validate_ohlcv_batch_with_invalid(self):
        """Test batch validation with some invalid candles."""
        validator = DataValidator()
        candles = [
            [1700000000000, 50000, 51000, 49000, 50500, 100],  # Valid
            [1700000060000, 50500, 49000, 50000, 51000, 120],  # Invalid: high < close
            [1700000120000, 51000, 52000, 50500, 51500, 150]   # Valid
        ]
        
        valid, errors = validator.validate_ohlcv_batch(
            candles=candles,
            symbol='BTC/USDT'
        )
        
        assert len(valid) == 2  # Only 2 valid
        assert len(errors) == 1
        assert errors[0]['index'] == 1
        assert validator.stats['failed'] == 1
    
    def test_duplicate_detection(self):
        """Test duplicate candles are detected."""
        validator = DataValidator()
        candles = [
            [1700000000000, 50000, 51000, 49000, 50500, 100],
            [1700000000000, 50000, 51000, 49000, 50500, 100],  # Duplicate
            [1700000060000, 50500, 51500, 50000, 51000, 120]
        ]
        
        valid, errors = validator.validate_ohlcv_batch(
            candles=candles,
            symbol='BTC/USDT',
            allow_duplicates=False
        )
        
        assert len(valid) == 2  # Duplicate skipped
        assert validator.stats['duplicates_detected'] == 1
        assert any('duplicate' in e['error'] for e in errors)
    
    def test_late_arrival_detection(self):
        """Test out-of-order candles are detected."""
        validator = DataValidator(level=ValidationLevel.STRICT)
        candles = [
            [1700000120000, 51000, 52000, 50500, 51500, 150],  # Latest
            [1700000060000, 50500, 51500, 50000, 51000, 120],  # Out of order
        ]
        
        valid, errors = validator.validate_ohlcv_batch(
            candles=candles,
            symbol='BTC/USDT'
        )
        
        assert validator.stats['late_arrivals'] == 1
    
    def test_remove_duplicates(self):
        """Test duplicate removal utility."""
        validator = DataValidator()
        candles = [
            [1700000000000, 50000, 51000, 49000, 50500, 100],
            [1700000000000, 50000, 51000, 49000, 50500, 100],  # Duplicate
            [1700000060000, 50500, 51500, 50000, 51000, 120],
            [1700000060000, 50500, 51500, 50000, 51000, 120],  # Duplicate
        ]
        
        unique = validator.remove_duplicates(candles)
        
        assert len(unique) == 2
        assert validator.stats['duplicates_detected'] == 2
    
    def test_sort_by_timestamp(self):
        """Test timestamp sorting."""
        validator = DataValidator()
        candles = [
            [1700000120000, 51000, 52000, 50500, 51500, 150],
            [1700000000000, 50000, 51000, 49000, 50500, 100],
            [1700000060000, 50500, 51500, 50000, 51000, 120],
        ]
        
        sorted_candles = validator.sort_by_timestamp(candles)
        
        timestamps = [c[0] for c in sorted_candles]
        assert timestamps == sorted(timestamps)
    
    def test_get_stats(self):
        """Test statistics tracking."""
        validator = DataValidator()
        candles = [
            [1700000000000, 50000, 51000, 49000, 50500, 100],  # Valid
            [1700000060000, 50500, 49000, 50000, 51000, 120],  # Invalid
        ]
        
        validator.validate_ohlcv_batch(candles, 'BTC/USDT')
        stats = validator.get_stats()
        
        assert stats['total_validated'] == 2
        assert stats['passed'] == 1
        assert stats['failed'] == 1
        assert stats['success_rate_percent'] == 50.0
    
    def test_reset_stats(self):
        """Test statistics reset."""
        validator = DataValidator()
        validator.stats['passed'] = 100
        validator.stats['failed'] = 50
        
        validator.reset_stats()
        
        assert validator.stats['passed'] == 0
        assert validator.stats['failed'] == 0
    
    def test_clear_cache(self):
        """Test duplicate detection cache clearing."""
        validator = DataValidator()
        candles = [
            [1700000000000, 50000, 51000, 49000, 50500, 100]
        ]
        
        # First validation
        validator.validate_ohlcv_batch(candles, 'BTC/USDT')
        assert len(validator._seen_ids) > 0
        
        # Clear cache
        validator.clear_cache()
        assert len(validator._seen_ids) == 0
        
        # Same candle should be accepted again
        valid, errors = validator.validate_ohlcv_batch(candles, 'BTC/USDT')
        assert len(valid) == 1


class TestValidationLevels:
    """Test different validation strictness levels."""
    
    def test_strict_level_rejects_late_arrivals(self):
        """Test STRICT level rejects late arrivals."""
        validator = DataValidator(level=ValidationLevel.STRICT)
        candles = [
            [1700000120000, 51000, 52000, 50500, 51500, 150],
            [1700000060000, 50500, 51500, 50000, 51000, 120],  # Late
        ]
        
        valid, errors = validator.validate_ohlcv_batch(candles, 'BTC/USDT')
        
        assert len(valid) == 1  # Late arrival rejected
        assert any('late_arrival' in e['error'] for e in errors)
    
    def test_normal_level_accepts_late_arrivals(self):
        """Test NORMAL level accepts late arrivals with warning."""
        validator = DataValidator(level=ValidationLevel.NORMAL)
        candles = [
            [1700000120000, 51000, 52000, 50500, 51500, 150],
            [1700000060000, 50500, 51500, 50000, 51000, 120],  # Late
        ]
        
        valid, errors = validator.validate_ohlcv_batch(candles, 'BTC/USDT')
        
        # Late arrival accepted in NORMAL mode
        assert len(valid) >= 1


class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    def test_get_validator_singleton(self):
        """Test global validator is singleton."""
        validator1 = get_validator()
        validator2 = get_validator()
        
        assert validator1 is validator2
    
    def test_validate_ohlcv_convenience(self):
        """Test validate_ohlcv convenience function."""
        candles = [
            [1700000000000, 50000, 51000, 49000, 50500, 100],
            [1700000060000, 50500, 51500, 50000, 51000, 120]
        ]
        
        valid, errors = validate_ohlcv(
            candles=candles,
            symbol='BTC/USDT',
            strict=False
        )
        
        assert len(valid) == 2
        assert len(errors) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
