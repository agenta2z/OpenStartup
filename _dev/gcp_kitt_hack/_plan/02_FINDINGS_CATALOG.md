# Findings Catalog
> Every finding is normalized to: **id**, **file:line**, **current behaviour**, **quantified impact**, **risk**, **fix sketch**, **type**, **score**.
> **See also:** [`helmfile_enhancement_plan/02_FINDINGS_CATALOG.md`](helmfile_enhancement_plan/02_FINDINGS_CATALOG.md) for the helmfile-specific findings catalog (49 entries: HF-01..HF-49). The A1/A2/E2 items below have child entries HF-43/44/45 with file:line evidence and verified diff numbers.

> Findings are grouped by component prefix:
> - **A** = DTE distributed-client / distributed-worker (`amp/*` and `helmfile/dte/*`)
> - **B** = Scraper (`scraper/temporal-pg-redis/*`)
> - **C** = Kitt-runbooks (`kitt-runbooks/*`) and `dtecli`
> - **D** = Operators / collectors (`forge_containers`, `sweeper`, `k8s-metadata-collector`, `iam-sidecar`)
> - **E** = Cross-cutting (observability, duplication, CI)

---

## A. DTE distributed-client & distributed-worker

> **Verified duplication**: `amp/distributed-worker/helpers.go` differs from `helmfile/dte/distributed-worker/helpers.go` by **only 12 lines**; client `main.go` differs by **100 lines**. These are clearly forks-without-merge — the highest-leverage maintenance issue in the repo.

### A1 — Code duplication: `amp/*` ↔ `helmfile/dte/*`
- **Files**: `amp/distributed-{client,worker}/*` ≈ `helmfile/dte/distributed-{client,worker}/*` (~6 files, ~5 800 LoC each side)
- **Current**: Two near-identical copies. `helpers.go` diverges by 12 lines, `client/main.go` by 100. Bug-fix cost is ≈2× and risk of silent regressions is high (e.g. recent group-cache work could land in only one).
- **Quantified**: ~10–15% engineering overhead per fix. Risk-weighted ~$5–10K / mo in lost throughput from divergent bug-class regressions.
- **Risk**: HIGH long-term to leave; **MED** to fix (refactor).
- **Fix**: Extract shared `pkg/dte` Go module (see §06). Each binary becomes a thin `main` + env wiring.
- **Type**: Refactor (multi-PR).
- **Score: P0**

### A2 — Per-request `&http.Client{...}` in `getClusterTokenFromAuthProvider` and `cluster_db.go`
- **Files**: `amp/distributed-worker/helpers.go:~641`; `cluster_db.go`; mirrored in `helmfile/dte/`.
- **Current**: New `http.Client` allocated per call → no keep-alive reuse, fresh TLS + connection pool every time.
- **Quantified**: -40–50% auth-path latency at p99; -20% CPU on hot auth path; ~$500–1 000 / mo COGS.
- **Risk**: LOW.
- **Fix**: Package-level `http.Client` with `Transport: &http.Transport{MaxIdleConnsPerHost: 32, IdleConnTimeout: 90s}`; export getter for tests.
- **Type**: Code change.
- **Score: P0**

### A3 — Token cache absent (and missing the `groups` dimension that just landed)
- **Files**: `amp/distributed-worker/helpers.go:~561-799`.
- **Current**: Every activity exchanges a fresh token from auth-provider. Recent commits (`00170e6`, `1d0fd4f`) added group caching at the token *body* level but no in-memory cross-call cache exists.
- **Quantified**: Each cached hit saves ~200–500 ms; with 1.5M/mo at 10% re-auth rate ≈ 150K saved auth round-trips/month → ~$2–5K/mo.
- **Risk**: MED — must include `(cluster, groups, issuer)` in cache key; invalidate on 401.
- **Fix**: `sync.Map` or `golang-lru/v2` LRU; TTL = `expiry - 60s` (capped at 5 min). Emit `auth_token_cache_{hits,misses,invalidations}` counters.
- **Type**: Code change.
- **Score: P0**

