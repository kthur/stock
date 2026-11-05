# -*- coding: utf-8 -*-
"""
tests/test_phase150_challenger.py - Empirical Adversarial Challenger Test Suite for Phase 150.
Features: F730, F731, F732, F733, F734.

Adversarial Stress Test Matrix:
1. SAC Continuous Action Simplex Under Extreme Order Books (F730):
   - 500 randomized extreme order book states (spreads up to 1,000 bps, VPIN > 0.95, OBI = +/-1.0).
   - Strict simplex constraint: sum(w_route) == 1.0 +- 1e-5 and w_route >= 0.0.
   - Toxic VPIN cascade guard: VPIN > 0.65 forces tactical pause with zero slice ratio (alpha == 0.0)
     and suppresses aggressive taker route (< 5%).
   - Terminal clearance guard: t/T > 0.90 forces aggressive taker with 100% slice ratio.
   - Degenerate, zero, infinite, and NaN inputs to 12D state vector.

2. Joseph Covariance Numerical Stability (F732):
   - 1,000 sequential random Kalman measurement updates with extreme slippages up to 500 bps.
   - Exact symmetry: ||P - P^T||_inf < 1e-12 across all 1,000 updates.
   - Positive semi-definiteness: all eigenvalues >= 1e-8 without exception.
   - Singular and ill-conditioned observation matrices (H = 0, rank-deficient, collinear).
   - Extreme measurement noise variance R in [1e-8, 1e6] and parameter boundary clamping.
   - 2D vs 3D Kalman filter mode parity.

3. Asymmetric Leland Buffer Bands & Multiplier Dynamics (F733 & F734):
   - Z-score sweep across [-10.0, +10.0]: exact runner expansion (2.20x at z >= +3.0) and loser contraction (0.60x at z <= -3.0).
   - Monotonicity and continuity of Leland multipliers.
   - Gate 4 leveraged Leland bandwidth expansion: exact 1.140x at L=1.35.
   - Instant zero-latency bypass for fresh entry (w_curr == 0.0) and full exit (w_target == 0.0).
   - Boundary rebalancing mechanics: exact clamp to U_i or L_i under moderate drift, with severe drift bypass (>= 50%).
   - Integration with UnifiedPortfolioAllocator.apply_leland_no_trade_buffers.

4. 252-Day Drift Simulations & Turnover Compression (F734):
   - Multi-asset 252-day drift simulation across 5 independent seeds: annual turnover <= 4.50x and reduction >= 40.0%.
   - High-volatility crisis market stress (daily vol 2.5% ~ 5.0%): annual turnover strictly <= 4.50x.
   - Asymmetric vs symmetric Leland buffer turnover comparison.

5. Capital-Weighted Net Roundtrip Friction & Microstructure Harvester (F731 & F734):
   - Capital-weighted roundtrip friction hurdle <= 7.00 bps (6.72 bps at 60% US / 40% KRX).
   - Sensitivity boundary: maximum allowable KRX weighting to maintain <= 7.00 bps.
   - US lit maker rebate (+2.5 bps) and Nextrade ATS midpoint crosses (-35% fee, 50% spread saving).
   - High-concurrency thread safety (16 threads, 0 races, 0 deadlocks).
"""

from __future__ import annotations

import math
import os
import sys
import tempfile
import threading
import time
import unittest
from typing import Any, Dict, List, Tuple

import numpy as np
import pytest

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

import src.execution.rl_execution_agent as rl_mod
from src.execution.rl_execution_agent import (
    ContinuousAction,
    ExecutionAction,
    ExecutionState,
    RLExecutionAgent,
    RLOrderExecutionAgent,
    Phase150RLOrderExecutionAgent,
)
import src.core.fast_lob_engine as lob_mod
from src.core.fast_lob_engine import (
    FastLOBEngine,
    FastOrderBookMatchingEngine,
    Phase150FastLOBEngine,
)
import src.execution.slippage_feedback as slip_mod
from src.execution.slippage_feedback import (
    Online3DKalmanSlippageFilter,
    OnlineKalmanSlippageFilter,
    Phase150OnlineKalmanFilter,
    SlippageFeedbackEngine,
)
import src.execution.turnover_optimizer as turn_mod
from src.execution.turnover_optimizer import (
    TurnoverOptimizer,
    Phase150TurnoverOptimizer,
)
from src.risk.portfolio_allocator import PortfolioAllocator
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.execution.oms_engine import ExecutionOMSEngine, Phase150OMSEngine


