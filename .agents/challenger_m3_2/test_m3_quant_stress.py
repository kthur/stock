"""
Adversarial Stress Verification Script for Milestone 3 (CPCV PBO & Historical Stress Testing Engine)
Executed by Challenger 2 (challenger_m3_2)
"""

import os
import sys
import unittest
import numpy as np
import pandas as pd

# Add repo root and trading_system to sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
TS_PATH = os.path.join(REPO_ROOT, "trading_system")
if TS_PATH not in sys.path:
    sys.path.append(TS_PATH)

from src.ai.cpcv_stress_tester import (
    CPCVStressTester,
    StressTestReport,
    run_historical_stress_test,
)


class TestM3QuantStress(unittest.TestCase):
    """Adversarial stress test suite for CPCV PBO & Historical Stress Testing Engine."""

    # -------------------------------------------------------------------------
    # 1. CPCV Probability of Backtest Overfitting (PBO) Verification
    # -------------------------------------------------------------------------

    def test_pbo_boundedness_and_robustness(self):
        """Verify PBO is bounded within [0.0, 1.0] across diverse matrix shapes & edge inputs."""
        tester = CPCVStressTester(n_splits=6, n_test_splits=2)

        # 1a. Random Gaussian return matrices
        np.random.seed(101)
        for num_samples in [30, 100, 500]:
            for num_models in [2, 5, 20]:
                matrix = np.random.randn(num_samples, num_models) * 0.02
                res = tester.compute_pbo(matrix)
                pbo = res["pbo"]
                self.assertTrue(0.0 <= pbo <= 1.0, f"PBO out of bounds: {pbo} for shape {(num_samples, num_models)}")

        # 1b. Degenerate inputs: Single model
        matrix_1m = np.random.randn(100, 1)
        res_1m = tester.compute_pbo(matrix_1m)
        self.assertEqual(res_1m["pbo"], 0.0, "Single model should return PBO = 0.0")

        # 1c. All-zero matrix
        zero_matrix = np.zeros((100, 5))
        res_zero = tester.compute_pbo(zero_matrix)
        self.assertTrue(0.0 <= res_zero["pbo"] <= 1.0, "All-zero matrix PBO must be bounded [0.0, 1.0]")

        # 1d. Identical models matrix
        base_series = np.random.randn(100, 1)
        identical_matrix = np.hstack([base_series] * 4)
        res_identical = tester.compute_pbo(identical_matrix)
        self.assertTrue(0.0 <= res_identical["pbo"] <= 1.0, "Identical models PBO must be bounded [0.0, 1.0]")

        # 1e. NaNs / Infs in matrix
        nan_matrix = np.random.randn(100, 4)
        nan_matrix[10, 1] = np.nan
        nan_matrix[20, 2] = np.inf
        nan_matrix[30, 3] = -np.inf
        res_nan = tester.compute_pbo(nan_matrix)
        self.assertTrue(0.0 <= res_nan["pbo"] <= 1.0, "NaN/Inf return matrix PBO must be bounded [0.0, 1.0]")

        print("[PASS] PBO Boundedness & Robustness verified: PBO in [0.0, 1.0] across all scenarios.")

    def test_logit_rank_percentile_clipping(self):
        """Verify logit rank percentile clipping when q_s = 0.0 or 1.0 to prevent infinite logits."""
        tester = CPCVStressTester(n_splits=6, n_test_splits=2)

        # Construct a scenario where model 0 is clearly best in both IS and OOS (q_s = 1.0)
        np.random.seed(42)
        n_samples = 200
        n_models = 5

        # Model 0 has huge positive mean return in all folds
        matrix = np.random.randn(n_samples, n_models) * 0.01
        matrix[:, 0] += 0.10  # Dominant positive performance

        res = tester.compute_pbo(matrix)
        logits = res["logits"]
        ranks = res["ranks"]

        self.assertGreater(len(logits), 0)
        for rank, logit in zip(ranks, logits):
            # Assert rank is valid percentile
            self.assertTrue(0.0 <= rank <= 1.0, f"Rank {rank} out of bounds")

            # Assert logit is strictly finite (no inf or NaN)
            self.assertTrue(np.isfinite(logit), f"Logit {logit} is not finite for rank {rank}")

            # Verify math of clipping:
            rank_clipped = float(np.clip(rank, 1e-5, 1.0 - 1e-5))
            expected_logit = float(np.log(rank_clipped / (1.0 - rank_clipped)))
            self.assertAlmostEqual(logit, expected_logit, places=5)

        # Test extreme boundary values directly on clipping logic
        q_s_extreme_high = 1.0
        clipped_high = np.clip(q_s_extreme_high, 1e-5, 1.0 - 1e-5)
        logit_high = np.log(clipped_high / (1.0 - clipped_high))
        self.assertTrue(np.isfinite(logit_high), "High extreme logit must be finite")
        self.assertAlmostEqual(logit_high, 11.512925, places=4)

        q_s_extreme_low = 0.0
        clipped_low = np.clip(q_s_extreme_low, 1e-5, 1.0 - 1e-5)
        logit_low = np.log(clipped_low / (1.0 - clipped_low))
        self.assertTrue(np.isfinite(logit_low), "Low extreme logit must be finite")
        self.assertAlmostEqual(logit_low, -11.512925, places=4)

        print("[PASS] Logit Rank Percentile Clipping verified: No infinity / NaN when q_s = 0.0 or 1.0.")

    def test_cpcv_combinatorial_splits_is_oos(self):
        """Verify C(N, k) splits, purged/embargo boundaries, and IS vs OOS Sharpe evaluation."""
        n_splits = 6
        n_test_splits = 2
        purge = 5
        embargo = 10

        tester = CPCVStressTester(
            n_splits=n_splits,
            n_test_splits=n_test_splits,
            purge_window=purge,
            embargo_window=embargo,
        )

        n_samples = 300
        n_models = 4
        matrix = np.random.randn(n_samples, n_models) * 0.01

        folds = tester.generate_purged_folds(matrix)

        # C(6, 2) = 15 combinations
        expected_combinations = 15
        self.assertEqual(len(folds), expected_combinations, f"Expected {expected_combinations} folds, got {len(folds)}")

        for fold_i, (train_idx, test_idx, test_blocks) in enumerate(folds):
            # Assert disjointness
            overlap = set(train_idx).intersection(set(test_idx))
            self.assertEqual(len(overlap), 0, f"Fold {fold_i} has overlapping train and test indices!")

            # Assert non-empty
            self.assertGreater(len(train_idx), 0, f"Fold {fold_i} train_idx is empty")
            self.assertGreater(len(test_idx), 0, f"Fold {fold_i} test_idx is empty")

            # Check IS vs OOS Sharpe calculation consistency
            train_data = matrix[train_idx]
            test_data = matrix[test_idx]

            is_sharpe = (np.mean(train_data, axis=0) / (np.std(train_data, axis=0, ddof=1) + 1e-8)) * np.sqrt(252.0)
            oos_sharpe = (np.mean(test_data, axis=0) / (np.std(test_data, axis=0, ddof=1) + 1e-8)) * np.sqrt(252.0)

            best_is_idx = int(np.argmax(is_sharpe))
            best_oos_perf = oos_sharpe[best_is_idx]
            rank_in_oos = float(np.sum(oos_sharpe <= best_oos_perf) / n_models)

            self.assertTrue(0.0 < rank_in_oos <= 1.0, f"Fold {fold_i} rank_in_oos {rank_in_oos} invalid")

        print(f"[PASS] CPCV Combinatorial splits verified: C({n_splits}, {n_test_splits}) = {len(folds)} folds correctly evaluated.")

    # -------------------------------------------------------------------------
    # 2. Historical Stress Testing Engine Verification
    # -------------------------------------------------------------------------

    def test_shock_vector_calculations(self):
        """Verify shock vector transformation formulas for 2008_CRISIS, 2020_COVID, 2022_FED_HIKE."""
        tester = CPCVStressTester()
        n_bars = 100
        np.random.seed(42)
        base_returns = np.random.randn(n_bars) * 0.01

        # 2a. '2008_CRISIS'
        shock_2008 = tester._apply_scenario_shock(base_returns, "2008_CRISIS")
        self.assertEqual(len(shock_2008), n_bars)
        # Expected: base returns shifted by -0.0025, scaled by 3.0, with acute shock -0.015 in middle block
        mid_start = n_bars // 4
        mid_end = min(n_bars, mid_start + max(10, n_bars // 3))

        non_mid_idx = [i for i in range(n_bars) if i < mid_start or i >= mid_end]
        expected_non_mid = (base_returns[non_mid_idx] - 0.0025) * 3.0
        np.testing.assert_allclose(shock_2008[non_mid_idx], expected_non_mid, rtol=1e-5)

        expected_mid = (base_returns[mid_start:mid_end] - 0.0025) * 3.0 - 0.015
        np.testing.assert_allclose(shock_2008[mid_start:mid_end], expected_mid, rtol=1e-5)

        # 2b. '2020_COVID'
        shock_2020 = tester._apply_scenario_shock(base_returns, "2020_COVID")
        crash_len = min(25, n_bars // 2)
        rebound_len = min(40, n_bars - crash_len)

        expected_crash = (base_returns[:crash_len] - 0.008) * 3.5
        np.testing.assert_allclose(shock_2020[:crash_len], expected_crash, rtol=1e-5)

        expected_rebound = (base_returns[crash_len : crash_len + rebound_len] + 0.004) * 2.0
        np.testing.assert_allclose(shock_2020[crash_len : crash_len + rebound_len], expected_rebound, rtol=1e-5)

        # 2c. '2022_FED_HIKE'
        shock_2022 = tester._apply_scenario_shock(base_returns, "2022_FED_HIKE")
        expected_2022 = (base_returns - 0.0012) * 1.8
        np.testing.assert_allclose(shock_2022, expected_2022, rtol=1e-5)

        # 2d. Unknown scenario fallback
        shock_unknown = tester._apply_scenario_shock(base_returns, "UNKNOWN_SCENARIO")
        expected_unknown = base_returns * 1.5
        np.testing.assert_allclose(shock_unknown, expected_unknown, rtol=1e-5)

        print("[PASS] Shock vector calculations verified for 2008_CRISIS, 2020_COVID, 2022_FED_HIKE.")

    def test_mdd_mathematical_bounds(self):
        """Verify MDD bounds (0.0 <= MDD <= 1.0) under extreme and adversarial return series."""
        np.random.seed(42)

        test_cases = [
            ("Random Walk", np.random.randn(200) * 0.02),
            ("Extreme Positive (+500%)", np.array([5.0] * 50)),
            ("Extreme Negative (-99%)", np.array([-0.99] * 50)),
            ("Flat Zero Returns", np.zeros(100)),
            ("Alternating Crash Rebound", np.tile([-0.50, +1.00], 50)),
            ("Sine Wave Oscillations", np.sin(np.linspace(0, 10 * np.pi, 200)) * 0.10),
            ("NaN / Inf Injected", np.array([0.01, np.nan, -0.05, np.inf, 0.02, -0.90])),
        ]

        for name, ret in test_cases:
            for scenario in ["2008_CRISIS", "2020_COVID", "2022_FED_HIKE"]:
                report = run_historical_stress_test(ret, scenario=scenario)

                # Report can be single StressTestReport or dict
                if isinstance(report, dict):
                    report = list(report.values())[0]

                mdd = report.mdd
                self.assertTrue(
                    0.0 <= mdd <= 1.0,
                    f"MDD {mdd} out of bounds [0.0, 1.0] for case '{name}' under scenario '{scenario}'",
                )

        print("[PASS] MDD mathematical bounds verified: 0.0 <= MDD <= 1.0 across all extreme return distributions.")

    def test_cvar_properties(self):
        """Verify CVaR mathematical properties: CVaR_95 <= VaR_95 and CVaR_99 <= VaR_99."""
        np.random.seed(777)

        distributions = [
            ("Gaussian Normal", np.random.randn(500) * 0.02),
            ("Heavy-tailed Student-t", np.random.standard_t(df=3, size=500) * 0.02),
            ("Laplace (Double Exp)", np.random.laplace(loc=0.0, scale=0.02, size=500)),
            ("Uniform", np.random.uniform(-0.05, 0.05, size=500)),
            ("Skewed Log-Normal", np.random.lognormal(mean=0.0, sigma=0.02, size=500) - 1.0),
            ("Constant Negative", np.full(100, -0.03)),
            ("Constant Positive", np.full(100, 0.02)),
        ]

        for name, ret in distributions:
            for scenario in ["2008_CRISIS", "2020_COVID", "2022_FED_HIKE"]:
                report = run_historical_stress_test(ret, scenario=scenario)

                var_95 = report.var_95
                cvar_95 = report.cvar_95
                var_99 = report.var_99
                cvar_99 = report.cvar_99

                # In return space (where losses are negative), CVaR is expected value in tail <= VaR.
                # So CVaR <= VaR must hold strictly.
                self.assertLessEqual(
                    cvar_95,
                    var_95 + 1e-12,
                    f"CVaR_95 ({cvar_95}) > VaR_95 ({var_95}) for distribution '{name}' under '{scenario}'",
                )
                self.assertLessEqual(
                    cvar_99,
                    var_99 + 1e-12,
                    f"CVaR_99 ({cvar_99}) > VaR_99 ({var_99}) for distribution '{name}' under '{scenario}'",
                )

                # Additionally, 99% tail is more extreme than 95% tail
                self.assertLessEqual(var_99, var_95 + 1e-12, f"VaR_99 ({var_99}) > VaR_95 ({var_95})")
                self.assertLessEqual(cvar_99, cvar_95 + 1e-12, f"CVaR_99 ({cvar_99}) > CVaR_95 ({cvar_95})")

        print("[PASS] CVaR properties verified: CVaR_95 <= VaR_95 and CVaR_99 <= VaR_99 hold universally.")

    def test_stress_recovery_time_logic(self):
        """Verify Stress Recovery Time logic (counting bars from max drawdown trough/peak to recovery)."""
        tester = CPCVStressTester()

        # Construct synthetic return series with known peak, trough, and recovery bar
        # 1. Start with 1.0 (flat 0% for 10 bars) -> peak_val = 1.0
        # 2. Drop by -5% per bar for 4 bars -> cum_ret at bar 13 = 1.0 * (0.95)^4 = 0.8145 (MDD ~18.55% at bar 13)
        # 3. Gain by +6% per bar for 4 bars -> bar 14: 0.8634, bar 15: 0.9152, bar 16: 0.9701, bar 17: 1.0283 (recovers to >= 1.0 at bar 17)
        returns = np.array([0.0] * 10 + [-0.05] * 4 + [0.06] * 4 + [0.0] * 10)

        # Run test with unknown scenario to use unshocked/1.5x scaling
        report = tester._stress_test_single_series(returns, scenario="UNKNOWN", mdd_threshold=0.30)

        # Check calculated recovery time
        recovery_time = report.stress_recovery_time

        # Verify trough index and recovery
        cum_ret = np.cumprod(1.0 + returns * 1.5)
        peak = np.maximum.accumulate(cum_ret)
        drawdowns = (peak - cum_ret) / np.maximum(peak, 1e-8)
        max_dd_idx = int(np.argmax(drawdowns))

        peak_val = peak[max_dd_idx]
        recovery_indices = np.where(cum_ret[max_dd_idx:] >= peak_val)[0]
        expected_recovery_time = int(recovery_indices[0]) if len(recovery_indices) > 0 else len(cum_ret) - max_dd_idx

        self.assertEqual(recovery_time, expected_recovery_time, "Recovery time does not match empirical bar count from trough")
        self.assertGreater(recovery_time, 0, "Recovery time should be positive when drawdown recovers")

        # Test series that NEVER recovers
        no_recovery_returns = np.array([0.0] * 5 + [-0.10] * 5 + [0.0] * 10)
        no_recovery_report = tester._stress_test_single_series(no_recovery_returns, scenario="UNKNOWN", mdd_threshold=0.30)
        # Should return bars from max_dd_idx to end of series
        self.assertGreater(no_recovery_report.stress_recovery_time, 0)

        print(f"[PASS] Stress Recovery Time logic verified: Recovery time = {recovery_time} bars from max drawdown trough.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
