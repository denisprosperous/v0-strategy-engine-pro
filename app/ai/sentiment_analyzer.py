import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import aiohttp
import json
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import openai
from transformers import pipeline

from app.config.settings import settings

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """Advanced sentiment analysis engine for market data"""
    
    def __init__(self):
        self.openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.vader_analyzer = SentimentIntensityAnalyzer()
        
        # Initialize HuggingFace sentiment pipeline
        try:
            self.hf_sentiment = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                token=settings.huggingface_token
            )
        except Exception as e:
            logger.warning(f"Could not initialize HuggingFace pipeline: {e}")
            self.hf_sentiment = None
        
        # News sources configuration
        self.news_sources = {
            'mediastack': {
                'api_key': settings.mediastack_api_key,
                'base_url': 'http://api.mediastack.com/v1/news',
                'quota': 100  # calls per month
            },
            'currents': {
                'api_key': settings.currents_api_key,
                'base_url': 'https://api.currentsapi.services/v1/search',
                'quota': 20  # calls per day
            }
        }
        
        # Sentiment cache
        self.sentiment_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
    async def analyze_text_sentiment(self, text: str, source: str = "general") -> Dict[str, Any]:
        """Analyze sentiment of a single text using multiple models"""
        try:
            results = {}
            
            # TextBlob analysis
            blob = TextBlob(text)
            results['textblob'] = {
                'polarity': blob.sentiment.polarity,  # -1 to 1
                'subjectivity': blob.sentiment.subjectivity,  # 0 to 1
                'confidence': 0.7  # Medium confidence for TextBlob
            }
            
            # VADER analysis
            vader_scores = self.vader_analyzer.polarity_scores(text)
            results['vader'] = {
                'compound': vader_scores['compound'],  # -1 to 1
                'positive': vader_scores['pos'],
                'negative': vader_scores['neg'],
                'neutral': vader_scores['neu'],
                'confidence': 0.8  # High confidence for VADER
            }
            
            # HuggingFace analysis (if available)
            if self.hf_sentiment:
                try:
                    hf_result = self.hf_sentiment(text)[0]
                    # Map labels to sentiment scores
                    label_mapping = {
                        'LABEL_0': -1,  # Negative
                        'LABEL_1': 0,   # Neutral
                        'LABEL_2': 1    # Positive
                    }
                    hf_score = label_mapping.get(hf_result['label'], 0)
                    results['huggingface'] = {
                        'score': hf_score,
                        'confidence': hf_result['score'],
                        'label': hf_result['label']
                    }
                except Exception as e:
                    logger.warning(f"HuggingFace analysis failed: {e}")
            
            # OpenAI analysis for complex sentiment
            try:
                openai_result = await self._analyze_with_openai(text, source)
                results['openai'] = openai_result
            except Exception as e:
                logger.warning(f"OpenAI analysis failed: {e}")
            
            # Calculate weighted average sentiment
            weighted_sentiment = self._calculate_weighted_sentiment(results)
            
            return {
                'text': text[:200] + "..." if len(text) > 200 else text,  # Truncate for storage
                'source': source,
                'timestamp': datetime.utcnow().isoformat(),
                'individual_scores': results,
                'weighted_sentiment': weighted_sentiment['score'],
                'confidence': weighted_sentiment['confidence'],
                'sentiment_label': self._get_sentiment_label(weighted_sentiment['score'])
            }
            
        except Exception as e:
            logger.error(f"Error analyzing text sentiment: {e}")
            return {
                'text': text[:200] + "..." if len(text) > 200 else text,
                'source': source,
                'timestamp': datetime.utcnow().isoformat(),
                'weighted_sentiment': 0.0,
                'confidence': 0.0,
                'sentiment_label': 'neutral',
                'error': str(e)
            }
    
    async def _analyze_with_openai(self, text: str, source: str) -> Dict[str, Any]:
        """Analyze sentiment using OpenAI GPT"""
        try:
            prompt = f"""
            Analyze the sentiment of the following {source} text regarding cryptocurrency markets.
            Provide a sentiment score from -1 (very negative) to 1 (very positive) and confidence level from 0 to 1.
            
            Text: "{text}"
            
            Respond in JSON format:
            {{
                "sentiment_score": float,
                "confidence": float,
                "reasoning": "brief explanation",
                "market_impact": "low/medium/high"
            }}
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial sentiment analyst specializing in cryptocurrency markets."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                result = json.loads(result_text)
                return {
                    'score': result.get('sentiment_score', 0.0),
                    'confidence': result.get('confidence', 0.5),
                    'reasoning': result.get('reasoning', ''),
                    'market_impact': result.get('market_impact', 'low')
                }
            except json.JSONDecodeError:
                logger.warning("Failed to parse OpenAI response as JSON")
                return {'score': 0.0, 'confidence': 0.5, 'reasoning': 'Parse error'}
                
        except Exception as e:
            logger.error(f"OpenAI analysis error: {e}")
            return {'score': 0.0, 'confidence': 0.5, 'reasoning': str(e)}
    
    def _calculate_weighted_sentiment(self, results: Dict[str, Any]) -> Dict[str, float]:
        """Calculate weighted average sentiment from multiple models"""
        weights = {
            'textblob': 0.2,
            'vader': 0.3,
            'huggingface': 0.3,
            'openai': 0.2
        }
        
        total_score = 0.0
        total_weight = 0.0
        total_confidence = 0.0
        confidence_count = 0
        
        for model, weight in weights.items():
            if model in results:
                if model == 'textblob':
                    score = results[model]['polarity']
                    confidence = results[model]['confidence']
                elif model == 'vader':
                    score = results[model]['compound']
                    confidence = results[model]['confidence']
                elif model == 'huggingface':
                    score = results[model]['score']
                    confidence = results[model]['confidence']
                elif model == 'openai':
                    score = results[model]['score']
                    confidence = results[model]['confidence']
                else:
                    continue
                
                total_score += score * weight
                total_weight += weight
                total_confidence += confidence
                confidence_count += 1
        
        if total_weight == 0:
            return {'score': 0.0, 'confidence': 0.0}
        
        weighted_score = total_score / total_weight
        avg_confidence = total_confidence / confidence_count if confidence_count > 0 else 0.0
        
        return {
            'score': weighted_score,
            'confidence': avg_confidence
        }
    
    def _get_sentiment_label(self, score: float) -> str:
        """Convert sentiment score to label"""
        if score >= 0.3:
            return 'positive'
        elif score <= -0.3:
            return 'negative'
        else:
            return 'neutral'
    
    async def get_news_sentiment(self, symbol: str, hours: int = 24) -> Dict[str, Any]:
        """Get sentiment from news articles for a specific symbol"""
        try:
            # Check cache first
            cache_key = f"news_sentiment_{symbol}_{hours}"
            if cache_key in self.sentiment_cache:
                cached_data = self.sentiment_cache[cache_key]
                if datetime.utcnow() - cached_data['timestamp'] < timedelta(seconds=self.cache_ttl):
                    return cached_data['data']
            
            # Fetch news articles
            news_articles = await self._fetch_news_articles(symbol, hours)
            
            if not news_articles:
                return {
                    'symbol': symbol,
                    'sentiment_score': 0.0,
                    'confidence': 0.0,
                    'article_count': 0,
                    'articles': []
                }
            
            # Analyze sentiment for each article
            sentiments = []
            for article in news_articles:
                sentiment = await self.analyze_text_sentiment(
                    f"{article.get('title', '')} {article.get('description', '')}",
                    source="news"
                )
                sentiments.append(sentiment)
            
            # Calculate aggregate sentiment
            if sentiments:
                total_score = sum(s['weighted_sentiment'] for s in sentiments)
                total_confidence = sum(s['confidence'] for s in sentiments)
                avg_score = total_score / len(sentiments)
                avg_confidence = total_confidence / len(sentiments)
            else:
                avg_score = 0.0
                avg_confidence = 0.0
            
            result = {
                'symbol': symbol,
                'sentiment_score': avg_score,
                'confidence': avg_confidence,
                'article_count': len(news_articles),
                'sentiment_label': self._get_sentiment_label(avg_score),
                'articles': news_articles[:10],  # Limit to 10 articles
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Cache the result
            self.sentiment_cache[cache_key] = {
                'data': result,
                'timestamp': datetime.utcnow()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting news sentiment for {symbol}: {e}")
            return {
                'symbol': symbol,
                'sentiment_score': 0.0,
                'confidence': 0.0,
                'article_count': 0,
                'error': str(e)
            }
    
    async def _fetch_news_articles(self, symbol: str, hours: int) -> List[Dict[str, Any]]:
        """Fetch news articles from multiple sources"""
        articles = []
        
        # Keywords for search
        keywords = [symbol.replace('/', ''), symbol.split('/')[0]]  # BTC/USDT -> ['BTCUSDT', 'BTC']
        
        for source_name, source_config in self.news_sources.items():
            try:
                if source_name == 'mediastack':
                    source_articles = await self._fetch_mediastack_news(keywords, hours)
                elif source_name == 'currents':
                    source_articles = await self._fetch_currents_news(keywords, hours)
                else:
                    continue
                
                articles.extend(source_articles)
                
            except Exception as e:
                logger.warning(f"Failed to fetch from {source_name}: {e}")
                continue
        
        # Remove duplicates and sort by date
        unique_articles = []
        seen_titles = set()
        
        for article in articles:
            title = article.get('title', '').lower()
            if title not in seen_titles:
                seen_titles.add(title)
                unique_articles.append(article)
        
        return unique_articles[:50]  # Limit to 50 articles
    
    async def _fetch_mediastack_news(self, keywords: List[str], hours: int) -> List[Dict[str, Any]]:
        """Fetch news from MediaStack API"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'access_key': settings.mediastack_api_key,
                    'keywords': ' OR '.join(keywords),
                    'languages': 'en',
                    'sort': 'published_desc',
                    'limit': 25
                }
                
                async with session.get(self.news_sources['mediastack']['base_url'], params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('data', [])
                    else:
                        logger.warning(f"MediaStack API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching MediaStack news: {e}")
            return []
    
    async def _fetch_currents_news(self, keywords: List[str], hours: int) -> List[Dict[str, Any]]:
        """Fetch news from Currents API"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'apiKey': settings.currents_api_key,
                    'keyword': ' OR '.join(keywords),
                    'language': 'en',
                    'limit': 20
                }
                
                async with session.get(self.news_sources['currents']['base_url'], params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('news', [])
                    else:
                        logger.warning(f"Currents API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching Currents news: {e}")
            return []
    
    async def get_social_sentiment(self, symbol: str, hours: int = 24) -> Dict[str, Any]:
        """Get sentiment from social media (placeholder for future implementation)"""
        # This would integrate with Twitter, Reddit, etc.
        # For now, return a placeholder
        return {
            'symbol': symbol,
            'sentiment_score': 0.0,
            'confidence': 0.0,
            'source': 'social',
            'timestamp': datetime.utcnow().isoformat(),
            'note': 'Social sentiment analysis not yet implemented'
        }
    
    async def get_aggregate_sentiment(self, symbol: str, hours: int = 24) -> Dict[str, Any]:
        """Get aggregate sentiment from all sources"""
        try:
            # Get sentiment from different sources
            news_sentiment = await self.get_news_sentiment(symbol, hours)
            social_sentiment = await self.get_social_sentiment(symbol, hours)
            
            # Calculate weighted aggregate
            weights = {
                'news': 0.7,
                'social': 0.3
            }
            
            total_score = (
                news_sentiment['sentiment_score'] * weights['news'] +
                social_sentiment['sentiment_score'] * weights['social']
            )
            
            total_confidence = (
                news_sentiment['confidence'] * weights['news'] +
                social_sentiment['confidence'] * weights['social']
            )
            
            return {
                'symbol': symbol,
                'aggregate_sentiment': total_score,
                'confidence': total_confidence,
                'sentiment_label': self._get_sentiment_label(total_score),
                'sources': {
                    'news': news_sentiment,
                    'social': social_sentiment
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting aggregate sentiment for {symbol}: {e}")
            return {
                'symbol': symbol,
                'aggregate_sentiment': 0.0,
                'confidence': 0.0,
                'error': str(e)
            }
