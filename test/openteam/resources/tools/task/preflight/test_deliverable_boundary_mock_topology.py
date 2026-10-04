"""Mock topology integration test for deliverable boundary semantics (Part 2).

Exercises the surfacing helpers end-to-end against the two-axis contract:

  * ``outputs/`` IS the deliverable set (no ``final_deliverables/`` subfolder).
  * A child is a deliverable source iff its ``outputs/`` is non-empty
    (``workspace.has_deliverables``) AND it passes the caller-supplied
    ``boundary_filter`` — there are NO per-node deliverable flags.
  * Promotion carries a selected child's ``outputs/`` up into the parent's
    ``outputs/`` (via the ``deliverable_boundary`` collect/aggregate helpers,
    which the orchestrators call internally).

The leaf "inferencer" is a DeliverableStub that writes a tagged file into its
workspace's ``outputs/`` on each call.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


# Tag-marker stub: writes a known file to its workspace's outputs/ so we can
# assert exactly where it ends up after surfacing.
def _make_stub(tag, filename):
    """Create a stub inferencer that writes <filename> tagged with <tag>."""
    from agent_foundation.common.inferencers.inferencer_base import InferencerBase
    from attr import attrib, attrs

    @attrs(auto_attribs=False)
    class DeliverableStub(InferencerBase):
        _tag: str = attrib(default=tag)
        _filename: str = attrib(default=filename)

        def _infer(self, inference_input, inference_config=None, **_inference_args):
            ws = self._workspace
            if ws is None or ws.outputs_dir is None:
                # Workspace not configured — return a string response as fallback
                return f"stub:{self._tag}"
            os.makedirs(ws.outputs_dir, exist_ok=True)
            target = os.path.join(ws.outputs_dir, self._filename)
            with open(target, "w", encoding="utf-8") as f:
                f.write(f"# Deliverable from {self._tag}\n")
            return f"stub:{self._tag}"

    return DeliverableStub()


def _ws(tmp):
    from agent_foundation.common.inferencers.inferencer_workspace import (
        InferencerWorkspace,
    )

    w = InferencerWorkspace(root=str(tmp))
    w.ensure_dirs()
    return w


@pytest.mark.preflight
def test_S1_workspace_outputs_dir_is_the_deliverable_set(tmp_path):
    """S1: workspace.outputs_dir is the deliverable directory (Part 2)."""
    w = _ws(tmp_path)
    assert w.outputs_dir is not None
    assert os.path.isdir(w.outputs_dir)
    # Retired attrib/property must be gone.
    assert not hasattr(w, "deliverables_dir")
    assert not hasattr(w, "use_final_deliverables_folder")


@pytest.mark.preflight
def test_S2_child_workspace_has_outputs_dir(tmp_path):
    """S2: ws.child("foo").outputs_dir resolves under the child root."""
    w = _ws(tmp_path)
    child = w.child("worker_0")
    assert child.outputs_dir is not None
    assert child.outputs_dir.rstrip("/\\").endswith("outputs")


@pytest.mark.preflight
def test_S3_grandchild_workspace_has_outputs_dir(tmp_path):
    """S3: child().child() — outputs_dir resolves 2+ hops deep."""
    w = _ws(tmp_path)
    grandchild = w.child("a").child("b")
    assert grandchild.outputs_dir is not None
    assert grandchild.outputs_dir.rstrip("/\\").endswith("outputs")


@pytest.mark.preflight
def test_S4_stub_writes_to_outputs_dir(tmp_path):
    """S4: A stub inferencer correctly writes to its workspace's outputs_dir."""
    w = _ws(tmp_path)
    stub = _make_stub("test_S4", "out.md")
    stub._workspace = w
    stub.infer("input")
    assert os.path.isfile(os.path.join(w.outputs_dir, "out.md"))
    # And has_deliverables now reports True (outputs/ non-empty).
    assert w.has_deliverables is True


@pytest.mark.preflight
def test_S5_collect_helper_finds_children_with_deliverables(tmp_path):
    """S5: collect_child_boundary_deliverables returns children whose outputs/
    are non-empty."""
    from agent_foundation.common.inferencers.deliverable_boundary import (
        collect_child_boundary_deliverables,
    )

    parent = _ws(tmp_path)
    child_a = parent.child("worker_0")
    child_a.ensure_dirs()
    with open(os.path.join(child_a.outputs_dir, "a.md"), "w") as f:
        f.write("hi")
    child_b = parent.child("worker_1")
    child_b.ensure_dirs()
    with open(os.path.join(child_b.outputs_dir, "b.md"), "w") as f:
        f.write("bye")

    children = collect_child_boundary_deliverables(parent)
    assert len(children) == 2
    names = sorted(c.child_name for c in children)
    assert names == ["worker_0", "worker_1"]


