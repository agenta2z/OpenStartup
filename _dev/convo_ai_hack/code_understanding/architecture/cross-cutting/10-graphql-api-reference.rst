==========================================
GraphQL API Reference
==========================================

The convoai service exposes its public API surface primarily through
**Spring GraphQL** (with REST endpoints for streaming/voice/WebSocket
flows). This page documents the complete GraphQL API surface.

Schema architecture
=====================

**Federated, per-product:** each product owns its GraphQL controllers,
but schemas are composed at the **AGG (Atlassian GraphQL Gateway)**
layer. Convoai is a **subgraph** of AGG.

* **2 primary schema files** (downstream client schemas):

  * ``modules/platform/client/client-api/src/main/graphql/agg/schema.graphqls`` — main AGG schema
  * ``modules/platform/client/client-api/src/main/graphql/ai_3p/schema.graphqls`` — third-party AI federation

* **6 federated subschema files** (subgraph contributions):

  * ``platform/base/base-api/.../graphqlschema/ConvoAiBase.graphqls``
  * ``platform/base/base-api/.../graphqlschema/agg-shared-types.graphqls``
  * ``platform/conversation/conversation-api/.../AgentSessionMutation.graphqls``
  * ``platform/conversation/conversation-api/.../ConversationStateMutation.graphqls``

Verified controller distribution (49 total)
=============================================

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Module
     - Controllers
     - Notes
   * - **agentstudio-impl**
     - **22**
     - Largest surface — full agent CRUD, knowledge, scenarios, batch eval, widgets
   * - **csm-impl**
     - **14**
     - Agent management, knowledge, coaching, handoff config, widgets, BYOD
   * - **conversation-impl**
     - 2
     - AgentSession + ConversationState (federated session state)
   * - **rovo-impl**
     - 2
     - AvailableSkills + RovoAgentVersion mutations
   * - **convo-ai-service**
     - 1
     - NodeQueryController (federation entity resolver)
   * - **confluence-impl**
     - 1
     - ConfluenceSpaceRecommendation
   * - **atlas-impl**
     - 1
     - Atlas-specific
   * - **atlassianstudio-impl**
     - 1
     - AtlassianStudio context
   * - **aifeature-impl**
     - 1
     - AiFeaturesGraphQLController (consolidates 39 features)

**Notable: 0 ``@SubscriptionMapping``** — streaming is via HTTP SSE
or WebSocket (see ``cross-cutting/04-streaming-and-coroutines.rst``),
NOT GraphQL subscriptions.

Authentication (per-field annotations)
========================================

The AGG schema uses **per-field auth category annotations** in
docstrings:

.. code-block:: text

   |Authentication Category    |Callable      |
   |:--------------------------|:-------------|
   | SESSION                   | ✅ Yes       |
   | API_TOKEN                 | ✅ Yes       |
   | CONTAINER_TOKEN           | ❌ No        |
   | FIRST_PARTY_OAUTH         | ✅ Yes       |
   | THIRD_PARTY_OAUTH         | ❌ No        |
   | UNAUTHENTICATED           | ✅ Yes       |

These categories map to AGG-side request authentication checks.
The convoai subgraph itself receives **already-authenticated** user
context via SLAuth/ASAP signed headers.

Federation patterns
======================

**``@SchemaMapping``** (10+ controllers): used for **field resolvers
on entity types** that are owned by other subgraphs. E.g.:

* ``CsmAgentIdentityConfigController`` resolves CSM-specific fields on the federated ``Agent`` type
* ``CsmHandoffConfigQueryController`` resolves handoff config fields
* ``AgentStudioScenarioFieldResolver`` resolves scenario fields on ``Agent``

Federation pattern: **each product extends shared types** like
``Agent``, ``Conversation``, ``Scenario`` with product-specific fields.

Mutation patterns (transactional semantics)
=============================================

**Standard mutation contract**:

.. code-block:: kotlin

   @MutationMapping
   suspend fun agentStudio_createAgent(
       @Argument input: AgentStudioCreateAgentInputGraphQLType,
       env: DataFetchingEnvironment,
   ): AgentStudioCreateAgentPayloadGraphQLType {
       return agentStudioContextService.runWithRovoContextSuspend(env) {
           try {
               val request = input.toRovoAgentUpdateRequest()
               agentStudioAgentService.createAgent(request).toAgentStudioAssistantGraphQLType()
           } catch (e: Exception) {
               e.toMutationErrorGraphQLType(...)
           }
       }
   }

**Conventions**:

* Input types: ``*InputGraphQLType``
* Payload types: ``*PayloadGraphQLType`` (return data + error union)
* Error mapping: ``e.toMutationErrorGraphQLType()`` extension function
* Context wrapping: ``runWithRovoContextSuspend(env)`` for tenant + user MDC
* Suspend functions throughout (Kotlin coroutines, not blocking)

Code generation
=================

GraphQL types (``*GraphQLType``) are **auto-generated from
``.graphqls`` schema files**. Look at:

* ``modules/platform/base/base-api/build/generated/...`` — generated DTOs
* ``modules/platform/base/base-api/build/resources/main/graphqlschema/`` — generated schema fragments

Generated package: ``io.atlassian.micros.convoai.graphql.generated.model.*``

Versioning strategy
=====================

