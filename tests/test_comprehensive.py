import unittest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Import the modules to test
from exchanges.base_exchange import BaseExchange, Order
from exchanges.binance_api import BinanceAPI
from exchanges.bybit_api import BybitAPI
from exchanges.okx_api import OKXAPI
from exchanges.kucoin_api import KuCoinAPI
from exchanges.gateio_api import GateioAPI

from risk_management.manager import RiskManager, RiskParameters
from ai_models.llm_integration import (
    DeepSeekAnalyzer, ClaudeAnalyzer, MistralAnalyzer, 
    GeminiAnalyzer, LLMOrchestrator, LLMResponse
)
from trading.mode_manager import TradingModeManager, TradingMode, TradingConfig
from analytics.dashboard import PerformanceAnalytics, DashboardManager
from social.social_trading import SocialTradingManager, SocialSignal, SignalVisibility

class TestExchangeIntegrations(unittest.TestCase):
    """Test all exchange integrations"""
    
    def setUp(self):
        self.api_key = "test_api_key"
        self.secret_key = "test_secret_key"
        self.passphrase = "test_passphrase"
    
    @patch('ccxt.binance')
    def test_binance_integration(self, mock_ccxt):
        """Test Binance API integration"""
        # Mock CCXT response
        mock_exchange = Mock()
        mock_exchange.fetch_ticker.return_value = {'last': 50000.0}
        mock_exchange.fetch_ohlcv.return_value = [
            [1640995200000, 50000, 51000, 49000, 50500, 1000],
            [1640998800000, 50500, 52000, 50000, 51500, 1200]
        ]
        mock_exchange.create_order.return_value = {
            'id': '12345',
            'symbol': 'BTC/USDT',
            'status': 'filled',
            'filled': 0.1,
            'remaining': 0,
            'fee': {'cost': 0.5, 'currency': 'USDT'}
        }
        mock_ccxt.return_value = mock_exchange
        
        # Test Binance API
        binance = BinanceAPI(self.api_key, self.secret_key)
        
        # Test get_price
        price = binance.get_price('BTC/USDT')
        self.assertEqual(price, 50000.0)
        
        # Test get_historical_data
        data = binance.get_historical_data('BTC/USDT', '1h', 2)
        self.assertIsInstance(data, pd.DataFrame)
        self.assertEqual(len(data), 2)
        
        # Test place_order
        order = Order(
            symbol='BTC/USDT',
            order_type='market',
            side='buy',
            amount=0.1,
            price=50000.0
        )
        result = binance.place_order(order)
        self.assertIn('order_id', result)
    
    @patch('ccxt.bybit')
    def test_bybit_integration(self, mock_ccxt):
        """Test Bybit API integration"""
        mock_exchange = Mock()
        mock_exchange.fetch_ticker.return_value = {'last': 50000.0}
        mock_ccxt.return_value = mock_exchange
        
        bybit = BybitAPI(self.api_key, self.secret_key)
        price = bybit.get_price('BTC/USDT')
        self.assertEqual(price, 50000.0)
    
    @patch('ccxt.okx')
    def test_okx_integration(self, mock_ccxt):
        """Test OKX API integration"""
        mock_exchange = Mock()
        mock_exchange.fetch_ticker.return_value = {'last': 50000.0}
        mock_ccxt.return_value = mock_exchange
        
        okx = OKXAPI(self.api_key, self.secret_key, self.passphrase)
        price = okx.get_price('BTC/USDT')
        self.assertEqual(price, 50000.0)

