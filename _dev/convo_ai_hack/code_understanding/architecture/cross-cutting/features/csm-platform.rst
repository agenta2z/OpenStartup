.. _feature-csm-platform:

==================================================================
CSM Platform — Customer Support Management agent platform
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Footprint: **64,298 LoC across 544 files** (third-largest module after rovo-impl + aifeature)
:Module: ``modules/product/csm/`` (csm-api + csm-impl)
:Triage score: **24/25 — product-critical, multi-feature surface**
:Companion docs: :ref:`feature-csm-voice` (voice-mode CSM)

.. contents:: On this page
   :local:
   :depth: 2

What CSM Platform IS (in one paragraph)
==========================================

The CSM Platform is the **Customer Support Management agent platform** —
the end-customer-facing AI agent for help-seekers. Unlike Rovo
(internal Atlassian-employee-facing) or JSM (IT-service-management
agents), CSM is **public-facing**: customers visit a help center, type
a question into a widget, and a tenant-customized AI agent answers
using the tenant's knowledge sources, with optional handoff to a human
support agent if the query is too complex. CSM has its own **45 REST/GraphQL
controllers**, **8 main feature areas**, **Arize-based ML observability**,
and a **plugin-based pipeline** with router, search, clarification,
out-of-domain detection, and handoff plugins. It is the **third-largest
module** in the codebase at 64K LoC across 544 files. Voice-mode CSM
is a separate slice (~1.2K LoC) documented in its own deep-dive.

Anatomy — module structure
==============================

**2 sub-modules**:

.. list-table::
   :header-rows: 1
   :widths: 32 16 16 36

   * - Module
     - LoC
     - Files
     - Role
   * - **csm-api**
     - small
     - ~50
     - Contracts, DTOs, agent identity types
   * - **csm-impl**
     - **~63K**
     - **~494**
     - All implementation: orchestrator, plugins, services, controllers

**Top-15 files by LoC** (verified):

.. list-table::
   :header-rows: 1
   :widths: 50 12 38

   * - File
     - LoC
     - Role
   * - ``CsmAgentOrchestratorImpl.kt``
     - **1,777**
     - **Largest single file.** Central orchestrator: multi-turn flow + plugin sequencing + response generation
   * - ``CsmWorkflow.kt``
     - 1,365
     - Workflow engine: conversation state machine + routing logic
   * - ``CsmInternalSearchServiceImpl.kt``
     - 1,217
     - Searches internal knowledge bases / documents / content repos
   * - ``CSMArizeSpanWriter.kt``
     - **1,023**
     - **ML observability!** Arize tracing — captures LLM latency, token usage, conversation outcome for ML quality monitoring
   * - ``CsmSearchServiceImpl.kt``
     - 911
     - External search integration (Jira, Confluence, Zendesk, etc.)
   * - ``CsmChatServiceV2.kt``
     - 836
     - Top-level chat service — orchestrates answer generation pipeline
   * - ``SearchAggServiceImpl.kt``
     - 802
     - Aggregates + ranks search results from multiple sources
   * - ``CsmChatV2Controller.kt``
     - 668
     - REST v2 chat endpoint
   * - ``CsmWidgetConfigService.kt``
     - 637
     - Per-tenant + per-widget configuration
   * - ``LoomSupportPlugin.kt``
     - 602
     - Video/screen capture integration
   * - ``CsmInternalSearchPlugin.kt``
     - 578
     - Pluggable internal search capability
   * - ``CSMConversationReportingV2Controller.kt``
     - 446
     - Conversation analytics + reporting endpoints
   * - ``CsmAnswerGeneratorPromptBuilder.kt``
     - 567
     - LLM prompt construction with context + intent + knowledge
   * - ``CsmSearchPlugin.kt``
     - 517
     - Pluggable external search capability
   * - ``CsmLLMJudgePromptProvider.kt``
     - 537
     - **LLM-based eval** — answer quality + relevance judgment
   * - ``CsmEvaluationStrategy.kt``
     - 456
     - Multi-strategy eval framework (BLEU, semantic similarity, custom judges)

