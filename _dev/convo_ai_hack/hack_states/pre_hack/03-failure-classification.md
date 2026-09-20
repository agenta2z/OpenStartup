# Failure Classification & Hypotheses

**Captured:** 2026-05-01
**Scope:** 37 failures from `:convo-ai-test-integration:integrationTest` against pristine `main` @ `9151ac1341`

---

## Hypothesis ranking

The 37 failures cluster into 4 root-cause buckets. Here's my best read on each, with confidence levels.

### Bucket A — Routes returning 404 NOT_FOUND (11 failures, ~30%)

**Affected:** JsmChatV1ControllerIT (4), WhiteboardAITeammateStreamingNativeControllerIT (1 of 3), AgentStudioBatchEvaluationV1ControllerIT (1 of 4), ConvoStarterControllerIT, InvokeAgentIT, JiraAiSuggestIssuesControllerIT (1 of 2), ForceRatingControllerIT.

**Pattern:** Test calls a controller endpoint, expects 200/429/504, gets **404**.

**Most likely cause:** **Missing feature-flag context.** Many endpoints are gated behind `@ConditionalOnProperty` or runtime FF checks. CI sets these via `-Dconvoai.tests.featureFlags.defaultGateValue=true` (or similar) when running `Shard*FlagsOn`; the monolithic `integrationTest` task does NOT.

**Confidence:** **HIGH** — matches the "404 when expected SUCCESSFUL" signature exactly.

**Verification:** Re-run with explicit FF system property:
```
./gradlew :convo-ai-test-integration:integrationTest \
  -Dconvoai.tests.featureFlags.defaultGateValue=true
```

If the 11 failures drop to 0 (or close to it), hypothesis confirmed.

---

### Bucket B — GraphQL "Response has 1 unexpected error" (7 failures, ~19%)

**Affected:** AgentStudioScenarioCreateMutationIT, AgentStudioScenarioUpdateMutationCreateScenarioIT (4), AgentStudioWidgetQueryIT, JiraIssueRelatedResourcesGraphQLIntegrationIT, JiraSimilarWorkItemsGraphQLIntegrationIT.

**Pattern:** GraphQL query/mutation returns an error in the `errors` array; test asserts no errors → fails with "Response has 1 unexpected error(s) of 1 total".

**Most likely cause:** Same as Bucket A — endpoints gated by FF, or a downstream sidecar mock returning 500 which surfaces as a GraphQL error. The pattern of "Response has 1 unexpected error" is the GraphQL framework's way of saying "your query was processed but the resolver threw".

**Confidence:** **MEDIUM-HIGH** — same root cause as Bucket A but routed through GraphQL.

**Verification:** Look at the actual error message in `convo-ai-test-integration/build/reports/tests/integrationTest/<class>/index.html` to see what the underlying error was.

---

### Bucket C — Identity / Provisioning errors (5 failures, ~14%)

**Affected:** AgentStudioBatchEvaluationV1ControllerIT (3), ProvisioningServiceIT (3 — but only 2 of these are this bucket; 1 is AssertionFailedError).

**Pattern:** Tests for CSM-product flows or provisioning callbacks fail with:
- `IdentityCreateException: CSM Agent identity` (×2)
- `ProvisioningCallbackException: Callback failed` (×2)

**Most likely cause:** **Mocked identity/provisioning sidecar gaps.** The local sandbox's WireMock stubs for the Identity Service or Provisioning callback endpoint don't cover these specific scenarios.

**Confidence:** **MEDIUM** — could also be a real bug in master, but the wide repo precedent of `@Disabled("Flaky: ResponsibleAIClient moderation request is unmatched")` suggests stub-coverage is the standard local-vs-CI gap.

**Verification:** Check `wiremock_stubs/identity/` and `wiremock_stubs/provisioning/` directories — see if the CSM flow has stubs.

---

### Bucket D — AI Gateway returning UNKNOWN_ERROR / SERVER_ERROR (3 failures, ~8%)

**Affected:** SAINExecutorWithSourcesIT, SAINStandaloneHybridOrchestratorIT (2).

**Pattern:** SAIN orchestrator tries to call AI Gateway → mock returns `error_category: UNKNOWN_ERROR` or `SERVER_ERROR` → test fails.

