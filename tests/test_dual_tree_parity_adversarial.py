"""
tests/test_dual_tree_parity_adversarial.py
Adversarial Stress Test Suite for Dual-Tree Cryptographic Parity Guard & Synchronizer.

Written by Challenger 1 (critic, specialist) to empirically stress-test
scripts/verify_dual_tree_parity.py under adversarial scenarios in isolated sandboxes:
  1. Corrupted single byte mutations in deep files (first, middle, chunk boundary, EOF).
  2. Missing file in target directory, missing file in source directory, and asymmetric matrices.
  3. Extra unmonitored files and __pycache__ noise (deep caches, temp files, OS metadata, hidden files).
  4. Huge simulated files (10MB+, boundary chunk mutations) and zero-byte files.
  5. Case sensitivity traps (e.g. Test.py vs test.py) and Windows NTFS casing behavior.
  6. Unconditional exit code 1 guarantee across all parity violation categories.
  7. Full repair verification via --sync across directions (newest, src-to-ts, ts-to-src, dry-run).
  8. Non-UTF8 binary corrupted python files and resilient diff formatting.
  9. CLI patch output and JSON report generation under adversarial conditions.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Generator, Tuple

import pytest

from scripts.verify_dual_tree_parity import (
    DEFAULT_MIN_FILES,
    FileHashMeta,
    MismatchDetail,
    ParityReport,
    compare_trees,
    compute_sha256,
    find_repo_root,
    scan_tree,
    sync_trees,
)

REPO_ROOT = find_repo_root()
VERIFIER_SCRIPT = REPO_ROOT / "scripts" / "verify_dual_tree_parity.py"


@pytest.fixture
def sandbox_trees(tmp_path: Path) -> Generator[Tuple[Path, Path], None, None]:
    """Creates isolated src and target directory trees with baseline matching files."""
    src = tmp_path / "sandbox_src"
    tgt = tmp_path / "sandbox_tgt"
    src.mkdir(parents=True, exist_ok=True)
    tgt.mkdir(parents=True, exist_ok=True)

    # Populate baseline identical structure
    for i in range(5):
        p1 = src / f"module_{i}.py"
        p2 = tgt / f"module_{i}.py"
        content = f"# module {i}\ndef f{i}():\n    return {i * 10}\n".encode("utf-8")
        p1.write_bytes(content)
        p2.write_bytes(content)

    yield src, tgt


# ==============================================================================
# 1. Deep Nesting & Single-Byte Mutation Stress Tests
# ==============================================================================

def test_adversarial_deep_nested_single_byte_mutations(sandbox_trees: Tuple[Path, Path]):
    """Empirically asserts single-byte mutations in deeply nested paths are detected."""
    src, tgt = sandbox_trees

    # Construct a 12-level deep path
    deep_rel = Path("level1/level2/level3/level4/level5/level6/level7/level8/level9/level10/level11/deep.py")
    deep_src = src / deep_rel
    deep_tgt = tgt / deep_rel
    deep_src.parent.mkdir(parents=True, exist_ok=True)
    deep_tgt.parent.mkdir(parents=True, exist_ok=True)

    base_payload = b"X" * 4096
    deep_src.write_bytes(base_payload)
    deep_tgt.write_bytes(base_payload)

    # Baseline check: 100% parity
    report = compare_trees(src, tgt, python_only=True)
    assert report.passed is True
    assert report.mismatched_count == 0

    # 1. Mutate byte 0 (first byte)
    mutated_0 = bytearray(base_payload)
    mutated_0[0] ^= 0x01
    deep_tgt.write_bytes(bytes(mutated_0))

    report = compare_trees(src, tgt, python_only=True, generate_diffs=True)
    assert report.passed is False
    assert report.mismatched_count == 1
    assert report.mismatches[0].rel_path == deep_rel.as_posix()
    assert report.mismatches[0].src_sha256 != report.mismatches[0].target_sha256

    # Verify CLI returns exit code 1
    cmd = [
        sys.executable,
        str(VERIFIER_SCRIPT),
        "--check",
        "--src-dir",
        str(src),
        "--target-dir",
        str(tgt),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1, f"Expected exit code 1, got {res.returncode}"
    assert "FAIL" in res.stdout
    assert deep_rel.as_posix() in res.stdout

    # 2. Mutate middle byte
    mutated_mid = bytearray(base_payload)
    mutated_mid[2048] ^= 0xFF
    deep_tgt.write_bytes(bytes(mutated_mid))

    report = compare_trees(src, tgt, python_only=True)
    assert report.passed is False
    assert report.mismatched_count == 1

    # 3. Mutate EOF byte (last byte)
    mutated_eof = bytearray(base_payload)
    mutated_eof[-1] ^= 0x80
    deep_tgt.write_bytes(bytes(mutated_eof))

    report = compare_trees(src, tgt, python_only=True)
    assert report.passed is False
    assert report.mismatched_count == 1


# ==============================================================================
# 2. Asymmetric Missing Files in Source & Target
# ==============================================================================

def test_adversarial_missing_in_target_and_source_matrix(sandbox_trees: Tuple[Path, Path]):
    """Empirically tests unilateral and bilateral missing file scenarios."""
    src, tgt = sandbox_trees

    # File only in source
    p_src_only = src / "sub_pkg" / "src_only_component.py"
    p_src_only.parent.mkdir(parents=True, exist_ok=True)
    p_src_only.write_text("SRC_ONLY = True\n", encoding="utf-8")

    report = compare_trees(src, tgt, python_only=True)
    assert report.passed is False
    assert report.only_in_src_count == 1
    assert report.only_in_target_count == 0
    assert report.only_in_src == ["sub_pkg/src_only_component.py"]

    cmd = [
        sys.executable,
        str(VERIFIER_SCRIPT),
        "--src-dir",
        str(src),
        "--target-dir",
        str(tgt),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1
    assert "sub_pkg/src_only_component.py" in res.stdout

    # File only in target
    p_tgt_only = tgt / "another_pkg" / "tgt_only_component.py"
    p_tgt_only.parent.mkdir(parents=True, exist_ok=True)
    p_tgt_only.write_text("TGT_ONLY = True\n", encoding="utf-8")

    report = compare_trees(src, tgt, python_only=True)
    assert report.passed is False
    assert report.only_in_src_count == 1
    assert report.only_in_target_count == 1
    assert "another_pkg/tgt_only_component.py" in report.only_in_target

    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1
    assert "another_pkg/tgt_only_component.py" in res.stdout


# ==============================================================================
# 3. Noise & Unmonitored Artifact Invariance
# ==============================================================================

def test_adversarial_unmonitored_artifacts_and_pycache_noise(sandbox_trees: Tuple[Path, Path]):
    """Asserts verifier ignores __pycache__, temp files, OS files, but fails on non-py in --all-files."""
    src, tgt = sandbox_trees

    # Inject deep __pycache__ in src only
    cache_dir = src / "sub" / "__pycache__"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "module.cpython-311.pyc").write_bytes(b"\x00\x01\x02\x03CACHE")
    (cache_dir / "module.cpython-311.pyo").write_bytes(b"\x00\x01\x02\x03OPT")

    # Inject IDE & test cache in tgt only
    pytest_cache = tgt / ".pytest_cache" / "v"
    pytest_cache.mkdir(parents=True, exist_ok=True)
    (pytest_cache / "cache.json").write_text("{}", encoding="utf-8")

    mypy_cache = src / ".mypy_cache" / "3.11"
    mypy_cache.mkdir(parents=True, exist_ok=True)
    (mypy_cache / "meta.json").write_text("{}", encoding="utf-8")

    # Inject temp, swap, and OS junk files
    (src / "temp.tmp").write_text("temp", encoding="utf-8")
    (tgt / "file.swp").write_bytes(b"swap")
    (src / "backup.bak").write_text("bak", encoding="utf-8")
    (src / ".DS_Store").write_bytes(b"\x00\x00\x01")
    (tgt / "Thumbs.db").write_bytes(b"\x00\x00\x02")
    (src / ".hidden_file.py").write_text("HIDDEN=True\n", encoding="utf-8")

    # In default python_only mode, all the above MUST be ignored
    report = compare_trees(src, tgt, python_only=True)
    assert report.passed is True
    assert report.mismatched_count == 0
    assert report.only_in_src_count == 0
    assert report.only_in_target_count == 0

    cmd = [
        sys.executable,
        str(VERIFIER_SCRIPT),
        "--src-dir",
        str(src),
        "--target-dir",
        str(tgt),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0

    # Non-Python files in python-only mode vs --all-files mode:
    (src / "README.md").write_text("# Doc\n", encoding="utf-8")
    (tgt / "README.md").write_text("# Different Doc\n", encoding="utf-8")

    # In python_only mode, README.md is ignored
    report_py = compare_trees(src, tgt, python_only=True)
    assert report_py.passed is True

    # In --all-files mode, README.md causes parity failure
    report_all = compare_trees(src, tgt, python_only=False)
    assert report_all.passed is False
    assert report_all.mismatched_count == 1
    assert report_all.mismatches[0].rel_path == "README.md"

    cmd_all = [
        sys.executable,
        str(VERIFIER_SCRIPT),
        "--all-files",
        "--src-dir",
        str(src),
        "--target-dir",
        str(tgt),
    ]
    res_all = subprocess.run(cmd_all, capture_output=True, text=True)
    assert res_all.returncode == 1
    assert "README.md" in res_all.stdout


# ==============================================================================
# 4. Huge Simulated Files & Zero-Byte Files
# ==============================================================================

def test_adversarial_zero_byte_files(sandbox_trees: Tuple[Path, Path]):
    """Empirically tests zero-byte files (identical and divergent)."""
    src, tgt = sandbox_trees

    # Case A: Identical 0-byte file in both trees
    (src / "empty.py").write_bytes(b"")
    (tgt / "empty.py").write_bytes(b"")

    empty_sha256 = hashlib.sha256(b"").hexdigest()
    assert empty_sha256 == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    report = compare_trees(src, tgt, python_only=True)
    assert report.passed is True
    assert (src / "empty.py").as_posix() not in report.only_in_src

    # Case B: 0 bytes in src vs 1 byte in tgt
    (tgt / "empty.py").write_bytes(b"\n")
    report = compare_trees(src, tgt, python_only=True)
    assert report.passed is False
    assert report.mismatched_count == 1
    assert report.mismatches[0].rel_path == "empty.py"
    assert report.mismatches[0].src_size == 0
    assert report.mismatches[0].target_size == 1

    cmd = [
        sys.executable,
        str(VERIFIER_SCRIPT),
        "--src-dir",
        str(src),
        "--target-dir",
        str(tgt),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1


def test_adversarial_huge_file_chunk_boundary_mutation(sandbox_trees: Tuple[Path, Path]):
    """Empirically tests a 10MB file with mutation exactly at 64KB chunk boundaries."""
    src, tgt = sandbox_trees

    file_size = 10 * 1024 * 1024  # 10 MB (160 chunks of 64KB)
    huge_src = src / "huge_module.py"
    huge_tgt = tgt / "huge_module.py"

    # Create deterministic repeating pattern
    chunk = b"A" * 65536
    num_chunks = file_size // 65536

    with open(huge_src, "wb") as f_src, open(huge_tgt, "wb") as f_tgt:
        for _ in range(num_chunks):
            f_src.write(chunk)
            f_tgt.write(chunk)

    # Identical huge file check
    report = compare_trees(src, tgt, python_only=True)
    assert report.passed is True

    # Mutate byte 65535 (last byte of chunk 0)
    with open(huge_tgt, "r+b") as f_tgt:
        f_tgt.seek(65535)
        f_tgt.write(b"B")

    report = compare_trees(src, tgt, python_only=True)
    assert report.passed is False
    assert report.mismatched_count == 1
    assert report.mismatches[0].rel_path == "huge_module.py"

    # Mutate byte 65536 (first byte of chunk 1)
    with open(huge_tgt, "r+b") as f_tgt:
        f_tgt.seek(65535)
        f_tgt.write(b"A")  # Restore
        f_tgt.seek(65536)
        f_tgt.write(b"C")  # Mutate chunk 1

    report = compare_trees(src, tgt, python_only=True)
    assert report.passed is False
    assert report.mismatched_count == 1


# ==============================================================================
# 5. Case Sensitivity Traps
# ==============================================================================

def test_adversarial_case_sensitivity_traps(sandbox_trees: Tuple[Path, Path]):
    """Tests case mismatch behavior (e.g. TestComponent.py vs testcomponent.py)."""
    src, tgt = sandbox_trees

    # Create distinct case names
    (src / "CaseComponent.py").write_text("# CaseComponent\n", encoding="utf-8")
    (tgt / "casecomponent.py").write_text("# CaseComponent\n", encoding="utf-8")

    # In scan_tree, filesystem returns whatever casing exists
    report = compare_trees(src, tgt, python_only=True)

    # Because relative paths differ in casing ("CaseComponent.py" vs "casecomponent.py"):
    # Parity MUST fail because one side does not have the exact case key of the other!
    assert report.passed is False
    assert "CaseComponent.py" in report.only_in_src
    assert "casecomponent.py" in report.only_in_target

    cmd = [
        sys.executable,
        str(VERIFIER_SCRIPT),
        "--src-dir",
        str(src),
        "--target-dir",
        str(tgt),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1


# ==============================================================================
# 6. Exit Code 1 Unconditional Guarantee
# ==============================================================================

@pytest.mark.parametrize(
    "failure_scenario",
    [
        "mismatch",
        "missing_src",
        "missing_tgt",
        "strict_underflow",
        "combined",
    ],
)
def test_adversarial_exit_code_unconditional_guarantee(sandbox_trees: Tuple[Path, Path], failure_scenario: str):
    """Verifies exit code 1 is unconditionally returned for all parity violation types."""
    src, tgt = sandbox_trees

    extra_args = []
    if failure_scenario == "mismatch":
        (tgt / "module_0.py").write_bytes(b"# corrupted\n")
    elif failure_scenario == "missing_src":
        (tgt / "extra_tgt.py").write_bytes(b"# only in target\n")
    elif failure_scenario == "missing_tgt":
        (src / "extra_src.py").write_bytes(b"# only in src\n")
    elif failure_scenario == "strict_underflow":
        # 5 identical files present, require 10
        extra_args = ["--strict", "--min-files", "10"]
    elif failure_scenario == "combined":
        (tgt / "module_0.py").write_bytes(b"# corrupted\n")
        (tgt / "extra_tgt.py").write_bytes(b"# only in target\n")
        (src / "extra_src.py").write_bytes(b"# only in src\n")
        extra_args = ["--strict", "--min-files", "20"]

    cmd = [
        sys.executable,
        str(VERIFIER_SCRIPT),
        "--src-dir",
        str(src),
        "--target-dir",
        str(tgt),
        *extra_args,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1, (
        f"Scenario '{failure_scenario}' failed to exit with code 1. Got: {res.returncode}\n"
        f"STDOUT: {res.stdout}\nSTDERR: {res.stderr}"
    )


def test_adversarial_exit_code_two_on_system_and_cli_errors(sandbox_trees: Tuple[Path, Path]):
    """Verifies exit code 2 is returned on bad arguments or missing directories."""
    src, tgt = sandbox_trees

    # Invalid flag
    res = subprocess.run(
        [sys.executable, str(VERIFIER_SCRIPT), "--non-existent-flag"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 2

    # Non-existent source directory
    res_no_dir = subprocess.run(
        [
            sys.executable,
            str(VERIFIER_SCRIPT),
            "--src-dir",
            "non/existent/path/for/sure",
            "--target-dir",
            str(tgt),
        ],
        capture_output=True,
        text=True,
    )
    assert res_no_dir.returncode == 2


# ==============================================================================
# 7. Complete Repair Verification via --sync
# ==============================================================================

def test_adversarial_sync_repairs_all_directions(sandbox_trees: Tuple[Path, Path]):
    """Tests bidirectional sync engine under complex divergent scenarios."""
    src, tgt = sandbox_trees

    # Setup divergent scenario:
    # 1. file_src_only: in src only
    # 2. file_tgt_only: in tgt only
    # 3. file_mismatch_src_newer: src has newer mtime
    # 4. file_mismatch_tgt_newer: tgt has newer mtime

    (src / "file_src_only.py").write_text("SRC_ONLY\n", encoding="utf-8")
    (tgt / "file_tgt_only.py").write_text("TGT_ONLY\n", encoding="utf-8")

    mismatch_1_src = src / "mismatch_1.py"
    mismatch_1_tgt = tgt / "mismatch_1.py"
    mismatch_1_src.write_text("MISMATCH_1_SRC_NEWER\n", encoding="utf-8")
    mismatch_1_tgt.write_text("MISMATCH_1_OLD\n", encoding="utf-8")
    now = time.time()
    os.utime(mismatch_1_tgt, (now - 100, now - 100))
    os.utime(mismatch_1_src, (now + 100, now + 100))

    mismatch_2_src = src / "mismatch_2.py"
    mismatch_2_tgt = tgt / "mismatch_2.py"
    mismatch_2_src.write_text("MISMATCH_2_OLD\n", encoding="utf-8")
    mismatch_2_tgt.write_text("MISMATCH_2_TGT_NEWER\n", encoding="utf-8")
    os.utime(mismatch_2_src, (now - 100, now - 100))
    os.utime(mismatch_2_tgt, (now + 100, now + 100))

    # Pre-sync verification: fails with code 1
    pre_report = compare_trees(src, tgt, python_only=True)
    assert pre_report.passed is False
    assert pre_report.mismatched_count == 2
    assert pre_report.only_in_src_count == 1
    assert pre_report.only_in_target_count == 1

    # Test --dry-run first: ensure files on disk remain untouched
    cmd_dry = [
        sys.executable,
        str(VERIFIER_SCRIPT),
        "--sync",
        "--direction",
        "newest",
        "--dry-run",
        "--src-dir",
        str(src),
        "--target-dir",
        str(tgt),
    ]
    res_dry = subprocess.run(cmd_dry, capture_output=True, text=True)
    assert res_dry.returncode == 1  # check runs after sync and fails because dry-run didn't change disk
    assert not (tgt / "file_src_only.py").exists()
    assert not (src / "file_tgt_only.py").exists()

    # Now run real --sync with --direction newest
    cmd_sync = [
        sys.executable,
        str(VERIFIER_SCRIPT),
        "--sync",
        "--direction",
        "newest",
        "--src-dir",
        str(src),
        "--target-dir",
        str(tgt),
    ]
    res_sync = subprocess.run(cmd_sync, capture_output=True, text=True)
    assert res_sync.returncode == 0, f"Sync failed: {res_sync.stderr}\n{res_sync.stdout}"

    # Verify post-sync parity: 100% PASS with 0 mismatches
    post_report = compare_trees(src, tgt, python_only=True)
    assert post_report.passed is True
    assert post_report.mismatched_count == 0
    assert post_report.only_in_src_count == 0
    assert post_report.only_in_target_count == 0

    # Verify exact contents
    assert (tgt / "file_src_only.py").read_text(encoding="utf-8") == "SRC_ONLY\n"
    assert (src / "file_tgt_only.py").read_text(encoding="utf-8") == "TGT_ONLY\n"
    assert (tgt / "mismatch_1.py").read_text(encoding="utf-8") == "MISMATCH_1_SRC_NEWER\n"
    assert (src / "mismatch_2.py").read_text(encoding="utf-8") == "MISMATCH_2_TGT_NEWER\n"


def test_adversarial_sync_src_to_ts_and_ts_to_src(tmp_path: Path):
    """Tests directional sync modes src-to-ts and ts-to-src."""
    src = tmp_path / "src_dir"
    tgt = tmp_path / "tgt_dir"
    src.mkdir()
    tgt.mkdir()

    f_src = src / "override.py"
    f_tgt = tgt / "override.py"
    f_src.write_text("SOURCE_CANONICAL\n", encoding="utf-8")
    f_tgt.write_text("TARGET_MUTATED\n", encoding="utf-8")

    # Give target a newer mtime
    now = time.time()
    os.utime(f_src, (now - 200, now - 200))
    os.utime(f_tgt, (now + 200, now + 200))

    # Synchronize src-to-ts: even though target is newer, src-to-ts MUST overwrite target
    sync_trees(src, tgt, direction="src-to-ts")
    assert f_tgt.read_text(encoding="utf-8") == "SOURCE_CANONICAL\n"

    # Now test ts-to-src
    f_tgt.write_text("TARGET_AUTHORITATIVE\n", encoding="utf-8")
    sync_trees(src, tgt, direction="ts-to-src")
    assert f_src.read_text(encoding="utf-8") == "TARGET_AUTHORITATIVE\n"


# ==============================================================================
# 8. Binary / Non-UTF8 Files & Diff Formatter Resilience
# ==============================================================================

def test_adversarial_non_utf8_binary_files(sandbox_trees: Tuple[Path, Path]):
    """Verifies that non-UTF8 binary byte sequences in .py files do not crash the verifier or diff engine."""
    src, tgt = sandbox_trees

    binary_payload_1 = b"\x00\xff\xfe\x80\x81\xfe\xff\x00\x01\x02\x03\x04"
    binary_payload_2 = b"\x00\xff\xfe\x80\x81\xfe\xff\x00\x01\x02\x99\x99"

    bin_src = src / "binary_module.py"
    bin_tgt = tgt / "binary_module.py"
    bin_src.write_bytes(binary_payload_1)
    bin_tgt.write_bytes(binary_payload_2)

    # CLI with --diff: must not raise UnicodeDecodeError and must exit code 1
    cmd = [
        sys.executable,
        str(VERIFIER_SCRIPT),
        "--check",
        "--diff",
        "--src-dir",
        str(src),
        "--target-dir",
        str(tgt),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1
    assert "binary_module.py" in res.stdout


# ==============================================================================
# 9. CLI Patch Output & JSON Report Generation
# ==============================================================================

def test_adversarial_cli_patch_file_and_json_generation(sandbox_trees: Tuple[Path, Path], tmp_path: Path):
    """Tests generating patch file and JSON reports under adversarial mismatches."""
    src, tgt = sandbox_trees

    (src / "patch_test.py").write_text("LINE_1 = 1\nLINE_2 = 2\n", encoding="utf-8")
    (tgt / "patch_test.py").write_text("LINE_1 = 1\nLINE_2 = 999\n", encoding="utf-8")

    patch_file = tmp_path / "divergence.patch"
    json_file = tmp_path / "divergence.json"

    cmd = [
        sys.executable,
        str(VERIFIER_SCRIPT),
        "--check",
        "--diff",
        "--diff-output",
        str(patch_file),
        "--json-output",
        str(json_file),
        "--src-dir",
        str(src),
        "--target-dir",
        str(tgt),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1

    # Verify patch file created and valid
    assert patch_file.is_file()
    patch_text = patch_file.read_text(encoding="utf-8")
    assert "-LINE_2 = 2" in patch_text
    assert "+LINE_2 = 999" in patch_text

    # Verify JSON report file created and valid
    assert json_file.is_file()
    data = json.loads(json_file.read_text(encoding="utf-8"))
    assert data["passed"] is False
    assert data["mismatched_count"] == 1
    assert data["mismatches"][0]["rel_path"] == "patch_test.py"