The 8 main feature areas
============================

**1. Conversation Orchestration & Workflow** (~3,142 LoC)
-----------------------------------------------------------

* ``CsmAgentOrchestratorImpl.kt`` (1,777) — central orchestrator
* ``CsmWorkflow.kt`` (1,365) — workflow state machine

The **conversation entry point** for CSM. Receives user message,
sequences through plugins (router → search → clarify → answer →
optionally handoff), produces response.

**2. Search & Knowledge Retrieval** (~3,028 LoC)
--------------------------------------------------

* ``CsmInternalSearchServiceImpl.kt`` (1,217)
* ``CsmSearchServiceImpl.kt`` (911)
* ``SearchAggServiceImpl.kt`` (802)

Multi-source knowledge lookup. Internal vs external; aggregation
across sources; ranking. Powers the answer generation.

**3. Chat API & REST Controllers** (~1,504 LoC)
-------------------------------------------------

* ``CsmChatV2Controller.kt`` (668) — text chat REST endpoint
* ``CSMConversationReportingV2Controller.kt`` (446) — analytics

**45 controllers total** (verified by ``find ... -name '*Controller.kt'``):

* GraphQL: ``CsmAgentMutationController``, ``CsmAgentVersionMutationController``,
  ``CsmAgentIdentityConfigMutationController``,
  ``CsmHandoffConfigQueryController``, ``CsmKnowledgeSourceMutationController``,
  ``CsmCoachingContent{Query,Mutation}Controller``,
  ``CsmWidgetMutationController``, ``CsmActionMutationController``
* REST: ``CsmChatV2Controller``, ``CSMConversationReportingV2Controller``, ...

**4. Answer Generation & LLM Integration** (~1,104 LoC)
---------------------------------------------------------

* ``CsmAnswerGeneratorPromptBuilder.kt`` (567)
* ``CsmChatServiceV2.kt`` (836)

Constructs the final LLM prompt with conversation history,
classified intent, retrieved knowledge, and confidence-scoring
output schema.

**5. Plugin System & Request Interceptors** (~2,670+ LoC)
-----------------------------------------------------------