class TestRiskManagement(unittest.TestCase):
    """Test risk management system"""
    
    def setUp(self):
        self.risk_params = RiskParameters(
            max_position_size=0.05,
            max_portfolio_risk=0.02,
            max_drawdown=0.15,
            max_open_trades=10
        )
        self.risk_manager = RiskManager(10000, self.risk_params)
    
    def test_position_size_calculation(self):
        """Test position size calculation"""
        entry_price = 50000.0
        stop_loss_price = 49000.0
        symbol = "BTC/USDT"
        exchange = "binance"
        
        position_size = self.risk_manager.calculate_position_size(
            entry_price, stop_loss_price, symbol, exchange
        )
        
        self.assertGreater(position_size, 0)
        self.assertLessEqual(position_size, 0.1)  # Should not exceed 10% of balance
    
    def test_drawdown_check(self):
        """Test drawdown checking"""
        # Simulate losses
        self.risk_manager.current_balance = 8500  # 15% loss
        self.risk_manager.peak_balance = 10000
        
        # Should still be within limits
        self.assertTrue(self.risk_manager.check_drawdown())
        
        # Simulate excessive losses
        self.risk_manager.current_balance = 8000  # 20% loss
        self.assertFalse(self.risk_manager.check_drawdown())
    
    def test_daily_loss_check(self):
        """Test daily loss checking"""
        # Simulate daily loss
        self.risk_manager.daily_pnl = -400  # 4% daily loss
        self.assertTrue(self.risk_manager.check_daily_loss())
        
        # Simulate excessive daily loss
        self.risk_manager.daily_pnl = -600  # 6% daily loss
        self.assertFalse(self.risk_manager.check_daily_loss())
    
    def test_risk_report(self):
        """Test risk report generation"""
        report = self.risk_manager.get_risk_report()
        
        self.assertIn('current_balance', report)
        self.assertIn('max_drawdown', report)
        self.assertIn('open_positions', report)
        self.assertIn('risk_limits', report)

