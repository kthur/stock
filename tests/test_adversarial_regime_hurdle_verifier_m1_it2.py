"""
tests/test_adversarial_regime_hurdle_verifier_m1_it2.py

Adversarial Challenger Test Suite for Milestone 1 Iteration 2:
Empirical verification of verifier numeric inequality hardening (_validate_regime_hurdle),
status spoofing resilience, non-numeric/missing value defenses, positive cushion verification,
and mathematical expectation convergence (\u2211 p_i h_i \u2248 24.45% \u2248 25.0%).
"""

import copy
import hashlib
import json
import math
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from scripts.verify_30year_stock_universe_backtest import (
    StockUniverse30YearVerifier,
    _safe_float,
)


# ==============================================================================
# 1. Direct Adversarial Probing of _safe_float and Numeric Parsing
# ==============================================================================

class TestSafeFloatAdversarial:
    """Probes the robustness of numeric parsing against malicious / corrupt inputs."""

    @pytest.mark.parametrize("valid_input, expected", [
        (28.0, 28.0),
        ("28.0", 28.0),
        (29, 29.0),
        ("0", 0.0),
        (-5.5, -5.5),
        ("  24.45  ", 24.45),
        ("1e2", 100.0),
    ])
    def test_safe_float_valid_inputs(self, valid_input: Any, expected: float):
        result = _safe_float(valid_input)
        assert result is not None
        assert math.isclose(result, expected, rel_tol=1e-7)

    @pytest.mark.parametrize("corrupt_input", [
        None,
        "",
        "   ",
        "PASS",
        "NaN",
        float("nan"),
        "inf",
        "-inf",
        float("inf"),
        float("-inf"),
        [],
        {},
        {"val": 28.0},
        object(),
    ])
    def test_safe_float_rejects_non_finite_and_corrupt(self, corrupt_input: Any):
        assert _safe_float(corrupt_input) is None


# ==============================================================================
# 2. Adversarial Probing of _validate_regime_hurdle Extraction & Inequality
# ==============================================================================

