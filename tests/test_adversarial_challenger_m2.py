"""
tests/test_adversarial_challenger_m2.py
Adversarial Stress Harness for Milestone 2:
- 31-Strategy Canonical Sequence & Multi-File Consistency
- Strategy Correlation Monitor & Meucci ESC Stress Testing across 31 strategies
- CrossSectionalScoreNormalizer Multi-Factor Edge Cases & Mathematical Bounds
- verify_gha_artifacts.py & merge_predictions.py Robustness
"""

import math
import os
import re
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from trading_system.scripts.verify_gha_artifacts import (
    STRATEGIES as VERIFIER_STRATEGIES,
    STRATEGY_PANEL_ALIASES,
    check_regression,
    check_surge,
    check_vcp,
    check_vcp_ml,
    check_generic_strategy,
    verify_market_strategies,
    verify_ensemble,
    verify_gh_pages,
)
from trading_system.src.analysis.strategy_correlation_monitor import StrategyCorrelationMonitor
from trading_system.src.ai.score_normalizer import CrossSectionalScoreNormalizer
from trading_system.merge_predictions import ALL_31_STRATEGIES as MERGE_31_STRATEGIES

# Canonical 31-strategy reference from PROJECT.md
CANONICAL_31_STRATEGIES = [
    "regression", "surge", "lead_lag", "vcp_rule", "vcp_ml", "lstm",
    "stat_arb", "sector_rotation", "rim_valuation", "event_driven", "mq_factor",
    "iv_skew", "order_flow", "short_term_reversal", "arm_factor",
    "card_factor", "latr_factor", "inst_foreign_sector",
    "supply_chain", "sentiment", "factor_neutralized", "vol_target",
    "microstructure", "accruals_quality", "short_squeeze", "valueup_catalyst",
    "trend_efficiency", "gamma_squeeze", "insider_buying", "darkpool", "earnings_tone_drift"
]


class TestAdversarialCanonicalSequence:
    """Stress tests verifying strict 1:1 multi-file consistency of canonical 31 strategies."""

    def test_canonical_list_length_and_uniqueness(self):
        assert len(CANONICAL_31_STRATEGIES) == 31
        assert len(set(CANONICAL_31_STRATEGIES)) == 31
        assert CANONICAL_31_STRATEGIES[29] == "darkpool"  # Strategy 30 (0-indexed 29)
        assert CANONICAL_31_STRATEGIES[30] == "earnings_tone_drift"  # Strategy 31 (0-indexed 30)

    def test_merge_predictions_matches_canonical(self):
        assert MERGE_31_STRATEGIES == CANONICAL_31_STRATEGIES

    def test_verifier_strategies_matches_canonical(self):
        assert VERIFIER_STRATEGIES[:31] == CANONICAL_31_STRATEGIES

    def test_verifier_panel_aliases_covers_all_31_and_ensemble(self):
        expected_keys = set(CANONICAL_31_STRATEGIES) | {"ensemble"}
        actual_keys = set(STRATEGY_PANEL_ALIASES.keys())
        assert expected_keys.issubset(actual_keys)
        for key, aliases in STRATEGY_PANEL_ALIASES.items():
            assert len(aliases) >= 1
            assert all(isinstance(a, str) and len(a) > 0 for a in aliases)

    def test_run_pipeline_registry_and_verification_files(self):
        pipeline_path = Path("trading_system/run_pipeline.py")
        content = pipeline_path.read_text(encoding="utf-8")

        # Verify STRATEGY_REGISTRY contains all expected strategy files
        for strat in CANONICAL_31_STRATEGIES:
            if strat in ("regression", "surge", "lead_lag", "vcp_rule", "vcp_ml", "stat_arb", "sector_rotation", "rim_valuation"):
                # Core strategies have their own dedicated runners or files
                continue
            # Non-core strategies must be defined in STRATEGY_REGISTRY with their output filename
            assert f"{strat}_predictions.txt" in content or f"{strat}" in content

        # Check verification_files list in run_pipeline.py
        for strat in [
            "pipeline_result.txt", "surge_predictions.txt", "lead_lag_predictions.txt",
            "vcp_patterns.txt", "vcp_ml_predictions.txt", "lstm_predictions.txt",
            "stat_arb_predictions.txt", "sector_predictions.txt", "rim_predictions.txt",
            "darkpool_predictions.txt", "earnings_tone_drift_predictions.txt",
            "ensemble_predictions.txt", "strategy_data_coverage_report.txt", "portfolio_allocation.txt"
        ]:
            assert f'"{strat}"' in content or f"'{strat}'" in content

    def test_agents_md_consistency(self):
        agents_path = Path("AGENTS.md")
        content = agents_path.read_text(encoding="utf-8")
        # Check Strategy 30 and Strategy 31 ordering
        s30_idx = content.find("Darkpool & HFT")
        s31_idx = content.find("Earnings Tone Drift")
        assert s30_idx != -1 and s31_idx != -1
        assert s30_idx < s31_idx, "Strategy 30 (Darkpool) must precede Strategy 31 (Earnings Tone Drift)"


