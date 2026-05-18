# Archived plans — tool workspace allocation enhancement

Archived 2026-05-17 16:21. Canonical plan now lives one level up at:

```
../unified_workspace_allocation_INTEGRATED_v5_FINAL_plan.md
```

## Plans archived here

| File | Original date | Author | Role |
|---|---|---|---|
| `runtime_workspace_relocation_plan.md` | 2026-05-17 10:10 | early analysis | First sketch of the problem; pre-v0 |
| `v0_tool_workspace_allocation_enhancement_plan.md` | 2026-05-17 10:15 | early plan | Standalone-CLI scope only |
| `v1_unified_workspace_allocation_plan.md` | 2026-05-17 10:26 | OpenStartup | First unified plan (697 lines) — both standalone + server-affiliated paths; nested layout |
| `v3_unified_workspace_allocation_INTEGRATED_plan.md` | 2026-05-17 11:12 | Rovo Dev | Integrated v1+Cursor+Claude round 1; nested layout; 12 RED tests; permanent regression tests; migration script; feature flag; 18-row risk register |
| `v4_unified_workspace_allocation_INTEGRATED_plan_AUDITED.md` | 2026-05-17 16:11 | Rovo Dev | Rovo Dev's flat-layout proposal; later audited & corrected; superseded because v5 (by Claude, 13:23) honors the user's previously-stated nested choice and integrates all v4 audit concerns. |

## Why v5 was chosen as canonical

1. **Architecture honors user's explicit prior choice (nested under sessions).** Rovo Dev's v4 silently reversed this; v5 restored it after Claude's review pointed out the process violation.
2. **Integrates all v3 operational discipline** (RED tests, permanent regression tests, deploy hygiene, feature flag, rollback matrix) PLUS Claude's `base_dir: Optional[Path]` cleaner allocator API + `SessionStore.get_session_tasks_dir()` convenience method.
3. **Risk #1 (slash-path session_id missing) verified to be 🟢 LOW** via source code inspection — closure scope captures `sid`, `SessionStore.create_session` eagerly mkdirs. v4 originally rated it 🔴 HIGH and used that as a (overstated) justification for the flat-layout reversal.

## When to consult an archived plan

- **Reading v1** is useful for the original 75-line `find_runtime_root()` + `allocate_tool_workspace()` source code (now in v5 §4 with the cleaner `base_dir` API).
- **Reading v3** is useful for the RED-test discipline and rollback matrix patterns (now in v5 §7 and §11).
- **Reading v4-audited** is useful for the empirical verification of Risk #1 (`sid` closure scope), the 538-line `SOURCES.txt` pollution finding, and the helper-code TOCTOU fix. All of these are folded into v5.

If you find that v5 contradicts one of these archived plans on a substantive point, **trust v5** — it's the most recent integration and the user's stated architectural choice (nested) is encoded there.
