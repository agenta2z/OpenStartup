.. _mod-convo-ai-service-api:

==============================================
``service/convo-ai-service-api``
==============================================

:Tier: service
:Path: ``modules/service/convo-ai-service-api``
:Size: ~822 source lines :sup:`(verified)`

Cross-cutting service-tier API. **Provisioning lifecycle**, **prompt store**, **POCO data-policy evaluation**, **Teamcamp client**, **versioning migration**.

Top files :sup:`(verified)`
============================

.. list-table::
   :header-rows: 1
   :widths: 55 15 30

   * - File
     - Lines
     - Concept
   * - ``TeamcampClient.kt``
     - 156
     - Teamcamp integration
   * - ``ProvisioningModels.kt``
     - 132
     - Provisioning DTOs
   * - ``PocoSensitiveDataPolicyEvaluationResponse.kt``
     - 122
     - POCO policy result
   * - ``ErsProvisioning.kt``
     - 59
     - Provisioning ERS doc
   * - ``ErsPrompt.kt``
     - 57
     - Prompt-store ERS doc

Key contracts
==============

* ``TeamcampClient`` — sub-tenant / org graph
* ``ProvisioningModels`` — tenant provisioning DTOs
* ``PocoSensitiveDataPolicyEvaluationResponse`` — POCO (Policy Catalog) evaluation result
* ``ErsProvisioning``, ``ErsPrompt`` — ERS persistence
* ``VersioningMigrationStore`` — agent-version migration state

Notable findings
==================

* **POCO** = Atlassian's central policy-catalog service for sensitive-data + governance rules. Convo-ai integrates to ask "can the user receive this AI response under their tenant's policy?"
* **Teamcamp** = Atlassian's org/team graph — for understanding tenant org structure.
* Five different concerns in one module — moderate cohesion. Could split, but each is small.

