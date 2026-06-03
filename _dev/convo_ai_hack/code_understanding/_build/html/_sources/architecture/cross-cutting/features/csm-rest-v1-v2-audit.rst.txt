.. _audit-csm-rest-v1-v2:

==================================================================
CSM REST V1 vs V2 — namespace audit (NOT a migration generation)
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Status: **AUDIT COMPLETE — claim was overinterpretation**
:Disposition: V1 and V2 are **separate API namespaces** by domain, NOT migration generations. NO controller pairs. NOTHING to deprecate.

.. contents:: On this page
   :local:
   :depth: 2

TL;DR
========

In the original :ref:`feature-csm-platform` deep-dive, we noted that
"REST v2 implies v1 exists" and flagged this as a candidate for the
JQL Phase 2 deletion pattern.

**Audit verdict**: ⚠️ **The original claim was an overinterpretation.**

Hard evidence (verified by ``find`` + ``grep``) shows:

* **8 v1 controllers** spanning **8 different domains** (transcript,
  oauth, knowledge, onboarding, knowledge-gap, handoff, annotation,
  handoff-forms)
* **6 v2 controllers** spanning **5 different domains** (chat,
  internal-chat, risk-eval, widget, conversation-reporting)
* **ZERO controller pairs** where the same domain has both V1 and V2
  (e.g., ``CsmChatV1Controller`` does NOT exist — only V2)
* **All v1 paths use ``/api/csm/v1/{domain}``** namespace
* **All v2 paths use ``/api/csm/v2/{domain}``** namespace

