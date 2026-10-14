"""
tests/test_phase106_macro_timing.py — Comprehensive Unit, Integration & Adversarial Test Harness.

Phase 106 / Feature F500 / Release R122 (v113 Production Master)
Milestone 1: Dynamic Macro Factor Timing Engine.

Test Categories Covered:
- Category 1: Exports, Alias Trees & Class Signatures (TC01~TC02)
- Category 2: Condition Vector Extraction & Hyperbolic Boundedness (TC03~TC05)
- Category 3: Robustness, Missing Data & Fallback Proxies (TC06~TC07)
- Category 4: International Timezone Causality & KRX 1-Day Lag (TC08)
- Category 5: Composite Macro Impulse Properties (TC09)
- Category 6: Dynamic Weight Modulation & Invariant Guarantees (TC10~TC15)
- Category 7: 37-Strategy Universe Integrity & EnsembleScoringEngine Integration (TC16~TC20)
- Category 8: Adversarial Monte Carlo Fuzzing & Numerical Boundary Continuity (TC21~TC22)
"""

from __future__ import annotations

import math
import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Path setup: Ensure repo root and trading_system are on sys.path
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.macro_factor_timing import (
    DynamicMacroFactorTimingEngine,
    MacroFactorTimingEngine,
    Phase106MacroFactorTimingEngine,
    MacroConditioningEngine,
    modulate_macro_factor_weights,
)
from src.ai.ensemble_scorer import EnsembleScoringEngine


# ---------------------------------------------------------------------------
# Test Fixtures & Constants
# ---------------------------------------------------------------------------
ALL_37_STRATEGIES: List[str] = [
    # Slow (12)
    "regression", "rim_valuation", "factor_neutralized", "valueup_catalyst",
    "accruals_quality", "mq_factor", "arm_factor", "card_factor", "latr_factor",
    "vol_target", "iv_skew", "earnings_tone_drift",
    # Medium (19)
    "vcp_rule", "vcp_ml", "surge", "lead_lag", "stat_arb", "sector_rotation",
    "lstm", "sentiment", "inst_foreign_sector", "supply_chain",
    "gamma_squeeze", "short_squeeze", "insider_buying", "trend_efficiency", "event_driven",
    "cross_asset_spillover", "supply_chain_gnn", "dual_correction", "index_rebalance",
    # Fast (6)
    "microstructure", "order_flow", "short_term_reversal", "darkpool",
    "range_expansion_breakout", "overnight_gap_reversal",
]

QUALITY_VALUATION_STRATEGIES: List[str] = [
    "rim_valuation", "accruals_quality", "mq_factor",
    "valueup_catalyst", "factor_neutralized", "regression",
]

MOMENTUM_BREAKOUT_STRATEGIES: List[str] = [
    "surge", "range_expansion_breakout", "vcp_rule",
    "vcp_ml", "trend_efficiency", "sector_rotation",
]


def make_equal_37_weights() -> Dict[str, float]:
    """Generates an equal-weighted 37-strategy dictionary strictly summing to 1.0."""
    w = 1.0 / len(ALL_37_STRATEGIES)
    d = {s: w for s in ALL_37_STRATEGIES}
    remainder = 1.0 - sum(d.values())
    d[ALL_37_STRATEGIES[0]] += remainder
    return d


def make_random_simplex_weights(n: int = 37, seed: int = 42) -> Dict[str, float]:
    """Generates random Dirichlet-distributed weights summing to 1.0."""
    rng = np.random.RandomState(seed)
    raw = rng.exponential(scale=1.0, size=n)
    norm = raw / raw.sum()
    strategies = ALL_37_STRATEGIES[:n]
    return {strategies[i]: float(norm[i]) for i in range(n)}


