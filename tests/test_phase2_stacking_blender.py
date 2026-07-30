import pytest
import numpy as np
from src.ai.stacking_blender import StackingBlender

def test_stacking_blender_fit_and_weights():
    blender = StackingBlender()
    
    # Synthetic out-of-fold predictions from 3 models
    np.random.seed(42)
    n_samples = 200
    y_true = np.random.randn(n_samples)
    
    # Model 1 has high correlation with target, Model 2 is noisy, Model 3 is moderate
    pred1 = y_true + np.random.normal(0, 0.2, n_samples)
    pred2 = np.random.randn(n_samples)
    pred3 = y_true + np.random.normal(0, 0.5, n_samples)
    
    preds_matrix = np.column_stack([pred1, pred2, pred3])
    
    weights = blender.fit_blender("sp500_h1", preds_matrix, y_true)
    
    # Weights should sum to 1.0
    assert pytest.approx(weights.sum(), abs=1e-5) == 1.0
    # Model 1 (most accurate) should receive highest weight
    assert weights[0] > weights[1]
    # Non-negative weights
    assert np.all(weights >= 0.0)

def test_stacking_blender_vix_regime_shift():
    blender = StackingBlender()
    preds_matrix = np.array([[1.0, 2.0, 3.0], [2.0, 3.0, 4.0]])
    blender.weights_cache["test_key"] = np.array([0.6, 0.3, 0.1])
    
    # Normal VIX (VIX=18) uses cached weights
    blend_normal = blender.predict_blend("test_key", preds_matrix, vix_level=18.0)
    
    # High VIX (VIX=35) triggers regime-adjusted weights
    blend_high_vix = blender.predict_blend("test_key", preds_matrix, vix_level=35.0)
    
    assert blend_normal is not None
    assert blend_high_vix is not None
    # High VIX prediction shifts towards conservative model 3
    assert blend_high_vix[0] != blend_normal[0]