@pytest.mark.preflight
def test_S6_aggregate_by_child_name(tmp_path):
    """S6: aggregate_into_self_deliverables produces workers/<name>/<file> structure."""
    from agent_foundation.common.inferencers.deliverable_boundary import (
        aggregate_into_self_deliverables,
        collect_child_boundary_deliverables,
    )

    parent = _ws(tmp_path)
    for n in ("worker_0", "worker_1"):
        c = parent.child(n)
        c.ensure_dirs()
        with open(os.path.join(c.outputs_dir, "result.md"), "w") as f:
            f.write(n)

    kids = collect_child_boundary_deliverables(parent)
    report = aggregate_into_self_deliverables(
        parent,
        kids,
        namespace_strategy="by_child_name",
        namespace_root="workers",
    )
    assert len(report.copied) == 2
    assert os.path.isfile(
        os.path.join(parent.outputs_dir, "workers/worker_0/result.md")
    )
    assert os.path.isfile(
        os.path.join(parent.outputs_dir, "workers/worker_1/result.md")
    )


@pytest.mark.preflight
def test_S7_aggregate_by_role_with_boundary_filter(tmp_path):
    """S7: by_role aggregation produces <role>/<file> structure; the caller
    supplies a role-based boundary_filter to SELECT deliverable-producing
    children (Part 2 — selection is caller-driven, not flag-driven)."""
    from agent_foundation.common.inferencers.deliverable_boundary import (
        aggregate_into_self_deliverables,
        collect_child_boundary_deliverables,
    )

    parent = _ws(tmp_path)
    for role in ("planner", "executor"):
        c = parent.child(role)
        c.ensure_dirs()
        with open(os.path.join(c.outputs_dir, f"{role}.md"), "w") as f:
            f.write(role)

    kids = collect_child_boundary_deliverables(
        parent,
        boundary_filter=lambda name, ws: name in ("planner", "executor"),
    )
    report = aggregate_into_self_deliverables(
        parent,
        kids,
        namespace_strategy="by_role",
    )
    assert len(report.copied) == 2
    assert os.path.isfile(os.path.join(parent.outputs_dir, "planner/planner.md"))
    assert os.path.isfile(os.path.join(parent.outputs_dir, "executor/executor.md"))


@pytest.mark.preflight
def test_S8_conflict_skip_existing(tmp_path):
    """S8: skip_existing strategy preserves existing files."""
    from agent_foundation.common.inferencers.deliverable_boundary import (
        aggregate_into_self_deliverables,
        ChildBoundaryDeliverables,
    )

    parent = _ws(tmp_path)
    # Put a pre-existing file under planner/
    pre_dir = os.path.join(parent.outputs_dir, "planner")
    os.makedirs(pre_dir)
    pre_file = os.path.join(pre_dir, "shared.md")
    with open(pre_file, "w") as f:
        f.write("existing-content")

    # Try to copy a new version of shared.md from a planner child
    src_child = parent.child("planner")
    src_child.ensure_dirs()
    new_file = os.path.join(src_child.outputs_dir, "shared.md")
    with open(new_file, "w") as f:
        f.write("new-content")

    report = aggregate_into_self_deliverables(
        parent,
        [
            ChildBoundaryDeliverables(
                child_name="planner",
                child_workspace_root=src_child.root,
                deliverable_files=["shared.md"],
                child_workspace=src_child,
            )
        ],
        namespace_strategy="by_role",
        conflict_strategy="skip_existing",
    )
    # Should be skipped (existing file preserved)
    with open(pre_file) as f:
        assert f.read() == "existing-content"
    assert "shared.md" in str(report.skipped)


