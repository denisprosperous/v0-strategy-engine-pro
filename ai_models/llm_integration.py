import openai
import anthropic
import google.generativeai as genai
from typing import Dict, List, Optional, Any
import requests
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class LLMResponse:
    """Standardized LLM response format"""
    content: str
    confidence: float
    model: str
    tokens_used: int
    cost: float
    metadata: Dict[str, Any]

class BaseLLM(ABC):
    """Abstract base class for LLM integrations"""
    
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    async def analyze_sentiment(self, text: str) -> LLMResponse:
        """Analyze sentiment of given text"""
        pass
    
    @abstractmethod
    async def generate_trading_insights(self, market_data: Dict) -> LLMResponse:
        """Generate trading insights from market data"""
        pass
    
    @abstractmethod
    async def analyze_news(self, news_articles: List[str]) -> LLMResponse:
        """Analyze news articles for market impact"""
        pass

class DeepSeekAnalyzer(BaseLLM):
    """DeepSeek V3.1 integration"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "deepseek-chat")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def analyze_sentiment(self, text: str) -> LLMResponse:
        """Analyze sentiment using DeepSeek"""
        prompt = f"""
        Analyze the sentiment of the following text for cryptocurrency trading:
        
        Text: {text}
        
        Provide:
        1. Overall sentiment (bullish/bearish/neutral)
        2. Confidence score (0-1)
        3. Key factors influencing sentiment
        4. Potential market impact
        """
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.3
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Parse sentiment score (simplified)
                sentiment_score = 0.5  # Default neutral
                if "bullish" in content.lower():
                    sentiment_score = 0.8
                elif "bearish" in content.lower():
                    sentiment_score = 0.2
                
                return LLMResponse(
                    content=content,
                    confidence=sentiment_score,
                    model="deepseek-chat",
                    tokens_used=result['usage']['total_tokens'],
                    cost=0.0,  # Calculate based on token usage
                    metadata={"model": self.model_name}
                )
            else:
                raise Exception(f"DeepSeek API error: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"DeepSeek sentiment analysis failed: {e}")
            return LLMResponse(
                content="Error analyzing sentiment",
                confidence=0.0,
                model="deepseek-chat",
                tokens_used=0,
                cost=0.0,
                metadata={"error": str(e)}
            )
    
    async def generate_trading_insights(self, market_data: Dict) -> LLMResponse:
        """Generate trading insights using DeepSeek"""
        prompt = f"""
        Analyze the following market data and provide trading insights:
        
        Market Data: {json.dumps(market_data, indent=2)}
        
        Provide:
        1. Technical analysis summary
        2. Key support/resistance levels
        3. Trading recommendations
        4. Risk assessment
        5. Confidence level (0-1)
        """
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 800,
                    "temperature": 0.2
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                return LLMResponse(
                    content=content,
                    confidence=0.7,  # Parse from response
                    model="deepseek-chat",
                    tokens_used=result['usage']['total_tokens'],
                    cost=0.0,
                    metadata={"market_data": market_data}
                )
            else:
                raise Exception(f"DeepSeek API error: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"DeepSeek trading insights failed: {e}")
            return LLMResponse(
                content="Error generating trading insights",
                confidence=0.0,
                model="deepseek-chat",
                tokens_used=0,
                cost=0.0,
                metadata={"error": str(e)}
            )
    
    async def analyze_news(self, news_articles: List[str]) -> LLMResponse:
        """Analyze news articles using DeepSeek"""
        articles_text = "\n\n".join(news_articles)
        prompt = f"""
        Analyze the following news articles for cryptocurrency market impact:
        
        Articles:
        {articles_text}
        
        Provide:
        1. Overall market sentiment
        2. Key events and their impact
        3. Affected cryptocurrencies
        4. Trading implications
        5. Confidence level (0-1)
        """
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 600,
                    "temperature": 0.3
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                return LLMResponse(
                    content=content,
                    confidence=0.6,
                    model="deepseek-chat",
                    tokens_used=result['usage']['total_tokens'],
                    cost=0.0,
                    metadata={"articles_count": len(news_articles)}
                )
            else:
                raise Exception(f"DeepSeek API error: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"DeepSeek news analysis failed: {e}")
            return LLMResponse(
                content="Error analyzing news",
                confidence=0.0,
                model="deepseek-chat",
                tokens_used=0,
                cost=0.0,
                metadata={"error": str(e)}
            )

class GrokAnalyzer(BaseLLM):
    """Grok AI integration"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "grok-beta")
        # Grok API endpoint would be configured here
        self.base_url = "https://api.x.ai/v1/chat/completions"  # Placeholder
    
    async def analyze_sentiment(self, text: str) -> LLMResponse:
        """Analyze sentiment using Grok"""
        # Implementation would be similar to DeepSeek
        # For now, return a placeholder response
        return LLMResponse(
            content="Grok sentiment analysis placeholder",
            confidence=0.6,
            model="grok-beta",
            tokens_used=0,
            cost=0.0,
            metadata={"model": self.model_name}
        )
    
    async def generate_trading_insights(self, market_data: Dict) -> LLMResponse:
        """Generate trading insights using Grok"""
        return LLMResponse(
            content="Grok trading insights placeholder",
            confidence=0.7,
            model="grok-beta",
            tokens_used=0,
            cost=0.0,
            metadata={"market_data": market_data}
        )
    
    async def analyze_news(self, news_articles: List[str]) -> LLMResponse:
        """Analyze news articles using Grok"""
        return LLMResponse(
            content="Grok news analysis placeholder",
            confidence=0.6,
            model="grok-beta",
            tokens_used=0,
            cost=0.0,
            metadata={"articles_count": len(news_articles)}
        )

