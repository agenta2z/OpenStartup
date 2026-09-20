# 04 — Troubleshooting

Run-time failure modes, diagnoses, and tested workarounds. Items below are the ones encountered in real runs (not speculation).

---

## A. Sandbox-startup failures (`atlas nebulae start`)

| Symptom | Diagnosis | Fix |
|---|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop not running | Open Docker Desktop, wait for green status, retry |
| `port 8081 already in use` | Stale sandbox or local `bootRun` | `atlas nebulae stop && lsof -ti:8081 \| xargs kill -9` |
| `nebulae plugin not found` | Plugin not installed | `atlas update nebulae` or `bin/install-nebulae.sh` |
| Sandbox hangs on `Pulling image …` | Slow network or first-run pull | Wait — first pull is ~3-5 GB. Subsequent runs hit cache. |
| `Failed to start service: tcs-sidecar` | TCS image version mismatch in `nebulae.yml` | Run `atlas update` to refresh plugin definitions |
| `Permission denied: /var/run/docker.sock` | Docker socket not granted to your user | `sudo chmod 666 /var/run/docker.sock` (re-set on Docker restart) |

---

## B. SLAuth / auth failures

| Symptom | Diagnosis | Fix |
|---|---|---|
| `403 Forbidden: insufficient permissions` from SLAuth | Not in `micros-sv--convo-ai-platform-dl-admins` group | File IDM access request; lead time hours-days |
| `Token expired` mid-run | Sliver session expired (~12 h TTL) | Re-auth: `slauth token -g micros-sv--convo-ai-platform-dl-admins` |
| `awaiting Okta SSO` printout | First Sliver auth — needs browser tap | Click the URL, approve via Yubikey |
| ASAP signing fails | `asap-properties.json` missing or invalid | Verify file exists + parses as JSON; restore from git if corrupt |

---

## C. Spring context startup failures (the smoke test)

The startup test boots the full Spring context. If it fails, the failure stack trace is your friend. Common causes:

| Stack trace contains | Likely cause | Fix |
|---|---|---|
| `BeanCreationException: Could not autowire field` | New bean missing a constructor arg | Check `@Autowired` and `@Bean` config in the changed module |
| `IllegalStateException: Failed to load ApplicationContext` (no other detail) | Earlier bean failed; check above the stack | Read the FULL log, not just the failing test |
| `java.lang.OutOfMemoryError: Java heap space` | 4096m heap insufficient | Bump `maxHeapSize` in `convo-ai-test-integration/build.gradle.kts:373` to 8192m; long-term fix is to reduce eager bean init |
| `ClassNotFoundException: ...` | Module dependency missing in `build.gradle.kts` | Add the missing `implementation(project(":..."))` line |
| `Statsig client not initialized` | Test profile didn't disable Statsig | Verify `application-test.yml` has `statsig.local-mode=true` |

---

## D. Integration test failures (specific tests)

| Symptom | Diagnosis | Fix |
|---|---|---|
| `Connection refused: localhost:8081` | App didn't start in the sandbox | Check `atlas nebulae logs convo-ai-platform`; usually a config error |
| `404 Not Found` on a WireMock-mocked endpoint | Mapping not registered in `wiremocks/__files/` | Add the mapping; remember to commit |
| `Test timed out after 20s` | Slow downstream or thread starvation | Increase timeout via `-Djunit.jupiter.execution.timeout.testable.method.default=60s`; long-term, profile the test |
| `Flaky: passes 8/10 runs` | Race condition or test ordering bug | DON'T add `@Disabled` ad-hoc; file a ticket so the team can fix the flake |
| `SagemakerInvokeEndpoint AccessDeniedException` | IAM gap on real-LLM cohort tests | The integration-tests sandbox uses `*no-sagemaker-environment-variables-config` (mocked); if you see this, you accidentally ran with the `staging` sandbox instead |

---

## E. Gradle daemon / build failures

| Symptom | Diagnosis | Fix |
|---|---|---|
| `daemon expired with FAILED state` | Stuck daemon, possibly OOM | `./gradlew --stop && ./gradlew clean` |
| `Could not lock state of artifact transform cache` | Concurrent Gradle invocations | Don't run two `./gradlew` in parallel; `./gradlew --stop` first |
| `Configuration cache problems found` | Cache stale after build script change | `./gradlew --stop` and re-run; cache rebuilds automatically |
| `unable to find valid certification path` | Corp proxy + bad TLS chain | Check `gradle.properties` for proxy + truststore configuration |

---

## F. Diagnostic commands

```bash
# Show what containers Nebulae has running
atlas nebulae status

# Show logs for the convo-ai-platform service container
atlas nebulae logs convo-ai-platform | tail -100

# Show all healthcheck states
atlas nebulae health

# Force-stop everything (when graceful stop fails)
atlas nebulae stop --force

# Show what's bound to test-relevant ports
lsof -iTCP:8081 -sTCP:LISTEN
lsof -iTCP:9090 -sTCP:LISTEN  # statsig sidecar
```

---

## G. When you've tried everything

