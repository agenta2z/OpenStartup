# Template Mode Flags: Wire `enable_deep_mode` / `enable_elegant_mode` End-to-End

**Status**: Proposal
**Date**: 2026-05-08
**Scope**: AgentFoundation prompt-template machinery + new flag plumbing
**Estimated effort**: ~2 hours

---

## 1. Goal

Make this work end-to-end:

```jinja2
{%- if enable_deep_mode %}
- {{ instructions.modes.deep_mode }}
{%- endif %}
{%- if enable_elegant_mode %}
- {{ instructions.modes.elegant_mode }}
{%- endif %}
```

Today: the template files exist (`deep_mode.jinja2`, `elegant_mode.jinja2`) but
nothing connects them to inferencers, YAML, or `instructions.modes.*` lookups.

---

## 2. Verified Current State (2026-05-08, re-verified deeply)

This section was rewritten after deep investigation revealed the existing
`.variables.yaml` + `__alias__` mechanism is **already implemented and working**
in production today. Earlier rev of this plan over-scoped because it didn't know.

### What's already implemented (✅)

| Layer | Status | Evidence |
|---|---|---|
| Mode template files | ✅ Exist | `AgentFoundation/.../_variables/instructions/modes/{deep,elegant}_mode.jinja2` (deep_mode has content, elegant_mode is empty) |
| `.variables.yaml` sidecar discovery | ✅ Implemented | `prompt_rendering.py:127-144` walks template_dir + cross-space root, loads each candidate via `vm.load_yaml_sidecar()` |
| `__alias__` resolution | ✅ Implemented | `RichPythonUtils/.../variable_manager/file_based.py:1396-1420` parses `__alias__` block into scoped alias dict; `_resolve_alias_cascaded()` resolves at lookup time |
| Production precedent for `__alias__` | ✅ Verified | `_archive/.variables.yaml:42` uses `__alias__: { strategy: employee.mindset }` — proves the mechanism works end-to-end |
| `instructions.modes.X` resolution path | ✅ Implemented | The variable manager resolves `instructions.modes.elegant_mode` → renders `_variables/instructions/modes/elegant_mode.jinja2` |
| `template_extra_feed` propagation to children | ✅ Implemented | `TemplatedInferencerBase._propagate_to_children()` cascades it |
| `template_root_space` attrib on inferencers | ✅ Implemented | `templated_inferencer_base.py:93` declares it; passed into `TemplateManager` at render time |

### What's still missing (❌)

| Gap | Why it matters | Where it goes |
|---|---|---|
| `__template_space__` auto-injection into Jinja feed | The new `.variables.yaml` aliases `__action__ → __template_space__` — but if `__template_space__` is never set, the alias resolves to nothing | Add to `_build_template_feed()` (Option A) — see Phase 2 |
| `enable_deep_mode` / `enable_elegant_mode` flag values in feed | The `{%- if enable_deep_mode %}` block needs the boolean to be set | Auto-derive from a `modes: dict[str, bool]` attrib |
| `modes: dict[str, bool]` attrib on `TemplatedInferencerBase` | Single declarative surface for enabling modes from YAML | New attrib (~3 lines) |
| Declarative loading of `instructions.modes.*` mode files | Without `template_variables: { "instructions.modes.deep_mode": null }` declaration, the lookup may silently fall through to `ChainableUndefined` and render empty (✓ insight from Plan A `cached-hennessy.md` Step 3b) | Verify in Phase 0 (smoke test); if needed, add to YAML topology configs |
| `{%- if enable_deep_mode %}...{%- endif %}` in `initial.jinja2` | The user-facing payoff | User-supplied snippet, just needs to be added |
| Empty `elegant_mode.jinja2` has no content | When enabled, renders nothing | Phase 6 — populate with concrete instruction text |
| Test coverage for conditional Jinja blocks | Regression guard | New M-series tests |
| Test coverage for `__template_space__` injection | Regression guard | New ST-series test |

### What changed in the design from v1 of this plan

- **DROPPED `_InstructionsProxy`** — the `.variables.yaml` + folder structure already provides `instructions.modes.*` resolution natively. Building a Python proxy would duplicate working code.
- **DROPPED Jinja-include trick** — same reason. The variable manager handles file-based lookups already.
- **REDUCED scope** — only need to (a) add the `modes` attrib + `enable_X` derivation, (b) inject `__template_space__` into the feed. Total: ~50 lines instead of ~200.