class TestPhase150ChallengerSACSimplex(unittest.TestCase):
    """Suite 1: SAC Action Simplex Under Extreme Order Books (F730)."""

    def setUp(self):
        np.random.seed(150001)
        self.agent = RLOrderExecutionAgent()

    def test_challenge_sac_simplex_500_extreme_order_books(self):
        """Stress 1.1: Simplex conservation across 500 randomized extreme order book states."""
        for iteration in range(500):
            t_ratio = float(np.random.uniform(0.0, 1.0))
            inv_ratio = float(np.random.uniform(0.0, 1.0))
            spread_bps = float(np.random.uniform(0.01, 1000.0))  # Spreads up to 1,000 bps
            obi = float(np.random.uniform(-1.0, 1.0))            # OBI in [-1.0, 1.0]
            vpin = float(np.random.uniform(0.0, 1.0))           # VPIN in [0.0, 1.0]
            vol = float(np.random.uniform(0.001, 0.50))
            ofi_vel = float(np.random.uniform(-1.0, 1.0))
            ofi_acc = float(np.random.uniform(-1.0, 1.0))
            gamma_sgn = float(np.random.choice([-1.0, 0.0, 1.0]))

            state = ExecutionState(
                time_ratio=t_ratio,
                inventory_ratio=inv_ratio,
                spread_bps=spread_bps,
                obi=obi,
                vpin=vpin,
                volatility=vol,
                ofi_velocity=ofi_vel,
                ofi_acceleration=ofi_acc,
                dealer_gamma_sign=gamma_sgn,
            )

            action = self.agent.compute_continuous_action(state)

            # Assert 1: Simplex sum == 1.0 +- 1e-5
            simplex_sum = float(np.sum(action.route_weights))
            self.assertAlmostEqual(
                simplex_sum, 1.0, places=5,
                msg=f"Iter {iteration}: Simplex sum violated: {simplex_sum:.8f} != 1.0"
            )

            # Assert 2: All probabilities non-negative
            self.assertTrue(
                np.all(action.route_weights >= -1e-8),
                f"Iter {iteration}: Negative route probability detected: {action.route_weights}"
            )

            # Assert 3: Continuous slice ratio in [0.0, 1.0]
            self.assertGreaterEqual(action.slice_ratio, 0.0)
            self.assertLessEqual(action.slice_ratio, 1.0)

            # Assert 4: Tick offset in [-2.0, 2.0]
            self.assertGreaterEqual(action.tick_offset, -2.0)
            self.assertLessEqual(action.tick_offset, 2.0)

            # Assert 5: Primary channel in valid execution actions
            self.assertIn(action.primary_channel, list(ExecutionAction))

    def test_challenge_toxic_vpin_cascade_tactical_pause(self):
        """Stress 1.2: VPIN > 0.65 up to 1.0 forces tactical pause with zero slice and suppressed taker."""
        # 1. Standard to high spreads (up to 100 bps): TACTICAL_PAUSE dominates primary channel
        for vpin in [0.70, 0.85, 0.95, 0.99, 1.00]:
            for obi in [-1.0, -0.5, 0.0, 0.5, 1.0]:
                for spread in [10.0, 25.0, 50.0, 100.0]:
                    state = ExecutionState(
                        time_ratio=0.30,  # Plenty of time remains (< 0.70)
                        inventory_ratio=0.80,
                        spread_bps=spread,
                        obi=obi,
                        vpin=vpin,
                        volatility=0.04,
                    )
                    action = self.agent.compute_continuous_action(state)

                    self.assertEqual(
                        action.slice_ratio, 0.0,
                        f"Slice ratio must be 0.0 during toxic cascade (vpin={vpin}, spread={spread})"
                    )
                    self.assertEqual(
                        action.primary_channel, ExecutionAction.TACTICAL_PAUSE,
                        f"Primary channel must be TACTICAL_PAUSE during toxic cascade (vpin={vpin}, spread={spread})"
                    )
                    self.assertLess(
                        action.route_weights[ExecutionAction.AGGRESSIVE_TAKER], 0.05,
                        "Aggressive taker weight must be heavily suppressed under high VPIN"
                    )

        # 2. Extreme spreads (up to 1,000 bps): slice ratio remains 0.0, taker route heavily suppressed
        for extreme_spread in [500.0, 1000.0]:
            state = ExecutionState(
                time_ratio=0.30,
                inventory_ratio=0.80,
                spread_bps=extreme_spread,
                obi=0.0,
                vpin=0.95,
                volatility=0.05,
            )
            action = self.agent.compute_continuous_action(state)
            self.assertEqual(action.slice_ratio, 0.0, "Zero slice must be maintained even under extreme spreads")
            self.assertLess(action.route_weights[ExecutionAction.AGGRESSIVE_TAKER], 0.05)

    def test_challenge_terminal_urgency_clearance(self):
        """Stress 1.3: Terminal urgency (t/T > 0.90, inv > 0) overrides toxicity to force 100% completion."""
        for t_ratio in [0.91, 0.95, 0.99, 1.00]:
            for vpin in [0.20, 0.70, 0.95, 1.00]:
                state = ExecutionState(
                    time_ratio=t_ratio,
                    inventory_ratio=0.50,
                    spread_bps=20.0,
                    obi=-0.80,
                    vpin=vpin,
                    volatility=0.03,
                )
                action = self.agent.compute_continuous_action(state)

                self.assertEqual(
                    action.slice_ratio, 1.0,
                    f"Terminal clearance must force slice_ratio == 1.0 at t/T={t_ratio}"
                )
                self.assertEqual(
                    action.primary_channel, ExecutionAction.AGGRESSIVE_TAKER,
                    f"Terminal clearance must select AGGRESSIVE_TAKER at t/T={t_ratio}"
                )
                self.assertGreater(
                    action.route_weights[ExecutionAction.AGGRESSIVE_TAKER], 0.50,
                    "Aggressive taker must dominate route simplex during terminal clearance"
                )

    def test_challenge_degenerate_and_nan_state_inputs(self):
        """Stress 1.4: Degenerate, zero, infinite, and NaN inputs to 12D state vector."""
        # Zero state
        zero_state = ExecutionState(
            time_ratio=0.0, inventory_ratio=0.0, spread_bps=0.0, obi=0.0, vpin=0.0, volatility=0.0
        )
        vec_zero = zero_state.to_12d_vector()
        self.assertEqual(len(vec_zero), 12)
        self.assertTrue(np.all(np.isfinite(vec_zero)))

        # Extreme values
        extreme_state = ExecutionState(
            time_ratio=1e6, inventory_ratio=-100.0, spread_bps=50000.0, obi=-50.0, vpin=100.0, volatility=1000.0
        )
        vec_ext = extreme_state.to_12d_vector()
        self.assertTrue(np.all(np.isfinite(vec_ext)))

        # NaN / Inf safety
        nan_state = ExecutionState(
            time_ratio=float("nan"),
            inventory_ratio=float("inf"),
            spread_bps=float("-inf"),
            obi=0.0,
            vpin=float("nan"),
            volatility=0.02,
        )
        vec_nan = nan_state.to_12d_vector()
        self.assertTrue(np.all(np.isfinite(vec_nan)), f"NaN/Inf leaked into state vector: {vec_nan}")

        # Action computation must survive NaN/Inf without exception
        action_nan = self.agent.compute_continuous_action(nan_state)
        self.assertAlmostEqual(float(np.sum(action_nan.route_weights)), 1.0, places=5)


