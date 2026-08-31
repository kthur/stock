import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest

from trading_system.scripts.verify_gha_artifacts import (
    MARKETS,
    STRATEGIES,
    STRATEGY_PANEL_ALIASES,
    check_regression,
    check_surge,
    check_vcp,
    check_vcp_ml,
    check_lead_lag,
    check_generic_strategy,
    verify_market_strategies,
    verify_ensemble,
    verify_gh_pages,
    run_verification,
)


CANONICAL_31 = [
    "regression", "surge", "lead_lag", "vcp_rule", "vcp_ml", "lstm",
    "stat_arb", "sector_rotation", "rim_valuation", "event_driven", "mq_factor",
    "iv_skew", "order_flow", "short_term_reversal", "arm_factor",
    "card_factor", "latr_factor", "inst_foreign_sector",
    "supply_chain", "sentiment", "factor_neutralized", "vol_target",
    "microstructure", "accruals_quality", "short_squeeze", "valueup_catalyst",
    "trend_efficiency", "gamma_squeeze", "insider_buying", "darkpool", "earnings_tone_drift"
]


# =========================================================================
# 1. Canonical Bijection and Registry Verification
# =========================================================================

def test_canonical_31_exact_match():
    assert len(STRATEGIES) == 31
    assert STRATEGIES == CANONICAL_31
    assert STRATEGIES[29] == "darkpool"
    assert STRATEGIES[30] == "earnings_tone_drift"


def test_strategy_panel_aliases_all_31_and_ensemble():
    assert len(STRATEGY_PANEL_ALIASES) == 32
    assert "ensemble" in STRATEGY_PANEL_ALIASES
    for s in CANONICAL_31:
        assert s in STRATEGY_PANEL_ALIASES, f"Strategy {s} missing alias definition"


# =========================================================================
# 2. Adversarial File Content Stress (Empty, Corrupt, Garbage, Edge Cases)
# =========================================================================

@pytest.mark.parametrize("corrupt_input", [
    "",
    "   \n\t  \n  ",
    "데이터 없음",
    "No data",
    "=== Header Only ===\nDate: 2026-09-01\nSymbol\tExpRet\n",
    "\x00\x00\x00\x00binary garbage\xff\xfe",
    "Malformed line 1\nMalformed line 2\nNaN\nNone\n#DIV/0!",
    "SYM1\tNaN\nSYM2\tNone\nSYM3\tinf\nSYM4\t-inf",
])
def test_check_regression_adversarial_inputs(corrupt_input):
    res = check_regression(corrupt_input, "SP500")
    assert res.valid is False


def test_check_regression_all_zeros():
    content = "=== Regression ===\nDate: 2026-09-01\n" + "\n".join(f"SYM{i}\t0.000000" for i in range(20))
    res = check_regression(content, "SP500")
    assert res.valid is False
    assert "all expected returns are 0.0" in res.message


def test_check_regression_boundary_count():
    c9 = "Date: 2026-09-01\n" + "\n".join(f"SYM{i}\t0.05" for i in range(9))
    r9 = check_regression(c9, "SP500")
    assert r9.valid is False
    assert r9.count == 9

    c10 = "Date: 2026-09-01\n" + "\n".join(f"SYM{i}\t0.05" for i in range(10))
    r10 = check_regression(c10, "SP500")
    assert r10.valid is True
    assert r10.count == 10


@pytest.mark.parametrize("corrupt_input", [
    "",
    "데이터 없음",
    "No data",
    "[SP500] AAPL: 0.0%",
    "\n".join(f"[SP500] SYM{i} (Name): 0.0%" for i in range(15)),
    "\n".join(f"[KOSPI] SYM{i} (Name): 15.0%" for i in range(15)),
    "\n".join(f"[SP500] SYM{i} (Name): 15.0%" for i in range(5)),
])
def test_check_surge_adversarial_inputs(corrupt_input):
    res = check_surge(corrupt_input, "SP500")
    assert res.valid is False


@pytest.mark.parametrize("corrupt_input", [
    "",
    "데이터 없음",
    "No data",
    "\n".join(f"[SP500] SYM{i} (Name): 0.0%" for i in range(15)),
    "\n".join(f"[KOSPI] SYM{i} (Name): 20.0%" for i in range(15)),
    "\n".join(f"[SP500] SYM{i} (Name): 20.0%" for i in range(6)),
])
def test_check_vcp_ml_adversarial_inputs(corrupt_input):
    res = check_vcp_ml(corrupt_input, "SP500")
    assert res.valid is False


