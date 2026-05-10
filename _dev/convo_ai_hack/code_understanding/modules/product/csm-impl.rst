.. _mod-csm-impl:

==============================================
``product/csm/csm-impl``
==============================================

:Tier: product
:Path: ``modules/product/csm/csm-impl``
:Size: ~62,796 source lines :sup:`(verified)`
:Importance: **Tier 1 — large product**

CSM (Customer Service Management) — JSM's external-customer-facing variant. Hosts the CSM agent orchestrator, workflow, internal+external search, voice AI, and chat surface.

Top files :sup:`(verified by line-count)`
===========================================

.. list-table::
   :header-rows: 1
   :widths: 65 15 20

   * - File
     - Lines
     - Subsystem
   * - ``orchestrator/CsmAgentOrchestratorImpl.kt``
     - 1,777
     - CSM agent orchestration
   * - ``workflow/CsmWorkflow.kt``
     - 1,365
     - CSM workflow definition
   * - ``service/search/internal/CsmInternalSearchServiceImpl.kt``
     - 1,217
     - Internal search (KB, runbooks)
   * - ``trace/CSMArizeSpanWriter.kt``
     - 1,023
     - Arize span emission (LLM observability)
   * - ``service/search/external/CsmSearchServiceImpl.kt``
     - 911
     - External search
   * - ``service/voice/VoiceAiService.kt``
     - 846
     - Voice AI (audio-mode chat)
   * - ``service/chat/CsmChatServiceV2.kt``
     - 836
     - Chat surface v2

Subsystems
============

1. **Orchestrator** (``orchestrator/CsmAgentOrchestratorImpl.kt``) — central coordinator for CSM agent flows.
2. **Workflow** (``workflow/CsmWorkflow.kt``) — encodes the CSM-specific multi-step agentic workflow.
3. **Internal vs external search** (``service/search/{internal,external}/``) — internal searches knowledge bases and runbooks; external surfaces customer-facing search.
4. **Voice AI** (``service/voice/VoiceAiService.kt``) — handles audio-input + audio-output conversational flows.
5. **Chat v2** (``service/chat/CsmChatServiceV2.kt``) — newer chat implementation, replacing v1.
6. **Arize observability** (``trace/CSMArizeSpanWriter.kt``) — emits spans to Arize (LLM observability platform) for trace analysis.

Skills as markdown :sup:`(verified earlier in cross-cutting/08-agent-runtime)`
================================================================================

CSM is the canonical example of the **markdown-skill pattern**:

* ``src/main/resources/skills/email-suppression-skill.md``
* ``src/main/resources/skills/migration-analysis-skill.md``
* (others — refund requests, password reset, etc.)

These are loaded by the ADK at runtime and exposed as agent capabilities. Editing a skill markdown is a code change (requires release), but it's NOT a Kotlin/Java change.

Patterns specific to csm-impl
================================

1. **Markdown skills.** First-class pattern in CSM; skills are markdown, not code.
2. **Voice AI as a separate service.** Voice paths don't share code with chat paths beyond high-level orchestration.
3. **Arize spans.** CSM has its own observability pipeline alongside the standard Atlassian one — likely for ML team visibility.
4. **External vs internal search separation.** Different security model, different data sources, different rate limits.

What you would change here
============================

* **Add a new agent skill** → new markdown file in ``src/main/resources/skills/``
* **Modify CSM workflow** → ``workflow/CsmWorkflow.kt``
* **Add a voice flow** → ``service/voice/``
* **Adjust Arize span schema** → ``trace/CSMArizeSpanWriter.kt``