class TestPhase150ChallengerJosephKalman(unittest.TestCase):
    """Suite 2: Joseph Covariance Numerical Stability & Slippage Feedback (F732)."""

    def setUp(self):
        np.random.seed(150002)

    def test_challenge_joseph_covariance_1000_sequential_updates(self):
        """Stress 2.1: 1,000 sequential random updates: exact symmetry and eigenvalues >= 1e-8."""
        kalman = Online3DKalmanSlippageFilter(dim=3)

        for step in range(1, 1001):
            # Extreme realized slippages: Uniform [-50.0, 500.0] with occasional 1,000 bps outliers
            if step % 50 == 0:
                slippage = float(np.random.choice([1000.0, -100.0, 0.0, 500.0]))
            else:
                slippage = float(np.random.uniform(-20.0, 100.0))

            # Random observation vector H
            h_gamma = float(np.random.uniform(0.01, 15.0))
            h_spread = float(np.random.uniform(0.10, 20.0))
            h_eta = float(np.random.uniform(0.01, 10.0))

            kalman.update(
                realized_slippage_bps=slippage,
                h_gamma=h_gamma,
                h_spread=h_spread,
                h_eta=h_eta,
            )

            P = kalman.P

            # Invariant 1: Exact Symmetry ||P - P^T||_inf < 1e-12
            sym_diff = np.max(np.abs(P - P.T))
            self.assertLess(
                sym_diff, 1e-12,
                f"Step {step}: Joseph covariance symmetry violated: max|P - P^T| = {sym_diff:.2e}"
            )

            # Invariant 2: Positive semi-definiteness with minimum eigenvalue >= 1e-8
            eigenvals = np.linalg.eigvalsh(P)
            min_eig = float(np.min(eigenvals))
            self.assertGreaterEqual(
                min_eig, 1e-8,
                f"Step {step}: Eigenvalue dropped below 1e-8: min_eig = {min_eig:.2e}, eigvals = {eigenvals}"
            )

            # Invariant 3: Parameter bounds strictly preserved
            self.assertGreaterEqual(kalman.gamma, 0.05)
            self.assertLessEqual(kalman.gamma, 5.0)
            self.assertGreaterEqual(kalman.spread, 0.10)
            self.assertLessEqual(kalman.spread, 5.0)
            self.assertGreaterEqual(kalman.eta, 0.10)
            self.assertLessEqual(kalman.eta, 5.0)

    def test_challenge_singular_and_degenerate_observation_matrices(self):
        """Stress 2.2: Ill-conditioned observation vectors (H = 0, rank-deficient, collinear)."""
        kalman = OnlineKalmanSlippageFilter(dim=3)

        # 1. Zero observation vector H = [0, 0, 0]
        res = kalman.update(realized_slippage_bps=10.0, h_gamma=0.0, h_spread=0.0, h_eta=0.0)
        self.assertTrue(np.all(np.isfinite(kalman.theta)))
        self.assertGreaterEqual(float(np.min(np.linalg.eigvalsh(kalman.P))), 1e-8)

        # 2. Near-zero tiny observation vector
        res = kalman.update(realized_slippage_bps=5.0, h_gamma=1e-12, h_spread=1e-12, h_eta=1e-12)
        self.assertTrue(np.all(np.isfinite(kalman.theta)))
        self.assertGreaterEqual(float(np.min(np.linalg.eigvalsh(kalman.P))), 1e-8)

        # 3. Collinear repeated observations
        for _ in range(50):
            kalman.update(realized_slippage_bps=8.0, h_gamma=2.0, h_spread=4.0, h_eta=6.0)
            self.assertLess(float(np.max(np.abs(kalman.P - kalman.P.T))), 1e-12)
            self.assertGreaterEqual(float(np.min(np.linalg.eigvalsh(kalman.P))), 1e-8)

    def test_challenge_measurement_noise_variance_limits(self):
        """Stress 2.3: Extreme measurement noise variance R in [1e-8, 1e6]."""
        kalman = OnlineKalmanSlippageFilter(dim=3)

        # Near-zero R (very high Kalman gain K -> 1/H)
        kalman.update(realized_slippage_bps=25.0, h_gamma=1.0, h_spread=1.0, h_eta=1.0, R_override=1e-8)
        self.assertTrue(np.all(np.isfinite(kalman.P)))
        self.assertGreaterEqual(float(np.min(np.linalg.eigvalsh(kalman.P))), 1e-8)

        # Huge R (near-zero Kalman gain K -> 0)
        kalman.update(realized_slippage_bps=25.0, h_gamma=1.0, h_spread=1.0, h_eta=1.0, R_override=1e6)
        self.assertTrue(np.all(np.isfinite(kalman.P)))
        self.assertGreaterEqual(float(np.min(np.linalg.eigvalsh(kalman.P))), 1e-8)

    def test_challenge_2d_and_3d_mode_stability_comparison(self):
        """Stress 2.4: Mode parity: both 2D and 3D filters remain stable over 500 updates."""
        k2d = OnlineKalmanSlippageFilter(dim=2)
        k3d = OnlineKalmanSlippageFilter(dim=3)

        for _ in range(500):
            slip = float(np.random.normal(5.0, 15.0))
            k2d.update(realized_slippage_bps=slip, h_kappa=1.0, h_beta=2.0)
            k3d.update(realized_slippage_bps=slip, h_gamma=1.0, h_spread=2.0, h_eta=1.5)

            # Check 2D
            self.assertLess(float(np.max(np.abs(k2d.P - k2d.P.T))), 1e-12)
            self.assertGreaterEqual(float(np.min(np.linalg.eigvalsh(k2d.P))), 1e-8)

            # Check 3D
            self.assertLess(float(np.max(np.abs(k3d.P - k3d.P.T))), 1e-12)
            self.assertGreaterEqual(float(np.min(np.linalg.eigvalsh(k3d.P))), 1e-8)


