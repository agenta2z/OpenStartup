# 01 — Prerequisites

Read this BEFORE attempting any test run. Each item is a real dependency; skipping any will cause confusing failures downstream.

---

## A. Toolchain

| Tool | Required version | Source of truth | Install |
|---|---|---|---|
| **Java** | 21 (Amazon Corretto 21.0.8 ideally; any 21.x works) | `.sdkmanrc:4` → `java=21.0.8-amzn` | `sdk install java 21.0.8-amzn` (auto-switches when you `cd` into the repo) |
| **Gradle** | 9.3.0+ (used via wrapper) | `gradle/wrapper/gradle-wrapper.properties` | `./gradlew` — no global install needed |
| **Atlas CLI** | latest stable | `bin/install-atlas.sh` | `brew install atlas-cli` or run `bin/install-atlas.sh` |
| **Nebulae plugin** | latest stable | `bin/install-nebulae.sh` | `atlas update nebulae` or run `bin/install-nebulae.sh` |
| **Docker** | Docker Desktop 4.20+ | implied by `processResources` task | Install Docker Desktop, **launch it** |
| **SDKMAN** | latest | for auto-Java-switching | `curl -s "https://get.sdkman.io" \| bash` |

**Verify all in one shot:**

```bash
java -version          # → openjdk version "21..."
./gradlew --version    # → Gradle 9.x
atlas --version        # → atlas vX.Y.Z
atlas nebulae --version # → nebulae plugin loaded
docker info            # → no error (daemon is running)
```

If any FAIL: `bin/first-run` is a one-shot installer that bootstraps everything. Run it.

---

## B. Auth & secrets

The integration-tests sandbox uses **mocked external services** (WireMock) so most secrets are NOT needed. But a few are:

| Secret | Where it's used | How to obtain |
|---|---|---|
| **SLAuth (Sliver) token** | Spring Cloud Config → fetches application config from staging | `slauth token -g micros-sv--convo-ai-platform-dl-admins` (one-time auth via Okta/Yubikey) |
| **TCS sidecar credentials** | Mocked in `integration-tests` sandbox — NOT needed | n/a |
| **AWS / SageMaker credentials** | NOT needed for `integration-tests` (uses `*no-sagemaker-environment-variables-config`) | n/a for smoke; needed for staging-with-real-LLM |
| **asap-properties.json** | ASAP service-to-service auth | Already in repo at `asap-properties.json` |

**Verify SLAuth works:**
```bash
slauth token -g micros-sv--convo-ai-platform-dl-admins | head -c 20
# should print 20 chars of a JWT (no error)
```

If that fails, you're not in the access group. File an IDM access request (lead time: hours-days) BEFORE attempting integration tests.

---

## C. Environment

The repo expects to be opened with `cd` (not `code .` from elsewhere) so SDKMAN auto-switches Java to 21.

```bash
cd ~/MyProjects/atlassian_packages/conversational-ai-platform
sdk current java   # → should show 21.0.8-amzn
```

**Memory budget**: integration tests JVM heap is 4096m × parallelism (default 8) = up to 32 GB. **Have at least 16GB RAM free** when running full integration suite. For smoke (`startupTest`), 4 GB is fine.

**Disk budget**: Docker images for the sandbox total ~3-5 GB on first run.

---

## D. Branch hygiene

Integration tests load configuration from your **current branch's** `gradle/`, `nebulae.yml`, and `convo-ai-test-integration/build.gradle.kts`. If you have uncommitted changes to these files, results may not match a clean CI run.

```bash
git status            # confirm clean tree (or accept that tests reflect your local mods)
git rev-parse HEAD    # note the commit you're testing
```

---

## E. Sanity checks BEFORE any test run

Run all 4. If any fails, **stop and fix it** before touching tests:

```bash
# 1. Java is 21
java -version 2>&1 | grep -q "version \"21" || { echo "FAIL: Java not 21"; exit 1; }

# 2. Atlas + nebulae are installed
atlas nebulae --version > /dev/null || { echo "FAIL: nebulae plugin missing"; exit 1; }

# 3. Docker daemon is running
docker info > /dev/null 2>&1 || { echo "FAIL: Docker daemon not running"; exit 1; }

# 4. Repo is up-to-date with origin/master (recommended, not required)
git fetch origin master --quiet
behind=$(git rev-list --count HEAD..origin/master)
[[ $behind -eq 0 ]] && echo "OK: up to date" || echo "INFO: $behind commits behind origin/master"
```

---

## F. Optional: pre-warm caches

First-time runs are slow (Gradle dependency resolution + Docker image pulls). To pre-warm:

```bash
./gradlew dependencies > /dev/null 2>&1 &  # background dependency resolve
atlas nebulae start -s integration-tests   # pulls all sandbox images (~3-5GB)
atlas nebulae stop                         # stop after pull (don't leave running)
```

This shaves 5-10 min off the first real test run.
