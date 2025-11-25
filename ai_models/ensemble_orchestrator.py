"""
AI Ensemble Orchestrator - Part 1
Core classes and provider initialization
"""
import asyncio
import time
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import Counter, defaultdict
import logging

try:
    import numpy as np
except ImportError:
    np = None

from .providers import OpenAIProvider, AnthropicProvider, GeminiProvider, GrokProvider, AIResponse

logger = logging.getLogger(__name__)

@dataclass
class EnsembleResult:
    consensus_signal: str
    confidence: float
    provider_responses: Dict[str, AIResponse] = field(default_factory=dict)
    voting_details: Dict[str, Any] = field(default_factory=dict)
    sentiment_score: Optional[float] = None
    risk_level: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self):
        return {
            "consensus_signal": self.consensus_signal,
            "confidence": self.confidence,
            "sentiment_score": self.sentiment_score,
            "risk_level": self.risk_level,
            "execution_time_ms": self.execution_time_ms,
            "voting_details": self.voting_details,
            "provider_count": len(self.provider_responses),
            "metadata": self.metadata
        }

class EnsembleOrchestrator:
    def __init__(self, api_keys: Optional[Dict[str, str]] = None, provider_weights: Optional[Dict[str, float]] = None, min_confidence: float = 0.6, min_providers: int = 2, enable_parallel: bool = True):
        self.providers = {}
        self.provider_weights = provider_weights or {}
        self.min_confidence = min_confidence
        self.min_providers = min_providers
        self.enable_parallel = enable_parallel
        self.stats = defaultdict(int)
        if api_keys is None:
            api_keys = {"openai": os.getenv("OPENAI_API_KEY", ""), "anthropic": os.getenv("ANTHROPIC_API_KEY", ""), "gemini": os.getenv("GOOGLE_API_KEY", ""), "grok": os.getenv("XAI_API_KEY", "")}
        self._initialize_providers(api_keys)
        if not self.provider_weights:
            for provider_name in self.providers.keys():
                self.provider_weights[provider_name] = 1.0
        logger.info(f"Initialized ensemble with {len(self.providers)} providers")

    def _initialize_providers(self, api_keys: Dict[str, str]):
        if api_keys.get("openai"):
            try:
                self.providers["openai"] = OpenAIProvider(api_key=api_keys["openai"], model="gpt-4-turbo", cache_ttl=300, rate_limit_rpm=60)
                logger.info("OpenAI initialized")
            except Exception as e:
                logger.warning(f"OpenAI init failed: {e}")
        if api_keys.get("anthropic"):
            try:
                self.providers["anthropic"] = AnthropicProvider(api_key=api_keys["anthropic"], model="claude-3-sonnet-20240229", cache_ttl=300, rate_limit_rpm=50)
                logger.info("Anthropic initialized")
            except Exception as e:
                logger.warning(f"Anthropic init failed: {e}")
        if api_keys.get("gemini"):
            try:
                self.providers["gemini"] = GeminiProvider(api_key=api_keys["gemini"], model="gemini-1.5-flash", cache_ttl=300, rate_limit_rpm=60)
                logger.info("Gemini initialized")
            except Exception as e:
                logger.warning(f"Gemini init failed: {e}")
        if api_keys.get("grok"):
            try:
                self.providers["grok"] = GrokProvider(api_key=api_keys["grok"], model="grok-beta", cache_ttl=300, rate_limit_rpm=60)
                logger.info("Grok initialized")
            except Exception as e:
                logger.warning(f"Grok init failed: {e}")

    async def _call_provider(self, provider_name: str, method: str, *args, **kwargs) -> Optional[AIResponse]:
        try:
            provider = self.providers[provider_name]
            method_func = getattr(provider, method)
            response = await method_func(*args, **kwargs)
            self.stats[f"{provider_name}_calls"] += 1
            return response
        except Exception as e:
            logger.error(f"Error calling {provider_name}.{method}: {e}")
            self.stats[f"{provider_name}_errors"] += 1
            return None

    async def _gather_responses(self, method: str, *args, **kwargs) -> Dict[str, AIResponse]:
        if self.enable_parallel:
            tasks = [self._call_provider(name, method, *args, **kwargs) for name in self.providers.keys()]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            responses = {}
            for provider_name, result in zip(self.providers.keys(), results):
                if isinstance(result, AIResponse):
                    responses[provider_name] = result
            return responses
        else:
            responses = {}
            for provider_name in self.providers.keys():
                response = await self._call_provider(provider_name, method, *args, **kwargs)
                if response:
                    responses[provider_name] = response
            return responses

    def _calculate_weighted_vote(self, responses: Dict[str, AIResponse], signal_key: str = "signal") -> Tuple[str, float, Dict]:
        weighted_votes = defaultdict(float)
        vote_details = []
        for provider_name, response in responses.items():
            signal = getattr(response, signal_key, None) or response.metadata.get(signal_key, "HOLD")
            confidence = response.confidence
            weight = self.provider_weights.get(provider_name, 1.0)
            vote_power = confidence * weight
            weighted_votes[signal] += vote_power
            vote_details.append({"provider": provider_name, "signal": signal, "confidence": confidence, "weight": weight, "vote_power": vote_power})
        if not weighted_votes:
            return "HOLD", 0.0, {"vote_details": vote_details, "reason": "no_votes"}
        consensus_signal = max(weighted_votes.items(), key=lambda x: x[1])[0]
        total_vote_power = sum(weighted_votes.values())
        consensus_confidence = weighted_votes[consensus_signal] / total_vote_power if total_vote_power > 0 else 0.0
        return consensus_signal, consensus_confidence, {"vote_details": vote_details, "vote_distribution": dict(weighted_votes), "total_vote_power": total_vote_power, "provider_count": len(responses)}

    async def analyze_sentiment_ensemble(self, text: str, market_context: Optional[Dict] = None) -> EnsembleResult:
        start_time = time.time()
        responses = await self._gather_responses("analyze_sentiment", text=text, market_context=market_context)
        if len(responses) < self.min_providers:
            return EnsembleResult(consensus_signal="HOLD", confidence=0.0, provider_responses=responses, metadata={"error": "insufficient_providers"})
        consensus_signal, confidence, voting_details = self._calculate_weighted_vote(responses)
        sentiment_scores = [r.sentiment_score for r in responses.values() if r.sentiment_score is not None]
        avg_sentiment = float(sum(sentiment_scores) / len(sentiment_scores)) if sentiment_scores else 0.0
        risk_votes = Counter([r.risk_level for r in responses.values() if r.risk_level])
        consensus_risk = risk_votes.most_common(1)[0][0] if risk_votes else "MEDIUM"
        self.stats["sentiment_analyses"] += 1
        return EnsembleResult(consensus_signal=consensus_signal, confidence=confidence, sentiment_score=avg_sentiment, risk_level=consensus_risk, provider_responses=responses, voting_details=voting_details, execution_time_ms=(time.time() - start_time) * 1000, metadata={"method": "analyze_sentiment_ensemble"})

    async def generate_trading_signal_ensemble(self, symbol: str, market_data: Dict, technical_indicators: Dict, timeframe: str = "1h") -> EnsembleResult:
        start_time = time.time()
        responses = await self._gather_responses("generate_trading_signal", symbol=symbol, market_data=market_data, technical_indicators=technical_indicators, timeframe=timeframe)
        if len(responses) < self.min_providers:
            return EnsembleResult(consensus_signal="HOLD", confidence=0.0, provider_responses=responses, metadata={"error": "insufficient_providers"})
        consensus_signal, confidence, voting_details = self._calculate_weighted_vote(responses)
        risk_votes = Counter([r.risk_level for r in responses.values() if r.risk_level])
        consensus_risk = risk_votes.most_common(1)[0][0] if risk_votes else "MEDIUM"
        self.stats["signal_generations"] += 1
        return EnsembleResult(consensus_signal=consensus_signal, confidence=confidence, risk_level=consensus_risk, provider_responses=responses, voting_details=voting_details, execution_time_ms=(time.time() - start_time) * 1000, metadata={"method": "generate_trading_signal_ensemble", "symbol": symbol})

    async def assess_risk_ensemble(self, symbol: str, position_data: Dict, market_conditions: Dict) -> EnsembleResult:
        start_time = time.time()
        responses = await self._gather_responses("assess_risk", symbol=symbol, position_data=position_data, market_conditions=market_conditions)
        if len(responses) < self.min_providers:
            return EnsembleResult(consensus_signal="HOLD", confidence=0.0, provider_responses=responses, metadata={"error": "insufficient_providers"})
        risk_votes = Counter([r.risk_level for r in responses.values() if r.risk_level])
        consensus_risk = risk_votes.most_common(1)[0][0] if risk_votes else "MEDIUM"
        confidences = [r.confidence for r in responses.values()]
        avg_confidence = float(sum(confidences) / len(confidences)) if confidences else 0.0
        self.stats["risk_assessments"] += 1
        return EnsembleResult(consensus_signal="ASSESS", confidence=avg_confidence, risk_level=consensus_risk, provider_responses=responses, voting_details={"risk_distribution": dict(risk_votes)}, execution_time_ms=(time.time() - start_time) * 1000, metadata={"method": "assess_risk_ensemble", "symbol": symbol})

    def get_provider_stats(self) -> Dict[str, Dict]:
        return {name: provider.get_stats() for name, provider in self.providers.items()}

    def get_orchestrator_stats(self) -> Dict:
        return dict(self.stats)

    def reset_all_stats(self):
        for provider in self.providers.values():
            provider.reset_stats()
        self.stats.clear()
