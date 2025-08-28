import requests
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

class OnChainAnalyzer:
    """Advanced on-chain analysis for cryptocurrency markets"""
    
    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        self.api_keys = api_keys or {}
        self.logger = logging.getLogger(__name__)
        
        # API endpoints (placeholder - would use real blockchain APIs)
        self.bitcoin_api_url = "https://api.blockchain.info"
        self.ethereum_api_url = "https://api.etherscan.io"
        self.glassnode_api_url = "https://api.glassnode.com"
        
        # API keys
        self.glassnode_api_key = self.api_keys.get('glassnode_api')
        self.etherscan_api_key = self.api_keys.get('etherscan_api')
    
    async def get_comprehensive_data(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive on-chain data for a symbol"""
        try:
            base_symbol = symbol.split('/')[0] if '/' in symbol else symbol
            
            results = {}
            
            # Exchange netflow
            exchange_netflow = await self.get_exchange_netflow(base_symbol)
            results['exchange_netflow'] = exchange_netflow
            
            # Active addresses
            active_addresses = await self.get_active_addresses(base_symbol)
            results['active_addresses'] = active_addresses
            
            # Transaction volume
            transaction_volume = await self.get_transaction_volume(base_symbol)
            results['transaction_volume'] = transaction_volume
            
            # Network hash rate
            hash_rate = await self.get_hash_rate(base_symbol)
            results['hash_rate'] = hash_rate
            
            # Whale movements
            whale_movements = await self.get_whale_movements(base_symbol)
            results['whale_movements'] = whale_movements
            
            # Network metrics
            network_metrics = await self.get_network_metrics(base_symbol)
            results['network_metrics'] = network_metrics
            
            # On-chain indicators
            indicators = self.calculate_on_chain_indicators(results)
            results['indicators'] = indicators
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error getting comprehensive on-chain data for {symbol}: {e}")
            return {
                'exchange_netflow': 0,
                'active_addresses': 0,
                'transaction_volume': 0,
                'hash_rate': 0,
                'whale_movements': [],
                'network_metrics': {},
                'indicators': {},
                'error': str(e)
            }
    
    async def get_exchange_netflow(self, symbol: str) -> float:
        """Get exchange netflow (inflow - outflow)"""
        try:
            # This would integrate with real blockchain APIs
            # For now, return simulated data
            
            import random
            
            # Simulate exchange netflow
            # Positive = outflow from exchanges (bullish)
            # Negative = inflow to exchanges (bearish)
            netflow = random.uniform(-1000000, 1000000)
            
            return netflow
            
        except Exception as e:
            self.logger.error(f"Error getting exchange netflow: {e}")
            return 0.0
    
    async def get_active_addresses(self, symbol: str) -> Dict[str, Any]:
        """Get active addresses data"""
        try:
            # This would integrate with real blockchain APIs
            # For now, return simulated data
            
            import random
            
            current_active = random.randint(500000, 2000000)
            avg_active = random.randint(400000, 1800000)
            
            return {
                'current': current_active,
                'avg_active_addresses': avg_active,
                'change_24h': random.uniform(-0.1, 0.1),
                'trend': 'increasing' if current_active > avg_active else 'decreasing'
            }
            
        except Exception as e:
            self.logger.error(f"Error getting active addresses: {e}")
            return {'current': 0, 'avg_active_addresses': 0, 'change_24h': 0, 'trend': 'stable'}
    
    async def get_transaction_volume(self, symbol: str) -> Dict[str, Any]:
        """Get transaction volume data"""
        try:
            # This would integrate with real blockchain APIs
            # For now, return simulated data
            
            import random
            
            daily_volume = random.uniform(10000000, 100000000)
            weekly_volume = daily_volume * random.uniform(5, 10)
            
            return {
                'daily_volume': daily_volume,
                'weekly_volume': weekly_volume,
                'avg_transaction_size': random.uniform(1000, 10000),
                'transaction_count': random.randint(100000, 500000)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting transaction volume: {e}")
            return {'daily_volume': 0, 'weekly_volume': 0, 'avg_transaction_size': 0, 'transaction_count': 0}
    
    async def get_hash_rate(self, symbol: str) -> Dict[str, Any]:
        """Get network hash rate data"""
        try:
            # This would integrate with real blockchain APIs
            # For now, return simulated data
            
            import random
            
            current_hash_rate = random.uniform(100, 500)  # EH/s for Bitcoin
            difficulty = random.uniform(1000000000000, 5000000000000)
            
            return {
                'current_hash_rate': current_hash_rate,
                'difficulty': difficulty,
                'hash_rate_change_24h': random.uniform(-0.05, 0.05),
                'mining_revenue': random.uniform(1000000, 5000000)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting hash rate: {e}")
            return {'current_hash_rate': 0, 'difficulty': 0, 'hash_rate_change_24h': 0, 'mining_revenue': 0}
    
    async def get_whale_movements(self, symbol: str) -> List[Dict[str, Any]]:
        """Get large whale movements"""
        try:
            # This would integrate with real blockchain APIs
            # For now, return simulated data
            
            import random
            
            movements = []
            num_movements = random.randint(5, 15)
            
            for i in range(num_movements):
                movement = {
                    'amount': random.uniform(1000, 10000),
                    'from_exchange': random.choice([True, False]),
                    'to_exchange': random.choice([True, False]),
                    'timestamp': (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat(),
                    'type': 'large_transfer' if not (movement.get('from_exchange') or movement.get('to_exchange')) else 'exchange_movement'
                }
                movements.append(movement)
            
            return movements
            
        except Exception as e:
            self.logger.error(f"Error getting whale movements: {e}")
            return []
    
    async def get_network_metrics(self, symbol: str) -> Dict[str, Any]:
        """Get network health metrics"""
        try:
            # This would integrate with real blockchain APIs
            # For now, return simulated data
            
            import random
            
            return {
                'block_height': random.randint(800000, 900000),
                'block_time': random.uniform(8, 12),  # minutes
                'mempool_size': random.randint(1000, 10000),
                'fee_rate': random.uniform(1, 50),  # sat/byte
                'network_utilization': random.uniform(0.3, 0.9),
                'node_count': random.randint(10000, 50000)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting network metrics: {e}")
            return {}
    
    def calculate_on_chain_indicators(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate on-chain indicators and signals"""
        try:
            indicators = {}
            
            # Exchange netflow indicator
            netflow = data.get('exchange_netflow', 0)
            if netflow > 1000000:
                indicators['exchange_signal'] = 'bullish'  # Large outflow
            elif netflow < -1000000:
                indicators['exchange_signal'] = 'bearish'  # Large inflow
            else:
                indicators['exchange_signal'] = 'neutral'
            
            # Active addresses indicator
            active_data = data.get('active_addresses', {})
            current_active = active_data.get('current', 0)
            avg_active = active_data.get('avg_active_addresses', 0)
            
            if current_active > avg_active * 1.2:
                indicators['activity_signal'] = 'bullish'
            elif current_active < avg_active * 0.8:
                indicators['activity_signal'] = 'bearish'
            else:
                indicators['activity_signal'] = 'neutral'
            
            # Transaction volume indicator
            volume_data = data.get('transaction_volume', {})
            daily_volume = volume_data.get('daily_volume', 0)
            
            if daily_volume > 50000000:  # High volume threshold
                indicators['volume_signal'] = 'bullish'
            elif daily_volume < 20000000:  # Low volume threshold
                indicators['volume_signal'] = 'bearish'
            else:
                indicators['volume_signal'] = 'neutral'
            
            # Whale movement indicator
            whale_movements = data.get('whale_movements', [])
            recent_movements = [m for m in whale_movements if 
                              datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00')) > 
                              datetime.now() - timedelta(hours=6)]
            
            outflow_movements = len([m for m in recent_movements if m.get('from_exchange')])
            inflow_movements = len([m for m in recent_movements if m.get('to_exchange')])
            
            if outflow_movements > inflow_movements * 1.5:
                indicators['whale_signal'] = 'bullish'
            elif inflow_movements > outflow_movements * 1.5:
                indicators['whale_signal'] = 'bearish'
            else:
                indicators['whale_signal'] = 'neutral'
            
            # Network health indicator
            network_data = data.get('network_metrics', {})
            fee_rate = network_data.get('fee_rate', 0)
            mempool_size = network_data.get('mempool_size', 0)
            
            if fee_rate < 10 and mempool_size < 5000:
                indicators['network_signal'] = 'bullish'  # Healthy network
            elif fee_rate > 30 or mempool_size > 8000:
                indicators['network_signal'] = 'bearish'  # Network congestion
            else:
                indicators['network_signal'] = 'neutral'
            
            # Composite on-chain signal
            bullish_signals = sum(1 for signal in indicators.values() if signal == 'bullish')
            bearish_signals = sum(1 for signal in indicators.values() if signal == 'bearish')
            
            if bullish_signals > bearish_signals:
                indicators['composite_signal'] = 'bullish'
            elif bearish_signals > bullish_signals:
                indicators['composite_signal'] = 'bearish'
            else:
                indicators['composite_signal'] = 'neutral'
            
            indicators['confidence'] = max(bullish_signals, bearish_signals) / len(indicators)
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error calculating on-chain indicators: {e}")
            return {'composite_signal': 'neutral', 'confidence': 0}
    
    async def get_historical_on_chain_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Get historical on-chain data"""
        try:
            # This would fetch historical data from blockchain APIs
            # For now, return simulated historical data
            
            import random
            
            dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days, 0, -1)]
            
            data = []
            for date in dates:
                row = {
                    'date': date,
                    'exchange_netflow': random.uniform(-2000000, 2000000),
                    'active_addresses': random.randint(400000, 2000000),
                    'transaction_volume': random.uniform(5000000, 100000000),
                    'hash_rate': random.uniform(100, 500),
                    'fee_rate': random.uniform(1, 50),
                    'mempool_size': random.randint(1000, 10000)
                }
                data.append(row)
            
            return pd.DataFrame(data)
            
        except Exception as e:
            self.logger.error(f"Error getting historical on-chain data: {e}")
            return pd.DataFrame()
    
    def analyze_on_chain_trends(self, historical_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze on-chain trends"""
        try:
            if historical_data.empty or len(historical_data) < 7:
                return {}
            
            trends = {}
            
            # Exchange netflow trend
            netflow_trend = historical_data['exchange_netflow'].tail(7).mean()
            trends['netflow_trend'] = 'outflow' if netflow_trend > 0 else 'inflow'
            trends['netflow_strength'] = abs(netflow_trend) / 1000000  # Normalize
            
            # Active addresses trend
            addresses_trend = historical_data['active_addresses'].tail(7).pct_change().mean()
            trends['addresses_trend'] = 'increasing' if addresses_trend > 0 else 'decreasing'
            trends['addresses_strength'] = abs(addresses_trend)
            
            # Transaction volume trend
            volume_trend = historical_data['transaction_volume'].tail(7).pct_change().mean()
            trends['volume_trend'] = 'increasing' if volume_trend > 0 else 'decreasing'
            trends['volume_strength'] = abs(volume_trend)
            
            # Network health trend
            fee_trend = historical_data['fee_rate'].tail(7).mean()
            mempool_trend = historical_data['mempool_size'].tail(7).mean()
            
            if fee_trend < 15 and mempool_trend < 5000:
                trends['network_health'] = 'excellent'
            elif fee_trend < 25 and mempool_trend < 7000:
                trends['network_health'] = 'good'
            else:
                trends['network_health'] = 'congested'
            
            return trends
            
        except Exception as e:
            self.logger.error(f"Error analyzing on-chain trends: {e}")
            return {}
    
    async def get_on_chain_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """Generate on-chain trading signals"""
        try:
            # Get comprehensive data
            data = await self.get_comprehensive_data(symbol)
            indicators = data.get('indicators', {})
            
            signals = []
            
            # Exchange netflow signal
            if indicators.get('exchange_signal') == 'bullish':
                signals.append({
                    'type': 'exchange_netflow',
                    'signal': 'buy',
                    'strength': 'strong' if abs(data.get('exchange_netflow', 0)) > 2000000 else 'moderate',
                    'description': 'Large outflow from exchanges indicates accumulation',
                    'confidence': 0.8
                })
            elif indicators.get('exchange_signal') == 'bearish':
                signals.append({
                    'type': 'exchange_netflow',
                    'signal': 'sell',
                    'strength': 'strong' if abs(data.get('exchange_netflow', 0)) > 2000000 else 'moderate',
                    'description': 'Large inflow to exchanges indicates distribution',
                    'confidence': 0.8
                })
            
            # Activity signal
            if indicators.get('activity_signal') == 'bullish':
                signals.append({
                    'type': 'network_activity',
                    'signal': 'buy',
                    'strength': 'moderate',
                    'description': 'High network activity indicates strong fundamentals',
                    'confidence': 0.7
                })
            
            # Whale movement signal
            if indicators.get('whale_signal') == 'bullish':
                signals.append({
                    'type': 'whale_movements',
                    'signal': 'buy',
                    'strength': 'strong',
                    'description': 'Whales moving coins out of exchanges',
                    'confidence': 0.9
                })
            elif indicators.get('whale_signal') == 'bearish':
                signals.append({
                    'type': 'whale_movements',
                    'signal': 'sell',
                    'strength': 'strong',
                    'description': 'Whales moving coins to exchanges',
                    'confidence': 0.9
                })
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating on-chain signals: {e}")
            return []
