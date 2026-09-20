.. _pai-modules:

==========================================
Proactive AI Platform — Module Reference
==========================================

This section catalogues every package under
``io.atlassian.micros.proactiveai`` (118 ``.kt`` files / ~7,765 LoC main),
grouped into two top-level sub-catalogues:

* :doc:`features/index` — the three user-facing **feature** packages
  (rovoinsights, nudge, greeting).
* :doc:`platform/index` — the twelve cross-cutting **platform** packages
  (requestcontext, interceptor, stratus, featuregate, logging, service/metric,
  task, sqs, client, context, utility, config).

For supplementary deep-dives that pre-existed this catalogue (kept for
historical reference and additional detail):

* :doc:`rovo-insights/index` — multi-page deep-dive of the Rovo Insights
  pipeline (system types, generation, API).
* :doc:`stratus/index` — extended Stratus / AI Gateway dive
  (ai-gateway, mcp-integration).
* :doc:`nudge/nudge-throttle` — nudge-throttle endpoint contract
  (request/response DTOs, controller, acceptance test).

Top-level catalogues
=====================

.. toctree::
   :maxdepth: 2
   :caption: Module catalogues

   features/index
   platform/index

Supplementary deep-dives
=========================

.. toctree::
   :maxdepth: 2
   :caption: Supplementary deep-dives

   rovo-insights/index
   stratus/index
   nudge/nudge-throttle

How to navigate
================

* If you are **debugging a feature**, start in :doc:`features/index` and
  follow the cross-references into the relevant platform layers.
* If you are **changing a platform layer**, start in :doc:`platform/index`
  and consult the :doc:`../architecture/cross-cutting/index` chapter that
  covers the same concern (e.g., async tasks, request context, metrics).
* If you need **per-file detail** for the largest features, the
  supplementary deep-dives have endpoint-level and DTO-level coverage.