1. **`./gradlew --stop`** + restart Docker Desktop + `atlas nebulae stop --force` + retry
2. **`git stash` + `git checkout master`** + see if the same test passes on master (isolates "is it my code" from "is it the env")
3. **`bin/local-fix-everything`** — repo-provided "nuke and reset" script (read it first; it deletes a lot)
4. **Ask in #convo-ai-platform-dev** with the exact command + the last 200 lines of output; tag your on-call

---

## H. Known-flaky tests (track in CI dashboard, not here)

The team maintains a known-flaky test list in their dashboards. Don't memorize it. If a test fails locally:

```bash
# Re-run JUST that test 3 times
for i in 1 2 3; do
  echo "=== Attempt $i ==="
  ./gradlew :convo-ai-test-integration:integrationTest --tests 'TheFailingTest' \
    -Pnebulae.enabled=true || true
done
```

If 2/3 pass, it's flaky. File a ticket; don't disable.

---

## Real-world bugs encountered during first end-to-end run (2026-05-01)

These 4 issues were hit and resolved while running `startupTest` from a fresh state. Use this as a checklist when you hit similar errors.

### Bug 1: HTTP 401 on `packages.atlassian.com` during dependency resolution

**Symptom**:
```
> Could not GET 'https://packages.atlassian.com/maven/repository/internal/...'.
   > Received status code 401 from server: Unauthorized
```

**Root cause**: `settings.gradle.kts` and `build.gradle.kts` declare `maven { setUrl(...) }` blocks for `packages.atlassian.com` **without `credentials { ... }` blocks**. The only credentials block in the repo (settings.gradle.kts:41-46) is scoped to the build cache, not dependency repos. Gradle has no way to inject auth.

**Fix**: Write a one-time global Gradle init script at `~/.gradle/init.d/atlassian-credentials.gradle.kts` (see SOP 01.C and 03 for full content). It uses `mavenUser` / `mavenPassword` from `~/.gradle/gradle.properties` (which `bin/first-run` populates) and applies them to any repo whose host is `packages.atlassian.com`.

**Verify**: `curl -u $USER:$TOKEN https://packages.atlassian.com/maven/repository/internal/io/atlassian/micros/contrib/micros-spring-boot-starter-base/7.7.1/micros-spring-boot-starter-base-7.7.1.pom` returns 200.

---

### Bug 2: `startupTest` exits 0 but no test ran

**Symptom**: `BUILD SUCCESSFUL`, but `convo-ai-test-integration/build/test-results/startupTest/` is empty.

**Root cause**: `startupTest` task **does NOT auto-depend on `startNebulaeForTests`**. The task uses `doFirst { environment(getNebulaeEnvVars(rootDir)) }` which silently no-ops when `.nebulae/.env` is absent. The Spring Boot context then fails to load due to missing env vars.

**Fix**: Always run `atlas nebulae start -s integration-tests` BEFORE `./gradlew :convo-ai-test-integration:startupTest`.

---

### Bug 3: `Could not resolve placeholder 'REDISX_CONVOAI_ASYNC_TASKS_HOST'`

**Symptom**:
```
ApplicationContextException: Failed to start bean ...
Caused by: IllegalArgumentException: Could not resolve placeholder 'REDISX_CONVOAI_ASYNC_TASKS_HOST' in value "${REDISX_CONVOAI_ASYNC_TASKS_HOST}"
```

**Root cause**: Same as Bug 2 — sandbox isn't running or `.nebulae/.env` is missing/stale.

**Fix**: After Bug 2's fix, verify `.nebulae/.env` contains the var:
```bash
grep REDISX_CONVOAI_ASYNC_TASKS_HOST .nebulae/.env
# Expected: REDISX_CONVOAI_ASYNC_TASKS_HOST="127.0.0.1"
```

If missing, restart the sandbox:
```bash
atlas nebulae stop -s integration-tests
atlas nebulae start -s integration-tests
```

---

### Bug 4: Atlas / Nebulae prompts for Okta auth

**Symptom**: `atlas nebulae start` hangs printing:
```
Opening browser to continue authentication...
If your browser doesn't open automatically, please navigate to ...
https://atlassian.okta.com/activate?user_code=XXXXXXXX
```

**Root cause**: Atlas needs an Okta SSO token to fetch service-proxy credentials for the sandbox setup phase. Token is cached for ~hours, but expires.

**Fix**: Open the printed URL, complete Okta SSO (YubiKey + password), and the `atlas nebulae start` command resumes automatically. No re-run needed.

---

## Sequence-of-3-fixes summary

| Order | Fix | Effort |
|---|---|---|
| 1 | Add `~/.gradle/init.d/atlassian-credentials.gradle.kts` | One-time, 30s |
| 2 | Authenticate Atlas via Okta (when prompted) | One-time per session, 30s |
| 3 | Run `atlas nebulae start -s integration-tests` BEFORE `gradlew startupTest` | Per test run, ~3-5 min |

After these 3 fixes, the happy path in SOP 03 §"Verified-working happy path" runs cleanly to PASS.

