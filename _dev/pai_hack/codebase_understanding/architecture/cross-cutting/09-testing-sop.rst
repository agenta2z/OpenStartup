=========================================
09 — Testing Standard Operating Procedure
=========================================

.. contents:: On this page
   :depth: 3
   :local:

Overview
--------

The proactive-ai-platform test suite contains **33 test source files**
across 11 packages, covering unit tests, acceptance tests, integration
tests, and architectural fitness tests.  All tests are written in
**Kotlin** using **JUnit 5** with **AssertJ** and **Mockito/MockK**
assertions.

Test File Inventory
-------------------

.. list-table::
   :header-rows: 1
   :widths: 60 20 20

   * - Test File
     - Pattern
     - Package
   * - ``ArchUnitTest.kt``
     - Architecture
     - root
   * - ``ExampleTest.kt``
     - Unit
     - root
   * - ``HealthCheckIT.kt``
     - Integration
     - root
   * - ``RovoInsightsControllerIT.kt``
     - Integration
     - root
   * - ``AsyncIdGatekeeperClientTest.kt``
     - Unit
     - client/identity
   * - ``IdGatekeeperClientTest.kt``
     - Unit
     - client/identity
   * - ``NudgeThrottleControllerAcceptanceTest.kt``
     - Acceptance
     - feature/nudge/api/rest
   * - ``RovoInsightsGenerationSqsQueueConsumerTest.kt``
     - Unit
     - feature/rovoinsights/internal
   * - ``RovoInsightsGenerationTaskHandlerTest.kt``
     - Unit
     - feature/rovoinsights
   * - ``FeatureFlagContextServiceImplTest.kt``
     - Unit
     - featuregate
   * - ``WebServiceAcceptanceTest.kt``
     - Acceptance
     - greeting
   * - ``CommonContextSetterTest.kt``
     - Unit
     - interceptor
   * - ``LoggingContextClearingFilterTest.kt``
     - Unit
     - interceptor
   * - ``RequestContextInterceptorTest.kt``
     - Unit
     - interceptor
   * - ``UserContextInterceptorTest.kt``
     - Unit
     - interceptor
   * - ``InterceptedLoggerTest.kt``
     - Unit
     - logging
   * - ``LaasLoggerFactoryTest.kt``
     - Unit
     - logging
   * - ``LaasLoggerTest.kt``
     - Unit
     - logging
   * - ``LoggerExtensionsTest.kt``
     - Unit
     - logging
   * - ``LoggingContextTest.kt``
     - Unit
     - logging
   * - ``NoopLoggerTest.kt``
     - Unit
     - logging
   * - ``WithUGCLoggerTest.kt``
     - Unit
     - logging
   * - ``MiscellaneousRequestContextVariablesServiceTest.kt``
     - Unit
     - requestcontext
   * - ``RequestScopedValuesInitterTest.kt``
     - Unit
     - requestcontext
   * - ``CoreMetricsServiceImplTest.kt``
     - Unit
     - service/metric
   * - ``MetricsServiceImplTest.kt``
     - Unit
     - service/metric
   * - ``AnalyticsEventsMessageQueueConsumerTest.kt``
     - Unit
     - sqs
   * - ``CommonSqsConfigTest.kt``
     - Unit
     - sqs
   * - ``AIGatewayServiceImplTest.kt``
     - Unit
     - stratus/internal
   * - ``AsyncTaskDispatcherTest.kt``
     - Unit
     - task
   * - ``AsyncTaskQueueRegistryTest.kt``
     - Unit
     - task
   * - ``AsyncTaskServiceImplTest.kt``
     - Unit
     - task/internal
   * - ``TestUsers.kt``
     - Helper
     - task

Test Patterns
-------------

The codebase uses **4 distinct test patterns**:

1. Unit Tests (``*Test.kt``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Count**: 26 files

Standard isolated tests that mock collaborators and verify a single class
in isolation.  Named ``<ClassName>Test.kt``.

Conventions:

- Use constructor injection with mock dependencies.
- Structured as ``@Test fun \`descriptive name\`()`` with backtick-quoted
  method names.
- Assertions via AssertJ (``assertThat(…).isEqualTo(…)``).

2. Acceptance Tests (``*AcceptanceTest.kt``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Count**: 2 files

- ``WebServiceAcceptanceTest.kt`` — verifies the ``/greetings`` endpoint.
- ``NudgeThrottleControllerAcceptanceTest.kt`` — verifies nudge throttle
  API contract.

These tests boot a partial Spring context (``@SpringBootTest`` with
``MOCK`` web environment) and test the full HTTP request-response cycle
through the controller layer.

3. Integration Tests (``*IT.kt``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Count**: 2 files

- ``HealthCheckIT.kt`` — verifies ``/healthcheck`` and ``/deepcheck``
  return 200 with a running application context.
- ``RovoInsightsControllerIT.kt`` — verifies the Rovo Insights REST API
  with a running application context.

These use ``@SpringBootTest`` with a real (or near-real) application
context.  SQS integration is typically disabled via
``proactive-ai.sqs.enabled=false`` to avoid requiring LocalStack.

4. Architecture Tests (ArchUnit)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Count**: 1 file

``ArchUnitTest.kt`` uses the `ArchUnit <https://www.archunit.org>`_
library to enforce structural rules at compile time:

.. code-block:: kotlin

   @Test
   fun `no circular packages`() {
       slices()
           .matching("io.atlassian.micros.proactiveai.(**)")
           .should()
           .beFreeOfCycles()
           .allowEmptyShould(true)
           .check(javaClasses)
   }

**Rule enforced**: No circular package dependencies under the root
package.  This prevents the dependency graph from degrading as the
codebase grows.

The ``ClassFileImporter`` excludes archives, JARs, and test classes,
scanning only production bytecode.

5. Test Helpers
^^^^^^^^^^^^^^^

**Count**: 1 file

``TestUsers.kt`` — shared test fixtures providing pre-built ``User``
instances for use across async-task test suites.

Coverage Matrix
---------------

.. list-table::
   :header-rows: 1
   :widths: 30 8 8 8 8

   * - Package
     - Unit
     - Accept.
     - Integ.
     - Arch.
   * - root (Application)
     - ✓
     - —
     - ✓
     - ✓
   * - client/identity
     - ✓
     - —
     - —
     - —
   * - feature/nudge
     - —
     - ✓
     - —
     - —
   * - feature/rovoinsights
     - ✓
     - —
     - ✓
     - —
   * - featuregate
     - ✓
     - —
     - —
     - —
   * - greeting
     - —
     - ✓
     - —
     - —
   * - interceptor
     - ✓
     - —
     - —
     - —
   * - logging
     - ✓
     - —
     - —
     - —
   * - requestcontext
     - ✓
     - —
     - —
     - —
   * - service/metric
     - ✓
     - —
     - —
     - —
   * - sqs
     - ✓
     - —
     - —
     - —
   * - stratus
     - ✓
     - —
     - —
     - —
   * - task
     - ✓
     - —
     - —
     - —

POCO Policy Tests
-----------------

Separate from JUnit, POCO policies have their own test suite in
``src/main/resources/policies/tests.json`` (5 test cases) executed via
``bin/poco-policy-test.sh``.  These validate the SLAUTH authorisation
rules at build time, ensuring policy changes don't accidentally expose
or block endpoints.

CI Integration
--------------

Tests are executed in the Bitbucket Pipelines CI:

- **Pull request**: lint + static analysis + full test suite.
- **Main branch**: full test suite + build + deploy.
- **Custom branch-deploy**: full test suite before staging deploy.

SQS-dependent tests can be opted out by setting
``proactive-ai.sqs.enabled=false`` in ``@SpringBootTest`` properties,
which causes all SQS beans (``SqsClient``, ``CommonSqsConfig``, queue
consumers) to drop out of the context via ``@ConditionalOnProperty``
and ``@ConditionalOnBean`` guards.

Static Analysis
---------------

In addition to test execution, the CI pipeline runs:

- **Checkstyle** (``checkstyle.xml``): code-style enforcement.
- **SonarQube** (``sonar-project.properties``): code quality and coverage
  analysis.
- **ArchUnit**: package-dependency cycle detection (see above).
- **POCO policy tests**: SLAUTH policy validation.