class ClaudeAnalyzer(BaseLLM):
    """Anthropic Claude integration"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "claude-3-sonnet-20240229")
        self.client = anthropic.Anthropic(api_key=api_key)
    
    async def analyze_sentiment(self, text: str) -> LLMResponse:
        """Analyze sentiment using Claude"""
        prompt = f"""
        Analyze the sentiment of the following text for cryptocurrency trading:
        
        Text: {text}
        
        Provide a JSON response with:
        - sentiment: "bullish", "bearish", or "neutral"
        - confidence: float between 0 and 1
        - key_factors: list of factors
        - market_impact: potential impact description
        """
        
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=500,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            
            # Parse JSON response
            try:
                parsed = json.loads(content)
                confidence = parsed.get('confidence', 0.5)
            except:
                confidence = 0.5
            
            return LLMResponse(
                content=content,
                confidence=confidence,
                model=self.model_name,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                cost=0.0,
                metadata={"model": self.model_name}
            )
            
        except Exception as e:
            self.logger.error(f"Claude sentiment analysis failed: {e}")
            return LLMResponse(
                content="Error analyzing sentiment",
                confidence=0.0,
                model=self.model_name,
                tokens_used=0,
                cost=0.0,
                metadata={"error": str(e)}
            )
    
    async def generate_trading_insights(self, market_data: Dict) -> LLMResponse:
        """Generate trading insights using Claude"""
        prompt = f"""
        Analyze the following market data and provide trading insights:
        
        Market Data: {json.dumps(market_data, indent=2)}
        
        Provide a comprehensive analysis including:
        1. Technical analysis summary
        2. Key support/resistance levels
        3. Trading recommendations
        4. Risk assessment
        5. Confidence level
        """
        
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=800,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            
            return LLMResponse(
                content=content,
                confidence=0.7,
                model=self.model_name,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                cost=0.0,
                metadata={"market_data": market_data}
            )
            
        except Exception as e:
            self.logger.error(f"Claude trading insights failed: {e}")
            return LLMResponse(
                content="Error generating trading insights",
                confidence=0.0,
                model=self.model_name,
                tokens_used=0,
                cost=0.0,
                metadata={"error": str(e)}
            )
    
    async def analyze_news(self, news_articles: List[str]) -> LLMResponse:
        """Analyze news articles using Claude"""
        articles_text = "\n\n".join(news_articles)
        prompt = f"""
        Analyze the following news articles for cryptocurrency market impact:
        
        Articles:
        {articles_text}
        
        Provide analysis of:
        1. Overall market sentiment
        2. Key events and their impact
        3. Affected cryptocurrencies
        4. Trading implications
        """
        
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=600,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            
            return LLMResponse(
                content=content,
                confidence=0.6,
                model=self.model_name,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                cost=0.0,
                metadata={"articles_count": len(news_articles)}
            )
            
        except Exception as e:
            self.logger.error(f"Claude news analysis failed: {e}")
            return LLMResponse(
                content="Error analyzing news",
                confidence=0.0,
                model=self.model_name,
                tokens_used=0,
                cost=0.0,
                metadata={"error": str(e)}
            )

class MistralAnalyzer(BaseLLM):
    """Mistral AI integration"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "mistral-large-latest")
        self.base_url = "https://api.mistral.ai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def analyze_sentiment(self, text: str) -> LLMResponse:
        """Analyze sentiment using Mistral"""
        prompt = f"""
        Analyze the sentiment of the following text for cryptocurrency trading:
        
        Text: {text}
        
        Provide sentiment analysis with confidence score.
        """
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.3
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                return LLMResponse(
                    content=content,
                    confidence=0.6,
                    model=self.model_name,
                    tokens_used=result['usage']['total_tokens'],
                    cost=0.0,
                    metadata={"model": self.model_name}
                )
            else:
                raise Exception(f"Mistral API error: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Mistral sentiment analysis failed: {e}")
            return LLMResponse(
                content="Error analyzing sentiment",
                confidence=0.0,
                model=self.model_name,
                tokens_used=0,
                cost=0.0,
                metadata={"error": str(e)}
            )
    
    async def generate_trading_insights(self, market_data: Dict) -> LLMResponse:
        """Generate trading insights using Mistral"""
        prompt = f"""
        Analyze the following market data and provide trading insights:
        
        Market Data: {json.dumps(market_data, indent=2)}
        
        Provide technical analysis and trading recommendations.
        """
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 800,
                    "temperature": 0.2
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                return LLMResponse(
                    content=content,
                    confidence=0.7,
                    model=self.model_name,
                    tokens_used=result['usage']['total_tokens'],
                    cost=0.0,
                    metadata={"market_data": market_data}
                )
            else:
                raise Exception(f"Mistral API error: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Mistral trading insights failed: {e}")
            return LLMResponse(
                content="Error generating trading insights",
                confidence=0.0,
                model=self.model_name,
                tokens_used=0,
                cost=0.0,
                metadata={"error": str(e)}
            )
    
    async def analyze_news(self, news_articles: List[str]) -> LLMResponse:
        """Analyze news articles using Mistral"""
        articles_text = "\n\n".join(news_articles)
        prompt = f"""
        Analyze the following news articles for cryptocurrency market impact:
        
        Articles:
        {articles_text}
        
        Provide market impact analysis.
        """
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 600,
                    "temperature": 0.3
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                return LLMResponse(
                    content=content,
                    confidence=0.6,
                    model=self.model_name,
                    tokens_used=result['usage']['total_tokens'],
                    cost=0.0,
                    metadata={"articles_count": len(news_articles)}
                )
            else:
                raise Exception(f"Mistral API error: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Mistral news analysis failed: {e}")
            return LLMResponse(
                content="Error analyzing news",
                confidence=0.0,
                model=self.model_name,
                tokens_used=0,
                cost=0.0,
                metadata={"error": str(e)}
            )

