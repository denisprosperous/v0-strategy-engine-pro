"""
Comprehensive AI Ensemble Testing Suite
Tests provider initialization, ensemble voting, signal generation, and performance metrics
"""
import pytest
import asyncio
import os
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_models.providers import OpenAIProvider, AnthropicProvider, GeminiProvider, GrokProvider, AIResponse
from ai_models.ensemble_orchestrator import EnsembleOrchestrator, EnsembleResult


class TestAIProviders:
    """Test individual AI providers"""
    
    @pytest.fixture
    def mock_api_keys(self):
        return {
            "openai": "test-openai-key",
            "anthropic": "test-anthropic-key",
            "gemini": "test-gemini-key",
            "grok": "test-grok-key"
        }
    
    @pytest.fixture
    def sample_market_data(self):
        return {
            "symbol": "BTC/USDT",
            "price": 45000.0,
            "volume_24h": 1234567890,
            "change_24h": 2.5,
            "high_24h": 46000.0,
            "low_24h": 44000.0
        }
    
    @pytest.fixture
    def sample_technical_indicators(self):
        return {
            "rsi": 65.0,
            "macd": {"value": 120.5, "signal": 100.3, "histogram": 20.2},
            "bollinger_bands": {"upper": 46500, "middle": 45000, "lower": 43500},
            "ema_20": 44800,
            "ema_50": 44200,
            "volume_sma": 1200000000
        }
    
    def test_openai_provider_initialization(self, mock_api_keys):
        """Test OpenAI provider initializes correctly"""
        provider = OpenAIProvider(api_key=mock_api_keys["openai"])
        assert provider.model == "gpt-4-turbo"
        assert provider.api_key == mock_api_keys["openai"]
        assert provider.cache is not None
        assert provider.rate_limiter is not None
    
    def test_anthropic_provider_initialization(self, mock_api_keys):
        """Test Anthropic provider initializes correctly"""
        provider = AnthropicProvider(api_key=mock_api_keys["anthropic"])
        assert provider.model == "claude-3-sonnet-20240229"
        assert provider.api_key == mock_api_keys["anthropic"]
    
    def test_gemini_provider_initialization(self, mock_api_keys):
        """Test Gemini provider initializes correctly"""
        provider = GeminiProvider(api_key=mock_api_keys["gemini"])
        assert provider.model_name == "gemini-1.5-flash"
        assert provider.api_key == mock_api_keys["gemini"]
    
    def test_grok_provider_initialization(self, mock_api_keys):
        """Test Grok provider initializes correctly"""
        provider = GrokProvider(api_key=mock_api_keys["grok"])
        assert provider.model == "grok-beta"
        assert provider.api_key == mock_api_keys["grok"]
    
    @pytest.mark.asyncio
    async def test_provider_caching(self, mock_api_keys):
        """Test that providers use caching effectively"""
        provider = OpenAIProvider(api_key=mock_api_keys["openai"], cache_ttl=60)
        
        # Mock API response
        mock_response = AIResponse(
            content="Test response",
            confidence=0.8,
            model="gpt-4-turbo",
            tokens_used=100,
            cost=0.001
        )
        
        # Set in cache
        provider.cache.set("test prompt", "gpt-4-turbo", mock_response)
        
        # Retrieve from cache
        cached = provider.cache.get("test prompt", "gpt-4-turbo")
        assert cached is not None
        assert cached.content == "Test response"
        assert cached.cached is True
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_api_keys):
        """Test rate limiter functionality"""
        provider = OpenAIProvider(api_key=mock_api_keys["openai"], rate_limit_rpm=60)
        
        start_time = time.time()
        
        # Acquire multiple times in quick succession
        for _ in range(3):
            await provider.rate_limiter.acquire()
        
        elapsed = time.time() - start_time
        
        # Should take negligible time for 3 requests under burst limit
        assert elapsed < 0.5


