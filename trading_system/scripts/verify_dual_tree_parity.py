#!/usr/bin/env python3
"""
scripts/verify_dual_tree_parity.py
Cryptographic SHA-256 Dual-Tree Parity Verifier & Bidirectional Synchronizer.

Verifies and maintains 100% bit-for-bit cryptographic parity between
root `src/` and `trading_system/src/` across the stock trading platform.

Exit codes:
  0: Parity holds (and in --strict mode, file count >= min-files threshold).
  1: Parity failure (content mismatch, missing files, or strict threshold not met).
  2: CLI argument or system/IO error.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import shutil
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Ignore directories and file patterns that are build/runtime caches or IDE artifacts
IGNORED_DIRS: Set[str] = {
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".idea",
    ".vscode",
    ".tox",
    "build",
    "dist",
}

IGNORED_EXTENSIONS: Set[str] = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".tmp",
    ".swp",
    ".bak",
}

IGNORED_FILENAMES: Set[str] = {
    ".DS_Store",
    "Thumbs.db",
}

DEFAULT_MIN_FILES: int = 328


@dataclass
class FileHashMeta:
    rel_path: str
    sha256: str
    size_bytes: int
    mtime_ns: int
    full_path: str


@dataclass
class MismatchDetail:
    rel_path: str
    src_sha256: str
    target_sha256: str
    src_size: int
    target_size: int
    src_mtime_ns: int
    target_mtime_ns: int
    diff_snippet: Optional[str] = None


@dataclass
class ParityReport:
    timestamp: str
    src_dir: str
    target_dir: str
    python_only: bool
    strict: bool
    min_files: int
    total_src_files: int
    total_target_files: int
    common_files_count: int
    identical_count: int
    mismatched_count: int
    only_in_src_count: int
    only_in_target_count: int
    passed: bool
    scan_duration_sec: float
    mismatches: List[MismatchDetail] = field(default_factory=list)
    only_in_src: List[str] = field(default_factory=list)
    only_in_target: List[str] = field(default_factory=list)
    failure_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_sha256(path: Path, chunk_size: int = 65536) -> str:
    """Computes SHA-256 digest of a file reading in chunks."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def find_repo_root(start_path: Optional[Path] = None) -> Path:
    """
    Locates repository root by searching upward for directories containing
    both `src` and `trading_system/src` or a `.git` marker.
    """
    current = (start_path or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent

    for candidate in [current, *current.parents]:
        has_src = (candidate / "src").is_dir()
        has_ts = (candidate / "trading_system" / "src").is_dir()
        if has_src and has_ts:
            return candidate
        if (candidate / ".git").exists():
            return candidate

    return Path.cwd().resolve()


def scan_tree(
    base_dir: Path,
    python_only: bool = True,
) -> Dict[str, FileHashMeta]:
    """
    Scans a directory tree and returns a mapping from POSIX relative path
    to FileHashMeta containing SHA-256 digest, file size, and mtime.
    """
    result: Dict[str, FileHashMeta] = {}
    base_dir = base_dir.resolve()
    if not base_dir.is_dir():
        raise FileNotFoundError(f"Directory does not exist or is not a directory: {base_dir}")

    for root, dirs, files in os.walk(base_dir):
        # In-place directory filtering
        dirs[:] = [
            d for d in dirs
            if d not in IGNORED_DIRS and not d.startswith(".") and not d.endswith("_cache")
        ]

        for filename in files:
            if filename in IGNORED_FILENAMES or filename.startswith("."):
                continue
            ext = os.path.splitext(filename)[1].lower()
            if ext in IGNORED_EXTENSIONS:
                continue
            if python_only and ext != ".py":
                continue

            full_path = Path(root) / filename
            try:
                rel_posix = full_path.relative_to(base_dir).as_posix()
                st = full_path.stat()
                digest = compute_sha256(full_path)
                result[rel_posix] = FileHashMeta(
                    rel_path=rel_posix,
                    sha256=digest,
                    size_bytes=st.st_size,
                    mtime_ns=st.st_mtime_ns,
                    full_path=str(full_path),
                )
            except OSError as exc:
                print(f"[WARN] Failed to read {full_path}: {exc}", file=sys.stderr)

    return result


def compare_trees(
    src_dir: Path,
    target_dir: Path,
    python_only: bool = True,
    strict: bool = False,
    min_files: int = DEFAULT_MIN_FILES,
    generate_diffs: bool = False,
    diff_max_lines: int = 50,
) -> ParityReport:
    """
    Compares two filesystem trees symmetrically and produces a comprehensive ParityReport.
    """
    t0 = time.perf_counter()
    src_files = scan_tree(src_dir, python_only=python_only)
    target_files = scan_tree(target_dir, python_only=python_only)
    t1 = time.perf_counter()

    src_keys = set(src_files.keys())
    target_keys = set(target_files.keys())

    only_in_src = sorted(list(src_keys - target_keys))
    only_in_target = sorted(list(target_keys - src_keys))
    common_keys = sorted(list(src_keys & target_keys))

    identical = 0
    mismatches: List[MismatchDetail] = []

    for k in common_keys:
        meta_src = src_files[k]
        meta_target = target_files[k]
        if meta_src.sha256 == meta_target.sha256:
            identical += 1
        else:
            diff_text = None
            if generate_diffs:
                try:
                    src_lines = Path(meta_src.full_path).read_text(
                        encoding="utf-8", errors="replace"
                    ).splitlines()
                    target_lines = Path(meta_target.full_path).read_text(
                        encoding="utf-8", errors="replace"
                    ).splitlines()
                    diff = list(
                        difflib.unified_diff(
                            src_lines,
                            target_lines,
                            fromfile=f"src/{k}",
                            tofile=f"trading_system/src/{k}",
                            lineterm="",
                        )
                    )
                    if diff:
                        diff_text = "\n".join(diff[:diff_max_lines])
                        if len(diff) > diff_max_lines:
                            diff_text += f"\n... [diff truncated after {diff_max_lines} lines]"
                except Exception as exc:
                    diff_text = f"[Unable to generate diff: {exc}]"

            mismatches.append(
                MismatchDetail(
                    rel_path=k,
                    src_sha256=meta_src.sha256,
                    target_sha256=meta_target.sha256,
                    src_size=meta_src.size_bytes,
                    target_size=meta_target.size_bytes,
                    src_mtime_ns=meta_src.mtime_ns,
                    target_mtime_ns=meta_target.mtime_ns,
                    diff_snippet=diff_text,
                )
            )

    failure_reasons: List[str] = []
    if len(mismatches) > 0:
        failure_reasons.append(f"{len(mismatches)} files have mismatched SHA-256 hashes")
    if len(only_in_src) > 0:
        failure_reasons.append(f"{len(only_in_src)} files exist only in {src_dir}")
    if len(only_in_target) > 0:
        failure_reasons.append(f"{len(only_in_target)} files exist only in {target_dir}")

    passed = (len(mismatches) == 0) and (len(only_in_src) == 0) and (len(only_in_target) == 0)

    if strict:
        if identical < min_files:
            passed = False
            failure_reasons.append(
                f"Strict threshold violation: identical file count {identical} < required {min_files}"
            )

    return ParityReport(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        src_dir=str(src_dir),
        target_dir=str(target_dir),
        python_only=python_only,
        strict=strict,
        min_files=min_files,
        total_src_files=len(src_files),
        total_target_files=len(target_files),
        common_files_count=len(common_keys),
        identical_count=identical,
        mismatched_count=len(mismatches),
        only_in_src_count=len(only_in_src),
        only_in_target_count=len(only_in_target),
        passed=passed,
        scan_duration_sec=t1 - t0,
        mismatches=mismatches,
        only_in_src=only_in_src,
        only_in_target=only_in_target,
        failure_reasons=failure_reasons,
    )


def sync_trees(
    src_dir: Path,
    target_dir: Path,
    direction: str = "newest",
    python_only: bool = True,
    dry_run: bool = False,
) -> Tuple[int, int]:
    """
    Synchronizes files between src_dir and target_dir.
    Directions:
      - 'newest': whichever side has a strictly newer mtime overwrites the other. Missing files copied.
      - 'src-to-ts': src overwrites target. Missing in target copied from src.
      - 'ts-to-src': target overwrites src. Missing in src copied from target.
    Returns (copied_count, overwritten_count).
    """
    src_files = scan_tree(src_dir, python_only=python_only)
    target_files = scan_tree(target_dir, python_only=python_only)

    copied = 0
    overwritten = 0

    src_keys = set(src_files.keys())
    target_keys = set(target_files.keys())
    all_keys = sorted(list(src_keys | target_keys))

    for k in all_keys:
        in_src = k in src_files
        in_target = k in target_files

        src_path = src_dir / k
        target_path = target_dir / k

        if in_src and not in_target:
            if direction in ("newest", "src-to-ts"):
                if not dry_run:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, target_path)
                copied += 1
            elif direction == "ts-to-src":
                # In ts-to-src, missing in target means we don't copy
                pass
        elif in_target and not in_src:
            if direction in ("newest", "ts-to-src"):
                if not dry_run:
                    src_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target_path, src_path)
                copied += 1
            elif direction == "src-to-ts":
                pass
        else:
            # Both exist; check if SHA-256 differs
            if src_files[k].sha256 != target_files[k].sha256:
                if direction == "src-to-ts":
                    source, dest = src_path, target_path
                elif direction == "ts-to-src":
                    source, dest = target_path, src_path
                else:  # newest
                    if src_files[k].mtime_ns >= target_files[k].mtime_ns:
                        source, dest = src_path, target_path
                    else:
                        source, dest = target_path, src_path

                if not dry_run:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
                overwritten += 1

    return copied, overwritten


