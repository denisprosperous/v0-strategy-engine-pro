import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import asyncio
from enum import Enum

from ai_models.llm_integration import LLMOrchestrator
from technical_analysis.indicators import TechnicalIndicators
from sentiment_analysis.sentiment_analyzer import SentimentAnalyzer
from on_chain.on_chain_analyzer import OnChainAnalyzer

class SignalType(Enum):
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"
    ON_CHAIN = "on_chain"
    FUNDAMENTAL = "fundamental"
    SOCIAL = "social"
    COMPOSITE = "composite"

class SignalStrength(Enum):
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    VERY_STRONG = 4

@dataclass
class TradingSignal:
    """Comprehensive trading signal data structure"""
    symbol: str
    signal_type: SignalType
    direction: str  # 'buy', 'sell', 'hold'
    strength: SignalStrength
    confidence: float  # 0-1
    price: float
    timestamp: datetime
    indicators: Dict[str, Any]
    description: str
    risk_level: str  # 'low', 'medium', 'high'
    time_horizon: str  # 'short', 'medium', 'long'
    metadata: Dict[str, Any]

class SignalGenerator:
    """Advanced signal generation system"""
    
    def __init__(self, llm_orchestrator: LLMOrchestrator):
        self.llm_orchestrator = llm_orchestrator
        self.technical_indicators = TechnicalIndicators()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.on_chain_analyzer = OnChainAnalyzer()
        self.logger = logging.getLogger(__name__)
        
        # Signal weights for composite signals
        self.signal_weights = {
            SignalType.TECHNICAL: 0.4,
            SignalType.SENTIMENT: 0.2,
            SignalType.ON_CHAIN: 0.2,
            SignalType.FUNDAMENTAL: 0.1,
            SignalType.SOCIAL: 0.1
        }
    
    async def generate_comprehensive_signals(self, symbol: str, market_data: pd.DataFrame) -> List[TradingSignal]:
        """Generate comprehensive trading signals using all available data"""
        signals = []
        
        # Generate technical signals
        technical_signals = await self.generate_technical_signals(symbol, market_data)
        signals.extend(technical_signals)
        
        # Generate sentiment signals
        sentiment_signals = await self.generate_sentiment_signals(symbol)
        signals.extend(sentiment_signals)
        
        # Generate on-chain signals
        on_chain_signals = await self.generate_on_chain_signals(symbol)
        signals.extend(on_chain_signals)
        
        # Generate fundamental signals
        fundamental_signals = await self.generate_fundamental_signals(symbol)
        signals.extend(fundamental_signals)
        
        # Generate social signals
        social_signals = await self.generate_social_signals(symbol)
        signals.extend(social_signals)
        
        # Generate composite signal
        composite_signal = self.generate_composite_signal(symbol, signals)
        if composite_signal:
            signals.append(composite_signal)
        
        return signals
    
    async def generate_technical_signals(self, symbol: str, market_data: pd.DataFrame) -> List[TradingSignal]:
        """Generate technical analysis signals"""
        signals = []
        
        try:
            # Calculate technical indicators
            indicators = self.technical_indicators.calculate_all(market_data)
            
            # RSI signals
            rsi = indicators.get('rsi', [])
            if len(rsi) > 0:
                current_rsi = rsi[-1]
                if current_rsi < 30:
                    signals.append(TradingSignal(
                        symbol=symbol,
                        signal_type=SignalType.TECHNICAL,
                        direction='buy',
                        strength=SignalStrength.STRONG if current_rsi < 20 else SignalStrength.MODERATE,
                        confidence=0.8 if current_rsi < 20 else 0.6,
                        price=market_data['close'].iloc[-1],
                        timestamp=datetime.now(),
                        indicators={'rsi': current_rsi},
                        description=f"RSI oversold signal: {current_rsi:.2f}",
                        risk_level='low',
                        time_horizon='short',
                        metadata={'indicator': 'rsi', 'value': current_rsi}
                    ))
                elif current_rsi > 70:
                    signals.append(TradingSignal(
                        symbol=symbol,
                        signal_type=SignalType.TECHNICAL,
                        direction='sell',
                        strength=SignalStrength.STRONG if current_rsi > 80 else SignalStrength.MODERATE,
                        confidence=0.8 if current_rsi > 80 else 0.6,
                        price=market_data['close'].iloc[-1],
                        timestamp=datetime.now(),
                        indicators={'rsi': current_rsi},
                        description=f"RSI overbought signal: {current_rsi:.2f}",
                        risk_level='low',
                        time_horizon='short',
                        metadata={'indicator': 'rsi', 'value': current_rsi}
                    ))
            
            # MACD signals
            macd = indicators.get('macd', [])
            macd_signal = indicators.get('macd_signal', [])
            if len(macd) > 1 and len(macd_signal) > 1:
                current_macd = macd[-1]
                current_signal = macd_signal[-1]
                prev_macd = macd[-2]
                prev_signal = macd_signal[-2]
                
                # MACD crossover signals
                if current_macd > current_signal and prev_macd <= prev_signal:
                    signals.append(TradingSignal(
                        symbol=symbol,
                        signal_type=SignalType.TECHNICAL,
                        direction='buy',
                        strength=SignalStrength.MODERATE,
                        confidence=0.7,
                        price=market_data['close'].iloc[-1],
                        timestamp=datetime.now(),
                        indicators={'macd': current_macd, 'macd_signal': current_signal},
                        description="MACD bullish crossover",
                        risk_level='medium',
                        time_horizon='medium',
                        metadata={'indicator': 'macd_crossover', 'type': 'bullish'}
                    ))
                elif current_macd < current_signal and prev_macd >= prev_signal:
                    signals.append(TradingSignal(
                        symbol=symbol,
                        signal_type=SignalType.TECHNICAL,
                        direction='sell',
                        strength=SignalStrength.MODERATE,
                        confidence=0.7,
                        price=market_data['close'].iloc[-1],
                        timestamp=datetime.now(),
                        indicators={'macd': current_macd, 'macd_signal': current_signal},
                        description="MACD bearish crossover",
                        risk_level='medium',
                        time_horizon='medium',
                        metadata={'indicator': 'macd_crossover', 'type': 'bearish'}
                    ))
            
            # Bollinger Bands signals
            bb_upper = indicators.get('bb_upper', [])
            bb_lower = indicators.get('bb_lower', [])
            bb_middle = indicators.get('bb_middle', [])
            
            if len(bb_upper) > 0 and len(bb_lower) > 0:
                current_price = market_data['close'].iloc[-1]
                current_upper = bb_upper[-1]
                current_lower = bb_lower[-1]
                current_middle = bb_middle[-1]
                
                if current_price <= current_lower:
                    signals.append(TradingSignal(
                        symbol=symbol,
                        signal_type=SignalType.TECHNICAL,
                        direction='buy',
                        strength=SignalStrength.STRONG,
                        confidence=0.8,
                        price=current_price,
                        timestamp=datetime.now(),
                        indicators={'bb_upper': current_upper, 'bb_lower': current_lower, 'bb_middle': current_middle},
                        description="Price at Bollinger Band lower bound",
                        risk_level='low',
                        time_horizon='short',
                        metadata={'indicator': 'bollinger_bands', 'position': 'lower'}
                    ))
                elif current_price >= current_upper:
                    signals.append(TradingSignal(
                        symbol=symbol,
                        signal_type=SignalType.TECHNICAL,
                        direction='sell',
                        strength=SignalStrength.STRONG,
                        confidence=0.8,
                        price=current_price,
                        timestamp=datetime.now(),
                        indicators={'bb_upper': current_upper, 'bb_lower': current_lower, 'bb_middle': current_middle},
                        description="Price at Bollinger Band upper bound",
                        risk_level='low',
                        time_horizon='short',
                        metadata={'indicator': 'bollinger_bands', 'position': 'upper'}
                    ))
            
            # Volume analysis
            volume = market_data['volume'].iloc[-1]
            avg_volume = market_data['volume'].rolling(20).mean().iloc[-1]
            
            if volume > avg_volume * 1.5:
                # High volume confirmation
                for signal in signals:
                    if signal.signal_type == SignalType.TECHNICAL:
                        signal.confidence *= 1.2
                        signal.strength = SignalStrength(signal.strength.value + 1) if signal.strength.value < 4 else signal.strength
                        signal.description += " (High volume confirmation)"
        
        except Exception as e:
            self.logger.error(f"Error generating technical signals for {symbol}: {e}")
        
        return signals
    
    async def generate_sentiment_signals(self, symbol: str) -> List[TradingSignal]:
        """Generate sentiment-based signals"""
        signals = []
        
        try:
            # Get sentiment data from multiple sources
            sentiment_data = await self.sentiment_analyzer.get_comprehensive_sentiment(symbol)
            
            # News sentiment
            news_sentiment = sentiment_data.get('news', {})
            if news_sentiment:
                sentiment_score = news_sentiment.get('score', 0)
                if sentiment_score > 0.6:
                    signals.append(TradingSignal(
                        symbol=symbol,
                        signal_type=SignalType.SENTIMENT,
                        direction='buy',
                        strength=SignalStrength.MODERATE,
                        confidence=min(sentiment_score, 0.8),
                        price=0.0,  # Will be filled by caller
                        timestamp=datetime.now(),
                        indicators={'news_sentiment': sentiment_score},
                        description=f"Positive news sentiment: {sentiment_score:.2f}",
                        risk_level='medium',
                        time_horizon='short',
                        metadata={'source': 'news', 'sentiment_score': sentiment_score}
                    ))
                elif sentiment_score < -0.6:
                    signals.append(TradingSignal(
                        symbol=symbol,
                        signal_type=SignalType.SENTIMENT,
                        direction='sell',
                        strength=SignalStrength.MODERATE,
                        confidence=min(abs(sentiment_score), 0.8),
                        price=0.0,
                        timestamp=datetime.now(),
                        indicators={'news_sentiment': sentiment_score},
                        description=f"Negative news sentiment: {sentiment_score:.2f}",
                        risk_level='medium',
                        time_horizon='short',
                        metadata={'source': 'news', 'sentiment_score': sentiment_score}
                    ))
            
            # Social media sentiment
            social_sentiment = sentiment_data.get('social', {})
            if social_sentiment:
                sentiment_score = social_sentiment.get('score', 0)
                if abs(sentiment_score) > 0.5:
                    direction = 'buy' if sentiment_score > 0 else 'sell'
                    signals.append(TradingSignal(
                        symbol=symbol,
                        signal_type=SignalType.SOCIAL,
                        direction=direction,
                        strength=SignalStrength.MODERATE,
                        confidence=min(abs(sentiment_score), 0.7),
                        price=0.0,
                        timestamp=datetime.now(),
                        indicators={'social_sentiment': sentiment_score},
                        description=f"Social media sentiment: {sentiment_score:.2f}",
                        risk_level='high',
                        time_horizon='short',
                        metadata={'source': 'social', 'sentiment_score': sentiment_score}
                    ))
        
        except Exception as e:
            self.logger.error(f"Error generating sentiment signals for {symbol}: {e}")
        
        return signals
    
    async def generate_on_chain_signals(self, symbol: str) -> List[TradingSignal]:
        """Generate on-chain analysis signals"""
        signals = []
        
        try:
            # Get on-chain data
            on_chain_data = await self.on_chain_analyzer.get_comprehensive_data(symbol)
            
            # Exchange netflow
            netflow = on_chain_data.get('exchange_netflow', 0)
            if netflow < -1000000:  # Large outflow from exchanges
                signals.append(TradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.ON_CHAIN,
                    direction='buy',
                    strength=SignalStrength.STRONG,
                    confidence=0.8,
                    price=0.0,
                    timestamp=datetime.now(),
                    indicators={'exchange_netflow': netflow},
                    description=f"Large exchange outflow: {netflow:,.0f}",
                    risk_level='low',
                    time_horizon='medium',
                    metadata={'metric': 'exchange_netflow', 'value': netflow}
                ))
            elif netflow > 1000000:  # Large inflow to exchanges
                signals.append(TradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.ON_CHAIN,
                    direction='sell',
                    strength=SignalStrength.STRONG,
                    confidence=0.8,
                    price=0.0,
                    timestamp=datetime.now(),
                    indicators={'exchange_netflow': netflow},
                    description=f"Large exchange inflow: {netflow:,.0f}",
                    risk_level='low',
                    time_horizon='medium',
                    metadata={'metric': 'exchange_netflow', 'value': netflow}
                ))
            
            # Active addresses
            active_addresses = on_chain_data.get('active_addresses', 0)
            avg_active_addresses = on_chain_data.get('avg_active_addresses', 0)
            
            if active_addresses > avg_active_addresses * 1.2:
                signals.append(TradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.ON_CHAIN,
                    direction='buy',
                    strength=SignalStrength.MODERATE,
                    confidence=0.6,
                    price=0.0,
                    timestamp=datetime.now(),
                    indicators={'active_addresses': active_addresses, 'avg_active_addresses': avg_active_addresses},
                    description=f"High network activity: {active_addresses:,.0f} addresses",
                    risk_level='medium',
                    time_horizon='medium',
                    metadata={'metric': 'active_addresses', 'value': active_addresses}
                ))
        
        except Exception as e:
            self.logger.error(f"Error generating on-chain signals for {symbol}: {e}")
        
        return signals
    
    async def generate_fundamental_signals(self, symbol: str) -> List[TradingSignal]:
        """Generate fundamental analysis signals"""
        signals = []
        
        try:
            # Get fundamental data
            fundamental_data = await self.get_fundamental_data(symbol)
            
            # Market cap analysis
            market_cap = fundamental_data.get('market_cap', 0)
            if market_cap > 0:
                # This would include more sophisticated fundamental analysis
                # For now, return a placeholder signal
                signals.append(TradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.FUNDAMENTAL,
                    direction='hold',
                    strength=SignalStrength.WEAK,
                    confidence=0.5,
                    price=0.0,
                    timestamp=datetime.now(),
                    indicators={'market_cap': market_cap},
                    description="Fundamental analysis completed",
                    risk_level='medium',
                    time_horizon='long',
                    metadata={'metric': 'market_cap', 'value': market_cap}
                ))
        
        except Exception as e:
            self.logger.error(f"Error generating fundamental signals for {symbol}: {e}")
        
        return signals
    
    async def generate_social_signals(self, symbol: str) -> List[TradingSignal]:
        """Generate social media and community signals"""
        signals = []
        
        try:
            # Get social data
            social_data = await self.get_social_data(symbol)
            
            # Trending analysis
            trending_score = social_data.get('trending_score', 0)
            if trending_score > 0.7:
                signals.append(TradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.SOCIAL,
                    direction='buy',
                    strength=SignalStrength.MODERATE,
                    confidence=0.6,
                    price=0.0,
                    timestamp=datetime.now(),
                    indicators={'trending_score': trending_score},
                    description=f"High social trending: {trending_score:.2f}",
                    risk_level='high',
                    time_horizon='short',
                    metadata={'metric': 'trending_score', 'value': trending_score}
                ))
        
        except Exception as e:
            self.logger.error(f"Error generating social signals for {symbol}: {e}")
        
        return signals
    
    def generate_composite_signal(self, symbol: str, individual_signals: List[TradingSignal]) -> Optional[TradingSignal]:
        """Generate composite signal from individual signals"""
        if not individual_signals:
            return None
        
        # Group signals by direction
        buy_signals = [s for s in individual_signals if s.direction == 'buy']
        sell_signals = [s for s in individual_signals if s.direction == 'sell']
        hold_signals = [s for s in individual_signals if s.direction == 'hold']
        
        # Calculate weighted scores
        buy_score = sum(s.confidence * self.signal_weights[s.signal_type] for s in buy_signals)
        sell_score = sum(s.confidence * self.signal_weights[s.signal_type] for s in sell_signals)
        
        # Determine composite direction
        if buy_score > sell_score and buy_score > 0.3:
            direction = 'buy'
            composite_score = buy_score
            signals = buy_signals
        elif sell_score > buy_score and sell_score > 0.3:
            direction = 'sell'
            composite_score = sell_score
            signals = sell_signals
        else:
            direction = 'hold'
            composite_score = 0.5
            signals = hold_signals
        
        # Calculate average price
        prices = [s.price for s in signals if s.price > 0]
        avg_price = sum(prices) / len(prices) if prices else 0.0
        
        # Determine strength
        if composite_score > 0.8:
            strength = SignalStrength.VERY_STRONG
        elif composite_score > 0.6:
            strength = SignalStrength.STRONG
        elif composite_score > 0.4:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK
        
        # Create composite signal
        return TradingSignal(
            symbol=symbol,
            signal_type=SignalType.COMPOSITE,
            direction=direction,
            strength=strength,
            confidence=composite_score,
            price=avg_price,
            timestamp=datetime.now(),
            indicators={'composite_score': composite_score, 'signal_count': len(signals)},
            description=f"Composite signal: {direction.upper()} (Score: {composite_score:.2f})",
            risk_level='medium',
            time_horizon='medium',
            metadata={
                'buy_score': buy_score,
                'sell_score': sell_score,
                'signal_count': len(signals),
                'individual_signals': [s.signal_type.value for s in signals]
            }
        )
    
    async def get_fundamental_data(self, symbol: str) -> Dict[str, Any]:
        """Get fundamental data for a symbol"""
        # Placeholder implementation
        return {
            'market_cap': 1000000000,
            'volume_24h': 50000000,
            'circulating_supply': 1000000
        }
    
    async def get_social_data(self, symbol: str) -> Dict[str, Any]:
        """Get social media data for a symbol"""
        # Placeholder implementation
        return {
            'trending_score': 0.5,
            'mentions_24h': 1000,
            'sentiment_score': 0.3
        }

