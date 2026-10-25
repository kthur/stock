#!/usr/bin/env python3
"""
scripts/hooks/pre-commit-dual-tree-sync.py
Git Pre-Commit Hook: Staging-Aware Dual-Tree Synchronizer & Parity Guard.

Inspects the Git staged index (via `git diff --cached --name-status`),
detects unilateral edits in either `src/` or `trading_system/src/`,
auto-mirrors the staged changes to the sibling tree, stages the mirrored
files (`git add`), catches bilateral conflicting edits, and executes the
full cryptographic parity verification before allowing the commit.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

SRC_PREFIX = "src/"
TS_PREFIX = "trading_system/src/"


def get_repo_root() -> Path:
    """Finds repository root using git rev-parse or fallback to current dir."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(res.stdout.strip()).resolve()
    except Exception:
        # Fallback to directory structure
        candidate = Path(__file__).resolve().parent.parent.parent
        if (candidate / "src").is_dir() and (candidate / "trading_system").is_dir():
            return candidate
        return Path.cwd().resolve()


def get_staged_changes(repo_root: Path) -> List[Tuple[str, str]]:
    """
    Returns a list of (status, file_path_posix) for all files staged in the index.
    Uses -z to handle spaces and special characters safely.
    """
    res = subprocess.run(
        ["git", "diff", "--cached", "--name-status", "-z"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    raw = res.stdout
    if not raw:
        return []

    tokens = raw.split(b"\0")
    changes: List[Tuple[str, str]] = []
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        if not token:
            idx += 1
            continue
        status = token.decode("utf-8", errors="replace")
        idx += 1
        if idx >= len(tokens):
            break

        if status.startswith("R"):
            # Rename has two paths: old_path (removed) and new_path (added)
            if idx + 1 >= len(tokens):
                break
            old_path = tokens[idx].decode("utf-8", errors="replace")
            idx += 1
            new_path = tokens[idx].decode("utf-8", errors="replace")
            idx += 1
            changes.append(("D", Path(old_path).as_posix()))
            changes.append(("A", Path(new_path).as_posix()))
        elif status.startswith("C"):
            # Copy has two paths: source old_path (unchanged) and target new_path (added)
            if idx + 1 >= len(tokens):
                break
            _old_path = tokens[idx].decode("utf-8", errors="replace")
            idx += 1
            new_path = tokens[idx].decode("utf-8", errors="replace")
            idx += 1
            changes.append(("A", Path(new_path).as_posix()))
        else:
            path_str = tokens[idx].decode("utf-8", errors="replace")
            idx += 1
            changes.append((status[0], Path(path_str).as_posix()))

    return changes


def get_unstaged_changed_files(repo_root: Path) -> Set[str]:
    """
    Returns the set of POSIX relative file paths with unstaged modifications or
    deletions in the working tree relative to the git index.
    Uses `git diff-files -z --name-only`, which respects Git filters and CRLF normalization.
    """
    try:
        res = subprocess.run(
            ["git", "diff-files", "-z", "--name-only"],
            cwd=repo_root,
            capture_output=True,
            check=True,
        )
        if not res.stdout:
            return set()
        return {
            Path(p.decode("utf-8", errors="replace")).as_posix()
            for p in res.stdout.split(b"\0")
            if p
        }
    except Exception:
        return set()


def get_staged_blob(repo_root: Path, file_path_posix: str) -> Optional[bytes]:
    """Retrieves staged blob bytes directly from git index :0:<path>."""
    res = subprocess.run(
        ["git", "show", f":0:{file_path_posix}"],
        cwd=repo_root,
        capture_output=True,
    )
    if res.returncode == 0:
        return res.stdout
    return None


def run_git_add(repo_root: Path, file_path_posix: str) -> None:
    """Stages a modified or newly created file into the git index."""
    subprocess.run(["git", "add", file_path_posix], cwd=repo_root, check=True)


def run_git_rm_cached(repo_root: Path, file_path_posix: str) -> None:
    """Removes a deleted file from the git index."""
    subprocess.run(
        ["git", "rm", "--cached", "--ignore-unmatch", file_path_posix],
        cwd=repo_root,
        capture_output=True,
    )


def is_monitored_file(rel_path: str) -> bool:
    """Determines if the relative file should be monitored for dual-tree parity."""
    if "__pycache__" in rel_path or rel_path.endswith((".pyc", ".pyo", ".tmp", ".swp")):
        return False
    return True


def synchronize_and_verify(
    repo_root: Path,
    auto_mirror: bool = True,
    quiet: bool = False,
) -> int:
    """
    Inspects staged files, auto-mirrors unilateral edits, stages mirrored files,
    aborts on bilateral conflicts, and executes dual-tree verification.
    """
    env_mode = os.environ.get("DUAL_TREE_MODE", "").strip().lower()
    if env_mode == "check":
        auto_mirror = False

    staged_changes = get_staged_changes(repo_root)

    # Filter for changes touching src/ or trading_system/src/
    src_touched: Dict[str, str] = {}  # rel_subpath -> status ('M', 'A', 'D', etc.)
    ts_touched: Dict[str, str] = {}

    for status, path in staged_changes:
        if path.startswith(SRC_PREFIX):
            rel = path[len(SRC_PREFIX):]
            if is_monitored_file(rel):
                src_touched[rel] = status
        elif path.startswith(TS_PREFIX):
            rel = path[len(TS_PREFIX):]
            if is_monitored_file(rel):
                ts_touched[rel] = status

    # Fast path: if neither tree is touched, exit 0 immediately
    if not src_touched and not ts_touched:
        return 0

    all_touched_rel = sorted(list(set(src_touched.keys()) | set(ts_touched.keys())))

    # Guard against unstaged working tree changes in monitored files
    unstaged_files = get_unstaged_changed_files(repo_root)
    dirty_staged_files: List[str] = []

    for rel in all_touched_rel:
        src_full = f"{SRC_PREFIX}{rel}"
        ts_full = f"{TS_PREFIX}{rel}"

        if rel in src_touched:
            if src_full in unstaged_files:
                dirty_staged_files.append(src_full)
            elif src_touched[rel] == "D" and (repo_root / src_full).exists():
                dirty_staged_files.append(src_full)

        if rel in ts_touched:
            if ts_full in unstaged_files:
                dirty_staged_files.append(ts_full)
            elif ts_touched[rel] == "D" and (repo_root / ts_full).exists():
                dirty_staged_files.append(ts_full)

    if dirty_staged_files:
        print(
            "\n[PRE-COMMIT ERROR] Monitored file(s) have unstaged working tree changes that differ from the staged index:",
            file=sys.stderr,
        )
        for dirty_path in sorted(set(dirty_staged_files)):
            print(f"  * {dirty_path}", file=sys.stderr)
        print(
            "\nDual-Tree cryptographic parity requires staged files to be cleanly synchronized with the working tree.\n"
            "To resolve this issue:\n"
            "  1. Stage all changes:    git add <file>\n"
            "  2. Or stash unstaged:    git stash --keep-index\n"
            "  3. Then re-run commit:   git commit\n",
            file=sys.stderr,
        )
        return 1

    has_conflicts = False
    mirrored_count = 0

    for rel in all_touched_rel:
        in_src = rel in src_touched
        in_ts = rel in ts_touched

        src_full = f"{SRC_PREFIX}{rel}"
        ts_full = f"{TS_PREFIX}{rel}"

        if in_src and in_ts:
            # Bilateral change: both trees were staged
            src_status = src_touched[rel]
            ts_status = ts_touched[rel]

            if src_status == "D" and ts_status == "D":
                # Both deleted in staged index -> consistent
                continue
            elif src_status == "D" or ts_status == "D":
                print(
                    f"\n[PRE-COMMIT CONFLICT] File '{rel}' deleted in one tree but modified in the other!\n"
                    f"  {src_full}: status '{src_status}'\n"
                    f"  {ts_full}: status '{ts_status}'\n"
                    f"Please resolve deletion conflict manually.",
                    file=sys.stderr,
                )
                has_conflicts = True
            else:
                # Both added or modified -> verify exact staged blob hash
                blob_src = get_staged_blob(repo_root, src_full)
                blob_ts = get_staged_blob(repo_root, ts_full)

                if blob_src is not None and blob_ts is not None:
                    h_src = hashlib.sha256(blob_src).hexdigest()
                    h_ts = hashlib.sha256(blob_ts).hexdigest()
                    if h_src != h_ts:
                        print(
                            f"\n[PRE-COMMIT CONFLICT] Bilateral conflicting staged modifications for '{rel}':\n"
                            f"  {src_full} SHA-256:    {h_src}\n"
                            f"  {ts_full} SHA-256: {h_ts}\n"
                            f"Aborting commit to prevent data loss. Reconcile both files before committing.",
                            file=sys.stderr,
                        )
                        has_conflicts = True
                    else:
                        # Blobs are identical; ensure on-disk byte parity
                        src_disk = repo_root / src_full
                        ts_disk = repo_root / ts_full
                        if src_disk.is_file() and ts_disk.is_file():
                            if src_disk.read_bytes() != ts_disk.read_bytes():
                                shutil.copy2(src_disk, ts_disk)
                else:
                    has_conflicts = True

        elif in_src and not in_ts:
            # Unilateral change in src/
            status = src_touched[rel]
            if not auto_mirror:
                print(
                    f"[PRE-COMMIT PARITY FAILURE] '{src_full}' was staged without mirror '{ts_full}' (check-only mode).",
                    file=sys.stderr,
                )
                return 1

            if status == "D":
                # Deleted from src/, remove from trading_system/src/
                target_disk_path = repo_root / ts_full
                if target_disk_path.exists():
                    target_disk_path.unlink()
                    try:
                        target_disk_path.parent.rmdir()
                    except OSError:
                        pass
                run_git_rm_cached(repo_root, ts_full)
                if not quiet:
                    print(f"[PRE-COMMIT AUTO-MIRROR] Staged removal: {ts_full}")
                mirrored_count += 1
            else:
                # Modified or Added in src/, mirror to trading_system/src/
                source_disk_path = repo_root / src_full
                target_disk_path = repo_root / ts_full
                target_disk_path.parent.mkdir(parents=True, exist_ok=True)
                if source_disk_path.is_file():
                    shutil.copy2(source_disk_path, target_disk_path)
                else:
                    blob = get_staged_blob(repo_root, src_full)
                    if blob is not None:
                        target_disk_path.write_bytes(blob)
                run_git_add(repo_root, ts_full)
                if not quiet:
                    print(f"[PRE-COMMIT AUTO-MIRROR] Synchronized & staged: {src_full} -> {ts_full}")
                mirrored_count += 1

        elif in_ts and not in_src:
            # Unilateral change in trading_system/src/
            status = ts_touched[rel]
            if not auto_mirror:
                print(
                    f"[PRE-COMMIT PARITY FAILURE] '{ts_full}' was staged without mirror '{src_full}' (check-only mode).",
                    file=sys.stderr,
                )
                return 1

            if status == "D":
                # Deleted from trading_system/src/, remove from src/
                target_disk_path = repo_root / src_full
                if target_disk_path.exists():
                    target_disk_path.unlink()
                    try:
                        target_disk_path.parent.rmdir()
                    except OSError:
                        pass
                run_git_rm_cached(repo_root, src_full)
                if not quiet:
                    print(f"[PRE-COMMIT AUTO-MIRROR] Staged removal: {src_full}")
                mirrored_count += 1
            else:
                # Modified or Added in trading_system/src/, mirror to src/
                source_disk_path = repo_root / ts_full
                target_disk_path = repo_root / src_full
                target_disk_path.parent.mkdir(parents=True, exist_ok=True)
                if source_disk_path.is_file():
                    shutil.copy2(source_disk_path, target_disk_path)
                else:
                    blob = get_staged_blob(repo_root, ts_full)
                    if blob is not None:
                        target_disk_path.write_bytes(blob)
                run_git_add(repo_root, src_full)
                if not quiet:
                    print(f"[PRE-COMMIT AUTO-MIRROR] Synchronized & staged: {ts_full} -> {src_full}")
                mirrored_count += 1

    if has_conflicts:
        return 1

    # Now verify complete parity across both trees using verify_dual_tree_parity.py
    verifier_script = repo_root / "scripts" / "verify_dual_tree_parity.py"
    if verifier_script.is_file():
        cmd = [sys.executable, str(verifier_script), "--check"]
        if quiet:
            cmd.append("--quiet")
        res = subprocess.run(cmd, cwd=repo_root)
        if res.returncode != 0:
            print("[PRE-COMMIT ERROR] Dual-Tree parity check failed after mirroring.", file=sys.stderr)
            return res.returncode
    else:
        print(f"[WARN] Verifier script not found at {verifier_script}", file=sys.stderr)

    if not quiet and mirrored_count > 0:
        print(f"[PRE-COMMIT] Successfully auto-mirrored {mirrored_count} file(s). Parity intact.")

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dual-Tree Cryptographic Pre-Commit Synchronization Hook"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check parity without automatically mirroring files.",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress informational stdout output.",
    )
    args = parser.parse_args(argv)

    repo_root = get_repo_root()
    env_mode = os.environ.get("DUAL_TREE_MODE", "").strip().lower()
    auto_mirror = not args.check_only and env_mode != "check"

    return synchronize_and_verify(
        repo_root=repo_root,
        auto_mirror=auto_mirror,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    sys.exit(main())