---

## 3. Design Decisions

### Decision 1 — Use `template_extra_feed` (NOT bare attribs)

**Rationale:** The whole point is to make these values appear in Jinja render
context. `template_extra_feed` is the existing, documented mechanism for that.
Bare attribs would require adding manual injection into `_build_template_feed`
for every new flag — same drift hazard as the CLI/slash issue we just fixed.

### Decision 2 — Mode flags as ONE dict, not many bare attribs

Instead of:
```python
enable_deep_mode: bool = attrib(default=False)
enable_elegant_mode: bool = attrib(default=False)
enable_careful_mode: bool = attrib(default=False)
# ... and every new mode adds another attrib
```

Use:
```python
modes: dict[str, bool] = attrib(factory=dict)
# {'deep_mode': True, 'elegant_mode': False}
```

Then auto-derive `enable_<name>` keys for `template_extra_feed`. New modes
require zero attrib changes — only a new template file + an entry in `modes`.

### Decision 3 — `instructions` variable resolves via lazy template-include helper

The Jinja context gets `instructions = _InstructionsProxy(template_manager)`.
On `instructions.modes.deep_mode` lookup, the proxy renders
`_variables/instructions/modes/deep_mode.jinja2` and returns the rendered text.
This means:
- New mode files dropped in `_variables/instructions/modes/` are auto-discovered
- No duplicate registration needed
- Templates can be parameterized themselves (e.g., `deep_mode.jinja2` could
  reference `{{ depth_level }}` if we want)

### Decision 4 — `TemplatedInferencerBase` is the right home

NOT `InferencerBase`. The base class doesn't deal with templates at all. Modes
are a Jinja-context concern; they belong on the class that builds the context.

### Decision 5 — Default ALL modes to False

Backwards-compatible. Existing runs see no change. Modes activate only when
explicitly enabled in YAML or via override.

---

## 4. The Plan

### Phase 0 — RESOLVED (no smoke test needed) *(0 min)*

Plan A `cached-hennessy.md` rev 06:12 verified the resolution path with a
file:line citation: `load_variables({"instructions.modes.deep_mode": None})`
returns `{"instructions": {"modes": {"deep_mode": "<text>"}}}` — proven by
the `notes.local_search_efficiency` pattern at
`test_template_manager_load_variable.py:350-381`.

**Implication:** No `template_variables` declaration needed. Just call
`load_variables()` directly from `_build_template_feed` for each enabled
mode. Phase 1.2b in v3 of this plan is therefore replaced by Phase 1.2c
(direct `load_variables()` call).

**Also verified by Plan A:** Mode files are read as **raw text** (NOT
rendered as Jinja2) at `read_text()` line 642 of the variable manager. This
means `{%- if enable_X %}` patterns in mode files won't be re-evaluated —
the file content is dropped into the parent template verbatim.

### Phase 1 — Inferencer attrib + propagation *(~30 min)*

**Step 1.1**: Add `modes: dict[str, bool]` attrib to `TemplatedInferencerBase`

`AgentFoundation/.../inferencers/templated_inferencer_base.py`:
```python
modes: dict[str, bool] = attrib(factory=dict)
# Maps mode_name → enabled. Auto-derived into `enable_<name>` keys in the
# Jinja render context, AND `instructions.modes.<name>` becomes available
# (renders the corresponding _variables/instructions/modes/<name>.jinja2).
```

**Step 1.2**: Inject mode flags into `_build_template_feed`

```python
def _build_template_feed(self, inference_input):
    feed = ...  # existing logic
    # Auto-derive enable_X keys for each mode
    for mode_name, enabled in (self.modes or {}).items():
        feed[f"enable_{mode_name}"] = bool(enabled)
    # NOTE: instructions.modes.X resolution comes from
    # FileBasedVariableManager + .variables.yaml — NO Python proxy needed.
    return feed
```

