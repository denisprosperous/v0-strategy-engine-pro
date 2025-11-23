"""Integration Tests for IntegratedExecutionEngine.

Tests the complete signal-to-trade pipeline with all modules:
- Fibonacci Engine integration
- Signal Validator integration
- Smart Scheduler integration
- Signal Scorer integration
- Execution and trade management

Author: v0-strategy-engine-pro
Version: 1.0 (Run #8)
"""

import pytest
import numpy as np
from datetime import datetime
from signal_generation.execution_engine_integrated import (
    IntegratedExecutionEngine,
    TradingSignal,
    SignalDirection,
    ExecutedTrade,
    OrderStatus
)


@pytest.fixture
def engine():
    """Create execution engine instance."""
    return IntegratedExecutionEngine(
        base_position_size=1000.0,
        max_spread=0.0005,
        max_latency_ms=500
    )


@pytest.fixture
def sample_ohlc():
    """Create sample OHLC data."""
    # [timestamp, high, low, close, volume]
    data = np.zeros((50, 5))
    
    # Generate realistic price data
    base_price = 50000.0
    for i in range(50):
        data[i, 0] = datetime.utcnow().timestamp() - (50-i)*60  # timestamps
        data[i, 1] = base_price + np.random.uniform(0, 200)  # high
        data[i, 2] = base_price - np.random.uniform(0, 200)  # low
        data[i, 3] = base_price + np.random.uniform(-100, 100)  # close
        data[i, 4] = np.random.uniform(100, 1000)  # volume
        base_price += np.random.uniform(-50, 50)
    
    return data


@pytest.fixture
def sample_market_data():
    """Create sample market data."""
    return {
        'rsi': 65.0,
        'ema_20': 49800.0,
        'ema_50': 49500.0,
        'ema_200': 48000.0,
        'atr': 500.0,
        'volume_ratio': 1.5,
        'volatility_regime': 'MEDIUM',
        'trend': 'UPTREND',
        'historical_win_rate': 0.70
    }


class TestPreFlightValidation:
    """Test pre-flight module validation."""
    
    def test_preflight_check_all_modules(self, engine):
        """Test all modules are initialized."""
        success, errors = engine.pre_flight_check()
        
        assert success is True
        assert len(errors) == 0
    
    def test_module_initialization(self, engine):
        """Test individual modules are initialized."""
        assert engine.fibonacci_engine is not None
        assert engine.signal_validator is not None
        assert engine.smart_scheduler is not None
        assert engine.signal_scorer is not None
    
    def test_trading_parameters(self, engine):
        """Test trading parameters are set."""
        assert engine.base_position_size == 1000.0
        assert engine.max_spread == 0.0005
        assert engine.max_latency_ms == 500


class TestSignalPipeline:
    """Test complete signal generation pipeline."""
    
    def test_pipeline_with_valid_signal(self, engine, sample_ohlc, sample_market_data):
        """Test pipeline generates signal with valid conditions."""
        # This may or may not generate a signal depending on Fibonacci detection
        signal = engine.generate_signal(
            symbol='BTCUSDT',
            ohlc_data=sample_ohlc,
            market_data=sample_market_data
        )
        
        # If signal generated, validate structure
        if signal is not None:
            assert isinstance(signal, TradingSignal)
            assert signal.symbol == 'BTCUSDT'
            assert signal.direction == SignalDirection.LONG
            assert signal.entry_price > 0
            assert signal.stop_loss < signal.entry_price
            assert signal.take_profit_1 > signal.entry_price
            assert signal.take_profit_2 > signal.take_profit_1
            assert 0 <= signal.confidence <= 1.0
            assert 0 <= signal.score <= 100
    
    def test_pipeline_fibonacci_detection(self, engine, sample_ohlc, sample_market_data):
        """Test Fibonacci detection in pipeline."""
        # Call Fibonacci engine directly
        fib_signal = engine.fibonacci_engine.get_signal(sample_ohlc, direction='long')
        
        # Fibonacci may or may not detect (depends on price position)
        # Just verify it doesn't crash
        assert fib_signal is None or isinstance(fib_signal, dict)
    
    def test_pipeline_validation_step(self, engine, sample_market_data):
        """Test signal validation step."""
        # Create mock signal
        mock_signal = {
            'strategy': 'test',
            'current_price': 50000.0,
            'confidence': 0.8
        }
        
        validation_result = engine.signal_validator.validate_signal(
            signal_data=mock_signal,
            market_data=sample_market_data
        )
        
        assert hasattr(validation_result, 'is_valid')
        assert hasattr(validation_result, 'confidence')
    
    def test_pipeline_scoring_step(self, engine, sample_market_data):
        """Test signal scoring step."""
        score_result = engine.signal_scorer.score_signal(
            signal_type='LONG',
            entry_price=50000.0,
            market_data=sample_market_data,
            fib_levels={}
        )
        
        assert hasattr(score_result, 'overall_score')
        assert hasattr(score_result, 'execution_tier')
        assert hasattr(score_result, 'confidence_level')
        assert 0 <= score_result.overall_score <= 100


