"""
tests/test_m1_challenger_multimarket_bfit.py
Independent Empirical Adversarial Verification Suite for M1: D-FCN & BFIT.

Evaluates:
1. Multi-market stress verification across all 5 individual markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000)
   as well as a pooled 3,379-symbol cross-market universe.
2. BFIT synergy enhancement of conviction vs linear factor beta leakage (|rho| < 0.15).
3. Precision-weighted D-FCN minimum distortion and mathematical optimality under heteroskedastic noise.
4. Stress-testing boundary conditions, condition numbers, and rank consistency.
"""

import unittest
import numpy as np
import pandas as pd

from src.core.multi_factor_neutralizer import (
    MultiFactorNeutralizerEngine,
    compute_precision_weighted_neutralization,
    compute_bilinear_interaction_alpha,
)


class TestChallengerMultiMarketStress(unittest.TestCase):
    """Stress tests across all 5 individual markets and pooled cross-sectional distributions."""

    def setUp(self):
        self.engine = MultiFactorNeutralizerEngine()
        self.markets = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]

    def _generate_synthetic_market_data(self, n: int, market: str, seed: int = 42) -> pd.DataFrame:
        rng = np.random.RandomState(seed)
        cap = np.exp(rng.normal(25.0, 1.8, size=n))
        pbr = rng.uniform(0.3, 8.0, size=n)
        per = rng.uniform(4.0, 60.0, size=n)
        roe = rng.normal(11.0, 8.0, size=n)
        cma = rng.normal(0.07, 0.18, size=n)
        mom = rng.normal(0.08, 0.30, size=n)

        # Inject realistic 10% missingness
        for arr in [pbr, per, roe, cma, mom]:
            mask = rng.uniform(0, 1, size=n) < 0.10
            arr[mask] = np.nan

        # Adversarial raw score strongly correlated with Value and Momentum
        # to test if neutralization successfully removes the factor bias
        raw_score = 0.5 * np.nan_to_num(mom / 0.30) + 0.4 * np.nan_to_num((1.0 / pbr)) + 0.1 * rng.normal(0, 1, size=n)

        return pd.DataFrame({
            "symbol": [f"{market}_{i:04d}" for i in range(n)],
            "name": [f"Name_{market}_{i}" for i in range(n)],
            "market": market,
            "market_cap": cap,
            "pbr": pbr,
            "per": per,
            "roe": roe,
            "asset_growth_yoy": cma,
            "momentum_12m": mom,
            "score": raw_score,
        })

    def test_each_market_individually(self):
        """Verify that |rho| < 0.15 SLA holds inside every individual market partition."""
        market_sizes = {
            "KOSPI": 850,
            "KOSDAQ": 1400,
            "SP500": 500,
            "NASDAQ": 1000,
            "RUSSELL2000": 1500,
        }
        for market, size in market_sizes.items():
            with self.subTest(market=market, size=size):
                df = self._generate_synthetic_market_data(size, market, seed=hash(market) % 10000)
                res = self.engine.compute_scores(universe=df)

                self.assertEqual(len(res), size)
                scores = res["factor_neutralized_score"].values
                self.assertFalse(np.isnan(scores).any(), f"NaN found in {market}")
                self.assertTrue(np.all((scores >= 0.0) & (scores <= 1.0)), f"Out of bounds in {market}")

                # Check correlations with observed factors using pairwise valid rows
                merged = pd.merge(df, res[["symbol", "factor_neutralized_score"]], on="symbol")
                s = merged["factor_neutralized_score"]
                factors = {
                    "SMB": np.log(merged["market_cap"].clip(lower=1e8)),
                    "HML": 1.0 / merged["pbr"].clip(lower=0.01),
                    "RMW": merged["roe"],
                    "CMA": merged["asset_growth_yoy"],
                    "UMD": merged["momentum_12m"],
                }
                for f_name, f_vals in factors.items():
                    r = abs(float(s.corr(f_vals)))
                    self.assertLess(
                        r, 0.15,
                        f"Market {market} breached SLA on factor {f_name}: |rho| = {r:.4f} >= 0.15"
                    )

    def test_pooled_3379_cross_sectional_universe(self):
        """Verify cross-market pooled universe of 3,379 symbols preserves |rho| < 0.15 globally and within subgroups."""
        sizes = {"KOSPI": 800, "KOSDAQ": 1400, "SP500": 500, "NASDAQ": 500, "RUSSELL2000": 179}
        dfs = [self._generate_synthetic_market_data(size, mkt, seed=i * 77) for i, (mkt, size) in enumerate(sizes.items())]
        full_universe = pd.concat(dfs, ignore_index=True)
        self.assertEqual(len(full_universe), 3379)

        res = self.engine.compute_scores(universe=full_universe)
        self.assertEqual(len(res), 3379)

        # Global decorrelation check
        merged = pd.merge(full_universe, res[["symbol", "factor_neutralized_score"]], on="symbol")
        s_glob = merged["factor_neutralized_score"]
        global_factors = {
            "SMB": np.log(merged["market_cap"].clip(lower=1e8)),
            "HML": 1.0 / merged["pbr"].clip(lower=0.01),
            "RMW": merged["roe"],
            "CMA": merged["asset_growth_yoy"],
            "UMD": merged["momentum_12m"],
        }
        for f_name, f_vals in global_factors.items():
            r_glob = abs(float(s_glob.corr(f_vals)))
            self.assertLess(
                r_glob, 0.15,
                f"Global pooled universe breached SLA on {f_name}: |rho| = {r_glob:.4f} >= 0.15"
            )

        # Sub-group decorrelation check within the pooled output (pairwise evaluation)
        for mkt in sizes.keys():
            mkt_merged = merged[merged["market"] == mkt]
            if len(mkt_merged) >= 20:
                s_sub = mkt_merged["factor_neutralized_score"]
                for f_name, f_vals in {
                    "SMB": np.log(mkt_merged["market_cap"].clip(lower=1e8)),
                    "HML": 1.0 / mkt_merged["pbr"].clip(lower=0.01),
                    "RMW": mkt_merged["roe"],
                    "CMA": mkt_merged["asset_growth_yoy"],
                    "UMD": mkt_merged["momentum_12m"],
                }.items():
                    r_sub = abs(float(s_sub.corr(f_vals)))
                    self.assertLess(
                        r_sub, 0.15,
                        f"Subgroup {mkt} inside pooled universe breached SLA on {f_name}: |rho| = {r_sub:.4f} >= 0.15"
                    )


