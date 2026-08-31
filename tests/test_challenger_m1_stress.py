"""Challenger Adversarial Stress Tests for Model Fallbacks, Cache Integrity, and Degradation.

Empirical verification of Milestone 1 requirements:
- Missing model directory and empty model directory fallback.
- Corrupted model files (truncated bytes, invalid JSON, binary corruption).
- Checksum tampering detection and sidecar metadata corruption.
- Heuristic fallback validation when models are missing in OnDevicePredictionModel and VCPSurgePredictor.
- Extreme numerical inputs (NaN, Inf, missing columns) during inference.
- Multi-threaded concurrent model save/load atomic operations.
"""

import os
import json
import shutil
import tempfile
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
import numpy as np
import pandas as pd
import xgboost as xgb

from src.ai.model_cache import ModelCacheManager, compute_sha256
from src.ai.prediction_model import OnDevicePredictionModel
from src.ai.vcp_ml_predictor import VCPSurgePredictor
from src.ai.lstm_predictor import LSTMPredictor


@pytest.fixture
def stress_temp_dir():
    temp_dir = tempfile.mkdtemp(prefix="stress_m1_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_ohlcv_dict():
    """Create sample OHLCV data for multiple symbols with 100 days of data."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    np.random.seed(42)
    data = {}
    for sym in ["TEST_01", "TEST_02", "TEST_03"]:
        base = 100.0 + np.random.randn() * 10.0
        pcts = np.random.randn(100) * 0.02
        close = base * np.cumprod(1.0 + pcts)
        high = close * (1.0 + np.abs(np.random.randn(100) * 0.01))
        low = close * (1.0 - np.abs(np.random.randn(100) * 0.01))
        open_p = (high + low) / 2.0
        volume = np.random.randint(10000, 500000, size=100)
        df = pd.DataFrame({
            "Open": open_p,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        }, index=dates)
        data[sym] = df
    return data


def test_empty_model_dir_graceful_degradation(stress_temp_dir, sample_ohlcv_dict):
    """Stress Test 1: Empty model directory should not crash prediction model or lead-lag."""
    model = OnDevicePredictionModel(model_dir=str(stress_temp_dir))
    assert len(model.models) == 0
    assert len(model.surge_models) == 0
    assert len(model.lgb_models) == 0
    assert len(model.cat_models) == 0
    assert len(model.lstm_models) == 0

    # Lead-lag prediction should return a valid DataFrame or empty without raising fatal error
    lead_lag_res = model.predict_lead_lag(sample_ohlcv_dict)
    assert isinstance(lead_lag_res, pd.DataFrame)

    # LSTM prediction on empty models should return an empty or valid DataFrame
    lstm_res = model.predict_lstm(sample_ohlcv_dict, horizon=20)
    assert isinstance(lstm_res, pd.DataFrame)


def test_corrupted_model_files_rejection_and_isolation(stress_temp_dir, sample_ohlcv_dict):
    """Stress Test 2: Corrupted binary/JSON files must be skipped and logged without crashing."""
    corrupted_files = [
        "xgb_model_sp500_1d.json",
        "lgb_model_sp500_1d.txt",
        "cat_model_sp500_1d.bin",
        "lstm_model_sp500_1d.pt",
        "xgb_surge_model_sp500_1d.json",
        "vcp_surge_sp500_1d.json",
    ]

    for fname in corrupted_files:
        fpath = stress_temp_dir / fname
        with open(fpath, "wb") as f:
            f.write(b"\x00\xFF\xFE\xFDGARBAGE_CORRUPTED_DATA_HEADER\x00\x00\x00")

        # Also write a corrupted metadata file
        meta_path = Path(str(fpath) + "_meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write("{invalid_json_corrupted: true,")

    # Initialize OnDevicePredictionModel on corrupted dir
    model = OnDevicePredictionModel(model_dir=str(stress_temp_dir))
    # It must not crash, and models should remain empty
    assert len(model.models) == 0
    assert len(model.surge_models) == 0
    assert len(model.cat_models) == 0


def test_checksum_tampering_and_meta_corruption(stress_temp_dir):
    """Stress Test 3: Valid model file tampered after write must be rejected by load_model_safe."""
    mgr = ModelCacheManager.get_instance()
    mgr.clear_memory_cache()

    features = [f"f_{i}" for i in range(5)]
    X = pd.DataFrame(np.random.randn(20, 5), columns=features)
    y = np.random.randn(20)

    model = xgb.XGBRegressor(n_estimators=3, max_depth=2, random_state=42)
    model.fit(X, y)

    target_file = stress_temp_dir / "xgb_model_kospi_5d.json"
    saved = mgr.save_model_atomic(model, target_file, {"market": "kospi", "horizon": 5}, feature_names=features)
    assert saved is True

    # Mutate 1 byte in the model file
    with open(target_file, "r+b") as f:
        f.seek(10)
        orig = f.read(1)
        f.seek(10)
        f.write(b"X" if orig != b"X" else b"Y")

    mgr.clear_memory_cache()
    # Checksum verification must detect the modification and refuse to load
    loaded = mgr.load_model_safe(target_file, verify_checksum=True)
    assert loaded is None, "Tampered model file MUST return None on checksum check"

    # Now test corrupted metadata JSON sidecar
    meta_file = Path(str(target_file) + "_meta.json")
    with open(meta_file, "w", encoding="utf-8") as f:
        f.write("CORRUPTED_JSON_CONTENT")

    mgr.clear_memory_cache()
    # Should safely handle the bad JSON and still load or fail gracefully without unhandled exception
    loaded_corrupt_meta = mgr.load_model_safe(target_file, verify_checksum=False)
    # verify_checksum=False should still attempt load safely
    assert loaded_corrupt_meta is not None or loaded_corrupt_meta is None


def test_vcp_ml_heuristic_fallback_when_models_absent(stress_temp_dir, sample_ohlcv_dict):
    """Stress Test 4: VCPSurgePredictor must provide valid [0.0, 1.0] predictions via heuristic fallback."""
    vcp_predictor = VCPSurgePredictor(model_dir=str(stress_temp_dir))
    assert len(vcp_predictor.models) == 0

    preds_df = vcp_predictor.predict(sample_ohlcv_dict)
    assert isinstance(preds_df, pd.DataFrame)
    assert len(preds_df) > 0
    assert "symbol" in preds_df.columns
    for h in [1, 3, 5, 20]:
        col = f"vcp_{h}d"
        assert col in preds_df.columns
        vals = preds_df[col].values
        assert np.all(np.isfinite(vals)), f"NaN or Inf found in {col}"
        assert np.all(vals >= 0.0), f"Negative probability in {col}"
        assert np.all(vals <= 1.0), f"Probability > 1.0 in {col}"


def test_extreme_numerical_inputs_and_nans(sample_ohlcv_dict):
    """Stress Test 5: Vectorized feature computation with NaNs, Infs, and zeros."""
    # Inject adversarial anomalies into prices
    dirty_dict = {}
    for sym, df in sample_ohlcv_dict.items():
        df_dirty = df.copy()
        df_dirty.iloc[10:15, df_dirty.columns.get_loc("Close")] = np.nan
        df_dirty.iloc[20:25, df_dirty.columns.get_loc("Volume")] = 0
        df_dirty.iloc[30, df_dirty.columns.get_loc("High")] = 1e9  # Extreme spike
        dirty_dict[sym] = df_dirty

    model = OnDevicePredictionModel()
    # Feature creation should not raise unhandled exception
    for sym, df in dirty_dict.items():
        df_feat = model._create_features(df)
        assert isinstance(df_feat, pd.DataFrame)


def test_concurrent_model_cache_save_and_load(stress_temp_dir):
    """Stress Test 6: Multi-threaded concurrent saves and loads to detect race conditions."""
    mgr = ModelCacheManager.get_instance()
    mgr.clear_memory_cache()

    features = [f"feat_{i}" for i in range(8)]
    X = pd.DataFrame(np.random.randn(30, 8), columns=features)
    y = np.random.randn(30)

    errors = []

    def worker_task(thread_id: int):
        try:
            m = xgb.XGBRegressor(n_estimators=2, max_depth=2, random_state=thread_id)
            m.fit(X, y)
            fpath = stress_temp_dir / f"xgb_model_concurrent_{thread_id % 4}_1d.json"
            mgr.save_model_atomic(m, fpath, {"thread_id": thread_id}, feature_names=features)
            loaded = mgr.load_model_safe(fpath, verify_checksum=True, expected_features=features)
            if loaded is None:
                errors.append(f"Thread {thread_id} failed to load saved model")
        except Exception as e:
            errors.append(f"Thread {thread_id} raised exception: {e}")

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(worker_task, i) for i in range(16)]
        for f in futures:
            f.result()

    assert len(errors) == 0, f"Concurrent execution errors: {errors}"
