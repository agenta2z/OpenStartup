.. _rai-business-and-technical-goals:

=============================================================================
Business & Technical Goals, Metrics, and Optimization Priorities
=============================================================================

:Date: 2026-05-04
:Sources: ``PLAN.md``, ``tasks/*.md``, ``agentic-coding-logs/``, ``operations/terraform/``, ``coverage-floors.yml``, Splunk/SignalFx evidence
:Verification: All numbers cross-verified against source files (no estimates).

**Purpose of this document:** If you are optimizing this codebase — for performance,
accuracy, safety, reliability, or developer velocity — this page tells you what to
optimize, by how much, and in what order.

---

.. contents:: Table of Contents
   :depth: 3
   :local:

---

Part 1 — The Five Engineering Objectives
==========================================

The ``PLAN.md`` defines **five named objectives** that every task must serve.
These are the team's current engineering north stars, derived from the archived
``improvement_plan/success-criteria.md`` (16 measurable criteria).

.. list-table::
   :header-rows: 1
   :widths: 5 25 70

   * - ID
     - Name
     - Definition of Done (measurable)
   * - **A**
     - **Trustworthy moderation decisions**
     - • 0 undocumented ``model_construct()`` calls feeding into decisions
       • 100% of fail-open paths emit a dedicated metric tagged with reason
       • Parser primary success rate metric exists; alert fires if rate drops below **95%**
   * - **B**
     - **Accurate self-reported health**
     - • Healthcheck covers ≥ 2 upstream probes (HTTPX + gRPC circuit breaker)
       • Broken upstream → instance unhealthy in **≤ 30 seconds**
   * - **C**
     - **Diagnosable in production**
     - • **100%** of moderation endpoints support ``debug.verbose`` → ``trace`` object
       • Model selection emits a dedicated metric per request
       • Fail-open vs evaluated decisions are distinguishable in metrics
   * - **D**
     - **Safe to evolve**
     - • 1 canonical definition per shared concept (no ``SelectedModel`` duplication)
       • Error handling, retry, fail-open policy each centralised in 1 location
       • Every feature gate has ``# Owner:`` + lifetime metadata
       • 0 unreachable config classes
   * - **E**
     - **Tested at the boundaries**
     - • Per-file branch coverage floors enforced in CI for **12 critical-path modules**
       • ``prompt_moderation.py`` ≥ **40 tests**; ``agent_moderation.py`` ≥ **30**; ``model_text_response_parse.py`` ≥ **20**
       • Parser branch coverage ≥ **90%**

---

Part 2 — Production SLOs (Verified from Terraform + Splunk)
=============================================================

These are **enforceable SLOs** registered in Atlassian's Tome platform via
``responsible-ai/operations/terraform/``. They are production targets, not aspirational.

2.1 Reliability SLOs
---------------------

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Endpoint
     - SLO Target
     - Measurement
   * - **Prompt Moderation**
     - **99.7% reliability**
     - Non-exception outcomes / total outcomes (``flask.micros.prompt_moderation.outcome.count``, outcome ≠ 'exception', prod)
   * - **Image Moderation**
     - **99.5% reliability**
     - Non-exception outcomes / total outcomes (``flask.micros.image_moderation.outcome.count``, prod)
   * - **Agent Moderation**
     - **99.5% reliability**
     - Non-exception outcomes / total (flask.micros.agent_moderation.outcome.count, prod)
   * - **Output Moderation**
     - Not separately registered (beta)
     -

Low traffic threshold for SLO calculation: **40,000 events** (below this, SLO is not computed).

Alert thresholds from ``locals.tf``:

* **Critical error rate**: errors > **5%** of requests (``critical_error_rate_threshold = 95`` = 95% success rate)
* **Standard error rate**: errors > **10%** of requests (``standard_error_rate_threshold = 90``)
* **Short window**: 5 minutes sustained; **long window**: 1 hour sustained

2.2 Latency SLOs
-----------------

All latency SLOs are measured at **P90** with **90% objective** (90th percentile
of requests must complete within threshold on 90% of measurement windows).

.. list-table::
   :header-rows: 1
   :widths: 35 20 20 25

   * - Endpoint / Model
     - P90 Target (ms)
     - Alert threshold (minor/major)
     - Metric
   * - **Prompt Moderation**
     - **1,000 ms**
     - 1,000ms minor (10m) / 1,000ms major (1h)
     - ``flask.micros.prompt_moderation.latency.hist.histogram``
   * - **Agent Moderation**
     - **1,000 ms**
     - 1,000ms minor / 1,000ms major
     - ``flask.micros.agent_moderation.latency.hist.histogram``
   * - **Image Moderation V0** (DEIM)
     - **1,000 ms**
     - 1,000ms minor / 1,000ms major
     - ``flask.micros.image_moderation.latency.hist.histogram``
   * - **Image Moderation V1** (ShieldGemma2)
     - **5,000 ms** *(draft SLO)*
     - 5,000ms minor / 5,000ms major
     - ``flask.micros.image_moderation.latency.hist.histogram``

---

Part 3 — Performance Baselines (Non-Regression Bounds)
=======================================================

From ``agentic-coding-logs/2026-04-20-203000-archived-plan-docs.md`` §6
(verified via PerfHammer load tests and incident analysis).

**Non-regression rule**: any code change that degrades throughput by > **5%** or
increases P95 latency by > **10%** at the same load level requires explicit justification.

3.1 Throughput baselines
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 20 20 25

   * - Scenario
     - ddev
     - stg-east
     - Source
   * - **Saturation throughput** (400 users)
     - **~20 RPS**
     - **~63 RPS**
     - PerfHammer load tests
   * - **Safe concurrent connections**
     - ~100 conns (~37 RPS)
     - —
     - Stress tests
   * - **Stress limit** (0% failures)
     - 200 concurrent (p50 ~4.7s)
     - —
     - Stress tests
   * - **Breaking point**
     - 300+ concurrent (connection failures)
     - —
     - Stress tests
   * - **GPT-OSS 20B on Launchpad** (ml.g6e.xlarge)
     - **~15 RPS per GPU** ceiling
     - —
     - Locust load test (2026-04-21)

3.2 Latency baselines (observed, not SLO targets)
---------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 25 20 20

   * - Metric
     - Value
     - Environment
     - Source
   * - **p95 latency** (production, last hour)
     - **2,152 ms**
     - prod-east
     - Splunk 2026-04-26
   * - **p99 latency** (production, last hour)
     - **3,604 ms**
     - prod-east
     - Splunk 2026-04-26
   * - **avg latency** (production, last hour)
     - **523 ms**
     - prod-east
     - Splunk 2026-04-26
   * - **avg latency** (stg, low load, 5 users)
     - **504 ms**
     - stg-east
     - PerfHammer
   * - **avg latency** (stg, saturation, 400 users)
     - **5,002 ms**
     - stg-east
     - PerfHammer
   * - **gRPC server deadline**
     - 5 seconds
     - all
     - ``triton_grpc_client.py``
   * - **gRPC client timeout** *(not enforced under gevent)*
     - 6 seconds
     - all
     - Incident postmortem
   * - **HTTPX connect timeout**
     - 3 seconds
     - all
     - ``app_context.py``
   * - **HTTPX read timeout** (RAI FT config)
     - 2 seconds
     - all
     - ``app_context.py``
   * - **MSP read timeout**
     - 2 seconds
     - all
     - ``app_context.py``
   * - **Gunicorn worker timeout**
     - 600 seconds
     - all
     - ``gunicorn.conf.py``

3.3 Traffic volume (observed production)
-----------------------------------------

From Splunk/SignalFx evidence (``agentic-coding-logs/2026-04-20-185300-phase-0-evidence.md``
and ``2026-04-24-091700-signalfx-metrics-guide.md``):

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Metric
     - Value
     - Date
   * - **prod-east traffic**
     - ~5,003 req/min avg (~83 RPS)
     - 2026-04-24
   * - **prod-east peak**
     - ~6,376 req/min at 07:02 PDT
     - 2026-04-24
   * - **Global peak**
     - ~6,774 req/min (all envs)
     - 2026-04-24
   * - **Traffic growth** (28-day trend)
     - +243% (1,953 → 6,692 req/min avg)
     - 2026-04-24 vs 4 weeks prior
   * - **Prompt moderation share**
     - **98.9%** of all traffic
     - prod-east, 24h window
   * - **Output moderation share**
     - **~0%** (zero controller logs in 24h)
     - prod-east, 24h window

**Critical implication**: prompt moderation is the single overwhelmingly dominant
endpoint. All optimisation work should be weighted accordingly.

---

Part 4 — Model Accuracy Targets
=================================

4.1 ML model performance benchmarks (offline evaluation)
----------------------------------------------------------

From ``responsible-ai/notebooks/evaluation/results/cat_acc_report.csv``
(per-model category accuracy across the AUP violation evaluation dataset):

.. list-table::
   :header-rows: 1
   :widths: 50 25 25

   * - Model
     - Category Accuracy
     - Notes
   * - **meta.llama-3-8b-instruct-rai-ft** (current prod primary)
     - **76.9%**
     - RAI fine-tuned — production default
   * - gpt-4o-2024-05-13
     - 75.2%
     - Strong baseline
   * - gpt-4-turbo-atlassian-0125
     - 75.4%
     - Strong baseline
   * - anthropic.claude-3-5-sonnet-20240620
     - 74.4%
     - Claude family
   * - anthropic.claude-3-sonnet-20240229
     - 74.1%
     - Claude family
   * - anthropic.claude-3-haiku-20240307
     - 68.6%
     - Fastest Claude
   * - gpt-3-5-turbo-atlassian-0125
     - 69.3%
     - Legacy baseline
   * - meta.llama3-8b-instruct-v1:0 *(untuned)*
     - 61.1%
     - Pre-fine-tune baseline

**Note**: ``assistance-service-plugin-gpt3``, ``llama-guard-7b``, ``openai-moderation-latest/stable``
all show 0.0 in cat_acc — these appear to be legacy/deprecated comparisons with different output formats.

4.2 Harm category coverage (14 evaluated categories)
------------------------------------------------------

From ``policy_category_defns.json`` and evaluation results:

1. Violence/Harassment
2. Hate/Discrimination
3. Misinformation
4. Sexual Content
5. Illegal Activity
6. Self-harm
7. Jailbreak/Prompt Injection
8. Intellectual Property / Copyright
9. Personally Identifiable Information (PII)
10. Politics
11. Profanity
12. Impersonation
13. Specialist Advice
14. High-risk Decisions

**No FPR/FNR targets** are currently published in operational files. This is a
known gap. The evaluation framework tracks FPR/FNR via confusion matrices but
no production enforcement thresholds are defined per category.

4.3 Parser primary success rate target
----------------------------------------

From ``tasks/AI-126-harden-response-parser.md``:

**Target: ≥ 95% primary parse success rate** (JSON parsed on first attempt, no fallback).
Below 95% → alert fires. Current state: **unmeasured** (no metrics on parse paths; AI-126 tracks fixing this).

4.4 Image moderation accuracy
-------------------------------

From ``experiments/image_moderation_v1/`` evaluation:

* V1 (ShieldGemma2) evaluated against LLaVAGuard dataset across 11 harm policy categories
* Optimal threshold determined by ``argmax(F1_scores)`` over 501 threshold values
* ROC-AUC and PR-AUC tracked per model version
* Current production models: V0 (DEIM, threshold 0.4) + V1 (ShieldGemma2, threshold 0.5, feature-flagged)

---

Part 5 — Code Quality & Test Coverage Targets
===============================================

From ``coverage-floors.yml`` (enforced in CI on every PR):

5.1 Global floor
-----------------

**Global branch coverage floor: 79%** (project-wide, measured 81% on 2026-04-20 with ``--cov-branch``).

5.2 Per-file coverage floors (12 critical-path modules)
---------------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 55 15 30

   * - File
     - Floor
     - Notes
   * - ``src/api/v1/moderation/prompt_moderation_controller.py``
     - **100%**
     - Handles **98.9% of prod traffic**. 100% achieved 2026-04-20.
   * - ``src/api/v1/moderation/agent_moderation_controller.py``
     - **100%**
     - 100% achieved 2026-04-20.
   * - ``src/api/v1/moderation/output_moderation_controller.py``
     - **100%**
     - 100% achieved 2026-04-20 (tiny file, 34 statements).
   * - ``src/api/v1/moderation/image_moderation_controller.py``
     - **89%**
     - Full-suite baseline 91% − 2pp drift buffer.
   * - ``src/service/moderation/prompt/prompt_moderation.py``
     - **98%**
     - Full-suite actual 100%; tight floor.
   * - ``src/service/moderation/agent/agent_moderation.py``
     - **88%**
     - Full-suite actual 90% − 2pp.
   * - ``src/service/moderation/output/output_moderation.py``
     - **98%**
     - 100% baseline.
   * - ``src/service/moderation/output/stream_processor.py``
     - **93%**
     - 95% baseline − 2pp.
   * - ``src/service/moderation/model_text_response_parse.py``
     - **74%** → target **≥ 90%**
     - Lowest floor. AI-126 will raise to ≥ 90%.
   * - ``src/inference_models/error_handling.py``
     - **98%**
     - 100% baseline.
   * - ``src/inference_models/rai_llama.py``
     - **74%**
     - Full-suite baseline 76% − 2pp.
   * - ``src/inference_models/rai_gpt_oss.py``
     - **100%**
     - 100% achieved 2026-04-20 (GPT-OSS about to take prod traffic).

5.3 Test count floors
----------------------

From ``PLAN.md`` Objective E:

.. list-table::
   :header-rows: 1
   :widths: 45 20 20 15

   * - Module
     - Current tests
     - Target
     - Status
   * - ``prompt_moderation.py``
     - 24
     - **≥ 40**
     - ❌ gap
   * - ``agent_moderation.py``
     - 18
     - **≥ 30**
     - ❌ gap
   * - ``model_text_response_parse.py``
     - 10
     - **≥ 20**
     - ❌ gap

---

Part 6 — Current Engineering Debt Prioritized by Impact
=========================================================

From ``PLAN.md`` tasks table, cross-referenced with traffic evidence.

.. list-table::
   :header-rows: 1
   :widths: 8 30 15 10 37

   * - Task
     - Title
     - Objectives
     - Priority
     - Impact if unresolved
   * - **AI-127**
     - Unify inference model layer (base class + dedup + decision metrics)
     - A, C, D
     - **P0**
     - Third model (GPT-OSS) in near-term roadmap; adding without base class triples duplication. No metric distinguishes fail-open from evaluated decisions → safety incidents invisible.
   * - **AI-126**
     - Harden response parser (instrumentation + validation + tests)
     - A, C, E
     - **P1**
     - 8 silent fallback paths; 0 metrics; parser branch coverage only 74%. Model output drift is invisible. ``model_construct()`` bypasses Pydantic on decision objects.
   * - **AI-128**
     - Feature gate audit + lifecycle policy
     - D
     - **P1**
     - **46 gates with 0 documented owners or cleanup dates**. Stale gates create invisible dead code and cognitive load. Blocking clean model rollouts.
   * - **AI-114**
     - Debug trace for output moderation
     - C
     - **P1**
     - Output endpoint is the only moderation endpoint without ``debug.verbose`` → ``trace``. Violates Principle #9 (uniform API contracts).
   * - **AI-122**
     - Document stream state constraints
     - D
     - **P2**
     - ``stream_accumulated_content`` in-process dict is an undocumented constraint. No reconnection, no distributed state. Architects may miss this when scaling.
   * - **AI-120**
     - Audit ``model_construct()`` outside the parser
     - A
     - **P2**
     - 8 ``model_construct()`` calls outside the parser; 0 have ``# CONSTRAINT:`` comments. Undocumented validation bypasses on decision objects.

---

Part 7 — Optimization Priority Matrix
=======================================

If you are deciding where to invest engineering effort, use this table.

**Guiding principle**: optimization work should be ordered by (impact on prod traffic) × (current gap from target).

7.1 What to optimize first: ranked list
-----------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 5 30 20 15 30

   * - Rank
     - Optimization target
     - Goal served
     - Effort
     - Why this rank
   * - 1
     - **Prompt moderation parser observability** (AI-126)
     - Accuracy, Safety (A)
     - Medium
     - Affects 98.9% of prod traffic. Silent fallbacks = invisible accuracy degradation. Zero metrics today. Parser drives every ALLOWED/DISALLOWED decision.
   * - 2
     - **Inference model unification + fail-open metrics** (AI-127)
     - Observability (C), Safety (A), Evolvability (D)
     - Large
     - Fail-open events are currently indistinguishable from real decisions in metrics. Can't measure model health without this. GPT-OSS rollout is blocked.
   * - 3
     - **Feature gate cleanup** (AI-128)
     - Evolvability (D)
     - Medium
     - 46 gates with 0 owners creates compounding cognitive debt. Every new model rollout uses feature gates — this must be clean first.
   * - 4
     - **Test coverage for prompt/agent/parser** (AI-126, Objective E)
     - Testing (E)
     - Medium
     - Parser at 74% branch coverage (target 90%). Prompt at 24 tests (target 40). These are the highest-traffic, highest-blast-radius files.
   * - 5
     - **Healthcheck gRPC probe** (Objective B)
     - Reliability (B)
     - Small
     - Broken Teamserve currently never causes healthcheck failure. ALB routes to broken instances. Root cause of the 2026-04-16 incident (22,260 errors in 2 hours).
   * - 6
     - **Throughput scaling** (non-regression enforcement)
     - Performance
     - Large
     - Traffic grew +243% in 4 weeks. Current saturation: 63 RPS (stg). Prod peak: ~113 RPS. No headroom at current scale. **Prerequisite: observability improvements (ranks 1-2) first.**
   * - 7
     - **Model accuracy improvement** (responsible-ai research)
     - ML Accuracy
     - Large
     - Current prod model (LLaMA RAI FT) at 76.9% category accuracy. No FPR/FNR targets defined. **ML team responsibility** — serving infra improvements are prerequisite.
   * - 8
     - **Output moderation debug trace** (AI-114)
     - Observability (C)
     - Small
     - Output moderation has ~0% of prod traffic today. Low urgency, but required for API contract uniformity (Principle #9).

7.2 What NOT to optimize right now
-------------------------------------

Per ``PLAN.md`` §9 (Out of Scope):

* **New harm categories / new content types** — product scope; foundation must be solid first
* **Infrastructure migration** (new regions, Kubernetes changes) — operational scope
* **ML model accuracy improvements** — ML team responsibility; serving infra must be observable first
* **Performance optimization (latency reduction, throughput increase)** — requires observability improvements as prerequisite

---

Part 8 — Monitoring & Alert Inventory
=======================================

8.1 Prometheus metrics currently emitted
------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Metric
     - Tags / What it captures
   * - ``flask.micros.prompt_moderation.outcome.count``
     - ``outcome`` (ALLOWED/DISALLOWED/exception), ``use_case_id``, ``harm_category``, ``model_version``, ``fail_open_type``
   * - ``flask.micros.prompt_moderation.latency.hist.histogram``
     - Full latency histogram per request
   * - ``flask.micros.agent_moderation.outcome.count``
     - Same tag structure as prompt
   * - ``flask.micros.image_moderation.outcome.count``
     - ``outcome``, ``model_evaluation_version`` (v0/v1)
   * - ``flask.micros.image_moderation.latency.hist.histogram``
     - Latency per image moderation request
   * - ``ANTIABUSE_CIRCUIT_BREAKER_STATE``
     - Circuit breaker open/closed for anti-abuse service
   * - ``ANTIABUSE_RESPONSE_STATUS``
     - HTTP status distribution for anti-abuse API calls

8.2 Missing metrics (active engineering debt)
-----------------------------------------------

Per tasks AI-127, AI-126, and the success criteria:

.. list-table::
   :header-rows: 1
   :widths: 40 25 35

   * - Missing metric
     - Task
     - Risk
   * - ``rai.model.selected{model, use_case, version}``
     - AI-127
     - No visibility into which model (LLaMA vs GPT-OSS) handles each request
   * - ``rai.decision.evaluated{outcome, harm_category}``
     - AI-127
     - Can't distinguish real decisions from fail-open
   * - ``rai.decision.fail_open{reason}``
     - AI-127
     - Fail-open events are invisible; safety incidents may go undetected
   * - ``rai.model_response.parse_fallback{level, model_version, outcome}``
     - AI-126
     - Parse quality is unmeasured; format drift is invisible
   * - Output moderation latency histogram
     - AI-114
     - Output moderation is completely dark from a metrics perspective

8.3 SignalFx dashboards (monitored)
-------------------------------------

From ``responsible-ai/operations/terraform/signalfx/dashboards/``:

* Moderation outcome counts (ALLOWED/DISALLOWED ratio over time)
* Latency distribution histogram (success requests only, by token bucket and endpoint)
* Exception rate chart (bad events / total events)
* Harm category distribution heatmap
* Cache performance chart (ETag hit/miss rate)
* Token consumed length distribution
* Token overflow ratio chart
* Non-alphanumeric ratio chart
* GPT-OSS rollout chart (traffic split between model versions)
* Image moderation file format breakdown
* Image size distribution chart

---

Part 9 — 13 Engineering Principles (Quick Reference)
======================================================

From ``PLAN.md`` / ``PRINCIPLES.md``. Every code change must satisfy these.

.. list-table::
   :header-rows: 1
   :widths: 5 35 60

   * - #
     - Principle
     - One-Line Mechanical Test
   * - 1
     - **One Canonical Definition**
     - ``grep -rn "class X" src/`` returns exactly 1 result
   * - 2
     - **No Silent Fallbacks**
     - Every ``except`` that doesn't re-raise has a metric + log
   * - 3
     - **Health Checks Cover All Paths**
     - Every upstream has a probe in ``/healthcheck``
   * - 4
     - **Gates Are Temporary**
     - Every gate in ``Features`` has an ``# Owner:`` comment
   * - 5
     - **Boundary Code Gets Most Tests**
     - Parsers have ≥ N+2 tests for N branches
   * - 6
     - **Make Constraints Explicit**
     - Every ``model_construct()`` has an adjacent ``# CONSTRAINT:`` comment
   * - 7
     - **Centralise Cross-Cutting**
     - Fail-open check appears in exactly 1 location
   * - 8
     - **Observe Before You Change**
     - Metrics exist before behavioural changes land
   * - 9
     - **Uniform API Contracts**
     - All moderation endpoints support the same features (debug trace, error format, headers)
   * - 10
     - **Earn Your Abstractions**
     - Every ABC has ≥ 2 concrete subclasses
   * - 11
     - **Defence in Depth for Safety**
     - No ``model_construct()`` on moderation decision objects
   * - 12
     - **Code Quality Standards**
     - ``./bin/lint`` and ``./bin/unit-test`` pass before commit
   * - 13
     - **Minimal Blast Radius**
     - Refactoring PRs ≠ behavioural change PRs

---

Part 10 — Scorecard: Current vs Target State
=============================================

As of 2026-05-04 (inferred from task statuses and evidence in logs):

.. list-table::
   :header-rows: 1
   :widths: 15 35 25 25

   * - ID
     - Criterion
     - Target
     - Current State
   * - **S1**
     - Fail-open paths emit dedicated metric with reason
     - 100% of fail-open paths metriced
     - **0%** — no dedicated fail-open metric
   * - **S2**
     - Model selection observable per request
     - ``rai.model.selected`` metric exists
     - **Not metriced** — logged only
   * - **S3**
     - Parse fallback is observable
     - ≥ 8 metric calls in parser; alert at < 95% primary success
     - **0 metrics** in parser (AI-126 open)
   * - **R1**
     - gRPC circuit breaker probed in healthcheck
     - ≥ 2 upstream probes
     - **1 probe** (HTTPX only; gRPC blind spot)
   * - **R2**
     - Broken upstream → unhealthy ≤ 30s
     - ≤ 30 seconds
     - **∞** — gRPC failure never triggers unhealthy
   * - **O1**
     - All endpoints support debug.verbose trace
     - 100% (4/4 endpoints)
     - **75%** (3/4 — output missing)
   * - **O2**
     - Model selection metriced
     - Dedicated metric per request
     - **❌ missing**
   * - **O3**
     - Fail-open vs evaluated distinguishable
     - Two distinct metric paths
     - **❌ missing**
   * - **V1**
     - No duplicate infrastructure classes
     - 1 definition per concept
     - **2 definitions** each (SelectedModel, MalformedModelOutput, RAIFTTeamserveEndpoint)
   * - **V2**
     - Error handling centralised
     - ≤ 1 location
     - **3+ locations** (3 fail-open checks in prompt_moderation.py alone)
   * - **V3**
     - Every feature gate has lifecycle metadata
     - 46/46 gates with ``# Owner:``
     - **0/46** gates documented
   * - **V4**
     - No dead config classes
     - 0 unreachable configs
     - **≥ 2 unreachable** (ModerationV1Config, ModerationV1_1Config)
   * - **C1**
     - Test counts for critical modules
     - prompt ≥ 40, agent ≥ 30, parser ≥ 20
     - **24 / 18 / 10** (all below target)
   * - **C2**
     - Parser branch coverage
     - ≥ 90%
     - **74%** (current floor)
   * - **C3**
     - Architectural constraints documented in code
     - 100% of constraints have ``# CONSTRAINT:``
     - **0** documented
   * - **C4**
     - Cross-cutting concerns single canonical implementation
     - 1 per policy
     - Error: **≥ 3 locations**; fail-open: **≥ 3 locations**

**Summary**: 0 of 16 criteria fully met as of plan creation (2026-04-17). As of 2026-05-04:
tasks AI-151, AI-156, AI-161 are done (dashboard + uv migration); AI-127, AI-126, AI-128 remain
the highest-impact open items.
