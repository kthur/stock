#!/usr/bin/env python3
"""
scripts/verify_benchmark_invariants_adversarial.py — Empirical Invariant & Mutation Verification

Verifies:
1. Strict invariant: synthetic_rows == 0 (strictly native Python int, not bool, not float) across:
   - benchmarks/30year/status.json
   - trading_system/result/status.json
   - benchmarks/30year/stock_universe_summary.json
   - trading_system/result/stock_universe_summary.json
2. Adversarial mutation rejection:
   - Mutating synthetic_rows to True, False, 0.0, 1.0, 1, -1, "0", None immediately triggers AssertionError.
3. Cryptographic parity:
   - SHA-256 match between root benchmarks and mirrored trading_system/result benchmarks.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ARTIFACTS = [
    PROJECT_ROOT / "benchmarks" / "30year" / "status.json",
    PROJECT_ROOT / "trading_system" / "result" / "status.json",
    PROJECT_ROOT / "benchmarks" / "30year" / "stock_universe_summary.json",
    PROJECT_ROOT / "trading_system" / "result" / "stock_universe_summary.json",
]


def strict_assert_synthetic_rows(val: Any, ctx: str = "") -> None:
    """Strictly assert that synthetic_rows == 0 and is native int 0 (not bool, not float)."""
    assert val == 0, f"synthetic_rows is {val} != 0 [{ctx}]"
    assert type(val) is int, f"synthetic_rows type is {type(val).__name__}, not int [{ctx}]"
    assert not isinstance(val, bool), f"synthetic_rows is bool [{ctx}]"


def find_all_synthetic_rows(d: Any, path: str = "") -> List[Tuple[str, Any]]:
    """Find all instances of synthetic_rows in nested dict/list."""
    res: List[Tuple[str, Any]] = []
    if isinstance(d, dict):
        for k, v in d.items():
            curr = f"{path}.{k}" if path else k
            if k == "synthetic_rows":
                res.append((curr, v))
            res.extend(find_all_synthetic_rows(v, curr))
    elif isinstance(d, list):
        for i, elem in enumerate(d):
            res.extend(find_all_synthetic_rows(elem, f"{path}[{i}]"))
    return res


def main() -> int:
    print("=" * 80)
    print("  EMPIRICAL ADVERSARIAL BENCHMARK INVARIANT VERIFICATION")
    print("=" * 80)

    # 1. Existence and cryptographic parity
    print("\n[Phase 1: Artifact Existence & Cryptographic Parity]")
    for p in ARTIFACTS:
        if not p.exists():
            print(f"  [FAIL] Artifact missing: {p}")
            return 1
        print(f"  [PASS] Found {p.relative_to(PROJECT_ROOT)} ({p.stat().st_size:,} bytes)")

    # Status parity
    h_stat_root = hashlib.sha256(ARTIFACTS[0].read_bytes()).hexdigest()
    h_stat_ts = hashlib.sha256(ARTIFACTS[1].read_bytes()).hexdigest()
    if h_stat_root != h_stat_ts:
        print(f"  [FAIL] status.json SHA-256 mismatch: {h_stat_root} != {h_stat_ts}")
        return 1
    print(f"  [PASS] status.json 100% SHA-256 match ({h_stat_root[:16]}...)")

    # Summary parity
    h_sum_root = hashlib.sha256(ARTIFACTS[2].read_bytes()).hexdigest()
    h_sum_ts = hashlib.sha256(ARTIFACTS[3].read_bytes()).hexdigest()
    if h_sum_root != h_sum_ts:
        print(f"  [FAIL] stock_universe_summary.json SHA-256 mismatch: {h_sum_root} != {h_sum_ts}")
        return 1
    print(f"  [PASS] stock_universe_summary.json 100% SHA-256 match ({h_sum_root[:16]}...)")

    # 2. Strict Invariant Check
    print("\n[Phase 2: Strict synthetic_rows == 0 Native Int Invariant]")
    total_checked = 0
    for p in ARTIFACTS:
        data = json.loads(p.read_text(encoding="utf-8"))
        occurrences = find_all_synthetic_rows(data)
        if not occurrences:
            print(f"  [FAIL] No synthetic_rows found in {p.name}")
            return 1
        for path_str, val in occurrences:
            strict_assert_synthetic_rows(val, f"{p.name}:{path_str}")
            print(f"  [PASS] {p.relative_to(PROJECT_ROOT)} -> {path_str} = {val} (type={type(val).__name__}, not_bool=True)")
            total_checked += 1

    print(f"  Total occurrences validated: {total_checked}")

    # 3. Adversarial Mutation Challenge
    print("\n[Phase 3: Adversarial Mutation Injection Challenge]")
    mutations = [
        (True, "bool True"),
        (False, "bool False (val==0 in Python!)"),
        (0.0, "float 0.0"),
        (1.0, "float 1.0"),
        (1, "int 1"),
        (-1, "int -1"),
        ("0", "str '0'"),
        (None, "None"),
    ]

    for bad_val, desc in mutations:
        failed = False
        try:
            strict_assert_synthetic_rows(bad_val, f"mutation={desc}")
        except AssertionError as e:
            failed = True
            print(f"  [PASS] Mutation '{desc}' successfully triggered assertion rejection: {e}")
        if not failed:
            print(f"  [CRITICAL BREACH] Mutation '{desc}' unexpectedly passed assertion!")
            return 1

    # In-memory mutation test across all 4 files
    print("\n[Phase 4: In-Memory Artifact Mutation Challenge]")
    for p in ARTIFACTS:
        data = json.loads(p.read_text(encoding="utf-8"))
        for bad_val, desc in mutations:
            d_mut = copy.deepcopy(data)
            if "synthetic_rows" in d_mut:
                d_mut["synthetic_rows"] = bad_val
                target_val = d_mut["synthetic_rows"]
            else:
                d_mut["metadata"]["synthetic_rows"] = bad_val
                target_val = d_mut["metadata"]["synthetic_rows"]

            caught = False
            try:
                strict_assert_synthetic_rows(target_val, f"in-memory mut of {p.name} with {desc}")
            except AssertionError:
                caught = True
            if not caught:
                print(f"  [CRITICAL BREACH] In-memory mutation of {p.name} with {desc} bypassed check!")
                return 1
        print(f"  [PASS] All {len(mutations)} mutations caught for {p.relative_to(PROJECT_ROOT)}")

    print("\n" + "=" * 80)
    print("  >>> ALL INVARIANT & MUTATION CHALLENGES PASSED (Exit Code 0) <<<")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
