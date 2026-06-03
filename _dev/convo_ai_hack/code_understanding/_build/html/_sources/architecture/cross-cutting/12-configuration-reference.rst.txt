==========================================
Configuration Reference
==========================================

This page documents the configuration architecture of convoai —
property files, environment variables, feature flags, and secret
management.

Configuration file inventory
==============================

.. list-table::
   :header-rows: 1
   :widths: 50 25 25

   * - File
     - Scope
     - Profile
   * - ``service/convo-ai-docker-image/.../application.yml``
     - Master config (~600 lines)
     - default
   * - ``service/convo-ai-docker-image/.../application-local-prod.yml``
     - Local dev, prod-like URLs
     - ``local-prod``
   * - ``service/convo-ai-docker-image/.../application-staging.yml``
     - Staging deployment
     - ``staging``
   * - ``service/convo-ai-docker-image/.../application-prod.yml``
     - Prod deployment
     - ``prod``
   * - Per-module ``application.yml``
     - Module-scoped overrides
     - inherits parent

**Profile activation**: ``SPRING_PROFILES_ACTIVE`` env var. Multiple profiles can be active (e.g., ``local-prod,debug``).

**Override precedence** (lowest → highest):

#. ``application.yml`` defaults
#. ``application-{profile}.yml``
#. Environment variables (e.g., ``${MESH_DEPENDENCY_AI_GATEWAY_BASE_URL}``)
#. System properties (``-Dprop=value``)
#. K8s ConfigMaps / Secrets (mounted as env vars)

Configuration hierarchy
=========================

YAML files use ``---`` to split per-profile sections inside one file:

.. code-block:: yaml

   # Default section
   server:
     port: 8080
   ---
   spring:
     config:
       activate:
         on-profile: staging
   server:
     port: 8443

Placeholder substitution: ``${VAR}`` or ``${VAR:default}``. Missing required vars cause startup failure.

@ConfigurationProperties classes (typed config)
==================================================

Pattern:

.. code-block:: kotlin

   @Validated
   @ConfigurationProperties(prefix = "teamserve")
   data class TeamserveProperties(
       val environment: TeamserveEnvironment,    // DEV, STG, PROD
       val port: Int = 443,
       @field:Valid val models: Map<String, TeamserveModelConfig>,
       @field:Valid val passagereranking: PassageRerankingConsumerSettings,
   )

**Major config classes**:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Class
     - Purpose
   * - ``TeamserveProperties``
     - LLM model routing, gRPC host derivation
   * - ``KaminoClientConfiguration``
     - Internal data service client (URLs via @Value)
   * - ``OrsConfig``, ``OrsClientConfig``
     - Object Resolver Service clients
   * - ``AIGatewayClientConfiguration``
     - AI Gateway client setup (8 LLM models)
   * - ``AggWebClientConfiguration``
     - AGG GraphQL gateway (24MB codec limit, SLAuth)
   * - per-product ``*ClientConfiguration``
     - Each product owns its client config

**Validation**: ``@Validated`` + ``@field:Valid`` enforce bean validation at startup. Missing required fields throw ``ConfigurationException``.

Environment variables
=======================

**Naming convention**: K8s style — ``MESH_DEPENDENCY_*_BASE_URL`` for service mesh endpoints.

**Critical vars**:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Variable
     - Purpose
   * - ``SPRING_PROFILES_ACTIVE``
     - Profile selection (e.g., ``staging``, ``prod``, ``local-prod``)
   * - ``MESH_DEPENDENCY_AI_GATEWAY_BASE_URL``
     - AI Gateway endpoint
   * - ``MESH_DEPENDENCY_AGG_BASE_URL``
     - AGG GraphQL Gateway endpoint
   * - ``TCS_SIDECAR_HOST`` + ``TCS_SIDECAR_HTTP_PORT``
     - Tenant Context Service sidecar
   * - ``ATLASSIAN_API_USER_NAME``, ``ATLASSIAN_API_KEY``
     - Atlassian internal API auth
   * - ``ATLASSIAN_HELLO_SESSION_KEY``
     - Atlassian Hello integration
   * - ``STATSIG_SDK_KEY``
     - Feature flag service auth
   * - ``OPENTRACING_AGENT_HOST`` + ``OPENTRACING_AGENT_PORT``
     - Trace export
   * - ``MESH_DEPENDENCY_*_BASE_URL`` (50+ services)
     - Per-dependency endpoints

Feature flag naming convention
================================

**Statsig** is the platform; **Kotlin enums** wrap each feature gate.

**Naming patterns**:

* **Kotlin enum**: ``{Module}FeatureFlags`` (e.g., ``CSMFeatureFlags``, ``AgentStudioFeatureFlags``, ``JsmFeatureFlags``)
* **Statsig key**: ``snake_case`` matching the enum value (e.g., enum ``ENABLE_NEW_ROUTER`` → key ``enable_new_router``)
* **Schema classes**: ``*StatsigSchema.kt`` for typed dynamic config (``VoiceConfigStatsigSchema``, ``SearchServiceStatsigSchema``)

**Adding a new flag**:

