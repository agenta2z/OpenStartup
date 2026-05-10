# `integrationTest` — Full Suite Result (37 failures)

**Captured:** 2026-05-01
**Task:** `:convo-ai-test-integration:integrationTest`
**Outcome:** ❌ **BUILD FAILED** (37 of 1,453 tests failed)

---

## Aggregate

| Metric | Value |
|---|---|
| Total tests | 1,453 |
| **Pass** | **1,261** (86.8%) |
| **Fail** | **37** (2.5%) |
| Skip | 155 (10.7%) |
| Wall time | 4m 32s (in-build) / 22.5min CPU (`time=1351.9s` from XMLs) |
| JUnit XML files | 247 (one per test class) |

**Pass rate excluding skip:** 1,261 / 1,298 = **97.2%**

---

## Failures by class

| # fails | Test class |
|---|---|
| 4 | `agentstudio.graphql.AgentStudioScenarioUpdateMutationCreateScenarioIT$CreateScenario` |
| 4 | `agentstudio.rest.AgentStudioBatchEvaluationV1ControllerIT` |
| 4 | `jsm.rest.JsmChatV1ControllerIT` |
| 3 | `agentstudio.graphql.AgentStudioUpgradeSchemaIT` |
| 3 | `aifeature.rest.WhiteboardAITeammateStreamingNativeControllerIT` |
| 3 | `provisioning.ProvisioningServiceIT` |
| 2 | `aifeature.rest.JiraAiSuggestIssuesControllerIT` |
| 2 | `product.rovo.sain.SAINStandaloneHybridOrchestratorIT` |
| 1 | `agentstudio.graphql.AgentStudioAgentVersionQueryIT` |
| 1 | `agentstudio.graphql.AgentStudioScenarioCreateMutationIT` |
| 1 | `agentstudio.graphql.AgentStudioWidgetQueryIT` |
| 1 | `aifeature.graphql.JiraIssueRelatedResourcesGraphQLIntegrationIT` |
| 1 | `aifeature.graphql.JiraSimilarWorkItemsGraphQLIntegrationIT` |
| 1 | `aifeature.rest.CommentSummaryServiceIT` |
| 1 | `aifeature.rest.CommentSummaryStreamingServiceIT` |
| 1 | `aifeature.rest.ConvoStarterControllerIT` |
| 1 | `aifeature.rest.InvokeAgentIT` |
| 1 | `plugin.RovoPluginControllerIT` |
| 1 | `product.rovo.rest.ForceRatingControllerIT` |
| 1 | `product.rovo.sain.SAINExecutorWithSourcesIT` |

**Total:** 37 failures across **20 unique test classes**.

---

## Failures by exception type

| Count | Exception type | Pattern |
|---|---|---|
| 22 | `java.lang.AssertionError` | Status code mismatches OR "Response has 1 unexpected error" |
| 6 | `org.opentest4j.AssertionFailedError` | Stronger AssertJ failures (substring/null assertions) |
| 3 | `ProvisioningCallbackException` | Provisioning sidecar mock missing scenarios |
| 3 | `AIGatewayResponseException` | AI Gateway mock returning UNKNOWN_ERROR / SERVER_ERROR |
| 2 | `IdentityCreateException` | CSM Agent identity mock not handling some scenarios |
| 1 | `(unclassified)` | (one of the 22 categorized as AssertionError above had a deeper cause) |

---

## Failures by HTTP-status-mismatch sub-pattern (most common)

| Expected | Actual | Count |
|---|---|---|
| 200/SUCCESSFUL | **404 NOT_FOUND** | 8 |
| 200/SUCCESSFUL | **500 INTERNAL_SERVER_ERROR** | 2 |
| 429 TOO_MANY_REQUESTS | **404 NOT_FOUND** | 2 |
| 504 GATEWAY_TIMEOUT | **404 NOT_FOUND** | 1 |

**Dominant signal:** **404 NOT_FOUND when 200 was expected** — this strongly suggests certain endpoint routes aren't being exposed (likely a missing FF gate enabled-by-default, or a Spring profile not loaded in our local sandbox config).

---

## Detailed failure list

For each failure: `[file:line of first stack frame] test name → exception summary`

### `agentstudio.graphql.AgentStudioAgentVersionQueryIT` (1)
- `[AssertionFailureBuilder.java:152]` getAgentVersions returns version history after publishing(TenantContext)
  → `AssertionFailedError: actual value is null ==> expected: not <null>`

### `agentstudio.graphql.AgentStudioScenarioCreateMutationIT` (1)
- `[AssertionErrors.java:39]` create assistant scenario with agentic skills
  → `AssertionError: Response has 1 unexpected error(s) of 1 total`

