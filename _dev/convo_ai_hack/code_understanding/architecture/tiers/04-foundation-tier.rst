.. _foundation-tier:

============================
Foundation Tier (11 modules)
============================

The **foundation tier** is the bedrock — infrastructure primitives that everything else depends on. It depends on **nothing** in this codebase except other foundation modules and ``convo-ai-test-utils``.

This isolation is enforced by Gradle (AGENTS.md line 23): try to add a platform/product/service dependency to a foundation module and the build fails.

11 modules :sup:`(verified by directory listing)`
====================================================

::

   adk/core-api               — Agent Development Kit contracts
   adk/core-impl              — ADK runtime
   capabilities/capabilities-api    — Async task / MCP / Aqui contracts
   capabilities/capabilities-spi    — Pluggable capability providers
   capabilities/capabilities-impl   — Concrete capability implementations
   context/context-api        — TenantContext, TenantContextService contracts
   context/context-impl       — AsyncTenantContextService, TcsService impl
   llm-models/llm-models-api  — Unified LLM request/response types
   testing/arch               — ArchUnit architecture tests
   utilities/utilities-api    — 15 sub-packages of cross-cutting primitives
   utilities/utilities-impl   — Filters, interceptors, concrete utility impls

utilities-api breakdown :sup:`(verified by directory listing)`
================================================================

The crown jewel of foundation. 15 sub-packages, each a focused area:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Sub-package
     - Purpose
   * - ``annotation/``
     - Marker annotations (``@ExcludeFromCoverage``, etc.)
   * - ``cache/``
     - Cache abstractions (likely Caffeine wrapper)
   * - ``client/``
     - Generic HTTP client utilities
   * - ``contentretrieval/``
     - Content fetching (URL retrieval, dedup, etc.)
   * - ``context/``
     - Request-scoped context primitives
   * - ``encoding/``
     - Token counting, base64, URL encoding helpers
   * - ``exception/``
     - Standardized exception hierarchy
   * - ``featureflag/``
     - ``RolloutService`` and feature gate evaluation
   * - ``identity/``
     - SLAuth / ASAP / User abstractions
   * - ``logging/``
     - ``MdcLoggingContext``, ``LaasLoggerFactory``, structured logging
   * - ``metrics/``
     - ``PlatformMetricTagsService``, OTel metric registration
   * - ``microsenv/``
     - Micros environment detection (dev/staging/prod)
   * - ``promptformatter/``
     - Prompt template rendering primitives
   * - ``requestcontext/``
     - Request attribute / scope primitives
   * - ``threading/``
     - ``CoroutineContextProvider``, suspend dispatcher utilities

Why this matters
================

The foundation tier is what makes **the rest of the codebase composable**. Every cross-cutting concern has its primitives here:

- **Tenant isolation** → ``foundation/context``
- **Telemetry** → ``foundation/utilities/logging`` + ``utilities/metrics``
- **Feature flags** → ``foundation/utilities/featureflag``
- **Identity** → ``foundation/utilities/identity``
- **Async orchestration** → ``foundation/capabilities`` + ``foundation/utilities/threading``
- **LLM model abstraction** → ``foundation/llm-models``
- **Agent runtime** → ``foundation/adk``

If you understand foundation, you understand 60% of the codebase's day-to-day patterns.

Notable foundation classes
===========================

- ``RolloutService`` (utilities-api/featureflag/) — see :ref:`feature-flags`
- ``MdcLoggingContext`` (utilities-api/logging/) — see :ref:`telemetry`
- ``CoroutineContextProvider`` (utilities-api/threading/) — provides coroutine contexts that include MDC, OTel trace, and request attributes. Per AGENTS.md line 39: "Raw ``Dispatchers.IO`` / ``Dispatchers.Default`` are forbidden."
- ``TenantContext`` (utilities-api/context/) and ``TenantContextService`` (context-api/) — see :ref:`tenant-isolation`
- ``User`` (utilities-api/identity/) — encapsulates invoking user vs agent principal
- ``LaasLoggerFactory`` (utilities-api/logging/) — log factory used by Application.kt
- ``HeaderFilter`` (utilities-impl/interceptors/) — verified existence; resolves headers into request attributes
- ``ExperienceRateLimitFilter`` (utilities-impl/interceptors/) — verified existence; per-experience rate limiting

Patterns specific to foundation
================================

1. **Isolation is sacred.** Foundation must build from a green-field checkout WITHOUT any other module. This means foundation can be released as a library and consumed by other Atlassian projects.

2. **Mockk only.** AGENTS.md line 24: "Foundation tests must use MockK — Mockito, PowerMock, EasyMock, and Spock are forbidden at dependency resolution time."

3. **Coverage tier 80%.** Per AGENTS.md line 53: ``convo-ai-foundation-*-impl`` modules must have ≥80% line coverage (vs 70% for platform-impl, 60% for other -impl). Foundation is held to a higher bar because the blast radius of a foundation bug is universal.

4. **No suspend functions in public utility APIs.** Coroutine integration goes through ``CoroutineContextProvider`` to avoid leaking ``Dispatchers.*`` choices into business code.

5. **Coroutine-aware MDC.** Standard SLF4J MDC is thread-local; Kotlin coroutines suspend across threads. ``MdcLoggingContext`` snapshots and restores MDC across suspension points so structured logging works.

What you would change here
===========================

- **Add a new tenant context field** → modify ``TenantContext`` + propagate through ``TenantContextService``
- **Introduce a new metric tag dimension** → add to ``PlatformMetricTagsService``
- **Standardize a new logging field** → add to ``MdcLoggingContext`` snapshot
- **Add a new ASAP issuer pattern** → modify ``HeaderFilter`` and ``identity`` package

What you would NOT change here
===============================

- LLM-specific behavior (lives in platform/service)
- Per-product context (lives in product/)
- HTTP routing (lives in service/)