#. Add enum entry in ``modules/.../{Feature}FeatureFlags.kt``:

   .. code-block:: kotlin

      enum class JsmFeatureFlags(override val key: String) : FeatureFlag {
          MY_NEW_FEATURE("my_new_feature"),
      }

#. Register in Statsig dashboard with default value

#. Use via ``rolloutService``:

   .. code-block:: kotlin

      val isEnabled = rolloutService
          .controlledByLimitedContext(JsmFeatureFlags.MY_NEW_FEATURE)
          .isEnabled

      // or for replacing-with pattern:
      val provider = rolloutService
          .controlledByLimitedContext(JsmFeatureFlags.MY_NEW_FEATURE)
          .replacingSuspend { oldImpl }
          .with { newImpl }
          .value

#. Add observability metric:

   .. code-block:: kotlin

      LlmUsageTrackingIds.MY_NEW_FEATURE   // for LLM usage tracking
      MetricKey.MY_NEW_FEATURE_HITS         // for general metrics

Secret management
===================

**Layers**:

#. **K8s Secrets** → environment variables (production)

   * Mounted via K8s deployment YAML
   * Pattern: secret resource ``my-secret`` → env var ``MY_SECRET``
   * Convention: secrets injected by Helm chart in ``modules/service/convo-ai-docker-image/helm/``

#. **SLAuth-managed** (inter-service)

   * SLAuth sidecar handles service-to-service tokens
   * No keys in app code; sidecar has key material

#. **ASAP keys** (inter-service signed requests)

   * Key id, audience, issuer in config
   * Private key in K8s Secret, loaded by sidecar

#. **Local dev**

   * ``application-local-prod.yml`` references env vars
   * ``.env`` file in repo root (NOT committed) for local dev secrets
   * Bootstrap script (``setup_local.sh``, ``bin/first-run``) prompts for local creds

**NEVER**:

* Commit secrets to git
* Hardcode in YAML (use ``${ENV_VAR}`` only)
* Log full secret values

Common misconfigurations (top 5 deployment pitfalls)
======================================================

#. **Missing ``MESH_DEPENDENCY_*_BASE_URL``**

   * Symptom: ``IllegalArgumentException: Could not resolve placeholder``
   * Fix: Verify all 50+ mesh URLs in ConfigMap

#. **Wrong profile activated**

   * Symptom: Staging URLs in prod, or localhost in production
   * Fix: Check ``SPRING_PROFILES_ACTIVE``; ensure profile YAML loaded

#. **Statsig SDK key stale**

   * Symptom: All feature flags return defaults; no error
   * Fix: Verify ``STATSIG_SDK_KEY`` is current (rotates periodically)

#. **Incomplete @ConfigurationProperties validation**

   * Symptom: ``NullPointerException`` when accessing nested config
   * Fix: Mark required fields without defaults; use ``@Validated``

#. **Statsig user attributes empty**

   * Symptom: Limited-context FFs always return false
   * Fix: Verify TCS sidecar reachable; cloudId resolves to tenant ID; user attributes populated

Configuration testing
=======================

**Unit tests**: ``@SpringBootTest(properties = [...])`` to override config inline:

.. code-block:: kotlin

   @SpringBootTest(
       properties = [
           "myservice.baseUrl=http://localhost:9999",
           "myservice.timeout=1s",
       ]
   )
   class MyServiceTest { ... }

**Integration tests**: Use ``@TestConfiguration`` to wire test beans; ``WireMock`` for external service stubs.

**Profile-specific test**: Activate test profile via ``@ActiveProfiles("test")``.

Adding new configuration (step-by-step)
==========================================

#. **Define properties class** (typed config):

   .. code-block:: kotlin

      @Validated
      @ConfigurationProperties(prefix = "myservice")
      data class MyServiceProperties(
          val apiUrl: String,
          val timeout: Duration = Duration.ofSeconds(10),
      )

#. **Add to ``application.yml``**:

   .. code-block:: yaml

      myservice:
        apiUrl: ${MYSERVICE_BASE_URL}
        timeout: 15s

#. **Register Spring bean**:

   .. code-block:: kotlin

      @Configuration
      class MyServiceConfiguration {
          @Bean fun myService(props: MyServiceProperties) =
              MyServiceImpl(props.apiUrl, props.timeout)
      }

#. **For K8s deployment**:

   * Add env var to ConfigMap: ``MYSERVICE_BASE_URL: https://...``
   * Or to Secret if sensitive (e.g., API keys)

#. **Document in this file** — add row to env vars table.

Open questions
================

* Is there a single "config reference doc" that lists every env var and its default? (No — would be valuable.)
* How are secrets rotated? (Statsig SDK key rotation procedure not documented.)
* What's the test profile for ``@SpringBootTest``? (``local-prod`` is implicit; should be explicit.)


==================================================
Marathon FF Composition (added 2026-05-03)
==================================================

There are **3 independent Marathon feature flags** in ``RovoSpecificFeatureFlags.kt``
that compose to define Marathon's runtime behavior. They are NOT hierarchical.

