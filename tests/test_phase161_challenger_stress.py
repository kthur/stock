"""
tests/test_phase161_challenger_stress.py
Empirical Challenger Stress Harness for Milestone 2: Dynamic Risk Budgeting & Multi-Regime Allocation Layer
(Phase 161, Features F785-F789, Release R163).

Adversarial Stress Test Suite:
- Challenge 1 (F785): Rényi entropy-regularized Kelly with extreme alphas (0.1, 0.5, 1.0, 2.0, 5.0),
  asserting non-negativity and simplex sum constraint under ill-conditioned and extreme inputs.
- Challenge 2 (F786): Factor beta neutralization across 1,000 random high-beta asset universes with
  gross leverage = 1.50x, asserting beta_port <= 1.000001 and concentration caps.
- Challenge 3 (F787): 6-Tier protective gating envelope under simultaneous extreme crisis triggers
  (OFI shock = -5.0, TSR = 1.25, HWM drawdown = -20%, mean correlation = 0.95), plus 64-combo envelope checks.
- Challenge 4 (F788): Top-150 mode preservation under rank-deficient sample covariance (N < 150, T < N),
  asserting condition number kappa <= 45.0, positive definiteness, and trace conservation.
"""

from __future__ import annotations

import math
import os
import sys
import unittest
import numpy as np
import pandas as pd

# Add repo roots to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.risk.dynamic_regime_leverage_allocator import (
    DynamicRegimeLeverageAllocator,
    WassersteinRobustKellyOptimizer,
    CorrelationBreakdownBrake,
)
from src.risk.portfolio_allocator import PortfolioAllocator
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator


