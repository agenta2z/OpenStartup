.. _mod-evaluation-spi:

==============================================
``platform/evaluation/evaluation-spi``
==============================================

:Tier: platform
:Path: ``modules/platform/evaluation/evaluation-spi``
:Size: ~658 source lines :sup:`(verified)`

ERS persistence contracts for evaluation runs and metrics. Substantially larger than the action/knowledge SPIs because evaluation has more first-class entities (jobs, runs, datasets, metric snapshots).

Notable findings
==================

* **Non-trivial SPI** (658 LoC vs 13 for action-spi). Reflects that evaluation has multiple persisted entity types: jobs, runs, datasets, judge results, metric snapshots.
* All persistence routed through ERS; no direct Postgres / Redis access.

