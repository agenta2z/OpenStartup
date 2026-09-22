"""Preflight tests for output_manifest emission (post-finalize hook).

Validates the manifest-emission contract. Part 2 (two-axis model) retired the
deliverable flags, so manifest emission is now gated SOLELY on
``output_manifest_index`` (the ``or self.output_is_deliverable`` auto-enable is
gone). The manifest is framework BOOKKEEPING and is written to ``artifacts/``
(Axis A), NOT to ``outputs/`` (the deliverable set).

Specifically:

  • InferencerBase has ``output_manifest_index: bool = attrib(default=False)``.
  • The retired ``output_is_deliverable`` attrib no longer exists.
  • Setting ``output_manifest_index=True`` emits the manifest file to
    ``artifacts/`` as ``<basename>_manifest.json`` with the documented schema
    (schema_version, output, contributors, stats).
  • The manifest is NOT emitted when ``output_manifest_index`` is False.

These tests use a non-local-access stub inferencer (so ``_finalize_output``
actually writes a file).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------


def _make_manifest_stub(
    output_path: str = "output.md", output_manifest_index: bool = False
):
    """Stub InferencerBase with template-style file output (NOT has_local_access).

    Returns a ``<Response>...</Response>``-delimited string so that
    ``_finalize_output`` writes it to ``workspace.outputs_dir/<output_path>``.
    """
    from agent_foundation.common.inferencers.inferencer_base import InferencerBase
    from attr import attrib, attrs

    @attrs(auto_attribs=False)
    class ManifestStub(InferencerBase):
        def _infer(self, inference_input, inference_config=None, **_inference_args):
            # Wrap in <Response> tags so extract_delimited can parse it
            return "<Response>stub-content</Response>"

    return ManifestStub(
        output_path=output_path,
        output_manifest_index=output_manifest_index,
    )


def _ws(tmp):
    from agent_foundation.common.inferencers.inferencer_workspace import (
        InferencerWorkspace,
    )

    w = InferencerWorkspace(root=str(tmp))
    w.ensure_dirs()
    return w


# -------------------------------------------------------------------------
# Attribute presence / retired-attrib absence
# -------------------------------------------------------------------------


@pytest.mark.preflight
def test_M1_output_is_deliverable_attr_is_retired():
    """M1: The ``output_is_deliverable`` attrib is RETIRED (Part 2)."""
    stub = _make_manifest_stub()
    assert not hasattr(stub, "output_is_deliverable"), (
        "InferencerBase.output_is_deliverable is RETIRED (Part 2, two-axis "
        "model). It must no longer exist — deliverables live directly in "
        "``outputs/`` and promotion is role-based."
    )
    assert not hasattr(stub, "is_deliverable_boundary"), (
        "InferencerBase.is_deliverable_boundary is RETIRED (Part 2). "
        "Child selection is via has_deliverables + boundary_filter."
    )


@pytest.mark.preflight
def test_M2_output_manifest_index_attr_exists():
    """M2: InferencerBase exposes ``output_manifest_index`` defaulting to False."""
    stub = _make_manifest_stub()
    assert hasattr(stub, "output_manifest_index"), (
        "InferencerBase must expose ``output_manifest_index`` attrib for "
        "provenance tracking (independent of promotion — KEEP per Part 2)."
    )
    assert stub.output_manifest_index is False, "Default must be False"


# -------------------------------------------------------------------------
# Negative case: no flag → no manifest
# -------------------------------------------------------------------------


@pytest.mark.preflight
def test_M3_no_flag_no_manifest_emitted(tmp_path):
    """M3: When ``output_manifest_index`` is False, no manifest file is written."""
    w = _ws(tmp_path)
    stub = _make_manifest_stub(output_manifest_index=False)
    stub._workspace = w
    stub.infer("input")

    output_file = os.path.join(w.outputs_dir, "output.md")
    assert os.path.isfile(output_file), "Output file should still be written"

    # Manifest is emitted to artifacts/ — assert it is absent there (and not
    # in outputs/ either).
    for base in (w.artifacts_dir, w.outputs_dir):
        manifest_file = os.path.join(base, "output_manifest.json")
        assert not os.path.exists(manifest_file), (
            "Manifest must NOT be emitted when output_manifest_index is False "
            f"— found unexpected manifest at {manifest_file}"
        )


# -------------------------------------------------------------------------
# Positive case: manifest flag → manifest in artifacts/
# -------------------------------------------------------------------------


@pytest.mark.preflight
def test_M4_manifest_emitted_to_artifacts_when_flag_set(tmp_path):
    """M4: Setting ``output_manifest_index=True`` emits the manifest into
    ``artifacts/`` (Axis A bookkeeping), NOT ``outputs/``."""
    w = _ws(tmp_path)
    stub = _make_manifest_stub(output_manifest_index=True)
    stub._workspace = w
    stub.infer("input")

    manifest_file = os.path.join(w.artifacts_dir, "output_manifest.json")
    assert os.path.isfile(manifest_file), (
        f"Manifest expected at {manifest_file} but not found. "
        "Verify _emit_output_manifest writes to artifacts_dir (Part 2, Axis A)."
    )
    # It must NOT be written into the deliverable set.
    assert not os.path.exists(os.path.join(w.outputs_dir, "output_manifest.json")), (
        "Manifest is bookkeeping — must NOT land in outputs/ (the deliverable set)"
    )


# -------------------------------------------------------------------------
# Schema: manifest content matches the documented v1.0 contract
# -------------------------------------------------------------------------


@pytest.mark.preflight
def test_M6_manifest_schema_v1(tmp_path):
    """M6: Manifest JSON has schema_version, output{path,size_bytes,produced_by,workspace_root},
    contributors[], stats{total}.
    """
    w = _ws(tmp_path)
    stub = _make_manifest_stub(output_manifest_index=True)
    stub._workspace = w
    stub.infer("input")

    manifest_file = os.path.join(w.artifacts_dir, "output_manifest.json")
    assert os.path.isfile(manifest_file)
    with open(manifest_file) as f:
        manifest = json.load(f)

    assert manifest.get("schema_version") == "1.0", (
        f"schema_version must be '1.0', got {manifest.get('schema_version')!r}"
    )

    out = manifest.get("output")
    assert isinstance(out, dict), "output block must be a dict"
    assert "path" in out and out["path"].endswith("output.md")
    assert isinstance(out.get("size_bytes"), int) and out["size_bytes"] >= 0
    assert out.get("produced_by", "").endswith("ManifestStub") or "Stub" in out.get(
        "produced_by", ""
    ), (
        f"produced_by should reflect the inferencer class, got {out.get('produced_by')!r}"
    )
    assert "workspace_root" in out

    assert isinstance(manifest.get("contributors"), list), "contributors must be a list"
    stats = manifest.get("stats")
    assert isinstance(stats, dict) and "total" in stats
    assert stats["total"] == len(manifest["contributors"])


# -------------------------------------------------------------------------
# No-workspace safety: don't crash when workspace is None
# -------------------------------------------------------------------------


@pytest.mark.preflight
def test_M9_no_workspace_no_crash(tmp_path):
    """M9: With no workspace assigned, manifest hook is a no-op (no crash)."""
    stub = _make_manifest_stub(output_manifest_index=True)
    # Do NOT assign _workspace
    # Should not crash — just returns the response unchanged
    result = stub.infer("input")
    assert result is not None