def emit_github_annotations(report: ParityReport) -> None:
    """Emits GitHub Actions ::error workflow command annotations."""
    for m in report.mismatches:
        msg = (
            f"SHA-256 Parity Mismatch: src/{m.rel_path} ({m.src_sha256[:8]}...) != "
            f"trading_system/src/{m.rel_path} ({m.target_sha256[:8]}...)"
        )
        print(f"::error file=src/{m.rel_path}::{msg}")

    for s in report.only_in_src:
        print(f"::error file=src/{s}::File exists only in src/, missing in trading_system/src/")

    for t in report.only_in_target:
        print(f"::error file=trading_system/src/{t}::File exists only in trading_system/src/, missing in src/")

    for reason in report.failure_reasons:
        if "Strict threshold violation" in reason:
            print(f"::error ::{reason}")


def write_github_step_summary(report: ParityReport, summary_file: Path) -> None:
    """Appends Markdown step summary to GitHub Actions summary file."""
    status_icon = "✅ PASS" if report.passed else "❌ FAIL"
    md = [
        "## 🔒 Dual-Tree Cryptographic Parity Verification Report",
        "",
        f"**Status**: {status_icon} | **Duration**: {report.scan_duration_sec:.4f}s | **Timestamp**: `{report.timestamp}`",
        "",
        "| Metric | Count | Evaluation |",
        "| :--- | :---: | :---: |",
        f"| Source Tree (`{report.src_dir}`) Files | {report.total_src_files} | ℹ️ Scanned |",
        f"| Target Tree (`{report.target_dir}`) Files | {report.total_target_files} | ℹ️ Scanned |",
        f"| Identical (100% Bit-for-Bit SHA-256 Match) | {report.identical_count} | {'✅' if report.identical_count >= report.min_files else '⚠️'} |",
        f"| Content Mismatches | {report.mismatched_count} | {'✅ 0' if report.mismatched_count == 0 else '❌ ' + str(report.mismatched_count)} |",
        f"| Only in Source (`{report.src_dir}`) | {report.only_in_src_count} | {'✅ 0' if report.only_in_src_count == 0 else '❌ ' + str(report.only_in_src_count)} |",
        f"| Only in Target (`{report.target_dir}`) | {report.only_in_target_count} | {'✅ 0' if report.only_in_target_count == 0 else '❌ ' + str(report.only_in_target_count)} |",
        "",
    ]

    if report.mismatches:
        md.append("### ❌ Mismatched Files")
        md.append("| File | `src/` SHA-256 | `trading_system/src/` SHA-256 |")
        md.append("| :--- | :---: | :---: |")
        for m in report.mismatches:
            md.append(f"| `{m.rel_path}` | `{m.src_sha256[:12]}...` | `{m.target_sha256[:12]}...` |")
        md.append("")

    if report.only_in_src:
        md.append(f"### ⚠️ Missing in `{report.target_dir}`")
        for s in report.only_in_src:
            md.append(f"- `{s}`")
        md.append("")

    if report.only_in_target:
        md.append(f"### ⚠️ Missing in `{report.src_dir}`")
        for t in report.only_in_target:
            md.append(f"- `{t}`")
        md.append("")

    try:
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write("\n".join(md) + "\n")
    except OSError as exc:
        print(f"[WARN] Could not write to GITHUB_STEP_SUMMARY: {exc}", file=sys.stderr)