class TestEnsembleOrchestrator:
    """Test ensemble orchestrator functionality"""
    
    @pytest.fixture
    def mock_api_keys(self):
        return {
            "openai": "test-openai-key",
            "anthropic": "test-anthropic-key",
            "gemini": "test-gemini-key",
            "grok": "test-grok-key"
        }
    
    @pytest.fixture
    def sample_market_data(self):
        return {
            "symbol": "ETH/USDT",
            "price": 3200.0,
            "volume_24h": 987654321,
            "change_24h": 1.8,
            "trend": "bullish"
        }
    
    @pytest.fixture
    def sample_indicators(self):
        return {
            "rsi": 58.0,
            "macd_histogram": 15.3,
            "trend_strength": 0.7
        }
    
    def test_ensemble_initialization(self, mock_api_keys):
        """Test ensemble orchestrator initialization"""
        with patch.multiple(
            'ai_models.providers.openai_provider',
            OpenAIProvider=Mock(return_value=Mock()),
        ), patch.multiple(
            'ai_models.providers.anthropic_provider',
            AnthropicProvider=Mock(return_value=Mock()),
        ):
            orchestrator = EnsembleOrchestrator(api_keys=mock_api_keys)
            assert len(orchestrator.provider_weights) > 0
            assert orchestrator.min_confidence == 0.6
            assert orchestrator.min_providers == 2
    
    @pytest.mark.asyncio
    async def test_weighted_voting_mechanism(self):
        """Test weighted voting calculates correctly"""
        orchestrator = EnsembleOrchestrator(
            api_keys=None,  # Will use empty defaults
            provider_weights={"openai": 1.5, "anthropic": 1.0, "gemini": 1.2}
        )
        
        # Mock responses
        responses = {
            "openai": AIResponse(content="Buy", confidence=0.8, signal="BUY", model="gpt-4", tokens_used=100, cost=0.001),
            "anthropic": AIResponse(content="Hold", confidence=0.6, signal="HOLD", model="claude", tokens_used=100, cost=0.001),
            "gemini": AIResponse(content="Buy", confidence=0.7, signal="BUY", model="gemini", tokens_used=100, cost=0.001)
        }
        
        signal, confidence, details = orchestrator._calculate_weighted_vote(responses)
        
        # BUY should win: (0.8*1.5 + 0.7*1.2) = 2.04 vs HOLD: (0.6*1.0) = 0.6
        assert signal == "BUY"
        assert confidence > 0.6
        assert "vote_distribution" in details
    
    @pytest.mark.asyncio
    async def test_sentiment_analysis_ensemble(self, mock_api_keys, sample_market_data):
        """Test ensemble sentiment analysis"""
        orchestrator = EnsembleOrchestrator(api_keys=mock_api_keys, min_providers=1)
        
        # Mock provider methods
        async def mock_analyze_sentiment(text, market_context=None):
            return AIResponse(
                content="Bullish sentiment detected",
                confidence=0.75,
                sentiment_score=0.6,
                signal="BUY",
                risk_level="MEDIUM",
                model="test",
                tokens_used=50,
                cost=0.0005
            )
        
        with patch.object(orchestrator, '_gather_responses', return_value={
            "test_provider": await mock_analyze_sentiment("Bitcoin bullish news"),
        }):
            result = await orchestrator.analyze_sentiment_ensemble(
                text="Bitcoin showing strong bullish momentum",
                market_context=sample_market_data
            )
            
            assert isinstance(result, EnsembleResult)
            assert result.consensus_signal in ["BUY", "SELL", "HOLD"]
            assert 0.0 <= result.confidence <= 1.0
            assert result.sentiment_score is not None
    
    @pytest.mark.asyncio
    async def test_trading_signal_generation_ensemble(self, mock_api_keys, sample_market_data, sample_indicators):
        """Test ensemble trading signal generation"""
        orchestrator = EnsembleOrchestrator(api_keys=mock_api_keys, min_providers=1)
        
        async def mock_generate_signal(symbol, market_data, technical_indicators, timeframe="1h"):
            return AIResponse(
                content="Strong buy signal",
                confidence=0.82,
                signal="BUY",
                risk_level="MEDIUM",
                model="test",
                tokens_used=75,
                cost=0.00075,
                metadata={
                    "entry_price": 3200.0,
                    "stop_loss": 3100.0,
                    "take_profit": 3400.0
                }
            )
        
        with patch.object(orchestrator, '_gather_responses', return_value={
            "test_provider": await mock_generate_signal("ETH/USDT", sample_market_data, sample_indicators),
        }):
            result = await orchestrator.generate_trading_signal_ensemble(
                symbol="ETH/USDT",
                market_data=sample_market_data,
                technical_indicators=sample_indicators,
                timeframe="1h"
            )
            
            assert isinstance(result, EnsembleResult)
            assert result.consensus_signal in ["BUY", "SELL", "HOLD"]
            assert result.confidence > 0.0
            assert result.execution_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_risk_assessment_ensemble(self, mock_api_keys):
        """Test ensemble risk assessment"""
        orchestrator = EnsembleOrchestrator(api_keys=mock_api_keys, min_providers=1)
        
        position_data = {
            "symbol": "BTC/USDT",
            "entry_price": 45000,
            "current_price": 46500,
            "position_size": 0.5,
            "unrealized_pnl": 750
        }
        
        market_conditions = {
            "volatility": "moderate",
            "trend": "bullish",
            "volume_trend": "increasing"
        }
        
        async def mock_assess_risk(symbol, position_data, market_conditions):
            return AIResponse(
                content="Medium risk position",
                confidence=0.7,
                risk_level="MEDIUM",
                model="test",
                tokens_used=60,
                cost=0.0006,
                metadata={
                    "risk_score": 0.55,
                    "recommended_action": "HOLD"
                }
            )
        
        with patch.object(orchestrator, '_gather_responses', return_value={
            "test_provider": await mock_assess_risk("BTC/USDT", position_data, market_conditions),
        }):
            result = await orchestrator.assess_risk_ensemble(
                symbol="BTC/USDT",
                position_data=position_data,
                market_conditions=market_conditions
            )
            
            assert isinstance(result, EnsembleResult)
            assert result.risk_level in ["LOW", "MEDIUM", "HIGH", "EXTREME"]
            assert result.confidence > 0.0
    
    def test_ensemble_statistics(self, mock_api_keys):
        """Test statistics tracking"""
        orchestrator = EnsembleOrchestrator(api_keys=mock_api_keys)
        
        # Simulate some activity
        orchestrator.stats["sentiment_analyses"] = 10
        orchestrator.stats["signal_generations"] = 5
        orchestrator.stats["risk_assessments"] = 3
        
        stats = orchestrator.get_orchestrator_stats()
        
        assert stats["sentiment_analyses"] == 10
        assert stats["signal_generations"] == 5
        assert stats["risk_assessments"] == 3
        
        # Test reset
        orchestrator.reset_all_stats()
        stats = orchestrator.get_orchestrator_stats()
        assert len(stats) == 0


