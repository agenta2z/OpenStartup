# Plan: Make Plan Templates Generic & Create Unified Research Task Preamble

**Date**: 2026-04-06
**Scope**: `OpenStartup/src/server/resources/prompt_templates/`
**Related Libraries**: `RichPythonUtils` (`TemplateManager`, `FileBasedVariableManager`)

---

## 1. Current State Analysis

### 1.1 Template Directory Layout (As-Is)

```
prompt_templates/
├── .variables.yaml                                    # Global: employee persona (name, role, mindset)
├── plan/main/
│   ├── initial.jinja2                                 # Plan creation prompt
│   ├── followup.jinja2                                # Plan refinement after review
│   ├── review.jinja2                                  # Plan review by reviewer agent
│   └── _variables/task_preamble/                      # EMPTY directory — no variable files
├── task_breakdown/main/
│   ├── initial.jinja2                                 # Task decomposition prompt (generic)
│   └── _variables/task_preamble/
│       ├── .config.yaml                               # "default: create_role" (metadata only, not code-read)
│       └── create_role/default.jinja2                 # Create-role-specific breakdown preamble
├── deep_research/main/
│   ├── initial.jinja2                                 # Deep research prompt (generic)
│   └── _variables/task_preamble/
│       ├── .config.yaml                               # "default: create_role" (metadata only)
│       ├── default.jinja2                             # Generic session-context preamble
│       └── create_role/default.jinja2                 # Create-role-specific research preamble
└── create_role/main/
    └── aggregate.jinja2                               # Role document synthesis (create_role-specific)
```

### 1.2 How the Template System Works

**TemplateManager** (from `RichPythonUtils`) manages template resolution:

1. **Template lookup**: `tm("initial", active_template_root_space="task_breakdown")` resolves to `task_breakdown/main/initial.jinja2` via the namespace hierarchy `{root_space}/{type}/{key}`.

2. **Variable resolution**: When `predefined_variables=True`, the TemplateManager auto-creates a `VariableLoader` that:
   - Scans the raw template for `{{ variable_name }}` references
   - Uses **cascade resolution** to find variable files:
     1. `{root_space}/{type}/_variables/` (most specific)
     2. `{root_space}/_variables/`
     3. `/_variables/` (global fallback)
   - Uses **underscore-split inference**: `task_preamble` → tries paths `task/preamble.*` and `task_preamble.*`
   - Resolved variables are injected as lowest-priority kwargs (overridable by `feed` and explicit `kwargs`)

3. **`.variables.yaml` sidecar**: Loaded at init, provides global variables like `employee` (name, role, mindset) — available across ALL templates.

4. **Jinja2 rendering**: Uses standard Jinja2 `Template.render()` which **silently treats undefined variables as empty strings** — so unresolved `{{ task_preamble }}` produces `""` without error.

### 1.3 How `create_role` Uses This Today

The `create_role/executor.py` (`build_create_role_inferencer`) builds a `BreakdownThenAggregateInferencer` pipeline:

1. **Breakdown** (`PromptWrapperInferencer`): `tm("initial", active_template_root_space="task_breakdown")`
   - Template: `task_breakdown/main/initial.jinja2` (generic task decomposition)
   - `{{ task_preamble }}` resolves via `task_breakdown/main/_variables/task_preamble/` — but there is **no** `default.jinja2` there, only `create_role/default.jinja2` as a subdirectory
   - **Current behavior**: `task_preamble` resolves to `""` (Jinja2 treats undefined → empty string)

2. **Workers** (`PromptWrapperInferencer`): `tm("initial", active_template_root_space="deep_research")`
   - Template: `deep_research/main/initial.jinja2` (generic deep research)
   - `{{ task_preamble }}` resolves via `deep_research/main/_variables/task_preamble/default.jinja2` (generic session context)
   - The `create_role/default.jinja2` in the same directory is **not** auto-selected — the `default.jinja2` wins

3. **Aggregator**: `tm("aggregate", active_template_root_space="create_role")`
   - Template: `create_role/main/aggregate.jinja2` (role-specific synthesis)
   - Contains role-creation-specific instructions hardcoded in the template body

