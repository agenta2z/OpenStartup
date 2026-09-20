.. _pai-platform-context:

============================================================================
``context`` — Tenant / Product / Experience domain models
============================================================================

:Date: 2026-05-04
:Files: 9 main / 0 test (covered indirectly by integration tests)
:Importance: **P2 — type-safe domain context; type system catches most bugs**

----

.. contents:: Table of Contents
   :depth: 2
   :local:

----

1. Overview
==============

Canonical types for everything that "describes who is asking and from where".
Every PAI request carries a ``TenantContext`` that bundles together the
product being used, the workspace data available, and the AI experience
being served. The package enforces type-safety through a hierarchy of narrow
interfaces so that each callsite only depends on the context it needs.

2. File inventory
====================

.. list-table::
   :header-rows: 1
   :widths: 45 15 40

   * - File
     - LoC
     - Role
   * - ``TenantContext.kt``
     - ~35
     - Aggregate data class implementing 4 marker interfaces
   * - ``ProductContext.kt`` / ``TenantContextModels.kt``
     - ~80
     - Product, data workspace, enablement state models
   * - ``DataContext.kt`` (in TenantContextModels)
     - —
     - Workspace data identifiers + Plato/ContentSearcher contexts
   * - ``ExperienceContext.kt`` (in TenantContextModels)
     - —
     - Use-case selector (experience + channelId)
   * - ``Product.kt`` (enum)
     - ~60
     - 7 products with legacy ID support
   * - ``Experience.kt`` (enum)
     - ~60
     - Experiences with branding, use-case, team ownership
   * - ``AIGatewayContext.kt`` (interface)
     - ~8
     - ``getAiGatewayUseCaseId()``, ``getAiGatewayCloudId()``
   * - ``CloudIdContext.kt`` (interface)
     - ~10
     - ``getCloudId()``, ``getBrowsingProduct()``, ``getExperience()``
   * - ``OrgIdContext.kt`` (interface)
     - ~5
     - ``getOrgId()``
   * - ``PlatformTenantContext.kt`` (interface)
     - ~3
     - Marker interface for cross-product tenant model

3. Interface hierarchy
=========================

.. code-block:: text

   PlatformTenantContext (marker)
   AIGatewayContext      → getAiGatewayUseCaseId(), getAiGatewayCloudId()
   CloudIdContext        → getCloudId(), getBrowsingProduct(), getExperience()
   OrgIdContext          → getOrgId()
       │
       └── TenantContext (data class) implements all four

**Narrowest-interface pattern**: method signatures should accept the narrowest
interface that satisfies their needs. E.g. a Stratus call only needs
``AIGatewayContext``, not ``TenantContext`` — keeps coupling low.

4. Key types deep dive
=========================

``TenantContext`` (data class)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   data class TenantContext(
       val productContext: ProductContext,
       val dataContext: DataContext,
       val experienceContext: ExperienceContext,
   ) : PlatformTenantContext, AIGatewayContext, CloudIdContext, OrgIdContext

Key methods:

* ``getTenantId()`` → ``cloudId ?: workspaceARI.resourceId``
* ``getAiGatewayUseCaseId()`` → ``experienceContext.experience.useCase.id``
* ``getConfluenceWorkspaceARI()`` / ``getJiraWorkspaceARI()`` — returns
  ``null`` if HIPAA-enabled (data isolation)

``Product`` (enum — 7 values)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   JIRA_PLATFORM("jira"), JIRA_SOFTWARE("jira-software"),
   JIRA_SERVICE_MANAGEMENT("jsm"), JIRA_WORK_MANAGEMENT("jira-core"),
   JIRA_PRODUCT_DISCOVERY("jpd"), CONFLUENCE("confluence"),
   BITBUCKET("bitbucket")

* ``matchesId(productId)`` — checks primary ID and ``legacyIds``
* ``ALL_JIRA_PRODUCTS`` — set of all 5 Jira variants
* ``findById(productId)`` — O(n) scan with legacy fallback

``Experience`` (enum)
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   enum class Experience(
       val id: String,
       val description: String,
       val supportedProducts: Set<Product>,
       val branding: Set<Branding>,
       val useCase: UseCase,
       val helpseekerExperience: HelpSeekerExperience,
       val owningTeam: String,
       val slackChannel: String,
       val internal: Boolean = false,
   )

Current value: ``PROACTIVE_AI_ROVO_BUTTON``. New experiences are added by
extending this enum.

Related enums:

* ``UseCase``: ``ROVO_BUTTON("rovo-button")``, ``ROVO_INSIGHTS("rovo-insights")``
* ``Branding``: ``ROVO``, ``ATLASSIAN_INTELLIGENCE``
* ``HelpSeekerExperience``: ``HELPSEEKER_EXPERIENCE``, ``NON_HELPSEEKER_EXPERIENCE``

``ProductEnablementState`` (data class)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Feature toggles per workspace:

* ``active``, ``aiEnabled``, ``rovoEnabled``, ``rovoLLMEnabled``
* ``hipaaEnabled``, ``guardPremiumEnabled``
* ``hasNonSiteProductWorkspaceAccess``

``DataWorkspaces``
~~~~~~~~~~~~~~~~~~~~

.. code-block:: kotlin

   data class DataWorkspaces(val workspaces: Set<DataWorkspace>) {
       fun getConfluenceAriIfAvailable(): ConfluenceWorkspaceARI?  // null if HIPAA
       fun getJiraAriIfAvailable(): JiraWorkspaceARI?              // null if HIPAA
   }

HIPAA-enabled workspaces return ``null`` to prevent data leaking into
non-compliant AI pipelines.

5. Error handling
====================

* ``ExperienceIdNotFoundException`` extends ``BadRequestException`` — thrown by
  ``Experience.findByIdOrThrow()`` when an unknown experience ID is provided.

6. Test coverage
==================

No dedicated unit tests. The ``context/`` package is covered indirectly by
integration tests that exercise the full request lifecycle. The Kotlin type
system catches most bugs at compile time (null-safety, exhaustive ``when``
on enums). Adding dedicated tests is low priority because:

* Data classes have no behaviour beyond field access.
* Enum values are compile-time constants.
* Interface methods are trivially delegated.

7. Integration patterns
==========================

* **Built by**: Controllers via ``CommonContextSetter.setTenant()``
* **Consumed by**: ``LoggingContext.addTenantContext()``, ``FeatureService``
  (Statsig context), ``AIGatewayService.buildAgent()``
* **Passed as**: Method arguments using narrowest interface

8. Design decisions
======================

1. **Interface segregation** — four narrow interfaces prevent tight coupling.
2. **HIPAA null-safety** — ``getConfluenceAriIfAvailable()`` returns ``null``
   for HIPAA workspaces rather than throwing, forcing callers to handle.
3. **Legacy ID support** — ``Product.matchesId()`` handles migration from old
   product IDs (e.g. ``"jira-servicedesk"`` → ``"jsm"``).
4. **Enum-based experiences** — closed set prevents unknown experiences from
   entering the system.

9. See also
==============

* :doc:`/architecture/cross-cutting/08-auth-and-tenant` — how context is built
* :doc:`/modules/platform/interceptor` — sets limited context
* :doc:`/modules/platform/requestcontext` — MDC context integration
