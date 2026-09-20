# Variable Manager & Template Manager Migration Plan

> **Source (upstream)**: `rankevolve/src/utils/`
> **Destination (target)**: `RichPythonUtils/src/rich_python_utils/`
> **Date**: 2026-04-06

---

## Executive Summary

This plan migrates **additional updates** from rankevolve's `variable_manager` and `template_manager` to RichPythonUtils. The changes fall into **4 categories**:

1. **New features** — cross-space fallback, folder-based variable resolution, override/alias API expansion, templated feed, YAML sidecar integration
2. **API surface changes** — public `extract_variables` functions, new class attributes and methods
3. **Dependency additions** — `resolve_fuzzy_path` function in `map_helper.py`, public `extract_variables` in `jinja2_format.py`
4. **Formatting/style changes** — line wrapping, comment updates (cosmetic, migrated for consistency)

---

## 1. Dependency Prerequisites (Must Be Done First)

### 1.1 Add `resolve_fuzzy_path` (and related) to `map_helper.py`

**File**: `RichPythonUtils/src/rich_python_utils/common_utils/map_helper.py`

The new `set()`, `get_effective_value()`, and `clear()` methods in `FileBasedVariableManager` import `resolve_fuzzy_path`, `get_at_path`, `has_path` from `map_helper`. While `get_at_path`, `has_path`, and `set_at_path` already exist, **`resolve_fuzzy_path` does NOT exist** in RichPythonUtils.

**Action**: Copy `resolve_fuzzy_path()` (and its helper `_generate_split_candidates` if used) from rankevolve's `map_helper.py` into RichPythonUtils's `map_helper.py`. Also consider copying `get_at_path_fuzzy` and `set_at_path_fuzzy` since they are closely related utilities.

**Risk**: LOW — additive function, no existing code affected.

### 1.2 Add public `extract_variables()` to `jinja2_format.py`

**File**: `RichPythonUtils/src/rich_python_utils/string_utils/formatting/jinja2_format.py`

Rankevolve has a public `extract_variables()` function. RichPythonUtils only has `compile_template(return_variables=True)` which is a different API.

**Action**: Add the standalone `extract_variables()` function from rankevolve's `jinja2_format.py` to RichPythonUtils's `jinja2_format.py`.

**Risk**: LOW — additive function.

### 1.3 Note on `_extract_variables` naming in `file_based.py`

In rankevolve's `file_based.py`, the extractor references use **public names** (`handlebars_format.extract_variables`, `jinja2_format.extract_variables`, `python_str_format.extract_variables`, `string_template_format.extract_variables`). In RichPythonUtils, these are **private** (`_extract_variables`).

**Decision**: Keep private `_extract_variables` in RichPythonUtils for `handlebars_format`, `python_str_format`, and `string_template_format` (they remain internal). Only add public `extract_variables` to `jinja2_format.py`. In `file_based.py`, continue using the private names with the `_` prefix for handlebars/python/template formats.

---

## 2. `common_objects/variable_manager/` Changes

### 2.1 `config.py` — 2 changes

**File**: `RichPythonUtils/src/rich_python_utils/common_objects/variable_manager/config.py`

| # | Change | Description |
|---|--------|-------------|
| 1 | Add `.jinja2` and `.jinja` to `file_extensions` default | `[".hbs", ".j2", ".txt", ""]` → `[".hbs", ".j2", ".jinja2", ".jinja", ".txt", ""]` |
| 2 | Add `cross_space_root` field | New field: `cross_space_root: Optional[str] = None` for cross-space variable fallback |

**Risk**: LOW — backward compatible (defaults unchanged for existing users, new field is Optional with None default).

### 2.2 `__init__.py` — No functional changes

Only import path differences (`rich_python_utils` vs `rankevolve`). **No action needed.**

### 2.3 `base.py` — No changes

Files are identical. **No action needed.**

### 2.4 `exceptions.py` — No changes

Files are identical. **No action needed.**

### 2.5 `file_based.py` — **Major changes** (most complex file)

**File**: `RichPythonUtils/src/rich_python_utils/common_objects/variable_manager/file_based.py`

#### 2.5.1 Cross-space fallback in `_get_cascade_paths()`

**Lines ~484-508 in rankevolve**: After building the cascade paths, adds a cross-space fallback path from `self.config.cross_space_root`.

```python
# Cross-space fallback: check a parent/shared root directory
cross_space = self.config.cross_space_root
if cross_space:
    cross_path = Path(cross_space)
    if cross_path != self.base_path and cross_path.is_dir():
        paths.append(get_vars_path(cross_path))
```

