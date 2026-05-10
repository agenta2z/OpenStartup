.. _tier-service:

==========================================================
Service tier — Boot, REST/GraphQL, deployment
==========================================================

The **HTTP entry point**. Spring Boot application, REST controllers, GraphQL schemas, deployment descriptors.

Architectural rule: service is the **only tier** that may depend on every other tier.
Test-time enforcement: ArchUnit.

Module catalog
================

.. toctree::
   :maxdepth: 1

   convo-ai-service
   convo-ai-test-integration
   convo-ai-service-api
   convo-ai-service-graphql
   convo-ai-service-descriptor
