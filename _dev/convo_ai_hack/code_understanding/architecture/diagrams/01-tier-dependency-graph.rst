.. _diag-tier-graph:

============================================
Diagram 1 — Tier Dependency Graph & Rules
============================================

The 5-tier hexagonal architecture: which tiers may depend on which, and **which rules are actually enforced** vs only documented.

The dependency graph
=====================

.. mermaid::

   %%{init: {'flowchart': {'curve': 'basis', 'htmlLabels': true, 'rankSpacing': 60, 'nodeSpacing': 40}}}%%
   flowchart TD
       %% Tier nodes (5 layers)
       SVC["**service**<br/>5 modules<br/>Spring Boot bootstrap, controllers,<br/>SQS handlers, deploy descriptor"]
       PROD["**product**<br/>29 modules<br/>Per-product business logic<br/>(jira, confluence, jsm, csm, rovo, ...)"]
       PLAT["**platform**<br/>36 modules<br/>Cross-product capabilities<br/>(AI Gateway client, conversation, knowledge, ...)"]
       FND["**foundation**<br/>11 modules<br/>Infrastructure primitives<br/>(TenantContext, MDC, RolloutService, ADK, ...)"]
       CTB["**contrib**<br/>4 modules<br/>Vendor adapters<br/>(small, opaque tier)"]

       %% Allowed dependency edges (downward)
       SVC -->|allowed| PROD
       SVC -->|allowed| PLAT
       SVC -->|allowed| FND
       SVC -->|allowed| CTB
       PROD -->|allowed| PLAT
       PROD -->|allowed| FND
       PROD -->|allowed| CTB
       PLAT -->|allowed| FND
       PLAT -->|allowed| CTB
       FND -->|allowed| CTB

       %% Forbidden upward edges (red dashed, with X marker via thick stroke)
       PLAT -.->|FORBIDDEN| PROD
       PROD -.->|FORBIDDEN| SVC
       FND -.->|FORBIDDEN| PLAT
       FND -.->|FORBIDDEN| PROD
       CTB -.->|FORBIDDEN| FND

       %% Styling
       classDef forbidden stroke:#d32f2f,stroke-width:2px,color:#d32f2f
       linkStyle 10,11,12,13,14 stroke:#d32f2f,stroke-width:2px,stroke-dasharray:5,5

       %% Tier coloring
       style SVC fill:#fff3e0,stroke:#e65100,stroke-width:2px
       style PROD fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
       style PLAT fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
       style FND fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
       style CTB fill:#eeeeee,stroke:#616161,stroke-width:2px

How to read it
---------------

* **Solid arrows down** = allowed direction. ``service`` may depend on ``product``; ``product`` may depend on ``platform``; etc.
* **Dashed red arrows up** = FORBIDDEN. ``foundation`` may not depend on ``platform``. ``platform`` may not depend on ``product``.
* **Same-tier dependencies** are allowed (e.g. ``foundation/utilities-api`` ← ``foundation/utilities-impl``).
* **A → B** means "A may import classes from B".

Why this shape?
================

This is a textbook **hexagonal / clean architecture**:

* The **core domain** (``platform``) doesn't know which products use it.
* The **application services** (``product``) compose domain capabilities for specific use cases.
* The **delivery mechanism** (``service``) handles HTTP, GraphQL, queues — easily swappable.
* The **substrate** (``foundation``) is reusable across services; could be extracted as a library.

The result: changing a Jira-specific behavior should NEVER require touching ``platform`` or ``foundation``. If it does, the abstraction has leaked.

Enforcement matrix :sup:`(verified — corrected from earlier docs)`
====================================================================

A critical clarification from a fresh investigation:

.. list-table::
   :header-rows: 1
   :widths: 35 25 40

   * - Rule
     - Enforced How?
     - File:Line
   * - api / spi / impl separation (no module depends on another's ``-impl``)
     - **DOCUMENTED ONLY** — no automated enforcement found
     - AGENTS.md:20 (rule); no enforcement code located
   * - SPI consumed only by matching ``-impl`` and ``convo-ai-service``
     - **DOCUMENTED ONLY**
     - AGENTS.md:21 (rule); no enforcement code located
   * - Platform may not depend on product / aifeature
     - **BUILD-TIME** (``GradleException`` in dep resolution listener)
     - ``build.gradle.kts:588`` and ``:596``
   * - Foundation isolation (only depends on other foundation + test-utils)
     - **TEST-TIME** (ArchUnit)
     - ``modules/foundation/testing/arch/.../FoundationModuleArchTest.kt:19-33``
   * - Foundation tests must use MockK (no Mockito/PowerMock/Spock)
     - **BUILD-TIME** (``GradleException``)
     - ``build.gradle.kts:628``

What this means in practice
----------------------------

* You **cannot** push a PR that makes ``platform/service-impl`` depend on ``product/jira-impl`` — Gradle dep-resolution rejects it.
* You **cannot** push a PR that adds Mockito to a ``foundation/*`` module — Gradle dep-resolution rejects it.
* You **cannot** push a PR where a ``foundation/*`` module depends on anything outside foundation — the ArchUnit test will fail (NOT the build, but a CI test failure).
* You **CAN** technically push a PR where ``conversation-impl`` depends on ``knowledge-impl`` — the api/spi/impl separation rule is documented but not automatically caught. **Reviewers must catch this.**

This is an important honesty distinction. AGENTS.md describes intent; only some intents are mechanized.

Module counts per tier
=======================

.. mermaid::

   pie title Modules per tier (85 total)
       "platform (36)" : 36
       "product (29)" : 29
       "foundation (11)" : 11
       "service (5)" : 5
       "contrib (4)" : 4

Insights
---------

* **Platform is the largest tier** (42% of modules). This makes sense: cross-cutting capabilities accumulate as the platform grows.
* **Product is large but disciplined** (34%). Each new product adds 2-6 modules; total reflects growth across 14 products.
* **Foundation is intentionally small** (13%). Foundation grows only when truly cross-cutting concerns emerge (e.g. tenant context, MDC, ADK).
* **Service is tiny** (6%). Controllers and bootstrap don't grow proportionally with capability count — same controllers route to many capabilities.
* **Contrib is vestigial** (5%). Only 4 modules; documented as "skip on first read".

What this NOT
==============

* Not a class diagram — that would be 12,990 nodes.
* Not a runtime call graph — these are **compile-time** dependencies, not runtime call paths.
* Not a deployment topology — this is module structure within a single deployable.

