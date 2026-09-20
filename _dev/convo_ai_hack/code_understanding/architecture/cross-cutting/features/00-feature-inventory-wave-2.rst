.. _features-wave-2:

==================================================================
Feature Inventory — Wave 2 (additional features discovered)
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Scope: Features beyond the 11 already inventoried

.. contents:: On this page
   :local:
   :depth: 2

Why this exists
==================

The original feature inventory (``00-feature-inventory.rst``)
catalogued the obvious user-facing features. Several substantial
features hide behind less obvious naming or live in less obvious
locations. This wave-2 inventory identifies them.

**Already inventoried** (do not appear below):

* Marathon orchestrator
* SAIN family
* MCP system
* Rovo Plugin system
* AIFC
* AgentStudio
* Deep Research
* Rovo Insights
* Chat Streaming
* Agent Framework (just added)
* JQL SchemaAgent audit (cleanup report)

Module-level scale baseline
==============================

For context, here are the actual module sizes (verified by
``find ... -exec cat | wc -l``) so you can calibrate which features
matter most:

.. list-table::
   :header-rows: 1
   :widths: 40 16 14 30

   * - Module
     - Main LoC
     - Files
     - Comment
   * - **product/rovo**
     - **544,435**
     - 3,794
     - The mothership. ~95% of the feature surface.
   * - **product/aifeature**
     - 74,461
     - 792
     - AIFC features expanded across product surfaces
   * - **product/jsm**
     - 69,395
     - 351
     - Jira Service Management agents (massive)
   * - **product/csm**
     - 64,298
     - 544
     - Customer Support Management agents
   * - **product/confluence**
     - 27,679
     - 144
     - Confluence-specific agent surface
   * - **product/agentstudio**
     - 16,602
     - 84
     - Build-an-agent platform
   * - **product/agent-framework**
     - 10,047
     - 47
     - Stratus minion framework
   * - **product/jira**
     - 9,545
     - 75
     - Jira-specific agent surface
   * - **product/atlassianstudio**
     - 4,839
     - 14
     - AtlassianStudio (?) — small, possibly emerging surface
   * - **product/adk**
     - 4,259
     - 68
     - Agent Development Kit
   * - **product/loom**
     - 3,874
     - 39
     - Loom integration
   * - **product/chat-common**
     - 1,276
     - 8
     - Shared chat utilities
   * - **product/jpd**
     - 242
     - 6
     - Jira Product Discovery (small)

The newly-discovered features
================================

Triage scoring legend:
   :V: User-visibility (1-5; 5 = explicit user surface)
   :L: LoC complexity (1-5; 5 = huge ~10K+)
   :C: Cross-cutting nature (1-5; 5 = many modules)
   :D: Documentation gap (1-5; 5 = essentially unknown)
   :S: Strategic importance (1-5; 5 = product-critical)

   Total = 5-25; recommend deep-dive for any score ≥18

Lumina — lightweight classifier sub-agent system
=================================================

**🟢 VERIFIED EXISTS** — 10+ files in ``rovo-impl/.../agent/lumina/``

.. list-table::
   :widths: 30 70

   * - **What it is**
     - A lightweight LLM-based classifier and sub-agent for
       routing/decision-making within agent flows. Used by MCP's
       ``ShouldUseLuminaToAnswerTool`` to decide whether Lumina
       should answer directly vs delegating to heavier orchestrator.
       Has its own answer-generation path with citation support.
   * - **Where**
     - ``rovo-impl/.../agent/lumina/`` (10+ files)
   * - **Key files**
     - * ``LuminaClassificationService.kt`` — classification engine
       * ``LuminaAnswerAgent.kt`` — the answer sub-agent
       * ``LuminaAnswerAgentHelper.kt`` — answer-formatting helpers
       * ``LuminaAgentSystemPromptTemplateGenerator.kt`` — prompt assembly
       * ``LuminaSubAgentHandler.kt`` — sub-agent dispatch
       * ``LuminaTagStreamParser.kt`` — streaming output parsing with tag awareness
       * ``LuminaStreamMessageBufferWithCitation.kt`` — citation-aware stream buffer
       * ``LuminaConfigService.kt`` + ``LuminaConfig.kt`` — config
       * ``LuminaAgentFeatureFlags.kt`` — FF gates (in rovo-api)
   * - **FF gates**
     - ``LuminaAgentFeatureFlags`` — exists; multiple flags
   * - **Triage**
     - V=4, L=2, C=3, D=5, S=4 → **Total: 18 → DEEP-DIVE WORTHWHILE**
   * - **Hypothesis**
     - Lumina is the "fast path" for queries that don't need full
       Marathon/SAIN orchestration. Likely powers single-turn
       general-knowledge answers with optional citation. Convergence
       point: SIMPLE classifier in SAIN may already use Lumina or
       be parallel to it.

