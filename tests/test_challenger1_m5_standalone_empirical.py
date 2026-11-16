"""
tests/test_challenger1_m5_standalone_empirical.py
Empirical Challenger 1 Stress Harness for Milestone 5 Dual-Tree Parity.

Verifies:
1. Single-byte mutation detection (offset 0, chunk boundary, EOF, src vs target).
2. Missing file detection in either tree (asymmetric missingness).
3. Strict threshold boundary check (min_files=378 PASS vs min_files=379 FAIL).
4. Zero-byte file handling (identical empty vs 0-byte vs 1-byte divergence).
5. Case-sensitivity traps (casing divergence between trees).
6. Target modified production modules SHA-256 identity.
7. Unconditional CLI exit code 1 guarantee across all failure modes.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from scripts.verify_dual_tree_parity import (
    DEFAULT_MIN_FILES,
    compare_trees,
    compute_sha256,
    find_repo_root,
    scan_tree,
)

REPO_ROOT = find_repo_root()
VERIFIER_SCRIPT = REPO_ROOT / "scripts" / "verify_dual_tree_parity.py"


@pytest.fixture
def sandbox_pair():
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        src = base / "src"
        tgt = base / "trading_system" / "src"
        src.mkdir(parents=True)
        tgt.mkdir(parents=True)

        for i in range(10):
            p_src = src / f"pkg_{i // 3}" / f"module_{i}.py"
            p_tgt = tgt / f"pkg_{i // 3}" / f"module_{i}.py"
            p_src.parent.mkdir(parents=True, exist_ok=True)
            p_tgt.parent.mkdir(parents=True, exist_ok=True)
            content = f"# Module {i}\ndef fn_{i}(): return {i * 42}\n".encode("utf-8") * 20
            p_src.write_bytes(content)
            p_tgt.write_bytes(content)

        yield src, tgt


def test_production_milestone_target_modules_exact_sha256():
    """Verify SHA-256 match for all 5 modules modified in M1-M4."""
    modules = [
        "core/multi_factor_neutralizer.py",
        "ai/factor_orthogonalizer.py",
        "ai/ensemble_scorer.py",
        "risk/unified_portfolio_allocator.py",
        "execution/oms_engine.py",
    ]
    for rel in modules:
        f_src = REPO_ROOT / "src" / rel
        f_tgt = REPO_ROOT / "trading_system" / "src" / rel
        assert f_src.exists(), f"Source file does not exist: {f_src}"
        assert f_tgt.exists(), f"Target file does not exist: {f_tgt}"
        h_src = hashlib.sha256(f_src.read_bytes()).hexdigest()
        h_tgt = hashlib.sha256(f_tgt.read_bytes()).hexdigest()
        assert h_src == h_tgt, f"SHA-256 mismatch for {rel}: {h_src} != {h_tgt}"


def test_production_dual_tree_exact_count_and_parity():
    """Verify production trees match exactly across all 378 python files."""
    report = compare_trees(
        REPO_ROOT / "src",
        REPO_ROOT / "trading_system" / "src",
        python_only=True,
        strict=True,
        min_files=378,
    )
    assert report.passed is True
    assert report.identical_count == 378
    assert report.mismatched_count == 0
    assert report.only_in_src_count == 0
    assert report.only_in_target_count == 0


def test_strict_threshold_boundary_n378_pass_n379_fail():
    """Verify strict threshold boundary: N=378 passes, N=379 fails."""
    src = REPO_ROOT / "src"
    tgt = REPO_ROOT / "trading_system" / "src"

    rep_378 = compare_trees(src, tgt, python_only=True, strict=True, min_files=378)
    assert rep_378.passed is True

    rep_379 = compare_trees(src, tgt, python_only=True, strict=True, min_files=379)
    assert rep_379.passed is False
    assert any("Strict threshold violation" in r for r in rep_379.failure_reasons)

    # CLI check
    res_378 = subprocess.run(
        [sys.executable, str(VERIFIER_SCRIPT), "--check", "--strict", "--min-files", "378"],
        capture_output=True,
        text=True,
    )
    assert res_378.returncode == 0

    res_379 = subprocess.run(
        [sys.executable, str(VERIFIER_SCRIPT), "--check", "--strict", "--min-files", "379"],
        capture_output=True,
        text=True,
    )
    assert res_379.returncode == 1
    assert "Strict threshold violation: identical file count 378 < required 379" in res_379.stdout


def test_single_byte_mutation_at_offsets(sandbox_pair):
    """Verify single-byte mutation detection at offset 0, chunk boundary, and EOF."""
    src, tgt = sandbox_pair

    # Create a 70KB file spanning across the 64KB chunk boundary
    large_payload = bytearray(b"A" * (70 * 1024))
    (src / "large.py").write_bytes(bytes(large_payload))
    (tgt / "large.py").write_bytes(bytes(large_payload))

    # Baseline check
    assert compare_trees(src, tgt, python_only=True).passed is True

    # 1. Mutate offset 0
    corrupt_0 = bytearray(large_payload)
    corrupt_0[0] ^= 0x01
    (tgt / "large.py").write_bytes(bytes(corrupt_0))
    rep = compare_trees(src, tgt, python_only=True)
    assert rep.passed is False
    assert rep.mismatched_count == 1

    # 2. Mutate exactly at 64KB boundary (offset 65536)
    corrupt_chunk = bytearray(large_payload)
    corrupt_chunk[65536] ^= 0x55
    (tgt / "large.py").write_bytes(bytes(corrupt_chunk))
    rep = compare_trees(src, tgt, python_only=True)
    assert rep.passed is False
    assert rep.mismatched_count == 1

    # 3. Mutate at EOF
    corrupt_eof = bytearray(large_payload)
    corrupt_eof[-1] ^= 0xFF
    (tgt / "large.py").write_bytes(bytes(corrupt_eof))
    rep = compare_trees(src, tgt, python_only=True)
    assert rep.passed is False
    assert rep.mismatched_count == 1


def test_missing_file_in_either_tree(sandbox_pair):
    """Verify detection of missing files in src or target."""
    src, tgt = sandbox_pair

    # Missing in target: delete a file from target
    target_file = tgt / "pkg_0" / "module_0.py"
    target_file.unlink()

    rep = compare_trees(src, tgt, python_only=True)
    assert rep.passed is False
    assert rep.only_in_src_count == 1
    assert "pkg_0/module_0.py" in rep.only_in_src

    # Restore and create missing in src: add file only to target
    target_file.write_bytes(b"# restored\n")
    unilateral_tgt = tgt / "pkg_new" / "unilateral.py"
    unilateral_tgt.parent.mkdir(parents=True, exist_ok=True)
    unilateral_tgt.write_bytes(b"# target only\n")

    rep2 = compare_trees(src, tgt, python_only=True)
    assert rep2.passed is False
    assert rep2.only_in_target_count == 1
    assert "pkg_new/unilateral.py" in rep2.only_in_target


def test_zero_byte_file_handling(sandbox_pair):
    """Verify zero-byte file identity, mismatch, and missingness."""
    src, tgt = sandbox_pair

    # Identical 0-byte files
    (src / "empty.py").write_bytes(b"")
    (tgt / "empty.py").write_bytes(b"")

    rep = compare_trees(src, tgt, python_only=True)
    assert rep.passed is True
    assert rep.identical_count == 11

    # Divergence: 0-byte vs 1-byte whitespace
    (tgt / "empty.py").write_bytes(b" ")
    rep_div = compare_trees(src, tgt, python_only=True)
    assert rep_div.passed is False
    assert rep_div.mismatched_count == 1
    assert rep_div.mismatches[0].src_size == 0
    assert rep_div.mismatches[0].target_size == 1


def test_case_sensitivity_traps(sandbox_pair):
    """Verify case sensitivity traps."""
    src, tgt = sandbox_pair

    (src / "Service_Alpha.py").write_text("# Case A\n", encoding="utf-8")
    (tgt / "service_alpha.py").write_text("# Case A\n", encoding="utf-8")

    rep = compare_trees(src, tgt, python_only=True)
    assert rep.passed is False
    assert "Service_Alpha.py" in rep.only_in_src
    assert "service_alpha.py" in rep.only_in_target


def test_cli_unconditional_exit_code_1_on_failure(sandbox_pair):
    """Verify CLI always exits with code 1 upon any parity mismatch."""
    src, tgt = sandbox_pair

    # Corrupt one file
    (tgt / "pkg_0" / "module_0.py").write_bytes(b"# corrupted\n")

    res = subprocess.run(
        [
            sys.executable,
            str(VERIFIER_SCRIPT),
            "--check",
            "--src",
            str(src),
            "--target",
            str(tgt),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1
    assert "Status:                     FAIL" in res.stdout
    assert "Content Mismatches:         1" in res.stdout