class TestPerformanceMetrics:
    """Test performance and latency metrics"""
    
    @pytest.mark.asyncio
    async def test_parallel_execution_faster_than_sequential(self):
        """Test that parallel execution is faster than sequential"""
        async def slow_task():
            await asyncio.sleep(0.1)
            return AIResponse(content="test", confidence=0.5, model="test", tokens_used=10, cost=0.0001)
        
        # Parallel
        start = time.time()
        tasks = [slow_task() for _ in range(3)]
        await asyncio.gather(*tasks)
        parallel_time = time.time() - start
        
        # Sequential
        start = time.time()
        for _ in range(3):
            await slow_task()
        sequential_time = time.time() - start
        
        # Parallel should be significantly faster
        assert parallel_time < sequential_time * 0.5
    
    @pytest.mark.asyncio
    async def test_ensemble_latency_tracking(self):
        """Test that ensemble tracks execution time"""
        orchestrator = EnsembleOrchestrator(api_keys=None, min_providers=1)
        
        async def mock_response():
            await asyncio.sleep(0.05)
            return AIResponse(content="test", confidence=0.5, signal="HOLD", model="test", tokens_used=10, cost=0.0001)
        
        with patch.object(orchestrator, '_gather_responses', return_value={"test": await mock_response()}):
            result = await orchestrator.analyze_sentiment_ensemble("test text")
            
            assert result.execution_time_ms > 0
            # Should be at least 50ms due to sleep
            assert result.execution_time_ms >= 50


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
