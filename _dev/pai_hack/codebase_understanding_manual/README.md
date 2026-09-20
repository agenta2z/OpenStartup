# Proactive AI Platform — Codebase Understanding

Comprehensive documentation for the `proactive-ai-platform` codebase — Atlassian's Spring Boot Kotlin micros service backing the *proactive AI experiences* layer (Rovo Insights, conversation-starter nudges, throttling).

## 🤖 If you are an AI agent, start here

Load these in order:

1. **[`AGENTS.md`](AGENTS.md)** — problem→chapter routing tables (25 categories).
2. **[`MANIFEST.json`](MANIFEST.json)** — machine-readable chapter manifest (filterable with `jq`).
3. **[`PROBLEM_PLAYBOOKS.md`](PROBLEM_PLAYBOOKS.md)** — 20 long-form "I need to …" scenarios.
4. **[`TESTING_SOP.md`](TESTING_SOP.md)** ⭐ — canonical PR-test SOP (what tests/checks/lint to run; what blocks merge; 14 verified gaps in current policy).
5. As needed: **[`SYMBOL_INDEX.md`](SYMBOL_INDEX.md)** (class/file→chapter), **[`TOPIC_INDEX.md`](TOPIC_INDEX.md)** (concept→chapter).

If your problem is in `AGENTS.md` §4 ("Known gaps"), **stop searching** — write new docs as part of your PR.

## Quick navigation

| I want to... | Go to |
|---|---|
| **Open a PR — what tests / lint / CI checks must pass?** | **[`TESTING_SOP.md`](TESTING_SOP.md)** ⭐ |
| **Understand test conventions (`*Test` vs `*IT` vs `*AcceptanceTest`)** | [`TESTING_SOP.md`](TESTING_SOP.md) §1–3 |
| Understand the overall system | [overviews/02-architectural-narrative.rst](overviews/02-architectural-narrative.rst) |
| See all packages at a glance | [overviews/01-multi-axis-matrix.rst](overviews/01-multi-axis-matrix.rst) |
| On-call / SRE incident response | [overviews/03-criticality-dashboard.rst](overviews/03-criticality-dashboard.rst) |
| **Understand FY26 H2 business goals + KPIs** | [architecture/cross-cutting/01-business-and-technical-goals.rst](architecture/cross-cutting/01-business-and-technical-goals.rst) |
| **Understand what shipped in PRs #96–#108** | [architecture/cross-cutting/02-development-history.rst](architecture/cross-cutting/02-development-history.rst) |
| Understand a request's lifecycle (sync + async) | [architecture/02-request-lifecycle.rst](architecture/02-request-lifecycle.rst) |
| Understand request-context / MDC / coroutine context | [architecture/cross-cutting/03-request-context-and-mdc.rst](architecture/cross-cutting/03-request-context-and-mdc.rst) |
| Understand feature flags (Statsig) | [architecture/cross-cutting/04-feature-flags.rst](architecture/cross-cutting/04-feature-flags.rst) |
| Understand metrics (Micrometer + SignalFx) | [architecture/cross-cutting/05-observability-and-metrics.rst](architecture/cross-cutting/05-observability-and-metrics.rst) |
| Understand async tasks (envelope → SQS → worker) | [architecture/cross-cutting/06-async-tasks-and-sqs.rst](architecture/cross-cutting/06-async-tasks-and-sqs.rst) |
| Understand the Stratus AI Gateway integration | [architecture/cross-cutting/07-ai-gateway-and-stratus.rst](architecture/cross-cutting/07-ai-gateway-and-stratus.rst) |
| Look up what every file does | [architecture/03-module-catalog.rst](architecture/03-module-catalog.rst) |
| Deep-dive: Rovo Insights | [modules/features/rovo-insights.rst](modules/features/rovo-insights.rst) |
| Deep-dive: Nudge throttling | [modules/features/nudge.rst](modules/features/nudge.rst) |
| Deep-dive: Async task framework | [modules/platform/task.rst](modules/platform/task.rst) |
| Deep-dive: Stratus AI Gateway | [modules/platform/stratus.rst](modules/platform/stratus.rst) |
| Deep-dive: Feature gate | [modules/platform/featuregate.rst](modules/platform/featuregate.rst) |

## Repository covered

- **`proactive-ai-platform`** (`/Users/tchen7/MyProjects/atlassian_packages/proactive-ai-platform`)
  Single-module Spring Boot 7.10 / Kotlin / Gradle. 118 main + 32 test `.kt` files. Deployed via Atlassian Micros.

## Quick statistics

