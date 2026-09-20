.. _mod-evaluation-impl:

==============================================
``platform/evaluation/evaluation-impl``  ⚠ god-module
==============================================

:Tier: platform
:Path: ``modules/platform/evaluation/evaluation-impl``
:Size: **~26,625 source lines** :sup:`(verified)` — *largest module in the codebase*
:Importance: Tier 1 — central impl, but at high refactor risk

Concrete batch evaluation runtime. Job lifecycle handlers, dataset operations, judging execution, deletion — all in one module.

Why so large?
==============

Evaluation is genuinely complex:

1. **Job state machine** — jobs transition through created → queued → running → judged → completed / failed states; each transition has a lifecycle handler.
2. **Async execution** — jobs run on background SQS workers (``BatchEvaluationTaskHandler`` with 60-min timeout).
3. **Two-phase execution** — execute the agent (one phase) then run the judge (separate phase, separate handler).
4. **Deletion is not free** — datasets, runs, metric snapshots all need cascade-cleanup; a separate ``BatchEvaluationDeleteTaskHandler`` does the work asynchronously.

Key Spring components :sup:`(verified)`
=========================================

Job orchestration:

* ``class BatchEvaluationLifecycleHandler``
* ``class BatchEvaluationDeleteLifecycleHandler``
* ``class BatchEvaluationTaskHandler``  (60-min timeout — SQS LongRun queue)
* ``class BatchEvaluationDeleteTaskHandler``

Domain services:

* ``class BatchEvaluationDatasetServiceImpl``
* ``class BatchEvaluationProjectServiceImpl``
* ``class BatchEvaluationJobDeletionServiceImpl``
* ``class BatchJudgementExecutionServiceImpl``
* ``class BatchEvaluationExecutionServiceImpl``

Config:

* ``class EvaluationConfig``

Notable findings
==================

* **God-module candidate.** 26K LoC in one module is the highest in the codebase. Splitting along the natural seams (lifecycle handlers / domain services / dataset / config) is plausible but would touch many imports.
* **Two parallel handler families** — one for job execution, one for deletion. Deletion runs in its own SQS queue with its own task type; not folded into the main job lifecycle.
* **60-minute task timeout** is the longest in the codebase (most other tasks are ≤5 min). Reflects that batch eval jobs can run for hours.

What you would change here
===========================

* **Add a new judge type** → register in ``BatchJudgementExecutionServiceImpl``
* **Add a new metric** → emit from the judging path; record in the run store
* **Add a new dataset source** → extend ``BatchEvaluationDatasetServiceImpl``

What you would NOT change here
===============================

* Per-product context (lives in product-specific ``EvaluationContextFactory`` subclasses, but those are still in evaluation-api — see notable findings)
* The judge LLM call itself (lives in ``platform/service/service-impl`` ``AIGatewayClientServiceImpl``)

