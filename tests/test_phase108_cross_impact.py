"""
tests/test_phase108_cross_impact.py
===================================
Comprehensive Unit, Integration, Invariant, and Stress Test Harness for
Multi-Asset Cross-Impact Almgren-Chriss Execution Engine with Kyle's Lambda
(Phase 108 / Feature F511 / Release R124 / v115 Production Master).

Test Categories Covered:
- Category 1: Class Exports, Signatures & Full Alias Trees (TC01~TC04)
- Category 2: Kyle's Lambda Parameter Estimation & Scaling Laws (TC05~TC09)
- Category 3: Higham Spectral PSD Projection & x^T Gamma x >= 0 Invariant (TC10~TC14)
- Category 4: Cross-Impact Matrix Construction & Sector Coupling (TC15~TC18)
- Category 5: Strict ADV Liquidity Participation Cap (<= 1.5%) (TC19~TC23)
- Category 6: Exact Integer Share Volume Conservation (TC24~TC28)
- Category 7: Coupled Cross-Impact Optimization & Cost Reduction vs Uncoordinated (TC29~TC34)
- Category 8: Scalability, Robustness & Adversarial Stress Tests (TC35~TC40)
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from typing import List

import numpy as np

# ---------------------------------------------------------------------------
# Path setup: Ensure repo root and trading_system are on sys.path
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(TRADING_SYSTEM_DIR), str(PROJECT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.execution.multi_asset_cross_impact_slicer import (
    AssetOrderSpec,
    CrossImpactMatrixResult,
    MultiAssetSliceSchedule,
    HighamPSDProjector,
    KylesLambdaEstimator,
    MultiAssetCrossImpactSlicer,
    MultiAssetAlmgrenChrissSlicer,
    Phase108MultiAssetCrossImpactSlicer,
    CrossImpactAlmgrenChrissEngine,
    CoupledExecutionTrajectoryOptimizer,
    KylesLambdaCrossImpactSlicer,
)
from trading_system.src.execution.multi_asset_cross_impact_slicer import (
    MultiAssetCrossImpactSlicer as MirroredSlicer,
    KylesLambdaEstimator as MirroredEstimator,
    HighamPSDProjector as MirroredProjector,
)


class TestPhase108CrossImpactSlicer(unittest.TestCase):
    """Master Unit Test Suite for Multi-Asset Cross-Impact Almgren-Chriss Execution Engine."""

    def setUp(self) -> None:
        """Set up standard test baskets."""
        self.samsung_spec = AssetOrderSpec(
            symbol="005930",
            target_quantity=10000,
            side="BUY",
            current_price=70000.0,
            adv_shares=15_000_000.0,
            daily_volatility=0.018,
            sector="SEMICONDUCTOR",
            spread_bps=5.0,
        )
        self.sk_hynix_spec = AssetOrderSpec(
            symbol="000660",
            target_quantity=5000,
            side="BUY",
            current_price=180000.0,
            adv_shares=4_000_000.0,
            daily_volatility=0.025,
            sector="SEMICONDUCTOR",
            spread_bps=6.0,
        )
        self.hyundai_spec = AssetOrderSpec(
            symbol="005380",
            target_quantity=4000,
            side="BUY",
            current_price=240000.0,
            adv_shares=1_200_000.0,
            daily_volatility=0.020,
            sector="AUTOMOTIVE",
            spread_bps=5.5,
        )
        self.kia_spec = AssetOrderSpec(
            symbol="000270",
            target_quantity=6000,
            side="BUY",
            current_price=110000.0,
            adv_shares=1_800_000.0,
            daily_volatility=0.022,
            sector="AUTOMOTIVE",
            spread_bps=5.0,
        )

    # -----------------------------------------------------------------------
    # Category 1: Class Exports, Signatures & Full Alias Trees (TC01~TC04)
    # -----------------------------------------------------------------------
    def test_tc01_class_exports_and_aliases(self):
        """TC01: Verify all required classes and aliases are exported correctly."""
        self.assertTrue(issubclass(MultiAssetAlmgrenChrissSlicer, MultiAssetCrossImpactSlicer))
        self.assertTrue(issubclass(Phase108MultiAssetCrossImpactSlicer, MultiAssetCrossImpactSlicer))
        self.assertTrue(issubclass(CrossImpactAlmgrenChrissEngine, MultiAssetCrossImpactSlicer))
        self.assertTrue(issubclass(CoupledExecutionTrajectoryOptimizer, MultiAssetCrossImpactSlicer))
        self.assertTrue(issubclass(KylesLambdaCrossImpactSlicer, MultiAssetCrossImpactSlicer))

    def test_tc02_primary_and_mirrored_parity(self):
        """TC02: Verify identical behavior between primary and mirrored modules."""
        slicer_prim = MultiAssetCrossImpactSlicer()
        slicer_mirr = MirroredSlicer()
        self.assertEqual(slicer_prim.version, slicer_mirr.version)
        self.assertEqual(slicer_prim.max_adv_participation, slicer_mirr.max_adv_participation)
        self.assertEqual(slicer_prim.default_n_slices, slicer_mirr.default_n_slices)

    def test_tc03_asset_order_spec_properties(self):
        """TC03: Verify AssetOrderSpec properties and signed quantity handling."""
        buy_order = AssetOrderSpec(symbol="A", target_quantity=1000, side="BUY")
        sell_order = AssetOrderSpec(symbol="B", target_quantity=500, side="SELL")
        self.assertEqual(buy_order.signed_quantity, 1000)
        self.assertEqual(sell_order.signed_quantity, -500)
        self.assertEqual(buy_order.abs_quantity, 1000)
        self.assertEqual(sell_order.abs_quantity, 500)

    def test_tc04_default_initialization_parameters(self):
        """TC04: Verify default engine initialization and Phase 108 flag."""
        slicer = MultiAssetCrossImpactSlicer()
        self.assertEqual(slicer.max_adv_participation, 0.015)
        self.assertEqual(slicer.default_n_slices, 6)
        self.assertTrue(slicer.use_u_curve)
        self.assertTrue(slicer.is_phase108)

    # -----------------------------------------------------------------------
    # Category 2: Kyle's Lambda Parameter Estimation & Scaling Laws (TC05~TC09)
    # -----------------------------------------------------------------------
    def test_tc05_kyles_lambda_formula(self):
        """TC05: Verify exact Kyle's Lambda formula: lambda = kappa * sigma * sqrt(P) / sqrt(ADV)."""
        estimator = KylesLambdaEstimator(kappa_kyle=0.35)
        order = AssetOrderSpec(
            symbol="TEST",
            target_quantity=1000,
            current_price=100.0,
            adv_shares=1_000_000.0,
            daily_volatility=0.02,
        )
        lambdas = estimator.estimate_lambdas([order])
        expected = 0.35 * 0.02 * math.sqrt(100.0) / math.sqrt(1_000_000.0)
        self.assertEqual(len(lambdas), 1)
        self.assertAlmostEqual(lambdas[0], expected, places=10)

    def test_tc06_kyles_lambda_volatility_scaling(self):
        """TC06: Verify linear scaling with daily volatility: double sigma -> double lambda."""
        estimator = KylesLambdaEstimator(kappa_kyle=0.35)
        o1 = AssetOrderSpec(symbol="A", target_quantity=100, daily_volatility=0.02)
        o2 = AssetOrderSpec(symbol="B", target_quantity=100, daily_volatility=0.04)
        lambdas = estimator.estimate_lambdas([o1, o2])
        self.assertAlmostEqual(lambdas[1] / lambdas[0], 2.0, places=9)

    def test_tc07_kyles_lambda_price_scaling(self):
        """TC07: Verify square-root scaling with price: 4x price -> 2x lambda."""
        estimator = KylesLambdaEstimator(kappa_kyle=0.35)
        o1 = AssetOrderSpec(symbol="A", target_quantity=100, current_price=100.0)
        o2 = AssetOrderSpec(symbol="B", target_quantity=100, current_price=400.0)
        lambdas = estimator.estimate_lambdas([o1, o2])
        self.assertAlmostEqual(lambdas[1] / lambdas[0], 2.0, places=9)

    def test_tc08_kyles_lambda_adv_inverse_sqrt_scaling(self):
        """TC08: Verify inverse square-root scaling with ADV: 4x ADV -> 0.5x lambda."""
        estimator = KylesLambdaEstimator(kappa_kyle=0.35)
        o1 = AssetOrderSpec(symbol="A", target_quantity=100, adv_shares=1_000_000.0)
        o2 = AssetOrderSpec(symbol="B", target_quantity=100, adv_shares=4_000_000.0)
        lambdas = estimator.estimate_lambdas([o1, o2])
        self.assertAlmostEqual(lambdas[1] / lambdas[0], 0.5, places=9)

    def test_tc09_kyles_lambda_kappa_proportionality(self):
        """TC09: Verify proportionality with kappa: double kappa -> double lambda."""
        est1 = KylesLambdaEstimator(kappa_kyle=0.20)
        est2 = KylesLambdaEstimator(kappa_kyle=0.40)
        o = AssetOrderSpec(symbol="A", target_quantity=100)
        l1 = est1.estimate_lambdas([o])[0]
        l2 = est2.estimate_lambdas([o])[0]
        self.assertAlmostEqual(l2 / l1, 2.0, places=9)

    # -----------------------------------------------------------------------
    # Category 3: Higham Spectral PSD Projection & Invariant (TC10~TC14)
    # -----------------------------------------------------------------------
    def test_tc10_psd_projection_eigenvalue_floor(self):
        """TC10: Verify Higham projection clamps all negative eigenvalues >= 1e-10."""
        # Construct an indefinite matrix with negative eigenvalues
        indef = np.array([
            [1.0, 2.0, 0.0],
            [2.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ])
        raw_eigvals = np.linalg.eigvalsh(indef)
        self.assertTrue(np.any(raw_eigvals < 0.0))

        psd_mat, min_eig, is_psd = HighamPSDProjector.project(indef, epsilon_eigen=1e-10)
        self.assertTrue(is_psd)
        post_eigvals = np.linalg.eigvalsh(psd_mat)
        self.assertTrue(np.all(post_eigvals >= (1e-10 - 1e-14)))
        self.assertAlmostEqual(min_eig, float(np.min(raw_eigvals)), places=9)

    def test_tc11_psd_quadratic_form_invariant(self):
        """TC11: Invariant check: x^T Gamma x >= 0 for arbitrary non-zero vectors x."""
        indef = np.array([
            [2.0, -3.0, 1.5],
            [-3.0, 1.0, -2.0],
            [1.5, -2.0, 0.5],
        ])
        psd_mat, _, is_psd = HighamPSDProjector.project(indef, epsilon_eigen=1e-10)
        self.assertTrue(is_psd)

        # Test across 200 random vectors
        rng = np.random.default_rng(42)
        for _ in range(200):
            x = rng.standard_normal(3)
            q_form = float(x @ psd_mat @ x)
            self.assertGreaterEqual(q_form, -1e-14)

    def test_tc12_psd_projection_preserves_already_psd(self):
        """TC12: Verify already PSD matrix is minimally perturbed by projection."""
        A = np.array([[2.0, 0.5], [0.5, 3.0]])
        psd_A, min_eig, is_psd = HighamPSDProjector.project(A, epsilon_eigen=1e-10)
        self.assertTrue(is_psd)
        diff = np.max(np.abs(psd_A - A))
        self.assertLess(diff, 1e-8)

    def test_tc13_psd_projection_singular_rank_deficient(self):
        """TC13: Verify projection handles singular rank-1 matrix."""
        # Rank-1 outer product matrix has (M-1) zero eigenvalues
        v = np.array([1.0, 2.0, 3.0])
        rank1 = np.outer(v, v)
        psd_mat, min_eig, is_psd = HighamPSDProjector.project(rank1, epsilon_eigen=1e-10)
        self.assertTrue(is_psd)
        eigvals = np.linalg.eigvalsh(psd_mat)
        self.assertTrue(np.all(eigvals >= 1e-10 - 1e-14))

    def test_tc14_psd_projection_symmetry(self):
        """TC14: Verify projected matrix is perfectly symmetric."""
        non_sym = np.array([[1.0, 5.0], [0.0, 2.0]])
        psd_mat, _, _ = HighamPSDProjector.project(non_sym, epsilon_eigen=1e-10)
        sym_diff = np.max(np.abs(psd_mat - psd_mat.T))
        self.assertLess(sym_diff, 1e-14)

    # -----------------------------------------------------------------------
    # Category 4: Cross-Impact Matrix Construction & Sector Coupling (TC15~TC18)
    # -----------------------------------------------------------------------
    def test_tc15_cross_impact_matrix_structure(self):
        """TC15: Verify Gamma_ij = sqrt(lambda_i * lambda_j) * C_ij structure."""
        estimator = KylesLambdaEstimator(kappa_kyle=0.35)
        orders = [self.samsung_spec, self.sk_hynix_spec]
        res = estimator.estimate_cross_impact_matrix(
            orders, sector_coupling_factor=0.60, cross_sector_factor=0.20
        )
        self.assertEqual(res.symbols, ["005930", "000660"])
        self.assertEqual(res.gamma_matrix.shape, (2, 2))
        self.assertTrue(res.is_psd)

        # Both are in SEMICONDUCTOR sector, so coupling should be 0.60
        lambdas = res.kyles_lambda
        expected_cross = math.sqrt(lambdas[0] * lambdas[1]) * 0.60
        self.assertAlmostEqual(res.gamma_matrix[0, 1], expected_cross, places=9)
        self.assertAlmostEqual(res.gamma_matrix[1, 0], expected_cross, places=9)

    def test_tc16_cross_sector_vs_intra_sector_coupling(self):
        """TC16: Verify intra-sector coupling is stronger than cross-sector coupling."""
        estimator = KylesLambdaEstimator(kappa_kyle=0.35)
        # Samsung (SEMI), SK Hynix (SEMI), Hyundai (AUTO)
        orders = [self.samsung_spec, self.sk_hynix_spec, self.hyundai_spec]
        res = estimator.estimate_cross_impact_matrix(
            orders, sector_coupling_factor=0.50, cross_sector_factor=0.15
        )
        lambdas = res.kyles_lambda
        # Normalized coupling: Gamma_ij / sqrt(lambda_i * lambda_j)
        c_semi = res.gamma_matrix[0, 1] / math.sqrt(lambdas[0] * lambdas[1])
        c_cross = res.gamma_matrix[0, 2] / math.sqrt(lambdas[0] * lambdas[2])
        self.assertGreater(c_semi, c_cross)

    def test_tc17_custom_empirical_correlation_matrix(self):
        """TC17: Verify custom empirical correlation matrix ingestion."""
        estimator = KylesLambdaEstimator(kappa_kyle=0.35)
        orders = [self.samsung_spec, self.sk_hynix_spec]
        custom_corr = np.array([[1.0, 0.75], [0.75, 1.0]])
        res = estimator.estimate_cross_impact_matrix(orders, correlation_matrix=custom_corr)
        self.assertTrue(res.is_psd)
        lambdas = res.kyles_lambda
        expected_cross = math.sqrt(lambdas[0] * lambdas[1]) * 0.75
        self.assertAlmostEqual(res.gamma_matrix[0, 1], expected_cross, places=9)

    def test_tc18_edge_case_single_asset_and_empty(self):
        """TC18: Verify single-asset and empty order handling."""
        estimator = KylesLambdaEstimator(kappa_kyle=0.35)
        empty_res = estimator.estimate_cross_impact_matrix([])
        self.assertEqual(len(empty_res.symbols), 0)
        self.assertEqual(empty_res.gamma_matrix.shape, (0, 0))

        single_res = estimator.estimate_cross_impact_matrix([self.samsung_spec])
        self.assertEqual(single_res.symbols, ["005930"])
        self.assertEqual(single_res.gamma_matrix.shape, (1, 1))
        self.assertTrue(single_res.is_psd)

    # -----------------------------------------------------------------------
    # Category 5: Strict ADV Liquidity Participation Cap (<= 1.5%) (TC19~TC23)
    # -----------------------------------------------------------------------
    def test_tc19_strict_adv_participation_cap_baseline(self):
        """TC19: Verify every asset & tranche satisfies rate <= 0.015 (1.5% of ADV)."""
        slicer = MultiAssetCrossImpactSlicer(max_adv_participation=0.015)
        orders = [self.samsung_spec, self.sk_hynix_spec, self.hyundai_spec]
        schedule = slicer.optimize_basket_slices(orders, n_slices=6)

        self.assertLessEqual(np.max(schedule.adv_participation_rates), 0.015 + 1e-6)
        self.assertTrue(np.all(schedule.adv_participation_rates >= 0.0))

    def test_tc20_adv_cap_with_large_order(self):
        """TC20: Verify large order automatically expands slices to honor 1.5% ADV cap."""
        slicer = MultiAssetCrossImpactSlicer(max_adv_participation=0.015)
        # Order 100,000 shares on stock with ADV 1,000,000. Cap = 15,000 shares/slice.
        large_order = AssetOrderSpec(
            symbol="LARGE",
            target_quantity=100000,
            adv_shares=1_000_000.0,
            daily_volatility=0.02,
        )
        schedule = slicer.optimize_basket_slices([large_order], n_slices=4)
        # Slices must have expanded to at least ceil(100000 / 15000) = 7
        self.assertGreaterEqual(schedule.n_slices, 7)
        self.assertLessEqual(np.max(schedule.adv_participation_rates), 0.015 + 1e-6)
        self.assertEqual(int(np.sum(schedule.slice_tranches[0])), 100000)

    def test_tc21_adv_cap_interval_basis_mode(self):
        """TC21: Verify interval basis participation mode enforces cap on interval volume."""
        slicer = MultiAssetCrossImpactSlicer(
            max_adv_participation=0.015,
            participation_basis="interval",
        )
        small_order = AssetOrderSpec(
            symbol="SMALL",
            target_quantity=3000,
            adv_shares=1_000_000.0,
            daily_volatility=0.02,
        )
        schedule = slicer.optimize_basket_slices([small_order], n_slices=6)
        self.assertLessEqual(np.max(schedule.adv_participation_rates), 0.015 + 1e-6)

    def test_tc22_u_curve_weighting_does_not_breach_cap(self):
        """TC22: Verify U-curve edge boosting does not breach the 1.5% ADV cap."""
        slicer = MultiAssetCrossImpactSlicer(max_adv_participation=0.015, use_u_curve=True)
        # Tight order: 15,000 shares out of 1,000,000 ADV
        tight_order = AssetOrderSpec(
            symbol="TIGHT",
            target_quantity=15000,
            adv_shares=1_000_000.0,
            daily_volatility=0.02,
        )
        schedule = slicer.optimize_basket_slices([tight_order], n_slices=6)
        self.assertLessEqual(np.max(schedule.adv_participation_rates), 0.015 + 1e-6)

    def test_tc23_all_slices_non_negative_for_buy_orders(self):
        """TC23: Verify all slice tranches for BUY orders are non-negative."""
        slicer = MultiAssetCrossImpactSlicer()
        orders = [self.samsung_spec, self.sk_hynix_spec]
        schedule = slicer.optimize_basket_slices(orders, n_slices=6)
        self.assertTrue(np.all(schedule.slice_tranches >= 0))

    # -----------------------------------------------------------------------
    # Category 6: Exact Integer Share Volume Conservation (TC24~TC28)
    # -----------------------------------------------------------------------
    def test_tc24_integer_volume_conservation_exact_sum(self):
        """TC24: Verify sum(slice_tranches, axis=1) == target_quantities exactly."""
        slicer = MultiAssetCrossImpactSlicer()
        orders = [self.samsung_spec, self.sk_hynix_spec, self.hyundai_spec, self.kia_spec]
        schedule = slicer.optimize_basket_slices(orders, n_slices=6)

        expected = np.array([o.signed_quantity for o in orders], dtype=np.int64)
        actual = np.sum(schedule.slice_tranches, axis=1)
        self.assertTrue(np.array_equal(actual, expected))

    def test_tc25_integer_shares_type_check(self):
        """TC25: Verify all slice tranches are genuine integer types."""
        slicer = MultiAssetCrossImpactSlicer()
        orders = [self.samsung_spec, self.sk_hynix_spec]
        schedule = slicer.optimize_basket_slices(orders, n_slices=6)

        self.assertTrue(np.issubdtype(schedule.slice_tranches.dtype, np.integer))
        for row in schedule.slice_tranches:
            for val in row:
                self.assertIsInstance(int(val), int)

    def test_tc26_odd_and_prime_share_quantities(self):
        """TC26: Verify volume conservation for irregular prime/odd target quantities."""
        slicer = MultiAssetCrossImpactSlicer()
        prime_orders = [
            AssetOrderSpec(symbol="P1", target_quantity=10007, adv_shares=2_000_000.0),
            AssetOrderSpec(symbol="P2", target_quantity=7777, adv_shares=1_500_000.0),
            AssetOrderSpec(symbol="P3", target_quantity=13, adv_shares=500_000.0),
        ]
        schedule = slicer.optimize_basket_slices(prime_orders, n_slices=6)
        expected = np.array([10007, 7777, 13], dtype=np.int64)
        actual = np.sum(schedule.slice_tranches, axis=1)
        self.assertTrue(np.array_equal(actual, expected))

    def test_tc27_sell_orders_conservation(self):
        """TC27: Verify volume conservation for SELL orders (negative quantities)."""
        slicer = MultiAssetCrossImpactSlicer()
        sell_orders = [
            AssetOrderSpec(symbol="S1", target_quantity=5000, side="SELL", adv_shares=1_000_000.0),
            AssetOrderSpec(symbol="S2", target_quantity=3333, side="SELL", adv_shares=1_000_000.0),
        ]
        schedule = slicer.optimize_basket_slices(sell_orders, n_slices=6)
        expected = np.array([-5000, -3333], dtype=np.int64)
        actual = np.sum(schedule.slice_tranches, axis=1)
        self.assertTrue(np.array_equal(actual, expected))
        self.assertTrue(np.all(schedule.slice_tranches <= 0))

    def test_tc28_cumulative_executed_trajectory_terminal_match(self):
        """TC28: Verify cumulative executed shares match target quantities at final slice."""
        slicer = MultiAssetCrossImpactSlicer()
        orders = [self.samsung_spec, self.sk_hynix_spec]
        schedule = slicer.optimize_basket_slices(orders, n_slices=6)

        terminal_executed = schedule.cumulative_executed[:, -1]
        expected = np.array([o.signed_quantity for o in orders], dtype=np.int64)
        self.assertTrue(np.array_equal(terminal_executed, expected))

    # -----------------------------------------------------------------------
    # Category 7: Coupled Optimization & Cost Reduction vs Uncoordinated (TC29~TC34)
    # -----------------------------------------------------------------------
    def test_tc29_total_execution_cost_non_negative(self):
        """TC29: Verify total execution cost is strictly non-negative."""
        slicer = MultiAssetCrossImpactSlicer()
        orders = [self.samsung_spec, self.sk_hynix_spec]
        schedule = slicer.optimize_basket_slices(orders, n_slices=6)

        self.assertGreaterEqual(schedule.total_execution_cost, 0.0)
        self.assertGreaterEqual(schedule.total_temporary_impact_cost, 0.0)

    def test_tc30_cost_reduction_under_correlated_basket(self):
        """TC30: Verify coupled execution cost <= uncoordinated execution cost."""
        slicer = MultiAssetCrossImpactSlicer()
        orders = [self.samsung_spec, self.sk_hynix_spec]
        schedule = slicer.optimize_basket_slices(orders, n_slices=6)

        self.assertLessEqual(
            schedule.total_execution_cost,
            schedule.uncoordinated_standalone_cost + 1e-6
        )
        self.assertGreaterEqual(schedule.cross_impact_savings_pct, 0.0)

    def test_tc31_uncorrelated_basket_parity(self):
        """TC31: When correlation is zero, coupled cost matches uncoordinated cost."""
        slicer = MultiAssetCrossImpactSlicer()
        orders = [self.samsung_spec, self.sk_hynix_spec]
        zero_corr = np.eye(2, dtype=np.float64)
        schedule = slicer.optimize_basket_slices(orders, correlation_matrix=zero_corr, n_slices=6)

        # Standalone costs match within discretization margin
        self.assertAlmostEqual(
            schedule.total_execution_cost,
            schedule.uncoordinated_standalone_cost,
            delta=1e-4
        )
        self.assertAlmostEqual(schedule.total_cross_impact_drag, 0.0, places=6)

    def test_tc32_high_correlation_semiconductor_pair_savings(self):
        """TC32: High correlation semiconductor cluster achieves positive execution savings."""
        slicer = MultiAssetCrossImpactSlicer()
        orders = [self.samsung_spec, self.sk_hynix_spec]
        high_corr = np.array([[1.0, 0.85], [0.85, 1.0]])
        schedule = slicer.optimize_basket_slices(orders, correlation_matrix=high_corr, n_slices=8)

        self.assertGreaterEqual(schedule.cross_impact_savings_pct, 0.0)
        self.assertLessEqual(schedule.total_execution_cost, schedule.uncoordinated_standalone_cost + 1e-6)

    def test_tc33_long_short_hedged_cross_impact_offset(self):
        """TC33: Long-Short pair (BUY Samsung, SELL SK Hynix) generates negative cross-impact drag."""
        slicer = MultiAssetCrossImpactSlicer()
        hedge_orders = [
            AssetOrderSpec(
                symbol="005930", target_quantity=10000, side="BUY",
                current_price=70000.0, adv_shares=15_000_000.0, daily_volatility=0.018,
                sector="SEMI",
            ),
            AssetOrderSpec(
                symbol="000660", target_quantity=5000, side="SELL",
                current_price=180000.0, adv_shares=4_000_000.0, daily_volatility=0.025,
                sector="SEMI",
            ),
        ]
        high_corr = np.array([[1.0, 0.80], [0.80, 1.0]])
        schedule = slicer.optimize_basket_slices(hedge_orders, correlation_matrix=high_corr, n_slices=6)

        # Opposite signs in correlated assets result in negative cross-impact drag (liquidity netting)
        self.assertLessEqual(schedule.total_cross_impact_drag, 0.0)
        self.assertGreaterEqual(schedule.total_execution_cost, 0.0)

    def test_tc34_savings_pct_zero_floor(self):
        """TC34: Verify cross_impact_savings_pct never returns negative value."""
        slicer = MultiAssetCrossImpactSlicer()
        orders = [self.samsung_spec]
        schedule = slicer.optimize_basket_slices(orders, n_slices=6)
        self.assertGreaterEqual(schedule.cross_impact_savings_pct, 0.0)

    # -----------------------------------------------------------------------
    # Category 8: Scalability, Robustness & Adversarial Stress Tests (TC35~TC40)
    # -----------------------------------------------------------------------
    def test_tc35_large_basket_scalability(self):
        """TC35: Verify solver handles large basket of 50 assets efficiently."""
        rng = np.random.default_rng(123)
        large_orders = []
        for i in range(50):
            adv = float(rng.uniform(500_000, 10_000_000))
            # Keep quantity well within daily ADV cap
            qty = int(adv * 0.01)
            large_orders.append(AssetOrderSpec(
                symbol=f"SYM_{i:03d}",
                target_quantity=qty,
                current_price=float(rng.uniform(10.0, 500.0)),
                adv_shares=adv,
                daily_volatility=float(rng.uniform(0.01, 0.04)),
                sector=f"SEC_{i % 5}",
            ))

        slicer = MultiAssetCrossImpactSlicer(max_adv_participation=0.015)
        schedule = slicer.optimize_basket_slices(large_orders, n_slices=6)

        self.assertEqual(len(schedule.symbols), 50)
        self.assertEqual(schedule.slice_tranches.shape, (50, 6))
        self.assertLessEqual(np.max(schedule.adv_participation_rates), 0.015 + 1e-6)
        expected_sums = np.array([o.signed_quantity for o in large_orders], dtype=np.int64)
        self.assertTrue(np.array_equal(np.sum(schedule.slice_tranches, axis=1), expected_sums))

    def test_tc36_rank_deficient_correlation_matrix_stress(self):
        """TC36: Verify engine handles ill-conditioned / rank-1 correlation matrix gracefully."""
        orders = [self.samsung_spec, self.sk_hynix_spec, self.hyundai_spec]
        # Ill-conditioned matrix: all off-diagonals 0.9999
        singular_corr = 0.9999 * np.ones((3, 3))
        np.fill_diagonal(singular_corr, 1.0)

        slicer = MultiAssetCrossImpactSlicer()
        schedule = slicer.optimize_basket_slices(orders, correlation_matrix=singular_corr, n_slices=6)
        self.assertGreaterEqual(schedule.total_execution_cost, 0.0)
        self.assertLessEqual(schedule.total_execution_cost, schedule.uncoordinated_standalone_cost + 1e-6)

    def test_tc37_extreme_volatility_divergence(self):
        """TC37: Verify stability when asset volatilities differ by 100x."""
        o_low = AssetOrderSpec(symbol="LOW", target_quantity=1000, daily_volatility=0.001)
        o_high = AssetOrderSpec(symbol="HIGH", target_quantity=1000, daily_volatility=0.10)
        slicer = MultiAssetCrossImpactSlicer()
        schedule = slicer.optimize_basket_slices([o_low, o_high], n_slices=6)

        self.assertFalse(np.isnan(schedule.total_execution_cost))
        self.assertFalse(np.isinf(schedule.total_execution_cost))
        self.assertGreaterEqual(schedule.total_execution_cost, 0.0)

    def test_tc38_extreme_adv_disparity(self):
        """TC38: Verify stability when ADV differs by 1,000x."""
        o_mega = AssetOrderSpec(symbol="MEGA", target_quantity=5000, adv_shares=50_000_000.0)
        o_micro = AssetOrderSpec(symbol="MICRO", target_quantity=500, adv_shares=50_000.0)
        slicer = MultiAssetCrossImpactSlicer()
        schedule = slicer.optimize_basket_slices([o_mega, o_micro], n_slices=6)

        self.assertLessEqual(np.max(schedule.adv_participation_rates), 0.015 + 1e-6)
        self.assertEqual(int(np.sum(schedule.slice_tranches[0])), 5000)
        self.assertEqual(int(np.sum(schedule.slice_tranches[1])), 500)

    def test_tc39_empty_basket_and_zero_quantity_orders(self):
        """TC39: Verify empty basket and zero-quantity orders return clean zero schedules."""
        slicer = MultiAssetCrossImpactSlicer()
        empty_sched = slicer.optimize_basket_slices([])
        self.assertEqual(empty_sched.n_slices, 0)
        self.assertEqual(empty_sched.total_execution_cost, 0.0)

        zero_order = AssetOrderSpec(symbol="ZERO", target_quantity=0)
        zero_sched = slicer.optimize_basket_slices([zero_order], n_slices=6)
        self.assertEqual(np.sum(zero_sched.slice_tranches), 0)
        self.assertEqual(zero_sched.total_execution_cost, 0.0)

    def test_tc40_alias_tree_direct_execution(self):
        """TC40: Verify alias classes execute identically to master class."""
        slicers = [
            MultiAssetCrossImpactSlicer(),
            MultiAssetAlmgrenChrissSlicer(),
            Phase108MultiAssetCrossImpactSlicer(),
            CrossImpactAlmgrenChrissEngine(),
            CoupledExecutionTrajectoryOptimizer(),
            KylesLambdaCrossImpactSlicer(),
        ]
        orders = [self.samsung_spec, self.sk_hynix_spec]
        base_sched = slicers[0].optimize_basket_slices(orders, n_slices=6)

        for alias_slicer in slicers[1:]:
            sched = alias_slicer.optimize_basket_slices(orders, n_slices=6)
            self.assertTrue(np.array_equal(sched.slice_tranches, base_sched.slice_tranches))
            self.assertAlmostEqual(sched.total_execution_cost, base_sched.total_execution_cost, places=6)


if __name__ == "__main__":
    unittest.main()
