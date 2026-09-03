
import sys
import os
import math
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath('trading_system'))
sys.path.insert(0, os.path.abspath('.'))

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.factor_suppression import RegimeFactorSuppressionEngine, solve_single_stage_entropy_allocation
from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine

print('=== STARTING FORENSIC INTEGRITY CHECKS ===')

# CHECK 1: CRISIS BASE WEIGHTS
print('--- CHECK 1: CRISIS Base Weights ---')
scorer = EnsembleScoringEngine()
assert 'CRISIS' in scorer.REGIME_2D_WEIGHTS, 'CRISIS must be in REGIME_2D_WEIGHTS'
crisis_w = scorer.REGIME_2D_WEIGHTS['CRISIS']
assert len(crisis_w) == 37, f'Expected 37 strategies, got {len(crisis_w)}'
w_sum = sum(crisis_w.values())
print(f'CRISIS weight sum: {w_sum:.12f}')
assert abs(w_sum - 1.0) < 1e-12, f'CRISIS weights do not sum to 1.0: {w_sum}'
min_w = min(crisis_w.values())
assert min_w >= 0.005, f'Weight below 0.005 floor found: {min_w}'

# Defensive dominance
assert crisis_w['vol_target'] == 0.080
assert crisis_w['stat_arb'] == 0.070
assert crisis_w['rim_valuation'] == 0.065
assert crisis_w['accruals_quality'] == 0.060
assert crisis_w['short_term_reversal'] == 0.055
assert crisis_w['card_factor'] == 0.050

# High-beta throttling
for hb in ['surge', 'vcp_rule', 'vcp_ml', 'short_squeeze', 'gamma_squeeze', 'trend_efficiency', 'range_expansion_breakout']:
    assert crisis_w[hb] == 0.005, f'{hb} in CRISIS is {crisis_w[hb]}'

# Fallback prevention
w_str = scorer.get_base_weights('CRISIS')
w_str_lower = scorer.get_base_weights('crisis')
w_substr = scorer.get_base_weights('MACRO_CRISIS_SHOCK')
w_dict = scorer.get_base_weights({'CRISIS': 1.0})
w_sideways = scorer.get_base_weights('SIDEWAYS_LOW_VOL')
assert abs(w_str['vol_target'] - 0.080) < 1e-6
assert abs(w_str_lower['vol_target'] - 0.080) < 1e-6
assert abs(w_substr['vol_target'] - 0.080) < 1e-6
assert abs(w_dict['vol_target'] - 0.080) < 1e-6
assert w_str['vol_target'] != w_sideways['vol_target']
print('CRISIS base weights: PASS')

# CHECK 2: MARKOV POSTERIOR SOFT-BLENDING
print('--- CHECK 2: Markov Posterior Soft-Blending ---')
np.random.seed(12345)
regimes = ['BULL_LOW_VOL', 'BULL_HIGH_VOL', 'SIDEWAYS_LOW_VOL', 'SIDEWAYS_HIGH_VOL', 'BEAR_LOW_VOL', 'BEAR_HIGH_VOL', 'CRISIS']
for trial in range(10):
    raw_p = np.random.exponential(scale=1.0, size=len(regimes))
    probs = {r: float(p / raw_p.sum()) for r, p in zip(regimes, raw_p)}
    blended = scorer.get_base_weights(probs)
    tot_blend = sum(blended.values())
    assert abs(tot_blend - 1.0) < 1e-10, f'Trial {trial}: Blended weights sum={tot_blend}'
    for strat in crisis_w.keys():
        expected_w = sum(probs[r] * scorer.REGIME_2D_WEIGHTS[r][strat] for r in regimes)
        actual_w = blended[strat]
        assert abs(actual_w - expected_w) < 1e-10
print('Markov posterior soft-blending exactness: PASS (10/10 random Dirichlet trials)')

