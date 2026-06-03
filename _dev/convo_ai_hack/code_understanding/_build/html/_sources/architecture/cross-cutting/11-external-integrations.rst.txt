==============================================
External Integrations Reference
==============================================

This page documents all external systems convoai integrates with —
their client classes, auth methods, retry/resilience patterns, and
observability hooks.

Integration topology
======================

.. mermaid::

   graph LR
     A[convoai] -->|gRPC + HTTP/SSE| B[AI Gateway]
     B --> C[OpenAI]
     B --> D[Anthropic]
     B --> E[Google Gemini]
     B --> F[Bedrock<br/>Llama]
     B --> G[Fireworks<br/>DeepSeek<br/>NexusFlow]
     A -->|GraphQL via SLAuth| H[AGG Gateway]
     H --> I[Jira]
     H --> J[Confluence]
     H --> K[Bitbucket]
     A -->|gRPC| L[Teamserve<br/>Embeddings]
     A -->|HTTP via SLAuth| M[ORS<br/>Object Resolver]
     A -->|HTTP via SLAuth| N[HelpKosh]
     A -->|HTTP via SLAuth| O[Kamino]
     A -->|HTTP via SLAuth| P[Tecton<br/>Features]
     A -->|HTTP| Q[Statsig<br/>Feature Flags]
     A -->|metric SDK| R[SignalFX + Splunk]
     A -->|trace SDK| S[ARIZE + Splunk]
     A -->|WebSocket| T[Twilio<br/>Voice Relay]
     T --> U[OpenAI Realtime API]

Per-integration contracts
============================

AI Gateway (most-critical integration)
-----------------------------------------

* **Class**: ``AIGatewayClientServiceImpl`` (3000+ LoC, ``platform/service/service-impl/``)
* **Config**: ``AIGatewayClientConfiguration`` (builder with retry policies)
* **Models routed through**: 8 LLMs (OpenAI, Anthropic, Google Gemini, Bedrock Llama, Fireworks, DeepSeek, NexusFlow)
* **Protocol**: gRPC (for grpc-supported models) + HTTP SSE (streaming)
* **Auth**: SLAuth egress tokens
* **Streaming**: per-model streaming wrapper; chunk-by-chunk processing via ``InterceptingChunkProcessor``
* **Error handling**: ``executeWithErrorCategorization()`` wrapper classifies into: rate-limit, timeout, content-policy-violation, server-error, network
* **Fallback**: per-model fallback chains; if primary model fails, secondary attempted
* **Metrics**: ``MetricsService.send()`` per call, tagged with model, error category

Atlassian product integrations (Jira, Confluence, Bitbucket)
--------------------------------------------------------------

* **Routed via**: AGG (Atlassian GraphQL Gateway) — single GraphQL endpoint, federated subgraphs
* **Class**: ``AggWebClient`` family in ``platform/client/client-impl/``
* **Config**: ``AggWebClientConfiguration`` (24MB codec limit, experimental APIs enabled)
* **Auth**: SLAuth Egress headers (``X-Slauth-Egress: true``, ``X-Slauth-Audience: graphql-gateway``)
* **Header propagation**: Reactor context → MDC fallback for ``X-Test-Case-Id``, ``X-Forwarded-Host``
* **Resilience**: per-service circuit breaker via ``AggResilienceProvider``; FF-gated by ``CONVO_AI_AGG_PER_SVC_CB``
* **Tenant context**: ``X-Forwarded-Host`` carries tenant domain; auto-set from request

**Per-product specifics**:

.. list-table::
   :header-rows: 1
   :widths: 18 38 44

   * - Product
     - Module
     - Notes
   * - Jira
     - ``platform/client/client-impl/.../jira/``
     - 702 files referencing Jira; biggest integration
   * - Confluence
     - ``platform/client/client-impl/.../confluence/``
     - 617 files referencing Confluence; ADF editor integration
   * - Bitbucket
     - ``platform/client/client-impl/.../bitbucket/``
     - 87 files; lighter integration
   * - Loom
     - ``modules/loom/``
     - Video transcript analysis
   * - Compass
     - ``platform/client/client-impl/.../compass/``
     - Service catalog integration

Observability integrations
----------------------------

* **SignalFX (metrics)**: via Micrometer; primary metric backend
* **Splunk (metrics + logs)**: dual-write for high-cardinality logs
* **ARIZE (LLM observability)**: ``CSMArizeSpanWriter`` (1023 LoC); per-LLM-call span capture
* **OpenTelemetry traces**: emit to ``OPENTRACING_AGENT_HOST`` + ``OPENTRACING_AGENT_PORT``

