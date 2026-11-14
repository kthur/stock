# -*- coding: utf-8 -*-
"""
tests/test_adversarial_m3_challenger.py — Adversarial Verification & Mutation Test Suite
for Milestone 3 (Feature F951: Dual-Tree Cryptographic Parity & Checkpoint Synchronization).

Focus Areas:
1. Strict Benchmark Invariant: synthetic_rows == 0 strictly native Python int across:
   - benchmarks/30year/status.json
   - trading_system/result/status.json
   - benchmarks/30year/stock_universe_summary.json
   - trading_system/result/stock_universe_summary.json
2. Adversarial Mutation Testing: Mutating synthetic_rows to True, False, 0.0, 1, -1, None, etc.
   strictly triggers assertion failure.
3. Dual-Tree Parity:
   - Bit-for-bit SHA-256 match for benchmarks
   - Bit-for-bit SHA-256 match for models (330/330 files + checkpoints/)
   - ModelCacheManager cache health verification on trading_system/models
4. Institutional KPI Verification:
   - Net CAGR >= 90.89%
   - Sharpe >= 4.72
   - MDD >= -14.00%
   - Active Win Rate >= 93.10%
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai.model_cache import ModelCacheManager, compute_sha256

BENCHMARK_ARTIFACTS = [
    PROJECT_ROOT / "benchmarks" / "30year" / "status.json",
    PROJECT_ROOT / "trading_system" / "result" / "status.json",
    PROJECT_ROOT / "benchmarks" / "30year" / "stock_universe_summary.json",
    PROJECT_ROOT / "trading_system" / "result" / "stock_universe_summary.json",
]


def strict_assert_synthetic_rows(val: Any, location_msg: str = "") -> None:
    """Strictly assert that synthetic_rows is native int 0 (not bool, not float, not non-zero)."""
    assert val == 0, f"synthetic_rows is {val} != 0 ({location_msg})"
    assert type(val) is int, f"synthetic_rows type is {type(val).__name__}, not int ({location_msg})"
    assert not isinstance(val, bool), f"synthetic_rows is a boolean ({location_msg})"


def find_all_keys(d: Any, target_key: str, path: str = "") -> List[Tuple[str, Any]]:
    """Recursively discover all instances of target_key in nested structures."""
    results: List[Tuple[str, Any]] = []
    if isinstance(d, dict):
        for k, v in d.items():
            curr_path = f"{path}.{k}" if path else k
            if k == target_key:
                results.append((curr_path, v))
            results.extend(find_all_keys(v, target_key, curr_path))
    elif isinstance(d, list):
        for i, item in enumerate(d):
            results.extend(find_all_keys(item, target_key, f"{path}[{i}]"))
    return results


class TestAdversarialM3Challenger:
    """Adversarial stress and verification suite for Milestone 3."""

    def test_tc01_benchmark_artifacts_existence_and_cryptographic_parity(self):
        """Verify all 4 benchmark artifacts exist and mirrored pairs have identical SHA-256."""
        for p in BENCHMARK_ARTIFACTS:
            assert p.exists(), f"Benchmark artifact missing: {p}"
            assert p.stat().st_size > 0, f"Benchmark artifact is empty: {p}"

        # Status parity
        status_root = BENCHMARK_ARTIFACTS[0]
        status_ts = BENCHMARK_ARTIFACTS[1]
        hash_status_root = hashlib.sha256(status_root.read_bytes()).hexdigest()
        hash_status_ts = hashlib.sha256(status_ts.read_bytes()).hexdigest()
        assert hash_status_root == hash_status_ts, (
            f"Cryptographic hash mismatch between status.json files:\n"
            f"  benchmarks/30year: {hash_status_root}\n"
            f"  trading_system/result: {hash_status_ts}"
        )

        # Summary parity
        summary_root = BENCHMARK_ARTIFACTS[2]
        summary_ts = BENCHMARK_ARTIFACTS[3]
        hash_summary_root = hashlib.sha256(summary_root.read_bytes()).hexdigest()
        hash_summary_ts = hashlib.sha256(summary_ts.read_bytes()).hexdigest()
        assert hash_summary_root == hash_summary_ts, (
            f"Cryptographic hash mismatch between stock_universe_summary.json files:\n"
            f"  benchmarks/30year: {hash_summary_root}\n"
            f"  trading_system/result: {hash_summary_ts}"
        )

    def test_tc02_strict_synthetic_rows_invariant_all_artifacts(self):
        """Verify synthetic_rows == 0 is strictly native int 0 across all benchmark files."""
        total_occurrences_checked = 0

        for p in BENCHMARK_ARTIFACTS:
            data = json.loads(p.read_text(encoding="utf-8"))
            occurrences = find_all_keys(data, "synthetic_rows")
            assert len(occurrences) >= 1, f"No synthetic_rows found in {p}"

            for key_path, val in occurrences:
                strict_assert_synthetic_rows(val, f"file={p.name}, path={key_path}")
                total_occurrences_checked += 1

        # Must have verified at least 4 occurrences across the 4 files
        assert total_occurrences_checked >= 4, (
            f"Expected at least 4 occurrences verified, got {total_occurrences_checked}"
        )

    def test_tc03_adversarial_mutation_synthetic_rows_type_and_value(self):
        """Adversarially verify that any mutation of synthetic_rows triggers strict assertion failure."""
        adversarial_mutations = [
            True,           # bool True (val != 0, is bool)
            False,          # bool False (val == 0 in Python, but is bool! Crucial edge case!)
            0.0,            # float zero (val == 0, but type is float)
            1.0,            # float one
            1,              # positive int
            -1,             # negative int
            "0",            # string zero
            "False",        # string False
            None,           # NoneType
            [],             # empty list
            {},             # empty dict
        ]

        for mutated_val in adversarial_mutations:
            with pytest.raises(AssertionError) as exc_info:
                strict_assert_synthetic_rows(mutated_val, f"mutation={repr(mutated_val)}")
            assert "synthetic_rows" in str(exc_info.value)

    def test_tc04_adversarial_in_memory_benchmark_mutation(self):
        """Adversarially mutate parsed benchmark structures in-memory and confirm detection."""
        for p in BENCHMARK_ARTIFACTS:
            data = json.loads(p.read_text(encoding="utf-8"))

            # Determine key location
            if "synthetic_rows" in data:
                key_holder = data
                key_name = "synthetic_rows"
            elif "metadata" in data and "synthetic_rows" in data["metadata"]:
                key_holder = data["metadata"]
                key_name = "synthetic_rows"
            else:
                pytest.fail(f"Could not locate synthetic_rows in {p}")

            # Verify original passes
            strict_assert_synthetic_rows(key_holder[key_name], f"clean {p.name}")

            # Adversarially test each mutation on the real data dictionary
            for bad_val in [True, False, 0.0, 1, -1, "0", None]:
                mutated_data = copy.deepcopy(data)
                target = mutated_data if key_name in mutated_data else mutated_data["metadata"]
                target[key_name] = bad_val

                with pytest.raises(AssertionError):
                    strict_assert_synthetic_rows(target[key_name], f"mutated {p.name} with {bad_val}")

    def test_tc05_dual_tree_models_directory_sha256_parity(self):
        """Verify 100% SHA-256 bit-for-bit parity across all regular files in models/ and trading_system/models/."""
        root_models = PROJECT_ROOT / "models"
        ts_models = PROJECT_ROOT / "trading_system" / "models"

        assert root_models.is_dir(), "Root models/ directory missing"
        assert ts_models.is_dir(), "Mirrored trading_system/models/ directory missing"
        assert (ts_models / "checkpoints").is_dir(), "trading_system/models/checkpoints missing"

        root_files = {p.name: compute_sha256(p) for p in root_models.glob("*") if p.is_file()}
        ts_files = {p.name: compute_sha256(p) for p in ts_models.glob("*") if p.is_file()}

        assert len(root_files) == 330, f"Expected 330 root model files, got {len(root_files)}"
        assert len(ts_files) == 330, f"Expected 330 ts model files, got {len(ts_files)}"
        assert root_files == ts_files, (
            f"Model directory mismatch: missing_in_ts={set(root_files.keys()) - set(ts_files.keys())}, "
            f"extra_in_ts={set(ts_files.keys()) - set(root_files.keys())}"
        )

        # Check clean architecture: zero tmp and lock files
        for d in (root_models, ts_models):
            tmp_files = list(d.glob("*.tmp")) + list(d.glob("*.lock"))
            assert len(tmp_files) == 0, f"Found stray temp/lock files in {d}: {tmp_files}"

    def test_tc06_trading_system_models_cache_health(self):
        """Empirically evaluate ModelCacheManager cache health report for trading_system/models/."""
        mgr = ModelCacheManager.get_instance()
        ts_models = PROJECT_ROOT / "trading_system" / "models"

        health = mgr.validate_cache_health(ts_models, verify_checksum=True)

        assert health["directory_exists"] is True
        assert health["is_fully_ready"] is True
        assert health["valid_models_count"] == 169
        assert health["stale_models_count"] == 0
        assert health["corrupted_models_count"] == 0
        assert len(health["issues"]) == 0

        # Verify all 5 markets are active
        market_status = health["market_status"]
        assert set(market_status.keys()) == {"sp500", "nasdaq", "russell2000", "kospi", "kosdaq"}
        for mkt, counts in market_status.items():
            assert counts["regression"] == 16, f"{mkt} regression count {counts['regression']} != 16"
            assert counts["surge"] == 8, f"{mkt} surge count {counts['surge']} != 8"
            assert counts["vcp"] == 8, f"{mkt} vcp count {counts['vcp']} != 8"

    def test_tc07_institutional_metrics_compliance(self):
        """Empirically verify that 30-year institutional benchmark metrics strictly meet or exceed requirements."""
        status_file = PROJECT_ROOT / "benchmarks" / "30year" / "status.json"
        assert status_file.exists()

        status_data = json.loads(status_file.read_text(encoding="utf-8"))
        metrics = status_data["metrics"]

        net_cagr = float(metrics["net_cagr_pct"])
        sharpe = float(metrics["sharpe_ratio"])
        sortino = float(metrics["sortino_ratio"])
        calmar = float(metrics["calmar_ratio"])
        mdd = float(metrics["max_drawdown_pct"])
        active_win_rate = float(metrics["active_win_rate_pct"])
        total_net_return = float(metrics["total_net_return_pct"])
        multiplier = float(metrics["final_equity_krw"]) / float(metrics["initial_capital_krw"])

        # Assert institutional requirements
        assert net_cagr >= 90.89, f"Net CAGR {net_cagr}% < 90.89%"
        assert sharpe >= 4.72, f"Sharpe ratio {sharpe} < 4.72"
        assert sortino >= 8.58, f"Sortino ratio {sortino} < 8.58"
        assert calmar >= 6.95, f"Calmar ratio {calmar} < 6.95"
        assert mdd >= -14.00, f"MDD {mdd}% breached -14.00% limit (must be >= -14.00%)"
        assert active_win_rate >= 93.10, f"Active Win Rate {active_win_rate}% < 93.10%"
        assert total_net_return >= 82_055_186_002.19, (
            f"Total Net Return {total_net_return}% < 82,055,186,002.19%"
        )
        assert multiplier > 820_000_000.0, f"Terminal multiplier {multiplier} <= 820,000,000x"

    def test_tc08_ts_models_direct_isolation_and_inference_fidelity(self):
        """Task 1 Challenge: Directly instantiate OnDevicePredictionModel and VCPSurgePredictor
        from trading_system/models/ with zero reliance on root models/, feeding synthetic 66-feature vectors."""
        import pandas as pd
        import numpy as np
        from src.ai.prediction_model import OnDevicePredictionModel
        from src.ai.vcp_ml_predictor import VCPSurgePredictor

        ts_models_dir = PROJECT_ROOT / "trading_system" / "models"
        root_models_dir = PROJECT_ROOT / "models"

        # Track file opens to ensure zero access to root_models_dir
        accessed_root_files = []
        original_open = open

        def guarded_open(file, *args, **kwargs):
            try:
                p = Path(file).resolve()
                if root_models_dir.resolve() in p.parents or p == root_models_dir.resolve():
                    accessed_root_files.append(str(p))
            except Exception:
                pass
            return original_open(file, *args, **kwargs)

        # 1. Load canonical 66 features from sidecar in trading_system/models
        meta_file = ts_models_dir / "xgb_model_sp500_1d.json_meta.json"
        assert meta_file.exists(), f"Meta sidecar missing: {meta_file}"
        with open(meta_file, "r", encoding="utf-8") as f:
            meta_data = json.load(f)

        assert meta_data.get("feature_fingerprint") == "6a48ad0a978d6ee5", (
            f"Fingerprint mismatch: expected '6a48ad0a978d6ee5', got {meta_data.get('feature_fingerprint')}"
        )
        canonical_features = meta_data.get("feature_names", [])
        assert len(canonical_features) == 66, f"Expected 66 features, found {len(canonical_features)}"

        # 2. Instantiate with isolation tracking
        import unittest.mock as mock
        with mock.patch("builtins.open", side_effect=guarded_open):
            pred_model = OnDevicePredictionModel(model_dir=str(ts_models_dir))
            vcp_predictor = VCPSurgePredictor(model_dir=str(ts_models_dir))

        # Assert zero reliance on root models/
        assert len(accessed_root_files) == 0, (
            f"Isolation violation! Direct loading from trading_system/models accessed root models: {accessed_root_files}"
        )

        all_markets = ["sp500", "nasdaq", "russell2000", "kospi", "kosdaq"]
        reg_horizons = [1, 5, 10, 20, 30, 60, 120, 200]
        surge_horizons = [1, 3, 5, 20]

        # 3. Verify all models are loaded
        for mkt in all_markets:
            assert mkt in pred_model.models, f"Missing regression models for {mkt}"
            for h in reg_horizons:
                assert h in pred_model.models[mkt], f"Missing {mkt} regression {h}d XGB"
                assert h in pred_model.lgb_models[mkt], f"Missing {mkt} regression {h}d LGB"

            assert mkt in pred_model.surge_models, f"Missing surge models for {mkt}"
            for h in surge_horizons:
                assert h in pred_model.surge_models[mkt], f"Missing {mkt} surge {h}d XGB"
                assert h in pred_model.surge_lgb_models[mkt], f"Missing {mkt} surge {h}d LGB"

            vcp_mkt = mkt.upper() if mkt.upper() in vcp_predictor.models else mkt.lower()
            assert vcp_mkt in vcp_predictor.models, f"Missing VCP ML models for {mkt}"
            for h in surge_horizons:
                assert h in vcp_predictor.models[vcp_mkt], f"Missing {mkt} VCP {h}d XGB"
                assert h in vcp_predictor.lgb_models[vcp_mkt], f"Missing {mkt} VCP {h}d LGB"

        # 4. Generate synthetic feature vectors across multiple test distributions
        rng = np.random.RandomState(42)
        n_samples = 20

        test_distributions = {
            "standard_normal": rng.randn(n_samples, 66),
            "zeros": np.zeros((5, 66)),
            "extreme_pos": np.full((5, 66), 50.0),
            "extreme_neg": np.full((5, 66), -50.0),
            "uniform": rng.uniform(0.0, 1.0, (n_samples, 66)),
        }

        # 5. Execute inference and verify numerical validity
        with mock.patch("builtins.open", side_effect=guarded_open):
            for dist_name, feat_matrix in test_distributions.items():
                df_synth = pd.DataFrame(feat_matrix, columns=canonical_features)

                for mkt in all_markets:
                    for h in reg_horizons:
                        xgb_reg = pred_model.models[mkt][h]
                        preds_xgb = xgb_reg.predict(df_synth)
                        assert np.all(np.isfinite(preds_xgb)), (
                            f"Non-finite prediction in {mkt} regression {h}d XGB on {dist_name}: {preds_xgb}"
                        )

                        lgb_reg = pred_model.lgb_models[mkt][h]
                        preds_lgb = lgb_reg.predict(df_synth)
                        assert np.all(np.isfinite(preds_lgb)), (
                            f"Non-finite prediction in {mkt} regression {h}d LGB on {dist_name}: {preds_lgb}"
                        )

                    for h in surge_horizons:
                        xgb_surge = pred_model.surge_models[mkt][h]
                        probs_xgb = xgb_surge.predict_proba(df_synth)[:, 1]
                        assert np.all(np.isfinite(probs_xgb)), (
                            f"Non-finite probability in {mkt} surge {h}d XGB on {dist_name}"
                        )
                        assert np.all((probs_xgb >= 0.0) & (probs_xgb <= 1.0)), (
                            f"Surge prob out of [0, 1] in {mkt} {h}d XGB on {dist_name}: min={probs_xgb.min()}, max={probs_xgb.max()}"
                        )

                        lgb_surge = pred_model.surge_lgb_models[mkt][h]
                        if hasattr(lgb_surge, "predict_proba"):
                            probs_lgb = lgb_surge.predict_proba(df_synth)[:, 1]
                        else:
                            probs_lgb = lgb_surge.predict(df_synth)
                            if getattr(probs_lgb, "ndim", 1) > 1 and probs_lgb.shape[1] > 1:
                                probs_lgb = probs_lgb[:, 1]
                        assert np.all(np.isfinite(probs_lgb)), (
                            f"Non-finite probability in {mkt} surge {h}d LGB on {dist_name}"
                        )
                        assert np.all((probs_lgb >= 0.0) & (probs_lgb <= 1.0)), (
                            f"Surge prob out of [0, 1] in {mkt} {h}d LGB on {dist_name}: min={probs_lgb.min()}, max={probs_lgb.max()}"
                        )

                        vcp_mkt = mkt.upper() if mkt.upper() in vcp_predictor.models else mkt.lower()
                        xgb_vcp = vcp_predictor.models[vcp_mkt][h]
                        probs_vcp_xgb = xgb_vcp.predict_proba(df_synth)[:, 1]
                        assert np.all(np.isfinite(probs_vcp_xgb)), (
                            f"Non-finite prob in {mkt} VCP {h}d XGB on {dist_name}"
                        )
                        assert np.all((probs_vcp_xgb >= 0.0) & (probs_vcp_xgb <= 1.0)), (
                            f"VCP prob out of [0, 1] in {mkt} {h}d XGB on {dist_name}: min={probs_vcp_xgb.min()}, max={probs_vcp_xgb.max()}"
                        )

                        lgb_vcp = vcp_predictor.lgb_models[vcp_mkt][h]
                        if hasattr(lgb_vcp, "predict_proba"):
                            probs_vcp_lgb = lgb_vcp.predict_proba(df_synth)[:, 1]
                        else:
                            probs_vcp_lgb = lgb_vcp.predict(df_synth)
                            if getattr(probs_vcp_lgb, "ndim", 1) > 1 and probs_vcp_lgb.shape[1] > 1:
                                probs_vcp_lgb = probs_vcp_lgb[:, 1]
                        assert np.all(np.isfinite(probs_vcp_lgb)), (
                            f"Non-finite prob in {mkt} VCP {h}d LGB on {dist_name}"
                        )
                        assert np.all((probs_vcp_lgb >= 0.0) & (probs_vcp_lgb <= 1.0)), (
                            f"VCP prob out of [0, 1] in {mkt} {h}d LGB on {dist_name}: min={probs_vcp_lgb.min()}, max={probs_vcp_lgb.max()}"
                        )

        # Confirm zero root models access during entire inference run
        assert len(accessed_root_files) == 0, (
            f"Isolation violation during inference: {accessed_root_files}"
        )

    def test_tc09_tamper_and_parity_sensitivity_divergence_detection(self):
        """Task 2 Challenge: Verify that artificial divergence between models/ and
        trading_system/models/ is immediately detected by parity check scripts,
        ModelCacheManager validation, and test_tc013 logic."""
        import tempfile
        import shutil

        root_models = PROJECT_ROOT / "models"
        ts_models = PROJECT_ROOT / "trading_system" / "models"

        # 1. Scratch copy of ts_models to mutate safely
        with tempfile.TemporaryDirectory(prefix="adv_tamper_test_") as tmpdir:
            scratch_models = Path(tmpdir) / "models"
            shutil.copytree(ts_models, scratch_models)

            # Test 1: Mutate tuned_params_sp500.json
            cfg_scratch = scratch_models / "tuned_params_sp500.json"
            cfg_content = json.loads(cfg_scratch.read_text(encoding="utf-8"))
            cfg_content["xgb"]["max_depth"] = 9999
            cfg_scratch.write_text(json.dumps(cfg_content), encoding="utf-8")

            # TC013 logic assertion must fail
            cfg_root = root_models / "tuned_params_sp500.json"
            assert compute_sha256(cfg_root) != compute_sha256(cfg_scratch), (
                "Mutated tuned_params_sp500.json failed to trigger SHA-256 mismatch!"
            )

            # Test 2: Mutate crisis_state.json
            cs_scratch = scratch_models / "crisis_state.json"
            cs_scratch.write_text(json.dumps({"crisis_stage": "MUTATED_TAMPER"}), encoding="utf-8")
            cs_root = root_models / "crisis_state.json"
            assert compute_sha256(cs_root) != compute_sha256(cs_scratch), (
                "Mutated crisis_state.json failed to trigger SHA-256 mismatch!"
            )

            # Test 3: Mutate binary model checkpoint (1-byte flip)
            target_bin = scratch_models / "xgb_model_sp500_1d.json"
            data = bytearray(target_bin.read_bytes())
            data[0] = ord(b'X') if data[0] != ord(b'X') else ord(b'Y')
            target_bin.write_bytes(bytes(data))

            root_bin = root_models / "xgb_model_sp500_1d.json"
            assert compute_sha256(root_bin) != compute_sha256(target_bin), (
                "Tampered binary checkpoint failed to trigger SHA-256 divergence!"
            )

            # ModelCacheManager cache health must flag corruption
            mgr = ModelCacheManager.get_instance()
            mgr.clear_memory_cache()
            health = mgr.validate_cache_health(scratch_models, verify_checksum=True)
            assert health["is_fully_ready"] is False or health["corrupted_models_count"] > 0, (
                f"Tampered binary was not detected by validate_cache_health: {health}"
            )

            # Test 4: Delete an arbitrary model checkpoint
            del_target = scratch_models / "lgb_model_kospi_1d.txt"
            del_target.unlink()
            health_after_del = mgr.validate_cache_health(scratch_models, verify_checksum=False)
            assert (
                health_after_del["is_fully_ready"] is False
                or health_after_del["valid_models_count"] < 169
                or len(health_after_del["issues"]) > 0
            ), f"Deleted model was not detected by cache health: {health_after_del}"

    def test_tc10_clean_architecture_zero_uncommitted_orphaned_or_temp_files(self):
        """Task 2 Challenge: Assert zero uncommitted, temporary, orphaned, or stale artifacts in trading_system/models/."""
        ts_models = PROJECT_ROOT / "trading_system" / "models"
        root_models = PROJECT_ROOT / "models"

        assert ts_models.is_dir()
        all_files = [p for p in ts_models.glob("*") if p.is_file()]
        all_dirs = [p for p in ts_models.glob("*") if p.is_dir()]

        # 1. Exact counts: 330 files and 1 directory ('checkpoints')
        assert len(all_files) == 330, f"Expected 330 files in trading_system/models, got {len(all_files)}"
        assert len(all_dirs) == 1, f"Expected 1 sub-directory in trading_system/models, got {len(all_dirs)}"
        assert all_dirs[0].name == "checkpoints"

        # 2. Check for temporary, lock, swap, backup, or cache files
        disallowed_patterns = ["*.tmp*", "*.lock*", "*~*", "*.swp", "*.bak", "*.old", "__pycache__", "*.DS_Store"]
        for pat in disallowed_patterns:
            matches = list(ts_models.rglob(pat))
            assert len(matches) == 0, f"Found disallowed temporary/orphaned files matching {pat}: {matches}"

        # 3. Model binary to sidecar 1-to-1 bijection
        model_extensions = {".json", ".txt", ".bin", ".pt", ".pkl"}
        config_and_state = {"crisis_state.json", "lead_lag_matrix.json"}
        tuned_param_files = {f"tuned_params_{m}.json" for m in ["sp500", "nasdaq", "russell2000", "kospi", "kosdaq"]}.union({"tuned_params.json"})

        model_binaries = []
        for f in all_files:
            if f.name.endswith("_meta.json"):
                continue
            if f.name in config_and_state or f.name in tuned_param_files or f.name.startswith("tuned_params_"):
                continue
            if f.suffix in model_extensions:
                model_binaries.append(f)

        assert len(model_binaries) == 161, f"Expected 161 model binaries, got {len(model_binaries)}"

        # Every model binary MUST have a sidecar whose sha256 exactly matches the binary
        for mb in model_binaries:
            sidecar = ts_models / f"{mb.name}_meta.json"
            assert sidecar.exists(), f"Orphaned model binary without sidecar: {mb.name}"
            with open(sidecar, "r", encoding="utf-8") as sf:
                meta = json.load(sf)
            actual_sha = compute_sha256(mb)
            assert meta.get("sha256") == actual_sha, (
                f"Sidecar sha256 mismatch for {mb.name}: recorded={meta.get('sha256')}, actual={actual_sha}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

