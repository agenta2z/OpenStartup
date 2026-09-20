# AGENTS.md — AI-Agent Entry Point for Proactive AI Platform Docs

> **Read this file FIRST if you are an AI agent working on the
> `proactive-ai-platform` codebase.** It tells you, for any arbitrary
> problem, **which document(s) to load** to find the answer in 1–3 hops.
>
> If you are a human, you can also use this — it doubles as a directive
> "where do I look?" guide.

---

## How to use this document

1. **Find your problem in Section 1** below ("Problem → Documents Routing
   Table"). It covers ~25 common problem categories.
2. If your problem isn't there, use Section 2 (Topic & Keyword Index) or
   Section 3 (Symbol/File Reverse Map).
3. If a document still doesn't answer it, that's a **documentation gap**
   — Section 4 lists known gaps so you don't waste cycles searching.
4. Section 5 has the canonical reproducibility commands so you can
   re-derive any number cited in any chapter.
5. Section 6 has the machine-readable manifest reference (see also
   `MANIFEST.json` at this directory).

---

## 1. Problem → Documents Routing Table

The 25 most-common problem categories. Each row tells you the **primary**
chapter to load, **then** any additional chapters you'll need for the full
answer.

### A. Investigating production / on-call

| Problem | Primary doc | Then load |
|---|---|---|
| **Why is endpoint p95 latency high?** | `architecture/cross-cutting/12-optimization-playbook.rst` Part 2 | `11-metrics-catalog.rst` Parts 1–2 (which metrics exist) + `09-deployment-and-config.rst` (alarms) |
| **An alarm fired — what do I do?** | `architecture/cross-cutting/11-metrics-catalog.rst` Part 4 (alarm catalog) | `09-deployment-and-config.rst` Part 7 (runbook convention) — note: **runbooks are TBD** today |
| **DLQ depth alarm fired** | `architecture/cross-cutting/06-async-tasks-and-sqs.rst` | `12-optimization-playbook.rst` Lever 4.x |
| **Service is throttling / 429s** | `architecture/cross-cutting/05-observability-and-metrics.rst` | `11-metrics-catalog.rst` Part 7 (egress timeouts) |
| **Splunk pivot / find a request_id** | `architecture/cross-cutting/03-request-context-and-mdc.rst` | `12-logging.rst` (module) |

### B. Adding / changing code

| Problem | Primary doc | Then load |
|---|---|---|
| **Add a new MetricKey** | `modules/platform/service-metric.rst` | `11-metrics-catalog.rst` Part 1 (the existing 7 enum values) |
| **Add a new Statsig feature flag** | `architecture/cross-cutting/04-feature-flags.rst` | `modules/platform/featuregate.rst` |
| **Add a new SQS consumer** | `modules/platform/sqs.rst` + `modules/platform/task.rst` | `architecture/cross-cutting/06-async-tasks-and-sqs.rst` + `modules/platform/config.rst` (worker-group conditions) |
| **Add a new REST controller** | `architecture/02-request-lifecycle.rst` | `modules/platform/interceptor.rst` (interceptor order) |
| **Add a new alarm** | `architecture/cross-cutting/11-metrics-catalog.rst` Part 4 | `architecture/cross-cutting/09-deployment-and-config.rst` (YAML schema) |
| **Add a new external dependency (egress)** | `architecture/cross-cutting/11-metrics-catalog.rst` Part 7 | `architecture/cross-cutting/09-deployment-and-config.rst` |
| **Add a new anonymous endpoint (skip SLAuth)** | `modules/platform/config.rst` (MvcSecurityConfig) | `architecture/cross-cutting/08-auth-and-tenant.rst` |
| **Add a new ADR** | `architecture/cross-cutting/14-architectural-decisions.rst` (schema at top) | — |

### C. Understanding why something is the way it is

| Problem | Primary doc | Then load |
|---|---|---|
| **Why SQS over Kafka?** | `architecture/cross-cutting/14-architectural-decisions.rst` ADR-002 | — |
| **Why three worker groups?** | `architecture/cross-cutting/14-architectural-decisions.rst` ADR-001 | `modules/platform/config.rst` |
| **Why MCP / Integrations Service?** | `architecture/cross-cutting/14-architectural-decisions.rst` ADR-005 | `modules/platform/stratus.rst` |
| **Why visibility extension?** | `architecture/cross-cutting/14-architectural-decisions.rst` ADR-004 | `modules/platform/sqs.rst` |
| **Why LaasLogger required?** | `architecture/cross-cutting/14-architectural-decisions.rst` ADR-009 | `modules/platform/logging.rst` |
| **Why Statsig two-phase context?** | `architecture/cross-cutting/14-architectural-decisions.rst` ADR-006 | `architecture/cross-cutting/04-feature-flags.rst` |

### D. Strategy & business context

| Problem | Primary doc | Then load |
|---|---|---|
| **What is the FY26 OKR?** | `architecture/cross-cutting/01-business-and-technical-goals.rst` Part 1 | — |
| **Where is PAI heading in FY27+?** | `architecture/cross-cutting/10-vision-and-strategy.rst` | — |
| **Who competes with PAI?** | `architecture/cross-cutting/10-vision-and-strategy.rst` Part 6 | — |
| **What metric should I move first?** | `architecture/cross-cutting/12-optimization-playbook.rst` | `01-business-and-technical-goals.rst` |

### E. History & decisions

| Problem | Primary doc | Then load |
|---|---|---|
| **What shipped recently?** | `architecture/cross-cutting/02-development-history.rst` (narrative) | `13-full-history-catalog.rst` (per-PR ledger) |
| **Who has worked on X?** | `architecture/cross-cutting/15-velocity-and-debt.rst` Part 2 (contributor distribution) | `13-full-history-catalog.rst` Part 5 (strategic PRs by author) |
| **What's the bus factor?** | `architecture/cross-cutting/14-architectural-decisions.rst` RISK-001 | `15-velocity-and-debt.rst` Part 11 |

### F. Finding code

| Problem | Primary doc | Then load |
|---|---|---|
| **Where is class `X` defined?** | `SYMBOL_INDEX.md` (this directory) | the chapter linked from there |
| **What does package `Y` do?** | `architecture/03-module-catalog.rst` | the per-module page in `modules/platform/` or `modules/features/` |
| **What file should I edit to change behaviour Z?** | `SYMBOL_INDEX.md` for the class | the per-module page |

---

## 2. Topic & Keyword Index

See `TOPIC_INDEX.md` in this directory for a full alphabetical index of
~120 topics → chapter(s).

Quick high-frequency topics:

| Topic | Primary chapter |
|---|---|
| Async task framework | `architecture/cross-cutting/06-async-tasks-and-sqs.rst` |
| MDC / logging context | `architecture/cross-cutting/03-request-context-and-mdc.rst` |
| Statsig / feature flags | `architecture/cross-cutting/04-feature-flags.rst` |
| SQS consumer / queue / DLQ | `architecture/cross-cutting/06-async-tasks-and-sqs.rst` |
| AI Gateway / Stratus | `architecture/cross-cutting/07-ai-gateway-and-stratus.rst` |
| MCP / Integrations Service | `architecture/cross-cutting/07-ai-gateway-and-stratus.rst` + ADR-005 |
| SLAuth / tenant context | `architecture/cross-cutting/08-auth-and-tenant.rst` |
| Spinnaker / nebulae / deployment | `architecture/cross-cutting/09-deployment-and-config.rst` |
| FY26 OKR / business goals | `architecture/cross-cutting/01-business-and-technical-goals.rst` |
| Three-horizon vision | `architecture/cross-cutting/10-vision-and-strategy.rst` |
| Alarms / SLOs / runbooks | `architecture/cross-cutting/11-metrics-catalog.rst` Parts 4–5 |
| Latency optimisation | `architecture/cross-cutting/12-optimization-playbook.rst` Part 2 |
| Throughput optimisation | `architecture/cross-cutting/12-optimization-playbook.rst` Part 3 |
| ADRs / decisions | `architecture/cross-cutting/14-architectural-decisions.rst` |
| Bus-factor / contributor concentration | `architecture/cross-cutting/15-velocity-and-debt.rst` Part 2 |

---

## 3. Symbol & File Reverse Map

See `SYMBOL_INDEX.md` in this directory for a per-class/per-file map back
to the chapter that covers it. Built from the live source on 2026-05-05
(121 type declarations counted).

---

## 4. Known documentation gaps (don't waste cycles searching)

If your problem is one of the following, the docs **do not currently
cover it** — use the in-repo source as the source of truth:

* **Live OKR progress %** — Atlas Goal MCP returns empty; visit
  ATLAS-115305 directly or ask Brian Feldman (DRI).
* **Runbook URLs** — five of six alarms have `Runbook: TBD` in
  `service-descriptor.sd.yml`.
* **Per-endpoint p95/p99 dashboard URLs** — only the global
  `http.server.requests` histogram is registered; per-endpoint dashboards
  rely on tag-filtering.
* **JVM heap dump / thread dump procedure** — not documented; standard
  Atlassian Micros runbooks apply (go/micros-runbook).
* **Graceful shutdown semantics** — not documented; defer to Spring
  Boot defaults.
* **TLS / certificate management** — handled by Micros service mesh;
  not documented in this repo.
* **CORS / security headers** — handled by SLAuth + the Micros gateway;
  not documented in this repo.
* **GDPR / data deletion** — no PII is persisted in PAI today;
  re-evaluate when caching strategy lands.
* **Rate limiting (per tenant / per user)** — not implemented; would
  belong with throttling logic when nudge surface ramps.
* **Circuit breaker pattern** — not implemented; relies on mesh egress
  retry policies (`retryOn5xxAnd429Policy` in service descriptor).
* **Audit logging** — not implemented; LaasLogger MDC keys partially
  cover this for request traces.
* **PAI FY27 vision document** — none authored by the team yet;
  `10-vision-and-strategy.rst` is a synthesised reconstruction.

If your problem is one of these and you must answer it, **the answer is
to write the documentation** as part of your PR. See "How to add a new
ADR" in `14-architectural-decisions.rst` and the reproducibility
checklist at the bottom of `15-velocity-and-debt.rst`.

---

## 5. Reproducibility commands

To re-derive any number cited in any chapter, run these from
`atlassian_packages/proactive-ai-platform/`:

```bash
# Total commits, contributors, AIX tickets, fix ratio, churn
git log --oneline | wc -l
git log --pretty=format:'%an' | sort | uniq -c | sort -rn
git log --grep='AIX-' --oneline | grep -oE 'AIX-[0-9]+' | sort -u
git log --grep='fix\|bug\|hotfix' -i --oneline | wc -l
git log --pretty=format: --name-only | grep -v '^$' | sort | uniq -c | sort -rn | head

# Symbol counts
grep -rEn '^(public )?(class|interface|object|enum class|sealed )' --include='*.kt' src/main/kotlin/ | wc -l
find src/main -name '*.kt' | wc -l
find src/test -name '*.kt' | wc -l

# Verify alarms / dependencies / sizing
grep -nE 'AlarmName:|Threshold:|Priority:|timeoutMs:|MaxRAMPercentage' service-descriptor.sd.yml
```

---

## 6. Machine-readable manifest

`MANIFEST.json` at this directory contains the same chapter→topics→
symbols mapping in JSON form. An agent can `cat MANIFEST.json | jq ...`
to filter chapters by topic, audience, or keyword without parsing RST.

Schema documented at the top of `MANIFEST.json`.

---

## 7. Recommended agent traversal pattern

For an arbitrary new problem:

```
1. Check Section 1 (Problem → Doc routing) for an exact match.
   If found → load primary chapter, optionally then-load secondaries.

2. If not in Section 1, check Section 2 (Topic Index).
   If found → load the chapter that owns the topic.

3. If not in Section 2 but you have a class/file name,
   check SYMBOL_INDEX.md for a chapter pointer.

4. If still not found, check Section 4 (Known Gaps).
   If your problem is listed there → STOP searching the docs;
   the answer requires writing new docs (or asking the team).

5. If not in Section 4, fall back to:
   a. `architecture/03-module-catalog.rst` (file-by-file reference)
   b. `architecture/00-glossary.rst`
   c. `grep` against the source tree directly.
```

---

## 8. Relationship to other top-level files at this directory

* `index.rst` — Sphinx-style master index for human reading.
* `README.md` — human-friendly quick-nav table.
* **`AGENTS.md` (this file)** — AI-agent entry point.
* `MANIFEST.json` — machine-readable chapter manifest.
* `SYMBOL_INDEX.md` — class/file → chapter reverse map.
* `TOPIC_INDEX.md` — topic/keyword → chapter index.
* `PROBLEM_PLAYBOOKS.md` — long-form playbook for ~20 common scenarios.

If you load only one file, load this one. If you load two, load this
one and `MANIFEST.json`.
