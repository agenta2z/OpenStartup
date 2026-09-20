=========================================
05 — Authentication & Security
=========================================

.. contents:: On this page
   :depth: 3
   :local:

Overview
--------

Proactive-AI-Platform is an **internal-ingress** Atlassian Micros service.
All inbound HTTP traffic passes through the Micros service-proxy (Envoy)
which enforces authentication via SLAUTH (ASAP-based service-to-service
auth) and authorisation via POCO (Policy Controller) before requests reach
the Spring Boot application.

Authentication Stack
--------------------

Service-Proxy (Envoy) Plugins
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Configured in ``service-descriptor.sd.yml → serviceProxy``:

.. code-block:: yaml

   ingress:
     authentication:
       enabled: true
   plugins:
     auth:
       authentication:
         plugins:
           - type: asap            # ASAP JWT token verification
           - type: slauthtoken     # SLAUTH token verification
           - type: build           # Build-time token support
           - type: usercontext     # User-Context header extraction
           - type: staffcontext    # Staff-Context header extraction
       authorization:
         plugins:
           - type: poco            # Policy Controller enforcement

The proxy validates every request's ASAP/SLAUTH token *before* it reaches
the JVM, extracting the authenticated principal (issuer) and optionally
the ``User-Context`` header.

SLAUTH Configuration (application.yml)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

   micros:
     security:
       slauth:
         poco-enabled: true
         poco:
           enforce-enabled: true
         default-granted-role: access
         ingress:
           enabled: true
       enabled: true

Key settings:

- ``poco-enabled: true`` + ``enforce-enabled: true`` — POCO policy
  enforcement is active (not audit-only).
- ``default-granted-role: access`` — authenticated principals receive the
  ``access`` role by default.
- ``ingress.enabled: true`` — SLAUTH ingress validation is on.

MvcSecurityConfig (Spring-side)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: kotlin

   @Configuration
   class MvcSecurityConfig {
       @Bean(name = [MicrosSecurityConstants.CUSTOM_ANONYMOUS_PATHS])
       fun anonymousPaths(): List<String> = listOf("/healthcheck", "/deepcheck")
   }

Only ``/healthcheck`` and ``/deepcheck`` are exempted from authentication
at the Spring Security level, matching the POCO open-principal rules.

POCO Policy Structure
---------------------

The authorisation policy is defined in
``src/main/resources/policies/service/policy.json`` with **6 allow rules**:

.. list-table::
   :header-rows: 1
   :widths: 40 12 18 30

   * - Description
     - Methods
     - Paths
     - Principals
   * - Rovo Insights endpoints
     - POST
     - ``/api/v1/rovo/insights/*``
     - ``micros/convo-ai``, ``micros/edge-authenticator``
   * - Charlie greeting (sample)
     - GET
     - ``/greetings/charlie``
     - ``micros/charlie``
   * - Nudge endpoint
     - POST
     - ``/api/v1/nudge/*``
     - ``micros/convo-ai``
   * - Rovo Insights async submit
     - POST
     - ``/api/v1/rovo-insights/*``
     - ``micros/convo-ai``
   * - Stratus test agent
     - POST
     - ``/stratus/test/**``
     - ``micros/charlie``, ``micros/edge-authenticator``
   * - Swagger / OpenAPI spec
     - GET
     - ``/api/swagger-ui/**``, ``/api/openapi/**``
     - **open** (publicly accessible)
   * - Health checks
     - GET
     - ``/healthcheck``, ``/deepcheck``
     - **open**

Policy Tests
^^^^^^^^^^^^

``src/main/resources/policies/tests.json`` contains 5 test cases that
validate the POCO rules via ``poco-policy-test.sh``:

1. ``charlie can get greeting via ASAP`` → allowed
2. ``anyone can get swagger`` → allowed (open)
3. ``non charlie cannot get charlie greeting`` → denied
4. ``healthcheck`` → allowed (open)
5. ``deepcheck`` → allowed (open)

Request Authentication Flow
---------------------------

.. code-block:: text

   Client
     │
     ▼
   ┌──────────────────────────┐
   │  Service Proxy (Envoy)   │
   │  ┌─────────────────────┐ │
   │  │ ASAP / SLAUTH token │ │  ← JWT verification
   │  │ validation          │ │
   │  └────────┬────────────┘ │
   │  ┌────────▼────────────┐ │
   │  │ POCO policy check   │ │  ← path + method + principal matching
   │  └────────┬────────────┘ │
   │  ┌────────▼────────────┐ │
   │  │ User-Context header │ │  ← usercontext plugin extracts UCT
   │  │ injection           │ │
   │  └────────┬────────────┘ │
   └───────────┼──────────────┘
               ▼
   ┌──────────────────────────┐
   │  Spring Boot Application │
   │  ┌─────────────────────┐ │
   │  │ MvcSecurityConfig   │ │  ← anonymous paths: /healthcheck, /deepcheck
   │  └────────┬────────────┘ │
   │  ┌────────▼────────────┐ │
   │  │ RequestContext      │ │  ← sets up request-scoped values,
   │  │ Interceptor (ord 1) │ │     feature-flag context, logging context
   │  └────────┬────────────┘ │
   │  ┌────────▼────────────┐ │
   │  │ UserContext         │ │  ← extracts User from User-Context header
   │  │ Interceptor (ord 2) │ │     via UserContextService; stores as
   │  └────────┬────────────┘ │     request attribute
   │           ▼              │
   │       Controller         │
   └──────────────────────────┘

Egress Authentication
---------------------

Outbound service-to-service calls use ASAP mutual TLS via the service
proxy's egress configuration:

.. code-block:: yaml

   egress:
     authentication:
       enabled: true
     dependencies:
       - name: id-gatekeeper      # timeout: 20 s
       - name: ai-gateway         # timeout: 600 s (10 min — LLM calls)
       - name: integrations-service  # timeout: 60 s

All egress dependencies use a retry policy on 5xx and 429 status codes.

User Context Extraction
-----------------------

``UserContextInterceptor`` (order 2 in the interceptor chain):

1. Reads the ``User-Context`` header via ``UserContextService``.
2. Builds a ``UserImpl`` with the decoded ``AccountId`` and extra context
   (``X-Forwarded-For``, ``X-Forwarded-Host``).
3. Stores the ``User`` as a servlet request attribute (key: ``user``).
4. Controllers access the user via ``@RequestAttribute("user") user: User``.

If the header is absent or unparseable the interceptor logs an info/warn
and continues — the request is not rejected (POCO already handled authZ).
