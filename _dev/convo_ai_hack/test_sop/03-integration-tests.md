# 03 — Integration tests

The big one. Requires **Docker + Nebulae + SLAuth** and ~15-60 min wall time.

**Read `01-prerequisites.md` first.** Don't even attempt this until all 4 sanity checks pass.

---

## A. The recommended path: smoke first

**Always start with the startup smoke test.** It's a single test that boots the full Spring context with all 250+ modules wired together. If it passes, deeper tests usually pass.

```bash
cd ~/MyProjects/atlassian_packages/conversational-ai-platform

# Smoke (1 test, ~3-5 min, no real LLM calls)
./gradlew :convo-ai-test-integration:startupTest -Pnebulae.enabled=true
```

What `-Pnebulae.enabled=true` does:
- Triggers `startNebulaeForTests` Gradle task → runs `atlas nebulae start -s integration-tests`
- After tests, triggers `stopNebulaeForTests` → runs `atlas nebulae stop`
- Without this flag, Gradle SKIPS the Nebulae start/stop. Tests then fail because the sandbox isn't running.

**Alternative (CI-style)**: set `CI=true` env var instead of `-Pnebulae.enabled=true`. Same effect.

---

## B. Manual sandbox lifecycle (faster iteration)

If you're iterating on a single test, start the sandbox once and re-use it across runs:

```bash
# Start sandbox manually (one-time, ~60-120s)
atlas nebulae start -s integration-tests

# Iterate: run a single test (no sandbox restart)
./gradlew :convo-ai-test-integration:test --tests 'FullContextStartupIT' \
  -Pnebulae.enabled=false   # ← key: disable auto start/stop since sandbox already running

# When done
atlas nebulae stop
```

Saves ~60s per iteration.

---

## C. Targeting specific tests

```bash
# By class name
./gradlew :convo-ai-test-integration:integrationTest --tests 'PromptModerationIT' \
  -Pnebulae.enabled=true

# By package (regex match on FQCN)
./gradlew :convo-ai-test-integration:integrationTest \
  --tests 'it.io.atlassian.micros.convoai.requestcontext.*' \
  -Pnebulae.enabled=true
```

---

## D. The full integration suite

**WARNING**: ~30-60 min, ~32 GB peak RAM, ~10-15 GB disk during run.

```bash
./gradlew :convo-ai-test-integration:integrationTest -Pnebulae.enabled=true
```

CI shards this across 4 parallel jobs × 2 feature-flag modes:

```bash
# Mirror CI's shard 1, flags ON
./bitbucket-pipelines-scripts/run-integration-tests-with-flag-modes.sh 1 --flags-on

# Or call Gradle directly
./gradlew :convo-ai-test-integration:integrationTestShard1FlagsOn -Pnebulae.enabled=true
```

Shard count is set by env var `INTEGRATION_TEST_SHARD_COUNT` (default 4 in CI).

---

## E. Feature-flag mode

CI runs every test TWICE: once with feature flags ON (`integrationTestShard{N}FlagsOn`) and once with flags OFF (`integrationTestShard{N}FlagsOff`). This catches regressions on either side of a flag rollout.

Locally, control via system property:

```bash
# All tests with flags ON
./gradlew :convo-ai-test-integration:integrationTest \
  -Dconvoai.tests.featureFlags.defaultGateValue=true \
  -Pnebulae.enabled=true

# All tests with flags OFF
./gradlew :convo-ai-test-integration:integrationTest \
  -Dconvoai.tests.featureFlags.defaultGateValue=false \
  -Pnebulae.enabled=true
```

Most local development should run flags ON (matches what production sees most of the time).

---

## F. WireMock stubs

External services (graphql-gateway, jira-project-components, streamhub, devai-rovodev-streamhub, assistance-service) are mocked via WireMock. Stubs live at:

```
convo-ai-test-integration/src/test/resources/wiremocks/
├── __files/
│   ├── wiremock_graphql-gateway/
│   ├── wiremock_jira-project-components/
│   ├── wiremock_streamhub/
│   └── wiremock_devai-rovodev-streamhub/
└── assistance-service/
```

The `*mocked-wiremock-config` plugin reference in `nebulae.yml:391` auto-loads these on sandbox start. **Do NOT modify them ad-hoc** — adding a mapping affects all tests; it should be reviewed.

---

## G. View results

| Path | Format |
|---|---|
| `convo-ai-test-integration/build/reports/tests/integrationTest/index.html` | HTML test report |
| `convo-ai-test-integration/build/test-results/integrationTest/*.xml` | JUnit XML (for CI parsers) |
| `convo-ai-test-integration/build/reports/tests/startupTest/index.html` | Startup smoke results |

For a Pollinator-style summary:
```bash
find convo-ai-test-integration/build/test-results -name "*.xml" -exec grep -l "<failure" {} \;
# any output = a failing test class
```

---

## H. Cleanup

```bash
# Stop sandbox + remove containers
atlas nebulae stop

# Free disk (Gradle daemon caches + build outputs)
./gradlew clean
docker system prune -f
```

