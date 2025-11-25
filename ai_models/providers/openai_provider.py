"""
OpenAI GPT Provider Wrapper
Implements caching, rate limiting, fallback, and structured analysis
"""
import openai
import asyncio
import time
import json
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging
from functools import wraps
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class AIResponse:
    """Standardized AI response format"""
    content: str
    confidence: float
    sentiment_score: Optional[float] = None
    signal: Optional[str] = None  # "BUY", "SELL", "HOLD"
    risk_level: Optional[str] = None  # "LOW", "MEDIUM", "HIGH"
    model: str = "unknown"
    tokens_used: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    cached: bool = False
    metadata: Dict[str, Any] = None

    def to_dict(self):
        return asdict(self)


class RateLimiter:
    """Token bucket rate limiter"""
    def __init__(self, calls_per_minute: int = 60, burst: int = 10):
        self.calls_per_minute = calls_per_minute
        self.burst = burst
        self.tokens = burst
        self.last_update = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(
                self.burst,
                self.tokens + elapsed * (self.calls_per_minute / 60.0)
            )
            self.last_update = now
            
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / (self.calls_per_minute / 60.0)
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


class ResponseCache:
    """Simple in-memory cache with TTL"""
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def _get_key(self, prompt: str, model: str) -> str:
        combined = f"{model}:{prompt}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def get(self, prompt: str, model: str) -> Optional[AIResponse]:
        key = self._get_key(prompt, model)
        if key in self.cache:
            entry, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                logger.debug(f"Cache hit for {model}")
                entry.cached = True
                return entry
            else:
                del self.cache[key]
        return None
    
    def set(self, prompt: str, model: str, response: AIResponse):
        key = self._get_key(prompt, model)
        self.cache[key] = (response, time.time())
    
    def clear(self):
        self.cache.clear()


class OpenAIProvider:
    """OpenAI GPT provider with advanced features"""
    
    MODELS = {
        "gpt-4-turbo": {"max_tokens": 128000, "cost_per_1k_input": 0.01, "cost_per_1k_output": 0.03},
        "gpt-4": {"max_tokens": 8192, "cost_per_1k_input": 0.03, "cost_per_1k_output": 0.06},
        "gpt-3.5-turbo": {"max_tokens": 16385, "cost_per_1k_input": 0.0005, "cost_per_1k_output": 0.0015},
    }
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo",
        max_retries: int = 3,
        cache_ttl: int = 300,
        rate_limit_rpm: int = 60
    ):
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.cache = ResponseCache(ttl_seconds=cache_ttl)
        self.rate_limiter = RateLimiter(calls_per_minute=rate_limit_rpm)
        self.stats = defaultdict(int)
        
        if model not in self.MODELS:
            raise ValueError(f"Unknown model: {model}. Available: {list(self.MODELS.keys())}")
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate API cost based on token usage"""
        model_config = self.MODELS[self.model]
        cost = (
            (input_tokens / 1000) * model_config["cost_per_1k_input"] +
            (output_tokens / 1000) * model_config["cost_per_1k_output"]
        )
        return round(cost, 6)
    
    async def _make_request(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 800,
        system_message: Optional[str] = None
    ) -> AIResponse:
        """Make API request with retries and error handling"""
        
        # Check cache first
        cached_response = self.cache.get(prompt, self.model)
        if cached_response:
            self.stats["cache_hits"] += 1
            return cached_response
        
        # Rate limiting
        await self.rate_limiter.acquire()
        
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                latency_ms = (time.time() - start_time) * 1000
                
                content = response.choices[0].message.content
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                total_tokens = response.usage.total_tokens
                cost = self._calculate_cost(input_tokens, output_tokens)
                
                ai_response = AIResponse(
                    content=content,
                    confidence=0.0,  # Will be extracted from content
                    model=self.model,
                    tokens_used=total_tokens,
                    cost=cost,
                    latency_ms=latency_ms,
                    cached=False,
                    metadata={
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "finish_reason": response.choices[0].finish_reason
                    }
                )
                
                # Cache successful response
                self.cache.set(prompt, self.model, ai_response)
                self.stats["api_calls"] += 1
                self.stats["total_tokens"] += total_tokens
                self.stats["total_cost"] += cost
                
                return ai_response
                
            except openai.RateLimitError as e:
                wait_time = 2 ** attempt
                logger.warning(f"Rate limit hit, waiting {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(wait_time)
            except openai.APIError as e:
                logger.error(f"OpenAI API error: {e} (attempt {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(1)
        
        raise Exception(f"Failed after {self.max_retries} retries")
    
    async def analyze_sentiment(self, text: str, market_context: Optional[Dict] = None) -> AIResponse:
        """Analyze sentiment of text for trading decisions"""
        
        context_str = ""
        if market_context:
            context_str = f"\n\nMarket Context: {json.dumps(market_context, indent=2)}"
        
        prompt = f"""
