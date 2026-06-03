.. _tier-product:

==========================================================
Product tier — Per-product features
==========================================================

The **product surface**. Per-product agent definitions, skills, and chat executors. Built on platform.

Architectural rule: product may depend on foundation + platform, not on service.
Test-time enforcement: ArchUnit.

Module catalog by product
============================

.. rubric:: Rovo (Atlassian's AI assistant) — 5 modules

.. toctree::
   :maxdepth: 1

   rovo-api
   rovo-impl
   rovo-spi
   rovo-extras-impl
   rovo-leaf-agents-impl
   marathon-stubs-publisher

.. rubric:: ADK (Agent Development Kit) — 2 modules

.. toctree::
   :maxdepth: 1

   adk-agent-api
   adk-dev

.. rubric:: AgentStudio — 2 modules

.. toctree::
   :maxdepth: 1

   agentstudio-api
   agentstudio-impl

.. rubric:: Agent framework — 1 module

.. toctree::
   :maxdepth: 1

   agent-framework-impl

.. rubric:: AI Features — 3 modules

.. toctree::
   :maxdepth: 1

   aifeature-api
   aifeature-spi
   aifeature-impl

.. rubric:: Atlassian Studio — 2 modules

.. toctree::
   :maxdepth: 1

   atlassianstudio-api
   atlassianstudio-impl

.. rubric:: Chat-common (cross-product) — 1 module

.. toctree::
   :maxdepth: 1

   chat-common-api

.. rubric:: Confluence — 2 modules

.. toctree::
   :maxdepth: 1

   confluence-api
   confluence-impl

.. rubric:: CSM (Customer Service) — 2 modules

.. toctree::
   :maxdepth: 1

   csm-api
   csm-impl

.. rubric:: Jira (Issues) — 2 modules

.. toctree::
   :maxdepth: 1

   jira-api
   jira-impl

.. rubric:: JPD (Product Discovery) — 2 modules

.. toctree::
   :maxdepth: 1

   jpd-api
   jpd-impl

.. rubric:: JSM (Service Management) — 2 modules

.. toctree::
   :maxdepth: 1

   jsm-api
   jsm-impl

.. rubric:: Loom (Video) — 2 modules

.. toctree::
   :maxdepth: 1

   loom-api
   loom-impl

.. rubric:: Shared features — 1 module

.. toctree::
   :maxdepth: 1

   shared-features-api
