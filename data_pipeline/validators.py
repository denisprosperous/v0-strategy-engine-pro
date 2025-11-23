"""Data Validation Pipeline - Segment 3

Comprehensive validation for all market data using Pydantic schemas.
Ensures data quality, detects duplicates, and handles late arrivals.

Features:
- Pydantic schema validation for OHLCV, tickers, order books, trades
- Duplicate detection and deduplication
- Data quality checks (NaN, infinity, negative prices, zero volumes)
- Out-of-order timestamp handling
- Validation statistics and error reporting
- Configurable strictness levels

Author: v0-strategy-engine-pro
Version: 1.0
"""

import logging
from typing import List, Optional, Dict, Any, Tuple, Set
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import Enum

import numpy as np
from pydantic import BaseModel, Field, validator, root_validator
from pydantic import ValidationError as PydanticValidationError

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation strictness levels."""
    STRICT = "strict"      # Reject any invalid data
    NORMAL = "normal"      # Reject critical issues, warn on minor
    LENIENT = "lenient"    # Accept most data, log warnings


class OHLCVCandle(BaseModel):
    """OHLCV candlestick data validation schema."""
    
    timestamp: int = Field(..., gt=0, description="Unix timestamp in milliseconds")
    open: Decimal = Field(..., gt=0, description="Opening price")
    high: Decimal = Field(..., gt=0, description="Highest price")
    low: Decimal = Field(..., gt=0, description="Lowest price")
    close: Decimal = Field(..., gt=0, description="Closing price")
    volume: Decimal = Field(..., ge=0, description="Trading volume")
    
    class Config:
        json_encoders = {Decimal: float}
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Ensure timestamp is within reasonable range."""
        # Reject timestamps before 2010 or more than 1 day in future
        min_timestamp = 1262304000000  # Jan 1, 2010
        max_timestamp = int(datetime.now().timestamp() * 1000) + 86400000  # +1 day
        
        if v < min_timestamp:
            raise ValueError(f"Timestamp too old: {v}")
        if v > max_timestamp:
            raise ValueError(f"Timestamp in future: {v}")
        
        return v
    
    @root_validator
    def validate_ohlc_logic(cls, values):
        """Validate OHLC price relationships."""
        o, h, l, c = values.get('open'), values.get('high'), values.get('low'), values.get('close')
        
        if not all([o, h, l, c]):
            return values
        
        # High must be highest
        if h < max(o, c, l):
            raise ValueError(f"High {h} is not the highest price")
        
        # Low must be lowest
        if l > min(o, c, h):
            raise ValueError(f"Low {l} is not the lowest price")
        
        # Close must be within high/low range
        if not (l <= c <= h):
            raise ValueError(f"Close {c} outside high/low range")
        
        # Open must be within high/low range
        if not (l <= o <= h):
            raise ValueError(f"Open {o} outside high/low range")
        
        return values
    
    @validator('volume')
    def validate_volume(cls, v, values):
        """Check for suspiciously low or high volume."""
        # Warn if volume is exactly zero (possible but rare)
        if v == 0:
            logger.warning(f"Zero volume candle at {values.get('timestamp')}")
        
        return v


class TickerData(BaseModel):
    """Ticker data validation schema."""
    
    symbol: str = Field(..., min_length=3, max_length=20)
    timestamp: int = Field(..., gt=0)
    bid: Decimal = Field(..., gt=0)
    ask: Decimal = Field(..., gt=0)
    last: Decimal = Field(..., gt=0)
    volume_24h: Decimal = Field(..., ge=0)
    high_24h: Decimal = Field(..., gt=0)
    low_24h: Decimal = Field(..., gt=0)
    
    @root_validator
    def validate_ticker_logic(cls, values):
        """Validate ticker data relationships."""
        bid, ask, last = values.get('bid'), values.get('ask'), values.get('last')
        high, low = values.get('high_24h'), values.get('low_24h')
        
        if bid and ask and bid >= ask:
            raise ValueError(f"Bid {bid} >= Ask {ask}")
        
        if last and high and low:
            if not (low <= last <= high):
                raise ValueError(f"Last price {last} outside 24h range [{low}, {high}]")
        
        if high and low and high < low:
            raise ValueError(f"24h high {high} < low {low}")
        
        return values


class OrderBookLevel(BaseModel):
    """Single order book level (price, quantity)."""
    
    price: Decimal = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=0)


