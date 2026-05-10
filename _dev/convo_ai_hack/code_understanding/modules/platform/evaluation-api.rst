.. _mod-evaluation-api:

==============================================
``platform/evaluation/evaluation-api``
==============================================

:Tier: platform
:Path: ``modules/platform/evaluation/evaluation-api``
:Size: ~2,764 source lines :sup:`(verified)`
:Importance: Tier 2 — primary evaluation contract

Contracts for **agent quality evaluation**: batch jobs, datasets, LLM-as-judge runs. Backs AgentStudio's batch-evaluation feature.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - File
     - Lines
     - Concept
   * - ``BatchEvaluationJobService.kt``
     - 183
     - Job CRUD + lifecycle
   * - ``BatchEvaluationDatasetService.kt``
     - 155
     - Dataset management
   * - ``LLMJudgeService.kt``
     - 151
     - LLM-as-judge orchestration
   * - ``BatchEvaluationJobRunStore.kt``
     - 126
     - Run-level persistence

Key public contracts
======================

* ``interface BatchEvaluationJobService`` — create/list/read/delete jobs
* ``interface BatchEvaluationDatasetService`` — manage evaluation datasets
* ``interface BatchEvaluationExecutionService`` — execute a job
* ``interface BatchJudgementExecutionService`` — execute the judging step
* ``interface LLMJudgePromptProviderFactory`` — produce prompts for judge LLM
* ``interface EvaluationContextFactory`` — build per-eval context
* ``interface RovoEvaluationContextFactory : EvaluationContextFactory`` — Rovo variant
* ``interface CsmEvaluationContextFactory : EvaluationContextFactory`` — CSM variant
* ``interface EvaluationContextFactoryProvider`` — pluggable factory selection
* ``interface ProductTypeAware`` — branch eval logic by product

Notable findings
==================

* **Product-aware context factories live in platform** — Rovo and CSM each have their own ``EvaluationContextFactory`` subclass. A Jira variant would presumably follow. Worth checking whether this leakage indicates a need for a generic mechanism.
* The ``ProductTypeAware`` interface formalizes the branching pattern.

