"""
Google Gemini Provider Wrapper
Implements caching, rate limiting, fallback, and structured analysis
"""
import google.generativeai as genai
import asyncio
import time
import json
from typing import Dict, List, Optional, Any
import logging
from collections import defaultdict

from .openai_provider import AIResponse, RateLimiter, ResponseCache

logger = logging.getLogger(__name__)


class GeminiProvider:
    """Google Gemini provider with advanced features"""
    
    MODELS = {
        "gemini-1.5-pro": {"max_tokens": 2097152, "cost_per_1m_input": 1.25, "cost_per_1m_output": 5.0},
        "gemini-1.5-flash": {"max_tokens": 1048576, "cost_per_1m_input": 0.075, "cost_per_1m_output": 0.30},
        "gemini-pro": {"max_tokens": 30720, "cost_per_1m_input": 0.5, "cost_per_1m_output": 1.5},
    }
    
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-1.5-flash",
        max_retries: int = 3,
        cache_ttl: int = 300,
        rate_limit_rpm: int = 60
    ):
        self.api_key = api_key
        self.model_name = model
        self.max_retries = max_retries
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.cache = ResponseCache(ttl_seconds=cache_ttl)
        self.rate_limiter = RateLimiter(calls_per_minute=rate_limit_rpm)
        self.stats = defaultdict(int)
        
        if model not in self.MODELS:
            raise ValueError(f"Unknown model: {model}. Available: {list(self.MODELS.keys())}")
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate API cost based on token usage (estimated)"""
        model_config = self.MODELS[self.model_name]
        cost = (
            (input_tokens / 1_000_000) * model_config["cost_per_1m_input"] +
            (output_tokens / 1_000_000) * model_config["cost_per_1m_output"]
        )
        return round(cost, 6)
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (Gemini doesn't always provide exact counts)"""
        # Approximation: ~0.75 tokens per word
        return int(len(text.split()) * 0.75)
    
    async def _make_request(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        system_instruction: Optional[str] = None
    ) -> AIResponse:
        """Make API request with retries and error handling"""
        
        # Check cache first
        cached_response = self.cache.get(prompt, self.model_name)
        if cached_response:
            self.stats["cache_hits"] += 1
            return cached_response
        
        # Rate limiting
        await self.rate_limiter.acquire()
        
        # Reconfigure model with system instruction if provided
        if system_instruction:
            model = genai.GenerativeModel(
                self.model_name,
                system_instruction=system_instruction
            )
        else:
            model = self.model
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                # Gemini API is synchronous, run in executor
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: model.generate_content(
                        prompt,
                        generation_config=genai.GenerationConfig(
                            temperature=temperature,
                            max_output_tokens=max_tokens,
                        )
                    )
                )
                
                latency_ms = (time.time() - start_time) * 1000
                
                content = response.text
                
                # Estimate tokens (Gemini doesn't always provide exact counts)
                input_tokens = self._estimate_tokens(prompt)
                output_tokens = self._estimate_tokens(content)
                total_tokens = input_tokens + output_tokens
                cost = self._calculate_cost(input_tokens, output_tokens)
                
                ai_response = AIResponse(
                    content=content,
                    confidence=0.0,
                    model=self.model_name,
                    tokens_used=total_tokens,
                    cost=cost,
                    latency_ms=latency_ms,
                    cached=False,
                    metadata={
                        "input_tokens_estimated": input_tokens,
                        "output_tokens_estimated": output_tokens,
                        "finish_reason": str(response.candidates[0].finish_reason) if response.candidates else "unknown"
                    }
                )
                
                # Cache successful response
                self.cache.set(prompt, self.model_name, ai_response)
                self.stats["api_calls"] += 1
                self.stats["total_tokens"] += total_tokens
                self.stats["total_cost"] += cost
                
                return ai_response
                
            except Exception as e:
                error_str = str(e).lower()
                if "quota" in error_str or "rate" in error_str:
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate/quota limit hit, waiting {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Gemini API error: {e} (attempt {attempt + 1}/{self.max_retries})")
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
        
        system_instruction = "You are an expert cryptocurrency market analyst. Provide precise, actionable sentiment analysis."
        
        response = await self._make_request(prompt, temperature=0.2, max_tokens=800, system_instruction=system_instruction)
        
        # Parse JSON response
        try:
            # Extract JSON from response (Gemini sometimes adds markdown)
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(content)
            response.confidence = parsed.get("confidence", 0.5)
            response.sentiment_score = parsed.get("sentiment_score", 0.0)
            response.signal = parsed.get("trading_signal", "HOLD")
            response.risk_level = parsed.get("risk_level", "MEDIUM")
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning(f"Failed to parse JSON response: {e}, using defaults")
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
        
        system_instruction = "You are an expert algorithmic trader. Generate precise trading signals based on comprehensive market analysis."
        
        response = await self._make_request(prompt, temperature=0.1, max_tokens=1200, system_instruction=system_instruction)
        
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(content)
            response.confidence = parsed.get("confidence", 0.5)
            response.signal = parsed.get("signal", "HOLD")
            response.risk_level = parsed.get("risk_level", "MEDIUM")
            response.metadata.update(parsed)
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning(f"Failed to parse trading signal JSON: {e}")
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
        
        system_instruction = "You are an expert risk manager for cryptocurrency trading. Provide thorough risk assessments."
        
        response = await self._make_request(prompt, temperature=0.2, max_tokens=1000, system_instruction=system_instruction)
        
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(content)
            response.confidence = parsed.get("confidence", 0.5)
            response.risk_level = parsed.get("risk_level", "MEDIUM")
            response.metadata.update(parsed)
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning(f"Failed to parse risk assessment JSON: {e}")
            response.confidence = 0.0
            response.risk_level = "HIGH"
        
        return response
    
    def get_stats(self) -> Dict:
        """Get provider usage statistics"""
        return dict(self.stats)
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats.clear()
