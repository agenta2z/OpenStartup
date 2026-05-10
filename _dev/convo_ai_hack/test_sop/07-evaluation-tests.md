# 07 — Evaluation / quality tests (LLM-Judge, AIFC, batch eval)

> **Why this exists.** v7 §6 measurement plan calls out **M1 (AIFC eval harness)** and **M2 (ARIZE per-turn quality)** as load-bearing for the AIFC 57pp factual-consistency recovery. This file documents how to actually exercise those pipelines locally, what's automatable today, and what is Databricks-only.
>
> **Bottom line.** The **LLMJudge framework** is the canonical quality assertion mechanism in this repo (NOT Arize directly). Local execution = JUnit `@Tag("integration-test")` runs. Production execution = SQS-triggered batch jobs orchestrated from Databricks via `operations/pollinator/scripts/llm_judge_evaluation.py`.

---

## A. Inventory — where eval lives in code

| Path | What it is |
|---|---|
| `modules/platform/evaluation/api` + `spi` + `impl` | Core evaluation framework: `BatchEvaluationJob`, `BatchEvaluationDatasetStore`, `BatchEvaluationResultStore`, `BatchJudgementExecutionService` |
| `modules/platform/evaluation/impl/.../LLMJudgeServiceImpl.kt` | The judge executor — runs LLM-prompted scoring against conversation transcripts |
| `modules/product/rovo/evaluation/` | Rovo-specific judge prompts (`RovoAgentEvaluationStrategy`) |
| `modules/product/csm/evaluation/` | CSM-specific judge prompts (`CsmEvaluationStrategy`) |
| `convo-ai-test-integration/src/test/kotlin/it/io/atlassian/micros/convoai/agentstudio/rest/AgentStudioBatchEvaluationV1ControllerIT.kt` | Integration test for the BatchEvaluation controller |
| `ers/schema/shipyard-specs/ati:cloud:convo-ai:*evaluation*_v1.json` | ERS data product schemas for evaluation results |
| `operations/pollinator/scripts/llm_judge_evaluation.py` | Databricks orchestration script — runs nightly judge passes in production |
| `developer.atlassian.com/deep_research/` | Deep-research evaluation docs |
| `evaluation/` (top-level) | Additional evaluation harnesses (golden datasets, replay tools) |

---

## B. The 4 ways to exercise evaluation

### B1. Run the BatchEvaluation integration tests (local, no LLM call)

These tests assert the **plumbing** (job creation → dataset hydration → judge dispatch → result persistence to ERS). They use stubbed LLM responses via WireMock.

```bash
cd /Users/tchen7/MyProjects/atlassian_packages/conversational-ai-platform

# Single test class
./gradlew :convo-ai-test-integration:integrationTest \
  --tests 'AgentStudioBatchEvaluationV1ControllerIT' \
  -Pnebulae.enabled=true

# All BatchEvaluation tests
./gradlew :convo-ai-test-integration:integrationTest \
  --tests 'it.io.atlassian.micros.convoai.agentstudio.*BatchEvaluation*' \
  -Pnebulae.enabled=true
```

If your sandbox is already running (cf. `08-live-sandbox.md`), use `-Pnebulae.enabled=false`.

**What this proves**: job lifecycle correctness; dataset persistence; result schema compliance. It does **not** prove LLM judge quality (it uses canned WireMock responses).

### B2. Run an end-to-end judge against a single conversation (local, real LLM)

There is no public CLI runner in the repo. The local pattern is to invoke the GraphQL mutation:

```bash
# Sandbox + app must be running
curl -X POST http://localhost:8081/graphql \
  -H "Content-Type: application/json" \
  -H "ATL-CloudId: <tenant-uuid>" \
  -d '{
    "query": "mutation { startBatchEvaluation(input: { datasetId: \"<id>\", judges: [\"factual-consistency-v1\"] }) { jobId } }"
  }'
```

You'll need:
- A staging-style cloudId allow-listed for evaluation
- A small `BatchEvaluationDataset` already inserted (use `BatchEvaluationDatasetStore.createDataset(...)` from a one-off Kotlin script or an integration test fixture)
- An LLM gateway credential — the local sandbox uses **mock LLM responses by default**; to call real Claude/GPT, set `LLM_USE_REAL_GATEWAY=true` env var on `bootRun` and supply a Sliver token to AI Gateway

### B3. The Databricks nightly orchestration (production only)

Path: `operations/pollinator/scripts/llm_judge_evaluation.py`

