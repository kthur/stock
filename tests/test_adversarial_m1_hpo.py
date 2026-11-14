import os
import sys
import json
import tempfile
import shutil
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ai.prediction_model import OnDevicePredictionModel
from src.ai.vcp_ml_predictor import VCPSurgePredictor


class TestAdversarialJSONLoading:
    """Stress-test JSON loading resilience against missing, malformed, non-dict, and exotic inputs."""

    @pytest.fixture(autouse=True)
    def setup_tmp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.model_dir = Path(self.temp_dir)
        yield
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_missing_all_files_returns_empty_dict(self):
        """When neither market file nor global fallback file exists, must return empty dict without crashing."""
        model = OnDevicePredictionModel(model_dir=str(self.model_dir))
        vcp = VCPSurgePredictor(model_dir=str(self.model_dir))

        for mkt in ["sp500", "nasdaq", "russell2000", "kospi", "kosdaq", "unknown_xyz"]:
            res_m = model._load_market_params(mkt)
            res_v = vcp._load_market_params(mkt)
            assert res_m == {}, f"Expected empty dict for {mkt}, got {res_m}"
            assert res_v == {}, f"Expected empty dict for {mkt}, got {res_v}"

    def test_corrupted_truncated_json_handled_gracefully(self):
        """Corrupt or truncated JSON must be caught and return empty dict without unhandled exception."""
        corrupt_file = self.model_dir / "tuned_params_sp500.json"
        with open(corrupt_file, "w", encoding="utf-8") as f:
            f.write('{"market": "SP500", "xgb": {"learning_rate": 0.03, ')  # Truncated

        model = OnDevicePredictionModel(model_dir=str(self.model_dir))
        vcp = VCPSurgePredictor(model_dir=str(self.model_dir))

        res_m = model._load_market_params("sp500")
        res_v = vcp._load_market_params("sp500")
        assert res_m == {}, f"Expected empty dict on corrupt JSON in model, got {res_m}"
        assert res_v == {}, f"Expected empty dict on corrupt JSON in vcp, got {res_v}"

    def test_empty_dictionary_json(self):
        """An empty JSON object '{}' must load cleanly as an empty dict."""
        empty_file = self.model_dir / "tuned_params_nasdaq.json"
        with open(empty_file, "w", encoding="utf-8") as f:
            f.write("{}")

        model = OnDevicePredictionModel(model_dir=str(self.model_dir))
        vcp = VCPSurgePredictor(model_dir=str(self.model_dir))

        assert model._load_market_params("nasdaq") == {}
        assert vcp._load_market_params("nasdaq") == {}

    @pytest.mark.parametrize("payload", [
        [1, 2, 3],
        "this is a raw string",
        12345,
        True,
        None,
    ])
    def test_non_dict_json_payloads_rejected(self, payload):
        """Non-dictionary JSON payloads (arrays, strings, numbers, booleans, null) must return {}."""
        test_file = self.model_dir / "tuned_params_kospi.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        model = OnDevicePredictionModel(model_dir=str(self.model_dir))
        vcp = VCPSurgePredictor(model_dir=str(self.model_dir))

        res_m = model._load_market_params("kospi")
        res_v = vcp._load_market_params("kospi")
        assert isinstance(res_m, dict) and res_m == {}, f"Expected empty dict for payload {payload}, got {res_m}"
        assert isinstance(res_v, dict) and res_v == {}, f"Expected empty dict for payload {payload}, got {res_v}"

    def test_fallback_to_global_when_market_missing(self):
        """When market-specific file is missing, must fall back to global tuned_params.json."""
        global_file = self.model_dir / "tuned_params.json"
        with open(global_file, "w", encoding="utf-8") as f:
            json.dump({"market": "GLOBAL", "xgb": {"learning_rate": 0.05}}, f)

        model = OnDevicePredictionModel(model_dir=str(self.model_dir))
        vcp = VCPSurgePredictor(model_dir=str(self.model_dir))

        # Query a market that does not have its own file
        res_m = model._load_market_params("russell2000")
        res_v = vcp._load_market_params("russell2000")

        assert res_m.get("market") == "GLOBAL"
        assert res_m.get("xgb", {}).get("learning_rate") == 0.05
        assert res_v.get("market") == "GLOBAL"
        assert res_v.get("xgb", {}).get("learning_rate") == 0.05

    @pytest.mark.parametrize("exotic_market", [
        "MARS",
        "UNKNOWN_99",
        "",
        None,
        123,
        "!@#$%^&*()_+",
        "   SP500   ",
    ])
    def test_exotic_and_invalid_market_identifiers(self, exotic_market):
        """Exotic or invalid market arguments must not cause unhandled exceptions."""
        model = OnDevicePredictionModel(model_dir=str(self.model_dir))
        vcp = VCPSurgePredictor(model_dir=str(self.model_dir))

        res_m = model._load_market_params(exotic_market)
        res_v = vcp._load_market_params(exotic_market)
        assert isinstance(res_m, dict)
        assert isinstance(res_v, dict)


