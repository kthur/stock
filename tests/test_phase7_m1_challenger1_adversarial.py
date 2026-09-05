
import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.factor_suppression import apply_quintic_hyperbolic_deadband, QUINT_PILLAR_MAP

class TestExtremeProbabilityVectorShifts:
    @pytest.fixture
    def engine(self):
        return EnsembleScoringEngine()

    @pytest.mark.parametrize('d_target,expected_jump', [
        (0.0, False),
        (0.10, False),
        (0.24999, False),
        (0.25000, False),
        (0.25001, True),
        (0.35, True),
        (0.60, True),
        (0.70, True),
        (0.95, True),
        (1.0, True),
    ])
    def test_dtv_boundary_transitions(self, engine, d_target, expected_jump):
        p_prev = {'BULL_LOW_VOL': 1.0, 'CRISIS': 0.0}
        p_curr = {'BULL_LOW_VOL': 1.0 - d_target, 'CRISIS': d_target}

        w_v7 = engine.get_base_weights(
            regime='CRISIS' if d_target > 0.5 else 'BULL_LOW_VOL',
            regime_probs=p_curr,
            prev_regime_probs=p_prev,
            version=7
        )

        assert all(np.isfinite(v) for v in w_v7.values()), f'NaN or Inf in weights for d_TV={d_target}'
        assert all(v >= 0.0 for v in w_v7.values()), f'Negative weight for d_TV={d_target}'
        w_sum = sum(w_v7.values())
        assert math.isclose(w_sum, 1.0000, abs_tol=1e-4), f'Simplex violation: sum={w_sum}'

        w_v6 = engine.get_base_weights(
            regime='CRISIS' if d_target > 0.5 else 'BULL_LOW_VOL',
            regime_probs=p_curr,
            prev_regime_probs=p_prev,
            version=6
        )

        if not expected_jump:
            for strat in w_v7:
                assert math.isclose(w_v7[strat], w_v6[strat], abs_tol=1e-4)
        else:
            for hedge in ['stat_arb', 'vol_target']:
                if hedge in w_v7 and hedge in w_v6:
                    assert w_v7[hedge] >= w_v6[hedge] - 1e-5

    def test_dtv_near_boundary_continuity(self, engine):
        eps = 1e-5
        p_prev = {'BULL_LOW_VOL': 1.0, 'CRISIS': 0.0}
        p_below = {'BULL_LOW_VOL': 1.0 - (0.25 - eps), 'CRISIS': 0.25 - eps}
        p_above = {'BULL_LOW_VOL': 1.0 - (0.25 + eps), 'CRISIS': 0.25 + eps}

        w_below = engine.get_base_weights(regime='BULL_LOW_VOL', regime_probs=p_below, prev_regime_probs=p_prev, version=7)
        w_above = engine.get_base_weights(regime='BULL_LOW_VOL', regime_probs=p_above, prev_regime_probs=p_prev, version=7)

        max_diff = max(abs(w_above[k] - w_below[k]) for k in w_above)
        assert max_diff < 1e-4, f'Discontinuity jump at boundary: max_diff={max_diff}'

    def test_dtv_orthogonal_disjoint_shift(self, engine):
        p_prev = {'BULL_LOW_VOL': 0.50, 'SIDEWAYS_LOW_VOL': 0.50}
        p_curr = {'BEAR_HIGH_VOL': 0.50, 'CRISIS': 0.50}

        w_crash = engine.get_base_weights(
            regime='CRISIS',
            regime_probs=p_curr,
            prev_regime_probs=p_prev,
            version=7
        )

        assert all(np.isfinite(v) for v in w_crash.values())
        assert math.isclose(sum(w_crash.values()), 1.0000, abs_tol=1e-4)
        assert all(v >= 0.0 for v in w_crash.values())

