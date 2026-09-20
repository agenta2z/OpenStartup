# 08 — Live integration sandbox (re-using a running Nebulae stack)

> **Why this exists.** Spinning the 18-container Nebulae sandbox takes 60-180 s. If the sandbox is already running, **iteration speed is 5-10× faster** by re-using it instead of restarting per test invocation. This file documents the canonical workflow with a worked example using the **currently-running session** at the time of writing.
>
> **Caveat.** Sandbox state is mutable. If a prior test left dirty data (a half-completed conversation, a stale flag override), re-using the sandbox can produce false failures. When in doubt, restart (cf. §F).

---

## A. Verifying a sandbox is running (current state)

> **CRITICAL** (verified 2026-05-04 — see `09-end-to-end-verification-log.md` §C.1).
> A sandbox showing `Up N days` in `docker ps` is NOT necessarily healthy. The Docker proxy keeps the host port open even when the container's app process has died. **Always run the §A.0 health check** before relying on a re-used sandbox.

### A.0 — Health check (run before `-Pnebulae.enabled=false`)

```bash
# All critical mocks must respond within 3 seconds.
HEALTHY=true
for svc_port in wiremock:7777 localstack:56574 ers-control:9001 ers-data:9002; do
  name=${svc_port%%:*}; port=${svc_port##*:}
  rc=$(curl -s --max-time 3 -o /dev/null -w "%{http_code}" "http://127.0.0.1:$port/")
  if [ "$rc" = "000" ]; then
    echo "DEGRADED: $name ($port) TCP-accepts but returned no HTTP body in 3s. RESTART required."
    HEALTHY=false
  else
    echo "OK     : $name ($port) HTTP $rc"
  fi
done
$HEALTHY || exit 1
```

If degraded:
```bash
docker compose --project-name convo-ai-integration-tests-<session-id> down -v
atlas nebulae start -s integration-tests   # 60-180 s
# then re-run §A.0
```

### A.1 — Container listing

```bash
docker ps --filter "name=convo-ai-integration-tests" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

> **NOTE:** `atlas nebulae status` does NOT exist (verified 2026-05-04). Only `start` and `stop`. Use `docker ps` as above.

**As of 2026-05-04 (verified at session-start):** session `3f2a39fb` is running, 18 containers, all `Up 2 days` (started `2026-05-01T21:00:45Z`). The compose project is:

```
com.docker.compose.project          = convo-ai-integration-tests-3f2a39fb
com.docker.compose.project.working_dir = atlassian_packages/conversational-ai-platform/.nebulae/integration-tests
```

The compose files are at:
```
.nebulae/integration-tests/docker-compose.resources.yml
.nebulae/integration-tests/docker-compose.dependencies.yml
.nebulae/integration-tests/docker-compose.webserver.yml
… (full set of docker-compose.*.yml in that directory)
```

Sandbox name = `integration-tests`; session id = `3f2a39fb`.

---

## B. Service → host port map (current session, verified)

| Service | Container name suffix | Host port | Purpose |
|---|---|---|---|
| WireMock | `wiremock-1` | **7777** | Mocks all external HTTP (AI Gateway, Confluence, Jira, Loom, etc.) |
| LocalStack | `localstack-1` | **56574** | AWS mocks (S3, SQS, DynamoDB, Stepfunctions) |
| Redis (cache) | `nebulae-convoai-cache-redisx-1` | **56575** | App cache backend |
| TCS sidecar (egress) | `tcs-sidecar-1` | **56578-56580** | Tenant Context Service mock |
| Platform statsd | `platform-statsd-1` | **56581** (TCP), **56774** (UDP) | Metrics ingestion |
| SLAuth mock egress | `egress-1` | **9100-9169** | Outbound SLAuth mock |
| SLAuth mock sidecar (platform) | `platform-slauth-1` | **8081**, **9090** | **NOTE: 8081 is normally the app port. Check the app config carefully.** |
| SLAuth mock sidecar (regular) | `slauth-1` | **7404**, **7405** | Inbound SLAuth mock |
| Hofund | `hofund-1` | **9800** | Atlassian config service |
| Nebulae proxy (envoy) | `nebulae-proxy-1` | **8090**, **56576**, **56577** | Reverse proxy gateway |
| TDP control | `tdp-control-1` | **7401** | Tenant Data Provisioning control |
| TDP OS | `tdp-os-1` | **7400** | Tenant Data Provisioning OS |
| ERS control | `ers-control-1` | **9001** | ERS control plane |
| ERS data | `ers-data-1` | **9002** | ERS data plane (where eval results land) |
| TCS sidecar (platform) | `platform-tcs-1` | **7407** | TCS for platform |
| Step Functions Local | `localsf-1` | (8083 internal) | AWS Step Functions mock |
| Memcached | `memcachedtls-1` | (11211 internal) | TLS memcached |
| S3 blackhole | `s3-blackhole-1` | (8080 internal) | S3 sink |

**Important port collision warning:** `platform-slauth-1` is on host port **8081**. If you `bootRun` the convo-ai app with the default port 8081, **it will fail to bind**. Set `SERVER_PORT=8082` or similar before `bootRun`, OR use the standard `bootRun` task which the build configures correctly via Nebulae env vars.

---

## C. Re-using the running sandbox

### C1. Run a single integration test against the running sandbox

```bash
cd /Users/tchen7/MyProjects/atlassian_packages/conversational-ai-platform

./gradlew :convo-ai-test-integration:integrationTest \
  --tests 'YourSpecificTest' \
  -Pnebulae.enabled=false                          # ← skip Nebulae start/stop
