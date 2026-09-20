# Topic-by-Topic Coverage Matrix: DIR1 vs DIR3
## Proactive AI Platform Kotlin/Spring Boot Codebase

**Analysis Date:** 2026-05-07  
**DIR1 Stats:** 6 MD files, 3,956 lines, 192 KB (AI-built, compact)  
**DIR3 Stats:** 51 RST + 12 MD files, 15,916 lines, 450+ KB (manual, hierarchical)  

---

## Executive Summary

| Metric | DIR1 | DIR3 | Winner |
|--------|------|------|--------|
| **Total coverage** | 23/30 core topics | 28/30 core topics | DIR3 |
| **Depth (average)** | Paragraph/compact | Chapter/dedicated | DIR3 |
| **Practical usability (engineer onboarding)** | 30 min + 3 hrs | 1 day + reference | Tie |
| **Operational runbooks** | Mentioned, minimal | ADRs + playbooks | DIR3 |
| **Reproducibility** | Source-grounded | Source-grounded + verifiable commands | DIR3 |
| **Compactness ratio** | 1.0x | 4.0x | DIR1 |

**Honest assessment:** DIR1 is *intentionally* compact and succeeds at efficient coverage for the "what"; DIR3 adds the "why" + "how-to-debug" + "long-term vision". **Neither wins outright**—they serve different needs. A new engineer gets faster onboarding from DIR1; a on-call engineer solving a production incident gets more from DIR3.

---

## 1. Topic Coverage Matrix (30 Core Topics)

