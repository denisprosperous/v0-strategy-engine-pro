import requests
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

class SentimentAnalyzer:
    """Advanced sentiment analysis for cryptocurrency markets"""
    
    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        self.api_keys = api_keys or {}
        self.logger = logging.getLogger(__name__)
        self.vader_analyzer = SentimentIntensityAnalyzer()
        
        # News API configuration
        self.news_api_key = self.api_keys.get('news_api')
        self.news_api_url = "https://newsapi.org/v2/everything"
        
        # Social media APIs (placeholder)
        self.twitter_api_key = self.api_keys.get('twitter_api')
        self.reddit_api_key = self.api_keys.get('reddit_api')
    
    async def get_comprehensive_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive sentiment analysis from multiple sources"""
        try:
            results = {}
            
            # News sentiment
            news_sentiment = await self.get_news_sentiment(symbol)
            results['news'] = news_sentiment
            
            # Social media sentiment
            social_sentiment = await self.get_social_sentiment(symbol)
            results['social'] = social_sentiment
            
            # Reddit sentiment
            reddit_sentiment = await self.get_reddit_sentiment(symbol)
            results['reddit'] = reddit_sentiment
            
            # Twitter sentiment
            twitter_sentiment = await self.get_twitter_sentiment(symbol)
            results['twitter'] = twitter_sentiment
            
            # Calculate composite sentiment
            composite_sentiment = self.calculate_composite_sentiment(results)
            results['composite'] = composite_sentiment
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error getting comprehensive sentiment for {symbol}: {e}")
            return {
                'news': {'score': 0, 'articles': []},
                'social': {'score': 0, 'mentions': 0},
                'reddit': {'score': 0, 'posts': []},
                'twitter': {'score': 0, 'tweets': []},
                'composite': {'score': 0, 'confidence': 0}
            }
    
    async def get_news_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Analyze news sentiment for a symbol"""
        try:
            if not self.news_api_key:
                return {'score': 0, 'articles': [], 'error': 'No News API key'}
            
            # Get news articles
            articles = await self.fetch_news_articles(symbol)
            
            if not articles:
                return {'score': 0, 'articles': [], 'error': 'No articles found'}
            
            # Analyze sentiment for each article
            sentiments = []
            for article in articles:
                title_sentiment = self.analyze_text_sentiment(article.get('title', ''))
                description_sentiment = self.analyze_text_sentiment(article.get('description', ''))
                
                # Weight title more heavily than description
                article_sentiment = (title_sentiment * 0.7) + (description_sentiment * 0.3)
                sentiments.append(article_sentiment)
                
                article['sentiment'] = article_sentiment
            
            # Calculate average sentiment
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
            
            return {
                'score': avg_sentiment,
                'articles': articles,
                'article_count': len(articles),
                'positive_articles': len([s for s in sentiments if s > 0.1]),
                'negative_articles': len([s for s in sentiments if s < -0.1]),
                'neutral_articles': len([s for s in sentiments if -0.1 <= s <= 0.1])
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing news sentiment: {e}")
            return {'score': 0, 'articles': [], 'error': str(e)}
    
    async def fetch_news_articles(self, symbol: str, days: int = 7) -> List[Dict[str, Any]]:
        """Fetch news articles for a symbol"""
        try:
            # Extract base symbol (e.g., 'BTC' from 'BTC/USDT')
            base_symbol = symbol.split('/')[0] if '/' in symbol else symbol
            
            # Search terms
            search_terms = [
                f"{base_symbol} cryptocurrency",
                f"{base_symbol} bitcoin" if base_symbol == "BTC" else f"{base_symbol} crypto",
                f"{base_symbol} price",
                f"{base_symbol} market"
            ]
            
            all_articles = []
            
            for term in search_terms:
                params = {
                    'q': term,
                    'apiKey': self.news_api_key,
                    'language': 'en',
                    'sortBy': 'publishedAt',
                    'from': (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
                    'pageSize': 20
                }
                
                response = requests.get(self.news_api_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get('articles', [])
                    all_articles.extend(articles)
                else:
                    self.logger.warning(f"News API error: {response.status_code}")
            
            # Remove duplicates and limit results
            unique_articles = []
            seen_urls = set()
            
            for article in all_articles:
                if article.get('url') and article['url'] not in seen_urls:
                    unique_articles.append(article)
                    seen_urls.add(article['url'])
            
            return unique_articles[:50]  # Limit to 50 articles
            
        except Exception as e:
            self.logger.error(f"Error fetching news articles: {e}")
            return []
    
    def analyze_text_sentiment(self, text: str) -> float:
        """Analyze sentiment of text using multiple methods"""
        if not text or len(text.strip()) < 10:
            return 0.0
        
        try:
            # TextBlob sentiment
            blob = TextBlob(text)
            textblob_sentiment = blob.sentiment.polarity
            
            # VADER sentiment
            vader_scores = self.vader_analyzer.polarity_scores(text)
            vader_sentiment = vader_scores['compound']
            
            # Combine scores (weighted average)
            combined_sentiment = (textblob_sentiment * 0.4) + (vader_sentiment * 0.6)
            
            return combined_sentiment
            
        except Exception as e:
            self.logger.error(f"Error analyzing text sentiment: {e}")
            return 0.0
    
    async def get_social_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Get social media sentiment (placeholder implementation)"""
        try:
            # This would integrate with social media APIs
            # For now, return simulated data
            
            base_symbol = symbol.split('/')[0] if '/' in symbol else symbol
            
            # Simulate social media sentiment
            import random
            sentiment_score = random.uniform(-0.5, 0.5)
            mentions = random.randint(100, 1000)
            
            return {
                'score': sentiment_score,
                'mentions': mentions,
                'platforms': ['twitter', 'reddit', 'telegram'],
                'trending': mentions > 500
            }
            
        except Exception as e:
            self.logger.error(f"Error getting social sentiment: {e}")
            return {'score': 0, 'mentions': 0, 'error': str(e)}
    
    async def get_reddit_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Get Reddit sentiment (placeholder implementation)"""
        try:
            # This would integrate with Reddit API
            # For now, return simulated data
            
            base_symbol = symbol.split('/')[0] if '/' in symbol else symbol
            
            # Simulate Reddit sentiment
            import random
            sentiment_score = random.uniform(-0.3, 0.3)
            posts = random.randint(10, 100)
            
            return {
                'score': sentiment_score,
                'posts': posts,
                'subreddits': ['cryptocurrency', 'bitcoin', 'altcoin'],
                'top_posts': []
            }
            
        except Exception as e:
            self.logger.error(f"Error getting Reddit sentiment: {e}")
            return {'score': 0, 'posts': 0, 'error': str(e)}
    
    async def get_twitter_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Get Twitter sentiment (placeholder implementation)"""
        try:
            # This would integrate with Twitter API
            # For now, return simulated data
            
            base_symbol = symbol.split('/')[0] if '/' in symbol else symbol
            
            # Simulate Twitter sentiment
            import random
            sentiment_score = random.uniform(-0.4, 0.4)
            tweets = random.randint(50, 500)
            
            return {
                'score': sentiment_score,
                'tweets': tweets,
                'hashtags': [f'#{base_symbol}', f'#{base_symbol}USD', 'crypto'],
                'influencers': []
            }
            
        except Exception as e:
            self.logger.error(f"Error getting Twitter sentiment: {e}")
            return {'score': 0, 'tweets': 0, 'error': str(e)}
    
    def calculate_composite_sentiment(self, sentiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate composite sentiment from multiple sources"""
        try:
            # Extract individual scores
            news_score = sentiment_data.get('news', {}).get('score', 0)
            social_score = sentiment_data.get('social', {}).get('score', 0)
            reddit_score = sentiment_data.get('reddit', {}).get('score', 0)
            twitter_score = sentiment_data.get('twitter', {}).get('score', 0)
            
            # Weight different sources
            weights = {
                'news': 0.4,      # News is most important
                'social': 0.2,    # General social media
                'reddit': 0.2,    # Reddit community
                'twitter': 0.2    # Twitter sentiment
            }
            
            # Calculate weighted average
            composite_score = (
                news_score * weights['news'] +
                social_score * weights['social'] +
                reddit_score * weights['reddit'] +
                twitter_score * weights['twitter']
            )
            
            # Calculate confidence based on data availability
            available_sources = sum(1 for source in [news_score, social_score, reddit_score, twitter_score] if source != 0)
            confidence = min(available_sources / 4, 1.0)
            
            # Determine sentiment category
            if composite_score > 0.2:
                sentiment_category = 'bullish'
            elif composite_score < -0.2:
                sentiment_category = 'bearish'
            else:
                sentiment_category = 'neutral'
            
            return {
                'score': composite_score,
                'confidence': confidence,
                'category': sentiment_category,
                'sources': {
                    'news': news_score,
                    'social': social_score,
                    'reddit': reddit_score,
                    'twitter': twitter_score
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating composite sentiment: {e}")
            return {
                'score': 0,
                'confidence': 0,
                'category': 'neutral',
                'sources': {}
            }
    
    def get_sentiment_trend(self, symbol: str, days: int = 7) -> Dict[str, Any]:
        """Get sentiment trend over time"""
        try:
            # This would fetch historical sentiment data
            # For now, return simulated trend data
            
            import random
            import numpy as np
            
            # Generate simulated trend data
            dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days, 0, -1)]
            base_sentiment = random.uniform(-0.3, 0.3)
            
            # Add some trend and noise
            trend = np.linspace(-0.1, 0.1, days)
            noise = np.random.normal(0, 0.1, days)
            sentiments = base_sentiment + trend + noise
            
            # Ensure sentiments are within [-1, 1] range
            sentiments = np.clip(sentiments, -1, 1)
            
            trend_data = []
            for date, sentiment in zip(dates, sentiments):
                trend_data.append({
                    'date': date,
                    'sentiment': float(sentiment),
                    'category': 'bullish' if sentiment > 0.1 else 'bearish' if sentiment < -0.1 else 'neutral'
                })
            
            # Calculate trend direction
            if len(sentiments) >= 2:
                trend_direction = 'increasing' if sentiments[-1] > sentiments[0] else 'decreasing'
                trend_strength = abs(sentiments[-1] - sentiments[0])
            else:
                trend_direction = 'stable'
                trend_strength = 0
            
            return {
                'trend_data': trend_data,
                'trend_direction': trend_direction,
                'trend_strength': trend_strength,
                'current_sentiment': float(sentiments[-1]) if len(sentiments) > 0 else 0,
                'average_sentiment': float(np.mean(sentiments))
            }
            
        except Exception as e:
            self.logger.error(f"Error getting sentiment trend: {e}")
            return {
                'trend_data': [],
                'trend_direction': 'stable',
                'trend_strength': 0,
                'current_sentiment': 0,
                'average_sentiment': 0
            }
    
    def analyze_market_sentiment(self, symbol: str, price_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze sentiment in relation to price action"""
        try:
            if price_data.empty or len(price_data) < 20:
                return {'sentiment': 0, 'price_correlation': 0}
            
            # Get sentiment data
            sentiment_data = await self.get_comprehensive_sentiment(symbol)
            composite_sentiment = sentiment_data.get('composite', {}).get('score', 0)
            
            # Calculate price momentum
            price_data['returns'] = price_data['close'].pct_change()
            price_data['momentum'] = price_data['returns'].rolling(5).mean()
            
            current_momentum = price_data['momentum'].iloc[-1] if len(price_data) > 0 else 0
            
            # Calculate correlation between sentiment and price
            if len(price_data) >= 20:
                sentiment_series = pd.Series([composite_sentiment] * len(price_data))
                price_series = price_data['returns'].fillna(0)
                correlation = sentiment_series.corr(price_series)
            else:
                correlation = 0
            
            # Determine sentiment-price alignment
            sentiment_price_alignment = 'aligned' if (
                (composite_sentiment > 0 and current_momentum > 0) or
                (composite_sentiment < 0 and current_momentum < 0)
            ) else 'diverging'
            
            return {
                'sentiment': composite_sentiment,
                'price_momentum': current_momentum,
                'price_correlation': correlation,
                'alignment': sentiment_price_alignment,
                'confidence': sentiment_data.get('composite', {}).get('confidence', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing market sentiment: {e}")
            return {'sentiment': 0, 'price_correlation': 0, 'error': str(e)}
