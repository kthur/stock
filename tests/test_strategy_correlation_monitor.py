"""Unit tests for Strategy Correlation Monitor & ESC calculation."""

import pandas as pd
import numpy as np
from src.analysis.strategy_correlation_monitor import StrategyCorrelationMonitor


def test_effective_strategy_count_orthogonal():
    monitor = StrategyCorrelationMonitor()

    # 4 completely uncorrelated strategies
    corr_df = pd.DataFrame(np.eye(4), columns=['s1', 's2', 's3', 's4'], index=['s1', 's2', 's3', 's4'])
    esc = monitor.compute_effective_strategy_count(corr_df)
    # Fully orthogonal matrix should yield ESC close to 4.0
    assert 3.8 <= esc <= 4.0


def test_effective_strategy_count_collinear():
    monitor = StrategyCorrelationMonitor()

    # 4 completely identical (collinear) strategies
    corr_df = pd.DataFrame(np.ones((4, 4)), columns=['s1', 's2', 's3', 's4'], index=['s1', 's2', 's3', 's4'])
    esc = monitor.compute_effective_strategy_count(corr_df)
    # Fully collinear matrix should yield ESC close to 1.0
    assert 1.0 <= esc <= 1.2


def test_analyze_correlations_summary(tmp_path):
    monitor = StrategyCorrelationMonitor(output_dir=str(tmp_path))

    # Generate synthetic scores for 50 stocks across 4 strategies
    np.random.seed(42)
    s1 = np.random.randn(50)
    s2 = s1 * 0.9 + np.random.randn(50) * 0.1  # High correlation with s1
    s3 = np.random.randn(50)  # Uncorrelated
    s4 = -s3 * 0.8 + np.random.randn(50) * 0.2  # Negatively correlated with s3

    df_scores = pd.DataFrame({'strat_1': s1, 'strat_2': s2, 'strat_3': s3, 'strat_4': s4})
    summary = monitor.analyze_correlations(df_scores, save_json=True)

    assert summary['total_strategies'] == 4
    assert 1.5 <= summary['effective_strategy_count'] <= 3.5
    assert len(summary['top_redundant_pairs']) >= 1
    # Check that strat_1 and strat_2 are detected as redundant
    top_pair = summary['top_redundant_pairs'][0]
    assert set([top_pair['strategy_1'], top_pair['strategy_2']]) == {'strat_1', 'strat_2'}
    assert top_pair['spearman_rho'] > 0.80

    # Verify JSON file was written
    out_file = tmp_path / "strategy_correlation_matrix.json"
    assert out_file.exists()
