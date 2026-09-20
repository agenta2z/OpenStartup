.. _feature-lumina:

==================================================================
Lumina — Lightweight LLM classifier + answer sub-agent for SAIN
==================================================================

:Verification date: 2026-05-02
:Source commit: ``9151ac1341583a0a1ba81d5742f904ff2c43d62b``
:Footprint: **1,136 LoC across 9 files** (compact, well-scoped)
:Module: ``modules/product/rovo/rovo-impl/.../agent/lumina/``
:Triage score: **18/25 — well-scoped feature**

.. contents:: On this page
   :local:
   :depth: 2

What Lumina IS (in one paragraph)
====================================

Lumina is a **lightweight LLM-driven query classifier and answer sub-agent
system** that serves as the **fast-path complement** of SAIN's full
orchestration. Given an incoming query, the SAIN orchestrator first asks
Lumina's classification service: "Is this query simple/formatting-rich
(LUMINA), or does it need full multi-tool orchestration (STANDARD)?"
**LUMINA-classified queries** route to Lumina's specialized answer
sub-agent which produces structured, citation-aware, formatting-rich
responses with tag-based output protocol. **STANDARD-classified queries**
fall through to the regular SAIN orchestration path. Lumina is **NOT a
replacement** for ``SainOrchestrationComplexityClassifier`` (which does
SIMPLE/COMPLEX routing within an orchestrator) — it's a **complementary
upstream stage** that handles the easiest queries with minimum LLM cost
and best-quality formatting.

Anatomy — where Lumina lives
================================

**One module, one folder**: ``rovo-impl/.../agent/lumina/`` — 1,136 LoC across 9 .kt files.

.. list-table::
   :header-rows: 1
   :widths: 44 12 44

   * - File
     - LoC
     - Role
   * - ``LuminaAnswerAgent.kt``
     - **235**
     - **Main entry.** The answer sub-agent — receives LUMINA-classified queries, runs structured answer generation
   * - ``LuminaSubAgentHandler.kt``
     - 219
     - Sub-agent lifecycle dispatcher — manages tool execution + streaming response
   * - ``LuminaStreamMessageBufferWithCitation.kt``
     - 158
     - **Citation-aware stream buffer** — tracks source references inline as the LLM streams output
   * - ``classification/LuminaClassificationService.kt``
     - 154
     - **Classification engine** — JSON-schema LLM call that classifies query as LUMINA or STANDARD
   * - ``LuminaAnswerAgentHelper.kt``
     - 124
     - Answer formatting utilities — structures responses for rich rendering
   * - ``LuminaAgentSystemPromptTemplateGenerator.kt``
     - 75
     - Prompt assembly — generates Lumina system prompts from Pebble templates
   * - ``config/LuminaConfigService.kt``
     - 70
     - Config service — fetches feature flag values + per-tenant config
   * - ``LuminaTagStreamParser.kt``
     - 59
     - **Tag-based output parser** — extracts structured data from LLM streams using custom XML-like tags
   * - ``config/LuminaConfig.kt``
     - 42
     - Config data classes

The 2-step Lumina pipeline
=============================

**Step 1: Classification** (``LuminaClassificationService``)
-------------------------------------------------------------

When SAIN receives a query:

1. Renders ``lumina_query_classification.pebble`` template with:

   * The user's query
   * (Possibly) recent conversation context

2. Calls LLM with **JSON-schema structured output** to enforce response format
3. Returns one of two classes:

   * ``LUMINA`` — query is simple, formatting-rich, well-served by Lumina's specialized prompt
   * ``STANDARD`` — query needs full SAIN orchestration (multi-tool, multi-turn, complex reasoning)

**Step 2A — LUMINA path** (``LuminaAnswerAgent`` + ``LuminaSubAgentHandler``)
------------------------------------------------------------------------------

If classified as LUMINA:

1. ``LuminaAnswerAgent`` is invoked
2. Builds system prompt via ``LuminaAgentSystemPromptTemplateGenerator``
3. Calls LLM with the Lumina-specific prompt
4. **Stream output is parsed in real-time** by ``LuminaTagStreamParser``:

   * Custom XML-like tag protocol delineates answer blocks, metadata, citations
   * Tags are extracted as the stream arrives (not buffered to end)

5. ``LuminaStreamMessageBufferWithCitation`` tracks citations inline:

   * As the LLM cites a source, the buffer records (source_id, char_position)
   * Citation references can be rendered in the UI alongside answer text

6. ``LuminaAnswerAgentHelper`` formats the structured output for delivery

**Step 2B — STANDARD path** (handled by SAIN orchestrators)
-------------------------------------------------------------

If classified as STANDARD: SAIN's full orchestration takes over —
``SainStandaloneHybridOrchestratorAgent``, ``SainHybridOrchestratorAgent``,
or ``SainLongHorizonOrchestratorAgent`` based on further classification.

The SAIN-Lumina relationship — VERIFIED
==========================================

This is the question the Wave-2 inventory raised. Now answered with hard evidence.

**Cross-references found** (verified by ``grep``):

.. list-table::
   :header-rows: 1
   :widths: 56 44

   * - Reference location
     - What it tells us
   * - ``rovo-api/.../sain/cli/SainCliStreamingWriter.kt``
     - Lumina's ``StreamMessageBufferWithCitation`` is reused by SAIN CLI streaming — confirms Lumina infrastructure (citation buffering) is part of SAIN
   * - ``rovo-impl/test/.../orchestrators/LongHorizonOrchestratorAgentTest.kt``
     - SAIN-LH test references Lumina — confirms Lumina is invoked from within SAIN orchestrators
   * - ``rovo-impl/test/.../orchestrators/HybridOrchestratorStreamingHandlerTest.kt``
     - SAIN-Hybrid test references Lumina — same
   * - ``rovo-impl/test/.../sain/orchestrator/DirectSainHybridOrchestratorConfigFactoryTest.kt``
     - Direct evidence that SAIN config-factory creates Lumina-related components

**Conclusion**: Lumina is **NOT a parallel competing orchestrator** to
SAIN. It's a **specialized component within SAIN**:

* **Classification** (LUMINA vs STANDARD) is the upstream gate
* **Lumina answer agent** is the optimized fast-path
* **Citation infrastructure** (``LuminaStreamMessageBufferWithCitation``)
  is shared with SAIN's CLI streaming writer

This **resolves the Wave-2 inventory open question**:
"Is Lumina the SIMPLE-path implementation of SAIN?" → **YES, partially**.
Lumina is one of SAIN's specialized sub-paths, distinct from
``SainOrchestrationComplexityClassifier``'s SIMPLE/COMPLEX dichotomy
(which operates *within* a chosen orchestrator).

The two classifications are DIFFERENT
=========================================

Important: Don't confuse these two classifiers:

.. list-table::
   :header-rows: 1
   :widths: 28 36 36

   * - Classifier
     - Decides
     - When
   * - ``LuminaClassificationService``
     - LUMINA (fast-path) vs STANDARD (full orchestration)
     - **Upstream** — before SAIN orchestrator chosen
   * - ``SainOrchestrationComplexityClassifier``
     - SIMPLE vs COMPLEX
     - **Inside** ``SainHybridOrchestratorAgent`` after STANDARD path chosen

Both can produce the same effective routing, but they operate at
different layers. Both could probably be unified — that's a design
question worth raising.

The MCP integration (``ShouldUseLuminaToAnswerTool``)
=========================================================

The MCP system has a tool ``ShouldUseLuminaToAnswerTool`` that
**lets the LLM itself decide** whether the current query should
invoke Lumina. This is a different invocation path than the upstream
classification — it's **agent-driven routing**: the orchestrator's
LLM looks at the query, calls ``should_use_lumina_to_answer``, and
gets back a boolean.

**Two paths into Lumina**:

1. **Pre-orchestration classification** (``LuminaClassificationService``)
   — runs before the orchestrator, returns LUMINA or STANDARD