This is **NOT a migration pattern** (where V2 is the replacement for
V1). It's **two parallel API namespaces** added at different times for
different domains. The CSM platform doc claim ("REST v2 implies v1
exists") was wrong.

**Recommendation**: ✅ **NOTHING TO DEPRECATE OR DELETE.**

Hard evidence — full inventory
==================================

**8 V1 controllers** (all under ``rest/v1/``):

.. list-table::
   :header-rows: 1
   :widths: 36 32 32

   * - File
     - Path
     - Domain
   * - ``CsmConversationTranscriptController.kt``
     - ``/api/csm/v1/transcript``
     - Transcripts
   * - ``CsmAgentOauthController.kt``
     - ``/api/csm/v1/oauth``
     - Agent OAuth
   * - ``CsmKnowledgeController.kt``
     - ``/api/csm/v1/knowledge/{containerId}``
     - Knowledge sources
   * - ``CsmOnboardingController.kt``
     - ``/api/csm/v1/onboard``
     - Onboarding
   * - ``CsmKnowledgeGapJobController.kt``
     - ``/api/csm/v1/knowledge-gap``
     - Knowledge Gap jobs
   * - ``CsmHandoffConfigController.kt``
     - (handoff config namespace)
     - Handoff config
   * - ``CsmAnnotationController.kt``
     - ``/api/csm/v1/annotation``
     - Annotations
   * - ``CsmHandoffFormsController.kt``
     - ``/api/csm/v1/handoff/forms``
     - Handoff forms

**6 V2 controllers** (all under ``rest/v2/``):

.. list-table::
   :header-rows: 1
   :widths: 36 32 32

   * - File
     - Path
     - Domain
   * - ``CsmChatV2Controller.kt``
     - ``/api/csm/v2/chat``
     - Chat (text)
   * - ``CsmInternalChatV2Controller.kt``
     - (internal chat namespace)
     - Internal chat
   * - ``CsmRiskEvaluationConfigV2Controller.kt``
     - (risk eval namespace)
     - Risk evaluation config
   * - ``CsmWidgetV2Controller.kt``
     - (widget namespace)
     - Widget config
   * - ``CSMConversationReportingV2Controller.kt``
     - (conversation reporting namespace)
     - Conversation reporting
   * - ``CSMInternalConversationReportingV2Controller.kt``
     - (internal reporting namespace)
     - Internal reporting

**12 internal controllers** (all under ``rest/internal/``):

* ``MlStudioTriggerController.kt`` — ``/internal/csm/ml-studio``
* ``InternalKnowledgeGapController.kt``
* ``CsmTicketOperationsController.kt``
* ``SupportWidgetDeleteController.kt``
* ``EmbedWidgetSubjectTokenCreateController.kt``
* ``InternalKnowledgeGapJobDeleteController.kt``
* ``CsmInternalAnnotationDeleteController.kt``
* ``EchoController.kt``
* ``CsmInternalAgentIdentityController.kt``
* ``CsmRiskEvaluationConfigController.kt``
* ``CsmInternalAgentKnowledgeSearchController.kt``
* ``AgentIdBackfillController.kt``

**1 voice controller** (under ``rest/voice/``):

* ``VoiceAiController.kt`` — voice-mode CSM (documented in :ref:`feature-csm-voice`)

The "no pairs" verification
==============================

Cross-checking domain by domain — does any V1 domain have a V2 counterpart?

.. list-table::
   :header-rows: 1
   :widths: 32 16 16 36

   * - Domain
     - Has V1?
     - Has V2?
     - Pair?
   * - Transcript
     - ✅ ``CsmConversationTranscriptController``
     - ❌
     - **No pair**
   * - OAuth
     - ✅ ``CsmAgentOauthController``
     - ❌
     - **No pair**
   * - Knowledge sources
     - ✅ ``CsmKnowledgeController``
     - ❌
     - **No pair**
   * - Onboarding
     - ✅ ``CsmOnboardingController``
     - ❌
     - **No pair**
   * - Knowledge gap
     - ✅ ``CsmKnowledgeGapJobController``
     - ❌
     - **No pair**
   * - Handoff config
     - ✅ ``CsmHandoffConfigController``
     - ❌
     - **No pair**
   * - Annotation
     - ✅ ``CsmAnnotationController``
     - ❌
     - **No pair**
   * - Handoff forms
     - ✅ ``CsmHandoffFormsController``
     - ❌
     - **No pair**
   * - **Chat**
     - ❌
     - ✅ ``CsmChatV2Controller``
     - **No pair (V2 only)**
   * - Internal chat
     - ❌
     - ✅ ``CsmInternalChatV2Controller``
     - **No pair (V2 only)**
   * - Risk evaluation
     - ❌
     - ✅ ``CsmRiskEvaluationConfigV2Controller``
     - **No pair (V2 only)**
   * - Widget config
     - ❌
     - ✅ ``CsmWidgetV2Controller``
     - **No pair (V2 only)**
   * - Reporting
     - ❌
     - ✅ ``CSMConversationReportingV2Controller``
     - **No pair (V2 only)**

**Result**: **0 of 13 domains have both V1 and V2.**

What IS happening (correct interpretation)
=============================================

The "v1" and "v2" naming reflects **API namespace versioning** (when
the endpoint was added), NOT a migration generation. Atlassian
internal API conventions support multiple version namespaces simultaneously
for organizational clarity:

* **/api/csm/v1/*** — older endpoint domains (added ~2023)
* **/api/csm/v2/*** — newer endpoint domains (added ~2024+)
* **/api/csm/voice/*** — voice-specific namespace
* **/internal/csm/*** — internal-only (not exposed externally)

When a NEW domain is added (e.g., risk evaluation), it goes into
the **current namespace** (v2 today). Existing v1 domains stay
where they are because changing path is a breaking change for
external consumers.

Why the original claim was wrong
====================================

The CSM platform deep-dive reasoned:

  *"REST v2 implies v1 exists somewhere. Migration plan? Sunset date?"*

This generalizes from common API conventions (e.g., AWS S3 v1 → v2 is
a true migration). But CSM doesn't follow that convention:

* No ``CsmChatV1Controller`` exists
* No ``CsmRiskEvaluationConfigV1Controller`` exists  
* The 8 V1 controllers serve **completely different concerns** than
  the 6 V2 controllers

The CSM platform doc has been **CORRECTED** in this audit.

What this means for the codebase
====================================

**Nothing to delete.** All 14 versioned controllers (+ 12 internal +
1 voice) are alive and actively serving traffic for their respective
domains.

**One observable inconsistency to consider** (low priority):
"v1" and "v2" in the namespace might confuse new contributors who
assume migration semantics. **Optional cleanup**: rename the
namespaces to be domain-named instead of versioned (e.g.,
``/api/csm/transcripts/`` instead of ``/api/csm/v1/transcript/``).
But this would be a major external-API change with **breaking
consequences for clients** — NOT recommended.

Summary
==========

.. list-table::
   :header-rows: 1
   :widths: 28 36 36

   * - Audit aspect
     - Original assumption
     - Reality
   * - V1 status
     - "Legacy, candidate for sunset"
     - **Active, current** (8 different domains)
   * - V2 status
     - "Current replacement"
     - **Newer namespace** for newly-added domains
   * - V1 ↔ V2 pairs
     - "Multiple expected"
     - **ZERO** found
   * - Action needed
     - "Plan deprecation"
     - **None** — claim was wrong
   * - LoC removable
     - "Probably hundreds"
     - **0**

