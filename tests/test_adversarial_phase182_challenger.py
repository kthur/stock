"""
tests/test_adversarial_phase182_challenger.py
=============================================
Empirical Adversarial Stress-Test Suite for Release R180 Milestone M3 (Phase 182).
Challenger Agent: challenger_m3_2

Target Features:
- F892: Spectral EVT-CVaR Tail-Risk Budgeting with Clamped GPD
- F893: Asymmetric Leland Dynamic Buffer Bands with Zero-Bypass
- F894: UnifiedPortfolioAllocator R180 8-Model Master Blend & Gatheral 3/2 Penalty

Adversarial Verification & Bug Reproduction:
1. Student-t (df=2.1, df=1.05 Cauchy-like), zero-volatility returns, uniform returns.
2. Parameter clamping: xi in [0.05, 0.45], scale sigma > 0, risk spectrum phi(p) decreasing and normalized.
3. [CRITICAL BUG 1]: compute_spectral_evt_cvar_risk_budget fails to propagate xi_bounds=(0.05, 0.45) to compute_evt_var_cvar (omits min_xi/max_xi on lines 297 & 352), returning xi_clamped = 0.01.
4. [CRITICAL BUG 2]: Leland buffer bands hardcode `t_w > 0.005` on line 196, causing any fresh entry with target weight <= 0.5% (e.g. w_target = 0.002) to be blocked and dropped to HOLD (weight 0.0).
5. [BUG 3]: NaN in alpha_vector corrupts all portfolio weights in allocate_portfolio_phase182 to NaN.
6. [BUG 4]: Empty portfolio input ({}) returns AllocationResult with empty metadata, violating the synthetic_rows == 0 system invariant.
7. Master 8-model blend: weights sum to 1.0000 across all 9 regimes.
8. Gatheral 3/2-power penalty monotonicity and strict convexity.
9. System invariants: synthetic_rows == 0 strictly int, Net Equity <= Gross Equity.
"""

from __future__ import annotations

import math
import os
import sys
import unittest
from typing import Dict, Any, List

import numpy as np
import pandas as pd
import pytest
import scipy.integrate as integrate

# Ensure repo root is on sys.path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# F892 Imports
from src.risk.evt_tail_risk import (
    fit_generalized_pareto,
    compute_evt_var_cvar,
    compute_spectral_expected_shortfall,
    compute_spectral_evt_cvar_risk_budget,
    SpectralEVTCVaRBudgetingEngine,
)
from src.risk.spectral_evt_cvar_allocator import (
    compute_evt_cvar_spectral_budget as standalone_evt_budget,
)
from src.risk.portfolio_allocator import PortfolioAllocator

# F893 Imports
from src.execution.leland_buffer_bands import (
    compute_asymmetric_leland_bands,
    compute_asymmetric_leeland_bands,
    is_zero_bypass_eligible,
    filter_portfolio_rebalance,
    AsymmetricLelandTurnoverOptimizer,
)
from src.risk.asymmetric_leeland_bands import (
    compute_asymmetric_leeland_bands as risk_compute_bands,
    is_zero_bypass_eligible as risk_is_zero_bypass_eligible,
)
from src.execution.turnover_optimizer import (
    TurnoverOptimizer,
    is_zero_bypass_eligible as turnover_is_zero_bypass_eligible,
)

# F894 Imports
from src.risk.unified_portfolio_allocator import (
    UnifiedPortfolioAllocator,
    allocate_portfolio_phase182,
    AllocationResult,
)