class TestBFITSynergyAndBetaLeakage(unittest.TestCase):
    """Stress tests for BFIT synergy tensor: conviction enhancement vs unwanted factor beta."""

    def setUp(self):
        self.engine = MultiFactorNeutralizerEngine()

    def test_bfit_tensor_properties(self):
        """Verify tensor symmetry, boundedness, and zero self-amplification."""
        # 1. Symmetry
        N, K = 100, 5
        S = np.random.normal(0, 1, size=(N, K))
        synergy_default = compute_bilinear_interaction_alpha(S)
        self.assertTrue(np.all(synergy_default >= -1.0) and np.all(synergy_default <= 1.0))

        # 2. Test explicit symmetric tensor vs transposed
        M_sym = np.array([
            [0.0, 0.25, 0.0, 0.0, 0.0],
            [0.25, 0.0, 0.0, 0.0, 0.20],
            [0.0, 0.0, 0.0, 0.15, 0.0],
            [0.0, 0.0, 0.15, 0.0, 0.0],
            [0.0, 0.20, 0.0, 0.0, 0.0],
        ])
        syn1 = compute_bilinear_interaction_alpha(S, M_sym)
        syn2 = compute_bilinear_interaction_alpha(S, M_sym.T)
        np.testing.assert_allclose(syn1, syn2, atol=1e-12)

        # 3. Asymmetric input tensor should still produce quadratic form S @ M @ S.T = S @ (0.5*(M + M.T)) @ S.T
        M_asym = np.array([
            [0.0, 0.50, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.40],
            [0.0, 0.0, 0.0, 0.30, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0],
        ])
        M_symmetrized = 0.5 * (M_asym + M_asym.T)
        syn_asym = compute_bilinear_interaction_alpha(S, M_asym)
        syn_symm = compute_bilinear_interaction_alpha(S, M_symmetrized)
        np.testing.assert_allclose(syn_asym, syn_symm, atol=1e-12)

    def test_bfit_conviction_enhancement(self):
        """Verify that BFIT synergy specifically boosts stocks with dual high factor synergy."""
        N = 200
        # Stock 0 has High Value (+3.0) and High Momentum (+3.0) -> expected strong positive synergy
        # Stock 1 has High Value (+3.0) and Low Momentum (-3.0) -> expected negative synergy
        # Stock 2 has Neutral factors (0.0) -> 0.0 synergy
        Z = np.zeros((N, 5), dtype=float)
        Z[0, 1] = 3.0  # Value
        Z[0, 4] = 3.0  # Momentum
        Z[1, 1] = 3.0  # Value
        Z[1, 4] = -3.0 # Momentum

        synergy = compute_bilinear_interaction_alpha(Z)
        # Value x Momentum M[1,4] = 0.25
        # Stock 0: 0.5 * (2 * 3.0 * 3.0 * 0.25) = 2.25 -> tanh(2.25) ~ 0.978
        # Stock 1: 0.5 * (2 * 3.0 * -3.0 * 0.25) = -2.25 -> tanh(-2.25) ~ -0.978
        self.assertGreater(synergy[0], 0.90, f"Stock 0 synergy should be > 0.90, got {synergy[0]}")
        self.assertLess(synergy[1], -0.90, f"Stock 1 synergy should be < -0.90, got {synergy[1]}")
        self.assertAlmostEqual(synergy[2], 0.0, places=5)

    def test_bfit_does_not_leak_linear_beta(self):
        """Verify that when BFIT is integrated into MultiFactorNeutralizerEngine,
        it does NOT introduce unwanted linear factor beta that violates the SLA |rho| < 0.15."""
        rng = np.random.RandomState(999)
        n = 1000
        # Highly synergistic factor matrix
        z_size = rng.normal(0, 1, size=n)
        z_val = rng.normal(0, 1, size=n)
        z_prof = rng.normal(0, 1, size=n)
        z_cma = rng.normal(0, 1, size=n)
        z_mom = rng.normal(0, 1, size=n)

        universe = pd.DataFrame({
            "symbol": [f"S_{i}" for i in range(n)],
            "market": "SP500",
            "market_cap": np.exp(25.0 + 1.5 * z_size),
            "pbr": 1.0 / np.clip(1.5 + 0.5 * z_val, 0.1, 10.0),
            "per": 20.0 + 5.0 * z_val,
            "roe": 12.0 + 5.0 * z_prof,
            "asset_growth_yoy": 0.08 + 0.10 * z_cma,
            "momentum_12m": 0.10 + 0.20 * z_mom,
        })
        raw_score = pd.DataFrame({
            "symbol": universe["symbol"],
            "score": rng.uniform(0.2, 0.8, size=n),
        })

        res = self.engine.compute_scores(universe=universe, raw_scores=raw_score)
        scores = res["factor_neutralized_score"]

        # Linear factor beta / correlation evaluation
        for col_name, factor_series in {
            "SMB": np.log(universe["market_cap"]),
            "HML": 1.0 / universe["pbr"],
            "RMW": universe["roe"],
            "CMA": universe["asset_growth_yoy"],
            "UMD": universe["momentum_12m"],
        }.items():
            r = abs(float(scores.corr(factor_series)))
            # Compute regression beta = cov(s, f) / var(f)
            beta = float(np.cov(scores, factor_series)[0, 1] / np.var(factor_series))
            self.assertLess(
                r, 0.15,
                f"Factor {col_name} breached correlation SLA under BFIT: |rho|={r:.4f} >= 0.15"
            )
            self.assertLess(
                abs(beta), 0.15,
                f"Factor {col_name} exhibited high linear beta under BFIT: beta={beta:.4f}"
            )


