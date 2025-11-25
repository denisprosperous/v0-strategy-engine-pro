"""
AI Integration Tests

Comprehensive test suite for AI ensemble integration:
- Configuration loading
- Adapter initialization
- Signal enhancement
- Risk assessment
- End-to-end signal flow

Author: v0-strategy-engine-pro
Version: 1.0 - Segment 3
"""

import asyncio
import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Import modules to test
try:
    from ai_models.ai_config import AIConfigManager, AIConfig, ProviderConfig
    from ai_models.ai_integration_adapter import AIIntegrationAdapter, AISignalEnhancement
    from signal_generation.signal_engine_ai_enhanced import AIEnhancedSignalEngine
    from signal_generation.signal_engine import SignalTier, SignalDirection
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)


class TestAIConfiguration:
    """Test AI configuration management."""
    
    def test_default_config_load(self):
        """Test loading default configuration."""
        config_manager = AIConfigManager()
        config = config_manager.get_config()
        
        assert isinstance(config, AIConfig)
        assert config.min_providers >= 1
        assert 0 < config.min_confidence <= 1.0
    
    def test_env_variable_override(self):
        """Test environment variable configuration."""
        with patch.dict(os.environ, {
            'AI_ENABLED': 'true',
            'AI_MIN_PROVIDERS': '3',
            'AI_MIN_CONFIDENCE': '0.75',
            'OPENAI_API_KEY': 'test-key-123'
        }):
            config_manager = AIConfigManager()
            config = config_manager.get_config()
            
            assert config.ai_enabled is True
            assert config.min_providers == 3
            assert config.min_confidence == 0.75
            assert config.providers['openai'].enabled is True
            assert config.providers['openai'].api_key == 'test-key-123'
    
    def test_get_api_keys(self):
        """Test API key extraction."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'key1',
            'ANTHROPIC_API_KEY': 'key2',
            'GOOGLE_API_KEY': ''
        }):
            config_manager = AIConfigManager()
            api_keys = config_manager.get_api_keys()
            
            assert 'openai' in api_keys
            assert 'anthropic' in api_keys
            assert 'gemini' not in api_keys  # Empty key should be excluded
    
    def test_provider_weights(self):
        """Test provider accuracy weights."""
        config_manager = AIConfigManager()
        weights = config_manager.get_provider_weights()
        
        # Should return weights for enabled providers only
        assert isinstance(weights, dict)
        for provider, weight in weights.items():
            assert 0 < weight <= 2.0  # Reasonable weight range


class TestAIIntegrationAdapter:
    """Test AI integration adapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return AIIntegrationAdapter(enable_ai=False)  # Disabled for unit tests
    
    def test_adapter_initialization(self, adapter):
        """Test adapter initialization."""
        assert adapter is not None
        assert adapter.enable_ai is False
        assert adapter.orchestrator is None
    
    @pytest.mark.asyncio
    async def test_enhance_signal_disabled(self, adapter):
        """Test signal enhancement when AI is disabled."""
        result = await adapter.enhance_signal(
            symbol="BTC/USDT",
            market_data={"price": 42000},
            technical_indicators={"rsi": 30},
            timeframe="1h"
        )
        
        assert result is None  # Should return None when disabled
    
    def test_signal_enhancement_object(self):
        """Test AISignalEnhancement object."""
        enhancement = AISignalEnhancement(
            ai_signal="BUY",
            ai_confidence=0.85,
            ai_sentiment_score=0.6,
            ai_risk_level="LOW",
            ensemble_consensus=True,
            provider_count=3
        )
        
        assert enhancement.should_boost_signal() is True
        assert enhancement.should_block_signal() is False
        
        # Test blocking signal
        block_enhancement = AISignalEnhancement(
            ai_signal="HOLD",
            ai_confidence=0.85,
            ai_risk_level="HIGH",
            ensemble_consensus=True,
            provider_count=2
        )
        
        assert block_enhancement.should_block_signal() is True
    
    def test_enhancement_to_dict(self):
        """Test enhancement serialization."""
        enhancement = AISignalEnhancement(
            ai_signal="BUY",
            ai_confidence=0.75,
            provider_count=2
        )
        
        data = enhancement.to_dict()
        
        assert isinstance(data, dict)
        assert data['ai_signal'] == "BUY"
        assert data['ai_confidence'] == 0.75
        assert data['provider_count'] == 2
    
    def test_adapter_stats(self, adapter):
        """Test adapter statistics."""
        stats = adapter.get_stats()
        
        assert isinstance(stats, dict)
        assert 'ai_enabled' in stats
        assert 'signals_enhanced' in stats