| Layer | Files | LoC (≈) | Notes |
|---|---|---|---|
| **Features (3 packages)** | 21 | 786 | rovoinsights (16 files, 658 LoC), nudge (4 files, 72 LoC), greeting (1 file, 56 LoC) |
| **Platform layers (12 packages)** | 97 | 6,979 | request context (14/906), service/metric (5/1243), featuregate (8/754), task (11/649), stratus (8/587), logging (6/568), utility (8/557), client (7/399), context (9/381), sqs (8/302), interceptor (5/295), config (6/208), exception (1/116) |
| **Root** | 1 | — | Application.kt |
| **Tests** | 32 | 6,313 | 0.81× test/main LoC ratio |
| **TOTAL** | **151** | **14,078** | 118 main + 32 test `.kt` files |

## Reading guide

**15 minutes** — Get oriented
1. [overviews/02-architectural-narrative.rst](overviews/02-architectural-narrative.rst) (walking tour: HTTP request → business logic → SQS worker)
2. [overviews/01-multi-axis-matrix.rst](overviews/01-multi-axis-matrix.rst) (all 15 packages mapped by size, tier, purpose)

**1 hour** — Understand the system
1. [architecture/01-architecture-overview.rst](architecture/01-architecture-overview.rst) (system boundary + Spring Boot structure)
2. [architecture/02-request-lifecycle.rst](architecture/02-request-lifecycle.rst) (sync + async lifecycles, where context flows)
3. [architecture/cross-cutting/01-business-and-technical-goals.rst](architecture/cross-cutting/01-business-and-technical-goals.rst) (FY26 H2 OKR, 400K → 1.5M monthly AI invocations)
4. [overviews/03-criticality-dashboard.rst](overviews/03-criticality-dashboard.rst) (SRE view: packages ranked by blast-radius)

**1 day** — Deep dive into a feature or platform layer
1. Read [architecture/03-module-catalog.rst](architecture/03-module-catalog.rst) (what every file does)
2. Pick a feature ([modules/features/](modules/features/)) or platform layer ([modules/platform/](modules/platform/))
3. Explore architecture cross-cutting chapters ([architecture/cross-cutting/](architecture/cross-cutting/))

## Documentation structure

```
codebase_understanding/
├── index.rst                         # Sphinx master index
├── README.md                         # This file
├── TESTING_SOP.md                    # ⭐ Canonical PR-test SOP (PR lifecycle, CI checks, gaps)
├── AGENTS.md                         # Problem→chapter routing for AI agents
├── MANIFEST.json                     # Machine-readable chapter inventory
├── PROBLEM_PLAYBOOKS.md              # 20 long-form "I need to…" scenarios
├── SYMBOL_INDEX.md                   # Class/file → chapter
├── TOPIC_INDEX.md                    # Concept → chapter
├── overviews/                        # Multi-axis tables, walking tour, criticality
│   ├── 01-multi-axis-matrix.rst
│   ├── 02-architectural-narrative.rst
│   └── 03-criticality-dashboard.rst
├── architecture/
│   ├── 00-glossary.rst               # Stratus, MCP, SHWorkers, …
│   ├── 01-architecture-overview.rst  # System boundary + Spring Boot structure
│   ├── 02-request-lifecycle.rst      # Sync + Async lifecycles
│   ├── 03-module-catalog.rst         # File-level catalog
│   └── cross-cutting/
│       ├── 01-business-and-technical-goals.rst
│       ├── 02-development-history.rst
│       ├── 03-request-context-and-mdc.rst
│       ├── 04-feature-flags.rst
│       ├── 05-observability-and-metrics.rst
│       ├── 06-async-tasks-and-sqs.rst
│       ├── 07-ai-gateway-and-stratus.rst
│       ├── 08-auth-and-tenant.rst
│       └── 09-deployment-and-config.rst
└── modules/
    ├── features/
    │   ├── rovo-insights.rst
    │   ├── nudge.rst
    │   └── greeting.rst
    └── platform/
        ├── requestcontext.rst
        ├── stratus.rst
        ├── context.rst
        ├── sqs.rst
        ├── task.rst
        ├── service-metric.rst
        ├── featuregate.rst
        ├── client.rst
        ├── interceptor.rst
        ├── logging.rst
        ├── utility.rst
        ├── exception.rst
        └── config.rst
```

## Verification

All numbers verified `2026-05-05` by:
- `find /Users/tchen7/MyProjects/atlassian_packages/proactive-ai-platform/src -name '*.kt' | wc -l`
- 4 parallel subagents reading every Kotlin file in the source set
- 8 deep-dive PR fetches via Bitbucket MCP (PRs #96–#108)
- Atlassian goal/project/Confluence searches for FY26 H2 OKR