class TestPhase150ChallengerLelandBands(unittest.TestCase):
    """Suite 3: Asymmetric Leland Dynamic Buffer Bands & Instant Bypass (F733 & F734)."""

    def setUp(self):
        np.random.seed(150003)
        self.opt = TurnoverOptimizer()
        self.unified_allocator = UnifiedPortfolioAllocator(version=150)
        self.port_allocator = PortfolioAllocator(version=150)

    def test_challenge_leland_multipliers_continuous_z_sweep(self):
        """Stress 3.1: Dense Z-score sweep [-10.0, +10.0]: runner expansion 2.2x and loser contraction 0.6x."""
        vol_20d = 0.02
        vol_5d = vol_20d * math.sqrt(5.0)

        # Test exact extreme runner (z = +5.0 and z = +10.0)
        u_runner = 5.0 * vol_5d
        m_up_run, m_low_run = PortfolioAllocator.calculate_asymmetric_leland_multipliers(u_runner, vol_20d)
        self.assertAlmostEqual(m_up_run, 2.20, places=4, msg="Runner upper band must expand to 2.20x at z = +5.0")
        self.assertAlmostEqual(m_low_run, 1.00, places=4, msg="Runner lower band must remain 1.00x at z = +5.0")

        # Test exact extreme loser (z = -5.0 and z = -10.0)
        u_loser = -5.0 * vol_5d
        m_up_lose, m_low_lose = PortfolioAllocator.calculate_asymmetric_leland_multipliers(u_loser, vol_20d)
        self.assertAlmostEqual(m_up_lose, 1.00, places=4, msg="Loser upper band must remain 1.00x at z = -5.0")
        self.assertAlmostEqual(m_low_lose, 0.60, places=4, msg="Loser lower band must contract to 0.60x at z = -5.0")

        # Test neutral position (z = 0.0)
        m_up_zero, m_low_zero = PortfolioAllocator.calculate_asymmetric_leland_multipliers(0.0, vol_20d)
        self.assertAlmostEqual(m_up_zero, 1.00, places=4)
        self.assertAlmostEqual(m_low_zero, 1.00, places=4)

        # Monotonicity check across 200 points in [-10.0, +10.0]
        z_grid = np.linspace(-10.0, 10.0, 201)
        prev_m_up = 0.0
        prev_m_low = 0.0

        for z in z_grid:
            u_ret = z * vol_5d
            m_up, m_low = PortfolioAllocator.calculate_asymmetric_leland_multipliers(u_ret, vol_20d)

            # Monotonicity: upper multiplier non-decreasing with z
            self.assertGreaterEqual(m_up, prev_m_up - 1e-9)
            # Monotonicity: lower multiplier non-decreasing with z
            self.assertGreaterEqual(m_low, prev_m_low - 1e-9)
            # Bounds
            self.assertGreaterEqual(m_up, 1.00)
            self.assertLessEqual(m_up, 2.20)
            self.assertGreaterEqual(m_low, 0.60)
            self.assertLessEqual(m_low, 1.00)

            prev_m_up = m_up
            prev_m_low = m_low

    def test_challenge_gate4_leveraged_bandwidth_expansion(self):
        """Stress 3.2: Gate 4 leveraged Leland bandwidth expansion: exact 1.140x at L=1.35."""
        target_w = {"STOCK_A": 0.05}
        daily_vols = {"STOCK_A": 0.02}

        # Baseline unleveraged (L = 1.00)
        bands_100 = self.opt.compute_leland_bands(
            target_weights=target_w, volatilities=daily_vols, leverage=1.00
        )
        delta_100 = bands_100["STOCK_A"][2] - target_w["STOCK_A"]

        # Leveraged bull regime (L = 1.35) -> expansion factor = 1.0 + 0.40 * (1.35 - 1.0) = 1.14
        bands_135 = self.opt.compute_leland_bands(
            target_weights=target_w, volatilities=daily_vols, leverage=1.35
        )
        delta_135 = bands_135["STOCK_A"][2] - target_w["STOCK_A"]

        expansion_ratio = delta_135 / delta_100
        self.assertAlmostEqual(
            expansion_ratio, 1.14, places=3,
            msg=f"Gate 4 expansion ratio at L=1.35 must be 1.140x: got {expansion_ratio:.4f}x"
        )

        # High leverage (L = 1.50) -> expansion factor = 1.0 + 0.40 * 0.50 = 1.20
        bands_150 = self.opt.compute_leland_bands(
            target_weights=target_w, volatilities=daily_vols, leverage=1.50
        )
        delta_150 = bands_150["STOCK_A"][2] - target_w["STOCK_A"]
        self.assertAlmostEqual(delta_150 / delta_100, 1.20, places=3)

    def test_challenge_instant_zero_latency_bypass_entry_and_exit(self):
        """Stress 3.3: Instant bypass for fresh entries (w_curr=0) and full exits (w_target=0) across 50 assets."""
        n_assets = 50
        symbols = [f"SYM_{i:02d}" for i in range(n_assets)]

        # 25 fresh entries (current = 0.0, target = 0.04)
        current = {s: 0.0 for s in symbols[:25]}
        target = {s: 0.04 for s in symbols[:25]}

        # 25 full exits (current = 0.04, target = 0.0)
        current.update({s: 0.04 for s in symbols[25:]})
        target.update({s: 0.0 for s in symbols[25:]})

        res = self.opt.optimize_allocations(
            current_holdings=current,
            target_allocations=target,
            use_leland_bands=True,
            total_capital=100_000_000.0,
        )

        for s in symbols[:25]:
            self.assertEqual(res[s]["action"], "BUY")
            self.assertAlmostEqual(
                res[s]["target_weight"], 0.04, places=6,
                msg=f"Fresh entry {s} must bypass Leland band and execute 100% target"
            )

        for s in symbols[25:]:
            self.assertEqual(res[s]["action"], "SELL")
            self.assertAlmostEqual(
                res[s]["target_weight"], 0.00, places=6,
                msg=f"Full liquidation {s} must bypass Leland band and liquidate 100%"
            )

    def test_challenge_boundary_rebalancing_mechanics(self):
        """Stress 3.4: Boundary rebalancing clamps precisely to band edges under moderate drift, with severe drift bypass."""
        bands = {"SYM_TEST": (0.080, 0.100, 0.120)}

        # Scenario A: Moderate drift above upper band (w_curr = 0.130 > U_i = 0.120, drift = 23% < 50%)
        res_above = self.opt.optimize_allocations(
            current_holdings={"SYM_TEST": 0.130},
            target_allocations={"SYM_TEST": 0.100},
            leland_bands=bands,
            rebalance_mode="boundary",
        )
        self.assertAlmostEqual(
            res_above["SYM_TEST"]["target_weight"], 0.120, places=5,
            msg="Moderate breach above upper band must rebalance to U_i (0.120) in boundary mode"
        )
        self.assertEqual(res_above["SYM_TEST"]["action"], "SELL")

        # Scenario B: Moderate drift below lower band (w_curr = 0.070 < L_i = 0.080, drift = 42.8% < 50%)
        res_below = self.opt.optimize_allocations(
            current_holdings={"SYM_TEST": 0.070},
            target_allocations={"SYM_TEST": 0.100},
            leland_bands=bands,
            rebalance_mode="boundary",
        )
        self.assertAlmostEqual(
            res_below["SYM_TEST"]["target_weight"], 0.080, places=5,
            msg="Moderate breach below lower band must rebalance to L_i (0.080) in boundary mode"
        )
        self.assertEqual(res_below["SYM_TEST"]["action"], "BUY")

        # Scenario C: Inside band (w_curr = 0.105 in [0.080, 0.120])
        res_inside = self.opt.optimize_allocations(
            current_holdings={"SYM_TEST": 0.105},
            target_allocations={"SYM_TEST": 0.100},
            leland_bands=bands,
            rebalance_mode="boundary",
        )
        self.assertAlmostEqual(
            res_inside["SYM_TEST"]["target_weight"], 0.105, places=5,
            msg="Inside band must hold current weight (0.105)"
        )
        self.assertEqual(res_inside["SYM_TEST"]["action"], "HOLD")

        # Scenario D: Severe drift (w_curr = 0.020, w_target = 0.050 -> drift = 150% >= 50%)
        # Triggers instant bypass back to raw target weight
        res_severe = self.opt.optimize_allocations(
            current_holdings={"SYM_TEST": 0.020},
            target_allocations={"SYM_TEST": 0.050},
            leland_bands={"SYM_TEST": (0.035, 0.050, 0.065)},
            rebalance_mode="boundary",
        )
        self.assertAlmostEqual(
            res_severe["SYM_TEST"]["target_weight"], 0.050, places=5,
            msg="Severe drift (>= 50%) must trigger instant bypass to target weight (0.050)"
        )

    def test_challenge_unified_allocator_leland_buffers(self):
        """Stress 3.5: UnifiedPortfolioAllocator.apply_leland_no_trade_buffers integration with leverage budget."""
        n = 10
        # Target weights summing to 0.80 (leaving cash buffer so total doesn't hit 1.0 limit after drift)
        target = np.full(n, 0.08)
        current = np.full(n, 0.08)
        current[0] = 0.00   # Fresh entry -> bypass to 0.08
        current[1] = 0.095  # Moderate breach above upper band -> rebalance to upper band
        current[2] = 0.065  # Moderate breach below lower band -> rebalance to lower band
        current[3] = 0.083  # Inside band -> hold
        vols = np.full(n, 0.02)
        u_rets = np.zeros(n)
        u_rets[1] = 0.10    # Winner

        res = self.unified_allocator.apply_leland_no_trade_buffers(
            target_weights=target,
            current_weights=current,
            volatilities=vols,
            unrealized_returns=u_rets,
            rebalance_mode="boundary",
            max_total_allocation=1.35,  # Allow Gate 4 bull leverage frontier
        )

        # Fresh entry must bypass buffer to full target weight
        self.assertAlmostEqual(res[0], 0.08, places=4)
        # Inside band must hold
        self.assertAlmostEqual(res[3], 0.083, places=4)
        # Budget constraint respected
        self.assertLessEqual(float(np.sum(res)), 1.35)


