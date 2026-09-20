# PROBLEM_PLAYBOOKS.md — "I need to …" Scenarios

> **Purpose.** End-to-end playbooks for the most common things a human
> or AI agent will be asked to do in the proactive-ai-platform codebase.
> Each playbook gives the **ordered chapter traversal**, the **commands
> to run**, and the **acceptance criteria** for "done".
>
> Companion files: [`AGENTS.md`](AGENTS.md) (problem-routing tables),
> [`SYMBOL_INDEX.md`](SYMBOL_INDEX.md) (class→chapter), [`TOPIC_INDEX.md`](TOPIC_INDEX.md)
> (concept→chapter), [`MANIFEST.json`](MANIFEST.json) (machine-readable).

---

## Playbook index

1. [Investigate high p95 latency on a user-facing endpoint](#1-investigate-high-p95-latency)
2. [Add a new MetricKey](#2-add-a-new-metrickey)
3. [Add a new Statsig feature flag](#3-add-a-new-statsig-feature-flag)
4. [Add a new SQS-driven async task type](#4-add-a-new-sqs-driven-async-task-type)
5. [Add a new REST endpoint (sync)](#5-add-a-new-rest-endpoint-sync)
6. [Add a new anonymous (unauthenticated) endpoint](#6-add-a-new-anonymous-endpoint)
7. [Add a new alarm with a runbook](#7-add-a-new-alarm-with-a-runbook)
8. [Add a new external (egress) dependency](#8-add-a-new-external-egress-dependency)
9. [Promote a Priority-Low alarm to Priority-Medium](#9-promote-an-alarm-priority)
10. [Investigate why a worker-conditional bean isn't created](#10-investigate-conditional-bean-not-created)
11. [Investigate a DLQ-depth alarm](#11-investigate-dlq-depth)
12. [Find the file/code that handles concept X](#12-find-code-for-a-concept)
13. [Pivot Splunk by `request_id` across the WebServer→Worker boundary](#13-splunk-pivot-cross-jvm)
14. [Author a new ADR](#14-author-a-new-adr)
15. [Compute current contributor / commit / churn analytics](#15-compute-velocity-analytics)
16. [Onboard a new engineer to the codebase in 1 day](#16-onboarding-1-day)
17. [Onboard an AI coding agent in 5 minutes](#17-onboard-ai-agent)
18. [Plan an OKR-moving PR (with required PR-description checklist)](#18-plan-an-okr-moving-pr)
19. [De-risk RISK-001 (single-contributor concentration)](#19-de-risk-bus-factor)
20. [Decide whether a behaviour is documented vs. a documentation gap](#20-decide-doc-vs-gap)

---

## 1. Investigate high p95 latency

**Read order:**
1. [`12-optimization-playbook.rst`](architecture/cross-cutting/12-optimization-playbook.rst) Part 2 — latency levers (3 ranked options).
2. [`11-metrics-catalog.rst`](architecture/cross-cutting/11-metrics-catalog.rst) Part 7 — egress timeouts (the **600 s ai-gateway** timeout dominates).
3. [`05-observability-and-metrics.rst`](architecture/cross-cutting/05-observability-and-metrics.rst) — how to query Splunk/SignalFx.

**Commands:**
```bash
# In Splunk:
index=micros service=proactive-ai-platform endpoint="<your-endpoint>"
| stats p95(duration_ms) by hour
```

**Acceptance:** root cause classified as one of (a) AI-Gateway sync call (use Lever 2.1: convert to async), (b) executor starvation (Lever 2.2), (c) downstream timeout (Lever 2.3).

---

## 2. Add a new MetricKey

**Read order:**
1. [`SYMBOL_INDEX.md`](SYMBOL_INDEX.md) §9 — find `MetricKey.kt`.
2. [`mod/platform/service-metric.rst`](modules/platform/service-metric.rst) — how `MetricsService` consumes the enum.
3. [`11-metrics-catalog.rst`](architecture/cross-cutting/11-metrics-catalog.rst) Part 1 — current 7 enum values + their LIVE/WIRED/PLANNED status.

**Steps:**
1. Add a new entry to `MetricKey.kt` enum with the wire name (use dotted prefix matching the package, e.g., `nudge.throttle.decision`).
2. Add the `count()` / `time()` call site in your code.
3. **In the same PR**, add a row to Part 1 of the metrics catalog.
4. **In the same PR**, if this metric will back an alarm, draft the alarm in `service-descriptor.sd.yml` (see Playbook #7).

**Anti-pattern (avoid):** adding the enum value without an emit site. 3/7 of today's enum values are zombies.

**Acceptance:** new metric appears in SignalFx within 1 deploy + 5 min lag, and is documented.

---

## 3. Add a new Statsig feature flag

**Read order:**
1. [`04-feature-flags.rst`](architecture/cross-cutting/04-feature-flags.rst) — Statsig SDK + two-phase context.
2. [`mod/platform/featuregate.rst`](modules/platform/featuregate.rst) — implementation.
3. [`14-architectural-decisions.rst`](architecture/cross-cutting/14-architectural-decisions.rst) ADR-006 — why two-phase.

**Steps:**
1. Decide: tenant-scoped flag → use `checkGate(...)`. Otherwise `checkGateWithLimitedContext(...)`.
2. Add an entry to `AiFeatureGates` enum (transient experiment) or `PermanentFeatureGates` (long-lived gate).
3. Configure the flag in Statsig console; coordinate with AIX team for rollout schedule.
4. Wire in the call site; **always** provide a `defaultValue` arg (defensive against Statsig SDK errors).

**Acceptance:** flag is callable with the right context phase; default value is safe; flag is registered with AIX rollout team.

---

## 4. Add a new SQS-driven async task type

**Read order:**
1. [`06-async-tasks-and-sqs.rst`](architecture/cross-cutting/06-async-tasks-and-sqs.rst) — full pipeline.
2. [`mod/platform/task.rst`](modules/platform/task.rst) — `AsyncTask` + `AsyncTaskHandler` template.
3. [`14-architectural-decisions.rst`](architecture/cross-cutting/14-architectural-decisions.rst) ADRs 002–004 — why SQS, why context replay, why visibility extension.
4. [`mod/platform/config.rst`](modules/platform/config.rst) — worker-group conditions (decide which pool will run it).

**Steps:**
1. Define a new sealed subclass of `AsyncTask` with `@JsonTypeInfo` discriminator.
2. Implement an `AsyncTaskHandler<MyTask>` Spring `@Service`.
3. Add a queue to `service-descriptor.sd.yml` with explicit `VisibilityTimeout` and `MaxReceiveCount` and a DLQ.
4. **Make the handler idempotent** (SQS at-least-once delivery — see [Lever 4.2](architecture/cross-cutting/12-optimization-playbook.rst)).
5. Add a `@Conditional(OnLongRunWorkerNodeOrLocalCondition::class)` SQS-consumer bean wiring this handler to the queue.
6. **Same PR:** add visibility-extender awareness if the task can run > 360 s (see ADR-004).
7. **Same PR:** add an alarm for DLQ depth (Playbook #7).

**Acceptance:** task survives a worker restart; full Splunk pivot works (Playbook #13).

---

## 5. Add a new REST endpoint (sync)

**Read order:**
1. [`02-request-lifecycle.rst`](architecture/02-request-lifecycle.rst) — what runs in what order.
2. [`mod/platform/interceptor.rst`](modules/platform/interceptor.rst) — the two interceptors that fire.
3. [`08-auth-and-tenant.rst`](architecture/cross-cutting/08-auth-and-tenant.rst) — what auth context you can rely on inside the handler.
4. [`mod/features/<feature>/`](modules/features) — pattern for your feature.

**Steps:**
1. Create a `@RestController` in the right `feature/<x>/api/` package.
2. Annotate handler with `@RequestAttribute(USER) user: User` if you need the authenticated user.
3. Add request DTOs in `feature/<x>/api/domain/` if they cross the boundary.
4. **If your endpoint will call AI Gateway sync**, do not. Use Playbook #4 (async task) and have the front end poll.
5. Register a `MetricKey` for the endpoint (Playbook #2) and emit `count()` + `timeAndCountResult()` for it.

**Acceptance:** endpoint passes integration tests; SLAuth-protected by default; appears in `http.server.requests` histogram.

---

## 6. Add a new anonymous endpoint

**Read order:**
1. [`SYMBOL_INDEX.md`](SYMBOL_INDEX.md) §2 — find `MvcSecurityConfig.kt`.
2. [`mod/platform/config.rst`](modules/platform/config.rst) §"Security Bypass Surface" — convention.
3. [`08-auth-and-tenant.rst`](architecture/cross-cutting/08-auth-and-tenant.rst).

**Steps:**
1. Add the path string to the `anonymousPaths()` bean's list.
2. **Get an AppSec review** — this is a security-sensitive surface change.
3. Document the new path in Part 1 of `08-auth-and-tenant.rst`.

**Acceptance:** path returns 200 without `X-Slauth-*` headers; AppSec sign-off recorded in PR description.

---

## 7. Add a new alarm with a runbook

**Read order:**
1. [`11-metrics-catalog.rst`](architecture/cross-cutting/11-metrics-catalog.rst) Part 4 — current alarms & schema.
2. [`14-architectural-decisions.rst`](architecture/cross-cutting/14-architectural-decisions.rst) ADR-012 — why everything is currently `Priority: Low`.
3. [`09-deployment-and-config.rst`](architecture/cross-cutting/09-deployment-and-config.rst) — runbook URL convention (`go/proactive-ai-platform-runbook`).

**Steps:**
1. Add an `AlarmName` block under the right resource in `service-descriptor.sd.yml` (model on existing ones in lines ~120-191).
2. Author the runbook on Confluence under `go/proactive-ai-platform-runbook` (today most are `TBD` — Playbook #19).
3. Set `Priority: Low` initially; promote per Playbook #9 once it has demonstrated low false-positive rate.
4. Update `11-metrics-catalog.rst` Part 4 in the same PR.

**Acceptance:** alarm visible in SignalFx; runbook URL resolvable.

---

## 8. Add a new external (egress) dependency

**Read order:**
1. [`11-metrics-catalog.rst`](architecture/cross-cutting/11-metrics-catalog.rst) Part 7 — current 3 dependencies + their timeouts.
2. [`mod/platform/client.rst`](modules/platform/client.rst) — `HttpClientCommons` and `Audiences`.

**Steps:**
1. Add a new entry to `Audiences` for the SLAuth audience id of the new service.
2. Add the dependency block in `service-descriptor.sd.yml` §`serviceProxy.egress.dependencies` with **explicit timeout and retry policy**.
3. **Be aware** that any ms over your timeout caps your endpoint p95 (see Playbook #1, Lever 2.3).
4. Document in Part 7 of metrics catalog.

**Acceptance:** mesh routing works locally + in stg; timeout is justified in PR description.

---

## 9. Promote an alarm priority

**Read order:**
1. [`11-metrics-catalog.rst`](architecture/cross-cutting/11-metrics-catalog.rst) Part 4.
2. [`14-architectural-decisions.rst`](architecture/cross-cutting/14-architectural-decisions.rst) ADR-012.
3. [`12-optimization-playbook.rst`](architecture/cross-cutting/12-optimization-playbook.rst) Levers 4.3 + 5.1.

**Pre-conditions (ALL required):**
* Runbook authored and tested.
* Alarm has had ≥ 1 month of zero false-positive history at `Priority: Low`.
* On-call rotation in Opsgenie includes routing for this priority.

**Steps:**
1. Change `Priority:` in `service-descriptor.sd.yml`.
2. Update Part 4 of metrics catalog.
3. Notify the team in `#help-ai-experience`.

**Acceptance:** next on-call rotation includes the alarm; one drill-fire confirms paging works.

---

## 10. Investigate "conditional bean not created"

**Read order:**
1. [`mod/platform/config.rst`](modules/platform/config.rst) — both `Condition` classes, what they check.
2. [`14-architectural-decisions.rst`](architecture/cross-cutting/14-architectural-decisions.rst) ADR-001 — why the gating exists.

**Diagnostic:**
1. Print `MICROS_GROUP` env var in the failing pod: `kubectl exec ... -- env | grep MICROS_GROUP`.
2. If unset → defaults to `WebServer`; neither worker condition matches → consumer not created → expected.
3. If set incorrectly → fix in `nebulae.yml` deploy spec.
4. If set correctly → check Spring bean log: `grep 'OnLongRunWorkerNodeOrLocalCondition matched\|did not match'` in startup logs.

**Acceptance:** Spring startup log shows the condition decision matching the deployed `MICROS_GROUP`.

---

## 11. Investigate a DLQ-depth alarm

**Read order:**
1. [`06-async-tasks-and-sqs.rst`](architecture/cross-cutting/06-async-tasks-and-sqs.rst).
2. [`12-optimization-playbook.rst`](architecture/cross-cutting/12-optimization-playbook.rst) Lever 4.x.
3. [`mod/platform/task.rst`](modules/platform/task.rst).

**Steps:**
1. Read the dead messages with `aws sqs receive-message --queue-url <DLQ url>`.
2. Group by failure reason (visible in MDC of original-attempt Splunk traces — Playbook #13).
3. If transient downstream → consider Lever 4.1 (raise `MaxReceiveCount`).
4. If handler bug → fix the handler, then **redrive** the DLQ.
5. If quota exhaustion → escalate to AI Gateway team.

**Acceptance:** DLQ drains; root cause documented in PR description.

---

## 12. Find code for a concept

**Order to try:**
1. **Concept name** → [`TOPIC_INDEX.md`](TOPIC_INDEX.md) → load the chapter.
2. **Class/interface name** → [`SYMBOL_INDEX.md`](SYMBOL_INDEX.md) → file path + chapter.
3. **File path** → [`SYMBOL_INDEX.md`](SYMBOL_INDEX.md) §"File-path → chapter quick map".
4. If none of the above → fall back to:
   * `arch/03-module-catalog.rst` (file-by-file inventory).
   * `arch/00-glossary.rst` (term definitions).
   * `grep -r 'concept-keyword' src/main/kotlin/`.

---

## 13. Splunk pivot cross-JVM

**Read order:**
1. [`03-request-context-and-mdc.rst`](architecture/cross-cutting/03-request-context-and-mdc.rst).
2. [`mod/platform/logging.rst`](modules/platform/logging.rst).

**SPL query:**
```spl
index=micros service=proactive-ai-platform request_id="<your-id>"
| sort _time
| table _time, MICROS_GROUP, message, account_id, tenant_id
```

**Why it works cross-JVM:** ADR-003 — context is replayed from SQS message attributes onto the worker JVM by `MessageQueueConsumerMiddleware`. So the same `request_id` appears on both the WebServer log line that submitted the task and on the LongRun log line that processed it.

---

## 14. Author a new ADR

**Read order:**
1. [`14-architectural-decisions.rst`](architecture/cross-cutting/14-architectural-decisions.rst) — schema + 13 examples.

**Steps:**
1. Pick the next `ADR-NNN` (zero-padded; never re-use).
2. Use the schema (Status, Date, Context, Decision, Alternatives, Consequences, Source, Confidence).
3. **Always** list rejected alternatives — that is what makes the ADR valuable later.
4. Cite the implementing PR/commit/file.
5. If your decision **supersedes** an existing ADR, mark the old one and link in both directions.

**Acceptance:** any future engineer can read your ADR alone and reconstruct your reasoning; rejected alternatives explain why your decision was non-obvious.

---

## 15. Compute velocity analytics

**Read order:**
1. [`15-velocity-and-debt.rst`](architecture/cross-cutting/15-velocity-and-debt.rst) Part 12 — reproducibility script.

**Run:**
```bash
cd atlassian_packages/proactive-ai-platform
git log --oneline | wc -l
git log --pretty=format:'%an' | sort | uniq -c | sort -rn
git log --grep='AIX-' --oneline | grep -oE 'AIX-[0-9]+' | sort -u | wc -l
```

**Acceptance:** every cell in chapter 15 re-derivable; if your number disagrees, the source is authoritative — update the chapter.

---

## 16. Onboarding (1-day plan)

**Hour 0–1:** [`README.md`](README.md) → [`ov/02-architectural-narrative.rst`](overviews/02-architectural-narrative.rst) (walking tour).

**Hour 1–2:** [`arch/01-architecture-overview.rst`](architecture/01-architecture-overview.rst) + [`arch/02-request-lifecycle.rst`](architecture/02-request-lifecycle.rst).

**Hour 2–3:** [`cc/01-business-and-technical-goals.rst`](architecture/cross-cutting/01-business-and-technical-goals.rst) + [`cc/10-vision-and-strategy.rst`](architecture/cross-cutting/10-vision-and-strategy.rst).

**Hour 3–5:** Three platform layers most relevant to your first PR (use [`SYMBOL_INDEX.md`](SYMBOL_INDEX.md) to find them).

**Hour 5–6:** [`cc/14-architectural-decisions.rst`](architecture/cross-cutting/14-architectural-decisions.rst) — read all 13 ADRs.

**Hour 6–7:** [`cc/02-development-history.rst`](architecture/cross-cutting/02-development-history.rst) — narrative; skim [`cc/13-full-history-catalog.rst`](architecture/cross-cutting/13-full-history-catalog.rst) for the strategic-PR list.

**Hour 7–8:** Local-dev setup per the in-repo `LOCAL_DEV.md`; run the canary `/greeting` endpoint locally.

---

## 17. Onboard AI agent (5-minute plan)

**Load these files in this order:**
1. [`AGENTS.md`](AGENTS.md) — problem-routing tables.
2. [`MANIFEST.json`](MANIFEST.json) — chapter manifest (`jq` it for filters).
3. The primary chapter for the user's specific problem (per `AGENTS.md` §1).
4. As needed: [`SYMBOL_INDEX.md`](SYMBOL_INDEX.md), [`TOPIC_INDEX.md`](TOPIC_INDEX.md), or this file.

If `AGENTS.md` §4 lists the user's problem under "Known gaps", **stop searching** the docs — write new docs as part of the PR.

---

## 18. Plan an OKR-moving PR

**Read order:**
1. [`12-optimization-playbook.rst`](architecture/cross-cutting/12-optimization-playbook.rst) Part 1 (OKR levers) + Part 8 (PR-authoring checklist).
2. [`01-business-and-technical-goals.rst`](architecture/cross-cutting/01-business-and-technical-goals.rst).

**PR description checklist (verbatim from Playbook §8 of `12-optimization-playbook`):**
1. Name the metric in the title.
2. Quote the baseline (signalfx-cli or screenshot).
3. Quote the expected delta with rationale tied to a specific lever.
4. List the counter-metric you watched.
5. Link the alarm that would catch a regression. If no alarm exists for what you're changing, **first PR is the alarm**, second PR is the change.

**Acceptance:** PR review can verify metric impact without running the change first.

---

## 19. De-risk RISK-001 (single-contributor concentration)

**Read order:**
1. [`14-architectural-decisions.rst`](architecture/cross-cutting/14-architectural-decisions.rst) RISK-001.
2. [`15-velocity-and-debt.rst`](architecture/cross-cutting/15-velocity-and-debt.rst) Part 2.
3. [`13-full-history-catalog.rst`](architecture/cross-cutting/13-full-history-catalog.rst) Part 8 — the four critical paths and their single owners.

**Concrete actions:**
1. Add "≥ 2 unique authors per critical-path PR" as a tracked KPI in the team's planning rhythm.
2. Pair-program the next material change to `feature/rovoinsights/` or `stratus/`.
3. Cross-train on `AsyncTaskService` / `AsyncTaskDispatcher` (use [`mod/platform/task.rst`](modules/platform/task.rst) as on-ramp).
4. Cross-train on Stratus / MCP integration (use [`mod/platform/stratus.rst`](modules/platform/stratus.rst) + ADR-005).

**Acceptance:** quarterly contributor-distribution check shows reduction in single-author share of human commits.

---

## 20. Decide doc vs. gap

**Procedure:**
1. Search [`AGENTS.md`](AGENTS.md) §1 (problem table) and §4 (known gaps).
2. Search [`TOPIC_INDEX.md`](TOPIC_INDEX.md) for the keyword.
3. Search [`SYMBOL_INDEX.md`](SYMBOL_INDEX.md) for any class/file you have.
4. If not in any of the above → **it's a gap**.
5. **Add** it to `AGENTS.md` §4 and to the gap list at the bottom of `TOPIC_INDEX.md`, **even if you don't write the content yet**. This prevents future agents from re-searching the same dead end.

**Acceptance:** every search either finds the answer or explicitly records "no answer here, look elsewhere".

---

## How to add a new playbook

When you find yourself walking another engineer through a recurring task, add it here:

1. Pick the next number in the index above.
2. Use the same **Read-order / Steps / Acceptance** structure.
3. **Cite chapters and the section/part within them** — not just the file. Agents that load a 600-line chapter to find one paragraph cost more than agents that load one paragraph.
4. Add a row to [`AGENTS.md`](AGENTS.md) §1 if your playbook covers a frequent agent-asked problem.
