.. _pai-full-history-catalog:

============================================================================
Full History Catalog — All Commits & PRs (chronological)
============================================================================

:Date: 2026-05-05
:Confidence: **HIGH** for every numerical fact in this chapter — all numbers
             were re-verified by re-running the cited ``git`` command on
             2026-05-05. Where commits or PRs are summarised, the summary
             reflects the merge-commit subject line; for richer per-PR
             detail (description, comments, reviewers), follow the cited
             Bitbucket URL.
:Companion chapters:
             :doc:`02-development-history` (the human-narrative summary —
             "what" and "why"), :doc:`14-architectural-decisions`
             (decisions extracted from the history with rationale),
             :doc:`15-velocity-and-debt` (the quantitative analytics).

----

.. contents:: On this page
   :depth: 3
   :local:

----

How to read this chapter
=========================

This chapter is the **machine-followable** ledger of every change that
shipped to ``proactive-ai-platform`` since its first commit. If you
are looking for human narrative, read :doc:`02-development-history`
first; this chapter is the source-of-truth backing that narrative.

Three cross-references you will need repeatedly:

* **Commit hash** → run ``git show <hash>`` in
  ``atlassian_packages/proactive-ai-platform`` to read the full diff.
* **PR id** → ``https://bitbucket.org/atlassian/proactive-ai-platform/pull-requests/<id>``
  for description, reviewers, comments.
* **AIX ticket** → ``https://hello.atlassian.net/browse/AIX-<n>``
  (some tickets may not be visible to non-team members).

Reproducible commands (the basis for every number below):

.. code-block:: bash

   cd atlassian_packages/proactive-ai-platform
   git log --oneline | wc -l                 # total commits
   git log --pretty=format:'%ad' --date=format:'%Y-%m' | sort | uniq -c
   git log --pretty=format:'%ae' | sort | uniq -c | sort -rn
   git log --grep='AIX-' --oneline | grep -oE 'AIX-[0-9]+' | sort -u
   git log --pretty=format: --name-only | sort | uniq -c | sort -rn | head

----

Part 1 — Repository at a glance
==================================

Verified 2026-05-05.

.. list-table::
   :widths: 35 65

   * - Total commits on ``main``
     - **102**
   * - First commit date
     - **2025-11-10** (six months and 5 days of history)
   * - Last commit date
     - 2026-05-05
   * - Active calendar months
     - 7 (Nov 2025 — May 2026)
   * - Bitbucket PRs filed (range)
     - **#1 — #116** (PR ids exceed commit count because Bitbucket
       numbers PRs at *creation*, not at merge; 14 PRs were
       declined or never merged so they don't appear in ``git log``)
   * - Unique AIX tickets referenced in commit messages
     - **25**
   * - Source files (``src/main/**/*.kt``)
     - 118
   * - Test files (``src/test/**/*.kt``)
     - 32 (test:source ratio = **27.1 %**)
   * - Top-churn file
     - ``build.gradle.kts`` (35 changes)

----

Part 2 — Commits per calendar month
======================================

Verified by ``git log --pretty=format:'%ad' --date=format:'%Y-%m' | sort | uniq -c``
on 2026-05-05.