class TestExecutionTiers:
    """Test execution tier-based position sizing."""
    
    def test_full_tier_position_sizing(self, engine):
        """Test FULL tier uses 100% position size."""
        signal = TradingSignal(
            symbol='BTCUSDT',
            direction=SignalDirection.LONG,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit_1=51000.0,
            take_profit_2=52000.0,
            execution_tier='FULL',
            confidence=0.9,
            score=85.0
        )
        
        success, error, trade = engine.execute_signal(signal)
        
        if success:
            assert trade.quantity == 1000.0  # 100% of base
    
    def test_reduced_tier_position_sizing(self, engine):
        """Test REDUCED tier uses 65% position size."""
        signal = TradingSignal(
            symbol='BTCUSDT',
            direction=SignalDirection.LONG,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit_1=51000.0,
            take_profit_2=52000.0,
            execution_tier='REDUCED',
            confidence=0.7,
            score=65.0
        )
        
        success, error, trade = engine.execute_signal(signal)
        
        if success:
            assert trade.quantity == 650.0  # 65% of base
    
    def test_skip_tier_no_execution(self, engine):
        """Test SKIP tier prevents execution."""
        signal = TradingSignal(
            symbol='BTCUSDT',
            direction=SignalDirection.LONG,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit_1=51000.0,
            take_profit_2=52000.0,
            execution_tier='SKIP',
            confidence=0.4,
            score=45.0
        )
        
        success, error, trade = engine.execute_signal(signal)
        
        assert success is False
        assert 'SKIP' in error
        assert trade is None


class TestTradeExecution:
    """Test trade execution functionality."""
    
    def test_execute_valid_signal(self, engine):
        """Test executing a valid signal."""
        signal = TradingSignal(
            symbol='ETHUSDT',
            direction=SignalDirection.LONG,
            entry_price=3000.0,
            stop_loss=2900.0,
            take_profit_1=3100.0,
            take_profit_2=3200.0,
            execution_tier='FULL',
            confidence=0.85,
            score=80.0
        )
        
        success, error, trade = engine.execute_signal(signal)
        
        assert success is True
        assert error is None
        assert trade is not None
        assert trade.symbol == 'ETHUSDT'
        assert trade.direction == 'long'
        assert trade.entry_price == 3000.0
    
    def test_trade_tracking(self, engine):
        """Test trades are tracked in open_trades."""
        signal = TradingSignal(
            symbol='SOLUSDT',
            direction=SignalDirection.LONG,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit_1=105.0,
            take_profit_2=110.0,
            execution_tier='FULL',
            confidence=0.8,
            score=75.0
        )
        
        engine.execute_signal(signal)
        
        assert 'SOLUSDT' in engine.open_trades
        assert len(engine.trade_history) > 0