class SignalFilter:
    """Filter and validate trading signals"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def filter_signals(self, signals: List[TradingSignal], min_confidence: float = 0.5) -> List[TradingSignal]:
        """Filter signals based on confidence and other criteria"""
        filtered_signals = []
        
        for signal in signals:
            # Check confidence threshold
            if signal.confidence < min_confidence:
                continue
            
            # Check signal age (reject old signals)
            if (datetime.now() - signal.timestamp).total_seconds() > 3600:  # 1 hour
                continue
            
            # Additional filtering logic can be added here
            filtered_signals.append(signal)
        
        return filtered_signals
    
    def rank_signals(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """Rank signals by priority"""
        def signal_score(signal: TradingSignal) -> float:
            # Calculate composite score
            base_score = signal.confidence
            
            # Boost score based on signal type
            type_boost = {
                SignalType.COMPOSITE: 1.5,
                SignalType.TECHNICAL: 1.2,
                SignalType.ON_CHAIN: 1.1,
                SignalType.SENTIMENT: 1.0,
                SignalType.FUNDAMENTAL: 0.9,
                SignalType.SOCIAL: 0.8
            }
            
            # Boost score based on strength
            strength_boost = {
                SignalStrength.VERY_STRONG: 1.4,
                SignalStrength.STRONG: 1.2,
                SignalStrength.MODERATE: 1.0,
                SignalStrength.WEAK: 0.8
            }
            
            return base_score * type_boost.get(signal.signal_type, 1.0) * strength_boost.get(signal.strength, 1.0)
        
        return sorted(signals, key=signal_score, reverse=True)

class SignalManager:
    """Manage and coordinate signal generation and processing"""
    
    def __init__(self, llm_orchestrator: LLMOrchestrator):
        self.signal_generator = SignalGenerator(llm_orchestrator)
        self.signal_filter = SignalFilter()
        self.logger = logging.getLogger(__name__)
    
    async def get_signals_for_symbol(self, symbol: str, market_data: pd.DataFrame) -> List[TradingSignal]:
        """Get comprehensive signals for a symbol"""
        try:
            # Generate all signals
            all_signals = await self.signal_generator.generate_comprehensive_signals(symbol, market_data)
            
            # Filter signals
            filtered_signals = self.signal_filter.filter_signals(all_signals)
            
            # Rank signals
            ranked_signals = self.signal_filter.rank_signals(filtered_signals)
            
            self.logger.info(f"Generated {len(ranked_signals)} signals for {symbol}")
            return ranked_signals
            
        except Exception as e:
            self.logger.error(f"Error getting signals for {symbol}: {e}")
            return []
    
    async def get_top_signals(self, symbols: List[str], market_data: Dict[str, pd.DataFrame], limit: int = 10) -> List[TradingSignal]:
        """Get top signals across multiple symbols"""
        all_signals = []
        
        for symbol in symbols:
            if symbol in market_data:
                signals = await self.get_signals_for_symbol(symbol, market_data[symbol])
                all_signals.extend(signals)
        
        # Rank all signals
        ranked_signals = self.signal_filter.rank_signals(all_signals)
        
        # Return top signals
        return ranked_signals[:limit]
