==============================================
Module: ``config`` — Application Configuration
==============================================

.. contents:: Section contents
   :depth: 2
   :local:

Purpose
=======

Centralises Spring Boot configuration: environment detection, security setup,
MVC interceptor registration, scheduling, and conditional bean activation for
worker-node topologies.

File Inventory
==============

.. list-table::
   :header-rows: 1
   :widths: 50 10 40

   * - File
     - LoC
     - Role
   * - ``MicrosEnvironmentConfig.kt``
     - 21
     - ``@Configuration`` — exposes ``MicrosEnvironmentType`` bean
   * - ``MicrosEnvironmentType.kt``
     - 27
     - Enum: LOCAL / STAGING / PROD with helpers
   * - ``MvcSecurityConfig.kt``
     - 15
     - ``@Configuration`` — anonymous path whitelist bean
   * - ``OnLongRunWorkerNodeOrLocalCondition.kt``
     - 21
     - ``Condition`` — true on long-run worker or local env
   * - ``OnSHWorkerNodeOrLocalCondition.kt``
     - 21
     - ``Condition`` — true on StreamHub worker or local env
   * - ``WebMvcConfiguration.kt``
     - 103
     - ``@Configuration @EnableScheduling`` — interceptors, async support

**Total: 6 files, ~208 LoC**

Class / Interface / Enum Catalog
================================

Configuration Classes
---------------------

* ``MicrosEnvironmentConfig`` (``@Configuration``) — reads
  ``${micros.environment.type}`` and produces a ``MicrosEnvironmentType`` bean.
* ``MvcSecurityConfig`` (``@Configuration``) — defines ``anonymousPaths()``
  bean (``List<String>``) listing URL patterns exempted from authentication.
* ``WebMvcConfiguration`` (``@Configuration``, ``@EnableScheduling``,
  ``WebMvcConfigurer``) — registers interceptors via ``addInterceptors()``
  and configures async support via ``configureAsyncSupport()``.

Enums
-----

* ``MicrosEnvironmentType`` — ``LOCAL``, ``STAGING``, ``PROD``.

  - ``isNonProduction(): Boolean`` — true for LOCAL, STAGING.
  - ``isProduction(): Boolean`` — true for PROD.
  - ``companion object fromString(value: String): MicrosEnvironmentType`` —
    case-insensitive lookup.

Condition Classes
-----------------

* ``OnLongRunWorkerNodeOrLocalCondition`` — implements Spring ``Condition``;
  returns ``true`` when ``MICROS_ENVTYPE == local`` **or** the node is tagged
  as a long-run worker.  Used by ``@Conditional`` on SQS consumers that
  process long-running tasks (e.g., Rovo Insights generation).

* ``OnSHWorkerNodeOrLocalCondition`` — same pattern but checks for the
  StreamHub (SH) worker tag.  Used by analytics-event SQS consumers.

Spring Component Annotations
=============================

=============================== ================================
Bean                             Annotation
=============================== ================================
``MicrosEnvironmentConfig``      ``@Configuration``
``MvcSecurityConfig``            ``@Configuration``
``WebMvcConfiguration``          ``@Configuration @EnableScheduling``
=============================== ================================

Beans produced:

* ``MicrosEnvironmentType`` via ``@Bean`` in ``MicrosEnvironmentConfig``.
* ``List<String>`` (anonymous paths) via ``@Bean`` in ``MvcSecurityConfig``.

Data Flow
=========

.. code-block:: mermaid

   flowchart TD
       A["application.yml
       micros.environment.type"] --> B["MicrosEnvironmentConfig (@Bean)"]
       B --> C[MicrosEnvironmentType enum bean]
       C --> D{OnLongRunWorkerNodeOrLocalCondition}
       D -->|gates| E[RovoInsightsGenerationSqsQueueConsumer]
       C --> F{OnSHWorkerNodeOrLocalCondition}
       F -->|gates| G[AnalyticsEventsSqsQueueConsumer]
       C --> H[WebMvcConfiguration]
       H --> I["addInterceptors()
       RequestContextInterceptor, UserContextInterceptor"]
       H --> J["configureAsyncSupport()
       async timeout, executor"]

Configuration Knobs
===================

.. list-table::
   :header-rows: 1
   :widths: 40 20 40

   * - Property
     - Default
     - Description
   * - ``micros.environment.type``
     - ``${MICROS_ENVTYPE}``
     - Determines LOCAL / STAGING / PROD
   * - ``micros.security.slauth.poco-enabled``
     - ``true``
     - Enables policy-based access control
   * - ``micros.security.slauth.ingress.enabled``
     - ``true``
     - Enables Slauth ingress verification
   * - ``micros.rest.asap.enabled``
     - ``false``
     - ASAP token validation
   * - ``micros.rest.asap.client.enabled``
     - ``true``
     - ASAP client for outbound calls

Testing Coverage
================

No dedicated test files exist for this module.  Coverage is indirect:

* ``MicrosEnvironmentType`` — implicitly tested via integration tests.
* ``WebMvcConfiguration`` — verified through acceptance tests that exercise
  the interceptor chain.
* Worker-node conditions — tested by SQS consumer startup in integration tests.

**Gap:** ``OnLongRunWorkerNodeOrLocalCondition`` and
``OnSHWorkerNodeOrLocalCondition`` have no unit tests verifying the
environment-variable matching logic.

Dependencies
============

Inbound (consumed by)
---------------------

* ``interceptor`` — interceptors registered by ``WebMvcConfiguration``.
* ``sqs`` — conditions gate consumer startup.
* ``feature/rovoinsights`` — long-run condition gates generation consumer.

Outbound (depends on)
---------------------

* ``interceptor`` — ``RequestContextInterceptor``, ``UserContextInterceptor``.
* Spring Framework — ``Condition``, ``WebMvcConfigurer``,
  ``@EnableScheduling``.

Open Questions / Ambiguities
=============================

1. ``MvcSecurityConfig.anonymousPaths()`` returns a ``List<String>`` bean —
   naming collision risk if other configs also declare ``List<String>`` beans.
   Should use ``@Qualifier`` or a wrapper type.
2. Worker-node conditions read environment variables directly rather than
   using ``@Value``-injected properties — harder to test and overrides via
   Spring test profiles.
3. ``WebMvcConfiguration`` at 103 LoC combines interceptor registration,
   async config, and scheduling enablement — consider splitting if more
   concerns are added.