class TestTradeManagement:
    """Test trade management functionality."""
    
    def test_pnl_update(self, engine):
        """Test P&L updates with price changes."""
        # Create and execute trade
        signal = TradingSignal(
            symbol='BTCUSDT',
            direction=SignalDirection.LONG,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit_1=51000.0,
            take_profit_2=52000.0,
            execution_tier='FULL',
            confidence=0.85,
            score=80.0
        )
        
        success, _, trade = engine.execute_signal(signal)
        
        if success:
            # Update with profitable price
            engine.update_trades({'BTCUSDT': 50500.0})
            
            trade = engine.open_trades['BTCUSDT']
            assert trade.current_price == 50500.0
            assert trade.current_pnl > 0
            assert trade.current_pnl_pct > 0
    
    def test_partial_exit_tp1(self, engine):
        """Test partial exit at TP1."""
        signal = TradingSignal(
            symbol='ETHUSDT',
            direction=SignalDirection.LONG,
            entry_price=3000.0,
            stop_loss=2900.0,
            take_profit_1=3100.0,
            take_profit_2=3200.0,
            execution_tier='FULL',
            confidence=0.85,
            score=80.0
        )
        
        success, _, _ = engine.execute_signal(signal)
        
        if success:
            # Price reaches TP1
            engine.update_trades({'ETHUSDT': 3100.0})
            
            trade = engine.open_trades.get('ETHUSDT')
            if trade:
                assert trade.partial_1_taken is True
    
    def test_full_exit_tp2(self, engine):
        """Test full exit at TP2."""
        signal = TradingSignal(
            symbol='SOLUSDT',
            direction=SignalDirection.LONG,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit_1=105.0,
            take_profit_2=110.0,
            execution_tier='FULL',
            confidence=0.85,
            score=80.0
        )
        
        success, _, _ = engine.execute_signal(signal)
        
        if success:
            # Price reaches TP2
            engine.update_trades({'SOLUSDT': 110.0})
            
            # Trade should be closed
            assert 'SOLUSDT' not in engine.open_trades
            assert len(engine.closed_trades) > 0
    
    def test_stop_loss_execution(self, engine):
        """Test stop loss execution."""
        signal = TradingSignal(
            symbol='ADAUSDT',
            direction=SignalDirection.LONG,
            entry_price=0.50,
            stop_loss=0.48,
            take_profit_1=0.52,
            take_profit_2=0.54,
            execution_tier='FULL',
            confidence=0.85,
            score=80.0
        )
        
        success, _, _ = engine.execute_signal(signal)
        
        if success:
            # Price hits stop loss
            engine.update_trades({'ADAUSDT': 0.48})
            
            # Trade should be closed
            assert 'ADAUSDT' not in engine.open_trades
            
            # Check closed trade
            if engine.closed_trades:
                closed = engine.closed_trades[-1]
                assert closed.exit_reason == 'sl'


class TestReporting:
    """Test reporting and summary functions."""
    
    def test_summary_generation(self, engine):
        """Test summary report generation."""
        summary = engine.get_summary()
        
        assert 'open_trades' in summary
        assert 'closed_trades' in summary
        assert 'total_open_pnl' in summary
        assert 'avg_pnl_pct' in summary
        assert 'modules_active' in summary
    
    def test_modules_active_status(self, engine):
        """Test module active status reporting."""
        summary = engine.get_summary()
        
        modules = summary['modules_active']
        assert modules['fibonacci'] is True
        assert modules['validator'] is True
        assert modules['scheduler'] is True
        assert modules['scorer'] is True
    
    def test_summary_with_open_trades(self, engine):
        """Test summary with active trades."""
        signal = TradingSignal(
            symbol='BTCUSDT',
            direction=SignalDirection.LONG,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit_1=51000.0,
            take_profit_2=52000.0,
            execution_tier='FULL',
            confidence=0.85,
            score=80.0
        )
        
        success, _, _ = engine.execute_signal(signal)
        
        if success:
            # Update price
            engine.update_trades({'BTCUSDT': 50500.0})
            
            summary = engine.get_summary()
            assert summary['open_trades'] >= 1
            assert summary['total_open_pnl'] != 0


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_symbol_update(self, engine):
        """Test updating non-existent symbol."""
        # Should not crash
        engine.update_trades({'INVALID': 100.0})
        assert True
    
    def test_empty_ohlc_handling(self, engine, sample_market_data):
        """Test handling empty OHLC data."""
        empty_ohlc = np.array([]).reshape(0, 5)
        
        # Should handle gracefully
        signal = engine.generate_signal(
            symbol='BTCUSDT',
            ohlc_data=empty_ohlc,
            market_data=sample_market_data
        )
        
        # Likely returns None, but shouldn't crash
        assert signal is None or isinstance(signal, TradingSignal)
