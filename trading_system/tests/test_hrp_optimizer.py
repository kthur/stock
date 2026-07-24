import numpy as np
import pytest
from src.analysis.portfolio_optimizer import calculate_hrp_weights, calculate_risk_parity_weights

def test_calculate_hrp_weights_basic():
    # 3x3 covariance matrix
    cov = np.array([
        [0.04, 0.01, 0.00],
        [0.01, 0.09, 0.02],
        [0.00, 0.02, 0.16]
    ])
    w = calculate_hrp_weights(cov)
    assert len(w) == 3
    assert np.isclose(np.sum(w), 1.0)
    assert np.all(w >= 0.0)
    assert np.all(w <= 1.0)

def test_calculate_hrp_weights_single_asset():
    cov = np.array([[0.05]])
    w = calculate_hrp_weights(cov)
    assert len(w) == 1
    assert w[0] == 1.0

def test_calculate_hrp_weights_invalid():
    assert len(calculate_hrp_weights(None)) == 0
    assert len(calculate_hrp_weights(np.array([]))) == 0

def test_portfolio_allocator_hrp_integration():
    import pandas as pd
    from src.risk.position_sizing import PortfolioAllocator

    allocator = PortfolioAllocator()
    preds = pd.DataFrame({'symbol': ['AAPL', 'MSFT', 'GOOGL'], 20: [0.10, 0.08, 0.12]})
    
    dates = pd.date_range('2026-01-01', periods=30)
    prices = {
        'AAPL': pd.DataFrame({'Close': np.linspace(100, 110, 30)}, index=dates),
        'MSFT': pd.DataFrame({'Close': np.linspace(200, 210, 30)}, index=dates),
        'GOOGL': pd.DataFrame({'Close': np.linspace(150, 160, 30)}, index=dates),
    }

    res = allocator.allocate(preds, prices, use_hrp=True)
    assert not res.empty
    assert 'weight' in res.columns
    assert res['weight'].sum() <= allocator.max_total_allocation
    assert np.all(res['weight'] <= allocator.max_single_position)

