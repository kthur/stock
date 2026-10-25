"""
tests/test_dual_tree_parity.py
Comprehensive test suite for Dual-Tree Cryptographic Parity Guard & Pre-Commit Automation.

Covers:
  - TC-1: Production repository 328-file parity assertion (100% bit-for-bit SHA-256 match).
  - TC-2: Cryptographic mirror parity between root and nested verifier scripts.
  - TC-3: CLI flags (--check, --strict, --json, --diff, --all-files, --sync, --quiet, --verbose).
  - TC-4: Adversarial single-byte corruption detection and unified diff generation.
  - TC-5: Adversarial missing file detection (only in src / only in target).
  - TC-6: Strict threshold enforcement (min-files assertion).
  - TC-7: Ignore rules invariance (__pycache__, .tmp, .pyc, Thumbs.db).
  - TC-8: Bi-directional synchronization engine (newest, src-to-ts, ts-to-src, dry-run).
  - TC-9: GitHub Actions error annotations and step summary generation.
  - TC-10: Pre-commit hook lifecycle simulation in temp git repository:
          unilateral auto-mirroring, bilateral conflict detection, check-only gating, and fast-path.
  - TC-11: Hook installer verification (git config core.hooksPath and fallback copying).
  - TC-12: Partial staged edits rejection (working tree differs from staged index).
  - TC-13: DUAL_TREE_MODE=check environment variable gating and check-only enforcement.
  - TC-14: git mv staged rename auto-mirroring and old path removal.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Generator

import pytest

import importlib.util

# Import parity modules directly
from scripts.verify_dual_tree_parity import (
    DEFAULT_MIN_FILES,
    FileHashMeta,
    MismatchDetail,
    ParityReport,
    compare_trees,
    compute_sha256,
    emit_github_annotations,
    find_repo_root,
    scan_tree,
    sync_trees,
    write_github_step_summary,
)

REPO_ROOT = find_repo_root()


def _load_pre_commit_hook():
    hook_script = REPO_ROOT / "scripts" / "hooks" / "pre-commit-dual-tree-sync.py"
    spec = importlib.util.spec_from_file_location("pre_commit_dual_tree_sync", hook_script)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load spec from {hook_script}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_pre_commit_mod = _load_pre_commit_hook()
hook_sync_and_verify = _pre_commit_mod.synchronize_and_verify


# ==============================================================================
# 1. Repository-Level Cryptographic Parity Tests
# ==============================================================================

def test_repo_full_dual_tree_parity():
    """Asserts 100% bit-for-bit SHA-256 parity across all 328 Python modules in production."""
    src_dir = REPO_ROOT / "src"
    ts_dir = REPO_ROOT / "trading_system" / "src"

    report = compare_trees(
        src_dir=src_dir,
        target_dir=ts_dir,
        python_only=True,
        strict=True,
        min_files=328,
        generate_diffs=True,
    )

    assert report.passed is True, f"Parity failure reasons: {report.failure_reasons}"
    assert report.mismatched_count == 0, f"Mismatches found: {[m.rel_path for m in report.mismatches]}"
    assert report.only_in_src_count == 0, f"Only in src: {report.only_in_src}"
    assert report.only_in_target_count == 0, f"Only in trading_system/src: {report.only_in_target}"
    assert report.identical_count >= 328, f"Expected >= 328 files, got {report.identical_count}"
    assert report.total_src_files == report.total_target_files
    assert len(report.failure_reasons) == 0


def test_verifier_scripts_bit_for_bit_identical():
    """Asserts scripts/verify_dual_tree_parity.py and trading_system/scripts/... are identical."""
    root_script = REPO_ROOT / "scripts" / "verify_dual_tree_parity.py"
    ts_script = REPO_ROOT / "trading_system" / "scripts" / "verify_dual_tree_parity.py"

    assert root_script.is_file(), f"Missing {root_script}"
    assert ts_script.is_file(), f"Missing {ts_script}"

    h1 = compute_sha256(root_script)
    h2 = compute_sha256(ts_script)

    assert h1 == h2, (
        f"Verifier scripts desynchronized!\n"
        f"  root: {root_script} ({h1})\n"
        f"  ts:   {ts_script} ({h2})"
    )


def test_cli_strict_execution_exit_code_zero():
    """Tests CLI execution of scripts/verify_dual_tree_parity.py --strict returns exit code 0."""
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "verify_dual_tree_parity.py"),
        "--check",
        "--strict",
        "--diff",
    ]
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert res.returncode == 0, f"CLI returned {res.returncode}:\n{res.stderr}\n{res.stdout}"
    assert "Status:                     PASS" in res.stdout
    assert "Strict Mode:                True" in res.stdout


def test_cli_json_and_output_file(tmp_path: Path):
    """Tests --json and --json-output flags produce schema-compliant reports."""
    json_path = tmp_path / "parity_test_report.json"
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "verify_dual_tree_parity.py"),
        "--strict",
        "--json",
        "--json-output",
        str(json_path),
    ]
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert res.returncode == 0

    # Test stdout json
    data_stdout = json.loads(res.stdout)
    assert data_stdout["passed"] is True
    assert data_stdout["identical_count"] >= 328
    assert data_stdout["mismatched_count"] == 0

    # Test written json file
    assert json_path.is_file()
    data_file = json.loads(json_path.read_text(encoding="utf-8"))
    assert data_file["passed"] is True
    assert data_file["timestamp"] is not None
    assert data_file["scan_duration_sec"] > 0


def test_cli_all_files_mode():
    """Tests --all-files includes non-python assets such as responsive.css."""
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "verify_dual_tree_parity.py"),
        "--all-files",
        "--strict",
        "--min-files",
        "328",
    ]
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert res.returncode == 0
    assert "Status:                     PASS" in res.stdout
    assert "Content Mismatches:         0" in res.stdout
    assert ("Total Source Files:         330" in res.stdout or "Total Source Files:         329" in res.stdout)
    assert ("Identical (100% SHA-256):   330" in res.stdout or "Identical (100% SHA-256):   329" in res.stdout)


# ==============================================================================
# 2. Adversarial & Mutation Tests (Isolated Temp Environments)
# ==============================================================================

@pytest.fixture
def mock_dual_trees(tmp_path: Path) -> Tuple[Path, Path]:
    """Creates a temporary dual-tree structure with 5 identical Python files."""
    src = tmp_path / "mock_src"
    ts = tmp_path / "mock_ts"
    src.mkdir()
    ts.mkdir()

    for i in range(5):
        rel = f"module_{i}.py"
        content = f"# Module {i}\ndef func_{i}():\n    return {i * 10}\n"
        (src / rel).write_text(content, encoding="utf-8")
        (ts / rel).write_text(content, encoding="utf-8")

    sub_src = src / "subpkg"
    sub_ts = ts / "subpkg"
    sub_src.mkdir()
    sub_ts.mkdir()
    (sub_src / "nested.py").write_text("class Nested:\n    pass\n", encoding="utf-8")
    (sub_ts / "nested.py").write_text("class Nested:\n    pass\n", encoding="utf-8")

    return src, ts


def test_adversarial_single_byte_mutation(mock_dual_trees: Tuple[Path, Path]):
    """TC-4: Tests that altering even a single byte triggers mismatch failure and generates diff."""
    src, ts = mock_dual_trees
    target_file = ts / "module_2.py"

    # Flip 1 byte: change 20 to 21
    original = target_file.read_text(encoding="utf-8")
    target_file.write_text(original.replace("20", "21"), encoding="utf-8")

    report = compare_trees(src, ts, python_only=True, generate_diffs=True)
    assert report.passed is False
    assert report.mismatched_count == 1
    assert report.mismatches[0].rel_path == "module_2.py"
    assert report.mismatches[0].diff_snippet is not None
    assert "-    return 20" in report.mismatches[0].diff_snippet
    assert "+    return 21" in report.mismatches[0].diff_snippet

    # Test CLI invocation fails with code 1
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "verify_dual_tree_parity.py"),
        "--src-dir", str(src),
        "--target-dir", str(ts),
        "--diff",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1
    assert "Status:                     FAIL" in res.stdout
    assert "module_2.py" in res.stdout


def test_adversarial_missing_in_target(mock_dual_trees: Tuple[Path, Path]):
    """TC-5a: Tests detection of file present in src but missing in target."""
    src, ts = mock_dual_trees
    new_src_file = src / "new_feature.py"
    new_src_file.write_text("# New feature\n", encoding="utf-8")

    report = compare_trees(src, ts, python_only=True)
    assert report.passed is False
    assert report.only_in_src_count == 1
    assert "new_feature.py" in report.only_in_src

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "verify_dual_tree_parity.py"),
        "--src-dir", str(src),
        "--target-dir", str(ts),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1
    assert "new_feature.py" in res.stdout


def test_adversarial_missing_in_src(mock_dual_trees: Tuple[Path, Path]):
    """TC-5b: Tests detection of file present in target but missing in src."""
    src, ts = mock_dual_trees
    new_ts_file = ts / "orphan_ts.py"
    new_ts_file.write_text("# Orphan\n", encoding="utf-8")

    report = compare_trees(src, ts, python_only=True)
    assert report.passed is False
    assert report.only_in_target_count == 1
    assert "orphan_ts.py" in report.only_in_target

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "verify_dual_tree_parity.py"),
        "--src-dir", str(src),
        "--target-dir", str(ts),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1
    assert "orphan_ts.py" in res.stdout


def test_strict_threshold_violation(mock_dual_trees: Tuple[Path, Path]):
    """TC-6: Tests that strict mode fails if total identical files < min_files."""
    src, ts = mock_dual_trees
    # mock_dual_trees has 6 identical files
    report = compare_trees(src, ts, python_only=True, strict=True, min_files=10)
    assert report.passed is False
    assert any("Strict threshold violation" in r for r in report.failure_reasons)

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "verify_dual_tree_parity.py"),
        "--src-dir", str(src),
        "--target-dir", str(ts),
        "--strict",
        "--min-files", "10",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1
    assert "Strict threshold violation" in res.stdout


def test_ignore_rules_invariance(mock_dual_trees: Tuple[Path, Path]):
    """TC-7: Tests that caches (__pycache__, .tmp, .pyc, Thumbs.db) are ignored."""
    src, ts = mock_dual_trees

    # Create ignored artifacts
    pycache_src = src / "__pycache__"
    pycache_src.mkdir()
    (pycache_src / "module_0.cpython-312.pyc").write_bytes(b"\x00\x01\x02")

    (src / "temp.tmp").write_text("temporary", encoding="utf-8")
    (ts / "Thumbs.db").write_bytes(b"\xff\xfe")
    (ts / ".DS_Store").write_bytes(b"\x00")

    report = compare_trees(src, ts, python_only=True)
    assert report.passed is True
    assert report.identical_count == 6


# ==============================================================================
# 3. Tree Synchronization Engine Tests
# ==============================================================================

def test_sync_trees_src_to_ts(mock_dual_trees: Tuple[Path, Path]):
    """TC-8a: Tests sync_trees with direction='src-to-ts'."""
    src, ts = mock_dual_trees

    # Add new file in src and modify one
    (src / "brand_new.py").write_text("print('brand new')\n", encoding="utf-8")
    (src / "module_0.py").write_text("print('updated in src')\n", encoding="utf-8")

    # Dry run first
    copied, overwritten = sync_trees(src, ts, direction="src-to-ts", dry_run=True)
    assert copied == 1
    assert overwritten == 1
    assert not (ts / "brand_new.py").exists()

    # Real run
    copied, overwritten = sync_trees(src, ts, direction="src-to-ts", dry_run=False)
    assert copied == 1
    assert overwritten == 1
    assert (ts / "brand_new.py").read_text(encoding="utf-8") == "print('brand new')\n"
    assert (ts / "module_0.py").read_text(encoding="utf-8") == "print('updated in src')\n"

    report = compare_trees(src, ts, python_only=True)
    assert report.passed is True


def test_sync_trees_ts_to_src(mock_dual_trees: Tuple[Path, Path]):
    """TC-8b: Tests sync_trees with direction='ts-to-src'."""
    src, ts = mock_dual_trees

    (ts / "orphan.py").write_text("print('from ts')\n", encoding="utf-8")
    (ts / "module_1.py").write_text("print('updated in ts')\n", encoding="utf-8")

    copied, overwritten = sync_trees(src, ts, direction="ts-to-src", dry_run=False)
    assert copied == 1
    assert overwritten == 1
    assert (src / "orphan.py").read_text(encoding="utf-8") == "print('from ts')\n"
    assert (src / "module_1.py").read_text(encoding="utf-8") == "print('updated in ts')\n"

    report = compare_trees(src, ts, python_only=True)
    assert report.passed is True


def test_sync_trees_newest_mtime(mock_dual_trees: Tuple[Path, Path]):
    """TC-8c: Tests sync_trees with direction='newest'."""
    src, ts = mock_dual_trees

    # Make module_0 newer in src
    time.sleep(0.01)
    (src / "module_0.py").write_text("# newer in src\n", encoding="utf-8")

    # Make module_1 newer in ts
    time.sleep(0.01)
    (ts / "module_1.py").write_text("# newer in ts\n", encoding="utf-8")

    copied, overwritten = sync_trees(src, ts, direction="newest", dry_run=False)
    assert overwritten == 2

    assert (ts / "module_0.py").read_text(encoding="utf-8") == "# newer in src\n"
    assert (src / "module_1.py").read_text(encoding="utf-8") == "# newer in ts\n"

    report = compare_trees(src, ts, python_only=True)
    assert report.passed is True


# ==============================================================================
# 4. GitHub Actions CI Telemetry & Annotations Tests
# ==============================================================================

def test_github_step_summary_output(mock_dual_trees: Tuple[Path, Path], tmp_path: Path):
    """TC-9: Tests Markdown summary table generation for $GITHUB_STEP_SUMMARY."""
    src, ts = mock_dual_trees
    (ts / "module_1.py").write_text("mismatch\n", encoding="utf-8")
    (src / "only_src.py").write_text("only src\n", encoding="utf-8")

    report = compare_trees(src, ts, python_only=True)
    summary_file = tmp_path / "step_summary.md"

    write_github_step_summary(report, summary_file)
    assert summary_file.is_file()

    content = summary_file.read_text(encoding="utf-8")
    assert "Dual-Tree Cryptographic Parity Verification Report" in content
    assert "❌ FAIL" in content
    assert "module_1.py" in content
    assert "only_src.py" in content


# ==============================================================================
# 5. Git Pre-Commit Hook Lifecycle Simulation Tests
# ==============================================================================

@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """Initializes a self-contained test Git repository with user config."""
    repo = tmp_path / "test_repo"
    repo.mkdir()

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test Committer"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@committer.com"], cwd=repo, check=True)

    # Set up directory layout
    src = repo / "src"
    ts = repo / "trading_system" / "src"
    scripts = repo / "scripts"
    scripts_hooks = repo / "scripts" / "hooks"
    githooks = repo / ".githooks"

    src.mkdir(parents=True)
    ts.mkdir(parents=True)
    scripts_hooks.mkdir(parents=True)
    githooks.mkdir(parents=True)

    # Copy actual production scripts into test repository
    shutil.copy2(REPO_ROOT / "scripts" / "verify_dual_tree_parity.py", scripts / "verify_dual_tree_parity.py")
    shutil.copy2(
        REPO_ROOT / "scripts" / "hooks" / "pre-commit-dual-tree-sync.py",
        scripts_hooks / "pre-commit-dual-tree-sync.py",
    )
    shutil.copy2(REPO_ROOT / ".githooks" / "pre-commit", githooks / "pre-commit")

    # Initial baseline file
    (src / "base.py").write_text("def base():\n    return 42\n", encoding="utf-8")
    (ts / "base.py").write_text("def base():\n    return 42\n", encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)

    yield repo


def test_hook_unilateral_edit_in_src_auto_mirrors(temp_git_repo: Path):
    """TC-10a: Tests unilateral edit in src/ is auto-mirrored and staged into trading_system/src/."""
    repo = temp_git_repo
    src_file = repo / "src" / "base.py"
    ts_file = repo / "trading_system" / "src" / "base.py"

    src_file.write_text("def base():\n    return 999\n", encoding="utf-8")
    subprocess.run(["git", "add", "src/base.py"], cwd=repo, check=True)

    # Execute hook
    ret = hook_sync_and_verify(repo_root=repo, auto_mirror=True, quiet=False)
    assert ret == 0

    # Verify ts_file was updated on disk and staged
    assert ts_file.read_text(encoding="utf-8") == "def base():\n    return 999\n"

    staged_diff = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    assert "src/base.py" in staged_diff
    assert "trading_system/src/base.py" in staged_diff

    # Verify commit succeeds with identical blobs
    subprocess.run(["git", "commit", "-m", "Unilateral update with auto-mirror"], cwd=repo, check=True)

    blob_src = subprocess.run(["git", "show", "HEAD:src/base.py"], cwd=repo, capture_output=True).stdout
    blob_ts = subprocess.run(["git", "show", "HEAD:trading_system/src/base.py"], cwd=repo, capture_output=True).stdout
    assert blob_src == blob_ts


def test_hook_unilateral_addition_in_ts_auto_mirrors(temp_git_repo: Path):
    """TC-10b: Tests adding a new file in trading_system/src/ auto-mirrors to src/."""
    repo = temp_git_repo
    new_ts_file = repo / "trading_system" / "src" / "new_strategy.py"
    new_src_file = repo / "src" / "new_strategy.py"

    new_ts_file.write_text("class AlphaStrategy:\n    pass\n", encoding="utf-8")
    subprocess.run(["git", "add", "trading_system/src/new_strategy.py"], cwd=repo, check=True)

    ret = hook_sync_and_verify(repo_root=repo, auto_mirror=True)
    assert ret == 0

    assert new_src_file.is_file()
    assert new_src_file.read_text(encoding="utf-8") == "class AlphaStrategy:\n    pass\n"

    staged_diff = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    assert "src/new_strategy.py" in staged_diff
    assert "trading_system/src/new_strategy.py" in staged_diff


def test_hook_bilateral_conflict_aborts_commit(temp_git_repo: Path):
    """TC-10c: Tests conflicting bilateral edits abort with code 1 and prevent commit."""
    repo = temp_git_repo
    src_file = repo / "src" / "base.py"
    ts_file = repo / "trading_system" / "src" / "base.py"

    src_file.write_text("conflict_a = True\n", encoding="utf-8")
    ts_file.write_text("conflict_b = True\n", encoding="utf-8")

    subprocess.run(["git", "add", "src/base.py", "trading_system/src/base.py"], cwd=repo, check=True)

    ret = hook_sync_and_verify(repo_root=repo, auto_mirror=True)
    assert ret == 1, "Expected hook to abort on bilateral conflict"

    # Verify disk files were NOT blindly overwritten
    assert src_file.read_text(encoding="utf-8") == "conflict_a = True\n"
    assert ts_file.read_text(encoding="utf-8") == "conflict_b = True\n"


def test_hook_check_only_mode_blocks_unilateral(temp_git_repo: Path):
    """TC-10d: Tests check-only mode fails when a file is staged without its mirror."""
    repo = temp_git_repo
    src_file = repo / "src" / "base.py"
    src_file.write_text("unmirrored = True\n", encoding="utf-8")
    subprocess.run(["git", "add", "src/base.py"], cwd=repo, check=True)

    ret = hook_sync_and_verify(repo_root=repo, auto_mirror=False)
    assert ret == 1

    # Verify mirror was NOT created
    ts_file = repo / "trading_system" / "src" / "base.py"
    assert "unmirrored" not in ts_file.read_text(encoding="utf-8")


def test_hook_fast_path_non_monitored_files(temp_git_repo: Path):
    """TC-10e: Tests fast path: commits touching only docs/ exit 0 immediately."""
    repo = temp_git_repo
    docs_file = repo / "README.md"
    docs_file.write_text("# Documentation\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)

    t0 = time.perf_counter()
    ret = hook_sync_and_verify(repo_root=repo, auto_mirror=True)
    duration = time.perf_counter() - t0

    assert ret == 0
    assert duration < 5.0  # Fast path should complete rapidly without tree scans


# ==============================================================================
# 6. Hook Installation Script Tests
# ==============================================================================

def test_install_hooks_script(temp_git_repo: Path):
    """TC-11: Tests install_hooks.py properly sets core.hooksPath and copies fallback."""
    repo = temp_git_repo
    installer = REPO_ROOT / "scripts" / "hooks" / "install_hooks.py"

    cmd = [sys.executable, str(installer)]
    res = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
    assert res.returncode == 0
    assert "[OK]" in res.stdout

    # Verify git config core.hooksPath
    hooks_path = subprocess.run(
        ["git", "config", "core.hooksPath"],
        cwd=repo,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert hooks_path == ".githooks"

    # Verify fallback copy
    fallback_hook = repo / ".git" / "hooks" / "pre-commit"
    assert fallback_hook.is_file()


# ==============================================================================
# 7. Milestone 1 Hardening Tests: Partial Staging, DUAL_TREE_MODE & Renames
# ==============================================================================

def test_hook_partial_staged_edits_rejected(temp_git_repo: Path):
    """
    TC-12: Asserts that partial staged edits (working tree differs from staged index)
    are rejected with exit code 1 to prevent silent desynchronization in Git HEAD.
    """
    repo = temp_git_repo
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=repo, check=True)

    src_file = repo / "src" / "base.py"
    ts_file = repo / "trading_system" / "src" / "base.py"

    # Step 1: Stage version 1 in src/base.py
    src_file.write_text("def base():\n    return 'staged_v1'\n", encoding="utf-8")
    subprocess.run(["git", "add", "src/base.py"], cwd=repo, check=True)

    # Step 2: Introduce unstaged modification in working tree (version 2)
    src_file.write_text("def base():\n    return 'unstaged_v2'\n", encoding="utf-8")

    # Step 3: Run pre-commit hook directly
    ret = hook_sync_and_verify(repo_root=repo, auto_mirror=True)
    assert ret == 1, "Hook must abort with exit code 1 when working tree differs from staged index"

    # Step 4: Verify target tree file was NOT modified or corrupted with unstaged v2
    assert ts_file.read_text(encoding="utf-8") == "def base():\n    return 42\n"

    # Step 5: Verify git index for target tree was NOT staged
    staged_files = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert "trading_system/src/base.py" not in staged_files

    # Step 6: Verify git commit is blocked end-to-end
    res = subprocess.run(
        ["git", "commit", "-m", "Attempt partial commit"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0, "git commit must fail when hook rejects partial staged edits"
    assert "unstaged working tree changes that differ from the staged index" in res.stderr

    # Step 7: Verify HEAD remains untouched
    head_src = subprocess.run(
        ["git", "show", "HEAD:src/base.py"],
        cwd=repo,
        capture_output=True,
        text=True,
    ).stdout
    head_ts = subprocess.run(
        ["git", "show", "HEAD:trading_system/src/base.py"],
        cwd=repo,
        capture_output=True,
        text=True,
    ).stdout
    assert "42" in head_src
    assert "42" in head_ts

    # Step 8: Symmetric verification in trading_system/src/
    subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=repo, check=True)
    ts_file.write_text("def base():\n    return 'ts_staged_v1'\n", encoding="utf-8")
    subprocess.run(["git", "add", "trading_system/src/base.py"], cwd=repo, check=True)
    ts_file.write_text("def base():\n    return 'ts_unstaged_v2'\n", encoding="utf-8")

    ret_sym = hook_sync_and_verify(repo_root=repo, auto_mirror=True)
    assert ret_sym == 1, "Hook must abort for unstaged changes in trading_system/src/"


def test_hook_dual_tree_mode_env_check(temp_git_repo: Path, monkeypatch: pytest.MonkeyPatch):
    """
    TC-13: Asserts that setting environment variable DUAL_TREE_MODE=check
    blocks commits on unilateral edits without modifying the target tree.
    """
    repo = temp_git_repo
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=repo, check=True)

    src_file = repo / "src" / "base.py"
    ts_file = repo / "trading_system" / "src" / "base.py"

    # Stage a clean unilateral edit
    src_file.write_text("def base():\n    return 'unilateral_edit'\n", encoding="utf-8")
    subprocess.run(["git", "add", "src/base.py"], cwd=repo, check=True)

    # Subtest 1: DUAL_TREE_MODE=check in Python call
    monkeypatch.setenv("DUAL_TREE_MODE", "check")
    ret = hook_sync_and_verify(repo_root=repo)
    assert ret == 1, "Hook must block when DUAL_TREE_MODE=check"
    assert ts_file.read_text(encoding="utf-8") == "def base():\n    return 42\n"

    # Subtest 2: DUAL_TREE_MODE=CHECK (case-insensitivity) via CLI git commit
    custom_env = os.environ.copy()
    custom_env["DUAL_TREE_MODE"] = "CHECK"
    res = subprocess.run(
        ["git", "commit", "-m", "Check mode test"],
        cwd=repo,
        env=custom_env,
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0, "git commit must be blocked by pre-commit hook"
    assert "was staged without mirror" in res.stderr
    assert "(check-only mode)" in res.stderr

    # Assert target file was NOT modified on disk or staged in git index
    assert ts_file.read_text(encoding="utf-8") == "def base():\n    return 42\n"
    staged_files = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert "trading_system/src/base.py" not in staged_files

    # Subtest 3: Unset DUAL_TREE_MODE allows commit to succeed with auto-mirroring
    monkeypatch.delenv("DUAL_TREE_MODE", raising=False)
    custom_env.pop("DUAL_TREE_MODE", None)
    res_success = subprocess.run(
        ["git", "commit", "-m", "Unset mode test with auto-mirror"],
        cwd=repo,
        env=custom_env,
        capture_output=True,
        text=True,
    )
    assert res_success.returncode == 0, f"git commit should succeed when DUAL_TREE_MODE is unset: {res_success.stderr}"
    assert ts_file.read_text(encoding="utf-8") == "def base():\n    return 'unilateral_edit'\n"


def test_hook_git_mv_rename_auto_mirrors(temp_git_repo: Path):
    """
    TC-14: Asserts that renaming a file via `git mv` in `src/` cleanly
    auto-mirrors the rename to `trading_system/src/`, removing old path
    and adding new path with 100% cryptographic parity.
    """
    repo = temp_git_repo
    src_dir = repo / "src"
    ts_dir = repo / "trading_system" / "src"

    # Setup initial committed nested file
    nested_src = src_dir / "pkg" / "component.py"
    nested_ts = ts_dir / "pkg" / "component.py"
    nested_src.parent.mkdir(parents=True, exist_ok=True)
    nested_ts.parent.mkdir(parents=True, exist_ok=True)

    nested_code = "class Component:\n    version = 1\n"
    nested_src.write_text(nested_code, encoding="utf-8")
    nested_ts.write_text(nested_code, encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add nested component"], cwd=repo, check=True)

    # Subtest 1: git mv on top-level file: src/base.py -> src/renamed_base.py
    subprocess.run(["git", "mv", "src/base.py", "src/renamed_base.py"], cwd=repo, check=True)

    ret1 = hook_sync_and_verify(repo_root=repo, auto_mirror=True)
    assert ret1 == 0, "Hook should cleanly mirror top-level rename"

    # Check on-disk state
    assert (src_dir / "renamed_base.py").is_file()
    assert not (src_dir / "base.py").exists()
    assert (ts_dir / "renamed_base.py").is_file()
    assert not (ts_dir / "base.py").exists()

    subprocess.run(["git", "commit", "-m", "Commit top-level rename"], cwd=repo, check=True)

    blob_src = subprocess.run(["git", "show", "HEAD:src/renamed_base.py"], cwd=repo, capture_output=True, check=True).stdout
    blob_ts = subprocess.run(["git", "show", "HEAD:trading_system/src/renamed_base.py"], cwd=repo, capture_output=True, check=True).stdout
    assert blob_src == blob_ts

    # Subtest 2: git mv on nested file: trading_system/src/pkg/component.py -> trading_system/src/pkg/new_comp.py
    subprocess.run(
        ["git", "mv", "trading_system/src/pkg/component.py", "trading_system/src/pkg/new_comp.py"],
        cwd=repo,
        check=True,
    )

    ret2 = hook_sync_and_verify(repo_root=repo, auto_mirror=True)
    assert ret2 == 0, "Hook should cleanly mirror reverse nested rename"

    assert (ts_dir / "pkg" / "new_comp.py").is_file()
    assert not (ts_dir / "pkg" / "component.py").exists()
    assert (src_dir / "pkg" / "new_comp.py").is_file()
    assert not (src_dir / "pkg" / "component.py").exists()

    subprocess.run(["git", "commit", "-m", "Commit nested reverse rename"], cwd=repo, check=True)

    # Final parity assertion across both trees
    report = compare_trees(src_dir, ts_dir, python_only=True)
    assert report.passed is True
    assert report.mismatched_count == 0
    assert report.only_in_src_count == 0
    assert report.only_in_target_count == 0

