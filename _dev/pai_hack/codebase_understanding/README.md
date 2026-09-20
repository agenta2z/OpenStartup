# Proactive AI Service — Documentation

## Navigation Guide

This documentation is built with [Sphinx](https://www.sphinx-doc.org/) using
the Read the Docs theme.  All source files live under `docs/` and are written
in reStructuredText (`.rst`).

### Directory Layout

```
docs/
├── conf.py                     # Sphinx configuration
├── Makefile                    # Build targets (html, linkcheck, clean, install)
├── index.rst                   # Root document with master toctree
├── README.md                   # This file – navigation guide
│
├── overviews/                  # High-level summaries & dashboards
│   ├── 01-multi-axis-matrix.rst
│   ├── 02-architectural-narrative.rst
│   └── 03-criticality-dashboard.rst
│
├── architecture/               # Architecture core documents
│   ├── 00-glossary.rst
│   ├── 01-architecture-overview.rst
│   ├── 02-request-lifecycle.rst
│   ├── 03-module-catalog.rst
│   └── cross-cutting/          # Cross-cutting concern deep-dives
│       └── index.rst           # (toctree stub for subtask 2 files)
│
├── modules/                    # Per-module reference documentation
│   ├── index.rst               # (toctree stub for subtask 3-4 files)
│   ├── core-platform/
│   ├── feature-modules/
│   ├── infrastructure/
│   └── utilities/
│
├── _legacy_md/                 # Migrated original Markdown files
├── _static/                    # Custom CSS / JS assets
└── _templates/                 # Sphinx template overrides
```

### Quick-Lookup Table

| What you need | Where to look |
|---|---|
| At-a-glance module comparison | `overviews/01-multi-axis-matrix.rst` |
| Technology stack & architecture narrative | `overviews/02-architectural-narrative.rst` |
| Operational criticality rankings | `overviews/03-criticality-dashboard.rst` |
| Key terms & acronyms | `architecture/00-glossary.rst` |
| Component topology & dependency DAG | `architecture/01-architecture-overview.rst` |
| HTTP request flow end-to-end | `architecture/02-request-lifecycle.rst` |
| All 16 modules with metrics | `architecture/03-module-catalog.rst` |
| Cross-cutting concerns (logging, auth, metrics…) | `architecture/cross-cutting/` |
| Individual module deep-dives | `modules/` |
| Original legacy docs (pre-Sphinx) | `_legacy_md/` |

### Reading Strategies

**New team member?**
Start with the *Architectural Narrative* → *Multi-Axis Matrix* → *Glossary*,
then read the *Request Lifecycle* to understand how requests flow through the
system.

**On-call engineer?**
Jump to the *Criticality Dashboard* for operational priorities, then consult
the relevant module reference under `modules/`.

**Feature developer?**
Read the *Module Catalog* to locate the package you need, check the
*Cross-Cutting Concerns* for shared infrastructure, then dive into the
specific module docs.

**Reviewer / Auditor?**
Use the *Multi-Axis Matrix* for a compliance-friendly overview of all modules
with their tier, size, and dependency counts.

### Building the Docs

```bash
cd docs/
make install    # one-time: install Sphinx + extensions
make html       # build HTML output in _build/html/
make linkcheck  # verify external links
make clean      # remove build artifacts
```

### Legacy Documentation

The original Markdown documentation has been preserved in `_legacy_md/`.
These files are **excluded** from the Sphinx build (`exclude_patterns` in
`conf.py`) but remain accessible for reference.  The reference docs in
`_legacy_md/` were consulted during the creation of this Sphinx documentation
and remain accessible for historical context.