class TestAdversarialStrategyCorrelationMonitor:
    """Stress tests Meucci ESC entropy calculation and correlation monitoring across 31 strategies."""

    def test_esc_all_orthogonal_31_strategies(self):
        """When 31 strategies are strictly uncorrelated (identity correlation matrix), ESC must equal 31.0."""
        monitor = StrategyCorrelationMonitor()
        identity_corr = pd.DataFrame(
            np.eye(31),
            index=CANONICAL_31_STRATEGIES,
            columns=CANONICAL_31_STRATEGIES
        )
        esc = monitor.compute_effective_strategy_count(identity_corr)
        assert math.isclose(esc, 31.0, abs_tol=0.1)

    def test_esc_perfectly_collinear_31_strategies(self):
        """When 31 strategies are perfectly collinear (all 1.0s), ESC must equal 1.0."""
        monitor = StrategyCorrelationMonitor()
        collinear_corr = pd.DataFrame(
            np.ones((31, 31)),
            index=CANONICAL_31_STRATEGIES,
            columns=CANONICAL_31_STRATEGIES
        )
        esc = monitor.compute_effective_strategy_count(collinear_corr)
        assert math.isclose(esc, 1.0, abs_tol=0.1)

    def test_esc_clustered_strategies(self):
        """5 clusters of 6 perfectly correlated strategies (30 total) -> ESC should be ~5.0."""
        block = np.zeros((30, 30))
        for i in range(5):
            block[i*6:(i+1)*6, i*6:(i+1)*6] = 1.0
        corr_df = pd.DataFrame(block)
        monitor = StrategyCorrelationMonitor()
        esc = monitor.compute_effective_strategy_count(corr_df)
        assert math.isclose(esc, 5.0, abs_tol=0.2)

    def test_esc_with_nans_and_singular_matrices(self):
        """Correlation matrix with NaNs, Infs, and zero variance signals must not crash."""
        monitor = StrategyCorrelationMonitor()
        bad_matrix = np.full((31, 31), np.nan)
        corr_df = pd.DataFrame(bad_matrix, index=CANONICAL_31_STRATEGIES, columns=CANONICAL_31_STRATEGIES)
        esc = monitor.compute_effective_strategy_count(corr_df)
        assert 1.0 <= esc <= 31.0

    def test_analyze_correlations_random_walk_data(self, tmp_path):
        """Run analyze_correlations on synthetic multi-factor dataframe with 31 columns and 200 symbols."""
        np.random.seed(42)
        n_symbols = 200
        data = {}
        for strat in CANONICAL_31_STRATEGIES:
            # Generate continuous scores with some correlation structure
            base = np.random.randn(n_symbols)
            noise = np.random.randn(n_symbols) * 0.5
            data[strat] = base + noise

        df = pd.DataFrame(data)
        monitor = StrategyCorrelationMonitor(output_dir=str(tmp_path))
        res = monitor.analyze_correlations(df, save_json=False)

        assert "effective_strategy_count" in res
        assert 1.0 <= res["effective_strategy_count"] <= 31.0
        assert "correlation_matrix" in res
        assert "top_redundant_pairs" in res
        assert "top_diversifier_pairs" in res
        assert res["total_strategies"] == 31
        assert "diversity_ratio" in res


