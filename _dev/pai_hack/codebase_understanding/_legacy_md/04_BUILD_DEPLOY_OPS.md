# 04 — Build, Deployment & Operational Infrastructure

**Last Updated:** 2026-05-07
**Owner:** Proactive AI Platform Team
**Service:** `proactive-ai-platform`
**Organization:** Engineering-AI

---

## Table of Contents

1. [Overview](#overview)
2. [Build System — build.gradle.kts](#build-system--buildgradlekts)
3. [Service Descriptor — service-descriptor.sd.yml](#service-descriptor--service-descriptorsdyml)
4. [CI Pipeline — bitbucket-pipelines.yml](#ci-pipeline--bitbucket-pipelinesyml)
5. [Docker — Dockerfile](#docker--dockerfile)
6. [CD Pipeline — default-pipelines.spinnaker.yaml](#cd-pipeline--default-pipelinesspinnakeryaml)
7. [Local Development — nebulae.yml](#local-development--nebulaeyml)
8. [Bin Scripts](#bin-scripts)
9. [StreamHub Configuration](#streamhub-configuration)
10. [POCO Authorization Policies](#poco-authorization-policies)
11. [Dependency Management — renovate.json5](#dependency-management--renovatejson5)
12. [Component & Project Descriptors](#component--project-descriptors)
13. [Code Quality — sonar-project.properties](#code-quality--sonar-projectproperties)
14. [Canary Configuration — canary-config.yml](#canary-configuration--canary-configyml)
15. [Reference Docs Inventory — docs/](#reference-docs-inventory--docs)

---

## Overview

The Proactive AI Platform (`proactive-ai-platform`) is an Atlassian Micros service built with Kotlin/Spring Boot, deployed via Spinnaker to AWS. It processes analytics events via SQS and StreamHub, supports long-running async tasks (Rovo Insights generation), and is authorized via POCO policies. The service runs on Java 21, uses Valkey/Redis for caching, and follows SOX-compliant deployment practices.

**Key infrastructure files at a glance:**

| File | Purpose |
|------|---------|
| `build.gradle.kts` | Gradle build — 28 dependencies, plugins, custom tasks |
| `service-descriptor.sd.yml` | Micros service descriptor (316 lines) — resources, queues, scaling |
| `bitbucket-pipelines.yml` | CI pipeline (287 lines) — lint, build, test, deploy |
| `Dockerfile` | Container image — 2-line minimal build |
| `default-pipelines.spinnaker.yaml` | CD pipeline — safe-release to stg/prod |
| `nebulae.yml` | Local dev environment (87 lines) |
| `bin/` | 8 shell scripts + 7 run-once setup scripts |
| `streamhub/` | Analytics event subscription config |
| `src/main/resources/policies/` | POCO authorization policies |
| `renovate.json5` | Automated dependency updates |
| `component-descriptor.yml` | Compass service registration |
| `project-descriptor.yml` | Micros project metadata |
| `sonar-project.properties` | SonarQube code quality config |

---

## Build System — `build.gradle.kts`

### Plugins (5)

| Plugin | Version | Purpose |
|--------|---------|---------|
| `io.atlassian.micros.springboot` | 7.10.0 | Atlassian Micros Spring Boot framework plugin |
| `com.atlassian.gradle.plugins.revealer` | 18.1.0 | Dependency version reporting/transparency |
| `io.spring.dependency-management` | 1.1.7 | Spring dependency BOM management |
| `org.jlleitschuh.gradle.ktlint` | 14.2.0 | Kotlin linting and code style enforcement |
| `jacoco` | 0.8.14 | Code coverage reporting |

Additional Kotlin plugins: `kotlin("jvm")`, `kotlin("plugin.spring")`.

### Dependency Management

BOM import: `io.micrometer:micrometer-bom:1.16.4`

### Dependencies (28 total)

#### Core Framework (3)
| Dependency | Purpose |
|------------|---------|
| `micros-spring-boot-starter-base` | Base Micros Spring Boot starter |
| `micros-spring-boot-starter-rest-spring-mvc` | REST API with Spring MVC |
| `micros-spring-boot-starter-lifecycle` | Micros lifecycle event handling |

#### Security & Auth (2)
| Dependency | Purpose |
|------------|---------|
| `micros-spring-boot-starter-security-slauth-server` | SLAuth server-side authentication |
| `micros-spring-boot-starter-spring-mvc-user-context` | User context extraction from requests |

#### Kotlin Runtime (4)
| Dependency | Purpose |
|------------|---------|
| `kotlin-reflect` | Kotlin reflection support |
| `kotlin-stdlib` | Kotlin standard library |
| `kotlinx-coroutines-core:1.10.2` | Kotlin coroutines for async processing |
| `kotlinx-coroutines-slf4j:1.10.2` | Coroutine-aware SLF4J MDC propagation |

#### Async & Reactive (1)
| Dependency | Purpose |
|------------|---------|
| `kotlinx-coroutines-reactor:1.10.2` | Bridge between Kotlin coroutines and Project Reactor |

#### Observability (2)
| Dependency | Purpose |
|------------|---------|
| `opentelemetry-extension-kotlin:1.61.0` | OpenTelemetry Kotlin extensions for tracing |
| `analytics-spring-boot:7.1.0` | Atlassian analytics event emission |

#### Serialization (1)
| Dependency | Purpose |
|------------|---------|
| `jackson-module-kotlin:2.21.3` | Jackson Kotlin module for JSON serialization |

#### Messaging (2)
| Dependency | Purpose |
|------------|---------|
| `sqs-queues-starter-aws-sdkv2:9.24.5` | AWS SQS queue consumer/producer with SDK v2 |
| `sqs-queues-dlq-actuator-aws-sdkv2:9.24.5` | SQS dead-letter queue actuator endpoint |

#### Platform Services (4)
| Dependency | Purpose |
|------------|---------|
| `featuregate-client-starter:10.4.0` | Feature gate/flag client |
| `tcs-client-starter:10.4.0` | Tenant Context Service client |
| `paas-sharding-context-java:2.0.7` | PaaS sharding context for multi-tenant routing |
| `adk-extensions-java:1.0.0` | Atlassian Developer Kit extensions |

#### Architecture Testing (1)
| Dependency | Purpose |
|------------|---------|
| `archunit:1.4.1` | Architecture rule testing (e.g., no circular deps) |

#### Annotation Processing (1)
| Dependency | Purpose |
|------------|---------|
| `spring-boot-configuration-processor` | Generates metadata for @ConfigurationProperties |

#### Dev-Only (1)
| Dependency | Purpose |
|------------|---------|
| `spring-boot-devtools` | Hot-reload during local development (developmentOnly) |

#### Test Dependencies (6)
| Dependency | Purpose |
|------------|---------|
| `kotlinx-coroutines-test:1.10.2` | Coroutine test utilities |
| `mockk:1.14.9` | Kotlin-idiomatic mocking framework |
| `wiremock-standalone:3.13.2` | HTTP service mocking for integration tests |
| `assertj-core:3.27.7` | Fluent assertion library |
| `httpclient5:5.6` | Apache HTTP client for integration tests |
| `spring-boot-starter-test` | Spring Boot test framework |

### Repositories

1. **maven-atlassian-com** — `https://packages.atlassian.com/maven/repository/internal`
2. **Maven Central**

### Project Coordinates

- **Group:** `io.atlassian.micros.proactiveai`
- **Version:** `1.0-SNAPSHOT`
- **Java Toolchain:** JDK 21

### Custom Gradle Tasks

| Task | Type | Description |
|------|------|-------------|
| `test` | Test | Unit tests (JUnit 5). Excludes *IT classes. Generates JUnit XML + HTML reports. Finalizes with JaCoCo. |
| `intTest` | Test | Integration tests. Runs only *IT classes. Depends on startNebulae, finalizedBy stopNebulae. Never cached. |
| `startNebulae` | Exec | Starts Nebulae local env. DOCKER_TAG=sandbox. Exports envs.json. |
| `runInNebulae` | Exec | Runs service inside Nebulae. DOCKER_TAG=sandbox. |
| `stopNebulae` | Exec | Stops Nebulae environment. |
| `runInDocker` | — | Alias for runInNebulae. |
| `processResources` | — | Token replacement: injects project.name and project.version. |
| `jacocoTestReport` | JacocoReport | XML + HTML coverage reports. Excludes Application, config, dto classes. |

### JaCoCo Configuration

- **Tool version:** 0.8.14
- **Reports:** XML (CI) + HTML (humans), CSV disabled
- **Exclusions:** Application class, config package, DTO package
- **Execution data:** Only from `test` task (not intTest)

---

## Service Descriptor — `service-descriptor.sd.yml`

**316 lines** defining the complete Micros service infrastructure.

### Service Metadata

| Property | Value |
|----------|-------|
| Organization | Engineering-AI (prod: Engineering-AI COGS) |
| Network Ingress | internal |
| Healthcheck | GET /healthcheck:8080 |
| Deepcheck | GET /deepcheck |
| Requires ASAP | true |
| Build Number | ${DOCKER_TAG} |

### Resources (4)

#### 1. SLAuth Gateway
- **Name:** `proactive-ai-gateway`

#### 2. Redis Cache (Valkey)
- **Name:** `proactive-ai-cache`
- **Engine:** Valkey 7.x, cluster mode disabled
- **Instance:** cache.t4g.small, 1 replica, transit encryption enabled
- **Data Types:** Identifier/OfEntity, UGC/Raw, PD/Pseudonymous
- **Alarm:** EngineCPUUtilizationTooHigh — threshold 90%, 5×60s periods, Priority Low

#### 3. SQS Queue — `analytics-events`
- **Visibility Timeout:** 120s (2 min)
- **Retention:** 3600s (1 hour)
- **MaxReceiveCount:** 3 (auto-provisions DLQ)
- **Data Type:** Usage/Action
- **IAM:** streamhub-demux can SendMessage, restricted by Micros OU path

#### 4. SQS Queue — `rovo-insights-generation-queue`
- **Visibility Timeout:** 360s (6 min) — for long-running LLM work
- **MaxReceiveCount:** 2 (auto-provisions DLQ)
- **Data Types:** Identifier/OfEntity, PD/Pseudonymous
- **Alarms:**
  - HighProcessingLatency — oldest message > 720s (12 min)
  - DLQAlertLow — any messages in DLQ
  - DLQAlertHigh — DLQ > 100 messages

### Retry Policy (Reusable YAML Anchor)
- Retries on 5xx and 429 status codes

### Worker Groups (3)

| Worker | Purpose | Scaling | Instance |
|--------|---------|---------|----------|
| WebServer (default) | HTTP requests | Default | t3a.medium |
| SHWorkers | StreamHub event processing | min: 1 | t3a.medium |
| LongRun | Async task framework | min: 1, max: 2 | t3a.medium |

### Lifecycle Events
- **Source:** queue — SQS-based for graceful shutdown during deployments

### Load Balancer
- **Type:** ALB, single: true

### Environment Variables
| Variable | Value |
|----------|-------|
| MEMORY_OPTS | -XX:MaxRAMPercentage=25.0 |
| TAP_SIDECAR_BASE_URL | http://tap-sidecar:8083 |

### Environment Overrides

| Environment | Changes |
|-------------|---------|
| local | Ports 8080:8090, 9010:9010; TAP sidecar; MEMORY=-Xmx512M |
| staging | continuous-chaos resource for chaos testing |
| prod | Organization: Engineering-AI COGS |

### Service Proxy
- **Auth Plugins:** ASAP, SLAuth Token, Build, User Context, Staff Context
- **Authorization:** POCO
- **Egress Dependencies:**

| Dependency | Timeout | Retry |
|------------|---------|-------|
| id-gatekeeper | 20s | 5xx+429 |
| ai-gateway | 600s (10 min) | 5xx+429 |
| integrations-service | 60s | 5xx+429 |

### Alarm Overrides
- UnHealthyHostCount: threshold 1, 6×60s, Priority Low
- WebServerMemoryAlarmHigh: threshold 90%, 2×300s, Priority Low

---

## CI Pipeline — `bitbucket-pipelines.yml`

**287 lines.** Base image: `gradle:9.4.1-jdk21`. Docker: 4096MB.

### Pipeline Steps (13)

| Step | Name | Size | Description |
|------|------|------|-------------|
| lint-and-static-analysis | Lint | 2x | ktlintCheck |
| run-test-and-build | Build, test and package | 4x | gradlew clean build |
| docker-image-build-and-upload | Build and upload Docker image | 4x | Multi-arch (amd64+arm64), SOX namespace |
| run-sonarqube | Run SonarQube | — | sonar-pipe, quality gates disabled |
| poco-policy-test-and-upload | POCO Policy Test+Upload | — | Tests and uploads policies |
| tag-policy-to-staging | Tag Policy staging | — | deployment: poco-staging |
| tag-policy-to-production | Tag Policy production | — | deployment: poco-production |
| provision-serviceproxy-alias | Provision SP Alias | — | Conditional on alias descriptor changes |
| deploy-to-spinnaker | Deploy via Spinnaker | — | deployment: spinnaker |
| validate-spinnaker-pipelines | Validate Spinnaker | — | atlas spin validate |
| validate-service-descriptors | Validate SD | — | Validates stg-east + prod-east |
| validate-streamhub-subscriptions | Validate StreamHub | — | Conditional on streamhub/** changes |
| provision-streamhub-subscriptions | Provision StreamHub | — | stg-east + prod-east |

### Pipeline Flows

**main branch (Production):**
1. Parallel: Lint + Build+Test + Validate SD + Validate Spinnaker + Validate StreamHub
2. SonarQube
3. POCO Policy Test+Upload
4. Parallel: Docker Build + SP Alias + StreamHub Provision
5. Tag Policy Staging
6. Tag Policy Production
7. Deploy via Spinnaker

**Pull Requests:**
1. Parallel: Lint + Build+Test + Validate SD + Validate Spinnaker + Validate StreamHub
2. SonarQube

**Custom branch-deploy-staging:** Same as main but only staging.

### SOX Compliance
- Main: NAMESPACE=sox, COMPLIANT=true
- Others: NAMESPACE=atlassian, COMPLIANT=false

---

## Docker — `Dockerfile`

```dockerfile
FROM docker.atl-paas.net/sox/micros-java-21:1.5.0
COPY ./build/libs/proactive-ai-platform*.jar /opt/service/service.jar
```

- **Base Image:** SOX-compliant Java 21 (micros-java-21:1.5.0)
- **Build Artifact:** Spring Boot fat JAR
- **Entry Point:** Inherited from base image
- **Multi-arch:** amd64 + arm64 via docker buildx

---

## CD Pipeline — `default-pipelines.spinnaker.yaml`

| Property | Value |
|----------|-------|
| Schema Version | 1 |
| Timezone | Australia/Sydney |
| Namespace | spinnaker-proactive-ai-platform |
| Template | safeRelease |
| Throughput | high |
| Slack Channel | #ai-experience-ops |
| Failure Notifications | Enabled (author + changelog) |

### Pipelines

1. **Primary** (service-descriptor): stg-east → prod-east, progressive rollout on prod
2. **Branch Deploy** (branch-deploy-staging): stg-east only

---

## Local Development — `nebulae.yml`

**87 lines.** Three sandbox profiles:

| Profile | Service | Upstreams | SHWorkers | Use Case |
|---------|---------|-----------|-----------|----------|
| default | Running | Mocked | Disabled | Full local sandbox |
| stg | Running | Proxied to staging | Disabled | Test with real staging services |
| stg_env_only | NOT running | Proxied to staging | Disabled | Run service from IDE |

SLAuth plugin provides local auth mock sidecar.

---

## Bin Scripts

### Top-Level Scripts (8)

| Script | Purpose | Usage |
|--------|---------|-------|
| `build-include.sh` | CI setup — Java, Atlas plugins | Sourced by CI |
| `get-deployment-access.sh` | Get deploy credentials | `./bin/get-deployment-access.sh` |
| `manual-deploy.sh` | Manual deploy to any env | `./bin/manual-deploy.sh <env>` |
| `poco-include.sh` | POCO setup helper | Sourced by POCO scripts |
| `poco-policy-tag.sh` | Tag POCO policy for env | `./bin/poco-policy-tag.sh <env>` |
| `poco-policy-test.sh` | Run POCO policy tests | `./bin/poco-policy-test.sh` |
| `poco-policy-upload.sh` | Upload POCO policy | `./bin/poco-policy-upload.sh <label>` |
| `spinnaker-deploy.sh` | Manual Spinnaker deploy | `./bin/spinnaker-deploy.sh` |

### Run-Once Setup Scripts (7)

| Script | Purpose |
|--------|---------|
| `check-java.sh` | Validates Java 21 installed |
| `configure-gradle.sh` | Configures Gradle with Atlassian secrets |
| `install-atlas.sh` | Installs Atlas CLI (macOS/Linux) |
| `install-docker-compose-v2.sh` | Installs Docker Compose v2 (v2.12.2) |
| `install-nebulae.sh` | Installs Nebulae + SLAuth mock sidecar |
| `install-slauth.sh` | Installs/upgrades SLAuth plugin |
| `spinnaker-onboard.sh` | One-time Spinnaker onboarding |

---

## StreamHub Configuration

### Subscription — `streamhub/subscriptions/analytics-events.yml`

| Property | Value |
|----------|-------|
| Alias | analytics-events-listener |
| Service ID | proactive-ai-platform |
| Owner | eng-ai-experience |
| Slack | #ai-experience-ops |
| Filter | avi:analytics-enriched:created:ui where eventName="rovoButton rendered" |
| SQS Target | analytics-events queue |

### Shipyard Artifact — `streamhub/shipyard-specs/artifact.yml`

- **Resource:** proactive-ai-platform/analytics-events-subscription
- **Type:** streamhub-subscription
- **Environments:** stg-east, prod-east

---

## POCO Authorization Policies

### Policy — `src/main/resources/policies/service/policy.json`

7 allow rules:

| # | Paths | Methods | Principals |
|---|-------|---------|------------|
| 1 | /api/v1/rovo/insights/* | POST | convo-ai, edge-authenticator |
| 2 | /greetings/charlie | GET | charlie |
| 3 | /api/v1/nudge/* | POST | convo-ai |
| 4 | /api/v1/rovo-insights/* | POST | convo-ai |
| 5 | /stratus/test/** | POST | charlie, edge-authenticator |
| 6 | /api/swagger-ui/**, /api/openapi/** | GET | Open |
| 7 | /healthcheck, /deepcheck | GET | Open |

### Tests — `src/main/resources/policies/tests.json`

5 test cases validating allow/deny behavior.

---

## Dependency Management — `renovate.json5`

- **Extends:** config:recommended + atlassian/golden-renovate-config:automated
- **Auto-merge:** minor and patch updates (branch merge, no PR)
- **Micros BOM upgrades:** Auto-runs OpenRewrite migration recipes

---

## Component & Project Descriptors

### component-descriptor.yml (Compass)
- **ID:** 4575388a-a28c-4710-9b74-2d310d81e0cb
- **Type:** micros-service, Tier 3, Java 21

### project-descriptor.yml
- Build commands: gradlew assemble → docker build → tag sandbox

### service-proxy-alias-descriptor.yml
- **Staging:** Simple → stg-east
- **Prod:** Simple → prod-east

---

## Code Quality — `sonar-project.properties`

- **Project:** proactive-ai-platform
- **Sources:** src/main, **Tests:** src/test
- **Coverage:** JaCoCo XML from unit tests only

---

## Canary Configuration — `canary-config.yml`

File exists but is empty. Used for canary deployment configuration with progressive rollouts.

---

## Reference Docs Inventory — `docs/`

16 reference documents:

| # | File | Size | Description |
|---|------|------|-------------|
| 1 | ADR_TEMPLATE.md | 8.7 KB | Architecture Decision Record template |
| 2 | ARCHITECTURE_INDEX.md | 17.2 KB | Master architecture documentation index |
| 3 | bitbucket-pipelines.md | 312 B | Pipeline status quick reference |
| 4 | bitbucket-sox.md | 952 B | SOX compliance controls guide |
| 5 | bitbucket.md | 409 B | Repository customization reference |
| 6 | micros-spring-boot-slauth.md | 1.6 KB | SLAuth authentication setup |
| 7 | micros-spring-boot.md | 1.7 KB | Micros Spring Boot framework overview |
| 8 | micros.md | 3.4 KB | Micros PaaS onboarding and deployment |
| 9 | nebulae.md | 2.1 KB | Nebulae local dev prerequisites |
| 10 | next-steps.md | 976 B | Post-setup checklist |
| 11 | poco.md | 2.0 KB | POCO authorization policy guide |
| 12 | renovate.md | 510 B | Renovate dependency automation |
| 13 | security-checklist.md | 1.9 KB | Security best practices |
| 14 | slauth.md | 600 B | SLAuth sidecar reference |
| 15 | sonarqube.md | 1.9 KB | SonarQube scanning and coverage |
| 16 | spinnaker.md | 5.1 KB | Spinnaker CD pipeline guide |

---

*Auto-generated on 2026-05-07 from repository source files.*
