"""
Adversarial Empirical Stress Testing Suite for Portfolio Allocator & Risk Engine
Authored by: challenger_1 (Empirical Challenger)

Challenge Scenarios:
1. EVT-CVaR Tail Calculations under degenerate, heavy-tailed (Pareto, Student-t df=2), and near-zero variance inputs.
2. Leland Dynamic Buffer Bands under extreme volatility (0% to 500% annualized) and extreme transaction costs.
3. Quarter-Kelly Sizing & SLSQP Non-linear EVT-CVaR Optimization numerical stability (no NaN, -Inf, unbounded weights).
4. RiskManager & CrisisDetector under macro shocks and extreme inputs.
5. HRP, ERC Risk Parity, Black-Litterman, and Sector Constraint robustness under singular/adversarial covariance matrices.
"""

import unittest
import numpy as np
import pandas as pd
from scipy.stats import t, pareto, cauchy

from trading_system.src.risk.portfolio_allocator import PortfolioAllocator
from trading_system.src.risk.portfolio_optimizer import PortfolioOptimizer
from trading_system.src.risk.risk_manager import (
    RiskManager, CrisisDetector, CrisisLevel, PortfolioCircuitBreaker
)
from trading_system.src.analysis.portfolio_optimizer import (
    calculate_hrp_weights, calculate_risk_parity_weights, calculate_black_litterman_weights
)