class TestAdversarialScoreNormalizer:
    """Stress tests CrossSectionalScoreNormalizer across 31 strategies under extreme conditions."""

    @pytest.fixture
    def normalizer(self):
        return CrossSectionalScoreNormalizer(method="winsorized_zscore", min_symbols_per_market=10)

    def test_normalize_all_31_strategies_with_heterogeneous_distributions(self, normalizer):
        """Test normalization when all 31 strategies have vastly different scales, fat tails, and missingness."""
        np.random.seed(123)
        n_stocks = 150
        data = {"market": ["KOSPI"] * 50 + ["SP500"] * 50 + ["NASDAQ"] * 50}

        for i, strat in enumerate(CANONICAL_31_STRATEGIES):
            if i % 5 == 0:
                # Heavy tailed Cauchy
                data[strat] = np.random.standard_cauchy(n_stocks)
            elif i % 5 == 1:
                # Exponential / positive skewed
                data[strat] = np.random.exponential(scale=10.0, size=n_stocks)
            elif i % 5 == 2:
                # Uniform [0, 1]
                data[strat] = np.random.uniform(0, 1, size=n_stocks)
            elif i % 5 == 3:
                # Sparse factor with 40% zeros
                vals = np.random.uniform(0, 10, size=n_stocks)
                vals[vals < 4.0] = 0.0
                data[strat] = vals
            else:
                # Normal distribution with 30% NaNs
                vals = np.random.randn(n_stocks) * 5.0 + 10.0
                nan_mask = np.random.rand(n_stocks) < 0.3
                vals[nan_mask] = np.nan
                data[strat] = vals

        df = pd.DataFrame(data)
        norm_df = normalizer.normalize_scores(df, CANONICAL_31_STRATEGIES, market_col="market")

        # Verify output bounds and properties
        for strat in CANONICAL_31_STRATEGIES:
            col_vals = norm_df[strat].dropna()
            assert (col_vals >= 0.005).all(), f"{strat} has values < 0.005"
            assert (col_vals <= 0.995).all(), f"{strat} has values > 0.995"
            # Verify NaNs are strictly preserved where input was NaN
            orig_nans = df[strat].isna()
            assert norm_df[strat].isna().equals(orig_nans)

    def test_percentile_rank_method_31_strategies(self):
        """Test percentile_rank method on all 31 strategies."""
        normalizer = CrossSectionalScoreNormalizer(method="percentile_rank", min_symbols_per_market=10)
        np.random.seed(99)
        n_stocks = 60
        data = {"market": ["SP500"] * n_stocks}
        for strat in CANONICAL_31_STRATEGIES:
            data[strat] = np.random.randn(n_stocks)

        df = pd.DataFrame(data)
        norm_df = normalizer.normalize_scores(df, CANONICAL_31_STRATEGIES, market_col="market")

        for strat in CANONICAL_31_STRATEGIES:
            col_vals = norm_df[strat]
            assert (col_vals >= 0.005).all()
            assert (col_vals <= 0.995).all()
            # Uniform spread check: min should be close to 0.005 and max close to 0.995
            assert col_vals.min() < 0.05
            assert col_vals.max() > 0.95

    def test_all_nan_and_constant_columns(self, normalizer):
        """Verify behavior when entire column is NaN or constant."""
        df = pd.DataFrame({
            "market": ["KOSPI"] * 20,
            "all_nan": [np.nan] * 20,
            "all_constant": [42.0] * 20,
            "single_valid": [10.0] + [np.nan] * 19,
        })
        norm_df = normalizer.normalize_scores(df, ["all_nan", "all_constant", "single_valid"], market_col="market")

        assert norm_df["all_nan"].isna().all()
        assert (norm_df["all_constant"] == 0.50).all()
        assert norm_df["single_valid"].iloc[0] == 0.50
        assert norm_df["single_valid"].iloc[1:].isna().all()