@pytest.mark.parametrize("corrupt_input", [
    "",
    "데이터 없음",
    "No data",
    "\n".join(f"[KOSPI] SYM{i}" for i in range(15)),
    "\n".join(f"[SP500] SYM{i}" for i in range(7)),
])
def test_check_vcp_rule_and_lead_lag_adversarial(corrupt_input):
    assert check_vcp(corrupt_input, "SP500").valid is False
    assert check_lead_lag(corrupt_input, "SP500").valid is False


@pytest.mark.parametrize("strat_name", CANONICAL_31[5:])
def test_check_generic_strategy_all_31_extended_adversarial(strat_name):
    # Empty
    assert check_generic_strategy("", "SP500", strat_name).valid is False
    assert check_generic_strategy("데이터 없음", "SP500", strat_name).valid is False

    # All zeros
    zero_content = "Rank\tSymbol\tScore\n" + "\n".join(f"{i+1}\tSYM{i}\t0.000" for i in range(15))
    assert check_generic_strategy(zero_content, "SP500", strat_name).valid is False

    # Under min count (8 items)
    under_content = "Rank\tSymbol\tScore\n" + "\n".join(f"{i+1}\tSYM{i}\t0.85" for i in range(8))
    assert check_generic_strategy(under_content, "SP500", strat_name).valid is False

    # Valid (12 items with non-zero)
    valid_content = "Rank\tSymbol\tScore\n" + "\n".join(f"{i+1}\tSYM{i}\t0.85" for i in range(12))
    res_valid = check_generic_strategy(valid_content, "SP500", strat_name)
    assert res_valid.valid is True
    assert res_valid.count == 12


# =========================================================================
# 3. Missing Directory & Partial Strategy Directory Verification
# =========================================================================

def test_verify_market_strategies_empty_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        m_res = verify_market_strategies(tmp_path, "SP500")
        assert len(m_res.strategies) == 31
        assert m_res.all_strategies_valid is False
        for s in CANONICAL_31:
            assert m_res.strategies[s].valid is False
            assert m_res.strategies[s].file_found is False


def test_verify_market_strategies_partial_missing_strategy():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        for strat in CANONICAL_31:
            if strat in ["darkpool", "earnings_tone_drift"]:
                continue
            if strat == "regression":
                fname = "pipeline_result_SP500.txt"
                content = "Date: 2026-09-01\n" + "\n".join(f"SYM{i}\t0.12" for i in range(12))
            elif strat == "surge":
                fname = "surge_predictions_SP500.txt"
                content = "\n".join(f"[SP500] SYM{i} (Name): 15.0%" for i in range(12))
            elif strat == "vcp_rule":
                fname = "vcp_patterns_SP500.txt"
                content = "\n".join(f"[SP500] SYM{i}" for i in range(12))
            elif strat == "vcp_ml":
                fname = "vcp_ml_predictions_SP500.txt"
                content = "\n".join(f"[SP500] SYM{i} (Name): 20.0%" for i in range(12))
            elif strat == "lead_lag":
                fname = "lead_lag_predictions_SP500.txt"
                content = "\n".join(f"[SP500] SYM{i}" for i in range(12))
            else:
                fname = f"{strat}_predictions_SP500.txt"
                content = "Date: 2026-09-01\n" + "\n".join(f"SYM{i}\t0.75" for i in range(12))
            (tmp_path / fname).write_text(content, encoding="utf-8")

        m_res = verify_market_strategies(tmp_path, "SP500")
        assert m_res.all_strategies_valid is False
        assert m_res.strategies["darkpool"].valid is False
        assert m_res.strategies["darkpool"].file_found is False
        assert m_res.strategies["earnings_tone_drift"].valid is False
        assert m_res.strategies["regression"].valid is True


# =========================================================================
# 4. Ensemble Predictions Adversarial Stress
# =========================================================================

