.. _modules-index:

==============================
Module Reference
==============================

This section provides detailed reference documentation for each functional
module in the Proactive AI Service, organized by architectural grouping.

.. toctree::
   :maxdepth: 2
   :caption: Platform Modules

   platform/index

.. toctree::
   :maxdepth: 2
   :caption: Client Modules

   client/index

.. toctree::
   :maxdepth: 2
   :caption: Feature Modules

   feature/index

.. toctree::
   :maxdepth: 2
   :caption: Integration Modules

   integration/index

Module Groupings
================

The 16 functional modules are organized into four groups:

**Platform** (9 modules)
   Cross-cutting infrastructure that every request passes through:
   request context, interceptors, tenant context, logging, configuration,
   metrics, exceptions, utilities, and feature gates.

**Client** (2 modules)
   Outbound HTTP clients: Identity Gatekeeper and shared HTTP constants.

**Feature** (2 modules)
   Product-facing features: Rovo Insights generation and nudge throttling.

**Integration** (3 modules)
   External-system adapters: AI Gateway (Stratus), SQS event consumption,
   and async-task dispatch framework.