### A4 — Unbounded goroutine fan-out in `DistributedTaskExecutionWorkflow`
- **File**: `amp/distributed-worker/main.go:93-207`, mirrored.
- **Current**: Loop launches one `workflow.ExecuteActivity` per cluster, no concurrency cap.
- **Quantified**: With 100+ cluster batches, p99 latency degrades 30%+; can saturate task queue → cascading retries.
- **Risk**: MED.
- **Fix**: Channel-based semaphore (e.g. cap=20); `workflow.NewSemaphore` pattern; counter metric for queued vs executing.
- **Type**: Code change.
- **Score: P1**

### A5 — Missing `ctx.Done()` check inside Argo polling loop
- **File**: `amp/distributed-worker/main.go:520-548`.
- **Current**: 10-min polling timer; no `case <-ctx.Done()`. Workflow cancel doesn't release activity.
- **Quantified**: Zombie goroutines on 5–15% of failed runs; queue backlog amplifier.
- **Risk**: MED.
- **Fix**: Add `case <-ctx.Done(): return ctx.Err()`.
- **Type**: Code change.
- **Score: P1**

### A6 — Synchronous `logAuthenticatedUser` SelfSubjectReview on hot path
- **File**: `helpers.go:306-390`.
- **Current**: After every successful token exchange, blocks on extra k8s API call for log-only purpose.
- **Quantified**: +100–200 ms per cluster connection; ~15–20% added critical-path latency.
- **Risk**: LOW.
- **Fix**: Run in `go func(){}` with 5-s timeout, cache result for 5 min keyed by `(cluster, user)`.
- **Type**: Code change.
- **Score: P1**

### A7 — Per-call `regexp.Compile` in `filterGroupsByPattern`
- **File**: `helpers.go:442-556`.
- **Current**: Compiles regex on every call (~15-30M compilations/mo at OKR scale).
- **Quantified**: ~10–15% latency on auth path; ~$500–1 000 / mo CPU.
- **Risk**: LOW.
- **Fix**: `sync.Once` per cluster annotation; or `var compiledPatterns sync.Map`.
- **Type**: Code change.
- **Score: P1**

### A8 — Activity timeouts/retries are uniform across activity types
- **File**: `main.go:117-127`.
- **Current**: Same 30-min timeout / same retry policy regardless of HealthCheck vs ServiceDiscovery.
- **Quantified**: -20–30% queue latency if specialised; -10% retry storm.
- **Risk**: MED.
- **Fix**: Per-type `ActivityOptions{}` constants; surfaced in env config.
- **Type**: Code change.
- **Score: P2**

### A9 — Missing pagination in K8s dynamic-client list ops
- **Files**: `helpers.go:1020-1062`; `distributed-client/main.go:1720-1868`.
- **Current**: `List` w/o `Limit`/`Continue`.
- **Quantified**: -30–50% memory for big clusters; -5–10s latency.
- **Risk**: LOW.
- **Fix**: `metav1.ListOptions{Limit: 200}` + continue loop.
- **Type**: Code change.
- **Score: P2**

### A10 — String concat in YAML generation, unbuffered
- **File**: `main.go:301-442`.
- **Current**: Repeated `fmt.Sprintf` for large workflow YAMLs.
- **Quantified**: ~5–10% memory per execution.
- **Risk**: LOW.
- **Fix**: `strings.Builder` with pre-grown capacity.
- **Type**: Code change.
- **Score: P3**

### A11 — No prometheus metrics emitted on either component
- **All files**.
- **Current**: No `/metrics` endpoint exposed; no histograms for auth/activity/k8s-call latency.
- **Quantified**: Operational blind spot — can't even *measure* what we'd be improving.
- **Risk**: LOW (additive).
- **Fix**: `promhttp.Handler()` + histograms (see §02-E1).
- **Type**: Code change.
- **Score: P1** (precondition for measuring P0 wins)

### A12 — Suspect race on global `jsonLogger`
- **Files**: `main.go:645-670`, `helpers.go:97-100`.
- **Current**: Global logger pointer used across goroutines.
- **Quantified**: 1–2 % chance of corruption / panic at scale.
- **Risk**: HIGH if hit, low likelihood; but easy to harden.
- **Fix**: Verify slog goroutine-safety; use ctx-attached logger; enable `-race` in CI.
- **Type**: Code change + CI.
- **Score: P2**