Identity integrations
-----------------------

* **SLAuth**: service-to-service egress tokens (sidecar at ``platform-slauth-1`` container)
* **ASAP**: signed-request inter-service auth (key id, audience, issuer)
* **TCS (Tenant Context Service)**: tenant resolution sidecar; cloudId → tenant metadata
* **OAuth (third-party)**: ``THIRD_PARTY_OAUTH`` for user-scoped access tokens

Internal integrations
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - System
     - Purpose
   * - **Teamserve**
     - LLM model routing + embeddings (gRPC)
   * - **ORS** (Object Resolver Service)
     - URL → object metadata
   * - **HelpKosh**
     - Help content
   * - **Kamino**
     - Internal data service
   * - **Tecton**
     - Feature store (user-document embeddings)
   * - **MecclesService**
     - Internal eval service
   * - **PassageReranking**
     - Search result reranking

Resilience patterns
=====================

Circuit breakers
------------------

* **Library**: resilience4j
* **Provider**: ``AggResilienceProvider`` (per-service registry)
* **FF gate**: ``CONVO_AI_AGG_PER_SVC_CB`` (controlled rollout)
* **Defaults**: per-service config (sliding window, failure rate threshold, wait duration)

.. code-block:: kotlin

   val breaker: CircuitBreaker? =
       rolloutService.controlledByFullContext(CONVO_AI_AGG_PER_SVC_CB)
           .ofNewCode { CircuitBreaker.of(serviceName, config) }

   breaker?.executeSupplier { ... } ?: fallback()

Retries
---------

* **AI Gateway**: per-model retry policy in ``AsyncBuilder``
* **AGG**: HTTP retry on 5xx + transient network errors
* **gRPC**: gRPC retry policy on UNAVAILABLE + DEADLINE_EXCEEDED
* **No global retry decorator** — opt-in per call site

Timeouts
----------

* **HTTP**: WebClient default 10s; some clients override (e.g., AI Gateway 60s for streaming)
* **gRPC**: 30s default
* **Streaming**: no timeout on stream; per-chunk timeout instead

Observability per integration
================================

Standard metric tags:

* ``service`` — target external system
* ``operation`` — endpoint/method name
* ``status`` — success/error
* ``error_category`` — when error: rate_limit, timeout, server_error, network, content_policy

**Latency histograms** for each integration; **error rates** with category breakdown.

Adding a new integration (step-by-step)
==========================================

#. **Define configuration** in ``application.yml``:

   .. code-block:: yaml

      myservice:
        baseUrl: ${MESH_DEPENDENCY_MYSERVICE_BASE_URL}
        timeout: 10s

#. **Create configuration properties class**:

   .. code-block:: kotlin

      @ConfigurationProperties("myservice")
      data class MyServiceConfig(
          val baseUrl: String,
          val timeout: Duration,
      )

#. **Create WebClient bean**:

   .. code-block:: kotlin

      @Configuration
      class MyServiceConfiguration {
          @Bean fun myServiceWebClient(cfg: MyServiceConfig): WebClient =
              WebClientConfiguration.createWebClient()
                  .baseUrl(cfg.baseUrl)
                  .defaultHeader(X_SLAUTH_EGRESS_HEADER, "true")
                  .defaultHeader(X_SLAUTH_AUDIENCE_HEADER, "myservice")
                  .build()
      }

#. **Create client wrapper**:

   .. code-block:: kotlin

      @Component
      class MyServiceClient(
          private val webClient: WebClient,
          private val metricsService: MetricsService,
      ) {
          suspend fun getData(id: String): MyData =
              executeWithErrorCategorization("myservice", "getData") {
                  webClient.get().uri("/data/{id}", id).retrieve()
                      .awaitBody<MyData>()
              }
      }

#. **Add circuit breaker** (optional):

   .. code-block:: kotlin

      val breaker = aggResilienceProvider.getBreaker("myservice")
      breaker?.executeSupplier { ... }

#. **Add to integration tests** with WireMock stub:

   .. code-block:: kotlin

      wireMockServer.stubFor(get("/data/abc")
          .willReturn(aResponse().withBody("""{"id":"abc"}""")))

#. **Document in this page** — add row to integration topology table.

Honest limitations
====================

* No global rate-limiting middleware — per-client implementation varies
* Circuit breakers FF-gated; not all services protected yet
* No automated client SDK generation from OpenAPI specs
* Integration test sandboxes mock SLAuth via local sidecar; production uses real SLAuth