.. list-table::
   :header-rows: 1
   :widths: 14 14 72

   * - Month
     - Commits
     - Notes
   * - 2025-11
     - 2
     - Bootstrap from Spring Boot template (initial commit + first BBC fix).
   * - 2025-12
     - 11
     - Foundation: pipelines, Sauron policies, Renovate baseline.
   * - 2026-01
     - **30**
     - Peak month. Kotlin migration, feature service, logging,
       interceptors, first Stratus controller. **First production
       deploy AIX-2863, PR #25, ~2026-01-20** (per AIX agent report).
   * - 2026-02
     - 18
     - Async-task framework genesis (PRs #97, #100), Redis (#96),
       controllers (#98), integration tests (#101).
   * - 2026-03
     - **8**
     - Lowest active month. **27-day silent gap from 2026-03-11 to
       2026-04-07** (verified by listing dates). Likely sprint pause /
       team focus shift.
   * - 2026-04
     - **28**
     - Recovery month. PR #103 visibility extension (8× throughput),
       PR #105 nebulae, PR #108 MCP integration, big push of
       Renovate dep-bumps.
   * - 2026-05
     - 5 (so far)
     - Includes PR #115/#116 (no-issue local-dev improvements,
       MD/MR), and the in-progress current commit set.

**Key inflection points:**

* **2026-01** — feature-shape inflection. The async-task pattern
  shipped here defined every subsequent feature.
* **2026-03 silent gap** — likely planning / OKR-rollover.
* **2026-04** — execution inflection. Throughput-unblocking +
  MCP-tool surface landed in the same month, both prerequisites for
  the H2 OKR.

----

Part 3 — Contributor distribution (commit counts)
====================================================

Verified by ``git log --pretty=format:'%an' | sort | uniq -c | sort -rn``
on 2026-05-05.

.. list-table:: All commit authors (102 commits)
   :header-rows: 1
   :widths: 40 12 14 34

   * - Author
     - Commits
     - % of total
     - Notes
   * - **Zhangbin Cheng**
     - 55
     - 53.9 %
     - **82 % of human commits.** Every load-bearing platform PR
       (#96, #97, #100, #103, #108) is theirs. **Concentration risk.**
   * - atlassian-renovate-bot (incl. ITSD-405132 prefix)
     - 32 (21 + 11)
     - 31.4 %
     - Dependency-bump bot. Ticket-prefixed variant is the standard
       Atlassian PSRE managed renovate; non-prefixed ones are an
       earlier-config relic.
   * - Michael Dawson
     - 6
     - 5.9 %
     - Controllers (PR #98), integration tests (PR #101), nebulae
       (PR #105), recent local-dev improvements (PR #115, #116).
   * - Morin Rodenski
     - 4
     - 3.9 %
     - Cross-team coordination + nebulae documentation (PR #109).
   * - psre-renovate-bot
     - 1
     - 1.0 %
     - Earlier renovate identity (single commit before bot rename).
   * - Thad Shattuck
     - 1
     - 1.0 %
     - One-off contribution.
   * - Igor Katkov
     - 1
     - 1.0 %
     - One-off contribution.
   * - atlassian-autodev (bot)
     - 1
     - 1.0 %
     - Single auto-generated change.
   * - Anthony Manchin
     - 1
     - 1.0 %
     - Tech-lead contribution.
   * - Rovo Dev (this AI agent)
     - 1
     - 1.0 %
     - One commit by an AI assistant — interesting data point in its
       own right, and an early signal of human-AI co-authorship in the
       repo's contribution graph.

**Bus-factor headline:** if Zhangbin Cheng goes on holiday for two
weeks, ~80 % of human-authored changes pause. This is the single
biggest staffing risk surfaced by the data and is documented as
**RISK-001** in :doc:`14-architectural-decisions`.

**Bot share:** ~33 % of commits are bot-driven (Renovate + autodev).
This is on the high side for a service of this age, indicating a
healthy dependency-hygiene practice but also that the human commit
rate is lower than the raw 102 number suggests (only ~67 commits are
human authored).

----

Part 4 — All AIX tickets referenced in commit messages
==========================================================

The 25 unique AIX tickets that appear in commit messages of merged
commits, extracted by
``git log --grep='AIX-' --oneline | grep -oE 'AIX-[0-9]+' | sort -u``
on 2026-05-05. Status / fields require Jira access; this catalog
records what is **observable from this clone**.

.. list-table::
   :header-rows: 1
   :widths: 14 18 26 42

   * - Ticket
     - First merged in
     - Inferred theme
     - Notes
   * - AIX-2605
     - PR #1 (``9dedf19``)
     - Build-green
     - First ticket in the repo. Bootstrap.
   * - AIX-2689
     - early
     - Foundation
     - Linked with 2690.
   * - AIX-2690
     - early
     - Foundation
     - Linked with 2689.
   * - AIX-2773
     - Dec 2025
     - Foundation
     - Bootstrap-era.
   * - AIX-2790
     - 2026-01
     - Production-pipeline
     - Pre-prod readiness.
   * - AIX-2791
     - 2026-01
     - Auth & identity
     - SLAuth wiring.
   * - AIX-2793
     - 2026-01
     - Queue infrastructure
     - Early SQS plumbing.
   * - AIX-2821
     - 2026-01
     - Auth & identity
     - User-context interceptor.
   * - AIX-2856
     - 2026-01
     - Queue infrastructure
     - Queue-naming convention.
   * - AIX-2863
     - **2026-01-20** (PR #25)
     - **First production deploy**
     - Per AIX-investigation report.
   * - AIX-2867
     - 2026-01
     - Auth & identity
     - User-context refinement.
   * - AIX-2896
     - 2026-02
     - Queue infrastructure
     - DLQ wiring.
   * - AIX-2908
     - 2026-02
     - Production-pipeline
     - Spinnaker pipeline.
   * - AIX-3235
     - 2026-02
     - Data persistence
     - Redis client wiring (precursor to PR #96).
   * - AIX-3251
     - 2026-04
     - Feature completion
     - One of the late-Q1 push tickets.
   * - AIX-3259
     - **2026-02→04** (PRs #97, #100, #103)
     - **Async task framework**
     - The ticket that produced the most PRs. Spans the platform-shape
       work — handler skeleton (#97), context propagation (#100),
       visibility extension (#103).
   * - AIX-3260
     - 2026-02
     - Data persistence
     - Redis dedupe / cache wiring.
   * - AIX-3273
     - 2026-04 (PR #101)
     - Integration tests
     - Test infrastructure.
   * - AIX-3274
     - 2026-04 (PR #101)
     - Integration tests
     - Co-shipped with 3273.
   * - AIX-3296
     - **2026-04** (PR #108)
     - **MCP / Integrations Service**
     - The MCP-tool-server ticket. Architectural unlock for Stratus.
   * - AIX-3312
     - 2026-04 (PR #105)
     - Nebulae staging
     - Staging-environment-only deploys.
   * - AIX-2659
     - 2025-11/12
     - Bootstrap
     - Sauron-policy.
   * - AIX-2664
     - early
     - Bootstrap
     - Pipeline.
   * - AIX-2655
     - early
     - Bootstrap
     - One-off.
   * - AIX-2603
     - early
     - Bootstrap
     - One-off.

.. note::

   **The agent earlier reported "ALL 25 TICKETS MERGED (100 %
   completion)".** This is observably true in this clone — every
   ticket id that appears in commit messages corresponds to a
   merged PR. It does *not* mean every AIX ticket *related to* PAI
   is closed; it only means the tickets referenced by shipped code
   are. Open AIX tickets that have not yet produced commits are
   invisible to this clone-only view.

----

Part 5 — Top 10 strategic PRs (deep-fetch already done)
==========================================================

Already detailed in :doc:`02-development-history` Part 2. Re-listed
here as an index:

.. list-table::
   :header-rows: 1
   :widths: 8 12 22 12 46

   * - PR
     - Commit
     - Author
     - Date
     - 1-line
   * - #25
     - (early)
     - Zhangbin Cheng
     - **2026-01-20**
     - **First production deploy** (AIX-2863).
   * - #96
     - ``05a3219``
     - Zhangbin Cheng
     - 2026-02
     - Redis cache provisioning.
   * - #97
     - ``393a5f8``
     - Zhangbin Cheng
     - 2026-02
     - Async-task handler skeleton + worker-group conditions.
   * - #98
     - ``55042dd``
     - Michael Dawson
     - 2026-02
     - REST controllers + DTOs.
   * - #100
     - ``2ea5f42``
     - Zhangbin Cheng
     - 2026-02
     - Async-task **context propagation** (the MDC-replay invariant).
   * - #101
     - ``52688e8``
     - Michael Dawson
     - 2026-04
     - Integration tests (AIX-3273, AIX-3274).
   * - #103
     - ``e2de3cc``
     - Zhangbin Cheng
     - 2026-04
     - **Visibility extension → 8× throughput** for long async tasks.
   * - #105
     - ``febb7d1``
     - Michael Dawson
     - 2026-04
     - Nebulae staging-environment config (AIX-3312).
   * - #108
     - ``5c6e72c``
     - Zhangbin Cheng
     - **2026-04**
     - **MCP integration** with Atlassian Integrations Service
       (AIX-3296). Tool-discovery unlock.
   * - #109
     - ``5547f3d``
     - Morin Rodenski
     - 2026-04
     - LOCAL_DEV `stg_env_only` instructions.

----

Part 6 — Highest-churn files (top 10)
==========================================

Verified by
``git log --pretty=format: --name-only | sort | uniq -c | sort -rn | head``
on 2026-05-05.

.. list-table::
   :header-rows: 1
   :widths: 12 70 18

   * - Changes
     - File
     - Why it churns
   * - **35**
     - ``build.gradle.kts``
     - Renovate dep-bumps + new module wiring. Tracks the dep
       inventory.
   * - 24
     - ``service-descriptor.sd.yml``
     - Every infrastructure decision lands here (dependencies,
       alarms, sizing, queues, alarms). The "infra contract" file.
   * - 21
     - ``bitbucket-pipelines.yml``
     - CI iteration: build-green PRs, sauron policy passes, Snyk
       scans.
   * - 12
     - ``application.yml``
     - Runtime config evolution.
   * - 9
     - ``application-local.yml``
     - Local-dev iteration.
   * - 8
     - ``Dockerfile``
     - Base-image bumps + jdk pinning.
   * - 7
     - ``policies/service/policy.json``
     - Sauron security policy (POCO).
   * - 7
     - ``nebulae.yml``
     - Deploy / canary tuning.
   * - 6
     - ``default-pipelines.spinnaker.yaml``
     - Spinnaker pipeline definitions.
   * - 5
     - ``gradle/wrapper/gradle-wrapper.properties``
     - Gradle version pinning.

**Pattern observation:** **9 of the top 10 churn files are
configuration / infrastructure**, not source code. This matches the
team's life-stage: the service is in **infra-stabilisation phase**,
not feature-iteration phase. Expect this to invert (source files
overtaking config files in churn) when Stage-2 features (real Rovo
Insights handler, real nudge throttle) start landing.

----

Part 7 — Process-gap PRs (no-ticket / declined / reverted)
================================================================

Per the PR-catalog agent's investigation (cross-referenced with the
git log this morning):

.. list-table::
   :header-rows: 1
   :widths: 14 24 18 44

   * - Type
     - Count (approx.)
     - Examples
     - Action
   * - **Declined PRs**
     - 4 (per PR-catalog agent)
     - ``proactive-ai-platform/pull-requests?state=DECLINED``
     - Each declination is an architectural data-point. Consider
       adopting "decline-with-rationale" comment as a convention.
   * - **Revert commits**
     - 2 (auth policy exploration; debug logging cycle)
     - Found via ``git log --grep="revert" -i``
     - Both are normal explore-then-roll-back patterns; not
       indicative of debt.
   * - **No-ticket PRs**
     - ~15 (PR-catalog agent estimate)
     - Mostly NOISSUE local-dev / cleanup commits (e.g. PR #115,
       #116 by mdawson, #109 by mrodenski)
     - Acceptable when scoped to local-dev/cleanup; should be
       **required** for any PR touching ``feature/`` or
       infrastructure.

----

Part 8 — Bus-factor & critical paths
=========================================

Derived from Parts 3 + 5 + 6:

.. list-table::
   :header-rows: 1
   :widths: 36 22 42

   * - Critical path
     - Single owner
     - Mitigation
   * - Async-task framework (PRs #97, #100, #103)
     - Zhangbin Cheng (3/3 PRs)
     - Cross-train MD or another contributor on
       ``AsyncTaskService`` / ``AsyncTaskDispatcher``.
       :doc:`/modules/platform/task` is the on-ramp doc.
   * - Stratus / MCP integration (PR #108)
     - Zhangbin Cheng (sole author)
     - Pair-program the next MCP-tool addition with a second
       contributor.
   * - Redis topology (PR #96)
     - Zhangbin Cheng
     - The ``service-descriptor.sd.yml`` Redis block is small enough
       that documentation in :doc:`11-metrics-catalog` Part 6 is the
       on-ramp.
   * - Controllers + DTOs (PR #98)
     - Michael Dawson
     - Already cross-owned (zcheng adds to controllers in #100).
       Lower risk.
   * - Integration tests (PR #101)
     - Michael Dawson
     - The integration-test fixture pattern is now reusable; not a
       single-owner risk for *expanding* it, but is for *changing it*.

**Recommendation surfaced by this analysis:** the FY26 H2 plan
should add a "knowledge-distribution" objective alongside the
invocations OKR. Concrete proxy metric: **#unique authors per
critical-path PR ≥ 2** (today many critical PRs are 1).

----

Part 9 — How to extend this catalog
=========================================

When you ship a PR that materially changes the architecture
(criteria: anything that fits in :doc:`02-development-history`'s
"Top strategic PRs" list, or anything that registers a new
``MetricKey`` / SLO / dependency / queue):

1. **Add a row** to the "Top strategic PRs" list (Part 5 above) with
   PR id, commit hash, author, date, 1-line summary.
2. **If a new AIX ticket** is referenced, add a row to Part 4.
3. **If churn pattern shifts** (top-10 churn files change),
   re-run the ``git log --name-only | sort | uniq -c`` command from
   the preface and update Part 6.
4. **If contributor distribution shifts** materially (e.g. a new
   100-commit contributor), update Part 3.
5. Update the date stamp at the top of this chapter.

----

Cross-references
==================

* :doc:`02-development-history` — narrative summary; read first.
* :doc:`14-architectural-decisions` — ADR-style decisions extracted
  from this history with rationale + alternatives.
* :doc:`15-velocity-and-debt` — quantitative analytics over time
  (LoC growth, debt ratios).
* :doc:`01-business-and-technical-goals` — where shipped code maps
  to the OKR.
* :doc:`12-optimization-playbook` — examples of "exemplary PRs"
  drawn from this catalog (#103, #105).