### `agentstudio.graphql.AgentStudioScenarioUpdateMutationCreateScenarioIT$CreateScenario` (4)
- update scenario properties false to true
- update scenario with only mandatory fields
- update scenario with configured tool configuration
- update scenario throws user has no permission
- All → `AssertionError: Response has 1 unexpected error(s) of 1 total`

### `agentstudio.graphql.AgentStudioUpgradeSchemaIT` (3)
- upgradeSchema agent is queryable as V2 after migration
- upgradeSchema migrates single-scenario agent merging behaviour and prompt
- upgradeSchema migrates multi-scenario V1 agent to V2 with new default scenario
- All → `AssertionError: data.agentStudio_upgradeSchema.success expected:<true> but was:<false>`

### `agentstudio.graphql.AgentStudioWidgetQueryIT` (1)
- get widgets by agentAri and containerType PORTAL
  → `AssertionError: Response has 1 unexpected error(s) of 1 total`

### `agentstudio.rest.AgentStudioBatchEvaluationV1ControllerIT` (4)
- downloadResults should return CSV with evaluation results for Rovo agent → `Status expected:<200> but was:<404>`
- downloadResults should include judge reasoning when metrics exist → `IdentityCreateException: CSM Agent identity`
- downloadResults should handle empty results → `IdentityCreateException: CSM Agent identity`
- POST dataset upload [productType=CSM] → `Status 500 INTERNAL_SERVER_ERROR expected SUCCESSFUL`

### `aifeature.graphql.JiraIssueRelatedResourcesGraphQLIntegrationIT` (1)
- query aiFeature jira related confluence pages → `AssertionError: Response has 1 unexpected error`

### `aifeature.graphql.JiraSimilarWorkItemsGraphQLIntegrationIT` (1)
- query aiFeature jira similar work items query with control reranker → `AssertionError: Response has 1 unexpected error`

### `aifeature.rest.CommentSummaryServiceIT` (1)
- POST api v2 jira comment summary error due to invalid ARI
  → `AssertionError: Identity service returned 404 Not Found`

### `aifeature.rest.CommentSummaryStreamingServiceIT` (1)
- POST api v2 jira comment summary error due to invalid ARI
  → `AssertionError: type:ERROR INTERNAL...`

### `aifeature.rest.ConvoStarterControllerIT` (1)
- POST api v2 ai-feature convo starter → `Status 404 expected SUCCESSFUL`

### `aifeature.rest.InvokeAgentIT` (1)
- POST invoke_agent for summarize from trello → `Status 404 expected SUCCESSFUL`

### `aifeature.rest.JiraAiSuggestIssuesControllerIT` (2)
- [localeCode=en-US] → `Status 500 expected SUCCESSFUL`
- [localeCode=de-DE] → `Status 404 expected SUCCESSFUL`

### `aifeature.rest.WhiteboardAITeammateStreamingNativeControllerIT` (3)
- search plugin and diagram generation → `AssertionFailedError: Expected substring`
- search plugin and use router for document generation → `AssertionFailedError: Expected substring`
- non-streaming sub topics multi-search + document v2 → `Status 404 expected SUCCESSFUL`

### `jsm.rest.JsmChatV1ControllerIT` (4)
- conversationChannelMessageCreateStream → `Status 404 expected SUCCESSFUL`
- conversationChannelMessagesRateLimit → `Status expected 429 but was 404`
- conversationChannelMessageCreateStream429 → `Status expected 429 but was 404`
- conversationChannelMessagesGet504 → `Status expected 504 but was 404`

### `plugin.RovoPluginControllerIT` (1)
- test content read plugin returns doc → `AssertionError: Retrieved the following details for the urls`

### `product.rovo.rest.ForceRatingControllerIT` (1)
- test force rating with default ratio → `Status 404 expected SUCCESSFUL`

### `product.rovo.sain.SAINExecutorWithSourcesIT` (1)
- SAIN executor should include sources in final response
  → `AIGatewayResponseException: error_category: UNKNOWN_ERROR`

### `product.rovo.sain.SAINStandaloneHybridOrchestratorIT` (2)
- SAIN executor should execute with tool calls response → `AIGatewayResponseException: UNKNOWN_ERROR`
- SAIN executor should execute with basic response → `AIGatewayResponseException: SERVER_ERROR`

### `provisioning.ProvisioningServiceIT` (3)
- test activation → `ProvisioningCallbackException: Callback failed`
- test 410 callback from CP throws suitable exception → `AssertionFailedError: Expected exception of class`
- test hard deletion → `ProvisioningCallbackException: Callback failed`