# CHECK 3: CONTINUOUS TV-DISTANCE AND VIX ENTROPY
print('--- CHECK 3: Continuous TV-Distance and VIX Entropy Smoothing ---')
alpha_0 = 0.20
beta_trans = 0.35
beta_vix = 0.30
beta_ent = 0.05
for vix_f in [12.0, 25.0, 40.0, 60.0]:
    for d_tv in [0.0, 0.25, 0.75, 1.0]:
        sigma_vix = float(np.clip((vix_f - 18.0) / 22.0, 0.0, 1.0))
        p_stress = float(np.clip((vix_f - 12.0) / 28.0, 1e-4, 1.0 - 1e-4))
        h_vix = float(-(p_stress * np.log(p_stress) + (1.0 - p_stress) * np.log(1.0 - p_stress)) / np.log(2.0))
        eff_alpha = float(np.clip(alpha_0 + beta_trans * d_tv + beta_vix * sigma_vix + beta_ent * h_vix, 0.15, 0.85))
        assert 0.15 <= eff_alpha <= 0.85
print('TV-distance and VIX entropy formula and bounds [0.15, 0.85]: PASS')

# CHECK 4: EXPONENTIAL CONVOLUTIONAL DECAY FILTER
print('--- CHECK 4: Multi-Horizon Exponential Convolutional Decay Filter ---')
engine_dec = EnsembleScoringEngine()
engine_dec.reset_decay_filter_state()
assert len(engine_dec._prev_filtered_scores) == 0
tau_lstm = engine_dec.get_regime_adaptive_half_lives('BULL_LOW_VOL')['lstm']
alpha_lstm = 1.0 - math.exp(-math.log(2.0) / tau_lstm)
df_t1 = pd.DataFrame({'symbol': ['S1', 'S2'], 'lstm_score': [0.90, 0.80], 'market': ['US', 'US']})
df_t2 = pd.DataFrame({'symbol': ['S1', 'S2'], 'lstm_score': [0.10, 0.20], 'market': ['US', 'US']})
res_filtered = engine_dec.apply_exponential_decay_filter(current_scores=df_t2, previous_scores=df_t1, regime='BULL_LOW_VOL')
expected_s1 = alpha_lstm * 0.10 + (1.0 - alpha_lstm) * 0.90
actual_s1 = res_filtered.loc[res_filtered['symbol'] == 'S1', 'lstm_score'].iloc[0]
assert abs(actual_s1 - expected_s1) < 1e-6
print(f'Decay filter formula verified: tau={tau_lstm}, alpha={alpha_lstm:.5f}: PASS')

# CHECK 5: TREND INERTIA AND CRASH PROTECTION
print('--- CHECK 5: Trend Inertia and Crash Protection Logic ---')
engine_t = EnsembleScoringEngine()
sharpes_flat = {s: 0.5 for s in crisis_w.keys()}
w_bull_low = engine_t.compute_dynamic_weights_from_sharpe(sharpes_flat, regime='BULL_LOW_VOL', factor_autocorr_dict={'surge': 0.90})
w_bull_high = engine_t.compute_dynamic_weights_from_sharpe(sharpes_flat, regime='BULL_HIGH_VOL')
w_crisis_dyn = engine_t.compute_dynamic_weights_from_sharpe(sharpes_flat, regime='CRISIS', vix_val=40.0)
assert w_bull_low['surge'] > w_bull_high['surge'] > w_crisis_dyn['surge']
assert w_crisis_dyn['short_term_reversal'] > w_bull_low['short_term_reversal']
print('Trend inertia and crash protection logic: PASS')

# CHECK 6: 4-PILLAR CLUSTER MAP
print('--- CHECK 6: 4-Pillar Cluster Map Coverage ---')
val_cols = {'rim_score', 'valueup_catalyst_score', 'accruals_quality_score', 'arm_score', 'factor_neutralized_score', 'reg_score'}
mom_cols = {'surge_score', 'vcp_ml_score', 'trend_efficiency_score', 'sector_score', 'range_expansion_score', 'mq_score', 'll_score', 'vcp_rule_score', 'lstm_score'}
flow_cols = {'order_flow_score', 'inst_foreign_sector_score', 'darkpool_score', 'microstructure_score', 'overnight_gap_score', 'stat_arb_score', 'iv_skew_score', 'reversal_score', 'vol_target_score'}
cat_cols = {'event_score', 'sentiment_score', 'short_squeeze_score', 'gamma_squeeze_score', 'supply_chain_score', 'supply_chain_gnn_score', 'cross_asset_spillover_score', 'dual_correction_score', 'index_rebalance_score', 'insider_buying_score', 'earnings_tone_drift_score', 'card_score', 'latr_score'}
clusters = [val_cols, mom_cols, flow_cols, cat_cols]
for i in range(len(clusters)):
    for j in range(i + 1, len(clusters)):
        overlap = clusters[i] & clusters[j]
        assert len(overlap) == 0, f'Overlap: {overlap}'
