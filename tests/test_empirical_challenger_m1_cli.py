import os
import sys
import json
import shutil
import tempfile
import hashlib
import subprocess
from pathlib import Path
from unittest.mock import patch
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

def _get_dir_state(d: Path):
    res = {}
    if not d.exists():
        return res
    for p in d.iterdir():
        if p.is_file():
            res[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return res

class TestEmpiricalCLIStressIsolation:
    """Empirical challenge to verify zero side-effects on production model directories
    when executing tune_models.py and tune_hyperparams.py with custom --output-dir."""

    @pytest.fixture(autouse=True)
    def setup_dirs(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_challenger_cli_")
        self.output_dir = Path(self.temp_dir)
        self.models_dir = REPO_ROOT / "models"
        self.ts_models_dir = REPO_ROOT / "trading_system" / "models"
        self.pre_models = _get_dir_state(self.models_dir)
        self.pre_ts_models = _get_dir_state(self.ts_models_dir)
        yield
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cli_tune_models_custom_output_dir_isolation_sp500(self):
        """Execute tune_models.py --market SP500 --output-dir <temp> and verify zero production mutation."""
        script = REPO_ROOT / "trading_system" / "scripts" / "tune_models.py"
        cmd = [
            sys.executable,
            str(script),
            "--trials", "1",
            "--output-dir", str(self.output_dir),
            "--market", "SP500",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=str(REPO_ROOT))
        assert res.returncode == 0, f"tune_models.py failed: {res.stderr}\nSTDOUT: {res.stdout}"

        expected_out = self.output_dir / "tuned_params_sp500.json"
        assert expected_out.exists(), f"Target file not found in {self.output_dir}"

        with open(expected_out, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("market") == "SP500"

        # Verify zero side-effects on production directories
        post_models = _get_dir_state(self.models_dir)
        post_ts_models = _get_dir_state(self.ts_models_dir)
        assert self.pre_models == post_models, "models/ was mutated during custom --output-dir execution!"
        assert self.pre_ts_models == post_ts_models, "trading_system/models/ was mutated during custom --output-dir execution!"

    def test_cli_tune_models_custom_output_dir_isolation_global(self):
        """Execute tune_models.py without --market (global) --output-dir <temp> and verify zero production mutation."""
        script = REPO_ROOT / "trading_system" / "scripts" / "tune_models.py"
        cmd = [
            sys.executable,
            str(script),
            "--trials", "1",
            "--output-dir", str(self.output_dir),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=str(REPO_ROOT))
        assert res.returncode == 0, f"tune_models.py failed: {res.stderr}\nSTDOUT: {res.stdout}"

        expected_out = self.output_dir / "tuned_params.json"
        assert expected_out.exists(), f"Target file not found in {self.output_dir}"

        with open(expected_out, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("market") == "GLOBAL"

        # Verify zero side-effects on production directories
        post_models = _get_dir_state(self.models_dir)
        post_ts_models = _get_dir_state(self.ts_models_dir)
        assert self.pre_models == post_models, "models/ was mutated during custom --output-dir execution!"
        assert self.pre_ts_models == post_ts_models, "trading_system/models/ was mutated during custom --output-dir execution!"

    def test_cli_tune_hyperparams_custom_output_dir_isolation_global(self):
        """Execute tune_hyperparams.py without --market (global) --output-dir <temp> and verify zero production mutation."""
        script = REPO_ROOT / "trading_system" / "scripts" / "tune_hyperparams.py"
        cmd = [
            sys.executable,
            str(script),
            "--trials", "1",
            "--output-dir", str(self.output_dir),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=str(REPO_ROOT))
        assert res.returncode == 0, f"tune_hyperparams.py failed: {res.stderr}\nSTDOUT: {res.stdout}"

        expected_out = self.output_dir / "tuned_params.json"
        assert expected_out.exists(), f"Target file not found in {self.output_dir}"

        with open(expected_out, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("market") == "GLOBAL"

        # Verify zero side-effects on production directories
        post_models = _get_dir_state(self.models_dir)
        post_ts_models = _get_dir_state(self.ts_models_dir)
        assert self.pre_models == post_models, "models/ was mutated during custom --output-dir execution!"
        assert self.pre_ts_models == post_ts_models, "trading_system/models/ was mutated during custom --output-dir execution!"

    def test_cli_tune_hyperparams_custom_output_dir_with_market_mock_data(self):
        """Execute tune_hyperparams.main with market='NASDAQ' using mock training data,
        verifying output file in custom output_dir and ZERO production directory mutation."""
        from trading_system.scripts import tune_hyperparams
        from trading_system.scripts.tune_models import create_mock_tuning_data
        from src.ai.prediction_model import OnDevicePredictionModel
        import pandas as pd

        model = OnDevicePredictionModel()
        mock_df = create_mock_tuning_data(model)
        mock_universe = pd.DataFrame([{"symbol": "AAPL", "market": "NASDAQ"}])

        with patch.object(tune_hyperparams, "load_data_for_tuning", return_value=(mock_df, mock_universe)):
            tune_hyperparams.main(trials=1, output_dir=str(self.output_dir), market="NASDAQ")

        expected_out = self.output_dir / "tuned_params_nasdaq.json"
        assert expected_out.exists(), f"Target file not found in {self.output_dir}"

        with open(expected_out, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("market") == "NASDAQ"

        # Verify zero side-effects on production directories
        post_models = _get_dir_state(self.models_dir)
        post_ts_models = _get_dir_state(self.ts_models_dir)
        assert self.pre_models == post_models, "models/ was mutated during custom --output-dir execution!"
        assert self.pre_ts_models == post_ts_models, "trading_system/models/ was mutated during custom --output-dir execution!"

    def test_cli_tune_hyperparams_unsupported_market_graceful_no_mutation(self):
        """Execute tune_hyperparams.py via CLI with an unpopulated market (e.g. UNKNOWN)
        and verify it aborts cleanly with 0 side effects on production directories."""
        script = REPO_ROOT / "trading_system" / "scripts" / "tune_hyperparams.py"
        cmd = [
            sys.executable,
            str(script),
            "--trials", "1",
            "--output-dir", str(self.output_dir),
            "--market", "UNKNOWN_MKT",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=str(REPO_ROOT))
        assert res.returncode == 0, f"tune_hyperparams.py crashed on unknown market: {res.stderr}"

        # Verify zero side-effects on production directories
        post_models = _get_dir_state(self.models_dir)
        post_ts_models = _get_dir_state(self.ts_models_dir)
        assert self.pre_models == post_models, "models/ was mutated during unknown market execution!"
        assert self.pre_ts_models == post_ts_models, "trading_system/models/ was mutated during unknown market execution!"