class TestAdversarialEVTCVaR(unittest.TestCase):
    """Adversarial stress-testing of EVT-GPD CVaR and its 3-tier fallback hierarchy."""

    def setUp(self):
        self.allocator = PortfolioAllocator(min_tail_samples=15)
        np.random.seed(42)

    def test_cvar_degenerate_all_zeros(self):
        """All zero returns series: EVT-CVaR must return 0.0 without NaN/Inf/Crash."""
        rets = np.zeros(500)
        res = self.allocator.estimate_evt_cvar(rets)
        self.assertTrue(np.isfinite(res["cvar"]), f"CVaR not finite: {res}")
        self.assertTrue(np.isfinite(res["var"]), f"VaR not finite: {res}")
        self.assertEqual(res["cvar"], 0.0)
        self.assertEqual(res["var"], 0.0)

    def test_cvar_degenerate_constant_positive(self):
        """Constant positive returns: All losses are negative (-0.02), CVaR must be 0.0 (floored)."""
        rets = np.full(500, 0.02)
        res = self.allocator.estimate_evt_cvar(rets)
        self.assertTrue(np.isfinite(res["cvar"]))
        self.assertEqual(res["cvar"], 0.0)

    def test_cvar_degenerate_constant_negative(self):
        """Constant negative returns: All losses are equal (+0.05), zero variance."""
        rets = np.full(500, -0.05)
        res = self.allocator.estimate_evt_cvar(rets)
        self.assertTrue(np.isfinite(res["cvar"]))
        self.assertAlmostEqual(res["cvar"], 0.05, places=4)
        self.assertAlmostEqual(res["var"], 0.05, places=4)

    def test_cvar_near_zero_variance(self):
        """Near-zero variance return series (variance ~ 1e-24)."""
        rets = np.random.normal(0.001, 1e-12, 500)
        res = self.allocator.estimate_evt_cvar(rets)
        self.assertTrue(np.isfinite(res["cvar"]))
        self.assertTrue(np.isfinite(res["var"]))
        self.assertGreaterEqual(res["cvar"], 0.0)

    def test_cvar_extreme_heavy_tail_pareto_low_alpha(self):
        """
        Pareto distribution with shape b = 1.2 (infinite variance, extreme tail risk).
        Must fit GPD or fallback gracefully to empirical without NaN/Inf, and xi must be clamped <= 0.50.
        """
        pareto_losses = pareto.rvs(b=1.2, loc=0, scale=0.01, size=1000)
        rets = -pareto_losses
        res = self.allocator.estimate_evt_cvar(rets, confidence=0.95)

        self.assertTrue(np.isfinite(res["cvar"]), f"CVaR is not finite: {res}")
        self.assertTrue(np.isfinite(res["var"]), f"VaR is not finite: {res}")
        self.assertGreater(res["cvar"], 0.0)
        self.assertLessEqual(res["xi"], 0.50, "Shape parameter xi was not properly clamped!")
        self.assertGreaterEqual(res["cvar"], res["var"] - 1e-6, "CVaR must be >= VaR")

    def test_cvar_extreme_heavy_tail_student_t_df2(self):
        """
        Student-t distribution with df = 2.0 (theoretical variance is infinite).
        Must produce positive finite CVaR >= VaR.
        """
        rets = t.rvs(df=2.0, loc=0.0001, scale=0.01, size=1000)
        res = self.allocator.estimate_evt_cvar(rets, confidence=0.95)

        self.assertTrue(np.isfinite(res["cvar"]))
        self.assertTrue(np.isfinite(res["var"]))
        self.assertGreater(res["cvar"], 0.0)
        self.assertGreaterEqual(res["cvar"], res["var"] - 1e-6)

    def test_cvar_cauchy_distribution_df1(self):
        """
        Cauchy distribution (Student-t df=1, undefined mean and variance).
        Must produce valid finite CVaR without exploding or throwing unhandled exception.
        """
        rets = cauchy.rvs(loc=0.0, scale=0.01, size=1000)
        # Clip extreme simulator artifacts to [-1.0, 1.0] for realistic equity returns
        rets = np.clip(rets, -1.0, 1.0)
        res = self.allocator.estimate_evt_cvar(rets, confidence=0.95)

        self.assertTrue(np.isfinite(res["cvar"]))
        self.assertTrue(np.isfinite(res["var"]))
        self.assertGreater(res["cvar"], 0.0)

    def test_cvar_flash_crash_outlier(self):
        """Flash crash scenario: 499 normal days (mu=0.001, sigma=0.01) + 1 day of -99.9% crash."""
        rets = np.random.normal(0.001, 0.01, 499)
        rets = np.append(rets, -0.999)
        res = self.allocator.estimate_evt_cvar(rets, confidence=0.95)

        self.assertTrue(np.isfinite(res["cvar"]))
        self.assertGreater(res["cvar"], 0.02)

    def test_cvar_dirty_inputs_nan_inf_empty(self):
        """Contaminated inputs: NaNs, Infs, None, empty arrays, small N."""
        # Empty array
        res_empty = self.allocator.estimate_evt_cvar(np.array([]))
        self.assertEqual(res_empty["cvar"], 0.0)
        self.assertEqual(res_empty["method"], "zero_fallback")

        # None
        res_none = self.allocator.estimate_evt_cvar(None)
        self.assertEqual(res_none["cvar"], 0.0)

        # Array with NaN and Infs
        dirty_rets = np.array([np.nan, 0.01, -0.02, np.inf, -np.inf, 0.03, -0.01, 0.005, -0.03, 0.02, -0.04])
        res_dirty = self.allocator.estimate_evt_cvar(dirty_rets)
        self.assertTrue(np.isfinite(res_dirty["cvar"]))
        self.assertGreaterEqual(res_dirty["cvar"], 0.0)

        # Very small sample sizes (N=1, 2, 4, 8)
        for n in [1, 2, 4, 8]:
            res_n = self.allocator.estimate_evt_cvar(np.random.normal(0, 0.02, n))
            self.assertTrue(np.isfinite(res_n["cvar"]))
            self.assertGreaterEqual(res_n["cvar"], 0.0)


