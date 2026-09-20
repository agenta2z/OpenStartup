.. _diag-tenant-identity:

================================================
Diagram 6 — Tenant Context & Identity Flow
================================================

Multi-tenant isolation is non-negotiable. This diagram shows how a request's tenant + user identity propagates from HTTP headers through every layer to the LLM provider.

End-to-end identity propagation
================================

.. mermaid::

   flowchart TB
       %% Origin
       UA[Customer Browser /<br/>Slack Bot / SDK]
       UA -->|HTTP request<br/>X-Slauth-Issuer<br/>X-Tenant-Context<br/>X-Cloud-Id| FILT

       %% Filter chain
       subgraph FC["Spring Filter Chain"]
           FILT[HeaderFilter<br/>foundation/utilities-impl/<br/>interceptors/HeaderFilter.kt]
           FILT --> RES1[Resolve TenantContext<br/>from X-Tenant-Context]
           FILT --> RES2[Resolve User<br/>from X-Slauth-Issuer]
           FILT --> RES3[Set MDC keys<br/>cloud_id, requestId, traceId]
       end

       FC --> ATTR

       %% Request attribute scope
       ATTR[Request Attributes<br/>TENANT_CONTEXT → TenantContext<br/>USER → User]

       ATTR -->|@RequestAttribute| CTL

       %% Controller
       subgraph CTLBLK["Controller (suspend fun)"]
           CTL[ChatV1Controller :167]
           CTL --> WRAP[withMdcContext { }<br/>:173]
           WRAP --> CHK[Experience allowlist :175<br/>Agent deactivation :181]
       end

       CTLBLK --> AC

       %% Platform
       subgraph PLAT["Platform Service Tier"]
           AC[AssistanceClient<br/>...WithPassThroughHeaders<br/>:219]
           AGS[AIGatewayClientServiceImpl<br/>:1067]
       end
       AC --> AGS

       %% AI Gateway out
       AGS -->|HTTP POST<br/>USE_CASE_ID :654<br/>CLOUD_ID :655<br/>USER_ID :656 ← invokingUser<br/>USER_CONTEXT :657<br/>X-Slauth-Issuer pass-through| AGW

       AGW[AI Gateway]
       AGW -->|provider headers| LLM[LLM Provider<br/>OpenAI/Anthropic/Google/DeepSeek]

       %% Style
       style FC fill:#fff8e1,stroke:#f57c00,stroke-width:2px
       style ATTR fill:#e1f5ff,stroke:#0277bd,stroke-width:2px
       style CTLBLK fill:#e8f5e9,stroke:#2e7d32
       style PLAT fill:#fce4ec,stroke:#c2185b
       style AGW fill:#ede7f6,stroke:#5e35b1,stroke-width:2px

How to read it
---------------

* **Vertical flow** = downward through the stack (HTTP → Spring → controller → platform → AI Gateway → LLM).
* Each **shaded box** is a stage that holds and may transform identity context.
* The **arrow labels** call out what gets passed/added at each hop.
* **PassThroughHeaders** is highlighted because it's the contract that retains the original ``X-Slauth-Issuer`` end-to-end.

The dual-principal model
=========================

The ``User`` class encapsulates two principals:

.. mermaid::

   classDiagram
       class User {
           +InvokingUser invokingUser
           +Principal accountId() AgentPrincipal or invoking
           +InvokingUser getInvokingUser() always human
       }

       class InvokingUser {
           +AccountId accountId
           +String userContextHeader
           +Locale locale
       }

       class AgentPrincipal {
           +AgentId agentId
           +String name
       }

       User "1" --> "1" InvokingUser : always
       User "1" --> "0..1" AgentPrincipal : optional

Key invariant (verified at ``AIGatewayClientServiceImpl.kt:656-657``):

.. code-block:: kotlin

   // Always attribute LLM usage to the invoking human user, even if
   // executing with an AgentPrincipal
   .header(AIGatewayHeaders.USER_ID,
           user.getInvokingUser().getAccountId().value())

**Why dual-principal?**

* Authorization checks ("can this agent access tenant X data?") use the AgentPrincipal — the agent is the one acting.
* Billing / quota / audit ("who incurred this LLM cost?") use the InvokingUser — the human who originated the request.

This split is what allows agents to act on behalf of users without skewing usage attribution.

The 4 attribution headers explained
=====================================

Every outbound LLM call sets these four headers (verified at lines 654-657):

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Header
     - Value source
     - What downstream uses it for
   * - ``USE_CASE_ID``
     - ``useCaseManager.getAiGatewayUseCaseId(aiGatewayContext)``
     - AI Gateway routing: which model defaults, which retry policy, which prompt-cache key
   * - ``CLOUD_ID``
     - ``aiGatewayContext.getAiGatewayCloudId()``
     - Multi-tenant attribution; per-tenant rate limits
   * - ``USER_ID``
     - ``user.getInvokingUser().getAccountId().value()``
     - Per-user quota tracking; auditing
   * - ``USER_CONTEXT``
     - ``user.getInvokingUser().getUserContextHeaderValue()``
     - Locale, consent state, additional opaque context

The pattern is repeated at line 2266+ in the same file — confirming it's a stable contract, not a one-off.

Patterns visible in this diagram
==================================

1. **Headers parsed once.** ``HeaderFilter`` parses headers and stashes resolved objects in request attributes. Controllers receive parsed objects via ``@RequestAttribute``, NOT raw headers.

2. **Identity propagates as headers AGAIN at the AI Gateway boundary.** Same identity, but explicitly re-encoded as headers because the AI Gateway is a separate process boundary.

3. **PassThroughHeaders preserves customer identity end-to-end.** The downstream services (AI Gateway, TCS, Statsig) re-validate ``X-Slauth-Issuer`` against the original customer-account ASAP token.

4. **Dual principal, single attribution.** The User has two principals; only the invoking-human attribution flows to the LLM provider for billing.

5. **MDC keys set in the filter, propagated by ``withMdcContext``.** The filter sets cloud_id, requestId, traceId on thread-local MDC; ``withMdcContext { }`` snapshots them so they survive coroutine suspension.

Failure modes
==============

If any stage drops identity:

* **Filter drops header** → ``UnauthorizedException`` at ``HeaderFilter``
* **Controller forgets ``withMdcContext``** → log lines after first suspend lose MDC keys (debugging nightmare; see :ref:`diag-mdc-state`)
* **AC forgets ``WithPassThroughHeaders``** → AI Gateway sees service-account ASAP, not customer's; rate limits / quotas attributed wrong
* **AGS forgets one of the 4 attribution headers** → AI Gateway rejects (or worse: bills wrong tenant)

These are all covered by integration tests (in ``convo-ai-test-integration``).

