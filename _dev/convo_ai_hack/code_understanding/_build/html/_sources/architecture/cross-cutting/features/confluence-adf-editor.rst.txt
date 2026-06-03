=================================================
Confluence ADF Editor AI
=================================================

**One-sentence definition**: An in-editor AI editing system for
Confluence pages — users invoke ``aifc-adf-update`` tool from within
the page editor, and an LLM-driven loop streams ADF (Atlassian
Document Format) edit operations that are applied incrementally.

**User-visible**: Yes — direct UX in Confluence page editor (sidebar
+ inline AI menu).

Where it lives
================

.. list-table::
   :header-rows: 1
   :widths: 50 12 38

   * - Path
     - Lines
     - Purpose
   * - ``modules/product/confluence/.../AdfEditorMinion.kt``
     - **~1,450**
     - Main editing-loop orchestrator
   * - ``modules/product/confluence/.../AdfEditOperation.kt``
     - ~80
     - Sealed interface defining all 6 ADF mutation commands
   * - ``modules/product/confluence/.../SystemPromptBuilder.kt``
     - ~250
     - Pebble template loader with dynamic prompt context injection
   * - ``modules/product/confluence/.../AdfEditorToolDefinition.kt``
     - ~120
     - Tool registration; schema (semanticQuery, contentId, status)
   * - ``modules/product/confluence/.../DynamicPromptingConfig.kt``
     - ~150
     - Keyword classifier for prompt-fragment injection
   * - ``modules/product/confluence/.../templates/adf_editor_minion_sys_prompt.pebble``
     - ~300
     - Core system prompt + examples
   * - Plus: ``SimpleAdfGenerationMinion.kt`` (~200) for blank-page fallback

ADF format basics
====================

**ADF (Atlassian Document Format)** is a tree-structured JSON document
format used across Atlassian's editor (Confluence, Jira, etc.):

.. code-block:: json

   {
     "type": "doc",
     "version": 1,
     "content": [
       { "type": "heading", "attrs": {"level": 1},
         "content": [{"type": "text", "text": "Hello"}] },
       { "type": "paragraph",
         "content": [{"type": "text", "text": "World"}] }
     ]
   }

**Why it matters for AI editing**:

* **Structured = surgical edits**: AI can target individual nodes by ``nodeId`` (e.g., "replace this paragraph", "delete this table"), avoiding whole-document regeneration
* **Round-trippable**: Editor parses + renders ADF natively; no lossy text conversion
* **Native semantics**: Tables, panels, lists, code blocks, status badges, action items all have first-class ADF representations

End-to-end flow
=================

.. mermaid::

   sequenceDiagram
     participant User
     participant Editor as Confluence Editor
     participant convoai as convoai
     participant Minion as AdfEditorMinion
     participant LLM

     User->>Editor: Selects text + invokes "Rephrase" AI menu
     Editor->>convoai: aifc-adf-update(semanticQuery, contentId, status)
     convoai->>Minion: invoke()
     Note over Minion: Build sysPrompt + userPrompt + ADF context
     loop max 15 iterations (configurable)
       Minion->>LLM: stream prompt
       LLM-->>Minion: stream tool calls
       Note over Minion: Parse AdfEditOperation list
       Minion->>Minion: Apply ops to local ADF (or via content service)
       Minion->>LLM: function message (current ADF state)
     end
     Note over Minion: Aggregate before/after diff
     Minion-->>convoai: ConfluencePageUpdateDirectData
     convoai-->>Editor: stream rendered changes
     Editor-->>User: Apply changes via native ADF renderer

ADF edit operations (6 ops)
=============================

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Operation
     - Semantics
   * - ``InsertAfter(nodeId, adf)``
     - Insert ADF subtree after specified node
   * - ``InsertBefore(nodeId, adf)``
     - Insert ADF subtree before specified node
   * - ``Replace(nodeId, adf)``
     - Replace specified node with new ADF subtree
   * - ``Delete(nodeId)``
     - Remove specified node
   * - ``CreateEmptyTable(nodeId, rows, cols)``
     - Structured table creation (instead of constructing ADF table by hand)
   * - ``GetPageContent(format: "adf"|"html")``
     - Synthetic — refresh current state (not a real LLM call)

Available AI operations (user-facing)
========================================

These map to LLM prompts that emit one or more ``AdfEditOperation``:

* **Summarize** — replace long content with condensed version
* **Rephrase** — alternative wording while preserving meaning
* **Expand** — add detail, examples, context
* **Translate** — translate selection to different language
* **Format** — convert prose → bullet list, table, panel
* **Improve writing** — grammar, clarity, conciseness
* **Custom prompt** — user types arbitrary instruction

Per-operation routing is handled by the LLM understanding the
``semanticQuery`` parameter; no hardcoded operation enum.

Prompt strategy (Pebble templates)
=====================================

**Base system prompt**: ``adf_editor_minion_sys_prompt.pebble``
(~300 lines) — core editing instructions + few-shot examples.

**Dynamic fragments**: loaded based on keyword classification by
``DynamicPromptingConfig``:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Keyword class
     - Fragment loaded
   * - ``TABLE``
     - Table-editing instructions + examples
   * - ``PANEL``
     - Panel (info/warning/note) instructions
   * - ``LIST``
     - List manipulation instructions
   * - ``FORMATTING``
     - Bold/italic/code formatting
   * - ``WRITING``
     - General writing tone instructions
   * - ``EMOJI``
     - Emoji insertion rules
   * - ``ACTION``
     - Action item / checklist instructions
   * - ``STATUS``
     - Status badge instructions

**Prompt versioning**: ``promptVersion`` field in tool input;
**version ≥11** enables semantic labels for structured data.

**HTML context mode**: optional — seeds document as HTML instead of
ADF JSON (experiment via FF ``AIFC_ADF_EDITOR_HTML_CONTEXT``). LLMs
sometimes parse HTML better than nested JSON.

Streaming considerations
==========================

* **LLM response streamed in chunks**; ``InterceptingChunkProcessor`` parses tool calls as they arrive
* **Semantic tool interception**: structure-aware table tools execute **during streaming** if FF ``AIFC_STRUCTURE_AWARE_TABLE_TOOLS`` enabled
* **Parallel tool calls**: 4 modes (``off`` / ``parallel_first_final`` / ``parallel_final`` / ``parallel_all``) to reduce iterations
* **Refresh strategy**: after each iteration, synthetic ``GetPageContent`` function message injected to keep LLM's view current (skip via FF ``AIFC_ADF_EDITOR_SKIP_GET_ADF_REFRESH``)
* **Time-to-first-bytes** tracked per turn (latency KPI)

Configuration / FF gates
==========================

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Feature flag
     - Effect
   * - ``AIFC_ADF_EDITOR_MAX_ITERATIONS``
     - Default 15; 5 if parallel mode on
   * - ``AIFC_ADF_EDITOR_PARALLEL_TOOL_CALL_MODE``
     - ``off`` / ``parallel_first_final`` / ``parallel_final`` / ``parallel_all``
   * - ``AIFC_ADF_CONTENT_SERVICE_TOOL_CALLS_FOR_TOOL``
     - Use content-service for ops instead of local executor
   * - ``AIFC_ADF_EDITOR_HTML_CONTEXT``
     - Seed/refresh as HTML instead of ADF
   * - ``AIFC_STRUCTURE_AWARE_TABLE_TOOLS``
     - Semantic table execution during streaming
   * - ``AIFC_MULTI_FORMAT_STREAMING``
     - ``contentType`` parameter for tools
   * - ``AIFC_BLANK_PAGE_CREATION_ROUTING``
     - Route blank pages to ``SimpleAdfGenerationMinion`` (append-only)
   * - ``CONVO_AI_ALLOW_INTENT_DETECTION_EVAL``
     - Skip execution for eval mode (test runs)
   * - ``AIFC_ADF_EDITOR_TOOL_ERROR_FEEDBACK``
     - Return operation error messages to LLM for retry

Known limitations
===================

#. **No new-page creation** — edit-only; blank pages route to ``SimpleAdfGenerationMinion`` (append-only fallback)
#. **Requires editor context** — needs active editor OR ``contentId + status`` (current/draft)
#. **Max 15 iterations** — runaway loops possible if LLM keeps repeating ops; tool-error feedback helps but doesn't always converge
#. **Selection fragment conversion** — user highlight passed as ADF or HTML depending on context mode; conversion can fail
#. **Function message history filtered** — excludes ``UrlRead`` results for current page (prevents redundancy) — may miss relevant context
#. **Backend flows can't use semantic table tools** — interception disabled when ``!isInBackendFlow`` (UI-only optimization)

Cross-references
==================

* :doc:`aifc` — AIFC umbrella (ADF editor is one of many AIFC features)
* :doc:`agent-framework` — minion infrastructure
* :doc:`../04-streaming-and-coroutines` — streaming patterns

