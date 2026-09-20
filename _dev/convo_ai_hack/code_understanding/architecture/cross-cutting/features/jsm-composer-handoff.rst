=================================================
JSM Composer & Handoff
=================================================

**One-sentence definition**: JSM Composer is an LLM-driven setup wizard
that conversationally configures a Jira Service Management project
(request types, queues, SLAs, portal) and executes the plan via
specialized "minions"; Handoff is the escalation path that routes the
user to a human agent when AI assistance is insufficient.

**User-visible**: Yes — direct UX in the JSM portal/admin UI.

Where it lives
================

.. list-table::
   :header-rows: 1
   :widths: 50 25 25

   * - Path
     - Lines
     - Purpose
   * - ``modules/product/jsm/jsm-impl/.../JSMServiceDeskComposerAgent.kt``
     - ~1000
     - Main composer orchestrator
   * - ``modules/product/jsm/jsm-impl/.../templates/jsm/composer/composer_system_template.pebble``
     - ~150
     - Conversational system prompt
   * - ``modules/product/jsm/jsm-impl/.../templates/jsm/composer/planner_system_template.pebble``
     - ~120
     - Plan generation prompt
   * - ``modules/product/rovo/rovo-impl/.../tools/handoff/StartHandoffToolImplementation.kt``
     - ~200
     - Handoff tool entry point
   * - ``modules/platform/base/base-api/.../DefaultFormHeuristicEvaluator.kt``
     - ~150
     - Form-complexity-based handoff trigger
   * - ``modules/product/rovo/rovo-impl/.../tools/handoff/TemplatedMessageHandoffOutputConverter.kt``
     - ~80
     - Handoff message templating
   * - ``modules/product/rovo/rovo-impl/.../tools/handoff/LiveChatHandoffOutputConverter.kt``
     - ~100
     - Live-chat handoff routing

End-to-end flow
=================

.. mermaid::

   stateDiagram-v2
     [*] --> GATHERING_INFO
     GATHERING_INFO --> GATHERING_INFO: User adds details
     GATHERING_INFO --> PLANNING: infoSufficient=true
     PLANNING --> WAITING_FOR_USER: Plan generated
     WAITING_FOR_USER --> EXECUTING: User approves
     WAITING_FOR_USER --> GATHERING_INFO: User edits plan
     EXECUTING --> COMPLETE: All minions run
     EXECUTING --> FAILED: Minion error
     COMPLETE --> [*]
     FAILED --> [*]

     PLANNING --> HANDOFF: Frustration / failure
     EXECUTING --> HANDOFF: Form too complex
     HANDOFF --> [*]: Routed to agent

**Step-by-step**:

#. **User message arrives** in JSM portal (chat UI)
#. **Composer enters GATHERING_INFO state** — runs ``composer_system_template.pebble`` LLM prompt; gathers user intent + reasonable defaults
#. **LLM returns JSON**: ``{ gatheredUserInput, infoSufficient: boolean, questions, agentMessage }``
#. **If ``infoSufficient=false``**: ask follow-up questions; loop back to step 2
#. **If ``infoSufficient=true``**: transition to **PLANNING** state
#. **PLANNING**: runs ``planner_system_template.pebble`` to generate a list of execution steps mapped to available minions
#. **WAITING_FOR_USER**: presents plan to user; awaits approval
#. **EXECUTING**: invokes minions sequentially; each minion calls JSM admin APIs
#. **COMPLETE**: emits summary to user; persists final state to ERS

Composer subsystem
====================

**Core class**: ``JSMServiceDeskComposerAgent extends BaseComposerAgent<ServiceDeskPlanStep>``

**State machine**: 5 states (GATHERING_INFO → PLANNING → WAITING_FOR_USER → EXECUTING → COMPLETE/FAILED)

**Available minions** (executable task handlers — only present in plan if injected at runtime):

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Minion
     - Purpose
   * - ``JsmManageRequestTypeMinion``
     - Create/update request types
   * - ``JsmQueueCreateMinion``
     - Create JSM queues
   * - ``JsmSLAMinion``
     - Configure SLA policies
   * - ``JsmPortalConfigMinion``
     - Set up customer portal
   * - (more added as needed)

**Anti-interrogation rule** (in ``composer_system_template.pebble``):

   *"Don't ask for one feature at a time. Bundle assumptions: 'I'll set up
   request types, queues, SLA policies, and the portal. Sound right?'
   This avoids 5-question chains that frustrate users."*

**Output JSON contract**:

.. code-block:: json

   {
     "gatheredUserInput": { "purpose": "IT support", "name": "..." },
     "infoSufficient": true,
     "questions": [],
     "agentMessage": "I'll set up your service desk with..."
   }

Handoff subsystem
===================

**Handoff triggers** (3 paths):

#. **User-initiated** (LLM detects via ``HandoffFrustrationDetectionTool``):

   * User says "talk to a human", "this isn't working", etc.
   * Tool invokes ``StartHandoffToolImplementation``

