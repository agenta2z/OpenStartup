.. _identity-and-auth:

============================
Identity & Authentication
============================

The platform uses **SLAuth** (Atlassian's internal service-to-service auth) for ingress and **ASAP** (Atlassian Service Authentication Protocol — JWT-based) for token issuance.

The User object
================

**Lives in:** ``modules/foundation/utilities/utilities-api/src/main/kotlin/io/atlassian/micros/convoai/foundation/utilities/identity/`` (verified directory)

The ``User`` class encapsulates two principals:

1. **The invoking user** — the human (or service account) that originated the request. Always populated.
2. **The agent principal** (optional) — when an agent acts on the user's behalf, this carries the agent's identity.

Why two principals?

Per the AI Gateway attribution pattern (``AIGatewayClientServiceImpl.kt:657``):

.. code-block:: kotlin

   // Always attribute LLM usage to the invoking human user, even if executing with an AgentPrincipal
   .header(AIGatewayHeaders.USER_ID, user.getInvokingUser().getAccountId().value())

LLM usage cost MUST be attributed to the human, not the service. But authorization checks ("can this agent access tenant X's data?") use the agent principal.

The ``user.getInvokingUser()`` method always returns the human; ``user.getAccountId()`` returns whichever principal the request runs as.

Authentication flow
====================

1. **Ingress** — HTTP request arrives with ``X-Slauth-Issuer`` header (the service-account ASAP token)
2. **Spring Security filter chain** — validates ASAP signature, extracts issuer
3. **HeaderFilter** (``foundation/utilities/utilities-impl/.../interceptors/HeaderFilter.kt``) — resolves issuer + tenant context into a ``User`` object
4. **Controller** — receives ``User`` via ``@RequestAttribute(USER) user: User``
5. **Downstream calls** — pass the ``X-Slauth-Issuer`` header through (``...WithPassThroughHeaders`` pattern) so downstream services re-validate

ASAP token caching
===================

The Application class (``modules/service/convo-ai-docker-image/.../Application.kt``) and the integration-tests sandbox both reference ASAP token caches. Per the integration-test logs:

.. code-block::

   ASAP signed request cache initialised for: issuer=micros/responsible-ai-api,
   keyId=micros/responsible-ai-api/responsible-ai-api-oe71il9bdu9k3iqs,
   refreshAfter=PT1M, evictAfter=PT3M, tokenExpiry=PT5M

So tokens are minted, cached, refreshed every 1 minute, evicted after 3 minutes, and expire after 5 minutes (signed lifetime). The cache prevents per-request CPU cost of signing.

The @CustomerAccountAllowed annotation
=======================================

Verified at ``ChatV1Controller.kt:165``. By default, the platform's filter chain rejects requests from customer-account ASAP issuers (only service-account issuers allowed). The ``@CustomerAccountAllowed`` annotation **opts in** the endpoint to accept customer-originated requests.

This is a security gate — most internal-only endpoints don't have it.

Patterns
=========

1. **Always attribute to invoking human.** ``user.getInvokingUser()`` for any external billing/quota/audit decision.

2. **Pass through SLAuth headers.** Don't re-mint; downstream services validate the original issuer.

3. **Customer-allowed is opt-in.** New endpoints default to service-only unless ``@CustomerAccountAllowed`` is added.

4. **ASAP cache is mandatory.** Per-request signing is too expensive; rely on the cache.

What you would change here
===========================

- **Add an endpoint accessible to customers** → annotate with ``@CustomerAccountAllowed``
- **Change attribution semantics** → modify the User class + AI Gateway header construction
- **Add a new ASAP issuer** → register in deploy descriptor + Atlassian identity service

What you would NOT change here
===============================

- ASAP cache config (lives in deploy descriptor)
- SLAuth filter chain (lives in Spring Security config)