Tecton — ML feature store integration
========================================

**🟢 VERIFIED EXISTS** — 10+ files in ``platform/client/.../tecton/``

.. list-table::
   :widths: 30 70

   * - **What it is**
     - Integration with Tecton (a Databricks-acquired ML feature
       store). Provides per-(user, agent, project) ML features for
       proactive AI suggestions and personalization.
   * - **Where**
     - ``platform/client/client-api`` + ``client-impl`` ``/.../tecton/``
   * - **Key files**
     - * ``TectonConfiguration.kt`` — Spring config
       * ``TectonFeatureServiceClientCacheImpl.kt`` — cached client (likely Caffeine-backed)
       * ``user/UserDocumentClientImpl.kt`` — per-user document features
       * ``user/UserProjectFeaturesClientImpl.kt`` — per-(user, project) features
       * ``agent/AgentFeaturesClientImpl.kt`` — per-agent features
       * ``jira/JiraIssueUpdatesFeaturesClientImpl.kt`` — per-Jira-issue features
       * ``jira/ProactiveAIWBFeaturesClientImpl.kt`` — **proactive AI Whiteboard features** (suggests AI-suggested whiteboard ideas)
   * - **Triage**
     - V=2 (backend infra), L=2, C=3, D=5, S=4 → **Total: 16**
   * - **Hypothesis**
     - Tecton powers the "proactive AI" surface — those moments where
       Rovo offers an unsolicited suggestion ("Want to try X?"). The
       presence of "ProactiveAIWB" (Whiteboard) suggests a specific
       proactive surface for AI-on-whiteboards. Worth a focused doc.

Memory / Personalization subsystem
=====================================

**🟢 VERIFIED EXISTS** — 109 files matching ``*memor*`` or ``/memory/``

.. list-table::
   :widths: 30 70

   * - **What it is**
     - Cross-conversation memory: stores per-(user, agent) facts
       so the agent remembers preferences, relationships, and prior
       interactions. Visible in the ``RovoChatV1Controller`` via
       ``GET /memories/agent/{agentId}`` endpoint.
   * - **Where**
     - 109 files across rovo-impl + likely platform/conversation
   * - **Triage**
     - V=4 (user-visible memory inspection), L=4 (109 files = ~10K+ LoC), C=4, D=5, S=5 → **Total: 22 → STRONG DEEP-DIVE CANDIDATE**
   * - **Hypothesis**
     - Major user-facing capability. Likely composed of: memory
       extraction (extracting facts during conversation), memory
       storage (per-(user, agent)), memory retrieval (query at
       request time), memory eviction, memory inspection UI backing.

CSM Voice — voice-mode customer support
=========================================

**🟢 VERIFIED EXISTS** — Multiple files in ``csm-impl/.../service/voice/``
+ platform-tier audio service

.. list-table::
   :widths: 30 70

   * - **What it is**
     - Voice-based AI agent for Customer Support Management. Caller
       speaks → STT → AI agent processes → TTS → speech response.
       Implements voice ID, voice agent resolution, and voice-mode
       chat session.
   * - **Where**
     - * ``product/csm/csm-impl/service/voice/`` —
         VoiceAiService, VoiceAgentResolver, VoiceCallerUser,
         VoiceAIConfig
       * ``product/csm/csm-api/api/voice/VoiceMessage.kt`` — DTO
       * ``platform/service/.../audio/`` — TextToSpeechProvider,
         TextToSpeechService, SpeechToTextRequest
   * - **Triage**
     - V=5 (explicit user surface), L=3, C=3, D=5, S=5 → **Total: 21 → DEEP-DIVE CANDIDATE**
   * - **Hypothesis**
     - Powers Atlassian's CSM voice channel. Likely integrates with
       phone systems, supports human-handoff fallback, and maintains
       voice-specific session state (callerId, hold-music, IVR-style
       prompts).

CSM and JSM agent platforms
==============================

**🟢 VERIFIED EXISTS** — Massive: CSM=64K LoC/544 files, JSM=69K LoC/351 files

