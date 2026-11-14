# -*- coding: utf-8 -*-
"""
tests/test_adversarial_m2_verification.py — Empirical Adversarial Stress Test Suite
for Milestone 2: Cross-Market Multi-Model Retraining, Checksum Integrity, and Inference Fidelity.

Coverage:
1. Model loading across all 5 markets (sp500, nasdaq, russell2000, kospi, kosdaq) via ModelCacheManager.
2. Adversarial 1-byte binary corruption injection: strictly triggers SHA-256 mismatch and returns None.
3. Adversarial zero-byte truncation and missing binary rejection.
4. Tampered sidecar injection: altered sha256 checksum strictly rejects model load.
5. Tampered sidecar injection: altered feature_fingerprint triggers schema mismatch warning/flag.
6. Synthetic feature matrix inference fidelity matching canonical 66-feature schema:
   - Evaluates normal, zero, extreme (+100/-100), and uniform input distributions.
   - Verifies regression models output finite, non-NaN values in expected numerical bounds.
   - Verifies surge and VCP classifiers output probabilities strictly bounded in [0.0, 1.0].
7. Calibrator and Lead-Lag matrix empirical validation.
8. Invariant verification: synthetic_rows == 0 is strictly native Python int 0 across all benchmark files.
9. Cryptographic dual-tree parity verification (368 files bit-for-bit SHA-256 match).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pytest

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai.model_cache import (
    ModelCacheManager,
    compute_sha256,
    compute_feature_fingerprint,
)

ALL_5_MARKETS = ["sp500", "nasdaq", "russell2000", "kospi", "kosdaq"]
REG_HORIZONS = [1, 5, 10, 20, 30, 60, 120, 200]
SURGE_HORIZONS = [1, 3, 5, 20]


@pytest.fixture
def temp_dir():
    """Create and cleanly tear down a temporary test directory."""
    d = tempfile.mkdtemp(prefix="adv_test_m2_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="module")
def canonical_66_features() -> List[str]:
    """Load canonical 66-feature schema from authoritative production sidecar."""
    meta_path = PROJECT_ROOT / "models" / "xgb_model_sp500_1d.json_meta.json"
    assert meta_path.exists(), f"Sidecar missing: {meta_path}"
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    features = meta.get("feature_names", [])
    assert len(features) == 66, f"Expected 66 features, found {len(features)}"
    return features


class TestAdversarialM2ModelLoadingAndFidelity:
    """Empirical adversarial stress test suite for Milestone 2 verification."""

    def test_adv_m2_01_all_markets_model_loading_and_safe_retrieval(self):
        """Verify ModelCacheManager.load_model_safe() successfully loads models across all 5 markets."""
        mgr = ModelCacheManager.get_instance()
        mgr.clear_memory_cache()

        models_dir = PROJECT_ROOT / "models"
        assert models_dir.exists(), "models/ directory does not exist"

        for mkt in ALL_5_MARKETS:
            # 1. XGBoost Regression
            xgb_reg_path = models_dir / f"xgb_model_{mkt}_1d.json"
            assert xgb_reg_path.exists(), f"Missing {xgb_reg_path}"
            m_xgb_reg = mgr.load_model_safe(xgb_reg_path, verify_checksum=True, use_memory_cache=False)
            assert m_xgb_reg is not None, f"Failed to load {xgb_reg_path.name}"

            # 2. LightGBM Regression
            lgb_reg_path = models_dir / f"lgb_model_{mkt}_1d.txt"
            assert lgb_reg_path.exists(), f"Missing {lgb_reg_path}"
            m_lgb_reg = mgr.load_model_safe(lgb_reg_path, verify_checksum=True, use_memory_cache=False)
            assert m_lgb_reg is not None, f"Failed to load {lgb_reg_path.name}"

            # 3. XGBoost Surge Classifier
            xgb_surge_path = models_dir / f"xgb_surge_model_{mkt}_1d.json"
            assert xgb_surge_path.exists(), f"Missing {xgb_surge_path}"
            m_xgb_surge = mgr.load_model_safe(
                xgb_surge_path, is_classifier=True, verify_checksum=True, use_memory_cache=False
            )
            assert m_xgb_surge is not None, f"Failed to load {xgb_surge_path.name}"

            # 4. LightGBM Surge Classifier
            lgb_surge_path = models_dir / f"lgb_surge_model_{mkt}_1d.txt"
            assert lgb_surge_path.exists(), f"Missing {lgb_surge_path}"
            m_lgb_surge = mgr.load_model_safe(lgb_surge_path, verify_checksum=True, use_memory_cache=False)
            assert m_lgb_surge is not None, f"Failed to load {lgb_surge_path.name}"

            # 5. VCP ML Classifier
            vcp_path = models_dir / f"vcp_surge_{mkt}_1d.json"
            assert vcp_path.exists(), f"Missing {vcp_path}"
            m_vcp = mgr.load_model_safe(vcp_path, is_classifier=True, verify_checksum=True, use_memory_cache=False)
            assert m_vcp is not None, f"Failed to load {vcp_path.name}"

    def test_adv_m2_02_checkpoint_corruption_single_byte_injection(self, temp_dir):
        """Adversarial 1-byte checkpoint alteration strictly triggers checksum mismatch and returns None."""
        mgr = ModelCacheManager.get_instance()
        mgr.clear_memory_cache()

        models_dir = PROJECT_ROOT / "models"
        candidates = [
            "xgb_model_sp500_1d.json",
            "lgb_model_sp500_1d.txt",
            "xgb_surge_model_sp500_1d.json",
            "vcp_surge_sp500_1d.json",
        ]

        for cand in candidates:
            src_bin = models_dir / cand
            src_meta = models_dir / f"{cand}_meta.json"
            assert src_bin.exists() and src_meta.exists()

            # Copy clean checkpoint pair to isolated temp directory
            dst_bin = temp_dir / cand
            dst_meta = temp_dir / f"{cand}_meta.json"
            shutil.copy2(src_bin, dst_bin)
            shutil.copy2(src_meta, dst_meta)

            # Assert clean model loads successfully
            mgr.clear_memory_cache()
            clean_loaded = mgr.load_model_safe(dst_bin, verify_checksum=True, use_memory_cache=False)
            assert clean_loaded is not None, f"Clean model {cand} failed to load"

            # Inject 1-byte binary corruption (alter byte at offset 10)
            with open(dst_bin, "r+b") as bf:
                bf.seek(min(10, max(0, dst_bin.stat().st_size - 1)))
                orig_byte = bf.read(1)
                corrupted_byte = bytes([(orig_byte[0] ^ 0xFF)]) if orig_byte else b"\x58"
                bf.seek(min(10, max(0, dst_bin.stat().st_size - 1)))
                bf.write(corrupted_byte)

            # Assert SHA-256 now strictly mismatches
            mgr.clear_memory_cache()
            corrupted_loaded = mgr.load_model_safe(dst_bin, verify_checksum=True, use_memory_cache=False)
            assert corrupted_loaded is None, (
                f"Security breach: 1-byte corrupted model {cand} was NOT rejected by load_model_safe()!"
            )

            # Assert validate_cache_health flags corruption
            health = mgr.validate_cache_health(temp_dir, verify_checksum=True)
            assert health["corrupted_models_count"] >= 1
            assert health["is_fully_ready"] is False
            assert any(f"Corrupted checksum: {cand}" in issue for issue in health["issues"])

            # Clean up for next candidate
            dst_bin.unlink(missing_ok=True)
            dst_meta.unlink(missing_ok=True)

    def test_adv_m2_03_zero_byte_truncation_and_missing_binary(self, temp_dir):
        """Zero-byte truncated binary and missing binary files are rejected safely."""
        mgr = ModelCacheManager.get_instance()
        mgr.clear_memory_cache()

        models_dir = PROJECT_ROOT / "models"
        src_bin = models_dir / "xgb_model_sp500_1d.json"
        src_meta = models_dir / "xgb_model_sp500_1d.json_meta.json"

        dst_bin = temp_dir / "truncated_model.json"
        dst_meta = temp_dir / "truncated_model.json_meta.json"
        shutil.copy2(src_meta, dst_meta)

        # 1. Truncated 0-byte file
        dst_bin.touch()
        assert dst_bin.stat().st_size == 0
        loaded_zero = mgr.load_model_safe(dst_bin, verify_checksum=True, use_memory_cache=False)
        assert loaded_zero is None, "0-byte model must return None"

        # 2. Missing binary with dangling sidecar
        dst_bin.unlink()
        assert not dst_bin.exists()
        loaded_missing = mgr.load_model_safe(dst_bin, verify_checksum=True, use_memory_cache=False)
        assert loaded_missing is None, "Non-existent model file must return None"

    def test_adv_m2_04_tampered_sidecar_checksum_spoofing(self, temp_dir):
        """Tampering with sidecar SHA-256 checksum strictly prevents loading of binary."""
        mgr = ModelCacheManager.get_instance()
        mgr.clear_memory_cache()

        models_dir = PROJECT_ROOT / "models"
        src_bin = models_dir / "xgb_model_sp500_1d.json"
        src_meta = models_dir / "xgb_model_sp500_1d.json_meta.json"

        dst_bin = temp_dir / "spoofed_model.json"
        dst_meta = temp_dir / "spoofed_model.json_meta.json"
        shutil.copy2(src_bin, dst_bin)

        with open(src_meta, "r", encoding="utf-8") as f:
            meta = json.load(f)

        # Spoof the SHA-256 hash in the sidecar
        meta["sha256"] = "0" * 64
        with open(dst_meta, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        mgr.clear_memory_cache()
        loaded = mgr.load_model_safe(dst_bin, verify_checksum=True, use_memory_cache=False)
        assert loaded is None, "Model with spoofed sidecar checksum must be strictly rejected"

    def test_adv_m2_05_tampered_sidecar_feature_fingerprint_detection(self, temp_dir, canonical_66_features):
        """Tampering with feature_fingerprint in sidecar is detected and surfaced in health report."""
        mgr = ModelCacheManager.get_instance()
        mgr.clear_memory_cache()

        models_dir = PROJECT_ROOT / "models"
        src_bin = models_dir / "xgb_model_sp500_1d.json"
        src_meta = models_dir / "xgb_model_sp500_1d.json_meta.json"

        dst_bin = temp_dir / "tampered_fp_model.json"
        dst_meta = temp_dir / "tampered_fp_model.json_meta.json"
        shutil.copy2(src_bin, dst_bin)

        with open(src_meta, "r", encoding="utf-8") as f:
            meta = json.load(f)

        # Tamper with feature fingerprint
        meta["feature_fingerprint"] = "deadbeef_tampered"
        with open(dst_meta, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        # validate_cache_health detects feature schema mismatch
        report = mgr.validate_cache_health(temp_dir, expected_features=canonical_66_features)
        assert any("Feature schema mismatch" in issue for issue in report["issues"]), (
            f"Feature schema mismatch not detected in health report: {report['issues']}"
        )

    def test_adv_m2_06_synthetic_feature_matrix_inference_fidelity_all_5_markets(
        self, canonical_66_features
    ):
        """Empirically test model inference fidelity across 5 markets using synthetic feature matrices."""
        mgr = ModelCacheManager.get_instance()
        models_dir = PROJECT_ROOT / "models"
        n_features = len(canonical_66_features)
        assert n_features == 66

        # Construct diverse synthetic feature test matrices
        rng = np.random.RandomState(42)
        test_matrices = {
            "normal_distribution": rng.randn(40, n_features).astype(np.float32),
            "all_zeros_boundary": np.zeros((15, n_features), dtype=np.float32),
            "uniform_range": rng.uniform(-2.0, 2.0, (20, n_features)).astype(np.float32),
            "extreme_high_value": (np.ones((10, n_features), dtype=np.float32) * 50.0),
            "extreme_low_value": (np.ones((10, n_features), dtype=np.float32) * -50.0),
        }

        # Test key horizons across all 5 markets
        test_horizons = [1, 5, 20]

        for mkt in ALL_5_MARKETS:
            for h in test_horizons:
                # -------------------------------------------------------------
                # 1. XGBoost Regression
                # -------------------------------------------------------------
                xgb_reg_file = models_dir / f"xgb_model_{mkt}_{h}d.json"
                if xgb_reg_file.exists():
                    model_reg = mgr.load_model_safe(xgb_reg_file, verify_checksum=True, use_memory_cache=True)
                    assert model_reg is not None

                    for name, X in test_matrices.items():
                        preds = model_reg.predict(X)
                        assert isinstance(preds, np.ndarray), f"Expected ndarray for {mkt} {h}d {name}"
                        assert len(preds) == len(X), f"Length mismatch for {mkt} {h}d {name}"
                        assert np.all(np.isfinite(preds)), f"NaN/Inf detected in XGB reg {mkt} {h}d on {name}"
                        # Returns should not wildly explode (must be within [-10.0, 10.0])
                        assert np.all(np.abs(preds) < 10.0), (
                            f"Numerical explosion in XGB reg {mkt} {h}d on {name}: min={preds.min()}, max={preds.max()}"
                        )

                # -------------------------------------------------------------
                # 2. LightGBM Regression
                # -------------------------------------------------------------
                lgb_reg_file = models_dir / f"lgb_model_{mkt}_{h}d.txt"
                if lgb_reg_file.exists():
                    model_lgb_reg = mgr.load_model_safe(lgb_reg_file, verify_checksum=True, use_memory_cache=True)
                    assert model_lgb_reg is not None

                    for name, X in test_matrices.items():
                        preds = model_lgb_reg.predict(X)
                        assert isinstance(preds, np.ndarray)
                        assert len(preds) == len(X)
                        assert np.all(np.isfinite(preds)), f"NaN/Inf detected in LGB reg {mkt} {h}d on {name}"
                        assert np.all(np.abs(preds) < 10.0), (
                            f"Numerical explosion in LGB reg {mkt} {h}d on {name}: min={preds.min()}, max={preds.max()}"
                        )

                # -------------------------------------------------------------
                # 3. XGBoost Surge Classifier
                # -------------------------------------------------------------
                xgb_surge_file = models_dir / f"xgb_surge_model_{mkt}_{h}d.json"
                if xgb_surge_file.exists():
                    model_surge = mgr.load_model_safe(
                        xgb_surge_file, is_classifier=True, verify_checksum=True, use_memory_cache=True
                    )
                    assert model_surge is not None

                    for name, X in test_matrices.items():
                        if hasattr(model_surge, "predict_proba"):
                            probs = model_surge.predict_proba(X)
                            assert np.all(np.isfinite(probs)), f"NaN/Inf in XGB surge proba {mkt} {h}d on {name}"
                            assert np.all((probs >= -1e-6) & (probs <= 1.0 + 1e-6)), (
                                f"Probabilities out of [0, 1] bounds in {mkt} {h}d on {name}: min={probs.min()}, max={probs.max()}"
                            )
                            # Row sums must equal 1.0
                            row_sums = probs.sum(axis=1)
                            assert np.allclose(row_sums, 1.0, atol=1e-4), f"Probabilities do not sum to 1.0: {row_sums}"
                        else:
                            preds = model_surge.predict(X)
                            assert np.all(np.isfinite(preds))

                # -------------------------------------------------------------
                # 4. LightGBM Surge Classifier
                # -------------------------------------------------------------
                lgb_surge_file = models_dir / f"lgb_surge_model_{mkt}_{h}d.txt"
                if lgb_surge_file.exists():
                    model_lgb_surge = mgr.load_model_safe(lgb_surge_file, verify_checksum=True, use_memory_cache=True)
                    assert model_lgb_surge is not None

                    for name, X in test_matrices.items():
                        probs = model_lgb_surge.predict(X)
                        assert np.all(np.isfinite(probs)), f"NaN/Inf in LGB surge {mkt} {h}d on {name}"
                        assert np.all((probs >= -1e-6) & (probs <= 1.0 + 1e-6)), (
                            f"LGB surge probabilities out of [0, 1] in {mkt} {h}d on {name}: min={probs.min()}, max={probs.max()}"
                        )

                # -------------------------------------------------------------
                # 5. VCP XGBoost Classifier
                # -------------------------------------------------------------
                vcp_file = models_dir / f"vcp_surge_{mkt}_{h}d.json"
                if vcp_file.exists():
                    model_vcp = mgr.load_model_safe(
                        vcp_file, is_classifier=True, verify_checksum=True, use_memory_cache=True
                    )
                    assert model_vcp is not None

                    for name, X in test_matrices.items():
                        if hasattr(model_vcp, "predict_proba"):
                            probs = model_vcp.predict_proba(X)
                            assert np.all(np.isfinite(probs))
                            assert np.all((probs >= -1e-6) & (probs <= 1.0 + 1e-6))
                        else:
                            preds = model_vcp.predict(X)
                            assert np.all(np.isfinite(preds))

    def test_adv_m2_07_calibrators_and_lead_lag_fidelity(self):
        """Empirically test calibrators and lead-lag cross-correlation artifacts."""
        mgr = ModelCacheManager.get_instance()
        models_dir = PROJECT_ROOT / "models"

        # 1. Calibrators
        calib_file = models_dir / "calibrators.pkl"
        assert calib_file.exists(), "calibrators.pkl missing"
        calibs = mgr.load_model_safe(calib_file, verify_checksum=True, use_memory_cache=False)
        assert calibs is not None, "Failed to load calibrators.pkl"
        assert isinstance(calibs, dict), f"calibrators.pkl should be dict, got {type(calibs)}"

        test_scores = np.linspace(0.0, 1.0, 50)
        for name, cal_obj in calibs.items():
            if hasattr(cal_obj, "predict"):
                cal_preds = cal_obj.predict(test_scores)
                assert np.all(np.isfinite(cal_preds)), f"NaN/Inf in calibrator {name}"
                assert np.all((cal_preds >= -1e-5) & (cal_preds <= 1.0 + 1e-5)), (
                    f"Calibrator {name} output out of [0, 1] bounds"
                )
                # Monotonicity check
                diffs = np.diff(cal_preds)
                assert np.all(diffs >= -1e-5), f"Calibrator {name} violated monotonicity: min diff={diffs.min()}"

        # 2. Lead-Lag Matrix
        lead_lag_file = models_dir / "lead_lag_matrix.json"
        assert lead_lag_file.exists(), "lead_lag_matrix.json missing"
        with open(lead_lag_file, "r", encoding="utf-8") as f:
            ll_data = json.load(f)

        assert isinstance(ll_data, dict)
        leaders = ll_data.get("leaders", [])
        assert len(leaders) >= 5, f"Expected at least 5 leaders, found {len(leaders)}"
        matrix = ll_data.get("lag_cross_correlations", {})
        for leader, followers in matrix.items():
            for follower, corr in followers.items():
                assert np.isfinite(corr), f"NaN/Inf in lead-lag correlation: {leader}->{follower}"
                assert -1.0 <= corr <= 1.0, f"Correlation coefficient out of [-1, 1]: {corr}"

    def test_adv_m2_08_strict_invariant_synthetic_rows_int_zero(self):
        """Strict verification that synthetic_rows == 0 is native Python int 0."""
        benchmark_paths = [
            PROJECT_ROOT / "benchmarks" / "30year" / "status.json",
            PROJECT_ROOT / "trading_system" / "result" / "status.json",
        ]

        checked = 0
        for p in benchmark_paths:
            if p.exists():
                checked += 1
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                assert "synthetic_rows" in data, f"Missing synthetic_rows in {p}"
                val = data["synthetic_rows"]
                assert val == 0, f"synthetic_rows in {p} is {val}, must be 0"
                assert type(val) is int, f"synthetic_rows in {p} is {type(val)}, must be native int"
                assert not isinstance(val, bool), f"synthetic_rows in {p} must not be boolean"

        assert checked == 2, f"Expected both status.json files to exist, checked {checked}"

    def test_adv_m2_09_dual_tree_cryptographic_parity_execution(self):
        """Execute scripts/verify_dual_tree_parity.py --check --strict and assert 100% parity."""
        verify_script = PROJECT_ROOT / "scripts" / "verify_dual_tree_parity.py"
        assert verify_script.exists()

        python_exe = sys.executable
        res = subprocess.run(
            [python_exe, str(verify_script), "--check", "--strict"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )

        assert res.returncode == 0, (
            f"Dual-tree parity check failed (code {res.returncode}):\n{res.stdout}\n{res.stderr}"
        )
        assert "Status:                     PASS" in res.stdout
        assert "Identical (100% SHA-256):   368" in res.stdout
        assert "Content Mismatches:         0" in res.stdout
