"""
Forensic Audit Verification Script
Auditor 1: Empirical verification of RIM valuation, coverage analyzer, adapters, report generator, and html output.
"""
import os
import sys
import re
import numpy as np
import pandas as pd

# Add paths
REPO_ROOT = r"d:\Finance\code\stock"
TRADING_SYSTEM_DIR = os.path.join(REPO_ROOT, "trading_system")

for p in [TRADING_SYSTEM_DIR, REPO_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

from src.core.rim_valuation import RIMValuationEngine, ABSOLUTE_ROE_CAP, EXTREME_ROE_THRESHOLD
from src.analysis.coverage_analyzer import StrategyCoverageAnalyzer
from src.core.strategy_registry import StrategyRegistry
from src.ai.ml_strategy_adapters import VCPRuleStrategyAdapter
from generate_report import (
    format_metric_cell,
    parse_rim,
    parse_strategy_coverage_report,
    build_strategy_health_monitor_html,
    build_tab_status_banner,
    main as generate_report_main
)

def test_1_rim_forensics():
    print("=== Test 1: RIM Valuation Forensic Integrity ===")
    engine = RIMValuationEngine(default_required_return=0.08)

    test_df = pd.DataFrame([
        # 1. Normal stock
        {'symbol': '005930', 'market': 'KOSPI', 'Close': 70000.0, 'bps': 50000.0, 'roe': 0.12, 'operating_income': 100, 'net_income': 100},
        # 2. Missing BPS (NaN)
        {'symbol': '000001', 'market': 'KOSPI', 'Close': 5000.0, 'bps': np.nan, 'roe': 0.15, 'operating_income': 10, 'net_income': 10},
        # 3. Capital Impairment (Negative BPS with positive net income)
        {'symbol': '000003', 'market': 'KOSPI', 'Close': 1000.0, 'bps': -500.0, 'roe': 0.20, 'operating_income': 10, 'net_income': 10},
        # 4. Operating Loss (Positive BPS)
        {'symbol': '000004', 'market': 'KOSPI', 'Close': 20000.0, 'bps': 15000.0, 'roe': -0.05, 'operating_income': -10, 'net_income': -10},
        # 5. Preferred Share
        {'symbol': '005935', 'market': 'KOSPI', 'Close': 60000.0, 'bps': 50000.0, 'roe': 0.12, 'operating_income': 100, 'net_income': 100},
        # 6. Low Earnings Quality (Operating loss but positive net income)
        {'symbol': '000060', 'market': 'KOSPI', 'Close': 30000.0, 'bps': 20000.0, 'roe': 0.25, 'operating_income': -5, 'net_income': 50},
    ])

    res = engine.compute_rim_scores(test_df).set_index('symbol')
    print(res[['Close', 'bps', 'roe', 'rim_score', 'intrinsic_value', 'discount_ratio', 'rim_filter_reason']])

    # Check 1: Normal stock must have valid numeric rim_score, intrinsic_value, discount_ratio
    assert pd.notna(res.loc['005930', 'rim_score']), "005930 rim_score is NaN!"
    assert pd.notna(res.loc['005930', 'intrinsic_value']), "005930 intrinsic_value is NaN!"
    assert pd.notna(res.loc['005930', 'discount_ratio']), "005930 discount_ratio is NaN!"
    assert res.loc['005930', 'rim_filter_reason'] == ""

    # Check 2: Missing BPS must be MISSING_FUNDAMENTALS and NaN score (NOT synthetic 0.08 / 1.0)
    assert res.loc['000001', 'rim_filter_reason'] == 'MISSING_FUNDAMENTALS', f"Wrong reason: {res.loc['000001', 'rim_filter_reason']}"
    assert pd.isna(res.loc['000001', 'rim_score']), "Missing BPS got non-NaN rim_score!"
    assert pd.isna(res.loc['000001', 'intrinsic_value']), "Missing BPS got non-NaN intrinsic_value!"
    assert pd.isna(res.loc['000001', 'discount_ratio']), "Missing BPS got non-NaN discount_ratio!"

    # Check 3: Capital Impairment (Negative BPS)
    assert res.loc['000003', 'rim_filter_reason'] == 'CAPITAL_IMPAIRMENT', f"Wrong reason: {res.loc['000003', 'rim_filter_reason']}"
    assert pd.isna(res.loc['000003', 'rim_score'])
    assert pd.isna(res.loc['000003', 'intrinsic_value'])

    # Check 4: Operating Loss
    assert res.loc['000004', 'rim_filter_reason'] == 'OPERATING_LOSS'
    assert pd.isna(res.loc['000004', 'rim_score'])

    # Check 5: Preferred Share
    assert res.loc['005935', 'rim_filter_reason'] == 'PREFERRED_SHARE'
    assert pd.isna(res.loc['005935', 'rim_score'])

    # Check 6: Low Earnings Quality
    assert res.loc['000060', 'rim_filter_reason'] == 'LOW_EARNINGS_QUALITY'
    assert pd.isna(res.loc['000060', 'rim_score'])

    print("-> Test 1 Passed: Genuine NaN invalidation & explicit filter tagging verified.")

def test_2_coverage_analyzer_forensics():
    print("=== Test 2: Coverage Analyzer Suffix & Missingness Forensics ===")
    analyzer = StrategyCoverageAnalyzer()

    # Fundamental dict with 6-digit keys
    fund_dict = {
        '005930': pd.DataFrame({'bps': [50000.0], 'roe': [0.12]}),
        '000660': pd.DataFrame({'bps': [80000.0], 'roe': [0.10]}),
        'AAPL': pd.DataFrame({'book_value': [50000.0], 'roe': [0.25]}),
    }

    # Query with suffixed symbols: _has_symbol_fundamental_data(features_df, sym)
    assert analyzer._has_symbol_fundamental_data(fund_dict, '005930.KS') == True
    assert analyzer._has_symbol_fundamental_data(fund_dict, '000660.KQ') == True
    assert analyzer._has_symbol_fundamental_data(fund_dict, 'AAPL.US') == True
    assert analyzer._has_symbol_fundamental_data(fund_dict, '999999.KS') == False

    # DataFrame with symbol column containing 6-digit codes
    fund_df = pd.DataFrame([
        {'symbol': '005930', 'bps': 50000.0, 'roe': 0.12},
        {'symbol': 'AAPL', 'book_value': 50000.0, 'roe': 0.25},
    ])
    assert analyzer._has_symbol_fundamental_data(fund_df, '005930.KS') == True
    assert analyzer._has_symbol_fundamental_data(fund_df, '005930') == True
    assert analyzer._has_symbol_fundamental_data(fund_df, 'AAPL.US') == True
    assert analyzer._has_symbol_fundamental_data(fund_df, 'NVDA.US') == False

    print("-> Test 2 Passed: Symbol suffix normalization verified.")

def test_3_adapter_consistency():
    print("=== Test 3: Adapter Meta Score Column Consistency ===")
    reg = StrategyRegistry()
    reg.auto_discover()
    entry = reg.get("vcp_rule")
    assert entry is not None, "vcp_rule strategy not registered!"
    engine_cls, vcp_meta = entry
    assert vcp_meta.score_column == "vcp_rule_score", f"Expected vcp_rule_score, got {vcp_meta.score_column}"
    adapter = VCPRuleStrategyAdapter()
    df_empty = adapter.compute_scores(None)
    assert "vcp_rule_score" in df_empty.columns
    print("-> Test 3 Passed: VCP adapter score_column aligned with EnsembleScoringEngine.")

def test_4_html_generation_and_nan_scan():
    print("=== Test 4: End-to-End HTML Dashboard Generation & Zero-NaN Scan ===")
    result_dir = os.path.join(REPO_ROOT, "trading_system", "result")
    out_html = os.path.join(REPO_ROOT, "gh-pages", "index.html")

    # Run generator
    generate_report_main(["--result-dir", result_dir, "--out", out_html])
    assert os.path.exists(out_html), "index.html was not generated!"

    with open(out_html, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Verify Health Monitor presence
    assert "Strategy Data Health Monitor" in html_content
    assert "health-monitor-section" in html_content
    assert "switchTabById(" in html_content

    # Regex scan for forbidden raw nan in table cells
    # Check <td>nan</td>, <td>NaN</td>, <td>None</td>, <td>undefined</td>, <td>nan%</td>
    bad_patterns = [
        r"<td[^>]*>\s*nan\s*</td>",
        r"<td[^>]*>\s*NaN\s*</td>",
        r"<td[^>]*>\s*None\s*</td>",
        r"<td[^>]*>\s*undefined\s*</td>",
        r"<td[^>]*>\s*nan%\s*</td>",
        r"<td[^>]*>\s*NaN%\s*</td>",
        r"<td[^>]*>\s*null\s*</td>",
    ]

    for pat in bad_patterns:
        matches = list(re.finditer(pat, html_content, re.IGNORECASE))
        if matches:
            for m in matches[:5]:
                print(f"FAILED MATCH: {m.group(0)}")
            raise AssertionError(f"Found forbidden pattern '{pat}' in generated HTML ({len(matches)} occurrences)!")

    print("-> Test 4 Passed: 100% Zero-NaN verified in generated HTML.")

if __name__ == "__main__":
    test_1_rim_forensics()
    test_2_coverage_analyzer_forensics()
    test_3_adapter_consistency()
    test_4_html_generation_and_nan_scan()
    print("\nALL 4 FORENSIC AUDIT EMPIRICAL CHECKS PASSED.")