def make_synthetic_macro_df(
    days: int = 25,
    us10y_base: float = 4.20,
    us2y_base: float = 3.80,
    usdkrw_base: float = 1350.0,
    dxy_base: float = 104.5,
    sox_base: float = 4800.0,
    wti_base: float = 75.0,
    shock_on_last_day: bool = False,
    us10y_shock: float = 0.0,
    us2y_shock: float = 0.0,
    sox_shock: float = 0.0,
) -> pd.DataFrame:
    """Creates a synthetic multi-day macro DataFrame."""
    dates = pd.date_range(end="2026-10-14", periods=days, freq="B")
    df = pd.DataFrame(index=dates)
    df["us10y"] = us10y_base + np.linspace(0.0, 0.10, days)
    df["us2y"] = us2y_base + np.linspace(0.0, 0.08, days)
    df["usdkrw"] = usdkrw_base + np.linspace(0.0, 5.0, days)
    df["dxy"] = dxy_base + np.linspace(0.0, 0.5, days)
    df["sox"] = sox_base + np.linspace(0.0, 50.0, days)
    df["wti"] = wti_base + np.linspace(0.0, 1.0, days)

    if shock_on_last_day:
        df.iloc[-1, df.columns.get_loc("us10y")] += us10y_shock
        df.iloc[-1, df.columns.get_loc("us2y")] += us2y_shock
        df.iloc[-1, df.columns.get_loc("sox")] += sox_shock

    return df


