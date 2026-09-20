# `startupTest` — Smoke Result (PASS)

**Captured:** 2026-05-01
**Task:** `:convo-ai-test-integration:startupTest`
**Outcome:** ✅ **PASS**

---

## What this test does

`startupTest` verifies the Spring Boot ApplicationContext loads cleanly — all 200+ beans wire correctly under the mocked sandbox environment. It does NOT exercise HTTP endpoints, business logic, or backend integrations.

| Test class | `it.io.atlassian.micros.convoai.FullContextStartupIT` |
|---|---|
| Method | `Full application context loads successfully with all modules` |
| Source | `convo-ai-test-integration/src/test/kotlin/it/io/atlassian/micros/convoai/FullContextStartupIT.kt` |

---

## Result (from JUnit XML)

```xml
<testsuite tests="1" failures="0" errors="0" skipped="0" time="32.504">
  <testcase name="Full application context loads successfully with all modules"
            classname="it.io.atlassian.micros.convoai.FullContextStartupIT"
            time="0.4"/>
</testsuite>
```

| Metric | Value |
|---|---|
| Total tests | 1 |
| Pass | 1 |
| Fail | 0 |
| Skip | 0 |
| Wall time | 32.5s (32.5s = Spring context load; 0.4s = test body) |

---

## What this proves

- ✅ Mocked sandbox infrastructure works on this laptop
- ✅ Maven artifactory auth works (via `~/.gradle/init.d/` init script)
- ✅ All 200+ Spring beans wire correctly
- ✅ Redis env var resolution from `.nebulae/.env` works
- ✅ All sidecars (TCS, Statsig, AI Gateway, async-tasks Redis, etc.) start and respond to healthchecks
- ✅ JVM warm-up + bean instantiation completes in <60s

## What this does NOT prove

- Wire-protocol correctness with real backends
- Specific endpoint behavior
- Data flow through downstream services
- Performance under load