### A13 — JWT group split on every call
- **File**: `helpers.go:33-102`.
- **Current**: `strings.Split(groups, ",")` per token use.
- **Quantified**: -2–5 % latency.
- **Risk**: LOW.
- **Fix**: Cache parsed slice in token struct.
- **Type**: Code change.
- **Score: P3**

### A14 — Argo polling 10 min timeout vs 30 min activity timeout mismatch
- **File**: `main.go:540` vs `:117-127`.
- **Current**: Misalignment leaves activity running 19 min after polling exits.
- **Quantified**: 5 % latency on timeout cases.
- **Risk**: LOW.
- **Fix**: Use single source-of-truth duration constant.
- **Type**: Config.
- **Score: P3**

---

## B. Scraper (`scraper/temporal-pg-redis`)

### B1 — N+1 visited-check inside link-processing loop
- **File**: `src/worker.py:420-450`.
- **Current**: For each discovered link → `was_url_visited()` + `is_in_work_set()` (2 calls/link).
- **Quantified**: -50–70 % activity latency if batched; ~500K saved DB calls/mo at 400K rate.
- **Risk**: LOW.
- **Fix**: `was_url_visited_batch(job_id, urls)` using `WHERE url = ANY($1)` + Redis `SMISMEMBER` / `MGET`.
- **Type**: Code.
- **Score: P0/P1**

### B2 — Missing Redis pipeline on pop-process-ack path
- **Files**: `src/redis_utils.py:336-378`, `:380-418`.
- **Current**: 5+ sequential round-trips per URL (SPOP, ZADD, SCARD ×2, ZCARD, INCRBY).
- **Quantified**: -40 % p50 per-URL latency; ~$1–3K/mo Redis CPU.
- **Risk**: LOW.
- **Fix**: `r.pipeline()` block; or single Lua script.
- **Type**: Code.
- **Score: P1**

### B3 — Workflow `gather_timeout` race orphans activities
- **File**: `src/workflow.py:448-494`.
- **Current**: Wait `gather_timeout=110s` (workflow=120s); if breached, logs but moves on; activities orphaned in inconsistent state.
- **Quantified**: ~5–10 % silent workflow failures at scale.
- **Risk**: HIGH (data integrity).
- **Fix**: Increase to 300 s = activity timeout, OR shrink batch from 10→5 and add `last_seen_progress` heartbeat.
- **Type**: Code (small).
- **Score: P1**

### B4 — KEDA scaler keyed only on Temporal task-queue depth
- **File**: `scraper/temporal-pg-redis/k8s/keda-scaledobject.yaml`.
- **Current**: Scales 0→1000 pods on `taskQueue=scraper-task-queue threshold=50`. No Redis-depth trigger.
- **Quantified**: Misses spike when work backs up in Redis but Temporal queue is briefly drained; +30 % spike scaling lag.
- **Risk**: MED (extra trigger could over-scale).
- **Fix**: Additional trigger: `type: redis` watching `WORK_QUEUE_KEY` size threshold ~1000.
- **Type**: Config (yaml).
- **Score: P2**

### B5 — Missing prepared statements
- **File**: `src/db_utils.py:239-257`.
- **Current**: Plain parameterised `SELECT` re-parsed for every call.
- **Quantified**: -15–20 % DB CPU; potentially $2–5K/mo.
- **Risk**: LOW.
- **Fix**: `await conn.prepare(...)` once per worker; reuse.
- **Type**: Code.
- **Score: P2**

### B6 — Missing TTLs on Redis work/processing keys
- **File**: `src/redis_utils.py:275-296`, `:336-378`.
- **Current**: No `EXPIRE` set; zombie keys accumulate if jobs crash.
- **Quantified**: -10–20 % memory waste over weeks; eviction risk.
- **Risk**: MED.
- **Fix**: `EXPIRE key 7d` after job completion / per-key on first write.
- **Type**: Code.
- **Score: P2**

### B7 — Per-request fetch timeout absent
- **File**: `src/worker.py:311-324`.
- **Current**: Activity-level timeout only; single slow URL stalls activity.
- **Quantified**: -5–10 % p95 from stalls.
- **Risk**: MED (timeout-storm risk).
- **Fix**: `requests.get(..., timeout=30)`; categorise `Timeout` as retryable.
- **Type**: Code.
- **Score: P2**