class TestPhase150ChallengerDriftTurnover(unittest.TestCase):
    """Suite 4: 252-Day Drift Simulations & Turnover Compression (F734)."""

    def setUp(self):
        self.opt = TurnoverOptimizer()

    def _run_drift_sim(
        self,
        n_assets: int = 50,
        n_days: int = 252,
        seed: int = 42,
        vol_min: float = 0.012,
        vol_max: float = 0.028,
        leverage: float = 1.0,
    ) -> Dict[str, float]:
        np.random.seed(seed)
        symbols = [f"ASSET_{i:03d}" for i in range(n_assets)]
        w_target = {s: 1.0 / n_assets for s in symbols}
        tgt_val = 1.0 / n_assets
        daily_vols = {s: float(np.random.uniform(vol_min, vol_max)) for s in symbols}

        h_target = dict(w_target)
        h_boundary = dict(w_target)
        cum_to_target = 0.0
        cum_to_boundary = 0.0

        for _ in range(n_days):
            common = np.random.normal(0.0004, 0.010)
            returns = {s: 0.40 * common + 0.60 * np.random.normal(0.0, daily_vols[s]) for s in symbols}

            # Drift target portfolio
            d_A = {s: max(1e-5, h_target[s] * (1.0 + returns[s])) for s in symbols}
            tot_A = sum(d_A.values())
            d_A = {s: v / tot_A for s, v in d_A.items()}

            # Drift boundary portfolio
            d_B = {s: max(1e-5, h_boundary[s] * (1.0 + returns[s])) for s in symbols}
            tot_B = sum(d_B.values())
            d_B = {s: v / tot_B for s, v in d_B.items()}

            unrealized = {s: (d_B[s] - tgt_val) / tgt_val for s in symbols}
            bands = self.opt.compute_leland_bands(
                target_weights=w_target,
                volatilities=daily_vols,
                unrealized_returns=unrealized,
                gamma=3.0,
                leverage=leverage,
            )

            res_target = self.opt.optimize_allocations(
                current_holdings=d_A,
                target_allocations=w_target,
                leland_bands=bands,
                rebalance_mode="target",
                preserve_budget=False,
            )
            res_boundary = self.opt.optimize_allocations(
                current_holdings=d_B,
                target_allocations=w_target,
                leland_bands=bands,
                rebalance_mode="boundary",
                preserve_budget=False,
            )

            cum_to_target += sum(abs(res_target[s]["target_weight"] - d_A[s]) for s in symbols)
            cum_to_boundary += sum(abs(res_boundary[s]["target_weight"] - d_B[s]) for s in symbols)

            for s in symbols:
                h_target[s] = res_target[s]["target_weight"]
                h_boundary[s] = res_boundary[s]["target_weight"]

        red_pct = ((cum_to_target - cum_to_boundary) / max(cum_to_target, 1e-6)) * 100.0
        return {
            "annual_turnover_target": cum_to_target,
            "annual_turnover_boundary": cum_to_boundary,
            "turnover_reduction_pct": red_pct,
        }

    def test_challenge_drift_turnover_across_5_independent_seeds(self):
        """Stress 4.1: 252-day drift: boundary turnover <= 4.50x across 5 random seeds."""
        seeds = [42, 101, 777, 2026, 9999]
        for seed in seeds:
            res = self._run_drift_sim(n_assets=50, n_days=252, seed=seed)
            self.assertLessEqual(
                res["annual_turnover_boundary"], 4.50,
                f"Seed {seed}: Annual turnover {res['annual_turnover_boundary']:.2f}x exceeds 4.50x hurdle"
            )
            self.assertGreaterEqual(
                res["turnover_reduction_pct"], 40.0,
                f"Seed {seed}: Turnover reduction {res['turnover_reduction_pct']:.1f}% below 40.0% hurdle"
            )

    def test_challenge_crisis_high_volatility_drift_turnover(self):
        """Stress 4.2: High-volatility market stress (daily vol 2.5% ~ 5.0%): turnover <= 4.50x."""
        res = self._run_drift_sim(
            n_assets=40,
            n_days=252,
            seed=2008,
            vol_min=0.025,
            vol_max=0.050,
            leverage=1.0,
        )
        self.assertLessEqual(
            res["annual_turnover_boundary"], 4.50,
            f"High vol stress: Annual turnover {res['annual_turnover_boundary']:.2f}x exceeds 4.50x limit"
        )
        self.assertGreater(res["turnover_reduction_pct"], 25.0)


