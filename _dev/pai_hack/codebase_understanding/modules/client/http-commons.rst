=====================================================
Module: ``http-commons`` — Shared HTTP Constants
=====================================================

.. contents:: Section contents
   :depth: 2
   :local:

Purpose
=======

Centralises HTTP header names and audience identifiers used across all
outbound HTTP clients.  Prevents string duplication and ensures consistent
Slauth egress header usage.

File Inventory
==============

.. list-table::
   :header-rows: 1
   :widths: 45 10 45

   * - File
     - LoC
     - Role
   * - ``HttpClientCommons.kt``
     - 18
     - Object — HTTP header name constants
   * - ``Audiences.kt``
     - 8
     - Object — Slauth audience identifier constants

**Total: 2 files, ~26 LoC**

Class / Interface / Enum Catalog
================================

Objects
-------

* ``HttpClientCommons`` — constants:

  - ``HOST`` — ``"Host"``
  - ``X_FORWARDED_HOST`` — ``"X-Forwarded-Host"``
  - ``X_SLAUTH_EGRESS_HEADER`` — Slauth egress header for service-to-service auth.
  - ``X_SLAUTH_AUDIENCE_HEADER`` — Slauth audience header.
  - Additional header constants for request context propagation.

* ``Audiences`` — constants:

  - ``AI_GATEWAY = "ai-gateway"``
  - ``CONVO_AI = "convo-ai"``
  - ``INTEGRATIONS_SERVICE = "integrations-service"``
  - ``IDENTITY_PLATFORM = "identity-platform"``

Spring Component Annotations
=============================

None — pure constants with no Spring annotations.

Data Flow
=========

.. code-block:: mermaid

   flowchart TD
       A[HttpClientCommons] -->|header constants| D[AsyncIdGatekeeperClientImpl]
       A -->|header constants| E[AIGatewayServiceImpl]
       A -->|header constants| F[IntegrationServiceToolProvider]
       B[Audiences] -->|IDENTITY_PLATFORM| D
       B -->|AI_GATEWAY| E
       B -->|INTEGRATIONS_SERVICE| F

Configuration Knobs
===================

None — all values are compile-time constants.

Testing Coverage
================

No dedicated test files.  Constants are validated indirectly through client
integration tests.

Dependencies
============

Inbound (consumed by)
---------------------

* ``client/identity`` — uses header constants and ``IDENTITY_PLATFORM`` audience.
* ``integration/stratus`` — uses ``AI_GATEWAY``, ``INTEGRATIONS_SERVICE``
  audiences and header constants.

Outbound (depends on)
---------------------

None — leaf module with no dependencies.

Open Questions / Ambiguities
=============================

1. ``Audiences`` values must match the Slauth service registry — no
   compile-time validation against the actual registry.
2. Some header constants may duplicate values in ``HeaderConstants`` (from
   ``requestcontext`` module) — potential for drift.
3. Adding a new upstream service requires adding a constant here and
   redeploying — consider externalising audience names to config if the
   list grows.