#. **Form-heuristic-triggered** (auto, via ``DefaultFormHeuristicEvaluator``):

   .. list-table::
      :header-rows: 1
      :widths: 40 60

      * - Reason
        - Trigger
      * - ``UNSUPPORTED_REQUIRED_FIELD``
        - Form has a required field type AI can't fill
      * - ``TOO_COMPLEX``
        - ``requiredFieldCount > maxRequiredFieldsThreshold``
      * - ``TOO_MANY_OPTIONS``
        - ``maxRequiredOptionCount > maxRequiredOptionCountThreshold``

#. **System-initiated** (composer fails):

   * Plan generation fails 3 times → fallback to handoff
   * Minion execution fails non-recoverably → fallback to handoff

**Handoff state transfer**:

.. code-block:: kotlin

   data class HandoffToolContext(
       val tenant: TenantContext,
       val user: User,
       val conversationId: String,
       val attachments: List<FileAttachment>,
       val planState: ComposerPlanState,
       val reason: FallbackReason,
   )

**Output converters** (multiple targets):

* ``TemplatedMessageHandoffOutputConverter`` — generic templated message (Slack, email)
* ``LiveChatHandoffOutputConverter`` — live chat agent (CSM)
* ``JSMCreateRequestHandoffTool`` — creates JSM request with full context

Integration topology
======================

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - System
     - Direction
     - Purpose
   * - **JSM Portal**
     - ← (inbound)
     - User messages from JSM web UI
   * - **JSM Admin APIs**
     - → (outbound)
     - Minions create request types / queues / SLAs
   * - **Agent Platform (CSM)**
     - → (outbound)
     - Handoff escalation to live agent
   * - **Slack**
     - → (outbound)
     - Optional handoff notification
   * - **Ticket Creation**
     - → (outbound)
     - JSMCreateRequestHandoffTool creates request with context
   * - **File Attachments**
     - ← + → (passthrough)
     - User-uploaded files passed through handoff context
   * - **LLM Service**
     - ← (model invocation)
     - Plan generation + conversational prompting

Configuration & feature flags
================================

**Composer configuration**:

* **Available minions**: injected at runtime via ``ComposerMinionRegistry``; composer only presents features for available minions
* **Rollout service**: ``rolloutService.controlledByLimitedContext(...)`` checked in ``StartHandoffToolImplementation``

**Handoff configuration** (``FormHeuristicConfig``):

.. code-block:: kotlin

   data class FormHeuristicConfig(
       val enabled: Boolean,
       val maxRequiredFieldsThreshold: Int,            // e.g., 5
       val maxRequiredOptionCountThreshold: Int,       // e.g., 50
       val perFlowOverrides: Map<FlowType, FormHeuristicConfig>,
   )

**FF gates**:

* Composer enabled per cloudId via Statsig FF
* Handoff tool exposure controlled by ``rolloutService``
* Per-flow handoff thresholds configurable

Observability
===============

**Metrics emitted** (via ``ComposerMetrics``):

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Metric
     - Tags
   * - ``solcom.execution.total``
     - state, model, flow_type — E2E per turn
   * - ``solcom.plan.handling``
     - state, model — All states
   * - ``solcom.gathering_info``
     - model, success — Per-state latency
   * - ``solcom.planning``
     - model, success — Per-state latency
   * - ``solcom.executing``
     - model, success — Per-state latency
   * - ``solcom.llm.call``
     - operation, model — Per-LLM-call
   * - ``solcom.minion.invocation``
     - minion, phase (planning/execution) — Per-minion latency
   * - ``solcom.plan.load`` / ``solcom.plan.persist``
     - operation, success — Store I/O latency
   * - **Handoff rate** (from handoff metrics)
     - flow_type, fallback_reason — Critical KPI

**Backend**: SignalFx (Micrometer) + Splunk dual-write

**Logging**: Structured context via ``ComposerInstrumentation`` + ``ComposerTraceContext``

Known limitations & open questions
=====================================

**Limitations**:

#. **Single-stream execution**: Minions run sequentially; no parallelism
#. **Plan persistence**: ERS-stored; recovery on interruption requires manual reload
#. **Minion coupling**: Composer tightly tied to JSM minions; CSM handoff still being integrated
#. **Form complexity cutoff**: Hard threshold; no graceful degradation
#. **User intent ambiguity**: Edge cases in domain detection rely on LLM parsing

**Open questions** (suggested follow-up investigations):

#. How is conversation history pruned for very long escalations before CSM handoff?
#. Does ``stillInFocus()`` check in ``StartHandoffToolImplementation`` prevent re-escalation loops?
#. How are attachment IDs validated before passing to downstream agents?
#. Is there a max-attempt budget before auto-escalation, or purely heuristic-driven?
#. Are SLA metrics computed during planning or only at execution time?

Cross-references
==================

* :doc:`jsm-platform` — JSM-tier overview (mentions composer + handoff)
* :doc:`agent-framework` — minion infrastructure
* :doc:`csm-platform` — CSM-side handoff receiver
* :doc:`../patterns` — composer pattern (Pattern 1 of cross-cutting patterns)
