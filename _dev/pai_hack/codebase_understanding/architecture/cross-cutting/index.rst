.. _cross-cutting-index:

==============================
Cross-Cutting Concerns
==============================

This section documents the cross-cutting architectural concerns that span
multiple modules in the Proactive AI Service.

.. toctree::
   :maxdepth: 2
   :caption: Cross-Cutting Topics

   01-business-and-technical-goals
   02-development-history
   03-feature-flags-and-gates
   04-observability-and-metrics
   05-authentication-and-security
   06-error-handling-and-resilience
   07-deployment-topology
   08-data-storage
   09-testing-sop

Overview
========

Cross-cutting concerns in the Proactive AI Service include:

* **Business & Technical Goals** — strategic objectives, OKRs, and metrics
  driving the proactive-ai-platform.
* **Development History** — PR timeline, past decisions, and evolution of the
  codebase.
* **Feature Flags & Gates** — Switcheroo/Statsig integration, evaluation
  context, flag tracking for analytics.
* **Observability & Metrics** — Micrometer-based metric emission, custom
  MetricKey entries, LaasLogger hierarchy, and MDC propagation.
* **Authentication & Security** — SLAUTH token validation, POCO policy
  enforcement, and the security filter chain.
* **Error Handling & Resilience** — Exception hierarchy, REST client error
  mapping, retry policies, and DLQ strategies.
* **Deployment Topology** — Worker groups, SQS queue bindings, Docker config,
  and Spinnaker pipelines.
* **Data Storage** — SQS-only persistence model, Redis/Valkey cache, and
  message lifecycle.
* **Testing SOP** — Test patterns, coverage matrix, POCO policy tests, and
  CI integration.
