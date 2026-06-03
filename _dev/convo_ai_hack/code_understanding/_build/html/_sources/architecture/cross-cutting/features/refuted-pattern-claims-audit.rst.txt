.. _audit-refuted-pattern-claims:

==================================================================
Pattern 1 refutation audits — AIFC SchemaAgents + A2A versioning
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Status: **TWO PATTERN-1 CLAIMS REFUTED**
:Disposition: Both "AIFC SchemaAgent variants" and "A2A versioning" claims in :ref:`cross-cutting-patterns` Pattern 1 were OVERINTERPRETATION. Audits found NO legacy/new coexistence in either case.

.. contents:: On this page
   :local:
   :depth: 2

TL;DR
========

The cross-cutting patterns doc (:ref:`cross-cutting-patterns`) Pattern 1
listed two "needs audit" entries that are now resolved:

.. list-table::
   :header-rows: 1
   :widths: 32 24 44

   * - Claim
     - Original verdict
     - Audit verdict
   * - **AIFC SchemaAgent variants** (V1/Enhanced/Search/Validate/Documentation)
     - "Needs audit — same JQL pattern likely"
     - **REFUTED** — no AIFC-prefixed SchemaAgents exist
   * - **A2A versioning** (legacy + new agent-to-agent protocols)
     - "Needs audit — suspected"
     - **REFUTED** — single non-versioned implementation

**Result**: Pattern 1's instance count drops from 8 to 6 verified instances.
The patterns doc has been updated.

Audit 1 — AIFC SchemaAgent variants
=========================================

**Investigation method**: Search for AIFC-prefixed SchemaAgent files
across all modules.

**Hard evidence** (verified by ``find`` + ``grep``):

.. code-block:: bash

   # All AIFC-prefixed SchemaAgent files: NONE
   find $SRC/modules -name 'Aifc*SchemaAgent*.kt' -path '*/main/*'
   # → no matches

   # All Aifc*Agent files: NONE
   find $SRC/modules -name 'Aifc*Agent*.kt' -path '*/main/*'
   # → no matches

   # All SchemaAgent files in any aifc-named directory: NONE
   find $SRC/modules -path '*aifc*' -name '*SchemaAgent*.kt' -path '*/main/*'
   # → no matches

**What the original AIFC doc actually flagged**:

The :ref:`feature-aifc` doc mentioned multiple SchemaAgent variants
related to AIFC's content creation pipeline. However, the underlying
SchemaAgents are NOT in AIFC modules. They live in
``rovo-impl/.../subagent/jirabatchagents/`` and include:

* ``JqlExecutionSchemaAgent`` (current)
* ``JqlExecutionSchemaAgentV1``
* ``JqlValidationSchemaAgent``
* ``JqlSearchSchemaAgent``
* ``JqlDocumentationSchemaAgent``
* (Plus ``EnhancedJqlExecutionSchemaAgent`` — already deleted in JQL Phase 2)

**These are Rovo SchemaAgents that AIFC consumes** — not AIFC-owned.
The "AIFC variants" framing in the AIFC doc was imprecise. The actual
audit candidate is the **JQL/Jira SchemaAgent family** in rovo-impl —
already partially addressed by :ref:`jql-audit` Phase 2 (Enhanced
deletion) and Phase 3 (NL2Jql migration deferred).

**Recommendation**:

* ✅ Update Pattern 1 in :ref:`cross-cutting-patterns` — remove "AIFC
  SchemaAgent variants" entry
* ✅ The rovo-impl Jira agent family audit IS valuable but already
  tracked via JQL Phase 2/3 and a future "JqlValidation/Search/
  Documentation audit" ticket
* ✅ Update :ref:`feature-aifc` doc to clarify "AIFC consumes Rovo
  SchemaAgents; AIFC does not own variants"

**Audit verdict**: ✅ **NO CODE CHANGES** — claim was misframed.

Audit 2 — A2A (Agent-to-Agent) versioning
=============================================

**Investigation method**: Search for A2A versioning / legacy patterns
across all modules.

**Hard evidence** (verified by ``find`` + ``grep``):

A2A IS a real, active concept (~16,500 LoC). It uses Atlassian's
``a2a-spring-boot-starter`` library for agent-to-agent communication.

**Key files identified**:

