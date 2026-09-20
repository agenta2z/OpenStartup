.. _mod-evaluation-impl-corrected:

==================================================================
``platform/evaluation/evaluation-impl`` — batch eval runtime
==================================================================

:Tier: platform
:Path: ``modules/platform/evaluation/evaluation-impl``
:Size: **7,390 main LoC** :sup:`(verified 2026-05-02 — earlier 26,625 figure was incorrect)`
:Files: ~30 main
:Importance: ⭐⭐⭐ Tier 2 — batch evaluation runtime

.. note::
   The catalog page previously showed 26,625 LoC for this module. Direct verification
   on 2026-05-02 with ``find -P -name '*.kt' -type f -exec cat {} +`` shows **7,390 LoC** —
   significantly smaller. The earlier figure may have included transitive includes.
   This page reflects the verified ground truth.

Top files (verified)
======================

.. list-table::
   :header-rows: 1
   :widths: 60 15 25

   * - File
     - Lines
     - Role
   * - ``service/LLMJudgeServiceImpl.kt``
     - **848**
     - LLM-as-judge orchestration
   * - ``service/BatchEvaluationJobServiceImpl.kt``
     - **826**
     - Job CRUD + lifecycle
   * - ``service/BatchEvaluationExecutionServiceImpl.kt``
     - 632
     - Job execution
   * - ``service/BatchEvaluationDatasetServiceImpl.kt``
     - 632
     - Dataset CRUD
   * - ``service/BatchJudgementExecutionServiceImpl.kt``
     - 536
     - Judging execution
   * - ``store/BatchEvaluationDatasetStoreImpl.kt``
     - 414
     - Dataset persistence
   * - ``store/BatchEvaluationJobRunStoreImpl.kt``
     - 406
     - Run persistence
   * - ``service/BatchEvaluationResultServiceImpl.kt``
     - 285
     - Result service
   * - ``store/ResultMetricStoreImpl.kt``
     - 249
     - Metric persistence

Architectural structure
=========================

Two-layer architecture: **services + stores**.

**Services** (~3,759 LoC):

* ``BatchEvaluationJobServiceImpl`` (826) — job lifecycle (create / queue / run / judge / complete / fail / delete)
* ``BatchEvaluationDatasetServiceImpl`` (632) — dataset CRUD
* ``BatchEvaluationExecutionServiceImpl`` (632) — agent-execution phase
* ``BatchJudgementExecutionServiceImpl`` (536) — judging phase (separate from execution)
* ``LLMJudgeServiceImpl`` (848) — LLM-as-judge prompts + orchestration
* ``BatchEvaluationResultServiceImpl`` (285) — read aggregated results

**Stores** (~1,069 LoC):

* ``BatchEvaluationDatasetStoreImpl`` (414)
* ``BatchEvaluationJobRunStoreImpl`` (406)
* ``ResultMetricStoreImpl`` (249)

Two-phase execution model
===========================

Distinctive design: agent execution + judging are **two separate services with two separate
SQS task handlers**.

1. **Phase 1 — Execute the agent.** ``BatchEvaluationExecutionServiceImpl`` runs the agent
   on each dataset row. Long-running (60-min SQS task timeout — the longest in the codebase).

2. **Phase 2 — Judge the responses.** ``BatchJudgementExecutionServiceImpl`` invokes the
   ``LLMJudgeServiceImpl`` to score each response. Separate task → can re-judge without
   re-running the agent.

This separation lets you:

* Re-judge old runs with a new judge prompt
* Scale execution + judging independently
* Keep judge-LLM costs separate from agent-LLM costs in observability

Critical observations
=======================

1. **Module was over-counted.** Previous catalog showed 26,625 LoC; actual is 7,390. The "god-module" framing was wrong. Real complexity is moderate.

2. **LLM-as-judge is 848 LoC** — the largest single file. Judge prompt construction + variant management is non-trivial.

3. **Two-phase model is sound** — separating execution from judging is a deliberate cost + flexibility win.

