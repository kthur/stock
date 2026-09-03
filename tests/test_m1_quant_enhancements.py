import pytest
import numpy as np
import pandas as pd

from src.ai.factor_suppression import RegimeFactorSuppressionEngine
from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine
from src.ai.ensemble_scorer import EnsembleScoringEngine

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


class TestM1QuantEnhancements:
    """Comprehensive test suite for Milestone 1 Apex Quantitative Enhancements (Features 1-6)."""

    # -------------------------------------------------------------------------
    # FEATURE 6: Statistically Calibrated Suppression Cutoffs theta(R, N)
    # -------------------------------------------------------------------------
    def test_feature_6_statistically_calibrated_cutoff_formula(self):
        """Verify theta(R, N) = clip(theta_0(R) + 1.645 / sqrt(max(N-3, 1)), 0.35, 0.85)."""
        engine = RegimeFactorSuppressionEngine()
        theta_0 = 0.60

        # 1. Fallbacks for None or N <= 3
        assert engine.calibrate_cutoff(theta_0, None) == 0.60
        assert engine.calibrate_cutoff(theta_0, 1) == 0.60
        assert engine.calibrate_cutoff(theta_0, 2) == 0.60
        assert engine.calibrate_cutoff(theta_0, 3) == 0.60

        # 2. Monotonic decay as sample size N increases
        theta_50 = engine.calibrate_cutoff(theta_0, 50)
        theta_500 = engine.calibrate_cutoff(theta_0, 500)
        theta_2000 = engine.calibrate_cutoff(theta_0, 2000)

        expected_50 = np.clip(0.60 + 1.645 / np.sqrt(47), 0.35, 0.85)
        expected_500 = np.clip(0.60 + 1.645 / np.sqrt(497), 0.35, 0.85)
        expected_2000 = np.clip(0.60 + 1.645 / np.sqrt(1997), 0.35, 0.85)

        assert abs(theta_50 - expected_50) < 1e-4
        assert abs(theta_500 - expected_500) < 1e-4
        assert abs(theta_2000 - expected_2000) < 1e-4
        assert theta_50 > theta_500 > theta_2000 > theta_0

        # 3. Clamping to bounds [0.35, 0.85]
        assert engine.calibrate_cutoff(0.10, 10000) == 0.35
        assert engine.calibrate_cutoff(0.80, 5) == 0.85

    def test_feature_6_suppress_weights_integration_with_sample_size(self):
        """Verify suppress_weights adapts cutoff dynamically when n_samples is passed."""
        engine = RegimeFactorSuppressionEngine()
        base_weights = {'surge': 0.50, 'vcp_ml': 0.50}
        # Correlation = 0.75 between two momentum strategies
        corr_df = pd.DataFrame(
            [[1.0, 0.75], [0.75, 1.0]],
            index=['surge', 'vcp_ml'],
            columns=['surge', 'vcp_ml']
        )

        # In SIDEWAYS_LOW_VOL, theta_0 = 0.60
        # For N=10: theta(R, 10) = 0.60 + 1.645/sqrt(7) = 0.60 + 0.6217 = 0.85 (clipped)
        # Since rho=0.75 < 0.85, no penalty occurs!
        rep_small_n = engine.get_suppression_report(
            base_weights, corr_df, 'SIDEWAYS_LOW_VOL', n_samples=10
        )
        assert rep_small_n['penalties']['surge'] == 1.0
        assert rep_small_n['penalties']['vcp_ml'] == 1.0

        # For N=1000: theta(R, 1000) = 0.60 + 1.645/sqrt(997) ~ 0.652
        # Since rho=0.75 > 0.652, collinearity penalty IS applied!
        rep_large_n = engine.get_suppression_report(
            base_weights, corr_df, 'SIDEWAYS_LOW_VOL', n_samples=1000
        )
        assert rep_large_n['penalties']['surge'] < 1.0
        assert rep_large_n['penalties']['vcp_ml'] < 1.0

    # -------------------------------------------------------------------------
    # FEATURE 1: Pipeline Sequence Rectification (Pre-Ortho Suppression)
    # -------------------------------------------------------------------------
    def test_feature_1_pre_orthogonalization_raw_correlation_suppression(self):
        """Verify combine_predictions monitors raw correlation and applies active suppression penalties."""
        engine = EnsembleScoringEngine()
        np.random.seed(42)
        n = 100
        base_latent = np.random.randn(n)

        # Create DataFrame where surge and vcp_ml are almost perfectly collinear
        df = pd.DataFrame({
            'symbol': [f'SYM_{i:03d}' for i in range(n)],
            'name': [f'SYM_{i:03d}' for i in range(n)],
            'market': ['KOSPI'] * n,
            'close': [50000.0] * n,
            'volume': [1_000_000.0] * n,
            'surge_score': np.clip(0.50 + 0.35 * base_latent + 0.02 * np.random.randn(n), 0.0, 1.0),
            'vcp_ml_score': np.clip(0.50 + 0.35 * base_latent + 0.02 * np.random.randn(n), 0.0, 1.0),
            'rim_score': np.random.uniform(0.2, 0.8, n),
            'order_flow_score': np.random.uniform(0.2, 0.8, n),
        })

        res = engine.combine_predictions(
            s_df=df[['symbol', 'surge_score', 'close', 'volume']],
            vcp_ml_df=df[['symbol', 'vcp_ml_score', 'close', 'volume']],
            rim_df=df[['symbol', 'rim_score', 'close', 'volume']],
            order_flow_df=df[['symbol', 'order_flow_score', 'close', 'volume']],
            regime='SIDEWAYS_LOW_VOL'
        )

        assert hasattr(res, 'attrs')
        assert 'correlation_report' in res.attrs
        rep = res.attrs['correlation_report']

        raw_corr = rep['correlation_matrix']
        # Pre-orthogonalization raw correlation between surge and vcp_ml must be high (> 0.80)
        assert raw_corr.loc['surge', 'vcp_ml'] > 0.80

        # In SIDEWAYS_LOW_VOL, MOMENTUM is a high-risk redundant cluster; penalties must be active (< 1.0)
        penalties = rep['penalties']
        assert penalties['surge'] < 1.0
        assert penalties['vcp_ml'] < 1.0

    # -------------------------------------------------------------------------
    # FEATURE 2: Dual-Consensus Spectral Whitening & Marchenko-Pastur Floor
    # -------------------------------------------------------------------------
    def test_feature_2_preserve_top_k_dual_consensus(self):
        """Verify Dual-Consensus Spectral Whitening preserves PC1 (trend) and PC2 (value) while reducing correlation."""
        N, K = 300, 10
        np.random.seed(42)
        pc1_trend = np.random.normal(0, 1, N)
        pc2_value = np.random.normal(0, 1, N)

        cols = [f'strat_{i}' for i in range(K)]
        data = {'symbol': [f'SYM_{i:04d}' for i in range(N)]}
        for j in range(K):
            if j < 4:
                raw = 0.7 * pc1_trend + 0.3 * np.random.normal(0, 1, N)
            elif j < 8:
                raw = 0.7 * pc2_value + 0.3 * np.random.normal(0, 1, N)
            else:
                raw = 0.4 * pc1_trend + 0.4 * pc2_value + 0.4 * np.random.normal(0, 1, N)
            data[cols[j]] = 1.0 / (1.0 + np.exp(-raw))
        df = pd.DataFrame(data)

        # Baseline pairwise off-diagonal correlation
        raw_corr = np.corrcoef(df[cols].values, rowvar=False)
        off_diag = ~np.eye(K, dtype=bool)
        mean_raw_corr = np.mean(np.abs(raw_corr[off_diag]))
        assert mean_raw_corr > 0.35

        # Apply dual-consensus orthogonalization (preserve_top_k=2)
        engine = FactorOrthogonalizerEngine(preserve_top_k=2)
        ortho_df = engine.orthogonalize(df, cols, preserve_top_k=2)
        vals = ortho_df[cols].values

        assert vals.shape == (N, K)
        assert np.all(vals >= 0.0) and np.all(vals <= 1.0)
        assert np.all(np.isfinite(vals))

        # Correlation reduced while preserving leading factors
        ortho_corr = np.corrcoef(vals, rowvar=False)
        mean_ortho_corr = np.mean(np.abs(ortho_corr[off_diag]))
        assert mean_ortho_corr < mean_raw_corr

    def test_feature_2_marchenko_pastur_spectral_floor_stability(self):
        """Verify Marchenko-Pastur noise floor prevents over-amplification in rank-deficient cases (N < K)."""
        N, K = 5, 15
        np.random.seed(99)
        cols = [f'strat_{i}' for i in range(K)]
        df = pd.DataFrame(np.random.uniform(0.2, 0.8, (N, K)), columns=cols)
        df['symbol'] = [f'SYM_{i}' for i in range(N)]

        engine = FactorOrthogonalizerEngine(preserve_top_k=2)
        res = engine.orthogonalize(df, cols, preserve_top_k=2)

        vals = res[cols].values
        assert vals.shape == (N, K)
        assert not np.isnan(vals).any()
        assert not np.isinf(vals).any()
        assert np.all(vals >= 0.0) and np.all(vals <= 1.0)

    # -------------------------------------------------------------------------
    # FEATURE 3: Symmetric Richards / Bessembinder Tail Convex Power-Law
    # -------------------------------------------------------------------------
    def test_feature_3_bessembinder_symmetric_properties(self):
        """Verify strict monotonicity, rank preservation, neutral invariance, and decile spread expansion."""
        scores = np.linspace(0.05, 0.95, 100)

        # 1. Neutral invariance: 0.50 -> 0.50
        neutral_arr = np.array([0.50] * 10)
        res_neutral = EnsembleScoringEngine.apply_bessembinder_convex_power_law(
            neutral_arr, symmetric=True
        )
        np.testing.assert_allclose(res_neutral, 0.50, atol=1e-5)

        # 2. Strict monotonicity & Rank preservation (Spearman rho = 1.0000)
        transformed = EnsembleScoringEngine.apply_bessembinder_convex_power_law(
            scores, symmetric=True
        )
        assert len(transformed) == len(scores)
        assert np.all(np.diff(transformed) > 0)
        spearman_corr = pd.Series(scores).corr(pd.Series(transformed), method='spearman')
        assert spearman_corr > 0.99999

        # 3. Decile spread widening & noise suppression (as mathematically derived in plan_m1_3):
        # S=0.95 -> S* ~ 0.884, S=0.05 -> S* ~ 0.116, S=0.55 -> S* ~ 0.513
        test_inputs = np.array([0.05, 0.50, 0.55, 0.95, 1.00])
        test_trans = EnsembleScoringEngine.apply_bessembinder_convex_power_law(
            test_inputs, symmetric=True
        )
        assert abs(test_trans[0] - 0.116) < 0.01   # S=0.05 -> S* ~ 0.116
        assert abs(test_trans[1] - 0.500) < 1e-4   # S=0.50 -> S* = 0.500
        assert abs(test_trans[2] - 0.513) < 0.01   # S=0.55 -> S* ~ 0.513 (noise compressed towards neutral)
        assert abs(test_trans[3] - 0.884) < 0.01   # S=0.95 -> S* ~ 0.884
        assert abs(test_trans[4] - 1.000) < 1e-4   # S=1.00 -> S* = 1.000 (full dynamic range reached)

        # Convex expansion: Tail conviction (S=0.95) relative to near-center noise (S=0.55) expands dramatically
        raw_conviction_ratio = (0.95 - 0.50) / (0.55 - 0.50)  # 0.45 / 0.05 = 9.0
        trans_conviction_ratio = (test_trans[3] - 0.50) / (test_trans[2] - 0.50) # > 25.0
        assert trans_conviction_ratio > raw_conviction_ratio * 2.5

        # 4. Backward compatibility: symmetric=False retains one-sided right-tail boost only
        legacy_boosted = EnsembleScoringEngine.apply_bessembinder_convex_power_law(
            scores, symmetric=False
        )
        # Left tail (e.g. index 5, score ~ 0.09) should NOT be modified in legacy mode
        assert abs(legacy_boosted[5] - scores[5]) < 1e-6
        # Right tail should be boosted
        assert legacy_boosted[-1] >= scores[-1]

    # -------------------------------------------------------------------------
    # FEATURE 4: Continuous Bilinear Cross-Pillar Synergy Kernel
    # -------------------------------------------------------------------------
    def test_feature_4_bilinear_cross_pillar_synergy_properties(self):
        """Verify continuous synergy without step discontinuities, cluster mutual exclusivity, and regime adaptation."""
        # Test 1: Continuity (no step cliffs at 0.599 vs 0.601)
        df1 = pd.DataFrame({
            'rim_score': [0.599],
            'surge_score': [0.750],
        })
        df2 = pd.DataFrame({
            'rim_score': [0.601],
            'surge_score': [0.750],
        })
        # Generate dummy 5 rows for minimum row threshold
        dummy_df1 = pd.concat([df1] * 5, ignore_index=True)
        dummy_df2 = pd.concat([df2] * 5, ignore_index=True)

        mult1 = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(dummy_df1, regime='BULL_LOW_VOL').iloc[0]
        mult2 = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(dummy_df2, regime='BULL_LOW_VOL').iloc[0]

        # In the old step system, crossing 0.60 caused a 3.5% jump. In bilinear, difference is < 0.005!
        assert abs(mult2 - mult1) < 0.005, f"Discontinuity detected: {mult1} vs {mult2}"

        # Test 2: Cluster Mutual Exclusivity:
        # dual_correction is in Catalyst ONLY. Having high dual_correction alone must produce NO cross-pillar synergy!
        df_isolated = pd.DataFrame({
            'dual_correction_score': [0.95] * 5,
        })
        mult_isolated = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df_isolated, regime='SIDEWAYS_LOW_VOL')
        np.testing.assert_allclose(mult_isolated.values, 1.000, atol=1e-5)

        # Test 3: Quadruple Confluence (all 4 pillars high) reaches near max bonus (1.08 ~ 1.10)
        df_quad = pd.DataFrame({
            'rim_score': [0.90] * 5,              # Valuation
            'surge_score': [0.90] * 5,            # Momentum
            'order_flow_score': [0.90] * 5,       # Flow
            'event_score': [0.90] * 5,            # Catalyst
        })
        mult_quad = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df_quad, regime='BULL_LOW_VOL')
        assert np.all(mult_quad >= 1.07) and np.all(mult_quad <= 1.10)

        # Test 4: 2D Regime Adaptation:
        # Bull regime gives higher weight to Momentum x Flow than Bear regime
        df_mom_flow = pd.DataFrame({
            'surge_score': [0.90] * 5,
            'order_flow_score': [0.90] * 5,
        })
        mult_bull = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df_mom_flow, regime='BULL_LOW_VOL').iloc[0]
        mult_bear = EnsembleScoringEngine.compute_bilinear_cross_pillar_synergy(df_mom_flow, regime='BEAR_HIGH_VOL').iloc[0]
        assert mult_bull > mult_bear

    # -------------------------------------------------------------------------
    # FEATURE 5: 2D Regime-Adaptive Strategy Half-Life Scaling
    # -------------------------------------------------------------------------
    def test_feature_5_regime_adaptive_half_lives(self):
        """Verify 2D regime modulation on half-lives and tier elasticity."""
        hl_bull = EnsembleScoringEngine.get_regime_adaptive_half_lives('BULL_LOW_VOL')
        hl_sideways = EnsembleScoringEngine.get_regime_adaptive_half_lives('SIDEWAYS_LOW_VOL')
        hl_bear = EnsembleScoringEngine.get_regime_adaptive_half_lives('BEAR_HIGH_VOL')
        hl_crisis = EnsembleScoringEngine.get_regime_adaptive_half_lives('CRISIS')

        # 1. Bull vs Sideways vs Bear vs Crisis ordering
        assert hl_bull['surge'] > hl_sideways['surge'] > hl_bear['surge'] > hl_crisis['surge']
        assert hl_bull['rim_valuation'] > hl_sideways['rim_valuation'] > hl_bear['rim_valuation'] > hl_crisis['rim_valuation']

        # 2. Fast tier accelerates more in volatile regimes (microstructure base=0.5)
        assert hl_crisis['microstructure'] <= 0.15
        assert hl_bull['microstructure'] >= 0.50

        # 3. Slow tier (rim_valuation base=45.0) remains bounded and doesn't decay to zero
        assert hl_crisis['rim_valuation'] >= 5.0

    def test_feature_5_exponential_decay_filter_and_rank_ic_integration(self):
        """Verify apply_exponential_decay_filter and apply_rank_ic_decay_calibration accept regime."""
        df_curr = pd.DataFrame({
            'symbol': ['S1', 'S2'],
            'surge_score': [0.80, 0.70],
            'rim_score': [0.60, 0.50],
        })
        df_prev = pd.DataFrame({
            'symbol': ['S1', 'S2'],
            'surge_score': [0.60, 0.50],
            'rim_score': [0.70, 0.60],
        })

        # Apply decay filter under Crisis regime (fast responsiveness)
        res_crisis = EnsembleScoringEngine.apply_exponential_decay_filter(
            df_curr, df_prev, regime='CRISIS'
        )
        # Apply decay filter under Bull Low Vol regime (slow decay, more smoothing)
        res_bull = EnsembleScoringEngine.apply_exponential_decay_filter(
            df_curr, df_prev, regime='BULL_LOW_VOL'
        )

        assert not res_crisis.empty and not res_bull.empty
        # In Crisis, current score has higher weight (closer to df_curr)
        # In Bull, previous score has more smoothing influence
        assert abs(res_crisis.loc[0, 'surge_score'] - 0.80) <= abs(res_bull.loc[0, 'surge_score'] - 0.80)

        # Verify apply_rank_ic_decay_calibration with regime
        weights = {'surge': 0.50, 'rim_valuation': 0.50}
        calibrated = EnsembleScoringEngine.apply_rank_ic_decay_calibration(
            weights,
            latency_days=2.0,
            regime='CRISIS'
        )
        assert len(calibrated) == 2
        assert abs(sum(calibrated.values()) - 1.0) < 1e-5