.. list-table::
   :widths: 30 70

   * - **What it is**
     - Per-product specialization of Rovo for Customer Support
       Management (CSM) and Jira Service Management (JSM). Each has
       its own GraphQL controllers, REST controllers, agent
       definitions, scenarios, knowledge integrations, and workflow.
   * - **Where**
     - * ``product/csm/csm-impl/`` — 64,298 LoC, 544 files
       * ``product/jsm/jsm-impl/`` — 69,395 LoC, 351 files
   * - **Triage**
     - V=5, L=5 (HUGE), C=4, D=5, S=5 → **Total: 24 → MULTIPLE DEEP-DIVES NEEDED**
   * - **Hypothesis**
     - Each is a feature-platform of comparable size to AIFC or
       AgentStudio. Each likely has 10-20 distinct user-facing
       sub-features. Should be deep-dived module-by-module.

AIFEATURE — the "AI in product" cross-cutting infrastructure
==============================================================

**🟢 VERIFIED EXISTS** — 74,461 LoC, 792 files (the second-largest module
after rovo-impl)

.. list-table::
   :widths: 30 70

   * - **What it is**
     - Cross-cutting infrastructure for "AI inside Atlassian products"
       — beyond AIFC. Likely covers: write/refine, summarize, translate,
       AI-in-context, slash-commands, ADF rich-text manipulation, etc.
   * - **Where**
     - ``product/aifeature/`` — 74K LoC across many sub-packages
   * - **Triage**
     - V=5, L=5, C=5 (used by everything), D=5, S=5 → **Total: 25 → MOST URGENT DEEP-DIVE**
   * - **Hypothesis**
     - This is **the largest unaudited module** in the codebase. It
       likely contains the editor-level AI surface (write/refine,
       slash commands, smart suggestions) that's distinct from
       AIFC's "create new content from prompt" pattern. Probably has
       30+ sub-features. Worth multiple deep-dives.

Agent Versioning
==================

**🟢 VERIFIED EXISTS** — 3 modules: ``platform/agent-version/agent-version-{api,spi,impl}``

.. list-table::
   :widths: 30 70

   * - **What it is**
     - Per-agent version management. Tracks agent definitions across
       versions, enables A/B testing variants, supports rollback, and
       provides historical query.
   * - **Where**
     - ``platform/agent-version/`` (3 sub-modules)
   * - **Triage**
     - V=2 (backend), L=3, C=3, D=4, S=3 → **Total: 15 → moderate priority**
   * - **Hypothesis**
     - Used by AgentStudio for the agent lifecycle (DRAFT → PUBLISHED
       → ARCHIVED). Provides the "diff" view of agent changes over
       time. Likely powers rollback if a published agent regresses.

Knowledge / Knowledge Gap
============================

**🟢 VERIFIED EXISTS** — ``platform/knowledge/`` + ``platform/knowledge-gap/``

.. list-table::
   :widths: 30 70

   * - **What it is**
     - Knowledge sources system — attaches Confluence pages,
       databases, files, etc. as "knowledge" an agent can reference.
       Knowledge-gap detects when an agent encounters a question it
       can't answer well, surfaces "missing knowledge" suggestions.
   * - **Where**
     - * ``platform/knowledge/`` (api/spi/impl)
       * ``platform/knowledge-gap/`` (api/spi/impl) — exposed via
         ``AgentStudioKnowledgeGapQueryController`` + ``MutationController``
   * - **Triage**
     - V=4 (user-visible knowledge attachments), L=3, C=4, D=4, S=4 → **Total: 19 → DEEP-DIVE WORTHWHILE**
   * - **Hypothesis**
     - Major AgentStudio feature. Knowledge-gap likely uses LLM-as-judge
       to identify "the agent kept saying I don't know" patterns and
       suggests knowledge to add.

Evaluation Framework
======================

**🟢 VERIFIED EXISTS** — ``platform/evaluation/`` (api/spi/impl)

.. list-table::
   :widths: 30 70

   * - **What it is**
     - Cross-cutting evaluation framework. Used by AgentStudio's batch
       evaluation, Deep Research's ablation framework, conversation
       review, LLM-judge.
   * - **Where**
     - ``platform/evaluation/`` (api/spi/impl)
   * - **Triage**
     - V=2, L=3, C=4, D=4, S=4 → **Total: 17 → moderate**
   * - **Hypothesis**
     - Provides shared abstractions for "did this agent do well?"
       evaluation. Pluggable judge backends. Used by multiple consumers.

Widget System
===============

**🟢 VERIFIED EXISTS** — ``platform/widget/`` (api/spi)

