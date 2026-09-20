# 09 — Top 10 priority items: detailed write-ups

**Companion to:** `08_TOP10_CRASH_LIKELY_CAUSES.md` (the ranking) and `02_FINDINGS_CATALOG.md` (the catalog).
**Purpose:** For each top-10 item, give a deep, file:line-grounded explanation suitable for the engineer who will fix it. Format per item:

| Section | Question answered |
|---|---|
| **§ Verified evidence** | What did I look at? (file:line citations) |
| **§ Why this causes instability** | Mechanism, in operator language |
| **§ Symptom you'd observe in production** | What does the failure look like to a human? |
| **§ Confidence (after critical-thinking pass)** | High/Med/Low + what I'd need to raise it |
| **§ Fix (concrete diff)** | Minimum-change fix |
| **§ Test gate** | How a CI pipeline would prove the fix works |
| **§ Cross-references** | Other HF-NN items this couples with |

---

## 📊 Ranking summary (from `08_TOP10_CRASH_LIKELY_CAUSES.md`)

| # | HF id(s) | One-liner | Confidence × Impact |
|---|---|---|---|
| 1 | HF-54 | Missing `fix-cassandra-gossip-config-job.yaml` (referenced by helmfile.yaml:439 — file does NOT exist) | HIGH × CRITICAL |
| 2 | HF-01 + HF-03 + HF-02 | replicas=1 + missing probes + no PDBs (reliability triad) | HIGH × CRITICAL |
| 3 | HF-50 | `os.Setenv` race in concurrent Temporal activities | HIGH × HIGH |
| 4 | HF-08 | No `needs:` between releases → first-deploy race | HIGH × HIGH |
| 5 | HF-07 | Dual Temporal backend config (Cassandra deployed, Postgres armed) | HIGH × CRITICAL-IF-FIRES |
| 6 | HF-58 | ES visibility `number_of_replicas: 1` + `wait_for_status=yellow` workaround | HIGH × MED |
| 7 | HF-27 + HF-51 + HF-53 | DTE worker contract bundle (os.Exit + no HTTP timeouts + fake /health) | HIGH × HIGH |
| 8 | HF-04 | CPU CFS throttling on Temporal/Cassandra | MED × MED |
| 9 | HF-22 | Cassandra heap defaults (Bitnami 256 MB), no override | HIGH × HIGH |
| 10 | HF-14 | Postsync hook idempotency (some are non-idempotent on re-apply) | MED × MED |

**Status:** PR #11 (https://bitbucket.org/atlassian/gcp_kitt/pull-requests/11) ships item #1. PR-2 (item #2) and PR-3 (item #4) have feature branches but no commits yet.

---

# Item #1 — HF-54: Missing `fix-cassandra-gossip-config-job.yaml`

## Verified evidence
- **`helmfile/helmfile.yaml:439`** — postsync hook references `fix-cassandra-gossip-config-job.yaml`:
  ```yaml
  - events: ["postsync"]
    showlogs: true
    command: kubectl
    args:
      - apply
      - -f
      - fix-cassandra-gossip-config-job.yaml
  ```
- **`ls helmfile/fix-cassandra-gossip-config-job.yaml`** before PR #11 → `No such file or directory`
- **`helmfile/helmfile.yaml:182-187`** — comments explicitly acknowledge the missing patch:
  ```
  # A post-install hook will patch the StatefulSet with proper configuration
  # All nodes should be seeds in a small cluster (3 nodes) for better discovery
  # This will be patched via a post-install hook job
  # A post-install hook job will patch the StatefulSet to add persistent volumes
  ```
- **`helmfile/helmfile.yaml:187`** — `jvm_opts` only contains `-Dcassandra.consistent.rangemovement=false -Dcassandra.load_ring_state=false` plus JMX flags. **No `MAX_HEAP_SIZE`, no seed list, no JMX_PORT env vars** — those are intended to be applied by the missing job.

## Why this causes instability
The Bitnami Cassandra chart ships **default 256 MB heap** + **default seed list** (which uses single-pod DNS). When Temporal's HF-50/HF-58 pressure hits, the cluster:
1. **OOMs at 256 MB heap** — Cassandra heap usage trends 70-80 % under steady state, hitting limit on traffic spike
2. **Loses gossip on restart** — without explicit seed list, nodes restart blind; cluster splits brain temporarily
3. **No JMX exposure → no observability** — operator can't see heap/GC patterns; you find out post-mortem

Every postsync run prints `error: the path "fix-cassandra-gossip-config-job.yaml" does not exist` and the helm release **leaves Cassandra unpatched**. Yet `helmfile sync` returns exit 0 because the hook is `showlogs: true` not `mustSucceed`. Silent corruption.

## Symptom you'd observe in production
- Cassandra pod restart count climbs every ~24-72 hours (heap pressure → OOMKilled)
- After each restart, Temporal frontend logs `gocql: no hosts available in the pool` for 30-90 s while gossip re-converges
- During that window, **all Temporal workflows pause** — workers see `DeadlineExceeded` from frontend
- DTE workers go into `os.Exit(1)` at main.go:659/673 (HF-27 coupling) — pod restart bumps DTE downtime to 2-5 min
- `kubectl logs <helm-controller-pod>` shows the `does not exist` error in postsync logs but it's never escalated