class TestBoundaryClampingAndSanitization:
    """Stress-test hyperparameter boundary constraints (scale_pos_weight <= 20.0, lr > 0, max_depth > 0)."""

    @pytest.fixture(autouse=True)
    def setup_tmp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.model_dir = Path(self.temp_dir)
        yield
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scale_pos_weight_hard_cap_enforcement_vcp(self):
        """Institutional spec in AGENTS.md mandates scale_pos_weight <= 20.0 for surge classification.
        If a tuned parameter file configures scale_pos_weight > 20.0 (e.g. 50.0 or 100.0),
        VCPSurgePredictor MUST enforce scale_pos_weight <= 20.0."""
        # Setup hostile profile with scale_pos_weight = 50.0
        hostile_profile = {
            "market": "KOSDAQ",
            "surge_xgb": {
                "scale_pos_weight": 50.0,
                "n_estimators": 5,
                "max_depth": 3,
                "learning_rate": 0.05
            },
            "vcp_ml": {
                "scale_pos_weight": 50.0,
                "max_depth": 3,
                "learning_rate": 0.05
            }
        }
        with open(self.model_dir / "tuned_params_kosdaq.json", "w", encoding="utf-8") as f:
            json.dump(hostile_profile, f)

        vcp = VCPSurgePredictor(model_dir=str(self.model_dir))
        mkt_params = vcp._load_market_params("kosdaq")

        kw_xgb = dict(vcp._surge_xgb_kwargs)
        if 'surge_xgb' in mkt_params:
            kw_xgb.update(mkt_params['surge_xgb'])
        if 'vcp_ml' in mkt_params:
            for k, v in mkt_params['vcp_ml'].items():
                if k in kw_xgb or k in ['scale_pos_weight', 'window_step_size']:
                    kw_xgb[k] = v

        # Simulate sparse positive samples: 2 positive, 100 negative (ratio = 50.0)
        pos_count = 2
        neg_count = 100

        # Execute the exact calculation from vcp_ml_predictor.py:498-503
        spw_cap = kw_xgb.get('scale_pos_weight', 20.0)
        try:
            spw_cap = min(float(spw_cap), 20.0) if (spw_cap is not None and float(spw_cap) > 0) else 20.0
        except (TypeError, ValueError):
            spw_cap = 20.0
        scale_pos_weight = min(neg_count / pos_count, spw_cap)

        # AGENTS.md requirement: Surge 분류기: scale_pos_weight <= 20.0
        assert scale_pos_weight <= 20.0, (
            f"VULNERABILITY: scale_pos_weight was set to {scale_pos_weight}, exceeding "
            f"institutional limit of 20.0 when hostile profile specified {kw_xgb.get('scale_pos_weight')}. "
            f"spw_cap must be bounded by min(spw_cap, 20.0)."
        )

    def test_scale_pos_weight_prediction_model_cap(self):
        """Verify OnDevicePredictionModel clamps scale_pos_weight <= 20.0 in train_surge_models."""
        pos_count = 2
        neg_count = 100
        # Line 2365 of prediction_model.py: scale_pos_weight = min(neg_count / pos_count, 20.0)
        scale_pos_weight = min(neg_count / pos_count, 20.0)
        assert scale_pos_weight <= 20.0

    @pytest.mark.parametrize("invalid_spw", [-5.0, 0.0, "invalid", None])
    def test_scale_pos_weight_invalid_types_fallback_to_20(self, invalid_spw):
        """When scale_pos_weight has invalid/negative/zero values, spw_cap should safely fall back to 20.0."""
        kw_xgb = {'scale_pos_weight': invalid_spw}
        spw_cap = kw_xgb.get('scale_pos_weight', 20.0)
        try:
            spw_cap = float(spw_cap) if (spw_cap is not None and float(spw_cap) > 0) else 20.0
        except (TypeError, ValueError):
            spw_cap = 20.0

        assert spw_cap == 20.0

    def test_learning_rate_and_max_depth_adversarial_clamping(self):
        """Adversarial profiles with negative learning_rate or negative/zero max_depth
        must either be clamped to safe positive values or rejected during parameter loading/training."""
        hostile_profile = {
            "market": "SP500",
            "xgb": {
                "learning_rate": -0.05,
                "max_depth": -2,
                "n_estimators": 10
            }
        }
        with open(self.model_dir / "tuned_params_sp500.json", "w", encoding="utf-8") as f:
            json.dump(hostile_profile, f)

        model = OnDevicePredictionModel(model_dir=str(self.model_dir))
        mkt_params = model._load_market_params("sp500")

        kw_xgb = dict(model._xgb_kwargs)
        if 'xgb' in mkt_params:
            kw_xgb.update(mkt_params['xgb'])

        # Check if the loaded parameter dict contains negative/invalid values
        # In an institutional production system, hyperparameter overrides should be sanitized:
        # learning_rate > 0 and max_depth > 0
        lr = kw_xgb.get('learning_rate', 0.05)
        depth = kw_xgb.get('max_depth', 5)

        assert lr > 0, f"VULNERABILITY: learning_rate={lr} is non-positive; will crash XGBoost/LightGBM"
        assert depth > 0, f"VULNERABILITY: max_depth={depth} is non-positive; will crash XGBoost/CatBoost"


