# RST Documentation Audit: DIR1 (AI-built) vs DIR2 (Human-calibrated)
**proactive-ai-platform codebase | 2026-05-06**

---

## Quick Snapshot

| Dimension | DIR1 | DIR2 | Delta |
|-----------|------|------|-------|
| RST Files | 47 | 51 | +4 |
| RST Lines | 7,301 | 12,528 | **+71.6%** |
| Size | 256 KB | 450 KB | +76% |
| Cross-cutting Chapters | 9 | 15 | +6 |
| Supplementary Docs | 1 (README) | 7 (TESTING_SOP, PLAYBOOKS, etc.) | +6 |
| **STRUCTURE SCORE** | **6.8 / 10** | **8.7 / 10** | ✓ DIR2 wins |

---

## Coverage Matrix (Highlights)

### Unique to DIR1 (5 files, 810 lines)
- `architecture/cross-cutting/03-feature-flags.rst` (162 lines) — Replaced by shorter DIR2 version
- `architecture/cross-cutting/04-auth-and-tenant.rst` (218 lines) — More comprehensive than DIR2
- `architecture/cross-cutting/05-observability.rst` (167 lines) — Replaced by abbreviated DIR2 version
- `architecture/cross-cutting/06-messaging-and-sqs.rst` (153 lines) — Replaced by DIR2 async-tasks doc
- `architecture/cross-cutting/08-build-and-test.rst` (200 lines) — **COMPLETELY MISSING in DIR2**
- `modules/nudge/index.rst` (33 lines) — Orphaned in DIR2
- `modules/platform/exception.rst` (83 lines) — **COMPLETELY MISSING in DIR2**

### Unique to DIR2 (8 files, 2,835 lines)
- `architecture/cross-cutting/10-vision-and-strategy.rst` (385 lines) — **NEW: Strategic 5-year vision**
- `architecture/cross-cutting/11-metrics-catalog.rst` (450 lines) — **NEW: All metrics/SLOs with source citations**
- `architecture/cross-cutting/12-optimization-playbook.rst` (368 lines) — **NEW: How-to move each metric**
- `architecture/cross-cutting/14-architectural-decisions.rst` (668 lines) — **NEW: Decision audit log**
- `architecture/cross-cutting/15-velocity-and-debt.rst` (564 lines) — **NEW: Debt + PR velocity tracking**
- Plus 7 supplementary Markdown docs (120 KB): **TESTING_SOP.md** (critical for PR submission), PROBLEM_PLAYBOOKS.md (on-call runbooks), MANIFEST.json (programmatic index), SYMBOL_INDEX.md, TOPIC_INDEX.md, AGENTS.md, README.md

---

## Findings

### INDEX/TOCTREE INTEGRITY
✓ **DIR1**: All 47 files referenced in toctrees exist on disk (100% clean)
✓ **DIR2**: All 51 files referenced in toctrees exist on disk (100% clean)
⚠️ **DIR2 only**: TESTING_SOP.md referenced in index.rst but NOT in Sphinx toctree (orphaned)

### STRUCTURAL ORGANIZATION
**DIR1**: Flat list of 9 cross-cutting chapters (confusing — chapter 13 jumps at end)
**DIR2**: Explicit 3-tier grouping with narrative framing:
  - Business & Strategy Spine (01, 10, 11, 12)
  - Historical Record (02, 13, 14, 15)
  - Technical Concepts (03–09)
→ **DIR2's hierarchical structure is vastly superior for navigation**

### CONTENT DEPTH COMPARISON (Sample Platform Modules)
| Module | DIR1 | DIR2 | Ratio |
|--------|------|------|-------|
| requestcontext | 52 lines | 233 lines | +448% |
| logging | 83 lines | 225 lines | +171% |
| task | 121 lines | 253 lines | +109% |
| utility | 90 lines | 285 lines | +317% |
| sqs | 64 lines | 203 lines | +317% |
| service-metric | 56 lines | 187 lines | +334% |

→ **DIR2 platform modules are 2.2× larger on average**

### TOP-LEVEL INDEX FRAMING
**DIR1** (137 lines): Technical scope snapshot, 3 navigation paths, verification methodology noted
**DIR2** (106 lines): Rich metadata (Date, OKR context), 9 navigation paths, mentions business goals (FY26: 400K→1.5M invocations), explicit test categories

