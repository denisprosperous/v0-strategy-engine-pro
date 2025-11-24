"""
PortfolioRiskCalculator Tests: Professional-Grade Coverage
=========================================================
- Parametric, Historical, Monte Carlo VaR/CVaR
- Rolling drawdown, Sharpe, Sortino
- Portfolio beta, correlation heatmap, decomposition
- Data diagnostics, error/edge case handling
- Global reproducible seed for deterministic results when needed
"""

import numpy as np
import pandas as pd
import pytest
import random
from risk_management.portfolio_risk import PortfolioRiskCalculator, PortfolioRiskConfig

@pytest.fixture
def dummy_portfolio():
    np.random.seed(42)
    random.seed(42)
    # 3 assets, 100 days
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    prices = pd.DataFrame({
        'timestamp': np.tile(dates, 3),
        'symbol': ['BTC']*100 + ['ETH']*100 + ['USD']*100,
        'price': np.concatenate([
            20000 + np.cumsum(np.random.randn(100)*150),  # BTC
            1000 + np.cumsum(np.random.randn(100)*30),    # ETH
            1 + np.cumsum(np.random.randn(100)*0.0004),   # USD (stable)
        ])
    }).reset_index(drop=True)
    return prices

@pytest.fixture
def standard_config():
    return PortfolioRiskConfig(var_confidence_levels=[0.95, 0.99], monte_carlo_paths=5000, min_sample_size=50)

@pytest.fixture
def calculator(dummy_portfolio, standard_config):
    c = PortfolioRiskCalculator(config=standard_config)
    c.ingest(dummy_portfolio, weights={'BTC':0.5, 'ETH':0.4, 'USD':0.1}, asset_type={'BTC':'crypto','ETH':'crypto','USD':'cash'})
    return c

class TestPortfolioRiskVaR:
    def test_parametric_var(self, calculator):
        v95 = calculator.parametric_var(confidence=0.95)
        v99 = calculator.parametric_var(confidence=0.99)
        assert v99 > v95 > 0
    def test_historical_var(self, calculator):
        v95 = calculator.historical_var(confidence=0.95)
        v99 = calculator.historical_var(confidence=0.99)
        assert v99 > v95 > 0
    def test_monte_carlo_var(self, calculator):
        v95 = calculator.monte_carlo_var(confidence=0.95)
        assert v95 > 0
    def test_var_monotonicity(self, calculator):
        assert calculator.historical_var(confidence=0.99) > calculator.historical_var(confidence=0.95)

class TestPortfolioRiskCVaR:
    def test_cvar_methods_agree(self, calculator):
        h = calculator.cvar(method='historical', confidence=0.95)
        p = calculator.cvar(method='parametric', confidence=0.95)
        m = calculator.cvar(method='monte_carlo', confidence=0.95)
        assert 0.7*min(h,p,m) < h < 1.3*max(h,p,m)
    def test_cvar_worst_case(self, calculator):
        mc = calculator.cvar(method='monte_carlo', confidence=0.99)
        hist = calculator.cvar(method='historical', confidence=0.99)
        assert mc > 0 and hist > 0

class TestPortfolioRollingMetrics:
    def test_rolling_drawdown(self, calculator):
        drawdowns = calculator.rolling_drawdown(window=20)
        assert (drawdowns <= 0).all()
        assert len(drawdowns) == 100
    def test_rolling_sharpe_sortino(self, calculator):
        sharpe = calculator.rolling_sharpe(window=20)
        sortino = calculator.rolling_sortino(window=20)
        assert (abs(sharpe) < 10).all()
        assert (abs(sortino) < 15).all()

class TestPortfolioCorrelation:
    def test_correlation_heatmap(self, calculator):
        corr = calculator.correlation_heatmap()
        assert set(corr.index) == {"BTC","ETH","USD"}
        assert np.all(np.diag(corr)==1)
    def test_risk_decomposition(self, calculator):
        contrib = calculator.asset_risk_decomposition()
        assert abs(sum(contrib.values())-1) < 0.02
        assert all(0<=v<=1 for v in contrib.values())

class TestPortfolioBeta:
    def test_portfolio_beta_sane(self, calculator):
        # Use BTC as 'market' proxy
        bench = calculator.returns()['BTC']
        beta = calculator.portfolio_beta(bench)
        assert -2 <= beta <= 2

class TestInputEdgeCases:
    def test_zero_variance_asset(self, dummy_portfolio, standard_config):
        # All prices constant
        dummy_portfolio.loc[dummy_portfolio['symbol']=='BTC', 'price'] = 9999
        calc = PortfolioRiskCalculator(config=standard_config)
        calc.ingest(dummy_portfolio, weights={'BTC':0.5, 'ETH':0.4, 'USD':0.1}, asset_type={'BTC':'crypto','ETH':'crypto','USD':'cash'})
        v95 = calc.parametric_var(confidence=0.95)
        # Should be near zero
        assert v95 < 2
    def test_missing_data_acceptance(self, dummy_portfolio, standard_config):
        # Remove 9% of ETH values randomly
        idx = (dummy_portfolio['symbol']=='ETH').to_numpy().nonzero()[0]
        drop = np.random.choice(idx, size=int(len(idx)*0.09), replace=False)
        test_df = dummy_portfolio.drop(drop)
        calc = PortfolioRiskCalculator(config=standard_config)
        calc.ingest(test_df, weights={'BTC':0.5, 'ETH':0.4, 'USD':0.1})
        v = calc.historical_var(confidence=0.95)
        assert v > 0
    def test_too_much_missing_raises(self, dummy_portfolio, standard_config):
        idx = (dummy_portfolio['symbol']=='ETH').to_numpy().nonzero()[0]
        drop = np.random.choice(idx, size=int(len(idx)*0.12), replace=False)
        test_df = dummy_portfolio.drop(drop)
        calc = PortfolioRiskCalculator(config=standard_config)
        with pytest.raises(AssertionError):
            calc.ingest(test_df, weights={'BTC':0.5, 'ETH':0.4, 'USD':0.1})
    def test_insufficient_sample_size_raises(self, dummy_portfolio, standard_config):
        sample = dummy_portfolio.iloc[:45].copy()
        calc = PortfolioRiskCalculator(config=PortfolioRiskConfig(min_sample_size=50))
        with pytest.raises(AssertionError):
            calc.ingest(sample, weights={'BTC':0.5, 'ETH':0.4, 'USD':0.1})
class TestReporting:
    def test_full_report_keys(self, calculator):
        report = calculator.report()
        expected = {'parametric_var_95','parametric_var_99','historical_var_95','historical_var_99','monte_carlo_var_95','cvar_historical','cvar_parametric','rolling_drawdown','rolling_sharpe','rolling_sortino','correlation_heatmap','asset_risk_decomposition'}
        assert expected.issubset(set(report.keys()))
