"""
tests/test_challenger_m1_2_empirical.py -- Challenger M1-2 Empirical Verification Suite

Empirical Stress Testing for Milestone 1:
1. Complete 3,379 symbol execution latency SLA (< 50ms mean / median) across 100 benchmark trials under various missingness profiles.
2. Rank correlation preservation (Spearman rho >= 0.65) across 50 Monte Carlo universe simulations.
3. Factor correlation SLA gate (|rho| < 0.15) across all 5 Fama-French factors.
4. End-to-end integration and compatibility with EnsembleScoringEngine and run_pipeline.py.
"""

import os
import sys
import time
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trading_system.src.core.multi_factor_neutralizer import MultiFactorNeutralizerEngine
from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine


class TestChallengerM1_2Empirical(unittest.TestCase):

    def setUp(self):
        self.engine = MultiFactorNeutralizerEngine()
        self.ensemble = EnsembleScoringEngine()

    def _generate_synthetic_universe(
        self,
        n_symbols: int = 3379,
        factor_loading: float = 0.50,
        missing_rate: float = 0.0,
        seed: int = 42,
    ) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
        """Generate synthetic multi-market universe with known factor and idiosyncratic components."""
        rng = np.random.default_rng(seed)
        symbols = [f"SYM_{i:04d}" for i in range(n_symbols)]
        markets = rng.choice(['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000'], size=n_symbols)

        # 5 Fama-French factors
        size_raw = np.exp(rng.normal(25.0, 1.5, size=n_symbols))
        per_raw = rng.choice([1.0, -1.0], size=n_symbols, p=[0.85, 0.15]) * rng.uniform(5.0, 60.0, size=n_symbols)
        ep_yield = np.where(per_raw > 0, 1.0 / per_raw, -1.0 / np.abs(per_raw))
        roe_raw = rng.normal(12.0, 8.0, size=n_symbols)
        cma_raw = rng.normal(0.08, 0.15, size=n_symbols)
        mom_raw = rng.normal(0.10, 0.25, size=n_symbols)

        # Normalize factors
        z_size = (np.log(size_raw) - np.mean(np.log(size_raw))) / (np.std(np.log(size_raw)) + 1e-8)
        z_val = (ep_yield - np.mean(ep_yield)) / (np.std(ep_yield) + 1e-8)
        z_prof = (roe_raw - np.mean(roe_raw)) / (np.std(roe_raw) + 1e-8)
        z_cma = (cma_raw - np.mean(cma_raw)) / (np.std(cma_raw) + 1e-8)
        z_mom = (mom_raw - np.mean(mom_raw)) / (np.std(mom_raw) + 1e-8)

        factor_composite = (0.4 * z_size + 0.3 * z_val + 0.3 * z_prof + 0.2 * z_cma + 0.5 * z_mom)
        factor_composite /= np.std(factor_composite) + 1e-8

        # Pure idiosyncratic alpha
        pure_alpha = rng.normal(0, 1, size=n_symbols)
        raw_latent = factor_loading * factor_composite + np.sqrt(max(0.0, 1.0 - factor_loading**2)) * pure_alpha
        raw_score = 1.0 / (1.0 + np.exp(-raw_latent))

        universe_df = pd.DataFrame({
            'symbol': symbols,
            'name': [f"Name_{s}" for s in symbols],
            'market': markets,
            'market_cap': size_raw,
            'per': per_raw,
            'roe': roe_raw,
            'asset_growth_yoy': cma_raw,
            'momentum_12m': mom_raw,
        })

        raw_scores_df = pd.DataFrame({
            'symbol': symbols,
            'score': raw_score,
        })

        if missing_rate > 0.0:
            for col in ['per', 'roe', 'asset_growth_yoy', 'momentum_12m']:
                mask = rng.uniform(0, 1, size=n_symbols) < missing_rate
                universe_df.loc[mask, col] = np.nan
            cap_mask = rng.uniform(0, 1, size=n_symbols) < (missing_rate * 0.5)
            universe_df.loc[cap_mask, 'market_cap'] = np.nan

        return universe_df, raw_scores_df, pure_alpha

    # =========================================================================
    # 1. Empirical Latency Benchmark across 3,379 symbols (< 50ms)
    # =========================================================================

    def test_empirical_latency_distribution_3379_symbols(self):
        """Execute 100 trials on 3,379 symbols and measure latency distribution."""
        universe_df, raw_scores_df, _ = self._generate_synthetic_universe(n_symbols=3379, factor_loading=0.60)

        # Warmup
        for _ in range(5):
            _ = self.engine.compute_scores(universe=universe_df, raw_scores=raw_scores_df)

        n_trials = 100
        latencies_ms = []

        for _ in range(n_trials):
            t0 = time.perf_counter()
            res = self.engine.compute_scores(universe=universe_df, raw_scores=raw_scores_df)
            t1 = time.perf_counter()
            latencies_ms.append((t1 - t0) * 1000.0)

        latencies = np.array(latencies_ms)
        mean_lat = np.mean(latencies)
        p50_lat = np.median(latencies)
        p95_lat = np.percentile(latencies, 95)
        p99_lat = np.percentile(latencies, 99)
        max_lat = np.max(latencies)

        print("\n[LATENCY BENCHMARK -- 3,379 Symbols (100 trials)]")
        print(f"  Mean:   {mean_lat:.2f} ms")
        print(f"  Median: {p50_lat:.2f} ms")
        print(f"  P95:    {p95_lat:.2f} ms")
        print(f"  P99:    {p99_lat:.2f} ms")
        print(f"  Max:    {max_lat:.2f} ms")

        self.assertLess(mean_lat, 50.0, f"Mean latency {mean_lat:.2f}ms exceeds 50ms SLA")
        self.assertLess(p50_lat, 50.0, f"Median latency {p50_lat:.2f}ms exceeds 50ms SLA")

    def test_empirical_latency_under_heavy_missingness(self):
        """Benchmark latency when 80% of fundamentals are missing across 3,379 symbols."""
        universe_df, raw_scores_df, _ = self._generate_synthetic_universe(
            n_symbols=3379, factor_loading=0.60, missing_rate=0.80
        )

        latencies_ms = []
        for _ in range(30):
            t0 = time.perf_counter()
            res = self.engine.compute_scores(universe=universe_df, raw_scores=raw_scores_df)
            t1 = time.perf_counter()
            latencies_ms.append((t1 - t0) * 1000.0)

        mean_lat = np.mean(latencies_ms)
        p50_lat = np.median(latencies_ms)
        p95_lat = np.percentile(latencies_ms, 95)

        print("\n[LATENCY BENCHMARK -- 80% Missing Fundamentals (30 trials)]")
        print(f"  Mean: {mean_lat:.2f} ms | Median: {p50_lat:.2f} ms | P95: {p95_lat:.2f} ms")

        self.assertLess(mean_lat, 50.0)
        self.assertLess(p50_lat, 50.0)

    # =========================================================================
    # 2. Empirical Rank Preservation (Spearman rho >= 0.65)
    # =========================================================================

    def test_empirical_spearman_rank_preservation_monte_carlo(self):
        """Test Spearman rank correlation across 50 Monte Carlo simulations with moderate factor loading."""
        n_sims = 50
        rank_corrs_raw = []
        rank_corrs_pure = []

        for seed in range(n_sims):
            universe_df, raw_scores_df, pure_alpha = self._generate_synthetic_universe(
                n_symbols=1000, factor_loading=0.50, seed=1000 + seed
            )
            universe_df['pure_alpha'] = pure_alpha

            res = self.engine.compute_scores(universe=universe_df, raw_scores=raw_scores_df)
            merged = pd.merge(pd.merge(raw_scores_df, universe_df[['symbol', 'pure_alpha']], on='symbol'), res, on='symbol')

            rho_raw = merged['score'].corr(merged['factor_neutralized_score'], method='spearman')
            rho_pure = merged['pure_alpha'].corr(merged['factor_neutralized_score'], method='spearman')

            rank_corrs_raw.append(rho_raw)
            rank_corrs_pure.append(rho_pure)

        mean_rho_raw = np.mean(rank_corrs_raw)
        min_rho_raw = np.min(rank_corrs_raw)
        mean_rho_pure = np.mean(rank_corrs_pure)

        print("\n[RANK PRESERVATION -- 50 Monte Carlo Trials]")
        print(f"  Corr(Neutralized, Raw):  Mean={mean_rho_raw:.4f}, Min={min_rho_raw:.4f}")
        print(f"  Corr(Neutralized, Pure): Mean={mean_rho_pure:.4f}")

        self.assertGreaterEqual(mean_rho_raw, 0.65, f"Mean Spearman rho with raw score {mean_rho_raw:.4f} < 0.65")
        self.assertGreaterEqual(min_rho_raw, 0.60, f"Min Spearman rho with raw score {min_rho_raw:.4f} < 0.60")

    # =========================================================================
    # 3. Hard Factor Correlation SLA Gate (|rho| < 0.15)
    # =========================================================================

    def test_empirical_factor_correlation_sla_3379_symbols(self):
        """Empirically test factor correlation across 3,379 symbols with extreme factor loading (0.90)."""
        universe_df, raw_scores_df, _ = self._generate_synthetic_universe(
            n_symbols=3379, factor_loading=0.90, seed=777
        )

        res_df = self.engine.compute_scores(universe=universe_df, raw_scores=raw_scores_df)
        eval_df = pd.merge(universe_df, res_df[['symbol', 'factor_neutralized_score']], on='symbol').dropna()
        neut_score = eval_df['factor_neutralized_score']

        ep_yield = np.where(eval_df['per'] > 0, 1.0 / eval_df['per'], -1.0 / np.abs(eval_df['per']))
        corrs = {
            'SMB (Size)': abs(neut_score.corr(np.log(eval_df['market_cap'].clip(lower=1e8)))),
            'HML (Value)': abs(neut_score.corr(pd.Series(ep_yield, index=eval_df.index))),
            'RMW (Prof)': abs(neut_score.corr(eval_df['roe'])),
            'CMA (Invest)': abs(neut_score.corr(eval_df['asset_growth_yoy'])),
            'UMD (Mom)': abs(neut_score.corr(eval_df['momentum_12m'])),
        }

        print("\n[FACTOR CORRELATION SLA GATE -- 3,379 Symbols (Loading=0.90)]")
        for factor, rho in corrs.items():
            print(f"  |rho({factor})| = {rho:.4f}")
            self.assertLess(rho, 0.15, f"{factor} correlation SLA failed: {rho:.4f} >= 0.15")

    # =========================================================================
    # 4. End-to-End Ensemble Integration & Pipeline Compatibility
    # =========================================================================

    def test_ensemble_scoring_engine_direct_integration(self):
        """Verify EnsembleScoringEngine ingests factor_neutralized_df and computes ensembled scores."""
        universe_df, raw_scores_df, _ = self._generate_synthetic_universe(n_symbols=100, seed=123)
        fn_df = self.engine.compute_scores(universe=universe_df, raw_scores=raw_scores_df)

        symbols = universe_df['symbol'].tolist()
        names = universe_df['name'].tolist()
        markets = universe_df['market'].tolist()

        base_df = pd.DataFrame({
            'symbol': symbols,
            'name': names,
            'market': markets,
            'score': np.random.uniform(0.1, 0.9, size=len(symbols)),
            'expected_return': np.random.uniform(0.01, 0.15, size=len(symbols)),
        })

        regimes = ["BULL_LOW_VOL", "BEAR_HIGH_VOL", "SIDEWAYS_LOW_VOL", "BEAR_LOW_VOL"]
        for regime in regimes:
            ens_result = self.ensemble.combine_predictions(
                reg_df=base_df.copy(),
                s_df=base_df.copy(),
                v_rule_df=base_df.copy(),
                vcp_ml_df=base_df.copy(),
                ll_df=base_df.copy(),
                lstm_df=base_df.copy(),
                stat_arb_df=base_df.copy(),
                sector_df=base_df.copy(),
                rim_df=base_df.copy(),
                event_df=base_df.copy(),
                mq_df=base_df.copy(),
                iv_skew_df=base_df.copy(),
                order_flow_df=base_df.copy(),
                reversal_df=base_df.copy(),
                arm_df=base_df.copy(),
                card_df=base_df.copy(),
                latr_df=base_df.copy(),
                inst_foreign_sector_df=base_df.copy(),
                supply_chain_df=base_df.copy(),
                sentiment_df=base_df.copy(),
                factor_neutralized_df=fn_df.copy(),
                regime=regime,
            )

            self.assertFalse(ens_result.empty, f"Ensemble returned empty DataFrame for regime {regime}")
            self.assertIn('ensemble_score', ens_result.columns)
            self.assertIn('factor_neutralized_score', ens_result.columns)
            self.assertFalse(ens_result['ensemble_score'].isna().all())

    def test_pipeline_text_formatting_simulation(self):
        """Simulate run_pipeline.py lines 2880-2905 to ensure text generation works cleanly."""
        universe_df, raw_scores_df, _ = self._generate_synthetic_universe(n_symbols=50, seed=456)
        factor_neutralized_df = self.engine.compute_scores(universe=universe_df, raw_scores=raw_scores_df)

        lines = []
        lines.append("=== Strategy 21: Multi-Factor Style Neutralized Pure Alpha Predictions ===\n")
        lines.append("Date: 2026-08-14 19:00:00 KST\n")
        lines.append(f"Total symbols evaluated: {len(factor_neutralized_df)}\n\n")
        lines.append(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Market':<10}{'FN Score':<14}\n")
        lines.append("-" * 60 + "\n")

        for rank, (_, row) in enumerate(factor_neutralized_df.head(100).iterrows(), 1):
            name_str = str(row['name'])[:16] if pd.notna(row['name']) else "Unknown"
            score_val = row.get('factor_neutralized_score', row.get('neutralized_score', 0.0))
            if pd.isna(score_val):
                score_val = 0.0
            formatted_line = f"{rank:<5}{row['symbol']:<10}{name_str:<18}{str(row['market']):<10}{score_val * 100.0 if score_val <= 1.0 else score_val:>12.1f}%\n"
            lines.append(formatted_line)

        output_text = "".join(lines)
        self.assertIn("SYM_0000", output_text)
        self.assertIn("Strategy 21", output_text)
        self.assertEqual(len(lines), 5 + len(factor_neutralized_df))


if __name__ == '__main__':
    unittest.main()
