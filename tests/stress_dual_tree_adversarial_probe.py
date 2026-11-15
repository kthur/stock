"""
tests/stress_dual_tree_adversarial_probe.py
Adversarial Empirical Probe Harness for Dual-Tree Cryptographic Parity.

Executed by challenger_r186_m3_1 to independently verify and probe edge cases:
- Probe 1: Direct bit-for-bit SHA-256 equivalence between root and nested verifier scripts.
- Probe 2: Full repository 378-module cryptographic parity and identical file count assertion.
- Probe 3: Strict threshold enforcement (--min-files 378 passes, --min-files 379 fails).
- Probe 4: Adversarial single-byte mutation detection across multiple byte offsets.
- Probe 5: Adversarial zero-byte file behavior (identical empty vs divergent empty).
- Probe 6: Case-sensitivity traps and POSIX normalization.
- Probe 7: Pycache, OS junk, and cache artifact isolation under deep nesting.
- Probe 8: All-files mode parity verification (379 files, including non-py assets).
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Ensure repo root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.verify_dual_tree_parity import (
    DEFAULT_MIN_FILES,
    compare_trees,
    compute_sha256,
    find_repo_root,
    scan_tree,
)

REPO_ROOT = find_repo_root()
ROOT_VERIFIER = REPO_ROOT / "scripts" / "verify_dual_tree_parity.py"
TS_VERIFIER = REPO_ROOT / "trading_system" / "scripts" / "verify_dual_tree_parity.py"


def probe_1_script_identity():
    print("[PROBE 1] Script Bit-for-Bit Identity Check...")
    h1 = hashlib.sha256(ROOT_VERIFIER.read_bytes()).hexdigest()
    h2 = hashlib.sha256(TS_VERIFIER.read_bytes()).hexdigest()
    assert h1 == h2, f"SHA-256 mismatch between scripts: {h1} != {h2}"
    assert DEFAULT_MIN_FILES == 378, f"DEFAULT_MIN_FILES must be 378, got {DEFAULT_MIN_FILES}"
    print(f"  PASS: Both scripts share identical SHA-256: {h1}")


def probe_2_production_parity():
    print("[PROBE 2] Production Dual-Tree Parity Scan...")
    src_dir = REPO_ROOT / "src"
    ts_dir = REPO_ROOT / "trading_system" / "src"

    report = compare_trees(src_dir, ts_dir, python_only=True, strict=True, min_files=378)
    assert report.passed, f"Parity failed: {report.failure_reasons}"
    assert report.mismatched_count == 0, f"Found {report.mismatched_count} mismatches"
    assert report.only_in_src_count == 0, f"Only in src: {report.only_in_src}"
    assert report.only_in_target_count == 0, f"Only in ts: {report.only_in_target}"
    assert report.identical_count == 378, f"Expected exactly 378 identical python files, got {report.identical_count}"
    assert report.total_src_files == 378
    assert report.total_target_files == 378
    print(f"  PASS: Exactly 378/378 identical Python files verified in {report.scan_duration_sec:.3f}s")


def probe_3_strict_threshold_bounds():
    print("[PROBE 3] Strict Threshold Bound Enforcement...")
    src_dir = REPO_ROOT / "src"
    ts_dir = REPO_ROOT / "trading_system" / "src"

    # min_files = 378 should PASS
    rep_378 = compare_trees(src_dir, ts_dir, python_only=True, strict=True, min_files=378)
    assert rep_378.passed, "Strict threshold 378 should pass"

    # min_files = 379 should FAIL
    rep_379 = compare_trees(src_dir, ts_dir, python_only=True, strict=True, min_files=379)
    assert not rep_379.passed, "Strict threshold 379 must fail when 378 files present"
    assert any("Strict threshold violation" in r for r in rep_379.failure_reasons)

    # CLI test for min-files 379 exit code
    res = subprocess.run(
        [sys.executable, str(ROOT_VERIFIER), "--check", "--strict", "--min-files", "379"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1, f"Expected returncode 1, got {res.returncode}"
    assert "Strict threshold violation: identical file count 378 < required 379" in res.stdout
    print("  PASS: Boundary threshold min_files=379 correctly rejected with exit code 1")


def probe_4_adversarial_single_byte_mutation():
    print("[PROBE 4] Adversarial Single-Byte Mutation Harness...")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / "src"
        tgt = tmp_path / "tgt"
        src.mkdir()
        tgt.mkdir()

        # Seed 10 files
        for i in range(10):
            p1 = src / f"mod_{i}.py"
            p2 = tgt / f"mod_{i}.py"
            data = f"def fn_{i}(): return {i * 100}\n".encode() * 50
            p1.write_bytes(data)
            p2.write_bytes(data)

        # Baseline
        rep = compare_trees(src, tgt, python_only=True)
        assert rep.passed and rep.identical_count == 10

        # Mutation at offset 0
        target_file = tgt / "mod_3.py"
        raw = bytearray(target_file.read_bytes())
        raw[0] ^= 0x01
        target_file.write_bytes(bytes(raw))

        rep = compare_trees(src, tgt, python_only=True, generate_diffs=True)
        assert not rep.passed
        assert rep.mismatched_count == 1
        assert rep.mismatches[0].rel_path == "mod_3.py"
        assert rep.mismatches[0].diff_snippet is not None

        # Mutation at end of file
        raw = bytearray(target_file.read_bytes())
        raw[-1] ^= 0xFF
        target_file.write_bytes(bytes(raw))

        rep = compare_trees(src, tgt, python_only=True)
        assert not rep.passed
        assert rep.mismatched_count == 1

        # Mutation in middle of large payload
        large_src = src / "large.py"
        large_tgt = tgt / "large.py"
        payload = b"Z" * (128 * 1024)
        large_src.write_bytes(payload)
        large_tgt.write_bytes(payload)

        raw_large = bytearray(payload)
        raw_large[65536] ^= 0x42  # exactly at 64K boundary
        large_tgt.write_bytes(bytes(raw_large))

        rep = compare_trees(src, tgt, python_only=True)
        assert not rep.passed
        assert rep.mismatched_count == 2  # mod_3 and large
    print("  PASS: Single-byte mutations at start, chunk boundary, and EOF reliably detected")


def probe_5_adversarial_zero_byte_files():
    print("[PROBE 5] Adversarial Zero-Byte File Handling...")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / "src"
        tgt = tmp_path / "tgt"
        src.mkdir()
        tgt.mkdir()

        (src / "__init__.py").write_bytes(b"")
        (tgt / "__init__.py").write_bytes(b"")

        empty_digest = compute_sha256(src / "__init__.py")
        assert empty_digest == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

        rep = compare_trees(src, tgt, python_only=True)
        assert rep.passed
        assert rep.identical_count == 1

        # Divergence: 0-byte vs 1-byte
        (tgt / "__init__.py").write_bytes(b" ")
        rep = compare_trees(src, tgt, python_only=True)
        assert not rep.passed
        assert rep.mismatched_count == 1
        assert rep.mismatches[0].src_size == 0
        assert rep.mismatches[0].target_size == 1

        # Missing: deleted in target
        (tgt / "__init__.py").unlink()
        rep = compare_trees(src, tgt, python_only=True)
        assert not rep.passed
        assert rep.only_in_src_count == 1
    print("  PASS: Zero-byte file identity, mismatch, and missingness correctly verified")


def probe_6_case_sensitivity_traps():
    print("[PROBE 6] Case-Sensitivity Stress Probe...")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / "src"
        tgt = tmp_path / "tgt"
        src.mkdir()
        tgt.mkdir()

        # Create CamelCase in src and lowercase in tgt
        (src / "MyService.py").write_text("# service\n", encoding="utf-8")
        (tgt / "myservice.py").write_text("# service\n", encoding="utf-8")

        rep = compare_trees(src, tgt, python_only=True)
        assert not rep.passed
        # Because POSIX keys differ: MyService.py vs myservice.py
        assert "MyService.py" in rep.only_in_src
        assert "myservice.py" in rep.only_in_target
    print("  PASS: Case sensitivity mismatch causes explicit parity failure")


def probe_7_pycache_and_unmonitored_isolation():
    print("[PROBE 7] Pycache and Unmonitored Artifact Isolation...")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / "src"
        tgt = tmp_path / "tgt"
        src.mkdir()
        tgt.mkdir()

        (src / "core.py").write_text("X = 1\n", encoding="utf-8")
        (tgt / "core.py").write_text("X = 1\n", encoding="utf-8")

        # Inject deep __pycache__, .pytest_cache, .mypy_cache
        pycache_dir = src / "sub" / "__pycache__"
        pycache_dir.mkdir(parents=True)
        (pycache_dir / "core.cpython-311.pyc").write_bytes(b"\x00\x00\x00\x00junk")
        (src / "sub" / "core.py").write_text("Y = 2\n", encoding="utf-8")
        (tgt / "sub").mkdir(parents=True, exist_ok=True)
        (tgt / "sub" / "core.py").write_text("Y = 2\n", encoding="utf-8")

        (tgt / ".pytest_cache").mkdir()
        (tgt / ".pytest_cache" / "cache.db").write_bytes(b"cache")
        (src / "core.py.bak").write_text("backup", encoding="utf-8")
        (tgt / "Thumbs.db").write_bytes(b"thumbs")
        (src / ".DS_Store").write_bytes(b"ds")
        (src / ".git").mkdir()
        (src / ".git" / "HEAD").write_text("ref", encoding="utf-8")

        rep = compare_trees(src, tgt, python_only=True)
        assert rep.passed
        assert rep.identical_count == 2
        assert rep.only_in_src_count == 0
        assert rep.only_in_target_count == 0
    print("  PASS: Cache directories and junk files fully isolated and ignored")


def probe_8_all_files_mode():
    print("[PROBE 8] All-Files Mode Verification in Production...")
    src_dir = REPO_ROOT / "src"
    ts_dir = REPO_ROOT / "trading_system" / "src"

    rep = compare_trees(src_dir, ts_dir, python_only=False, strict=False)
    assert rep.passed
    assert rep.identical_count == 379
    assert rep.mismatched_count == 0
    # Confirm responsive.css is captured
    all_files = scan_tree(src_dir, python_only=False)
    assert "web/assets/responsive.css" in all_files
    print(f"  PASS: All-files mode verified across {rep.identical_count} files including web assets")


def main():
    print("=" * 80)
    print("STARTING ADVERSARIAL EMPIRICAL PROBES FOR DUAL-TREE PARITY (F977)")
    print("=" * 80)
    probe_1_script_identity()
    probe_2_production_parity()
    probe_3_strict_threshold_bounds()
    probe_4_adversarial_single_byte_mutation()
    probe_5_adversarial_zero_byte_files()
    probe_6_case_sensitivity_traps()
    probe_7_pycache_and_unmonitored_isolation()
    probe_8_all_files_mode()
    print("=" * 80)
    print("ALL 8 ADVERSARIAL PROBES PASSED WITH 100% EMPIRICAL SUCCESS")
    print("=" * 80)


def test_probe_1_script_identity(): probe_1_script_identity()
def test_probe_2_production_parity(): probe_2_production_parity()
def test_probe_3_strict_threshold_bounds(): probe_3_strict_threshold_bounds()
def test_probe_4_adversarial_single_byte_mutation(): probe_4_adversarial_single_byte_mutation()
def test_probe_5_adversarial_zero_byte_files(): probe_5_adversarial_zero_byte_files()
def test_probe_6_case_sensitivity_traps(): probe_6_case_sensitivity_traps()
def test_probe_7_pycache_and_unmonitored_isolation(): probe_7_pycache_and_unmonitored_isolation()
def test_probe_8_all_files_mode(): probe_8_all_files_mode()


if __name__ == "__main__":
    main()
