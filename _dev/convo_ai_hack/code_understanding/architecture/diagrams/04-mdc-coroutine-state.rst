.. _diag-mdc-state:

================================================
Diagram 4 — MDC + Coroutine Context Lifecycle
================================================

The **#1 source of subtle bugs** in this codebase is MDC loss across coroutine suspensions. This diagram makes the lifecycle explicit so reviewers can spot violations in PRs.

The "good" lifecycle (with ``withMdcContext``)
================================================

.. mermaid::

   stateDiagram-v2
       direction TB
       [*] --> RequestArrives

       state "Spring Filter Chain" as Filter {
           RequestArrives --> ParseHeaders
           ParseHeaders --> SetMDC: cloud_id, requestId,<br/>traceId set on thread-local MDC
           SetMDC --> StashAttributes: TenantContext, User<br/>stashed in request attributes
       }

       Filter --> ControllerEntry: forward to controller

       state "Controller (suspend fun)" as CtrlScope {
           ControllerEntry --> WrapMDC: call withMdcContext { }
           WrapMDC --> SnapshotMDC: snapshot current MDC<br/>into coroutine context
       }

       CtrlScope --> SuspendPoint1: first suspend call<br/>(e.g. agentService.isDeactivated)

       state "Coroutine suspends" as Susp1 {
           SuspendPoint1 --> ThreadAFreed: thread A returned to pool
           ThreadAFreed --> WaitingOnIO: waiting for downstream
           WaitingOnIO --> ResumeOnThreadB: callback fires on thread B
           ResumeOnThreadB --> RestoreMDC: MDC snapshot restored<br/>onto thread B
       }

       Susp1 --> ContinueExecution: thread B has<br/>same MDC keys
       ContinueExecution --> LogStmt1: log.info(...)<br/>✅ HAS cloud_id, requestId, traceId
       LogStmt1 --> StreamingLoop

       state "Streaming Loop" as StreamLoop {
           StreamingLoop --> EmitChunk: chunk emitted to Flux
           EmitChunk --> SuspendForNext: suspend until next chunk
           SuspendForNext --> ResumeOnThreadX: may resume on any thread
           ResumeOnThreadX --> RestoreMDCAgain: MDC restored
           RestoreMDCAgain --> StreamingLoop: next iteration
       }

       StreamLoop --> StreamComplete: LLM done
       StreamComplete --> [*]

The "bad" lifecycle (without ``withMdcContext``)
=================================================

.. mermaid::

   stateDiagram-v2
       direction TB
       [*] --> RequestArrives_bad

       state "Spring Filter Chain" as Filter_bad {
           RequestArrives_bad --> SetMDC_bad: MDC set on thread A
       }

       Filter_bad --> ControllerEntry_bad: forward

       state "Controller (no withMdcContext)" as CtrlBad {
           ControllerEntry_bad --> Log1_bad: log.info("starting")<br/>✅ MDC PRESENT
           Log1_bad --> SuspendCall_bad: agentService.isDeactivated(...)
       }

       CtrlBad --> Susp_bad: coroutine suspends

       state "Resumes on thread B" as ResumeBad {
           Susp_bad --> ThreadBNoMDC: thread B has<br/>EMPTY thread-local MDC
       }

       ResumeBad --> Log2_bad: log.info("after suspend")<br/>❌ NO cloud_id, NO requestId,<br/>❌ NO traceId
       Log2_bad --> Debug_nightmare: Logs are<br/>untraceable
       Debug_nightmare --> [*]

How to read it
---------------

* The **state diagram** shows the **lifecycle of MDC keys** over time, not the call sequence.
* Each box is a state of "what does the MDC look like right now?".
* **Arrows are state transitions** (suspend, resume, log call).
* The **good** version stays in MDC-populated states; the **bad** version transitions to MDC-empty states after the first suspend.

Why this happens
=================

* Standard SLF4J ``MDC`` is **thread-local** (uses ``ThreadLocal<Map<String, String>>``).
* Kotlin coroutines suspend → state machine returns control to the dispatcher → eventually resumes on **a different thread**.
* The new thread doesn't have the suspended coroutine's MDC; its own MDC is empty (or worse, stale from a prior request).
* Result: log lines after the first suspend lose all keys.

The fix: ``MdcLoggingContext.withMdcContext { }``
====================================================

The function (in ``foundation/utilities/logging/``) does the following dance:

.. mermaid::

   sequenceDiagram
       participant Caller
       participant Wrap as withMdcContext { block }
       participant CC as Coroutine Context
       participant Block as { ... your code ... }

       Caller->>Wrap: invoke
       Wrap->>Wrap: snapshot current MDC (Map<K,V>)
       Wrap->>CC: install MDCContext(snapshot)<br/>as a coroutine context element
       Wrap->>Block: execute with extended context

       Note over Block: ... runs your code ...

       loop on every suspend / resume
           Block->>CC: suspend point
           CC->>CC: install snapshot onto<br/>resuming thread's MDC
           Block->>Block: continue execution<br/>(MDC populated)
       end

       Block-->>Wrap: completes
       Wrap->>Wrap: restore caller's prior MDC
       Wrap-->>Caller: return value

The MDC snapshot becomes a **coroutine context element**, which is propagated automatically across suspensions via the ``kotlinx-coroutines-slf4j`` library (the ``MDCContext`` class).

Verified usage
================

* ``ChatV1Controller.kt:173`` — wraps the entire streaming endpoint body in ``withMdcContext { }``
* AGENTS.md lines 35-36 — documents the rule
* AGENTS.md line 39 — corollary: raw ``Dispatchers.IO`` and ``Dispatchers.Default`` are forbidden because they don't carry the MDC context

The GraphQL equivalent
=======================

Spring's ``RequestContextHolder`` is also thread-local. Suspend GraphQL handlers (``@QueryMapping``, ``@MutationMapping``) face the same problem with request attributes (TenantContext, User).

The fix: ``withRequestAttributesContext { }`` (AGENTS.md lines 31-33).

The pattern is identical: snapshot, install as coroutine element, propagate, restore.

How a reviewer spots violations
=================================

In a PR diff, look for:

1. **A new ``suspend fun`` in a controller without a ``withMdcContext { }`` wrap.**
2. **A use of ``Dispatchers.IO`` or ``Dispatchers.Default`` instead of ``CoroutineContextProvider``.**
3. **A ``@QueryMapping suspend fun`` without ``withRequestAttributesContext { }``.**
4. **A ``flow { }`` builder that emits inside a ``Dispatchers.*`` switch.**

All four are code-review red flags backed by the foundation invariant that "suspend = MDC must be coroutine-bound, not thread-bound".