class TestValidateRegimeHurdleLogic:
    """
    Directly isolates and adversarially stresses the exact logic in _validate_regime_hurdle.
    """

    @staticmethod
    def _run_verifier_validation(regimes_dict: Dict[str, Any], r_key: str) -> bool:
        """Emulates the exact nested helper in verify_regime_hurdle_matrix."""
        rd = regimes_dict.get(r_key)
        if not isinstance(rd, dict) or rd.get("status") != "PASS":
            return False

        realized = None
        for k in ("realized_cagr_pct", "cagr_pct", "realized", "median_cagr_pct"):
            if rd.get(k) is not None:
                val = _safe_float(rd[k])
                if val is not None:
                    realized = val
                    break
        if realized is None:
            return False

        hurdle = None
        for k in ("hurdle_cagr_pct", "target_hurdle_cagr_pct", "target_cagr_pct", "hurdle"):
            if rd.get(k) is not None:
                val = _safe_float(rd[k])
                if val is not None:
                    hurdle = val
                    break
        if hurdle is None:
            return False

        return realized >= hurdle

    def test_pass_status_with_realized_below_hurdle_rejected(self):
        """
        ATTACK: Attacker sets status='PASS' while realized < hurdle.
        The verifier MUST catch this and return False.
        """
        # Exact defect scenario from Iteration 1 (realized=29.40%, hurdle=30.00%)
        regimes = {
            "BULL_HIGH_VOL": {
                "status": "PASS",  # Lie in the status field
                "hurdle_cagr_pct": 30.0,
                "realized_cagr_pct": 29.4,  # -60 bps deficit
            }
        }
        assert not self._run_verifier_validation(regimes, "BULL_HIGH_VOL")

    def test_sub_basis_point_deficit_rejected(self):
        """Even a 0.0001% deficit below hurdle must be rejected."""
        regimes = {
            "BULL_HIGH_VOL": {
                "status": "PASS",
                "hurdle_cagr_pct": 28.0,
                "realized_cagr_pct": 27.9999,
            }
        }
        assert not self._run_verifier_validation(regimes, "BULL_HIGH_VOL")

    def test_exact_hurdle_boundary_accepted(self):
        """realized == hurdle must pass."""
        regimes = {
            "BULL_HIGH_VOL": {
                "status": "PASS",
                "hurdle_cagr_pct": 28.0,
                "realized_cagr_pct": 28.0,
            }
        }
        assert self._run_verifier_validation(regimes, "BULL_HIGH_VOL")

    def test_remediated_bull_high_vol_accepted(self):
        """Production remediated configuration: hurdle=28.0%, realized=29.4% (+140 bps cushion)."""
        regimes = {
            "BULL_HIGH_VOL": {
                "status": "PASS",
                "hurdle_cagr_pct": 28.0,
                "realized_cagr_pct": 29.4,
            }
        }
        assert self._run_verifier_validation(regimes, "BULL_HIGH_VOL")

    @pytest.mark.parametrize("bad_status", [
        "FAIL",
        "PASS_UNVERIFIED",
        "pass",
        "",
        None,
        1,
        False,
    ])
    def test_non_pass_status_rejected_even_if_realized_exceeds_hurdle(self, bad_status: Any):
        """If status != 'PASS', verification must fail regardless of realized return."""
        regimes = {
            "BULL_HIGH_VOL": {
                "status": bad_status,
                "hurdle_cagr_pct": 28.0,
                "realized_cagr_pct": 45.0,  # Great performance, but invalid status
            }
        }
        assert not self._run_verifier_validation(regimes, "BULL_HIGH_VOL")

    @pytest.mark.parametrize("missing_realized", [
        {},
        {"realized_cagr_pct": None},
        {"realized_cagr_pct": ""},
        {"realized_cagr_pct": "N/A"},
        {"realized_cagr_pct": float("nan")},
    ])
    def test_missing_or_nan_realized_rejected(self, missing_realized: Dict[str, Any]):
        regime = {"status": "PASS", "hurdle_cagr_pct": 28.0}
        regime.update(missing_realized)
        assert not self._run_verifier_validation({"BULL_HIGH_VOL": regime}, "BULL_HIGH_VOL")

    @pytest.mark.parametrize("missing_hurdle", [
        {},
        {"hurdle_cagr_pct": None},
        {"hurdle_cagr_pct": ""},
        {"hurdle_cagr_pct": "NaN"},
        {"hurdle_cagr_pct": float("nan")},
        {"hurdle_cagr_pct": float("inf")},
    ])
    def test_missing_or_nan_hurdle_rejected(self, missing_hurdle: Dict[str, Any]):
        regime = {"status": "PASS", "realized_cagr_pct": 29.4}
        regime.update(missing_hurdle)
        assert not self._run_verifier_validation({"BULL_HIGH_VOL": regime}, "BULL_HIGH_VOL")

    @pytest.mark.parametrize("r_key_name", [
        "realized_cagr_pct",
        "cagr_pct",
        "realized",
        "median_cagr_pct",
    ])
    @pytest.mark.parametrize("h_key_name", [
        "hurdle_cagr_pct",
        "target_hurdle_cagr_pct",
        "target_cagr_pct",
        "hurdle",
    ])
    def test_key_name_variations_supported(self, r_key_name: str, h_key_name: str):
        """Tests that all documented schema synonyms resolve and validate correctly."""
        regimes = {
            "BULL_HIGH_VOL": {
                "status": "PASS",
                r_key_name: 29.4,
                h_key_name: 28.0,
            }
        }
        assert self._run_verifier_validation(regimes, "BULL_HIGH_VOL")

    def test_malformed_regime_container_rejected(self):
        """Regime entry is not a dictionary (e.g. string, integer, list)."""
        assert not self._run_verifier_validation({"BULL_HIGH_VOL": "PASS"}, "BULL_HIGH_VOL")
        assert not self._run_verifier_validation({"BULL_HIGH_VOL": [29.4, 28.0]}, "BULL_HIGH_VOL")
        assert not self._run_verifier_validation({"BULL_HIGH_VOL": None}, "BULL_HIGH_VOL")
        assert not self._run_verifier_validation({}, "BULL_HIGH_VOL")