def parse_arguments(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dual-Tree Cryptographic Parity Guard & Bidirectional Synchronizer"
    )

    # Core Modes
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--check",
        action="store_true",
        default=True,
        help="Validate parity and exit with 0 (pass) or 1 (fail). [Default mode]",
    )
    mode_group.add_argument(
        "--sync",
        action="store_true",
        help="Synchronize divergent and missing files between trees.",
    )

    # Filtering & Thresholds
    parser.add_argument(
        "--strict",
        action="store_true",
        help=f"Assert identical count >= min-files (default {DEFAULT_MIN_FILES}) and 0 mismatches/missing.",
    )
    parser.add_argument(
        "--min-files",
        type=int,
        default=DEFAULT_MIN_FILES,
        help=f"Minimum files threshold for strict validation (default: {DEFAULT_MIN_FILES}).",
    )
    filter_group = parser.add_mutually_exclusive_group()
    filter_group.add_argument(
        "--python-only",
        action="store_true",
        default=True,
        help="Only evaluate .py files (default: True).",
    )
    filter_group.add_argument(
        "--all-files",
        action="store_false",
        dest="python_only",
        help="Evaluate all files (including .css and assets).",
    )

    # Diff & Reporting
    parser.add_argument(
        "--diff",
        "--generate-diffs",
        action="store_true",
        dest="generate_diffs",
        help="Generate and display unified diffs for mismatched files.",
    )
    parser.add_argument(
        "--diff-max-lines",
        type=int,
        default=50,
        help="Maximum diff lines per mismatched file (default: 50).",
    )
    parser.add_argument(
        "--diff-output",
        type=str,
        default=None,
        help="Optional path to write full unified patch file (e.g. parity_diff.patch).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON parity report to stdout.",
    )
    parser.add_argument(
        "--json-output",
        type=str,
        default=None,
        help="Path to write JSON parity report file.",
    )

    # Sync Configuration
    parser.add_argument(
        "--direction",
        choices=["newest", "src-to-ts", "ts-to-src"],
        default="newest",
        help="Synchronization direction: newest (mtime), src-to-ts, or ts-to-src.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate synchronization without modifying files on disk.",
    )

    # Paths
    parser.add_argument(
        "--root-dir",
        type=str,
        default=None,
        help="Root repository directory (auto-detected if omitted).",
    )
    parser.add_argument(
        "--src-dir",
        type=str,
        default="src",
        help="Path to source tree relative to root-dir or absolute (default: 'src').",
    )
    parser.add_argument(
        "--target-dir",
        type=str,
        default="trading_system/src",
        help="Path to target tree relative to root-dir or absolute (default: 'trading_system/src').",
    )

    # CI & Telemetry
    parser.add_argument(
        "--gh-annotations",
        action="store_true",
        help="Emit GitHub Actions ::error annotations on failure.",
    )
    parser.add_argument(
        "--step-summary",
        "--github-summary",
        action="store_true",
        dest="step_summary",
        help="Append Markdown summary table to $GITHUB_STEP_SUMMARY.",
    )

    # Verbosity
    verb_group = parser.add_mutually_exclusive_group()
    verb_group.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress non-essential stdout output.",
    )
    verb_group.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print verbose details of all verified files.",
    )

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    try:
        args = parse_arguments(argv)
    except SystemExit as exc:
        return 2 if exc.code != 0 else 0
    except Exception as exc:
        print(f"[CLI ERROR] Argument parsing failed: {exc}", file=sys.stderr)
        return 2

    # Resolve paths
    repo_root = find_repo_root(Path(args.root_dir) if args.root_dir else None)
    src_dir = (Path(args.src_dir) if Path(args.src_dir).is_absolute() else repo_root / args.src_dir).resolve()
    target_dir = (Path(args.target_dir) if Path(args.target_dir).is_absolute() else repo_root / args.target_dir).resolve()

    if not src_dir.is_dir():
        print(f"[SYSTEM ERROR] Source directory not found: {src_dir}", file=sys.stderr)
        return 2
    if not target_dir.is_dir():
        print(f"[SYSTEM ERROR] Target directory not found: {target_dir}", file=sys.stderr)
        return 2

    # If --sync mode is requested
    if args.sync:
        if not args.quiet:
            print(f"[SYNC] Synchronizing: {src_dir} <-> {target_dir} (direction={args.direction}, dry_run={args.dry_run})")
        try:
            copied, overwritten = sync_trees(
                src_dir=src_dir,
                target_dir=target_dir,
                direction=args.direction,
                python_only=args.python_only,
                dry_run=args.dry_run,
            )
            if not args.quiet:
                print(f"[SYNC COMPLETE] Copied new files: {copied}, Overwritten mismatched: {overwritten}")
        except Exception as exc:
            print(f"[SYSTEM ERROR] Sync failed: {exc}", file=sys.stderr)
            return 2

    # Perform Parity Check
    try:
        report = compare_trees(
            src_dir=src_dir,
            target_dir=target_dir,
            python_only=args.python_only,
            strict=args.strict,
            min_files=args.min_files,
            generate_diffs=args.generate_diffs,
            diff_max_lines=args.diff_max_lines,
        )
    except Exception as exc:
        print(f"[SYSTEM ERROR] Verification failed: {exc}", file=sys.stderr)
        return 2

    # Generate Patch File if requested
    if args.diff_output and report.mismatches:
        try:
            patches = []
            for m in report.mismatches:
                if m.diff_snippet:
                    patches.append(m.diff_snippet)
            if patches:
                Path(args.diff_output).write_text("\n\n".join(patches) + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"[WARN] Failed to write diff output: {exc}", file=sys.stderr)

    # Output JSON report if requested
    if args.json_output:
        try:
            Path(args.json_output).parent.mkdir(parents=True, exist_ok=True)
            with open(args.json_output, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2)
        except OSError as exc:
            print(f"[WARN] Failed to write json output: {exc}", file=sys.stderr)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))

    # GitHub Actions Annotations
    in_gh_actions = (os.environ.get("GITHUB_ACTIONS") == "true")
    if args.gh_annotations or (in_gh_actions and not report.passed):
        emit_github_annotations(report)

    # GitHub Step Summary
    summary_env = os.environ.get("GITHUB_STEP_SUMMARY")
    if args.step_summary or (in_gh_actions and summary_env):
        if summary_env:
            write_github_step_summary(report, Path(summary_env))

    # Human-readable stdout output
    if not args.quiet and not args.json:
        status_str = "PASS" if report.passed else "FAIL"
        print("================================================================================")
        print("                   DUAL-TREE CRYPTOGRAPHIC PARITY REPORT                        ")
        print("================================================================================")
        print(f" Status:                     {status_str}")
        print(f" Source Directory:           {report.src_dir}")
        print(f" Target Directory:           {report.target_dir}")
        print(f" Filter Mode:                {'Python Files Only (.py)' if report.python_only else 'All Files'}")
        print(f" Strict Mode:                {report.strict} (min_files={report.min_files})")
        print(f" Scan Duration:              {report.scan_duration_sec:.4f}s")
        print(f" Total Source Files:         {report.total_src_files}")
        print(f" Total Target Files:         {report.total_target_files}")
        print(f" Identical (100% SHA-256):   {report.identical_count}")
        print(f" Content Mismatches:         {report.mismatched_count}")
        print(f" Only in Source:             {report.only_in_src_count}")
        print(f" Only in Target:             {report.only_in_target_count}")
        print("================================================================================")

        if args.verbose:
            print("[VERBOSE] Files verified identically:")
            src_files = scan_tree(src_dir, python_only=args.python_only)
            for rel_k in sorted(src_files.keys()):
                if rel_k not in report.only_in_src and rel_k not in [m.rel_path for m in report.mismatches]:
                    print(f"  OK: {rel_k} -> {src_files[rel_k].sha256[:16]}...")

        if report.mismatches:
            print("\n[MISMATCHES]")
            for m in report.mismatches:
                print(f"  * {m.rel_path}:")
                print(f"      src SHA-256:    {m.src_sha256} ({m.src_size} bytes)")
                print(f"      target SHA-256: {m.target_sha256} ({m.target_size} bytes)")
                if m.diff_snippet:
                    print("      --- Unified Diff Snippet ---")
                    for line in m.diff_snippet.splitlines()[:15]:
                        print(f"      {line}")

        if report.only_in_src:
            print(f"\n[ONLY IN SOURCE: {report.src_dir}]")
            for s in report.only_in_src:
                print(f"  + {s}")

        if report.only_in_target:
            print(f"\n[ONLY IN TARGET: {report.target_dir}]")
            for t in report.only_in_target:
                print(f"  + {t}")

        if report.failure_reasons:
            print("\n[FAILURE REASONS]")
            for r in report.failure_reasons:
                print(f"  ! {r}")

        print("================================================================================")

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