Per the **CSM REST audit** (see ``features/csm-rest-v1-v2-audit.rst``),
**no V1/V2 versioning** exists at the GraphQL layer. Versioning is
handled via:

1. **Field deprecation** (``@deprecated(reason: "...")`` directive)
2. **Schema-additive evolution** (new fields, no breaking removals)
3. **Federation flexibility** — products can extend types without
   coordination via ``@key``, ``@external``, ``@requires``

There is no ``v1.``/``v2.`` prefix on any GraphQL operation observed.

Per-product API surface
=========================

AgentStudio (22 controllers — agent management UI)
---------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Controller
     - Purpose
   * - ``AgentStudioAgentMutationController``
     - Agent CRUD, permissions, conversation starters
   * - ``AgentStudioAgentQueryController``
     - Agent reads
   * - ``AgentStudioAgenticSkillsQueryController``
     - Agentic skills lookup
   * - ``AgentStudioActionMutationController``
     - Action management
   * - ``AgentStudioAuthReadinessQueryController``
     - Auth-readiness status
   * - ``AgentStudioBatchEvaluationMutationController/QueryController``
     - Batch evaluation jobs (test agents at scale)
   * - ``AgentStudioConversationReviewMutationController/QueryController``
     - Per-conversation review (LLM-judge UI)
   * - ``AgentStudioKnowledgeGapMutationController/QueryController``
     - Knowledge Gap workflow integration
   * - ``AgentStudioKnowledgeMutationController``
     - Knowledge source CRUD
   * - ``AgentStudioMigrationController``
     - Agent migration (V1 → V2 scenarios)
   * - ``AgentStudioReportQueryController``
     - **Insights config (single boolean)** — see ``features/agentstudio-reports.rst``
   * - ``AgentStudioScenarioMutationController/QueryController``
     - Scenario CRUD
   * - ``AgentStudioSkillsQueryController``
     - Skills enumeration
   * - ``AgentStudioToolIntegrationQueryController``
     - Tool integration registry
   * - ``AgentStudioWidgetMutationController/QueryController``
     - Widget configuration

CSM (14 controllers — Customer Service Management agents)
----------------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Controller
     - Purpose
   * - ``CsmAgentMutationController/QueryController``
     - CSM agent CRUD
   * - ``CsmAgentVersionMutationController``
     - Versioning (publish/rollback)
   * - ``CsmAgentIdentityConfigMutationController/Controller``
     - Agent identity (name, persona)
   * - ``CsmActionMutationController/QueryController``
     - Action handlers (handoff, request creation)
   * - ``CsmAiHubQueryController``
     - AI Hub central UI
   * - ``CsmByodQueryController``
     - Bring-Your-Own-Data
   * - ``CsmCoachingContentMutationController/QueryController``
     - Coaching content
   * - ``CsmHandoffConfigMutationController/QueryController``
     - Handoff routing config
   * - ``CsmKnowledgeSourceMutationController``
     - Knowledge source CRUD
   * - ``CsmKnowledgeCollectionQueryController``
     - Knowledge collection reads
   * - ``CsmWidgetClientKeyGenerationController``
     - Widget client key generation
   * - ``CsmWidgetConfigQueryController``
     - Widget config reads
   * - ``CsmWidgetMutationController``
     - Widget CRUD

Other products
----------------

* **rovo-impl** (2): ``AvailableSkills``, ``RovoAgentVersion`` — generic Rovo agent ops
* **conversation-impl** (2): federated session/state mutations
* **convo-ai-service** (1): ``NodeQueryController`` — federation entity resolver (reads any node by ID)
* **confluence-impl** (1): ``ConfluenceSpaceRecommendation`` — space recommendations
* **atlas-impl** (1): Atlas-specific
* **atlassianstudio-impl** (1): cross-product context
* **aifeature-impl** (1): consolidates 39 AI features into single GraphQL controller (``AiFeaturesGraphQLController``)

Querying examples
===================

Get agent insights config:

.. code-block:: graphql

   query GetInsights($id: ID!, $cloudId: ID!) {
     agentStudio_insightsConfiguration(id: $id, cloudId: $cloudId) {
       isHandoffConfigured
     }
   }

Create an agent:

.. code-block:: graphql

   mutation CreateAgent($input: AgentStudioCreateAgentInputGraphQLType!) {
     agentStudio_createAgent(input: $input) {
       agent { id, name }
       error { message, code }
     }
   }

Adding a new GraphQL operation
================================

#. Add field to schema fragment (``*-api/src/main/resources/graphqlschema/*.graphqls``)
#. Run ``./gradlew generateGraphqlTypes`` to regenerate ``*GraphQLType`` DTOs
#. Add controller method with ``@QueryMapping`` or ``@MutationMapping``
#. Wrap in ``runWithRovoContextSuspend(env)`` for tenant context
#. Use ``e.toMutationErrorGraphQLType()`` for error handling
#. Add tests under ``arch/`` to verify schema mapping consistency

Open questions
================

#. **Schema federation specifics** — does AGG do automatic stitching, or is it explicit via gateway config?
#. **Subscription strategy** — why no GraphQL subscriptions? (Streaming via SSE/WebSocket only)
#. **Versioning policy** — what's the deprecation timeline for fields marked ``@deprecated``?
#. **Per-field auth caching** — does AGG cache auth checks per request?
