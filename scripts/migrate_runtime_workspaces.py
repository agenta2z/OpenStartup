#!/usr/bin/env python3
"""ONE-TIME migration to unified workspace layout.

Operations (all default --dry-run; require --apply for writes):
  1. src/openteam/server/_runtime/tasks/* -> _runtime/tasks/task/*
     (legacy standalone task workspaces — move out of source tree)
  2. _runtime/servers/<server>/tasks/* -> orphans report
     (cannot auto-associate to historical sessions; left in place)
  3. test/.../_runtime/ leaked workspaces -> report + optional archive

Usage:
    python scripts/migrate_runtime_workspaces.py --dry-run
    python scripts/migrate_runtime_workspaces.py --apply
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually move files (default is dry-run)",
    )
    args = parser.parse_args()
    dry_run = not args.apply

    repo_root = Path(__file__).resolve().parent.parent
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"=== Workspace Migration ({mode}) ===\n")

    # 1. Migrate standalone task workspaces from src/ to _runtime/tasks/task/
    old_standalone = repo_root / "src" / "openteam" / "server" / "_runtime" / "tasks"
    new_standalone = repo_root / "_runtime" / "tasks" / "task"
    moved = 0
    if old_standalone.exists():
        print(f"1. Migrating standalone workspaces: {old_standalone}")
        for old in sorted(old_standalone.iterdir()):
            if not old.is_dir():
                continue
            new = new_standalone / old.name
            if new.exists():
                print(f"   SKIP (exists): {old.name}")
                continue
            print(f"   MOVE: {old.name} -> {new}")
            if not dry_run:
                new_standalone.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old), str(new))
            moved += 1
        print(f"   Total: {moved} workspaces {'would be' if dry_run else ''} moved.\n")
    else:
        print(f"1. No legacy standalone workspaces at {old_standalone}\n")

    # 2. Report orphan server-level task dirs
    servers_dir = repo_root / "_runtime" / "servers"
    orphan_dirs = []
    if servers_dir.exists():
        for server in servers_dir.iterdir():
            if not server.is_dir():
                continue
            tasks_dir = server / "tasks"
            if tasks_dir.exists() and any(tasks_dir.iterdir()):
                orphan_dirs.append(tasks_dir)

    if orphan_dirs:
        print(f"2. Orphan server-level task dirs (cannot auto-associate with sessions):")
        for d in orphan_dirs:
            count = sum(1 for _ in d.iterdir() if _.is_dir())
            print(f"   {d} ({count} task dirs)")
        print("   These are left in place. Review manually.\n")
    else:
        print("2. No orphan server-level task dirs found.\n")

    # 3. Report leaked test workspaces
    test_leaks = list((repo_root / "test").rglob("_runtime"))
    test_leaks = [d for d in test_leaks if d.is_dir()]
    if test_leaks:
        print(f"3. Leaked test workspaces ({len(test_leaks)} directories):")
        for d in test_leaks:
            count = sum(1 for _ in d.iterdir() if _.is_dir())
            print(f"   {d.relative_to(repo_root)} ({count} subdirs)")
        if not dry_run:
            archive = repo_root / "_runtime" / "_archive" / "test_leaked"
            archive.mkdir(parents=True, exist_ok=True)
            for d in test_leaks:
                rel = d.relative_to(repo_root)
                dest = archive / str(rel).replace("/", "_")
                if not dest.exists():
                    shutil.move(str(d), str(dest))
                    print(f"   ARCHIVED: {rel} -> {dest.relative_to(repo_root)}")
        print()
    else:
        print("3. No leaked test workspaces found.\n")

    if dry_run:
        print("Re-run with --apply to execute these changes.")
    else:
        print("Migration complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
