# Convo AI Platform — Test State Snapshot

**Captured:** 2026-05-01 14:35 PT
**Author:** Rovo Dev (automated session)
**Repo:** `/Users/tchen7/MyProjects/atlassian_packages/conversational-ai-platform`

---

## Repo state at capture time

| Field | Value |
|---|---|
| Branch | `main` |
| HEAD commit | `9151ac1341583a0a1ba81d5742f904ff2c43d62b` |
| HEAD commit subject | `Merged in aknight/support-multi-bodied-extensions (pull request #28959)` |
| Tracked files modified | **0** |
| Untracked files | 4 (Archive.lib, docs/deep_research/, docs/deep_research_docs.tar.gz, jira_api_tools_agents_report.md — pre-existing artifacts, not from this session) |

**This snapshot represents PRISTINE master.** No code changes were applied during this session.

---

## Tests run (in order)

| # | Task | Outcome | Tests | Pass | Fail | Skip | Time |
|---|---|---|---|---|---|---|---|
| 1 | `:convo-ai-test-integration:startupTest` | ✅ **PASS** | 1 | 1 | 0 | 0 | 32.5s |
| 2 | `:convo-ai-test-integration:integrationTest` | ❌ **BUILD FAILED** | 1,453 | 1,261 | **37** | 155 | 4m 32s |

**Combined pass rate (excluding skipped):** 1,262 / 1,299 = **97.2%**

---

## Environment

| Component | Version / Status |
|---|---|
| Java | OpenJDK Temurin 21.0.10 |
| Atlas | 1.96.0 |
| Nebulae | 4.53 |
| Docker Desktop | running, 24 sandbox containers up during runs |
| Sandbox | `integration-tests` (mocked WireMock + sidecars) |
| Gradle | 9.3.0 (wrapper-bundled) |

### One-time setup applied (NOT a code change to the repo)

- Wrote `~/.gradle/init.d/atlassian-credentials.gradle.kts` to inject Maven credentials into `packages.atlassian.com` repos. Required because the repo's `settings.gradle.kts` and `build.gradle.kts` declare these repos WITHOUT `credentials { ... }` blocks. Without this script, all dependency resolution fails with HTTP 401.

---

## Files in this state directory

| File | Purpose |
|---|---|
| `00-state-snapshot.md` | This file — overall summary |
| `01-startupTest-result.md` | Detailed `startupTest` result (PASS) |
| `02-integrationTest-result.md` | Detailed `integrationTest` result (37 failures) |
| `03-failure-classification.md` | Analysis of failure patterns |
| `failures.json` | Raw failure data (machine-parseable) |

---

## Caveat: monolithic `integrationTest` ≠ what CI runs

CI (per `bitbucket-pipelines.yml`) runs **6 sharded variants** (3 shards × 2 FF contexts):

```
:convo-ai-test-integration:integrationTestShard1FlagsOn
:convo-ai-test-integration:integrationTestShard1FlagsOff
:convo-ai-test-integration:integrationTestShard2FlagsOn
:convo-ai-test-integration:integrationTestShard2FlagsOff
:convo-ai-test-integration:integrationTestShard3FlagsOn
:convo-ai-test-integration:integrationTestShard3FlagsOff
```

The non-sharded `:convo-ai-test-integration:integrationTest` task (the one we ran) does NOT set feature-flag system properties. Some failures may be due to tests expecting specific FF states that aren't set in the monolithic run.

**Important:** The 37 failures captured here may NOT all reproduce on CI. Some are likely environment-specific (mocked-stub gaps, missing FF context).