class TestSevereNoiseVsSignalDeadband:
    @pytest.fixture
    def engine(self):
        return EnsembleScoringEngine()

    def test_noise_suppression_spectrum(self):
        delta_noise = 0.045
        z_pos = np.logspace(-6, -2, 500)
        z_neg = -z_pos
        z_grid = np.concatenate([z_neg, z_pos])

        denoised = apply_quintic_hyperbolic_deadband(z_grid, delta_noise=delta_noise, alpha_pos=5.0)
        leakage = np.abs(denoised) / np.abs(z_grid)
        elimination = 1.0 - leakage

        min_elim = np.min(elimination)
        max_leak = np.max(leakage)
        assert min_elim >= 0.9990, f'Min elimination {min_elim*100:.4f}% < 99.9%'

        z_1e2 = np.array([0.010, -0.010])
        denoised_1e2 = apply_quintic_hyperbolic_deadband(z_1e2, delta_noise=delta_noise, alpha_pos=5.0)
        leak_1e2 = np.abs(denoised_1e2) / np.abs(z_1e2)
        assert (leak_1e2 < 0.0006).all()
        assert (leak_1e2 > 0.0004).all()

    def test_high_signal_transmission_spectrum(self):
        delta_noise = 0.045
        z_high = np.concatenate([
            np.linspace(-1.0, -0.150, 200),
            np.linspace(0.150, 1.0, 200)
        ])

        denoised = apply_quintic_hyperbolic_deadband(z_high, delta_noise=delta_noise, alpha_pos=5.0)
        transmission = np.abs(denoised) / np.abs(z_high)
        min_trans = np.min(transmission)
        assert min_trans >= 0.9999, f'Min transmission {min_trans*100:.5f}% < 99.99%'

    def test_extreme_numerical_stability(self):
        delta_noise = 0.045
        z_extreme = np.array([0.0, 1e-15, -1e-15, 1e-30, 50.0, -50.0, 1e3, -1e3])
        denoised = apply_quintic_hyperbolic_deadband(z_extreme, delta_noise=delta_noise, alpha_pos=5.0)

        assert all(np.isfinite(denoised))
        assert denoised[0] == 0.0
        assert denoised[1] >= 0.0 and denoised[2] <= 0.0
        assert math.isclose(denoised[4], 50.0, rel_tol=1e-9)
        assert math.isclose(denoised[5], -50.0, rel_tol=1e-9)

    def test_all_regimes_conditioned_deadband(self):
        regimes = [
            'BULL_LOW_VOL', 'BULL_HIGH_VOL',
            'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL',
            'BEAR_LOW_VOL', 'BEAR_HIGH_VOL',
            'CRISIS'
        ]
        delta_noise = 0.045
        z_noise = np.array([1e-6, 1e-4, 1e-2, -1e-6, -1e-4, -1e-2])
        z_signal = np.array([0.15, 0.30, 0.50, -0.15, -0.30, -0.50])

        for r in regimes:
            d_noise = apply_quintic_hyperbolic_deadband(z_noise, delta_noise=delta_noise, regime=r)
            d_sig = apply_quintic_hyperbolic_deadband(z_signal, delta_noise=delta_noise, regime=r)

            leakage = np.abs(d_noise) / np.abs(z_noise)
            for i, z in enumerate(z_noise):
                assert leakage[i] <= 0.0010, (
                    f"Noise leakage for z={z} in regime {r} was {leakage[i]*100:.4f}% > 0.10% "
                    f"(elimination {(1.0 - leakage[i])*100:.4f}% < 99.9%)! "
                    f"Root cause: eff_alpha_neg in {r} is lower than quintic (alpha < 5.0)."
                )
            trans = np.abs(d_sig) / np.abs(z_signal)
            assert (trans >= 0.9999).all(), f"Signal transmission fell below 99.99% in regime {r}"

