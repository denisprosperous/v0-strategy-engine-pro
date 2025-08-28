import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import talib

class TechnicalIndicators:
    """Advanced technical analysis indicators"""
    
    def __init__(self):
        self.logger = None  # Will be set by caller if needed
    
    def calculate_all(self, df: pd.DataFrame) -> Dict[str, List[float]]:
        """Calculate all technical indicators"""
        if df.empty or len(df) < 20:
            return {}
        
        indicators = {}
        
        # Basic indicators
        indicators.update(self.calculate_rsi(df))
        indicators.update(self.calculate_macd(df))
        indicators.update(self.calculate_bollinger_bands(df))
        indicators.update(self.calculate_moving_averages(df))
        indicators.update(self.calculate_stochastic(df))
        indicators.update(self.calculate_atr(df))
        indicators.update(self.calculate_volume_indicators(df))
        
        return indicators
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> Dict[str, List[float]]:
        """Calculate RSI (Relative Strength Index)"""
        try:
            rsi = talib.RSI(df['close'].values, timeperiod=period)
            return {'rsi': rsi.tolist()}
        except Exception as e:
            return {'rsi': []}
    
    def calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, List[float]]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        try:
            macd, macd_signal, macd_hist = talib.MACD(
                df['close'].values, 
                fastperiod=fast, 
                slowperiod=slow, 
                signalperiod=signal
            )
            return {
                'macd': macd.tolist(),
                'macd_signal': macd_signal.tolist(),
                'macd_histogram': macd_hist.tolist()
            }
        except Exception as e:
            return {'macd': [], 'macd_signal': [], 'macd_histogram': []}
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> Dict[str, List[float]]:
        """Calculate Bollinger Bands"""
        try:
            bb_upper, bb_middle, bb_lower = talib.BBANDS(
                df['close'].values,
                timeperiod=period,
                nbdevup=std_dev,
                nbdevdn=std_dev,
                matype=0
            )
            return {
                'bb_upper': bb_upper.tolist(),
                'bb_middle': bb_middle.tolist(),
                'bb_lower': bb_lower.tolist()
            }
        except Exception as e:
            return {'bb_upper': [], 'bb_middle': [], 'bb_lower': []}
    
    def calculate_moving_averages(self, df: pd.DataFrame) -> Dict[str, List[float]]:
        """Calculate various moving averages"""
        try:
            sma_20 = talib.SMA(df['close'].values, timeperiod=20)
            sma_50 = talib.SMA(df['close'].values, timeperiod=50)
            sma_200 = talib.SMA(df['close'].values, timeperiod=200)
            ema_12 = talib.EMA(df['close'].values, timeperiod=12)
            ema_26 = talib.EMA(df['close'].values, timeperiod=26)
            
            return {
                'sma_20': sma_20.tolist(),
                'sma_50': sma_50.tolist(),
                'sma_200': sma_200.tolist(),
                'ema_12': ema_12.tolist(),
                'ema_26': ema_26.tolist()
            }
        except Exception as e:
            return {
                'sma_20': [], 'sma_50': [], 'sma_200': [],
                'ema_12': [], 'ema_26': []
            }
    
    def calculate_stochastic(self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Dict[str, List[float]]:
        """Calculate Stochastic Oscillator"""
        try:
            slowk, slowd = talib.STOCH(
                df['high'].values,
                df['low'].values,
                df['close'].values,
                fastk_period=k_period,
                slowk_period=d_period,
                slowk_matype=0,
                slowd_period=d_period,
                slowd_matype=0
            )
            return {
                'stoch_k': slowk.tolist(),
                'stoch_d': slowd.tolist()
            }
        except Exception as e:
            return {'stoch_k': [], 'stoch_d': []}
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> Dict[str, List[float]]:
        """Calculate Average True Range"""
        try:
            atr = talib.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=period)
            return {'atr': atr.tolist()}
        except Exception as e:
            return {'atr': []}
    
    def calculate_volume_indicators(self, df: pd.DataFrame) -> Dict[str, List[float]]:
        """Calculate volume-based indicators"""
        try:
            # Volume SMA
            volume_sma = talib.SMA(df['volume'].values, timeperiod=20)
            
            # On Balance Volume (OBV)
            obv = talib.OBV(df['close'].values, df['volume'].values)
            
            # Volume Rate of Change
            volume_roc = talib.ROC(df['volume'].values, timeperiod=10)
            
            return {
                'volume_sma': volume_sma.tolist(),
                'obv': obv.tolist(),
                'volume_roc': volume_roc.tolist()
            }
        except Exception as e:
            return {'volume_sma': [], 'obv': [], 'volume_roc': []}
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals based on technical indicators"""
        if df.empty or len(df) < 50:
            return pd.DataFrame()
        
        # Calculate all indicators
        indicators = self.calculate_all(df)
        
        # Create signals DataFrame
        signals = df.copy()
        signals['signal'] = 0  # 0 = hold, 1 = buy, -1 = sell
        
        # RSI signals
        if 'rsi' in indicators and len(indicators['rsi']) > 0:
            rsi = indicators['rsi'][-1]
            if rsi < 30:
                signals['signal'].iloc[-1] = 1  # Oversold - buy signal
            elif rsi > 70:
                signals['signal'].iloc[-1] = -1  # Overbought - sell signal
        
        # MACD signals
        if 'macd' in indicators and 'macd_signal' in indicators:
            if len(indicators['macd']) > 1 and len(indicators['macd_signal']) > 1:
                macd = indicators['macd'][-1]
                macd_signal = indicators['macd_signal'][-1]
                prev_macd = indicators['macd'][-2]
                prev_signal = indicators['macd_signal'][-2]
                
                # MACD crossover
                if macd > macd_signal and prev_macd <= prev_signal:
                    signals['signal'].iloc[-1] = 1  # Bullish crossover
                elif macd < macd_signal and prev_macd >= prev_signal:
                    signals['signal'].iloc[-1] = -1  # Bearish crossover
        
        # Bollinger Bands signals
        if 'bb_upper' in indicators and 'bb_lower' in indicators:
            if len(indicators['bb_upper']) > 0 and len(indicators['bb_lower']) > 0:
                current_price = df['close'].iloc[-1]
                bb_upper = indicators['bb_upper'][-1]
                bb_lower = indicators['bb_lower'][-1]
                
                if current_price <= bb_lower:
                    signals['signal'].iloc[-1] = 1  # Price at lower band
                elif current_price >= bb_upper:
                    signals['signal'].iloc[-1] = -1  # Price at upper band
        
        # Moving Average signals
        if 'sma_20' in indicators and 'sma_50' in indicators:
            if len(indicators['sma_20']) > 0 and len(indicators['sma_50']) > 0:
                sma_20 = indicators['sma_20'][-1]
                sma_50 = indicators['sma_50'][-1]
                current_price = df['close'].iloc[-1]
                
                if current_price > sma_20 > sma_50:
                    signals['signal'].iloc[-1] = 1  # Bullish MA alignment
                elif current_price < sma_20 < sma_50:
                    signals['signal'].iloc[-1] = -1  # Bearish MA alignment
        
        return signals
    
    def get_support_resistance(self, df: pd.DataFrame, window: int = 20) -> Dict[str, float]:
        """Calculate support and resistance levels"""
        if df.empty or len(df) < window:
            return {'support': 0, 'resistance': 0}
        
        recent_data = df.tail(window)
        
        # Find local minima and maxima
        highs = recent_data['high'].values
        lows = recent_data['low'].values
        
        # Resistance (local maxima)
        resistance_levels = []
        for i in range(1, len(highs) - 1):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                resistance_levels.append(highs[i])
        
        # Support (local minima)
        support_levels = []
        for i in range(1, len(lows) - 1):
            if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                support_levels.append(lows[i])
        
        # Get current levels
        current_price = df['close'].iloc[-1]
        
        # Find nearest support and resistance
        support = max([s for s in support_levels if s < current_price], default=current_price * 0.95)
        resistance = min([r for r in resistance_levels if r > current_price], default=current_price * 1.05)
        
        return {
            'support': support,
            'resistance': resistance,
            'support_levels': support_levels,
            'resistance_levels': resistance_levels
        }
    
    def calculate_volatility(self, df: pd.DataFrame, window: int = 20) -> float:
        """Calculate price volatility"""
        if df.empty or len(df) < window:
            return 0.0
        
        returns = df['close'].pct_change().dropna()
        if len(returns) < window:
            return 0.0
        
        return returns.tail(window).std()
    
    def detect_patterns(self, df: pd.DataFrame) -> List[Dict[str, any]]:
        """Detect candlestick patterns"""
        if df.empty or len(df) < 5:
            return []
        
        patterns = []
        
        try:
            # Common candlestick patterns
            pattern_functions = [
                ('DOJI', talib.CDLDOJI),
                ('HAMMER', talib.CDLHAMMER),
                ('ENGULFING', talib.CDLENGULFING),
                ('MORNINGSTAR', talib.CDLMORNINGSTAR),
                ('EVENINGSTAR', talib.CDLEVENINGSTAR),
                ('SHOOTINGSTAR', talib.CDLSHOOTINGSTAR),
                ('HANGINGMAN', talib.CDLHANGINGMAN)
            ]
            
            for pattern_name, pattern_func in pattern_functions:
                try:
                    pattern_result = pattern_func(
                        df['open'].values,
                        df['high'].values,
                        df['low'].values,
                        df['close'].values
                    )
                    
                    # Check if pattern occurred in recent candles
                    recent_patterns = pattern_result[-5:]  # Last 5 candles
                    if any(recent_patterns != 0):
                        patterns.append({
                            'pattern': pattern_name,
                            'strength': max(abs(p) for p in recent_patterns if p != 0),
                            'position': len(df) - 1 - list(reversed(recent_patterns)).index(max(recent_patterns, key=abs))
                        })
                except Exception as e:
                    continue
                    
        except Exception as e:
            pass
        
        return patterns
