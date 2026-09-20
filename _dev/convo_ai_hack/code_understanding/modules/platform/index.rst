.. _tier-platform:

==========================================================
Platform tier — Convo-AI capabilities
==========================================================

The **central abstraction layer**. Defines what convo-ai *is*: agents, tools, workflow, evaluation, knowledge, conversations, sandbox, AI gateway.

Architectural rule: platform may depend on foundation, not on product or service.
Test-time enforcement: ArchUnit.

Module catalog by sub-domain
==============================

.. rubric:: Action runtime (3 modules)

.. toctree::
   :maxdepth: 1

   action-api
   action-spi
   action-impl

.. rubric:: Agent versioning (3 modules)

.. toctree::
   :maxdepth: 1

   agent-version-api
   agent-version-spi
   agent-version-impl

.. rubric:: Base / utilities (2 modules)

.. toctree::
   :maxdepth: 1

   base-api
   base-impl

.. rubric:: Atlassian REST/GraphQL clients (2 modules)

.. toctree::
   :maxdepth: 1

   client-api
   client-impl

.. rubric:: Conversation runtime (3 modules)

.. toctree::
   :maxdepth: 1

   conversation-api
   conversation-spi
   conversation-impl

.. rubric:: Evaluation runtime (3 modules)

.. toctree::
   :maxdepth: 1

   evaluation-api
   evaluation-spi
   evaluation-impl

.. rubric:: Knowledge / RAG (3 modules)

.. toctree::
   :maxdepth: 1

   knowledge-api
   knowledge-spi
   knowledge-impl

.. rubric:: Knowledge gaps (3 modules)

.. toctree::
   :maxdepth: 1

   knowledge-gap-api
   knowledge-gap-spi
   knowledge-gap-impl

.. rubric:: Sandbox (2 modules)

.. toctree::
   :maxdepth: 1

   sandbox-api
   sandbox-impl

.. rubric:: Service layer (2 modules)

.. toctree::
   :maxdepth: 1

   service-api
   service-impl

.. rubric:: Stratus contracts (2 modules)

.. toctree::
   :maxdepth: 1

   stratus-api
   stratus-spi

.. rubric:: Tool registry (3 modules)

.. toctree::
   :maxdepth: 1

   tool-registry-umbrella
   tool-registry-api
   tool-registry-impl

.. rubric:: Widget (1 module)

.. toctree::
   :maxdepth: 1

   widget-api

.. rubric:: Workflow runtime (3 modules)

.. toctree::
   :maxdepth: 1

   workflow-umbrella
   workflow-api
   workflow-impl