### 1.4 Key Problems Identified

| # | Problem | Impact |
|---|---------|--------|
| P1 | **Plan templates are not task-agnostic**: `plan/main/initial.jinja2` has Meta-specific notes, hardcoded output format, and environment-specific instructions baked into the template body. These should be factored into injectable variables. | Cannot reuse plan templates for non-Meta, non-plan-specific tasks |
| P2 | **`plan/main/_variables/task_preamble/` is empty**: No default or task-specific preambles exist for the plan phase. `{{ task_preamble }}` always resolves to `""`. | Plan phase gets no task context |
| P3 | **`.config.yaml` files are non-functional**: The `default: create_role` in `.config.yaml` is documentation-only; no code reads it. The `create_role/default.jinja2` subdirectories under `task_preamble/` are not auto-selected. | Misleading metadata; `create_role` variant is currently unused by the variable resolver |
| P4 | **Duplication of create_role-specific content**: Role-creation-specific instructions exist in both `task_breakdown/...create_role/default.jinja2` and `deep_research/...create_role/default.jinja2`, plus `create_role/main/aggregate.jinja2`. | Maintenance burden; divergent content |
| P5 | **No mechanism to select task-specific variant**: The current cascade only supports `default.jinja2` auto-resolution. The `create_role/default.jinja2` subdirectories require an explicit selection mechanism (not yet implemented). | Can't dynamically switch task preambles via the variable resolver alone |

---

## 2. Design Goals

