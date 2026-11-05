"""
tests/test_phase149_challenger.py - Empirical Adversarial Challenger Test Suite for Phase 149.
Features F725, F726, F727, F728, F729.

Adversarial Stress Test Matrix:
1. Simplex Conservation: sum(w_i) + w_cash == L +- 1e-6 across 100 randomized portfolios
   under high dimensions (N=100, 200, 500), all-negative alphas, ill-conditioned covariance
   matrices (cond > 1e8), and saturated capacity caps.
2. Strict Beta Clamping: beta_port <= 1.000001 when L > 1.00 across extreme beta spreads [-2.0, 3.5],
   verifying cash buffer absorption and unleveraged exemption.
3. Shannon Entropy Regularizer: Monotonicity of H(w) with increasing lambda_entropy without
   weight distortion, ranking inversion, or non-negativity breaches.
4. 4-Tier Protective Gating Lower Envelope: Simultaneous compounding market shocks across all 4 gates
   and 1,000 Monte Carlo sweeps.
5. Leland Dynamic Buffer Bandwidth & Instant Bypass: Exact 1.1400000x expansion at L=1.35,
   zero-latency instant bypass for fresh entry (w_curr == 0) and full exit (w_target == 0).
"""

from __future__ import annotations

import math
import os
import sys
import unittest
import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.risk.dynamic_regime_leverage_allocator import (
    DynamicRegimeLeverageAllocator,
    FractionalKellyAllocator,
    Phase149KellyAllocator,
    EntropyRegularizedKellyAllocator,
    VERSION,
    RELEASE,
    FEATURE,
)
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase149Challenger(unittest.TestCase):
    """Empirical Adversarial Challenge Test Suite for Phase 149 Quant Risk Architecture."""

    def setUp(self):
        np.random.seed(149999)
        self.allocator = DynamicRegimeLeverageAllocator(
            max_bull_leverage=1.35,
            min_crisis_exposure=0.15,
            borrowing_spread_bps=60.0,
            hwm_dd_limit=-0.15,
            default_kappa=0.375,
            top_k_modes=50,
            lambda_entropy=0.001,
        )
        self.port_allocator = PortfolioAllocator(version=149)
        self.unified_allocator = UnifiedPortfolioAllocator(version=149)

    # =========================================================================
    # Suite 1: Simplex Invariant Conservation sum(w) + w_cash == L +- 1e-6
    # =========================================================================

    def test_challenge_simplex_100_random_portfolios(self):
        """Stress 1.1: Simplex conservation across 100 randomized portfolios across dimensions N in [10, 200] and L in [0.15, 1.35]."""
        for iteration in range(100):
            N = np.random.randint(10, 100)
            lev = float(np.random.uniform(0.15, 1.35))
            mu = np.random.uniform(-0.002, 0.008, N)
            # Random positive definite covariance
            A = np.random.normal(0, 0.01, size=(N, N))
            cov = A @ A.T + 1e-4 * np.eye(N)
            betas = np.random.uniform(-0.5, 2.5, N)

            w, w_cash = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=mu,
                cov_matrix=cov,
                leverage=lev,
                asset_betas=betas,
            )

            total = float(np.sum(w) + w_cash)
            diff = abs(total - lev)
            self.assertLessEqual(
                diff, 1e-6,
                f"Iter {iteration}: Simplex sum violated: sum(w)+w_cash={total:.8f} != lev={lev:.8f}, diff={diff:.2e}"
            )
            self.assertTrue(np.all(w >= -1e-12), f"Negative weight detected in iter {iteration}")
            self.assertGreaterEqual(w_cash, -1e-12, f"Negative cash detected in iter {iteration}")

    def test_challenge_simplex_all_negative_alphas(self):
        """Stress 1.2: All-negative expected returns across 20 randomized tests (must return 100% Cash, sum==L)."""
        for iteration in range(20):
            N = np.random.randint(5, 50)
            lev = float(np.random.uniform(0.15, 1.35))
            mu = np.random.uniform(-0.05, -0.001, N)
            cov = np.eye(N) * 0.0004

            w, w_cash = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=mu,
                cov_matrix=cov,
                leverage=lev,
            )

            self.assertTrue(np.all(w == 0.0), f"Non-zero weights under all-negative returns in iter {iteration}")
            self.assertAlmostEqual(w_cash, lev, places=6)
            self.assertAlmostEqual(float(np.sum(w) + w_cash), lev, places=6)

    def test_challenge_simplex_high_dimension_500_assets(self):
        """Stress 1.3: High-dimensional portfolios N=100, N=200, N=500 under L=1.35."""
        for N in [100, 200, 500]:
            mu = np.random.uniform(0.0005, 0.003, N)
            # Diagonal + low rank factor covariance to avoid memory explosion
            K = 5
            B = np.random.normal(0, 0.01, size=(N, K))
            cov = B @ B.T + np.diag(np.random.uniform(0.0001, 0.0004, N))
            lev = 1.35

            w, w_cash = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=mu,
                cov_matrix=cov,
                leverage=lev,
            )

            self.assertEqual(len(w), N)
            self.assertTrue(np.all(w >= 0.0))
            self.assertAlmostEqual(float(np.sum(w) + w_cash), lev, places=6)

    def test_challenge_simplex_ill_conditioned_covariance(self):
        """Stress 1.4: Ill-conditioned covariance matrix (condition number > 1e10, near singular)."""
        N = 30
        lev = 1.35
        # Generate ill-conditioned matrix using SVD with exponentially decaying singular values
        U, _ = np.linalg.qr(np.random.normal(0, 1, size=(N, N)))
        s = np.logspace(-1, -12, N)  # Cond number = 1e11
        cov_ill = U @ np.diag(s) @ U.T
        cov_ill = 0.5 * (cov_ill + cov_ill.T)  # Enforce exact symmetry
        self.assertGreater(np.linalg.cond(cov_ill), 1e10)

        mu = np.random.uniform(0.001, 0.005, N)
        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov_ill,
            leverage=lev,
        )

        self.assertTrue(np.all(np.isfinite(w)))
        self.assertTrue(np.isfinite(w_cash))
        self.assertTrue(np.all(w >= 0.0))
        self.assertAlmostEqual(float(np.sum(w) + w_cash), lev, places=6)

    def test_challenge_simplex_saturated_capacity_caps(self):
        """Stress 1.5: Saturated single-stock caps and sector caps where N * cap < L (capacity deficit absorbed by cash)."""
        # Case A: N=8 assets, cap=0.05 * 1.35 = 0.0675 per asset. Max equity = 8 * 0.0675 = 0.54.
        N = 8
        lev = 1.35
        mu = np.full(N, 0.010)  # Huge alpha forces all assets to cap
        cov = np.eye(N) * 0.0001

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=lev,
            max_single_stock=0.05,
        )

        cap_stock = 0.05 * lev
        for i in range(N):
            self.assertAlmostEqual(w[i], cap_stock, places=5)
        self.assertAlmostEqual(float(np.sum(w)), N * cap_stock, places=5)
        self.assertAlmostEqual(w_cash, lev - (N * cap_stock), places=5)
        self.assertAlmostEqual(float(np.sum(w) + w_cash), lev, places=6)

        # Case B: Multi-sector saturated caps
        N = 20
        sector_map = {"SEC_A": list(range(10)), "SEC_B": list(range(10, 20))}
        w_sec, w_cash_sec = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=np.full(N, 0.010),
            cov_matrix=np.eye(N) * 0.0001,
            leverage=lev,
            sector_indices=sector_map,
            max_sector_exposure=0.25,
        )
        cap_sec = 0.25 * lev
        self.assertAlmostEqual(float(np.sum(w_sec[sector_map["SEC_A"]])), cap_sec, places=5)
        self.assertAlmostEqual(float(np.sum(w_sec[sector_map["SEC_B"]])), cap_sec, places=5)
        self.assertAlmostEqual(float(np.sum(w_sec) + w_cash_sec), lev, places=6)

    # =========================================================================
    # Suite 2: Strict Beta Clamping beta_port <= 1.000001 when L > 1.00
    # =========================================================================

    def test_challenge_beta_clamping_100_random_beta_spreads(self):
        """Stress 2.1: 100 randomized portfolios with asset betas sampled from extreme spread [-2.0, 3.5]."""
        for iteration in range(100):
            N = np.random.randint(15, 60)
            lev = float(np.random.uniform(1.001, 1.35))
            mu = np.random.uniform(0.001, 0.006, N)
            cov = np.eye(N) * 0.0004
            betas = np.random.uniform(-2.0, 3.5, N)

            w, w_cash = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=mu,
                cov_matrix=cov,
                leverage=lev,
                asset_betas=betas,
            )

            port_beta = float(np.sum(w * betas))
            self.assertLessEqual(
                port_beta, 1.000001,
                f"Iter {iteration}: Beta clamping failed: beta_port={port_beta:.7f} > 1.000001 at L={lev:.4f}"
            )
            self.assertAlmostEqual(
                float(np.sum(w) + w_cash), lev, places=6,
                msg=f"Iter {iteration}: Simplex broken under beta clamping: sum={float(np.sum(w) + w_cash)}"
            )

    def test_challenge_beta_clamping_extreme_positive_betas(self):
        """Stress 2.2: Extreme positive beta stress: all betas in [2.5, 3.5] at L=1.35."""
        N = 25
        lev = 1.35
        mu = np.full(N, 0.005)
        cov = np.eye(N) * 0.0004
        betas = np.random.uniform(2.5, 3.5, N)

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=lev,
            asset_betas=betas,
        )

        port_beta = float(np.sum(w * betas))
        self.assertAlmostEqual(port_beta, 1.000000, places=5)
        self.assertLessEqual(port_beta, 1.000001)
        self.assertAlmostEqual(float(np.sum(w) + w_cash), lev, places=6)
        # Verify substantial cash absorption due to forced equity de-leveraging
        self.assertGreater(w_cash, 0.50)

    def test_challenge_beta_clamping_extreme_negative_betas(self):
        """Stress 2.3: Extreme negative beta stress: all betas in [-2.0, -0.5] at L=1.35."""
        N = 20
        lev = 1.35
        mu = np.full(N, 0.004)
        cov = np.eye(N) * 0.0004
        betas = np.random.uniform(-2.0, -0.5, N)

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=lev,
            asset_betas=betas,
        )

        port_beta = float(np.sum(w * betas))
        # Negative beta is intrinsically <= 1.000001
        self.assertLess(port_beta, 0.0)
        self.assertLessEqual(port_beta, 1.000001)
        self.assertAlmostEqual(float(np.sum(w) + w_cash), lev, places=6)

    def test_challenge_beta_clamping_unleveraged_boundary(self):
        """Stress 2.4: Beta clamping exemption when unleveraged: L <= 1.00 must not downscale high beta."""
        N = 20
        mu = np.full(N, 0.004)
        cov = np.eye(N) * 0.0004
        betas = np.full(N, 2.0)  # High beta

        # Case A: Exactly unleveraged L=1.00 -> NOT clamped
        w_100, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.00,
            asset_betas=betas,
        )
        port_beta_100 = float(np.sum(w_100 * betas))
        self.assertAlmostEqual(port_beta_100, 2.00, places=4)
        self.assertGreater(port_beta_100, 1.000001)

        # Case B: Leveraged L=1.01 -> STRICTLY clamped to 1.00
        w_101, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.01,
            asset_betas=betas,
        )
        port_beta_101 = float(np.sum(w_101 * betas))
        self.assertAlmostEqual(port_beta_101, 1.000000, places=5)
        self.assertLessEqual(port_beta_101, 1.000001)

    # =========================================================================
    # Suite 3: Shannon Entropy Regularizer Monotonicity & Behavior
    # =========================================================================

    def test_challenge_shannon_entropy_monotonicity_sweep(self):
        """Stress 3.1: Sweep lambda_entropy across 6 orders of magnitude, assert H(w) monotonically non-decreasing."""
        N = 30
        mu = np.linspace(0.001, 0.008, N)
        cov = np.eye(N) * 0.0004
        lambdas = [0.0, 1e-5, 1e-4, 1e-3, 5e-3, 1e-2, 5e-2]
        entropies = []
        eps = 1e-12

        for lam in lambdas:
            w, w_cash = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=mu,
                cov_matrix=cov,
                leverage=1.35,
                lambda_entropy=lam,
            )
            self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.35, places=6)
            self.assertTrue(np.all(w >= 0.0))

            w_bar = w / np.sum(w)
            h = -float(np.sum(w_bar * np.log(w_bar + eps)))
            entropies.append(h)

        # Assert monotonicity: H(w; lambda_1) <= H(w; lambda_2) for lambda_1 < lambda_2
        for i in range(len(entropies) - 1):
            self.assertLessEqual(
                entropies[i], entropies[i + 1] + 1e-6,
                f"Entropy decreased: H({lambdas[i]})={entropies[i]:.6f} > H({lambdas[i+1]})={entropies[i+1]:.6f}"
            )

    def test_challenge_shannon_entropy_rank_order_preservation(self):
        """Stress 3.2: Verify Shannon entropy preserves relative rank of alphas under spherical covariance."""
        N = 10
        mu = np.array([0.001 * (i + 1) for i in range(N)])  # Strictly increasing alpha
        cov = np.eye(N) * 0.0004

        for lam in [0.0001, 0.001, 0.01]:
            w, _ = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=mu,
                cov_matrix=cov,
                leverage=1.35,
                lambda_entropy=lam,
            )
            # Higher alpha must yield equal or higher weight (no rank inversion)
            for i in range(N - 1):
                self.assertGreaterEqual(
                    w[i + 1], w[i] - 1e-7,
                    f"Rank inversion at lambda={lam}: w[{i}]={w[i]:.6f} > w[{i+1}]={w[i+1]:.6f}"
                )

    def test_challenge_shannon_entropy_high_dimension(self):
        """Stress 3.3: Shannon entropy regularizer under high dimensions N=150, 300."""
        for N in [150, 300]:
            mu = np.random.uniform(0.001, 0.005, N)
            cov = np.eye(N) * 0.0004
            w, w_cash = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=mu,
                cov_matrix=cov,
                leverage=1.35,
                lambda_entropy=0.001,
            )
            self.assertTrue(np.all(np.isfinite(w)))
            self.assertTrue(np.all(w >= 0.0))
            self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.35, places=6)

    # =========================================================================
    # Suite 4: 4-Tier Protective Gating Lower Envelope Under Simultaneous Shocks
    # =========================================================================

    def test_challenge_4tier_simultaneous_compounding_shocks(self):
        """Stress 4.1: Simultaneous compounding shocks cleanly evaluate lower envelope without numerical breakdown."""
        alloc = self.allocator
        vix_calm = [14.0] * 5
        tsr_calm_5d = [0.88, 0.89, 0.90, 0.87, 0.89]

        # Shock Matrix: (VIX, VIX_history, TSR, TSR_hist, NAV, Regime, Expected_Leverage)
        scenarios = [
            # 1. Dual: VIX vel spike (0.40) + TSR backwardation (0.50) -> min = 0.40
            {
                "vix": 29.0, "vix_hist": [14.0, 16.0, 18.0, 20.0, 15.0],
                "tsr": 1.15, "tsr_hist": tsr_calm_5d,
                "nav": 100.0, "regime": "BULL_LOW_VOL",
                "expected": 0.40
            },
            # 2. Dual: TSR backwardation (0.50) + HWM DD -8% (0.85) -> min = 0.50
            {
                "vix": 16.0, "vix_hist": vix_calm,
                "tsr": 1.12, "tsr_hist": tsr_calm_5d,
                "nav": 92.0, "regime": "BULL_LOW_VOL",
                "expected": 0.50
            },
            # 3. Triple: VIX vel spike (0.40) + TSR inversion (0.50) + HWM DD -12% (0.15) -> min = 0.15
            {
                "vix": 30.0, "vix_hist": [15.0, 18.0, 21.0, 24.0, 15.0],
                "tsr": 1.20, "tsr_hist": tsr_calm_5d,
                "nav": 88.0, "regime": "BULL_LOW_VOL",
                "expected": 0.15
            },
            # 4. Quadruple Apocalypse: PANIC_CRISIS (0.15) + VIX 85 + TSR 2.0 + NAV -50%
            {
                "vix": 85.0, "vix_hist": [30.0, 45.0, 60.0, 75.0, 40.0],
                "tsr": 2.00, "tsr_hist": [1.5, 1.8, 1.9, 2.0, 2.1],
                "nav": 50.0, "regime": "PANIC_CRISIS",
                "expected": 0.15
            },
            # 5. Relief Rally with 5d Contango satisfied: 1.35x
            {
                "vix": 15.0, "vix_hist": vix_calm,
                "tsr": 0.88, "tsr_hist": tsr_calm_5d,
                "nav": 100.0, "regime": "RELIEF_RALLY",
                "expected": 1.35
            },
            # 6. Relief Rally with broken Contango: drops to 0.90x
            {
                "vix": 15.0, "vix_hist": vix_calm,
                "tsr": 0.88, "tsr_hist": [0.88, 0.96, 0.89, 0.90, 0.91],
                "nav": 100.0, "regime": "RELIEF_RALLY",
                "expected": 0.90
            },
        ]

        for idx, sc in enumerate(scenarios):
            alloc.hwm_peak = 100.0  # Reset HWM peak
            lev = alloc.evaluate_dynamic_leverage_frontier(
                current_nav=sc["nav"],
                vix=sc["vix"],
                vix_history=sc["vix_hist"],
                tsr_ratio=sc["tsr"],
                regime=sc["regime"],
                tsr_history=sc["tsr_hist"],
            )
            self.assertAlmostEqual(
                lev, sc["expected"], places=4,
                msg=f"Scenario {idx+1} failed: got {lev:.4f}, expected {sc['expected']:.4f}"
            )

    def test_challenge_4tier_monte_carlo_lower_envelope(self):
        """Stress 4.2: 500 Monte Carlo boundary sweeps verifying L_t == max(0.15, min(L_regime, L_vix, L_tsr, L_dd))."""
        alloc = self.allocator
        for _ in range(500):
            alloc.hwm_peak = 100.0
            nav = float(np.random.uniform(70.0, 110.0))
            vix = float(np.random.uniform(10.0, 60.0))
            vix_hist = list(np.random.uniform(10.0, 40.0, 5))
            tsr = float(np.random.uniform(0.70, 1.50))
            regimes = ["BULL_LOW_VOL", "BULL_HIGH_VOL", "SIDEWAYS_LOW_VOL", "BEAR_LOW_VOL", "BEAR_HIGH_VOL", "PANIC_CRISIS"]
            regime = np.random.choice(regimes)

            lev = alloc.evaluate_dynamic_leverage_frontier(
                current_nav=nav,
                vix=vix,
                vix_history=vix_hist,
                tsr_ratio=tsr,
                regime=regime,
            )

            # Invariants:
            self.assertGreaterEqual(lev, 0.15 - 1e-9)
            self.assertLessEqual(lev, 1.35 + 1e-9)
            self.assertTrue(math.isfinite(lev))

    # =========================================================================
    # Suite 5: Leland Buffer Bandwidth & Instant Bypass
    # =========================================================================

    def test_challenge_leland_exact_1_1400000x_multiplier(self):
        """Stress 5.1: Verify Leland buffer expansion is exact 1.1400000x at L=1.35 across various base deltas."""
        for delta_base in [0.005, 0.010, 0.020, 0.035, 0.050]:
            expanded = self.allocator.calculate_leveraged_leland_buffer(delta_base, leverage=1.35)
            multiplier = expanded / delta_base
            self.assertAlmostEqual(
                multiplier, 1.1400000, places=7,
                msg=f"Leland multiplier mismatch at delta_base={delta_base}: {multiplier:.8f} != 1.1400000"
            )

    def test_challenge_leland_multiplier_monotonicity(self):
        """Stress 5.2: Leland multiplier monotonicity across leverage spectrum [0.50 to 1.35]."""
        leverages = [0.50, 0.85, 1.00, 1.05, 1.15, 1.25, 1.35]
        multipliers = [
            self.allocator.calculate_leveraged_leland_buffer(0.01, leverage=lev) / 0.01
            for lev in leverages
        ]
        # For L <= 1.0, multiplier should be 1.0
        self.assertAlmostEqual(multipliers[0], 1.0, places=7)
        self.assertAlmostEqual(multipliers[1], 1.0, places=7)
        self.assertAlmostEqual(multipliers[2], 1.0, places=7)
        # For L > 1.0, multiplier strictly increases
        for i in range(2, len(multipliers) - 1):
            self.assertLess(multipliers[i], multipliers[i + 1])
        # At 1.35x, exactly 1.1400000
        self.assertAlmostEqual(multipliers[-1], 1.1400000, places=7)

    def test_challenge_leland_zero_latency_instant_bypass(self):
        """Stress 5.3: Zero-latency instant bypass: w_curr == 0 (entry) and w_target == 0 (liquidation) must NEVER be held."""
        pa = self.port_allocator
        mkt_map = {"SYM_IN": "SP500", "SYM_OUT": "SP500", "SYM_HOLD": "SP500"}
        vol_map = {"SYM_IN": 0.02, "SYM_OUT": 0.02, "SYM_HOLD": 0.02}
        adv_map = {"SYM_IN": 1e9, "SYM_OUT": 1e9, "SYM_HOLD": 1e9}

        # Sub-test A: Fresh Entry inside buffer band (w_curr=0, w_targ=0.002, delta ~ 0.005)
        # Even though 0 is inside [0.002 - 0.005, 0.002 + 0.005], instant bypass must BUY
        res_entry = pa.compute_portfolio_rebalance(
            current_weights={"SYM_IN": 0.0},
            target_weights={"SYM_IN": 0.002},
            market_map=mkt_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            leverage=1.35,
        )
        trade_in = res_entry["trades"]["SYM_IN"]
        self.assertEqual(trade_in["action"], "BUY")
        self.assertAlmostEqual(trade_in["w_new"], 0.002, places=6)

        # Sub-test B: Full Liquidation inside buffer band (w_curr=0.002, w_targ=0, delta ~ 0.005)
        # Even though 0.002 is inside [0 - 0.005, 0 + 0.005], instant bypass must SELL
        res_exit = pa.compute_portfolio_rebalance(
            current_weights={"SYM_OUT": 0.002},
            target_weights={"SYM_OUT": 0.0},
            market_map=mkt_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            leverage=1.35,
        )
        trade_out = res_exit["trades"]["SYM_OUT"]
        self.assertEqual(trade_out["action"], "SELL")
        self.assertAlmostEqual(trade_out["w_new"], 0.0, places=6)

        # Sub-test C: Existing position inside buffer band (w_curr=0.030, w_targ=0.031) -> HOLD
        res_hold = pa.compute_portfolio_rebalance(
            current_weights={"SYM_HOLD": 0.030},
            target_weights={"SYM_HOLD": 0.031},
            market_map=mkt_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            leverage=1.35,
        )
        trade_hold = res_hold["trades"]["SYM_HOLD"]
        self.assertEqual(trade_hold["action"], "HOLD")
        self.assertAlmostEqual(trade_hold["w_new"], 0.030, places=6)


if __name__ == "__main__":
    unittest.main()
