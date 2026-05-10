# Convo-AI-Platform Testing SOP — Overview

**Repo:** `conversational-ai-platform` (Atlassian, Bitbucket: `bitbucket.org/atlassian/conversational-ai-platform`)
**Stack:** Kotlin 1.9+ / Spring Boot / Gradle 9.3 multi-module / Java 21 (Amazon Corretto 21.0.8)
**Test frameworks:** JUnit 5 (Jupiter) + WireMock + Spring Boot Test
**Sandbox runtime:** Atlas Nebulae (Atlassian-internal Docker-Compose-on-steroids)

---

## SOP set

| File | Purpose |
|---|---|
| `00-overview.md` | This file. Map of the SOP and high-level test taxonomy. |
| `01-prerequisites.md` | Tools, env, IAM, secrets you need BEFORE anything. |
| `02-unit-tests.md` | Run unit tests locally (no Docker, no Nebulae, ~5 min). |
| `03-integration-tests.md` | Run integration tests locally with Nebulae (Docker, ~15-60 min). |
| `04-troubleshooting.md` | Known failure modes + diagnoses + workarounds. |
| `05-ci-mirror.md` | Mirror what CI does so local results predict CI results. |
| `06-load-tests.md` | **NEW** — Run perfhammer/Locust load tests; feed M7 saturation dashboard. |
| `07-evaluation-tests.md` | **NEW** — LLM-Judge eval + AIFC golden-set + ARIZE; feed M1/M2 quality measurement. |
| `08-live-sandbox.md` | **NEW** — Re-use the running 18-container Nebulae sandbox (5-10× faster iteration). **Includes critical health-check before re-use.** |
| `09-end-to-end-verification-log.md` | **NEW** — Verbatim 2026-05-04 dry-run of the SOP showing what is verified vs what needs correction. Source-of-truth for "does the SOP actually work". |

---

## Test taxonomy in this repo

| Type | Source set | Run command | What it asserts |
|---|---|---|---|
| **Unit** | `src/test/kotlin` (every module) | `./gradlew test` (or sharded: `-PunitTestShard=core\|rovo\|product`) | Fast, in-process, no external services. Mocked deps. |
| **Startup smoke** | `convo-ai-test-integration/src/test/kotlin/.../FullContextStartupIT.kt` | `./gradlew :convo-ai-test-integration:startupTest -Pnebulae.enabled=true` | Full Spring context boots — proves all modules wire together. |
| **Integration** | `convo-ai-test-integration/src/test/kotlin/it/...` (250+ tests, JUnit `@Tag("integration-test")`) | `./gradlew :convo-ai-test-integration:integrationTest -Pnebulae.enabled=true` (or sharded `integrationTestShard{1..4}{FlagsOn\|FlagsOff}`) | HTTP-level tests against the locally-running service in a Nebulae sandbox; external services mocked via WireMock. |
| **Evaluation (BatchEval)** | `convo-ai-test-integration/.../AgentStudioBatchEvaluation*IT.kt` + `modules/platform/evaluation/` | `./gradlew :convo-ai-test-integration:integrationTest --tests '*BatchEvaluation*' -Pnebulae.enabled=true` | LLM-Judge plumbing: job lifecycle → dataset → judge dispatch → ERS persistence. WireMock-canned LLM responses. (See `07-evaluation-tests.md`) |
| **Load (Locust/perfhammer)** | `operations/perfhammer/tests/*.py` | `cd operations/perfhammer && locust -f tests/rovo-chat-stream-api.py` | Streaming-API throughput / saturation against local sandbox, staging, or (with approval) prod. Feeds the M7 dashboard. (See `06-load-tests.md`) |
| **Live-sandbox iteration** | re-use running `convo-ai-integration-tests-<session-id>-*` containers | `./gradlew … -Pnebulae.enabled=false` | 5-10× faster dev loop; skip Nebulae start/stop. (See `08-live-sandbox.md`) |

Key tag conventions (verified at `convo-ai-test-integration/build.gradle.kts:167,354`):
- `@Tag("startup-test")` → only the startup smoke (1 test)
- `@Tag("integration-test")` → the 250+ integration tests
- Default `test` task **excludes** both tags

---

## Local-CI parity

CI runs **8 integration shards** (4 shards × FlagsOn/FlagsOff) plus **3 unit shards** (core/rovo/product) plus **lint/detekt**. Locally, you'd typically run only:
1. `./gradlew test` — all unit tests
2. `./gradlew :convo-ai-test-integration:startupTest -Pnebulae.enabled=true` — smoke (1 test, ~3-5 min)
3. **Only if needed**: `./gradlew :convo-ai-test-integration:integrationTest -Pnebulae.enabled=true` — full integration (~30-60 min)

If smoke + unit pass locally, CI failures are usually **environmental** (IAM, Sliver token expiry) not code defects.

---

## Quick-start (TL;DR)

```bash
cd ~/MyProjects/atlassian_packages/conversational-ai-platform

# Once: install tools (sdkman, atlas CLI, nebulae plugin)
bin/first-run

# Daily: unit tests (fast, no docker)
./gradlew test

# Smoke: full context boots (needs Docker + ~3-5 min)
./gradlew :convo-ai-test-integration:startupTest -Pnebulae.enabled=true

# Full integration (only when really needed)
./gradlew :convo-ai-test-integration:integrationTest -Pnebulae.enabled=true
```

Read `04-troubleshooting.md` BEFORE you assume a failure is in your code.