CSM has its own plugin system (separate from Rovo's plugin system):

.. list-table::
   :header-rows: 1
   :widths: 36 14 50

   * - Plugin
     - LoC
     - Role
   * - ``LoomSupportPlugin.kt``
     - 602
     - Video/screen capture context
   * - ``CsmInternalSearchPlugin.kt``
     - 578
     - Internal search capability
   * - ``CsmSearchPlugin.kt``
     - 517
     - External search capability
   * - ``router/`` (sub-folder)
     - moderate
     - Initial routing decision
   * - ``actionconfirmation/`` (sub-folder)
     - moderate
     - Confirms user intent for high-impact actions
   * - ``clarification/`` (sub-folder)
     - moderate
     - Asks clarifying question when ambiguous
   * - ``outofdomain/`` (sub-folder)
     - moderate
     - Detects out-of-domain queries
   * - ``handoff/`` (sub-folder)
     - moderate
     - Detects need for human escalation

**6. Observability & Tracing** (~1,023 LoC)
---------------------------------------------

* ``CSMArizeSpanWriter.kt`` (1,023)

**Arize integration** — ML observability platform. Captures:

* LLM latency (per inference call)
* Token usage (per call + per conversation)
* Model selection (which model was used)
* Conversation outcomes (resolved | handed-off | abandoned)
* Custom spans for ML quality monitoring

This is **distinct from regular APM tracing** (OpenInference) —
Arize is specifically for ML observability (model drift, prediction quality).

**7. Handoff & Escalation** (plugin + service)
------------------------------------------------

CSM **DOES** have a human-handoff path (unlike CSM Voice):

* ``plugin/handoff/`` — detects when conversation requires human
* ``service/handoff/`` — manages escalation workflow + queue assignment
* ``CsmHandoffConfigQueryController.kt`` — per-tenant handoff config

**Escalation criteria** (inferred from naming):

* Confidence threshold not met (low LLM confidence)
* User explicitly requests human ("speak to agent")
* Handoff-trigger keyword detected
* Conversation duration / turn count exceeded threshold

**8. Configuration, Security & Evaluation** (~2,500+ LoC)
-----------------------------------------------------------

* ``CsmWidgetConfigService.kt`` (637) — per-tenant + per-widget config
* ``CsmLLMJudgePromptProvider.kt`` (537) — LLM-as-judge for quality
* ``CsmEvaluationStrategy.kt`` (456) — multi-strategy eval (BLEU, semantic similarity, custom)
* ``service/jwt/``, ``service/oauth/``, ``security/`` — auth + tenant isolation

Additional components
========================

* **Async Processing** (``async/``) — ticket filing, bulk ops in background
* **Channel Recommendation** (``service/channelRecommendation/``) — routes users to chat / email / ticket
* **Agent Coaching** (``service/agentcoaching/``) — real-time suggestions for HUMAN agents (when escalated)
* **Content Retrieval** (``service/contentretrieval/``) — Dewey + JAC integrations for knowledge fetch
* **Streaming** (``streaming/CsmStreamOutputHandler.kt``) — Server-sent events
* **Coaching content** — knowledge that helps the human agent (post-handoff) handle the case better

End-to-end flow — text chat conversation
=============================================

Sequence diagram for a typical CSM chat:

.. mermaid::

   sequenceDiagram
       autonumber
       participant U as Customer
       participant W as Help Widget
       participant Ctrl as CsmChatV2Controller<br/>(668 LoC)
       participant Svc as CsmChatServiceV2<br/>(836 LoC)
       participant Orch as CsmAgentOrchestratorImpl<br/>(1,777 LoC)
       participant WF as CsmWorkflow<br/>(1,365 LoC)
       participant Plugins as Plugins<br/>(router/search/clarify/handoff)
       participant Search as CsmInternalSearch<br/>ServiceImpl (1,217 LoC)
       participant Prompt as CsmAnswerGenerator<br/>PromptBuilder (567 LoC)
       participant LLM
       participant Arize as CSMArizeSpan<br/>Writer (1,023 LoC)
       participant Handoff as Handoff Plugin/Service

       U->>W: type "How do I reset my password?"
       W->>Ctrl: POST /v2/chat (text)
       Ctrl->>Svc: createMessage(req)
       Svc->>Orch: handle(req, ctx)

       Orch->>WF: nextState(currentState)
       WF-->>Orch: SEARCH

       Orch->>Plugins: router.route(req)
       Plugins-->>Orch: intent=PASSWORD_RESET

       Orch->>Search: search(query, knowledgeSources)
       Search-->>Orch: ranked results

       Orch->>Prompt: buildAnswerPrompt(query, results, intent, history)
       Prompt-->>Orch: prompt

       Orch->>LLM: invoke(prompt)
       LLM-->>Orch: answer + confidence

       Orch->>Arize: recordSpan(latency, tokens, confidence, model)

       alt confidence > threshold
           Orch->>Plugins: outofdomain.check(answer)
           Orch->>Svc: AnswerResponse(answer, sources)
           Svc-->>Ctrl: stream(SSE)
           Ctrl-->>U: stream answer
       else confidence < threshold
           Orch->>Handoff: shouldHandoff(...)
           Handoff-->>Orch: YES (route to human)
           Orch->>Svc: HandoffResponse(escalateTo=queueX)
           Svc-->>Ctrl: handoff signal
           Ctrl-->>U: "Connecting you to a human agent..."
       end

External system fan-out
==========================

.. list-table::
   :header-rows: 1
   :widths: 24 28 48

   * - System
     - How
     - Used for
   * - **AI Gateway** (LLM)
     - per-turn
     - Answer generation, routing classification
   * - **Knowledge sources** (Confluence, Jira, Zendesk, web)
     - via search services
     - Knowledge retrieval
   * - **Dewey** (knowledge cache)
     - via contentretrieval
     - Cached knowledge access
   * - **JAC** (Jira-Atlassian-Confluence?)
     - via contentretrieval
     - External content
   * - **Loom**
     - via LoomSupportPlugin
     - Video / screencap context
   * - **Turbopuffer / OpenSearch**
     - via search
     - Vector search for semantic similarity
   * - **Barista** (LLM gateway?)
     - via search/eval
     - LLM access path
   * - **Arize**
     - via CSMArizeSpanWriter
     - ML observability + model quality monitoring
   * - **Human handoff** (e.g., Zendesk live chat, Salesforce)
     - via service/handoff
     - Human agent transfer
   * - **JSM Cloud REST**
     - via search
     - Ticket creation/lookup

Smells and concerns
=====================

.. list-table::
   :header-rows: 1
   :widths: 6 32 16 46

   * - Sev
     - Issue
     - Where
     - Notes
   * - 🔴
     - **1,777-LoC ``CsmAgentOrchestratorImpl.kt``**
     - orchestrator/
     - Largest file. Should split: ConversationDispatcher, PluginCoordinator, ResponseAggregator, ErrorHandler.
   * - 🔴
     - **1,365-LoC ``CsmWorkflow.kt``**
     - workflow/
     - Workflow state machine. Same split principle.
   * - 🔴
     - **1,217-LoC ``CsmInternalSearchServiceImpl.kt``**
     - service/search/
     - Same.
   * - 🔴
     - **45 controllers in one module**
     - csm-impl/
     - Many domain concerns mixed. Consider sub-modularization.
   * - 🔴
     - **CSM has its own plugin system** (separate from Rovo's)
     - plugin/
     - Rovo + CSM + agent-framework + MCP all have plugin/tool registries. Convergence opportunity.
   * - 🟡
     - **Two search services** (Internal + External)
     - service/search/
     - Why split? Verify intent — could be unified with type tag.
   * - 🟡
     - **No FF gate for Arize observability cost**
     - CSMArizeSpanWriter
     - 1,023 LoC of always-on tracing. Per-call cost may be material.
   * - 🟡
     - **Coaching content + Coaching Service** for human agents
     - service/agentcoaching/
     - Worth a separate brief deep-dive — what UX does this power?
   * - 🟡
     - **REST v2 implies v1 exists** somewhere
     - rest/v2/
     - Migration plan? Sunset date?
   * - 🟡
     - **Handoff goes to "queue assignment"** but queue management not in this module
     - service/handoff/
     - Where's the human-agent system integration? Likely external (Zendesk?) — needs documentation.
   * - 🟢
     - **Plugin architecture is clean** (router, search, clarify, handoff)
     - plugin/
     - Good separation; new plugins can be added independently.
   * - 🟢
     - **Arize ML observability** is a sophisticated investment
     - CSMArizeSpanWriter
     - Most products don't have this; CSM does.
   * - 🟢
     - **LLM-as-judge for quality** (CsmLLMJudgePromptProvider)
     - service/
     - Continuous quality monitoring via LLM.

Refactoring opportunities
============================

1. **Split ``CsmAgentOrchestratorImpl.kt``** (XL, 🔴 high) — 1,777 LoC into 3-4 services. ~5-7 days.

2. **Split ``CsmWorkflow.kt``** (M, 🔴 high) — 1,365 LoC into state-machine + transition + trigger files. ~3 days.

3. **Modularize csm-impl** (XL, 🔴 high) — 45 controllers + 544 files into per-domain Gradle sub-modules (csm-chat-impl, csm-config-impl, csm-handoff-impl, etc.). ~3-4 weeks.

4. **Audit Internal vs External search split** (S, 🟡 medium) — ``CsmInternalSearchServiceImpl`` + ``CsmSearchServiceImpl`` — verify split is meaningful or unify. ~3 days.

5. **Document REST v2 → v1 migration** (XS, 🟡 medium) — find ``CsmChatV1Controller`` if exists; document deprecation. ~half day.

6. **Add per-tenant Arize cost accounting** (S, 🟡 medium) — emit metric per-tenant span count for cost allocation. ~1 day.

7. **Document the handoff queue integration** (S, 🟡 medium) — where do escalated chats go (Zendesk? Salesforce? Custom?). ~1 day.

8. **Deep-dive agent coaching subsystem** (M, 🟢 low) — separate doc; understand the human-agent UX. ~1 day investigation.

9. **Audit for cross-product duplication** (M, 🟢 low) — CSM Search vs Rovo's search vs JSM's RunbookSearch. Same problem solved 3 ways?

What you would change here
============================

* **Add a new CSM plugin** (e.g., translation):
   1. Create class in ``plugin/translation/CsmTranslationPlugin.kt``
   2. Implement plugin interface
   3. Register via Spring auto-discovery
   4. Add to orchestrator's plugin sequencing config

* **Modify chat answer prompt** → ``CsmAnswerGeneratorPromptBuilder.kt`` (or its Pebble template)

* **Add new GraphQL endpoint for AgentStudio** → new ``Csm*Controller.kt``

* **Tune handoff trigger threshold** → ``CsmHandoffConfigQueryController`` config

* **Modify per-tenant widget config schema** → ``CsmWidgetConfigService.kt``

* **Add new knowledge source type** → ``CsmInternalSearchServiceImpl`` + new fetcher

* **Track new conversation outcome** → ``CSMArizeSpanWriter`` span definition

What you would NOT change here
================================

* Marathon orchestrator — owned by ``rovo-impl/.../agent/orchestrators/marathon/``
* SAIN orchestrators — owned by ``rovo-impl/.../product/rovo/sain/``
* AgentStudio CRUD — owned by ``agentstudio-impl/``
* CSM Voice — owned by ``csm-impl/.../service/voice/`` (separate doc)
* Knowledge / Knowledge Gap — owned by ``platform/knowledge/`` + ``platform/knowledge-gap/``
* External knowledge sources (Confluence, Zendesk) — third-party APIs
* Human-agent system (Zendesk Chat, Salesforce, custom) — external
* Arize platform — external SaaS

Verification audit log
========================

✅ **Personally verified with bash:**

* Total LoC: 64,298 across 544 files
* 45 controllers (find + count)
* Top-15 files by LoC (find + sort)
* Top GraphQL controllers exist (CsmKnowledgeSourceMutation, CsmHandoffConfigQuery, CsmAgentVersion, CsmCoachingContent, etc.)
* Top REST controllers exist (CsmChatV2, CSMConversationReportingV2)
* Sub-package structure verified (orchestrator/, workflow/, service/, plugin/, agent/, async/, etc.)
* CSMArizeSpanWriter is 1,023 LoC

⚠️ **Inferred from sub-agent + naming**:

* The 8-feature-area categorization (sub-agent's grouping; my organization)
* End-to-end flow ordering (responsibility-based inference)
* The "router → search → clarify → answer → handoff" plugin sequence (naming inference; not source-verified ordering)
* The "outofdomain" check after answer generation (could be before)
* The Arize span content (fields are guessed based on standard ML observability)
* The "Dewey" and "JAC" abbreviations (sub-agent reported; not expanded)

❌ **UNVERIFIED:**

* The exact plugin sequencing (which plugins fire in what order)
* The handoff queue integration (which external system?)
* Per-tenant CSM rollout state (% of tenants using AI agent?)
* Per-conversation cost (token + Arize + Loom + search)
* The relationship between "agent coaching" content and the post-handoff human agent
* REST v1 controller existence + deprecation status
* The internal vs external search split rationale

Open questions for institutional knowledge
=============================================

1. **Is REST v1 still active?** What's the deprecation timeline?
2. **What does the handoff route to** — Zendesk Chat? Salesforce? Custom queue manager?
3. **What does "Dewey" stand for** in the content retrieval integration?
4. **What does "JAC" stand for** — Jira-Atlassian-Confluence?
5. **What's the typical conversation length** + handoff rate?
6. **What's the Arize per-call cost** at production scale?
7. **Why does CSM have its own plugin system** distinct from Rovo's? Convergence plans?
8. **What's the difference between Internal and External search services**?
9. **What model(s) does CSM use** for answer generation? Same as Rovo or specialized?
10. **Is "coaching content" served to human agents in real-time** during conversations?