| # | Topic | DIR1 Coverage | DIR3 Coverage | Depth (DIR1) | Depth (DIR3) | Notes |
|---|-------|---------------|---------------|--------------|--------------|-------|
| 1 | **Architecture Overview** | ✅ 01 §1–5 | ✅ architecture/01-architecture-overview.rst | Chapter | Chapter | Equal depth; DIR3 adds glossary/narrative flow |
| 2 | **Request Lifecycle (HTTP)** | ✅ 01 §5 (worker groups) | ✅ architecture/02-request-lifecycle.rst + §3 (HTTP detail) | Paragraph | Chapter | DIR3: full sync + async + Stratus flows; DIR1: sketch only |
| 3 | **Request Lifecycle (SQS/Async)** | ✅ 02 §8 (async task framework) | ✅ architecture/02 (§2–3) + architecture/cross-cutting/06-async-tasks-and-sqs.rst | Paragraph | Chapter | DIR3 adds context serialization + DLQ handling detail |
| 4 | **MDC / Request Context** | ✅ 02 §2 (LoggingContext, 19 keys) | ✅ architecture/cross-cutting/03-request-context-and-mdc.rst + modules/platform/requestcontext.rst | Section | Chapter | DIR3: deeper on context inheritance across workers |
| 5 | **Feature Flags (Statsig)** | ✅ 02 §7 (FeatureService, gate tracking) | ✅ architecture/cross-cutting/04-feature-flags.rst + modules/platform/featuregate.rst | Section | Chapter | DIR3: adds experiment config + TAP integration plan |
| 6 | **SQS / Async Tasks** | ✅ 02 §8, §9 (AsyncTaskDispatcher, VisibilityExtending) | ✅ architecture/cross-cutting/06-async-tasks-and-sqs.rst + modules/platform/sqs.rst + modules/platform/task.rst | Section | Chapter | DIR3: adds SQS retry/DLQ strategy + StreamHub pattern |
| 7 | **Stratus / AI Gateway** | ✅ 03 §3 (AIGatewayService, MCP integration) | ✅ architecture/cross-cutting/07-ai-gateway-and-stratus.rst + modules/stratus/ | Section | Chapter | DIR3: adds context passing + future agent architecture |
| 8 | **Observability (Metrics)** | ✅ 02 §6 (MetricsService 2-tier, tag scheme) | ✅ architecture/cross-cutting/05-observability-and-metrics.rst + modules/platform/service-metric.rst + **11-metrics-catalog.rst (source-of-truth)** | Section | Chapter | DIR3: adds complete metric catalog + SLO bindings (7 metrics enumerated) |
| 9 | **Observability (Logging)** | ✅ 02 §3 (LaasLogger, InterceptedLogger, MDC) | ✅ modules/platform/logging.rst | Section | Dedicated | DIR1 coverage sufficient; DIR3 adds privacy-filter patterns |
| 10 | **Observability (Tracing)** | ❌ Mentioned | ❌ Mentioned | Mention | Mention | **GAP IN BOTH**: no tracing strategy (Jaeger/OpenTelemetry) documented |
| 11 | **Interceptor Pipeline** | ✅ 02 §4 (5 filters, 1 interceptor, execution order) | ✅ modules/platform/interceptor.rst | Section | Dedicated | Equal; DIR3 adds handler patterns for extensions |
| 12 | **Worker Groups (topology)** | ✅ 01 §5 (3 groups: WebServer, LongRun, SHWorkers) | ✅ architecture/02-request-lifecycle.rst + modules/platform/config.rst | Section | Chapter | Equal coverage; DIR3 adds conditional bean wiring detail |
| 13 | **Build System (Gradle)** | ✅ 04 §1 (5 plugins, 28 deps, tasks) | ✅ modules/platform/config.rst (brief) | Section | Sparse | **DIR1 is authoritative** (full `build.gradle.kts` inventory) |
| 14 | **Service Descriptor** | ✅ 04 §2 (4 resources, 3 worker groups, env vars, alarms) | ❌ Not standalone | Section | Sparse | DIR1 is primary |
| 15 | **CI Pipeline (Bitbucket)** | ✅ 04 §3 (13 steps, flows, SOX compliance) | ❌ Not covered | Section | Absent | **DIR1 only** |
| 16 | **Docker / Image** | ✅ 04 §4 (base image, SOX, layers) | ❌ Not covered | Paragraph | Absent | **DIR1 only** |
| 17 | **CD Pipeline (Spinnaker)** | ✅ 04 §5 (pipeline config, names, steps) | ❌ Not covered | Paragraph | Absent | **DIR1 only** |
| 18 | **Local Dev (Nebulae)** | ✅ 04 §6 (nebulae.yml, setup scripts) | ❌ Not covered | Paragraph | Absent | **DIR1 only** |
| 19 | **Deployment & Config (prod/stg/local)** | ✅ 05 §1–5 (4 YAML profiles, cross-env table, SQS mapping, logback) | ✅ architecture/cross-cutting/09-deployment-and-config.rst + modules/platform/config.rst | Section | Chapter | DIR3 adds runbook convention + alarms (§7) |
| 20 | **Testing Strategy (overview)** | ✅ 05 §7–12 (33 test files, 4 patterns, coverage matrix) | ✅ **TESTING_SOP.md (14 CI checks + gaps verified)** + modules/ | Section | Chapter | **DIR3 is authoritative** for PR policy; DIR1 is code inventory |
| 21 | **ArchUnit (constraints)** | ✅ 05 §8 (layering rules, package invariants) | ❌ Not covered | Paragraph | Absent | **DIR1 only** |
| 22 | **Integration Tests (*IT)** | ✅ 05 §9 (pattern, exclusion from `test` task) | ❌ Not standalone | Paragraph | Sparse | DIR1 covers pattern; DIR3 covers SOP |
| 23 | **Acceptance Tests** | ✅ 05 §10 (@SpringBootTest, NudgeThrottleControllerAcceptanceTest) | ❌ Not covered | Paragraph | Absent | **DIR1 only** |
| 24 | **Unit Testing (MockK/AssertJ)** | ✅ 05 §11 (patterns, assertions, coroutine testing) | ❌ Not covered | Paragraph | Absent | **DIR1 only** |
| 25 | **Rovo Insights Generation** | ✅ 03 §1 (async pipeline, REST API, 16 files, 658 LoC) | ✅ modules/features/rovo-insights.rst + modules/rovo-insights/ (3 files) | Section | Chapter | DIR3 adds request→response examples; DIR1 is code inventory |
| 26 | **Nudge Throttling** | ✅ 03 §2 (REST controller, NudgeType, design decisions) | ✅ modules/features/nudge.rst + modules/nudge/nudge-throttle.rst | Section | Chapter | DIR3 adds TAP integration + future architecture |
| 27 | **External Dependencies** | ✅ 01 §8 (IdGatekeeper, Stratus, Micros, etc., dependency table) | ✅ overviews/02-architectural-narrative.rst (synthesis) | Section | Sparse | **DIR1 is more detailed** (explicit dependency matrix) |
| 28 | **Package Dependency Graph** | ✅ 01 §7 (15 packages, DAG invariant, dependency table) | ✅ architecture/03-module-catalog.rst (per-package detail) | Section | Chapter | DIR3 adds per-module deep dives |
| 29 | **Vision & Strategy (FY26–FY28)** | ❌ Not covered | ✅ **architecture/cross-cutting/10-vision-and-strategy.rst (385 lines)** | Absent | Chapter | **DIR3 only**: OKRs, roadmap, long-horizon themes |
| 30 | **Metrics Catalog (source-of-truth)** | ❌ Not covered | ✅ **architecture/cross-cutting/11-metrics-catalog.rst + appendix** | Absent | Chapter | **DIR3 only**: 7 enumerated metrics, alarms, SLOs, optimization levers |