class OrderBook(BaseModel):
    """Order book validation schema."""
    
    symbol: str = Field(..., min_length=3)
    timestamp: int = Field(..., gt=0)
    bids: List[OrderBookLevel] = Field(..., min_items=1, max_items=1000)
    asks: List[OrderBookLevel] = Field(..., min_items=1, max_items=1000)
    
    @root_validator
    def validate_order_book(cls, values):
        """Validate order book structure."""
        bids = values.get('bids', [])
        asks = values.get('asks', [])
        
        if not bids or not asks:
            return values
        
        # Bids should be descending (highest first)
        bid_prices = [b.price for b in bids]
        if bid_prices != sorted(bid_prices, reverse=True):
            logger.warning("Bids not sorted in descending order")
        
        # Asks should be ascending (lowest first)
        ask_prices = [a.price for a in asks]
        if ask_prices != sorted(ask_prices):
            logger.warning("Asks not sorted in ascending order")
        
        # Best bid should be < best ask
        best_bid = bid_prices[0]
        best_ask = ask_prices[0]
        if best_bid >= best_ask:
            raise ValueError(f"Best bid {best_bid} >= best ask {best_ask}")
        
        return values


class TradeData(BaseModel):
    """Trade execution validation schema."""
    
    trade_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=3)
    timestamp: int = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=0)
    side: str = Field(..., regex="^(buy|sell|BUY|SELL)$")
    is_maker: bool