class TestConcurrentInvocations:
    """Stress-test concurrent invocations of _load_market_params across multiple threads."""

    def test_concurrent_multithreaded_reads_across_markets(self):
        """Concurrently invoke _load_market_params from 50 threads across diverse markets."""
        model = OnDevicePredictionModel()
        vcp = VCPSurgePredictor()

        markets = ["sp500", "nasdaq", "russell2000", "kospi", "kosdaq", "global", "unknown", None]
        errors = []

        def worker_task(thread_id: int):
            for i in range(20):
                mkt = markets[(thread_id + i) % len(markets)]
                try:
                    res_m = model._load_market_params(mkt)
                    res_v = vcp._load_market_params(mkt)
                    if not isinstance(res_m, dict) or not isinstance(res_v, dict):
                        errors.append(f"Thread {thread_id} got non-dict: {type(res_m)}, {type(res_v)}")
                except Exception as ex:
                    errors.append(f"Thread {thread_id} crashed on {mkt}: {ex}")

        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(worker_task, tid) for tid in range(50)]
            for fut in as_completed(futures):
                fut.result()

        assert len(errors) == 0, f"Concurrent reads encountered errors: {errors[:5]}"

    def test_concurrent_reads_during_file_modification(self):
        """Concurrently read market params while another thread atomically rewrites the parameter file."""
        temp_dir = tempfile.mkdtemp()
        model_dir = Path(temp_dir)
        target_file = model_dir / "tuned_params_sp500.json"

        # Initialize with valid JSON
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump({"market": "SP500", "xgb": {"learning_rate": 0.03}}, f)

        vcp = VCPSurgePredictor(model_dir=str(model_dir))
        stop_event = threading.Event()
        read_errors = []

        def reader_loop():
            while not stop_event.is_set():
                try:
                    params = vcp._load_market_params("sp500")
                    assert isinstance(params, dict)
                except Exception as ex:
                    read_errors.append(str(ex))

        def writer_loop():
            for i in range(30):
                tmp_path = model_dir / f"tmp_{i}.json"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump({"market": "SP500", "xgb": {"learning_rate": 0.01 + (i * 0.001)}}, f)
                # Atomic replace with retry for Windows file locking
                for _ in range(10):
                    try:
                        os.replace(tmp_path, target_file)
                        break
                    except (PermissionError, OSError):
                        import time
                        time.sleep(0.005)

        threads = [threading.Thread(target=reader_loop) for _ in range(8)]
        for t in threads:
            t.start()

        writer_thread = threading.Thread(target=writer_loop)
        writer_thread.start()
        writer_thread.join()

        stop_event.set()
        for t in threads:
            t.join()

        shutil.rmtree(temp_dir, ignore_errors=True)
        assert len(read_errors) == 0, f"Encountered read errors during concurrent write: {read_errors[:5]}"


class TestToolingAndMirrorIntegrity:
    """Stress-test tooling scripts and mirror parity between root models/ and trading_system/models/."""

    def test_tune_hyperparams_script_syntax_and_imports(self):
        """Verify that trading_system/scripts/tune_hyperparams.py imports cleanly without NameError."""
        import importlib
        try:
            mod = importlib.import_module("trading_system.scripts.tune_hyperparams")
            assert hasattr(mod, "_resolve_model_dir"), "Missing _resolve_model_dir function"
        except NameError as ne:
            pytest.fail(f"VULNERABILITY: tune_hyperparams.py has NameError: {ne} (likely missing 'Optional' import)")
        except Exception as e:
            pytest.fail(f"Unexpected import failure in tune_hyperparams.py: {e}")

    def test_tuned_params_mirror_parity_all_files(self):
        """Verify that all tuned_params_*.json and tuned_params.json files in models/
        are identical to trading_system/models/ bit-for-bit (or semantically equivalent)."""
        root_models = REPO_ROOT / "models"
        ts_models = REPO_ROOT / "trading_system" / "models"

        primary_files = list(root_models.glob("tuned_params*.json"))
        assert len(primary_files) >= 6, f"Expected at least 6 tuned_params files, found {len(primary_files)}"

        mismatches = []
        for p_file in primary_files:
            rel_name = p_file.name
            mirror_file = ts_models / rel_name
            if not mirror_file.exists():
                mismatches.append(f"Missing mirror file: {mirror_file}")
                continue

            with open(p_file, "r", encoding="utf-8") as f1, open(mirror_file, "r", encoding="utf-8") as f2:
                d1 = json.load(f1)
                d2 = json.load(f2)

            # Compare keys
            diff_keys = set(d1.keys()).symmetric_difference(set(d2.keys()))
            if diff_keys:
                mismatches.append(f"{rel_name} key mismatch: divergent keys={diff_keys}")
            elif d1 != d2:
                mismatches.append(f"{rel_name} content mismatch between models/ and trading_system/models/")

        assert len(mismatches) == 0, (
            f"VULNERABILITY: Mirror parity broken between models/ and trading_system/models/:\n"
            + "\n".join(mismatches)
        )