class TestPhase161ChallengerStress(unittest.TestCase):
    """Adversarial stress harness for Phase 161 Quant Risk Architecture."""

    def setUp(self):
        np.random.seed(161)
        self.allocator = DynamicRegimeLeverageAllocator(
            max_bull_leverage=1.50,
            min_crisis_exposure=0.15,
            borrowing_spread_bps=60.0,
            hwm_dd_limit=-0.15,
            default_kappa=0.375,
            top_k_modes=150,
            lambda_entropy=0.001,
        )
        self.unified_allocator = UnifiedPortfolioAllocator(version=161)

    # =========================================================================
    # CHALLENGE 1 (F785): RÉNYI ENTROPY KELLY WITH EXTREME ALPHAS
    # =========================================================================

    def test_c1_f785_renyi_entropy_kelly_extreme_alphas(self):
        """C1 [F785]: Stress test Rényi entropy-regularized Kelly with extreme alphas (0.1, 0.5, 1.0, 2.0, 5.0)."""
        extreme_alphas = [0.1, 0.5, 1.0, 2.0, 5.0]
        rng = np.random.RandomState(42)

        for alpha_r in extreme_alphas:
            for trial in range(30):
                N = rng.randint(4, 35)
                # Generate ill-conditioned covariance matrix
                A = rng.randn(N, N)
                cov = A @ A.T + np.eye(N) * 1e-4
                # Expected returns
                mu = rng.uniform(0.01, 0.25, N)
                target_lev = float(rng.choice([1.0, 1.25, 1.50]))

                # 1. Test allocator.compute_renyi_regularized_kelly
                w1 = self.allocator.compute_renyi_regularized_kelly(
                    mu, cov, alpha_renyi=alpha_r, target_leverage=target_lev, lambda_entropy=0.02
                )
                self.assertEqual(len(w1), N)
                self.assertTrue(
                    np.all(w1 >= -1e-11),
                    f"Negative weight found in w1: min={np.min(w1)} for alpha_renyi={alpha_r}"
                )
                self.assertAlmostEqual(
                    float(np.sum(w1)),
                    target_lev,
                    places=4,
                    msg=f"Simplex sum mismatch in w1 for alpha_renyi={alpha_r}"
                )

                # 2. Test robust_kelly_optimizer.allocate_robust_weights directly
                w2 = self.allocator.robust_kelly_optimizer.allocate_robust_weights(
                    alpha=mu,
                    cov=cov,
                    epsilon=0.01,
                    lambda_entropy=0.02,
                    alpha_renyi=alpha_r,
                    target_leverage=target_lev,
                )
                self.assertEqual(len(w2), N)
                self.assertTrue(
                    np.all(w2 >= -1e-11),
                    f"Negative weight found in w2: min={np.min(w2)} for alpha_renyi={alpha_r}"
                )
                self.assertAlmostEqual(
                    float(np.sum(w2)),
                    target_lev,
                    places=4,
                    msg=f"Simplex sum mismatch in w2 for alpha_renyi={alpha_r}"
                )

    def test_c1_f785_renyi_entropy_all_negative_returns_collapse(self):
        """C1 [F785]: Extreme alpha stress test with all negative returns collapses to zero or cash."""
        extreme_alphas = [0.1, 0.5, 1.0, 2.0, 5.0]
        cov = np.eye(4) * 0.04
        mu_neg = np.array([-0.05, -0.02, -0.08, -0.01])

        for a in extreme_alphas:
            w = self.allocator.robust_kelly_optimizer.allocate_robust_weights(
                alpha=mu_neg, cov=cov, alpha_renyi=a, epsilon=0.02
            )
            self.assertAlmostEqual(float(np.sum(np.abs(w))), 0.0, places=6)

    # =========================================================================
    # CHALLENGE 2 (F786): 1,000 HIGH-BETA UNIVERSES AT 1.50X GROSS LEVERAGE
    # =========================================================================

    def test_c2_f786_portfolio_factor_beta_1000_high_beta_universes(self):
        """C2 [F786]: Verify portfolio factor beta <= 1.000001 across 1,000 random high-beta asset universes with gross leverage = 1.50x."""
        rng = np.random.RandomState(161)
        trials = 1000
        max_observed_beta = -1.0
        failures = []

        for i in range(trials):
            N = rng.randint(5, 75)
            # High-beta asset universe: beta drawn from [1.10, 3.50]
            asset_betas = rng.uniform(1.10, 3.50, N)

            # Generate random unconstrained weights with gross leverage = 1.50x
            raw_w = rng.uniform(0.01, 1.0, N)
            w_initial = (raw_w / np.sum(raw_w)) * 1.50

            # Apply factor beta clamping
            w_clamped = self.allocator.clamp_factor_beta(w_initial, asset_betas, max_beta=1.000001)
            port_beta = float(np.sum(w_clamped * asset_betas))

            if port_beta > 1.000001 + 1e-9:
                failures.append((i, N, port_beta))

            max_observed_beta = max(max_observed_beta, port_beta)

        self.assertEqual(len(failures), 0, f"Beta clamping failed on {len(failures)} universes: {failures[:5]}")
        self.assertLessEqual(max_observed_beta, 1.000001 + 1e-9)

    def test_c2_f786_concentration_box_caps_under_leverage(self):
        """C2 [F786]: Verify single-stock (0.05 * L) and single-sector (0.25 * L) concentration caps under 1.50x leverage."""
        L = 1.50
        max_stock_cap = 0.05 * L  # 0.075
        max_sector_cap = 0.25 * L  # 0.375

        weights = {f"SYM_{i}": 0.15 for i in range(10)}
        sectors = {f"SYM_{i}": ("TECH" if i < 6 else "FIN") for i in range(10)}

        capped = self.allocator.enforce_concentration_caps(weights, sectors, gross_leverage=L)

        for sym, w in capped.items():
            self.assertLessEqual(w, max_stock_cap + 1e-6)

        tech_sum = sum(w for sym, w in capped.items() if sectors[sym] == "TECH")
        fin_sum = sum(w for sym, w in capped.items() if sectors[sym] == "FIN")
        self.assertLessEqual(tech_sum, max_sector_cap + 1e-6)
        self.assertLessEqual(fin_sum, max_sector_cap + 1e-6)

    # =========================================================================
    # CHALLENGE 3 (F787): 6-TIER GATING WITH SIMULTANEOUS CRISIS TRIGGERS
    # =========================================================================

    def test_c3_f787_simultaneous_crisis_triggers_lower_envelope(self):
        """C3 [F787]: Stress test 6-tier gating with simultaneous crisis triggers
        (OFI shock = -5.0, TSR = 1.25, HWM drawdown = -20%, correlation = 0.95)."""
        res = self.allocator.evaluate_6tier_protective_gating(
            vix=55.0,
            tsr=1.25,
            drawdown=-0.20,
            mean_corr=0.95,
            ofi_shock=-5.0,
            regime="BULL_LOW_VOL",
        )

        # Strict lower envelope containment: must collapse to crisis floor 0.15
        self.assertAlmostEqual(res["allowed_leverage"], 0.15, places=5)
        self.assertTrue(res["tier1_crisis_gate_active"])
        self.assertTrue(res["tier2_vol_spike_active"])
        self.assertTrue(res["tier3_tsr_lock_active"])
        self.assertTrue(res["ofi_shock_gate_active"])
        self.assertTrue(res["tier4_drawdown_ratchet_active"])
        self.assertTrue(res["tier5_correlation_brake_active"])
        self.assertEqual(res["haircut_multiplier"], 0.70)
        self.assertEqual(len(res["active_tiers"]), 6)

    def test_c3_f787_combinatorial_64_state_envelope_containment(self):
        """C3 [F787]: Verify strict minimum envelope monotonicity across all 2^6 = 64 trigger states."""
        for t1 in (False, True):
            for t2 in (False, True):
                for t3 in (False, True):
                    for tofi in (False, True):
                        for t4 in (False, True):
                            for t5 in (False, True):
                                vix_val = 45.0 if t1 else (32.0 if t2 else 18.0)
                                tsr_val = 1.15 if t3 else 0.90
                                ofi_val = -3.5 if tofi else 0.5
                                dd_val = -0.16 if t4 else -0.02
                                corr_val = 0.92 if t5 else 0.40

                                r = self.allocator.evaluate_6tier_protective_gating(
                                    vix=vix_val,
                                    tsr=tsr_val,
                                    drawdown=dd_val,
                                    mean_corr=corr_val,
                                    ofi_shock=ofi_val,
                                    regime="BULL_LOW_VOL",
                                )

                                # Lower envelope calculation
                                exp_lev = 1.50
                                if t5:
                                    exp_lev = min(exp_lev, 0.70)
                                if t3:
                                    exp_lev = min(exp_lev, 0.50)
                                if tofi:
                                    exp_lev = min(exp_lev, 0.40)
                                if t2 or vix_val >= 30.0:
                                    exp_lev = min(exp_lev, 0.40)
                                if t4:
                                    exp_lev = min(exp_lev, 0.15)
                                if t1:
                                    exp_lev = min(exp_lev, 0.15)
                                exp_lev = max(0.15, exp_lev)

                                self.assertAlmostEqual(
                                    r["allowed_leverage"],
                                    exp_lev,
                                    places=5,
                                    msg=f"Envelope breach in state (t1={t1}, t2={t2}, t3={t3}, tofi={tofi}, t4={t4}, t5={t5})"
                                )

    # =========================================================================
    # CHALLENGE 4 (F788): TOP-150 MODE PRESERVATION UNDER RANK-DEFICIENT COVARIANCE
    # =========================================================================

    def test_c4_f788_top150_mode_preservation_rank_deficient_covariance(self):
        """C4 [F788]: Verify Top-150 mode preservation under rank-deficient sample covariance (N < 150, T < N)
        and confirm condition number kappa <= 45.0."""
        rng = np.random.RandomState(161)

        test_dimensions = [
            (25, 12),    # N=25 < 150, T=12 (rank <= 11)
            (60, 25),    # N=60 < 150, T=25 (rank <= 24)
            (120, 50),   # N=120 < 150, T=50 (rank <= 49)
            (149, 70),   # N=149 < 150, T=70 (rank <= 69)
            (180, 80),   # N=180 >= 150, T=80 (rank <= 79, top 150 modes requested)
        ]

        for N, T in test_dimensions:
            X = rng.normal(0, 0.02, (T, N))
            raw_cov = np.cov(X, rowvar=False)

            # Assert raw sample covariance is rank-deficient
            raw_rank = np.linalg.matrix_rank(raw_cov)
            self.assertLess(raw_rank, N, f"Raw covariance should be rank-deficient for N={N}, T={T}")

            # Denoise via Top-150 RMT
            cleaned_cov = self.allocator.denoise_covariance_nonlinear_rmt(
                raw_cov, top_modes=150, max_condition_number=45.0, t_obs=T
            )

            # 1. Output dimension matches
            self.assertEqual(cleaned_cov.shape, (N, N))

            # 2. Condition number strictly bounded by 45.0 + 1e-4
            evals = np.linalg.eigvalsh(cleaned_cov)
            cond = float(np.max(evals) / max(np.min(evals), 1e-12))
            self.assertLessEqual(
                cond,
                45.0 + 1e-4,
                f"Condition number {cond:.4f} exceeded 45.0 for N={N}, T={T}"
            )

            # 3. Strict positive definiteness: all eigenvalues > 1e-8
            min_eig = float(np.min(evals))
            self.assertGreater(
                min_eig,
                1e-8,
                f"Minimum eigenvalue {min_eig} <= 1e-8 for N={N}, T={T}"
            )

            # 4. Trace conservation: total variance preserved within 1%
            tr_raw = float(np.trace(raw_cov))
            tr_clean = float(np.trace(cleaned_cov))
            self.assertAlmostEqual(
                tr_raw,
                tr_clean,
                delta=0.01 * tr_raw,
                msg=f"Trace conservation breached for N={N}, T={T}: raw={tr_raw}, clean={tr_clean}"
            )

            # 5. Volatilities on diagonal strictly positive
            diags = np.diag(cleaned_cov)
            self.assertTrue(np.all(diags > 0.0), f"Non-positive diagonal volatility for N={N}, T={T}")


if __name__ == "__main__":
    unittest.main()