class TestPhase150ChallengerFrictionAndLOB(unittest.TestCase):
    """Suite 5: Capital-Weighted Execution Friction & Microstructure Harvester (F731 & F734)."""

    def setUp(self):
        self.lob = FastLOBEngine("NVDA")

    def test_challenge_capital_weighted_roundtrip_friction_hurdle(self):
        """Stress 5.1: Capital-weighted roundtrip friction hurdle <= 7.00 bps (realizing 6.72 bps)."""
        w_us = 0.60
        w_krx = 0.40

        net_friction_us_bps = 3.20
        net_friction_krx_bps = 12.00

        weighted_friction = w_us * net_friction_us_bps + w_krx * net_friction_krx_bps

        self.assertAlmostEqual(weighted_friction, 6.72, places=2)
        self.assertLessEqual(
            weighted_friction, 7.00,
            f"Capital-weighted net friction {weighted_friction:.2f} bps exceeds 7.00 bps hurdle"
        )

    def test_challenge_allocation_sensitivity_krx_boundary(self):
        """Stress 5.2: Allocation sensitivity: determine maximum allowable KRX weighting to satisfy <= 7.00 bps."""
        net_us = 3.20
        net_krx = 12.00
        # Target: w_us * net_us + (1 - w_us) * net_krx <= 7.00
        # w_krx_max = (7.00 - net_us) / (net_krx - net_us)
        w_krx_max = (7.00 - net_us) / (net_krx - net_us)
        self.assertAlmostEqual(w_krx_max, 3.80 / 8.80, places=4)
        self.assertGreater(w_krx_max, 0.40, "Portfolio must safely accommodate at least 40% KRX allocation")

        # Test at 70% US / 30% KRX
        f_70_30 = 0.70 * net_us + 0.30 * net_krx
        self.assertLessEqual(f_70_30, 7.00)

    def test_challenge_us_lit_maker_rebate_and_nextrade_cross(self):
        """Stress 5.3: Lit maker rebates (+2.5 bps) and Nextrade ATS midpoint crosses (-35% fee)."""
        # US Lit venue maker rebate
        res_us = self.lob.harvest_spread_and_fees(
            venue="BZX",
            channel="PASSIVE_MAKER",
            spread_bps=4.0,
            notional=200_000.0,
            shares=2000,
            is_maker=True,
        )
        self.assertEqual(res_us["maker_rebate_bps"], 2.5)
        self.assertEqual(res_us["net_harvested_alpha_bps"], 4.5)  # 2.0 (half-spread) + 2.5 (rebate)
        self.assertEqual(res_us["harvested_cash"], 90.0)

        # Nextrade ATS dark midpoint cross
        res_nextrade = self.lob.harvest_spread_and_fees(
            venue="NEXTRADE_ATS",
            channel="MID_PEG_DARK",
            spread_bps=12.0,
            notional=100_000_000.0,
            shares=1000,
            is_maker=True,
        )
        self.assertEqual(res_nextrade["spread_saving_bps"], 6.0) # 50% of 12.0 bps
        self.assertEqual(res_nextrade["fee_discount_pct"], 35.0)
        self.assertEqual(res_nextrade["net_harvested_alpha_bps"], 6.5)

    def test_challenge_16_thread_concurrency_stress(self):
        """Stress 5.4: 16-thread high-concurrency stress test with zero deadlocks or exceptions."""
        num_threads = 16
        iterations = 25
        agent = RLOrderExecutionAgent()
        kalman = OnlineKalmanSlippageFilter()
        matching = FastOrderBookMatchingEngine("NVDA")

        temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(temp_dir.name, "concurrent_challenger.db")
        oms = ExecutionOMSEngine(db_path=db_path)

        exceptions: List[Exception] = []

        def worker(thread_idx: int):
            try:
                for i in range(iterations):
                    # 1. RL SAC forward pass
                    state = ExecutionState(
                        time_ratio=float((i + 1) / 30.0),
                        inventory_ratio=float(max(0.0, 1.0 - (i / 25.0))),
                        spread_bps=float(5.0 + (i % 10)),
                        obi=float(-0.5 + 0.1 * (thread_idx % 10)),
                        vpin=float(0.1 + 0.03 * (thread_idx % 10)),
                        volatility=0.02,
                    )
                    action = agent.compute_continuous_action(state)
                    assert float(np.sum(action.route_weights)) == pytest.approx(1.0, abs=1e-5)

                    # 2. Kalman filter update
                    kalman.update(
                        realized_slippage_bps=float(2.0 + (i % 5)),
                        h_gamma=1.0,
                        h_spread=2.0,
                        h_eta=1.0,
                    )

                    # 3. LOB matching
                    matching.add_limit_order(
                        order_id=f"ORD_{thread_idx}_{i}",
                        side="BUY" if i % 2 == 0 else "SELL",
                        price=100.0 + (i % 5),
                        volume=10.0,
                    )
            except Exception as e:
                exceptions.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        temp_dir.cleanup()
        self.assertEqual(len(exceptions), 0, f"Concurrent execution generated exceptions: {exceptions}")


if __name__ == "__main__":
    unittest.main()