```

The `-Pnebulae.enabled=false` flag tells the build:
- **DO NOT** invoke `atlas nebulae start -s integration-tests` (the sandbox is already there)
- **DO NOT** invoke `atlas nebulae stop` after the test
- Tests pull connection info from the env vars Nebulae has already exported into the shell session **OR** from the `.nebulae/integration-tests/container-resources-*.env` files (which the build module loads)

### C2. Run the smoke against the running sandbox

```bash
./gradlew :convo-ai-test-integration:startupTest -Pnebulae.enabled=false
```

Time: ~2-3 minutes (vs ~5-7 min cold).

### C3. Run all integration tests against the running sandbox (sharded)

```bash
./gradlew :convo-ai-test-integration:integrationTestShard1FlagsOn -Pnebulae.enabled=false
./gradlew :convo-ai-test-integration:integrationTestShard1FlagsOff -Pnebulae.enabled=false
# … shards 2, 3, 4
```

---

## D. Inspecting a live container while a test runs

### D1. Tail logs

The convo-ai-platform app does **not** run inside the sandbox by default — the sandbox provides the **dependencies**, you run the app via `./gradlew :convo-ai-test-integration:bootRun` or the test task. To tail dependency logs:

```bash
# WireMock (most useful — shows what stubs were hit)
docker logs -f convo-ai-integration-tests-3f2a39fb-wiremock-1

# LocalStack (useful for S3/SQS/DynamoDB issues)
docker logs -f convo-ai-integration-tests-3f2a39fb-localstack-1

# ERS data (useful for evaluation-result issues)
docker logs -f convo-ai-integration-tests-3f2a39fb-ers-data-1

# All compose logs at once (very chatty)
docker compose --project-name convo-ai-integration-tests-3f2a39fb logs -f
```

### D2. Inspect WireMock stubs

```bash
# List all stubs currently registered
curl -s http://localhost:7777/__admin/mappings | jq '.mappings[] | .request.urlPattern' | head -40

# List recently received requests (the "journal")
curl -s http://localhost:7777/__admin/requests | jq '.requests[].request.url' | head -40

# Reset the journal (between tests, if state is sticky)
curl -X DELETE http://localhost:7777/__admin/requests
```

### D3. Inspect LocalStack AWS state

```bash
# S3 buckets
aws --endpoint-url=http://localhost:56574 s3 ls

# SQS queues
aws --endpoint-url=http://localhost:56574 sqs list-queues

# DynamoDB tables
aws --endpoint-url=http://localhost:56574 dynamodb list-tables
```

(use `AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_REGION=us-east-1` for LocalStack)

### D4. Inspect Redis state

```bash
docker exec convo-ai-integration-tests-3f2a39fb-nebulae-convoai-cache-redisx-1 redis-cli
> KEYS *
> TTL <some-key>
```

---

## E. When to throw the sandbox away and start fresh

**Restart the sandbox** if any of these:
- Smoke test (`startupTest`) starts failing where it didn't before AND no source change explains it
- WireMock journal shows requests for stubs you've since removed
- LocalStack S3/SQS shows buckets/queues you've since deleted in code
- The sandbox is older than 2-3 days (drift from upstream image refreshes)
- A previous test deadlocked Tomcat threads (`startupTest` hangs on context refresh)

**Restart sequence:**

```bash
cd /Users/tchen7/MyProjects/atlassian_packages/conversational-ai-platform

# Clean stop (preserves volumes for fast restart)
atlas nebulae stop -s integration-tests

# OR, hard stop + remove volumes (slowest restart, most reliable)
docker compose --project-name convo-ai-integration-tests-3f2a39fb down -v

# Restart fresh (60-180 s)
atlas nebulae start -s integration-tests
```

**Or** the next `./gradlew :convo-ai-test-integration:integrationTest -Pnebulae.enabled=true` will trigger the start automatically if the sandbox is gone.

---

## F. Cleanup before logout / disk pressure

```bash
# Stop the sandbox (containers stop, volumes preserved)
atlas nebulae stop -s integration-tests

# Reclaim disk (volumes removed) — run on a planned cadence, NOT during active dev
docker compose --project-name convo-ai-integration-tests-3f2a39fb down -v
docker volume prune -f
```

---

## G. Multi-session caveat

The session ID (`3f2a39fb` for the current one) is generated per `atlas nebulae start` call. If you accidentally run `atlas nebulae start -s integration-tests` while another session is active, you may get a **second** sandbox with a different session id. Verify with:

```bash
docker ps --filter "name=convo-ai-integration-tests" --format "{{.Names}}" | awk -F- '{print $5}' | sort -u
# should print exactly one session id
```

If two are running, `atlas nebulae stop -s integration-tests` will stop **the most recently created** one. To stop a specific one:

```bash
docker compose --project-name convo-ai-integration-tests-<session-id> down
```

---

## H. v7 plan tie-ins

| v7 item | How the live sandbox accelerates |
|---|---|
| **All M-series instrumentation work (M1-M9)** | Iterate on `@WithSpan`/dispatcher metrics with restart-only-app, not full sandbox |
| **R-1A, R-1B (per-tool deadline, tool-error feedback)** | Iterate on `SimpleLoopWorkflowExecutorImpl.kt` with sub-30s test cycles |
| **N1 (Insights cache TTL)** | One-line change + single integration test → ~90s feedback |
| **T1 (bound channel)** | Iterate on `HttpRequestStreamingWriter.kt` + sandbox restart to catch heap pressure |
| **L1 (TCS Caffeine cache)** | Iterate on `AsyncTenantContextService.kt` with sandbox `tcs-sidecar-1` already serving |
| **Q1 (PageSearch L2 rerank)** | Iterate on `ConfluencePageSearchServiceImpl.kt`; observe WireMock journal for which PageSearch endpoint was hit |