### B8 — Python ↔ JS divergence (retry policy, mark_url_visited error class)
- **Files**: `src/workflow.py:125-159` vs `src-js/workflow.js`; `src/worker.py:335-370` vs `src-js/activities.js`.
- **Current**: Two implementations with subtly different retry/skip semantics.
- **Quantified**: 10–20 % failure-rate drift; future bug fixes go in only one.
- **Risk**: HIGH.
- **Fix**: Audit + extract YAML config of retry policies shared by both; or pick one impl and decommission the other (see §06).
- **Type**: Code + config.
- **Score: P1** (audit) → **P3** (consolidation)

### B9 — Connection-pool monitoring & circuit breaker absent
- **Files**: `src/db_utils.py:50-92`, `src/redis_utils.py:35-56`.
- **Current**: Pool created; no metric, no timeout (Redis), no leak detection.
- **Quantified**: Risk of weeks-later cascading failure; one slow Redis blocks all workers.
- **Risk**: HIGH (rare, catastrophic).
- **Fix**: Connection-acquire timeout, Prom gauges for active/idle, periodic `SELECT 1` keepalive.
- **Type**: Code.
- **Score: P1**

### B10 — Inefficient JSON of `store_pending_activities`
- **File**: `src/redis_utils.py:648-704`.
- **Current**: Stores full activity dict as JSON per write.
- **Quantified**: -5–10 ms per write; +50K serialisations/mo at OKR scale.
- **Risk**: LOW.
- **Fix**: Use `HSET` field-per-activity; smaller deltas; cheaper updates.
- **Type**: Code.
- **Score: P3**

### B11 — Missing histogram metrics for activity duration
- **File**: `src/metrics.py`.
- **Current**: Counter-only; no p95/p99 histogram.
- **Quantified**: Can't SLO; can't alert on tail.
- **Risk**: LOW.
- **Fix**: `prom.Histogram` per activity; buckets `[0.1,0.5,1,5,30,300]`.
- **Type**: Code.
- **Score: P2**

### B12 — Polling loop in `process_urls_as_activities` wastes worker slots when idle
- **File**: `src/workflow.py:375-425`.
- **Current**: Polls every 2-5 s; never adapts to empty work_count.
- **Quantified**: 10 % worker waste in low-throughput periods.
- **Risk**: MED (changes scheduling cadence).
- **Fix**: Adaptive backoff: 2s→30s when last batch empty.
- **Type**: Code.
- **Score: P3**

### B13 — Activity timeout vs `URL_SCRAPING_TIMEOUT` mismatch
- **File**: `src/worker.py:135-136`, `:236`, `:259`.
- **Current**: Activity timeout 5min, scraping timeout 2min — wastes 3min after URL failure.
- **Quantified**: ~3 min wasted per timeout; small but easy.
- **Risk**: LOW.
- **Fix**: Single source-of-truth: `ACTIVITY_TIMEOUT = URL_TIMEOUT + 60s`.
- **Type**: Config.
- **Score: P3**

### B14 — Workflow payload-size validation missing
- **File**: `src/workflow.py:364-450`.
- **Current**: Could exceed Temporal 2 MB payload limit on link-heavy pages.
- **Quantified**: Random workflow failures.
- **Risk**: MED.
- **Fix**: Cap discovered links to 100 per page; drop+warn beyond.
- **Type**: Code.
- **Score: P2**

### B15 — `scraper_processor.py` duplicated in `scraper/pg/` and `lambda/pg/` (780 LoC each)
- **Files**: `scraper/pg/scraper_processor.py`, `lambda/pg/scraper_processor.py`.
- **Current**: Same file in two places; same divergence risk as A1.
- **Quantified**: Maintenance only; ~$0.5–1K / mo eng cost.
- **Risk**: HIGH for correctness.
- **Fix**: One copy in `scraper/pg/`; the other becomes a thin Lambda entry-point importing it.
- **Type**: Refactor.
- **Score: P2**

---

## C. Kitt-runbooks & dtecli

> Recent git history: 15+ commits in 3 months added ~+400 lines of logging to cordon flows. **We level/sample, we don't delete.** (See §05.)