→ **DIR2 reads like "living systems guide"; DIR1 reads like "snapshot"**

### MANDATORY CHAPTERS (both dirs)
✓ `01-business-and-technical-goals.rst` — Present in both (DIR2: 345 lines vs DIR1: 225 lines, +53%)
✓ `02-development-history.rst` — Present in both (DIR2: 273 lines vs DIR1: 235 lines, +16%)

---

## DIR2 Supplementary Markdown Docs: Value Assessment

| Doc | Size | Value | Status |
|-----|------|-------|--------|
| **TESTING_SOP.md** | 33 KB | **CRITICAL** — PR blocking checks, test categories, conventions, 14 policy gaps | Must-read; orphaned from toctree |
| **PROBLEM_PLAYBOOKS.md** | 19 KB | **HIGH** — 12 on-call runbooks (latency, queue backups, feature flags stuck) | Operational gold |
| **MANIFEST.json** | 23 KB | **HIGH** — Structured map of all 118 files w/ criticality, size, dependencies | Enables tooling |
| **SYMBOL_INDEX.md** | 18 KB | **HIGH** — Master class/function index (searchable reference) | Developer-friendly |
| **TOPIC_INDEX.md** | 15 KB | **MEDIUM** — Glossary + cross-refs (largely duplicates 00-glossary.rst) | Supplementary |
| **AGENTS.md** | 12 KB | **LOW** — Metadata about investigation methodology | Transparency only |
| **README.md** | 8.2 KB | **LOW** — Scope statement (nearly identical to index.rst) | Redundant |

**Total supplementary value**: Approximately 120 KB of content not present in DIR1 at all.
**Critical gap in DIR1**: No testing SOP, no on-call playbooks, no programmatic index.

---

## Key Losses (DIR1 → DIR2)

1. **exception.rst** (83 lines) — REST client exception hierarchy docs lost
2. **modules/nudge/index.rst** (33 lines) — Module index page lost (only nudge-throttle.rst remains)
3. **build-and-test.rst** (200 lines) — CI/testing practices completely missing in DIR2
4. **13-full-history-catalog.rst** — Reduced from 833 to 582 lines (250-line cut)

**Impact**: Exception handling and build/test CI documentation are now invisible.

---

## Scoring Rationale

### DIR1: 6.8 / 10
**Why not higher?**
- Missing 6 strategic chapters (vision, metrics, optimization, decisions, debt)
- Zero operational/on-call documentation
- No testing SOP or CI expectations documented
- Flat cross-cutting structure (no thematic grouping)
- 2 missing platform modules (exception.rst, build-and-test.rst)
- Top-level index lacks business context

**Verdict**: Sound technical foundation, but reads like auto-generated snapshot. Good for architecture reading; weak for onboarding and ops.

### DIR2: 8.7 / 10
**Why not 9+?**
- 2 missing modules (exception.rst, nudge/index.rst)
- TESTING_SOP.md orphaned from Sphinx toctree
- Some chapter overlap/redundancy (vision, metrics, optimization)
- 13-full-history-catalog pruned (lost detail)

**Verdict**: Production-ready. Business-aware, operationally complete, hierarchically organized. Minor fixable gaps.

---

## Recommendation

**Use DIR2 as canonical.** 

DIR1 is useful as a reference for how to algorithmically generate baseline structure, but human iteration has:
- **+71.6% content** (7.3K → 12.5K lines)
- **+6 strategic chapters** covering vision, metrics, decisions, debt
- **+7 supplementary docs** (120 KB) covering testing/ops/indexing
- **Better navigation** (3-tier hierarchy vs. flat list)

**To make DIR2 perfect**:
1. Add missing `exception.rst` (REST exception classes)
2. Restore `modules/nudge/index.rst` (module overview)
3. Wire TESTING_SOP.md into Sphinx toctree
4. De-duplicate metrics/optimization content if desired

---

## Detailed Report

See: `AUDIT_REPORT_RST_STRUCTURE_COVERAGE.txt` (460 lines)
Includes: file-by-file coverage matrix, toctree integrity analysis, framing quality comparison, module organization deep-dive.