def test_verify_ensemble_adversarial():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1. Missing file
        res = verify_ensemble(tmp_path)
        assert res.valid is False
        assert res.file_found is False

        # 2. Empty file
        ens_file = tmp_path / "ensemble_predictions.txt"
        ens_file.write_text("", encoding="utf-8")
        assert verify_ensemble(tmp_path).valid is False

        # 3. Data missing notice
        ens_file.write_text("데이터 없음", encoding="utf-8")
        assert verify_ensemble(tmp_path).valid is False

        # 4. Valid file matching pipeline format
        valid_ens = (
            "=== 31-Strategy Ensemble [SP500] ===\n"
            "Strategy Weights:\n"
            "  regression: 5.0%\n"
            "  darkpool: 3.5%\n"
            "  earnings_tone_drift: 3.5%\n\n"
            "Top Recommendations:\n"
            + "\n".join(f"{i+1}   AAPL   Apple   0.88   12.5%" for i in range(20))
        )
        ens_file.write_text(valid_ens, encoding="utf-8")
        res_v = verify_ensemble(tmp_path)
        assert res_v.valid is True
        assert res_v.file_found is True
        assert "SP500" in res_v.markets_found
        assert res_v.total_recommendations == 20
        assert res_v.strategy_weights.get("regression") == 5.0
        assert res_v.strategy_weights.get("darkpool") == 3.5
        assert res_v.strategy_weights.get("earnings_tone_drift") == 3.5


# =========================================================================
# 5. GitHub Pages HTML Adversarial Stress
# =========================================================================

def test_verify_gh_pages_adversarial():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1. Missing index.html
        res = verify_gh_pages(tmp_path)
        assert res.valid is False
        assert res.file_found is False

        # 2. Empty index.html
        html_file = tmp_path / "index.html"
        html_file.write_text("", encoding="utf-8")
        assert verify_gh_pages(tmp_path).valid is False

        # 3. Only 1 market (requires >= 2)
        html_file.write_text("<html><body>SP500 only</body></html>", encoding="utf-8")
        assert verify_gh_pages(tmp_path).valid is False

        # 4. 2 markets but missing panels
        html_file.write_text("<html><body>SP500 NASDAQ</body></html>", encoding="utf-8")
        res4 = verify_gh_pages(tmp_path)
        assert res4.valid is False

        # 5. Panels with only <th> headers (0 data rows)
        html_chunks = ["<html><body>SP500 NASDAQ KOSPI"]
        for p_id in STRATEGY_PANEL_ALIASES:
            html_chunks.append(f'<div id="panel-{p_id}"><table><tr><th>H1</th><th>H2</th></tr></table></div>')
        html_chunks.append("</body></html>")
        html_file.write_text("".join(html_chunks), encoding="utf-8")
        res5 = verify_gh_pages(tmp_path)
        assert res5.valid is False

        # 6. Fully populated with >= 5 data rows per panel
        html_chunks = ["<html><body>SP500 NASDAQ KOSPI"]
        for p_id in STRATEGY_PANEL_ALIASES:
            rows = "".join(f"<tr><td>Sym{i}</td><td>Score</td></tr>" for i in range(8))
            html_chunks.append(f'<div id="panel-{p_id}"><table><thead><tr><th>H1</th></tr></thead><tbody>{rows}</tbody></table></div>')
        html_chunks.append("</body></html>")
        html_file.write_text("".join(html_chunks), encoding="utf-8")
        res6 = verify_gh_pages(tmp_path)
        assert res6.valid is True
        assert len(res6.strategy_panels_valid) == 32
        assert all(res6.strategy_panels_valid.values())


# =========================================================================
# 6. CLI Execution & Strict Mode Subprocess Stress
# =========================================================================

def test_cli_strict_mode_exit_code_on_failure():
    with tempfile.TemporaryDirectory() as empty_dir:
        cmd = [
            sys.executable,
            "trading_system/scripts/verify_gha_artifacts.py",
            "--result-dir", empty_dir,
            "--gh-pages-dir", empty_dir,
            "--strict"
        ]
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert proc.returncode == 1


def test_cli_json_mode_output():
    with tempfile.TemporaryDirectory() as empty_dir:
        cmd = [
            sys.executable,
            "trading_system/scripts/verify_gha_artifacts.py",
            "--result-dir", empty_dir,
            "--gh-pages-dir", empty_dir,
            "--json"
        ]
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        assert "markets" in data
        assert "ensemble" in data
        assert "gh_pages" in data
        assert data["overall_passed"] is False