class TestAdversarialVerifierGhaArtifacts:
    """Stress tests verify_gha_artifacts checkers and alias resolvers across various input shapes."""

    def test_check_generic_strategy_various_formats(self):
        content_table = """
        === Strategy Output ===
        Rank | Symbol | Name | Score | Vol
        1    | 005930 | Samsung | 0.854 | 12.3%
        2    | 000660 | SK Hynix| 0.762 | 15.1%
        3    | 035420 | NAVER   | 0.651 | 11.0%
        4    | 035720 | Kakao   | 0.589 | 18.2%
        5    | 051910 | LG Chem | 0.540 | 14.5%
        6    | 005380 | Hyundai | 0.512 | 10.8%
        7    | 000270 | Kia     | 0.498 | 11.2%
        8    | 068270 | Celltr  | 0.477 | 20.1%
        9    | 105560 | KB Fin  | 0.465 | 9.5%
        10   | 055550 | Shinhan | 0.430 | 8.8%
        """
        res = check_generic_strategy(content_table, "KOSPI", "darkpool")
        assert res.valid is True
        assert res.non_zero is True
        assert res.count >= 10

    def test_check_generic_strategy_rejects_all_zeros(self):
        content_zeros = """
        === Strategy Output ===
        1 | 005930 | 0.000 | 0.0%
        2 | 000660 | 0.000 | 0.0%
        3 | 035420 | 0.000 | 0.0%
        4 | 035720 | 0.000 | 0.0%
        5 | 051910 | 0.000 | 0.0%
        6 | 005380 | 0.000 | 0.0%
        7 | 000270 | 0.000 | 0.0%
        8 | 068270 | 0.000 | 0.0%
        9 | 105560 | 0.000 | 0.0%
        10| 055550 | 0.000 | 0.0%
        """
        res = check_generic_strategy(content_zeros, "KOSPI", "earnings_tone_drift")
        assert res.valid is False
        assert res.non_zero is False
        assert "all output values are 0.0" in res.message

    def test_verify_market_strategies_full_31_mock(self, tmp_path):
        """Create mock files for all 31 strategies and verify verify_market_strategies evaluates all 31."""
        market = "SP500"
        for strat in VERIFIER_STRATEGIES:
            if strat == "regression":
                lines = [f"{i} | AAPL{i} | 0.0{i+1}" for i in range(15)]
                (tmp_path / f"pipeline_result_{market}.txt").write_text("\n".join(lines), encoding="utf-8")
            elif strat == "surge":
                lines = [f"[{market}] AAPL{i} (Apple): {10.5 + i}%" for i in range(15)]
                (tmp_path / f"surge_predictions_{market}.txt").write_text("\n".join(lines), encoding="utf-8")
            elif strat == "lead_lag":
                lines = [f"[{market}] Sector Lead -> AAPL{i}: score 0.{i}" for i in range(15)]
                (tmp_path / f"lead_lag_predictions_{market}.txt").write_text("\n".join(lines), encoding="utf-8")
            elif strat == "vcp_rule":
                lines = [f"[{market}] AAPL{i} VCP Pattern detected" for i in range(15)]
                (tmp_path / f"vcp_patterns_{market}.txt").write_text("\n".join(lines), encoding="utf-8")
            elif strat == "vcp_ml":
                lines = [f"[{market}] AAPL{i} (Apple): {20.5 + i}%" for i in range(15)]
                (tmp_path / f"vcp_ml_predictions_{market}.txt").write_text("\n".join(lines), encoding="utf-8")
            else:
                lines = [f"{i+1} | AAPL{i} | Score: 0.{70 + i}" for i in range(15)]
                (tmp_path / f"{strat}_predictions_{market}.txt").write_text("\n".join(lines), encoding="utf-8")

        m_res = verify_market_strategies(tmp_path, market)
        assert len(m_res.strategies) == len(VERIFIER_STRATEGIES)
        assert m_res.all_strategies_valid is True
        for s_key in VERIFIER_STRATEGIES:
            assert s_key in m_res.strategies
            assert m_res.strategies[s_key].valid is True
            assert m_res.strategies[s_key].non_zero is True
