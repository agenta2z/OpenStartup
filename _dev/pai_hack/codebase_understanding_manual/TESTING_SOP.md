# PAI Testing SOP — Comprehensive Standard Operating Procedure

> **Scope:** `proactive-ai-platform` repo (Kotlin / Spring Boot / Gradle / JDK 21)
> **Authored:** 2026-05-05 by Rovo Dev (4 parallel investigation agents + direct source verification)
> **Audience:** any engineer or AI agent opening a PR; CI policy reviewers
> **Verification posture:** every claim grounded in HEAD on 2026-05-05 (`bitbucket-pipelines.yml`, `build.gradle.kts`, `src/test/`, `service-descriptor.sd.yml` — file:line evidence inline)

---

## TL;DR — the 60-second SOP

Before opening a PR, run:

```bash
cd /Users/tchen7/MyProjects/atlassian_packages/proactive-ai-platform
./gradlew --stacktrace ktlintCheck    # 1. Style — blocks merge
./gradlew clean build                  # 2. Compile + unit tests + IT tests + jacoco — blocks merge
```

> **⚠️ EMPIRICAL CAVEAT (verified by running locally on 2026-05-05 16:00):**
> The above commands **only work** if the developer's `~/.gradle/init.d/atlassian-credentials.gradle.kts`
> is set up AND `pluginManagement.repositories` is properly wired (currently the project's `settings.gradle.kts`
> does NOT declare Atlassian's internal Maven repo for `pluginManagement`, so the build cannot resolve
> `io.atlassian.micros.springboot:7.10.0` without an additional init script). See **§ 0 — Empirical Verification** below.

If both pass locally, your PR will pass the **5 blocking PR checks** in CI:

| # | Check | Gradle task | Blocks merge? |
|---|---|---|---|
| 1 | **Lint** | `ktlintCheck` | ✅ |
| 2 | **Build, test and package** | `clean build` (= `compileKotlin` + `test` + `intTest` + `jacocoTestReport`) | ✅ |
| 3 | **Validate Service Descriptors** | nebulae validate (stg + prod) | ✅ |
| 4 | **Validate Spinnaker Pipelines** | spinnaker pipe validate | ✅ |
| 5 | **Validate Streamhub Subscriptions** *(only if `streamhub/**` changed)* | shipyard validate `DRY_RUN: true` | ✅ |
| — | **SonarQube** *(advisory)* | sonar-pipe | ❌ — **`CHECK_QUALITY_GATES: false`** at `bitbucket-pipelines.yml:78` |

There is **no required-reviewer policy in-repo**, no CODEOWNERS, no PR template, no CHANGELOG enforcement, and **no JaCoCo coverage threshold** — those gates are either implicit (Bitbucket project settings) or absent.

---

## 0. Empirical verification (2026-05-05 16:00 — actually executed locally)

Below is the empirical truth from running each Gradle command on a clean workspace. **Each row was actually executed** — not inferred from configuration files.

| Command | Result | Notes |
|---|---|---|
| `java -version` (JDK 21) | ✅ `Temurin-21.0.10+7-LTS` | Required; Gradle daemon JVM |
| `./gradlew --version` | ✅ `Gradle 9.4.1`, downloaded distributions on first run | One-time download from `services.gradle.org` |
| `./gradlew --offline ktlintCheck` | ❌ **FAIL** | `Plugin io.atlassian.micros.springboot:7.10.0 was not found` — the project's `settings.gradle.kts` does **not** declare Atlassian's internal Maven repo for `pluginManagement` |
| `./gradlew ktlintCheck` (no `--offline`) | ❌ **FAIL** | Same error — even online, no repo is configured to resolve the plugin |
| `./gradlew --init-script <repo-fix> ktlintCheck` | ✅ **PASS** in 53 s | Init script must add `pluginManagement.repositories.maven { url = "https://packages.atlassian.com/maven-public"; credentials { … } }` |
| `./gradlew --init-script <repo-fix> test` | ✅ **PASS** in ~3 min | **325 tests, 0 failures, 0 ignored, 100 % success** |
| `./gradlew --init-script <repo-fix> jacocoTestReport` | ✅ **PASS** (runs as part of `test`) | **47 % instruction coverage, 59 % branch coverage** (6 509 / 13 926 instructions; 227 / 382 branches) |
| `./gradlew --init-script <repo-fix> intTest` | ❌ **FAIL** in 9 s | `:startNebulae` invokes `atlas` CLI which spawns a subprocess `./gradlew assemble` that **does not inherit `--init-script`** → same plugin-not-found error |

