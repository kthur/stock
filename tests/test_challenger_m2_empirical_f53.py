"""
Adversarial Verification & Stress Test Suite for Feature F53
Feature: Multivariate R-Vine Copula & Information Entropy Parity (IEP)
Target: trading_system/src/risk/unified_portfolio_allocator.py

Challenger: Challenger 1 (Milestone 2 Allocation & Execution Architecture)
Focus Areas:
1. Epistemic entropy U extremes (U = 1.0 vs U = 0.0) and convergence toward equal weighting (0.25).
2. Cascade contagion sensitivity: EVT-CVaR weight monotonic expansion vs Risk Parity collapse across Lambda_cascade in [0, 1].
3. Euler CCVaR safety-weighted headroom redistribution monotonicity: higher cascade exposure -> lower redistributed weight.
4. Numerical robustness under adversarial returns: all zeros, collinear columns, extreme crashes, rank-deficient covariance.
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator


class TestF53EmpiricalChallengerSuite:
    """Empirical adversarial test suite for Feature F53."""

    # =========================================================================
    # 1. EPISTEMIC ENTROPY U EXTREMES: U = 1.0 (MAX) VS U = 0.0 (ZERO)
    # =========================================================================

    def test_epistemic_entropy_convergence_to_equal_weighting(self):
        """
        Adversarial Test 1: Verify IEP behavior as epistemic entropy U varies from 0.0 to 1.0.
        When U = 1.0 (maximum uncertainty across regimes) and cascade contagion is benign,
        IEP should pull blend weights toward equal risk budgeting (0.25 for all 4 models).
        When U = 0.0 (certain regime), IEP adjustment is 0, preserving the regime prior.
        """
        allocator = UnifiedPortfolioAllocator()

        # Regime priors that are heavily skewed away from 0.25:
        # e.g., BULL_LOW_VOL: bl=0.65, herc=0.25, rp=0.10, cvar=0.00
        # If deterministic (U = 0.0):
        w_u0 = allocator.compute_information_theoretic_blend_weights(
            regime={"BULL_LOW_VOL": 1.0},
            rvine_cascade_index=0.0,
            version=8,
        )

        # Intermediate entropy: mix of 2 regimes
        w_u_mid = allocator.compute_information_theoretic_blend_weights(
            regime={"BULL_LOW_VOL": 0.5, "SIDEWAYS_LOW_VOL": 0.5},
            rvine_cascade_index=0.0,
            version=8,
        )

        # Maximum entropy across 6 regimes: U = 1.0
        regimes_6 = ["BULL_LOW_VOL", "BULL_HIGH_VOL", "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL", "BEAR_LOW_VOL", "BEAR_HIGH_VOL"]
        w_u1 = allocator.compute_information_theoretic_blend_weights(
            regime={r: 1.0 / 6 for r in regimes_6},
            rvine_cascade_index=0.0,
            version=8,
        )

        # Distance from equal weighting (0.25)
        dist_u0 = sum((w_u0[k] - 0.25) ** 2 for k in w_u0)
        dist_u_mid = sum((w_u_mid[k] - 0.25) ** 2 for k in w_u_mid)
        dist_u1 = sum((w_u1[k] - 0.25) ** 2 for k in w_u1)

        print(f"\n[IEP Entropy Test] dist_u0={dist_u0:.5f}, dist_u_mid={dist_u_mid:.5f}, dist_u1={dist_u1:.5f}")
        print(f"w_u0: {w_u0}")
        print(f"w_u_mid: {w_u_mid}")
        print(f"w_u1: {w_u1}")

        # Assertion: As entropy U increases, weight dispersion from 0.25 must strictly decrease
        assert dist_u1 < dist_u_mid < dist_u0, (
            f"Expected monotonic decrease in variance from 0.25 as U increases: {dist_u1} < {dist_u_mid} < {dist_u0}"
        )

    def test_epistemic_entropy_damping_under_extreme_cascade(self):
        """
        Adversarial Test 2: When cascade contagion is extreme (e.g. Lambda_cascade >= 0.67),
        contagion_damp = max(0, 1 - 1.5 * lam_casc) drops to 0.0.
        Systemic tail contagion MUST override epistemic uncertainty (IEP), so the portfolio
        does NOT revert to naive equal weighting during a systemic crash.
        """
        allocator = UnifiedPortfolioAllocator()
        regimes_6 = ["BULL_LOW_VOL", "BULL_HIGH_VOL", "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL", "BEAR_LOW_VOL", "BEAR_HIGH_VOL"]
        uniform_regime = {r: 1.0 / 6 for r in regimes_6}

        w_crash = allocator.compute_information_theoretic_blend_weights(
            regime=uniform_regime,
            rvine_cascade_index=0.80,
            version=8,
        )

        # Under extreme cascade contagion, CVaR must dominate, NOT equal weighting 0.25
        assert w_crash["cvar"] > 0.40, f"CVaR should dominate under extreme cascade, got {w_crash['cvar']}"
        assert w_crash["rp"] < 0.15, f"RP should collapse under extreme cascade, got {w_crash['rp']}"

    # =========================================================================
    # 2. CASCADE CONTAGION SENSITIVITY & MONOTONICITY ACROSS LAMBDA_CASCADE
    # =========================================================================

    def test_cascade_contagion_monotonicity_cvar_expansion_and_rp_collapse(self):
        """
        Adversarial Test 3: Sweep Lambda_cascade from 0.15 to 1.00 in steps of 0.05.
        Assert that:
        1. Above the deadband (Lambda_cascade >= 0.15), EVT-CVaR weight is monotonically non-decreasing.
        2. Above the deadband (Lambda_cascade >= 0.15), Risk Parity weight is monotonically non-increasing.
        3. At Lambda_cascade = 1.00, EVT-CVaR is the dominant risk model while RP is marginalized.
        """
        allocator = UnifiedPortfolioAllocator()
        regimes_to_test = ["SIDEWAYS_LOW_VOL", "BEAR_LOW_VOL", "BULL_HIGH_VOL"]

        for reg in regimes_to_test:
            cvar_weights = []
            rp_weights = []
            grid = np.linspace(0.15, 1.0, 18)

            for lam in grid:
                w = allocator.compute_information_theoretic_blend_weights(
                    regime=reg,
                    rvine_cascade_index=float(lam),
                    version=8,
                )
                cvar_weights.append(w["cvar"])
                rp_weights.append(w["rp"])

            # Check monotonicity above deadband
            for i in range(len(grid) - 1):
                assert cvar_weights[i + 1] >= cvar_weights[i] - 1e-4, (
                    f"Regime {reg}: CVaR weight not monotonically non-decreasing at lam={grid[i+1]:.2f}: "
                    f"{cvar_weights[i+1]} < {cvar_weights[i]}"
                )
                assert rp_weights[i + 1] <= rp_weights[i] + 1e-4, (
                    f"Regime {reg}: RP weight not monotonically non-increasing at lam={grid[i+1]:.2f}: "
                    f"{rp_weights[i+1]} > {rp_weights[i]}"
                )

            # At extreme cascade (lam = 1.0), CVaR must be higher than RP by at least 2.5x
            assert cvar_weights[-1] > 2.5 * rp_weights[-1], (
                f"Regime {reg}: CVaR ({cvar_weights[-1]}) should dominate RP ({rp_weights[-1]}) at lam=1.0"
            )

    def test_full_range_cascade_behavior_including_sub_deadband(self):
        """
        Adversarial Test 4: Examine sub-deadband behavior (0.0 <= Lambda_cascade <= 0.15).
        In this range, max(0, lam - 0.15) == 0, so delta_rvine has 0 impact.
        Verify that for any U (entropy), the weights remain well-behaved, bounded in [0, 1],
        and sum to 1.0000.
        """
        allocator = UnifiedPortfolioAllocator()
        sub_grid = np.linspace(0.0, 0.15, 10)

        for lam in sub_grid:
            w = allocator.compute_information_theoretic_blend_weights(
                regime={"BULL_LOW_VOL": 0.5, "BEAR_HIGH_VOL": 0.5},
                rvine_cascade_index=float(lam),
                version=8,
            )
            assert np.isclose(sum(w.values()), 1.0, atol=1e-5)
            for k, val in w.items():
                assert 0.0 <= val <= 1.0

    # =========================================================================
    # 3. EULER CCVAR SAFETY-WEIGHTED HEADROOM REDISTRIBUTION MONOTONICITY
    # =========================================================================

    def test_euler_ccvar_headroom_redistribution_monotonicity(self):
        """
        Adversarial Test 5: Verify that Euler CCVaR headroom redistribution in version >= 8
        is strictly monotonic with respect to asset cascade exposure:
        w_i propto w_i * headroom_i * exp(-1.5 * c_i^{cascade}).
        Given equal priors and equal headrooms, an asset with lower cascade contagion
        MUST receive strictly greater redistributed weight than an asset with higher cascade contagion.
        """
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.50)
        symbols = ["VOLATILE_BREACH", "SAFE_LOW_CASC", "MODERATE_CASC", "HIGH_CASC"]
        n = len(symbols)

        # Construct covariance where VOLATILE_BREACH causes a massive TRC violation
        # while the other 3 assets have identical symmetric diagonal variances and 0 cross-covariance
        cov = np.diag([0.40, 0.02, 0.02, 0.02])
        cov[0, 1:] = 0.08
        cov[1:, 0] = 0.08

        # Symmetrical predicted returns
        pred_returns = np.array([0.08, 0.04, 0.04, 0.04])
        # Returns history with neutral symmetric returns
        np.random.seed(42)
        rets = np.random.normal(0, 0.015, size=(40, n))
        rets[:, 0] = np.random.normal(0, 0.05, size=40)
        df_rets = pd.DataFrame(rets, columns=symbols)

        # Asset 1: c_casc = 0.05 (Safe)
        # Asset 2: c_casc = 0.35 (Moderate)
        # Asset 3: c_casc = 0.75 (High)
        cascade_vec = np.array([0.90, 0.05, 0.35, 0.75])

        w_opt = allocator.optimize_multi_model_blend(
            predicted_returns=pred_returns,
            returns_df=df_rets,
            cov_matrix=cov,
            symbols=symbols,
            asset_cascade_vector=cascade_vec,
            version=8,
        )

        print(f"\n[Euler CCVaR Redistribution] Target Weights: {dict(zip(symbols, w_opt))}")

        # Check strict monotonicity of redistributed weight among the non-violating assets
        # Low cascade > Moderate cascade > High cascade
        assert w_opt[1] > w_opt[2], f"Safe ({w_opt[1]}) should be > Moderate ({w_opt[2]})"
        assert w_opt[2] > w_opt[3], f"Moderate ({w_opt[2]}) should be > High ({w_opt[3]})"

        # Ratio test: ratio w[1]/w[2] should reflect exp(-1.5 * (0.05 - 0.35)) = exp(0.45) ~ 1.56
        # Allow tolerance due to baseline model weights and constraints
        assert w_opt[1] / w_opt[3] > 1.30, (
            f"Ratio of Safe to High cascade weight ({w_opt[1] / w_opt[3]}) must reflect safety premium"
        )

    # =========================================================================
    # 4. ADVERSARIAL AND DEGENERATE INPUT STRESS TESTS
    # =========================================================================

    def test_rvine_metrics_with_collinear_and_identical_returns(self):
        """
        Adversarial Test 6: Compute R-Vine metrics with identical/collinear columns.
        Kendall's tau will be 1.0 (or close).
        Verify no ZeroDivisionError, NaN, or Inf in Clayton theta inversion.
        """
        allocator = UnifiedPortfolioAllocator()
        t = 50
        col = np.linspace(-0.05, 0.05, t)
        # 4 identical columns
        returns_collinear = np.column_stack([col, col, col, col])

        res = allocator.compute_rvine_tail_cascade_metrics(returns_collinear)

        assert math.isfinite(res["lambda_cascade_aggregate"])
        assert 0.0 <= res["lambda_cascade_aggregate"] <= 1.0
        assert not np.isnan(res["asset_cascade_vector"]).any()
        assert not np.isnan(res["pairwise_lower_tail_matrix"]).any()

    def test_rvine_metrics_with_all_zero_returns(self):
        """
        Adversarial Test 7: Zero return matrix (stagnant market / holiday data).
        Std is 0. Verify fallback without crash.
        """
        allocator = UnifiedPortfolioAllocator()
        returns_zeros = np.zeros((30, 4))
        res = allocator.compute_rvine_tail_cascade_metrics(returns_zeros)

        assert res["lambda_cascade_aggregate"] == 0.0
        assert res["tree1_lower_tail_mean"] == 0.0
        assert (res["asset_cascade_vector"] == 0.0).all()

    def test_rvine_metrics_with_nan_and_inf_inputs(self):
        """
        Adversarial Test 8: Returns matrix poisoned with NaNs and Infs.
        Engine must cleanse via nan_to_num and produce bounded results.
        """
        allocator = UnifiedPortfolioAllocator()
        np.random.seed(99)
        r = np.random.normal(0, 0.02, size=(40, 3))
        r[5, 0] = np.nan
        r[10, 1] = np.inf
        r[15, 2] = -np.inf

        res = allocator.compute_rvine_tail_cascade_metrics(r)
        assert math.isfinite(res["lambda_cascade_aggregate"])
        assert not np.isnan(res["asset_cascade_vector"]).any()

    def test_version_gating_f53_vs_f49(self):
        """
        Adversarial Test 9: Verify that version=7 uses Archimedean Clayton/Gumbel
        while version=8 activates R-Vine and IEP.
        """
        allocator = UnifiedPortfolioAllocator()
        # High entropy regime
        reg = {"BULL_LOW_VOL": 0.25, "BULL_HIGH_VOL": 0.25, "BEAR_LOW_VOL": 0.25, "BEAR_HIGH_VOL": 0.25}

        w_v7 = allocator.compute_information_theoretic_blend_weights(
            regime=reg,
            rvine_cascade_index=0.40,
            copula_lower_tail=0.40,
            version=7,
        )

        w_v8 = allocator.compute_information_theoretic_blend_weights(
            regime=reg,
            rvine_cascade_index=0.40,
            copula_lower_tail=0.40,
            version=8,
        )

        # In version 8, R-Vine cascade shifts and IEP should result in distinct weights
        assert w_v7 != w_v8
        assert w_v8["cvar"] > w_v7["cvar"]