**Comment update**: `"cascade (variable_type -> variable_root_space -> global)"` → `"cascade (variable_type -> variable_root_space -> global -> cross-space)"`

#### 2.5.2 Version resolution refactor in `_find_variable_file()`

**Lines ~537-582 in rankevolve**: The version resolution logic is refactored from a single `file_variants` list into a 3-phase approach:

- **Phase 1**: Check versioned file variants (overrides + version suffix) — was previously combined into one loop
- **Phase 2** (NEW): Folder-based fallback for versioned variables — checks if `cascade_path / path_variant / version` is a directory and resolves via `_resolve_variable_folder()`
- **Phase 3** (NEW): Unversioned file fallback — separate loop for unversioned plain files

This is a **significant refactor** that changes how variable file resolution works.

#### 2.5.3 New method: `_resolve_variable_folder()`

**Lines ~593-638 in rankevolve**: Entirely new method for resolving a variable from a folder containing variant files:

1. Check for a file named `default` (with any configured extension)
2. Check for `.config.yaml` with a `default` key naming the file
3. If exactly one content file exists, use it (unambiguous)
4. Otherwise raise `AmbiguousVariableError`

#### 2.5.4 Enhanced `_read_file_content()` — directory handling

**Lines ~641-688 in rankevolve**: The `_read_file_content()` method is enhanced to handle directory-type variables:

- If `file_path` is a directory, looks for `.config.yaml` with a `default` key
- Resolves to the default variant file within subdirectories
- Returns empty string if still a directory after resolution

#### 2.5.5 Override/Alias API reorganization and expansion

In RichPythonUtils, the Override/Alias region contains:
- `_init_override_layer()` — exists ✓
- `_cascade_scopes()` — exists ✓ (minor docstring difference)
- `load_yaml_sidecar()` — exists ✓

In rankevolve, this section is **moved to the end of the file** and significantly expanded with:

| Method | Status | Description |
|--------|--------|-------------|
| `_init_override_layer()` | EXISTS | Same |
| `_cascade_scopes()` | EXISTS | Minor docstring change |
| `_resolve_alias_cascaded()` | **NEW** | Resolves alias by cascading through scoped alias dicts |
| `_overrides` (property) | **NEW** | Backward compat property for global scope overrides |
| `_aliases` (property) | **NEW** | Backward compat property for global scope aliases |
| `_yaml_sidecar` (property) | **NEW** | Backward compat property for global scope yaml sidecar |
| `load_yaml_sidecar()` | EXISTS | Same implementation |
| `aliases` (property) | **NEW** | Returns merged alias registry across all scopes |
| `set()` | **NEW** | Set a variable with alias/fuzzy resolution |
| `clear()` | **NEW** | Remove a set/overridden variable |
| `clear_all()` | **NEW** | Remove all overrides across all scopes |
| `get_effective_value()` | **NEW** | Get effective value with cascade resolution, overrides, YAML sidecar, and fuzzy matching |
| `get_all_variables()` | **NEW** | Get all variables as nested dict with overrides applied |

**Note**: The existing `_init_override_layer()`, `_cascade_scopes()`, and `load_yaml_sidecar()` methods need to be **moved** from their current position (middle of file) to the end of the file in a new `# region Override & Alias API` section to match rankevolve's organization.

#### 2.5.6 Extractor reference naming changes

In `_get_variable_extractor()`:
- `handlebars_format._extract_variables` → keep as `_extract_variables` (private in RichPythonUtils)
- `jinja2_format.compile_template(t, return_variables=True)[1]` → `jinja2_format.extract_variables` (once added)
- `python_str_format._extract_variables` → keep as `_extract_variables`
- `string_template_format._extract_variables` → keep as `_extract_variables`

**Only the jinja2 extractor logic actually changes** (from `compile_template` approach to direct `extract_variables`).

#### 2.5.7 Formatting/style changes (cosmetic)

Multiple line-wrapping changes for long lines. These are style-only and should be applied for consistency.

---

## 3. `string_utils/formatting/template_manager/` Changes

### 3.1 `__init__.py` — No functional changes

RichPythonUtils already has SOP imports that rankevolve doesn't have (RichPythonUtils is ahead here). Only import path differences. **No action needed.**

### 3.2 `variable_manager.py` — No functional changes

Only import path differences. **No action needed.**

### 3.3 `sop_manager.py` — Trivial difference

Only differences:
- Rankevolve has a copyright comment at line 1
- Different import path for stategraph
- One blank line removed

**No action needed** (RichPythonUtils version is correct as-is).

### 3.4 `template_manager.py` — **Significant changes**

**File**: `RichPythonUtils/src/rich_python_utils/string_utils/formatting/template_manager/template_manager.py`

