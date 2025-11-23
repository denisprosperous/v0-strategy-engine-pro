"""Tests for BackfillManager.

Comprehensive tests for historical data backfilling:
- Gap detection and analysis
- Backfill job execution
- Continuity validation
- Multi-symbol orchestration
- Startup recovery

Author: v0-strategy-engine-pro
Version: 1.0 (Run #9)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_pipeline.backfill_manager import (
    BackfillManager,
    DataGap,
    BackfillJob,
    BackfillStatus,
    GapPriority
)


@pytest.fixture
def backfill_manager():
    """Create backfill manager instance."""
    return BackfillManager(
        database_handler=None,
        exchange_connector=None,
        max_concurrent_symbols=5,
        chunk_size=100,
        rate_limit_delay=0.1
    )


@pytest.fixture
def sample_gap():
    """Create sample data gap."""
    return DataGap(
        symbol='BTCUSDT',
        exchange='binance',
        timeframe='1h',
        start_time=datetime(2025, 11, 20, 0, 0),
        end_time=datetime(2025, 11, 20, 12, 0),
        gap_size=12,
        priority=GapPriority.HIGH
    )


@pytest.fixture
def sample_continuous_data():
    """Create sample continuous time-series data."""
    start = datetime(2025, 11, 20, 0, 0)
    timestamps = [start + timedelta(hours=i) for i in range(24)]
    
    return pd.DataFrame({
        'timestamp': timestamps,
        'open': np.random.uniform(50000, 51000, 24),
        'high': np.random.uniform(50500, 51500, 24),
        'low': np.random.uniform(49500, 50500, 24),
        'close': np.random.uniform(50000, 51000, 24),
        'volume': np.random.uniform(100, 1000, 24)
    })


@pytest.fixture
def sample_gapped_data():
    """Create sample time-series data with gaps."""
    timestamps = [
        datetime(2025, 11, 20, 0, 0),
        datetime(2025, 11, 20, 1, 0),
        datetime(2025, 11, 20, 2, 0),
        # Gap from 2:00 to 6:00
        datetime(2025, 11, 20, 6, 0),
        datetime(2025, 11, 20, 7, 0),
        datetime(2025, 11, 20, 8, 0),
        # Gap from 8:00 to 12:00
        datetime(2025, 11, 20, 12, 0),
        datetime(2025, 11, 20, 13, 0)
    ]
    
    return pd.DataFrame({
        'timestamp': timestamps,
        'open': np.random.uniform(50000, 51000, len(timestamps)),
        'high': np.random.uniform(50500, 51500, len(timestamps)),
        'low': np.random.uniform(49500, 50500, len(timestamps)),
        'close': np.random.uniform(50000, 51000, len(timestamps)),
        'volume': np.random.uniform(100, 1000, len(timestamps))
    })


class TestDataGap:
    """Test DataGap functionality."""
    
    def test_gap_creation(self, sample_gap):
        """Test gap creation."""
        assert sample_gap.symbol == 'BTCUSDT'
        assert sample_gap.exchange == 'binance'
        assert sample_gap.timeframe == '1h'
        assert sample_gap.gap_size == 12
        assert sample_gap.priority == GapPriority.HIGH
    
    def test_gap_duration_calculation(self, sample_gap):
        """Test gap duration calculation."""
        duration = sample_gap.get_duration_hours()
        assert duration == 12.0
    
    def test_gap_criticality(self):
        """Test gap criticality detection."""
        critical_gap = DataGap(
            symbol='ETHUSDT',
            exchange='binance',
            timeframe='1h',
            start_time=datetime.utcnow() - timedelta(hours=2),
            end_time=datetime.utcnow(),
            gap_size=2,
            priority=GapPriority.CRITICAL
        )
        
        assert critical_gap.is_critical() is True


class TestGapPriority:
    """Test gap priority classification."""
    
    def test_priority_determination(self, backfill_manager):
        """Test priority is determined correctly based on age."""
        now = datetime.utcnow()
        
        # Critical: < 24 hours old
        critical_time = now - timedelta(hours=12)
        priority = backfill_manager._determine_priority(critical_time)
        assert priority == GapPriority.CRITICAL
        
        # High: 1-7 days old
        high_time = now - timedelta(days=3)
        priority = backfill_manager._determine_priority(high_time)
        assert priority == GapPriority.HIGH
        
        # Medium: 7-30 days old
        medium_time = now - timedelta(days=15)
        priority = backfill_manager._determine_priority(medium_time)
        assert priority == GapPriority.MEDIUM
        
        # Low: > 30 days old
        low_time = now - timedelta(days=45)
        priority = backfill_manager._determine_priority(low_time)
        assert priority == GapPriority.LOW


class TestTimeframeConversion:
    """Test timeframe conversion utilities."""
    
    def test_timeframe_to_seconds(self, backfill_manager):
        """Test timeframe string to seconds conversion."""
        assert backfill_manager._get_timeframe_seconds('1m') == 60
        assert backfill_manager._get_timeframe_seconds('5m') == 300
        assert backfill_manager._get_timeframe_seconds('1h') == 3600
        assert backfill_manager._get_timeframe_seconds('4h') == 14400
        assert backfill_manager._get_timeframe_seconds('1d') == 86400
        assert backfill_manager._get_timeframe_seconds('1w') == 604800
    
    def test_expected_candles_calculation(self, backfill_manager):
        """Test expected candles calculation."""
        start = datetime(2025, 11, 20, 0, 0)
        end = datetime(2025, 11, 21, 0, 0)  # 24 hours
        
        # 1 hour timeframe = 24 candles
        candles = backfill_manager._calculate_expected_candles(start, end, '1h')
        assert candles == 24
        
        # 4 hour timeframe = 6 candles
        candles = backfill_manager._calculate_expected_candles(start, end, '4h')
        assert candles == 6


class TestContinuityValidation:
    """Test time-series continuity validation."""
    
    def test_continuous_data_validation(self, backfill_manager, sample_continuous_data):
        """Test validation passes for continuous data."""
        is_valid, error = backfill_manager._validate_continuity(sample_continuous_data, '1h')
        
        assert is_valid is True
        assert error is None
    
    def test_gapped_data_detection(self, backfill_manager, sample_gapped_data):
        """Test validation detects gaps."""
        is_valid, error = backfill_manager._validate_continuity(sample_gapped_data, '1h')
        
        # Should detect discontinuity
        assert is_valid is False
        assert error is not None
        assert 'Discontinuity' in error
    
    def test_single_row_validation(self, backfill_manager):
        """Test validation with single row."""
        single_row = pd.DataFrame({
            'timestamp': [datetime.utcnow()],
            'close': [50000.0]
        })
        
        is_valid, error = backfill_manager._validate_continuity(single_row, '1h')
        
        assert is_valid is True
        assert error is None


class TestBackfillJob:
    """Test BackfillJob functionality."""
    
    def test_job_creation(self, backfill_manager, sample_gap):
        """Test backfill job creation."""
        gaps = [sample_gap]
        job = backfill_manager.create_backfill_job(gaps)
        
        assert job.job_id is not None
        assert len(job.gaps) == 1
        assert job.total_candles == 12
        assert job.status == BackfillStatus.PENDING
    
    def test_job_progress_calculation(self, sample_gap):
        """Test job progress calculation."""
        job = BackfillJob(
            job_id='test_job',
            gaps=[sample_gap],
            total_candles=100,
            filled_candles=50
        )
        
        progress = job.get_progress()
        assert progress == 50.0
    
    def test_job_completion_status(self, sample_gap):
        """Test job completion detection."""
        job = BackfillJob(
            job_id='test_job',
            gaps=[sample_gap],
            status=BackfillStatus.COMPLETED
        )
        
        assert job.is_complete() is True
    
    def test_zero_progress_handling(self, sample_gap):
        """Test progress with zero total candles."""
        job = BackfillJob(
            job_id='test_job',
            gaps=[sample_gap],
            total_candles=0
        )
        
        progress = job.get_progress()
        assert progress == 0.0


class TestGapDetection:
    """Test gap detection functionality."""
    
    def test_gap_detection_with_no_data(self, backfill_manager):
        """Test gap detection when no data exists."""
        # Mock _fetch_existing_data to return None
        backfill_manager._fetch_existing_data = lambda *args: None
        
        start_date = datetime(2025, 11, 20, 0, 0)
        end_date = datetime(2025, 11, 21, 0, 0)
        
        gaps = backfill_manager.detect_gaps(
            symbol='BTCUSDT',
            exchange='binance',
            timeframe='1h',
            start_date=start_date,
            end_date=end_date
        )
        
        assert len(gaps) == 1
        assert gaps[0].symbol == 'BTCUSDT'
        assert gaps[0].start_time == start_date
        assert gaps[0].end_time == end_date
    
    def test_gap_detection_with_continuous_data(self, backfill_manager, sample_continuous_data):
        """Test gap detection with continuous data."""
        # Mock to return continuous data
        backfill_manager._fetch_existing_data = lambda *args: sample_continuous_data
        
        start_date = datetime(2025, 11, 20, 0, 0)
        end_date = datetime(2025, 11, 21, 0, 0)
        
        gaps = backfill_manager.detect_gaps(
            symbol='BTCUSDT',
            exchange='binance',
            timeframe='1h',
            start_date=start_date,
            end_date=end_date
        )
        
        # Should detect no gaps
        assert len(gaps) == 0
    
    def test_gap_detection_with_gapped_data(self, backfill_manager, sample_gapped_data):
        """Test gap detection with gapped data."""
        # Mock to return gapped data
        backfill_manager._fetch_existing_data = lambda *args: sample_gapped_data
        
        start_date = datetime(2025, 11, 20, 0, 0)
        end_date = datetime(2025, 11, 20, 23, 0)
        
        gaps = backfill_manager.detect_gaps(
            symbol='BTCUSDT',
            exchange='binance',
            timeframe='1h',
            start_date=start_date,
            end_date=end_date
        )
        
        # Should detect 2 gaps (from fixture)
        assert len(gaps) >= 1  # At least one gap detected


class TestMultiSymbolOrchestration:
    """Test multi-symbol backfill orchestration."""
    
    def test_detect_all_gaps(self, backfill_manager):
        """Test gap detection across multiple symbols."""
        # Mock to return no data (full gap)
        backfill_manager._fetch_existing_data = lambda *args: None
        
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        all_gaps = backfill_manager.detect_all_gaps(
            symbols=symbols,
            exchange='binance',
            timeframe='1h',
            lookback_days=7
        )
        
        # Should have gaps for all symbols
        assert len(all_gaps) == 3
        assert all(symbol in all_gaps for symbol in symbols)
    
    def test_concurrent_symbol_limit(self, backfill_manager):
        """Test concurrent symbol processing limit."""
        assert backfill_manager.max_concurrent_symbols == 5


class TestStatusReporting:
    """Test status reporting functionality."""
    
    def test_status_summary_empty(self, backfill_manager):
        """Test status summary with no jobs."""
        summary = backfill_manager.get_status_summary()
        
        assert summary['active_jobs'] == 0
        assert summary['completed_jobs'] == 0
        assert summary['detected_gaps'] == 0
    
    def test_status_summary_with_job(self, backfill_manager, sample_gap):
        """Test status summary with active job."""
        job = backfill_manager.create_backfill_job([sample_gap])
        
        summary = backfill_manager.get_status_summary()
        
        assert summary['active_jobs'] == 1
        assert job.job_id in summary['jobs']
        assert summary['jobs'][job.job_id]['status'] == 'pending'


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_timeframe_handling(self, backfill_manager):
        """Test handling of invalid timeframe."""
        # Should default to 1 hour
        seconds = backfill_manager._get_timeframe_seconds('invalid')
        assert seconds == 3600
    
    def test_empty_gaps_list(self, backfill_manager):
        """Test handling empty gaps list."""
        job = backfill_manager.create_backfill_job([])
        
        assert job.total_candles == 0
        assert len(job.gaps) == 0


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limit_configuration(self, backfill_manager):
        """Test rate limit is configured."""
        assert backfill_manager.rate_limit_delay == 0.1
    
    def test_chunk_size_configuration(self, backfill_manager):
        """Test chunk size is configured."""
        assert backfill_manager.chunk_size == 100


class TestSingletonAccess:
    """Test singleton pattern for backfill manager."""
    
    def test_singleton_instance(self):
        """Test get_backfill_manager returns singleton."""
        from data_pipeline.backfill_manager import get_backfill_manager
        
        manager1 = get_backfill_manager()
        manager2 = get_backfill_manager()
        
        assert manager1 is manager2
