"""
tests/test_phase108_brinson_attributor.py — Comprehensive Unit & Adversarial Test Harness.

Phase 108 / Feature F512 / Release R124 (v115 Production Master)
Milestone 3: Institutional Brinson-Fachler Multi-Currency Factor Performance Attributor.

Test Categories:
- Category 1: Class Instantiation, Config, Attributes & Alias Trees (TC01~TC03)
- Category 2: Single-Period Hand-Calculated Brinson-Fachler Decomposition (TC04~TC06)
- Category 3: Single-Period 1,000+ Randomized Portfolio Fuzzing & Arithmetic Identity (TC07~TC09)
- Category 4: Multi-Currency & CIP Forward Hedging Integration (TC10~TC13)
- Category 5: Multi-Period Compounding via Carino Logarithmic Linking (TC14~TC17)
- Category 6: Fama-French 5-Factor + Momentum Multi-Factor OLS Regression (TC18~TC21)
- Category 7: 2D Market Regime Conditional Performance Evaluation (TC22~TC24)
- Category 8: Audit-Ready Institutional Tear Sheet Generation (Text & Markdown) (TC25~TC27)
- Category 9: Asset-Level to Segment-Level Mapping & Cross-Market Aggregation (TC28~TC30)
- Category 10: Adversarial Stress & Numerical Boundary Edge Cases (TC31~TC34)
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

# Path setup: Ensure repo root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(TRADING_SYSTEM_DIR), str(PROJECT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.analysis.brinson_factor_attributor import (
    BrinsonFactorAttributor,
    SegmentAttribution,
    BrinsonDecompositionResult,
    MultiPeriodAttributionResult,
    FactorRiskAttributionResult,
    InstitutionalBrinsonFactorAttributor,
    Phase108BrinsonFactorAttributor,
    MultiCurrencyBrinsonAttributor,
    BrinsonFachlerPerformanceAttributor,
    CANONICAL_2D_REGIMES,
    CANONICAL_FACTORS,
)


class TestPhase108BrinsonAttributor(unittest.TestCase):
    """Comprehensive test harness for BrinsonFactorAttributor."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        np.random.seed(42)
        self.attributor = BrinsonFactorAttributor(
            base_currency="KRW",
            default_benchmark="EQUAL_WEIGHT",
            tolerance=1e-6,
            normalize_weights=True,
        )

    # -----------------------------------------------------------------------
    # Category 1: Class Instantiation, Config, Attributes & Alias Trees
    # -----------------------------------------------------------------------

    def test_tc01_class_aliases(self) -> None:
        """TC01: Verify full alias trees for backward compatibility."""
        self.assertIs(InstitutionalBrinsonFactorAttributor, BrinsonFactorAttributor)
        self.assertIs(Phase108BrinsonFactorAttributor, BrinsonFactorAttributor)
        self.assertIs(MultiCurrencyBrinsonAttributor, BrinsonFactorAttributor)
        self.assertIs(BrinsonFachlerPerformanceAttributor, BrinsonFactorAttributor)

    def test_tc02_default_initialization(self) -> None:
        """TC02: Verify default attributes and configs."""
        attr = BrinsonFactorAttributor()
        self.assertEqual(attr.base_currency, "KRW")
        self.assertEqual(attr.default_benchmark, "EQUAL_WEIGHT")
        self.assertEqual(attr.tolerance, 1e-6)
        self.assertTrue(attr.normalize_weights)

    def test_tc03_custom_initialization(self) -> None:
        """TC03: Verify custom base currency and tolerance settings."""
        attr = InstitutionalBrinsonFactorAttributor(
            base_currency="USD",
            default_benchmark="SP500",
            tolerance=1e-8,
            normalize_weights=False,
        )
        self.assertEqual(attr.base_currency, "USD")
        self.assertEqual(attr.default_benchmark, "SP500")
        self.assertEqual(attr.tolerance, 1e-8)
        self.assertFalse(attr.normalize_weights)

    # -----------------------------------------------------------------------
    # Category 2: Single-Period Hand-Calculated Brinson-Fachler Decomposition
    # -----------------------------------------------------------------------

    def test_tc04_hand_calculated_single_period_exact_values(self) -> None:
        """
        TC04: Verify single-period Brinson-Fachler decomposition against exact hand-calculated figures.

        Sectors: Technology, Financials, Healthcare
        Weights:
            Portfolio: Tech=0.50, Fin=0.30, Health=0.20
            Benchmark: Tech=0.40, Fin=0.40, Health=0.20
        Local Returns:
            Portfolio: Tech=0.10, Fin=0.04, Health=0.02
            Benchmark: Tech=0.08, Fin=0.03, Health=0.01
        """
        p_weights = {"Technology": 0.50, "Financials": 0.30, "Healthcare": 0.20}
        b_weights = {"Technology": 0.40, "Financials": 0.40, "Healthcare": 0.20}
        p_returns = {"Technology": 0.10, "Financials": 0.04, "Healthcare": 0.02}
        b_returns = {"Technology": 0.08, "Financials": 0.03, "Healthcare": 0.01}

        result = self.attributor.decompose_single_period(
            portfolio_weights=p_weights,
            benchmark_weights=b_weights,
            asset_returns_local=p_returns,
            benchmark_returns_local=b_returns,
        )

        # Expected:
        # R_p = 0.50*0.10 + 0.30*0.04 + 0.20*0.02 = 0.066
        # R_b = 0.40*0.08 + 0.40*0.03 + 0.20*0.01 = 0.046
        # Delta R = 0.066 - 0.046 = 0.020
        # Alloc: (0.50-0.40)*(0.08-0.046) + (0.30-0.40)*(0.03-0.046) + 0 = 0.0034 + 0.0016 = 0.0050
        # Select: 0.40*(0.10-0.08) + 0.40*(0.04-0.03) + 0.20*(0.02-0.01) = 0.0080 + 0.0040 + 0.0020 = 0.0140
        # Inter: (0.50-0.40)*(0.10-0.08) + (0.30-0.40)*(0.04-0.03) + 0 = 0.0020 - 0.0010 = 0.0010
        # Total = 0.0050 + 0.0140 + 0.0010 = 0.0200
        self.assertAlmostEqual(result.portfolio_return_base, 0.066, places=12)
        self.assertAlmostEqual(result.benchmark_return_base, 0.046, places=12)
        self.assertAlmostEqual(result.total_active_return, 0.020, places=12)
        self.assertAlmostEqual(result.allocation_effect, 0.0050, places=12)
        self.assertAlmostEqual(result.selection_effect, 0.0140, places=12)
        self.assertAlmostEqual(result.interaction_effect, 0.0010, places=12)
        self.assertAlmostEqual(result.currency_effect, 0.0, places=12)
        self.assertTrue(result.is_identity_valid)
        self.assertLess(result.arithmetic_identity_error, 1e-15)

    def test_tc05_segment_level_breakdown_verification(self) -> None:
        """TC05: Verify individual segment attribution items."""
        p_weights = {"Tech": 0.60, "Fin": 0.40}
        b_weights = {"Tech": 0.40, "Fin": 0.60}
        p_returns = {"Tech": 0.12, "Fin": 0.05}
        b_returns = {"Tech": 0.10, "Fin": 0.04}

        result = self.attributor.decompose_single_period(
            portfolio_weights=p_weights,
            benchmark_weights=b_weights,
            asset_returns_local=p_returns,
            benchmark_returns_local=b_returns,
        )

        self.assertEqual(len(result.segments), 2)
        tech_seg = next(s for s in result.segments if s.segment == "Tech")
        self.assertAlmostEqual(tech_seg.portfolio_weight, 0.60, places=10)
        self.assertAlmostEqual(tech_seg.benchmark_weight, 0.40, places=10)
        self.assertAlmostEqual(tech_seg.active_weight, 0.20, places=10)
        self.assertAlmostEqual(tech_seg.active_return_local, 0.02, places=10)
        self.assertAlmostEqual(tech_seg.interaction_effect, 0.20 * 0.02, places=10)

    def test_tc06_identical_weights_zero_allocation(self) -> None:
        """TC06: When portfolio and benchmark weights are identical, allocation and interaction are strictly 0."""
        weights = {"A": 0.50, "B": 0.50}
        p_returns = {"A": 0.05, "B": -0.02}
        b_returns = {"A": 0.02, "B": 0.01}

        result = self.attributor.decompose_single_period(
            portfolio_weights=weights,
            benchmark_weights=weights,
            asset_returns_local=p_returns,
            benchmark_returns_local=b_returns,
        )

        self.assertAlmostEqual(result.allocation_effect, 0.0, places=14)
        self.assertAlmostEqual(result.interaction_effect, 0.0, places=14)
        self.assertAlmostEqual(result.total_active_return, result.selection_effect, places=14)
        self.assertTrue(result.is_identity_valid)

    # -----------------------------------------------------------------------
    # Category 3: Single-Period 1,000+ Randomized Portfolio Fuzzing
    # -----------------------------------------------------------------------

    def test_tc07_randomized_portfolio_fuzzing_1000_runs(self) -> None:
        """
        TC07: Test arithmetic identity across 1,000 randomized portfolios.
        Validates: |R_total - (R_alloc + R_select + R_inter + R_curr)| < 1e-6 (empirically < 1e-14).
        """
        num_runs = 1000
        max_error = 0.0

        for run_idx in range(num_runs):
            num_segs = np.random.randint(2, 12)
            seg_names = [f"SEG_{i}" for i in range(num_segs)]

            # Generate random non-negative weights
            raw_pw = np.random.uniform(0.01, 1.0, size=num_segs)
            raw_bw = np.random.uniform(0.01, 1.0, size=num_segs)
            pw = raw_pw / np.sum(raw_pw)
            bw = raw_bw / np.sum(raw_bw)

            # Random local returns in [-25%, +35%]
            p_ret = np.random.uniform(-0.25, 0.35, size=num_segs)
            b_ret = np.random.uniform(-0.25, 0.35, size=num_segs)

            # Random currency returns, hedge ratios, forward premiums
            curr_ret = np.random.uniform(-0.08, 0.08, size=num_segs)
            hedge_r = np.random.uniform(0.0, 1.0, size=num_segs)
            fwd_prem = np.random.uniform(-0.03, 0.03, size=num_segs)

            p_weights_dict = {seg_names[i]: float(pw[i]) for i in range(num_segs)}
            b_weights_dict = {seg_names[i]: float(bw[i]) for i in range(num_segs)}
            p_returns_dict = {seg_names[i]: float(p_ret[i]) for i in range(num_segs)}
            b_returns_dict = {seg_names[i]: float(b_ret[i]) for i in range(num_segs)}
            curr_returns_dict = {seg_names[i]: float(curr_ret[i]) for i in range(num_segs)}
            hedge_ratios_dict = {seg_names[i]: float(hedge_r[i]) for i in range(num_segs)}
            forward_prems_dict = {seg_names[i]: float(fwd_prem[i]) for i in range(num_segs)}

            res = self.attributor.decompose_single_period(
                portfolio_weights=p_weights_dict,
                benchmark_weights=b_weights_dict,
                asset_returns_local=p_returns_dict,
                benchmark_returns_local=b_returns_dict,
                currency_returns=curr_returns_dict,
                hedge_ratios=hedge_ratios_dict,
                forward_premiums=forward_prems_dict,
            )

            self.assertTrue(res.is_identity_valid, f"Identity violated at run {run_idx}")
            self.assertLess(res.arithmetic_identity_error, 1e-6)
            if res.arithmetic_identity_error > max_error:
                max_error = res.arithmetic_identity_error

            # Sub-decomposition check
            curr_sub_sum = res.currency_allocation + res.currency_selection + res.currency_interaction
            self.assertAlmostEqual(res.currency_effect, curr_sub_sum, places=12)

        # Empirically verify machine precision across all 1,000 runs
        self.assertLess(max_error, 1e-13, f"Max error across 1,000 runs was {max_error:.2e}")

    def test_tc08_sparse_disjoint_segments(self) -> None:
        """TC08: Verify portfolios where portfolio and benchmark hold completely disjoint segments."""
        p_weights = {"Segment_A": 0.70, "Segment_B": 0.30}
        b_weights = {"Segment_C": 0.50, "Segment_D": 0.50}
        p_returns = {"Segment_A": 0.05, "Segment_B": 0.02}
        b_returns = {"Segment_C": 0.01, "Segment_D": -0.03}

        result = self.attributor.decompose_single_period(
            portfolio_weights=p_weights,
            benchmark_weights=b_weights,
            asset_returns_local=p_returns,
            benchmark_returns_local=b_returns,
        )

        self.assertEqual(len(result.segments), 4)
        self.assertTrue(result.is_identity_valid)
        self.assertLess(result.arithmetic_identity_error, 1e-14)

    def test_tc09_unnormalized_weights_auto_normalization(self) -> None:
        """TC09: Verify automatic weight normalization when input weights do not sum to 1.0."""
        p_weights = {"Tech": 50.0, "Fin": 50.0}
        b_weights = {"Tech": 20.0, "Fin": 80.0}
        p_returns = {"Tech": 0.10, "Fin": 0.02}
        b_returns = {"Tech": 0.05, "Fin": 0.01}

        result = self.attributor.decompose_single_period(
            portfolio_weights=p_weights,
            benchmark_weights=b_weights,
            asset_returns_local=p_returns,
            benchmark_returns_local=b_returns,
        )

        self.assertTrue(result.is_identity_valid)
        self.assertAlmostEqual(result.segments[0].portfolio_weight, 0.50, places=10)
        self.assertAlmostEqual(result.segments[1].portfolio_weight, 0.50, places=10)

    # -----------------------------------------------------------------------
    # Category 4: Multi-Currency & CIP Forward Hedging Integration
    # -----------------------------------------------------------------------

    def test_tc10_unhedged_foreign_currency_passthrough(self) -> None:
        """TC10: When hedge ratio is 0.0, hedged currency return equals raw currency return."""
        p_weights = {"US_Tech": 1.0}
        b_weights = {"US_Tech": 1.0}
        p_returns = {"US_Tech": 0.05}
        b_returns = {"US_Tech": 0.05}
        c_returns = {"US_Tech": 0.02}  # USD appreciated 2% against KRW
        h_ratios = {"US_Tech": 0.0}   # Unhedged

        result = self.attributor.decompose_single_period(
            portfolio_weights=p_weights,
            benchmark_weights=b_weights,
            asset_returns_local=p_returns,
            benchmark_returns_local=b_returns,
            currency_returns=c_returns,
            hedge_ratios=h_ratios,
        )

        # Base return = (1 + 0.05)*(1 + 0.02) - 1 = 0.071
        self.assertAlmostEqual(result.portfolio_return_base, 0.071, places=10)
        self.assertAlmostEqual(result.benchmark_return_base, 0.071, places=10)
        self.assertAlmostEqual(result.total_active_return, 0.0, places=10)
        self.assertTrue(result.is_identity_valid)

    def test_tc11_fully_hedged_cip_forward_replacement(self) -> None:
        """TC11: When hedge ratio is 1.0, currency return is replaced by CIP forward premium f."""
        p_weights = {"US_Tech": 1.0}
        b_weights = {"US_Tech": 1.0}
        p_returns = {"US_Tech": 0.05}
        b_returns = {"US_Tech": 0.05}
        c_returns = {"US_Tech": -0.05}  # USD depreciated 5%
        h_ratios = {"US_Tech": 1.0}    # Fully hedged
        f_premiums = {"US_Tech": 0.005} # CIP forward premium 0.5%

        result = self.attributor.decompose_single_period(
            portfolio_weights=p_weights,
            benchmark_weights=b_weights,
            asset_returns_local=p_returns,
            benchmark_returns_local=b_returns,
            currency_returns=c_returns,
            hedge_ratios=h_ratios,
            forward_premiums=f_premiums,
        )

        # Hedged currency return = (1 - 1)*(-0.05) + 1*0.005 = 0.005
        # Portfolio base return = (1 + 0.05)*(1 + 0.005) - 1 = 0.05525
        # Benchmark base return = (1 + 0.05)*(1 - 0.05) - 1 = -0.0025 (unhedged benchmark)
        # Active return = 0.05525 - (-0.0025) = 0.05775 (+5.775%)
        self.assertAlmostEqual(result.portfolio_return_base, 0.05525, places=10)
        self.assertAlmostEqual(result.benchmark_return_base, -0.0025, places=10)
        self.assertAlmostEqual(result.total_active_return, 0.05775, places=10)
        self.assertAlmostEqual(result.currency_effect, 0.05775, places=10)
        self.assertTrue(result.is_identity_valid)

    def test_tc12_partial_hedging_interpolation(self) -> None:
        """TC12: Verify partial hedging linearly interpolates between raw currency return and forward premium."""
        p_weights = {"US_Stock": 1.0}
        b_weights = {"US_Stock": 1.0}
        p_returns = {"US_Stock": 0.0}
        b_returns = {"US_Stock": 0.0}
        c_returns = {"US_Stock": 0.04}
        f_premiums = {"US_Stock": 0.01}
        h_ratios = {"US_Stock": 0.50}

        result = self.attributor.decompose_single_period(
            portfolio_weights=p_weights,
            benchmark_weights=b_weights,
            asset_returns_local=p_returns,
            benchmark_returns_local=b_returns,
            currency_returns=c_returns,
            hedge_ratios=h_ratios,
            forward_premiums=f_premiums,
        )

        # Hedged return = 0.5*0.04 + 0.5*0.01 = 0.025
        # Benchmark unhedged = 0.04
        # Active = 0.025 - 0.04 = -0.015
        self.assertAlmostEqual(result.currency_effect, -0.015, places=10)
        self.assertTrue(result.is_identity_valid)

    def test_tc13_currency_allocation_alpha(self) -> None:
        """TC13: Overweighting an appreciating currency generates positive currency allocation effect."""
        # Base currency KRW: Domestic (c=0), Foreign US (c=+0.03)
        p_weights = {"KRX": 0.30, "US": 0.70}  # Overweight US
        b_weights = {"KRX": 0.70, "US": 0.30}
        p_returns = {"KRX": 0.0, "US": 0.0}
        b_returns = {"KRX": 0.0, "US": 0.0}
        c_returns = {"KRX": 0.0, "US": 0.03}

        result = self.attributor.decompose_single_period(
            portfolio_weights=p_weights,
            benchmark_weights=b_weights,
            asset_returns_local=p_returns,
            benchmark_returns_local=b_returns,
            currency_returns=c_returns,
        )

        # Currency allocation = (0.70 - 0.30) * 0.03 = +0.012 (+1.20%)
        self.assertAlmostEqual(result.currency_allocation, 0.012, places=10)
        self.assertAlmostEqual(result.total_active_return, 0.012, places=10)
        self.assertTrue(result.is_identity_valid)

    # -----------------------------------------------------------------------
    # Category 5: Multi-Period Compounding via Carino Logarithmic Linking
    # -----------------------------------------------------------------------

    def test_tc14_multi_period_carino_exact_identity(self) -> None:
        """TC14: Verify Carino multi-period compounded linking arithmetic identity."""
        num_days = 20
        daily_results: List[BrinsonDecompositionResult] = []

        for d in range(num_days):
            pw = {"SecA": 0.60, "SecB": 0.40}
            bw = {"SecA": 0.50, "SecB": 0.50}
            pret = {"SecA": float(np.random.normal(0.001, 0.01)), "SecB": float(np.random.normal(0.0005, 0.01))}
            bret = {"SecA": float(np.random.normal(0.0008, 0.01)), "SecB": float(np.random.normal(0.0006, 0.01))}
            cret = {"SecA": 0.0, "SecB": float(np.random.normal(0.0002, 0.005))}

            res = self.attributor.decompose_single_period(
                portfolio_weights=pw,
                benchmark_weights=bw,
                asset_returns_local=pret,
                benchmark_returns_local=bret,
                currency_returns=cret,
            )
            daily_results.append(res)

        multi_res = self.attributor.decompose_multi_period(daily_results=daily_results)

        self.assertTrue(multi_res.is_identity_valid)
        self.assertLess(multi_res.arithmetic_identity_error, 1e-14)
        self.assertEqual(len(multi_res.carino_coefficients), num_days)

        # Explicit component sum check
        comp_sum = (
            multi_res.cumulative_allocation
            + multi_res.cumulative_selection
            + multi_res.cumulative_interaction
            + multi_res.cumulative_currency
        )
        self.assertAlmostEqual(multi_res.cumulative_active_return, comp_sum, places=13)

    def test_tc15_single_period_multi_period_equivalence(self) -> None:
        """TC15: When T=1 period, Carino coefficient is 1.0 and multi-period matches single period."""
        pw = {"Tech": 0.70, "Fin": 0.30}
        bw = {"Tech": 0.50, "Fin": 0.50}
        pret = {"Tech": 0.03, "Fin": -0.01}
        bret = {"Tech": 0.01, "Fin": 0.00}

        single_res = self.attributor.decompose_single_period(
            portfolio_weights=pw,
            benchmark_weights=bw,
            asset_returns_local=pret,
            benchmark_returns_local=bret,
        )

        multi_res = self.attributor.decompose_multi_period(daily_results=[single_res])

        self.assertEqual(len(multi_res.carino_coefficients), 1)
        self.assertAlmostEqual(multi_res.carino_coefficients[0], 1.0, places=12)
        self.assertAlmostEqual(multi_res.cumulative_active_return, single_res.total_active_return, places=12)
        self.assertAlmostEqual(multi_res.cumulative_allocation, single_res.allocation_effect, places=12)
        self.assertAlmostEqual(multi_res.cumulative_selection, single_res.selection_effect, places=12)

    def test_tc16_identical_daily_returns_taylor_limit(self) -> None:
        """TC16: When portfolio return == benchmark return, Carino linking handles smooth limit without 0/0 error."""
        daily_p = [0.01, 0.02, 0.015]
        daily_b = [0.01, 0.02, 0.015]  # Exactly equal

        coeffs = self.attributor.compute_carino_coefficients(daily_p_returns=daily_p, daily_b_returns=daily_b)

        self.assertEqual(len(coeffs), 3)
        for k in coeffs:
            self.assertTrue(math.isfinite(k))
            self.assertGreater(k, 0.0)

    def test_tc17_empty_multi_period(self) -> None:
        """TC17: Empty input to decompose_multi_period returns zero result with valid identity."""
        multi_res = self.attributor.decompose_multi_period(daily_results=[])
        self.assertTrue(multi_res.is_identity_valid)
        self.assertEqual(multi_res.cumulative_active_return, 0.0)
        self.assertEqual(len(multi_res.carino_coefficients), 0)

    # -----------------------------------------------------------------------
    # Category 6: Fama-French 5-Factor + Momentum Multi-Factor OLS Regression
    # -----------------------------------------------------------------------

    def test_tc18_fama_french_factor_recovery_accuracy(self) -> None:
        """
        TC18: Generate synthetic portfolio returns with known factor loadings and verify regression accuracy.

        Model: R_p - R_f = alpha + 1.20*MKT + 0.40*SMB - 0.30*HML + 0.20*RMW - 0.15*CMA + 0.35*UMD + noise
        """
        n_days = 252
        true_alpha = 0.05 / 252.0  # +5% annual alpha
        true_betas = {
            "MKT": 1.20,
            "SMB": 0.40,
            "HML": -0.30,
            "RMW": 0.20,
            "CMA": -0.15,
            "UMD": 0.35,
        }

        # Generate orthogonal/random factor returns
        factors_data = {
            f: np.random.normal(0.0003, 0.01, size=n_days) for f in CANONICAL_FACTORS
        }
        factor_df = pd.DataFrame(factors_data)

        # Generate portfolio returns
        p_returns = np.full(n_days, true_alpha)
        for f_name, beta_val in true_betas.items():
            p_returns += beta_val * factor_df[f_name].values
        # Add small i.i.d. noise
        p_returns += np.random.normal(0.0, 0.0005, size=n_days)

        res = self.attributor.map_factor_risk(
            portfolio_returns=p_returns,
            factor_returns=factor_df,
            risk_free_rate=0.0,
        )

        # Verify alpha recovery (annualized ~ 5.0%)
        self.assertAlmostEqual(res.alpha_annualized, 0.05, delta=0.015)
        self.assertGreater(res.r_squared, 0.95)

        # Verify factor betas recovery
        for f_name, expected_beta in true_betas.items():
            est_beta = res.factor_betas.get(f_name)
            self.assertIsNotNone(est_beta)
            self.assertAlmostEqual(est_beta, expected_beta, delta=0.08)
            # t-stat should be significant
            self.assertGreater(abs(res.factor_t_stats[f_name]), 3.0)
            self.assertLess(res.factor_p_values[f_name], 0.01)

    def test_tc19_case_insensitive_and_alternate_factor_names(self) -> None:
        """TC19: Verify factor regression recognizes alternate factor names like 'MKT-RF' and 'MOM'."""
        n_days = 100
        factor_df = pd.DataFrame({
            "MKT-RF": np.random.normal(0.0005, 0.01, size=n_days),
            "smb": np.random.normal(0.0, 0.008, size=n_days),
            "hml": np.random.normal(0.0, 0.008, size=n_days),
            "rmw": np.random.normal(0.0, 0.008, size=n_days),
            "cma": np.random.normal(0.0, 0.008, size=n_days),
            "MOM": np.random.normal(0.0002, 0.01, size=n_days),
        })
        p_returns = 1.1 * factor_df["MKT-RF"].values + np.random.normal(0.0, 0.001, size=n_days)

        res = self.attributor.map_factor_risk(
            portfolio_returns=p_returns,
            factor_returns=factor_df,
        )

        self.assertIn("MKT", res.factor_betas)
        self.assertAlmostEqual(res.factor_betas["MKT"], 1.1, delta=0.1)

    def test_tc20_insufficient_data_error_handling(self) -> None:
        """TC20: Verify ValueError raised when observations < 3."""
        with self.assertRaises(ValueError):
            self.attributor.map_factor_risk(
                portfolio_returns=[0.01, 0.02],
                factor_returns=pd.DataFrame({"MKT": [0.01, 0.02]}),
            )

    def test_tc21_specific_risk_calculation(self) -> None:
        """TC21: Verify idiosyncratic specific risk is non-negative and properly scaled."""
        n_days = 60
        factor_df = pd.DataFrame({"MKT": np.random.normal(0.0, 0.01, size=n_days)})
        p_returns = np.random.normal(0.0, 0.02, size=n_days)

        res = self.attributor.map_factor_risk(
            portfolio_returns=p_returns,
            factor_returns=factor_df,
        )

        self.assertGreater(res.specific_risk, 0.0)
        self.assertTrue(math.isfinite(res.specific_risk))

    # -----------------------------------------------------------------------
    # Category 7: 2D Market Regime Conditional Performance Evaluation
    # -----------------------------------------------------------------------

    def test_tc22_2d_regime_breakdown_evaluation(self) -> None:
        """TC22: Verify conditional performance across canonical 2D market regimes."""
        n_days = 140
        regimes: List[str] = []
        for r in CANONICAL_2D_REGIMES:
            regimes.extend([r] * 20)  # 20 days per regime

        # In Bull regimes, make portfolio outperform
        p_returns = []
        b_returns = []
        for r in regimes:
            if "BULL" in r:
                p_returns.append(0.015)
                b_returns.append(0.005)
            elif "BEAR" in r or "CRISIS" in r:
                p_returns.append(-0.01)
                b_returns.append(-0.02)
            else:
                p_returns.append(0.002)
                b_returns.append(0.001)

        factor_df = pd.DataFrame({"MKT": b_returns})

        res = self.attributor.map_factor_risk(
            portfolio_returns=p_returns,
            factor_returns=factor_df,
            regime_labels=regimes,
            benchmark_returns=b_returns,
        )

        self.assertEqual(len(res.regime_breakdown), len(CANONICAL_2D_REGIMES))

        bull_metrics = res.regime_breakdown["BULL_LOW_VOL"]
        self.assertEqual(bull_metrics["count"], 20.0)
        self.assertAlmostEqual(bull_metrics["mean_portfolio_return"], 0.015, places=5)
        self.assertAlmostEqual(bull_metrics["mean_benchmark_return"], 0.005, places=5)
        self.assertAlmostEqual(bull_metrics["win_rate"], 1.0, places=5)

        bear_metrics = res.regime_breakdown["BEAR_LOW_VOL"]
        self.assertAlmostEqual(bear_metrics["mean_portfolio_return"], -0.01, places=5)
        self.assertAlmostEqual(bear_metrics["mean_benchmark_return"], -0.02, places=5)
        self.assertAlmostEqual(bear_metrics["win_rate"], 1.0, places=5)

    def test_tc23_single_regime_fallback(self) -> None:
        """TC23: Verify regime breakdown works properly when only one regime is present."""
        n_days = 30
        regimes = ["SIDEWAYS_LOW_VOL"] * n_days
        p_returns = np.random.normal(0.001, 0.005, size=n_days)
        factor_df = pd.DataFrame({"MKT": np.random.normal(0.0005, 0.005, size=n_days)})

        res = self.attributor.map_factor_risk(
            portfolio_returns=p_returns,
            factor_returns=factor_df,
            regime_labels=regimes,
        )

        self.assertIn("SIDEWAYS_LOW_VOL", res.regime_breakdown)
        self.assertEqual(res.regime_breakdown["SIDEWAYS_LOW_VOL"]["count"], 30.0)

    def test_tc24_regime_labels_length_mismatch_resizing(self) -> None:
        """TC24: Verify graceful handling when regime labels array length does not match returns."""
        p_returns = np.random.normal(0.001, 0.01, size=50)
        factor_df = pd.DataFrame({"MKT": np.random.normal(0.0005, 0.01, size=50)})
        regimes = ["BULL_LOW_VOL", "BEAR_LOW_VOL"]  # length 2, resized to 50

        res = self.attributor.map_factor_risk(
            portfolio_returns=p_returns,
            factor_returns=factor_df,
            regime_labels=regimes,
        )
        self.assertGreater(len(res.regime_breakdown), 0)

    # -----------------------------------------------------------------------
    # Category 8: Audit-Ready Institutional Tear Sheet Generation
    # -----------------------------------------------------------------------

    def test_tc25_text_tear_sheet_formatting(self) -> None:
        """TC25: Verify plain text ASCII tear sheet generation."""
        p_weights = {"Tech": 0.60, "Fin": 0.40}
        b_weights = {"Tech": 0.50, "Fin": 0.50}
        p_returns = {"Tech": 0.08, "Fin": 0.02}
        b_returns = {"Tech": 0.05, "Fin": 0.01}

        decomp_res = self.attributor.decompose_single_period(
            portfolio_weights=p_weights,
            benchmark_weights=b_weights,
            asset_returns_local=p_returns,
            benchmark_returns_local=b_returns,
            as_of_date="2026-10-15",
        )

        factor_df = pd.DataFrame({
            "MKT": np.random.normal(0.001, 0.01, size=30),
            "SMB": np.random.normal(0.0, 0.005, size=30),
        })
        factor_res = self.attributor.map_factor_risk(
            portfolio_returns=np.random.normal(0.001, 0.01, size=30),
            factor_returns=factor_df,
            regime_labels=["BULL_LOW_VOL"] * 30,
        )

        sheet = self.attributor.generate_tear_sheet(decomp_res, factor_result=factor_res, format="text")

        self.assertIsInstance(sheet, str)
        self.assertIn("INSTITUTIONAL PERFORMANCE ATTRIBUTION TEAR SHEET", sheet)
        self.assertIn("EXECUTIVE SUMMARY", sheet)
        self.assertIn("SEGMENT ATTRIBUTION BREAKDOWN", sheet)
        self.assertIn("FACTOR RISK MAPPING", sheet)
        self.assertIn("2D MARKET REGIME CONDITIONAL PERFORMANCE", sheet)
        self.assertIn("Valid: True", sheet)

    def test_tc26_markdown_tear_sheet_formatting(self) -> None:
        """TC26: Verify GitHub-flavored Markdown tear sheet generation."""
        p_weights = {"Tech": 0.70, "Health": 0.30}
        b_weights = {"Tech": 0.50, "Health": 0.50}
        p_returns = {"Tech": 0.04, "Health": 0.01}
        b_returns = {"Tech": 0.02, "Health": 0.00}

        decomp_res = self.attributor.decompose_single_period(
            portfolio_weights=p_weights,
            benchmark_weights=b_weights,
            asset_returns_local=p_returns,
            benchmark_returns_local=b_returns,
        )

        sheet = self.attributor.generate_tear_sheet(decomp_res, format="markdown")

        self.assertIsInstance(sheet, str)
        self.assertIn("# Institutional Performance Attribution Tear Sheet", sheet)
        self.assertIn("| Component | Description | Contribution (%) |", sheet)
        self.assertIn("| Segment | Port Wgt (%) | Bench Wgt (%) |", sheet)
        self.assertIn("Valid: **True**", sheet)

    def test_tc27_multi_period_markdown_tear_sheet(self) -> None:
        """TC27: Verify multi-period Carino tear sheet markdown output."""
        d1 = self.attributor.decompose_single_period(
            portfolio_weights={"A": 1.0}, benchmark_weights={"A": 1.0},
            asset_returns_local={"A": 0.02}, benchmark_returns_local={"A": 0.01},
        )
        d2 = self.attributor.decompose_single_period(
            portfolio_weights={"A": 1.0}, benchmark_weights={"A": 1.0},
            asset_returns_local={"A": -0.01}, benchmark_returns_local={"A": -0.02},
        )
        multi_res = self.attributor.decompose_multi_period([d1, d2])

        sheet = self.attributor.generate_tear_sheet(multi_res, format="markdown")
        self.assertIn("Executive Summary (Carino Multi-Period Linking)", sheet)
        self.assertIn("Periods Evaluated**: 2", sheet)

    # -----------------------------------------------------------------------
    # Category 9: Asset-Level to Segment-Level Mapping & Cross-Market
    # -----------------------------------------------------------------------

    def test_tc28_asset_to_segment_mapping_aggregation(self) -> None:
        """TC28: Verify aggregation from asset-level securities to segment-level sectors."""
        portfolio_weights = {
            "005930.KS": 0.30,  # Samsung Electronics (Tech)
            "000660.KS": 0.20,  # SK Hynix (Tech)
            "055550.KS": 0.50,  # Shinhan Financial (Fin)
        }
        benchmark_weights = {
            "005930.KS": 0.40,
            "000660.KS": 0.10,
            "055550.KS": 0.50,
        }
        p_returns = {
            "005930.KS": 0.05,
            "000660.KS": 0.10,
            "055550.KS": 0.02,
        }
        b_returns = {
            "005930.KS": 0.04,
            "000660.KS": 0.06,
            "055550.KS": 0.01,
        }
        segment_map = {
            "005930.KS": "KRX_TECH",
            "000660.KS": "KRX_TECH",
            "055550.KS": "KRX_FIN",
        }

        result = self.attributor.decompose_single_period(
            portfolio_weights=portfolio_weights,
            benchmark_weights=benchmark_weights,
            asset_returns_local=p_returns,
            benchmark_returns_local=b_returns,
            segment_mapping=segment_map,
        )

        self.assertEqual(len(result.segments), 2)
        tech_seg = next(s for s in result.segments if s.segment == "KRX_TECH")
        fin_seg = next(s for s in result.segments if s.segment == "KRX_FIN")

        # Tech portfolio weight = 0.30 + 0.20 = 0.50
        # Tech benchmark weight = 0.40 + 0.10 = 0.50
        self.assertAlmostEqual(tech_seg.portfolio_weight, 0.50, places=10)
        self.assertAlmostEqual(tech_seg.benchmark_weight, 0.50, places=10)
        # Tech portfolio return = (0.30*0.05 + 0.20*0.10)/0.50 = 0.070
        self.assertAlmostEqual(tech_seg.portfolio_return_local, 0.070, places=10)
        self.assertTrue(result.is_identity_valid)
        self.assertLess(result.arithmetic_identity_error, 1e-14)

    def test_tc29_cross_market_krw_and_usd_portfolio(self) -> None:
        """TC29: Multi-market cross-asset portfolio with domestic KRX (KRW) and foreign US (USD)."""
        p_weights = {
            "005930.KS": 0.40,
            "NVDA": 0.60,
        }
        b_weights = {
            "005930.KS": 0.50,
            "NVDA": 0.50,
        }
        p_returns = {
            "005930.KS": 0.02,
            "NVDA": 0.08,
        }
        b_returns = {
            "005930.KS": 0.01,
            "NVDA": 0.06,
        }
        segment_map = {
            "005930.KS": "KRX_EQUITY",
            "NVDA": "US_EQUITY",
        }
        currency_returns = {
            "005930.KS": 0.0,
            "NVDA": 0.015,  # USDKRW up 1.5%
        }
        hedge_ratios = {
            "005930.KS": 0.0,
            "NVDA": 0.80,   # 80% hedged
        }
        forward_premiums = {
            "005930.KS": 0.0,
            "NVDA": -0.001, # forward discount -0.1%
        }

        result = self.attributor.decompose_single_period(
            portfolio_weights=p_weights,
            benchmark_weights=b_weights,
            asset_returns_local=p_returns,
            benchmark_returns_local=b_returns,
            currency_returns=currency_returns,
            hedge_ratios=hedge_ratios,
            forward_premiums=forward_premiums,
            segment_mapping=segment_map,
        )

        self.assertEqual(len(result.segments), 2)
        self.assertTrue(result.is_identity_valid)
        self.assertLess(result.arithmetic_identity_error, 1e-14)
        self.assertNotEqual(result.currency_effect, 0.0)

    def test_tc30_unmapped_assets_classified_as_unclassified(self) -> None:
        """TC30: Assets missing from segment mapping are grouped into UNCLASSIFIED segment."""
        p_weights = {"ASSET_A": 0.50, "ASSET_B": 0.50}
        b_weights = {"ASSET_A": 0.50, "ASSET_B": 0.50}
        p_returns = {"ASSET_A": 0.02, "ASSET_B": 0.01}
        b_returns = {"ASSET_A": 0.01, "ASSET_B": 0.01}
        seg_map = {"ASSET_A": "SEC_A"}  # ASSET_B not mapped

        result = self.attributor.decompose_single_period(
            portfolio_weights=p_weights,
            benchmark_weights=b_weights,
            asset_returns_local=p_returns,
            benchmark_returns_local=b_returns,
            segment_mapping=seg_map,
        )

        seg_names = {s.segment for s in result.segments}
        self.assertIn("SEC_A", seg_names)
        self.assertIn("UNCLASSIFIED", seg_names)
        self.assertTrue(result.is_identity_valid)

    # -----------------------------------------------------------------------
    # Category 10: Adversarial Stress & Numerical Boundary Edge Cases
    # -----------------------------------------------------------------------

    def test_tc31_all_cash_zero_returns_portfolio(self) -> None:
        """TC31: All-cash portfolio with zero returns across all assets."""
        p_weights = {"CASH": 1.0}
        b_weights = {"CASH": 1.0}
        p_returns = {"CASH": 0.0}
        b_returns = {"CASH": 0.0}

        result = self.attributor.decompose_single_period(
            portfolio_weights=p_weights,
            benchmark_weights=b_weights,
            asset_returns_local=p_returns,
            benchmark_returns_local=b_returns,
        )

        self.assertEqual(result.portfolio_return_base, 0.0)
        self.assertEqual(result.benchmark_return_base, 0.0)
        self.assertEqual(result.total_active_return, 0.0)
        self.assertEqual(result.allocation_effect, 0.0)
        self.assertEqual(result.selection_effect, 0.0)
        self.assertEqual(result.interaction_effect, 0.0)
        self.assertEqual(result.currency_effect, 0.0)
        self.assertTrue(result.is_identity_valid)

    def test_tc32_extreme_market_crash_returns(self) -> None:
        """TC32: Extreme crash returns (-50% market drop) and large currency devaluations."""
        p_weights = {"Equity": 0.80, "Bond": 0.20}
        b_weights = {"Equity": 0.50, "Bond": 0.50}
        p_returns = {"Equity": -0.50, "Bond": 0.05}
        b_returns = {"Equity": -0.45, "Bond": 0.04}
        c_returns = {"Equity": -0.20, "Bond": 0.00}
        h_ratios = {"Equity": 0.50, "Bond": 0.00}

        result = self.attributor.decompose_single_period(
            portfolio_weights=p_weights,
            benchmark_weights=b_weights,
            asset_returns_local=p_returns,
            benchmark_returns_local=b_returns,
            currency_returns=c_returns,
            hedge_ratios=h_ratios,
        )

        self.assertTrue(result.is_identity_valid)
        self.assertLess(result.arithmetic_identity_error, 1e-14)

    def test_tc33_single_segment_boundary_case(self) -> None:
        """TC33: Single segment universe (no allocation effect possible)."""
        p_weights = {"Global": 1.0}
        b_weights = {"Global": 1.0}
        p_returns = {"Global": 0.08}
        b_returns = {"Global": 0.05}

        result = self.attributor.decompose_single_period(
            portfolio_weights=p_weights,
            benchmark_weights=b_weights,
            asset_returns_local=p_returns,
            benchmark_returns_local=b_returns,
        )

        self.assertAlmostEqual(result.allocation_effect, 0.0, places=12)
        self.assertAlmostEqual(result.selection_effect, 0.03, places=12)
        self.assertAlmostEqual(result.interaction_effect, 0.0, places=12)
        self.assertAlmostEqual(result.total_active_return, 0.03, places=12)
        self.assertTrue(result.is_identity_valid)

    def test_tc34_hedge_ratio_out_of_bounds_clipping(self) -> None:
        """TC34: Hedge ratios outside [0.0, 1.0] are automatically clipped without errors."""
        p_weights = {"US": 1.0}
        b_weights = {"US": 1.0}
        p_returns = {"US": 0.0}
        b_returns = {"US": 0.0}
        c_returns = {"US": 0.05}
        h_ratios = {"US": 1.50}  # Over 1.0, should clip to 1.0
        f_prems = {"US": 0.01}

        result = self.attributor.decompose_single_period(
            portfolio_weights=p_weights,
            benchmark_weights=b_weights,
            asset_returns_local=p_returns,
            benchmark_returns_local=b_returns,
            currency_returns=c_returns,
            hedge_ratios=h_ratios,
            forward_premiums=f_prems,
        )

        # Hedged return with h=1.0: 0.01
        self.assertEqual(result.segments[0].hedge_ratio, 1.0)
        self.assertAlmostEqual(result.segments[0].currency_return_portfolio, 0.01, places=10)
        self.assertTrue(result.is_identity_valid)


if __name__ == "__main__":
    unittest.main()