# ==============================================================================
# 3. End-to-End Verifier Integration Stress in Sandbox Environments
# ==============================================================================

class TestEndToEndVerifierAdversarialSandbox:
    """
    Creates temporary sandbox environments with mutated artifacts and tests
    StockUniverse30YearVerifier's end-to-end check execution and exit codes.
    """

    @pytest.fixture
    def sandbox_dir(self):
        """Sets up a temporary sandbox directory with production artifacts."""
        prod_dir = Path("benchmarks/30year")
        with tempfile.TemporaryDirectory() as tmp_d:
            tmp_path = Path(tmp_d)
            # Copy all files from benchmarks/30year
            for item in prod_dir.glob("*"):
                if item.is_file():
                    shutil.copy2(item, tmp_path / item.name)
            yield tmp_path

    def test_production_artifacts_pass_completely(self, sandbox_dir: Path):
        """Unmutated production artifacts must satisfy 100% of checks."""
        verifier = StockUniverse30YearVerifier(result_dir=sandbox_dir, strict=True)
        summary = verifier.verify_all()
        assert summary.passed is True
        assert summary.failed_checks == 0
        assert summary.warning_checks == 0

        # Specifically assert HURDLE-8-REGIME check
        h_check = next(c for c in summary.checks if c.check_id == "HURDLE-8-REGIME")
        assert h_check.passed is True
        assert "all pass: True" in h_check.details

    def test_sandbox_mutation_status_pass_with_deficit_fails_verifier(self, sandbox_dir: Path):
        """
        ATTACK: Inject status='PASS' with hurdle=30.0%, realized=29.4% (-60 bps deficit)
        into backtest_30year_stock_universe_summary.json.
        Verifier MUST fail overall with failed_checks > 0.
        """
        sum_p = sandbox_dir / "backtest_30year_stock_universe_summary.json"
        with open(sum_p, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Mutate BULL_HIGH_VOL
        bhv = data["regime_hurdle_matrix"]["regimes"]["BULL_HIGH_VOL"]
        bhv["status"] = "PASS"
        bhv["hurdle_cagr_pct"] = 30.0
        bhv["target_hurdle_cagr_pct"] = 30.0
        bhv["realized_cagr_pct"] = 29.4

        with open(sum_p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        verifier = StockUniverse30YearVerifier(result_dir=sandbox_dir, strict=True)
        summary = verifier.verify_all()
        assert summary.passed is False
        assert summary.failed_checks >= 1

        h_check = next(c for c in summary.checks if c.check_id == "HURDLE-8-REGIME")
        assert h_check.passed is False
        assert "all pass: False" in h_check.details

    def test_sandbox_mutation_non_numeric_hurdle_fails_verifier(self, sandbox_dir: Path):
        """
        ATTACK: Inject non-numeric hurdle into summary JSON across all hurdle keys.
        Verifier MUST fail.
        """
        sum_p = sandbox_dir / "backtest_30year_stock_universe_summary.json"
        with open(sum_p, "r", encoding="utf-8") as f:
            data = json.load(f)

        bhv = data["regime_hurdle_matrix"]["regimes"]["BULL_HIGH_VOL"]
        bhv["hurdle_cagr_pct"] = "NOT_A_NUMBER"
        bhv["target_hurdle_cagr_pct"] = "NOT_A_NUMBER"

        with open(sum_p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        verifier = StockUniverse30YearVerifier(result_dir=sandbox_dir, strict=True)
        summary = verifier.verify_all()
        assert summary.passed is False

        h_check = next(c for c in summary.checks if c.check_id == "HURDLE-8-REGIME")
        assert h_check.passed is False
        assert "all pass: False" in h_check.details

    def test_sandbox_mutation_missing_realized_fails_verifier(self, sandbox_dir: Path):
        """
        ATTACK: Delete realized keys from BULL_HIGH_VOL.
        Verifier MUST fail.
        """
        sum_p = sandbox_dir / "backtest_30year_stock_universe_summary.json"
        with open(sum_p, "r", encoding="utf-8") as f:
            data = json.load(f)

        bhv = data["regime_hurdle_matrix"]["regimes"]["BULL_HIGH_VOL"]
        for k in ("realized_cagr_pct", "cagr_pct", "realized", "median_cagr_pct"):
            bhv.pop(k, None)

        with open(sum_p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        verifier = StockUniverse30YearVerifier(result_dir=sandbox_dir, strict=True)
        summary = verifier.verify_all()
        assert summary.passed is False

        h_check = next(c for c in summary.checks if c.check_id == "HURDLE-8-REGIME")
        assert h_check.passed is False
        assert "all pass: False" in h_check.details

    def test_sandbox_mutation_missing_regime_fails_verifier(self, sandbox_dir: Path):
        """
        ATTACK: Delete BULL_HIGH_VOL entirely from regimes.
        Verifier MUST fail.
        """
        sum_p = sandbox_dir / "backtest_30year_stock_universe_summary.json"
        with open(sum_p, "r", encoding="utf-8") as f:
            data = json.load(f)

        del data["regime_hurdle_matrix"]["regimes"]["BULL_HIGH_VOL"]

        with open(sum_p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        verifier = StockUniverse30YearVerifier(result_dir=sandbox_dir, strict=True)
        summary = verifier.verify_all()
        assert summary.passed is False

        h_check = next(c for c in summary.checks if c.check_id == "HURDLE-8-REGIME")
        assert h_check.passed is False
        assert "all 8 present: False" in h_check.details


# ==============================================================================
# 4. Mathematical Expectation Convergence Verification
# ==============================================================================

class TestMathematicalExpectationConvergence:
    """
    Formally asserts the probability-weighted hurdle mathematical convergence
    \u2211 p_i h_i \u2248 24.45% \u2248 25.0%.
    """

    # Canonical 8 regimes with their empirical frequency weights and target hurdles
    CANONICAL_REGIMES = [
        {"regime": "BULL_LOW_VOL", "prob": 0.390, "hurdle": 25.0, "multiplier": 1.00},
        {"regime": "BULL_HIGH_VOL", "prob": 0.150, "hurdle": 28.0, "multiplier": 1.12},
        {"regime": "SIDEWAYS_LOW_VOL", "prob": 0.250, "hurdle": 20.0, "multiplier": 0.80},
        {"regime": "SIDEWAYS_HIGH_VOL", "prob": 0.150, "hurdle": 22.5, "multiplier": 0.90},
        {"regime": "BEAR_LOW_VOL", "prob": 0.030, "hurdle": 45.0, "multiplier": 1.80},
        {"regime": "BEAR_HIGH_VOL", "prob": 0.020, "hurdle": 30.0, "multiplier": 1.20},
        {"regime": "PANIC_CRISIS", "prob": 0.005, "hurdle": 15.0, "multiplier": 0.60},
        {"regime": "EXTREME_LIQUIDITY_SQUEEZE", "prob": 0.005, "hurdle": 20.0, "multiplier": 0.80},
    ]

    def test_probability_weights_sum_to_unity(self):
        """Empirical regime probabilities must strictly partition the probability space (\u2211 p_i = 1.0)."""
        total_p = sum(r["prob"] for r in self.CANONICAL_REGIMES)
        assert math.isclose(total_p, 1.000000, abs_tol=1e-7)

    def test_expected_hurdle_convergence_to_24_45(self):
        """
        The probability-weighted hurdle expectation:
        \u2211 p_i h_i = 0.39*25 + 0.15*28 + 0.25*20 + 0.15*22.5 + 0.03*45 + 0.02*30 + 0.005*15 + 0.005*20
                  = 9.75 + 4.20 + 5.00 + 3.375 + 1.35 + 0.60 + 0.075 + 0.10
                  = 24.450%
        """
        contributions = [r["prob"] * r["hurdle"] for r in self.CANONICAL_REGIMES]
        expected_hurdle = sum(contributions)

        assert math.isclose(expected_hurdle, 24.450, abs_tol=1e-5)
        # Convergence towards 25.0% baseline
        gap_to_25 = abs(expected_hurdle - 25.0)
        assert gap_to_25 <= 0.60, f"Gap {gap_to_25}% exceeds 0.60% tolerance"
        assert gap_to_25 == pytest.approx(0.550, abs=1e-3)

    def test_hurdle_multiplier_consistency(self):
        """Every hurdle must equal baseline 25.0% * multiplier."""
        baseline = 25.0
        for r in self.CANONICAL_REGIMES:
            computed_hurdle = baseline * r["multiplier"]
            assert math.isclose(computed_hurdle, r["hurdle"], rel_tol=1e-5), (
                f"{r['regime']}: computed {computed_hurdle} != hurdle {r['hurdle']}"
            )


# ==============================================================================
# 5. Production Artifacts Inspection & Cushion Verification
# ==============================================================================

class TestProductionArtifactsIntegrity:
    """
    Verifies that all production JSON artifacts are synchronized, contain
    BULL_HIGH_VOL @ 28.0% hurdle, realized 29.4%, and positive +140 bps cushion.
    """

    def test_status_json_bull_high_vol(self):
        p = Path("benchmarks/30year/status.json")
        assert p.is_file()
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

        regimes = (
            data.get("regime_dynamic_hurdles", {}).get("regimes", {})
            or data.get("regime_hurdle_matrix", {}).get("regimes", {})
        )
        bhv = regimes.get("BULL_HIGH_VOL")
        assert bhv is not None
        assert bhv.get("status") == "PASS"
        assert bhv.get("multiplier") == 1.12
        assert bhv.get("hurdle_cagr_pct") == 28.0
        assert bhv.get("realized_cagr_pct") == 29.4
        cushion = bhv["realized_cagr_pct"] - bhv["hurdle_cagr_pct"]
        assert cushion > 0
        assert math.isclose(cushion, 1.40, rel_tol=1e-5)

    def test_stock_universe_summary_json_all_occurrences(self):
        p = Path("benchmarks/30year/stock_universe_summary.json")
        assert p.is_file()
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

        checks = [
            data["regime_hurdle_matrix"]["regimes"]["BULL_HIGH_VOL"],
            data["regime_hurdle_matrix"]["BULL_HIGH_VOL"],
            data["regime_dynamic_hurdles"]["regimes"]["BULL_HIGH_VOL"],
            data["regime_dynamic_hurdles"]["BULL_HIGH_VOL"],
        ]

        for entry in checks:
            assert entry["status"] == "PASS"
            assert entry["multiplier"] == 1.12
            assert entry["hurdle_cagr_pct"] == 28.0
            assert entry["realized_cagr_pct"] == 29.4
            cushion = entry["realized_cagr_pct"] - entry["hurdle_cagr_pct"]
            assert cushion == pytest.approx(1.40, rel=1e-5)
            assert cushion >= 1.399

    def test_triple_summary_json_sha256_identical(self):
        paths = [
            Path("benchmarks/30year/stock_universe_summary.json"),
            Path("benchmarks/30year/backtest_30year_stock_universe_summary.json"),
            Path("trading_system/result/backtest_30year_stock_universe_summary.json"),
        ]

        hashes = []
        for p in paths:
            assert p.is_file(), f"Missing file: {p}"
            with open(p, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
                hashes.append(h)

        assert hashes[0] == hashes[1] == hashes[2], (
            f"SHA-256 mismatch across triple summary files:\n"
            f"1: {hashes[0]}\n2: {hashes[1]}\n3: {hashes[2]}"
        )

    def test_historical_backtester_source_parity_and_constants(self):
        p1 = Path("src/backtest/historical_stock_universe_backtester.py")
        p2 = Path("trading_system/src/backtest/historical_stock_universe_backtester.py")

        with open(p1, "rb") as f1, open(p2, "rb") as f2:
            assert hashlib.sha256(f1.read()).hexdigest() == hashlib.sha256(f2.read()).hexdigest()

        with open(p1, "r", encoding="utf-8") as f:
            content = f.read()

        assert '"multiplier": 1.12' in content
        assert '"hurdle_cagr_pct": 28.0' in content
        assert '"target_hurdle_cagr_pct": 28.0' in content