class TestAdversarialLelandBufferBands(unittest.TestCase):
    """Adversarial stress-testing of Leland dynamic buffer bands and rebalancing rules."""

    def setUp(self):
        self.allocator = PortfolioAllocator(
            risk_aversion=1.0,
            delta_floor=0.005,
            delta_cap=0.050,
            rebalance_mode="boundary"
        )

    def test_leland_extreme_volatility(self):
        """
        Test buffer band calculation across extreme volatilities:
        - sigma = 0.0 (zero vol -> safe floor)
        - sigma = 1e-10 (near zero)
        - sigma = 0.315 (500% annualized vol -> delta_cap)
        - sigma = 5.0 (8000% annualized vol -> delta_cap)
        - sigma = -0.05 (negative vol passed -> safe floor)
        - sigma = NaN / Inf
        """
        # Zero vol -> bounded within [delta_floor, delta_cap]
        d_zero = self.allocator.calculate_dynamic_buffer_band("SYM", target_weight=0.20, cost_rate=0.002, volatility_20d=0.0)
        self.assertTrue(self.allocator.delta_floor <= d_zero <= self.allocator.delta_cap)

        # Near zero vol
        d_tiny = self.allocator.calculate_dynamic_buffer_band("SYM", target_weight=0.20, cost_rate=0.002, volatility_20d=1e-10)
        self.assertTrue(self.allocator.delta_floor <= d_tiny <= self.allocator.delta_cap)

        # Extreme 500% vol -> clamped to delta_cap (0.050)
        d_huge = self.allocator.calculate_dynamic_buffer_band("SYM", target_weight=0.20, cost_rate=0.002, volatility_20d=0.315)
        self.assertEqual(d_huge, self.allocator.delta_cap)

        # 5.0 vol
        d_extreme = self.allocator.calculate_dynamic_buffer_band("SYM", target_weight=0.20, cost_rate=0.002, volatility_20d=5.0)
        self.assertEqual(d_extreme, self.allocator.delta_cap)

        # Negative vol
        d_neg = self.allocator.calculate_dynamic_buffer_band("SYM", target_weight=0.20, cost_rate=0.002, volatility_20d=-0.05)
        self.assertTrue(self.allocator.delta_floor <= d_neg <= self.allocator.delta_cap)

        # NaN / Inf vol
        d_nan = self.allocator.calculate_dynamic_buffer_band("SYM", target_weight=0.20, cost_rate=0.002, volatility_20d=float("nan"))
        self.assertTrue(self.allocator.delta_floor <= d_nan <= self.allocator.delta_cap)

    def test_leland_extreme_transaction_costs(self):
        """
        Test buffer band calculation across extreme transaction cost rates:
        - c_i = 0.0 -> delta_floor
        - c_i = 10.0 (1000% cost) -> delta_cap
        - c_i = -0.05 -> delta_floor
        """
        d_zero_cost = self.allocator.calculate_dynamic_buffer_band("SYM", target_weight=0.20, cost_rate=0.0, volatility_20d=0.02)
        self.assertEqual(d_zero_cost, self.allocator.delta_floor)

        d_huge_cost = self.allocator.calculate_dynamic_buffer_band("SYM", target_weight=0.20, cost_rate=10.0, volatility_20d=0.02)
        self.assertEqual(d_huge_cost, self.allocator.delta_cap)

        d_neg_cost = self.allocator.calculate_dynamic_buffer_band("SYM", target_weight=0.20, cost_rate=-0.05, volatility_20d=0.02)
        self.assertEqual(d_neg_cost, self.allocator.delta_floor)

    def test_leland_extreme_risk_aversion(self):
        """
        Test buffer band calculation across extreme risk aversion:
        - gamma = 0.0 (division by zero risk)
        - gamma = 1e-10 (near zero risk aversion -> wide band clamped to delta_cap)
        - gamma = 1e6 (infinite risk aversion -> narrow band clamped to delta_floor)
        """
        d_zero_gamma = self.allocator.calculate_dynamic_buffer_band("SYM", target_weight=0.20, cost_rate=0.002, volatility_20d=0.02, risk_aversion=0.0)
        self.assertTrue(self.allocator.delta_floor <= d_zero_gamma <= self.allocator.delta_cap)

        d_tiny_gamma = self.allocator.calculate_dynamic_buffer_band("SYM", target_weight=0.20, cost_rate=0.002, volatility_20d=0.02, risk_aversion=1e-10)
        self.assertEqual(d_tiny_gamma, self.allocator.delta_cap)

        d_huge_gamma = self.allocator.calculate_dynamic_buffer_band("SYM", target_weight=0.20, cost_rate=0.002, volatility_20d=0.02, risk_aversion=1e6)
        self.assertEqual(d_huge_gamma, self.allocator.delta_floor)

    def test_rebalance_extreme_portfolio_states(self):
        """
        Stress test compute_portfolio_rebalance under degenerate/extreme portfolio distributions:
        - Total current weights > 1.0 (over-allocated)
        - Total target weights > 1.0
        - Target weight = 0.0 (complete divestment)
        - Unmatched symbols
        - Check weight conservation: sum(new_weights) <= 1.0, no NaNs
        """
        current_w = {"SYM_A": 0.60, "SYM_B": 0.50, "SYM_C": 0.10}  # sum = 1.20
        target_w = {"SYM_A": 0.20, "SYM_B": 0.00, "SYM_D": 0.30}
        market_map = {"SYM_A": "KOSPI", "SYM_B": "KOSDAQ", "SYM_C": "SP500", "SYM_D": "NASDAQ"}
        vol_map = {"SYM_A": 0.02, "SYM_B": 0.05, "SYM_C": 0.015, "SYM_D": 0.03}
        adv_map = {"SYM_A": 1e9, "SYM_B": 5e8, "SYM_C": 1e7, "SYM_D": 5e6}

        res = self.allocator.compute_portfolio_rebalance(
            current_weights=current_w,
            target_weights=target_w,
            market_map=market_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            portfolio_value=100_000_000.0
        )

        new_weights = res["new_weights"]
        self.assertLessEqual(sum(new_weights.values()), 1.0 + 1e-6)
        for sym, w in new_weights.items():
            self.assertTrue(np.isfinite(w), f"Weight for {sym} is not finite: {w}")
            self.assertGreaterEqual(w, 0.0, f"Weight for {sym} is negative: {w}")

        # SYM_B target was 0.0 -> must be fully sold
        self.assertEqual(res["trades"]["SYM_B"]["action"], "SELL")
        self.assertEqual(new_weights["SYM_B"], 0.0)