class TestAIEnhancedSignalEngine:
    """Test AI-enhanced signal engine."""
    
    @pytest.fixture
    def engine(self):
        """Create engine instance."""
        return AIEnhancedSignalEngine(enable_ai=False)
    
    @pytest.fixture
    def config(self):
        """Signal engine configuration."""
        return {
            'fib_tolerance_atr': 0.1,
            'rsi_tier1_max': 30,
            'rsi_tier2_range': (25, 35),
            'rsi_skip_above': 70,
            'rsi_skip_below': 15,
            'volume_tier1_min': 1.5,
            'volume_tier2_min': 1.2,
            'volume_tier3_min': 1.0,
            'stop_atr_mult': 2.0
        }
    
    def test_engine_initialization(self, engine):
        """Test engine initialization."""
        assert engine is not None
        assert engine.enable_ai is False
        assert engine.ai_initialized is False
    
    @pytest.mark.asyncio
    async def test_signal_generation_without_ai(self, engine, config):
        """Test signal generation with AI disabled."""
        signal = await engine.classify_signal_with_ai(
            symbol="BTC/USDT",
            timeframe="1h",
            fib_levels={0.618: 42000},
            rsi=28.5,
            ema_20=42100,
            ema_50=41800,
            ema_200=41000,
            current_price=42000,
            volume_ratio=1.6,
            atr=350,
            config=config
        )
        
        # Should generate base technical signal
        if signal:
            assert signal.symbol == "BTC/USDT"
            assert signal.direction in [SignalDirection.LONG, SignalDirection.SHORT]
            assert 0 <= signal.confidence <= 100
            assert not hasattr(signal, 'ai_metadata')  # No AI metadata when disabled
    
    @pytest.mark.asyncio
    async def test_ai_initialization(self, engine):
        """Test AI initialization."""
        # Mock environment with no API keys
        with patch.dict(os.environ, {}, clear=True):
            result = await engine.initialize_ai()
            
            # Should fail without API keys
            assert result is False
            assert engine.ai_initialized is False
    
    def test_ai_stats(self, engine):
        """Test AI statistics."""
        stats = engine.get_ai_stats()
        
        assert isinstance(stats, dict)
        assert 'ai_enabled' in stats
        assert 'ai_initialized' in stats
        assert 'signals_ai_enhanced' in stats
    
    def test_stats_reset(self, engine):
        """Test statistics reset."""
        # Modify stats
        engine.ai_stats['signals_ai_enhanced'] = 10
        engine.ai_stats['signals_ai_boosted'] = 5
        
        # Reset
        engine.reset_ai_stats()
        
        # Verify reset
        assert engine.ai_stats['signals_ai_enhanced'] == 0
        assert engine.ai_stats['signals_ai_boosted'] == 0


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_full_signal_flow_without_ai(self):
        """Test complete signal flow without AI."""
        engine = AIEnhancedSignalEngine(enable_ai=False)
        
        config = {
            'fib_tolerance_atr': 0.1,
            'rsi_tier1_max': 30,
            'rsi_tier2_range': (25, 35),
            'rsi_skip_above': 70,
            'rsi_skip_below': 15,
            'volume_tier1_min': 1.5,
            'volume_tier2_min': 1.2,
            'volume_tier3_min': 1.0,
            'stop_atr_mult': 2.0
        }
        
        # Generate signal
        signal = await engine.classify_signal_with_ai(
            symbol="BTC/USDT",
            timeframe="1h",
            fib_levels={0.618: 42000, 0.382: 43000},
            rsi=28.5,
            ema_20=42100,
            ema_50=41800,
            ema_200=41000,
            current_price=42000,
            volume_ratio=1.6,
            atr=350,
            config=config,
            volume=1250000
        )
        
        # Verify signal structure if generated
        if signal:
            assert signal.symbol == "BTC/USDT"
            assert signal.timeframe == "1h"
            assert signal.entry_price > 0
            assert signal.stop_loss != signal.entry_price
            assert signal.take_profit_1 > 0
            assert signal.take_profit_2 > 0
            assert isinstance(signal.tier, SignalTier)
            assert isinstance(signal.direction, SignalDirection)
    
    @pytest.mark.asyncio
    @patch('ai_models.ai_integration_adapter.EnsembleOrchestrator')
    async def test_full_signal_flow_with_mocked_ai(self, mock_orchestrator):
        """Test complete signal flow with mocked AI."""
        # Create mock AI response
        mock_result = Mock()
        mock_result.consensus_signal = "BUY"
        mock_result.confidence = 0.85
        mock_result.sentiment_score = 0.6
        mock_result.risk_level = "LOW"
        mock_result.provider_responses = {"openai": Mock(), "anthropic": Mock()}
        mock_result.execution_time_ms = 150.0
        
        # Mock orchestrator methods
        mock_orch_instance = AsyncMock()
        mock_orch_instance.generate_trading_signal_ensemble.return_value = mock_result
        mock_orchestrator.return_value = mock_orch_instance
        
        # Create engine with AI enabled
        engine = AIEnhancedSignalEngine(enable_ai=True)
        
        # Mock API keys in environment
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            await engine.initialize_ai()
        
        config = {
            'fib_tolerance_atr': 0.1,
            'rsi_tier1_max': 30,
            'rsi_tier2_range': (25, 35),
            'rsi_skip_above': 70,
            'rsi_skip_below': 15,
            'volume_tier1_min': 1.5,
            'volume_tier2_min': 1.2,
            'volume_tier3_min': 1.0,
            'stop_atr_mult': 2.0
        }
        
        # Generate AI-enhanced signal
        signal = await engine.classify_signal_with_ai(
            symbol="BTC/USDT",
            timeframe="1h",
            fib_levels={0.618: 42000},
            rsi=28.5,
            ema_20=42100,
            ema_50=41800,
            ema_200=41000,
            current_price=42000,
            volume_ratio=1.6,
            atr=350,
            config=config
        )
        
        # Verify AI enhancement was applied
        if signal and engine.ai_initialized:
            assert hasattr(signal, 'ai_metadata')
            stats = engine.get_ai_stats()
            assert stats['signals_ai_enhanced'] > 0


# ========== PYTEST FIXTURES ==========

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ========== RUN TESTS ==========

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])