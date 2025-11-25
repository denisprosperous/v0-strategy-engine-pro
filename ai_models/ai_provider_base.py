"""
Base AI Provider Class
Foundation for all LLM/AI integrations with comprehensive error handling,
retry logic, caching, rate limiting, and cost tracking.
"""

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from functools import wraps
import aiohttp
from cachetools import TTLCache


class AnalysisType(Enum):
    """Types of AI analysis tasks"""
    SENTIMENT = "sentiment"
    MARKET_INSIGHTS = "market_insights"
    NEWS_ANALYSIS = "news_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    SIGNAL_GENERATION = "signal_generation"
    TECHNICAL_ANALYSIS = "technical_analysis"


@dataclass
class LLMConfig:
    """Configuration for LLM providers"""
    api_key: str
    model_name: str
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 2.0
    exponential_backoff: bool = True
    enable_caching: bool = True
    cache_ttl: int = 3600
    max_requests_per_minute: int = 60
    cost_per_1k_input_tokens: float = 0.0
    cost_per_1k_output_tokens: float = 0.0
    base_url: Optional[str] = None
    extra_headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Standardized response from AI providers"""
    content: str
    analysis_type: AnalysisType
    confidence: float  # 0.0 to 1.0
    model: str
    provider: str
    tokens_used: int
    input_tokens: int
    output_tokens: int
    cost: float
    latency_ms: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    cache_hit: bool = False
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        d = asdict(self)
        d['analysis_type'] = self.analysis_type.value
        return d
    
    @property
    def success(self) -> bool:
        """Check if analysis was successful"""
        return self.error is None and self.content and self.confidence > 0


class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, max_requests: int, time_window: float = 60.0):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait until request can proceed"""
        async with self.lock:
            now = time.time()
            # Remove requests outside time window
            self.requests = [t for t in self.requests if now - t < self.time_window]
            
            if len(self.requests) >= self.max_requests:
                # Calculate wait time
                oldest = self.requests[0]
                wait_time = self.time_window - (now - oldest)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    return await self.acquire()
            
            self.requests.append(now)


