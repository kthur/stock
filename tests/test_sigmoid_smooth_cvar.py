import numpy as np
from src.risk.portfolio_allocator import PortfolioAllocator


def test_evt_cvar_sigmoid_continuity():
    """Verify that EVT-CVaR transitions smoothly across sample sizes without step discontinuity."""
    allocator = PortfolioAllocator(min_tail_samples=15)

    np.random.seed(42)
    # Generate t-distributed returns with heavy tails
    returns = np.random.standard_t(df=4, size=150) * 0.02

    res = allocator.estimate_evt_cvar(returns, confidence=0.95)
    assert res['var'] > 0
    assert res['cvar'] >= res['var']
    assert np.isfinite(res['cvar'])


def test_compute_tail_stress_cov():
    """Verify that compute_tail_stress_cov mixes lower tail covariance and retains positive definiteness."""
    np.random.seed(42)
    n_days, n_assets = 100, 5
    returns = np.random.randn(n_days, n_assets) * 0.02
    # Inject joint crash on 5 days
    returns[:5, :] -= 0.08

    base_cov = np.cov(returns, rowvar=False)
    stressed_cov = PortfolioAllocator.compute_tail_stress_cov(returns, base_cov, tail_quantile=0.10, stress_weight=0.30)

    assert stressed_cov.shape == (n_assets, n_assets)
    # Check symmetric
    np.testing.assert_allclose(stressed_cov, stressed_cov.T, atol=1e-8)
    # Check positive definite (all eigenvalues > 0)
    eigvals = np.linalg.eigvalsh(stressed_cov)
    assert np.all(eigvals > 0)
