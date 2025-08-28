import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import openai
import json

from app.config.settings import settings
from app.ai.sentiment_analyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)

class AIRecommendationEngine:
    """Advanced AI recommendation engine for trading decisions"""
    
    def __init__(self):
        self.openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # ML models
        self.price_prediction_model = None
        self.signal_classifier = None
        self.scaler = StandardScaler()
        
        # Model training data
        self.training_data = []
        self.model_last_updated = None
        
        # Recommendation cache
        self.recommendation_cache = {}
        self.cache_ttl = 600  # 10 minutes
        
    async def generate_recommendation(self, symbol: str, exchange: str, 
                                    market_data: Dict[str, Any], 
                                    sentiment_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate comprehensive trading recommendation"""
        try:
            # Check cache first
            cache_key = f"recommendation_{symbol}_{exchange}"
            if cache_key in self.recommendation_cache:
                cached_data = self.recommendation_cache[cache_key]
                if datetime.utcnow() - cached_data['timestamp'] < timedelta(seconds=self.cache_ttl):
                    return cached_data['data']
            
            # Get sentiment data if not provided
            if not sentiment_data:
                sentiment_data = await self.sentiment_analyzer.get_aggregate_sentiment(symbol, hours=24)
            
            # Calculate technical indicators
            technical_indicators = self._calculate_technical_indicators(market_data)
            
            # Generate ML-based prediction
            ml_prediction = await self._generate_ml_prediction(symbol, market_data, technical_indicators, sentiment_data)
            
            # Generate AI analysis
            ai_analysis = await self._generate_ai_analysis(symbol, market_data, technical_indicators, sentiment_data)
            
            # Calculate risk assessment
            risk_assessment = self._calculate_risk_assessment(market_data, technical_indicators, sentiment_data)
            
            # Generate final recommendation
            recommendation = self._generate_final_recommendation(
                symbol, ml_prediction, ai_analysis, risk_assessment, technical_indicators
            )
            
            # Cache the result
            self.recommendation_cache[cache_key] = {
                'data': recommendation,
                'timestamp': datetime.utcnow()
            }
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error generating recommendation for {symbol}: {e}")
            return {
                'symbol': symbol,
                'recommendation': 'hold',
                'confidence': 0.0,
                'reasoning': f'Error generating recommendation: {str(e)}',
                'risk_level': 'high',
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _calculate_technical_indicators(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate technical indicators from market data"""
        try:
            ohlcv = market_data.get('ohlcv', [])
            if not ohlcv or len(ohlcv) < 50:
                return {}
            
            closes = [candle['close'] for candle in ohlcv]
            highs = [candle['high'] for candle in ohlcv]
            lows = [candle['low'] for candle in ohlcv]
            volumes = [candle['volume'] for candle in ohlcv]
            
            indicators = {}
            
            # Moving averages
            indicators['sma_20'] = np.mean(closes[-20:]) if len(closes) >= 20 else closes[-1]
            indicators['sma_50'] = np.mean(closes[-50:]) if len(closes) >= 50 else closes[-1]
            indicators['ema_12'] = self._calculate_ema(closes, 12)
            indicators['ema_26'] = self._calculate_ema(closes, 26)
            
            # RSI
            indicators['rsi'] = self._calculate_rsi(closes, 14)
            
            # MACD
            macd_line, signal_line, histogram = self._calculate_macd(closes)
            indicators['macd_line'] = macd_line
            indicators['macd_signal'] = signal_line
            indicators['macd_histogram'] = histogram
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(closes, 20)
            indicators['bb_upper'] = bb_upper
            indicators['bb_middle'] = bb_middle
            indicators['bb_lower'] = bb_lower
            indicators['bb_position'] = (closes[-1] - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
            
            # Volume indicators
            indicators['volume_sma'] = np.mean(volumes[-20:]) if len(volumes) >= 20 else volumes[-1]
            indicators['volume_ratio'] = volumes[-1] / indicators['volume_sma'] if indicators['volume_sma'] > 0 else 1.0
            
            # Price momentum
            indicators['price_momentum'] = (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 else 0.0
            indicators['price_acceleration'] = (closes[-1] - 2 * closes[-2] + closes[-3]) / closes[-3] if len(closes) >= 3 else 0.0
            
            # Volatility
            returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
            indicators['volatility'] = np.std(returns[-20:]) if len(returns) >= 20 else 0.0
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            return {}
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1]
        
        alpha = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        
        return ema
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index)"""
        if len(prices) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(prices) < slow:
            return 0.0, 0.0, 0.0
        
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        macd_line = ema_fast - ema_slow
        
        # For simplicity, we'll use a simple average for signal line
        # In practice, you'd want to calculate EMA of MACD line
        signal_line = macd_line * 0.8  # Simplified
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return prices[-1], prices[-1], prices[-1]
        
        recent_prices = prices[-period:]
        sma = np.mean(recent_prices)
        std = np.std(recent_prices)
        
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        return upper_band, sma, lower_band
    
    async def _generate_ml_prediction(self, symbol: str, market_data: Dict[str, Any], 
                                    technical_indicators: Dict[str, float], 
                                    sentiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate ML-based price prediction"""
        try:
            # Prepare features
            features = []
            
            # Technical indicators
            for indicator, value in technical_indicators.items():
                features.append(value)
            
            # Sentiment features
            features.append(sentiment_data.get('aggregate_sentiment', 0.0))
            features.append(sentiment_data.get('confidence', 0.0))
            
            # Market data features
            ohlcv = market_data.get('ohlcv', [])
            if ohlcv:
                features.extend([
                    ohlcv[-1]['close'],
                    ohlcv[-1]['volume'],
                    (ohlcv[-1]['high'] - ohlcv[-1]['low']) / ohlcv[-1]['close'],  # Volatility
                ])
            
            # Normalize features
            features_array = np.array(features).reshape(1, -1)
            
            # For now, return a simple prediction based on technical indicators
            # In a full implementation, you'd use trained ML models
            
            prediction_score = self._simple_prediction_score(technical_indicators, sentiment_data)
            
            return {
                'prediction_type': 'price_direction',
                'prediction_score': prediction_score,
                'confidence': 0.7,
                'time_horizon': '24h',
                'features_used': len(features)
            }
            
        except Exception as e:
            logger.error(f"Error generating ML prediction: {e}")
            return {
                'prediction_type': 'price_direction',
                'prediction_score': 0.0,
                'confidence': 0.0,
                'time_horizon': '24h',
                'error': str(e)
            }
    
    def _simple_prediction_score(self, technical_indicators: Dict[str, float], 
                                sentiment_data: Dict[str, Any]) -> float:
        """Simple prediction score based on technical indicators and sentiment"""
        score = 0.0
        weight = 0.0
        
        # RSI signals
        rsi = technical_indicators.get('rsi', 50.0)
        if rsi < 30:
            score += 0.3  # Oversold - bullish signal
            weight += 0.3
        elif rsi > 70:
            score -= 0.3  # Overbought - bearish signal
            weight += 0.3
        
        # Moving average signals
        sma_20 = technical_indicators.get('sma_20', 0)
        sma_50 = technical_indicators.get('sma_50', 0)
        if sma_20 > sma_50:
            score += 0.2  # Golden cross
            weight += 0.2
        else:
            score -= 0.2  # Death cross
            weight += 0.2
        
        # MACD signals
        macd_histogram = technical_indicators.get('macd_histogram', 0)
        if macd_histogram > 0:
            score += 0.2
            weight += 0.2
        else:
            score -= 0.2
            weight += 0.2
        
        # Bollinger Bands position
        bb_position = technical_indicators.get('bb_position', 0.5)
        if bb_position < 0.2:
            score += 0.2  # Near lower band - potential bounce
            weight += 0.2
        elif bb_position > 0.8:
            score -= 0.2  # Near upper band - potential reversal
            weight += 0.2
        
        # Sentiment
        sentiment_score = sentiment_data.get('aggregate_sentiment', 0.0)
        score += sentiment_score * 0.3
        weight += 0.3
        
        # Normalize score
        if weight > 0:
            return score / weight
        else:
            return 0.0
    
    async def _generate_ai_analysis(self, symbol: str, market_data: Dict[str, Any], 
                                  technical_indicators: Dict[str, float], 
                                  sentiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI analysis using OpenAI"""
        try:
            # Prepare market summary
            current_price = market_data.get('current_price', 0)
            price_change_24h = market_data.get('price_change_24h', 0)
            volume_24h = market_data.get('volume_24h', 0)
            
            # Create analysis prompt
            prompt = f"""
            Analyze the trading opportunity for {symbol} based on the following data:
            
            Current Price: ${current_price:,.2f}
            24h Change: {price_change_24h:+.2f}%
            24h Volume: ${volume_24h:,.0f}
            
            Technical Indicators:
            - RSI: {technical_indicators.get('rsi', 0):.2f}
            - MACD: {technical_indicators.get('macd_line', 0):.4f}
            - Bollinger Bands Position: {technical_indicators.get('bb_position', 0.5):.2f}
            - Volume Ratio: {technical_indicators.get('volume_ratio', 1.0):.2f}
            
            Sentiment Analysis:
            - Overall Sentiment: {sentiment_data.get('aggregate_sentiment', 0):.3f}
            - Confidence: {sentiment_data.get('confidence', 0):.2f}
            
            Provide a trading recommendation in JSON format:
            {{
                "recommendation": "buy/sell/hold",
                "confidence": 0.0-1.0,
                "reasoning": "detailed explanation",
                "risk_level": "low/medium/high",
                "expected_return": "percentage estimate",
                "time_horizon": "short/medium/long term",
                "key_factors": ["factor1", "factor2", "factor3"]
            }}
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert cryptocurrency trading analyst. Provide clear, actionable trading recommendations based on technical and fundamental analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                analysis = json.loads(result_text)
                return analysis
            except json.JSONDecodeError:
                logger.warning("Failed to parse AI analysis as JSON")
                return {
                    'recommendation': 'hold',
                    'confidence': 0.5,
                    'reasoning': 'AI analysis parse error',
                    'risk_level': 'medium'
                }
                
        except Exception as e:
            logger.error(f"Error generating AI analysis: {e}")
            return {
                'recommendation': 'hold',
                'confidence': 0.5,
                'reasoning': f'AI analysis error: {str(e)}',
                'risk_level': 'medium'
            }
    
    def _calculate_risk_assessment(self, market_data: Dict[str, Any], 
                                 technical_indicators: Dict[str, float], 
                                 sentiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive risk assessment"""
        try:
            risk_score = 0.0
            risk_factors = []
            
            # Volatility risk
            volatility = technical_indicators.get('volatility', 0.0)
            if volatility > 0.05:  # 5% daily volatility
                risk_score += 0.3
                risk_factors.append(f"High volatility: {volatility:.2%}")
            
            # Volume risk
            volume_ratio = technical_indicators.get('volume_ratio', 1.0)
            if volume_ratio < 0.5:
                risk_score += 0.2
                risk_factors.append(f"Low volume: {volume_ratio:.2f}x average")
            
            # Technical risk
            rsi = technical_indicators.get('rsi', 50.0)
            if rsi > 80 or rsi < 20:
                risk_score += 0.2
                risk_factors.append(f"Extreme RSI: {rsi:.1f}")
            
            # Sentiment risk
            sentiment_score = abs(sentiment_data.get('aggregate_sentiment', 0.0))
            if sentiment_score > 0.7:
                risk_score += 0.2
                risk_factors.append(f"Extreme sentiment: {sentiment_score:.2f}")
            
            # Market structure risk
            bb_position = technical_indicators.get('bb_position', 0.5)
            if bb_position > 0.9 or bb_position < 0.1:
                risk_score += 0.1
                risk_factors.append(f"Price at Bollinger Band extremes")
            
            # Normalize risk score
            risk_score = min(risk_score, 1.0)
            
            # Determine risk level
            if risk_score < 0.3:
                risk_level = "low"
            elif risk_score < 0.6:
                risk_level = "medium"
            else:
                risk_level = "high"
            
            return {
                'risk_score': risk_score,
                'risk_level': risk_level,
                'risk_factors': risk_factors,
                'max_position_size': self._calculate_max_position_size(risk_score)
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk assessment: {e}")
            return {
                'risk_score': 0.5,
                'risk_level': 'medium',
                'risk_factors': ['Risk calculation error'],
                'max_position_size': 0.01  # 1% default
            }
    
    def _calculate_max_position_size(self, risk_score: float) -> float:
        """Calculate maximum position size based on risk score"""
        # Higher risk = smaller position size
        base_size = 0.05  # 5% base position size
        risk_adjustment = 1.0 - risk_score
        return base_size * risk_adjustment
    
    def _generate_final_recommendation(self, symbol: str, ml_prediction: Dict[str, Any], 
                                     ai_analysis: Dict[str, Any], risk_assessment: Dict[str, Any],
                                     technical_indicators: Dict[str, float]) -> Dict[str, Any]:
        """Generate final trading recommendation"""
        try:
            # Combine ML and AI predictions
            ml_score = ml_prediction.get('prediction_score', 0.0)
            ai_recommendation = ai_analysis.get('recommendation', 'hold')
            ai_confidence = ai_analysis.get('confidence', 0.5)
            
            # Convert AI recommendation to score
            ai_score_map = {'buy': 1.0, 'sell': -1.0, 'hold': 0.0}
            ai_score = ai_score_map.get(ai_recommendation, 0.0)
            
            # Weighted combination
            ml_weight = 0.4
            ai_weight = 0.6
            
            combined_score = (ml_score * ml_weight) + (ai_score * ai_weight)
            combined_confidence = (ml_prediction.get('confidence', 0.5) * ml_weight) + (ai_confidence * ai_weight)
            
            # Determine final recommendation
            if combined_score > 0.3:
                final_recommendation = 'buy'
            elif combined_score < -0.3:
                final_recommendation = 'sell'
            else:
                final_recommendation = 'hold'
            
            # Calculate expected return
            expected_return = self._calculate_expected_return(combined_score, technical_indicators, risk_assessment)
            
            return {
                'symbol': symbol,
                'recommendation': final_recommendation,
                'confidence': combined_confidence,
                'score': combined_score,
                'expected_return': expected_return,
                'risk_level': risk_assessment['risk_level'],
                'max_position_size': risk_assessment['max_position_size'],
                'time_horizon': ai_analysis.get('time_horizon', '24h'),
                'reasoning': ai_analysis.get('reasoning', ''),
                'key_factors': ai_analysis.get('key_factors', []),
                'risk_factors': risk_assessment['risk_factors'],
                'technical_summary': {
                    'rsi': technical_indicators.get('rsi', 0),
                    'macd_signal': 'bullish' if technical_indicators.get('macd_histogram', 0) > 0 else 'bearish',
                    'bb_position': technical_indicators.get('bb_position', 0.5),
                    'volume_trend': 'high' if technical_indicators.get('volume_ratio', 1.0) > 1.5 else 'normal'
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating final recommendation: {e}")
            return {
                'symbol': symbol,
                'recommendation': 'hold',
                'confidence': 0.0,
                'reasoning': f'Error generating recommendation: {str(e)}',
                'risk_level': 'high',
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _calculate_expected_return(self, score: float, technical_indicators: Dict[str, float], 
                                 risk_assessment: Dict[str, Any]) -> float:
        """Calculate expected return based on score and risk"""
        # Base expected return based on score
        base_return = score * 0.05  # 5% max return
        
        # Adjust for volatility
        volatility = technical_indicators.get('volatility', 0.0)
        volatility_adjustment = 1.0 - (volatility * 2)  # Higher volatility reduces expected return
        
        # Adjust for risk
        risk_adjustment = 1.0 - risk_assessment['risk_score']
        
        expected_return = base_return * volatility_adjustment * risk_adjustment
        
        return max(min(expected_return, 0.10), -0.10)  # Cap between -10% and +10%
    
    async def get_top_recommendations(self, symbols: List[str], exchange: str, 
                                    limit: int = 10) -> List[Dict[str, Any]]:
        """Get top trading recommendations for multiple symbols"""
        try:
            recommendations = []
            
            for symbol in symbols:
                try:
                    # This would normally fetch market data from the exchange
                    # For now, we'll create mock data
                    mock_market_data = {
                        'current_price': 50000.0,
                        'price_change_24h': 2.5,
                        'volume_24h': 1000000,
                        'ohlcv': []  # Would contain actual OHLCV data
                    }
                    
                    recommendation = await self.generate_recommendation(
                        symbol, exchange, mock_market_data
                    )
                    
                    if recommendation['confidence'] > 0.6:  # Only high-confidence recommendations
                        recommendations.append(recommendation)
                        
                except Exception as e:
                    logger.warning(f"Error getting recommendation for {symbol}: {e}")
                    continue
            
            # Sort by confidence and expected return
            recommendations.sort(key=lambda x: (x['confidence'], x.get('expected_return', 0)), reverse=True)
            
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error getting top recommendations: {e}")
            return []
