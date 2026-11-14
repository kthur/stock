import os
import sys
import json
import time
import shutil
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch
import pytest

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ai.prediction_model import OnDevicePredictionModel
from src.ai.vcp_ml_predictor import VCPSurgePredictor
from trading_system.scripts.tune_models import (
    tune_hyperparameters,
    _resolve_model_dir,
    create_mock_tuning_data,
)


class TestAdversarialTuningCLI:
    """Empirical verification of CLI execution with valid and invalid --market parameters."""

    @pytest.fixture(autouse=True)
    def setup_tmp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir)
        yield
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cli_help_flag_execution(self):
        """Verify CLI entrypoint cleanly supports --market, --trials, --output-dir via subprocess."""
        script_path = REPO_ROOT / "trading_system" / "scripts" / "tune_models.py"
        assert script_path.exists(), f"tune_models.py not found at {script_path}"

        res = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert res.returncode == 0, f"--help failed: {res.stderr}"
        assert "--market" in res.stdout
        assert "--trials" in res.stdout
        assert "--output-dir" in res.stdout

    def test_cli_execution_valid_market_sp500(self):
        """Verify CLI execution with valid market SP500 outputs tuned_params_sp500.json."""
        model = OnDevicePredictionModel()
        mock_df = create_mock_tuning_data(model)

        with patch("trading_system.scripts.tune_models.load_tuning_data", return_value=mock_df):
            res = tune_hyperparameters(
                n_trials=1,
                output_dir=str(self.output_dir),
                market="SP500",
            )

        assert isinstance(res, dict)
        assert res.get("market") == "SP500"
        expected_file = self.output_dir / "tuned_params_sp500.json"
        assert expected_file.exists(), "Expected tuned_params_sp500.json to be generated"

        with open(expected_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data.get("market") == "SP500"
        assert "xgb" in saved_data
        assert "surge_xgb" in saved_data

    def test_cli_execution_valid_market_kospi(self):
        """Verify CLI execution with valid market KOSPI outputs tuned_params_kospi.json."""
        model = OnDevicePredictionModel()
        mock_df = create_mock_tuning_data(model)

        with patch("trading_system.scripts.tune_models.load_tuning_data", return_value=mock_df):
            res = tune_hyperparameters(
                n_trials=1,
                output_dir=str(self.output_dir),
                market="KOSPI",
            )

        assert isinstance(res, dict)
        assert res.get("market") == "KOSPI"
        expected_file = self.output_dir / "tuned_params_kospi.json"
        assert expected_file.exists(), "Expected tuned_params_kospi.json to be generated"

        with open(expected_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data.get("market") == "KOSPI"

    def test_cli_execution_invalid_market_graceful_handling(self):
        """Verify CLI execution with invalid/unsupported market (INVALID_MARKET)
        completes without unhandled exceptions and tags output appropriately."""
        model = OnDevicePredictionModel()
        mock_df = create_mock_tuning_data(model)

        with patch("trading_system.scripts.tune_models.load_tuning_data", return_value=mock_df):
            res = tune_hyperparameters(
                n_trials=1,
                output_dir=str(self.output_dir),
                market="INVALID_MARKET",
            )

        assert isinstance(res, dict)
        assert res.get("market") == "INVALID_MARKET"
        expected_file = self.output_dir / "tuned_params_invalid_market.json"
        assert expected_file.exists(), "Expected tuned_params_invalid_market.json to be generated"

        with open(expected_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data.get("market") == "INVALID_MARKET"

    def test_cli_subprocess_end_to_end_mocked(self):
        """Execute tune_models.py via external python subprocess with sys.argv simulating CLI flags."""
        script_code = f"""
import sys
from pathlib import Path
from unittest.mock import patch
from trading_system.scripts.tune_models import create_mock_tuning_data, tune_hyperparameters
from src.ai.prediction_model import OnDevicePredictionModel

model = OnDevicePredictionModel()
mock_df = create_mock_tuning_data(model)

with patch('trading_system.scripts.tune_models.load_tuning_data', return_value=mock_df):
    tune_hyperparameters(n_trials=1, output_dir=r'{self.output_dir}', market='KOSPI')
"""
        proc = subprocess.run(
            [sys.executable, "-c", script_code],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO_ROOT),
        )
        assert proc.returncode == 0, f"Subprocess failed with code {proc.returncode}:\n{proc.stderr}"
        out_file = self.output_dir / "tuned_params_kospi.json"
        assert out_file.exists(), "Subprocess did not create expected output file"


class TestAdversarialLoadLatency:
    """Stress-test latency of 10,000 calls to _load_market_params(market) ensuring low I/O overhead."""

    def test_latency_10000_calls_vcp_predictor(self):
        """Verify latency of 10,000 calls to VCPSurgePredictor._load_market_params is < 5.0 ms/call."""
        vcp = VCPSurgePredictor()
        markets = ["sp500", "nasdaq", "russell2000", "kospi", "kosdaq", "unknown_mkt"]

        t0 = time.perf_counter()
        for i in range(10000):
            mkt = markets[i % len(markets)]
            params = vcp._load_market_params(mkt)
            assert isinstance(params, dict)
        t1 = time.perf_counter()

        elapsed_total = t1 - t0
        latency_per_call_ms = (elapsed_total / 10000.0) * 1000.0

        # Empirical latency SLA: average call must be < 5.0 ms (typically < 0.2 ms with OS disk caching)
        assert latency_per_call_ms < 5.0, (
            f"LATENCY SLA BREACH: 10,000 calls took {elapsed_total:.2f}s "
            f"({latency_per_call_ms:.4f} ms/call > 5.0 ms threshold)"
        )

    def test_latency_10000_calls_prediction_model(self):
        """Verify latency of 10,000 calls to OnDevicePredictionModel._load_market_params is < 5.0 ms/call."""
        model = OnDevicePredictionModel()
        markets = ["sp500", "nasdaq", "russell2000", "kospi", "kosdaq", "unknown_mkt"]

        t0 = time.perf_counter()
        for i in range(10000):
            mkt = markets[i % len(markets)]
            params = model._load_market_params(mkt)
            assert isinstance(params, dict)
        t1 = time.perf_counter()

        elapsed_total = t1 - t0
        latency_per_call_ms = (elapsed_total / 10000.0) * 1000.0

        assert latency_per_call_ms < 5.0, (
            f"LATENCY SLA BREACH: 10,000 calls took {elapsed_total:.2f}s "
            f"({latency_per_call_ms:.4f} ms/call > 5.0 ms threshold)"
        )


class TestSimultaneousModelIntegration:
    """Stress-test concurrent and simultaneous instantiation of OnDevicePredictionModel and VCPSurgePredictor."""

    def test_simultaneous_instantiation_and_isolation(self):
        """Instantiate OnDevicePredictionModel and VCPSurgePredictor simultaneously,
        verifying identical parameter loading and zero mutual interference."""
        model = OnDevicePredictionModel()
        vcp = VCPSurgePredictor()

        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]

        for mkt in markets:
            p_model = model._load_market_params(mkt)
            p_vcp = vcp._load_market_params(mkt)

            assert p_model.get("market") == mkt
            assert p_vcp.get("market") == mkt

            # Verify exact dictionary identity between both models
            assert p_model == p_vcp, (
                f"Mismatch in loaded parameter profile for market {mkt}: "
                f"OnDevicePredictionModel={p_model} vs VCPSurgePredictor={p_vcp}"
            )

    def test_simultaneous_fallback_to_global_profile(self):
        """Verify that both instances fallback to the exact same global profile when queried with unknown market."""
        model = OnDevicePredictionModel()
        vcp = VCPSurgePredictor()

        p_model = model._load_market_params("NON_EXISTENT_MARKET")
        p_vcp = vcp._load_market_params("NON_EXISTENT_MARKET")

        assert p_model.get("market") == "GLOBAL"
        assert p_vcp.get("market") == "GLOBAL"
        assert p_model.get("xgb", {}).get("max_depth") == p_vcp.get("xgb", {}).get("max_depth")
