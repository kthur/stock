"""
tests/test_phase106_challenger_m1_2.py — Adversarial Stress Test Suite for Milestone 1.

Challenger M1_2 Stress Tests:
1. Test EnsembleScoringEngine weight computation and calculate_ensemble_score() with sudden regime shifts.
2. Test Decoupling alpha tilts in calculate_ensemble_score() violating Quality boost invariant.
3. Stress test KRX vs US timezone causality on DataFrame inputs (zero leakage).
4. Stress test KRX vs US timezone causality on Dictionary inputs (leakage detection).
5. Stress test short-history boundary conditions (len < lag).
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
from src.ai.ensemble_scorer import EnsembleScoringEngine


QUALITY_VALUATION_STRATEGIES = [
    "rim_valuation", "accruals_quality", "mq_factor",
    "valueup_catalyst", "factor_neutralized", "regression",
]

MOMENTUM_BREAKOUT_STRATEGIES = [
    "surge", "range_expansion_breakout", "vcp_rule",
    "vcp_ml", "trend_efficiency", "sector_rotation",
]


class TestPhase106AdversarialChallengerM1(unittest.TestCase):
    """
    Empirical Adversarial Test Suite for Milestone 1.
    """

    def setUp(self) -> None:
        self.engine = DynamicMacroFactorTimingEngine()
        self.scorer = EnsembleScoringEngine()

    # -----------------------------------------------------------------------
    # Challenge 1: Sudden Regime Shifts in EnsembleScoringEngine
    # -----------------------------------------------------------------------
    def test_challenge_01_sudden_regime_shift_macro_modulation_bypass(self) -> None:
        """
        Adversarial Test: Verify whether sudden regime shifts bypass macro factor modulation.
        In discrete regime mode, is_regime_shift triggers early return at line 14219
        before macro modulation is applied at line 14238.
        """
        scorer = EnsembleScoringEngine()
        macro_ind = {
            "us10y": 3.50,
            "us2y": 4.50, # Inverted yield curve: raw spread = -1.00%
        }
        sharpes = {"regression": 1.5, "rim_valuation": 1.2, "surge": 0.8}

        # Step 1: Initialize in BULL_LOW_VOL
        w_bull = scorer.compute_dynamic_weights_from_sharpe(
            sharpes,
            regime="BULL_LOW_VOL",
            market="us",
            macro_indicators=macro_ind,
        )

        # Step 2: Sudden regime shift to CRISIS with identical inverted yield curve
        w_crisis = scorer.compute_dynamic_weights_from_sharpe(
            sharpes,
            regime="CRISIS",
            market="us",
            macro_indicators=macro_ind,
        )

        # Baseline unmodulated weights for CRISIS
        scorer_unmod = EnsembleScoringEngine()
        w_crisis_unmod = scorer_unmod.compute_dynamic_weights_from_sharpe(
            sharpes,
            regime="CRISIS",
            market="us",
            macro_indicators=None,
        )
        q_sum_unmod = sum(w_crisis_unmod[k] for k in QUALITY_VALUATION_STRATEGIES if k in w_crisis_unmod)
        q_sum_crisis = sum(w_crisis[k] for k in QUALITY_VALUATION_STRATEGIES if k in w_crisis)

        expected_w_crisis_mod = self.engine.modulate_strategy_weights(
            w_crisis_unmod,
            macro_ind,
            market="us",
        )
        q_sum_expected = sum(expected_w_crisis_mod[k] for k in QUALITY_VALUATION_STRATEGIES if k in expected_w_crisis_mod)

        print(f"\n[Regime Shift Test] q_sum_unmod={q_sum_unmod:.6f}, q_sum_crisis={q_sum_crisis:.6f}, q_sum_expected={q_sum_expected:.6f}")
        
        is_bypassed = (abs(q_sum_crisis - q_sum_unmod) < 1e-6)
        quality_boost_ratio = q_sum_crisis / max(1e-6, q_sum_unmod)

        # Strict invariant assertion: Quality MUST be boosted >= 15% on regime shift
        self.assertFalse(
            is_bypassed,
            f"CRITICAL BUG: Macro factor timing modulation was completely BYPASSED during sudden regime shift! "
            f"Quality sum is {q_sum_crisis:.6f} (matches unmodulated {q_sum_unmod:.6f}), "
            f"expected modulated {q_sum_expected:.6f}. Quality boost ratio is {quality_boost_ratio:.4f} < 1.1500.",
        )
        self.assertGreaterEqual(
            quality_boost_ratio,
            1.150000,
            f"Quality boost ratio {quality_boost_ratio:.4f} violates >= 1.1500 requirement during regime shift.",
        )

    # -----------------------------------------------------------------------
    # Challenge 2: Decoupling Tilts Dilute Quality Invariant in calculate_ensemble_score
    # -----------------------------------------------------------------------
    def test_challenge_02_decoupling_us_bull_kr_bear_invariant(self) -> None:
        """
        Adversarial Test: Check whether DECOUPLING_US_BULL_KR_BEAR breaks the Quality >= 15% invariant
        in calculate_ensemble_score().
        """
        scorer = EnsembleScoringEngine()
        macro_ind = {
            "us10y": 3.80,
            "us2y": 4.60, # Inverted yield curve: raw spread = -0.80%
        }

        # Properly formatted strategy DataFrame fixtures
        symbols = ["005930", "AAPL"]
        reg_df = pd.DataFrame({"symbol": symbols, "market": ["KOSPI", "SP500"], "pred_return_20d": [0.03, 0.04]})
        surge_df = pd.DataFrame({"symbol": symbols, "market": ["KOSPI", "SP500"], "surge_score": [0.60, 0.70]})
        rim_df = pd.DataFrame({"symbol": symbols, "market": ["KOSPI", "SP500"], "rim_score": [0.55, 0.65]})
        valueup_df = pd.DataFrame({"symbol": symbols, "market": ["KOSPI", "SP500"], "valueup_score": [0.50, 0.60]})

        res = scorer.calculate_ensemble_score(
            scores_df=None,
            regression_df=reg_df,
            surge_df=surge_df,
            rim_df=rim_df,
            valueup_catalyst_df=valueup_df,
            decoupling_status="DECOUPLING_US_BULL_KR_BEAR",
            macro_indicators=macro_ind,
            version=113,
        )

        us_w = scorer.us_strategy_weights
        kr_w = scorer.kr_strategy_weights

        # 1. Simplex sums
        self.assertAlmostEqual(sum(us_w.values()), 1.0, places=6, msg="US weights simplex sum != 1.0")
        self.assertAlmostEqual(sum(kr_w.values()), 1.0, places=6, msg="KR weights simplex sum != 1.0")

        # 2. Check US Quality allocation under inversion
        # Unmodulated baseline US weights in BULL_LOW_VOL
        scorer_base = EnsembleScoringEngine()
        base_us_w = scorer_base.compute_dynamic_weights_from_sharpe({}, regime="BULL_LOW_VOL", market="us")
        q_base_us = sum(base_us_w[k] for k in QUALITY_VALUATION_STRATEGIES if k in base_us_w)
        q_final_us = sum(us_w[k] for k in QUALITY_VALUATION_STRATEGIES if k in us_w)

        us_boost = q_final_us / max(1e-6, q_base_us)
        print(f"\n[Decoupling US Bull] q_base_us={q_base_us:.6f}, q_final_us={q_final_us:.6f}, boost={us_boost:.4f}")

        self.assertGreaterEqual(
            us_boost,
            1.150000,
            f"Decoupling DECOUPLING_US_BULL_KR_BEAR diluted US Quality allocation below invariant: boost={us_boost:.4f} < 1.1500.",
        )

    # -----------------------------------------------------------------------
    # Challenge 3: KRX vs US Timezone Causality Stress Test (DataFrame)
    # -----------------------------------------------------------------------
    def test_challenge_03_dataframe_krx_causality_zero_leakage(self) -> None:
        """
        Adversarial Test: When DataFrame is passed, mutating Day T US macro indicators
        MUST produce exactly ZERO difference in KRX weights at Day T.
        """
        days = 25
        dates = pd.date_range("2026-09-15", periods=days, freq="B")
        df_clean = pd.DataFrame(index=dates)
        df_clean["us10y"] = np.linspace(4.0, 4.2, days)
        df_clean["us2y"] = np.linspace(3.8, 3.9, days)
        df_clean["dxy"] = np.linspace(104.0, 105.0, days)
        df_clean["sox"] = np.linspace(4800.0, 4900.0, days)
        df_clean["wti"] = np.linspace(75.0, 78.0, days)
        df_clean["usdkrw"] = np.linspace(1340.0, 1350.0, days)

        # Extreme Day T US shock
        df_shocked = df_clean.copy()
        df_shocked.iloc[-1, df_shocked.columns.get_loc("us10y")] = 2.0  # -220 bps yield crash
        df_shocked.iloc[-1, df_shocked.columns.get_loc("us2y")] = 5.5   # +160 bps yield surge -> deep inversion
        df_shocked.iloc[-1, df_shocked.columns.get_loc("sox")] = 3000.0 # -40% tech crash
        df_shocked.iloc[-1, df_shocked.columns.get_loc("dxy")] = 120.0  # +15% dollar spike
        df_shocked.iloc[-1, df_shocked.columns.get_loc("wti")] = 40.0   # -50% oil collapse

        base_weights = {
            "regression": 0.10, "rim_valuation": 0.10, "surge": 0.10,
            "vcp_rule": 0.10, "vcp_ml": 0.10, "sector_rotation": 0.10,
            "mq_factor": 0.10, "valueup_catalyst": 0.10, "factor_neutralized": 0.10,
            "accruals_quality": 0.10,
        }

        w_krx_clean = self.engine.modulate_strategy_weights(base_weights, df_clean, market="kr")
        w_krx_shocked = self.engine.modulate_strategy_weights(base_weights, df_shocked, market="kr")
        max_krx_diff = max(abs(w_krx_clean[k] - w_krx_shocked[k]) for k in base_weights)

        w_us_clean = self.engine.modulate_strategy_weights(base_weights, df_clean, market="us")
        w_us_shocked = self.engine.modulate_strategy_weights(base_weights, df_shocked, market="us")
        max_us_diff = max(abs(w_us_clean[k] - w_us_shocked[k]) for k in base_weights)

        print(f"\n[Timezone DF Test] max_krx_diff={max_krx_diff:.10e}, max_us_diff={max_us_diff:.6f}")

        self.assertGreater(max_us_diff, 0.05, "US market should have reacted significantly to Day T shock.")
        self.assertEqual(
            max_krx_diff,
            0.0,
            f"CRITICAL CAUSALITY VIOLATION: Day T US macro shock leaked into KRX weights! max_diff={max_krx_diff:.10e}",
        )

    # -----------------------------------------------------------------------
    # Challenge 4: KRX vs US Timezone Causality Stress Test (Dictionary)
    # -----------------------------------------------------------------------
    def test_challenge_04_dictionary_krx_causality_leakage(self) -> None:
        """
        Adversarial Test: When macro indicators are passed as a dictionary of current
        market indicators, does extract_macro_condition_vector(is_krx=True) enforce lag?
        Or does it leak contemporaneous US moves into KRX weights?
        """
        base_weights = {
            "regression": 0.10, "rim_valuation": 0.10, "surge": 0.10,
            "vcp_rule": 0.10, "vcp_ml": 0.10, "sector_rotation": 0.10,
            "mq_factor": 0.10, "valueup_catalyst": 0.10, "factor_neutralized": 0.10,
            "accruals_quality": 0.10,
        }

        dict_shocked = {
            "us10y": 2.0, "us2y": 5.0, # Inverted yield curve
            "sox": 3000.0, "dxy": 120.0, "wti": 40.0, "usdkrw": 1350.0,
        }
        dict_clean = {
            "us10y": 4.2, "us2y": 3.8, # Normal steep curve
            "sox": 4900.0, "dxy": 104.5, "wti": 75.0, "usdkrw": 1350.0,
        }

        w_krx_from_clean = self.engine.modulate_strategy_weights(base_weights, dict_clean, market="kr")
        w_krx_from_shocked = self.engine.modulate_strategy_weights(base_weights, dict_shocked, market="kr")

        diff = max(abs(w_krx_from_clean[k] - w_krx_from_shocked[k]) for k in base_weights)
        print(f"\n[Timezone Dict Test] max_diff between clean and shocked dict in KRX: {diff:.6f}")

        cond_clean = self.engine.extract_macro_condition_vector(dict_shocked, is_krx=False)
        cond_krx = self.engine.extract_macro_condition_vector(dict_shocked, is_krx=True)

        self.assertNotEqual(
            cond_clean,
            cond_krx,
            "DICTIONARY CAUSALITY LEAKAGE: extract_macro_condition_vector returns identical conditions "
            "for is_krx=True and is_krx=False under dictionary input! Contemporaneous US shock leaks to KRX.",
        )

    # -----------------------------------------------------------------------
    # Challenge 5: Single-day history boundary condition in DataFrame
    # -----------------------------------------------------------------------
    def test_challenge_05_single_day_dataframe_krx_leakage(self) -> None:
        """
        Adversarial Test: When DataFrame has only 1 row (length 1),
        idx_s = -1 - lag if len(clean_s) > lag else -1
        Since len(1) > 1 is False, idx_s falls back to -1 (Day T).
        Verify whether contemporaneous shock leaks to KRX when len(df) == 1.
        """
        dates = pd.date_range("2026-10-14", periods=1)
        df_1d_clean = pd.DataFrame(
            {"us10y": [4.20], "us2y": [3.80], "dxy": [104.5], "sox": [4800.0], "wti": [75.0], "usdkrw": [1350.0]},
            index=dates,
        )
        df_1d_shocked = pd.DataFrame(
            {"us10y": [2.00], "us2y": [5.00], "dxy": [120.0], "sox": [3000.0], "wti": [40.0], "usdkrw": [1350.0]},
            index=dates,
        )

        cond_clean = self.engine.extract_macro_condition_vector(df_1d_clean, is_krx=True)
        cond_shocked = self.engine.extract_macro_condition_vector(df_1d_shocked, is_krx=True)

        # If it fell back to -1, cond_shocked will show inversion is True
        print(f"\n[1-Day DF Test] is_inverted for clean={cond_clean['is_inverted']}, shocked={cond_shocked['is_inverted']}")
        self.assertFalse(
            cond_shocked["is_inverted"],
            "SINGLE-DAY DF LEAKAGE: 1-day DataFrame falls back to iloc[-1] and leaks Day T shock to KRX!",
        )


if __name__ == "__main__":
    unittest.main()
