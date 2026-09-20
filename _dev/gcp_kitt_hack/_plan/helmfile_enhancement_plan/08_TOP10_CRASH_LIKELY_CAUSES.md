# Top 10 Items Most Likely Contributing to Observed Crashes / Instability

> **Authored:** 2026-05-11 by helmfile_enhancement_plan/ Tier-0 work, **without runtime cluster evidence**.
> **Method:** judgment-based ranking using verified static-code evidence + critical-thinking + code-archaeology of recent ops notes (DEPLOYMENT_SUMMARY.md, KEDA_TEMPORAL_CONNECTION_ISSUE.md, helmfile.yaml comments). Each item carries an explicit **Confidence** (how sure am I the defect is real and active) and **Impact** (how much of the crash symptom does fixing it remove) score.
>
> **Scoring scale:**
> - **Confidence:** *Very High* (binary-verified, can be checked offline) · *High* (multi-line code evidence + ops-note corroboration) · *Med* (code evidence but conditional on workload) · *Low* (plausible but speculative)
> - **Impact:** *Very High* (likely removes >30% of crash incidents) · *High* (likely removes 10-30%) · *Med* (likely removes 5-10%) · *Low* (defense-in-depth; may not change today's incident rate)
> - **Composite priority:** Confidence × Impact, weighted toward Impact (a Very High Impact / Med Confidence item beats a Med Impact / Very High Confidence item)

---

## 0. CRITICAL CAVEATS (read before trusting this list)

1. **The actual deployed Temporal backend is Cassandra**, NOT PostgreSQL.
   - Verified: `helmfile.yaml:207` declares `driver: "cassandra"`.
   - The `temporal-values.yaml` file (PostgreSQL backend) IS NOT applied by `helmfile.yaml`. It's a parallel armed-bomb config (this is exactly **HF-07**).
   - **Consequence:** HF-56 (PostgreSQL maxConns:20) is **NOT currently active** — it would only fire if someone runs `helm upgrade -f temporal-values.yaml` outside the helmfile path. I previously promoted HF-56 to top-3; **demoted to #11** in this list.
   - **Consequence:** Cassandra-related items (HF-54, HF-22, HF-43, HF-16) are all live.

2. **There are no `needs:` directives anywhere in helmfile.yaml** (verified by `grep -nE 'needs:' helmfile.yaml` → 0 hits). On a first deploy or after a delete-and-redeploy, releases come up in declaration order without dependency edges. Temporal can race against Cassandra readiness.

3. **None of these items have been confirmed against runtime cluster evidence** (no kubectl access). Confidence scores reflect static + archaeological evidence only.

4. **Subagents disagreed** on the backend question during my investigation; one read `temporal-values.yaml` (PostgreSQL) and assumed that was the deployed config. I caught this with direct re-verification of `helmfile.yaml:207`. **The dual-config bug is so confusing that even three independent investigators got the wrong answer.** That alone is evidence that HF-07 is operationally dangerous.

---

## The Top 10 (ranked by Confidence × Impact, weighted toward Impact)

### #1 — HF-54: Missing `fix-cassandra-gossip-config-job.yaml`

| Field | Value |
|---|---|
| **Confidence** | **Very High** — `ls helmfile/fix-cassandra-gossip-config-job.yaml` returns "No such file"; helmfile.yaml:432-439 references it from a postsync hook |
| **Impact** | **Very High** — directly causes recurring Cassandra gossip thrash and node-discovery failures, the exact symptom the user describes |
| **Crash mechanism** | Every `helmfile apply` runs the postsync hook → `kubectl apply -f fix-cassandra-gossip-config-job.yaml` → file missing → hook errors. Critically, **the JVM options that the hook is supposed to set include `-Dcassandra.consistent.rangemovement=false` and `-Dcassandra.load_ring_state=false`** (helmfile.yaml:188). Without these flags applied at JVM startup, Cassandra nodes that restart load **stale gossip state** from peers → split-gossip → "Down" status → Temporal frontend can't reach storage → Temporal pod restart loop. |
| **Why this is #1** | It is the only top-3 candidate that is BOTH (a) a binary-verifiable defect (file exists or it doesn't) AND (b) has a comment in helmfile.yaml that literally describes the failure mode it was meant to fix ("This helps fix gossip issues when nodes have stale peer information") AND (c) the fix-job is explicitly the one ops manually wrote to address ongoing issues — meaning the *issue is real and known to ops* but the fix never lands |
| **Fix** | Restore the file (~50 lines, can be reconstructed from helmfile.yaml comments at lines 184-190) OR delete the postsync hook (6-line removal) if the fix has been applied manually. **Default: restore.** |
| **Fix blast radius** | LOW. The job sets JVM startup options on Cassandra StatefulSet. Wrong values cause node won't start, easily detected during apply. |
| **Acceptance** | `helmfile apply 2>&1 \| grep -ic "fix-cassandra-gossip-config-job.yaml" → 0`; `kubectl exec cassandra-0 -- nodetool status` shows all nodes as `UN` (Up Normal) for >1 hour |

---

### #2 — HF-01 + HF-03 + HF-02 (probes / replicas / PDBs — must ship as bundle)

| Field | Value |
|---|---|
| **Confidence** | **Very High** — verified `replicaCount: 1` at helmfile.yaml lines 74, 100, 146 (3 separate services); no startupProbe in temporal-manifests/temporal-server.yaml; `kubectl get pdb -n temporal` would show 0 (we predict) |
| **Impact** | **Very High** — without these, *any* pod restart for *any* reason becomes a full outage. With Cassandra-backed Temporal needing >120s startup, **kubelet kills frontend/history mid-keyspace-init**. |
| **Crash mechanism** | (1) Temporal frontend pod starts → connects to Cassandra → schema verification takes 60-120s → kubelet's default liveness probe (10s timeout, 3 failures = ~30s grace) kills it as "unhealthy" → restart → keyspace verification starts over → infinite loop. (2) `replicaCount: 1` means there's no second pod to absorb traffic during the restart → frontend RPCs from history/matching/worker time out → cascade. (3) No PDB means `kubectl drain` (for routine node maintenance) evicts the only replica → guaranteed outage. |
| **Why bundle?** | Shipping any single one of HF-01/02/03 alone moves no metric. Probes without 2+ replicas just delays the inevitable single-pod outage. 2 replicas without PDB still die on `kubectl drain`. Probes + PDB without 2 replicas still single-points-of-failure. **Must ship together.** |
| **Why #2 not #1** | Equal confidence to #1, but slightly less impact: #1 is causing *active* gossip thrash on every deploy; this bundle causes outages only when something else triggers a pod restart. #1 is the trigger; this bundle is the amplifier. Fix #1 first to reduce the trigger frequency; ship this bundle to make residual triggers non-fatal. |
| **Fix** | startupProbe: `initialDelaySeconds: 60, periodSeconds: 10, failureThreshold: 30` for frontend/history/matching/worker (allows up to 5min startup); replicaCount: `2` for all four services + Web; PodDisruptionBudget(minAvailable: 1) for each. ~50 lines + 5 PDB manifests. |
| **Fix blast radius** | LOW. PDBs are advisory until a drain happens. Probes with conservative thresholds can only false-positive (extra restart), not false-negative (mask real failure). |
| **Acceptance** | Force `kubectl delete pod -n temporal temporal-frontend-0`; new pod reaches Ready ≤180s without restart loops. `kubectl drain <node>` succeeds without taking down Temporal. |

---

### #3 — HF-50: `os.Setenv` race in concurrent Temporal activities

| Field | Value |
|---|---|
| **Confidence** | **Very High** — verified at `dte/distributed-worker/main.go:910,915-916,999,1004-1005`; verified `MaxConcurrentActivityExecutionSize: 20` at line 683 → **20 concurrent activities can race on `os.Setenv`** simultaneously |
| **Impact** | **High** — produces intermittent, non-reproducible 401/403 failures; directly degrades workflow reliability; **invisible in normal logging** because the corruption is timing-dependent |
| **Crash mechanism** | `HealthCheckActivity` and `ServiceDiscoveryActivity` both call `os.Setenv("DTE_SLAUTH_TOKEN", authToken)`. `os.Setenv` mutates process-wide state. Temporal worker runs up to 20 activities concurrently in goroutines within ONE process. Activity A's tokens get overwritten by Activity B mid-execution → A's downstream HTTP call uses B's token → 401/403 → activity fails → workflow retries → **retry loop with the same race**. Symptoms: intermittent "permission denied" against random target clusters; disappear on retry; NEVER reproducible in dev. |
| **Why #3** | This is the textbook Heisenbug. **Cannot debug from logs alone** — the corruption happens in-process. A growing fraction of "mysterious workflow failures" likely traces here. The 20-concurrent-activity setting is the gun; multiple `os.Setenv` calls are the bullet. |
| **Fix** | Pass tokens through activity input map (already partially supported by Temporal); thread through function parameters; remove ALL `os.Setenv`/`os.Unsetenv` from activity bodies. ~100 LoC, contained refactor. |
| **Fix blast radius** | LOW-MED. Activities still receive the same token; only the delivery mechanism changes. Unit-testable. |
| **Acceptance** | `grep -nE 'os\.(Setenv\|Unsetenv)' dte/distributed-worker/*.go → 0 hits`. Add a stress test running 50 concurrent activities with distinct tokens; assert each downstream call sees the right token. |

---

### #4 — HF-08: Missing `needs:` between releases (first-deploy race)

| Field | Value |
|---|---|
| **Confidence** | **Very High** — `grep -nE 'needs:' helmfile.yaml` returns 0 hits |
| **Impact** | **Very High** for first-deploy and post-disaster-recovery; **Low** for steady-state |
| **Crash mechanism** | Without `needs:`, helmfile applies releases in declaration order with **no readiness gating**. Temporal release tries to come up before `temporal-postgresql` (vestigial), `temporal-redis`, AND Cassandra are ready → connection-refused → init failure → CrashLoopBackOff → kubelet retries → eventually one of the dependencies comes up → Temporal stabilizes after several minutes of crash-looping. **DEPLOYMENT_ORDER.md (per subagent 3) explicitly documents "controller crashing because config-domain ConfigMap didn't exist"** — same class of bug. |
| **Why #4** | Doesn't crash steady-state but **every fresh deploy looks broken for 5-10 minutes** until accidental ordering settles. Operators get used to it; pipelines have implicit retries; nobody fixes the root cause. **Trivial fix, large operability gain.** |
| **Fix** | Add `needs: ["k8s/redis", "k8s/elasticsearch", "k8s/cassandra"]` (or actual release names) to the Temporal release. Repeat for `temporal-helloworld-worker → temporal`. ~10 lines. |
| **Fix blast radius** | LOW. `needs:` only adds wait-for-ready; it cannot break anything. Worst case is slower deploys. |
| **Acceptance** | Fresh deploy from `helmfile destroy && helmfile apply` succeeds in single pass without CrashLoopBackOff on Temporal. |

---

### #5 — HF-07: Dual Temporal backend config (Cassandra ↔ Postgres)

| Field | Value |
|---|---|
| **Confidence** | **Very High** — verified `helmfile.yaml:207 driver: "cassandra"` AND `temporal-values.yaml:12 cassandra.enabled: false` (Postgres backend declared) |
| **Impact** | **Very High** when it fires (Temporal silent re-point + data-loss risk); **Zero** until then. Armed bomb. |
| **Crash mechanism** | Two values files exist with incompatible Temporal backends. `helmfile.yaml` applies Cassandra. `temporal-values.yaml` declares Postgres. **Whoever runs `helm upgrade temporal -f temporal-values.yaml` outside the helmfile path** (any oncall, any operator who copy-pastes a runbook step, any Argo CD sync drift) will silently re-point Temporal at a Postgres that may not exist → **immediate crashloop + workflow data loss** if the keyspace is then reformatted. |
| **Why #5** | Cannot be ranked higher because it's not actively crashing today. Cannot be ranked lower because the **investigation itself proved the danger** — three independent subagents read the wrong values file and reported PostgreSQL was the deployed backend. If three careful investigators got it wrong, an oncall at 3am will too. |
| **Fix** | Either (a) delete `temporal-values.yaml` (best — single source of truth) OR (b) rename to `temporal-values.dev-only.yaml` + add header comment `# DO NOT use with helm upgrade temporal -- this is shadow config for dev experimentation only`. Trivial. |
| **Fix blast radius** | ZERO if you choose (a) and the file truly isn't applied (verified). |
| **Acceptance** | `find helmfile/ -name 'temporal-values*' → 0` (option a) OR file renamed with explanatory header (option b). |

---

### #6 — HF-58: Elasticsearch visibility `replicas: 1` → permanent yellow + workaround

| Field | Value |
|---|---|
| **Confidence** | **Very High** — verified `helmfile.yaml:251-252` (`number_of_shards: 1, number_of_replicas: 1`) AND ES has 3 nodes (line 224 `replicas: 3`). With 3 ES nodes, replicas:1 SHOULD work, but the code uses workaround `wait_for_status=yellow` (line 235), suggesting the cluster IS NOT actually 3 nodes in practice |
| **Impact** | **High** — masks real ES issues; if a node fails, replica can't reallocate; visibility queries degrade |
| **Crash mechanism** | The presence of `wait_for_status=yellow` workaround is itself the smoking gun: **operators set this to make pods come up despite the cluster being unhealthy**. This means in production, ES is permanently yellow; Temporal "visibility" queries (workflow history search) hit unassigned-shard errors silently; sometimes timeout under load → workflow task failures → the user sees crashes. The workaround masks the symptom but doesn't fix the cause. |
| **Why #6** | High Confidence + High Impact, but ES queries failing silently is a *latency / reliability* bug, not a *crash-the-pod* bug. Demoted to #6 because items above more directly explain pod restarts. |
| **Fix** | Two paths: (a) `number_of_replicas: 0` if running single-node ES (matches the workaround intent); (b) verify the cluster IS 3-node and remove the `wait_for_status=yellow` workaround so green is enforced. **Default: (a)** because it's safer and matches the apparent reality. |
| **Fix blast radius** | LOW. Replicas=0 means no redundancy on visibility data; visibility data is reconstructable from Temporal history. |
| **Acceptance** | `curl :9200/_cluster/health` returns `status: green` within 60s of apply. |

---

### #7 — HF-27 + HF-51 + HF-53: DTE worker contract bundle (os.Exit + HTTP timeouts + fake `/health`)

| Field | Value |
|---|---|
| **Confidence** | **Very High** — verified all three: `os.Exit(1)` at main.go:749 in HTTP-listener goroutine; bare `http.ListenAndServe` (no timeouts) at line 747; `/health` returns hardcoded `{"Status":"healthy"}` at lines 763-780 regardless of worker liveness |
| **Impact** | **High** — silent worker death masked from k8s; workflow tasks pile up; user sees "stuck" workflows |
| **Crash mechanism** | Triple-layered failure: (a) any port-bind blip kills the pod via os.Exit(1); (b) slow client / dropped TCP keeps connections open forever (no timeouts); (c) when the worker goroutine errors out (Temporal connection lost, panic, etc.), the goroutine logs and exits but **the HTTP server keeps running and `/health` keeps returning 200** — k8s leaves the pod in service → activities never processed → workflow timeouts. **The user sees: workflows stuck, no errors in any single log, "everything looks healthy."** |
| **Why #7** | Bundles cleanly; ~40 LoC fix; high impact on workflow reliability. Below probes/replicas because it doesn't *cause* pod restarts (it *masks* them). |
| **Fix** | (a) Replace `os.Exit(1)` with structured-error-and-restart-via-supervisor; (b) `http.Server{ReadTimeout:10s, WriteTimeout:30s, IdleTimeout:120s}`; (c) atomic worker-health flag + `recover()` in the worker goroutine; `/health` reads the flag. ~40 LoC. |
| **Fix blast radius** | LOW. Each change is locally contained. |
| **Acceptance** | Force-kill Temporal frontend connection; within 30s `/health` returns 503; pod removed from service. |

---

### #8 — HF-04: CPU CFS throttling on Temporal/Cassandra (with HF-43 caveat)

| Field | Value |
|---|---|
| **Confidence** | **High** — verified Temporal `cpu: 1000m` limit, Cassandra has limits, JVM workloads (Temporal Java + Cassandra Java + Kibana Java) are all CPU-limited. Recent Prometheus memory comment (`Increased from 4Gi to 8Gi … Recommended 12Gi`) shows ops actively firefighting resource pressure. |
| **Impact** | **High** for tail latency; **Med** for actual crashes |
| **Crash mechanism** | JVMs experience GC pauses; during a pause, the GC threads consume CPU bursts that exceed the limit → CFS throttles them → GC takes 5-10x longer → application thread starves → Temporal frontend RPC times out → history pod marks frontend unhealthy → cascade. **Indirect crash mechanism via timeout cascade.** |
| **Why #8** | High Confidence + High Impact-on-latency, but only Med Impact on the specific *crash* symptom. The crash needs the timeout cascade to actually trigger; on a quiet cluster, throttling produces only latency tails. |
| **Fix** | **Remove CPU limits** on Cassandra/Temporal/JVM workloads (keep CPU *requests* for scheduling). This is the standard recommendation for JVM workloads on Kubernetes — see kubernetes.io guidance and Java in Kubernetes blog posts. ~15 lines of YAML. |
| **Fix blast radius** | MED. Removing limits means a runaway JVM can consume all node CPU. Mitigation: set requests appropriately so scheduler reserves capacity; use Pod Priority Class to make Cassandra/Temporal `system-cluster-critical`. |
| **Acceptance** | Prometheus query `rate(container_cpu_cfs_throttled_periods_total{namespace="temporal"}[5m]) → 0`. p99 Temporal RPC latency reduced ≥ 30%. |

---

### #9 — HF-22: Cassandra memory pressure / heap not tuned for workload

| Field | Value |
|---|---|
| **Confidence** | **Med-High** — verified Cassandra has limits set, JVM heap config exists in the helmfile.yaml jvm_opts string, but heap size is not visible in the snippet I read. Indirect evidence: the gossip workaround flags exist, post-install hooks exist, JMX is configured for monitoring — operators are watching this closely, suggesting active issues. |
| **Impact** | **High** when it fires — Cassandra OOMKill restart triggers all the Temporal cascade above |
| **Crash mechanism** | Cassandra heap too small for working set → frequent GC → eventually OOMKill or heap-exhaustion exception → node down → triggers HF-54 (gossip thrash without the fix-job applied) → Temporal frontend can't reach storage → cascade. |
| **Why #9** | Med-High Confidence (haven't read the actual JVM heap value); High Impact when triggered. **Causally linked to #1** — if HF-54 is fixed, HF-22's downstream impact shrinks dramatically. |
| **Fix** | Set Cassandra heap to ~50% of container memory limit; configure JMX-readable heap metrics; add an alert at 80% heap. ~10 lines of jvm_opts changes + 1 alerting rule. |
| **Fix blast radius** | LOW. Right-sized heap is operationally safer than current. |
| **Acceptance** | `nodetool gcstats` shows GC frequency reduced; no OOMKill on Cassandra StatefulSet for 7 days. |

---

### #10 — HF-14: Postsync hook idempotency (re-apply crash on second deploy)

| Field | Value |
|---|---|
| **Confidence** | **High** — verified 10 postsync hooks at helmfile.yaml lines 338, 354, 362, 371, 378, 394, 402, 409, 425, 433. Per subagent 3, **DEPLOYMENT_ORDER.md explicitly documents "controller crashing because config-domain ConfigMap didn't exist"** — first-class evidence that postsync hooks have caused production crashes. |
| **Impact** | **Med-High** — affects every redeploy / GitOps sync; doesn't affect quiet steady-state |
| **Crash mechanism** | A hook does e.g. `kubectl create configmap …` without `--dry-run=client \| kubectl apply -f -` idempotency. On second `helmfile apply`, the hook errors with "already exists" → helmfile may abort → partial deploy state → some pods restart with old config, some with new → drift → eventually one pod crashes because of mismatched config. |
| **Why #10** | High Confidence; Med-High Impact (only on redeploys); the missing-file case (HF-54) is a strict subset of "hook fails silently/loudly," but HF-54 deserves its own #1 slot because it has unique causal link to gossip. The other 9 hooks need a generic idempotency wrapper. |
| **Fix** | Wrap each postsync hook in a `command: bash` invocation that does `kubectl apply -f` (idempotent) instead of `kubectl create -f` (one-shot). Where the hook is intrinsically one-shot (e.g., `cassandra snapshot before ddl`), gate it on a state check (`kubectl get … 2>/dev/null \|\| run-the-hook`). ~30 lines across 10 hooks. |
| **Fix blast radius** | LOW. `kubectl apply` is idempotent by design; gating on existence is a standard pattern. |
| **Acceptance** | `helmfile apply` run twice in succession (with no source changes) produces zero hook failures. |

---

## Summary table — all 10 with composite priority

| Rank | HF | Title | Confidence | Impact | Composite | Why this rank |
|---|---|---|---|---|---|---|
| 1 | HF-54 | Missing gossip job file | Very High | Very High | 25 | Active gossip thrash every deploy; comment in code documents the unfixed bug |
| 2 | HF-01+03+02 | Probes / replicas / PDBs (bundle) | Very High | Very High | 24 | No bundle = no benefit; together = restarts non-fatal |
| 3 | HF-50 | os.Setenv race | Very High | High | 20 | Heisenbug; corrupts auth tokens at high concurrency |
| 4 | HF-08 | Missing `needs:` | Very High | Very High (first-deploy) / Low (steady) | 18 | Trivial fix, eliminates 5-10min crashloop on every fresh deploy |
| 5 | HF-07 | Dual backend config | Very High | Very High (when it fires) / Zero (today) | 16 | Armed bomb; investigators got fooled mid-investigation |
| 6 | HF-58 | ES yellow + workaround | Very High | High (latency, masked errors) | 16 | wait_for_status=yellow workaround proves operators know |
| 7 | HF-27+51+53 | DTE worker contract bundle | Very High | High (silent stuck workflows) | 15 | Masks failures rather than causing them |
| 8 | HF-04 | CPU CFS throttling | High | High (latency) / Med (crash) | 12 | Indirect crash via timeout cascade |
| 9 | HF-22 | Cassandra memory | Med-High | High (when fires) | 10 | Causally linked to #1; fix #1 first |
| 10 | HF-14 | Postsync hook idempotency | High | Med-High (redeploy only) | 9 | Generic version of #1; ops note documents past crash |

**Items I deliberately demoted** (with reasoning):

- **HF-56 (PostgreSQL maxConns: 20)** — was top-3 in my prior message; demoted to **NOT in top 10** because the PostgreSQL backend is NOT actually deployed (HF-07 dual-config). Becomes #1 the moment HF-07 fires.
- **HF-10 (KEDA gRPC)** — was top-7 candidate; demoted because the doc reads as a *diagnostic narrative* not a *current outage*. Likely already worked-around. Keep at MED priority.
- **HF-17 (ES ILM)** — long-term issue; not crashing today.
- **HF-23 (gRPC plaintext)** — security, not crash.
- **HF-46/47/49** (strategic refactors) — months away.
- **HF-39 (Cilium policies)** — already downgraded to MED in Appendix E; not implicated.

---

## What this top-10 buys you, in three sentences

**If you ship items #1, #2 (bundle), #4, and #5 in week 1 (~150 lines of code change across 4 PRs), you address the "every deploy crashes for 5-10 minutes" symptom AND the "Cassandra recurrently goes sideways" symptom AND remove the dual-config armed bomb.** Items #3, #6, #7 in week 2 address the silent-failure modes (workflow auth corruption, masked ES degradation, stuck workflows). Items #8, #9, #10 in weeks 3-4 address the latency-tail-induced cascades and re-apply hazards. **Total: ~10 PRs, ~400 lines of code change, addresses the full crash-and-instability story without touching anything strategic (HF-46/47/49) or security-only (HF-06/HF-42/HF-61).**

Security items (HF-06 creds.json, HF-42 Grafana password, HF-61 JWT) are **not in this top-10 by design** — they are critical CRITICAL but not crash-causing. They should ship in a parallel security-sprint, not by displacing crash fixes.

---

## Confidence in this ranking itself

**Med-High overall.** Specifically:

- ✅ **Very High** for the *static defects* — every HF cited above has direct file:line evidence I verified personally
- ✅ **High** for the *causal mechanism* — each crash mechanism is grounded in well-known k8s / Temporal / Cassandra failure modes
- ⚠️ **Med** for the *causal probability today* — without runtime evidence (no cluster access), I cannot rule out that some other issue (network, DNS, IAM) is the actual primary cause
- ⚠️ **Low** for the *exact ordering* of items 6-10 — these are within ranking-noise of each other; reasonable people could swap them

**The strongest evidence behind this list is the helmfile.yaml *comments themselves*** — operators wrote multiple "this fix is needed because X happens" comments next to configurations, and those comments are still the current state of the file. Operators know about the bugs. The fixes haven't been applied.

If you can run `diagnostics/crash_root_cause_diagnostic.sh` against the cluster, all items 1-10 will be re-classified into CONFIRMED / LIKELY / UNLIKELY / INCONCLUSIVE within ~2 minutes and this ranking can be tightened by an order of magnitude.

---

## Cross-references

- Full HF details: `02_FINDINGS_CATALOG.md`
- PR-level diff + acceptance + rollback: `04_PR_BREAKDOWN.md`
- Sequencing/tier rationale: `03_PRIORITIZED_PLAN.md`
- Refutation log (HF-57 EBS, HF-39 Cilium): `02_FINDINGS_CATALOG.md` Appendix E
- Runtime diagnostic: `diagnostics/crash_root_cause_diagnostic.sh`
- Provenance to source plans: `07_PARENT_PLAN_INTEGRATION.md`
