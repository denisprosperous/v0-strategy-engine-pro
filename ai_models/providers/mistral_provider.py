"""
Mistral AI Provider Wrapper
Implements caching, rate limiting, fallback, and structured analysis
"""
import httpx
import asyncio
import time
import json
from typing import Dict, List, Optional, Any
import logging
from collections import defaultdict

from .openai_provider import AIResponse, RateLimiter, ResponseCache

logger = logging.getLogger(__name__)


class MistralProvider:
    """Mistral AI provider with advanced features"""
    
    MODELS = {
        "mistral-large-latest": {"max_tokens": 128000, "cost_per_1m_input": 4.0, "cost_per_1m_output": 12.0},
        "mistral-medium-latest": {"max_tokens": 32000, "cost_per_1m_input": 2.7, "cost_per_1m_output": 8.1},
        "mistral-small-latest": {"max_tokens": 32000, "cost_per_1m_input": 1.0, "cost_per_1m_output": 3.0},
        "open-mistral-7b": {"max_tokens": 32000, "cost_per_1m_input": 0.25, "cost_per_1m_output": 0.25},
        "open-mixtral-8x7b": {"max_tokens": 32000, "cost_per_1m_input": 0.7, "cost_per_1m_output": 0.7},
        "open-mixtral-8x22b": {"max_tokens": 64000, "cost_per_1m_input": 2.0, "cost_per_1m_output": 6.0},
    }
    
    BASE_URL = "https://api.mistral.ai/v1"
    
    def __init__(
        self,
        api_key: str,
        model: str = "mistral-small-latest",
        max_retries: int = 3,
        cache_ttl: int = 300,
        rate_limit_rpm: int = 60
    ):
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.cache = ResponseCache(ttl_seconds=cache_ttl)
        self.rate_limiter = RateLimiter(calls_per_minute=rate_limit_rpm)
        self.stats = defaultdict(int)
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        
        if model not in self.MODELS:
            raise ValueError(f"Unknown model: {model}. Available: {list(self.MODELS.keys())}")
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate API cost based on token usage"""
        model_config = self.MODELS[self.model]
        cost = (
            (input_tokens / 1_000_000) * model_config["cost_per_1m_input"] +
            (output_tokens / 1_000_000) * model_config["cost_per_1m_output"]
        )
        return round(cost, 6)
    
    async def _make_request(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
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
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                response = await self.client.post("/chat/completions", json=payload)
                response.raise_for_status()
                
                latency_ms = (time.time() - start_time) * 1000
                
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                # Mistral returns usage info
                usage = data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", input_tokens + output_tokens)
                
                cost = self._calculate_cost(input_tokens, output_tokens)
                
                ai_response = AIResponse(
                    content=content,
                    confidence=0.0,
                    model=self.model,
                    tokens_used=total_tokens,
                    cost=cost,
                    latency_ms=latency_ms,
                    cached=False,
                    metadata={
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "finish_reason": data["choices"][0].get("finish_reason"),
                    }
                )
                
                # Cache successful response
                self.cache.set(prompt, self.model, ai_response)
                self.stats["api_calls"] += 1
                self.stats["total_tokens"] += total_tokens
                self.stats["total_cost"] += cost
                
                return ai_response
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    wait_time = (2 ** attempt) * 1.5
                    logger.warning(f"Rate limit hit, waiting {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Mistral API error {e.response.status_code}: {e} (attempt {attempt + 1}/{self.max_retries})")
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
        
        response = await self._make_request(prompt, temperature=0.2, max_tokens=1000, system_message=system_message)
        
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
        
        response = await self._make_request(prompt, temperature=0.1, max_tokens=1500, system_message=system_message)
        
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
        
        response = await self._make_request(prompt, temperature=0.2, max_tokens=1200, system_message=system_message)
        
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
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