.. list-table::
   :widths: 30 70

   * - **What it is**
     - Renderable UI widgets that agents can produce as part of their
       responses (charts, tables, interactive elements). Distinct from
       Maui's full mini-apps — widgets are simpler embedded components.
   * - **Where**
     - ``platform/widget/`` + AgentStudio's ``AgentStudioWidgetQueryController`` + ``MutationController``
   * - **Triage**
     - V=4 (user-visible widgets), L=2, C=3, D=4, S=3 → **Total: 16**
   * - **Hypothesis**
     - The ``AGENTIC_UI`` stream message type in ``RovoChatV1StreamMessageType``
       likely carries widget content. Worth correlating.

ADK — Agent Development Kit
==============================

**🟢 VERIFIED EXISTS** — ``product/adk/`` 4,259 LoC, 68 files

.. list-table::
   :widths: 30 70

   * - **What it is**
     - Agent Development Kit — likely the **public/external SDK**
       that customers/partners use to build custom Rovo agents
       outside AgentStudio's UI.
   * - **Where**
     - ``product/adk/``
   * - **Triage**
     - V=2 (developer-facing, not end-user), L=2, C=2, D=5, S=4 → **Total: 15**
   * - **Hypothesis**
     - This is the SDK external developers consume. Critical for
       ecosystem strategy but lower-priority for internal codebase
       deep-dive.

Loom integration
==================

**🟢 VERIFIED EXISTS** — ``product/loom/`` 3,874 LoC, 39 files

.. list-table::
   :widths: 30 70

   * - **What it is**
     - Loom (video) integration. Likely supports: extracting transcripts
       from Loom videos for AI context, creating Loom videos from AI
       summaries, embedding video references in AI responses.
   * - **Where**
     - ``product/loom/``
   * - **Triage**
     - V=4, L=2, C=2, D=4, S=3 → **Total: 15**
   * - **Hypothesis**
     - Video-AI bridge. Worth a brief deep-dive but not urgent.

AtlassianStudio
=================

**🟢 VERIFIED EXISTS** — ``product/atlassianstudio/`` 4,839 LoC, 14 files

.. list-table::
   :widths: 30 70

   * - **What it is**
     - Likely the AtlassianStudio (Atlassian's IDE-style admin interface
       for org management) AI integration. Uses ``AgentChatExecutor``
       which delegates to Marathon (verified earlier).
   * - **Where**
     - ``product/atlassianstudio/``
   * - **Triage**
     - V=3, L=2, C=2, D=5, S=3 → **Total: 15**
   * - **Hypothesis**
     - Small but explicit surface. Probably worth a 1-page brief
       (not full deep-dive).

Conversation memory + history (additional)
==============================================

**Likely exists but not specifically inventoried** — ``platform/conversation/``

* ``ConversationHistoryItem`` confirmed (used in ``RovoChatV1Controller``)
* ``ConversationFileUploadIllegalContentException`` confirmed
* "ConversationManager" backend referenced in Marathon doc as UNRESOLVED

Worth a brief investigation: where does conversation persistence live?
What's the storage backend? What's the retention policy?

Triage summary — recommended next deep-dives
================================================

In priority order (deep-dive any score ≥18):

.. list-table::
   :header-rows: 1
   :widths: 24 12 64

   * - Feature
     - Score
     - Reason
   * - **AIFEATURE module**
     - **25**
     - **Most urgent**. Largest unaudited module (74K LoC); likely contains 30+ sub-features powering the editor-level AI surface
   * - **CSM/JSM agent platforms**
     - **24**
     - Two huge product-tier modules; each deserves dedicated deep-dive
   * - **Memory subsystem**
     - **22**
     - 109 files; user-visible (memories endpoint exposed); cross-conversation personalization
   * - **CSM Voice**
     - **21**
     - Explicit user surface (voice mode); high strategic importance
   * - **Knowledge / Knowledge Gap**
     - **19**
     - User-visible AgentStudio feature; LLM-judge integration
   * - **Lumina**
     - **18**
     - Lightweight classifier; convergence with SAIN's SIMPLE classifier
   * - **Evaluation Framework**
     - 17
     - Cross-cutting; used by multiple consumers
   * - **Tecton (ML features)**
     - 16
     - Backend infra; powers proactive AI
   * - **Widget System**
     - 16
     - User-visible; correlate with AGENTIC_UI envelope type

Things ruled OUT
==================

NOT separate features (just code-organization with no user-facing distinction):

* **chat-common** (1,276 LoC) — utility code; not a feature
* **shared-features** (16 LoC) — empty placeholder
* **jpd** (242 LoC) — too small to be a feature; likely Jira Product Discovery shim
* **Workplace Insights** — could not find a directly-named module; may
  be implemented as part of Rovo Insights with a different label

Cross-references with existing inventory
============================================

This wave-2 inventory **complements** the original feature inventory.
Update the master inventory to reference these features once they're
deep-dived.

