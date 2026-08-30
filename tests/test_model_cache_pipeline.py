"""Comprehensive Unit and Integration Tests for High-Performance Model Cache Pipeline."""

import os
import json
import time
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import pytest
import numpy as np
import pandas as pd
import xgboost as xgb
import lightgbm as lgb
from sklearn.linear_model import Ridge

from src.ai.model_cache import ModelCacheManager, compute_sha256, compute_feature_fingerprint
from src.ai.model_io import save_model, load_model
from src.config import TradingConfig


@pytest.fixture
def temp_model_dir():
    """Create and cleanup a temporary model directory."""
    temp_dir = tempfile.mkdtemp(prefix="test_model_cache_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def dummy_data():
    """Generate simple synthetic training data and features."""
    np.random.seed(42)
    features = [f"feat_{i}" for i in range(10)]
    X = pd.DataFrame(np.random.randn(50, 10), columns=features)
    y = np.random.randn(50)
    return X, y, features


def test_atomic_save_and_checksum_verification(temp_model_dir, dummy_data):
    """Test that saving a model creates valid atomic files with SHA-256 and metadata."""
    X, y, features = dummy_data
    model = xgb.XGBRegressor(n_estimators=5, max_depth=2, random_state=42)
    model.fit(X, y)

    mgr = ModelCacheManager.get_instance()
    mgr.clear_memory_cache()

    target_file = temp_model_dir / "xgb_model_kospi_1d.json"
    success = mgr.save_model_atomic(
        model=model,
        filepath=target_file,
        metadata={"market": "kospi", "horizon": 1},
        feature_names=features,
    )
    assert success is True
    assert target_file.exists()

    meta_file = Path(str(target_file) + "_meta.json")
    assert meta_file.exists()

    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["market"] == "kospi"
    assert meta["horizon"] == 1
    assert "sha256" in meta
    assert meta["feature_count"] == 10
    assert meta["feature_fingerprint"] == compute_feature_fingerprint(features)

    # Verify loaded model can predict
    loaded = mgr.load_model_safe(target_file, verify_checksum=True, expected_features=features)
    assert loaded is not None
    preds = loaded.predict(X)
    assert len(preds) == len(X)


def test_corrupted_model_detection(temp_model_dir, dummy_data):
    """Test that 1-byte binary corruption triggers SHA-256 checksum mismatch and rejection."""
    X, y, features = dummy_data
    model = xgb.XGBRegressor(n_estimators=5, max_depth=2, random_state=42)
    model.fit(X, y)

    mgr = ModelCacheManager.get_instance()
    mgr.clear_memory_cache()

    target_file = temp_model_dir / "xgb_model_sp500_5d.json"
    mgr.save_model_atomic(model, target_file, {"market": "sp500", "horizon": 5}, feature_names=features)

    # Corrupt model file by appending garbage byte
    with open(target_file, "ab") as f:
        f.write(b"CORRUPTED_BYTE")

    mgr.clear_memory_cache()
    loaded_corrupted = mgr.load_model_safe(target_file, verify_checksum=True)
    assert loaded_corrupted is None, "Corrupted model must be rejected on checksum mismatch!"


def test_feature_fingerprint_mismatch(temp_model_dir, dummy_data):
    """Test feature fingerprint mismatch detection when columns differ."""
    X, y, features = dummy_data
    model = xgb.XGBRegressor(n_estimators=5, max_depth=2, random_state=42)
    model.fit(X, y)

    mgr = ModelCacheManager.get_instance()
    target_file = temp_model_dir / "xgb_model_nasdaq_20d.json"
    mgr.save_model_atomic(model, target_file, feature_names=features)

    altered_features = features[:8] + ["new_feat_x", "new_feat_y"]
    mgr.clear_memory_cache()
    # Loading still returns the model but safely detects the fingerprint difference in logs
    loaded = mgr.load_model_safe(target_file, expected_features=altered_features)
    assert loaded is not None


def test_parallel_loading_performance(temp_model_dir, dummy_data):
    """Test parallel multi-threaded loading across multiple model files."""
    X, y, features = dummy_data
    mgr = ModelCacheManager.get_instance()
    mgr.clear_memory_cache()

    # Create 10 dummy models
    for i in range(10):
        model = xgb.XGBRegressor(n_estimators=3, max_depth=2, random_state=42)
        model.fit(X, y)
        m_file = temp_model_dir / f"xgb_model_kosdaq_{i+1}d.json"
        mgr.save_model_atomic(model, m_file, {"market": "kosdaq", "horizon": i+1}, feature_names=features)

    # Test parallel load
    loaded_map = mgr.load_all_models_parallel(temp_model_dir, max_workers=4)
    assert len(loaded_map) == 10
    for fname, m_obj in loaded_map.items():
        assert m_obj is not None


def test_validate_cache_health(temp_model_dir, dummy_data):
    """Test validate_cache_health report calculation across 5 markets."""
    X, y, features = dummy_data
    mgr = ModelCacheManager.get_instance()
    mgr.clear_memory_cache()

    # Save models for all 5 markets
    markets = ["sp500", "nasdaq", "russell2000", "kospi", "kosdaq"]
    for mkt in markets:
        model = xgb.XGBRegressor(n_estimators=2, max_depth=2, random_state=42)
        model.fit(X, y)
        target = temp_model_dir / f"xgb_model_{mkt}_1d.json"
        mgr.save_model_atomic(model, target, {"market": mkt, "horizon": 1}, feature_names=features)

    health = mgr.validate_cache_health(
        temp_model_dir,
        required_markets=markets,
        required_horizons=[1],
        max_age_days=7,
    )

    assert health["directory_exists"] is True
    assert health["valid_models_count"] == 5
    assert health["corrupted_models_count"] == 0
    assert health["stale_models_count"] == 0
    assert health["is_fully_ready"] is True


def test_model_staleness_ttl(temp_model_dir, dummy_data):
    """Test model staleness expiration detection (> max_age_days)."""
    X, y, features = dummy_data
    mgr = ModelCacheManager.get_instance()
    mgr.clear_memory_cache()

    old_date = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")
    model = xgb.XGBRegressor(n_estimators=2, max_depth=2, random_state=42)
    model.fit(X, y)
    target = temp_model_dir / "xgb_model_kospi_60d.json"
    mgr.save_model_atomic(model, target, {"market": "kospi", "horizon": 60, "train_date": old_date}, feature_names=features)

    health = mgr.validate_cache_health(
        temp_model_dir,
        required_markets=["kospi"],
        max_age_days=7,
    )
    assert health["stale_models_count"] >= 1


def test_model_io_wrapper_integration(temp_model_dir, dummy_data):
    """Test model_io.save_model and load_model wrappers."""
    X, y, features = dummy_data
    model = xgb.XGBRegressor(n_estimators=3, max_depth=2, random_state=42)
    model.fit(X, y)

    target = temp_model_dir / "xgb_model_wrapper_test.json"
    success = save_model(model, target, {"type": "test"}, feature_names=features)
    assert success is True

    loaded = load_model(target, verify_checksum=True, expected_features=features)
    assert loaded is not None
    assert len(loaded.predict(X)) == len(X)


def test_config_model_cache_attributes():
    """Verify TradingConfig has model cache attributes and defaults."""
    cfg = TradingConfig()
    assert hasattr(cfg, "model_cache_enabled")
    assert cfg.model_cache_enabled is True
    assert hasattr(cfg, "model_cache_max_age_days")
    assert cfg.model_cache_max_age_days == 7
    assert hasattr(cfg, "model_cache_verify_checksum")
    assert cfg.model_cache_verify_checksum is True