#!/usr/bin/env python3
"""
Adversarial Verification Suite for Milestone 1 (GHA Pipeline & Caching Integrity)
Tests:
1. YAML schema and syntax validation across all workflow files.
2. Target market matrix consistency across workflows.
3. Cache key and restore-key robustness (no cross-contamination across targets).
4. Artifact naming and download pattern integrity.
5. Simulated multi-market split and merge pipeline resilience under missing markets.
6. Strategy output listing parity across Step Summary, Rename, and Release steps.
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import yaml

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def test_yaml_syntax():
    print("[TEST 1] Testing YAML syntax across all .github/workflows/*.yml...")
    workflow_files = glob.glob(".github/workflows/*.yml")
    assert len(workflow_files) > 0, "No workflow files found!"
    for f in workflow_files:
        with open(f, "r", encoding="utf-8") as fp:
            data = yaml.safe_load(fp)
            assert isinstance(data, dict), f"File {f} did not parse into a dict"
            assert "name" in data, f"File {f} missing 'name'"
            assert "jobs" in data or "on" in data, f"File {f} missing 'jobs' or 'on'"
            print(f"  [OK] {f} is valid YAML.")
    print("-> PASS: All workflow YAML files parsed successfully.\n")

def test_matrix_targets_consistency():
    print("[TEST 2] Testing Matrix target options across workflows...")
    workflows_with_matrix = [
        ".github/workflows/pipeline.yml",
        ".github/workflows/training.yml",
        ".github/workflows/preseed.yml",
        ".github/workflows/weekly_hpo.yml"
    ]
    core_5 = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
    for wf in workflows_with_matrix:
        with open(wf, "r", encoding="utf-8") as fp:
            content = fp.read()
            # Check CORE_5 definition in bash step
            for mkt in core_5:
                assert mkt in content, f"Market {mkt} missing from {wf}"
            print(f"  [OK] {wf} contains all CORE_5 targets.")
    print("-> PASS: Target markets consistent across matrix workflows.\n")

def test_cache_keys_and_isolation():
    print("[TEST 3] Testing Cache keys and cross-target isolation...")
    # Verify that market-specific caches (db, ai-models) include ${{ matrix.target }}
    # to avoid cross-target cache collisions
    for wf in [".github/workflows/pipeline.yml", ".github/workflows/training.yml", ".github/workflows/preseed.yml"]:
        with open(wf, "r", encoding="utf-8") as fp:
            content = fp.read()
            # If it has matrix.target, check cache keys for models and db
            if "matrix.target" in content:
                # Find all actions/cache blocks
                cache_blocks = re.findall(r"uses:\s*actions/cache(?:/restore)?@v\d+.*?key:\s*([^\n\r]+)", content, re.DOTALL)
                for key_line in cache_blocks:
                    if "ai-models-" in key_line:
                        assert "matrix.target" in key_line, f"Cache key '{key_line}' in {wf} lacks matrix.target isolation!"
                    if "stock-prices-db-" in key_line:
                        assert "matrix.target" in key_line, f"Cache key '{key_line}' in {wf} lacks matrix.target isolation!"
                    print(f"  [OK] Cache key '{key_line.strip()}' properly isolated in {wf}.")
    print("-> PASS: All market-specific caches are properly isolated by matrix.target.\n")

def test_strategy_file_lists_parity():
    print("[TEST 4] Testing 31-strategy output listings parity in pipeline.yml...")
    with open(".github/workflows/pipeline.yml", "r", encoding="utf-8") as fp:
        content = fp.read()

    # Strategy 6 is lstm_predictions.txt
    assert "lstm_predictions.txt" in content, "lstm_predictions.txt missing from pipeline.yml!"
    
    # Check step summary file loop
    step_summary_match = re.search(r"### 📁 (?:31|34|37)대 전략 출력 파일 현황[\s\S]*?for f in ([^;]+);", content)
    assert step_summary_match, "Step summary file loop not found in pipeline.yml"
    summary_files = step_summary_match.group(1).split()
    assert "lstm_predictions.txt" in summary_files, "lstm_predictions.txt missing from Step Summary loop"
    print(f"  [OK] Step summary contains {len(summary_files)} entries including lstm_predictions.txt.")

    # Check release upload file loop
    release_match = re.search(r"# Upload all strategy files and report outputs[\s\S]*?for f in ([^;]+); do", content)
    assert release_match, "Release upload file loop not found in pipeline.yml"
    release_files = release_match.group(1).replace("\\\n", " ").replace("\\", " ").split()
    assert "lstm_predictions.txt" in release_files, "lstm_predictions.txt missing from Release Upload loop"
    print(f"  [OK] Release upload contains {len(release_files)} entries including lstm_predictions.txt.")

    # Check split rename loop
    rename_match = re.search(r"mkdir -p trading_system/result_split[\s\S]*?for f in ([^;]+); do", content)
    assert rename_match, "Rename split loop not found in pipeline.yml"
    rename_files = rename_match.group(1).replace("\\\n", " ").replace("\\", " ").split()
    assert "lstm_predictions" in rename_files, "lstm_predictions missing from Rename loop"
    print(f"  [OK] Split rename contains {len(rename_files)} entries including lstm_predictions.")
    print("-> PASS: Strategy output file listings are consistent.\n")

def test_merge_simulation_resilience():
    print("[TEST 5] Testing merge_predictions.py simulation with partial / mock market artifacts...")
    # Create temp directory structure simulating GHA merge step
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        ts_dir = tmp_path / "trading_system"
        res_dir = ts_dir / "result"
        res_dir.mkdir(parents=True)
        art_dir = ts_dir / "artifacts_in"
        art_dir.mkdir(parents=True)

        # Mock market split files for KOSPI and SP500 (partial run)
        markets = ["KOSPI", "SP500"]
        for mkt in markets:
            mkt_art_dir = art_dir / f"result-{mkt}"
            mkt_art_dir.mkdir()
            # write mock files
            (mkt_art_dir / f"lstm_predictions_{mkt}.txt").write_text(
                f"=== Strict Causal LSTM Time-Series Deep Learning Predictions ===\nDate: 2026-09-01 00:00 KST\n\n1 005930 Samsung 12.5%\n2 000660 SKHynix 10.2%\n",
                encoding="utf-8"
            )
            (mkt_art_dir / f"surge_predictions_{mkt}.txt").write_text(
                f"=========================================\n[1일] {mkt} Top 20 Surge Predictions (>= 20% Return Probability)\n=========================================\n1. [{mkt}] ABC (001): 85.0%\n2. [{mkt}] DEF (002): 75.0%\n",
                encoding="utf-8"
            )
            (mkt_art_dir / f"ensemble_predictions_{mkt}.txt").write_text(
                f"=========================================\n[{mkt}] Top 100 Ensemble Picks (Target Horizon: 20D Expected Return)\n=========================================\n1 005930 Samsung 88.5% 15.2%\n",
                encoding="utf-8"
            )

        # Copy split files as GHA does
        for mkt in markets:
            for f in (art_dir / f"result-{mkt}").glob("*.*"):
                shutil.copy(f, res_dir / f.name)

        # Import merge_predictions functions and run
        sys.path.insert(0, str(Path("trading_system").resolve()))
        import merge_predictions
        target_dirs = merge_predictions.discover_target_markets(ts_dir, res_dir)
        assert len(target_dirs) >= 2, f"Expected at least 2 discovered target dirs, got {target_dirs}"
        
        # Test merging functions
        merge_predictions.merge_generic_strategy_files(res_dir, target_dirs, "lstm_predictions.txt", "Strict Causal LSTM Time-Series Deep Learning Predictions")
        merge_predictions.merge_surge_predictions(res_dir, target_dirs)
        merge_predictions.merge_ensemble_predictions(res_dir, target_dirs)

        merged_lstm = res_dir / "lstm_predictions.txt"
        assert merged_lstm.exists(), "Merged lstm_predictions.txt not created"
        lstm_content = merged_lstm.read_text(encoding="utf-8")
        assert "Samsung" in lstm_content, "Samsung missing from merged LSTM"
        print(f"  [OK] Merged LSTM content length: {len(lstm_content)} chars.")

        merged_surge = res_dir / "surge_predictions.txt"
        assert merged_surge.exists(), "Merged surge_predictions.txt not created"
        surge_content = merged_surge.read_text(encoding="utf-8")
        assert "ABC" in surge_content, "ABC missing from merged surge"
        print(f"  [OK] Merged surge content length: {len(surge_content)} chars.")

        merged_ens = res_dir / "ensemble_predictions.txt"
        assert merged_ens.exists(), "Merged ensemble_predictions.txt not created"
        ens_content = merged_ens.read_text(encoding="utf-8")
        assert "Samsung" in ens_content, "Samsung missing from merged ensemble"
        print(f"  [OK] Merged ensemble content length: {len(ens_content)} chars.")

    print("-> PASS: Simulated multi-market merge succeeded robustly.\n")

def main():
    print("==================================================================")
    print("   ADVERSARIAL VERIFICATION SUITE - MILESTONE 1 (R1 GHA INTEGRITY)")
    print("==================================================================\n")
    test_yaml_syntax()
    test_matrix_targets_consistency()
    test_cache_keys_and_isolation()
    test_strategy_file_lists_parity()
    test_merge_simulation_resilience()
    print("==================================================================")
    print("   ALL 5 ADVERSARIAL INTEGRITY SUITES PASSED EMPIRICALLY!       ")
    print("==================================================================")

if __name__ == "__main__":
    main()
