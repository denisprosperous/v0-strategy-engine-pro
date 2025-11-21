"""News Filter: Economic Calendar & Event Awareness.

Safety layer that prevents trading during high-impact economic events.

Handles:
- Forex: Red-flag events (NFP, CPI, FOMC, ECB, BoE) - 30min buffer
- Stocks: Earnings announcements - 48 hour blackout
- Crypto: Funding rate spikes, BTC dominance shocks - rate limiting

Author: Trading Bot v0
Version: 1.0
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EventImpact(Enum):
    """Economic event impact levels."""
    HIGH = 3      # Red flag - skip trading
    MEDIUM = 2    # Yellow flag - reduce risk
    LOW = 1       # Green flag - tradeable


class EventType(Enum):
    """Types of economic events."""
    NFP = 'nonfarm_payroll'          # US Non-Farm Payroll
    CPI = 'consumer_price_index'     # Inflation data
    FOMC = 'fed_funds_decision'      # Federal Reserve decision
    ECB = 'ecb_decision'             # European Central Bank
    BOE = 'boe_decision'             # Bank of England
    EARNINGS = 'earnings'             # Company earnings
    DIVIDEND = 'dividend_ex_date'    # Stock dividend date
    FUNDING = 'crypto_funding'       # Crypto funding rate
    BTC_DOMINANCE = 'btc_dominance'  # BTC dominance shift


class EventSeverity(Enum):
    """How severe the market impact typically is."""
    CRITICAL = 5   # Extreme volatility expected
    VERY_HIGH = 4  # High volatility likely
    HIGH = 3       # Moderate-high volatility
    MEDIUM = 2     # Moderate volatility
    LOW = 1        # Low volatility


class NewsEvent:
    """Represents a single economic event."""
    
    def __init__(self, event_type: EventType, event_time: datetime,
                 asset_class: str, impact: EventImpact,
                 severity: EventSeverity, description: str = ""):
        self.event_type = event_type
        self.event_time = event_time  # UTC time of event
        self.asset_class = asset_class  # 'forex', 'stocks', 'crypto'
        self.impact = impact
        self.severity = severity
        self.description = description
    
    def is_active(self, current_time: datetime, buffer_before_min: int = 30,
                  buffer_after_min: int = 30) -> bool:
        """Check if event is currently active (within buffer window).
        
        Args:
            current_time: Current time (UTC)
            buffer_before_min: Minutes before event to block trading
            buffer_after_min: Minutes after event to block trading
            
        Returns:
            True if currently in event window
        """
        time_to_event = (self.event_time - current_time).total_seconds() / 60
        
        # Check if we're in the buffer window
        if -buffer_after_min < time_to_event < buffer_before_min:
            return True
        
        return False
    
    def minutes_until_event(self, current_time: datetime) -> float:
        """Get minutes until event (negative if past)."""
        delta = self.event_time - current_time
        return delta.total_seconds() / 60


class NewsFilter:
    """Economic calendar and event-aware trading filter."""
    
    # Red-flag events for Forex
    FOREX_RED_FLAGS = [
        EventType.NFP,
        EventType.CPI,
        EventType.FOMC,
        EventType.ECB,
        EventType.BOE,
    ]
    
    # Earnings for Stocks
    STOCK_EVENTS = [
        EventType.EARNINGS,
        EventType.DIVIDEND,
    ]
    
    # Crypto events
    CRYPTO_EVENTS = [
        EventType.FUNDING,
        EventType.BTC_DOMINANCE,
    ]
    
    def __init__(self):
        self.scheduled_events: List[NewsEvent] = []
        self.event_cache = {}  # Cache for recent events
    
    def add_event(self, event: NewsEvent):
        """Add an event to the calendar."""
        self.scheduled_events.append(event)
        logger.info(f"Added event: {event.event_type.value} at {event.event_time}")
    
    def add_forex_event(self, event_type: EventType, event_time: datetime,
                       impact: EventImpact, severity: EventSeverity,
                       description: str = ""):
        """Add a Forex economic event."""
        if event_type not in self.FOREX_RED_FLAGS:
            logger.warning(f"{event_type.value} not a known Forex event")
        
        event = NewsEvent(event_type, event_time, 'forex', impact, severity, description)
        self.add_event(event)
    
    def add_stock_event(self, event_type: EventType, symbol: str,
                       event_time: datetime, impact: EventImpact,
                       severity: EventSeverity, description: str = ""):
        """Add a stock market event (earnings, dividends)."""
        desc = f"{symbol}: {description}" if description else symbol
        event = NewsEvent(event_type, event_time, f'stocks_{symbol}', impact, severity, desc)
        self.add_event(event)
    
    def add_crypto_event(self, event_type: EventType, event_time: datetime,
                        impact: EventImpact, severity: EventSeverity,
                        description: str = ""):
        """Add a crypto market event."""
        event = NewsEvent(event_type, event_time, 'crypto', impact, severity, description)
        self.add_event(event)
    
    def can_trade_forex(self, current_time: datetime,
                       buffer_min: int = 30) -> Tuple[bool, Optional[str]]:
        """Check if safe to trade Forex now.
        
        Args:
            current_time: Current UTC time
            buffer_min: Minutes before/after event to block trading
            
        Returns:
            (can_trade, reason) tuple
        """
        for event in self.scheduled_events:
            if event.asset_class != 'forex':
                continue
            
            if event.is_active(current_time, buffer_before_min=buffer_min,
                             buffer_after_min=buffer_min):
                minutes = event.minutes_until_event(current_time)
                if minutes > 0:
                    return False, f"Event {event.event_type.value} in {minutes:.0f}min"
                else:
                    return False, f"Event {event.event_type.value} just occurred"
        
        return True, None
    
    def can_trade_stock(self, symbol: str, current_time: datetime,
                       buffer_hours: int = 48) -> Tuple[bool, Optional[str]]:
        """Check if safe to trade stock now.
        
        Args:
            symbol: Stock symbol
            current_time: Current UTC time
            buffer_hours: Hours before/after earnings to block trading
            
        Returns:
            (can_trade, reason) tuple
        """
        buffer_min = buffer_hours * 60
        
        for event in self.scheduled_events:
            if not event.asset_class.startswith(f'stocks_{symbol}'):
                continue
            
            if event.event_type == EventType.EARNINGS:
                if event.is_active(current_time, buffer_before_min=buffer_min,
                                 buffer_after_min=buffer_min):
                    hours = event.minutes_until_event(current_time) / 60
                    if hours > 0:
                        return False, f"Earnings in {hours:.1f}h"
                    else:
                        return False, f"Earnings just occurred"
        
        return True, None
    
    def can_trade_crypto(self, current_time: datetime,
                        funding_check: bool = True) -> Tuple[bool, Optional[str]]:
        """Check if safe to trade Crypto now.
        
        Args:
            current_time: Current UTC time
            funding_check: Whether to check funding rate events
            
        Returns:
            (can_trade, reason) tuple
        """
        # Funding rate typically happens every 8 hours (00:00, 08:00, 16:00 UTC)
        if funding_check:
            hour = current_time.hour
            # Avoid trading 15min before and after funding times
            if hour in [0, 8, 16]:
                minute = current_time.minute
                if minute < 15 or minute > 45:
                    return False, "Near crypto funding time (high volatility)"
        
        # Check for scheduled dominance shocks
        for event in self.scheduled_events:
            if event.asset_class != 'crypto':
                continue
            
            if event.event_type == EventType.BTC_DOMINANCE:
                if event.is_active(current_time, buffer_before_min=15,
                                 buffer_after_min=30):
                    return False, f"BTC dominance event: {event.description}"
        
        return True, None
    
    def get_next_event(self, asset_class: str, current_time: datetime) -> Optional[NewsEvent]:
        """Get the next upcoming event for an asset class.
        
        Args:
            asset_class: 'forex', 'stocks', or 'crypto'
            current_time: Current UTC time
            
        Returns:
            Next NewsEvent or None
        """
        upcoming = []
        for event in self.scheduled_events:
            if asset_class == 'stocks' and not event.asset_class.startswith('stocks'):
                continue
            elif asset_class != 'stocks' and event.asset_class != asset_class:
                continue
            
            if event.event_time > current_time:
                upcoming.append(event)
        
        if not upcoming:
            return None
        
        # Return soonest event
        return min(upcoming, key=lambda e: e.event_time)
    
    def get_events_in_range(self, asset_class: str, start_time: datetime,
                           end_time: datetime) -> List[NewsEvent]:
        """Get all events in a time range.
        
        Args:
            asset_class: Filter by asset class
            start_time: Range start
            end_time: Range end
            
        Returns:
            List of matching events
        """
        events = []
        for event in self.scheduled_events:
            if asset_class == 'stocks' and not event.asset_class.startswith('stocks'):
                continue
            elif asset_class != 'stocks' and event.asset_class != asset_class:
                continue
            
            if start_time <= event.event_time <= end_time:
                events.append(event)
        
        return sorted(events, key=lambda e: e.event_time)
    
    def get_trading_restriction(self, symbol: str, current_time: datetime) -> Optional[str]:
        """Get any active trading restriction for a symbol.
        
        Returns reason if trading is restricted, None if OK.
        """
        if symbol.startswith('forex_'):
            can_trade, reason = self.can_trade_forex(current_time)
            return reason if not can_trade else None
        
        elif symbol.startswith('crypto_'):
            can_trade, reason = self.can_trade_crypto(current_time)
            return reason if not can_trade else None
        
        else:  # Stock
            can_trade, reason = self.can_trade_stock(symbol, current_time)
            return reason if not can_trade else None
    
    def clear_past_events(self, current_time: datetime):
        """Remove events that have passed."""
        self.scheduled_events = [
            e for e in self.scheduled_events 
            if e.event_time > current_time - timedelta(hours=1)
        ]
    
    def get_summary(self) -> Dict:
        """Get current event calendar summary."""
        forex_events = [e for e in self.scheduled_events if e.asset_class == 'forex']
        stock_events = [e for e in self.scheduled_events if e.asset_class.startswith('stocks')]
        crypto_events = [e for e in self.scheduled_events if e.asset_class == 'crypto']
        
        return {
            'total_events': len(self.scheduled_events),
            'forex_events': len(forex_events),
            'stock_events': len(stock_events),
            'crypto_events': len(crypto_events),
            'next_forex': str(self.get_next_event('forex', datetime.utcnow())) if self.get_next_event('forex', datetime.utcnow()) else None,
            'next_crypto': str(self.get_next_event('crypto', datetime.utcnow())) if self.get_next_event('crypto', datetime.utcnow()) else None,
        }


# Singleton instance
_filter = NewsFilter()


def get_news_filter() -> NewsFilter:
    """Get the global news filter instance."""
    return _filter
