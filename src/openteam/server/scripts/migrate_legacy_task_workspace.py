#!/usr/bin/env fbpython
# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.
# pyre-strict
"""One-time, in-place, idempotent migration of legacy (pre-"two-axis") AF task
workspaces to the layout the current OpenStartup server + UI expect.

Background
----------
AgentFoundation's task-workspace layout was refactored ("two-axis" model):

* ``outputs/final_deliverables/`` was **retired** — deliverables now live directly
  in ``outputs/``.
* Framework bookkeeping (``round_log.jsonl``, ``*_manifest.json``) moved from
  ``outputs/`` into ``artifacts/``.
* Deliverable promotion (a container node surfacing a winning descendant's
  ``outputs/output.md``) is written by a fresh run as an *absolute symlink*; leaf
  nodes hold a real ``output.md``.

Two completed runs predate that refactor and are our reuse/render fixtures. Under
the current readers they *misrender*: worker nodes surface ``round_log.jsonl`` as
their "deliverable", and deliverables reachable only through promotion symlinks
into ``final_deliverables/`` dangle the moment that dir is removed. This tool
reshapes such a workspace, **in place**, to match what a fresh two-axis run would
have written — without re-running any inference.

Readers this must satisfy (verified against the server source; unchanged here):

* ``task_graph_reconstruct._resolve_output_path``: a node's deliverable is
  ``outputs/output.md`` (``.is_file()`` follows symlinks) else the
  alphabetically-first regular non-dot file in ``outputs/`` else ``None``.  ⇒ a
  lone ``round_log.jsonl`` in ``outputs/`` is (wrongly) surfaced as a deliverable.
* ``view_file`` (``GET /api/view``) ``.resolve()``s then 404s on a missing target
  ⇒ **no dangling ``output.md`` may remain**.
* ``_detect_class`` reads ``logs/session/<Class>-<uuid>.jsonl`` ⇒ ``logs/`` is
  untouchable (Part 3 — ``artifacts/inference/`` — has NOT landed).

Design choices (see the plan for rationale)
-------------------------------------------
* **Materialize (real copies), not re-point symlinks.** Resolution/serving readers
  treat a symlink-to-real-file and a real file identically, so this is invisible
  to them, and it makes the tree self-contained so a plain ``cp -a`` into another
  session (parallel test/debug) is foolproof and no promotion symlink can dangle.
* **Keep ``plan.md``** at the RP top (it is the ``document_path`` / reuse anchor);
  Phase B additionally creates the byte-identical canonical ``output.md``.

Phases (ordering is load-bearing: materialize while targets still exist, then
operate on all-real files)
-------------------------------------------------------------------------------
0. **Backup** the task dir to an out-of-tree ``.tgz`` (a copy inside ``tasks/``
   would be scanned as a phantom task by ``find_reusable_workspace``).
A. **Materialize** every promotion ``output.md`` symlink directly under an
   ``outputs/`` to a real copy of its *canonical de-fd* content (strip a
   ``/outputs/final_deliverables/`` segment and prefer the direct file — it is the
   newer one a fresh ``propose`` promotes).
B. **Retire** each ``final_deliverables/`` — classifying every entry **by TYPE
   first** (a symlink is ``unlink``ed, never moved: moving a link relocates the
   link, which would dangle once the aggregator fd is removed), then real
   deliverables are hoisted/kept and real bookkeeping is relocated to
   ``artifacts/``; finally ``rmdir`` the emptied dir.
C. **Relocate** remaining ``outputs/`` bookkeeping (``round_log.jsonl`` /
   ``*_manifest.json``) to ``artifacts/``.
D. **Fill the worker promotion gap**: a container node with no ``outputs/``
   deliverable but a real highest-round ``children/round_<n>/children/fix/outputs/
   output.md`` gets that winner *copied* to its ``outputs/output.md`` — exactly
   what a fresh MFDual worker promotes (the live code promotes the fix child).

The tool is idempotent (a second run finds nothing to do), backup-first, and
``--dry-run`` capable. It never deletes unique file data (stale copies are moved
to ``artifacts/`` with a collision-safe name); the only destructive op is
unlinking a *symlink* and ``rmdir`` of an emptied ``final_deliverables/``.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger: logging.Logger = logging.getLogger("migrate_legacy_task_workspace")

FINAL_DELIVERABLES: str = "final_deliverables"
_ROUND_RE: re.Pattern[str] = re.compile(r"round_\d+$")
# Backups go here (a sibling of ``servers/``), never inside any session ``tasks/``.
_BACKUP_SUBDIR: str = "_fixture_backups"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _is_bookkeeping(name: str) -> bool:
    """A workspace file is framework bookkeeping (belongs in ``artifacts/``) iff it
    is ``round_log.jsonl`` or matches ``*_manifest.json``. Everything else under
    ``outputs/`` is a deliverable (denylist, not allowlist ⇒ unknown deliverables
    such as ``proposals.json`` / ``doc_pointers.json`` are preserved)."""
    return name == "round_log.jsonl" or name.endswith("_manifest.json")


def _within(path: str, root: Path) -> bool:
    """True iff *path* (resolved) is inside *root*."""
    try:
        return os.path.commonpath([os.path.realpath(path), str(root)]) == str(root)
    except ValueError:
        return False


def _collision_safe(dest_dir: Path, name: str, tag: str = "") -> Path:
    """A destination path in *dest_dir* for *name* that does not clobber anything.

    ``tag`` (e.g. ``"fd"``) is inserted before the extension for the first
    candidate; a numeric counter is appended on further collisions. Never
    overwrites (checks both ``exists`` and ``is_symlink`` so a dangling link at
    the destination is not silently reused)."""
    base, ext = os.path.splitext(name)
    mid = f".{tag}" if tag else ""
    candidate = dest_dir / f"{base}{mid}{ext}"
    i = 0
    while candidate.exists() or candidate.is_symlink():
        i += 1
        candidate = dest_dir / f"{base}{mid}.{i}{ext}"
    return candidate


def _outputs_dirs(task_root: Path) -> list[Path]:
    """Every directory literally named ``outputs`` under *task_root* (does not
    follow symlinks, so the external ``outputs/docs/codebase`` is never entered)."""
    found: list[Path] = []
    for dirpath, _dirnames, _files in os.walk(task_root, followlinks=False):
        if os.path.basename(dirpath) == "outputs":
            found.append(Path(dirpath))
        # prune nothing — trees are small and bounded.
    return sorted(found)


def resolve_output_path(node: Path) -> Optional[str]:
    """Faithful reimplementation of the server's
    ``task_graph_reconstruct._resolve_output_path`` — used for Phase-D gating and
    for verification so our decisions match the live reader exactly."""
    outputs = node / "outputs"
    if not outputs.is_dir():
        return None
    primary = outputs / "output.md"
    if primary.is_file():
        return str(primary.resolve())
    try:
        files = sorted(
            f for f in outputs.iterdir() if f.is_file() and not f.name.startswith(".")
        )
    except OSError:
        files = []
    if files:
        return str(files[0].resolve())
    return None


class Stats:
    """Per-task action counters, printed as the run summary."""

    def __init__(self) -> None:
        self.materialized: int = 0
        self.fd_symlinks_unlinked: int = 0
        self.fd_stale_moved: int = 0
        self.fd_promoted: int = 0
        self.fd_bookkeeping_moved: int = 0
        self.fd_dirs_removed: int = 0
        self.bookkeeping_relocated: int = 0
        self.workers_promoted: int = 0

    def summary(self) -> str:
        return (
            f"materialized={self.materialized} "
            f"fd_symlinks_unlinked={self.fd_symlinks_unlinked} "
            f"fd_stale_moved={self.fd_stale_moved} fd_promoted={self.fd_promoted} "
            f"fd_bookkeeping_moved={self.fd_bookkeeping_moved} "
            f"fd_dirs_removed={self.fd_dirs_removed} "
            f"bookkeeping_relocated={self.bookkeeping_relocated} "
            f"workers_promoted={self.workers_promoted}"
        )


def _move(src: Path, dst: Path, dry: bool) -> None:
    logger.info("  move   %s -> %s", src, dst)
    if not dry:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))


def _unlink(p: Path, dry: bool) -> None:
    logger.info("  unlink %s", p)
    if not dry:
        p.unlink()


def _copyfile(src: Path, dst: Path, dry: bool) -> None:
    logger.info("  copy   %s -> %s", src, dst)
    if not dry:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)  # copies content; never preserves a symlink


# ---------------------------------------------------------------------------
# Phase 0 — backup
# ---------------------------------------------------------------------------
def phase0_backup(task_root: Path, backups_dir: Path, dry: bool) -> Optional[Path]:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = backups_dir / f"{task_root.name}_pre2axis_{ts}.tgz"
    logger.info("[phase 0] backup %s -> %s", task_root, dest)
    if dry:
        return None
    backups_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(dest, "w:gz") as tar:
        # dereference=False → symlinks are stored as symlinks (true rollback).
        tar.add(str(task_root), arcname=task_root.name)
    return dest


# ---------------------------------------------------------------------------
# Phase A — materialize promotion output.md symlinks (from de-fd canonical)
# ---------------------------------------------------------------------------
def phaseA_materialize(task_root: Path, dry: bool, stats: Stats) -> None:
    logger.info("[phase A] materialize promotion output.md symlinks")
    for outputs in _outputs_dirs(task_root):
        link = outputs / "output.md"
        if not link.is_symlink():
            continue
        target = os.readlink(link)  # absolute in these trees
        real = os.path.realpath(link)
        if not _within(real, task_root):
            logger.warning("  skip external/out-of-tree link %s -> %s", link, target)
            continue
        # [NEW-1] canonical = the direct (de-fd) file when it exists (it is the
        # newer one a fresh ``propose`` promotes); else the link's own realpath.
        canonical = real
        if f"/outputs/{FINAL_DELIVERABLES}/" in target:
            stripped = target.replace(f"/outputs/{FINAL_DELIVERABLES}/", "/outputs/")
            if os.path.isfile(stripped):
                canonical = stripped
        if not os.path.isfile(canonical):
            logger.warning("  skip: canonical target missing for %s", link)
            continue
        logger.info("  materialize %s (from %s)", link, canonical)
        stats.materialized += 1
        if not dry:
            link.unlink()
            shutil.copyfile(canonical, link)


# ---------------------------------------------------------------------------
# Phase B — retire final_deliverables/ (TYPE-first: symlinks unlinked, never moved)
# ---------------------------------------------------------------------------
def phaseB_retire_fd(task_root: Path, dry: bool, stats: Stats) -> None:
    logger.info("[phase B] retire final_deliverables/")
    for outputs in _outputs_dirs(task_root):
        fd = outputs / FINAL_DELIVERABLES
        if fd.is_symlink() or not fd.is_dir():
            continue
        node = outputs.parent
        artifacts = node / "artifacts"
        for entry in sorted(fd.iterdir()):
            # TYPE FIRST — a symlink is unlinked, never moved. shutil.move on a
            # link relocates the *link*; once the aggregator fd is removed the
            # moved link dangles (and trips the dangling-symlink check).
            if entry.is_symlink():
                _unlink(entry, dry)
                stats.fd_symlinks_unlinked += 1
                continue
            if entry.is_dir():
                # Not expected in these fixtures; preserve as a deliverable.
                dest = outputs / entry.name
                if dest.exists():
                    _move(entry, _collision_safe(artifacts, entry.name, "fd"), dry)
                    stats.fd_stale_moved += 1
                else:
                    _move(entry, dest, dry)
                    stats.fd_promoted += 1
                continue
            # real file
            if _is_bookkeeping(entry.name):
                _move(entry, _collision_safe(artifacts, entry.name), dry)
                stats.fd_bookkeeping_moved += 1
                continue
            direct = outputs / entry.name
            if direct.is_file():  # a real deliverable already sits directly in outputs/
                _move(entry, _collision_safe(artifacts, entry.name, "fd"), dry)
                stats.fd_stale_moved += 1
            else:
                _move(entry, direct, dry)
                stats.fd_promoted += 1
        # remove the now-empty final_deliverables/
        logger.info("  rmdir  %s", fd)
        stats.fd_dirs_removed += 1
        if not dry:
            try:
                fd.rmdir()
            except OSError as exc:
                logger.warning("  rmdir failed (not empty?) %s: %s", fd, exc)
                stats.fd_dirs_removed -= 1


# ---------------------------------------------------------------------------
# Phase C — relocate direct outputs/ bookkeeping to artifacts/
# ---------------------------------------------------------------------------
def phaseC_relocate_bookkeeping(task_root: Path, dry: bool, stats: Stats) -> None:
    logger.info("[phase C] relocate bookkeeping outputs/ -> artifacts/")
    for outputs in _outputs_dirs(task_root):
        node = outputs.parent
        artifacts = node / "artifacts"
        for entry in sorted(outputs.iterdir()):
            if entry.is_dir() and not entry.is_symlink():
                continue
            if not _is_bookkeeping(entry.name):
                continue
            if entry.is_symlink():
                # a bookkeeping symlink must not be moved (would dangle) — unlink.
                _unlink(entry, dry)
                stats.fd_symlinks_unlinked += 1
            elif entry.is_file():
                _move(entry, _collision_safe(artifacts, entry.name), dry)
                stats.bookkeeping_relocated += 1


# ---------------------------------------------------------------------------
# Phase D — fill the worker promotion gap (copy the round-fix winner)
# ---------------------------------------------------------------------------
def _round_fix_winner(node: Path) -> Optional[Path]:
    """The winning deliverable a fresh MFDual/Dual promotes: the highest
    ``children/round_<n>/children/fix/outputs/output.md`` that is a real file
    (scanning highest round first; matches the live ``_last_output_child_ws`` =
    the fix step's workspace). ``None`` when the node ran no fix round."""
    children = node / "children"
    if not children.is_dir():
        return None
    rounds = sorted(
        c for c in children.iterdir() if c.is_dir() and _ROUND_RE.match(c.name)
    )
    for r in reversed(rounds):
        cand = r / "children" / "fix" / "outputs" / "output.md"
        if cand.is_file():
            return cand
    return None


def phaseD_promote_workers(task_root: Path, dry: bool, stats: Stats) -> None:
    logger.info("[phase D] fill worker promotion gap")
    for outputs in _outputs_dirs(task_root):
        node = outputs.parent
        if (outputs / "output.md").is_file():
            continue  # already has a canonical deliverable
        # Gate: the node has no non-bookkeeping deliverable file (so after A–C it
        # resolves to None). Using this (rather than resolve==None) makes --dry-run
        # accurate even though Phase C has not physically moved bookkeeping yet.
        non_book = [
            f
            for f in outputs.iterdir()
            if f.is_file()
            and not f.name.startswith(".")
            and not _is_bookkeeping(f.name)
        ]
        if non_book:
            continue
        winner = _round_fix_winner(node)
        if winner is None:
            continue  # no descendant winner — legitimately None (do NOT fabricate)
        logger.info("  promote worker %s <- %s", outputs / "output.md", winner)
        stats.workers_promoted += 1
        if not dry:
            shutil.copyfile(winner, outputs / "output.md")


# ---------------------------------------------------------------------------
# built-in static verification
# ---------------------------------------------------------------------------
def _dangling_in_tree(task_root: Path) -> list[str]:
    """Symlinks under *task_root* that don't resolve AND whose target is inside
    the tree. The intentional external ``outputs/docs/codebase`` (target outside
    the tree) is exempt — a bare "no broken symlink" check would false-fail if
    that external tree were absent, which is orthogonal to this migration.
    Covers both file and dir symlinks (``followlinks=False`` never descends them).
    """
    bad: list[str] = []
    for dirpath, dirnames, files in os.walk(task_root, followlinks=False):
        for name in list(dirnames) + list(files):
            p = Path(dirpath) / name
            if not p.is_symlink() or p.exists():
                continue  # not a link, or resolves fine
            tgt = os.readlink(p)
            abs_tgt = tgt if os.path.isabs(tgt) else os.path.join(dirpath, tgt)
            if _within(abs_tgt, task_root):
                bad.append(f"dangling in-tree symlink: {p} -> {tgt}")
    return bad


def verify(task_root: Path) -> list[str]:
    """Return a list of failures (empty ⇒ pass). Structural invariants only; the
    before/after reconstruction diff is run separately."""
    failures: list[str] = []

    fds = [
        d
        for d, _dn, _f in os.walk(task_root, followlinks=False)
        if os.path.basename(d) == FINAL_DELIVERABLES
    ]
    if fds:
        failures.append(f"{len(fds)} final_deliverables/ dir(s) remain")

    for outputs in _outputs_dirs(task_root):
        for entry in outputs.iterdir():
            if entry.is_file() and _is_bookkeeping(entry.name):
                failures.append(f"bookkeeping left in outputs/: {entry}")

    failures.extend(_dangling_in_tree(task_root))

    # completion signal + task_meta must be intact.
    if not (task_root / "task_meta.json").is_file():
        failures.append("task_meta.json missing")

    return failures


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------
def migrate_one(task_root: Path, backups_dir: Path, dry: bool, backup: bool) -> bool:
    """Migrate a single task dir. Returns True on success (verification passed or
    dry-run)."""
    logger.info("=== %s%s ===", task_root, "  (DRY-RUN)" if dry else "")
    stats = Stats()
    if backup:
        phase0_backup(task_root, backups_dir, dry)
    else:
        logger.info("[phase 0] backup SKIPPED (--no-backup)")
    phaseA_materialize(task_root, dry, stats)
    phaseB_retire_fd(task_root, dry, stats)
    phaseC_relocate_bookkeeping(task_root, dry, stats)
    phaseD_promote_workers(task_root, dry, stats)
    logger.info("[summary] %s", stats.summary())
    if dry:
        logger.info("[verify] skipped (dry-run)")
        return True
    failures = verify(task_root)
    if failures:
        for f in failures:
            logger.error("[verify] FAIL: %s", f)
        return False
    logger.info("[verify] PASS")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("task_dirs", nargs="+", help="AF task workspace dir(s) to migrate")
    ap.add_argument(
        "--dry-run", action="store_true", help="report actions, change nothing"
    )
    ap.add_argument(
        "--no-backup", action="store_true", help="skip the Phase-0 tar backup"
    )
    ap.add_argument("--verbose", action="store_true", help="debug logging")
    ap.add_argument(
        "--backups-dir",
        default=None,
        help="override backup location (default: <…>/OpenStartup/_runtime/_fixture_backups)",
    )
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )

    ok = True
    for raw in args.task_dirs:
        task_root = Path(raw).resolve()
        if not task_root.is_dir():
            logger.error("not a directory: %s", task_root)
            ok = False
            continue
        if args.backups_dir:
            backups_dir = Path(args.backups_dir).resolve()
        else:
            # default: the OpenStartup _runtime root's _fixture_backups sibling of servers/
            # <…>/_runtime/servers/<server>/sessions/<sess>/tasks/<task>
            runtime = task_root
            for _ in range(4):
                runtime = runtime.parent
            # runtime now points at <…>/_runtime/servers/<server>; go up to _runtime
            backups_dir = task_root
            while backups_dir.name != "_runtime" and backups_dir.parent != backups_dir:
                backups_dir = backups_dir.parent
            backups_dir = backups_dir / _BACKUP_SUBDIR
        if not migrate_one(task_root, backups_dir, args.dry_run, not args.no_backup):
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