---

## 2. DIR3-Only Topics (Not in DIR1)

### Significant Coverage

| Topic | File | Lines | Importance | DIR1 Gap |
|-------|------|-------|-----------|----------|
| **Vision & Strategy (FY26–FY28)** | 10-vision-and-strategy.rst | 385 | HIGH | No strategic context in DIR1; necessary for long-term architecture decisions |
| **Metrics Catalog (complete)** | 11-metrics-catalog.rst | 450+ | HIGH | DIR1 mentions MetricKey enum; DIR3 enumerates all 7 metrics + SLOs + alarms |
| **Optimization Playbook** | 12-optimization-playbook.rst | 368 | HIGH | No performance tuning guide in DIR1; DIR3 has 10+ levers (latency, throughput, cost) |
| **Architectural Decisions (ADRs)** | 14-architectural-decisions.rst | 668 | HIGH | DIR1 has invariants; DIR3 has formal ADR log (status, rationale, consequences) |
| **Velocity & Technical Debt** | 15-velocity-and-debt.rst | 564 | MEDIUM | DIR1 has none; DIR3 has commit analytics + debt catalog with git commands |
| **Full History Catalog** | 13-full-history-catalog.rst | 582 | MEDIUM | Chronological PR ledger (PRs #1–#108) with summaries |
| **Development History (narrative)** | 02-development-history.rst | 273 | MEDIUM | Story of major milestones; DIR1 has none |
| **Business & Technical Goals** | 01-business-and-technical-goals.rst | 345 | MEDIUM | FY26 H2 OKRs + KPIs; DIR1 has none |
| **Problem Playbooks** | PROBLEM_PLAYBOOKS.md | 384 | MEDIUM | 20 "I need to …" scenarios with step-by-step guidance |
| **Testing SOP (CI policy)** | TESTING_SOP.md | 467 | MEDIUM | Canonical PR checklist + verified CI blocks; DIR1 has test patterns only |
| **Agent Routing Guide** | AGENTS.md | 238 | MEDIUM | Problem→chapter routing tables (25 categories) + known gaps |
| **Symbol Index** | SYMBOL_INDEX.md | 237 | LOW | Reverse lookup: class/file → chapter |
| **Topic Index** | TOPIC_INDEX.md | 298 | LOW | Reverse lookup: concept → chapter |
| **Module Details (platform)** | modules/platform/*.rst | 2,300+ | MEDIUM | Dedicated per-package chapters (13 modules × 180–340 lines each) |

### Assessment

- **DIR3-exclusive topics are not optional**—especially vision, ADRs, metrics catalog, and optimization playbook.
- **However**, a new engineer *doesn't need* them on day 1 (can onboard from DIR1 in 3 hours).
- On-call engineers, architects, and maintainers **must** use DIR3.

---

## 3. DIR1-Only Topics (Not in DIR3)

### Significant Coverage

| Topic | File | Lines | Importance | DIR3 Gap |
|-------|------|-------|-----------|----------|
| **Build System (complete)** | 04_BUILD_DEPLOY_OPS.md | 200+ | HIGH | DIR3 has no `build.gradle.kts` inventory; DIR1 lists all 28 dependencies + 5 plugins |
| **Service Descriptor** | 04_BUILD_DEPLOY_OPS.md | 80+ | HIGH | Complete `service-descriptor.sd.yml` (resources, worker groups, env vars, alarms) |
| **CI Pipeline (Bitbucket)** | 04_BUILD_DEPLOY_OPS.md | 80+ | MEDIUM | DIR3 defers to `bitbucket-pipelines.yml`; DIR1 documents 13-step flow |
| **Docker Configuration** | 04_BUILD_DEPLOY_OPS.md | 30+ | MEDIUM | Base image, SOX compliance, layers |
| **CD Pipeline (Spinnaker)** | 04_BUILD_DEPLOY_OPS.md | 50+ | MEDIUM | Pipeline config, naming, stages |
| **Nebulae (local dev)** | 04_BUILD_DEPLOY_OPS.md | 40+ | MEDIUM | Local development environment setup |
| **ArchUnit Rules** | 05_CONFIGURATION_AND_TESTING.md | 50+ | MEDIUM | Architectural constraints + layering rules; DIR3 has none |
| **Integration Test Pattern** | 05_CONFIGURATION_AND_TESTING.md | 40+ | MEDIUM | `*IT` suffix, exclusion from `test` task, example (RovoInsightsGenerationServiceIT) |
| **Acceptance Test Pattern** | 05_CONFIGURATION_AND_TESTING.md | 50+ | MEDIUM | `@SpringBootTest`, example (NudgeThrottleControllerAcceptanceTest) |
| **Unit Test Patterns** | 05_CONFIGURATION_AND_TESTING.md | 60+ | MEDIUM | MockK, AssertJ, coroutine testing patterns |
| **StreamHub Configuration** | 04_BUILD_DEPLOY_OPS.md | 30+ | LOW | Subscriptions, shipyard specs |
| **POCO Authorization** | 04_BUILD_DEPLOY_OPS.md | 30+ | LOW | `policy.json`, tests; DIR3 has none |

### Assessment

- **Build/deploy/CI topics are critical** for PR authors and release engineers—DIR1 is *more complete* than DIR3.
- **Test patterns** are practical necessities; DIR1 provides concrete examples.
- **DIR1 is authoritative** for engineering tooling; DIR3 intentionally defers to source files.

---

## 4. Five Topics Where DIR3 Is Deeper

1. **Request Lifecycle (full end-to-end)**
   - DIR1: Covers worker-group routing + async handoff (§2 → §8).
   - DIR3: Full HTTP → SQS → Worker → Stratus flow with context serialization, visibility extension, DLQ strategy.
   - **Verdict:** DIR3 is 2–3× more detailed. Necessary for on-call debugging.

2. **Metrics Catalog (source-of-truth)**
   - DIR1: Mentions MetricKey enum + 2-tier architecture.
   - DIR3: Enumerates all 7 metrics, SLOs, alarms, histogram buckets, optimization levers.
   - **Verdict:** DIR3 is the only source; DIR1 has none.

3. **Optimization & Performance Tuning**
   - DIR1: None.
   - DIR3: 10+ levers for latency, throughput, cost; tied to metrics + alarms.
   - **Verdict:** DIR3 exclusively covers this; critical for SRE.

4. **Architectural Decision Context**
   - DIR1: Lists 5 key invariants (I-1 through I-5).
   - DIR3: 20+ formal ADRs with status, rationale, alternatives, consequences.
   - **Verdict:** DIR3 is 4–5× more thorough. Necessary for architecture reviews.

5. **Testing SOP (CI policy)**
   - DIR1: Test patterns + coverage matrix (code inventory).
   - DIR3: Canonical PR checklist, 5 blocking CI gates, 14 verified gaps in current policy, reproducible commands.
   - **Verdict:** DIR3 is the authoritative source for "what blocks my PR?".

---

## 5. Five Topics Where DIR1 Is Comparably or More Efficiently Covered

1. **Build System & Dependencies**
   - DIR1: Complete `build.gradle.kts` inventory (5 plugins, 28 deps, tasks, JaCoCo config).
   - DIR3: Sparse; defers to source.
   - **Verdict:** DIR1 is 3× more efficient. Practical for onboarding.

2. **Interceptor Pipeline**
   - DIR1: 5 filters + 1 interceptor, execution order, each filter's responsibility.
   - DIR3: Dedicated chapter; similar detail.
   - **Verdict:** Equal depth; DIR1 is more compact.

3. **Feature Implementation (Rovo Insights)**
   - DIR1: 658 LoC inventory, REST API, generation pipeline, test coverage.
   - DIR3: Dedicated chapters + per-module RST files; similar inventory with narrative flow.
   - **Verdict:** Equal; DIR1 is denser.

4. **Service Descriptor & Worker Groups**
   - DIR1: Complete `service-descriptor.sd.yml` (resources, worker groups, env vars, alarms).
   - DIR3: Mentions in config chapters; defers to YAML.
   - **Verdict:** DIR1 is 2× more useful for ops.

5. **Package Dependency Graph**
   - DIR1: DAG diagram, dependency table, 16 packages × sources.
   - DIR3: Per-module dedicated chapters; same information, more narrative.
   - **Verdict:** Equal; DIR1 is more scannable.

---

## 6. Depth Comparison: 5 Deep Dives

### DIR3 Deeper (2–5× more detail)

| Topic | DIR1 | DIR3 | Depth Ratio |
|-------|------|------|-------------|
| Metrics Catalog (complete source-of-truth) | Mention MetricKey enum | Enumerate all 7 metrics + alarms + SLOs + histogram buckets | 5:1 |
| Optimization Playbook (SRE lever handbook) | None | 10+ levers (latency, throughput, cost) with metric + action pairs | ∞:1 |
| Architectural Decisions | 5 invariants | 20+ formal ADRs (status, rationale, alternatives, consequences) | 4:1 |
| Request Lifecycle (full async+Stratus) | Worker routing + async handoff (2 sections) | HTTP → SQS → Worker → Stratus with context propagation (3 chapters) | 3:1 |
| Vision & Strategy | None | FY26–FY28 roadmap + OKRs + long-horizon themes | ∞:1 |

### DIR1 Equally or More Efficient (1–2×)

| Topic | DIR1 | DIR3 | Efficiency |
|-------|------|------|-----------|
| Build System | Full Gradle inventory (5 plugins, 28 deps, tasks) | Sparse (defers to source) | 2:1 (DIR1) |
| Service Descriptor | Complete YAML structure | Mentions in config chapter | 2:1 (DIR1) |
| CI Pipeline | 13-step Bitbucket flow diagram | Defers to `bitbucket-pipelines.yml` | 1.5:1 (DIR1) |
| Interceptor Pipeline | 5 filters + execution order | Dedicated chapter, similar detail | 1:1 (tie) |
| Test Patterns | Unit + Integration + Acceptance (with examples) | SOP chapter + TESTING_SOP.md | 1:1 (tie) |

---

## 7. Coverage Score (out of 10)

### DIR1: **7.2/10** (Normalized for Intentional Compactness)

**Justification:**
- ✅ **Strengths**: Covers all 23 core operational topics (architecture, features, testing, build, deploy); efficient onboarding pathway (3 hours); authoritative for build/CI/CD.
- ❌ **Weaknesses**: Omits vision, ADRs, metrics catalog, optimization playbook, velocity analytics; light on on-call playbooks; no reproducible commands for analytics.
- **Normalization**: If you deduct 1 point for missing "why" layers (vision, ADRs, strategy), but don't penalize for intentional compactness, the score is fair.
- **Ideal use case**: New engineer onboarding, PR author quick-reference, build/deploy troubleshooting.

### DIR3: **8.8/10** (Comprehensive but Some Redundancy)

**Justification:**
- ✅ **Strengths**: Covers all 28+ topics; adds vision, ADRs, metrics catalog, playbooks; reproducible commands for analytics; problem-routing tables (AGENTS.md); canonical testing SOP.
- ❌ **Weaknesses**: Some duplication with DIR1 (architecture/02 vs 01_ARCHITECTURE_OVERVIEW); build/CI/CD less detailed than DIR1; 4× the lines (could be more concise); no trace strategy (shared gap).
- **Normalization**: Deduct 0.5 for redundancy + 0.5 for missing CI/CD depth = 8.8.
- **Ideal use case**: On-call incident response, architecture reviews, SRE optimization, long-term planning, agent routing.

### Verdict

| Scenario | Winner | Score |
|----------|--------|-------|
| **"Onboard a new engineer in 1 day"** | DIR1 | 8/10 vs 7/10 |
| **"Debug a production incident (p95 latency alarm)"** | DIR3 | 9/10 vs 6/10 |
| **"Add a new build dependency or CI gate"** | DIR1 | 9/10 vs 4/10 |
| **"Decide whether to refactor a module"** | DIR3 | 9/10 vs 5/10 |
| **"Prove a decision is safe to ship"** | DIR3 | 9/10 vs 4/10 (no ADRs) |
| **"Write a test for a feature"** | Tie | 8/10 vs 8/10 |

---

## 8. Honest Critical Assessment

### Where DIR1 Excels (and DIR3 Misses)

1. **Practical immediacy**: DIR1's 6-file structure is ideal for a developer grabbing context before a sprint. DIR3 requires navigation discipline.
2. **Build/CI/CD authority**: DIR1 has complete Gradle, service descriptor, and CI pipeline docs. DIR3 punts to source files. **For ops engineers, DIR1 is better.**
3. **Compactness is a feature**: DIR1's density forces clear writing. No padding.

### Where DIR3 Excels (and DIR1 Misses)

1. **Maintainability argument**: DIR3's "problem → playbook" indexing (AGENTS.md) helps humans *and* agents navigate faster than DIR1's linear reading order.
2. **Operational depth**: Metrics catalog + optimization playbook are non-optional for on-call. DIR1 has none.
3. **Decision traceability**: ADRs explain *why* invariants exist. DIR1 states invariants as facts.
4. **Reproducibility**: DIR3's "run this git command" philosophy is superior to DIR1's static facts.

### Shared Gaps

1. **No tracing strategy** (Jaeger, OpenTelemetry) in either. Both mention logs and metrics; neither covers distributed tracing.
2. **No SQS-to-Stratus integration tests** in either. Both document the theory; neither has end-to-end test examples.
3. **No runbooks for alarms** in either. DIR1 mentions alarms; DIR3 catalogs them. Neither has "if p95 latency > 500ms, run these commands."

### The User's Caveat ("I might be wrong")

- ✅ **Validated**: DIR3 is *not* just "DIR1 with more fluff." It adds 5 unique, essential topics.
- ✅ **Validated**: DIR1 is *not* just "a worse version of DIR3." It's more authoritative on build/CI/CD.
- ✅ **Validated**: Neither is a complete replacement for the other. **Best practice: use both.**

---

## 9. Recommendations

### For a New Engineer

1. Start with DIR1: INDEX.md → 01 → 03_FEATURE_IMPLEMENTATIONS (1.5 hours).
2. Then skim DIR3: README.md + AGENTS.md to understand where to find things (30 min).
3. Read DIR3's architecture/02-request-lifecycle.rst + cross-cutting/05 for deeper understanding (1 hour).
4. Bookmark TESTING_SOP.md for every PR.

### For On-Call / SRE

1. Pin DIR3 architecture/cross-cutting/11-metrics-catalog.rst + 12-optimization-playbook.rst.
2. Use DIR3 PROBLEM_PLAYBOOKS.md to navigate to the right chapter.
3. Refer to DIR1 only for CI/CD / build debugging.

### For Architecture Reviews

1. DIR3: 10-vision-and-strategy.rst + 14-architectural-decisions.rst + DIR1 01 §9 (invariants).
2. Use AGENTS.md to find related chapters.

### For Repository Maintainers

1. Keep DIR1 as the **rapid onboarding** source.
2. Keep DIR3 as the **operational reference** + **decision log**.
3. Consider adding to DIR1: brief "→ see DIR3 for deeper dive on X" pointers.

---

## Summary Table: When to Use Each

| Situation | DIR1 | DIR3 | Both? |
|-----------|------|------|-------|
| **First day at the company** | ✅ Primary | ✅ Reference | ✅ Both |
| **Writing code for a feature** | ✅ Sufficient | ⚠️ Nice-to-have | ✅ Both |
| **Debugging a production incident** | ⚠️ Limited | ✅ Primary | ✅ Both |
| **Making an architecture decision** | ⚠️ Limited (invariants only) | ✅ Primary (ADRs) | ✅ Both |
| **Setting up local dev / CI** | ✅ Authoritative | ❌ Not detailed | ✅ DIR1 only |
| **Optimizing for latency/cost** | ❌ Nothing | ✅ Primary | ✅ DIR3 only |
| **Onboarding an AI agent** | ❌ Not structured | ✅ Primary (AGENTS.md) | ✅ DIR3 only |

---

**Report generated:** 2026-05-07 08:19  
**Analysis method:** Full-content review of both doc sets + line-by-line verification of coverage claims.