.. list-table::
   :header-rows: 1
   :widths: 50 12 38

   * - File
     - LoC
     - Role
   * - ``foundation/adk/core-api/.../a2a/A2aStateKeys.kt``
     - 21
     - Context propagation constants for A2A flow
   * - ``foundation/adk/core-impl/.../a2a/AdkA2aRequestHandlerProvider.kt``
     - 22
     - **Single Spring component** providing A2A request handler
   * - ``foundation/adk/core-impl/.../a2a/AdkRequestHandler.kt``
     - 300+
     - Core A2A request handler — handles inter-agent calls
   * - ``platform/conversation/.../ConversationChannelRemoteA2ATaskMetadataUpdateRequest.kt``
     - 8
     - DTO for A2A task metadata updates

**Versioning check**:

.. code-block:: bash

   # @Deprecated annotations on A2A files: NONE
   grep -rln '@Deprecated' $SRC/modules --include='*.kt' | xargs grep -l 'A2A\|AgentToAgent'
   # → no matches

   # V1/V2/Legacy/Enhanced variants of A2A: NONE
   find $SRC/modules -name 'A2A*V1*.kt' -o -name 'A2A*V2*.kt' \\
       -o -name 'Legacy*A2A*.kt' -o -name 'A2A*Legacy*.kt'
   # → no matches

   # Factory pattern wiring multiple A2A versions: NONE
   grep -rn 'A2aFactory\|A2AVersionRouter' $SRC/modules --include='*.kt'
   # → no matches

**The implementation pattern**:

.. code-block:: kotlin

   @Component
   class AdkA2aRequestHandlerProvider : A2aRequestHandlerProvider {
       override fun create(): RequestHandler {
           return AdkRequestHandler(agenticSkillA2AAgentProvider, observabilityContextFactory)
       }
   }

This is **single, current, non-versioned**. The cross-cutting patterns
doc's inference of "legacy + new agent-to-agent protocols" was based
on architectural intuition (most cross-system communication systems
have legacy variants), but this codebase doesn't.

**Why might this be?** The A2A integration uses an external library
(``a2a-spring-boot-starter``) that handles versioning at the protocol
layer, not at the application layer. Application code only needs to
implement the current ``A2aRequestHandlerProvider`` interface. Future
protocol versions would likely be added at the library level, not
duplicated in application code.

**Audit verdict**: ✅ **NO CODE CHANGES** — claim was unfounded.

**Recommendation**:

* ✅ Update Pattern 1 in :ref:`cross-cutting-patterns` — remove "A2A
  versioning" entry  
* ✅ A2A is a clean, modern integration; flag as "good architecture
  pattern" worth replicating

Both refutations — what they teach us
=========================================

These two refutations are **methodologically valuable** for several
reasons:

**1. Audits are bidirectional** — they can DELETE claims, not just CONFIRM them.

The JQL Phase 2 audit DELETED 963 LoC of dead code. These two audits
DELETE 2 false claims from the patterns doc. Both are valuable.

**2. Architectural intuition has limits** — the "legacy/new pattern"
hypothesis was reasonable a priori, but evidence said no.

**3. Documentation should evolve with audits** — the patterns doc
(written based on partial evidence) had to be updated as audits
revealed reality.

**4. Pattern density is real, but not universal** — the codebase DOES
have lots of legacy/new coexistence (verified for JQL, JSM, SAIN,
Pebble templates). Not EVERY suspected case is real.

Updated Pattern 1 instance count
====================================

After these two refutations, :ref:`cross-cutting-patterns` Pattern 1
("Legacy/new coexistence") instance table now reads:

**6 verified instances** (was 8):

* ✅ JQL agents (Enhanced deletion executed; NL2 migration deferred)
* ✅ JSM PlanGenerator (FF identified; deletion deferred to V2 100%)
* ✅ NL2 Jql variants (audit complete; migration in JQL Phase 3)
* ✅ SAIN orchestrators (3 coexist intentionally — different complexity tiers)
* ✅ Pebble templates (memory extraction V1 + V2 + explicit_only)
* ✅ CSM REST namespaces (audited; NOT migration — separate domains)

**Refuted/withdrawn**:

* ❌ AIFC SchemaAgent variants (no AIFC-owned variants exist)
* ❌ A2A versioning (no V1/V2 split — single non-versioned impl)

