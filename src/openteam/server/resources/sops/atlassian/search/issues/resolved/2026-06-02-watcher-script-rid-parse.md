# Resolved: Chain watcher failed to parse `ML Studio Run ID:` output

- **Date discovered**: 2026-06-02
- **Cycle**: First automated L2 cross-tenant refresh (ml-registry EnsembleL23p v35)
- **Severity**: Low (caught immediately on first Phase 2 → Phase 3 transition; one short re-run)
- **Status**: ✅ Resolved — v2 watcher deployed; awk parser hardened

## What happened

The first version of `run_chain_watcher.sh` was meant to detect Phase 2's completion and
auto-fire Phase 3 with the resulting run ID. On the first real Phase 2 → Phase 3 handoff,
the watcher fired Phase 3 with an **empty run-id string**, causing the chained
`atlas ml workflow run` invocation to fail with a parse error rather than starting the
expected Tarot V2 packaging run.

## Root cause

The watcher's awk parser was matching on the literal prefix `Run ID:` but the actual
output of `atlas ml workflow run` is:

```
ML Studio Run ID: <uuid>
```

The longer prefix caused awk to match the wrong field (or no field at all) and emit an
empty string, which the watcher passed through to the next command without validation.

## Resolution

The v2 watcher (deployed mid-cycle on 2026-06-02) made two changes:

1. **Updated awk match** to look for `ML Studio Run ID:` explicitly.
2. **Added a non-empty validation guard** before each chained CLI call:
   ```bash
   if [ -z "$rid" ]; then
     echo "ERROR: failed to extract run-id from previous phase output; aborting chain"
     exit 1
   fi
   ```

Phase 3 then chained correctly and produced run `1b1a1e42-4adf-4429-a11d-5ec1789045e7`.

## Prevention going forward

The lesson — **always validate non-empty rid before entering any poll loop or chained CLI
call** — is captured as a hard rule for any new automation script in this SOP family.
The orchestrator script (`CoreProjects/xtenant_refresh_automation/refresh_xtenant_orchestrator.py`)
applies this rule across all chained-phase boundaries.

## Why this is filed as "resolved"

The v2 watcher has been in use for the rest of the 2026-06-02 cycle without issue,
and the hardened pattern is enshrined in the orchestrator script. Future watcher
versions should follow the same validate-then-chain pattern.
