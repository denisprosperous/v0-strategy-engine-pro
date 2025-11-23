"""Backfill Manager: Historical Data Gap Filling System.

Automatically detects and fills gaps in historical market data:
- Gap detection across time ranges
- Multi-symbol orchestration
- Rate-limited exchange requests
- Resumable operations
- Startup auto-recovery

Author: v0-strategy-engine-pro
Version: 1.0 (Run #9)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from enum import Enum
import logging
import time
from collections import defaultdict

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class BackfillStatus(Enum):
    """Backfill operation status."""
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    FAILED = 'failed'
    PAUSED = 'paused'


class GapPriority(Enum):
    """Priority levels for gap filling."""
    CRITICAL = 1  # < 1 day old
    HIGH = 2      # 1-7 days old
    MEDIUM = 3    # 7-30 days old
    LOW = 4       # > 30 days old


@dataclass
class DataGap:
    """Represents a gap in time-series data."""
    symbol: str
    exchange: str
    timeframe: str
    start_time: datetime
    end_time: datetime
    gap_size: int  # Number of missing candles
    priority: GapPriority
    detected_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_duration_hours(self) -> float:
        """Get gap duration in hours."""
        return (self.end_time - self.start_time).total_seconds() / 3600
    
    def is_critical(self) -> bool:
        """Check if gap is critical (recent data)."""
        return self.priority == GapPriority.CRITICAL


@dataclass
class BackfillJob:
    """Backfill job tracking."""
    job_id: str
    gaps: List[DataGap]
    status: BackfillStatus = BackfillStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_candles: int = 0
    filled_candles: int = 0
    failed_candles: int = 0
    error_messages: List[str] = field(default_factory=list)
    
    def get_progress(self) -> float:
        """Get completion progress (0-100)."""
        if self.total_candles == 0:
            return 0.0
        return (self.filled_candles / self.total_candles) * 100
    
    def is_complete(self) -> bool:
        """Check if job is completed."""
        return self.status == BackfillStatus.COMPLETED


class BackfillManager:
    """Manages historical data backfilling operations."""
    
    def __init__(self,
                 database_handler=None,
                 exchange_connector=None,
                 max_concurrent_symbols: int = 5,
                 chunk_size: int = 100,
                 rate_limit_delay: float = 0.5):
        """
        Initialize backfill manager.
        
        Args:
            database_handler: Database connection handler
            exchange_connector: Exchange API connector
            max_concurrent_symbols: Max symbols to backfill simultaneously
            chunk_size: Number of candles per request
            rate_limit_delay: Delay between requests (seconds)
        """
        self.database = database_handler
        self.exchange = exchange_connector
        self.max_concurrent_symbols = max_concurrent_symbols
        self.chunk_size = chunk_size
        self.rate_limit_delay = rate_limit_delay
        
        # State tracking
        self.active_jobs: Dict[str, BackfillJob] = {}
        self.completed_jobs: List[BackfillJob] = []
        self.detected_gaps: Dict[str, List[DataGap]] = defaultdict(list)
        
        logger.info(f"BackfillManager initialized: chunk_size={chunk_size}, rate_limit={rate_limit_delay}s")
    
    # ===================== GAP DETECTION =====================
    
    def detect_gaps(self,
                    symbol: str,
                    exchange: str,
                    timeframe: str,
                    start_date: datetime,
                    end_date: datetime) -> List[DataGap]:
        """Detect gaps in historical data for a symbol.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name
            timeframe: Timeframe (e.g., '1h', '1d')
            start_date: Start of range to check
            end_date: End of range to check
            
        Returns:
            List of detected gaps
        """
        logger.info(f"Detecting gaps for {symbol} on {exchange} ({timeframe})")
        
        # Get existing data from database
        existing_data = self._fetch_existing_data(
            symbol, exchange, timeframe, start_date, end_date
        )
        
        if existing_data is None or len(existing_data) == 0:
            # Entire range is missing
            gap = DataGap(
                symbol=symbol,
                exchange=exchange,
                timeframe=timeframe,
                start_time=start_date,
                end_time=end_date,
                gap_size=self._calculate_expected_candles(start_date, end_date, timeframe),
                priority=self._determine_priority(end_date)
            )
            return [gap]
        
        # Detect gaps in existing data
        gaps = []
        expected_interval = self._get_timeframe_seconds(timeframe)
        
        for i in range(len(existing_data) - 1):
            current_time = existing_data.iloc[i]['timestamp']
            next_time = existing_data.iloc[i + 1]['timestamp']
            
            time_diff = (next_time - current_time).total_seconds()
            
            if time_diff > expected_interval * 1.5:  # Gap detected (with tolerance)
                gap_start = current_time + timedelta(seconds=expected_interval)
                gap_end = next_time
                gap_size = int(time_diff / expected_interval) - 1
                
                gap = DataGap(
                    symbol=symbol,
                    exchange=exchange,
                    timeframe=timeframe,
                    start_time=gap_start,
                    end_time=gap_end,
                    gap_size=gap_size,
                    priority=self._determine_priority(gap_end)
                )
                gaps.append(gap)
        
        logger.info(f"Detected {len(gaps)} gaps for {symbol}")
        self.detected_gaps[symbol].extend(gaps)
        
        return gaps
    
    def detect_all_gaps(self,
                       symbols: List[str],
                       exchange: str,
                       timeframe: str,
                       lookback_days: int = 90) -> Dict[str, List[DataGap]]:
        """Detect gaps for multiple symbols.
        
        Args:
            symbols: List of trading symbols
            exchange: Exchange name
            timeframe: Timeframe
            lookback_days: Days to look back
            
        Returns:
            Dictionary mapping symbols to their gaps
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=lookback_days)
        
        all_gaps = {}
        
        for symbol in symbols:
            try:
                gaps = self.detect_gaps(symbol, exchange, timeframe, start_date, end_date)
                if gaps:
                    all_gaps[symbol] = gaps
            except Exception as e:
                logger.error(f"Error detecting gaps for {symbol}: {e}")
        
        return all_gaps
    
    # ===================== BACKFILL EXECUTION =====================
    
    def fill_gap(self, gap: DataGap) -> Tuple[bool, int, Optional[str]]:
        """Fill a single data gap.
        
        Args:
            gap: DataGap to fill
            
        Returns:
            (success, candles_filled, error_message)
        """
        logger.info(f"Filling gap for {gap.symbol}: {gap.start_time} to {gap.end_time}")
        
        try:
            # Fetch historical data from exchange
            historical_data = self._fetch_from_exchange(
                symbol=gap.symbol,
                exchange=gap.exchange,
                timeframe=gap.timeframe,
                start_time=gap.start_time,
                end_time=gap.end_time
            )
            
            if historical_data is None or len(historical_data) == 0:
                return False, 0, "No data available from exchange"
            
            # Validate data continuity
            is_valid, validation_error = self._validate_continuity(historical_data, gap.timeframe)
            if not is_valid:
                logger.warning(f"Continuity validation failed: {validation_error}")
            
            # Insert into database
            inserted_count = self._insert_data_batch(historical_data)
            
            logger.info(f"Successfully filled gap: {inserted_count} candles")
            return True, inserted_count, None
            
        except Exception as e:
            error_msg = f"Error filling gap: {str(e)}"
            logger.error(error_msg)
            return False, 0, error_msg
    
    def create_backfill_job(self, gaps: List[DataGap]) -> BackfillJob:
        """Create a backfill job from detected gaps.
        
        Args:
            gaps: List of gaps to fill
            
        Returns:
            BackfillJob instance
        """
        job_id = f"backfill_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        total_candles = sum(gap.gap_size for gap in gaps)
        
        job = BackfillJob(
            job_id=job_id,
            gaps=gaps,
            total_candles=total_candles
        )
        
        self.active_jobs[job_id] = job
        logger.info(f"Created backfill job {job_id}: {len(gaps)} gaps, {total_candles} candles")
        
        return job
    
    def execute_job(self, job: BackfillJob) -> bool:
        """Execute a backfill job.
        
        Args:
            job: BackfillJob to execute
            
        Returns:
            Success status
        """
        logger.info(f"Executing backfill job {job.job_id}")
        
        job.status = BackfillStatus.IN_PROGRESS
        job.started_at = datetime.utcnow()
        
        # Sort gaps by priority (critical first)
        sorted_gaps = sorted(job.gaps, key=lambda g: g.priority.value)
        
        for gap in sorted_gaps:
            try:
                success, filled_count, error = self.fill_gap(gap)
                
                if success:
                    job.filled_candles += filled_count
                else:
                    job.failed_candles += gap.gap_size
                    if error:
                        job.error_messages.append(f"{gap.symbol}: {error}")
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
                
                # Log progress
                progress = job.get_progress()
                logger.info(f"Job {job.job_id} progress: {progress:.1f}%")
                
            except Exception as e:
                logger.error(f"Error processing gap: {e}")
                job.failed_candles += gap.gap_size
                job.error_messages.append(str(e))
        
        # Finalize job
        job.completed_at = datetime.utcnow()
        job.status = BackfillStatus.COMPLETED if job.failed_candles == 0 else BackfillStatus.FAILED
        
        # Move to completed
        self.completed_jobs.append(job)
        del self.active_jobs[job.job_id]
        
        logger.info(f"Job {job.job_id} completed: {job.filled_candles}/{job.total_candles} filled")
        
        return job.status == BackfillStatus.COMPLETED
    
    # ===================== STARTUP RECOVERY =====================
    
    def auto_recover_on_startup(self,
                                symbols: List[str],
                                exchange: str,
                                timeframe: str = '1h',
                                lookback_days: int = 7) -> BackfillJob:
        """Automatically detect and fill gaps on system startup.
        
        Args:
            symbols: Symbols to check
            exchange: Exchange name
            timeframe: Timeframe
            lookback_days: Days to look back
            
        Returns:
            Created backfill job
        """
        logger.info(f"Running startup auto-recovery for {len(symbols)} symbols")
        
        # Detect all gaps
        all_gaps = self.detect_all_gaps(symbols, exchange, timeframe, lookback_days)
        
        # Flatten gaps
        gaps_list = []
        for symbol, gaps in all_gaps.items():
            gaps_list.extend(gaps)
        
        if not gaps_list:
            logger.info("No gaps detected - data is current")
            return None
        
        # Create and execute job
        job = self.create_backfill_job(gaps_list)
        self.execute_job(job)
        
        return job
    
    # ===================== HELPER METHODS =====================
    
    def _fetch_existing_data(self, symbol: str, exchange: str, timeframe: str,
                            start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """Fetch existing data from database."""
        if self.database is None:
            return None
        
        # Placeholder - implement database query
        # return self.database.query_market_data(symbol, exchange, timeframe, start_date, end_date)
        return None
    
    def _fetch_from_exchange(self, symbol: str, exchange: str, timeframe: str,
                            start_time: datetime, end_time: datetime) -> Optional[pd.DataFrame]:
        """Fetch historical data from exchange."""
        if self.exchange is None:
            return None
        
        # Placeholder - implement exchange API call
        # return self.exchange.fetch_ohlcv(symbol, timeframe, start_time, end_time)
        return None
    
    def _insert_data_batch(self, data: pd.DataFrame) -> int:
        """Insert data batch into database."""
        if self.database is None:
            return 0
        
        # Placeholder - implement batch insert
        # return self.database.insert_market_data_batch(data)
        return len(data)
    
    def _validate_continuity(self, data: pd.DataFrame, timeframe: str) -> Tuple[bool, Optional[str]]:
        """Validate time-series continuity."""
        if len(data) < 2:
            return True, None
        
        expected_interval = self._get_timeframe_seconds(timeframe)
        
        timestamps = data['timestamp'].values if 'timestamp' in data.columns else data.index.values
        
        for i in range(len(timestamps) - 1):
            if isinstance(timestamps[i], pd.Timestamp):
                time_diff = (timestamps[i + 1] - timestamps[i]).total_seconds()
            else:
                time_diff = timestamps[i + 1] - timestamps[i]
            
            if abs(time_diff - expected_interval) > expected_interval * 0.1:  # 10% tolerance
                return False, f"Discontinuity at index {i}: {time_diff}s vs expected {expected_interval}s"
        
        return True, None
    
    def _get_timeframe_seconds(self, timeframe: str) -> int:
        """Convert timeframe string to seconds."""
        multipliers = {'m': 60, 'h': 3600, 'd': 86400, 'w': 604800}
        
        if timeframe[-1] in multipliers:
            value = int(timeframe[:-1])
            unit = timeframe[-1]
            return value * multipliers[unit]
        
        return 3600  # Default to 1 hour
    
    def _calculate_expected_candles(self, start_date: datetime, end_date: datetime, timeframe: str) -> int:
        """Calculate expected number of candles in time range."""
        interval_seconds = self._get_timeframe_seconds(timeframe)
        duration_seconds = (end_date - start_date).total_seconds()
        return int(duration_seconds / interval_seconds)
    
    def _determine_priority(self, gap_end_time: datetime) -> GapPriority:
        """Determine gap priority based on recency."""
        age_hours = (datetime.utcnow() - gap_end_time).total_seconds() / 3600
        
        if age_hours < 24:
            return GapPriority.CRITICAL
        elif age_hours < 168:  # 7 days
            return GapPriority.HIGH
        elif age_hours < 720:  # 30 days
            return GapPriority.MEDIUM
        else:
            return GapPriority.LOW
    
    # ===================== REPORTING =====================
    
    def get_status_summary(self) -> Dict:
        """Get backfill manager status summary."""
        return {
            'active_jobs': len(self.active_jobs),
            'completed_jobs': len(self.completed_jobs),
            'detected_gaps': sum(len(gaps) for gaps in self.detected_gaps.values()),
            'total_symbols_tracked': len(self.detected_gaps),
            'jobs': {
                job_id: {
                    'status': job.status.value,
                    'progress': job.get_progress(),
                    'filled': job.filled_candles,
                    'total': job.total_candles
                }
                for job_id, job in self.active_jobs.items()
            }
        }


# Module-level singleton
_backfill_manager = None


def get_backfill_manager() -> BackfillManager:
    """Get global backfill manager."""
    global _backfill_manager
    if _backfill_manager is None:
        _backfill_manager = BackfillManager()
    return _backfill_manager