@pytest.mark.preflight
def test_S9_worker_outputs_surface_under_workers_namespace(tmp_path):
    """S9: worker children's outputs/ surface under the parent's
    outputs/workers/<name>/ (the BTA-shaped aggregation)."""
    from agent_foundation.common.inferencers.deliverable_boundary import (
        aggregate_into_self_deliverables,
        collect_child_boundary_deliverables,
    )

    parent = _ws(tmp_path / "bta_root")
    for i in range(2):
        wc = parent.child(f"worker_{i}")
        wc.ensure_dirs()
        with open(os.path.join(wc.outputs_dir, f"worker_{i}_plan.md"), "w") as f:
            f.write(f"plan {i}")

    kids = collect_child_boundary_deliverables(parent)
    aggregate_into_self_deliverables(
        parent,
        kids,
        namespace_strategy="by_child_name",
        namespace_root="workers",
    )

    assert os.path.isfile(
        os.path.join(parent.outputs_dir, "workers/worker_0/worker_0_plan.md")
    )
    assert os.path.isfile(
        os.path.join(parent.outputs_dir, "workers/worker_1/worker_1_plan.md")
    )


@pytest.mark.preflight
def test_S10_empty_child_outputs_are_not_collected(tmp_path):
    """S10: a child whose outputs/ is empty is NOT selected as a deliverable
    source (has_deliverables gate — replaces the old flag-off no-op)."""
    from agent_foundation.common.inferencers.deliverable_boundary import (
        collect_child_boundary_deliverables,
    )

    parent = _ws(tmp_path)
    # A child directory that exists but has an empty outputs/.
    empty_child = parent.child("worker_0")
    empty_child.ensure_dirs()
    assert empty_child.has_deliverables is False

    kids = collect_child_boundary_deliverables(parent)
    assert kids == []


@pytest.mark.preflight
def test_S11_role_boundary_filter_selects_named_children(tmp_path):
    """S11: PTI-style role selection — only planner/executor are surfaced with
    by_role namespacing; bookkeeping children are excluded by the filter."""
    from agent_foundation.common.inferencers.deliverable_boundary import (
        aggregate_into_self_deliverables,
        collect_child_boundary_deliverables,
    )

    parent = _ws(tmp_path / "pti_root")
    # planner + executor are real roles; "guardrail" is a bookkeeping child.
    for role in ("planner", "executor", "guardrail"):
        c = parent.child(role)
        c.ensure_dirs()
        with open(os.path.join(c.outputs_dir, f"{role}.md"), "w") as f:
            f.write(role)

    kids = collect_child_boundary_deliverables(
        parent,
        boundary_filter=lambda name, ws: name in ("planner", "executor"),
    )
    aggregate_into_self_deliverables(
        parent,
        kids,
        namespace_strategy="by_role",
    )

    assert os.path.isfile(os.path.join(parent.outputs_dir, "planner/planner.md"))
    assert os.path.isfile(os.path.join(parent.outputs_dir, "executor/executor.md"))
    # guardrail was filtered out — never surfaced.
    assert not os.path.exists(os.path.join(parent.outputs_dir, "guardrail"))


@pytest.mark.preflight
def test_S12_full_chain_workers_to_parent(tmp_path):
    """S12: full surfacing chain — a nested BTA's workers/ subtree surfaces
    through a role boundary into planner/workers/... (two hops)."""
    from agent_foundation.common.inferencers.deliverable_boundary import (
        aggregate_into_self_deliverables,
        collect_child_boundary_deliverables,
    )

    parent = _ws(tmp_path / "pti")
    # Planner role already contains a nested BTA's aggregated deliverables
    # (a workers/ subfolder) inside its own outputs/.
    planner_ws = parent.child("planner")
    planner_ws.ensure_dirs()
    workers_dir = os.path.join(planner_ws.outputs_dir, "workers", "worker_0")
    os.makedirs(workers_dir)
    with open(os.path.join(workers_dir, "worker_0_plan.md"), "w") as f:
        f.write("nested worker output")

    kids = collect_child_boundary_deliverables(
        parent,
        boundary_filter=lambda name, ws: name == "planner",
    )
    aggregate_into_self_deliverables(
        parent,
        kids,
        namespace_strategy="by_role",
    )

    # Worker file surfaced through the planner role boundary.
    expected = os.path.join(
        parent.outputs_dir, "planner/workers/worker_0/worker_0_plan.md"
    )
    assert os.path.isfile(expected), f"missing: {expected}"