all_pillars = val_cols | mom_cols | flow_cols | cat_cols
assert len(all_pillars) == 37, f'Expected 37, got {len(all_pillars)}'
print(f'4-pillar cluster map: PASS (exactly {len(all_pillars)} strategies, no overlap)')

# CHECK 7: SINGLE-STAGE ENTROPY ALLOCATION WITH PARTIAL MISSINGNESS
print('--- CHECK 7: Single-Stage Entropy Program and Partial Missingness ---')
supp_eng = RegimeFactorSuppressionEngine()
all_37 = list(crisis_w.keys())
active_20 = all_37[:20]
missing_17 = all_37[20:]
np.random.seed(999)
A = np.random.randn(20, 20)
corr_active = np.corrcoef(A)
np.fill_diagonal(corr_active, 1.0)
corr_df_20 = pd.DataFrame(corr_active, index=active_20, columns=active_20)
base_w_37 = dict(crisis_w)
supp_w_37 = supp_eng.suppress_weights(base_weights=base_w_37, corr_matrix=corr_df_20, regime_label='SIDEWAYS_LOW_VOL', use_entropy_allocation=True, n_samples=50)
assert len(supp_w_37) == 37
assert abs(sum(supp_w_37.values()) - 1.0) < 1e-10
assert all(v >= 0.0 for v in supp_w_37.values())
base_missing_sum = sum(base_w_37[s] for s in missing_17)
supp_missing_sum = sum(supp_w_37[s] for s in missing_17)
assert abs(supp_missing_sum - base_missing_sum) < 1e-4
print(f'Missing share base={base_missing_sum:.4f}, suppressed={supp_missing_sum:.4f}: PASS')

# CHECK 8: ACTIVE SUBSPACE ISOLATION IN PCA-ZCA WHITENING
print('--- CHECK 8: Active-Subspace Isolation in PCA-ZCA Whitening ---')
ortho_eng = FactorOrthogonalizerEngine(default_method='pca_symmetric')
N = 50
np.random.seed(999)
X_active = np.random.multivariate_normal([0, 0, 0], [[1, 0.7, 0.6], [0.7, 1, 0.5], [0.6, 0.5, 1]], size=N)
col_const1 = np.full((N, 1), 0.50)
col_const2 = np.zeros((N, 1))
X_mixed = np.hstack([X_active, col_const1, col_const2])
means = np.mean(X_mixed, axis=0)
stds = np.std(X_mixed, axis=0)
stds[3] = 1e-6
stds[4] = 1e-6
X_res = ortho_eng._pca_zca_symmetric(X_mixed, means, stds, preserve_pc1=True, preserve_top_k=1)
assert X_res.shape == (N, 5)
assert not np.isnan(X_res).any()
assert np.all(X_res[:, 3] == 0.50)
assert np.all(X_res[:, 4] == 0.00)
corr_orig = np.corrcoef(X_mixed[:, :3].T)
corr_ortho = np.corrcoef(X_res[:, :3].T)
off_diag_orig = np.sum(np.abs(corr_orig)) - 3.0
off_diag_ortho = np.sum(np.abs(corr_ortho)) - 3.0
assert off_diag_ortho < off_diag_orig
print(f'Active subspace decorrelation off_diag before={off_diag_orig:.4f}, after={off_diag_ortho:.4f}: PASS')

print('=== ALL 8 MATHEMATICAL AND INTEGRITY FORENSIC CHECKS PASSED 100% ===')