This script:
1. Reads the active `BatchEvaluationDataset` IDs from a Databricks table
2. POSTs `startBatchEvaluation` mutations to the prod convo-ai-platform GraphQL endpoint
3. Polls for job completion
4. Reads results from the ERS data product `ati:cloud:convo-ai:evaluation_result_v1`
5. Computes per-judge / per-cohort aggregates
6. Posts to a Databricks dashboard + SignalFx

**Cannot be run locally** without the Databricks runtime. The local equivalent is B1+B2 plus your own aggregation script.

### B4. The AIFC golden eval (manual + ARIZE)

The 300-row golden dataset referenced by v7 M1 + Q13 is **not yet wired** in the repo (it's the v7 deliverable Q13). What exists today:
- The `LLMJudgeServiceImpl` can be parameterised with any `EvaluationDataset`
- `ARIZE` ingestion is partial; v7 Q14 is the explicit task to wire `LLMJudgeServiceImpl` results into the ARIZE event pipeline at 5% sample with cohort tags

**Status:** Q13 (dataset PR) and Q14 (ARIZE wire) are **prerequisites** for closing the AIFC factual gap. Until they ship, "AIFC eval" runs are ad-hoc + manual.

---

## C. ERS data products (where results live)

After a batch eval job completes, results land in:
- `ati:cloud:convo-ai:evaluation_result_v1` — per-row judge verdict (factual / recall / relevancy + numeric score)
- `ati:cloud:convo-ai:evaluation_metric_v1` — per-job aggregate metrics
- `ati:cloud:convo-ai:batch_evaluation_job_v1` — job lifecycle records

Inspect via Socrates (`socrates-vnext/`) or via direct ERS query:
```bash
# Pseudo-command; exact CLI varies by team
ers query --product convo-ai --resource evaluation_result_v1 --since 1d
```

---

## D. What's auto-runnable in CI today

| Item | Triggered in CI? |
|---|---|
| BatchEvaluation integration tests (B1) | **Yes** — they run as part of `integrationTestShard{N}{FlagsOn,FlagsOff}` (cf. `05-ci-mirror.md`) |
| End-to-end judge with real LLM (B2) | **No** — operator-driven only |
| Databricks nightly judge (B3) | **Yes** — orchestrated outside this repo, runs nightly per Databricks scheduler |
| AIFC golden eval (B4) | **Not yet** — pending Q13 + Q14 |

---

## E. Common evaluation-test failures

| Symptom | Likely cause | Fix |
|---|---|---|
| `BatchEvaluationDatasetStore` returns null in test | Test forgot to seed the dataset via `@BeforeEach` or `IntegrationTest` base class fixture | check the IT base class for the fixture pattern |
| `LLMJudgeServiceImpl` returns 500 | Wiremock missing stub for the judge LLM call | add a WireMock stub under `convo-ai-test-integration/src/test/resources/wiremocks/ai_gateway/` (cf. existing stubs there) |
| Real LLM run hangs | `LLM_USE_REAL_GATEWAY=true` set but Sliver token expired | `slauth token --aud ai-gateway` to refresh |
| ERS write fails locally | `ers-control` and `ers-data` containers not in sandbox | sandbox start (`atlas nebulae start -s integration-tests`); confirm `docker ps | grep ers-` shows both Up |

---

## F. v7 plan tie-ins

| v7 item | What this SOP enables |
|---|---|
| **M1 (AIFC eval harness)** | B1 + B4 once Q13 lands |
| **M2 (ARIZE per-turn judge)** | B2 once Q14 lands |
| **Q1-Q5 (AIFC factual recovery)** | Use B1 to verify per-flag-cohort delta on golden eval |
| **Q12 (PR-pipeline regression block)** | The CI gate — runs B1 on every PR, blocks merge on regression |
| **N8 (Insights structuredOutputEnabled)** | Use B2 to A/B quality of structured-output mode |
| **R-1B (tool-error feedback)** | Use B1 to verify recovery rate ≥40% target |

---

## G. Cleanup

ERS rows persist across test runs unless explicitly cleared. The IT base class typically tears down test data via `@AfterEach`; confirm by inspecting your specific test file.

```bash
# If you ran B2 locally and want to clear local sandbox state:
docker compose --project-name convo-ai-integration-tests-3f2a39fb \
  exec ers-control sh -c 'curl -X POST http://localhost:8080/admin/reset' || true
```

(The exact reset endpoint varies by ers-control build; if it errors, restart the sandbox.)