class DataValidator:
    """Main data validation engine."""
    
    def __init__(self, level: ValidationLevel = ValidationLevel.NORMAL):
        """Initialize validator.
        
        Args:
            level: Validation strictness level
        """
        self.level = level
        self.stats = {
            'total_validated': 0,
            'passed': 0,
            'failed': 0,
            'duplicates_detected': 0,
            'quality_issues': 0,
            'late_arrivals': 0
        }
        self._seen_ids: Set[str] = set()  # For duplicate detection
        self._last_timestamps: Dict[str, int] = {}  # For late arrival detection
    
    def validate_ohlcv_batch(
        self,
        candles: List[List[Any]],
        symbol: str,
        allow_duplicates: bool = False
    ) -> Tuple[List[OHLCVCandle], List[Dict[str, Any]]]:
        """Validate batch of OHLCV candles.
        
        Args:
            candles: List of [timestamp, open, high, low, close, volume]
            symbol: Trading symbol
            allow_duplicates: If True, don't check for duplicates
        
        Returns:
            Tuple of (valid_candles, errors)
        """
        valid_candles = []
        errors = []
        
        for i, candle in enumerate(candles):
            self.stats['total_validated'] += 1
            
            try:
                # Convert to dict for Pydantic
                candle_dict = {
                    'timestamp': int(candle[0]),
                    'open': Decimal(str(candle[1])),
                    'high': Decimal(str(candle[2])),
                    'low': Decimal(str(candle[3])),
                    'close': Decimal(str(candle[4])),
                    'volume': Decimal(str(candle[5]))
                }
                
                # Validate with Pydantic
                validated = OHLCVCandle(**candle_dict)
                
                # Check for duplicates
                candle_id = f"{symbol}:{validated.timestamp}"
                if not allow_duplicates and candle_id in self._seen_ids:
                    self.stats['duplicates_detected'] += 1
                    errors.append({
                        'index': i,
                        'error': 'duplicate',
                        'message': f"Duplicate candle at {validated.timestamp}"
                    })
                    continue
                
                # Check for late arrivals (out of order)
                last_ts = self._last_timestamps.get(symbol, 0)
                if validated.timestamp < last_ts:
                    self.stats['late_arrivals'] += 1
                    if self.level == ValidationLevel.STRICT:
                        errors.append({
                            'index': i,
                            'error': 'late_arrival',
                            'message': f"Out of order: {validated.timestamp} < {last_ts}"
                        })
                        continue
                    else:
                        logger.warning(f"Late arrival for {symbol}: {validated.timestamp}")
                
                # Quality checks
                if not self._quality_check_candle(validated):
                    self.stats['quality_issues'] += 1
                    if self.level == ValidationLevel.STRICT:
                        errors.append({
                            'index': i,
                            'error': 'quality_check',
                            'message': 'Failed quality check'
                        })
                        continue
                
                # Mark as valid
                self._seen_ids.add(candle_id)
                self._last_timestamps[symbol] = validated.timestamp
                valid_candles.append(validated)
                self.stats['passed'] += 1
                
            except (ValueError, InvalidOperation, PydanticValidationError) as e:
                self.stats['failed'] += 1
                errors.append({
                    'index': i,
                    'error': 'validation_error',
                    'message': str(e),
                    'data': candle
                })
        
        return valid_candles, errors
    
    def validate_ticker(self, ticker_data: Dict[str, Any]) -> Optional[TickerData]:
        """Validate ticker data.
        
        Args:
            ticker_data: Raw ticker data dict
        
        Returns:
            Validated TickerData or None if invalid
        """
        self.stats['total_validated'] += 1
        
        try:
            validated = TickerData(**ticker_data)
            self.stats['passed'] += 1
            return validated
        except PydanticValidationError as e:
            self.stats['failed'] += 1
            logger.error(f"Ticker validation failed: {e}")
            return None
    
    def validate_order_book(self, book_data: Dict[str, Any]) -> Optional[OrderBook]:
        """Validate order book data.
        
        Args:
            book_data: Raw order book dict
        
        Returns:
            Validated OrderBook or None if invalid
        """
        self.stats['total_validated'] += 1
        
        try:
            # Convert bids/asks to OrderBookLevel objects
            if 'bids' in book_data:
                book_data['bids'] = [
                    OrderBookLevel(price=Decimal(str(b[0])), quantity=Decimal(str(b[1])))
                    for b in book_data['bids']
                ]
            if 'asks' in book_data:
                book_data['asks'] = [
                    OrderBookLevel(price=Decimal(str(a[0])), quantity=Decimal(str(a[1])))
                    for a in book_data['asks']
                ]
            
            validated = OrderBook(**book_data)
            self.stats['passed'] += 1
            return validated
        except PydanticValidationError as e:
            self.stats['failed'] += 1
            logger.error(f"Order book validation failed: {e}")
            return None
    
    def _quality_check_candle(self, candle: OHLCVCandle) -> bool:
        """Perform quality checks on candle data.
        
        Args:
            candle: Validated OHLCV candle
        
        Returns:
            True if passes quality checks
        """
        # Check for NaN or infinity
        for field in ['open', 'high', 'low', 'close', 'volume']:
            value = getattr(candle, field)
            if value != value:  # NaN check
                logger.error(f"NaN detected in {field}")
                return False
            if value == float('inf') or value == float('-inf'):
                logger.error(f"Infinity detected in {field}")
                return False
        
        # Check for unrealistic price movements (>50% in one candle)
        price_change = abs(candle.close - candle.open) / candle.open
        if price_change > 0.5:
            logger.warning(f"Large price movement: {price_change*100:.1f}%")
            # Don't reject, just warn
        
        # Check for zero spread (suspicious)
        if candle.high == candle.low:
            logger.warning(f"Zero spread candle at {candle.timestamp}")
        
        return True
    
    def remove_duplicates(
        self,
        candles: List[List[Any]]
    ) -> List[List[Any]]:
        """Remove duplicate candles based on timestamp.
        
        Args:
            candles: List of OHLCV candles
        
        Returns:
            Deduplicated list
        """
        seen_timestamps = set()
        unique_candles = []
        
        for candle in candles:
            timestamp = int(candle[0])
            if timestamp not in seen_timestamps:
                seen_timestamps.add(timestamp)
                unique_candles.append(candle)
            else:
                self.stats['duplicates_detected'] += 1
        
        return unique_candles
    
    def sort_by_timestamp(
        self,
        candles: List[List[Any]]
    ) -> List[List[Any]]:
        """Sort candles by timestamp (handle late arrivals).
        
        Args:
            candles: List of OHLCV candles
        
        Returns:
            Sorted list
        """
        return sorted(candles, key=lambda x: int(x[0]))
    
    def get_stats(self) -> Dict[str, int]:
        """Get validation statistics.
        
        Returns:
            Dict with validation stats
        """
        success_rate = (self.stats['passed'] / self.stats['total_validated'] * 100) \
            if self.stats['total_validated'] > 0 else 0
        
        return {
            **self.stats,
            'success_rate_percent': round(success_rate, 2)
        }
    
    def reset_stats(self) -> None:
        """Reset validation statistics."""
        self.stats = {
            'total_validated': 0,
            'passed': 0,
            'failed': 0,
            'duplicates_detected': 0,
            'quality_issues': 0,
            'late_arrivals': 0
        }
    
    def clear_cache(self) -> None:
        """Clear duplicate detection cache."""
        self._seen_ids.clear()
        self._last_timestamps.clear()


# Module-level validator instance
_validator: Optional[DataValidator] = None


def get_validator(level: ValidationLevel = ValidationLevel.NORMAL) -> DataValidator:
    """Get or create the global validator instance.
    
    Args:
        level: Validation strictness level
    
    Returns:
        DataValidator instance
    """
    global _validator
    if _validator is None:
        _validator = DataValidator(level=level)
    return _validator


def validate_ohlcv(
    candles: List[List[Any]],
    symbol: str,
    strict: bool = False
) -> Tuple[List[OHLCVCandle], List[Dict[str, Any]]]:
    """Convenience function to validate OHLCV data.
    
    Args:
        candles: List of OHLCV candles
        symbol: Trading symbol
        strict: Use strict validation
    
    Returns:
        Tuple of (valid_candles, errors)
    """
    level = ValidationLevel.STRICT if strict else ValidationLevel.NORMAL
    validator = get_validator(level=level)
    return validator.validate_ohlcv_batch(candles, symbol)
