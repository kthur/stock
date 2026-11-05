"""
tests/test_phase145_empirical_challenger.py - Rigorous Empirical Challenger Suite for Phase 145.
Features F705, F706, F707, F708, F709.

Adversarial Stress Test Matrix:
1. Gross Leverage Frontier & 5-Day Contango Hysteresis in RELIEF_RALLY & BULL_LOW_VOL.
2. Strict Beta Clamping (beta_port <= 1.000001) under extreme high-beta and mixed assets with cash buffering.
3. Rapid De-leveraging (0.15x ~ 0.25x) during Crisis/Bear Regimes and step-change transitions.
4. 4-Tier Protective Gating Lower Envelope across 1,000 Monte Carlo boundary sweeps.
5. Fractional Kelly 4th-Order Fat-Tail Risk Contraction under asymmetric and heavy-tailed distributions.
6. Simplex Conservation & Capacity Invariance across 500 randomized portfolios.
7. PortfolioAllocator & UnifiedPortfolioAllocator Integration, Leland Multiplier & Instant Bypass.
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
    Phase145KellyAllocator,
    VERSION,
    RELEASE,
    FEATURE,
)
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase145EmpiricalChallenger(unittest.TestCase):
    """Rigorous Empirical Adversarial Suite for Phase 145."""

    def setUp(self):
        np.random.seed(20261031)
        self.allocator = DynamicRegimeLeverageAllocator(
            max_bull_leverage=1.30,
            min_crisis_exposure=0.15,
            borrowing_spread_bps=60.0,
            hwm_dd_limit=-0.15,
            default_kappa=0.375,
            top_k_modes=50,
        )

    # =========================================================================
    # 1. Gross Leverage Ceiling & 5-Day Contango Hysteresis
    # =========================================================================

    def test_challenger_bull_low_vol_ceiling_exact(self):
        """Verify BULL_LOW_VOL gross leverage is exactly 1.30x under ideal calm conditions."""
        vix_hist = [12.0, 12.1, 12.0, 12.2, 12.0]
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=12.0,
            vix_history=vix_hist,
            tsr_ratio=0.85,
            regime="BULL_LOW_VOL",
        )
        self.assertEqual(L, 1.30)

    def test_challenger_relief_rally_5d_contango_boundary_scan(self):
        """
        Exhaustive scan of the 5-day contango lock:
        TSR < 0.95 for 5 consecutive days is required to reach 1.30x.
        Any breach (even by 1e-6) must lock leverage to 0.90x.
        """
        vix_hist = [14.0] * 5

        # Case A: Exactly 5 consecutive days below 0.95
        pass_history = [0.949, 0.940, 0.930, 0.920, 0.910]
        L_pass = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0, vix=14.0, vix_history=vix_hist, tsr_ratio=0.910,
            regime="RELIEF_RALLY", tsr_history=pass_history
        )
        self.assertEqual(L_pass, 1.30)

        # Case B: Each position in past 5 days individually breaches 0.95
        for breach_idx in range(5):
            fail_history = [0.900] * 5
            fail_history[breach_idx] = 0.950001
            L_fail = self.allocator.evaluate_dynamic_leverage_frontier(
                current_nav=100.0, vix=14.0, vix_history=vix_hist, tsr_ratio=0.900,
                regime="RELIEF_RALLY", tsr_history=fail_history
            )
            self.assertEqual(L_fail, 0.90, f"Failed at breach_idx={breach_idx}")

        # Case C: Boundary condition at exactly 0.9500000000
        boundary_history = [0.94, 0.94, 0.94, 0.94, 0.95]
        L_boundary = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0, vix=14.0, vix_history=vix_hist, tsr_ratio=0.94,
            regime="RELIEF_RALLY", tsr_history=boundary_history
        )
        self.assertEqual(L_boundary, 0.90)

        # Case D: Older breach beyond 5 days does NOT lock
        # History length 7: day -7 was 1.10, but last 5 days are < 0.95
        clean_7d = [1.10, 1.05, 0.92, 0.91, 0.93, 0.89, 0.90]
        L_7d = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0, vix=14.0, vix_history=vix_hist, tsr_ratio=0.90,
            regime="RELIEF_RALLY", tsr_history=clean_7d
        )
        self.assertEqual(L_7d, 1.30)

        # Case E: Degenerate histories (NaN, empty, short)
        self.assertEqual(
            self.allocator.evaluate_dynamic_leverage_frontier(
                100.0, 14.0, vix_hist, 0.90, "RELIEF_RALLY", tsr_history=[]
            ),
            0.90
        )
        self.assertEqual(
            self.allocator.evaluate_dynamic_leverage_frontier(
                100.0, 14.0, vix_hist, 0.90, "RELIEF_RALLY", tsr_history=[0.90, 0.91, 0.92]
            ),
            0.90
        )
        self.assertEqual(
            self.allocator.evaluate_dynamic_leverage_frontier(
                100.0, 14.0, vix_hist, 0.90, "RELIEF_RALLY", tsr_history=None
            ),
            0.90
        )

    def test_challenger_bull_high_vol_frontier(self):
        """Verify BULL_HIGH_VOL gross leverage is 1.15x."""
        vix_hist = [16.0] * 5
        L = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0, vix=16.0, vix_history=vix_hist, tsr_ratio=0.88,
            regime="BULL_HIGH_VOL"
        )
        self.assertEqual(L, 1.15)

    # =========================================================================
    # 2. Strict Beta Clamping & Cash Buffering (beta_port <= 1.00)
    # =========================================================================

    def test_challenger_strict_beta_clamping_under_extreme_betas(self):
        """
        Adversarial: Asset betas are extreme (e.g. 2.0 to 4.5).
        Under leverage=1.30, portfolio beta must be clamped strictly to <= 1.000001.
        Excess capital must be buffered in cash, so sum(w) + w_cash == 1.30.
        """
        N = 20
        mu = np.full(N, 0.005)
        cov = np.eye(N) * 0.0004
        extreme_betas = np.linspace(2.0, 4.0, N)  # Average beta = 3.0

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.30,
            asset_betas=extreme_betas,
        )

        realized_beta = float(np.sum(w * extreme_betas))
        self.assertLessEqual(realized_beta, 1.000001)
        self.assertGreater(realized_beta, 0.95)  # Clamped accurately near 1.00

        # Cash buffer absorbs all reduced allocation
        total_sum = float(np.sum(w)) + w_cash
        self.assertAlmostEqual(total_sum, 1.30, places=7)
        self.assertGreater(w_cash, 0.80)  # Significant cash buffer created

    def test_challenger_beta_clamping_mixed_negative_and_zero_betas(self):
        """
        Adversarial: Portfolio contains negative beta (inverse ETFs), zero beta, and high beta.
        Clamping must only activate if net portfolio beta exceeds 1.00.
        """
        N = 5
        mu = np.array([0.004, 0.005, 0.006, 0.007, 0.008])
        cov = np.eye(N) * 0.0004

        # Betas: [-1.5, 0.0, 0.8, 1.2, 1.5]
        mixed_betas = np.array([-1.5, 0.0, 0.8, 1.2, 1.5])
        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.30,
            asset_betas=mixed_betas,
        )
        port_beta = float(np.sum(w * mixed_betas))
        self.assertLessEqual(port_beta, 1.000001)
        self.assertAlmostEqual(float(np.sum(w)) + w_cash, 1.30, places=7)

    def test_challenger_unleveraged_beta_exemption(self):
        """When leverage <= 1.00, beta clamping is not enforced."""
        N = 25  # 25 assets * 0.05 cap = 1.25 >= 1.00 capacity
        mu = np.full(N, 0.005)
        cov = np.eye(N) * 0.0004
        high_betas = np.full(N, 1.80)

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.00,
            asset_betas=high_betas,
        )
        port_beta = float(np.sum(w * high_betas))
        # Since leverage <= 1.00, port_beta can be 1.80 (no clamping)
        self.assertGreater(port_beta, 1.00)
        self.assertAlmostEqual(port_beta, 1.80, places=4)
        self.assertAlmostEqual(float(np.sum(w)) + w_cash, 1.00, places=7)

    def test_challenger_unified_allocator_beta_clamping(self):
        """Verify UnifiedPortfolioAllocator clamps beta to <= 1.00 under leverage=1.30."""
        upa = UnifiedPortfolioAllocator(version=145)
        w = np.array([0.5, 0.5])
        cov = np.eye(2) * 0.00002
        high_betas = np.array([2.2, 2.2])

        scaled_w, eff_alloc = upa.apply_target_volatility_scaling(
            weights=w,
            cov_matrix=cov,
            regime="BULL_LOW_VOL",
            expected_returns=np.array([0.20, 0.20]),
            asset_betas=high_betas,
        )
        self.assertAlmostEqual(eff_alloc, 1.30, places=2)
        port_beta = float(np.sum(scaled_w * high_betas))
        self.assertLessEqual(port_beta, 1.000001)

    # =========================================================================
    # 3. Rapid De-leveraging in Crisis & Bear Regimes
    # =========================================================================

    def test_challenger_rapid_deleveraging_regime_targets(self):
        """Verify rapid de-leveraging to 0.15x ~ 0.25x in bear/crisis regimes."""
        vix_hist = [15.0] * 5
        nav = 100.0
        tsr = 0.90

        # BEAR_HIGH_VOL -> 0.25x
        L_bear_hi = self.allocator.evaluate_dynamic_leverage_frontier(
            nav, 16.0, vix_hist, tsr, "BEAR_HIGH_VOL"
        )
        self.assertEqual(L_bear_hi, 0.25)

        # PANIC_CRISIS -> 0.15x
        L_panic = self.allocator.evaluate_dynamic_leverage_frontier(
            nav, 16.0, vix_hist, tsr, "PANIC_CRISIS"
        )
        self.assertEqual(L_panic, 0.15)

        # BEAR_LOW_VOL -> 0.60x
        L_bear_lo = self.allocator.evaluate_dynamic_leverage_frontier(
            nav, 16.0, vix_hist, tsr, "BEAR_LOW_VOL"
        )
        self.assertEqual(L_bear_lo, 0.60)

    def test_challenger_instantaneous_crisis_transition_simulation(self):
        """
        Stress: Sequential simulation of 10 calm bull days (1.30x)
        followed by a flash crisis on Day 11.
        Leverage must drop instantaneously from 1.30x to 0.15x with 0 lag.
        """
        alloc = DynamicRegimeLeverageAllocator(max_bull_leverage=1.30)
        nav = 100.0
        vix_hist = [12.0] * 5

        # 10 days of BULL_LOW_VOL
        for day in range(1, 11):
            L = alloc.evaluate_dynamic_leverage_frontier(nav, 12.0, vix_hist, 0.88, "BULL_LOW_VOL")
            self.assertEqual(L, 1.30)

        # Day 11: Regime shifts to PANIC_CRISIS
        L_crisis = alloc.evaluate_dynamic_leverage_frontier(nav, 12.0, vix_hist, 0.88, "PANIC_CRISIS")
        self.assertEqual(L_crisis, 0.15)

    def test_challenger_casing_and_alias_robustness(self):
        """Adversarial: Unusual regime string casing and variants."""
        vix_hist = [15.0] * 5
        variants = [
            ("panic_crisis", 0.15),
            ("Crisis", 0.15),
            ("CRISIS_PANIC", 0.15),
            ("bear_high_vol", 0.25),
            ("BEAR_HIGH_VOL", 0.25),
            ("bull_low_vol", 1.30),
        ]
        for reg_str, expected in variants:
            L = self.allocator.evaluate_dynamic_leverage_frontier(
                100.0, 15.0, vix_hist, 0.88, reg_str
            )
            self.assertEqual(L, expected, f"Failed for regime {reg_str}")

    # =========================================================================
    # 4. 4-Tier Protective Gating Lower Envelope (Monte Carlo Sweep)
    # =========================================================================

    def test_challenger_4tier_protective_gating_lower_envelope_monte_carlo(self):
        """
        1,000 randomized Monte Carlo scenarios across all 4 protective gates:
        1. Gate 1: VIX level [10, 80], VIX velocity [-5, +15]
        2. Gate 2: TSR [0.5, 2.0]
        3. Gate 3: HWM Drawdown [-35%, 0%]
        4. Regime: All 8 regimes
        Invariants:
        - Leverage is ALWAYS in [0.15, 1.30]
        - Leverage is <= vix_cap
        - Leverage is <= tsr_cap
        - Leverage is <= dd_cap
        - No NaNs or infinities
        """
        regimes = [
            "BULL_LOW_VOL", "RELIEF_RALLY", "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL", "BEAR_HIGH_VOL", "PANIC_CRISIS"
        ]

        for i in range(1000):
            alloc = DynamicRegimeLeverageAllocator(max_bull_leverage=1.30)
            nav_peak = np.random.uniform(100.0, 200.0)
            dd_pct = np.random.uniform(-0.35, 0.0)
            curr_nav = nav_peak * (1.0 + dd_pct)

            # Establish peak
            alloc.evaluate_dynamic_leverage_frontier(nav_peak, 14.0, [14.0]*5, 0.88, "BULL_LOW_VOL")

            vix = np.random.uniform(10.0, 80.0)
            vix_5d_ago = np.random.uniform(10.0, 80.0)
            vix_hist = [vix_5d_ago] * 5
            vix_vel = (vix - vix_5d_ago) / 5.0

            tsr = np.random.uniform(0.50, 2.00)
            reg = np.random.choice(regimes)

            L = alloc.evaluate_dynamic_leverage_frontier(
                current_nav=curr_nav,
                vix=vix,
                vix_history=vix_hist,
                tsr_ratio=tsr,
                regime=reg,
            )

            # Assert invariants
            self.assertTrue(math.isfinite(L), f"L is not finite: {L}")
            self.assertGreaterEqual(L, 0.15 - 1e-9)
            self.assertLessEqual(L, 1.30 + 1e-9)

            # Theoretical gate caps
            if vix > 28.0 or vix_vel > 2.00:
                self.assertLessEqual(L, 0.40 + 1e-9)
            elif vix > 22.0 or vix_vel > 1.00:
                self.assertLessEqual(L, 0.75 + 1e-9)
            elif vix > 18.0 or vix_vel > 0.50:
                self.assertLessEqual(L, 1.00 + 1e-9)

            if tsr >= 1.08:
                self.assertLessEqual(L, 0.50 + 1e-9)
            elif tsr >= 1.00:
                self.assertLessEqual(L, 0.80 + 1e-9)

            if dd_pct <= -0.120:
                self.assertEqual(L, 0.15)
            elif dd_pct <= -0.100:
                self.assertLessEqual(L, 0.50 + 1e-9)
            elif dd_pct <= -0.070:
                self.assertLessEqual(L, 0.85 + 1e-9)

    def test_challenger_simultaneous_multi_gate_shock(self):
        """Stress: Simultaneous activation of all 4 gates (VIX spike + backwardation + drawdown)."""
        alloc = DynamicRegimeLeverageAllocator(max_bull_leverage=1.30)
        alloc.evaluate_dynamic_leverage_frontier(100.0, 14.0, [14.0]*5, 0.88, "BULL_LOW_VOL")

        # Multi-shock: VIX=38 (cap 0.40), TSR=1.20 (cap 0.50), DD=-11% (cap 0.50)
        L = alloc.evaluate_dynamic_leverage_frontier(
            current_nav=89.0,
            vix=38.0,
            vix_history=[20.0]*5,  # vel = (38-20)/5 = 3.6 > 2.0
            tsr_ratio=1.20,
            regime="BULL_LOW_VOL",
        )
        # Min envelope: min(1.30, 0.40, 0.50, 0.50) = 0.40
        self.assertAlmostEqual(L, 0.40, places=5)

    # =========================================================================
    # 5. Fractional Kelly 4th-Order Fat-Tail Risk Contraction
    # =========================================================================

    def test_challenger_fat_tail_monotonic_contraction(self):
        """
        Verify:
        1. Within a portfolio, as an asset's negative coskewness intensifies,
           its individual allocation strictly decreases monotonically.
        2. When all assets suffer catastrophic tail risk (mu_eff <= 0),
           equity allocation drops to 0.0 and cash absorbs 100% of the gross leverage frontier.
        """
        N = 25
        mu = np.linspace(0.003, 0.006, N)
        cov = np.eye(N) * 0.0004

        # Baseline: normal distribution (s = 0, k = 0)
        w_base, cash_base = self.allocator.compute_fractional_kelly_weights(
            mu, cov, leverage=1.30, coskewness=np.zeros(N), cokurtosis=np.zeros(N)
        )

        # Asset 0 subjected to graduated negative coskewness
        s_levels = [-0.001, -0.003, -0.006]
        w_asset0 = [w_base[0]]

        for s_val in s_levels:
            s_vec = np.zeros(N)
            s_vec[0] = s_val
            w_test, _ = self.allocator.compute_fractional_kelly_weights(
                mu, cov, leverage=1.30, coskewness=s_vec
            )
            w_asset0.append(w_test[0])

        # Assert strict monotonic decrease of Asset 0's weight
        for i in range(len(w_asset0) - 1):
            self.assertGreater(w_asset0[i], w_asset0[i + 1])

        # Catastrophic scenario: all assets have severe crash risk overwhelming expected return
        s_cat = np.full(N, -0.050)
        k_cat = np.full(N, 0.150)
        w_cat, cash_cat = self.allocator.compute_fractional_kelly_weights(
            mu, cov, leverage=1.30, coskewness=s_cat, cokurtosis=k_cat
        )
        self.assertEqual(float(np.sum(w_cat)), 0.0)
        self.assertAlmostEqual(cash_cat, 1.30, places=7)

    def test_challenger_fat_tail_heavy_tailed_pareto_student_t(self):
        """Stress: Empirical co-moments calculated from Student-t (df=2.5) with extreme outliers."""
        T, N = 300, 20
        # Student-t with df=2.5 has heavy fat tails
        raw_rets = np.random.standard_t(df=2.5, size=(T, N)) * 0.015
        s_w, k_w = self.allocator.compute_higher_order_co_moments(raw_rets)

        self.assertEqual(len(s_w), N)
        self.assertEqual(len(k_w), N)
        self.assertTrue(np.all(np.isfinite(s_w)))
        self.assertTrue(np.all(np.isfinite(k_w)))

        # Allocate with empirical higher co-moments
        mu = np.full(N, 0.004)
        cov = np.cov(raw_rets, rowvar=False) + 1e-4 * np.eye(N)
        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            mu, cov, leverage=1.30, coskewness=s_w, cokurtosis=k_w
        )
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertTrue(np.all(w >= 0.0))
        self.assertAlmostEqual(float(np.sum(w)) + w_cash, 1.30, places=7)

    # =========================================================================
    # 6. Simplex Sum Conservation & Capacity Limits across 500 Portfolios
    # =========================================================================

    def test_challenger_simplex_and_capacity_random_sweep(self):
        """
        Adversarial: 500 randomized portfolios with random asset counts N in [5, 40],
        random expected returns, random covariances, random sector groupings,
        and random leverage in [0.20, 1.30].
        Assert:
        1. sum(w) + w_cash == leverage (tolerance 1e-6)
        2. w_i <= 0.05 * leverage + 1e-9 (single stock capacity)
        3. sum(w_sector) <= 0.25 * leverage + 1e-9 (sector capacity)
        4. w_i >= 0.0 and w_cash >= 0.0
        5. Zero NaNs
        """
        for trial in range(500):
            N = np.random.randint(5, 41)
            lev = float(np.random.uniform(0.20, 1.30))
            mu = np.random.uniform(-0.002, 0.010, N)

            # Random valid positive definite covariance
            A = np.random.normal(0, 0.02, size=(N, N))
            cov = A @ A.T + 1e-4 * np.eye(N)

            # Random sectors: 3 sectors
            sectors = {"Sec1": [], "Sec2": [], "Sec3": []}
            sec_keys = list(sectors.keys())
            for idx in range(N):
                sectors[sec_keys[idx % 3]].append(idx)

            betas = np.random.uniform(0.5, 2.5, N)

            w, w_cash = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=mu,
                cov_matrix=cov,
                leverage=lev,
                sector_indices=sectors,
                asset_betas=betas,
            )

            # Invariant 1: Simplex conservation
            tot_sum = float(np.sum(w)) + w_cash
            self.assertAlmostEqual(tot_sum, lev, places=6, msg=f"Trial {trial} simplex sum failed")

            # Invariant 2: Single stock capacity
            cap_stock = 0.05 * lev + 1e-8
            self.assertTrue(np.all(w <= cap_stock), f"Trial {trial} single-stock cap breached: {np.max(w)} > {cap_stock}")

            # Invariant 3: Sector capacity
            cap_sector = 0.25 * lev + 1e-7
            for sec_name, idxs in sectors.items():
                sec_weight = float(np.sum(w[idxs]))
                self.assertLessEqual(sec_weight, cap_sector, f"Trial {trial} sector {sec_name} cap breached")

            # Invariant 4: Non-negativity
            self.assertTrue(np.all(w >= -1e-12), f"Trial {trial} negative weight found")
            self.assertGreaterEqual(w_cash, -1e-12, f"Trial {trial} negative cash found")

            # Invariant 5: Beta clamping if lev > 1.00
            if lev > 1.00:
                p_beta = float(np.sum(w * betas))
                self.assertLessEqual(p_beta, 1.000001, f"Trial {trial} beta clamping breached: {p_beta}")

    # =========================================================================
    # 7. PortfolioAllocator & Dynamic Rebalance Integration
    # =========================================================================

    def test_challenger_portfolio_allocator_leland_expansion_and_bypass(self):
        """
        Verify:
        1. At leverage 1.30x, Leland dynamic buffer band expands by exactly 1.12x.
        2. Fresh entry (w_curr == 0.0) instantly bypasses the buffer band.
        3. Full liquidation (w_targ == 0.0) instantly bypasses the buffer band.
        4. Summary total_asset_weight + cash_weight == 1.30x.
        """
        pa = PortfolioAllocator(version=145)

        # Baseline unleveraged delta
        delta_base = pa.calculate_dynamic_buffer_band(
            symbol="AAPL", target_weight=0.04, cost_rate=0.0010, volatility_20d=0.02, leverage=1.00
        )
        # Leveraged delta (1.30x) -> expansion factor = 1.0 + 0.40 * (1.30 - 1.0) = 1.12
        delta_lev = pa.calculate_dynamic_buffer_band(
            symbol="AAPL", target_weight=0.04, cost_rate=0.0010, volatility_20d=0.02, leverage=1.30
        )
        self.assertAlmostEqual(delta_lev / delta_base, 1.12, places=5)

        # Test compute_portfolio_rebalance with leverage=1.30
        curr_w = {"NEW_POS": 0.0, "EXIT_POS": 0.04, "HOLD_POS": 0.05}
        tgt_w = {"NEW_POS": 0.05, "EXIT_POS": 0.00, "HOLD_POS": 0.051}  # Small drift for HOLD_POS
        mkt_map = {"NEW_POS": "SP500", "EXIT_POS": "SP500", "HOLD_POS": "SP500"}
        vol_map = {"NEW_POS": 0.02, "EXIT_POS": 0.02, "HOLD_POS": 0.02}
        adv_map = {"NEW_POS": 1e9, "EXIT_POS": 1e9, "HOLD_POS": 1e9}

        res = pa.compute_portfolio_rebalance(
            current_weights=curr_w,
            target_weights=tgt_w,
            market_map=mkt_map,
            volatility_map=vol_map,
            adv_map=adv_map,
            leverage=1.30,
        )

        trades = res["trades"]
        # NEW_POS: instant bypass -> BUY
        self.assertEqual(trades["NEW_POS"]["action"], "BUY")
        self.assertEqual(trades["NEW_POS"]["w_target"], 0.05)
        self.assertEqual(trades["NEW_POS"]["w_new"], 0.05)

        # EXIT_POS: instant bypass -> SELL
        self.assertEqual(trades["EXIT_POS"]["action"], "SELL")
        self.assertEqual(trades["EXIT_POS"]["w_target"], 0.00)
        self.assertEqual(trades["EXIT_POS"]["w_new"], 0.00)

        # Total sum check
        summary = res["summary"]
        self.assertAlmostEqual(summary["total_asset_weight"] + summary["cash_weight"], 1.30, places=5)


if __name__ == "__main__":
    unittest.main()
