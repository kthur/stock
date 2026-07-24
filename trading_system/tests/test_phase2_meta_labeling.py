import numpy as np
import pandas as pd
import pytest
from src.ai.triple_barrier import apply_triple_barrier, get_daily_vol
from src.ai.meta_labeler import MetaLabeler

def test_daily_vol_computation():
    close = pd.Series(np.linspace(100, 120, 50))
    vol = get_daily_vol(close)
    assert len(vol) == 50
    assert (vol > 0).all()

def test_triple_barrier_method():
    dates = pd.date_range('2026-01-01', periods=40)
    df = pd.DataFrame({
        'Open': np.linspace(100, 140, 40),
        'High': np.linspace(102, 142, 40),
        'Low': np.linspace(98, 138, 40),
        'Close': np.linspace(100, 140, 40)
    }, index=dates)
    
    tb_df = apply_triple_barrier(df, pt_sl=(1.0, 1.0), num_days=5)
    assert not tb_df.empty
    assert 'label' in tb_df.columns
    assert 'meta_label' in tb_df.columns
    assert 'barrier_hit' in tb_df.columns

def test_meta_labeler_training_and_filtering():
    X = pd.DataFrame({
        'f1': np.random.randn(100),
        'f2': np.random.randn(100)
    })
    meta_y = pd.Series(np.random.choice([0, 1], size=100))
    
    labeler = MetaLabeler(probability_threshold=0.5)
    labeler.train(X, meta_y)
    assert labeler.is_fitted
    
    probs = labeler.predict_probability(X)
    assert len(probs) == 100
    assert np.all(probs >= 0.0) and np.all(probs <= 1.0)
    
    primary_sig = pd.Series(np.ones(100))
    filtered_sig = labeler.filter_signals(X, primary_sig)
    assert len(filtered_sig) == 100
    assert set(filtered_sig.unique()).issubset({0, 1})
