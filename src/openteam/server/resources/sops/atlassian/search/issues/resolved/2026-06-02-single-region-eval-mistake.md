# Resolved: Single-region eval mistake

- **Date discovered**: 2026-06-02
- **Cycle**: First automated L2 cross-tenant refresh (ml-registry EnsembleL23p v35)
- **Severity**: Medium (would have shipped a misleading launch doc; no production impact)
- **Status**: ✅ Resolved — prevention guard in place in [`../../SOP.md`](../../SOP.md)

## What happened

During the first automated cycle of the `lkp_ugc_dup_exception_list` refresh, the orchestrator
fired four eval workflow runs intending to cover `us_west_2`, `us`, `eu_west_1`, and `eu`.
In reality, all four runs used the **same** blueprint ID `ab41e4d7-...` which is registered
only for region `us_west_2`. The result: four redundant us_west_2 evals, zero coverage of
the three other regions.

Affected runs (now superseded):
- `ab41e4d7` × 4 (all us_west_2, all SUCCEEDED but with no eval value beyond the first one)

## How it surfaced

The mistake was **not** caught by any automated check. It was caught by a user
critical-thinking challenge:

> "can you help double check, was your eval runs real? if they really ran you should have got
>  the valid links? or it is simply due to some permission issues, can you investigate?"

Detection then took ~5 minutes:
1. Inspected each "regional" run's Databricks job ID
2. Discovered all 4 mapped to the same job (`668049859677762`)
3. Read the job's `realm` tag → confirmed all 4 jobs were `us_west_2`

## Root cause

`atlas ml workflow run` has **no `--region` flag**. The ML Platform team registers a
**separate blueprint per (workflow_name, region)** pair, and `atlas ml workflow get-blueprint -n <name>`
returns only the single most recent variant for a name — silently hiding the existence of the
other regional siblings.

The orchestrator's discovery logic had assumed (incorrectly) that one blueprint =
all-region execution, mirroring the convention used by some other ML workflows where
region is a runtime parameter.

## Resolution

After detection, the correct per-region blueprints were extracted from the runbook URLs in
Confluence page 7049101435 and the `realm` tag of each blueprint's bound Databricks job was
verified before re-running:

| Region | Blueprint ID | Verified `realm` tag |
|---|---|---|
| us_west_2 | `453a789e-409d-4ebf-9c0f-8552621d937b` | `us_west_2` ✅ |
| us | `992be8ce-bb75-4588-ab4e-fd2ad83460a4` | `us` ✅ |
| eu_west_1 | `4f7067a0-eb66-49e4-989d-380aeaf4d890` | `eu_west_1` ✅ |
| eu | `404106f4-40c7-44c3-9ac2-ad99cc96de26` | `eu` ✅ |

The four NEW correct regional eval runs were then fired and all SUCCEEDED:
- us_west_2: `ae0e1ac2-e7eb-46d1-ba27-187e6169dbd1`
- us: `599a8702-6af4-44a3-a385-242097de97a8`
- eu_west_1: `c590b9f0-2c1c-4176-bb2e-a49a37e61887`
- eu: `2d7e0b6a-55ab-4790-b5ce-e9074c1f7a67`

The 2026-06-02 launch doc (Confluence 7128443945) was then patched in-place to reference
the correct runs, with a footer comment recording the correction history.

## Prevention going forward

Three layers of defense are now in place (all in `../../SOP.md`):

1. **Verified blueprint reference table** in Prerequisites — lists all 4 region-specific
   blueprint IDs explicitly, so the orchestrator + any human can use the right one.

2. **Explicit warning in Phase 9** — the section opens with the all-caps note:
   > **CRITICAL — DO NOT REPEAT 2026-06-02 MISTAKE**: `atlas ml workflow run` has
   > **NO `--region` flag**. Running the same blueprint 4 times produces 4 us_west_2 runs,
   > not 4 region runs. Use the 4 region-specific blueprint IDs from the Verified
   > blueprint reference table.

3. **Paranoia region-verification snippet** in Phase 9 — a copy-paste bash block that
   extracts the Databricks job ID and asserts its `realm` tag matches the requested
   region before believing the run is correctly regional.

## Why this is filed as "resolved"

The bug cannot recur without simultaneously violating three independent guards
(table, warning, verification snippet). The forward-looking lesson — "do not trust
`get-blueprint -n <name>` alone; verify the region tag" — is preserved in the SOP
itself; this file is the historical record explaining why those guards exist.