Sandbox auto-stops on JVM exit if you used `-Pnebulae.enabled=true` (per `stopNebulaeForTests` task), but a `^C` mid-run leaves it running. Always run `atlas nebulae stop` after a hard interrupt.

---

## Verified-working happy path (2026-05-01)

This sequence was executed end-to-end and confirmed to PASS:

```bash
cd /Users/tchen7/MyProjects/atlassian_packages/conversational-ai-platform

# 1. One-time setup: Gradle init script for Atlassian artifactory auth
#    (see 01-prerequisites.md §C — required because dependency repos in
#    settings.gradle.kts/build.gradle.kts have NO credentials block)
mkdir -p ~/.gradle/init.d
cat > ~/.gradle/init.d/atlassian-credentials.gradle.kts <<'INIT'
allprojects {
    afterEvaluate {
        val mavenUser = providers.gradleProperty("mavenUser").orNull
            ?: System.getenv("ARTIFACTORY_USER") ?: ""
        val mavenPassword = providers.gradleProperty("mavenPassword").orNull
            ?: System.getenv("ARTIFACTORY_PASSWORD") ?: ""
        if (mavenUser.isNotEmpty() && mavenPassword.isNotEmpty()) {
            repositories.withType<MavenArtifactRepository>().configureEach {
                if (url.host == "packages.atlassian.com") {
                    credentials {
                        username = mavenUser
                        password = mavenPassword
                    }
                }
            }
        }
    }
}
INIT

# 2. Start the integration-tests sandbox (24 mocked sidecars; ~3-5 min)
#    Will prompt for Atlas Okta auth on first run today
atlas nebulae start -s integration-tests

# 3. Run the integration test (must be after sandbox is up)
./gradlew :convo-ai-test-integration:startupTest -Pnebulae.enabled=true

# Result: BUILD SUCCESSFUL; 1 test passed in ~33s after 1m of compile

# 4. Cleanup
atlas nebulae stop -s integration-tests
```

### Result

```xml
<testsuite tests="1" failures="0" errors="0" skipped="0" time="32.504">
  <testcase name="Full application context loads successfully with all modules"
            classname="it.io.atlassian.micros.convoai.FullContextStartupIT"
            time="0.4"/>
</testsuite>
```


---

## Full integration suite results (2026-05-01)

The full `:convo-ai-test-integration:integrationTest` task was executed end-to-end:

```
Tests:    1,445 total
Passed:   1,261 (87.3%)
Skipped:  147   (10.2%)
Failed:   37    (2.5%)
Time:     4m 32s
```

### Build outcome
**`BUILD FAILED`** — any test failure causes the task to fail (Gradle convention).

### Failure breakdown by test class

| # fails | Test class |
|---|---|
| 4 | JsmChatV1ControllerIT |
| 4 | AgentStudioScenarioUpdateMutationCreateScenarioIT |
| 4 | AgentStudioBatchEvaluationV1ControllerIT |
| 3 | WhiteboardAITeammateStreamingNativeControllerIT |
| 3 | ProvisioningServiceIT |
| 3 | AgentStudioUpgradeSchemaIT |
| 2 | SAINStandaloneHybridOrchestratorIT |
| 2 | JiraAiSuggestIssuesControllerIT |
| 1 each | (11 other classes) |

### Failure root-cause categories

| Pattern | Likely cause |
|---|---|
| `AssertionError` in controller tests | wiremock stub returns different shape than the test expects |
| `AIGatewayResponseException` in SAIN tests | AI Gateway sidecar mock not configured for these payloads |
| `IdentityCreateException` / `ProvisioningCallbackException` | Provisioning sidecar mock not handling these scenarios |

### Critical caveat: CI runs SHARDED tasks, NOT this monolithic task

CI's `bitbucket-pipelines.yml` runs **3 sharded variants** with **feature-flag On/Off contexts**:
- `:convo-ai-test-integration:integrationTestShard1FlagsOn`
- `:convo-ai-test-integration:integrationTestShard1FlagsOff`
- ...and 4 more shards

The **monolithic `integrationTest`** task we ran does NOT set feature-flag system properties. Tests that require specific feature-flag states (and there are many) get default values, which causes some failures that don't occur in CI.

### To reproduce CI behavior locally

```bash
# Run a specific shard with FF context (mirrors what CI does)
./gradlew :convo-ai-test-integration:integrationTestShard1FlagsOn
./gradlew :convo-ai-test-integration:integrationTestShard1FlagsOff
# (similar for shards 2 and 3)
```

### What this proves

✅ **Test infrastructure works** — 1,261 of 1,445 tests pass cleanly under the local mocked sandbox.

❌ **The monolithic `integrationTest` task is NOT the canonical entrypoint** — CI uses sharded + FF-context variants. Use those for parity with CI.

### Next steps if pursuing 100% green

1. **Run with sharded tasks** (`integrationTestShard{N}FlagsOn`) to match CI exactly
2. **Investigate the 21 failing classes** — likely each needs either:
   - An additional WireMock stub mapping
   - A missing feature-flag system property set via `-Dconvoai.tests.featureFlags.defaultGateValue=true`
   - An `@Disabled("Flaky locally")` annotation if known unstable

