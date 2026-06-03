# Preflight Tests: Quick Start Guide

## One-Time Setup (2 minutes)
```bash
cd /path/to/OpenStartup
make preflight-install-hook
```

## Before Every Commit
Just commit normally. The pre-commit hook auto-runs TIER 1 in <2 seconds:
```bash
git commit -m "Fix feature XYZ"
# ✅ Pre-commit: TIER 1 Jinja render check PASSED
# Commit proceeds
```

If TIER 1 fails:
```bash
# See error details:
make preflight-tier1

# Fix the Jinja template(s) and try again
```

## Before Pushing (Recommended)
```bash
make preflight        # Runs TIER 1 + TIER 2 (~60s)
# If both pass: safe to push ✅
# If either fails: fix locally
```

## Full Test Suite (for CI or thorough local check)
```bash
make preflight-full   # Runs all tiers (~12 minutes)
```

## What Gets Tested

| Tier | Scope | Time | When |
|------|-------|------|------|
| **TIER 1** | All Jinja templates render correctly | <5s | Every commit (auto) + before push |
| **TIER 2** | Topology instantiates & mocks render | <60s | Before push (recommended) |
| **TIER 3** | Real CLI end-to-end smoke test | ~10min | CI only (too slow locally) |

## What It Catches
✅ Slash-vs-dot bugs: `{{ notes/field }}` → `{{ notes.field }}`  
✅ Typos in variables: `{{ undefined_var }}`  
✅ Jinja syntax errors  
✅ Topology wiring bugs  
✅ Integration failures  

## Example: The Bug It Would Have Caught

### The Original Bug
```jinja2
{# BAD #}
{{ notes/local_search_efficiency }}
```

### TIER 1 Catches It Instantly
```
$ git commit -m "Update template"
⏳ Pre-commit hook: running TIER 1 Jinja render check...
❌ TIER 1 FAILED
   test_jinja_render_all_templates.py::test_template_renders_without_undefined[notes_template.jinja2]
   UndefinedError: 'StubObject' has no attribute '__truediv__'
   
Fix the Jinja syntax error and try again.
```

### Fix
```jinja2
{# GOOD #}
{{ notes.local_search_efficiency }}
```

### Re-commit
```
$ git commit -m "Update template"
✅ TIER 1 PASSED: All templates render without errors
Commit successful
```

## Troubleshooting

### "make: command not found"
Pre-commit hook runs without make. Run directly:
```bash
OPENSTARTUP_PATH=$(pwd) pytest test/openteam/resources/tools/task/preflight/test_jinja_render_all_templates.py -v
```

### "jinja2 module not found"
Install dependencies:
```bash
pip install jinja2 pytest
```

### "How do I bypass the hook?"
```bash
git commit --no-verify    # NOT RECOMMENDED
```

### "Pre-commit hook didn't run"
Verify it's installed:
```bash
git config core.hooksPath     # Should show: .githooks
cat .git/hooks/pre-commit      # Should exist or be a symlink
```

Re-install:
```bash
make preflight-install-hook
```

---

## For Team Leads / CI Engineers

### Add to CI Pipeline (GitHub Actions example)
```yaml
# .github/workflows/preflight.yml
name: Preflight Checks
on: [pull_request, push]

jobs:
  tier1-tier2:
    runs-on: ubuntu-latest
    timeout-minutes: 2
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: make preflight    # TIER 1 + TIER 2

  tier3-smoke:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: tier1-tier2
    if: github.event_name == 'push'
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: make preflight-tier3
```

### Require Preflight to Pass
- GitHub: Settings → Branches → Require checks to pass before merging → `tier1-tier2`
- GitLab: Settings → Protected Branches → Allowed to merge → `preflight`

---

## Key Metrics

- **Time to detect slash-vs-dot bug**: <2s (pre-commit) vs 1h38m (integration test)
- **Templates auto-tested**: All `.jinja2` files (currently 47+)
- **CI time saved per caught bug**: ~1.5 hours
- **False positives**: None (pure Jinja syntax validation)

---

For full architecture details, see: `PREFLIGHT_TEST_ARCHITECTURE.md`
