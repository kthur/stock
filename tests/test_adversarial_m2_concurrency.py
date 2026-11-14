# -*- coding: utf-8 -*-
"""
tests/test_adversarial_m2_concurrency.py — Empirical Adversarial Stress Test Suite
for Milestone 2: Model Cache Manager Concurrency, Cache Health Boundary Transitions,
and Production Model Directory Protection.

Target Objectives:
1. Concurrent Atomic Save/Load Stress: Spawns 10 parallel threads concurrently saving
   and loading model checkpoints via ModelCacheManager into an isolated temporary directory,
   asserting 0 file corruption, 0 race conditions, and 0 orphaned temporary files.
2. Cache Health Boundary Checks: Tests validate_cache_health() across multiple market
   directory subsets (empty, partial, full, corrupted, schema-drifted) confirming that
   is_fully_ready transitions strictly when all required markets have regression >= 1
   and corrupted_models_count == 0.
3. Production Directory Immunity: Verifies that models/ and trading_system/models/
   are never polluted, mutated, or contaminated during any test run.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pytest
import xgboost as xgb
from sklearn.linear_model import Ridge

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
TRADING_SYS_DIR = PROJECT_ROOT / "trading_system"
if str(TRADING_SYS_DIR) not in sys.path:
    sys.path.insert(0, str(TRADING_SYS_DIR))

from src.ai.model_cache import (
    ModelCacheManager,
    compute_sha256,
    compute_feature_fingerprint,
)


def _compute_dir_manifest(directory: Path) -> Dict[str, Tuple[int, str]]:
    """Compute mapping of relpath -> (file_size, sha256_hash) for all files in directory."""
    manifest = {}
    if not directory.exists():
        return manifest
    for p in sorted(directory.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(directory))
            try:
                size = p.stat().st_size
                h = compute_sha256(p)
                manifest[rel] = (size, h)
            except Exception:
                pass
    return manifest


class TestAdversarialConcurrencyAndCacheHealth:
    """Empirical adversarial test suite for concurrency, cache health boundaries, and directory isolation."""

    @pytest.fixture
    def isolated_temp_dir(self):
        """Provide clean, isolated temporary directory for testing."""
        td = tempfile.mkdtemp(prefix="adv_m2_cache_")
        path = Path(td)
        yield path
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

    def test_concurrent_atomic_save_load_stress_10_threads(self, isolated_temp_dir):
        """Spawns 10 parallel threads concurrently saving and loading model checkpoints,
        asserting 0 file corruption, 0 race conditions, and 0 orphaned temporary files.
        Simulates 10 parallel retrain workers across markets and horizons.
        """
        mgr = ModelCacheManager.get_instance()
        num_threads = 10
        barrier = threading.Barrier(num_threads)
        errors: List[str] = []
        features_list = [f"f_{i}" for i in range(10)]

        # Define 10 distinct worker tasks across markets & model types
        tasks = [
            ("sp500", "xgb_model", [1, 5, 10, 20], False),
            ("nasdaq", "xgb_model", [1, 5, 10, 20], False),
            ("russell2000", "xgb_model", [1, 5, 10, 20], False),
            ("kospi", "xgb_model", [1, 5, 10, 20], False),
            ("kosdaq", "xgb_model", [1, 5, 10, 20], False),
            ("sp500", "xgb_surge_model", [1, 3, 5, 20], True),
            ("nasdaq", "xgb_surge_model", [1, 3, 5, 20], True),
            ("russell2000", "xgb_surge_model", [1, 3, 5, 20], True),
            ("kospi", "xgb_surge_model", [1, 3, 5, 20], True),
            ("kosdaq", "xgb_surge_model", [1, 3, 5, 20], True),
        ]

        saved_files: List[Tuple[Path, bool]] = []
        saved_files_lock = threading.Lock()

        def _worker(thread_id: int):
            try:
                # Synchronize start across all 10 threads
                barrier.wait(timeout=10.0)
            except Exception as e:
                errors.append(f"Thread {thread_id} barrier timeout: {e}")
                return

            market, prefix, horizons, is_classifier = tasks[thread_id]

            for h in horizons:
                try:
                    X_dummy = np.random.RandomState(thread_id * 100 + h).randn(30, 10)
                    if is_classifier:
                        y_dummy = (X_dummy[:, 0] > 0).astype(int)
                        m = xgb.XGBClassifier(
                            n_estimators=2,
                            max_depth=2,
                            learning_rate=0.1,
                            n_jobs=1,
                            tree_method="hist",
                            eval_metric="logloss",
                        )
                        m.fit(X_dummy, y_dummy)
                    else:
                        y_dummy = X_dummy[:, 0] * 2.0 + np.random.randn(30) * 0.1
                        m = xgb.XGBRegressor(
                            n_estimators=2,
                            max_depth=2,
                            learning_rate=0.1,
                            n_jobs=1,
                            tree_method="hist",
                        )
                        m.fit(X_dummy, y_dummy)

                    target_path = isolated_temp_dir / f"{prefix}_{market}_{h}d.json"

                    # 1. Atomic Save
                    save_ok = mgr.save_model_atomic(
                        model=m,
                        filepath=target_path,
                        feature_names=features_list,
                        metadata={
                            "thread_id": thread_id,
                            "market": market,
                            "horizon": h,
                            "saved_time": time.time(),
                        },
                    )
                    if not save_ok:
                        errors.append(f"Thread {thread_id} ({market}_{h}d): save_model_atomic returned False")

                    with saved_files_lock:
                        saved_files.append((target_path, is_classifier))

                    # 2. Immediate Safe Load of just-saved model
                    loaded = mgr.load_model_safe(
                        filepath=target_path,
                        verify_checksum=True,
                        expected_features=features_list,
                        is_classifier=is_classifier,
                        use_memory_cache=(h % 2 == 0),
                    )
                    if loaded is None:
                        errors.append(f"Thread {thread_id} ({market}_{h}d): load_model_safe returned None")
                    else:
                        preds = loaded.predict(X_dummy)
                        if not np.all(np.isfinite(preds)):
                            errors.append(f"Thread {thread_id} ({market}_{h}d): non-finite predictions detected")

                    # 3. Check sidecar metadata integrity
                    meta_path = Path(str(target_path) + "_meta.json")
                    if not meta_path.exists():
                        errors.append(f"Thread {thread_id} ({market}_{h}d): metadata sidecar missing")
                    else:
                        with open(meta_path, "r", encoding="utf-8") as mf:
                            meta_data = json.load(mf)
                        actual_sha = compute_sha256(target_path)
                        if meta_data.get("sha256") != actual_sha:
                            errors.append(
                                f"Thread {thread_id} ({market}_{h}d): Checksum mismatch in sidecar: {meta_data.get('sha256')} vs {actual_sha}"
                            )

                except Exception as ex:
                    errors.append(f"Thread {thread_id} ({market}_{h}d) raised exception: {type(ex).__name__}: {ex}")

        # Phase 1: 10 threads concurrently save and load models
        threads = [threading.Thread(target=_worker, args=(i,), name=f"AdvWorker-{i}") for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=45.0)

        # Assert zero errors across all 10 threads
        assert not errors, f"Concurrency stress errors observed ({len(errors)} errors): {errors[:10]}"

        # Assert exactly 40 models were saved across 10 threads (4 per thread)
        assert len(saved_files) == 40, f"Expected 40 models saved, found {len(saved_files)}"

        # Phase 2: All 10 threads concurrently cross-load ALL 40 models from disk
        load_errors: List[str] = []
        barrier_load = threading.Barrier(num_threads)

        def _load_worker(thread_id: int):
            try:
                barrier_load.wait(timeout=10.0)
            except Exception as e:
                load_errors.append(f"LoadThread {thread_id} barrier timeout: {e}")
                return

            X_test = np.random.RandomState(42).randn(10, 10)
            for fpath, is_clf in saved_files:
                try:
                    loaded = mgr.load_model_safe(
                        filepath=fpath,
                        verify_checksum=True,
                        expected_features=features_list,
                        is_classifier=is_clf,
                        use_memory_cache=False,  # Force disk read and SHA-256 verification
                    )
                    if loaded is None:
                        load_errors.append(f"LoadThread {thread_id}: failed to load {fpath.name}")
                    else:
                        preds = loaded.predict(X_test)
                        if not np.all(np.isfinite(preds)):
                            load_errors.append(f"LoadThread {thread_id}: non-finite predictions in {fpath.name}")
                except Exception as ex:
                    load_errors.append(f"LoadThread {thread_id} failed on {fpath.name}: {ex}")

        load_threads = [threading.Thread(target=_load_worker, args=(i,), name=f"AdvLoadWorker-{i}") for i in range(num_threads)]
        for t in load_threads:
            t.start()
        for t in load_threads:
            t.join(timeout=45.0)

        assert not load_errors, f"Concurrent cross-load errors ({len(load_errors)}): {load_errors[:10]}"

        # Assert ZERO orphaned temporary files in directory
        temp_files = list(isolated_temp_dir.glob("*.tmp*"))
        assert len(temp_files) == 0, f"Found {len(temp_files)} orphaned temporary files: {[f.name for f in temp_files]}"

        # Assert all saved files exist, have matching checksums, and non-zero size
        json_models = [f for f in isolated_temp_dir.glob("*.json") if not f.name.endswith("_meta.json")]
        assert len(json_models) == 40, f"Expected 40 json model files, found {len(json_models)}"
        for pf in json_models:
            assert pf.stat().st_size > 0, f"File {pf.name} is 0 bytes"
            meta_f = Path(str(pf) + "_meta.json")
            assert meta_f.exists(), f"Sidecar for {pf.name} missing"
            with open(meta_f, "r", encoding="utf-8") as f:
                meta = json.load(f)
            assert meta["sha256"] == compute_sha256(pf), f"SHA mismatch on final validation for {pf.name}"

    def test_cache_health_boundary_transitions(self, isolated_temp_dir):
        """Adversarially tests validate_cache_health() transitions across directory states:
        empty -> partial markets -> full markets -> corruption injection -> recovery.
        """
        mgr = ModelCacheManager.get_instance()
        features = [f"feat_{i}" for i in range(5)]
        dummy_model = xgb.XGBRegressor(n_estimators=2, max_depth=2, n_jobs=1, tree_method="hist")
        dummy_model.fit(np.eye(5), np.ones(5))

        # 1. Empty Directory Boundary
        rep_empty = mgr.validate_cache_health(isolated_temp_dir)
        assert rep_empty["is_fully_ready"] is False
        assert rep_empty["total_files"] == 0
        assert rep_empty["valid_models_count"] == 0
        assert rep_empty["corrupted_models_count"] == 0

        # 2. Non-existent Directory Boundary
        rep_nonexist = mgr.validate_cache_health(isolated_temp_dir / "non_existent_subdir")
        assert rep_nonexist["is_fully_ready"] is False
        assert rep_nonexist["directory_exists"] is False
        assert any("does not exist" in issue for issue in rep_nonexist["issues"])

        # 3. Partial Market Subsets (SP500 only)
        # Create regression model for sp500
        sp500_reg = isolated_temp_dir / "xgb_model_sp500_1d.json"
        mgr.save_model_atomic(dummy_model, sp500_reg, feature_names=features)

        # Default required markets requires all 5 (sp500, nasdaq, russell2000, kospi, kosdaq) -> must be False
        rep_sp500_only = mgr.validate_cache_health(isolated_temp_dir)
        assert rep_sp500_only["is_fully_ready"] is False
        assert rep_sp500_only["market_status"]["sp500"]["regression"] == 1
        assert rep_sp500_only["market_status"]["nasdaq"]["regression"] == 0

        # But if required_markets is explicitly ['sp500'], it must transition to True
        rep_req_sp500 = mgr.validate_cache_health(isolated_temp_dir, required_markets=["sp500"])
        assert rep_req_sp500["is_fully_ready"] is True
        assert rep_req_sp500["corrupted_models_count"] == 0

        # 4. Partial Market Subsets (SP500 + NASDAQ)
        nasdaq_reg = isolated_temp_dir / "xgb_model_nasdaq_1d.json"
        mgr.save_model_atomic(dummy_model, nasdaq_reg, feature_names=features)

        rep_two = mgr.validate_cache_health(isolated_temp_dir)
        assert rep_two["is_fully_ready"] is False  # Missing 3 markets
        assert mgr.validate_cache_health(isolated_temp_dir, required_markets=["sp500", "nasdaq"])["is_fully_ready"] is True

        # 5. Populate All 5 Required Markets with regression models
        for m in ["russell2000", "kospi", "kosdaq"]:
            f = isolated_temp_dir / f"xgb_model_{m}_1d.json"
            mgr.save_model_atomic(dummy_model, f, feature_names=features)

        rep_all_5 = mgr.validate_cache_health(isolated_temp_dir)
        assert rep_all_5["is_fully_ready"] is True
        assert rep_all_5["corrupted_models_count"] == 0
        for m in ["sp500", "nasdaq", "russell2000", "kospi", "kosdaq"]:
            assert rep_all_5["market_status"][m]["regression"] >= 1

        # 6. Check VCP categorization distinction
        # vcp_surge_{market}_1d.json must be categorized as vcp, NOT surge
        vcp_model_path = isolated_temp_dir / "vcp_surge_sp500_1d.json"
        mgr.save_model_atomic(dummy_model, vcp_model_path, feature_names=features)
        rep_vcp = mgr.validate_cache_health(isolated_temp_dir)
        assert rep_vcp["market_status"]["sp500"]["vcp"] == 1
        assert rep_vcp["market_status"]["sp500"]["surge"] == 0

        # Now add actual surge model
        surge_model_path = isolated_temp_dir / "xgb_surge_model_sp500_1d.json"
        mgr.save_model_atomic(dummy_model, surge_model_path, feature_names=features)
        rep_surge = mgr.validate_cache_health(isolated_temp_dir)
        assert rep_surge["market_status"]["sp500"]["vcp"] == 1
        assert rep_surge["market_status"]["sp500"]["surge"] == 1

        # 7. Corruption Injection Boundary: Corrupt sp500_reg file content
        with open(sp500_reg, "a", encoding="utf-8") as cf:
            cf.write("\nMALICIOUS_BYTE_CORRUPTION_INJECTION\n")

        rep_corrupt = mgr.validate_cache_health(isolated_temp_dir)
        assert rep_corrupt["corrupted_models_count"] >= 1, "Corrupted model must be detected"
        assert rep_corrupt["is_fully_ready"] is False, "is_fully_ready must drop to False on corruption"
        assert any("Corrupted checksum" in issue for issue in rep_corrupt["issues"])

        # 8. Recovery Boundary: Re-save sp500_reg cleanly
        mgr.save_model_atomic(dummy_model, sp500_reg, feature_names=features)
        rep_recovered = mgr.validate_cache_health(isolated_temp_dir)
        assert rep_recovered["corrupted_models_count"] == 0
        assert rep_recovered["is_fully_ready"] is True, "is_fully_ready must recover to True after resaving clean model"

        # 9. Schema Drift Boundary: Expected features mismatch
        drifted_features = [f"drift_{i}" for i in range(5)]
        rep_drift = mgr.validate_cache_health(isolated_temp_dir, expected_features=drifted_features)
        assert any("Feature schema mismatch" in issue for issue in rep_drift["issues"])

    def test_production_directories_immunity_guarantee(self):
        """Takes full cryptographic manifest of models/ and trading_system/models/,
        runs operations, and verifies 0 pollution, 0 mutation, and 0 added/removed files.
        """
        prod_models_dir = PROJECT_ROOT / "models"
        prod_ts_models_dir = PROJECT_ROOT / "trading_system" / "models"

        manifest_models_before = _compute_dir_manifest(prod_models_dir)
        manifest_ts_models_before = _compute_dir_manifest(prod_ts_models_dir)

        assert len(manifest_models_before) > 0, "Root models/ directory must contain production files"
        assert len(manifest_ts_models_before) > 0, "trading_system/models/ directory must contain production files"

        # Execute operations via ModelCacheManager with isolated paths
        mgr = ModelCacheManager.get_instance()
        with tempfile.TemporaryDirectory(prefix="adv_test_immunity_") as td:
            temp_p = Path(td)
            dummy = xgb.XGBRegressor(n_estimators=2, max_depth=2, n_jobs=1, tree_method="hist")
            dummy.fit(np.eye(3), np.ones(3))
            mgr.save_model_atomic(dummy, temp_p / "temp_m.json")
            mgr.load_model_safe(temp_p / "temp_m.json")
            mgr.validate_cache_health(temp_p)

        manifest_models_after = _compute_dir_manifest(prod_models_dir)
        manifest_ts_models_after = _compute_dir_manifest(prod_ts_models_dir)

        # Assert strictly zero differences in root models/
        added_models = set(manifest_models_after.keys()) - set(manifest_models_before.keys())
        removed_models = set(manifest_models_before.keys()) - set(manifest_models_after.keys())
        modified_models = [
            k for k in manifest_models_before.keys()
            if k in manifest_models_after and manifest_models_before[k] != manifest_models_after[k]
        ]

        assert not added_models, f"Pollution detected! Added files in models/: {added_models}"
        assert not removed_models, f"Mutation detected! Removed files in models/: {removed_models}"
        assert not modified_models, f"Mutation detected! Modified files in models/: {modified_models}"

        # Assert strictly zero differences in trading_system/models/
        added_ts = set(manifest_ts_models_after.keys()) - set(manifest_ts_models_before.keys())
        removed_ts = set(manifest_ts_models_before.keys()) - set(manifest_ts_models_after.keys())
        modified_ts = [
            k for k in manifest_ts_models_before.keys()
            if k in manifest_ts_models_after and manifest_ts_models_before[k] != manifest_ts_models_after[k]
        ]

        assert not added_ts, f"Pollution detected! Added files in trading_system/models/: {added_ts}"
        assert not removed_ts, f"Mutation detected! Removed files in trading_system/models/: {removed_ts}"
        assert not modified_ts, f"Mutation detected! Modified files in trading_system/models/: {modified_ts}"


if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING ADVERSARIAL STRESS TEST SUITE: M2 CONCURRENCY & CACHE HEALTH")
    print("=" * 70)
    suite = TestAdversarialConcurrencyAndCacheHealth()

    # 1. Production directory manifest snapshot
    prod_models_dir = PROJECT_ROOT / "models"
    prod_ts_models_dir = PROJECT_ROOT / "trading_system" / "models"
    m_before = _compute_dir_manifest(prod_models_dir)
    ts_m_before = _compute_dir_manifest(prod_ts_models_dir)
    print(f"[Snapshot] models/ count: {len(m_before)}, trading_system/models/ count: {len(ts_m_before)}")

    # 2. Concurrency stress test
    with tempfile.TemporaryDirectory(prefix="adv_run_stress_") as td:
        print("[Test 1/3] Running 10-thread concurrent atomic save/load stress test...")
        suite.test_concurrent_atomic_save_load_stress_10_threads(Path(td))
        print("  -> PASS: 10 threads, 40 models saved/loaded, 0 corruption, 0 race conditions, 0 orphaned temp files.")

    # 3. Cache health boundary test
    with tempfile.TemporaryDirectory(prefix="adv_run_boundary_") as td:
        print("[Test 2/3] Running cache health boundary transition test...")
        suite.test_cache_health_boundary_transitions(Path(td))
        print("  -> PASS: All boundary transitions verified (empty/partial/full/corrupted/recovered).")

    # 4. Production directory immunity test
    print("[Test 3/3] Running production directory immunity verification...")
    suite.test_production_directories_immunity_guarantee()
    m_after = _compute_dir_manifest(prod_models_dir)
    ts_m_after = _compute_dir_manifest(prod_ts_models_dir)
    assert m_before == m_after, "Root models/ directory was polluted or mutated!"
    assert ts_m_before == ts_m_after, "trading_system/models/ directory was polluted or mutated!"
    print("  -> PASS: 0 pollution, 0 mutation in production directories.")

    print("=" * 70)
    print("ALL 3 ADVERSARIAL STRESS TESTS PASSED EMPIRICALLY (100% OK)")
    print("=" * 70)