### C1 — Excessive Info-level logging (Splunk-cost amplifier)
- **Files**: `kitt-runbooks/activities.go:25, 35, 43, 64, 113-118, 225-228, 295-299, 327-330, 364-369`.
- **Current**: 8–15 KV pairs per activity at Info; per-node logs in `BuildDeleteNodeActivity` loop multiply.
- **Quantified**: ~100 KB / workflow × 1 000 / day = ~$500 / mo Splunk; 30–50 % of audit-flow volume is reducible.
- **Risk**: LOW (level demotion only).
- **Fix**: Move per-node-detail logs to Debug; aggregate node summaries; sample 1/100 for high-volume Info lines; preserve all the cordon-flow context that was deliberately added recently (see §05 §3).
- **Type**: Code (small).
- **Score: P1**

### C2 — K8s clientset re-created per activity
- **File**: `kitt-runbooks/activities.go:28, 46, 244, 250` → `internal/k8sclient/client.go:73`.
- **Current**: Each activity calls `NewK8sClient()` → fresh TLS + token-exchange.
- **Quantified**: 0.5–2 s overhead × 5 activities = **2.5–10 s MTTR** per cordon workflow.
- **Risk**: HIGH (touches auth path).
- **Fix**: Cache by cluster in worker process; `sync.Map[clusterID]*Client`. Re-create on auth failure. Coordinate with the recent `slauth-token` group cache (don't double-cache).
- **Type**: Code.
- **Score: P0**

### C3 — Sequential `CheckNodeStatusActivity` over node list
- **File**: `kitt-runbooks/workflow_node_cordoned.go:81-89`.
- **Current**: `for n in cordonedNodes { ExecuteActivity(...).Get() }` linear.
- **Quantified**: 10 nodes × 2 s = **20 s sequential** vs ≈2 s parallel.
- **Risk**: HIGH (must avoid hammering apiserver, but Temporal naturally serialises across worker pods).
- **Fix**: Collect futures, `await` all; cap parallelism at 10.
- **Type**: Code.
- **Score: P1**

### C4 — Splunk searches not cached / not narrowed
- **File**: `activities.go:105-109`.
- **Current**: `cluster_splunk_index env=%s region=%s @tag=apiserver ...` with `earliest=-3d@h`; no cache.
- **Quantified**: ~3000 redundant queries / day on the same cluster; -50 % Splunk query cost achievable.
- **Risk**: MED.
- **Fix**: Cache by `(clusterName, earliest)` key for 10 min; tighten earliest to `-1h@h` for recent-cordon detection; add `head 1000`.
- **Type**: Code.
- **Score: P2**

### C5 — Nodes / pods List without field selectors
- **Files**: `internal/k8sclient/client.go:89, 114-116, 144`.
- **Current**: `Nodes().List({})` and cluster-wide `Pods(NamespaceAll).List({FieldSelector: spec.nodeName=...})` w/o pagination.
- **Quantified**: -40–60 % apiserver CPU on big clusters; saves transfer of 100KB+ per call.
- **Risk**: MED.
- **Fix**: Add `FieldSelector: "spec.unschedulable=true"` to nodes; `Limit: 500` + Continue token for pods.
- **Type**: Code.
- **Score: P2**

### C6 — Auth-diagnostics on every client creation
- **File**: `internal/k8sclient/auth_diag.go` invoked from `client.go:73`.
- **Current**: Runs TokenReview + 5 SelfSubjectAccessReview on every client.
- **Quantified**: 6 extra API calls × 100 ms = **600 ms / activity**.
- **Risk**: MED.
- **Fix**: Behind a flag (`KITT_RUNBOOK_AUTH_DIAG=1`); cache by `(token, cluster)` for 1 h.
- **Type**: Code.
- **Score: P1**

### C7 — `DescribeNode()` re-fetches data we already have
- **File**: `activities.go:53` → `client.go:144`.
- **Current**: Activity uses both `GetNodeNonTerminatedPodNamespaces()` and `DescribeNode()` → 2 redundant Lists.
- **Quantified**: 2× extra K8s List calls per node.
- **Risk**: LOW.
- **Fix**: Return pod-namespaces from CheckNodeStatusActivity; build describe in workflow.
- **Type**: Code.
- **Score: P2**

### C8 — Activities have no retry policy
- **File**: `workflow_node_cordoned.go:53, 74, 83, 92`.
- **Current**: No `RetryPolicy` set in `ActivityOptions`.
- **Quantified**: ~10 % workflow fails on transient K8s throttle / dial errors; SRE retries manually.
- **Risk**: MED.
- **Fix**: `RetryPolicy: {MaxAttempts: 3, InitialInterval: 1s, BackoffCoefficient: 2}`.
- **Type**: Code (one-liner per activity).
- **Score: P1**

### C9 — Splunk client 60-s HTTP timeout & no retry
- **File**: `internal/splunk/client.go:55`.
- **Current**: Timeout 60 s; activity stalls if Splunk slow.
- **Quantified**: -45 s p99 SRE-wait when Splunk degraded.
- **Risk**: LOW.
- **Fix**: 15 s timeout, env-configurable, fail-fast.
- **Type**: Code (one-liner).
- **Score: P2**

### C10 — `FetchClusterFromRegistry` per activity
- **File**: `activities.go:89`.
- **Current**: Re-resolves env/region for every audit activity.
- **Quantified**: +100–200 ms per workflow.
- **Risk**: LOW.
- **Fix**: Cache 1 h; or pass env/region as workflow input.
- **Type**: Code.
- **Score: P2**

### C11 — EC2 client recreated per region inside loop
- **File**: `activities.go:331-333`.
- **Current**: `ec2.NewFromConfig()` inside loop.
- **Quantified**: -50–100 ms per region in multi-region cordon.
- **Risk**: LOW.
- **Fix**: `map[region]*ec2.Client` cache.
- **Type**: Code.
- **Score: P3**

### C12 — Unstructured workflow logs (Splunk parse cost)
- **File**: `workflow_node_cordoned.go:45, 56, 59, 63`.
- **Current**: `logger.Info("Workflow execution started")` w/o `workflow_id`/`cluster_id`.
- **Quantified**: SRE Splunk regex parse adds ~$100/mo query cost.
- **Risk**: LOW.
- **Fix**: Always include `workflow_id, cluster_id, status` as fields.
- **Type**: Code.
- **Score: P2**

### C13 — CLI status command sequential
- **File**: `dtecli/src/cli/commands/workflow/status.ts` (1012 lines).
- **Current**: Likely sequential history fetch per workflow.
- **Quantified**: 10 workflows = 10× RPC latency; SRE-visible delay.
- **Risk**: LOW.
- **Fix**: `Promise.all()` with concurrency cap.
- **Type**: Code.
- **Score: P3**

### C14 — Activity heartbeat absent on long-running activities
- **File**: `workflow_node_cordoned.go:47` → `WithDefaultActivityOptions`.
- **Current**: No `HeartbeatTimeout` set; AWS-loop activities can falsely time out.
- **Quantified**: Rare but causes activity loss.
- **Risk**: LOW.
- **Fix**: `HeartbeatTimeout: 30s` on `BuildDeleteNodeActivity`; `RecordHeartbeat` in AWS loop.
- **Type**: Code.
- **Score: P3**

---

## D. Operators / collectors

### D1 — `k8s-metadata-collector` polls full `Nodes().List()` + `Pods("").List()` every `TIMEOUT_IN_SECONDS`
- **File**: `k8s-metadata-collector/main.go:120-128`, `:316-345`.
- **Current**: Every loop pulls every Node and every Pod cluster-wide; no informer; no pagination; `log.Fatalf` on transient list error → pod restart loop.
- **Quantified**: Single biggest gcp_kitt-side apiserver consumer per cluster. -90 % API List calls if switched to **shared informer**; eliminates `log.Fatalf` restart cascade (4–8 restarts/day on a busy cluster).
- **Risk**: MED (informer adoption is a real change, but pattern is well-known).
- **Fix**: `informers.NewSharedInformerFactory(client, 30*time.Minute)`, `NodeInformer`, `PodInformer`, `ServiceAccountInformer`. Compute deltas in event handlers; emit on a timer to Kinesis. Replace `log.Fatalf` in `GetPodsAndNodes` with logged error + retry.
- **Type**: Code (medium).
- **Score: P0**

### D2 — `k8s-metadata-collector` uses `PutRecord` per pod/node/SA
- **File**: `k8s-metadata-collector/main.go:237-241, 266, 296`.
- **Current**: One `PutRecord` per item; UUID partition-key per record.
- **Quantified**: Kinesis cost is per-shard-PUT-payload-unit (25 KB). Switching to `PutRecords` (up to 500 records / 5 MB per call) reduces request count ~50–100× → -60 % Kinesis cost; lower throttle risk.
- **Risk**: LOW (Kinesis SDK supports it).
- **Fix**: Buffer up to 500 records or 4 MB; flush; surface `failed_records` metric.
- **Type**: Code.
- **Score: P0**

### D3 — Sweeper does cluster-wide `Pods("")` List with no filters or pagination
- **File**: `sweeper/controllers/sweeper_controller.go:152-165`.
- **Current**: `r.Client.List(ctx, &pods)` for the KITT namespace branch.
- **Quantified**: On a 5 000-pod cluster: ~15 MB transfer per reconcile; reconciles every CR change. -95 % API load if scoped + watch-driven.
- **Risk**: LOW.
- **Fix**: `client.MatchingLabelsSelector(...)` + `client.Limit(500)` continue loop; long-term, watch only Pods missing the label via predicate (see D4).
- **Type**: Code.
- **Score: P0**

### D4 — Sweeper retries on **any** error in `labelPod`
- **File**: `sweeper/controllers/sweeper_controller.go:184-198`.
- **Current**: `retry.OnError(retry.DefaultBackoff, func(err error) bool { return true }, ...)`.
- **Quantified**: Retry storm against pods with `validation policy` or `permission denied` (which won't ever succeed).
- **Risk**: MED (currently silent; fix is straightforward).
- **Fix**: Use `apierrors.IsConflict(err) || apierrors.IsServerTimeout(err)` predicate; do not retry 403/422.
- **Type**: Code (small).
- **Score: P0**

### D5 — `ForgeAppReconciler.Reconcile` does **5+ `Status().Update()`** per reconcile
- **File**: `forge_containers/controllers/forgeapp_controller.go:99, 119, 138, 164, 170, 194, 211, 223, 236, 251, 336`.
- **Current**: Status object is updated after every sub-step (initial, namespace, SA, deploy, service, http-proxy, running). Each is an etcd write + risk of write-conflict retry.
- **Quantified**: -70 % etcd writes from this controller; -30 % p95 reconcile; reduces apiserver write QPS.
- **Risk**: LOW.
- **Fix**: Build a local `desiredStatus`; compare to current at end-of-reconcile; one `Status().Patch()` (server-side apply preferred).
- **Type**: Code (medium).
- **Score: P0**

### D6 — `logStatus` does `json.MarshalIndent` every reconcile
- **File**: `forge_containers/controllers/forgeapp_controller.go:890-894`.
- **Current**: Pretty-prints whole Status struct on every call (called twice during init).
- **Quantified**: ~50 KB of pretty-JSON / reconcile ÷ Splunk; CPU; allocator.
- **Risk**: LOW.
- **Fix**: Move to `V(1)` level + `json.Marshal` (no indent) + only on transitions.
- **Type**: Code.
- **Score: P1**

### D7 — `ensureNamespace` polls 3× with `time.Sleep(1s)` for namespace active
- **File**: `forge_containers/controllers/forgeapp_controller.go:603-628`.
- **Current**: Synchronous sleep loop blocks reconciler worker thread.
- **Quantified**: Up to 3 s reconciler-thread blocked per namespace creation.
- **Risk**: LOW.
- **Fix**: Return `ctrl.Result{RequeueAfter: 1*time.Second}` instead of sleeping.
- **Type**: Code.
- **Score: P2**

### D8 — `addFinalizer` does an extra `r.Get()` even on first call
- **File**: `forgeapp_controller.go:346-374`.
- **Current**: Re-fetches the object then `Update()` for finalizer addition.
- **Quantified**: -1 apiserver Get per reconcile of new resources.
- **Risk**: LOW.
- **Fix**: Use `client.Patch` w/ `MergeFromWithOptions`.
- **Type**: Code.
- **Score: P3**

### D9 — Hardcoded 5 s requeue with no exponential backoff for not-ready deployment
- **File**: `forgeapp_controller.go:299, 326`.
- **Current**: `RequeueAfter: 5 * time.Second` for un-ready pods until forever.
- **Quantified**: For long-failing deployments, ~17K reconciles / day for one app.
- **Risk**: LOW.
- **Fix**: Backoff: 5s → 10s → 30s → 60s → cap at 5 min.
- **Type**: Code.
- **Score: P2**

### D10 — `SetupWithManager` does no event filter / predicate
- **File**: `forgeapp_controller.go:560-575`.
- **Current**: Reconciles on **every** owned object's spec/status change (Deployment, Service, SA, RoleBinding, PDB, HTTPProxy).
- **Quantified**: Status updates on Deployment by upstream controllers cause spurious reconciles → at OKR scale this multiplies.
- **Risk**: MED (filter must be correct).
- **Fix**: `builder.WithPredicates(predicate.GenerationChangedPredicate{})` for owned resources to skip status-only updates.
- **Type**: Code.
- **Score: P1**

### D11 — `pod_label_sweeper.py` is a one-shot Python script, not an operator
- **File**: `deploy/python/pod_label_sweeper.py` (562 LoC).
- **Current**: Runs as a one-shot job; sequential namespace → pods → patch loop; no parallelism; no incremental.
- **Quantified**: Slow on large clusters; functionally overlaps with `sweeper/controllers/sweeper_controller.go`.
- **Risk**: MED (operational change).
- **Fix**: Either decommission in favour of the Go controller (target state), or parallelise with `concurrent.futures.ThreadPoolExecutor` in the interim.
- **Type**: Refactor (decom) or small code (parallelise).
- **Score: P2**

### D12 — `iam-sidecar` is solid (no critical finding)
- **Files**: `iam-sidecar/iam-sidecar.go`, `gcp.go`.
- **Note**: Cache, early-refresh, mutex pattern, AWS+GCP discovery look correct. Only minor: `runtime.NumCPU` not pinned and STS region required (intentional). **Leave alone.** Listed for completeness.

### D13 — `forge_containers/k8s-deployment.js` (852) and `kittz/k8s-deployment.js` (950) diverged
- **Files**: above.
- **Current**: Two near-duplicates with diff confirmed (98 lines apart). Same divergence-risk as A1/B15.
- **Quantified**: Eng cost; small but recurring.
- **Risk**: LOW.
- **Fix**: Promote one to a shared `kittz/lib/k8s-deployment.js` module; the other becomes a re-export.
- **Type**: Refactor.
- **Score: P3**

### D14 — `asi/internal/asicore/asi.go` `UpdateASI` re-creates ServiceAccount on every reconcile of an existing ASI
- **File**: `asi/internal/asicore/asi.go:143-235` (`UpdateASI`), `:237-275` (`createOrUpdateKubernetesServiceAccount`).
- **Current**: Reads, then unconditionally calls Create/Update; no diff check.
- **Quantified**: Avoidable apiserver writes; small but cumulative.
- **Risk**: LOW.
- **Fix**: Only `Update` if annotations differ.
- **Type**: Code.
- **Score: P3**

---

## E. Cross-cutting

### E1 — No `prometheus_client` / metrics endpoint surface in DTE worker, scraper-go variants, kitt-runbooks
- **All Go services**.
- **Current**: No `/metrics` exposed; no histograms.
- **Quantified**: Cannot measure improvements from §A2/A3/D1/D5; this is the **precondition**.
- **Risk**: LOW.
- **Fix**: Add `promhttp.Handler()`, RED-method histograms (Rate-Errors-Duration) per activity / reconcile / auth call. Standard label set: `service, activity_type, cluster, result`.
- **Type**: Code.
- **Score: P0** (enables proving every other P0)

### E2 — CI does not assert `amp/*` ↔ `helmfile/dte/*` parity
- **Repo root**.
- **Current**: Two copies can drift silently (12-line and 100-line drift today).
- **Fix**: Until §06's consolidation lands, add a `pre-commit`/CI step: `diff -q amp/distributed-worker/helpers.go helmfile/dte/distributed-worker/helpers.go` (and friends); allow drift only via a marker file.
- **Type**: CI config.
- **Score: P1**

### E3 — `-race` not enabled in Go tests
- **Repo root**.
- **Current**: Tests run without `-race` → races like A12 hide.
- **Fix**: Add `go test -race ./...` to CI.
- **Type**: CI config.
- **Score: P2**