class CostTracker:
    """Track API costs across providers"""
    
    def __init__(self):
        self.daily_costs = {}
        self.total_cost = 0.0
        self.cost_by_provider = {}
        self.cost_by_model = {}
        self.reset_time = time.time()
    
    def add_cost(self, cost: float, provider: str, model: str):
        """Add cost to tracking"""
        self.total_cost += cost
        self.cost_by_provider[provider] = self.cost_by_provider.get(provider, 0.0) + cost
        self.cost_by_model[model] = self.cost_by_model.get(model, 0.0) + cost
        
        # Daily tracking
        today = time.strftime("%Y-%m-%d")
        if today not in self.daily_costs:
            self.daily_costs[today] = 0.0
        self.daily_costs[today] += cost
    
    def get_daily_cost(self) -> float:
        """Get today's cost"""
        today = time.strftime("%Y-%m-%d")
        return self.daily_costs.get(today, 0.0)
    
    def reset_if_needed(self):
        """Reset daily costs if new day"""
        if time.time() - self.reset_time > 86400:  # 24 hours
            today = time.strftime("%Y-%m-%d")
            # Keep only today's costs
            self.daily_costs = {today: self.daily_costs.get(today, 0.0)}
            self.reset_time = time.time()


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers"""
    
    def __init__(self, config: LLMConfig, provider_name: str):
        self.config = config
        self.provider_name = provider_name
        self.logger = logging.getLogger(f"{__name__}.{provider_name}")
        
        # Initialize components
        self.rate_limiter = RateLimiter(config.max_requests_per_minute)
        self.cost_tracker = CostTracker()
        
        # Cache setup
        if config.enable_caching:
            self.cache = TTLCache(maxsize=1000, ttl=config.cache_ttl)
        else:
            self.cache = None
        
        # Performance tracking
        self.request_count = 0
        self.error_count = 0
        self.total_latency = 0.0
        self.cache_hits = 0
    
    def _get_cache_key(self, prompt: str, analysis_type: AnalysisType, **kwargs) -> str:
        """Generate cache key from prompt and parameters"""
        key_data = {
            'prompt': prompt,
            'type': analysis_type.value,
            'model': self.config.model_name,
            **kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _check_cache(self, cache_key: str) -> Optional[LLMResponse]:
        """Check if response is in cache"""
        if not self.cache:
            return None
        
        cached = self.cache.get(cache_key)
        if cached:
            self.cache_hits += 1
            cached.cache_hit = True
            self.logger.debug(f"Cache hit for key: {cache_key[:8]}...")
            return cached
        return None
    
    def _store_cache(self, cache_key: str, response: LLMResponse):
        """Store response in cache"""
        if self.cache is not None:
            self.cache[cache_key] = response
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage"""
        input_cost = (input_tokens / 1000) * self.config.cost_per_1k_input_tokens
        output_cost = (output_tokens / 1000) * self.config.cost_per_1k_output_tokens
        return input_cost + output_cost
    
    async def _retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                self.error_count += 1
                
                if attempt < self.config.max_retries - 1:
                    if self.config.exponential_backoff:
                        wait_time = self.config.retry_delay * (2 ** attempt)
                    else:
                        wait_time = self.config.retry_delay
                    
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(
                        f"All {self.config.max_retries} attempts failed: {str(e)}"
                    )
        
        raise last_exception
    
    @abstractmethod
    async def _make_api_call(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Make API call to provider (implemented by subclasses)"""
        pass
    
    async def analyze(
        self,
        prompt: str,
        analysis_type: AnalysisType,
        **kwargs
    ) -> LLMResponse:
        """Main analysis method with full error handling and caching"""
        start_time = time.time()
        
        # Check cache first
        cache_key = self._get_cache_key(prompt, analysis_type, **kwargs)
        cached_response = self._check_cache(cache_key)
        if cached_response:
            return cached_response
        
        # Rate limiting
        await self.rate_limiter.acquire()
        
        self.request_count += 1
        
        try:
            # Make API call with retry logic
            result = await self._retry_with_backoff(
                self._make_api_call,
                prompt,
                **kwargs
            )
            
            # Calculate metrics
            latency_ms = (time.time() - start_time) * 1000
            self.total_latency += latency_ms
            
            input_tokens = result.get('input_tokens', 0)
            output_tokens = result.get('output_tokens', 0)
            total_tokens = input_tokens + output_tokens
            cost = self._calculate_cost(input_tokens, output_tokens)
            
            # Track cost
            self.cost_tracker.add_cost(cost, self.provider_name, self.config.model_name)
            self.cost_tracker.reset_if_needed()
            
            # Create response
            response = LLMResponse(
                content=result.get('content', ''),
                analysis_type=analysis_type,
                confidence=result.get('confidence', 0.5),
                model=self.config.model_name,
                provider=self.provider_name,
                tokens_used=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                latency_ms=latency_ms,
                timestamp=time.time(),
                metadata=result.get('metadata', {}),
                cache_hit=False,
                error=None
            )
            
            # Cache successful response
            self._store_cache(cache_key, response)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {str(e)}", exc_info=True)
            
            # Return error response
            return LLMResponse(
                content="",
                analysis_type=analysis_type,
                confidence=0.0,
                model=self.config.model_name,
                provider=self.provider_name,
                tokens_used=0,
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                latency_ms=(time.time() - start_time) * 1000,
                timestamp=time.time(),
                metadata={},
                cache_hit=False,
                error=str(e)
            )
    
    async def analyze_sentiment(self, text: str, context: Dict = None) -> LLMResponse:
        """Analyze sentiment for trading"""
        prompt = self._build_sentiment_prompt(text, context)
        return await self.analyze(prompt, AnalysisType.SENTIMENT)
    
    async def generate_market_insights(self, market_data: Dict) -> LLMResponse:
        """Generate trading insights from market data"""
        prompt = self._build_market_insights_prompt(market_data)
        return await self.analyze(prompt, AnalysisType.MARKET_INSIGHTS)
    
    async def analyze_news(self, articles: List[str], symbols: List[str] = None) -> LLMResponse:
        """Analyze news impact on markets"""
        prompt = self._build_news_analysis_prompt(articles, symbols)
        return await self.analyze(prompt, AnalysisType.NEWS_ANALYSIS)
    
    async def assess_risk(self, position_data: Dict, market_conditions: Dict) -> LLMResponse:
        """Assess trading risk"""
        prompt = self._build_risk_assessment_prompt(position_data, market_conditions)
        return await self.analyze(prompt, AnalysisType.RISK_ASSESSMENT)
    
    def _build_sentiment_prompt(self, text: str, context: Dict = None) -> str:
        """Build sentiment analysis prompt"""
        context_str = ""
        if context:
            context_str = f"\n\nAdditional Context:\n{json.dumps(context, indent=2)}"
        
        return f"""Analyze the following text for cryptocurrency/financial trading sentiment:

Text: {text}{context_str}

Provide a JSON response with:
{{
    "sentiment": "bullish" | "bearish" | "neutral",
    "confidence": 0.0-1.0,
    "key_factors": ["factor1", "factor2", ...],
    "market_impact": "description",
    "affected_assets": ["BTC", "ETH", ...],
    "time_horizon": "short" | "medium" | "long"
}}

Be concise and data-driven in your analysis."""
    
    def _build_market_insights_prompt(self, market_data: Dict) -> str:
        """Build market insights prompt"""
        return f"""Analyze the following market data and provide actionable trading insights:

Market Data:
{json.dumps(market_data, indent=2)}

Provide a JSON response with:
{{
    "trend": "bullish" | "bearish" | "sideways",
    "strength": 0.0-1.0,
    "support_levels": [price1, price2, ...],
    "resistance_levels": [price1, price2, ...],
    "key_indicators": {{"indicator": "analysis", ...}},
    "trading_recommendation": "buy" | "sell" | "hold" | "wait",
    "confidence": 0.0-1.0,
    "risk_level": "low" | "medium" | "high",
    "reasoning": "brief explanation"
}}

Focus on technical analysis and price action."""
    
    def _build_news_analysis_prompt(self, articles: List[str], symbols: List[str] = None) -> str:
        """Build news analysis prompt"""
        articles_text = "\n\n---\n\n".join(articles[:5])  # Limit to 5 articles
        symbols_str = ", ".join(symbols) if symbols else "cryptocurrency markets"
        
        return f"""Analyze the following news articles for impact on {symbols_str}:

Articles:
{articles_text}

Provide a JSON response with:
{{
    "overall_sentiment": "positive" | "negative" | "neutral",
    "market_impact": "high" | "medium" | "low",
    "affected_symbols": {{"symbol": "impact_description", ...}},
    "key_events": ["event1", "event2", ...],
    "trading_implications": "description",
    "confidence": 0.0-1.0,
    "urgency": "immediate" | "near_term" | "long_term"
}}

Focus on market-moving information."""
    
    def _build_risk_assessment_prompt(self, position_data: Dict, market_conditions: Dict) -> str:
        """Build risk assessment prompt"""
        return f"""Assess the risk of the following trading position given current market conditions:

Position Data:
{json.dumps(position_data, indent=2)}

Market Conditions:
{json.dumps(market_conditions, indent=2)}

Provide a JSON response with:
{{
    "risk_level": "low" | "medium" | "high" | "extreme",
    "risk_score": 0.0-1.0,
    "key_risks": ["risk1", "risk2", ...],
    "recommended_actions": ["action1", "action2", ...],
    "stop_loss_suggestion": price_level,
    "position_sizing_advice": "description",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}

Be conservative and prioritize capital preservation."""
    
    def get_stats(self) -> Dict[str, Any]:
        """Get provider statistics"""
        avg_latency = self.total_latency / max(self.request_count, 1)
        cache_hit_rate = self.cache_hits / max(self.request_count, 1) * 100
        error_rate = self.error_count / max(self.request_count, 1) * 100
        
        return {
            'provider': self.provider_name,
            'model': self.config.model_name,
            'total_requests': self.request_count,
            'errors': self.error_count,
            'error_rate_pct': round(error_rate, 2),
            'cache_hits': self.cache_hits,
            'cache_hit_rate_pct': round(cache_hit_rate, 2),
            'avg_latency_ms': round(avg_latency, 2),
            'total_cost_usd': round(self.cost_tracker.total_cost, 4),
            'daily_cost_usd': round(self.cost_tracker.get_daily_cost(), 4),
        }