**Step 1.2c** (REPLACES v3's 1.2b — Plan A `cached-hennessy.md` rev 06:12 insight):
Call `load_variables()` directly inside `_build_template_feed` for each
enabled mode, then deep-merge the returned `{"instructions": {"modes": {...}}}`
nested dict into `feed`. This is cleaner than the v3 approach because:

- No `__attrs_post_init__` mutation of `template_variables`
- Lazy: only loads content for modes actually enabled
- Localized: all logic lives in one method
- Survives modes being toggled at runtime (rare but possible)

```python
# Inside _build_template_feed, after the enable_X derivation:
for mode_name, enabled in (self.modes or {}).items():
    feed[f"enable_{mode_name}"] = bool(enabled)
    if not enabled:
        continue
    if not (hasattr(self, "template_manager") and self.template_manager):
        continue

    var_key = f"instructions.modes.{mode_name}"
    try:
        mode_vars = self.template_manager.load_variables(
            {var_key: None},
            root_space=self.template_root_space or "",
            # Use template_version only if attrib exists; default empty
            default_version=getattr(self, "template_version", "") or "",
        )
    except FileNotFoundError:
        # Mode declared but file missing — debug-log, don't fail the run
        logger.debug(
            "Mode '%s' enabled but no instruction file found at "
            "_variables/instructions/modes/%s; rendering will skip content.",
            mode_name, mode_name,
        )
        continue
    except Exception as e:
        # Unexpected: warn so we don't silently swallow real bugs
        # (Plan A v2 used `except Exception: pass` which masks failures —
        # explicitly NOT adopted; we log unexpected errors visibly.)
        logger.warning(
            "Failed to load mode instructions for '%s': %s", mode_name, e,
        )
        continue

    # Deep-merge into feed so multiple modes coexist
    for k, v in mode_vars.items():
        if isinstance(v, dict) and isinstance(feed.get(k), dict):
            _deep_merge(feed[k], v)
        else:
            feed.setdefault(k, v)
```

**Critical design choice (rejection of Plan A v2 anti-pattern):**
Plan A v2 used `except Exception: pass`. This is the exact "ad-hoc, hacky"
pattern the user explicitly rejected. We instead:
- Catch the **specific** expected error (`FileNotFoundError`) at debug level
- Log unexpected errors at warning level so operators can diagnose
- Never swallow exceptions silently

**Step 1.3**: Cascade modes to children

The codebase has TWO YAML conventions and we COMMIT to one (rejecting Plan A
v2's "use whichever you prefer" non-decision):

- **`_modes:` (underscore prefix) at top-level YAML** = cascading default;
  inherited by all descendants unless overridden. **DEFAULT for topology
  authors.**
- **`modes:` (no underscore) on a specific inferencer** = per-instance
  override.

**VERIFICATION REQUIRED before merging this plan:**
Inspect `_instantiate.py` to confirm the `_<key>:` cascade convention applies
to arbitrary keys (not just hardcoded ones). If it doesn't, fall back to
a single canonical `modes:` attrib that callers explicitly thread through —
NO silent per-key magic.

In `_propagate_to_children` (or wherever `_template_extra_feed` cascade
lives), add the same cascade for `_modes`. ~5 lines.

(Plan A v2 punted on this with "both patterns are valid — pick whichever
suits your topology." For a real, elegant solution, we commit to one
default and document the override mechanism.)

### Phase 2 — Inject `__template_space__` into the render feed *(~20 min)*

This is the gap that prevents the user's `.variables.yaml` aliasing from
working. The new `.variables.yaml` says:
```yaml
__alias__:
  __action__: __template_space__
```
which means: "when a template references `__action__`, resolve it as
`__template_space__`". But `__template_space__` itself is never set. We need
to set it.

**Two implementation options — pick one:**

**Option A (preferred): inject in `TemplatedInferencerBase._build_template_feed`**

```python
# templated_inferencer_base.py:_build_template_feed
def _build_template_feed(self, inference_input):
    feed = ...  # existing logic
    # Auto-inject the active template space so .variables.yaml can alias it
    if self.template_root_space:
        feed["__template_space__"] = self.template_root_space
    # Auto-derive enable_X for declared modes
    for mode_name, enabled in (self.modes or {}).items():
        feed[f"enable_{mode_name}"] = bool(enabled)
    return feed
```

- ✅ Single point of injection
- ✅ Co-located with `template_root_space` attrib (semantic locality)
- ✅ No changes to `TemplateManager` (cleaner blast radius)
- ❌ Only inferencers that go through this code path get `__template_space__` —
  but that's all of them, so this is fine

**Option B: inject in `TemplateManager.__call__`**

- ✅ Universal — anyone using TemplateManager directly also benefits
- ❌ Touches a more sensitive shared dependency
- ❌ Risk of unrelated callers being affected

**Recommendation: Option A.** Lower blast radius. Same observable behavior for
the inferencer-driven path (which is 100% of our use case).

**Note on `instructions.modes.X`**: this works automatically once the
`.variables.yaml` is in place AND the template is loaded by an inferencer
whose `template_root_space` is set. No proxy or extra Python needed —
`FileBasedVariableManager` handles the file-based lookup. We do NOT need to
build the `_InstructionsProxy` class proposed in v1 of this plan.

### Phase 3 — Wire the actual `initial.jinja2` *(~10 min)*

`AgentFoundation/.../prompt_templates/plan/main/initial.jinja2` — add the
block the user wants:

```jinja2
{%- if enable_deep_mode %}
- {{ instructions.modes.deep_mode }}
{%- endif %}
{%- if enable_elegant_mode %}
- {{ instructions.modes.elegant_mode }}
{%- endif %}
```

(The user already wrote this block; we just need the surrounding machinery.)

### Phase 4 — YAML / CLI surface *(~20 min)*

**Option A**: Bare YAML attrib pass-through (simplest)
```yaml
# In any YAML topology file:
_target_: PlanThenImplementInferencer
modes:
  deep_mode: true
  elegant_mode: true
```

This works today via the existing `attrib`-default mechanism — once Step 1.1
adds the attrib, YAML can set it.

**Option B**: CLI flag for end-users (later, optional)
```bash
task-cli "design API" --mode deep_mode --mode elegant_mode
```

Add to `tool.json` as a `repeatable` parameter. Executor turns it into:
```python
overrides["modes"] = {m: True for m in arguments.get("mode", [])}
```

Phase 4 = Option A only. CLI flag (Option B) is out of scope for this plan.

### Phase 5 — Tests *(~30 min)*

**Test M1** — modes dict cascades to children
```python
def test_modes_propagate_to_children():
    parent = SomeTemplatedInferencer(modes={"deep_mode": True})
    parent._propagate_to_children()
    for child in parent._iter_child_inferencers():
        assert child.modes == {"deep_mode": True}
```

**Test M2** — `enable_<mode>` keys appear in template feed
```python
def test_modes_become_enable_keys_in_feed():
    inf = ...(modes={"deep_mode": True, "elegant_mode": False})
    feed = inf._build_template_feed(inference_input={})
    assert feed["enable_deep_mode"] is True
    assert feed["enable_elegant_mode"] is False
```

**Test M3** — `instructions.modes.X` resolves to mode template content via FileBasedVariableManager
```python
def test_instructions_modes_resolve():
    """Verify the existing _variables/ + .variables.yaml mechanism resolves
    `instructions.modes.deep_mode` to the rendered template content."""
    # Render a minimal template that uses {{ instructions.modes.deep_mode }}
    rendered = template_manager.render("plan/main/some_test_template", {})
    assert "spawn many agents" in rendered  # deep_mode.jinja2 content
```

**Test ST1** — `__template_space__` is auto-injected from `template_root_space`
```python
def test_template_space_injected_into_feed():
    inf = ...(template_root_space="plan")
    feed = inf._build_template_feed(inference_input={})
    assert feed["__template_space__"] == "plan"
```

**Test ST2** — `__action__` alias resolves to `__template_space__` via .variables.yaml
```python
def test_action_alias_resolves_to_template_space():
    """End-to-end: render a mode template that references {{ __action__ }}
    when invoked from a `plan/` template — should render as "plan"."""
    inf = ...(template_root_space="plan")
    rendered = inf._render_prompt(...)
    # The mode template that uses __action__ should see "plan"
    assert "plan" in rendered  # if the mode references __action__
```

**Test M4** — Conditional rendering (positive case)
```python
def test_initial_jinja2_renders_deep_mode_when_enabled():
    rendered = template_manager.render(
        "plan/main/initial",
        {"enable_deep_mode": True, "instructions": _InstructionsProxy(tm), ...}
    )
    assert "spawn many agents" in rendered
```

**Test M5** — Conditional rendering (negative case)
```python
def test_initial_jinja2_omits_deep_mode_when_disabled():
    rendered = template_manager.render(
        "plan/main/initial",
        {"enable_deep_mode": False, ...}
    )
    assert "spawn many agents" not in rendered
```

**Test M6** — Conditional rendering (undefined case)
```python
def test_initial_jinja2_handles_undefined_flag():
    # No enable_deep_mode in feed at all
    rendered = template_manager.render("plan/main/initial", {...})
    assert "spawn many agents" not in rendered  # default-off behavior
```

---

## 5. Risk Register

| # | Risk | Mitigation |
|---|---|---|
| 1 | StrictUndefined renderer crashes when `enable_X` not set | Step 1.2 always injects `enable_<mode>: False` for known modes; for unknown modes, the `{%- if %}` block uses Jinja's truthiness which `Undefined` handles as False under DebugUndefined (verify which Undefined the codebase uses) |
| 2 | Lazy proxy fails inside template stub-renderer test | Test stubbing already handles arbitrary attribute access (`StubObject` pattern); proxy will just be replaced with stub and tests still pass |
| 3 | Mode files reference variables of their own | `_InstructionsProxy.__getattr__` passes `{}` as variables. If mode files need parameters, add a `modes_context: dict` attrib (defer until a real mode needs it) |
| 4 | `_propagate_to_children` adds modes to inferencers that don't have `modes` attrib (e.g., InferencerBase) | Use `getattr/setattr` with hasattr guard; only set on TemplatedInferencerBase descendants |
| 5 | Existing `template_extra_feed["modes"]` collision (if anything already uses that key) | Reserved namespace check during code review |

---

## 6. Out of Scope

- CLI `--mode` flag (defer to follow-up)
- Mode-specific instruction parameterization (defer until a mode needs it)
- "ultrathink" / "careful" as separate modes (could be added later as additional `.jinja2` files; out of scope here)
- Slash-command surface for setting modes
- Per-child mode overrides (parent's modes always cascade as a complete dict)

---

## 7. Success Criteria

1. ✅ `modes={"deep_mode": True}` in YAML → `enable_deep_mode` appears in template feed
2. ✅ `instructions.modes.deep_mode` in any template → renders the file content
3. ✅ Modes cascade to children via `_propagate_to_children`
4. ✅ Adding a new `.jinja2` file in `_variables/instructions/modes/` makes it available without code changes
5. ✅ All 6 mode tests (M1-M6) pass
6. ✅ Full preflight still passes (currently 71)
7. ✅ Existing inferencer instantiation behaves identically when `modes` is empty (default)

---

## 8. Phased Shipping (revised — Plan A insights folded in)

| Phase | Time | Risk |
|---|---|---|
| 0 — Smoke test for `instructions.modes.X` auto-resolution (Plan A insight) | 15 min | Low |
| 1 — `modes` attrib + cascade + conditional `template_variables` auto-declare | 30 min | Low |
| 2 — Inject `__template_space__` + `enable_X` keys into `_build_template_feed` | 20 min | Low |
| 3 — Wire `initial.jinja2` (user's block) | 5 min | Low |
| 4 — YAML pass-through verification (works for free after Phase 1) | 10 min | Low |
| 5 — Tests M1-M6 + ST1-ST2 | 30 min | Low |
| 6 — Populate `elegant_mode.jinja2` with concrete content (Plan A Step 1) | 10 min | Trivial |
| **Total** | **~2 hours** | — |

The plan got SHORTER (vs. v1) after the deeper investigation, then grew back
slightly (vs. v2) when Plan A's `template_variables: null` insight was folded
in. Final size is still ~50% of v1.

What we ship:
1. Phase 0 smoke test guards against assumption errors
2. `modes` dict attrib (3 lines)
3. Auto-derive `enable_X` keys (3 lines)
4. Auto-inject `template_variables` for declared modes (4 lines, conditional)
5. Inject `__template_space__` (2 lines)
6. Add the user's `{%- if %}` block (4 lines)
7. Populate `elegant_mode.jinja2` with concrete instruction text (1 file)
8. Tests M1-M6 + ST1-ST2 (~100 lines)

---

## 9. Open Questions

| Q | Default proposal |
|---|---|
| Should `enable_<mode>` keys be auto-added to feed even for modes not in `self.modes`? | No — only set keys for modes the user declared. Templates use the `{%- if %}` Jinja idiom which handles missing keys as False under our Undefined config. |
| Should `_InstructionsProxy.modes` autodiscover from filesystem or only render on lookup? | Lookup-only (lazy). Filesystem scan would slow inferencer init for no benefit. |
| Should mode templates support per-mode template_variables? | Not yet. If a mode needs parameters, add later via `modes_context: dict`. |
| Should we make this a slash flag too (`/task --mode deep_mode`)? | Out of scope; defer. The YAML path is the primary surface. |

---

## 9.5 Plan A's `elegant_mode.jinja2` Content (imported verbatim)

Plan A `cached-hennessy.md` Step 1 proposed this concrete content for the
currently-empty `elegant_mode.jinja2`:

> *"Produce an elegant, proper solution — not ad-hoc or hacky. Prefer clean architecture, reuse existing patterns, and ensure the solution addresses root causes rather than symptoms."*

This is good — it captures the user's recurring instruction
*"we want real, elegant, proper solution, not ad-hoc, hacky things"* almost
verbatim. Use as-is unless the user wants to refine it.

## 9.6 Why This Plan Is Better Than Either Source — v4 Comparison

This v4 of Plan B integrates Plan A v2's verified `load_variables()`
insight while rejecting Plan A v2's `except Exception: pass` anti-pattern
and its non-decision on `_modes:` vs `modes:` cascade convention.

| Concern | Plan A v2 (06:12) | Plan B v3 (mine) | Plan B v4 (this) |
|---|---|---|---|
| Right fix location for `__template_space__` | ✅ AgentFoundation | ✅ Same | ✅ Same |
| `modes: dict` abstraction | ✅ Adopted from v3 | ✅ | ✅ |
| `load_variables()` direct-call mechanism | ✅ **NEW INSIGHT** | ❌ Missed (used `template_variables` mutation instead) | ✅ Folded in (Phase 1.2c) |
| `read_text()` raw-text fact documented | ✅ **NEW INSIGHT** | ❌ Missed | ✅ Folded in (Phase 0 RESOLVED note) |
| Error handling | 🔴 `except Exception: pass` (anti-pattern) | N/A | ✅ Specific exception + warn-on-unexpected |
| `_modes:` vs `modes:` decision | 🔴 "Both valid, you pick" (non-decision) | ❌ Didn't address | ✅ Commit to `_modes:` as default + verify with code |
| `template_version` attrib safety | 🔴 Unverified `self.template_version` access | ❌ Didn't address | ✅ `getattr(...)` fallback |
| Phase 0 smoke test | ❌ | ✅ | ✅ Marked RESOLVED — Plan A answered it |
| Risk register | ❌ | ✅ | ✅ |
| Out-of-scope list | ❌ | ✅ | ✅ |
| File:line citations | 🟡 Better than v1 but still sparse | ✅ | ✅ Plus Plan A v2's citations |
| Total length | 134 lines | 470 lines | ~510 lines (more rigor) |
| Speculative future-modes section | ❌ (good — no scope creep) | 🟡 had it | ⚠️ Should consider trimming §10 |

## 10. The User's Recurring Phrases as Future Modes

The user's recent slash commands repeatedly say:
> *"make carefully, thoroughly double check with critical-thinking, make really deep, thorough and accurate investigation; ultrathink"*

These are clearly meta-instructions the user wants the agent to internalize.
Once Phase 1-3 ship, adding new modes is trivial:

```
_variables/instructions/modes/
├── deep_mode.jinja2          (exists)
├── elegant_mode.jinja2       (exists)
├── careful_mode.jinja2       (NEW — captures "careful, thorough double-check")
├── ultrathink_mode.jinja2    (NEW — captures "spawn agents, deep investigation")
└── critical_thinking_mode.jinja2  (NEW)
```

YAML:
```yaml
modes:
  careful_mode: true
  ultrathink_mode: true
  critical_thinking_mode: true
```

→ All instructions appear in the rendered prompt automatically.

This is the long-term vision the plan enables. Out of scope for this proposal,
but the architecture supports it natively.

---

**END**
