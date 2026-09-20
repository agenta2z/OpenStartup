==========================================
Glossary
==========================================

This page consolidates all domain acronyms and terms used across the
documentation. When in doubt, check here first.

.. glossary::
   :sorted:

   ADF
       **Atlassian Document Format**. Tree-structured JSON document
       format used across Atlassian's editor (Confluence, Jira, etc.).
       See :doc:`cross-cutting/features/confluence-adf-editor`.

   ADK
       **Agent Development Kit**. The standardized framework /
       libraries used to build agents in convoai (covers tool
       contracts, prompt templating, memory abstraction).

   AGG
       **Atlassian GraphQL Gateway**. The central GraphQL gateway
       that federates queries across all Atlassian product subgraphs.
       Convoai is one subgraph. See :doc:`cross-cutting/10-graphql-api-reference`.

   AIFC
       **AI for Confluence**. Confluence-specific AI features umbrella
       (ADF Editor, page summarization, etc.). See :doc:`cross-cutting/features/aifc`.

   AIFEATURE
       Distinct from AIFC. The AIFEATURE module is the consolidated
       AI features registry — 39 features, 1 GraphQL controller. See
       :doc:`cross-cutting/features/aifeature`.

   ARIZE
       Third-party LLM observability platform. Captures per-LLM-call
       spans for evaluation + drift detection.

   ASAP
       **Atlassian Service Authentication Protocol**. Signed-request
       inter-service authentication using JWT-like tokens. Used for
       service-to-service calls within Atlassian.

   BCS
       **Behavior Conformance Service**. (Inferred — verify usage.)

   CCS
       **Conversation Context Service**. (Inferred — verify usage.)

   CSM
       **Customer Service Management**. Atlassian's customer support
       agent platform. See :doc:`cross-cutting/features/csm-platform`.

   ERS
       **Event Routing Service**. Atlassian's persistence + messaging
       layer. Used for plan persistence, conversation state.

   Federation (GraphQL)
       Apollo Federation pattern — multiple subgraphs (services) own
       their own schema slices, composed at the gateway layer (AGG).

   FF / FeatureFlag
       Statsig-managed feature flag. Wrapped in Kotlin enums like
       ``CSMFeatureFlags``, ``JsmFeatureFlags``. See :doc:`cross-cutting/03-feature-flags`.

   JSM
       **Jira Service Management**. Atlassian's IT service management
       product. See :doc:`cross-cutting/features/jsm-platform`.

   JSM Composer
       LLM-driven setup wizard for JSM project configuration. See
       :doc:`cross-cutting/features/jsm-composer-handoff`.

   Lumina
       Specialized SAIN sub-component for citation-rich, formatting-
       aware responses. NOT a competing orchestrator. See
       :doc:`cross-cutting/features/lumina`.

   Marathon
       Long-horizon agent orchestrator (multi-step task chaining).
       See :doc:`cross-cutting/features/marathon-orchestrator`.

   MCP
       **Model Context Protocol**. Plugin protocol for 3rd-party tool
       integration. See :doc:`cross-cutting/features/mcp-system`.

   Minion
       A specialized task executor — runs as part of an agent flow.
       Examples: ``JsmManageRequestTypeMinion``, ``CollectionMemoryExtractor``.
       See :doc:`cross-cutting/features/agent-framework`.

   Pebble
       Templating engine used for LLM system prompts. Templates live
       in ``modules/.../resources/templates/*.pebble``.

   Provider Pattern
       resilience pattern: ``rolloutService.controlledByLimitedContext(FF).replacingSuspend{V1}.with{V2}.value``
       for FF-gated A/B testing of two implementations.

   Rovo
       Atlassian's AI assistant brand. The Rovo Chat Sandbox + Rovo
       Plugin System are the two main user surfaces.

   Rovo Plugin
       Internal Atlassian plugin protocol (predecessor of MCP).
       See :doc:`cross-cutting/features/rovo-plugin-system`.

   SAIN
       **Search-AI standalone hybrid orchestrator**. Hybrid SAIN
       orchestrator with sub-agents, CLI, and ranking. See
       :doc:`cross-cutting/features/sain`.

   SchemaAgent
       Class type that defines an LLM-callable JSON-schema-validated
       tool. Pattern: ``class FooSchemaAgent : SchemaAgent<FooArgs, FooResponse>``.

   SignalFx
       Primary metrics backend (used via Micrometer).

   SLAuth
       **Service-to-service Lightweight Auth**. Egress token system
       for outbound HTTP calls from convoai. Sidecar at ``platform-slauth-1``.

   SLI / SLO
       **Service Level Indicator** / **Service Level Objective**.
       Reliability targets.

   SSE
       **Server-Sent Events**. HTTP-based streaming protocol used
       for streaming chat responses.

   Statsig
       Feature flag service used by Atlassian. Convoai integrates
       via Kotlin enum wrappers like ``JsmFeatureFlags``.

   Switcheroo
       Atlassian's internal feature flag rollout management tool.

   TAP
       **Targeting and Personalization** — Atlassian's audience
       targeting platform.

   TCS
       **Tenant Context Service**. Sidecar service that resolves
       cloudId → tenant metadata (org ID, region, settings). Critical
       for tenant-isolation. See :doc:`cross-cutting/02-tenant-isolation`.

   Tecton
       Feature store integration; used for user-document features
       and project features.

   Teamserve
       Internal Atlassian LLM model routing service. gRPC + embeddings.

   TOC
       **Table of Contents**. The toctree directive in Sphinx
       (used throughout this docs library).

   TWG
       **Teamwork Graph**. Cross-product graph of work entities
       (issues, pages, PRs, projects, goals).

   Twilio
       Telephony provider used for CSM Voice integration. See
       :doc:`cross-cutting/features/csm-voice`.

   YubiKey
       Hardware security key used for git push authentication
       to bitbucket.org via PKCS#11 (per developer SSH config).

   convoai
       Shorthand for ``conversational-ai-platform``, the codebase
       this documentation describes.


==========================================
Round-3 Glossary Additions
==========================================

* **TP** — TurboPuffer; Atlassian's vector database/search service
  used for procedural memory storage. Naming pattern: ``TPMetadata``,
  ``TPPartitionKey``, ``TPUpsertRequest``, ``TurboPufferService``.
  See :doc:`business/05-open-questions-resolved` §11.1.
* **ERS** — Entity Relationship Store; Atlassian's wrapper around
  DynamoDB used for conversation history AND agent definitions.
  Subject to DynamoDB's 256KB per-item limit. See
  :doc:`business/05-open-questions-resolved` §11.2.
* **ASSP** — Async Service Scaling Protocol; Marathon's backend
  protocol for tool execution. Gated by
  ``ROVO_MARATHON_USE_ASSP`` feature flag.

* **HO** — HybridOrchestrator; Rovo's primary orchestrator type for
  most contexts. See :doc:`cross-cutting/features/orchestrator-selection`.
* **LH** — LongHorizon; alternative orchestrator type, selected via
  experiment. See :doc:`cross-cutting/features/orchestrator-selection`.
* **TD** — Transition Delay; orchestrator behavior modifier (e.g.,
  ``lh_implicit_td`` variant)
* **TTFB** — Time To First Byte; latency optimization target for LH
  (``LH_TTFB_OPTIMIZATION_EXP``)
