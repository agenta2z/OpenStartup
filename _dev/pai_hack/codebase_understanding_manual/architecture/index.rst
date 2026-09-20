.. _pai-architecture:

==============
Architecture
==============

.. toctree::
   :maxdepth: 2

   00-glossary
   01-architecture-overview
   02-request-lifecycle
   03-module-catalog

.. toctree::
   :maxdepth: 2
   :caption: Cross-cutting chapters

   cross-cutting/index

Architecture documents
=======================

**00-glossary.rst** — Defines PAI-specific terminology: Stratus (AI Gateway), MCP (Model Context Protocol), SHWorkers (short-lived task workers), LongRun (persistent workers), Envelope (async task wrapper), Context (request context with tenant/user metadata).

**01-architecture-overview.rst** — System boundary: Spring Boot 7.10 entry points, how requests flow to feature packages (rovoinsights, nudge, greeting), where SQS fits, what external systems we call (IdGatekeeper, Statsig, SignalFx, StreamHub).

**02-request-lifecycle.rst** — Sync + async lifecycles: How a request initializes MDC / RequestContext, routes to a feature package, optionally queues an Envelope to SQS, and how worker groups consume downstream. Request-scoped vs. worker-scoped context.

**03-module-catalog.rst** — File-level catalog: every ``.kt`` file listed with its purpose, exported API, and where it fits in the dependency graph.

**cross-cutting/** — Deep dives into orthogonal concerns:

* **01-business-and-technical-goals.rst** — FY26 H2 OKR: scale from 400K to 1.5M monthly AI invocations; reduce latency, improve feature parity
* **02-development-history.rst** — Strategic PRs #96–#108 chronologically: which features shipped when, what was refactored, why
* **03-request-context-and-mdc.rst** — How RequestContext propagates across sync + async boundaries, MDC integration, Kotlin coroutine context
* **04-feature-flags.rst** — Statsig integration: how flags control feature availability, canary rollouts, A/B testing
* **05-observability-and-metrics.rst** — Micrometer + SignalFx: what metrics we emit, how to debug latency, SLO definitions
* **06-async-tasks-and-sqs.rst** — Envelope lifecycle: task creation, SQS queuing, worker consumption, error handling, DLQ strategy
* **07-ai-gateway-and-stratus.rst** — AI Gateway / Stratus integration: how we call LLMs, token budgets, fallback strategies, latency budgets
* **08-auth-and-tenant.rst** — IdGatekeeper integration, tenant isolation, user context propagation
* **09-deployment-and-config.rst** — Spring Boot config, environment-specific settings, deployment topology (Micros + worker groups)