class TestExtremePillarHarmonyRegularizer:
    @pytest.fixture
    def engine(self):
        return EnsembleScoringEngine()

    @pytest.fixture
    def base_df(self):
        n = 10
        idx = [f'SYM_{i}' for i in range(n)]
        df = pd.DataFrame({'symbol': idx}, index=idx)
        strat_cols = [
            'rim_score', 'valueup_catalyst_score', 'accruals_quality_score',
            'surge_score', 'vcp_ml_score', 'trend_efficiency_score',
            'order_flow_score', 'darkpool_score', 'microstructure_score',
            'event_score', 'sentiment_score', 'insider_buying_score',
            'supply_chain_score', 'cross_asset_spillover_score', 'dual_correction_score'
        ]
        for c in strat_cols:
            df[c] = 0.50
        return df

    def test_all_five_pillars_zero(self, engine, base_df):
        df = base_df.copy()
        for col in df.columns:
            if col != 'symbol':
                df[col] = 0.0

        for r in ['BULL_LOW_VOL', 'CRISIS', 'SIDEWAYS_LOW_VOL', 'BEAR_HIGH_VOL']:
            mult = engine.compute_quint_pillar_tensor_synergy(df, regime=r, version=7)
            assert not mult.isna().any()
            assert not np.isinf(mult).any()
            np.testing.assert_allclose(mult.values, 1.0000, atol=1e-5)

    def test_all_five_pillars_one(self, engine, base_df):
        df = base_df.copy()
        for col in df.columns:
            if col != 'symbol':
                df[col] = 1.0

        mult_bull = engine.compute_quint_pillar_tensor_synergy(df, regime='BULL_LOW_VOL', version=7)
        assert not mult_bull.isna().any()
        np.testing.assert_allclose(mult_bull.values, 1.220, atol=1e-4)

        mult_crisis = engine.compute_quint_pillar_tensor_synergy(df, regime='CRISIS', version=7)
        assert not mult_crisis.isna().any()
        np.testing.assert_allclose(mult_crisis.values, 1.040, atol=1e-4)

    def test_one_pillar_one_four_pillars_zero(self, engine, base_df):
        pillars = {
            'val': ['rim_score', 'valueup_catalyst_score', 'accruals_quality_score'],
            'mom': ['surge_score', 'vcp_ml_score', 'trend_efficiency_score'],
            'flow': ['order_flow_score', 'darkpool_score', 'microstructure_score'],
            'cat': ['event_score', 'sentiment_score', 'insider_buying_score'],
            'net': ['supply_chain_score', 'cross_asset_spillover_score', 'dual_correction_score'],
        }

        for target_p, p_cols in pillars.items():
            df = base_df.copy()
            for col in df.columns:
                if col != 'symbol':
                    df[col] = 0.0
            for col in p_cols:
                df[col] = 1.0

            mult = engine.compute_quint_pillar_tensor_synergy(df, regime='BULL_LOW_VOL', version=7)
            assert not mult.isna().any()
            np.testing.assert_allclose(mult.values, 1.0000, atol=1e-5)

    def test_monte_carlo_randomized_stress(self, engine):
        np.random.seed(12345)
        n = 200
        symbols = [f'MC_{i}' for i in range(n)]
        df = pd.DataFrame({'symbol': symbols}, index=symbols)

        strat_cols = [
            'rim_score', 'valueup_catalyst_score', 'accruals_quality_score',
            'surge_score', 'vcp_ml_score', 'trend_efficiency_score',
            'order_flow_score', 'darkpool_score', 'microstructure_score',
            'event_score', 'sentiment_score', 'insider_buying_score',
            'supply_chain_score', 'cross_asset_spillover_score', 'dual_correction_score'
        ]
        regimes = ['BULL_LOW_VOL', 'CRISIS', 'SIDEWAYS_HIGH_VOL', 'BEAR_LOW_VOL']

        for it in range(10):
            for c in strat_cols:
                mask = np.random.rand(n)
                vals = np.random.uniform(0.0, 1.0, n)
                vals[mask < 0.20] = 0.0
                vals[mask > 0.80] = 1.0
                df[c] = vals

            for r in regimes:
                mult = engine.compute_quint_pillar_tensor_synergy(df, regime=r, version=7)
                assert not mult.isna().any()
                assert not np.isinf(mult).any()
                assert (mult >= 1.0000 - 1e-6).all()
                assert (mult <= 1.22001).all()

class TestFullPipelineIntegrityStress:
    @pytest.fixture
    def engine(self):
        return EnsembleScoringEngine()

    def test_combine_predictions_extreme_adversarial(self, engine):
        np.random.seed(999)
        n = 30
        symbols = [f'SYM_{i:02d}' for i in range(n)]

        data = {
            'symbol': symbols,
            'market': ['SP500', 'NASDAQ', 'RUSSELL2000', 'KOSPI', 'KOSDAQ'] * 6,
            'volatility_20d': [0.001] * 10 + [0.03] * 10 + [0.25] * 10,
            'close': [1.0] * 5 + [100.0] * 20 + [500000.0] * 5,
            'volume': [10.0] * 5 + [1_000_000.0] * 20 + [50_000_000.0] * 5,
            'operating_margin': [-0.80] * 5 + [0.15] * 20 + [0.60] * 5,
            'roe': [-0.50] * 5 + [0.20] * 20 + [0.80] * 5,
            'surge_score': [0.0] * 10 + [0.5] * 10 + [1.0] * 10,
            'vcp_ml_score': [1.0] * 10 + [0.5] * 10 + [0.0] * 10,
            'stat_arb_score': [0.5] * 30,
            'rim_score': [0.0] * 5 + [0.95] * 20 + [0.1] * 5,
            'order_flow_score': [0.99] * 15 + [0.01] * 15,
            'dual_correction_score': [0.5] * 30,
            'event_score': [0.0] * 30,
            'sentiment_score': [1.0] * 30,
            'trend_efficiency_score': [0.5] * 30,
            'darkpool_score': [0.5] * 30,
            'cross_asset_spillover_score': [0.5] * 30,
            'supply_chain_gnn_score': [0.5] * 30,
            'range_expansion_score': [0.5] * 30,
            'overnight_gap_score': [0.5] * 30,
            'index_rebalance_score': [0.5] * 30,
        }
        df = pd.DataFrame(data)

        p_prev = {'BULL_LOW_VOL': 1.0}
        p_curr = {'CRISIS': 1.0}

        out = engine.combine_predictions(
            predictions_df=df,
            target_horizon='20d',
            regime='CRISIS',
            regime_probs=p_curr,
            prev_regime_probs=p_prev,
            version=7
        )

        assert not out['ensemble_score'].isna().any()
        assert not np.isinf(out['ensemble_score']).any()
        assert (out['ensemble_score'] >= 0.0).all() and (out['ensemble_score'] <= 1.0).all()
        assert not out['ensemble_expected_return'].isna().any()
        assert not np.isinf(out['ensemble_expected_return']).any()
        assert (out['ensemble_expected_return'] >= 0.0).all()
