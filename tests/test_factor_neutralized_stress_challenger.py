"""
tests/test_factor_neutralized_stress_challenger.py
Empirical Adversarial Stress Suite for MultiFactorNeutralizerEngine (Strategy 21).

Tests:
1. Extreme Factor Collinearity (r >= 0.9999, exact linear dependence, singular design matrix).
2. Extreme Missingness (95%, 98%, 99.9% missing fundamentals across 3,379 symbols).
3. Zero-Variance and Constant Inputs (all zero, all constant, mixed zero-variance factors).
4. Tiny Universes (N=1, 2, 3, 5, 6, 7) and asymmetric multi-market singletons.
5. Extreme Numerical Outliers (10^15 cap, negative PER/ROE, Infs, NaNs).
6. Hard SLA Gate: Strict |rho(f_k, score)| < 0.15 under adversarial target synthesis.
7. Interface, argument binding, fallback contracts, and schema integrity.
"""

import sys
import os
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trading_system.src.core.multi_factor_neutralizer import MultiFactorNeutralizerEngine


class TestMultiFactorNeutralizerStressChallenger(unittest.TestCase):

    def setUp(self):
        self.engine = MultiFactorNeutralizerEngine()

    def _make_base_universe(self, n=3379, seed=42):
        np.random.seed(seed)
        symbols = [f"SYM_{i:04d}" for i in range(n)]
        markets = np.random.choice(["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"], size=n)
        return pd.DataFrame({
            "symbol": symbols,
            "name": [f"Name_{s}" for s in symbols],
            "market": markets,
            "market_cap": np.exp(np.random.normal(25.0, 1.5, size=n)),
            "per": np.random.uniform(5.0, 50.0, size=n),
            "pbr": np.random.uniform(0.5, 5.0, size=n),
            "roe": np.random.normal(12.0, 6.0, size=n),
            "asset_growth_yoy": np.random.normal(0.08, 0.15, size=n),
            "momentum_12m": np.random.normal(0.10, 0.25, size=n),
        })

    # =========================================================================
    # 1. Extreme Collinearity & Linear Dependence Stress
    # =========================================================================

    def test_extreme_collinearity_r_09999(self):
        """Test with r >= 0.9999 pairwise correlation between all 5 factors."""
        n = 3379
        np.random.seed(101)
        base_latent = np.random.normal(0, 1, size=n)

        # All factors almost perfectly collinear
        cap = np.exp(25.0 + 1.5 * (base_latent + np.random.normal(0, 0.001, size=n)))
        per = 20.0 + 5.0 * (base_latent + np.random.normal(0, 0.001, size=n))
        pbr = 2.0 + 0.5 * (base_latent + np.random.normal(0, 0.001, size=n))
        roe = 10.0 + 2.0 * (base_latent + np.random.normal(0, 0.001, size=n))
        cma = 0.05 + 0.01 * (base_latent + np.random.normal(0, 0.001, size=n))
        mom = 0.10 + 0.05 * (base_latent + np.random.normal(0, 0.001, size=n))

        universe = pd.DataFrame({
            "symbol": [f"S_{i}" for i in range(n)],
            "market": np.random.choice(["KOSPI", "SP500"], size=n),
            "market_cap": cap,
            "per": per,
            "pbr": pbr,
            "roe": roe,
            "asset_growth_yoy": cma,
            "momentum_12m": mom,
        })

        raw_scores = pd.DataFrame({
            "symbol": universe["symbol"],
            "score": base_latent * 0.9 + np.random.normal(0, 0.1, size=n),
        })

        res = self.engine.compute_scores(universe=universe, raw_scores=raw_scores)
        self.assertEqual(len(res), n)
        self.assertFalse(res["factor_neutralized_score"].isna().any())

        # Check correlation SLA
        eval_df = pd.merge(universe, res[["symbol", "factor_neutralized_score"]], on="symbol")
        score = eval_df["factor_neutralized_score"]
        self.assertLess(abs(score.corr(np.log(eval_df["market_cap"]))), 0.15)
        self.assertLess(abs(score.corr(eval_df["roe"])), 0.15)
        self.assertLess(abs(score.corr(eval_df["asset_growth_yoy"])), 0.15)
        self.assertLess(abs(score.corr(eval_df["momentum_12m"])), 0.15)

    def test_exact_linear_dependence_singular_matrix(self):
        """Test with exact duplicate and linear combination factors (rank-deficient X)."""
        n = 500
        np.random.seed(102)
        base = np.random.normal(10, 2, size=n)

        universe = pd.DataFrame({
            "symbol": [f"S_{i}" for i in range(n)],
            "market": "KOSPI",
            "market_cap": np.exp(base),
            "per": base * 2.0,  # Exact linear
            "pbr": base * 0.5,  # Exact linear
            "roe": base * -1.5, # Exact linear
            "asset_growth_yoy": base * 0.1,
            "momentum_12m": base,
        })
        raw_scores = pd.DataFrame({
            "symbol": universe["symbol"],
            "score": base + np.random.normal(0, 0.5, size=n),
        })

        res = self.engine.compute_scores(universe=universe, raw_scores=raw_scores)
        self.assertEqual(len(res), n)
        self.assertFalse(res["factor_neutralized_score"].isna().any())
        self.assertTrue(np.all((res["factor_neutralized_score"] >= 0.0) & (res["factor_neutralized_score"] <= 1.0)))

    # =========================================================================
    # 2. Extreme Missing Data Stress
    # =========================================================================

    def test_95_percent_missing_fundamentals(self):
        """Test 95% missing fundamentals across 3,379 symbols."""
        universe = self._make_base_universe(n=3379, seed=201)
        # 95% missing in all fundamental columns
        mask = np.random.uniform(0, 1, size=3379) < 0.95
        for col in ["per", "pbr", "roe", "asset_growth_yoy", "momentum_12m"]:
            universe.loc[mask, col] = np.nan
        cap_mask = np.random.uniform(0, 1, size=3379) < 0.90
        universe.loc[cap_mask, "market_cap"] = np.nan

        raw_scores = pd.DataFrame({
            "symbol": universe["symbol"],
            "score": np.random.uniform(0, 1, size=3379),
        })

        res = self.engine.compute_scores(universe=universe, raw_scores=raw_scores)
        valid_count = res["factor_neutralized_score"].notna().sum()
        coverage_pct = (valid_count / 3379) * 100.0
        self.assertEqual(coverage_pct, 100.0, "Coverage must be 100% under 95% missingness")
        self.assertFalse(np.isinf(res["factor_neutralized_score"].values).any())

    def test_99_9_percent_missing_fundamentals(self):
        """Test 99.9% missing fundamentals (only 3 symbols have data out of 3,379)."""
        universe = self._make_base_universe(n=3379, seed=202)
        universe.iloc[3:, universe.columns.get_loc("market_cap"):] = np.nan

        raw_scores = pd.DataFrame({
            "symbol": universe["symbol"],
            "score": np.random.uniform(0, 1, size=3379),
        })

        res = self.engine.compute_scores(universe=universe, raw_scores=raw_scores)
        self.assertEqual(len(res), 3379)
        self.assertFalse(res["factor_neutralized_score"].isna().any())

    def test_entire_factor_column_100_percent_nan(self):
        """Test when entire factor columns (e.g. asset_growth_yoy, pbr) are 100% NaN."""
        universe = self._make_base_universe(n=1000, seed=203)
        universe["asset_growth_yoy"] = np.nan
        universe["pbr"] = np.nan
        universe["per"] = np.nan

        raw_scores = pd.DataFrame({
            "symbol": universe["symbol"],
            "score": np.random.uniform(0, 1, size=1000),
        })

        res = self.engine.compute_scores(universe=universe, raw_scores=raw_scores)
        self.assertEqual(len(res), 1000)
        self.assertFalse(res["factor_neutralized_score"].isna().any())

    # =========================================================================
    # 3. Constant and Zero-Variance Inputs
    # =========================================================================

    def test_all_zero_factors_and_all_zero_scores(self):
        """Test when all factors and raw scores are exactly 0.0."""
        n = 100
        universe = pd.DataFrame({
            "symbol": [f"SYM_{i}" for i in range(n)],
            "market": "KOSPI",
            "market_cap": 0.0,
            "per": 0.0,
            "pbr": 0.0,
            "roe": 0.0,
            "asset_growth_yoy": 0.0,
            "momentum_12m": 0.0,
            "score": 0.0,
        })

        res = self.engine.compute_scores(universe=universe)
        self.assertEqual(len(res), n)
        self.assertFalse(res["factor_neutralized_score"].isna().any())
        self.assertTrue((res["factor_neutralized_score"] == 0.5).all())

    def test_constant_non_zero_factors(self):
        """Test when all factors are constant non-zero numbers."""
        n = 100
        universe = pd.DataFrame({
            "symbol": [f"SYM_{i}" for i in range(n)],
            "market": "SP500",
            "market_cap": 1e10,
            "per": 15.0,
            "pbr": 1.5,
            "roe": 10.0,
            "asset_growth_yoy": 0.05,
            "momentum_12m": 0.12,
            "score": np.linspace(0.1, 0.9, n),
        })

        res = self.engine.compute_scores(universe=universe)
        self.assertEqual(len(res), n)
        self.assertFalse(res["factor_neutralized_score"].isna().any())
        self.assertTrue(np.all((res["factor_neutralized_score"] >= 0.0) & (res["factor_neutralized_score"] <= 1.0)))

    # =========================================================================
    # 4. Tiny Universes & Asymmetric Multi-Market Partitions
    # =========================================================================

    def test_single_element_universe_n_1(self):
        """Test N=1 single-element universe."""
        universe = pd.DataFrame({
            "symbol": ["SINGLE_SYM"],
            "market": ["KOSPI"],
            "market_cap": [1e9],
            "per": [10.0],
            "roe": [15.0],
            "asset_growth_yoy": [0.05],
            "momentum_12m": [0.2],
            "score": [0.75],
        })

        res = self.engine.compute_scores(universe=universe)
        self.assertEqual(len(res), 1)
        self.assertEqual(res.loc[0, "factor_neutralized_score"], 0.5)
        self.assertFalse(res.isna().any().any())

    def test_tiny_universes_n_2_to_7(self):
        """Test N=2, 3, 4, 5, 6, 7 universes across boundary conditions."""
        for n in [2, 3, 4, 5, 6, 7]:
            universe = self._make_base_universe(n=n, seed=400 + n)
            universe["market"] = "SP500"
            raw_scores = pd.DataFrame({
                "symbol": universe["symbol"],
                "score": np.linspace(0.1, 0.9, n),
            })
            res = self.engine.compute_scores(universe=universe, raw_scores=raw_scores)
            self.assertEqual(len(res), n)
            self.assertFalse(res["factor_neutralized_score"].isna().any())
            self.assertTrue(np.all((res["factor_neutralized_score"] >= 0.0) & (res["factor_neutralized_score"] <= 1.0)))

    def test_asymmetric_multi_market_singletons(self):
        """Test asymmetric multi-market where some markets have exactly 1 symbol."""
        symbols = [f"SYM_{i}" for i in range(100)]
        markets = ["KOSPI"] * 96 + ["SP500", "NASDAQ", "RUSSELL2000", "KOSDAQ"]
        universe = pd.DataFrame({
            "symbol": symbols,
            "market": markets,
            "market_cap": np.exp(np.random.normal(25.0, 1.0, size=100)),
            "per": np.random.uniform(5.0, 30.0, size=100),
            "roe": np.random.normal(10.0, 5.0, size=100),
            "asset_growth_yoy": np.random.normal(0.05, 0.1, size=100),
            "momentum_12m": np.random.normal(0.1, 0.2, size=100),
            "score": np.random.uniform(0, 1, size=100),
        })

        res = self.engine.compute_scores(universe=universe)
        self.assertEqual(len(res), 100)
        self.assertFalse(res["factor_neutralized_score"].isna().any())

    # =========================================================================
    # 5. Extreme Outliers and Malformed Data
    # =========================================================================

    def test_extreme_numerical_outliers(self):
        """Test extreme outliers: 10^18 cap, negative PER/ROE, infinite values."""
        n = 100
        universe = self._make_base_universe(n=n, seed=501)
        universe.loc[0, "market_cap"] = 1e18
        universe.loc[1, "market_cap"] = 1e-15
        universe.loc[2, "market_cap"] = -100.0
        universe.loc[3, "per"] = 1e12
        universe.loc[4, "per"] = -1e12
        universe.loc[5, "per"] = 0.00001
        universe.loc[6, "roe"] = -10000.0
        universe.loc[7, "roe"] = 10000.0
        universe.loc[8, "asset_growth_yoy"] = 1e6
        universe.loc[9, "asset_growth_yoy"] = -1e6

        # Infs
        universe.loc[10, "per"] = np.inf
        universe.loc[11, "roe"] = -np.inf

        raw_scores = pd.DataFrame({
            "symbol": universe["symbol"],
            "score": np.random.uniform(0, 1, size=n),
        })
        raw_scores.loc[0, "score"] = 1e9
        raw_scores.loc[1, "score"] = -1e9

        res = self.engine.compute_scores(universe=universe, raw_scores=raw_scores)
        self.assertEqual(len(res), n)
        self.assertFalse(res["factor_neutralized_score"].isna().any())
        self.assertFalse(np.isinf(res["factor_neutralized_score"].values).any())
        self.assertTrue(np.all((res["factor_neutralized_score"] >= 0.0) & (res["factor_neutralized_score"] <= 1.0)))

    # =========================================================================
    # 6. Monte Carlo Adversarial Target Synthesis (|rho| < 0.15 Gate)
    # =========================================================================

    def test_monte_carlo_adversarial_target_rho_sla(self):
        """Stress-test 30 independent adversarial scenarios with high factor correlation."""
        for seed in range(30):
            np.random.seed(seed + 1000)
            n = 1000
            universe = self._make_base_universe(n=n, seed=seed)

            # Adversarial target: strong non-linear and linear factor blend
            log_cap = np.log(universe["market_cap"].clip(lower=1e6))
            bp_val = 1.0 / universe["pbr"].clip(lower=0.01)
            prof = universe["roe"]
            inv = universe["asset_growth_yoy"]
            mom = universe["momentum_12m"]

            # Standardize components
            z_c = (log_cap - log_cap.mean()) / log_cap.std()
            z_v = (bp_val - bp_val.mean()) / bp_val.std()
            z_p = (prof - prof.mean()) / prof.std()
            z_i = (inv - inv.mean()) / inv.std()
            z_m = (mom - mom.mean()) / mom.std()

            # Synthetic heavily factor-contaminated score (rho ~ 0.85 with factors)
            w = np.random.uniform(-1, 1, size=5)
            w /= np.linalg.norm(w)
            synth_score = (w[0]*z_c + w[1]*z_v + w[2]*z_p + w[3]*z_i + w[4]*z_m) * 0.9 + np.random.normal(0, 0.2, size=n)

            raw_scores = pd.DataFrame({"symbol": universe["symbol"], "score": synth_score})
            res = self.engine.compute_scores(universe=universe, raw_scores=raw_scores)

            eval_df = pd.merge(universe, res[["symbol", "factor_neutralized_score"]], on="symbol").dropna()
            neut = eval_df["factor_neutralized_score"]

            corrs = [
                abs(neut.corr(np.log(eval_df["market_cap"].clip(lower=1e6)))),
                abs(neut.corr(1.0 / eval_df["pbr"].clip(lower=0.01))),
                abs(neut.corr(eval_df["roe"])),
                abs(neut.corr(eval_df["asset_growth_yoy"])),
                abs(neut.corr(eval_df["momentum_12m"])),
            ]
            max_rho = max(corrs)
            self.assertLess(
                max_rho, 0.15,
                f"Seed {seed} SLA violated: max |rho|={max_rho:.4f} >= 0.15"
            )

    # =========================================================================
    # 7. Bug A-3 Contract and Interface Variants
    # =========================================================================

    def test_bug_a3_contract_empty_factors_and_empty_scores(self):
        """Bug A-3: If no factors exist AND no explicit raw scores exist, return NaNs."""
        universe = pd.DataFrame({
            "symbol": ["005930", "000660"],
            "name": ["Samsung", "Hynix"],
            "market": ["KOSPI", "KOSPI"],
        })
        res = self.engine.compute_scores(universe=universe)
        self.assertEqual(len(res), 2)
        self.assertTrue(res["factor_neutralized_score"].isna().all())

    def test_prices_dict_input_and_momentum_fallback(self):
        """Test engine accepts prices_dict and successfully computes momentum fallback."""
        n_days = 260
        dates = pd.date_range("2025-01-01", periods=n_days)
        prices_map = {
            "SYM_A": pd.DataFrame({"Close": np.linspace(100, 200, n_days)}, index=dates),
            "SYM_B": pd.DataFrame({"Close": np.linspace(200, 100, n_days)}, index=dates),
            "SYM_C": pd.DataFrame({"Close": np.random.uniform(50, 60, n_days)}, index=dates),
        }
        res = self.engine.compute_scores(prices_dict=prices_map)
        self.assertEqual(len(res), 3)
        self.assertFalse(res["factor_neutralized_score"].isna().any())


if __name__ == "__main__":
    unittest.main()
