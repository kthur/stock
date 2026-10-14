"""
tests/test_phase106_adversarial_challenger1.py — Empirical Challenger Stress Test Suite.

Phase 106 / Feature F500 / Release R122 (v113 Production Master)
Milestone 1: Dynamic Macro Factor Timing Engine Adversarial Challenge.

Challenger M1_1 Adversarial Stress Test Suite:
1. Extreme macro inputs & condition vector containment in [-1.0, 1.0]
2. Adversarial baseline weight distributions & Quality boost invariance (>= 15%)
3. Inversion boundary conditions (micro-spreads around zero)
4. Robustness against malformed inputs and crash prevention
5. 10,000-iteration Monte Carlo simplex sum and non-negativity fuzzing
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.macro_factor_timing import DynamicMacroFactorTimingEngine


ALL_37_STRATEGIES: List[str] = [
    "regression", "rim_valuation", "factor_neutralized", "valueup_catalyst",
    "accruals_quality", "mq_factor", "arm_factor", "card_factor", "latr_factor",
    "vol_target", "iv_skew", "earnings_tone_drift",
    "vcp_rule", "vcp_ml", "surge", "lead_lag", "stat_arb", "sector_rotation",
    "lstm", "sentiment", "inst_foreign_sector", "supply_chain",
    "gamma_squeeze", "short_squeeze", "insider_buying", "trend_efficiency", "event_driven",
    "cross_asset_spillover", "supply_chain_gnn", "dual_correction", "index_rebalance",
    "microstructure", "order_flow", "short_term_reversal", "darkpool",
    "range_expansion_breakout", "overnight_gap_reversal",
]

QUALITY_VALUATION_STRATEGIES: List[str] = [
    "rim_valuation", "accruals_quality", "mq_factor",
    "valueup_catalyst", "factor_neutralized", "regression",
]


class TestPhase106AdversarialChallenger1(unittest.TestCase):
    """
    Adversarial Stress Test Suite for Milestone 1.
    """

    def setUp(self) -> None:
        self.engine = DynamicMacroFactorTimingEngine()
        w = 1.0 / len(ALL_37_STRATEGIES)
        self.base_weights = {s: w for s in ALL_37_STRATEGIES}
        diff = 1.0 - sum(self.base_weights.values())
        self.base_weights[ALL_37_STRATEGIES[0]] += diff

    # -----------------------------------------------------------------------
    # Challenge 1: Condition Vector Containment & Non-Escape
    # -----------------------------------------------------------------------
    def test_adv_01_condition_vector_extreme_scalars(self) -> None:
        """Tests that condition vector stays strictly within [-1.0, 1.0] under extreme values."""
        extreme_dicts = [
            {"term_spread": 1e9, "yield_velocity": -1e9, "sox_spillover": 1e12},
            {"term_spread": -1e9, "yield_velocity": 1e9, "usdkrw_momentum": -1e12},
            {"raw_spread_10y2y": 500.0, "yield_velocity": 500.0},
            {"raw_spread_10y2y": -500.0, "yield_velocity": -500.0},
            {"sox_spillover": 0.999999999999, "wti_terms_of_trade": -0.999999999999},
        ]
        for ind in extreme_dicts:
            cond = self.engine.extract_macro_condition_vector(ind)
            for k in ("term_spread", "yield_velocity", "usdkrw_momentum", "dxy_momentum", "sox_spillover", "wti_terms_of_trade", "macro_impulse"):
                val = cond[k]
                self.assertTrue(
                    math.isfinite(val),
                    f"Metric {k} must be finite for {ind}, got {val}"
                )
                self.assertGreaterEqual(
                    val, -1.0,
                    f"Metric {k} underflowed [-1.0, 1.0]: {val} for {ind}"
                )
                self.assertLessEqual(
                    val, 1.0,
                    f"Metric {k} overflowed [-1.0, 1.0]: {val} for {ind}"
                )

    def test_adv_02_condition_vector_dataframe_nan_inf_exposure(self) -> None:
        """
        Adversarially tests DataFrame inputs containing Inf or zeros to check for NaN leakage.
        Exposes whether NaN escapes into condition vector when clean_s or clean_fx contains zeros or Infs.
        """
        # Test 2A: Inf in term_spread series
        df_inf = pd.DataFrame({"term_spread": [np.inf] * 25})
        cond_inf = self.engine.extract_macro_condition_vector(df_inf)
        yield_vel_is_finite = math.isfinite(cond_inf["yield_velocity"])
        macro_imp_is_finite = math.isfinite(cond_inf["macro_impulse"])

        # Test 2B: Zero in currency series causing 0/0 division
        df_zero_fx = pd.DataFrame({"usdkrw": [0.0, 0.0]})
        cond_fx = self.engine.extract_macro_condition_vector(df_zero_fx)
        fx_mom_is_finite = math.isfinite(cond_fx["usdkrw_momentum"])

        # Record findings
        if not yield_vel_is_finite or not macro_imp_is_finite or not fx_mom_is_finite:
            # We assert this failure so it is formally captured in pytest report
            self.fail(
                f"BUG DISCOVERED: Condition vector leaked NaN! "
                f"term_spread=inf -> yield_velocity={cond_inf['yield_velocity']}, macro_impulse={cond_inf['macro_impulse']}; "
                f"usdkrw=[0,0] -> usdkrw_momentum={cond_fx['usdkrw_momentum']}"
            )

    # -----------------------------------------------------------------------
    # Challenge 2: Crash Vulnerabilities & Malformed Inputs
    # -----------------------------------------------------------------------
    def test_adv_03_crash_on_string_or_bad_type_in_direct_keys(self) -> None:
        """
        Tests whether extract_macro_condition_vector crashes on malformed direct dictionary inputs.
        """
        malformed_inputs = [
            {"term_spread": "invalid_string"},
            {"yield_velocity": "corrupt_data"},
            {"term_spread": [1, 2, 3]},
            {"sox_spillover": {"nested": "obj"}},
        ]
        crashes = []
        for bad_inp in malformed_inputs:
            try:
                self.engine.extract_macro_condition_vector(bad_inp)
            except Exception as e:
                crashes.append((bad_inp, type(e).__name__, str(e)))

        if crashes:
            self.fail(
                f"BUG DISCOVERED: Unhandled crash on malformed direct dictionary inputs: {crashes}"
            )

    # -----------------------------------------------------------------------
    # Challenge 3: Inversion Quality Boost Invariant (>= 15%) & Saturation
    # -----------------------------------------------------------------------
    def test_adv_04_inversion_quality_boost_under_standard_and_low_base(self) -> None:
        """
        Verifies that Quality/Valuation factors increase by >= 15% under inverted yield curve
        for standard and low baseline weight distributions.
        """
        inversion_indicators = [
            {"raw_spread_10y2y": -0.05, "term_spread": -0.10},
            {"raw_spread_10y2y": -0.50, "term_spread": -0.76},
            {"raw_spread_10y2y": -2.00, "term_spread": -0.99},
            {"raw_spread_10y2y": -0.0001, "term_spread": -0.0002},
        ]
        # Baseline distributions
        test_baselines = [
            ("Equal 37", self.base_weights),
            ("Low Quality (5%)", {
                **{q: 0.05 / 6.0 for q in QUALITY_VALUATION_STRATEGIES},
                **{s: 0.95 / 31.0 for s in ALL_37_STRATEGIES if s not in QUALITY_VALUATION_STRATEGIES},
            }),
            ("Medium Quality (30%)", {
                **{q: 0.30 / 6.0 for q in QUALITY_VALUATION_STRATEGIES},
                **{s: 0.70 / 31.0 for s in ALL_37_STRATEGIES if s not in QUALITY_VALUATION_STRATEGIES},
            }),
            ("High Quality (70%)", {
                **{q: 0.70 / 6.0 for q in QUALITY_VALUATION_STRATEGIES},
                **{s: 0.30 / 31.0 for s in ALL_37_STRATEGIES if s not in QUALITY_VALUATION_STRATEGIES},
            }),
        ]

        for base_name, base_w in test_baselines:
            w_q_in = sum(base_w[q] for q in QUALITY_VALUATION_STRATEGIES)
            for ind in inversion_indicators:
                mod_w = self.engine.modulate_strategy_weights(base_w, ind)
                w_q_out = sum(mod_w[q] for q in QUALITY_VALUATION_STRATEGIES)
                ratio = w_q_out / w_q_in
                self.assertGreaterEqual(
                    ratio, 1.150000 - 1e-6,
                    f"Inversion Quality boost failed for {base_name} under {ind}: ratio={ratio:.6f} < 1.150000"
                )
                self.assertAlmostEqual(
                    sum(mod_w.values()), 1.0, places=6,
                    msg=f"Simplex sum violated for {base_name} under {ind}: {sum(mod_w.values())}"
                )

    def test_adv_05_inversion_quality_boost_saturation_boundary(self) -> None:
        """
        Evaluates the mathematical saturation boundary when baseline Quality is >= 85%.
        When W_Q_base > 1.0 / 1.15 ≈ 0.8696, Quality * 1.15 > 1.0, which is mathematically
        incompatible with simplex normalization and non-negativity.
        Verifies that the engine gracefully handles saturation without crashing or violating simplex sum.
        """
        # Baseline with 90% Quality
        base_90 = {
            **{q: 0.90 / 6.0 for q in QUALITY_VALUATION_STRATEGIES},
            **{s: 0.10 / 31.0 for s in ALL_37_STRATEGIES if s not in QUALITY_VALUATION_STRATEGIES},
        }
        ind = {"raw_spread_10y2y": -0.50}
        mod_w = self.engine.modulate_strategy_weights(base_90, ind)
        total_sum = sum(mod_w.values())
        self.assertAlmostEqual(total_sum, 1.0, places=6)
        for k, v in mod_w.items():
            self.assertGreaterEqual(v, 0.0, f"Weight {k} is negative: {v}")
            self.assertTrue(math.isfinite(v), f"Weight {k} is not finite: {v}")

    # -----------------------------------------------------------------------
    # Challenge 4: Inversion Boundaries Around Zero
    # -----------------------------------------------------------------------
    def test_adv_06_inversion_boundaries_around_zero(self) -> None:
        """
        Tests microscopic spread values around zero (-1e-12, -1e-9, 0.0, +1e-9, +1e-12).
        Verifies exact transition between inversion and neutral/expansion.
        """
        micro_cases = [
            (-1e-12, True),
            (-1e-9, True),
            (-1e-6, True),
            (0.0, False),
            (1e-6, False),
            (1e-9, False),
            (1e-12, False),
        ]
        w_q_base = sum(self.base_weights[q] for q in QUALITY_VALUATION_STRATEGIES)

        for spread_val, expect_inverted in micro_cases:
            ind = {"raw_spread_10y2y": spread_val}
            cond = self.engine.extract_macro_condition_vector(ind)
            self.assertEqual(
                cond["is_inverted"], expect_inverted,
                f"Spread {spread_val} expected is_inverted={expect_inverted}, got {cond['is_inverted']}"
            )
            mod_w = self.engine.modulate_strategy_weights(self.base_weights, ind)
            w_q_mod = sum(mod_w[q] for q in QUALITY_VALUATION_STRATEGIES)
            if expect_inverted:
                self.assertGreaterEqual(
                    w_q_mod / w_q_base, 1.150000 - 1e-6,
                    f"Micro-inversion at spread {spread_val} failed >= 15% Quality boost"
                )
            self.assertAlmostEqual(sum(mod_w.values()), 1.0, places=6)

    # -----------------------------------------------------------------------
    # Challenge 5: 10,000-Iteration Monte Carlo Simplex Fuzzer
    # -----------------------------------------------------------------------
    def test_adv_07_monte_carlo_10000_fuzzing(self) -> None:
        """
        Runs 10,000 randomized Monte Carlo stress iterations across:
        - Random Dirichlet base weights (including highly sparse / skewed)
        - Extreme and random macro inputs (spreads, velocities, momentums)
        - Inverted and steepening regimes
        Verifies:
        1. Simplex sum is strictly 1.000000 (tolerance 1e-6)
        2. Non-negative weights (all w >= 0.0)
        3. Zero NaN and zero Inf
        4. Inversion boost >= 15% whenever W_Q_base in [0.01, 0.80]
        """
        rng = np.random.RandomState(106)
        num_iterations = 10000

        for i in range(num_iterations):
            # Generate random baseline distribution
            alpha = rng.uniform(0.1, 5.0)
            raw_w = rng.dirichlet(np.full(len(ALL_37_STRATEGIES), alpha))
            base_w = {ALL_37_STRATEGIES[j]: float(raw_w[j]) for j in range(len(ALL_37_STRATEGIES))}

            # Generate random macro environment
            raw_spread = float(rng.uniform(-2.5, 3.5))
            macro_ind = {
                "raw_spread_10y2y": raw_spread,
                "term_spread": float(np.tanh(raw_spread * 2.0)),
                "yield_velocity": float(rng.uniform(-1.0, 1.0)),
                "usdkrw_momentum": float(rng.uniform(-1.0, 1.0)),
                "dxy_momentum": float(rng.uniform(-1.0, 1.0)),
                "sox_spillover": float(rng.uniform(-1.0, 1.0)),
                "wti_terms_of_trade": float(rng.uniform(-1.0, 1.0)),
            }

            mod_w = self.engine.modulate_strategy_weights(base_w, macro_ind)

            # Invariant 1: Simplex sum == 1.0
            tot_sum = sum(mod_w.values())
            self.assertAlmostEqual(
                tot_sum, 1.0, places=6,
                msg=f"Iteration {i}: Simplex sum violated: {tot_sum}"
            )

            # Invariant 2 & 3: Non-negativity & finite
            for k, v in mod_w.items():
                self.assertGreaterEqual(
                    v, 0.0,
                    f"Iteration {i}: Negative weight for {k}: {v}"
                )
                self.assertTrue(
                    math.isfinite(v),
                    f"Iteration {i}: Non-finite weight for {k}: {v}"
                )

            # Invariant 4: Quality boost >= 15% when inverted and baseline Quality <= 80%
            if raw_spread < 0:
                w_q_in = sum(base_w[q] for q in QUALITY_VALUATION_STRATEGIES)
                w_q_out = sum(mod_w[q] for q in QUALITY_VALUATION_STRATEGIES)
                if 0.01 <= w_q_in <= 0.80:
                    ratio = w_q_out / w_q_in
                    self.assertGreaterEqual(
                        ratio, 1.150000 - 1e-6,
                        f"Iteration {i}: Quality boost {ratio:.6f} < 1.15 (in={w_q_in:.4f}, out={w_q_out:.4f})"
                    )


if __name__ == "__main__":
    unittest.main()