class TestAdversarialPhase182Challenger(unittest.TestCase):
    """Adversarial challenger test cases executing empirical stress harnesses."""

    # =========================================================================
    # AREA 1: Feature F892 (Spectral EVT-CVaR Tail Risk with Clamped GPD)
    # =========================================================================

    def test_adv01_student_t_df21_tail_clamping(self):
        """ADV01: Student-t(df=2.1) heavy tail must have xi strictly clamped to [0.05, 0.45]."""
        np.random.seed(20261108)
        # Theoretical tail index for Student-t(df) is 1/df ~= 0.476, which exceeds 0.45
        t_returns = np.random.standard_t(df=2.1, size=(1000, 4)) * 0.02
        losses = -t_returns[:, 0]

        xi, sigma, u = fit_generalized_pareto(losses, min_xi=0.05, max_xi=0.45)
        self.assertGreaterEqual(xi, 0.05, f"Tail index {xi} below min 0.05")
        self.assertLessEqual(xi, 0.45, f"Tail index {xi} exceeded max 0.45")
        self.assertGreater(sigma, 0.0, f"Scale parameter {sigma} must be strictly positive")
        self.assertTrue(math.isfinite(xi))
        self.assertTrue(math.isfinite(sigma))
        self.assertTrue(math.isfinite(u))

        # Test multi-asset risk budget under df=2.1
        budget = compute_spectral_evt_cvar_risk_budget(t_returns, xi_bounds=(0.05, 0.45))
        self.assertGreaterEqual(budget["xi_clamped"], 0.05)
        self.assertLessEqual(budget["xi_clamped"], 0.45)
        self.assertGreater(budget["beta_scale"], 0.0)
        self.assertEqual(budget["synthetic_rows"], 0)
        self.assertIs(type(budget["synthetic_rows"]), int)

    def test_adv02_cauchy_like_extreme_tail_clamping(self):
        """ADV02: Cauchy-like infinite-variance returns (df=1.05) must not cause NaN/Inf and xi <= 0.45."""
        np.random.seed(42)
        # df=1.05 -> theoretical xi = 1/1.05 = 0.952!
        extreme_losses = np.abs(np.random.standard_t(df=1.05, size=2000)) * 0.05
        extreme_losses = np.clip(extreme_losses, 0.0, 100.0)  # avoid machine overflow

        xi, sigma, u = fit_generalized_pareto(extreme_losses, min_xi=0.05, max_xi=0.45)
        self.assertAlmostEqual(xi, 0.45, delta=1e-5, msg="Extreme tail must clamp at upper boundary 0.45")
        self.assertGreater(sigma, 0.0)
        self.assertTrue(math.isfinite(xi))
        self.assertTrue(math.isfinite(sigma))

        # Check EVT-VaR and EVT-CVaR
        res = compute_evt_var_cvar(extreme_losses, alpha=0.99, min_xi=0.05, max_xi=0.45)
        self.assertFalse(math.isnan(res["evt_var"]))
        self.assertFalse(math.isnan(res["evt_cvar"]))
        self.assertGreaterEqual(res["evt_cvar"], res["evt_var"])
        self.assertEqual(res["xi_clamped"], 0.45)

    def test_adv03_zero_volatility_returns(self):
        """ADV03: Degenerate zero-volatility returns (constant 0.0) must not crash with DivByZero."""
        zero_returns = np.zeros((100, 3), dtype=np.float64)

        budget = compute_spectral_evt_cvar_risk_budget(zero_returns, xi_bounds=(0.05, 0.45))
        self.assertEqual(len(budget["risk_budget_weights"]), 3)
        self.assertAlmostEqual(float(np.sum(budget["risk_budget_weights"])), 1.0, places=4)
        for w in budget["risk_budget_weights"]:
            self.assertFalse(math.isnan(w))
            self.assertFalse(math.isinf(w))
            self.assertGreaterEqual(w, 0.0)
        self.assertGreaterEqual(budget["xi_clamped"], 0.05)
        self.assertLessEqual(budget["xi_clamped"], 0.45)
        self.assertGreater(budget["beta_scale"], 0.0)
        self.assertEqual(budget["synthetic_rows"], 0)

    def test_adv04_uniform_light_tail_returns(self):
        """ADV04: Uniform returns have finite support (unconstrained xi < 0), must clamp to min_xi=0.05."""
        np.random.seed(123)
        unif_returns = np.random.uniform(-0.04, 0.04, size=1500)
        losses = -unif_returns

        xi, sigma, u = fit_generalized_pareto(losses, min_xi=0.05, max_xi=0.45)
        self.assertGreaterEqual(xi, 0.05, "Uniform light tail must be clamped to min_xi=0.05")
        self.assertLessEqual(xi, 0.45)
        self.assertGreater(sigma, 0.0)

    def test_adv05_risk_spectrum_phi_decreasing_and_normalized(self):
        """ADV05: Risk spectrum weights phi(p) must integrate to 1.0 and decrease with confidence level."""
        gamma = 5.0
        # 1. Strictly normalized: integral of phi(p) over [0, 1] is exactly 1.0
        quad_int, _ = integrate.quad(
            lambda a: gamma * math.exp(gamma * (1.0 - a)) / (math.exp(gamma) - 1.0),
            0.0, 1.0
        )
        self.assertAlmostEqual(quad_int, 1.0, places=6, msg="Integral of phi(alpha) over [0, 1] must equal 1.0")

        # 2. Strictly decreasing with respect to confidence level alpha:
        alphas = np.linspace(0.01, 0.99, 100)
        phi_vals = [float(gamma * math.exp(gamma * (1.0 - a)) / (math.exp(gamma) - 1.0)) for a in alphas]
        for i in range(len(phi_vals) - 1):
            self.assertGreater(
                phi_vals[i], phi_vals[i + 1],
                f"phi(alpha) not strictly decreasing: {phi_vals[i]} <= {phi_vals[i+1]} at alpha={alphas[i]}"
            )

        # 3. Test in PortfolioAllocator method directly
        alloc = PortfolioAllocator()
        res_90 = alloc.compute_evt_cvar_spectral_budget(np.random.randn(200) * 0.02, alpha=0.90, gamma=gamma)
        res_99 = alloc.compute_evt_cvar_spectral_budget(np.random.randn(200) * 0.02, alpha=0.99, gamma=gamma)
        self.assertGreater(res_90["phi_spectral_weight"], res_99["phi_spectral_weight"])

    def test_adv06_reproduce_f892_xi_clamping_defect(self):
        """ADV06 (EMPIRICAL DEFECT PROOF): compute_spectral_evt_cvar_risk_budget fails to clamp xi to 0.05.

        ROOT CAUSE:
        In src/risk/evt_tail_risk.py:
        Line 352: final_evt = compute_evt_var_cvar(port_losses, alpha=alpha, tail_quantile=tail_quantile)
        Line 297: evt_metrics = compute_evt_var_cvar(losses, alpha=alpha, tail_quantile=tail_quantile)
        Both calls omit min_xi/max_xi, defaulting compute_evt_var_cvar to min_xi=0.01 from Phase 178.
        Therefore, when returns are light-tailed (e.g. uniform or Gaussian), xi_clamped returns 0.01,
        directly violating the Feature F892 contract xi in [0.05, 0.45].
        """
        np.random.seed(123)
        R_uniform = np.random.uniform(-0.02, 0.02, size=(500, 3))
        res = standalone_evt_budget(R_uniform, alpha=0.95, gamma=5.0, xi_bounds=(0.05, 0.45))

        # This check exposes the defect: xi_clamped is 0.01 instead of >= 0.05
        # We record the empirical value:
        observed_xi = res["xi_clamped"]
        # Expected: observed_xi >= 0.05 per F892 spec
        # Actual: observed_xi == 0.01
        self.assertGreaterEqual(
            observed_xi, 0.05,
            f"F892 CLAMPING DEFECT: xi_clamped = {observed_xi} < 0.05 (defaulted to Phase 178 min_xi=0.01)!"
        )

    # =========================================================================
    # AREA 2: Feature F893 (Asymmetric Leland Buffer Bands with Zero-Bypass)
    # =========================================================================

    def test_adv07_fresh_entry_zero_bypass_never_blocked(self):
        """ADV07: Fresh entry (w_curr = 0.0 -> w_target = 0.05) must NEVER be blocked by the buffer band."""
        curr = {"AAPL": 0.0}
        tgt = {"AAPL": 0.05}

        # Check eligibility function
        self.assertTrue(is_zero_bypass_eligible(0.0, 0.05))
        self.assertTrue(risk_is_zero_bypass_eligible(0.0, 0.05))
        self.assertTrue(turnover_is_zero_bypass_eligible(0.0, 0.05))

        # Check filter_portfolio_rebalance
        out = filter_portfolio_rebalance(curr, tgt)
        self.assertEqual(out.actions["AAPL"], "BYPASS_ENTRY")
        self.assertAlmostEqual(out.executable_weights["AAPL"], 0.05, places=5)
        self.assertEqual(out.filtered_turnover, out.raw_turnover)

    def test_adv08_complete_exit_zero_bypass_never_blocked(self):
        """ADV08: Complete exit (w_curr = 0.05 -> w_target = 0.0) must NEVER be blocked by the buffer band."""
        curr = {"AAPL": 0.05}
        tgt = {"AAPL": 0.0}

        # Check eligibility function
        self.assertTrue(is_zero_bypass_eligible(0.05, 0.0))
        self.assertTrue(risk_is_zero_bypass_eligible(0.05, 0.0))
        self.assertTrue(turnover_is_zero_bypass_eligible(0.05, 0.0))

        # Check filter_portfolio_rebalance
        out = filter_portfolio_rebalance(curr, tgt)
        self.assertEqual(out.actions["AAPL"], "BYPASS_EXIT")
        self.assertAlmostEqual(out.executable_weights["AAPL"], 0.0, places=5)
        self.assertEqual(out.filtered_turnover, out.raw_turnover)

    def test_adv09_within_band_micro_shifts_suppression(self):
        """ADV09: Trades below the band threshold must be suppressed to HOLD (filtered turnover = 0)."""
        # Base bandwidth is >= 0.005 (min_bandwidth)
        # Shift of 0.001 (0.10 -> 0.101) is strictly inside the band
        curr = {"SYM_A": 0.100, "SYM_B": 0.200, "SYM_C": 0.300}
        tgt = {"SYM_A": 0.101, "SYM_B": 0.199, "SYM_C": 0.301}

        out = filter_portfolio_rebalance(curr, tgt)
        for sym in curr:
            self.assertEqual(out.actions[sym], "HOLD", f"Shift for {sym} was not suppressed to HOLD")
            self.assertEqual(out.executable_weights[sym], curr[sym])

        self.assertGreater(out.raw_turnover, 0.0)
        self.assertAlmostEqual(out.filtered_turnover, 0.0, places=6)
        self.assertAlmostEqual(out.turnover_reduction_pct, 100.0, places=1)

    def test_adv10_asymmetric_winner_expansion_loser_contraction(self):
        """ADV10: Strong positive alpha widens upper band, strong negative alpha narrows upper band."""
        curr = {"WINNER": 0.10, "LOSER": 0.10}
        tgt = {"WINNER": 0.10, "LOSER": 0.10}
        alphas = {"WINNER": 3.0, "LOSER": -3.0}
        vols = {"WINNER": 0.15, "LOSER": 0.15}

        bands = compute_asymmetric_leland_bands(curr, tgt, alphas=alphas, volatilities=vols)

        w_plus = bands["WINNER"]["half_width_plus"]
        w_minus = bands["WINNER"]["half_width_minus"]
        l_plus = bands["LOSER"]["half_width_plus"]
        l_minus = bands["LOSER"]["half_width_minus"]

        # Winner: upper band expanded, lower band contracted
        self.assertGreater(w_plus, w_minus)
        self.assertGreater(bands["WINNER"]["asymmetry_delta"], 0.0)

        # Loser: lower band expanded, upper band contracted
        self.assertLess(l_plus, l_minus)
        self.assertLess(bands["LOSER"]["asymmetry_delta"], 0.0)

    def test_adv16_reproduce_f893_small_fresh_entry_blocking_defect(self):
        """ADV16 (EMPIRICAL DEFECT PROOF): Fresh entry with w_target <= 0.005 is BLOCKED by buffer band.

        ROOT CAUSE:
        In src/execution/leland_buffer_bands.py:
        Line 196: elif c_w <= 1e-4 and t_w > 0.005:
        The fresh entry bypass condition hardcodes `t_w > 0.005`.
        If the allocator creates a fresh entry position of 0.2% (w_target = 0.002, typical for
        large-universe institutional portfolios), the buffer is NOT bypassed.
        Because w_target (0.002) <= upper_bound (0.005), the execution engine classifies it as HOLD,
        and sets executable_weights = 0.0! The new stock is NEVER entered!
        Meanwhile, is_zero_bypass_eligible(0.0, 0.002) returns True!
        """
        curr = {"MICRO_ENTRY": 0.0}
        tgt = {"MICRO_ENTRY": 0.002}  # 0.2% fresh allocation

        self.assertTrue(
            is_zero_bypass_eligible(0.0, 0.002),
            "is_zero_bypass_eligible must report True for fresh entry"
        )

        out = filter_portfolio_rebalance(curr, tgt)
        # Exposing the defect: action is HOLD and executable weight is 0.0 instead of BYPASS_ENTRY!
        self.assertEqual(
            out.actions["MICRO_ENTRY"], "BYPASS_ENTRY",
            f"F893 ZERO-BYPASS DEFECT: Fresh entry w_target=0.002 was blocked! Action={out.actions['MICRO_ENTRY']}, Executable={out.executable_weights['MICRO_ENTRY']}"
        )

    # =========================================================================
    # AREA 3: Feature F894 (UnifiedPortfolioAllocator R180 8-Model Master Blend)
    # =========================================================================

    def test_adv11_regime_model_weights_sum_to_one_across_all_9_regimes(self):
        """ADV11: Verify 8 models sum strictly to 1.0000 across all 9 regimes."""
        alloc = UnifiedPortfolioAllocator()
        required_regimes = [
            "BULL_LOW_VOL", "RELIEF_RALLY", "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL", "BEAR_HIGH_VOL",
            "PANIC_CRISIS", "CRISIS"
        ]
        required_models = [
            "black_litterman", "herc", "risk_parity", "evt_cvar",
            "hyperbolic_ot", "spectral_barycenter", "regime_leverage", "tail_kurtosis_parity"
        ]

        self.assertEqual(len(alloc.REGIME_MODEL_WEIGHTS_PHASE182), 9)
        for reg in required_regimes:
            self.assertIn(reg, alloc.REGIME_MODEL_WEIGHTS_PHASE182)
            m_dict = alloc.REGIME_MODEL_WEIGHTS_PHASE182[reg]
            self.assertEqual(len(m_dict), 8)
            for m in required_models:
                self.assertIn(m, m_dict, f"Missing model {m} in regime {reg}")
                self.assertGreaterEqual(m_dict[m], 0.0, f"Negative weight for {m} in {reg}")

            # Strict sum == 1.0000
            total_w = sum(m_dict.values())
            self.assertAlmostEqual(total_w, 1.0000, places=6, msg=f"Sum of model weights in {reg} is {total_w} != 1.0")

    def test_adv12_gatheral_market_impact_penalty_monotonicity_and_convexity(self):
        """ADV12: Gatheral 3/2 penalty must be strictly monotonically increasing and convex in trade size."""
        alloc = UnifiedPortfolioAllocator()
        # Test monotonicity across increasing trade sizes
        trade_sizes = np.linspace(0.005, 0.15, 20)
        penalties = []
        for dw in trade_sizes:
            p = alloc.compute_gatheral_market_impact_penalty(
                weights={"STK": dw},
                current_weights={"STK": 0.0},
                total_equity=10_000_000_000.0,
            )
            penalties.append(p)

        # 1. Monotonicity: p[i+1] > p[i]
        for i in range(len(penalties) - 1):
            self.assertGreater(
                penalties[i + 1], penalties[i],
                f"Monotonicity violated at index {i}: {penalties[i+1]} <= {penalties[i]}"
            )

        # 2. Strict Convexity: second differences must be positive
        for i in range(1, len(penalties) - 1):
            second_diff = penalties[i + 1] - 2 * penalties[i] + penalties[i - 1]
            self.assertGreater(
                second_diff, 0.0,
                f"Convexity violated at trade size {trade_sizes[i]}: second diff = {second_diff} <= 0"
            )

        # 3. Super-linear scaling verification: scaling dw by 2x must scale penalty by > 4x
        p_base = alloc.compute_gatheral_market_impact_penalty({"STK": 0.02}, {"STK": 0.0})
        p_double = alloc.compute_gatheral_market_impact_penalty({"STK": 0.04}, {"STK": 0.0})
        ratio = p_double / p_base
        self.assertGreater(ratio, 4.0, f"Super-linear 3/2 law expected ratio > 4.0, got {ratio:.2f}")

    def test_adv13_capital_conservation_invariant(self):
        """ADV13: Net Equity <= Gross Equity must hold strictly under all market regimes."""
        alloc = UnifiedPortfolioAllocator()
        alphas = pd.Series({"AAPL": 2.5, "NVDA": 3.0, "MSFT": -1.5, "AMZN": 0.2})
        regimes = [
            "BULL_LOW_VOL", "BULL_HIGH_VOL", "SIDEWAYS_LOW_VOL",
            "BEAR_LOW_VOL", "PANIC_CRISIS", "CRISIS"
        ]

        for reg in regimes:
            res = alloc.allocate_portfolio_phase182(alphas, regime=reg)
            self.assertLessEqual(
                res.net_leverage, res.gross_leverage + 1e-5,
                f"Capital conservation violated in regime {reg}: Net {res.net_leverage} > Gross {res.gross_leverage}"
            )
            self.assertGreaterEqual(res.net_leverage, 0.0)

    def test_adv14_synthetic_rows_zero_invariant_native_int(self):
        """ADV14: synthetic_rows == 0 must be strictly native Python int across all engines."""
        # 1. UnifiedPortfolioAllocator
        res_alloc = allocate_portfolio_phase182({"AAPL": 1.0, "MSFT": 2.0})
        self.assertEqual(res_alloc.metadata["synthetic_rows"], 0)
        self.assertIs(type(res_alloc.metadata["synthetic_rows"]), int)

        # 2. EVTTailRisk Engine
        evt_engine = SpectralEVTCVaRBudgetingEngine()
        res_evt = evt_engine.compute_evt_cvar_spectral_budget(np.random.randn(50, 2) * 0.02)
        self.assertEqual(res_evt["synthetic_rows"], 0)
        self.assertIs(type(res_evt["synthetic_rows"]), int)

        # 3. Leland Buffer Bands
        leland_out = filter_portfolio_rebalance({"AAPL": 0.10}, {"AAPL": 0.12})
        self.assertEqual(leland_out.synthetic_rows, 0)
        self.assertIs(type(leland_out.synthetic_rows), int)

    def test_adv15_extreme_market_shocks_and_empty_portfolios(self):
        """ADV15: Extreme alpha spikes and negative outliers degrade gracefully."""
        alloc = UnifiedPortfolioAllocator()
        res_extreme = alloc.allocate_portfolio_phase182(
            {"NORMAL": 1.0, "SPIKE": 1e9, "PLUNGE": -1e9},
            regime="BULL_LOW_VOL",
        )
        for sym, w in res_extreme.target_weights.items():
            self.assertFalse(math.isnan(w))
            self.assertFalse(math.isinf(w))
            self.assertGreaterEqual(w, 0.0)

    def test_adv17_reproduce_f894_nan_alpha_vector_corruption(self):
        """ADV17 (EMPIRICAL DEFECT PROOF): Single NaN in alpha_vector corrupts entire portfolio to NaN.

        ROOT CAUSE:
        In src/risk/unified_portfolio_allocator.py:
        Line 573: raw_scores = s.values.astype(np.float64)
        Lacks np.nan_to_num(raw_scores, nan=0.0).
        np.max(raw_scores) evaluates to NaN, resulting in exp_scores = NaN and target_weights = NaN!
        """
        alloc = UnifiedPortfolioAllocator()
        res = alloc.allocate_portfolio_phase182(pd.Series({"VALID": 1.5, "CORRUPT": np.nan}))
        # Check if valid stock gets corrupted to NaN:
        is_corrupted = math.isnan(res.target_weights.get("VALID", 0.0))
        self.assertFalse(
            is_corrupted,
            f"F894 NUMERICAL RESILIENCE DEFECT: NaN in alpha_vector corrupted valid stock weights to NaN! Output: {res.target_weights}"
        )

    def test_adv18_reproduce_f894_empty_portfolio_invariant_defect(self):
        """ADV18 (EMPIRICAL DEFECT PROOF): Empty portfolio input returns AllocationResult without synthetic_rows.

        ROOT CAUSE:
        In src/risk/unified_portfolio_allocator.py:
        Line 543: return AllocationResult({}, net_leverage=0.0, gross_leverage=0.0, regime=regime)
        Omits metadata={'synthetic_rows': 0, ...}, resulting in res.metadata = {},
        violating the system invariant that synthetic_rows == 0 must be present in metadata.
        """
        alloc = UnifiedPortfolioAllocator()
        res = alloc.allocate_portfolio_phase182({})
        self.assertIn(
            "synthetic_rows", res.metadata,
            f"F894 INVARIANT DEFECT: Empty portfolio result missing 'synthetic_rows' metadata! metadata={res.metadata}"
        )
        self.assertEqual(res.metadata["synthetic_rows"], 0)
        self.assertIs(type(res.metadata["synthetic_rows"]), int)


if __name__ == "__main__":
    unittest.main()