1. **Generic plan templates**: Factor out environment/task-specific content so `plan/main/*.jinja2` can serve any planning task (not just Meta-specific engineering plans).
2. **Unified research task preamble**: Create a `default.jinja2` in `plan/main/_variables/task_preamble/` that provides good generic context for any research-oriented planning task.
3. **Clean separation of concerns**: Task-type-specific instructions (like create_role's "Role Responsibility Document" format) should be in a separate variable, NOT baked into the generic template body.
4. **Leverage existing cascade**: Use the TemplateManager's native cascade and kwargs-override mechanisms — no changes to `RichPythonUtils`.
5. **Backward compatibility**: `create_role/executor.py` must continue to work correctly.

---

## 3. Proposed Design

### 3.1 Architecture: Two-Variable Pattern

Instead of one monolithic `{{ task_preamble }}`, use **two variables** in plan templates:

| Variable | Purpose | Resolution |
|----------|---------|------------|
| `{{ task_preamble }}` | **Generic, task-agnostic** context: session paths, environment info, general investigation guidelines | Resolved via `_variables/task_preamble/default.jinja2` — same for ALL tasks |
| `{{ task_instructions }}` | **Task-type-specific** instructions: output format, domain-specific criteria, quality requirements | Resolved via `_variables/task_instructions/default.jinja2` (generic) OR overridden by kwargs at call time |

This cleanly separates:
- **What context does the agent need?** → `task_preamble` (generic)
- **What specific task is the agent performing?** → `task_instructions` (task-specific, overridable)

### 3.2 Variable Resolution Strategy

For `plan` templates when called generically:
```python
tm("initial", active_template_root_space="plan")
```
- `{{ task_preamble }}` → `plan/main/_variables/task_preamble/default.jinja2` (unified research preamble)
- `{{ task_instructions }}` → `plan/main/_variables/task_instructions/default.jinja2` (generic plan instructions)

For `plan` templates when called from `create_role` executor (future):
```python
tm("initial",
   active_template_root_space="plan",
   task_instructions=create_role_specific_instructions)  # explicit kwarg override
```
- `{{ task_preamble }}` → same generic preamble (session context)
- `{{ task_instructions }}` → overridden by the explicit kwarg with role-creation-specific content

**Why kwargs override?** The TemplateManager merges: `predefined_vars (lowest) < feed < kwargs (highest)`. Passing `task_instructions=...` as a kwarg naturally overrides the file-resolved default. This is the cleanest mechanism — no filesystem tricks, no new features needed in RichPythonUtils.

### 3.3 Where Do Create-Role-Specific Instructions Live?

The role-creation-specific instructions remain in:
- `create_role/main/aggregate.jinja2` — the synthesis template (already has them, and that's the only truly role-specific template in the pipeline)

For future plan-phase use by create_role, the executor would load role-specific instructions and pass them as kwargs. This avoids duplicating content across multiple `_variables/` directories.

**For the `task_breakdown` and `deep_research` phases**, the existing `create_role/default.jinja2` subdirectories can stay for now (they document intent) OR be consolidated. See Step 7 below for the deduplication approach.

### 3.4 Proposed Directory Layout (To-Be)

```
prompt_templates/
├── .variables.yaml                                    # (unchanged) Global employee persona
├── _variables/                                        # NEW: Global fallback variables
│   └── task_preamble/
│       └── default.jinja2                             # Generic session context (reused from deep_research)
├── plan/main/
│   ├── initial.jinja2                                 # REFACTORED: generic, uses {{ task_preamble }} + {{ task_instructions }}
│   ├── followup.jinja2                                # REFACTORED: generic, uses {{ task_preamble }} + {{ task_instructions }}
│   ├── review.jinja2                                  # REFACTORED: generic, uses {{ task_preamble }} + {{ task_instructions }}
│   └── _variables/
│       ├── task_preamble/
│       │   └── default.jinja2                         # NEW: Unified researches preamble (plan-phase-specific)
│       └── task_instructions/
│           └── default.jinja2                         # NEW: Generic plan quality & format notes (extracted from current templates)
├── task_breakdown/main/
│   ├── initial.jinja2                                 # (unchanged)
│   └── _variables/task_preamble/
│       ├── default.jinja2                             # NEW: Generic breakdown preamble (was missing)
│       └── create_role/default.jinja2                 # (keep for now — documents create_role intent)
├── deep_research/main/
│   ├── initial.jinja2                                 # (unchanged)
│   └── _variables/task_preamble/
│       ├── default.jinja2                             # (unchanged — generic session context)
│       └── create_role/default.jinja2                 # (keep for now — documents create_role intent)
└── create_role/main/
    └── aggregate.jinja2                               # (unchanged — role-specific synthesis)
```

### 3.5 Critical Design Decision: `.config.yaml` Files

**Decision: Remove `.config.yaml` files.**

Rationale:
- They are not read by any code (verified: zero grep hits across `RichPythonUtils` and `OpenStartup` Python sources)
- They create a false impression that `create_role` is auto-selected as the default variant
- With the new design, every `task_preamble/` directory has a proper `default.jinja2` that the variable resolver naturally finds
- Task-specific variants like `create_role/` are selected via explicit kwargs, not filesystem defaults

---

## 4. Implementation Steps

### Step 1: Create global fallback `task_preamble`

**File**: `prompt_templates/_variables/task_preamble/default.jinja2`

Content: Generic session context (based on `deep_research/main/_variables/task_preamble/default.jinja2`):

```jinja2
## Session Context
{% if session_root_path %}- session_root_path: {{ session_root_path }}
{% endif %}{% if workflow_target_path %}- workflow_target_path: {{ workflow_target_path }}
{% endif %}{% if docs_path %}- docs_path: {{ docs_path }}
{% endif %}
```

This serves as the ultimate fallback — any template referencing `{{ task_preamble }}` that doesn't have a more specific `_variables/task_preamble/default.jinja2` in its own root_space/type directory will get this.

### Step 2: Create `plan/main/_variables/task_preamble/default.jinja2` (Unified Researches Preamble)

**File**: `plan/main/_variables/task_preamble/default.jinja2`

This is the **unified researches task preamble** — plan-phase-specific context that applies to ANY planning task:

```jinja2
## Planning Context

{% if session_root_path %}- Working directory: {{ session_root_path }}
{% endif %}{% if workflow_target_path %}- Target: {{ workflow_target_path }}
{% endif %}{% if docs_path %}- Documentation: {{ docs_path }}
{% endif %}

You are creating a comprehensive, implementable plan. Approach this with:
- **Evidence-based analysis**: Investigate thoroughly before proposing solutions. Include concrete findings, specific file paths, and reasoned analysis.
- **Practical specificity**: A good plan demonstrates that you actually read and understood the relevant materials, not just skimmed them.
- **Balanced scope**: Cover all aspects of the request without over-engineering or making unnecessary changes.
```

### Step 3: Refactor `plan/main/initial.jinja2`

**Goal**: Extract environment-specific "NOTES" sections into `{{ task_instructions }}`, keep core template generic.

**Current structure** (content baked in):
```
You are tasked with creating a comprehensive plan...
{{ task_preamble }}
{{ input }}
## Your Task: Create a Detailed Plan
[5 plan sections — keep as-is, these are genuinely generic]
## Plan Quality & Size Guidelines [keep — generic]
## Output Requirements [keep — generic]
## Response Format [keep — generic]
## NOTES (Meta-specific environment):     ← EXTRACT to task_instructions
## NOTES (on resolving dependencies):     ← EXTRACT to task_instructions
## NOTES (on accessing files...):         ← EXTRACT to task_instructions
## NOTES (on engineering quality):        ← EXTRACT to task_instructions
## NOTES (emphasizing requirements):      ← EXTRACT to task_instructions
## NOTES (on agent behavior):            ← KEEP (partially) — these are generic agent guidelines
```

**Refactored structure**:
```jinja2
You are tasked with creating a comprehensive plan for the following user request:

**Original User Request:**
<UserRequest>
{{ task_preamble }}
{{ input }}
</UserRequest>

---

## Your Task: Create a Detailed Plan

Create a comprehensive, implementable plan that covers:

1. **High-Level Approach**: Overall strategy and architecture decisions
2. **Files to Create/Modify**: Specific files with their intended changes
3. **Key Implementation Steps**: Ordered list of concrete tasks
4. **Potential Risks and Mitigations**: What could go wrong and how to prevent it
5. **Testing Strategy**: How to verify the implementation works

## Plan Quality & Size Guidelines
[keep existing content — this is generic]

## Output Requirements
[keep existing content — this is generic]

## Response Format
[keep existing content — this is generic]

{{ task_instructions }}

## NOTES (on agent behavior):
[keep the generic agent behavior notes — deep investigation, file verification, etc.]
```

### Step 4: Create `plan/main/_variables/task_instructions/default.jinja2`

**File**: `plan/main/_variables/task_instructions/default.jinja2`

Contains the extracted environment/engineering-specific notes as the default plan instructions:

```jinja2
## NOTES (on environment):
- Always target specific files or narrow subdirectories for searches. Avoid recursive searches on large top-level directories.
- If a search command seems to hang, move on and try a more targeted search.

## NOTES (on resolving dependencies):
- Do NOT conclude a module/dependency is unavailable just because you cannot find it in the codebase.
- Check the environment, build tool configs, and alternative import paths before dismissing.
- Only dismiss a dependency as "unavailable" after ALL checks fail.

## NOTES (on accessing files outside the repo root):
- Try efficient file-reading tools first. If they fail with path errors, fall back to command-line tools (cat, grep, sed, ls).

## NOTES (on engineering quality):
- Prefer elegant, well-structured solutions over hacky ones.
- Mind the blast radius of changes, but proceed if broader changes are genuinely beneficial.

## NOTES (emphasizing requirements):
- Do NOT fabricate or assume file paths, function signatures, or module structures — always verify.
- If benchmarking is needed, plan to write results to a file (not just stdout).
```

### Step 5: Similarly refactor `followup.jinja2` and `review.jinja2`

Apply the same `{{ task_instructions }}` pattern:
- `followup.jinja2`: Add `{{ task_instructions }}` before the agent behavior notes section
- `review.jinja2`: Add `{{ task_instructions }}` before the agent behavior notes section

Both already have similar environment-specific NOTES sections that should be extracted.

### Step 6: Add `default.jinja2` to `task_breakdown/main/_variables/task_preamble/`

**File**: `task_breakdown/main/_variables/task_preamble/default.jinja2`

Currently this directory only has `create_role/default.jinja2`. Add a generic default:

```jinja2
## Session Context
{% if session_root_path %}- session_root_path: {{ session_root_path }}
{% endif %}{% if workflow_target_path %}- workflow_target_path: {{ workflow_target_path }}
{% endif %}{% if docs_path %}- docs_path: {{ docs_path }}
{% endif %}
```

This ensures the variable resolver finds a `default.jinja2` and doesn't resolve to empty.

### Step 7: Remove `.config.yaml` files

Delete:
- `task_breakdown/main/_variables/task_preamble/.config.yaml`
- `deep_research/main/_variables/task_preamble/.config.yaml`

### Step 8: Verify `create_role/executor.py` compatibility

The executor uses:
- `template_root_space="task_breakdown"` → `task_breakdown/main/initial.jinja2`
  - `{{ task_preamble }}` now resolves to the NEW `default.jinja2` (generic context) instead of `""` — this is **better** than before
- `template_root_space="deep_research"` → `deep_research/main/initial.jinja2`
  - `{{ task_preamble }}` continues to resolve to `default.jinja2` (unchanged)
- `active_template_root_space="create_role"` for aggregation → `create_role/main/aggregate.jinja2` (unchanged)

**No changes needed to `executor.py`**. The behavior either stays the same or improves (task_breakdown now gets session context instead of empty string).

---

## 5. Compatibility with `TemplateManager` from `RichPythonUtils`

### Variable Resolution Trace (Verification)

For `tm("initial", active_template_root_space="plan")`:

1. **Template lookup**: Resolves `plan/main/initial.jinja2` ✓
2. **Variable scan**: Finds `task_preamble`, `task_instructions`, `input`, `output_path`
3. **`task_preamble` resolution** (cascade):
   - `plan/main/_variables/task_preamble/default.jinja2` → **FOUND** ✓
4. **`task_instructions` resolution** (cascade):
   - `plan/main/_variables/task_instructions/default.jinja2` → **FOUND** ✓
5. **`input`, `output_path`**: Not file-resolved — passed via kwargs ✓
6. **`employee`**: Resolved via `.variables.yaml` sidecar ✓

For `tm("initial", active_template_root_space="plan", task_instructions="custom...")`:
- `task_instructions` kwarg overrides file-resolved value (kwargs > predefined_vars) ✓

### Key Mechanism Used
- **Cascade resolution** (existing) — `{root_space}/{type}/_variables/` → `{root_space}/_variables/` → `/_variables/`
- **Kwargs override** (existing) — `merged_kwargs = {**predefined_vars, **feed, **kwargs}`
- **Underscore split** (existing) — `task_preamble` → `task_preamble/default.*` OR `task/preamble.*`
- **No changes to RichPythonUtils needed**

---

## 6. Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Breaking `create_role` pipeline | Low | The executor uses `task_breakdown` and `deep_research` root spaces, not `plan`. Adding files to `plan/_variables/` doesn't affect existing resolution paths. Adding `default.jinja2` to `task_breakdown/_variables/task_preamble/` is additive. |
| Jinja2 undefined `task_instructions` in old callers | Low | Jinja2 silently renders undefined variables as `""`. New variable `task_instructions` is optional — callers that don't pass it get the file-resolved default. If there's no file AND no kwarg, it renders as empty (same as current `task_preamble` behavior). |
| `.config.yaml` removal breaks something | Very Low | Verified: zero grep hits for `.config.yaml` across all Python sources in both `RichPythonUtils` and `OpenStartup`. Purely metadata. |
| Plan templates becoming too generic (losing useful defaults) | Medium | The `task_instructions` default file preserves the current engineering-specific notes. Behavior only changes when explicitly overridden. |
| Underscore split ambiguity for `task_instructions` | Very Low | `task_instructions` splits to `["task/instructions", "task_instructions"]`. Both point to the same directory structure. No ambiguity if only one file exists at any cascade level. |

---

## 7. Testing Strategy

1. **Manual rendering test**: Create a small Python script that:
   - Instantiates `TemplateManager` at the templates root with `predefined_variables=True`
   - Calls `tm("initial", active_template_root_space="plan", input="test task", output_path="/tmp/plan.md")`
   - Verifies `{{ task_preamble }}` renders non-empty content from the unified preamble
   - Verifies `{{ task_instructions }}` renders the default engineering notes
   - Calls again with `task_instructions="custom override"` and verifies override

2. **Regression test for create_role**: Run the existing `create_role` executor flow (if tests exist) to verify:
   - `task_breakdown` phase still works (now with non-empty `task_preamble` — improvement)
   - `deep_research` phase still works (unchanged resolution)
   - Aggregation phase still works (unchanged)

3. **Visual inspection**: Render all three plan templates and compare output before/after refactoring to ensure no content is lost.

---

## 8. Summary of Changes

| File | Action | Description |
|------|--------|-------------|
| `_variables/task_preamble/default.jinja2` | **CREATE** | Global fallback session context preamble |
| `plan/main/initial.jinja2` | **MODIFY** | Extract env-specific notes → `{{ task_instructions }}`, keep generic structure |
| `plan/main/followup.jinja2` | **MODIFY** | Same pattern — add `{{ task_instructions }}` |
| `plan/main/review.jinja2` | **MODIFY** | Same pattern — add `{{ task_instructions }}` |
| `plan/main/_variables/task_preamble/default.jinja2` | **CREATE** | Unified researches preamble (plan-phase-specific context) |
| `plan/main/_variables/task_instructions/default.jinja2` | **CREATE** | Default plan quality/format notes (extracted from current plan templates) |
| `task_breakdown/main/_variables/task_preamble/default.jinja2` | **CREATE** | Generic breakdown preamble (was missing — `task_preamble` was resolving to empty) |
| `task_breakdown/main/_variables/task_preamble/.config.yaml` | **DELETE** | Non-functional metadata file |
| `deep_research/main/_variables/task_preamble/.config.yaml` | **DELETE** | Non-functional metadata file |
| `create_role/executor.py` | **NO CHANGE** | Existing flow unaffected; future plan phase uses kwarg override |

---

## 9. Critical Bug Found During Investigation

### 9.1 `_find_variable_file` Matches Directories (Latent `IsADirectoryError`)

**Severity**: CRITICAL (latent — not triggered yet because E2E tests haven't been run against current filesystem)

The `FileBasedVariableManager._find_variable_file()` uses `file_path.exists()` to check for variable files (line ~539 of `file_based.py`). This returns `True` for **directories**, not just files. The `file_extensions` list includes `""` (empty string), so when looking for variable `task_preamble`:

1. Underscore splits: `["task/preamble", "task_preamble"]`
2. For split `"task_preamble"` with extension `""`, it checks: `cascade_path / "task_preamble"`
3. This IS a directory → `exists()` returns `True` → **MATCH**
4. `_read_file_content()` then calls `directory.read_text()` → **`IsADirectoryError`**

**Verified empirically**: The directory at `task_breakdown/main/_variables/task_preamble` matches before any file inside it (like `create_role/default.jinja2`) can be considered.

**Impact**: Both `task_breakdown` and `deep_research` have `_variables/task_preamble/` directories that would trigger this crash when the `TemplateManager` resolves `{{ task_preamble }}` with `predefined_variables=True`.

**Why hasn't it crashed yet**: The `create_role` test is a manual E2E script requiring API credentials — it has likely never been run against the current filesystem template layout (templates may have been created after the executor was last tested, or tested with different/mocked templates).

**Fix options**:
1. **(Preferred) Remove the `task_preamble/` directories**: Replace them with flat files (`task_preamble.jinja2`) or ensure proper `default.jinja2` files exist AND the directory issue is handled
2. **Fix in RichPythonUtils**: Change `_find_variable_file` to use `file_path.is_file()` instead of `file_path.exists()` — this is the correct behavior anyway
3. **Both**: Fix the bug in RichPythonUtils AND restructure the OpenStartup templates

### 9.2 `create_role/` Subdirectories Are Unreachable

The variable resolver's underscore split mechanism generates paths like `task_preamble` and `task/preamble`, but it does NOT generate `task_preamble/create_role/default`. The subdirectory variant pattern (`_variables/task_preamble/create_role/default.jinja2`) has no resolution path in the current `FileBasedVariableManager` code.

This means:
- The `.config.yaml` files are non-functional (no code reads them)
- The `create_role/default.jinja2` files inside `task_preamble/` are unreachable
- The content in these files is effectively dead code

---

## 10. Comparison with Alternative Plan (from second agent)

A second agent produced an alternative plan. Here is a critical comparison:

### 10.1 Points of Agreement

| Point | Both Plans Agree |
|-------|-----------------|
| Two-variable pattern | `{{ task_preamble }}` (generic) + `{{ task_instructions }}` (task-specific, overridable via kwargs) |
| `.config.yaml` removal | Both correctly identify these as non-functional |
| Kwargs override mechanism | Both use TemplateManager's `predefined_vars < feed < kwargs` priority |
| Generic plan templates | Both aim to make `plan/main/*.jinja2` task-agnostic |
| `create_role/` subdirectories are unreachable | Both identify this (the second plan states it more forcefully) |

### 10.2 Key Differences

| Aspect | My Plan | Other Agent's Plan | Assessment |
|--------|---------|-------------------|------------|
| **`aggregate.jinja2` fate** | Keep unchanged | Delete; move content to `executor.py` constant + use `plan/initial.jinja2` with kwargs | **Other plan is better** — reduces template count and proves the generic design by dog-fooding it |
| **`create_role/` subdirectory content** | Keep subdirectories "for documentation" | Merge into `default.jinja2` at parent level, delete subdirectories | **Other plan is better** — fixes the latent directory-matching bug and simplifies |
| **Directory-as-bug awareness** | Identified `.config.yaml` as non-functional but didn't catch the `IsADirectoryError` | Identified directories as unreachable AND implicitly fixes by flattening | **Other plan is better** — actively fixes the bug |
| **Executor changes** | No changes to `executor.py` | Updates aggregation to use plan template | **Other plan is more ambitious** — trades more changes for a cleaner unified architecture |
| **Global `_variables/` fallback** | Creates global fallback | Creates global fallback | Same |
| **Plan template refactoring detail** | Detailed line-by-line extraction plan | Structural outline (less detailed) | **My plan is more detailed** for implementation |

### 10.3 Unified Recommendation (Best of Both)

1. **Adopt the two-variable pattern** (both plans agree)
2. **Flatten `create_role/` subdirectories** (other plan — fixes latent bug)
3. **Delete `aggregate.jinja2`** and use `plan/initial.jinja2` with kwargs override for aggregation (other plan — elegant dogfooding)
4. **Keep my plan's detailed extraction approach** for the actual template refactoring (my plan — more implementable)
5. **Fix `_find_variable_file` in RichPythonUtils** to use `is_file()` instead of `exists()` (new — neither plan explicitly calls this out as a RichPythonUtils fix, but it should be done)
6. **Create `task_breakdown/main/_variables/task_preamble/default.jinja2`** as a proper flat file (both plans agree it's missing)

---

## 11. Open Questions / Future Considerations

1. **Should `_find_variable_file` be fixed in RichPythonUtils?** This is the root cause of the directory-matching bug. Changing `exists()` to `is_file()` is a one-line fix with no behavioral change for correct usage. Recommend filing this as a separate PR.

2. **Should `task_instructions` also be added to `task_breakdown` and `deep_research` templates?** The same two-variable pattern could be applied consistently across all template types for maximum flexibility. This is a natural follow-up.

3. **Should `.config.yaml` become a supported feature?** If directory-based variable variants are desired, proper support should be added to `FileBasedVariableManager` (e.g., reading `.config.yaml` to determine subdirectory variant). This would be a `RichPythonUtils` enhancement — but may not be needed if kwargs override is sufficient.
