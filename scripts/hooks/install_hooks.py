#!/usr/bin/env python3
"""
scripts/hooks/install_hooks.py
Installs and configures Git Pre-Commit hooks for Dual-Tree Cryptographic Parity.

Actions:
  1. Sets git config core.hooksPath .githooks
  2. Copies .githooks/pre-commit to .git/hooks/pre-commit (as an active fallback)
  3. Configures executable file permissions
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path


def get_repo_root() -> Path:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(res.stdout.strip()).resolve()
    except Exception:
        candidate = Path(__file__).resolve().parent.parent.parent
        return candidate


def make_executable(path: Path) -> None:
    try:
        current_mode = path.stat().st_mode
        path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass


def install_hooks() -> int:
    repo_root = get_repo_root()
    githooks_dir = repo_root / ".githooks"
    git_hooks_dir = repo_root / ".git" / "hooks"
    source_hook = githooks_dir / "pre-commit"

    if not source_hook.is_file():
        print(f"[INSTALL ERROR] Source hook not found: {source_hook}", file=sys.stderr)
        return 1

    # 1. Configure git config core.hooksPath .githooks
    try:
        subprocess.run(
            ["git", "config", "core.hooksPath", ".githooks"],
            cwd=repo_root,
            check=True,
        )
        print("[HOOKS] Configured 'git config core.hooksPath .githooks'")
    except subprocess.CalledProcessError as exc:
        print(f"[WARN] Failed to set core.hooksPath: {exc}", file=sys.stderr)

    # 2. Make .githooks/pre-commit executable
    make_executable(source_hook)

    # 3. Copy to .git/hooks/pre-commit as fallback
    if git_hooks_dir.is_dir():
        target_hook = git_hooks_dir / "pre-commit"
        shutil.copy2(source_hook, target_hook)
        make_executable(target_hook)
        print(f"[HOOKS] Copied pre-commit hook to fallback: {target_hook}")
    else:
        print(f"[WARN] .git/hooks directory not found at {git_hooks_dir}")

    print("\n[OK] Dual-Tree Parity Git pre-commit hook successfully installed!")
    print("     Every commit touching src/ or trading_system/src/ will automatically mirror and verify parity.")
    return 0


if __name__ == "__main__":
    sys.exit(install_hooks())