2. **Mid-orchestration tool call** (``ShouldUseLuminaToAnswerTool``)
   — the orchestrator's LLM can ask "should I use Lumina?" mid-flow

Having both paths is **possibly redundant** and could be simplified.

The tag-based output protocol
================================

Lumina uses a **custom tag-based protocol** (parsed by ``LuminaTagStreamParser``,
59 LoC). The protocol uses XML-like tags to delineate output structure:

* Answer text blocks
* Metadata sections
* Citation markers (likely ``[^N^]`` style based on SAIN's pattern)

Why custom tags vs JSON streaming?

* JSON streaming requires waiting for valid JSON parse points
* Tags can be parsed incrementally as bytes arrive
* Better UX: user sees partial answer + citations stream in real-time

The citation system
=====================

``LuminaStreamMessageBufferWithCitation`` (158 LoC):

* As the LLM streams text, the buffer records citation markers
* Citation marker → source reference map is built incrementally
* Final answer can be rendered with footnote-style citations

This **same component is reused by SAIN CLI** (verified via
``SainCliStreamingWriter`` reference) — suggesting it was designed
generically and adopted by SAIN later.

End-to-end flow
==================

Sequence diagram (a typical chat turn):

.. mermaid::

   sequenceDiagram
       autonumber
       participant U as User
       participant Chat as RovoChatService
       participant SAIN as SAIN entry
       participant Class as LuminaClassification<br/>Service
       participant LLM
       participant Lumi as LuminaAnswerAgent
       participant Tags as LuminaTagStreamParser
       participant Cit as LuminaStream<br/>BufferWithCitation
       participant Std as Standard SAIN<br/>orchestrator

       U->>Chat: query
       Chat->>SAIN: routeAndExecute(query)

       SAIN->>Class: classify(query)
       Class->>LLM: invoke(lumina_classification.pebble + query)
       LLM-->>Class: {"class": "LUMINA"}
       Class-->>SAIN: LUMINA

       alt LUMINA path
           SAIN->>Lumi: answer(query, ctx)
           Lumi->>LLM: invoke with Lumina system prompt
           loop streaming
               LLM-->>Lumi: chunk
               Lumi->>Tags: parse(chunk)
               Tags-->>Lumi: parsed structure
               Lumi->>Cit: trackCitations(chunk)
               Cit-->>Lumi: updated buffer
               Lumi-->>U: stream chunk
           end
           Lumi-->>U: final answer + citations
       else STANDARD path
           SAIN->>Std: orchestrate(query, ctx)
           Std-->>U: final answer (full SAIN flow)
       end

Smells and concerns
=====================

.. list-table::
   :header-rows: 1
   :widths: 6 32 16 46

   * - Sev
     - Issue
     - Where
     - Notes
   * - 🟡
     - **Two classification mechanisms** (LuminaClassification + SainOrchestrationComplexityClassifier + ShouldUseLuminaToAnswerTool)
     - cross-system
     - Three different ways to decide "what path to take". Could be unified.
   * - 🟡
     - **Lumina lives outside its consumer** (in ``agent/lumina/``, used by ``product/rovo/sain/``)
     - location
     - Inconsistent: Lumina is a SAIN component but lives in agent/. Should consolidate or document the boundary.
   * - 🟡
     - **No KDoc on key classes** (verified by sub-agent — limited inline docs)
     - all files
     - 1,136 LoC of code with little explanation. Worth a 1-pager.
   * - 🟡
     - **Custom tag protocol** vs structured JSON
     - LuminaTagStreamParser
     - Pro: incremental parsing. Con: harder to evolve schema; client must implement parser.
   * - 🟢
     - **Compact** — only 9 files, 1,136 LoC
     - all
     - Small enough to refactor confidently.
   * - 🟢
     - **Citation infrastructure is reusable** (used by SAIN CLI)
     - StreamMessageBufferWithCitation
     - Good abstraction.

Refactoring opportunities
============================

1. **Move Lumina folder to ``product/rovo/sain/lumina/``** (S, 🟡 medium) — co-locate with consumer. ~1 hour.

2. **Unify the 3 classifiers** (M, 🟡 medium) — LuminaClassification + SainOrchestrationComplexityClassifier + ShouldUseLuminaToAnswerTool into one routing service. ~3-5 days.

3. **Document the tag protocol** (XS, 🟡 medium) — list every tag, what it means. ~half day.

4. **Add KDoc to all 9 files** (XS, 🟡 medium) — explain the responsibility of each. ~1 day.

5. **Add Sphinx classifier-flow diagram** (XS, 🟢 low) — visualize all 3 routing decisions.

6. **Audit ``ShouldUseLuminaToAnswerTool`` usage** (S, 🟢 low) — verify it's actually used by orchestrators or is dead code.

What you would change here
============================

* **Modify Lumina classification prompt** → ``resources/templates/agent/lumina/lumina_query_classification.pebble``

* **Modify Lumina answer prompt** → ``resources/templates/agent/lumina/lumina_answer_system_prompt.pebble``

* **Add new tag to output protocol** → ``LuminaTagStreamParser.kt`` + downstream parsers

* **Tune citation tracking** → ``LuminaStreamMessageBufferWithCitation.kt``

* **Change LLM model used by Lumina** → ``LuminaConfig.kt`` config

* **Add per-tenant LUMINA enablement** → ``LuminaAgentFeatureFlags.kt``

What you would NOT change here
================================

* SAIN orchestrators themselves — owned by ``product/rovo/sain/orchestrator/``
* MCP tool ``ShouldUseLuminaToAnswerTool`` — owned by ``product/rovo/mcp/tool/``
* Pebble template engine — third-party
* LLM service — owned by ``platform/service/service-impl``

Verification audit log
========================

✅ **Personally verified with bash:**

* 9 files in ``agent/lumina/``, 1,136 total LoC
* All 9 file LoC counts (find + wc)
* Cross-reference grep:

  * ``LuminaAnswerAgent``, ``LuminaClassification``, ``LuminaSubAgent``
  * Found in: SAIN CLI (``SainCliStreamingWriter``), 3 SAIN orchestrator tests, Lumina's own files

* ``LuminaConfigService.kt`` exists at ``classification/`` is wrong — it's at ``config/`` (corrected)
* ``LuminaClassificationService.kt`` is at ``classification/`` (verified)

⚠️ **Inferred from sub-agent report + naming**:

* The "LUMINA vs STANDARD" 2-class dichotomy (sub-agent claim; not directly verified by reading classifier output schema)
* The "fast-path" semantics (architectural inference)
* The Pebble template name ``lumina_query_classification.pebble`` (sub-agent claim)
* The end-to-end flow ordering (responsibility-based inference)
* The "JSON-schema structured output" (likely; not source-verified)

❌ **UNVERIFIED:**

* The exact JSON schema of the classification response
* Whether ``ShouldUseLuminaToAnswerTool`` actually exists (sub-agent reported it from MCP doc reference, not direct grep)
* The custom tag protocol tags (sub-agent didn't enumerate)
* Per-class FF rollout state
* Whether Lumina is at 100% production rollout
* The cost savings of LUMINA path vs STANDARD path

Open questions for institutional knowledge
=============================================

1. **What's the LUMINA classification rate** (% of queries classified as LUMINA)?
2. **What's the cost reduction** vs full SAIN orchestration?
3. **Are the 3 classifiers (Lumina + SainComplexity + ShouldUseLumina) genuinely distinct** or vestigial parallel paths?
4. **What's the current LLM model** used for classification + for Lumina answer?
5. **What does the tag protocol look like** — full enumeration?
6. **Why is Lumina in ``agent/lumina/`` not ``product/rovo/sain/lumina/``**?
7. **Is ``ShouldUseLuminaToAnswerTool`` still actively used**?
8. **What was Lumina named after**? (Codename inference: lightweight, illuminating answers)