**Most likely cause:** **AI Gateway sidecar mock not configured for SAIN's specific request shape.** SAIN sends complex tool-calling payloads that the mock may not have stubs for.

**Confidence:** **MEDIUM** — could also be that SAIN itself has issues, but the pattern of "mock returns UNKNOWN_ERROR" is a tell-tale wiremock fallback.

**Verification:** Check `wiremock_stubs/ai-gateway/` for SAIN-specific stubs.

---

### Bucket E — Substring / null assertion failures (4 failures, ~11%)

**Affected:** AgentStudioAgentVersionQueryIT, WhiteboardAITeammateStreamingNativeControllerIT (2), RovoPluginControllerIT.

**Pattern:** Tests assert specific text content in responses → actual response shape differs.

**Most likely cause:** **Mocked LLM responses don't match prompt-engineered expectations.** Stubs return generic mock LLM output; tests expect specific text from real model behavior.

**Confidence:** **MEDIUM** — these are the most "real" of the failure classes; could be brittle tests OR genuine product changes.

**Verification:** Read each failing test's source — see if the assertion is literal text match (brittle) or structural (real signal).

---

### Bucket F — 500 INTERNAL_SERVER_ERROR (3 failures, ~8%)

**Affected:** JiraAiSuggestIssuesControllerIT (1), AgentStudioBatchEvaluationV1ControllerIT (1), AgentStudioUpgradeSchemaIT (3).

**Pattern:** Endpoint returns 500. May be a real bug OR a downstream mock issue.

**Confidence:** **LOW-MEDIUM** — could be real product bugs. Worth investigating.

---

## Cross-cutting observations

### O1: All failures are in 20 unique classes (1.7% of test classes)

Out of 247 test classes, only **20 had any failures**. The remaining 227 are clean. The failure pattern is **concentrated**, not diffuse.

### O2: Pre-existing `@Disabled("Flaky: ...")` set the precedent

5+ tests in the repo are already `@Disabled` with reasons like:
- "Flaky: ResponsibleAIClient moderation request is unmatched"
- "Flaky: restricted forge agent access does not throw ForbiddenException"
- "Flaky: agentStudio_agentById intermittently returns INTERNAL_ERROR"
- "Flaky in CI: restricted OOTB agent permission lifecycle intermittently times out"

This confirms the **failure mode of "wiremock stubs don't perfectly cover all integration scenarios" is well-known in this codebase**. The 37 failures we're seeing are likely the same class of issue — stubs that work in CI's specific environment but not in local pristine sandbox.

### O3: CI-vs-local environmental delta is the dominant explanation

Combined evidence:
- CI uses sharded + FF-context tasks; we ran monolithic + no-FF
- 11 of 37 (30%) match the "FF-gated 404" signature exactly
- 7 more (19%) likely cascade from the same cause through GraphQL
- Existing `@Disabled` notes confirm stub-coverage gaps as the standard local-vs-CI gap

**Estimated environmental failures:** 25-30 of 37 (~70-80%).
**Estimated potentially-real-bug failures:** 7-12 of 37 (~20-30%).

---

## Recommended next steps (in priority order)

| # | Action | Expected effect | Effort |
|---|---|---|---|
| 1 | Re-run with `-Dconvoai.tests.featureFlags.defaultGateValue=true` | Drop ~11 failures (Bucket A) | 5 min |
| 2 | Run sharded variants `:integrationTestShard1FlagsOn` etc. for parity with CI | Confirm CI baseline locally | ~5 min per shard |
| 3 | Inspect `convo-ai-test-integration/build/reports/tests/integrationTest/index.html` to read actual error messages on Buckets B–D | Refine hypotheses | 30 min |
| 4 | Check `wiremock_stubs/{identity,provisioning,ai-gateway}/` for stub coverage | Confirm Buckets C, D | 20 min |
| 5 | If Buckets E, F persist after step 1: file Jira tickets for each | Track potentially-real bugs | varies |

---

## What this state document is NOT

- **NOT** a fix proposal. Recording only.
- **NOT** an assertion that any of these failures are real product bugs. Hypotheses ranked by confidence.
- **NOT** a guarantee that the same 37 fail next time — flaky tests may swap in/out.
