
import sys
import os
import math
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath('trading_system'))
sys.path.insert(0, os.path.abspath('.'))

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.factor_suppression import RegimeFactorSuppressionEngine
from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine

print('=== ADVERSARIAL STRESS TESTING ===')
scorer = EnsembleScoringEngine()

# Test A1: Empty/malformed inputs to compute_bilinear_cross_pillar_synergy
print('Test A1: Synergy edge cases...')
res_empty = scorer.compute_bilinear_cross_pillar_synergy(pd.DataFrame())
assert len(res_empty) == 0
res_few = scorer.compute_bilinear_cross_pillar_synergy(pd.DataFrame({'rim_score': [0.5, 0.6]}))
assert (res_few == 1.0).all()
res_none = scorer.compute_bilinear_cross_pillar_synergy(None)
assert res_none.iloc[0] == 1.0
print('Test A1: PASS')

# Test A2: Bessembinder with extreme values (all 0, all 1, negative, NaNs)
print('Test A2: Bessembinder edge cases...')
scores_zero = np.zeros(10)
b_zero = scorer.apply_bessembinder_convex_power_law(scores_zero, regime='BULL_LOW_VOL')
assert not np.isnan(b_zero).any()
assert (b_zero >= 0.0).all()

scores_one = np.ones(10)
b_one = scorer.apply_bessembinder_convex_power_law(scores_one, regime='CRISIS')
assert not np.isnan(b_one).any()
assert (b_one <= 1.0).all()
print('Test A2: PASS')

# Test A3: TV-distance & VIX entropy with extreme VIX values
print('Test A3: VIX extreme stress...')
sharpes = {s: 1.0 for s in scorer.REGIME_2D_WEIGHTS['CRISIS']}
w_huge_vix = scorer.compute_dynamic_weights_from_sharpe(sharpes, regime='CRISIS', vix_val=180.0, enable_tv_smoothing=True)
assert abs(sum(w_huge_vix.values()) - 1.0) < 1e-6
assert all(np.isfinite(v) for v in w_huge_vix.values())

w_neg_vix = scorer.compute_dynamic_weights_from_sharpe(sharpes, regime='BULL_LOW_VOL', vix_val=-10.0, enable_tv_smoothing=True)
assert abs(sum(w_neg_vix.values()) - 1.0) < 1e-6
assert all(np.isfinite(v) for v in w_neg_vix.values())
print('Test A3: PASS')

# Test A4: Decay filter with empty/corrupt previous scores
print('Test A4: Decay filter edge cases...')
df_curr = pd.DataFrame({'symbol': ['X'], 'regression_score': [0.5]})
df_corrupt = pd.DataFrame({'symbol': ['X', 'X'], 'regression_score': [np.nan, np.inf]})
res_corrupt = scorer.apply_exponential_decay_filter(current_scores=df_curr, previous_scores=df_corrupt, regime='BULL_LOW_VOL')
assert not res_corrupt.empty
assert np.isfinite(res_corrupt['regression_score'].iloc[0])
print('Test A4: PASS')

# Test A5: Factor orthogonalizer with near-zero, non-PSD, or extreme condition matrices
print('Test A5: Orthogonalizer extreme matrix shapes...')
ortho = FactorOrthogonalizerEngine()
# N=1, K=5
X_single = np.ones((1, 5))
means = np.mean(X_single, axis=0)
stds = np.std(X_single, axis=0)
res_single = ortho._pca_zca_symmetric(X_single, means, stds)
assert res_single.shape == (1, 5)
assert not np.isnan(res_single).any()

# All identical rows
X_ident = np.full((10, 4), 3.14159)
res_ident = ortho._pca_zca_symmetric(X_ident, np.mean(X_ident, axis=0), np.std(X_ident, axis=0))
assert res_ident.shape == (10, 4)
assert not np.isnan(res_ident).any()
print('Test A5: PASS')

print('=== ALL ADVERSARIAL STRESS TESTS PASSED ===')