class GeminiAnalyzer(BaseLLM):
    """Google Gemini integration"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "gemini-pro")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    async def analyze_sentiment(self, text: str) -> LLMResponse:
        """Analyze sentiment using Gemini"""
        prompt = f"""
        Analyze the sentiment of the following text for cryptocurrency trading:
        
        Text: {text}
        
        Provide sentiment analysis with confidence score.
        """
        
        try:
            response = self.model.generate_content(prompt)
            content = response.text
            
            return LLMResponse(
                content=content,
                confidence=0.6,
                model=self.model_name,
                tokens_used=0,  # Gemini doesn't provide token count in basic response
                cost=0.0,
                metadata={"model": self.model_name}
            )
            
        except Exception as e:
            self.logger.error(f"Gemini sentiment analysis failed: {e}")
            return LLMResponse(
                content="Error analyzing sentiment",
                confidence=0.0,
                model=self.model_name,
                tokens_used=0,
                cost=0.0,
                metadata={"error": str(e)}
            )
    
    async def generate_trading_insights(self, market_data: Dict) -> LLMResponse:
        """Generate trading insights using Gemini"""
        prompt = f"""
        Analyze the following market data and provide trading insights:
        
        Market Data: {json.dumps(market_data, indent=2)}
        
        Provide technical analysis and trading recommendations.
        """
        
        try:
            response = self.model.generate_content(prompt)
            content = response.text
            
            return LLMResponse(
                content=content,
                confidence=0.7,
                model=self.model_name,
                tokens_used=0,
                cost=0.0,
                metadata={"market_data": market_data}
            )
            
        except Exception as e:
            self.logger.error(f"Gemini trading insights failed: {e}")
            return LLMResponse(
                content="Error generating trading insights",
                confidence=0.0,
                model=self.model_name,
                tokens_used=0,
                cost=0.0,
                metadata={"error": str(e)}
            )
    
    async def analyze_news(self, news_articles: List[str]) -> LLMResponse:
        """Analyze news articles using Gemini"""
        articles_text = "\n\n".join(news_articles)
        prompt = f"""
        Analyze the following news articles for cryptocurrency market impact:
        
        Articles:
        {articles_text}
        
        Provide market impact analysis.
        """
        
        try:
            response = self.model.generate_content(prompt)
            content = response.text
            
            return LLMResponse(
                content=content,
                confidence=0.6,
                model=self.model_name,
                tokens_used=0,
                cost=0.0,
                metadata={"articles_count": len(news_articles)}
            )
            
        except Exception as e:
            self.logger.error(f"Gemini news analysis failed: {e}")
            return LLMResponse(
                content="Error analyzing news",
                confidence=0.0,
                model=self.model_name,
                tokens_used=0,
                cost=0.0,
                metadata={"error": str(e)}
            )

class LLMOrchestrator:
    """Orchestrates multiple LLM models for enhanced analysis"""
    
    def __init__(self, api_keys: Dict[str, str]):
        self.analyzers = {}
        
        # Initialize available analyzers
        if 'deepseek' in api_keys:
            self.analyzers['deepseek'] = DeepSeekAnalyzer(api_keys['deepseek'])
        if 'grok' in api_keys:
            self.analyzers['grok'] = GrokAnalyzer(api_keys['grok'])
        if 'claude' in api_keys:
            self.analyzers['claude'] = ClaudeAnalyzer(api_keys['claude'])
        if 'mistral' in api_keys:
            self.analyzers['mistral'] = MistralAnalyzer(api_keys['mistral'])
        if 'gemini' in api_keys:
            self.analyzers['gemini'] = GeminiAnalyzer(api_keys['gemini'])
        
        self.logger = logging.getLogger(__name__)
    
    async def ensemble_sentiment_analysis(self, text: str) -> Dict[str, LLMResponse]:
        """Run sentiment analysis across all available models"""
        results = {}
        
        for name, analyzer in self.analyzers.items():
            try:
                results[name] = await analyzer.analyze_sentiment(text)
            except Exception as e:
                self.logger.error(f"Error with {name} sentiment analysis: {e}")
        
        return results
    
    async def ensemble_trading_insights(self, market_data: Dict) -> Dict[str, LLMResponse]:
        """Run trading insights across all available models"""
        results = {}
        
        for name, analyzer in self.analyzers.items():
            try:
                results[name] = await analyzer.generate_trading_insights(market_data)
            except Exception as e:
                self.logger.error(f"Error with {name} trading insights: {e}")
        
        return results
    
    async def ensemble_news_analysis(self, news_articles: List[str]) -> Dict[str, LLMResponse]:
        """Run news analysis across all available models"""
        results = {}
        
        for name, analyzer in self.analyzers.items():
            try:
                results[name] = await analyzer.analyze_news(news_articles)
            except Exception as e:
                self.logger.error(f"Error with {name} news analysis: {e}")
        
        return results
    
    def get_consensus_analysis(self, results: Dict[str, LLMResponse]) -> Dict:
        """Generate consensus analysis from multiple LLM responses"""
        if not results:
            return {"consensus": "No analysis available", "confidence": 0.0}
        
        # Calculate average confidence
        confidences = [r.confidence for r in results.values() if r.confidence > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Generate consensus summary
        consensus_summary = f"Analysis from {len(results)} models with {avg_confidence:.2f} average confidence."
        
        return {
            "consensus": consensus_summary,
            "confidence": avg_confidence,
            "model_count": len(results),
            "individual_results": {name: r.content[:200] + "..." for name, r in results.items()}
        }