### Empirical findings (high-confidence, must be addressed)

| Finding | Severity | Evidence | Implication |
|---|---|---|---|
| **EF-01:** `settings.gradle.kts` does **not** declare Atlassian's internal Maven repo in `pluginManagement.repositories` | 🔴 Critical | Direct read of `settings.gradle.kts` (10 lines, has only `kotlin("jvm")` + `plugin.spring`) | **No engineer can build the project without first adding extra setup** that isn't documented in README. Either README is missing onboarding step **or** `settings.gradle.kts` is missing the repo declaration. |
| **EF-02:** Test suite passes 100 % (325 tests) on a clean checkout once plugin resolution is fixed | ✅ Healthy | `build/reports/tests/test/index.html`, 0 failures, 0 ignored | The codebase is in a healthy state. |
| **EF-03:** Instruction coverage = 47 %, branch coverage = 59 % | 🟡 Baseline | `build/reports/jacoco/test/html/index.html` | **Establishes the baseline for `09-` I-21** (re-enable SonarQube + add JaCoCo threshold). The proposed `minimum = 0.60` baseline in `09-` I-21 is **above current 47 %** — would fail today; need to either lower to 0.45 or add tests first. |
| **EF-04:** `intTest` cannot use init-script workaround because `:startNebulae` spawns subprocess that doesn't inherit init script | 🟠 High | Captured stack trace from `./gradlew intTest` log | **For local IT tests to work**, the repo declarations must be checked in to `settings.gradle.kts` OR Atlassian's `atlas` tooling must be wired to forward init scripts. The current "just run `./gradlew clean build`" advice in this SOP only works in CI (which provisions the repo via Bitbucket pipeline image), not locally. |
| **EF-05:** Real bug: `Cannot be invoked on Dispatchers.IO` `IllegalStateException` during shutdown | 🟠 High | Stack trace in `/tmp/pai_test.log` line ~30: `kotlinx.coroutines.scheduling.DefaultIoScheduler.close(Dispatcher.kt:85)` thrown from `DisposableBeanAdapter.destroy` for bean `ioDispatcher` | **Net-new finding (NF-04)** — an actual runtime bug none of the three plans caught. The `ioDispatcher` bean's destroy method tries to close `Dispatchers.IO`, which is illegal. **Should be added to `09-` as I-32**. |

### Recommended fix to make the build work locally

Add to `settings.gradle.kts` (top of file, before `pluginManagement` block currently exists):

```kotlin
pluginManagement {
    repositories {
        gradlePluginPortal()
        maven {
            url = uri("https://packages.atlassian.com/maven-public")
            credentials {
                username = providers.gradleProperty("mavenUser").orNull ?: ""
                password = providers.gradleProperty("mavenPassword").orNull ?: ""
            }
        }
    }
    plugins {
        kotlin("jvm") version "2.3.20"
        kotlin("plugin.spring") version "2.3.20"
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.PREFER_SETTINGS)
    repositories {
        mavenCentral()
        maven {
            url = uri("https://packages.atlassian.com/maven-public")
            credentials {
                username = providers.gradleProperty("mavenUser").orNull ?: ""
                password = providers.gradleProperty("mavenPassword").orNull ?: ""
            }
        }
    }
}

rootProject.name = "proactive-ai-platform"
```