class TestAdversarialKellyAndSLSQPOptimization(unittest.TestCase):
    """Adversarial stress-testing of Fractional Kelly sizing and SLSQP EVT-CVaR optimization."""

    def setUp(self):
        self.allocator = PortfolioAllocator(default_max_weight=0.25)
        self.optimizer = PortfolioOptimizer(default_max_weight=0.25)
        np.random.seed(42)

    def test_kelly_all_negative_returns(self):
        """Quarter-Kelly with all negative expected returns: Must return safe capped allocation without NaN/Inf, sum(w) <= 1.0."""
        mu_neg = pd.Series({"A": -0.05, "B": -0.02, "C": -0.10})
        vols = pd.Series({"A": 0.02, "B": 0.03, "C": 0.025})

        w = self.allocator.allocate_quarter_kelly(mu_neg, volatilities=vols)
        self.assertEqual(len(w), 3)
        self.assertLessEqual(sum(w.values()), 1.0 + 1e-6)
        for sym, weight in w.items():
            self.assertTrue(np.isfinite(weight))
            self.assertGreaterEqual(weight, 0.0)
            self.assertLessEqual(weight, 0.25 + 1e-6)

    def test_kelly_all_zero_returns(self):
        """Quarter-Kelly with all zero expected returns."""
        mu_zero = pd.Series({"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0})
        w = self.allocator.allocate_quarter_kelly(mu_zero)
        self.assertEqual(len(w), 4)
        self.assertAlmostEqual(sum(w.values()), 1.0, places=4)
        for sym, weight in w.items():
            self.assertEqual(weight, 0.25)

    def test_kelly_massive_disparity_and_nan_inf(self):
        """Quarter-Kelly with extreme numbers, NaN, and Infs."""
        mu_extreme = pd.Series({"A": 1e9, "B": 1e-12, "C": np.nan, "D": np.inf, "E": -1e6})
        vols = pd.Series({"A": 0.02, "B": 0.0, "C": np.nan, "D": np.inf, "E": 0.05})

        w = self.allocator.allocate_quarter_kelly(mu_extreme, volatilities=vols)
        self.assertEqual(len(w), 5)
        self.assertAlmostEqual(sum(w.values()), 1.0, places=4)
        for sym, weight in w.items():
            self.assertTrue(np.isfinite(weight))
            self.assertGreaterEqual(weight, 0.0)
            self.assertLessEqual(weight, 1.0)

    def test_kelly_volatility_targeted_scaling(self):
        """Volatility-targeted Kelly sizing with extreme target volatilities."""
        mu = pd.Series({"A": 0.05, "B": 0.03, "C": 0.02})
        vols = pd.Series({"A": 0.01, "B": 0.02, "C": 0.015})

        # Target annual vol 0.15 (normal)
        w_norm = self.allocator.allocate_volatility_targeted_kelly(mu, volatilities=vols, target_annual_vol=0.15)
        self.assertLessEqual(sum(w_norm.values()), 1.0 + 1e-6)

        # Target annual vol 0.0 (near zero -> scaled down)
        w_zero = self.allocator.allocate_volatility_targeted_kelly(mu, volatilities=vols, target_annual_vol=0.0)
        self.assertLessEqual(sum(w_zero.values()), 1.0 + 1e-6)
        for sym, weight in w_zero.items():
            self.assertTrue(np.isfinite(weight))
            self.assertGreaterEqual(weight, 0.0)

        # Target annual vol 10.0 (huge -> clamped)
        w_huge = self.allocator.allocate_volatility_targeted_kelly(mu, volatilities=vols, target_annual_vol=10.0)
        self.assertLessEqual(sum(w_huge.values()), 1.0 + 1e-6)

    def test_slsqp_cvar_singular_collinear_returns(self):
        """
        SLSQP EVT-CVaR optimization with collinear / rank-1 returns matrix.
        (Asset B = 2.0 * Asset A, Asset C = -1.0 * Asset A).
        Must not crash or produce NaNs.
        """
        N = 300
        base_rets = np.random.normal(0.001, 0.02, N)
        rets_df = pd.DataFrame({
            "ASSET_A": base_rets,
            "ASSET_B": base_rets * 2.0,
            "ASSET_C": base_rets * (-1.0)
        })
        mu = pd.Series({"ASSET_A": 0.001, "ASSET_B": 0.002, "ASSET_C": -0.001})

        w = self.allocator.optimize_with_evt_cvar_constraint(
            expected_returns=mu,
            returns_df=rets_df,
            max_cvar=0.05,
            max_weight=0.50
        )
        self.assertEqual(len(w), 3)
        self.assertAlmostEqual(sum(w.values()), 1.0, places=4)
        for sym, weight in w.items():
            self.assertTrue(np.isfinite(weight))
            self.assertGreaterEqual(weight, 0.0)

    def test_slsqp_cvar_infeasible_tight_constraint(self):
        """
        SLSQP EVT-CVaR optimization with an impossible max_cvar constraint (e.g. 0.0001
        when assets have 5% daily volatility).
        Optimizer must gracefully fall back to normalized initial weights without raising exceptions or returning NaNs.
        """
        N = 300
        rets_df = pd.DataFrame({
            "ASSET_A": np.random.normal(0.001, 0.05, N),
            "ASSET_B": np.random.normal(0.001, 0.06, N)
        })
        mu = pd.Series({"ASSET_A": 0.001, "ASSET_B": 0.001})

        w = self.allocator.optimize_with_evt_cvar_constraint(
            expected_returns=mu,
            returns_df=rets_df,
            max_cvar=0.0001,  # Infeasible budget
            max_weight=0.60
        )
        self.assertEqual(len(w), 2)
        self.assertAlmostEqual(sum(w.values()), 1.0, places=4)
        for sym, weight in w.items():
            self.assertTrue(np.isfinite(weight))
            self.assertGreaterEqual(weight, 0.0)

    def test_slsqp_cvar_heavy_tailed_assets(self):
        """SLSQP optimization under Student-t (df=2) heavy-tailed assets."""
        N = 400
        asset_a = t.rvs(df=2.0, loc=0.002, scale=0.03, size=N)
        asset_b = t.rvs(df=2.0, loc=0.001, scale=0.015, size=N)
        asset_c = np.random.normal(0.0005, 0.01, size=N)

        rets_df = pd.DataFrame({"A": asset_a, "B": asset_b, "C": asset_c})
        mu = pd.Series({"A": 0.002, "B": 0.001, "C": 0.0005})

        w = self.allocator.optimize_with_evt_cvar_constraint(
            expected_returns=mu,
            returns_df=rets_df,
            max_cvar=0.04,
            max_weight=0.50
        )
        self.assertEqual(len(w), 3)
        self.assertAlmostEqual(sum(w.values()), 1.0, places=4)
        for sym, weight in w.items():
            self.assertTrue(np.isfinite(weight))
            self.assertGreaterEqual(weight, 0.0)

    def test_portfolio_optimizer_mean_variance_cvar_stress(self):
        """Test PortfolioOptimizer.optimize_mean_variance with extreme return scale and tight CVaR limit."""
        N = 300
        rets_df = pd.DataFrame({
            "A": np.random.normal(0.001, 0.02, N),
            "B": np.random.normal(0.002, 0.03, N),
            "C": np.random.normal(0.0005, 0.01, N)
        })
        mu = pd.Series({"A": 100.0, "B": -50.0, "C": 0.0})

        w = self.optimizer.optimize_mean_variance(
            expected_returns=mu,
            returns_df=rets_df,
            risk_aversion=5.0,
            max_cvar_limit=0.035
        )
        self.assertEqual(len(w), 3)
        self.assertAlmostEqual(sum(w.values()), 1.0, places=4)
        for sym, weight in w.items():
            self.assertTrue(np.isfinite(weight))
            self.assertGreaterEqual(weight, 0.0)


    def test_sector_constraints_adversarial_inputs(self):
        """Test sector constraint capping when all assets belong to a single sector or extreme weights."""
        weights = {"A": 0.50, "B": 0.30, "C": 0.20}
        all_same_sec = {"A": "TECH", "B": "TECH", "C": "TECH"}

        # Defensive regime (cap = 25%)
        capped = self.allocator.apply_sector_and_factor_constraints(
            weights=weights,
            sector_map=all_same_sec,
            regime="BEAR",
            max_sector_cap=0.25,
            renormalize=False
        )
        self.assertAlmostEqual(sum(capped.values()), 0.25, places=4)
        for sym, w in capped.items():
            self.assertTrue(np.isfinite(w))
            self.assertGreaterEqual(w, 0.0)

    def test_atr_trailing_stop_adversarial(self):
        """Test calculate_atr_trailing_stop under edge/corrupt inputs."""
        # Zero current price -> safe fallback
        res_zero = self.allocator.calculate_atr_trailing_stop("SYM", current_price=0.0, atr_20d=100.0)
        self.assertEqual(res_zero["risk_pct"], 0.05)

        # Huge ATR
        res_huge = self.allocator.calculate_atr_trailing_stop("SYM", current_price=50000.0, atr_20d=30000.0)
        self.assertTrue(np.isfinite(res_huge["stop_loss"]))
        self.assertTrue(np.isfinite(res_huge["take_profit"]))
        self.assertGreaterEqual(res_huge["stop_loss"], 0.0)


class TestAdversarialHRPAndRiskParity(unittest.TestCase):
    """Adversarial testing of HRP, ERC, and Black-Litterman solvers."""

    def test_hrp_singular_covariance(self):
        """HRP with singular / rank-1 covariance matrix (all assets perfectly correlated)."""
        cov_singular = np.ones((5, 5)) * 0.0004
        np.fill_diagonal(cov_singular, 0.0004)

        w_hrp = calculate_hrp_weights(cov_singular)
        self.assertEqual(len(w_hrp), 5)
        self.assertAlmostEqual(np.sum(w_hrp), 1.0, places=4)
        for weight in w_hrp:
            self.assertTrue(np.isfinite(weight))
            self.assertGreaterEqual(weight, 0.0)

    def test_hrp_nan_inf_covariance(self):
        """HRP with contaminated NaN / Inf covariance entries."""
        cov_nan = np.array([
            [0.04, np.nan, 0.01],
            [np.nan, 0.05, np.inf],
            [0.01, np.inf, 0.03]
        ])
        w = calculate_hrp_weights(cov_nan)
        self.assertEqual(len(w), 3)
        self.assertAlmostEqual(np.sum(w), 1.0, places=4)
        for weight in w:
            self.assertTrue(np.isfinite(weight))
            self.assertGreaterEqual(weight, 0.0)

    def test_risk_parity_singular_covariance(self):
        """ERC Risk Parity with singular / zero covariance."""
        cov_zero = np.zeros((4, 4))
        w = calculate_risk_parity_weights(cov_zero)
        self.assertEqual(len(w), 4)
        self.assertAlmostEqual(np.sum(w), 1.0, places=4)
        self.assertTrue(np.allclose(w, 0.25, atol=1e-2))
        for weight in w:
            self.assertTrue(np.isfinite(weight))
            self.assertGreaterEqual(weight, 0.0)

    def test_black_litterman_degenerate_inputs(self):
        """Black-Litterman with flat returns and near-singular covariance."""
        cov = np.eye(3) * 0.0004
        mu = np.zeros(3)
        w = calculate_black_litterman_weights(cov, mu)
        self.assertEqual(len(w), 3)
        self.assertAlmostEqual(np.sum(w), 1.0, places=4)
        for weight in w:
            self.assertTrue(np.isfinite(weight))
            self.assertGreaterEqual(weight, 0.0)


class TestAdversarialRiskManagerAndCrisisDetector(unittest.TestCase):
    """Adversarial stress-testing of RiskManager, CrisisDetector, and PortfolioCircuitBreaker."""

    def setUp(self):
        self.rm = RiskManager(portfolio_value=100_000_000.0)
        self.cd = CrisisDetector(self.rm)
        self.cb = PortfolioCircuitBreaker(max_drawdown=-0.15)

    def test_crisis_detector_vix_extremes(self):
        """CrisisDetector evaluate under extreme VIX values."""
        # Extreme VIX 80.0 -> SEVERE
        lvl_80 = self.cd.evaluate(vix=80.0)
        self.assertEqual(lvl_80, CrisisLevel.SEVERE)

        # Normal VIX 12.0 -> NONE
        lvl_12 = self.cd.evaluate(vix=12.0)
        self.assertEqual(lvl_12, CrisisLevel.NONE)

        # Corrupted / NaN VIX -> Failsafe WATCH
        lvl_nan = self.cd.evaluate(vix=float("nan"))
        self.assertIn(lvl_nan, [CrisisLevel.WATCH, CrisisLevel.ACTIVE, CrisisLevel.SEVERE])

        # None VIX -> Failsafe
        lvl_none = self.cd.evaluate(vix=None)
        self.assertIn(lvl_none, [CrisisLevel.WATCH, CrisisLevel.ACTIVE, CrisisLevel.SEVERE])

    def test_crisis_detector_macro_extremes(self):
        """CrisisDetector under combined macro shocks (USD/KRW spike, Oil spike, TNX spike, CDS spike)."""
        # Extreme CDS spike (200bp > 150bp threshold)
        lvl_cds = self.cd.evaluate(vix=25.0, cds_5y=200.0)
        self.assertEqual(lvl_cds, CrisisLevel.SEVERE)

        # Check cash target and position multiplier in SEVERE crisis
        cash_target = self.cd.get_crisis_cash_target()
        self.assertGreaterEqual(cash_target, 0.80)
        pos_mult = self.cd.get_crisis_position_multiplier()
        self.assertLessEqual(pos_mult, 0.20)
        self.assertTrue(self.cd.should_block_new_buys())

    def test_circuit_breaker_drawdown(self):
        """PortfolioCircuitBreaker under -20% drawdown breach."""
        # Initial peak 100M
        self.assertFalse(self.cb.update_and_check(100_000_000.0))
        # New peak 120M
        self.assertFalse(self.cb.update_and_check(120_000_000.0))
        # Drop to 110M (-8.3% DD) -> Not tripped
        self.assertFalse(self.cb.update_and_check(110_000_000.0))
        # Drop to 100M (-16.6% DD from 120M peak) -> Tripped!
        self.assertTrue(self.cb.update_and_check(100_000_000.0))
        self.assertTrue(self.cb.is_tripped)


if __name__ == "__main__":
    unittest.main(verbosity=2)
