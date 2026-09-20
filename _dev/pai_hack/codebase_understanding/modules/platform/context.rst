==============================================
Module: ``context`` — Tenant & Product Context
==============================================

.. contents:: Section contents
   :depth: 2
   :local:

Purpose
=======

Defines the **tenant identity model** used throughout the service.  Every
authenticated request carries a ``TenantContext`` that captures the cloud-id,
org-id, product, experience, and workspace ARIs.  These types are consumed by
interceptors, feature-flag evaluation, logging, and all feature modules.

File Inventory
==============

.. list-table::
   :header-rows: 1
   :widths: 50 10 40

   * - File
     - LoC
     - Role
   * - ``AIGatewayContext.kt``
     - 7
     - Interface — AI Gateway use-case id & cloud-id
   * - ``CloudIdContext.kt``
     - 15
     - Interface — cloud-id, product, experience accessors
   * - ``Experience.kt``
     - 81
     - Enums: ``HelpSeekerExperience``, ``UseCase``, ``Branding``, ``Experience``
   * - ``OrgIdContext.kt``
     - 5
     - Interface — org-id accessor
   * - ``PlatformTenantContext.kt``
     - 3
     - Marker interface combining all context facets
   * - ``Product.kt``
     - 82
     - Enum: ``Product`` (Jira, Confluence, etc.)
   * - ``TenantContext.kt``
     - 41
     - Data class implementing all context interfaces
   * - ``TenantContextModels.kt``
     - 140
     - DTOs: ``ProductContext``, ``DataWorkspace``, ``PlatoContext``, etc.
   * - ``Types.kt``
     - 7
     - Type aliases: ``CloudId``, ``ActivationId``, ``OrgId``

**Total: 9 files, ~381 LoC**

Class / Interface / Enum Catalog
================================

Interfaces
----------

* ``AIGatewayContext`` — ``getAiGatewayUseCaseId()``, ``getAiGatewayCloudId()``.
* ``CloudIdContext`` — ``getCloudId()``, ``getBrowsingProduct()``,
  ``getExperience()``, ``getExperienceChannelId()``.
* ``OrgIdContext`` — ``getOrgId()``.
* ``PlatformTenantContext`` — marker interface extending all above.

Data Classes
------------

* ``TenantContext`` — **the principal context object**; implements
  ``PlatformTenantContext``, ``AIGatewayContext``, ``CloudIdContext``,
  ``OrgIdContext``.  Provides ``getConfluenceWorkspaceARI()`` and
  ``getJiraWorkspaceARI()`` convenience methods.
* ``ProductEnablementState`` — whether a product is enabled for the tenant.
* ``ProductContext`` — product + cloud-id pairing.
* ``ExperienceContext`` — experience + channel-id.
* ``DataWorkspace`` — workspace ARI + type.
* ``DataWorkspaces`` — collection with ``getConfluenceAriIfAvailable()`` /
  ``getJiraAriIfAvailable()`` helpers.
* ``DataContext`` — wraps ``DataWorkspaces``.
* ``PlatoContext`` — upstream orchestration context.
* ``ContentSearcherContext`` — search-scoping context.

Enums
-----

* ``Product`` — ``JIRA``, ``CONFLUENCE``, ``BITBUCKET``, ``TRELLO``,
  ``OPSGENIE``, ``STATUSPAGE``, ``HALP``, ``JSM_VIRTUAL_AGENT``, ``ROVO``,
  ``TEAM_CENTRAL``.  Companion: ``findById()``, ``matchesId()``,
  ``ALL_JIRA_PRODUCTS``, ``ALL_PRODUCTS``.
* ``Experience`` — ``CHAT``, ``SEARCH``, ``AGENT_BUILDER``, etc.
  Companion: ``findById()``, ``findByIdOrThrow()``.
* ``HelpSeekerExperience`` — sub-enum for help-seeker flows.
* ``UseCase`` — categorises the AI gateway use-case.
* ``Branding`` — presentation branding variant.
* ``DataWorkspaceType`` — ``CONFLUENCE_WORKSPACE``, ``JIRA_WORKSPACE``.

Exceptions
----------

* ``ExperienceIdNotFoundException`` — thrown by ``Experience.findByIdOrThrow``.

Type Aliases
------------

* ``CloudId = String``
* ``ActivationId = String``
* ``OrgId = String``

Spring Component Annotations
=============================

None — this module is a **pure domain model** with no Spring beans.

Data Flow
=========

.. code-block:: mermaid

   flowchart TD
       A[RequestContextExtractor] -->|extracts headers| B[TenantContext]
       B -->|cloudId, orgId, product, experience, workspaceARIs| C[CommonContextSetter.setTenant]
       C --> D[LoggingContext - MDC]
       C --> E[FeatureFlagContextService]
       C --> F[RequestScopedValueService]
       D & E & F --> G[Feature modules]
       G -->|cloudId| G1[gating]
       G -->|orgId| G2[permission checks]
       G -->|product| G3[routing]
       G -->|experience| G4[UX branching]

Configuration Knobs
===================

No YAML properties.  All values originate from HTTP request headers:

* ``X-Cloud-Id`` → ``cloudId``
* ``X-Org-Id`` → ``orgId``
* ``X-Product`` → ``product``
* ``X-Experience`` → ``experience``
* ``X-Experience-Channel-Id`` → ``experienceChannelId``

Testing Coverage
================

**No dedicated test files** exist for this module.  Coverage is achieved
indirectly through:

* ``CommonContextSetterTest`` (interceptor module)
* ``FeatureFlagContextServiceImplTest`` (featuregate module)
* Integration tests that exercise full request pipelines.

**Gap:** ``Experience.findByIdOrThrow`` error paths and ``Product.matchesId``
edge cases lack direct unit tests.

Dependencies
============

Inbound (consumed by)
---------------------

* ``requestcontext`` — ``RequestContextValues`` references ``TenantContext``.
* ``interceptor`` — ``CommonContextSetter`` creates and propagates contexts.
* ``featuregate`` — ``FeatureFlagContextService`` reads ``TenantContext``.
* ``logging`` — ``LoggingContext.addTenantContext`` receives ``TenantContext``.
* ``feature/rovoinsights`` — insight generation reads cloud-id.
* ``feature/nudge`` — throttle controller receives cloud-id header.
* ``integration/stratus`` — ``AIGatewayService.buildAgent`` reads cloud-id.

Outbound (depends on)
---------------------

* Atlassian ARI libraries — ``ConfluenceWorkspaceARI``, ``JiraWorkspaceARI``,
  ``ARILike``.
* Jackson — ``@JsonProperty`` annotations on models.

Open Questions / Ambiguities
=============================

1. ``TenantContextModels.kt`` at 140 LoC contains 8 data classes — consider
   splitting into ``workspace-models.kt`` and ``orchestration-models.kt``.
2. ``PlatformTenantContext`` is a marker interface with no methods — its value
   is purely for type-union; document whether this is intentional or vestigial.
3. ``Experience`` enum hard-codes UI experience identifiers; adding a new
   experience requires a code deploy rather than config.
4. ``AIGatewayContext`` methods overlap with ``CloudIdContext.getCloudId()`` —
   ``getAiGatewayCloudId`` vs ``getCloudId`` may diverge silently.