class TestLLMIntegrations(unittest.TestCase):
    """Test LLM integrations"""
    
    def setUp(self):
        self.api_key = "test_api_key"
    
    @patch('requests.post')
    async def test_deepseek_analyzer(self, mock_post):
        """Test DeepSeek analyzer"""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Bullish sentiment with 0.8 confidence'}}],
            'usage': {'total_tokens': 100}
        }
        mock_post.return_value = mock_response
        
        analyzer = DeepSeekAnalyzer(self.api_key)
        
        # Test sentiment analysis
        response = await analyzer.analyze_sentiment("Bitcoin is going to the moon!")
        self.assertIsInstance(response, LLMResponse)
        self.assertGreater(response.confidence, 0)
    
    @patch('anthropic.Anthropic')
    async def test_claude_analyzer(self, mock_anthropic):
        """Test Claude analyzer"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = '{"sentiment": "bullish", "confidence": 0.7}'
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 30
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        analyzer = ClaudeAnalyzer(self.api_key)
        
        # Test sentiment analysis
        response = await analyzer.analyze_sentiment("Ethereum fundamentals are strong")
        self.assertIsInstance(response, LLMResponse)
    
    def test_llm_orchestrator(self):
        """Test LLM orchestrator"""
        api_keys = {
            'deepseek': 'test_deepseek_key',
            'claude': 'test_claude_key'
        }
        
        orchestrator = LLMOrchestrator(api_keys)
        
        # Should have analyzers for provided keys
        self.assertIn('deepseek', orchestrator.analyzers)
        self.assertIn('claude', orchestrator.analyzers)
        self.assertNotIn('grok', orchestrator.analyzers)  # No key provided

class TestTradingModes(unittest.TestCase):
    """Test trading mode management"""
    
    def setUp(self):
        self.exchanges = [Mock(spec=BaseExchange)]
        self.risk_manager = Mock(spec=RiskManager)
        self.signal_manager = Mock(spec=object)
        
        self.trading_manager = TradingModeManager(
            self.exchanges, self.risk_manager, self.signal_manager
        )
    
    def test_mode_setting(self):
        """Test trading mode setting"""
        # Test setting auto mode
        self.trading_manager.set_mode(TradingMode.AUTO)
        self.assertEqual(self.trading_manager.config.mode, TradingMode.AUTO)
        
        # Test setting manual mode
        self.trading_manager.set_mode(TradingMode.MANUAL)
        self.assertEqual(self.trading_manager.config.mode, TradingMode.MANUAL)
    
    def test_trading_hours_check(self):
        """Test trading hours validation"""
        # Test with no trading hours (should always return True)
        self.assertTrue(self.trading_manager.is_trading_hours())
        
        # Test with specific trading hours
        config = TradingConfig(
            mode=TradingMode.AUTO,
            trading_hours={'monday': [9, 10, 11, 12, 13, 14, 15, 16]}
        )
        self.trading_manager.config = config
        
        # Mock current time to Monday 10 AM
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 10, 0)  # Monday 10 AM
            self.assertTrue(self.trading_manager.is_trading_hours())
            
            # Mock current time to Monday 8 AM (outside trading hours)
            mock_datetime.now.return_value = datetime(2024, 1, 1, 8, 0)  # Monday 8 AM
            self.assertFalse(self.trading_manager.is_trading_hours())
    
    async def test_manual_trade(self):
        """Test manual trade execution"""
        # Mock exchange response
        self.exchanges[0].place_order.return_value = {
            'order_id': '12345',
            'status': 'filled',
            'price': 50000.0
        }
        
        # Mock risk manager
        self.risk_manager.check_drawdown.return_value = True
        
        # Test manual trade
        success = await self.trading_manager.manual_trade(
            symbol='BTC/USDT',
            side='buy',
            amount=0.1,
            price=50000.0
        )
        
        self.assertTrue(success)
        self.exchanges[0].place_order.assert_called_once()
    
    def test_trading_status(self):
        """Test trading status reporting"""
        status = self.trading_manager.get_trading_status()
        
        self.assertIn('mode', status)
        self.assertIn('is_trading', status)
        self.assertIn('daily_trades', status)
        self.assertIn('open_positions', status)
        self.assertIn('performance', status)

class TestPerformanceAnalytics(unittest.TestCase):
    """Test performance analytics"""
    
    def setUp(self):
        self.analytics = PerformanceAnalytics()
        
        # Sample trade data
        self.sample_trades = [
            {
                'symbol': 'BTC/USDT',
                'side': 'buy',
                'amount': 0.1,
                'price': 50000.0,
                'pnl': 500.0,
                'timestamp': datetime.now() - timedelta(days=1),
                'strategy': 'momentum',
                'signal_confidence': 0.8
            },
            {
                'symbol': 'ETH/USDT',
                'side': 'sell',
                'amount': 1.0,
                'price': 3000.0,
                'pnl': -100.0,
                'timestamp': datetime.now() - timedelta(hours=12),
                'strategy': 'mean_reversion',
                'signal_confidence': 0.6
            }
        ]
    
    def test_comprehensive_metrics(self):
        """Test comprehensive metrics calculation"""
        metrics = self.analytics.calculate_comprehensive_metrics(self.sample_trades)
        
        self.assertEqual(metrics.total_trades, 2)
        self.assertEqual(metrics.winning_trades, 1)
        self.assertEqual(metrics.losing_trades, 1)
        self.assertEqual(metrics.win_rate, 0.5)
        self.assertEqual(metrics.total_pnl, 400.0)
        self.assertEqual(metrics.avg_win, 500.0)
        self.assertEqual(metrics.avg_loss, -100.0)
    
    def test_performance_grade(self):
        """Test performance grade calculation"""
        metrics = self.analytics.calculate_comprehensive_metrics(self.sample_trades)
        grade = self.analytics.calculate_performance_grade(metrics)
        
        # Should be a valid grade
        self.assertIn(grade, ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F'])
    
    def test_risk_assessment(self):
        """Test risk assessment"""
        metrics = self.analytics.calculate_comprehensive_metrics(self.sample_trades)
        risk_assessment = self.analytics.assess_risk(metrics)
        
        self.assertIn('risk_level', risk_assessment)
        self.assertIn('risk_score', risk_assessment)
        self.assertIn('max_drawdown_risk', risk_assessment)
        self.assertIn('volatility_risk', risk_assessment)
        self.assertIn('win_rate_risk', risk_assessment)
    
    def test_performance_report(self):
        """Test complete performance report generation"""
        report = self.analytics.generate_performance_report(self.sample_trades)
        
        self.assertIn('metrics', report)
        self.assertIn('grade', report)
        self.assertIn('risk_assessment', report)
        self.assertIn('strategy_analysis', report)
        self.assertIn('time_analysis', report)
        self.assertIn('recommendations', report)

class TestSocialTrading(unittest.TestCase):
    """Test social trading features"""
    
    def setUp(self):
        self.trading_manager = Mock(spec=TradingModeManager)
        self.social_manager = SocialTradingManager(self.trading_manager)
    
    def test_follow_user(self):
        """Test following a user"""
        # Mock database session
        with patch('social.social_trading.SessionLocal') as mock_session:
            mock_db = Mock()
            mock_session.return_value = mock_db
            
            # Mock user query
            mock_user = Mock()
            mock_user.id = 2
            mock_db.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Test following
            result = asyncio.run(self.social_manager.follow_user(1, 2))
            self.assertTrue(result)
            self.assertTrue(self.social_manager.is_following(1, 2))
    
    def test_unfollow_user(self):
        """Test unfollowing a user"""
        # Setup following relationship
        self.social_manager.following_users[1] = {2: {'since': datetime.now()}}
        
        # Test unfollowing
        result = asyncio.run(self.social_manager.unfollow_user(1, 2))
        self.assertTrue(result)
        self.assertFalse(self.social_manager.is_following(1, 2))
    
    def test_social_signal_creation(self):
        """Test social signal creation"""
        signal_data = {
            'symbol': 'BTC/USDT',
            'direction': 'buy',
            'entry_price': 50000.0,
            'stop_loss': 49000.0,
            'take_profit': 52000.0,
            'confidence': 0.8,
            'description': 'Strong bullish signal',
            'visibility': 'public'
        }
        
        with patch('social.social_trading.SessionLocal') as mock_session:
            mock_db = Mock()
            mock_session.return_value = mock_db
            
            # Mock user query
            mock_user = Mock()
            mock_user.id = 1
            mock_user.username = 'testuser'
            mock_db.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Test signal sharing
            signal_id = asyncio.run(self.social_manager.share_signal(1, signal_data))
            self.assertIsInstance(signal_id, str)
            self.assertTrue(signal_id.startswith('signal_'))

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    def setUp(self):
        # Setup mock components for integration testing
        self.mock_exchanges = [Mock(spec=BaseExchange)]
        self.risk_manager = RiskManager(10000)
        self.signal_manager = Mock()
        self.trading_manager = TradingModeManager(
            self.mock_exchanges, self.risk_manager, self.signal_manager
        )
    
    def test_complete_trading_workflow(self):
        """Test complete trading workflow"""
        # 1. Set trading mode
        self.trading_manager.set_mode(TradingMode.MANUAL)
        self.assertEqual(self.trading_manager.config.mode, TradingMode.MANUAL)
        
        # 2. Check risk parameters
        self.assertTrue(self.risk_manager.check_drawdown())
        self.assertTrue(self.risk_manager.check_daily_loss())
        
        # 3. Calculate position size
        position_size = self.risk_manager.calculate_position_size(
            50000.0, 49000.0, "BTC/USDT", "test"
        )
        self.assertGreater(position_size, 0)
        
        # 4. Get trading status
        status = self.trading_manager.get_trading_status()
        self.assertIn('mode', status)
        self.assertIn('performance', status)

def run_all_tests():
    """Run all tests"""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestExchangeIntegrations,
        TestRiskManagement,
        TestLLMIntegrations,
        TestTradingModes,
        TestPerformanceAnalytics,
        TestSocialTrading,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"TESTS COMPLETED")
    print(f"{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