# ---------------------------------------------------------------------------
# Test Suite Class
# ---------------------------------------------------------------------------
class TestPhase106MacroFactorTiming(unittest.TestCase):
    """
    Complete Verification Harness for Dynamic Macro Factor Timing Engine (F500).
    """

    def setUp(self) -> None:
        self.engine = DynamicMacroFactorTimingEngine(
            min_quality_boost_inversion=0.15,
            kappa_quality=0.35,
            kappa_momentum=0.40,
        )
        self.base_weights = make_equal_37_weights()

    # -----------------------------------------------------------------------
    # Category 1: Exports, Alias Trees & Class Signatures
    # -----------------------------------------------------------------------
    def test_01_alias_trees_and_module_exports(self) -> None:
        """Verifies all class aliases point to identical implementation and exports exist."""
        self.assertIs(MacroFactorTimingEngine, DynamicMacroFactorTimingEngine)
        self.assertIs(Phase106MacroFactorTimingEngine, DynamicMacroFactorTimingEngine)
        self.assertIs(MacroConditioningEngine, DynamicMacroFactorTimingEngine)
        self.assertTrue(callable(modulate_macro_factor_weights))

    def test_02_class_initialization_and_pillar_taxonomy(self) -> None:
        """Verifies default parameters and completeness of factor taxonomy."""
        self.assertAlmostEqual(self.engine.min_quality_boost_inversion, 0.15, places=5)
        self.assertAlmostEqual(self.engine.kappa_quality, 0.35, places=5)
        self.assertAlmostEqual(self.engine.kappa_momentum, 0.40, places=5)

        # Assert all 6 Quality/Valuation factors are defined
        for q in QUALITY_VALUATION_STRATEGIES:
            self.assertIn(q, self.engine.QUALITY_VALUATION_STRATEGIES)
        self.assertEqual(len(self.engine.QUALITY_VALUATION_STRATEGIES), 6)

        # Assert all 6 Momentum/Breakout factors are defined
        for m in MOMENTUM_BREAKOUT_STRATEGIES:
            self.assertIn(m, self.engine.MOMENTUM_BREAKOUT_STRATEGIES)
        self.assertEqual(len(self.engine.MOMENTUM_BREAKOUT_STRATEGIES), 6)

        # Assert macro weights sum to 1.0000
        w_sum = sum(self.engine.DEFAULT_MACRO_WEIGHTS.values())
        self.assertAlmostEqual(w_sum, 1.0, places=6)

    # -----------------------------------------------------------------------
    # Category 2: Condition Vector Extraction & Hyperbolic Boundedness
    # -----------------------------------------------------------------------
    def test_03_condition_vector_normal_extraction(self) -> None:
        """Verifies extraction from normal DataFrame yields bounded 6D continuous vector."""
        df = make_synthetic_macro_df(days=25, us10y_base=4.20, us2y_base=3.80)
        cond = self.engine.extract_macro_condition_vector(df, is_krx=False)

        required_keys = [
            "term_spread", "yield_velocity", "usdkrw_momentum",
            "dxy_momentum", "sox_spillover", "wti_terms_of_trade",
            "raw_spread_10y2y", "is_inverted",
        ]
        for k in required_keys:
            self.assertIn(k, cond)

        # Assert raw spread and inversion flag
        self.assertGreater(cond["raw_spread_10y2y"], 0.0)
        self.assertFalse(cond["is_inverted"])

        # Assert continuous metrics are strictly bounded in [-1.0, 1.0]
        continuous_keys = [k for k in required_keys if k not in ("raw_spread_10y2y", "is_inverted")]
        for k in continuous_keys:
            val = cond[k]
            self.assertGreaterEqual(val, -1.0, f"{k} < -1.0: {val}")
            self.assertLessEqual(val, 1.0, f"{k} > 1.0: {val}")
            self.assertTrue(math.isfinite(val))

    def test_04_condition_vector_extreme_shocks_boundedness(self) -> None:
        """Verifies strict [-1.0, 1.0] bounding under hyper-extreme shock scenarios."""
        shock_scenarios = [
            # High yields, huge dollar surge, tech crash, oil explosion
            {"us10y": 30.0, "us2y": 5.0, "usdkrw": 2500.0, "dxy": 180.0, "sox": 200.0, "wti": 300.0},
            # Deep inversion, won surge, dollar collapse, tech boom, oil collapse
            {"us10y": 1.0, "us2y": 12.0, "usdkrw": 800.0, "dxy": 60.0, "sox": 20000.0, "wti": 10.0},
            # Zero rates and flatline
            {"us10y": 0.001, "us2y": 0.001, "usdkrw": 1300.0, "dxy": 100.0, "sox": 4000.0, "wti": 70.0},
        ]
        for scenario in shock_scenarios:
            cond = self.engine.extract_macro_condition_vector(scenario, is_krx=False)
            for k, val in cond.items():
                if k not in ("raw_spread_10y2y", "is_inverted"):
                    self.assertGreaterEqual(val, -1.0, f"Violation on {k}: {val}")
                    self.assertLessEqual(val, 1.0, f"Violation on {k}: {val}")
                    self.assertTrue(math.isfinite(val))
                    self.assertFalse(math.isnan(val))

    def test_05_polymorphic_inputs_dict_and_dataframe(self) -> None:
        """Verifies that engine parses DataFrame, typed dict, and ticker-keyed dict identically."""
        # Ticker-keyed dict
        ticker_dict = {
            "^TNX": 4.15,
            "^FVX": 3.75,
            "US2Y": 3.65,
            "USDKRW=X": 1360.0,
            "DX-Y.NYB": 105.0,
            "^SOX": 4900.0,
            "CL=F": 78.0,
        }
        cond_ticker = self.engine.extract_macro_condition_vector(ticker_dict, is_krx=False)

        # Standard canonical dict
        canon_dict = {
            "us10y": 4.15,
            "us2y": 3.65,
            "usdkrw": 1360.0,
            "dxy": 105.0,
            "sox": 4900.0,
            "wti": 78.0,
        }
        cond_canon = self.engine.extract_macro_condition_vector(canon_dict, is_krx=False)

        self.assertAlmostEqual(cond_ticker["term_spread"], cond_canon["term_spread"], places=4)
        self.assertAlmostEqual(cond_ticker["raw_spread_10y2y"], cond_canon["raw_spread_10y2y"], places=4)

    # -----------------------------------------------------------------------
    # Category 3: Robustness, Missing Data & Fallbacks
    # -----------------------------------------------------------------------
    def test_06_missing_data_and_cold_start_fallback(self) -> None:
        """Verifies graceful handling of None, empty dict, empty df, and all-NaN inputs."""
        empty_inputs = [None, {}, pd.DataFrame(), pd.DataFrame({"us10y": [np.nan], "us2y": [np.nan]})]
        for inp in empty_inputs:
            cond = self.engine.extract_macro_condition_vector(inp, is_krx=False)
            self.assertIn("term_spread", cond)
            self.assertEqual(cond["term_spread"], 0.0)
            self.assertFalse(cond["is_inverted"])

            impulse = self.engine.compute_macro_impulse(cond)
            self.assertEqual(impulse, 0.0)

            # Modulation on missing data must preserve base weights
            w_mod = self.engine.modulate_strategy_weights(self.base_weights, inp)
            for k in self.base_weights:
                self.assertAlmostEqual(w_mod[k], self.base_weights[k], places=5)

    def test_07_alternate_spread_proxies(self) -> None:
        """Verifies fallback to US5Y when US2Y is absent."""
        proxy_dict = {"us10y": 4.25, "us5y": 3.95}  # Spread should be 4.25 - 3.95 = 0.30
        cond = self.engine.extract_macro_condition_vector(proxy_dict, is_krx=False)
        self.assertAlmostEqual(cond["raw_spread_10y2y"], 0.30, places=4)
        self.assertGreater(cond["term_spread"], 0.0)
        self.assertFalse(cond["is_inverted"])

    # -----------------------------------------------------------------------
    # Category 4: International Timezone Causality & KRX 1-Day Lag
    # -----------------------------------------------------------------------
    def test_08_krx_one_day_lag_causality(self) -> None:
        """Verifies that KRX market enforces 1-day lag on US macro shocks to eliminate lookahead bias."""
        # 25-day history with an extreme US shock on the very last day (day T)
        df = make_synthetic_macro_df(
            days=25,
            us10y_base=4.00,
            us2y_base=3.80,
            sox_base=4000.0,
            shock_on_last_day=True,
            us10y_shock=-1.00,  # 10Y drops by 100 bps on day T -> inversion on day T
            us2y_shock=+0.50,
            sox_shock=-800.0,
        )

        # US market sees day T shock
        cond_us = self.engine.extract_macro_condition_vector(df, is_krx=False)
        self.assertTrue(cond_us["is_inverted"], "US should observe inversion on day T")

        # KRX market must see day T-1 (before the shock occurred)
        cond_krx = self.engine.extract_macro_condition_vector(df, is_krx=True)
        self.assertFalse(cond_krx["is_inverted"], "KRX must lag 1 day and not see day T US shock")
        self.assertGreater(cond_krx["raw_spread_10y2y"], 0.0)

    # -----------------------------------------------------------------------
    # Category 5: Composite Macro Impulse Properties
    # -----------------------------------------------------------------------
    def test_09_macro_impulse_boundedness_and_direction(self) -> None:
        """Verifies macro impulse index bounds [-1.0, 1.0] and directionality."""
        # Recessionary headwinds
        bear_vec = {
            "term_spread": -0.80,
            "yield_velocity": -0.70,
            "sox_spillover": -0.90,
            "usdkrw_momentum": -0.60,
            "dxy_momentum": -0.50,
            "wti_terms_of_trade": -0.40,
        }
        impulse_bear = self.engine.compute_macro_impulse(bear_vec)
        self.assertLess(impulse_bear, 0.0)
        self.assertGreaterEqual(impulse_bear, -1.0)

        # Expansion tailwinds
        bull_vec = {
            "term_spread": +0.85,
            "yield_velocity": +0.65,
            "sox_spillover": +0.95,
            "usdkrw_momentum": +0.50,
            "dxy_momentum": +0.40,
            "wti_terms_of_trade": +0.30,
        }
        impulse_bull = self.engine.compute_macro_impulse(bull_vec)
        self.assertGreater(impulse_bull, 0.0)
        self.assertLessEqual(impulse_bull, 1.0)

    # -----------------------------------------------------------------------
    # Category 6: Dynamic Weight Modulation & Invariant Guarantees
    # -----------------------------------------------------------------------
    def test_10_yield_curve_inversion_quality_overweight_ge_15pct(self) -> None:
        """
        CORE INVARIANT: Asserts Quality/Valuation factors increase by >= 15% during inverted yield curve.
        """
        # Create inverted yield curve condition: 10Y=3.60, 2Y=4.40 => Spread = -0.80%
        inv_df = make_synthetic_macro_df(days=25, us10y_base=3.60, us2y_base=4.40)

        # Baseline Quality weight sum
        w_q_base = sum(self.base_weights[q] for q in QUALITY_VALUATION_STRATEGIES)
        self.assertGreater(w_q_base, 0.0)

        # Modulate weights
        w_mod = self.engine.modulate_strategy_weights(self.base_weights, inv_df, market="global")

        # Modulated Quality weight sum
        w_q_mod = sum(w_mod[q] for q in QUALITY_VALUATION_STRATEGIES)

        # Check >= 15% increase ratio
        boost_ratio = w_q_mod / w_q_base
        self.assertGreaterEqual(
            boost_ratio,
            1.150000 - 1e-9,
            f"Quality boost failed: expected >= 1.1500, got {boost_ratio:.6f}",
        )

        # Verify simplex sum = 1.000000
        total_w = sum(w_mod.values())
        self.assertAlmostEqual(total_w, 1.000000, places=6)

    def test_11_inversion_severity_monotonicity(self) -> None:
        """Verifies that deeper yield curve inversion imparts >= quality boost than mild inversion."""
        mild_inv = {"us10y": 4.10, "us2y": 4.15}   # Spread = -0.05%
        deep_inv = {"us10y": 3.00, "us2y": 4.50}   # Spread = -1.50%

        w_q_base = sum(self.base_weights[q] for q in QUALITY_VALUATION_STRATEGIES)

        w_mild = self.engine.modulate_strategy_weights(self.base_weights, mild_inv)
        w_deep = self.engine.modulate_strategy_weights(self.base_weights, deep_inv)

        w_q_mild = sum(w_mild[q] for q in QUALITY_VALUATION_STRATEGIES)
        w_q_deep = sum(w_deep[q] for q in QUALITY_VALUATION_STRATEGIES)

        # Both must meet the >= 15% threshold
        self.assertGreaterEqual(w_q_mild / w_q_base, 1.15 - 1e-9)
        self.assertGreaterEqual(w_q_deep / w_q_base, 1.15 - 1e-9)

        # Deep inversion should allocate at least as much as mild inversion
        self.assertGreaterEqual(w_q_deep, w_q_mild - 1e-9)

    def test_12_steepening_expansion_momentum_breakout_boost(self) -> None:
        """Verifies that steepening yield curve and expansion boosts Momentum/Breakout factors."""
        steep_df = make_synthetic_macro_df(
            days=25,
            us10y_base=4.80,
            us2y_base=2.80,  # Spread = +2.00%
            sox_base=5200.0,
        )

        w_m_base = sum(self.base_weights[m] for m in MOMENTUM_BREAKOUT_STRATEGIES)
        w_mod = self.engine.modulate_strategy_weights(self.base_weights, steep_df, market="global")
        w_m_mod = sum(w_mod[m] for m in MOMENTUM_BREAKOUT_STRATEGIES)

        self.assertGreater(
            w_m_mod,
            w_m_base,
            f"Momentum boost failed: base={w_m_base:.4f}, mod={w_m_mod:.4f}",
        )
        self.assertAlmostEqual(sum(w_mod.values()), 1.0, places=6)

    def test_13_simplex_normalization_invariant_exact_sum_one(self) -> None:
        """Asserts sum of weights strictly normalizes to 1.000000 across 50 random baseline distributions."""
        inv_df = make_synthetic_macro_df(days=25, us10y_base=3.50, us2y_base=4.50)
        for seed in range(50):
            base_w = make_random_simplex_weights(37, seed=seed)
            mod_w = self.engine.modulate_strategy_weights(base_w, inv_df)
            total = sum(mod_w.values())
            self.assertTrue(
                math.isclose(total, 1.0, rel_tol=1e-6, abs_tol=1e-9),
                f"Simplex violation at seed {seed}: sum={total:.12f}",
            )

    def test_14_strict_non_negativity_and_floor(self) -> None:
        """Asserts all modulated weights are strictly non-negative and satisfy floor."""
        inv_df = make_synthetic_macro_df(days=25, us10y_base=3.50, us2y_base=4.50)
        floor = 0.005
        mod_w = self.engine.modulate_strategy_weights(
            self.base_weights, inv_df, enforce_min_floor=True, floor_value=floor
        )
        for strat, w in mod_w.items():
            self.assertGreaterEqual(w, 0.0, f"Negative weight on {strat}: {w}")
            self.assertGreaterEqual(w, floor - 1e-9, f"Weight below floor on {strat}: {w}")

    def test_15_zero_nan_under_adversarial_inputs(self) -> None:
        """Asserts zero NaN and zero infinite values under adversarial numerical conditions."""
        adversarial_indicators = [
            {"us10y": float("inf"), "us2y": 4.0},
            {"us10y": 4.0, "us2y": float("-inf")},
            {"us10y": np.nan, "us2y": 4.0},
            {"usdkrw": 0.0, "dxy": -100.0, "sox": float("nan")},
        ]
        for ind in adversarial_indicators:
            mod_w = self.engine.modulate_strategy_weights(self.base_weights, ind)
            for strat, w in mod_w.items():
                self.assertFalse(math.isnan(w), f"NaN found in {strat}")
                self.assertTrue(math.isfinite(w), f"Infinite value found in {strat}")
            self.assertAlmostEqual(sum(mod_w.values()), 1.0, places=6)

    # -----------------------------------------------------------------------
    # Category 7: 37-Strategy Universe & Integration
    # -----------------------------------------------------------------------
    def test_16_strategy_universe_integrity(self) -> None:
        """Verifies that all 37 strategies are preserved without omissions or additions."""
        mod_w = self.engine.modulate_strategy_weights(self.base_weights, {"us10y": 4.0, "us2y": 4.2})
        self.assertEqual(set(mod_w.keys()), set(ALL_37_STRATEGIES))
        self.assertEqual(len(mod_w), 37)

    def test_17_subset_strategy_weight_handling(self) -> None:
        """Verifies modulation on a partial subset of strategies (e.g. 5 strategies)."""
        subset = {
            "rim_valuation": 0.20,
            "accruals_quality": 0.20,
            "surge": 0.20,
            "vcp_ml": 0.20,
            "stat_arb": 0.20,
        }
        inv_ind = {"us10y": 3.5, "us2y": 4.5}
        mod_w = self.engine.modulate_strategy_weights(subset, inv_ind)
        self.assertEqual(set(mod_w.keys()), set(subset.keys()))
        self.assertAlmostEqual(sum(mod_w.values()), 1.0, places=6)

        # Quality boost must hold on the subset
        q_base = subset["rim_valuation"] + subset["accruals_quality"]
        q_mod = mod_w["rim_valuation"] + mod_w["accruals_quality"]
        self.assertGreaterEqual(q_mod / q_base, 1.15 - 1e-9)

    def test_18_ensemble_scorer_engine_instantiation(self) -> None:
        """Verifies EnsembleScoringEngine contains DynamicMacroFactorTimingEngine instance."""
        scorer = EnsembleScoringEngine()
        self.assertTrue(hasattr(scorer, "macro_factor_timing"))
        self.assertIsInstance(scorer.macro_factor_timing, DynamicMacroFactorTimingEngine)

    def test_19_compute_dynamic_weights_from_sharpe_with_macro(self) -> None:
        """Verifies EnsembleScoringEngine.compute_dynamic_weights_from_sharpe with macro indicators."""
        scorer = EnsembleScoringEngine()
        sharpes = {s: 1.5 for s in ALL_37_STRATEGIES}
        inv_df = make_synthetic_macro_df(days=25, us10y_base=3.60, us2y_base=4.60)

        dyn_w = scorer.compute_dynamic_weights_from_sharpe(
            rolling_sharpes=sharpes,
            regime="SIDEWAYS_LOW_VOL",
            macro_indicators=inv_df,
            market="global",
        )
        self.assertAlmostEqual(sum(dyn_w.values()), 1.0, places=6)
        for s in ALL_37_STRATEGIES:
            self.assertIn(s, dyn_w)
            self.assertGreater(dyn_w[s], 0.0)

    def test_20_backward_compatibility_none_indicators(self) -> None:
        """Verifies compute_dynamic_weights_from_sharpe runs unmodified when macro_indicators=None."""
        scorer = EnsembleScoringEngine()
        sharpes = {s: 1.2 for s in ALL_37_STRATEGIES}
        w_none = scorer.compute_dynamic_weights_from_sharpe(
            rolling_sharpes=sharpes,
            regime="BULL_LOW_VOL",
            macro_indicators=None,
        )
        self.assertAlmostEqual(sum(w_none.values()), 1.0, places=6)
        expected_len = len(scorer.get_base_weights("BULL_LOW_VOL"))
        self.assertEqual(len(w_none), expected_len)
        for s in ALL_37_STRATEGIES:
            self.assertIn(s, w_none)

    # -----------------------------------------------------------------------
    # Category 8: Adversarial Fuzzing & Numerical Boundary Continuity
    # -----------------------------------------------------------------------
    def test_21_monte_carlo_fuzzing_500_iterations(self) -> None:
        """
        500-iteration Monte Carlo fuzzer validating simplex, non-negativity, zero-NaN,
        and the >= 15% inversion guarantee across randomized market regimes.
        """
        rng = np.random.RandomState(106)
        for i in range(500):
            us10y = rng.uniform(0.1, 10.0)
            us2y = rng.uniform(0.1, 10.0)
            usdkrw_ret = rng.uniform(-0.15, 0.15)
            dxy_ret = rng.uniform(-0.10, 0.10)
            sox_ret = rng.uniform(-0.30, 0.30)
            wti_ret = rng.uniform(-0.40, 0.40)

            ind = {
                "us10y": us10y,
                "us2y": us2y,
                "usdkrw_ret": usdkrw_ret,
                "dxy_ret": dxy_ret,
                "sox_ret": sox_ret,
                "wti_ret": wti_ret,
            }

            # Generate random baseline weights
            raw = rng.exponential(1.0, 37)
            raw /= raw.sum()
            base_w = {ALL_37_STRATEGIES[j]: float(raw[j]) for j in range(37)}

            mod_w = self.engine.modulate_strategy_weights(base_w, ind, enforce_min_floor=True)

            # Invariant 1: Simplex sum = 1.000000
            total = sum(mod_w.values())
            self.assertTrue(
                math.isclose(total, 1.0, rel_tol=1e-6, abs_tol=1e-8),
                f"Iteration {i}: Simplex failed: sum={total}",
            )

            # Invariant 2: Non-negative and finite
            for s, w in mod_w.items():
                self.assertGreaterEqual(w, 0.0, f"Iteration {i}: Negative weight on {s}")
                self.assertTrue(math.isfinite(w), f"Iteration {i}: Non-finite weight on {s}")

            # Invariant 3: Inversion Quality Overweight Guarantee
            if (us10y - us2y) < 0:
                q_base = sum(base_w[q] for q in QUALITY_VALUATION_STRATEGIES)
                q_mod = sum(mod_w[q] for q in QUALITY_VALUATION_STRATEGIES)
                self.assertGreaterEqual(
                    q_mod / q_base,
                    1.15 - 1e-8,
                    f"Iteration {i}: Inversion boost failed: ratio={q_mod/q_base:.6f}",
                )

    def test_22_boundary_zero_spread_continuity(self) -> None:
        """Verifies smooth continuity at S_10Y2Y = 0.0 with micro-perturbations."""
        zero_spread = {"us10y": 4.00, "us2y": 4.00}
        micro_neg = {"us10y": 4.00, "us2y": 4.000000001}   # -1e-9
        micro_pos = {"us10y": 4.000000001, "us2y": 4.00}   # +1e-9

        w_zero = self.engine.modulate_strategy_weights(self.base_weights, zero_spread)
        w_neg = self.engine.modulate_strategy_weights(self.base_weights, micro_neg)
        w_pos = self.engine.modulate_strategy_weights(self.base_weights, micro_pos)

        # Verify all sums are 1.000000
        self.assertAlmostEqual(sum(w_zero.values()), 1.0, places=6)
        self.assertAlmostEqual(sum(w_neg.values()), 1.0, places=6)
        self.assertAlmostEqual(sum(w_pos.values()), 1.0, places=6)

        # Micro negative must still satisfy the >= 15% rule safely
        q_base = sum(self.base_weights[q] for q in QUALITY_VALUATION_STRATEGIES)
        q_neg = sum(w_neg[q] for q in QUALITY_VALUATION_STRATEGIES)
        self.assertGreaterEqual(q_neg / q_base, 1.15 - 1e-9)

    def test_23_boundary_series_lengths_no_index_error(self) -> None:
        """Verifies boundary series lengths (1, 2, 20, 21, 22) for US and KRX without IndexError or Day T leakage."""
        for length in (1, 2, 20, 21, 22):
            dates = pd.date_range("2026-01-01", periods=length, freq="B")
            df = pd.DataFrame(index=dates)
            df["us10y"] = [4.0] * length
            df["us2y"] = [3.5] * length
            df["sox"] = [4000.0] * length
            df["dxy"] = [104.0] * length
            df["wti"] = [75.0] * length
            df["usdkrw"] = [1350.0] * length

            # Test both US (lag=0) and KRX (lag=1)
            for is_krx in (False, True):
                cond = self.engine.extract_macro_condition_vector(df, is_krx=is_krx)
                self.assertIsInstance(cond, dict)
                for k in ("term_spread", "yield_velocity", "usdkrw_momentum", "dxy_momentum", "sox_spillover", "wti_terms_of_trade", "macro_impulse"):
                    v = cond[k]
                    self.assertTrue(math.isfinite(v), f"Length {length}, is_krx={is_krx}: {k}={v} not finite")
                    self.assertGreaterEqual(v, -1.0)
                    self.assertLessEqual(v, 1.0)

                mod_w = self.engine.modulate_strategy_weights(self.base_weights, df, market="kr" if is_krx else "us")
                self.assertAlmostEqual(sum(mod_w.values()), 1.0, places=6)
                for s, w in mod_w.items():
                    self.assertGreaterEqual(w, 0.0)
                    self.assertTrue(math.isfinite(w))

            # Test Day T shock shielding for KRX when length == 1
            if length == 1:
                df_shock = df.copy()
                df_shock.iloc[-1, df_shock.columns.get_loc("us10y")] = 2.0  # Inversion shock
                cond_krx_shock = self.engine.extract_macro_condition_vector(df_shock, is_krx=True)
                self.assertFalse(cond_krx_shock["is_inverted"], "1-day history must shield KRX from Day T inversion")
                self.assertEqual(cond_krx_shock["term_spread"], 0.0)

    def test_24_zero_and_infinite_price_indicators_robustness(self) -> None:
        """Verifies zero prices, negative rates, and infinite values produce zero NaNs and valid simplex weights."""
        dates = pd.date_range("2026-01-01", periods=10, freq="B")
        df_zeros = pd.DataFrame({
            "us10y": [0.0] * 10,
            "us2y": [0.0] * 10,
            "dxy": [0.0] * 10,
            "sox": [0.0] * 10,
            "wti": [0.0] * 10,
            "usdkrw": [0.0] * 10,
        }, index=dates)

        cond_zeros = self.engine.extract_macro_condition_vector(df_zeros, is_krx=False)
        for k, v in cond_zeros.items():
            if isinstance(v, float):
                self.assertFalse(math.isnan(v), f"Zero prices leaked NaN into {k}")
                self.assertTrue(math.isfinite(v), f"Zero prices leaked non-finite into {k}")

        w_zeros = self.engine.modulate_strategy_weights(self.base_weights, df_zeros)
        self.assertAlmostEqual(sum(w_zeros.values()), 1.0, places=6)

        # Dictionary with infinite and malformed values
        dirty_dict = {
            "us10y": float("inf"),
            "us2y": float("-inf"),
            "term_spread": "corrupted_string",
            "yield_velocity": [1, 2, 3],
            "sox_spillover": {"nested": "dict"},
            "usdkrw": 0.0,
            "dxy": float("nan"),
            "wti": 0.0,
        }
        cond_dirty = self.engine.extract_macro_condition_vector(dirty_dict, is_krx=False)
        for k, v in cond_dirty.items():
            if isinstance(v, float):
                self.assertFalse(math.isnan(v), f"Dirty dict leaked NaN into {k}")
                self.assertTrue(math.isfinite(v), f"Dirty dict leaked non-finite into {k}")

        w_dirty = self.engine.modulate_strategy_weights(self.base_weights, dirty_dict)
        self.assertAlmostEqual(sum(w_dirty.values()), 1.0, places=6)
        for s, w in w_dirty.items():
            self.assertGreaterEqual(w, 0.0)


if __name__ == "__main__":
    unittest.main()