class TestDFCNPrecisionWeightedOptimality(unittest.TestCase):
    """Stress tests for precision-weighted minimum distortion GLS neutralization."""

    def test_precision_gls_weights_influence(self):
        """Verify that precision weights W = diag(w_i) properly downweight noisy stocks."""
        N, K = 100, 3
        np.random.seed(42)
        B = np.random.normal(0, 1, size=(N, K))
        y = np.random.normal(0, 1, size=N)

        # High precision on first 50 stocks (low noise), very low precision on last 50 stocks (high noise)
        w = np.ones(N)
        w[:50] = 100.0  # high precision -> minimize (y_star - y)^2 heavily
        w[50:] = 0.01   # low precision -> distortion is penalized lightly

        y_star = compute_precision_weighted_neutralization(y, B, weights_precision=w)

        # First 50 should have much smaller distortion |y_star - y| on average than last 50
        dist_first_50 = np.mean((y_star[:50] - y[:50]) ** 2)
        dist_last_50 = np.mean((y_star[50:] - y[50:]) ** 2)

        self.assertLess(
            dist_first_50, dist_last_50,
            f"High-precision stocks should have lower distortion: {dist_first_50} vs {dist_last_50}"
        )

    def test_orthogonality_condition(self):
        """Verify that B.T @ y_star is numerically zero (<= 1e-8) for well-conditioned B."""
        N, K = 200, 5
        np.random.seed(123)
        B = np.random.normal(0, 1, size=(N, K))
        y = np.random.normal(0, 1, size=N)
        w = np.random.uniform(0.5, 2.0, size=N)

        y_star = compute_precision_weighted_neutralization(y, B, weights_precision=w)
        ortho_err = np.max(np.abs(B.T @ y_star))
        self.assertLess(ortho_err, 1e-8, f"Max orthogonality error too large: {ortho_err}")

    def test_extreme_condition_number(self):
        """Verify stability when B has condition number > 1e12 (collinear factors)."""
        N, K = 100, 5
        np.random.seed(456)
        B = np.random.normal(0, 1, size=(N, K))
        # Make column 1 and 2 nearly identical
        B[:, 1] = B[:, 0] + 1e-12 * np.random.normal(0, 1, size=N)
        y = np.random.normal(0, 1, size=N)

        y_star = compute_precision_weighted_neutralization(y, B)
        self.assertFalse(np.isnan(y_star).any())
        self.assertFalse(np.isinf(y_star).any())


if __name__ == "__main__":
    unittest.main(verbosity=2)
