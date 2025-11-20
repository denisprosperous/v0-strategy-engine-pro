"""Configuration Schema for Modular Trading Bot.

Developer-ready configuration with validation.
All parameters tuned for 3-4 high-confidence daily trades.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import json
from enum import Enum


class TimeFrame(Enum):
    """Supported timeframes."""
    M1 = '1m'
    M5 = '5m'
    M15 = '15m'
    M30 = '30m'
    H1 = '1h'
    H4 = '4h'
    D1 = '1d'
    W1 = '1w'


@dataclass
class TradeTargets:
    """Daily trading targets."""
    trades_per_day_min: int = 3
    trades_per_day_max: int = 4
    win_rate_target: float = 0.70
    profit_factor_target: float = 2.5
    max_drawdown: float = 0.10
    daily_expectancy: float = 0.02  # 2% average


@dataclass
class FibonacciConfig:
    """Fibonacci strategy parameters."""
    levels: List[float] = None
    tolerance_atr: float = 0.1
    primary_level: float = 0.618
    fractal_depth: int = 2
    swing_validity_atr: float = 0.5  # Invalidation threshold
    cache_ttl_seconds: int = 3600
    
    def __post_init__(self):
        if self.levels is None:
            self.levels = [0.236, 0.382, 0.5, 0.618, 0.786]


@dataclass
class RSIConfig:
    """RSI indicator parameters."""
    period: int = 14
    tier1_max: int = 30
    tier2_range: tuple = (25, 35)
    skip_above: int = 70
    skip_below: int = 15


@dataclass
class EMAConfig:
    """EMA trend parameters."""
    fast: int = 20
    mid: int = 50
    slow: int = 200


@dataclass
class VolumeConfig:
    """Volume confirmation parameters."""
    avg_period: int = 20
    tier1_min_multiple: float = 1.5
    tier2_min_multiple: float = 1.2
    skip_below_multiple: float = 0.8


@dataclass
class ATRConfig:
    """ATR parameters."""
    period: int = 14
    volatility_breaker_multiple: float = 2.0  # 2x spike triggers reduction


@dataclass
class RiskConfig:
    """Risk management parameters."""
    tier1_pct: float = 0.02  # 2%
    tier2_pct: float = 0.015  # 1.5%
    tier3_pct: float = 0.0075  # 0.75%
    
    daily_max_loss: float = 0.05  # 5%
    weekly_max_loss: float = 0.12  # 12%
    max_concurrent_exposure: float = 0.10  # 10%
    
    # Per-asset caps
    crypto_cap: float = 0.06
    forex_cap: float = 0.06
    stocks_cap: float = 0.06


@dataclass
class StopsConfig:
    """Stop loss parameters by asset class."""
    # Crypto
    crypto_min_pct: float = 0.005
    crypto_max_pct: float = 0.01
    crypto_atr_mult: float = 0.8
    
    # Forex
    forex_min_pct: float = 0.01
    forex_max_pct: float = 0.02
    forex_atr_mult: float = 1.0
    
    # Stocks
    stocks_min_pct: float = 0.01
    stocks_max_pct: float = 0.015
    stocks_atr_mult: float = 1.2


@dataclass
class TargetsConfig:
    """Take profit parameters."""
    tier1_rr: float = 4.0  # 1:4
    tier2_rr: float = 3.0  # 1:3
    tier3_rr: float = 2.0  # 1:2
    
    tier1_partial_at_r: float = 2.0  # Exit 50% at 2R
    tier2_partial_at_r: float = 1.5  # Exit 50% at 1.5R
    breakeven_at_r: float = 1.0


@dataclass
class TrailingConfig:
    """Trailing stop parameters."""
    method: str = 'chandelier'  # 'chandelier' or 'ema'
    atr_multiple: float = 2.0
    ema_period: int = 20


@dataclass
class PreTradeConfig:
    """Pre-trade validation parameters."""
    max_spread: float = 0.0005  # 0.05%
    max_slippage_atr: float = 0.05  # 5% of ATR
    max_latency_ms: int = 500


@dataclass
class NewsConfig:
    """Economic calendar and earnings parameters."""
    forex_red_flag_buffer_min: int = 30
    stocks_earnings_buffer_hours: int = 48
    skip_events: List[str] = None
    
    def __post_init__(self):
        if self.skip_events is None:
            self.skip_events = ['NFP', 'CPI', 'FOMC', 'ECB', 'BoE']


@dataclass  
class TimeframeConfig:
    """Asset-specific timeframes."""
    crypto_frames: List[str] = None
    forex_frames: List[str] = None
    stocks_frames: List[str] = None
    
    def __post_init__(self):
        if self.crypto_frames is None:
            self.crypto_frames = ['1h', '4h']
        if self.forex_frames is None:
            self.forex_frames = ['4h', '1d']
        if self.stocks_frames is None:
            self.stocks_frames = ['1d', '1w']


@dataclass
class SchedulerConfig:
    """Scanning schedule parameters."""
    scan_windows_utc: List[str] = None
    
    def __post_init__(self):
        if self.scan_windows_utc is None:
            self.scan_windows_utc = ['08:00', '13:00', '17:00', 'HourlyCrypto']


@dataclass
class ModularTradingBotConfig:
    """Master configuration schema."""
    # Targets
    targets: TradeTargets = None
    
    # Strategy parameters
    fibonacci: FibonacciConfig = None
    rsi: RSIConfig = None
    ema: EMAConfig = None
    volume: VolumeConfig = None
    atr: ATRConfig = None
    
    # Risk management
    risk: RiskConfig = None
    stops: StopsConfig = None
    targets_config: TargetsConfig = None
    trailing: TrailingConfig = None
    
    # Execution
    pre_trade: PreTradeConfig = None
    news: NewsConfig = None
    timeframes: TimeframeConfig = None
    scheduler: SchedulerConfig = None
    
    def __post_init__(self):
        if self.targets is None:
            self.targets = TradeTargets()
        if self.fibonacci is None:
            self.fibonacci = FibonacciConfig()
        if self.rsi is None:
            self.rsi = RSIConfig()
        if self.ema is None:
            self.ema = EMAConfig()
        if self.volume is None:
            self.volume = VolumeConfig()
        if self.atr is None:
            self.atr = ATRConfig()
        if self.risk is None:
            self.risk = RiskConfig()
        if self.stops is None:
            self.stops = StopsConfig()
        if self.targets_config is None:
            self.targets_config = TargetsConfig()
        if self.trailing is None:
            self.trailing = TrailingConfig()
        if self.pre_trade is None:
            self.pre_trade = PreTradeConfig()
        if self.news is None:
            self.news = NewsConfig()
        if self.timeframes is None:
            self.timeframes = TimeframeConfig()
        if self.scheduler is None:
            self.scheduler = SchedulerConfig()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'targets': self.targets.__dict__,
            'fibonacci': self.fibonacci.__dict__,
            'rsi': self.rsi.__dict__,
            'ema': self.ema.__dict__,
            'volume': self.volume.__dict__,
            'atr': self.atr.__dict__,
            'risk': self.risk.__dict__,
            'stops': self.stops.__dict__,
            'targets_config': self.targets_config.__dict__,
            'trailing': self.trailing.__dict__,
            'pre_trade': self.pre_trade.__dict__,
            'news': self.news.__dict__,
            'timeframes': self.timeframes.__dict__,
            'scheduler': self.scheduler.__dict__,
        }
    
    def validate(self) -> tuple:
        """Validate configuration parameters.
        
        Returns:
            (is_valid, errors_list) tuple
        """
        errors = []
        
        # Validate risk parameters
        if self.risk.tier1_pct <= self.risk.tier2_pct:
            errors.append('Tier 1 risk must be > Tier 2 risk')
        
        if self.risk.daily_max_loss > self.risk.weekly_max_loss:
            errors.append('Daily max loss must be <= weekly max loss')
        
        # Validate Fib parameters
        if self.fibonacci.primary_level not in self.fibonacci.levels:
            errors.append(f'Primary level {self.fibonacci.primary_level} not in levels')
        
        # Validate R:R ratios
        if self.targets_config.tier1_rr <= self.targets_config.tier2_rr:
            errors.append('Tier 1 R:R must be > Tier 2 R:R')
        
        return len(errors) == 0, errors


# Default production-ready configuration
DEFAULT_CONFIG = ModularTradingBotConfig()