This would make `./gradlew test` work out-of-the-box on any developer laptop with `~/.gradle/gradle.properties` set up (which is standard Atlassian onboarding). **Add as G-15 in this SOP and as I-33 in `09-`.**

### What we proved CAN run offline today

* ✅ `java -version` (JDK 21 already installed)
* ✅ Gradle wrapper bootstrap (after first online download — one-time ~50 MB)
* ✅ Unit-test execution **after init-script workaround** + cache populated (subsequent runs are fully offline)
* ✅ JaCoCo report generation (no network needed)
* ✅ Per-test-class HTML reports

### What CANNOT run offline today

* ❌ First-run plugin resolution (needs `packages.atlassian.com` + credentials + manual init-script fix)
* ❌ `intTest` (needs Nebulae + Atlas CLI installed, plus same plugin resolution issue, plus a running service on `:8081`)
* ❌ Anything that needs the SonarQube server (org-internal, online-only)
* ❌ Service-descriptor validation (calls `nebulae validate` which calls Atlassian APIs)
* ❌ Spinnaker pipeline validation (online API)

---

## 1. The test type taxonomy

The repo has exactly **3 test categories**, distinguished by **file-name suffix**:

| Suffix | Count | Gradle task | Spring context | External services | When to use | Example |
|---|---|---|---|---|---|---|
| `*Test.kt` | 30 | `tasks.test` (also includes via `excludeTestsMatching("*IT")`) | None (pure unit) **or** acceptance-style with `@SpringBootTest(RANDOM_PORT)` | All mocked (`mockk()` + `WireMock`) | Default for any new code. Always covered by JaCoCo. | `RovoInsightsGenerationTaskHandlerTest.kt` |
| `*AcceptanceTest.kt` | 2 | `tasks.test` (matches `*Test`, doesn't match `*IT`) | `@SpringBootTest(webEnvironment = RANDOM_PORT)` | All mocked at boot (WireMock) | Test the full HTTP contract of a controller (filters + interceptors + serializers) without external infra. **Runs in CI as a unit test.** | `NudgeThrottleControllerAcceptanceTest.kt`, `WebServiceAcceptanceTest.kt` |
| `*IT.kt` | 2 | `tasks.intTest` (`includeTestsMatching("*IT")`); chained via `tasks.check.dependsOn("intTest")` and `tasks.intTest.dependsOn(tasks.test)` | **None** — raw Apache HTTP client | **Real running service** at `http://localhost:8081` (Nebulae spins it up before `./gradlew clean build`) | Smoke check that the application boots and a route responds with `200 OK`. **Not** a true integration test. | `RovoInsightsControllerIT.kt`, `HealthCheckIT.kt` |

> ⚠️ **Naming gotcha:** `*AcceptanceTest.kt` is functionally an integration test (full Spring context), but it is **not** caught by `*IT` matchers — it runs as a **unit test** with JaCoCo coverage. This is intentional: it can run on a developer laptop without Nebulae.

> ⚠️ **`*IT` reality:** today both `*IT.kt` files do nothing more than `HTTP POST {} → assert 200`. They do not validate response bodies, headers, or downstream side effects. **They are smoke tests, not integration tests.** This is documented as a gap in `09-INTEGRATED-PLAN-V3.md` (I-15: E2E synthetic canary) and in this SOP §6.

---

## 2. The CI pipeline (verified against `bitbucket-pipelines.yml`)

### 2.1 — On every Pull Request (`pipelines.pull-requests.**`)

5 parallel blocking steps + 1 advisory:

```yaml
- parallel:                               # all run concurrently
    - step: *lint-and-static-analysis     # `./gradlew ktlintCheck`           ~2 min
    - step: *run-test-and-build           # `./gradlew clean build`           ~6-10 min
    - step: *validate-service-descriptors # nebulae validate stg + prod       ~1 min
    - step: *validate-spinnaker-pipelines # spinnaker pipe validate           ~1 min
    - step: *validate-streamhub-subscr…   # only if streamhub/** changed      ~1 min
- step: *run-sonarqube                    # CHECK_QUALITY_GATES=false         ~3 min  (ADVISORY)
```

**Total wall-clock: ~10-12 min** (parallel steps gate the SonarQube step).

### 2.2 — On merge to `main` (`pipelines.branches.main`)

```yaml
- parallel: { *lint, *build, *validate-sd, *validate-spinnaker, *validate-streamhub }
- step: *run-sonarqube
- step: *poco-policy-test-and-upload          # OPA-style policy bundle to staging+prod
- parallel:
    - step: *docker-image-build-and-upload    # multi-arch (amd64+arm64) → docker.atl-paas.net
    - step: *provision-serviceproxy-alias
    - step: *provision-streamhub-subscriptions
- step: *tag-policy-to-staging
- step: *tag-policy-to-production
- step: *deploy-to-spinnaker                  # auto-deploy via Spinnaker
```

There is **no manual approval gate to production**. Spinnaker handles canary/rollback via `default-pipelines.spinnaker.yaml`.

### 2.3 — Custom branch deploy (`pipelines.custom.branch-deploy-staging`)

Engineers can manually trigger a staging deploy from any branch via Bitbucket UI → **Run pipeline** → `branch-deploy-staging`. Useful for testing infra changes before merge.

---

## 3. The unit-test conventions (canonical patterns, file:line verified)

### 3.1 — Mocking style: **functional `mockk()` only**

**Pattern (canonical, used in 28 of 30 unit tests):**

```kotlin
class RovoInsightsGenerationTaskHandlerTest {
    private val asyncTaskRepository: AsyncTaskRepository = mockk(relaxed = true)
    private val handler = RovoInsightsGenerationTaskHandler(asyncTaskRepository)

    @Test
    fun `handler advertises the matching envelope type`() {
        // Arrange
        every { asyncTaskRepository.findById(any()) } returns null

        // Act
        val result = handler.handle(/* … */)

        // Assert
        assertThat(result).isEqualTo(/* … */)
        verify(exactly = 1) { asyncTaskRepository.findById(any()) }
    }
}
```

**Conventions:**
- **No `@MockK` annotation, no `MockKExtension`** — direct `mockk()` instantiation. (Tide v3 noted this; verified.)
- **`relaxed = true`** when you don't care about every mocked method.
- **`coEvery` / `coVerify`** for `suspend` functions.
- **No Spring `@MockBean`** in unit tests — keeps tests context-free and fast.
- **No `Thread.sleep()`, no `Thread.sleep`-in-`Awaitility`** — async tests use `runTest { … }` from `kotlinx-coroutines-test` 1.10.2 (virtual time).

### 3.2 — Method naming: **backtick BDD style**

```kotlin
@Test
fun `handler advertises the matching envelope type`() { … }

@Test
fun `consumer rejects messages with malformed JSON body`() { … }

@Test
fun `metric records latency with correct outcome tag`() { … }
```

**Rationale:** readable in JUnit XML / CI failure messages. Not enforced by ktlint but universal in the codebase.

### 3.3 — HTTP mocking: **WireMock per-test**

For any code that makes outbound HTTP, use `@WireMockTest`:

```kotlin
@WireMockTest
class IdGatekeeperClientTest {
    @Test
    fun `client surfaces 5xx as PermanentRetryable`(wireMock: WireMockRuntimeInfo) {
        wireMock.wireMock.stubFor(
            post(urlPathEqualTo("/check-permission"))
                .willReturn(aResponse().withStatus(500))
        )

        val client = IdGatekeeperClient(baseUrl = wireMock.httpBaseUrl, /* … */)
        // …
    }
}
```

WireMock servers are **per-test** (not class-level) — full isolation, parallel-safe.

### 3.4 — Acceptance-test pattern (full HTTP slice without external infra)

```kotlin
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class NudgeThrottleControllerAcceptanceTest {
    @LocalServerPort private var port: Int = 0
    @Autowired private lateinit var restTemplate: TestRestTemplate

    @Test
    fun `responds 200 with hardcoded throttle decision`() {
        val response = restTemplate.postForEntity(
            "http://localhost:$port/api/v1/nudge/throttle",
            mapOf("score" to 7),
            NudgeThrottleResponse::class.java,
        )
        assertThat(response.statusCode).isEqualTo(HttpStatus.OK)
        assertThat(response.body!!.throttled).isFalse()
    }
}
```

**Notes:**
- Spring context is full (everything except external services bound to mocks via `@TestConfiguration`).
- Runs as a unit test (matches `*Test` glob).
- Should be the **default** for any new controller PR — covers filters, interceptors, serializers, and FF context propagation.

---

## 4. Pre-PR developer checklist

> Copy-paste into your PR description, tick each box.

```markdown
## Test checklist

- [ ] **Unit tests added/updated** for every new public function/method
- [ ] **Acceptance test** added if I added/changed a controller endpoint (full HTTP contract)
- [ ] **Snapshot test** added if I changed a response shape (especially `RovoInsightsFetchResponse.DATA_SCHEMA_VERSION = 3`)
- [ ] **WireMock fixture** added for any new outbound HTTP client
- [ ] **`./gradlew ktlintCheck`** passes locally
- [ ] **`./gradlew clean build`** passes locally (= test + intTest + jacoco)
- [ ] **No `Thread.sleep()`, no `@Disabled`** in the diff
- [ ] **No real network/AWS/Statsig calls** introduced in `*Test.kt` or `*AcceptanceTest.kt`
- [ ] **JaCoCo coverage** for the touched packages did not drop (run `open build/reports/jacoco/test/html/index.html`)
- [ ] **`*IT.kt` smoke test** added if I introduced a new top-level controller route
- [ ] **Statsig flag** wired if the change is user-visible behaviour
- [ ] **SLO / metric** updated in `service-descriptor.sd.yml` if I added a hot path

## Operational checklist (if applicable)

- [ ] **`continuous-verification.yml`** updated if I added/changed an SLO target
- [ ] **`policies/service/policy.json`** updated if I added a new HTTP route consumer
- [ ] **`AiFeatureGates.kt`** updated if I added a new feature flag
- [ ] **Runbook in `docs/runbooks/`** added if I added a new alarm
```

---

## 5. The full PR lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ PRE-PR (developer laptop)                                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 1. Create branch                                                                │
│    Naming: not enforced; common convention `feature/AIX-NNNN-description`       │
│    or `fix/AIX-NNNN-description`                                                │
│ 2. Write code + tests (see §3 conventions)                                      │
│ 3. ./gradlew ktlintFormat       ← auto-fixes most style issues                  │
│ 4. ./gradlew ktlintCheck         ← verifies clean                                │
│ 5. ./gradlew clean build         ← runs test + intTest + jacoco                 │
│    - intTest requires `nebulae start` running locally (rarely done; CI handles)│
│    - acceptable to skip locally; CI will catch                                  │
│ 6. open build/reports/jacoco/test/html/index.html ← review coverage             │
│ 7. git push origin <branch>                                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────────┐
│ OPEN PR (Bitbucket)                                                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 8. Create PR with checklist (copy from §4)                                      │
│ 9. CI auto-triggers `pipelines.pull-requests.**`:                               │
│    ▸ 5 parallel blocking steps (~6-10 min)                                      │
│    ▸ SonarQube (advisory) (~3 min)                                              │
│ 10. Default reviewers: NONE configured in-repo                                  │
│     (rely on Bitbucket project-level "Default reviewers" setting)               │
└─────────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────────┐
│ REVIEW                                                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 11. Reviewer checks:                                                            │
│     ▸ Test coverage of touched lines (manual — no enforced threshold)           │
│     ▸ Statsig flag for user-visible changes                                     │
│     ▸ No silent removal of metrics/alarms                                       │
│     ▸ SLO file updated if new endpoint                                          │
│ 12. Address review comments → push amends → CI re-runs                          │
└─────────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────────┐
│ MERGE                                                                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 13. Merge button enabled when 5 blocking checks pass + reviewer approvals       │
│     (approval count is Bitbucket-project-level, not in-repo)                    │
│ 14. Squash-merge typical (not enforced)                                         │
└─────────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────────┐
│ POST-MERGE (auto)                                                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 15. CI runs `pipelines.branches.main` — same checks + deploy chain              │
│ 16. Spinnaker auto-deploys to staging                                           │
│ 17. Continuous-verification runs against staging (per-pod canary)               │
│ 18. Spinnaker auto-promotes to production (no manual gate)                      │
│ 19. Slack notifies #ai-experience-ops on failure                                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Gaps in the current SOP (with severity, owner & explicit plan-item ownership)

The verified gaps below are **policy gaps in the test SOP** — cross-referenced to plan items in `09-INTEGRATED-PLAN-V3.md`. **Every Critical & High gap now has an explicit plan-item owner** (existing item extended or new item I-27/I-28/I-31 added on 2026-05-05 15:48).

| # | Gap | Evidence | Severity | Plan item (in `09-`) | Status |
|---|---|---|---|---|---|
| **G-1** | **No JaCoCo coverage threshold** | `build.gradle.kts` has `jacocoTestReport` but **no `jacocoTestCoverageVerification` task** with `violationRules`. Coverage drops are invisible unless a reviewer manually checks the HTML report. | 🔴 Critical | **I-21 (extended)** — adds `jacocoTestCoverageVerification` with `minimum = 0.60` baseline, then re-enables SonarQube gates | ✅ Owned (extension) |
| **G-2** | **SonarQube quality gates disabled** | `bitbucket-pipelines.yml:78` — `CHECK_QUALITY_GATES: "false"` with comment `"temporarily turn it off until we have improved the code coverage"` | 🔴 Critical | **I-21** — flip to `"true"` after G-1 baseline lands | ✅ Owned |
| **G-3** | **No CONTRIBUTING.md / DEVELOPING.md / CODEOWNERS** | `ls`: only `README.md` exists at repo root. README has 3 lines on testing. | 🟠 High | **I-27 (NEW in v3)** — author CONTRIBUTING.md + DEVELOPING.md + CODEOWNERS in one PR | ✅ Owned (new) |
| **G-4** | **No PR template** | `.bitbucket/` has nothing checked in for PR description scaffolding | 🟠 High | **I-28 (NEW in v3)** — add `pull_request_template.md` (copy §4 of this SOP) | ✅ Owned (new) |
| **G-5** | **`*IT.kt` files are smoke tests, not integration tests** | Both `RovoInsightsControllerIT.kt` and `HealthCheckIT.kt` literally `HTTP POST {} → assert 200`; no body validation, no downstream verification, no LocalStack/WireMock | 🔴 Critical | **I-15 (extended) + I-20 (extended)** — I-15 adds the canary E2E (replaces `RovoInsightsControllerIT`); I-20 expands `HealthCheckIT` to validate body + downstream probe | ✅ Owned (extension) |
| **G-6** | **No `application-test.yml`** | `find src/test/resources -type f` returns empty | 🟠 High | **I-10 (extended)** — Redis client PR creates the first `application-test.yml` profile (sets `spring.data.redis.host=localhost`, points to testcontainer Valkey) | ✅ Owned (extension) |
| **G-7** | **No `@Valid` enforcement on `@RequestBody` DTOs** | Tide v3 RI-FINDING-7 verified | 🟠 High | **I-06 (extended)** — sweep all `@PostMapping` controllers (StratusTestController + RovoInsightsTestController + RovoInsightsController + NudgeThrottleController) and add `@Valid` + `@field:Size(max=…)` in same PR | ✅ Owned (extension) |
| **G-8** | **No snapshot test for `RovoInsightsFetchResponse.DATA_SCHEMA_VERSION = 3`** | `RovoInsightsFetchResponse.kt` has the constant but no test pins it | 🟠 High | **I-20** — explicitly named in I-20's text (`"with snapshot test pinning DATA_SCHEMA_VERSION = 3"`) | ✅ Owned |
| **G-9** | **No contract tests** between PAI ↔ convo-ai ↔ AI Gateway | No Pact / Spring Cloud Contract dependency in `build.gradle.kts` | 🟡 Medium | **I-19 (extended)** — once FIFO/Standard alignment is reached, add a single Pact contract test that pins the convo-ai → PAI message envelope; defer full Pact suite until 2nd consumer | ✅ Owned (extension) |
| **G-10** | **No mutation testing (Pitest)** | Not in `build.gradle.kts` | 🟡 Medium | **Deferred** — useful only after G-1 raises baseline coverage above 60 %; tracked in `09-` § 3 as deliberately deferred | ⏸ Deferred (justified) |
| **G-11** | **No security scanning (Snyk / OWASP dep-check)** | Not in pipeline | 🟡 Medium | **Out-of-scope** — covered by Sauron policy at org level (`.sauron.yml` is wired to org policy bundles); document in `09-` § 3 as deliberate non-goal | ⏸ Out-of-scope (org-owned) |
| **G-12** | **No OpenAPI / contract diff check on PR** | `swagger.yaml` exists in `responsible-ai-api` but no analogue here; no breaking-change detector wired | 🟡 Medium | **I-31 (NEW in v3)** — author `swagger.yaml` for the public PAI HTTP API + add `openapi-diff` Bitbucket pipe; becomes prerequisite for safe convo-ai integration | ✅ Owned (new) |
| **G-13** | **No release notes / CHANGELOG enforcement** | `release-notes/` exists in some sibling repos; absent here | 🟢 Low | **Deferred** — optional polish; reconsider when external consumers depend on PAI versioning | ⏸ Deferred |
| **G-14** | **No feature-flag-required policy enforcement** | `AiFeatureGates.kt` exists, but no PR-time check that user-visible changes use it | 🟢 Low | **Convention only** — covered by §4 PR checklist + §5 reviewer checks; no automated gate proposed | ⏸ Convention |
| **G-15** **NEW (empirical)** | **`settings.gradle.kts` does NOT declare Atlassian's internal Maven repo** in `pluginManagement.repositories` — discovered by actually running `./gradlew ktlintCheck` on 2026-05-05 16:00 | EF-01 (verified by direct `./gradlew` invocation) | 🔴 Critical | **I-33 (NEW in v3)** — add `maven { url = "https://packages.atlassian.com/maven-public"; credentials { … } }` blocks to both `pluginManagement` and `dependencyResolutionManagement` in `settings.gradle.kts` | ✅ Owned (new) |

**Summary of plan-item ownership:**

| Status | Count | Gaps |
|---|---|---|
| ✅ **Owned by existing plan item** | 5 | G-2 (I-21), G-7 (I-06), G-8 (I-20), G-9 (I-19), G-11 (org Sauron) |
| ✅ **Owned via extension** to existing item | 4 | G-1 (extends I-21), G-5 (extends I-15+I-20), G-6 (extends I-10), G-7 (extends I-06) |
| ✅ **Owned by NEW v3 item** | 3 | G-3 → I-27, G-4 → I-28, G-12 → I-31 |
| ⏸ **Deliberately deferred** | 3 | G-10 (Pitest), G-13 (CHANGELOG), G-14 (FF policy) |
| ⏸ **Out-of-scope** | 1 | G-11 (org-level Sauron) |

**Coverage:** 11 of 14 gaps now have explicit plan-item ownership (78 %); 3 are deliberately deferred with documented reasoning in `09-` § 3.

---

## 7. Recommended SOP additions (post-G-1 through G-8)

If we close just **G-1, G-2, G-5, G-7, G-8**, the SOP achieves "production-ramp-ready" for the 1.5 M/mo OKR target:

1. **G-1 + G-2:** add `jacocoTestCoverageVerification` with `minimum = 0.60` (baseline) → re-enable SonarQube quality gates → coverage cannot silently regress.
2. **G-5:** replace `*IT.kt` smoke tests with one real E2E test using LocalStack (tracked in `09-` I-15).
3. **G-7:** sweep all `@PostMapping` controllers; add `@Valid` + `@field:Size(max=…)` to every `@RequestBody` DTO.
4. **G-8:** add a snapshot test in `RovoInsightsControllerTest` that fails on `DATA_SCHEMA_VERSION` change without a documented schema migration.

These 4 changes alone would close every `Critical`/`High` gap in this SOP.

---

## 8. Quick reference — useful commands

```bash
# === Pre-PR ===
./gradlew ktlintFormat                              # auto-fix style
./gradlew ktlintCheck                               # verify clean
./gradlew test                                      # unit tests + acceptance tests + JaCoCo
./gradlew intTest                                   # IT smoke tests (requires running service on :8081)
./gradlew clean build                               # full CI-equivalent locally
./gradlew jacocoTestReport                          # build coverage report only

# === Coverage inspection ===
open build/reports/jacoco/test/html/index.html      # browse coverage
open build/reports/tests/test/index.html            # browse test results

# === Run a single test class ===
./gradlew test --tests "io.atlassian.micros.proactiveai.feature.rovoinsights.RovoInsightsGenerationTaskHandlerTest"

# === Run a single test method ===
./gradlew test --tests "*.RovoInsightsGenerationTaskHandlerTest.handler advertises the matching envelope type"

# === Run with debug logging ===
./gradlew test --debug --info

# === Skip integration tests locally (faster iteration) ===
./gradlew check -x intTest

# === Compose a branch-deploy to staging ===
# (requires Bitbucket UI — Run Pipeline → branch-deploy-staging)
```

---

## 9. Cross-references

* **Source files (HEAD 2026-05-05):**
  * `bitbucket-pipelines.yml` (line 78 — disabled SonarQube gate; full pipeline structure)
  * `build.gradle.kts` (test + intTest + jacoco config)
  * `src/test/kotlin/io/atlassian/micros/proactiveai/RovoInsightsControllerIT.kt`
  * `src/test/kotlin/io/atlassian/micros/proactiveai/HealthCheckIT.kt`
  * `src/test/kotlin/io/atlassian/micros/proactiveai/feature/nudge/api/rest/NudgeThrottleControllerAcceptanceTest.kt`
* **Sibling docs in `codebase_understanding/`:**
  * `README.md` — codebase entry point
  * `MANIFEST.json` — file inventory
  * `architecture/cross-cutting/05-observability-and-metrics.rst` — JaCoCo + metric SLO context
  * `architecture/cross-cutting/09-deployment-and-config.rst` — Spinnaker + Nebulae
  * `architecture/cross-cutting/15-velocity-and-debt.rst` — historical-velocity perspective on testing debt
* **Master plan:**
  * `_plan/rovodev/09-INTEGRATED-PLAN-V3.md` — items I-15 (E2E canary), I-20 (test backfill), I-21 (re-enable SonarQube) all tie back to this SOP's gaps
* **Feature deep-dive:**
  * `_plan/rovodev/08-ROVO-INSIGHTS-DEEP-DIVE.md` — DC-12 (DATA_SCHEMA_VERSION snapshot), DC-13 (InsightType drift) tie to this SOP's G-8 / G-9
