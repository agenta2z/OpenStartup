=================================================
AgentStudio Reports & Insights
=================================================

**One-sentence definition**: A minimal agent-configuration insights
GraphQL query that returns whether a Rovo agent has handoff actions
configured. NOT a full analytics dashboard.

**User-visible**: Yes — surfaced in the AgentStudio admin UI to help
agent owners verify their agent is properly configured.

**Honest scope correction**: The Wave-2 inventory's score of 14 was
overstated. This is currently a **single-boolean configuration check**,
not a multi-metric performance dashboard. Future expansion is likely
but not yet implemented.

Where it lives
================

.. list-table::
   :header-rows: 1
   :widths: 60 12 28

   * - Path
     - Lines
     - Purpose
   * - ``modules/product/agentstudio/agentstudio-api/.../AgentStudioReportService.kt``
     - ~30
     - Service interface
   * - ``modules/product/agentstudio/agentstudio-impl/.../AgentStudioReportServiceImpl.kt``
     - ~150
     - Implementation
   * - ``modules/product/agentstudio/agentstudio-impl/.../graphql/AgentStudioReportQueryController.kt``
     - ~80
     - GraphQL endpoint

What it does
==============

**Single GraphQL query**:

.. code-block:: graphql

   query GetInsightsConfig($id: ID!, $cloudId: ID!) {
     agentStudio_insightsConfiguration(id: $id, cloudId: $cloudId) {
       isHandoffConfigured
     }
   }

**Returns**:

.. code-block:: json

   {
     "isHandoffConfigured": true
   }

**Implementation**: reads agent scenarios + skill instances via
``RovoAgentService``; checks if any scenario has a JSM handoff action
configured.

Data flow
===========

.. code-block:: text

   GraphQL Query
       ↓
   AgentStudioReportQueryController.getInsightsConfigurationByAgentId()
       ↓
   AgentStudioContextService.runWithRovoContextSuspend()  // tenant + user MDC
       ↓
   AgentStudioReportServiceImpl.getAgentInsightsConfiguration()
       ↓
   RovoAgentService.getAgent(agentId)
       ↓
   Iterate scenarios → check for handoff tool / action
       ↓
   Return AgentStudioInsightsConfigurationGraphQLType(isHandoffConfigured)

Configuration / FF gates
==========================

* ``HANDLE_V2_SKILLS_HANDOFF_CONFIG`` — controls Scenario V1 vs V2 logic in handoff detection
* No other FF gates

Permissions
=============

Standard ``User`` context + ``RovoAgentARI`` validation via
``AgentStudioContextService.runWithRovoContextSuspend()``. Same
permissions as other AgentStudio queries.

Honest gaps
=============

What this subsystem **does NOT** include (despite the "Reports" name):

#. ❌ No conversation analytics
#. ❌ No latency/error/throughput metrics surfaced to users
#. ❌ No ARIZE / Splunk integration
#. ❌ No multi-metric dashboard
#. ❌ No trend graphs or time-series data
#. ❌ No event-stream aggregation pipeline (real-time or batch)
#. ❌ No per-conversation review API (that's ``AgentStudioConversationReview*Controller``, separate)

For real conversation analytics + agent performance, see:

* ``AgentStudioConversationReviewQueryController`` — per-conversation LLM-judge reviews
* ``AgentStudioBatchEvaluationQueryController`` — batch evaluation jobs for testing agents at scale
* ARIZE dashboards (external, not in code) — for LLM observability
* SignalFx + Splunk dashboards — for system metrics

Open questions
================

#. Are there plans to expand this into a multi-metric dashboard? (Suggested: feature flag visibility, latency p50/p95, error rate, handoff rate)
#. Should this be merged with ``AgentStudioConversationReview*`` for unified agent insights?
#. What's the UI consumer of ``isHandoffConfigured`` exactly — agent settings page warning?

Cross-references
==================

* :doc:`agentstudio` — AgentStudio module overview
* :doc:`jsm-composer-handoff` — handoff system AgentStudio Reports queries