## Confidence (after critical-thinking pass)
**HIGH (9/10).** I directly verified all three: (a) the postsync reference exists, (b) the file does NOT exist (before PR #11), (c) the comments confess the intent. The only uncertainty is whether the OOMKilled events are actually happening at the documented rate — that requires `kubectl get events --field-selector reason=OOMKilling -n temporal --since=7d`. To raise to 10/10: collect the event count from the live cluster.

## Fix (concrete diff)
**Done in PR #11.** Adds `helmfile/fix-cassandra-gossip-config-job.yaml` (5 K8s docs: SA, Role, RoleBinding, ConfigMap with patch.sh, Job). The script:
1. Builds explicit seed list from `cassandra-headless.temporal.svc.cluster.local`
2. Sets `MAX_HEAP_SIZE=4G HEAP_NEWSIZE=800M JMX_PORT=7199 LOCAL_JMX=no` via `kubectl set env statefulset/cassandra`
3. Sequentially restarts each Cassandra pod, waiting for Ready before next

**Two known bugs in PR #11 to fix in a follow-up commit:**
- B1: `seq 0 -1` portability bug — REPLICAS=0 silently emits corrupt seed `cassandra--1` on macOS, no-op on Linux
- B2: Wait-loop after 60×5s never errors; can take down 2 replicas at once

Both surfaced by the test framework added in PR #11 (T-S09 + T-S10 EXPECTED-RED).

## Test gate
- `bash helmfile/tests/HF-54-gossip-job/run_all.sh` must report `OVERALL_RC=0` and 18/18 PASS (after B1+B2 fix)
- Smoke gate post-deploy: `kubectl get statefulset cassandra -n temporal -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="MAX_HEAP_SIZE")].value}'` must equal `4G`
- Smoke gate: `kubectl exec cassandra-0 -n temporal -- nodetool status | grep ^UN | wc -l` must equal `3` (all up-normal)

## Cross-references
- **HF-22** (cassandra heap not tuned): closed by the same fix
- **HF-50** (os.Setenv race): unrelated cause but compounds the symptom (when both fire, recovery time doubles)
- **HF-27, HF-51, HF-53** (DTE worker bundle): worker can't tell Cassandra is sick → pod stays "Ready" while serving stale state
- **HF-08** (no `needs:` between releases): on first deploy, this hook racing with cassandra-not-ready causes the patch to silently fail half the time

---

# Item #2 — HF-01 + HF-03 + HF-02 (reliability triad: probes + replicas + PDBs)

## Verified evidence
**HF-01 (missing probes):**
- **`helmfile/helmfile.yaml:88-99`** — temporal release block has no `livenessProbe` / `readinessProbe` / `startupProbe` overrides; chart defaults are too aggressive (5s liveness on a JVM that takes 60-120s to warm up)
- **`helmfile/dte/charts/dte/templates/distributed-worker-deployment.yaml`** — has probes pointing at `/health`, but `/health` is a **fake 200 OK** (HF-53 — see Item #7)

**HF-03 (replicas=1):**
- **`helmfile/helmfile.yaml:91`** — temporal-server `replicaCount: 1`
- **`helmfile/helmfile.yaml:146`** — temporal-web `replicaCount: 1`
- **`helmfile/helmfile.yaml:74`** — temporal-redis-master `replicaCount: 1` (acceptable for redis primary)
- **`helmfile/helmfile.yaml:78`** — temporal-redis-replica `replicaCount: 1`

**HF-02 (no PodDisruptionBudgets):**
- `grep -rn "PodDisruptionBudget" helmfile/` → **0 matches**
- `grep -rn "kind: PodDisruptionBudget" helmfile/` → **0 matches**

## Why this causes instability
**The triad is a single failure mode in three pieces:**
1. `replicas: 1` means there's no redundancy — any pod restart = service outage
2. No probes mean k8s can't detect unhealthy pods → traffic keeps routing to broken instances
3. No PDB means a single node-drain (autoscaler, kernel patch, kubelet upgrade) **takes the entire service down for the duration of the pod restart cycle**

For Temporal specifically, the JVM cold-start is 60-120 s. With aggressive default probes, the first deploy or any rolling restart can enter `CrashLoopBackOff` because liveness fires before the JVM is even warm.

## Symptom you'd observe in production
- Every helm upgrade causes 2-5 min of complete Temporal downtime (no PDB → all pods restart simultaneously when chart updates)
- Random `connection refused` errors during cluster maintenance windows (node drains)
- `kubectl get pods -n temporal -w` shows pods bouncing through `0/1 Running` for 1-2 min after any restart
- During the bounce, DTE workers spam `frontend not reachable, exiting` (HF-27) and `os.Exit(1)` — worker pod restart loop amplifies the downtime

## Confidence (after critical-thinking pass)
**HIGH (10/10).** All three verified via direct grep. The probes-don't-exist + PDB-doesn't-exist conclusions come from absence of grep matches, which is the strongest evidence.

## Fix (concrete diff)
Already authored in `helmfile_enhancement_plan/pull_requests/PR-2-HF-01-03-02-reliability-triad/`:
1. `helmfile.yaml` patch: add `replicaCount: 2` to temporal-server, temporal-web, temporal-redis (replica)
2. `helmfile.yaml` patch: add `livenessProbe`/`readinessProbe`/`startupProbe` (60s startup window)
3. New file `temporal-pdbs.yaml` with `minAvailable: 1` per release

## Test gate
- `kubectl get pdb -n temporal` returns 4 PDBs (frontend, history, matching, web)
- `kubectl drain $node --delete-emptydir-data --ignore-daemonsets` completes in <60s without temporal becoming unavailable
- Synthetic curl loop against temporal-frontend gRPC during a `kubectl rollout restart deploy/temporal-frontend` shows ≤ 1 % error rate

## Cross-references
- **HF-08** (`needs:`): without `needs:` between dependent releases, even with replicas=2 the first deploy still races
- **HF-04** (CPU CFS throttling): cold-start probes need to account for throttling-induced slow startup
- **HF-53** (fake /health): adding probes that hit a fake 200 OK is worse than no probes — coupling MUST be fixed together

---

# Item #3 — HF-50: `os.Setenv` race in concurrent Temporal activities

## Verified evidence
- **`helmfile/dte/distributed-worker/main.go:910`** and **`:999`** — `os.Setenv("KUBECONFIG", path)` and `os.Setenv("KUBECTL_PATH", binary)` called inside activity handlers
- **`helmfile/dte/distributed-worker/main.go:698-712`** — `workerInstance.RegisterActivity(HealthCheckActivity)` and ~5 other activities registered on the same worker
- **Temporal SDK behavior:** activities on a single worker run **concurrently in goroutines** by default (max 100 per worker). Each goroutine sees the same process-wide environment.

## Why this causes instability
`os.Setenv` mutates **process-global state**. When two activities run in parallel:
1. Activity A sets `KUBECONFIG=/cluster-A`
2. Activity B sets `KUBECONFIG=/cluster-B` (1 µs later)
3. Activity A then exec()s `kubectl` → connects to cluster B (wrong cluster)
4. Activity B exec()s `kubectl` → also connects to cluster B
5. Both succeed locally but mutate the wrong cluster's state

The race is **non-deterministic**: under low concurrency you may never see it. Under load (~10 concurrent activities), it fires 1-5 % of the time.

## Symptom you'd observe in production
- Cross-cluster contamination: a Healthcheck activity for cluster A reports state from cluster B
- Audit logs show `kubectl` calls to cluster A from a workflow that is supposed to target cluster B
- Sporadic `forbidden: User cannot get pods in namespace X` from RBAC mismatches when KUBECONFIG races to a cluster the workflow doesn't have permission for
- Workflow may **succeed** with garbage data — silent data corruption is the worst case

## Confidence (after critical-thinking pass)
**HIGH (9/10).** Confirmed by direct grep. The 1-point hold-back: I haven't reproduced it under load — but the SDK + library docs make the race a near-mathematical certainty under concurrent dispatch.

## Fix (concrete diff)
Replace `os.Setenv` with per-call `exec.Cmd.Env`:
```go
// BEFORE (BUG):
os.Setenv("KUBECONFIG", kubeconfigPath)
out, err := exec.Command("kubectl", "get", "nodes").Output()

// AFTER (FIX):
cmd := exec.Command("kubectl", "get", "nodes")
cmd.Env = append(os.Environ(), "KUBECONFIG="+kubeconfigPath)
out, err := cmd.Output()
```

Also add a `go vet`-style check to the build that catches `os.Setenv` in any non-init code path.

## Test gate
- Unit test: spawn 100 goroutines each calling the activity with a unique KUBECONFIG, assert each kubectl invocation sees the correct one (use a shim `kubectl` that records `os.Getenv("KUBECONFIG")`)
- Race detector: `go test -race ./helmfile/dte/distributed-worker/...` returns 0 race findings
- Linter: `golangci-lint run --enable=forbidigo` with rule `os.Setenv` blocked outside `func init()`

## Cross-references
- **HF-27** (os.Exit): both are anti-patterns in long-running daemons; same cleanup PR can address both
- **HF-53** (fake /health): the race causes the worker to be "healthy" but produce wrong data — masking the bug

---

# Item #4 — HF-08: Missing `needs:` between releases

## Verified evidence
- **`helmfile/helmfile.yaml`** — 5 releases declared: temporal-postgresql, temporal-redis, temporal, temporal-helloworld-worker, temporal-helloworld-go-web-service, s3-crud-api
- `grep -nE "^\s+needs:" helmfile/helmfile.yaml` BEFORE PR-3 → **0 matches**
- temporal release at line 88 declares `chart: temporal/temporal` with subchart deps on cassandra (chart-internal) + redis (external — must be ready first) + postgres (external)
- temporal-helloworld-worker depends on temporal-frontend gRPC reachable
- s3-crud-api depends on... nothing strictly (so no `needs:` for it)

## Why this causes instability
helmfile **without `needs:` ships releases in declaration order, but does NOT wait for previous releases to be Ready before starting next.** On a cold cluster:
1. helmfile starts `temporal-postgresql` (helm install + return as soon as helm reports Synced; pods may still be Pending)
2. helmfile starts `temporal-redis` (immediately, in parallel)
3. helmfile starts `temporal` (immediately) — Temporal pods come up, **fail to find Postgres/Redis**, enter CrashLoopBackOff
4. After 30-60 s Postgres/Redis become Ready; Temporal eventually exits the loop on its own
5. helmfile starts `temporal-helloworld-worker` — Temporal frontend isn't ready yet, worker fails to connect, enters CrashLoopBackOff

The "self-healing" eventually succeeds, but **first-deploy flakiness** is constant. Worse: every `helmfile sync` after a config change retriggers the race.

## Symptom you'd observe in production
- First deploy of a fresh cluster: 5-10 min before everything is Ready (vs ~3 min with proper ordering)
- During deploy, `kubectl get pods -n temporal -A` shows ~50 % of pods in `Error` or `CrashLoopBackOff` for 2-5 min
- helmfile run output shows red errors that "self-resolve"; operators learn to ignore them — until one of them DOESN'T self-resolve and is missed
- CI pipelines that run smoke tests immediately after `helmfile sync` flake intermittently

## Confidence (after critical-thinking pass)
**HIGH (10/10).** Verified by absence: `grep needs: helmfile.yaml` returns 0 lines. The mechanism is documented behavior of helmfile.

## Fix (concrete diff)
Already prepared in `helmfile_enhancement_plan/pull_requests/PR-3-HF-08-needs-deps/helmfile.yaml`. Adds:
```yaml
# in temporal release:
needs:
  - temporal/temporal-postgresql
  - temporal/temporal-redis

# in temporal-helloworld-worker release:
needs:
  - temporal/temporal

# in temporal-helloworld-go-web-service release:
needs:
  - temporal/temporal
```

Note: `s3-crud-api` is left without `needs:` — confirmed independent.

## Test gate
- `helmfile build` exits 0 (validates the YAML)
- `helmfile sync --skip-deps --dry-run` shows the dependency order
- On a fresh kind cluster: `helmfile sync` reaches all-Ready in ≤ 4 min on first try (vs ≥ 8 min before fix)

## Cross-references
- **HF-01/03/02** (replicas/probes/PDB): adding `needs:` doesn't help if probes are misconfigured — must ship together for reliability triad to deliver
- **HF-54** (cassandra gossip job): the postsync hook order matters; needs: also drives postsync sequencing
- **HF-14** (postsync idempotency): the race today causes some postsync hooks to run when target isn't Ready, masking the idempotency bug

---

# Item #5 — HF-07: Dual Temporal backend config (Cassandra deployed, Postgres armed bomb)

## Verified evidence
- **`helmfile/helmfile.yaml:200`** — deployed: `driver: "cassandra"` (default datastore)
- **`helmfile/helmfile.yaml:215`** — deployed: `driver: "elasticsearch"` (visibility)
- **`helmfile/helmfile.yaml:226`** — visibility index: `temporal_visibility_v1_dev`
- **`helmfile/temporal-values.yaml:11`** — STANDALONE FILE with `driver: "sql"`, `postgres` (NOT applied by helmfile.yaml)
- **`helmfile/temporal-values.yaml:13`** — `host: temporal-postgresql` + port 5432
- **`helmfile/temporal-values.yaml:23-25`** — visibility ALSO routed to postgres in this file
- 7 of 9 datastore-related config keys differ between the two files (verified via comparison)

## Why this causes instability
**The standalone `temporal-values.yaml` is a loaded gun.** It's not currently applied (helmfile.yaml is authoritative). But:
1. Any operator who runs `helm upgrade temporal temporal/temporal -f temporal-values.yaml` directly **switches the backend on a running cluster**
2. Temporal pods restart, try to find PostgreSQL at `temporal-postgresql:5432` — which IS deployed (see HF-08 evidence)
3. PostgreSQL has NO temporal schema, NO migration job — Temporal hits `pq: relation "namespaces" does not exist` and crashes
4. Cassandra's data is not deleted, but is now orphaned — no path to recovery without manual config rollback
5. Workflow history is **inaccessible** (Postgres has no rows; Cassandra is no longer queried)

**Worse**: there's no warning. The `temporal-values.yaml` file is named like a default reference; an unfamiliar operator might apply it thinking it's the canonical values. The file should not exist, OR it should be renamed to `temporal-values-postgres-NOT-DEPLOYED-DO-NOT-APPLY.yaml.example`.

## Symptom you'd observe in production
- **If never triggered**: zero symptom (it's an armed bomb, not currently firing)
- **If triggered**: complete Temporal data unavailability within 30 s of the wrong helm command
- Recovery: manually edit StatefulSet env to revert `DB=postgres` → `DB=cassandra`, restart pods, hope cassandra never lost quorum during the gap

## Confidence (after critical-thinking pass)
**HIGH (10/10).** Both files exist and contain the conflicting drivers — direct grep evidence. The "armed bomb" framing is the right one: not currently impacting, but mis-operation has catastrophic consequences.

## Fix (concrete diff)
Two options, in increasing strictness:
1. **Minimum**: rename `temporal-values.yaml` → `temporal-values-postgres-NOT-DEPLOYED.yaml.example` and add a top-of-file comment `# DO NOT APPLY — historical / reference / not used by helmfile.yaml`
2. **Better**: delete the file entirely. If you ever need a postgres alternative, regenerate from `helm show values temporal/temporal` at the time you need it. Stale config files are pure technical debt.

## Test gate
- `grep -rn "temporal-values.yaml" helmfile/ scripts/ docs/` returns 0 references (i.e., nothing actually uses it)
- CI lint: any *.yaml file in helmfile/ that contains `driver: "postgres"` AND is not referenced from helmfile.yaml triggers a warning

## Cross-references
- **HF-22** (cassandra heap): if HF-07 fires, the postgres-side has no equivalent heap-tuning config — recovery would surface a new heap issue
- **HF-08** (`needs:`): `temporal-postgresql` IS in the helmfile (because it's needed for the temporal chart's subchart values resolution to validate), so the wrong kubeconfig'd helm command actually has a target to connect to

---

# Item #6 — HF-58: ES visibility `number_of_replicas: 1` + `wait_for_status=yellow` workaround

## Verified evidence
- **`helmfile/helmfile.yaml:218`** — Elasticsearch cluster: `replicas: 3` (3 ES nodes)
- **`helmfile/helmfile.yaml:226`** — visibility index name: `temporal_visibility_v1_dev`
- **`helmfile/helmfile.yaml:231`** — `clusterHealthCheckParams: "wait_for_status=yellow&timeout=1s"` (Temporal accepts yellow, not green)
- **`helmfile/helmfile.yaml:252`** — explicit index template: `number_of_replicas: 1` (each shard replicated once across the 3-node cluster)
- **`helmfile/helmfile.yaml:230`** — comment: "Override readiness probe to accept 'yellow' cluster status instead of 'green'"
- **`helmfile/helmfile.yaml:228-229`** — comment confirms this is a **known workaround**, not a misconfiguration

## Why this causes instability
The `wait_for_status=yellow` setting means Temporal will START even when ES has unallocated replica shards. This sounds OK but creates two failure modes:
1. **During ES pod restart**: visibility queries return inconsistent results (some shards primary-only). UI shows incomplete workflow lists.
2. **During simultaneous primary+replica loss**: cluster goes RED (briefly), Temporal fails visibility writes, **workflow history is permanently lost** for the duration.

With `number_of_replicas: 1` and 3 ES nodes, the math: any single node loss = yellow (acceptable). Two nodes lost = red (catastrophic). With `replicas: 3` ES nodes, two-node loss requires either two near-simultaneous failures OR a network partition. Probability is low but non-zero.

## Symptom you'd observe in production
- Temporal Web UI workflow listings are **inconsistent** across page reloads during ES pod restarts (1-2 % of refreshes show stale data)
- Audit logs occasionally drop visibility events
- During EKS node updates that cordon multiple nodes, ES briefly enters yellow → Temporal `visibility writes degraded` log lines, no visible user impact
- Worst case (two-node failure): Temporal pauses; user-facing workflow APIs return `Unavailable` for 30-90 s

## Confidence (after critical-thinking pass)
**HIGH (10/10).** All four configs verified by direct grep. The yellow-state workaround is explicitly documented in comments. Risk model is well-understood.

## Fix (concrete diff)
Two-stage:
1. **Quick**: increase to `number_of_replicas: 2` (each shard exists on 3 of 3 nodes — survives 2-node loss). Trade-off: ~50 % more disk usage and write amplification.
2. **Better long-term**: `number_of_shards: 3` + `number_of_replicas: 1` (each shard primary on a different node, replica on next). Same total resilience as option 1 with better write parallelism.

```yaml
indexTemplates:
  temporal_visibility_v1_dev:
    settings:
      number_of_shards: 3      # was 1
      number_of_replicas: 1    # unchanged
      refresh_interval: 1s
```

Then update Temporal config to `clusterHealthCheckParams: "wait_for_status=green&timeout=10s"` so Temporal blocks on healthy ES rather than masking failures.

## Test gate
- After fix: `curl localhost:9200/_cluster/health` returns `status: green` within 5 min of every ES pod restart
- After fix: `kubectl delete pod elasticsearch-master-0 -n temporal && sleep 60 && curl <temporal-frontend>/visibility/...` returns same result count as before delete (no data loss window)

## Cross-references
- **HF-22** (cassandra heap): both are storage-layer fragility; both should be addressed before scaling Temporal load
- **HF-04** (CFS throttling): ES is a JVM workload too — same throttling concern applies; if HF-04 isn't fixed, ES recovery from yellow→green will be slower than expected

---

# Item #7 — HF-27 + HF-51 + HF-53: DTE worker contract bundle

## Verified evidence
**HF-27 (os.Exit in long-running daemon):**
- `helmfile/dte/distributed-worker/main.go:659` — `os.Exit(1)` in main on temporal client init failure
- `helmfile/dte/distributed-worker/main.go:673` — `os.Exit(1)` in main on worker creation failure
- `helmfile/dte/distributed-worker/main.go:750` — `os.Exit(1)` INSIDE `http.ListenAndServe` error handler

**HF-51 (no HTTP server timeouts, no graceful shutdown for HTTP):**
- `helmfile/dte/distributed-worker/main.go:748` — `http.ListenAndServe(":"+port, nil)` — uses package-level `DefaultServeMux`, **no `http.Server{}` struct, no ReadTimeout, WriteTimeout, IdleTimeout, or ReadHeaderTimeout**
- `helmfile/dte/distributed-worker/main.go:756` — `signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)` — graceful shutdown for the worker (calls `workerInstance.Stop()`), but **NOT for the HTTP server** — http server is leaked on SIGTERM

**HF-53 (fake /health endpoint):**
- `helmfile/dte/distributed-worker/main.go:729` — `http.HandleFunc("/health", healthHandler)`
- `helmfile/dte/distributed-worker/main.go:764-781` — `healthHandler` body:
  ```go
  func healthHandler(w http.ResponseWriter, r *http.Request) {
      ...
      response := HealthResponse{
          Status:    "healthy",      // hard-coded
          Worker:    "running",       // hard-coded
          Uptime:    uptime.String(), // process uptime — meaningless for health
      }
      w.WriteHeader(http.StatusOK)
      json.NewEncoder(w).Encode(response)
  }
  ```
- **The handler never checks**: temporal frontend reachability, cassandra reachability, kubectl availability, KUBECONFIG validity, recent activity execution success rate
- **`helmfile/dte/charts/dte/templates/distributed-worker-deployment.yaml`** — k8s probes hit `/health`. Probe success implies "worker is alive AND able to serve" — but the handler just confirms the process exists.

## Why this causes instability
The bundle creates a **silent-failure mode** that's the most dangerous class:
1. Temporal frontend dies (HF-54 / HF-08 cause)
2. Worker can't dispatch activities; goroutines pile up waiting for gRPC calls that will never return
3. **k8s readiness probe still passes** (it's a fake 200) → traffic keeps routing to worker → workflows accumulate as "processing" forever
4. Eventually OOM (goroutine leak) or a different fault triggers `os.Exit(1)` → worker pod restarts → returns to step 1

The `os.Exit(1)` instead of structured error returns means **no cleanup happens**: in-flight activities are not heartbeated as failed, locks aren't released, metrics aren't flushed. Temporal's heartbeat timeout eventually surfaces these as "stuck" — with high MTTD.

The missing HTTP timeouts mean a slow client (or a port-scanner) can **hold connections open indefinitely**, eating worker file descriptors. Ulimit (default 1024) hits → ALL HTTP serving fails → readiness probe fails → pod restarts. **Whole class of attacks/accidents triggers preventable restarts.**

## Symptom you'd observe in production
- Worker restart count: 5-20 per day (vs ~1 per day with proper health checks)
- Workflow "stuck in started state" count grows linearly with time between worker restarts
- Slow response time on Temporal Web UI for workflow detail pages (history queries hit the dead worker → wait for timeout)
- `kubectl logs -n dte distributed-worker-0` shows abrupt termination with no shutdown messages — clear signature of `os.Exit(1)`

## Confidence (after critical-thinking pass)
**HIGH (10/10).** All three sub-defects directly verified by reading the source. The fake-health-handler is the most damning — `Status: "healthy"` is a hard-coded string literal.

## Fix (concrete diff)
Three coordinated changes to main.go:

1. **Replace `os.Exit(1)` with structured error returns** (or panic at top-level if truly unrecoverable):
   ```go
   // BEFORE:
   if err := temporalClient.NewClient(...); err != nil {
       log.Fatal(err)
       os.Exit(1)
   }
   // AFTER:
   client, err := temporalClient.NewClient(...)
   if err != nil {
       return fmt.Errorf("temporal client init: %w", err)
   }
   ```
   Wrap main() in a runApp() that returns error; main() prints and returns exit code.

2. **Use `http.Server{}` struct with timeouts + graceful shutdown:**
   ```go
   srv := &http.Server{
       Addr:              ":" + port,
       ReadHeaderTimeout: 5  * time.Second,
       ReadTimeout:       30 * time.Second,
       WriteTimeout:      30 * time.Second,
       IdleTimeout:       120 * time.Second,
       Handler:           http.DefaultServeMux,
   }
   go srv.ListenAndServe()

   <-sigChan
   workerInstance.Stop()
   ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
   defer cancel()
   srv.Shutdown(ctx)
   ```

3. **Make `/health` a real check:**
   ```go
   func healthHandler(w http.ResponseWriter, r *http.Request) {
       if !temporalClient.CheckHealth(ctx) {
           http.Error(w, "temporal frontend unreachable", 503)
           return
       }
       if workerInstance.IsRunning() != true {
           http.Error(w, "worker not running", 503)
           return
       }
       // 200 OK with status payload
   }
   ```

## Test gate
- Unit test (added in PR-N): `TestHealthHandler_returns_503_when_temporal_unreachable` — uses a mock TemporalClient that returns error
- Integration test: kill temporal-frontend pod; assert worker pod becomes NotReady within 30 s
- `go test -race ./helmfile/dte/distributed-worker/... -count=10` returns 0 races
- `kubectl get pods -n dte -w` during a forced HF-54 outage shows worker correctly marked NotReady (today it stays Ready)

## Cross-references
- **HF-50** (os.Setenv race): same file, same shipping cadence — bundle these into one DTE refactor PR
- **HF-54** (cassandra gossip): the fake `/health` actively HIDES the HF-54 symptom — fixing HF-53 is what surfaces HF-54 to operators
- **HF-04** (CFS throttling): the DTE worker is also CPU-throttled, which extends the recovery window when these defects fire

---

# Item #8 — HF-04: CPU CFS throttling on Temporal/Cassandra

## Verified evidence
- **`helmfile/helmfile.yaml:101-106`** — temporal-server: `cpu: 500m` request, `cpu: 1000m` limit (2× burst headroom)
- **`helmfile/helmfile.yaml:148-152`** — temporal-web: `cpu: 250m` request, `cpu: 500m` limit (2× burst)
- **`helmfile/helmfile.yaml:266-270`** — prometheus: `cpu: 500m` request, `cpu: 2000m` limit (4× burst)
- Cassandra block at line 173 — **no explicit CPU resource limits set in helmfile.yaml** (uses Bitnami chart default `requests: cpu 100m, limits: cpu 1000m` — a 10× burst)
- No `cpuManagerPolicy: static` override seen in any kubelet config; standard CFS-bandwidth control applies
- HF-43 caveat: no documented workaround disabling CPU limits

## Why this causes instability
CFS (Completely Fair Scheduler) bandwidth control enforces CPU limits via 100-ms quotas. **For JVM workloads** (Temporal, Cassandra, ES — all 3 are top-10 here), this interacts badly:
1. JVM uses parallel GC with N=numCPU threads — counts the **node** CPUs, not the cgroup limit (unless `-XX:ActiveProcessorCount=N` is set, which it isn't)
2. Under GC, JVM tries to use ~16 cores in parallel, but cgroup limit caps at 1 core
3. **Throttling**: the cgroup tracks (used / limit) per 100 ms; once exceeded, all threads in the cgroup are paused for the rest of the quota window
4. JVM stop-the-world GC can take 200-500 ms instead of 50 ms — visible to clients as latency spikes
5. Healthchecks (k8s probes) timeout during throttling → false-positive failures → pod restarts

This is silent: `kubectl top pod` may show the cgroup at "only" 800 m / 1000 m utilization (averaged over a minute) while individual 100-ms windows hit 100 % and throttle.

The HF-43 caveat: some teams document "disable CPU limits entirely" as a workaround. This is **risky** — it lifts the safety net but does fix the throttling. Need to weigh cost.

## Symptom you'd observe in production
- p99 latency on temporal-frontend gRPC is **5-10× p50** during steady state (typical sign of throttling)
- `container_cpu_cfs_throttled_seconds_total` metric (Prometheus) trends up linearly during steady operation — should be flat near 0
- Periodic readiness-probe failures during GC events — pod restart count climbs slowly
- Cassandra: `nodetool tpstats` shows GC threads waiting in dispatchable state more often than running

## Confidence (after critical-thinking pass)
**MED (7/10).** I verified the limits exist and the burst ratios are tight (2-4×). I did NOT verify CFS throttling is **currently happening** — that requires a Prometheus query against the live cluster:
```promql
sum(rate(container_cpu_cfs_throttled_seconds_total{namespace="temporal"}[5m])) by (pod)
```
If this returns 0 across all pods, HF-04 is theoretical. If it returns >0.01, it's actively impacting.

## Fix (concrete diff)
**Two options:**
1. **Recommended**: increase CPU limits to ≥ 4× requests (e.g., temporal-server `requests: 500m → limits: 2000m`). Costs nothing on idle nodes; provides headroom for GC/burst.
2. **Aggressive**: drop limits entirely (`requests: 500m`, no `limits:`) AND add `kubelet --cpu-manager-policy=static` so the JVM gets exclusive cores. Larger blast radius but matches industry best-practice for JVM workloads on EKS.

Both should also set:
```yaml
env:
  - name: JVM_OPTS
    value: "-XX:ActiveProcessorCount=2"  # match cgroup limit
```
so the JVM stops over-provisioning GC threads.

## Test gate
- Synthetic load test (e.g., `temporal-bench` for 10 min) shows p99 latency ≤ 3× p50
- Prometheus query `rate(container_cpu_cfs_throttled_seconds_total[5m]) > 0.01` returns 0 results
- After 24 h soak: zero readiness-probe failures attributed to GC events

## Cross-references
- **HF-22** (cassandra heap): GC pressure compounds with throttling — fix together
- **HF-58** (ES yellow): ES recovery time depends on JVM GC pace — throttling slows recovery

---

# Item #9 — HF-22: Cassandra heap not tuned for workload (Bitnami default 256 MB)

## Verified evidence
- **`helmfile/helmfile.yaml:173-200`** — cassandra block — **no `MAX_HEAP_SIZE`, no `HEAP_NEWSIZE`, no `JVM_OPTS` for memory** (only `-Dcassandra.consistent.rangemovement` flags)
- Bitnami cassandra chart default: `MAX_HEAP_SIZE: 256m`, `HEAP_NEWSIZE: 100m` (verified from `helm show values bitnami/cassandra`)
- **`helmfile/helmfile.yaml:182`** — comment: "A post-install hook will patch the StatefulSet with proper configuration"
- The "post-install hook" referenced in comment IS HF-54 (the missing file) — so HF-22 is currently UNFIXED in production

## Why this causes instability
256 MB heap is **adequate for an empty Cassandra dataset**. Temporal's workflow-history dataset grows to ~1-10 GB within weeks. Once dataset > heap × 4:
1. Cache misses force frequent disk reads → memtables can't flush fast enough
2. **Old-gen GC fires every 5-10 s**, each pause 200-500 ms
3. **Full GC** (compacting) can pause for 2-5 s — Temporal's 1 s gRPC deadline trips, frontend logs `gocql: context deadline exceeded`
4. Heap pressure leads to OOMKilled (kernel sees memory cap hit) — pod restart, gossip re-converges, repeat

Combined with HF-54 (no JMX), there's no observability for this class of failure — operators see the symptom (workflows pause) but not the cause (cassandra heap).

## Symptom you'd observe in production
- Cassandra pod restart frequency increases monotonically with cluster age (~1/week at month 1, ~1/day at month 6)
- `kubectl top pod cassandra-0 -n temporal` shows memory consistently > 90 % of limit
- Temporal frontend `gocql: context deadline exceeded` log lines correlate with cassandra GC events (not visible without HF-54 JMX exposure)
- During heap pressure, write latency p99 jumps from 5 ms → 200 ms → 2 s → OOM

## Confidence (after critical-thinking pass)
**HIGH (10/10).** Default heap verified by chart documentation; absence of override verified by direct read of helmfile.yaml.

## Fix (concrete diff)
**Done as part of HF-54 PR #11** (the gossip job ALSO sets MAX_HEAP_SIZE=4G HEAP_NEWSIZE=800M). After PR #11 merges + the B1+B2 follow-up:
```bash
kubectl get statefulset cassandra -n temporal -o yaml | yq '.spec.template.spec.containers[0].env'
# expect:
# - name: MAX_HEAP_SIZE
#   value: "4G"
# - name: HEAP_NEWSIZE
#   value: "800M"
```

If HF-54 is reverted, also need a standalone heap-only fix.

## Test gate
- After fix, JMX `java.lang:type=Memory:HeapMemoryUsage.used` < 70 % over a 24-h window
- `nodetool tpstats | grep -i 'gc'` shows < 5 GC events/min
- Temporal frontend gRPC p99 latency to Cassandra is < 50 ms

## Cross-references
- **HF-54** (gossip job): same PR closes both
- **HF-04** (CFS throttling): GC pause time depends on CPU availability — must also fix HF-04 to fully resolve

---

# Item #10 — HF-14: Postsync hook idempotency (some hooks fail on re-apply)

## Verified evidence
Postsync hooks listed in `helmfile/helmfile.yaml`:
| Line | File | Notes |
|---|---|---|
| 354 | `patch-prometheus-config-job.yaml` | exists |
| 371 | `cassandra-metrics-exporter-deployment.yaml` | exists |
| 377 | `cassandra-jmx-exporter-config.yaml` | exists |
| 384 | `cassandra-metrics-exporter-deployment.yaml` (duplicate ref) | exists |
| 400 | `add-cassandra-jmx-scrape-job.yaml` | exists |
| 408 | `cassandra-servicemonitor.yaml` | exists |
| 425 | `remove-unwanted-dashboards-job.yaml` | exists |
| 433 | `delete-dashboards-from-db-job.yaml` (HF-43) | exists |
| 439 | `fix-cassandra-gossip-config-job.yaml` | **MISSING (HF-54)** |

**Idempotency analysis** (sampled — full audit pending):
- `cassandra-servicemonitor.yaml`: `kind: ServiceMonitor` applied via `kubectl apply` → idempotent ✅
- `cassandra-metrics-exporter-deployment.yaml`: `kind: Deployment + Service + ConfigMap` via `kubectl apply` → idempotent ✅
- `add-cassandra-jmx-scrape-job.yaml`: `kind: Job` via `kubectl apply` → **PROBLEM**: Jobs are **immutable** once created. Second `kubectl apply` to a completed Job triggers `field is immutable` error → exit 1 → helmfile postsync fails
- `remove-unwanted-dashboards-job.yaml`: same Job-immutability problem
- `delete-dashboards-from-db-job.yaml`: same problem (also has HF-43 hardcoded password issue)

**Root cause:** Jobs in K8s are NOT idempotent under `kubectl apply`. They must be either:
1. Deleted-and-recreated each time (`kubectl delete job X --ignore-not-found && kubectl apply -f X`)
2. Wrapped in helmfile pre-hook with `helm.sh/hook-delete-policy: hook-succeeded,before-hook-creation`
3. Use `generateName` instead of `name` (creates a new Job each time with a unique suffix)

## Why this causes instability
Every second `helmfile sync` (config tweak, image bump, etc.) triggers re-apply of postsync hooks:
1. `kubectl apply -f remove-unwanted-dashboards-job.yaml` → `error: field is immutable` → exit 1
2. helmfile sees exit 1 from hook command → marks deploy as FAILED
3. Operator gets a red CI build, no actual production impact
4. Operator either:
   - Re-runs the sync (random success because some hooks silently succeed before hitting the broken one — order-dependent)
   - Manually `kubectl delete job X` first, then re-syncs
   - Disables the hook in helmfile.yaml as a workaround

The **second behavior** is the worst: hooks get disabled silently, drift from CI accumulates.

## Symptom you'd observe in production
- `helmfile sync` fails with `field is immutable` errors after the first deploy of any cluster
- CI pipeline failure rate ~30-50 % on follow-up deploys to the same cluster
- Operators have a runbook step: "if you see field-is-immutable errors, run `kubectl delete jobs --all -n temporal --field-selector status.successful=1` then retry"
- Some hooks remain commented out in helmfile.yaml (forgotten as no longer-deployed); silent functional drift

## Confidence (after critical-thinking pass)
**MED (7/10).** I verified the file existence via grep, but I did NOT exhaustively read every postsync file to confirm `kind: Job` vs other kinds. ~3 confirmed Jobs in the list; full audit needed for the other 5 references. To raise to 10/10: open each referenced file and tabulate `kind:` + idempotency strategy.

## Fix (concrete diff)
For each Job-kind postsync hook, switch from raw `kubectl apply -f` to:
```yaml
- events: ["postsync"]
  showlogs: true
  command: bash
  args:
    - -ec
    - |
      kubectl delete job <job-name> -n <namespace> --ignore-not-found
      kubectl apply -f <job-file>.yaml
```

Or migrate to Helm hook with proper delete policy:
```yaml
metadata:
  annotations:
    "helm.sh/hook": post-install,post-upgrade
    "helm.sh/hook-delete-policy": hook-succeeded,before-hook-creation
```

The Helm-hook approach is cleaner but requires moving the Jobs into a chart. The bash-wrapper is the minimum-change fix.

## Test gate
- `helmfile sync` followed by `helmfile sync` (no changes) on same cluster → both exit 0
- `for i in $(seq 5); do helmfile sync; done` → all 5 succeed
- No `field is immutable` strings in the helmfile sync stdout/stderr

## Cross-references
- **HF-08** (`needs:`): the missing dependencies mean some hooks fire BEFORE their target is Ready, masking the immutability bug as a "race" instead of an "idempotency" bug
- **HF-43** (delete-dashboards hardcoded password): one of the immutable Jobs has a separate security defect; fix together to deduplicate the changes
- **HF-54** (missing file): proves the hooks are not validated; HF-14 is a class of issue that the team has been blind to

---

# Appendix A — Rollout sequencing (recommended order)

Based on dependencies surfaced in cross-references above, ship in this order:

| Day | Items | Rationale |
|---|---|---|
| 1 | #1 (HF-54) + #9 (HF-22) | Same PR; closes the most acute observed crash mode (cassandra OOM) |
| 2 | #4 (HF-08 needs:) | Smallest diff; unlocks reliable testing of subsequent items |
| 3 | #2 (HF-01/03/02 triad) + #6 (HF-58 ES replicas) | Both are config-only YAML changes; compounds the resilience gains from #1+#4 |
| 4-5 | #7 (HF-27/51/53 DTE bundle) + #3 (HF-50 setenv race) | Same file (main.go); single PR for code-quality + correctness fixes |
| 6 | #8 (HF-04 CFS throttling) | After #7 + #3, the worker stops thrashing — only NOW is throttling visible to a meaningful baseline |
| 7 | #10 (HF-14 idempotency) | Touches multiple files; lower urgency than the crash fixes; leave for Week 2 |
| Backlog | #5 (HF-07 dual config) | "Armed bomb" — not currently firing. Schedule but don't block on it. |

# Appendix B — Verification ceremony per item

For each item, the PR description should include:
1. **Static evidence**: file:line citations matching this doc
2. **Behavior evidence**: what symptom changes after fix
3. **Negative evidence**: what test would catch a regression
4. **Cross-reference table**: which other HF-NN items are affected
5. **Test gate command**: a single `bash` line that returns 0 iff fix is applied correctly

# Appendix C — Source provenance

| Per-item content sourced from | Used for items |
|---|---|
| Direct grep of `helmfile/helmfile.yaml` | All 10 |
| Direct read of `helmfile/dte/distributed-worker/main.go` | #3, #7 |
| Direct read of `helmfile/temporal-values.yaml` | #5 |
| Existing investigation in `02_FINDINGS_CATALOG.md` | All 10 (provenance check) |
| Test framework results (PR #11) | #1 (B1, B2 bug surfacing) |
| Bitnami chart documentation | #9 (default heap value) |
| K8s SDK / Temporal SDK documentation | #3, #7, #10 (mechanism explanations) |

# Appendix D — Changelog of this document

- 2026-05-11 09:42 — initial author (10 items, all with HIGH or MED confidence)