#### 3.4.1 New imports

```python
from rich_python_utils.string_utils.formatting.handlebars_format import (
    extract_variables as handlebars_extract_variables,  # NEW (use _extract_variables)
)
from rich_python_utils.string_utils.formatting.jinja2_format import (
    extract_variables as jinja2_extract_variables,  # NEW
)
```

#### 3.4.2 New class-level dict: `BUILTIN_VARIABLE_EXTRACTORS`

```python
BUILTIN_VARIABLE_EXTRACTORS = {
    jinjia_template_format: jinja2_extract_variables,
    handlebars_template_format: handlebars_extract_variables,
}
```

Maps formatter functions to their corresponding variable extractor functions.

#### 3.4.3 New attributes on `TemplateManager`

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_templated_feed` | `bool` | `False` | Enable resolution of feed values that reference other feed values |
| `template_variable_extractor` | `Union[str, Callable, None]` | `"default"` | Variable extractor function or "default" for auto-resolution |
| `cross_space_root` | `Optional[str]` | `None` | Path for cross-space variable/template fallback |

#### 3.4.4 New `__attrs_post_init__` logic

- Resolves `template_variable_extractor` from `"default"` to actual extractor function using `BUILTIN_VARIABLE_EXTRACTORS`
- VariableLoader creation now wrapped in `try/except ImportError`
- Cross-space root support: passes `cross_space_root` to `VariableLoaderConfig` and loads cross-space YAML sidecar

#### 3.4.5 New method: `_resolve_templated_feed()`

Delegates to `resolve_templated_feed()` from `formatting/common.py` (already exists in RichPythonUtils).

#### 3.4.6 YAML sidecar integration in `__call__()`

After resolving predefined variables, also includes YAML sidecar variables via `get_all_variables()`. These have lower priority than file-based resolved vars.

#### 3.4.7 Templated feed resolution in `__call__()`

After merging all variables, if `enable_templated_feed` is True, resolves templated feed values.

#### 3.4.8 Formatting/style changes (cosmetic)

Multiple line-wrapping changes.

---

## 4. Migration Order (Recommended)

| Step | File | Type | Risk |
|------|------|------|------|
| 1 | `map_helper.py` | Add `resolve_fuzzy_path` + helpers | LOW |
| 2 | `jinja2_format.py` | Add public `extract_variables()` | LOW |
| 3 | `config.py` | Add `.jinja2`/`.jinja` extensions + `cross_space_root` field | LOW |
| 4 | `file_based.py` | Cross-space fallback, folder resolution, version refactor, override API expansion | MEDIUM |
| 5 | `template_manager.py` | New attributes, extractors, cross-space, templated feed | MEDIUM |

---

## 5. Files NOT Requiring Changes

| File | Reason |
|------|--------|
| `base.py` | Identical |
| `exceptions.py` | Identical |
| `variable_manager/__init__.py` | Only import path differences |
| `template_manager/__init__.py` | RichPythonUtils already has SOP imports (ahead) |
| `template_manager/variable_manager.py` | Only import path differences |
| `template_manager/sop_manager.py` | Trivial/copyright differences only |
| `docs/` | Docs folder exists in rankevolve but contains rankevolve-specific content |

---

## 6. Risk Assessment

| Risk | Mitigation |
|------|------------|
| `resolve_fuzzy_path` not present in RichPythonUtils | Copy function + helpers from rankevolve |
| `_extract_variables` vs `extract_variables` naming | Keep private names in RichPythonUtils, only add public `extract_variables` to jinja2_format |
| Large refactor of version resolution in `_find_variable_file()` | Careful line-by-line migration, test afterward |
| New `set()`/`clear()`/`get_effective_value()` methods use `rankevolve` imports | Replace with `rich_python_utils` imports |
| `_read_file_content()` directory handling depends on `yaml` | yaml is already used by `load_yaml_sidecar()`, should be available |

---

## 7. Import Path Translation Reference

All `rankevolve.src.utils.` imports must be translated to `rich_python_utils.`:

| Rankevolve Import | RichPythonUtils Import |
|-------------------|----------------------|
| `rankevolve.src.utils.common_utils.map_helper` | `rich_python_utils.common_utils.map_helper` |
| `rankevolve.src.utils.string_utils.formatting.common` | `rich_python_utils.string_utils.formatting.common` |
| `rankevolve.src.utils.string_utils.formatting.handlebars_format` | `rich_python_utils.string_utils.formatting.handlebars_format` |
| `rankevolve.src.utils.string_utils.formatting.jinja2_format` | `rich_python_utils.string_utils.formatting.jinja2_format` |