Analyze the sentiment of the following text for cryptocurrency trading decisions.

Text: {text}{context_str}

Provide your analysis in JSON format:
{{
  "sentiment": "bullish" | "bearish" | "neutral",
  "confidence": 0.0 to 1.0,
  "sentiment_score": -1.0 to 1.0 (negative=bearish, positive=bullish),
  "key_factors": ["factor1", "factor2", ...],
  "market_impact": "description",
  "trading_signal": "BUY" | "SELL" | "HOLD",
  "risk_level": "LOW" | "MEDIUM" | "HIGH"
}}
"""
        
        system_message = "You are an expert cryptocurrency market analyst. Provide precise, actionable sentiment analysis."
        
        response = await self._make_request(prompt, temperature=0.2, system_message=system_message)
        
        # Parse JSON response
        try:
            parsed = json.loads(response.content)
            response.confidence = parsed.get("confidence", 0.5)
            response.sentiment_score = parsed.get("sentiment_score", 0.0)
            response.signal = parsed.get("trading_signal", "HOLD")
            response.risk_level = parsed.get("risk_level", "MEDIUM")
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response, using defaults")
            response.confidence = 0.3
        
        return response
    
    async def generate_trading_signal(
        self,
        symbol: str,
        market_data: Dict,
        technical_indicators: Dict,
        timeframe: str = "1h"
    ) -> AIResponse:
        """Generate trading signal based on comprehensive market analysis"""
        
        prompt = f"""
Analyze the following market data and generate a trading signal for {symbol} on {timeframe} timeframe.

Market Data:
{json.dumps(market_data, indent=2)}

Technical Indicators:
{json.dumps(technical_indicators, indent=2)}

Provide analysis in JSON format:
{{
  "signal": "BUY" | "SELL" | "HOLD",
  "confidence": 0.0 to 1.0,
  "entry_price": float,
  "stop_loss": float,
  "take_profit": float,
  "position_size_pct": 0.0 to 1.0,
  "reasoning": "detailed explanation",
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "key_indicators": ["indicator1", "indicator2", ...],
  "market_regime": "trending" | "ranging" | "volatile"
}}
"""
        
        system_message = "You are an expert algorithmic trader. Generate precise trading signals based on comprehensive market analysis."
        
        response = await self._make_request(prompt, temperature=0.1, max_tokens=1000, system_message=system_message)
        
        try:
            parsed = json.loads(response.content)
            response.confidence = parsed.get("confidence", 0.5)
            response.signal = parsed.get("signal", "HOLD")
            response.risk_level = parsed.get("risk_level", "MEDIUM")
            response.metadata.update(parsed)
        except json.JSONDecodeError:
            logger.warning("Failed to parse trading signal JSON")
            response.confidence = 0.0
            response.signal = "HOLD"
        
        return response
    
    async def assess_risk(
        self,
        symbol: str,
        position_data: Dict,
        market_conditions: Dict
    ) -> AIResponse:
        """Assess risk for existing or proposed position"""
        
        prompt = f"""
Assess the risk for the following trading position on {symbol}.

Position Data:
{json.dumps(position_data, indent=2)}

Market Conditions:
{json.dumps(market_conditions, indent=2)}

Provide risk assessment in JSON format:
{{
  "risk_level": "LOW" | "MEDIUM" | "HIGH" | "EXTREME",
  "risk_score": 0.0 to 1.0,
  "confidence": 0.0 to 1.0,
  "risk_factors": ["factor1", "factor2", ...],
  "recommended_action": "HOLD" | "REDUCE" | "CLOSE" | "INCREASE_SL",
  "max_position_size": float,
  "volatility_assessment": "description",
  "correlation_risks": ["risk1", "risk2", ...]
}}
"""
        
        system_message = "You are an expert risk manager for cryptocurrency trading. Provide thorough risk assessments."
        
        response = await self._make_request(prompt, temperature=0.2, system_message=system_message)
        
        try:
            parsed = json.loads(response.content)
            response.confidence = parsed.get("confidence", 0.5)
            response.risk_level = parsed.get("risk_level", "MEDIUM")
            response.metadata.update(parsed)
        except json.JSONDecodeError:
            logger.warning("Failed to parse risk assessment JSON")
            response.confidence = 0.0
            response.risk_level = "HIGH"
        
        return response
    
    def get_stats(self) -> Dict:
        """Get provider usage statistics"""
        return dict(self.stats)
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats.clear()