@pytest.mark.preflight
def test_S13_flat_promotion_carries_child_outputs_up(tmp_path):
    """S13: flat promotion (Dual-style pass-through) carries a selected child's
    outputs/ up into the parent's outputs/ with no role subfolder."""
    from agent_foundation.common.inferencers.inferencer_workspace import (
        InferencerWorkspace,
    )

    parent = _ws(tmp_path / "dual_ws")
    child = parent.child("base")
    child.ensure_dirs()
    with open(os.path.join(child.outputs_dir, "base.md"), "w") as f:
        f.write("base output")

    # Flat surface (the primitive the Dual pass-through uses).
    parent.surface_outputs_from(child)

    assert os.path.isfile(os.path.join(parent.outputs_dir, "base.md"))


@pytest.mark.preflight
def test_S14_flat_promotion_last_writer_wins(tmp_path):
    """S14: when the fixer's output replaces the base output, a flat promotion
    of the winner's outputs/ yields the winner content and NO fixer/ subfolder."""
    parent = _ws(tmp_path / "dual_ws")

    fixer = parent.child("fixer")
    fixer.ensure_dirs()
    with open(os.path.join(fixer.outputs_dir, "result.md"), "w") as f:
        f.write("FIXER_TAG")

    # The Dual selects the fixer as the active proposer and flat-promotes its
    # outputs/ (skip_existing=False so the winner wins).
    parent.surface_outputs_from(fixer, skip_existing=False)

    fp = os.path.join(parent.outputs_dir, "result.md")
    assert os.path.isfile(fp)
    with open(fp) as f:
        content = f.read()
    assert "FIXER_TAG" in content
    # NO fixer/ subfolder — flat promotion, not namespaced.
    assert not os.path.isdir(os.path.join(parent.outputs_dir, "fixer"))


@pytest.mark.preflight
def test_S15_no_files_no_op(tmp_path):
    """Negative: empty workspace produces empty collection (no crash)."""
    from agent_foundation.common.inferencers.deliverable_boundary import (
        collect_child_boundary_deliverables,
    )

    parent = _ws(tmp_path)
    children = collect_child_boundary_deliverables(parent)
    assert children == []


@pytest.mark.preflight
def test_S16_AggregateReport_fields(tmp_path):
    """S16: AggregateReport.skipped/copied populated correctly."""
    from agent_foundation.common.inferencers.deliverable_boundary import (
        aggregate_into_self_deliverables,
        ChildBoundaryDeliverables,
    )

    parent = _ws(tmp_path)
    # Create one child with one file, but pre-populate destination to trigger
    # skip_existing.
    role_dir = os.path.join(parent.outputs_dir, "planner")
    os.makedirs(role_dir)
    pre_file = os.path.join(role_dir, "x.md")
    with open(pre_file, "w") as f:
        f.write("kept")

    src_child = parent.child("planner")
    src_child.ensure_dirs()
    with open(os.path.join(src_child.outputs_dir, "x.md"), "w") as f:
        f.write("ignored")

    report = aggregate_into_self_deliverables(
        parent,
        [
            ChildBoundaryDeliverables(
                child_name="planner",
                child_workspace_root=src_child.root,
                deliverable_files=["x.md"],
                child_workspace=src_child,
            )
        ],
        namespace_strategy="by_role",
        conflict_strategy="skip_existing",
    )
    assert len(report.skipped) == 1
    assert len(report.copied) == 0
    assert "x.md" in report.skipped[0]


@pytest.mark.preflight
def test_S17_deep_child_outputs_dir_resolves(tmp_path):
    """S17: ws.child("a").child("b").child("c").child("d").outputs_dir resolves
    N levels deep."""
    w = _ws(tmp_path)
    deep = w.child("a").child("b").child("c").child("d")
    assert deep.outputs_dir is not None
    assert deep.outputs_dir.rstrip("/\\").endswith("outputs")


@pytest.mark.preflight
def test_S18_isolation_two_workers_no_cross_contamination(tmp_path):
    """Isolation: two parallel workers don't see each other's outputs."""
    parent = _ws(tmp_path)
    w0 = parent.child("worker_0")
    w0.ensure_dirs()
    with open(os.path.join(w0.outputs_dir, "w0.md"), "w") as f:
        f.write("zero")
    w1 = parent.child("worker_1")
    w1.ensure_dirs()
    with open(os.path.join(w1.outputs_dir, "w1.md"), "w") as f:
        f.write("one")
    # No cross-contamination
    assert os.listdir(w0.outputs_dir) == ["w0.md"]
    assert os.listdir(w1.outputs_dir) == ["w1.md"]
