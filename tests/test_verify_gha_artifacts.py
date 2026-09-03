import os
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
    print_report,
)


def test_canonical_strategies_count_and_order():
    """Verify that STRATEGIES list has exactly 37 items in canonical order."""
    assert len(STRATEGIES) == 37
    expected_order = [
        "regression", "surge", "lead_lag", "vcp_rule", "vcp_ml", "lstm",
        "stat_arb", "sector_rotation", "rim_valuation", "event_driven", "mq_factor",
        "iv_skew", "order_flow", "short_term_reversal", "arm_factor",
        "card_factor", "latr_factor", "inst_foreign_sector",
        "supply_chain", "sentiment", "factor_neutralized", "vol_target",
        "microstructure", "accruals_quality", "short_squeeze", "valueup_catalyst",
        "trend_efficiency", "gamma_squeeze", "insider_buying", "darkpool", "earnings_tone_drift",
        "cross_asset_spillover", "supply_chain_gnn", "range_expansion_breakout",
        "dual_correction", "index_rebalance", "overnight_gap_reversal"
    ]
    assert STRATEGIES == expected_order


def test_strategy_panel_aliases_coverage():
    """Verify that STRATEGY_PANEL_ALIASES covers ensemble and all 37 strategies."""
    assert "ensemble" in STRATEGY_PANEL_ALIASES
    for strat in STRATEGIES:
        assert strat in STRATEGY_PANEL_ALIASES, f"Strategy {strat} missing from STRATEGY_PANEL_ALIASES"
    assert len(STRATEGY_PANEL_ALIASES) == 38  # 37 strategies + ensemble


def test_check_regression_valid_and_empty():
    valid_content = "=== Regression ===\nDate: 2026-09-01\nSymbol\tExpRet\n" + "\n".join(f"AAPL\t{0.05 + i * 0.01:.4f}" for i in range(15))
    res = check_regression(valid_content, "SP500")
    assert res.valid is True
    assert res.count == 15
    assert res.non_zero is True

    empty_res = check_regression("데이터 없음", "SP500")
    assert empty_res.valid is False


def test_check_surge_valid():
    valid_content = "\n".join(f"[SP500] AAPL (Apple): {15.5 + i:.1f}%" for i in range(12))
    res = check_surge(valid_content, "SP500")
    assert res.valid is True
    assert res.count == 12


def test_check_vcp_rule_and_ml():
    vcp_content = "\n".join(f"[{m}] SYMB{i}: Pattern confirmed" for m in ["SP500"] for i in range(12))
    res_rule = check_vcp(vcp_content, "SP500")
    assert res_rule.valid is True
    assert res_rule.strategy == "vcp_rule"

    vcp_ml_content = "\n".join(f"[SP500] SYMB{i} (Company): {25.0 + i:.1f}%" for i in range(10))
    res_ml = check_vcp_ml(vcp_ml_content, "SP500")
    assert res_ml.valid is True


def test_check_generic_strategy():
    content = "=== Strategy Output ===\nDate: 2026-09-01\nRank\tSymbol\tScore\n" + "\n".join(f"{i+1}\tSYM{i}\t{0.85 - i * 0.02:.4f}" for i in range(15))
    res = check_generic_strategy(content, "SP500", "darkpool")
    assert res.valid is True
    assert res.count == 15
    assert res.strategy == "darkpool"


def test_verify_market_strategies_with_mock_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Create mock files for all 31 strategies
        for strat in STRATEGIES:
            if strat == "regression":
                fname = "pipeline_result_SP500.txt"
                content = "Date: 2026-09-01\n" + "\n".join(f"SYM{i}\t0.123" for i in range(12))
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
        assert len(m_res.strategies) == 37
        assert m_res.all_strategies_valid is True


def test_verify_gh_pages_mock():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Generate minimal index.html containing all 37 panels
        html_chunks = ["<html><body>SP500 NASDAQ RUSSELL2000 KOSPI KOSDAQ"]
        for p_id in STRATEGY_PANEL_ALIASES:
            rows = "".join(f"<tr><td>Item {i}</td><td>Value</td></tr>" for i in range(10))
            html_chunks.append(f'<div id="panel-{p_id}"><table><thead><tr><th>H1</th><th>H2</th></tr></thead><tbody>{rows}</tbody></table></div>')
        html_chunks.append("</body></html>")
        (tmp_path / "index.html").write_text("".join(html_chunks), encoding="utf-8")

        res = verify_gh_pages(tmp_path)
        assert res.valid is True
        assert len(res.strategy_panels_valid) == 38