Marathon FF Definitions
========================

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - FF Flag
     - File:Line
     - Purpose
   * - **ROVO_CHAT_USE_MARATHON_AGENT**
     - ``RovoSpecificFeatureFlags.kt:688``
     - **Primary gate**: enables Marathon for standard Rovo Chat agents (default: legacy A2A executor)
   * - **ROVO_MARATHON_ALPHA_MODE**
     - ``RovoSpecificFeatureFlags.kt:728``
     - **Behavioral modifier**: changes Marathon's internal orchestration strategy (alpha/experimental mode)
   * - **ROVO_MARATHON_USE_ASSP**
     - ``RovoSpecificFeatureFlags.kt:747``
     - **Infrastructure gate**: enables Async Service Scaling Protocol (ASSP) for tool execution + file operations

Composition Rules
==================

#. ``USE_MARATHON_AGENT`` must be **ON** to use Marathon at all
#. ``ALPHA_MODE`` modifies *how* Marathon runs (only evaluated if #1 is ON)
#. ``USE_ASSP`` independently gates ASSP protocol usage **at multiple
   tool handler call sites** (orthogonal to Marathon enablement)

Possible Request States
=========================

::

   (Marathon=ON,  AlphaMode=OFF, ASSP=OFF) — Standard Marathon, legacy protocol
   (Marathon=ON,  AlphaMode=OFF, ASSP=ON)  — Standard Marathon, ASSP protocol
   (Marathon=ON,  AlphaMode=ON,  ASSP=OFF) — Alpha mode, legacy
   (Marathon=ON,  AlphaMode=ON,  ASSP=ON)  — Alpha mode + ASSP
   (Marathon=OFF, *,             *)        — Marathon disabled (legacy A2A used)

**Implication**: "Marathon at 50%" is **ambiguous** — could be referring to
any of the 3 FFs. Always specify which FF when discussing rollout %.

Marathon FF Use Sites
======================

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - FF
     - Use sites
   * - ``ROVO_CHAT_USE_MARATHON_AGENT``
     - ``RovoChatExecutor.kt:1498``, ``RovoChatAsyncTaskLauncher.kt:483,960``, ``RovoChatAgentExecutionService.kt:404``
   * - ``ROVO_MARATHON_ALPHA_MODE``
     - ``RovoChatAgentExecutionService.kt:1039``
   * - ``ROVO_MARATHON_USE_ASSP``
     - ``RuntimeBackendUploader.kt:148,802,857``, ``MarathonClient.kt:62,713,2130``, ``SaveFileForUserMcpTool.kt:117,212``

==================================================
HybridOrchestratorFeatureFlags Enum (added 2026-05-03)
==================================================

A SEPARATE FF system from ``RovoSpecificFeatureFlags``, located at
``platform/base/base-api/.../HybridOrchestratorFeatureFlags.kt`` with
**23 enum values**.

**Critical insight**: This enum controls **orchestrator BEHAVIOR
(parameter tuning)**, NOT **orchestrator SELECTION**. Selection lives
in a separate experiment service (see
:doc:`../business/05-open-questions-resolved` §14.3).

Categories (23 values total)
==============================

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Category
     - Example values
   * - **Model config** (4)
     - ``ORCHESTRATOR_MODEL_CONFIG``, ``EXTENDED_THINKING_ORCHESTRATOR_MODEL_CONFIG``, ``CITATION_PROCESSOR_MODEL_CONFIG``, ``ANSWER_GENERATOR_MODEL_CONFIG``
   * - **Orchestrator behavior** (3)
     - ``HYBRID_ORCHESTRATOR_EXPERIMENT_CONTEXT_TEMPLATE``, ``ORCHESTRATOR_COMPLEXITY_CLASSIFY_LOGGING``, ``CANCEL_PARALLEL_JOB``
   * - **Editor/AIFC context** (5)
     - ``EDITOR_INLINE_ROVO_GUIDANCE_PROMPT``, ``EDITOR_ALIGNED_PROMPTS_2``, ``EDITOR_ALIGNED_PROMPTS_3``, ``AIFC_NEW_TRACES``, etc.
   * - **Reasoning / Extended Thinking** (4)
     - ``EXTENDED_THINKING_TOKEN_BUDGET``, ``REASONING_EFFORT``, ``DEFAULT_MODE_REASONING_BUDGET``, ``FORCE_EXTENDED_THINKING_ENABLED``
   * - **Marathon-related** (1)
     - ``MARATHON_RUNTIME_REMINDER`` (line 46)
   * - **Other** (~6)
     - Various trace, prompt, and configuration flags

When to Consult Each FF System
================================

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Question
     - FF system to consult
   * - "Is Marathon enabled for this user?"
     - ``RovoSpecificFeatureFlags`` (Marathon FFs)
   * - "What model is the orchestrator using?"
     - ``HybridOrchestratorFeatureFlags`` (model config)
   * - "What's the token budget for extended thinking?"
     - ``HybridOrchestratorFeatureFlags`` (reasoning)
   * - "Which orchestrator type was selected (Hybrid/SAIN/LongHorizon)?"
     - **Hello experiment service** (separate; see open question)
   * - "Is the editor using new prompts?"
     - ``HybridOrchestratorFeatureFlags`` (editor/AIFC)
