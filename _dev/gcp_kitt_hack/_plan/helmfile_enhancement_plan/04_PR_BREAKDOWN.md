# PR Breakdown — 22 reviewable PRs (one per finding)

> Every PR has:
> - **Stable ID** (`PR-HF-NN`) — quote in commit messages and Jira tickets
> - **Branch suggestion** (`fix/helmfile-…` / `chore/helmfile-…`)
> - **Files touched** with rough LoC budget
> - **Unified diff** (or pattern, where line-numbers vary across env files)
> - **Acceptance criterion** (a single command whose exit code or stdout determines pass/fail)
> - **Rollback** (single command)
> - **Depends-on** (PR-level dependencies)
> - **Risk-of-being-wrong** (the refute-attempt)
>
> All file paths are relative to `atlassian_packages/gcp_kitt/helmfile/` unless absolute.
> All diffs are `diff -U3` style. Apply with `git apply <patch>`.

---

## T0 — STOP THE BLEEDING

### `PR-HF-06` — Remove `python-app/creds.json` + revoke GCP impersonation

- **Branch:** `security/helmfile-remove-gcp-creds-from-git`
- **Files touched:** `python-app/creds.json` (delete), `.gitignore` (1 line), `python-app/README.md` (~10 lines documentation)
- **LoC budget:** −80 lines (deletion) + ~15
- **Depends-on:** none
- **Axis moved:** Security
- **Severity:** CRITICAL

**Patch:**
```bash
# Step 1: revoke first, *then* commit removal (so rotation race is closed)
gcloud iam workload-identity-pools providers describe aws83542177192 \
  --location=global --workload-identity-pool=kittwif --project=561807058386
# (capture the bound service account; coordinate with security team for revoke)

# Step 2: remove from working tree and index
cd atlassian_packages/gcp_kitt/helmfile
git rm --cached python-app/creds.json
rm python-app/creds.json

# Step 3: harden .gitignore
cat >> .gitignore <<'EOF'
# GCP workload identity / service account JSON — NEVER commit
**/creds.json
**/service-account-*.json
**/*-key.json
EOF

# Step 4: history rewrite (separate operation; coordinate with the team)
# Recommended: BFG Repo-Cleaner
#   bfg --delete-files creds.json
#   git reflog expire --expire=now --all && git gc --prune=now --aggressive
```

**Acceptance:**
```bash
[ -z "$(git ls-files atlassian_packages/gcp_kitt/helmfile/python-app/creds.json)" ] && echo PASS || echo FAIL
```

**Rollback:** N/A (security action; do not roll back). Re-creating creds.json should fetch from GCP Secret Manager via `python-app/credentials.py` instead.

**Risk-of-being-wrong:** LOW. Even if `python-app/main.py` requires creds at runtime, it can read them from `GOOGLE_APPLICATION_CREDENTIALS` env var pointing to a secret-mounted path. **Verify before merge:** `grep -rn 'creds.json' python-app/` to find readers and migrate them.

---

### `PR-HF-11` — `cleanup-all.sh` env-guard + kube-context check

- **Branch:** `safety/cleanup-all-confirmation-gate`
- **Files touched:** `cleanup-all.sh` (~10 lines)
- **LoC budget:** +12
- **Depends-on:** none
- **Axis moved:** Operability
- **Severity:** HIGH

**Patch:**
```diff
--- a/atlassian_packages/gcp_kitt/helmfile/cleanup-all.sh
+++ b/atlassian_packages/gcp_kitt/helmfile/cleanup-all.sh
@@ -1,5 +1,17 @@
 #!/bin/bash
+set -euo pipefail
+IFS=$'\n\t'

-set -e
+# Safety gates — refuse to run unless explicitly confirmed.
+if [[ "${I_REALLY_MEAN_IT:-0}" != "1" ]]; then
+  echo "REFUSING: this will force-delete ALL helmfile namespaces and CRDs." >&2
+  echo "  To proceed: I_REALLY_MEAN_IT=1 bash cleanup-all.sh" >&2
+  exit 2
+fi
+CTX="$(kubectl config current-context 2>/dev/null || echo unknown)"
+if [[ "$CTX" == *prod* || "$CTX" == *production* ]]; then
+  echo "REFUSING: current kube-context '$CTX' looks like a prod cluster." >&2
+  exit 3
+fi
+echo "Proceeding on context: $CTX (5s grace) ..." >&2
+sleep 5
```

**Acceptance:**
```bash
# Without env-var → exit 2
bash atlassian_packages/gcp_kitt/helmfile/cleanup-all.sh; [ $? -eq 2 ] && echo PASS-1 || echo FAIL-1

# With env-var on a non-prod context → proceeds (don't actually run on a real cluster)
I_REALLY_MEAN_IT=1 timeout 1 bash -n atlassian_packages/gcp_kitt/helmfile/cleanup-all.sh && echo PASS-2 || echo FAIL-2
```

**Rollback:** `git revert <sha>`

**Risk-of-being-wrong:** LOW. The only "regression" is on-call frustration if they forget the env-var; preferable to the alternative.

---

### `PR-HF-07` — Remove `temporal-values.yaml` configuration drift

- **Branch:** `chore/helmfile-remove-temporal-values-drift`
- **Files touched:** `temporal-values.yaml` (rename or delete), optionally `Makefile` / pre-commit hook
- **LoC budget:** −63 (delete) + ~5 (Makefile guard)
- **Depends-on:** none
- **Axis moved:** Reliability + Operability
- **Severity:** CRITICAL

**Patch (Option A — delete; recommended):**
```bash
cd atlassian_packages/gcp_kitt/helmfile
git rm temporal-values.yaml
```

**Patch (Option B — keep but mark UNUSED, if anyone might need the Postgres-backend reference):**
```diff
--- /dev/null
+++ b/atlassian_packages/gcp_kitt/helmfile/temporal-values.dev-postgres-only.yaml
@@ -0,0 +1,6 @@
+# UNUSED — DO NOT APPLY against the canonical cluster.
+# This file documents the legacy Postgres-backed Temporal configuration.
+# The current production configuration uses Cassandra (helmfile.yaml:259-282).
+# If you need a Postgres-backed dev cluster, copy this file under a new name
+# AND ensure helmfile.yaml is overridden accordingly. Kept for historical reference.
+# Last verified: 2026-05-11.
```
…then `git mv temporal-values.yaml temporal-values.dev-postgres-only.yaml` and apply the diff above on top.

**Optional Makefile guard:**
```diff
--- a/atlassian_packages/gcp_kitt/helmfile/Makefile
+++ b/atlassian_packages/gcp_kitt/helmfile/Makefile
@@ -1,5 +1,9 @@
 .PHONY: apply
 apply:
+	@if grep -rl 'temporal-values\.yaml' . | grep -v Makefile | head -1 | grep -q .; then \
+	   echo "ERROR: temporal-values.yaml referenced — drift trap. See PR-HF-07." >&2; \
+	   exit 1; \
+	fi
 	helmfile apply
```

**Acceptance:**
```bash
# Either zero copies, or one copy clearly marked UNUSED:
COUNT=$(find atlassian_packages/gcp_kitt/helmfile -name 'temporal-values*.yaml' | wc -l)
[ "$COUNT" -eq 0 ] && echo PASS-A && exit
[ "$COUNT" -eq 1 ] && head -1 $(find atlassian_packages/gcp_kitt/helmfile -name 'temporal-values*.yaml') | grep -q UNUSED && echo PASS-B
```

**Rollback:** `git revert <sha>`

**Risk-of-being-wrong:** MED. Some script or dev runbook may reference `temporal-values.yaml` by name. **Pre-merge check:** `grep -rn temporal-values.yaml atlassian_packages/ | grep -v node_modules`.

---

### `PR-HF-05` — Move plaintext secrets to `existingSecret:` references

- **Branch:** `security/helmfile-existing-secret-refs`
- **Files touched:** `helmfile.yaml` (~6 hunks), `values-eks.yaml` (1 hunk), new `helmfile/secrets-bootstrap.md`
- **LoC budget:** ~40 changed + 100 new docs
- **Depends-on:** `PR-HF-07` (delete drift first)
- **Axis moved:** Security
- **Severity:** CRITICAL

**Bootstrap step (one-time, manual; documented in new `secrets-bootstrap.md`):**
```bash
kubectl create namespace temporal --dry-run=client -o yaml | kubectl apply -f -

# Postgres
kubectl -n temporal create secret generic temporal-postgres-secret \
  --from-literal=postgres-password=$(openssl rand -hex 32) \
  --from-literal=password=$(openssl rand -hex 32)

# Redis
kubectl -n temporal create secret generic temporal-redis-secret \
  --from-literal=redis-password=$(openssl rand -hex 32)

# Grafana
kubectl -n temporal create secret generic temporal-grafana-admin \
  --from-literal=admin-user=admin \
  --from-literal=admin-password=$(openssl rand -hex 32)
```

**Patch (excerpt — apply to `helmfile.yaml`):**
```diff
--- a/atlassian_packages/gcp_kitt/helmfile/helmfile.yaml
+++ b/atlassian_packages/gcp_kitt/helmfile/helmfile.yaml
@@ -27,11 +27,8 @@ releases:
       - global:
           postgresql:
             auth:
-              postgresPassword: "temporal-postgres-password"
+              existingSecret: "temporal-postgres-secret"
+              secretKeys:
+                adminPasswordKey: postgres-password
+                userPasswordKey: password
             database: "temporal"
         auth:
-          username: "temporal"
-          password: "temporal-password"
+          username: "temporal"
+          existingSecret: "temporal-postgres-secret"
+          secretKeys:
+            userPasswordKey: password
           database: "temporal"
@@ -62,9 +59,8 @@ releases:
     values:
       - auth:
           enabled: true
-          password: "temporal-redis-password"
+          existingSecret: "temporal-redis-secret"
+          existingSecretPasswordKey: redis-password
@@ -298,10 +294,8 @@ releases:
         grafana:
           enabled: true
-          adminUser: "admin"
-          adminPassword: "Yfd2HxAsXiQ7brwIoeR5i2tvYH2jmRSBViBsWRM8"
+          admin:
+            existingSecret: "temporal-grafana-admin"
+            userKey: admin-user
+            passwordKey: admin-password
```
Plus a similar diff for `values-eks.yaml:88` Grafana admin override.

**Acceptance:**
```bash
# Returns 0
grep -nE 'password.*:.*"[A-Za-z0-9]{6,}"' atlassian_packages/gcp_kitt/helmfile/*.yaml | wc -l
```

**Rollback:** `helm rollback temporal <previous-rev>` and `git revert <sha>`. Bootstrap secrets remain in cluster (idempotent).

**Risk-of-being-wrong:** MED. Bitnami `existingSecret` key names differ across chart versions. **Pre-merge:** `helm show values bitnami/postgresql --version 16.7.27 | grep -A4 existingSecret`.

---

### `PR-HF-01` — Add startup/readiness/liveness probes for Temporal sub-roles

- **Branch:** `reliability/temporal-probes`
- **Files touched:** `helmfile.yaml` (4 hunks; one per sub-role)
- **LoC budget:** ~80 (4 × 20)
- **Depends-on:** `PR-HF-07` (drift removed)
- **Axis moved:** Reliability + Latency
- **Severity:** CRITICAL

**Patch (excerpt for the `frontend:` block; mirror for `history`, `matching`, `worker`):**
```diff
--- a/atlassian_packages/gcp_kitt/helmfile/helmfile.yaml
+++ b/atlassian_packages/gcp_kitt/helmfile/helmfile.yaml
@@ -134,6 +134,21 @@ releases:
         frontend:
           podAnnotations:
             prometheus.io/scrape: "true"
             prometheus.io/port: "9090"
             prometheus.io/job: "temporal-frontend"
+          startupProbe:
+            tcpSocket:
+              port: 7233
+            initialDelaySeconds: 60
+            periodSeconds: 10
+            failureThreshold: 30   # 5 min budget for Cassandra-backed startup
+          readinessProbe:
+            tcpSocket:
+              port: 7233
+            periodSeconds: 5
+            timeoutSeconds: 3
+            failureThreshold: 3
+          livenessProbe:
+            tcpSocket:
+              port: 7233
+            periodSeconds: 30
+            failureThreshold: 5
```

**Why TCP probe instead of HTTP/gRPC health-check?** Temporal's gRPC health check requires `grpc_health_probe` binary in the image (not present in `temporalio/server:1.28.1`). TCP is a sound proxy for "frontend is accepting connections" and matches Temporal's documented probe recipe. Upgrade to gRPC health-probe is a follow-up (see `06_OUT_OF_BOX.md` of the parent plan family).

**Acceptance:**
```bash
kubectl describe pod -n temporal -l app.kubernetes.io/component=frontend \
  | grep -E 'Liveness:|Readiness:|Startup:' | wc -l | grep -q '^[3-9]' && echo PASS || echo FAIL
```

**Rollback:** `helm rollback temporal <previous-rev>`. The diff is purely additive at the chart-values level; rollback removes the probe overrides and restores chart defaults.

**Risk-of-being-wrong:** MED. The Temporal helm chart 0.65.0 may already supply default probes. If so, our overrides take effect; if values keys differ between chart versions (`startupProbe` vs `probes.startup.enabled`), the override is silently ignored. **Pre-merge:** `helm show values temporal/temporal --version 0.65.0 | grep -A 2 -E '(startup|liveness|readiness)Probe'`.

---

### `PR-HF-03` — Bump replicas to 2 for Temporal sub-roles + Web + Redis-replica

- **Branch:** `reliability/temporal-replica-2`
- **Files touched:** `helmfile.yaml` (5 single-line changes), optional `values-eks.yaml`
- **LoC budget:** ±0 (value-only)
- **Depends-on:** `PR-HF-01`
- **Axis moved:** Reliability
- **Severity:** CRITICAL

**Patch:**
```diff
--- a/atlassian_packages/gcp_kitt/helmfile/helmfile.yaml
+++ b/atlassian_packages/gcp_kitt/helmfile/helmfile.yaml
@@ -68,7 +68,7 @@ releases:
         replica:
-          replicaCount: 1
+          replicaCount: 2
@@ -97,7 +97,7 @@ releases:
       - server:
-          replicaCount: 1
+          replicaCount: 2
@@ -145,7 +145,7 @@ releases:
         web:
           enabled: true
-          replicaCount: 1
+          replicaCount: 2
```

**Resource budget impact** (per cluster):
- Temporal server: +500m CPU req, +1Gi mem req per role × 4 roles = **+2 vCPU, +4 Gi RAM**.
- Web: +250m CPU, +512Mi mem.
- Redis replica: +100m CPU, +256Mi mem (per `values-eks.yaml:42-45`).
- **Total: ~+2.5 vCPU, +5 Gi RAM** at request level. Verify `kubectl describe nodes | grep -A4 Allocatable` has headroom.

**Acceptance:**
```bash
kubectl get deploy,sts -n temporal -o json \
  | jq -r '.items[] | select(.metadata.name | test("frontend|history|matching|worker|web")) | "\(.metadata.name) \(.spec.replicas)"' \
  | awk '$2 < 2 { print "FAIL:", $0; exit 1 }' && echo PASS
```

**Rollback:** `git revert <sha>` then `helmfile apply`.

**Risk-of-being-wrong:** LOW. Standard scale-out. Postgres deferred (single instance) → documented in PR description as known follow-up.

---

### `PR-HF-02` — Add PodDisruptionBudgets via `temporal-pdbs.yaml`

- **Branch:** `reliability/temporal-pdbs`
- **Files touched:** new `temporal-pdbs.yaml` (~70 lines), `helmfile.yaml` (~6 lines new postsync hook)
- **LoC budget:** +75
- **Depends-on:** `PR-HF-03`
- **Axis moved:** Reliability
- **Severity:** CRITICAL

**Patch (new file `temporal-pdbs.yaml`):**
```yaml
# PDBs for the Temporal control plane.
# Convention: with replicaCount=2, set maxUnavailable: 1 (allow rolling but never two-down).
# If a release has only 1 replica today (postgres), use minAvailable: 1 — kubectl drain will
# cordon-and-wait rather than evict.
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: { name: temporal-frontend-pdb, namespace: temporal }
spec:
  maxUnavailable: 1
  selector: { matchLabels: { app.kubernetes.io/name: temporal, app.kubernetes.io/component: frontend } }
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: { name: temporal-history-pdb, namespace: temporal }
spec:
  maxUnavailable: 1
  selector: { matchLabels: { app.kubernetes.io/name: temporal, app.kubernetes.io/component: history } }
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: { name: temporal-matching-pdb, namespace: temporal }
spec:
  maxUnavailable: 1
  selector: { matchLabels: { app.kubernetes.io/name: temporal, app.kubernetes.io/component: matching } }
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: { name: temporal-worker-pdb, namespace: temporal }
spec:
  maxUnavailable: 1
  selector: { matchLabels: { app.kubernetes.io/name: temporal, app.kubernetes.io/component: worker } }
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: { name: temporal-postgresql-pdb, namespace: temporal }
spec:
  minAvailable: 1   # 1-replica today; cordon-and-wait
  selector: { matchLabels: { app.kubernetes.io/name: postgresql } }
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: { name: temporal-redis-master-pdb, namespace: temporal }
spec:
  minAvailable: 1
  selector: { matchLabels: { app.kubernetes.io/name: redis, app.kubernetes.io/component: master } }
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: { name: temporal-redis-replica-pdb, namespace: temporal }
spec:
  maxUnavailable: 1
  selector: { matchLabels: { app.kubernetes.io/name: redis, app.kubernetes.io/component: replica } }
```

**Wire into `helmfile.yaml` hooks (postsync, after Temporal release):**
```diff
@@ -340,6 +340,12 @@ releases:
     hooks:
+      - events: ["postsync"]
+        showlogs: true
+        command: kubectl
+        args:
+          - apply
+          - -f
+          - temporal-pdbs.yaml
```

**Acceptance:**
```bash
kubectl get pdb -n temporal -o name | wc -l | awk '$1 >= 5 { exit 0 } { exit 1 }' && echo PASS
```

**Rollback:** `kubectl delete -f temporal-pdbs.yaml -n temporal`

**Risk-of-being-wrong:** LOW. PDBs are advisory until a drain happens. Even if labels are slightly off (chart label drift), the PDB is harmless when its selector matches nothing (`status: currentHealthy=0` and you'll see it in `kubectl get pdb`). **Pre-merge:** `kubectl get pod -n temporal --show-labels | head -5` to verify label keys match selectors above.

---

## T1 — REMOVE RECURRENCE

### `PR-HF-08` — Add `needs:` declarations between releases

- **Branch:** `reliability/helmfile-needs-deps`
- **Files touched:** `helmfile.yaml` (~12 lines added)
- **LoC budget:** +12
- **Depends-on:** T0 done
- **Axis:** Reliability + Operability
- **Severity:** HIGH

**Patch:**
```diff
--- a/atlassian_packages/gcp_kitt/helmfile/helmfile.yaml
+++ b/atlassian_packages/gcp_kitt/helmfile/helmfile.yaml
@@ -88,6 +88,9 @@ releases:
   - name: temporal
     namespace: temporal
+    needs:
+      - temporal/temporal-postgresql
+      - temporal/temporal-redis
     chart: temporal/temporal
     version: 0.65.0
@@ -442,6 +445,8 @@ releases:
   - name: temporal-helloworld-worker
     namespace: temporal-helloworld
+    needs:
+      - temporal/temporal
@@ -453,6 +458,8 @@ releases:
   - name: temporal-helloworld-go-web-service
     namespace: temporal-helloworld
+    needs:
+      - temporal-helloworld/temporal-helloworld-worker
@@ -464,6 +471,7 @@ releases:
   - name: s3-crud-api
     namespace: dtaske
+    needs: []   # explicit: independent of temporal stack
```

**Acceptance:**
```bash
helmfile -f atlassian_packages/gcp_kitt/helmfile/helmfile.yaml --debug list \
  | grep -cE 'NAME|temporal-(postgresql|redis|helloworld)' >= 5 && echo PASS
# Optional: helmfile destroy reverses the order: temporal first, then redis/postgres
```

**Rollback:** `git revert <sha>`

**Risk-of-being-wrong:** LOW. `needs:` syntax is documented in helmfile v0.x; format `<namespace>/<release-name>`. **Pre-merge:** `helmfile --debug template` exits 0.

---

### `PR-HF-09` — Eliminate `dte/distributed-worker/cluster_db.go` drift

- **Branch:** `chore/dte-cluster-db-canonical`
- **Files touched:** `dte/distributed-worker/cluster_db.go` (delete most), `dte/distributed-worker/main.go` (import swap), tests
- **LoC budget:** −300, +60
- **Depends-on:** none
- **Axis:** Reliability + Operability
- **Severity:** HIGH

**Patch (conceptual — full diff is mechanical):**
```diff
--- a/atlassian_packages/gcp_kitt/helmfile/dte/distributed-worker/cluster_db.go
+++ b/atlassian_packages/gcp_kitt/helmfile/dte/distributed-worker/cluster_db.go
@@ -1,4 +1,4 @@
-package main
+package main

 import (
   ...
+  "temporal-helloworld-dte/pkg/cluster"
+  "temporal-helloworld-dte/pkg/types"
 )

-// ClusterInfo represents a Kubernetes cluster ...   (DELETE entire struct, lines 16-33)
-type ClusterInfo struct {
-  ...
-}
+// ClusterInfo is exposed by pkg/types as the canonical type.
+type ClusterInfo = types.ClusterInfo

-// ClusterDB manages the cluster database (DELETE local copy)
-type ClusterDB struct {
-   clusters  map[string]*ClusterInfo
-   kibanaURL string
-}
+// Use the canonical ClusterDB from pkg/cluster.
+type ClusterDB = cluster.ClusterDB
+var NewClusterDB = cluster.NewClusterDB

-// fetchClusterFromKibana(...) — DELETE inline implementation (lines ~94-200);
-// use cluster.ClusterDB methods.
```

After this PR, `distributed-worker/cluster_db.go` shrinks to ~30 lines of type aliases + var assignments; all logic comes from `pkg/cluster`.

**Acceptance:**
```bash
cd atlassian_packages/gcp_kitt/helmfile/dte
go build ./... && go test ./...
diff -u distributed-worker/cluster_db.go pkg/cluster/cluster_db.go | wc -l | awk '$1 < 50 { exit 0 } { exit 1 }' && echo PASS
```

**Rollback:** `git revert <sha>`. Worker rebuilds with old struct.

**Risk-of-being-wrong:** MED. The dead-code branch in worker's `fetchClusterFromKibana` (lines 109-117) handled legacy `/api/console/proxy` URLs in `kibanaURL`. **Pre-merge:** verify no caller passes a URL containing `/api/console/proxy` at runtime: `grep -rn '/api/console/proxy' atlassian_packages/gcp_kitt/`.

---

### `PR-HF-04` — Remove (or 4×-bump) CPU `limits` for Temporal + Cassandra

- **Branch:** `latency/remove-cpu-limits-jvm`
- **Files touched:** `helmfile.yaml` (~6 small hunks), `values-eks.yaml` (~3 hunks)
- **LoC budget:** −12 or +6
- **Depends-on:** `PR-HF-01` (probes must work to detect any regression)
- **Axis:** Latency
- **Severity:** HIGH

**Patch (Option A — remove limits; recommended for JVM):**
```diff
--- a/atlassian_packages/gcp_kitt/helmfile/helmfile.yaml
+++ b/atlassian_packages/gcp_kitt/helmfile/helmfile.yaml
@@ -100,11 +100,9 @@ releases:
       - server:
           replicaCount: 2
           resources:
             requests:
               cpu: 500m
               memory: 1Gi
-            limits:
-              cpu: 1000m
               memory: 2Gi
```
Repeat for Web, Worker, Cassandra blocks.

**Patch (Option B — 4× bump if cluster has noisy-neighbor concerns):**
```diff
             limits:
-              cpu: 1000m
+              cpu: 2000m
               memory: 2Gi
```

Choose **A for prod** (k8s SIG-node guidance: JVM workloads suffer CFS throttling under tight CPU limits); choose **B for shared/dev clusters** where one rogue pod must not eat all node CPU.

**Acceptance:**
```bash
# Confirm CPU limits absent (Option A) OR ≥2× request (Option B)
kubectl get deploy -n temporal -o json \
  | jq -r '.items[].spec.template.spec.containers[].resources.limits.cpu // "none"' \
  | sort -u
# Expected: "none" (Option A) or "2" / "2000m" (Option B)
```

**Rollback:** `helm rollback temporal <prev>` then `git revert <sha>`. **Required for Option A:** add Prom alert `container_cpu_throttled_seconds_total{namespace="temporal"} > 1` BEFORE merging so a regression auto-pages.

**Risk-of-being-wrong:** MED. Cluster autoscaler may not have head-room if many pods burst simultaneously. **Canary 4 h on a non-prod cluster** before prod merge.

---

### `PR-HF-15` — Cassandra JMX hardening + `consistent.rangemovement` timestamping

- **Branch:** `security/cassandra-jmx-networkpolicy`
- **Files touched:** new `cassandra-jmx-netpol.yaml`, `helmfile.yaml` (1 hunk + 1 hook)
- **LoC budget:** +60
- **Depends-on:** none
- **Axis:** Security + Reliability
- **Severity:** HIGH

**Patch — new NetworkPolicy:**
```yaml
# cassandra-jmx-netpol.yaml — restrict Cassandra JMX (port 7199) to metrics-exporter only.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: cassandra-jmx-restrict
  namespace: temporal
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: cassandra
  policyTypes: [Ingress]
  ingress:
    - ports:
        - port: 7199
          protocol: TCP
      from:
        - podSelector:
            matchLabels:
              app: cassandra-metrics-exporter
    # Allow inter-Cassandra (gossip): port 7000/7001/9042 from same StatefulSet
    - ports:
        - port: 7000
        - port: 7001
        - port: 9042
      from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: cassandra
```

**Patch — helmfile.yaml comment annotation on the JVM opts:**
```diff
--- a/atlassian_packages/gcp_kitt/helmfile/helmfile.yaml
+++ b/atlassian_packages/gcp_kitt/helmfile/helmfile.yaml
@@ -181,6 +181,12 @@
           config:
+            # WARNING — `consistent.rangemovement=false` is a one-time bootstrap escape hatch.
+            # MUST flip to `true` after first stable cluster. Owner: <name>. Date set: 2026-05-08.
+            # Tracking: PR-HF-15 follow-up. Leaving on permanently risks data inconsistency
+            # during scale events (Cassandra streams won't wait for range agreement).
             jvm_opts: "-Dcassandra.consistent.rangemovement=false -Dcassandra.load_ring_state=false ..."
```

**Patch — wire NetworkPolicy as a postsync hook:**
```diff
+      - events: ["postsync"]
+        showlogs: true
+        command: kubectl
+        args: [apply, -f, cassandra-jmx-netpol.yaml]
```

**Acceptance:**
```bash
# From a non-exporter pod, JMX should be unreachable:
kubectl run -n temporal --rm -it --restart=Never --image=busybox jmx-test -- \
  nc -zv -w 3 cassandra-0.cassandra.temporal.svc.cluster.local 7199
# Expect: "no route to host" or timeout. Exit code != 0.

# From metrics-exporter, JMX should still work:
kubectl exec -n temporal -l app=cassandra-metrics-exporter -- \
  nc -zv -w 3 cassandra-0.cassandra.temporal.svc.cluster.local 7199
# Expect: "open". Exit code 0.
```

**Rollback:** `kubectl delete networkpolicy cassandra-jmx-restrict -n temporal`

**Risk-of-being-wrong:** MED. If `cassandra-metrics-exporter` pod label differs from `app: cassandra-metrics-exporter`, the policy locks out exporter too. **Pre-merge:** `kubectl get pod -n temporal -l app=cassandra-metrics-exporter` returns ≥1 pod.

---

### `PR-HF-10` — KEDA Temporal scaler diagnostic + ScaledObject fix

- **Branch:** `fix/keda-temporal-scaler-grpc`
- **Files touched:** new `helmfile/scripts/keda-diagnose.sh`, ScaledObject manifest (location TBD via diagnose), KEDA-version pin in helmfile.yaml
- **LoC budget:** +120 (script) + ~5 (manifest)
- **Depends-on:** none
- **Axis:** Latency + Operability
- **Severity:** HIGH

**Patch — `helmfile/scripts/keda-diagnose.sh`:**
```bash
#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Stage 1 — gather facts
echo "=== KEDA operator image (must be ≥ v2.14.0 for Temporal scaler) ==="
kubectl -n keda get deploy keda-operator \
  -o jsonpath='{.spec.template.spec.containers[*].image}'
echo
echo "=== KEDA operator pod containers (look for service-mesh sidecar) ==="
kubectl -n keda get pod -l app=keda-operator \
  -o jsonpath='{.items[0].spec.containers[*].name}'
echo
echo "=== DNS test from KEDA pod ==="
kubectl -n keda exec deploy/keda-operator -c keda-operator -- \
  nslookup temporal-frontend.temporal.svc.cluster.local || true
echo
echo "=== Short-DNS variant ==="
kubectl -n keda exec deploy/keda-operator -c keda-operator -- \
  nslookup temporal-frontend.temporal.svc || true
echo
echo "=== Temporal frontend logs (last 50 lines) ==="
kubectl -n temporal logs -l app.kubernetes.io/component=frontend --tail=50 \
  | grep -i -E 'connection|reject|deadline|peer' || true
echo
echo "=== ScaledObject status ==="
kubectl -n dtaske get scaledobject scraper-worker-scaler -o yaml \
  | yq '.status'
echo
echo "=== HPA status ==="
kubectl -n dtaske describe hpa keda-hpa-scraper-worker-scaler \
  | grep -A 20 'Conditions\|Events'
```

**Patch — ScaledObject swap to short-DNS endpoint** (illustrative; apply to wherever the manifest lives):
```diff
@@ ScaledObject metadata @@
 triggers:
   - metadata:
-      endpoint: temporal-frontend.temporal.svc.cluster.local:7233
+      endpoint: temporal-frontend.temporal.svc:7233
       namespace: default
       targetQueueSize: "50"
       taskQueue: scraper-task-queue
     type: temporal
```

**Patch — pin KEDA in helmfile.yaml (if KEDA is managed via helmfile; otherwise document upgrade in PR description):**
```diff
+  - name: keda
+    namespace: keda
+    chart: kedacore/keda
+    version: 2.14.2   # First version with stable Temporal scaler
```

**Acceptance:**
```bash
# 1. ScaledObject reports scaling-active = True
kubectl get scaledobject -n dtaske scraper-worker-scaler \
  -o jsonpath='{.status.conditions[?(@.type=="Active")].status}' | grep -q True && echo PASS-1

# 2. HPA can fetch metrics
kubectl get hpa -n dtaske keda-hpa-scraper-worker-scaler \
  -o jsonpath='{.status.conditions[?(@.type=="ScalingActive")].status}' | grep -q True && echo PASS-2

# 3. Synthetic load → replicas scale up
kubectl get hpa -n dtaske keda-hpa-scraper-worker-scaler -w  # observe replicas climb
```

**Rollback:** Restore old ScaledObject manifest from git; `kubectl apply -f <old>`. KEDA version downgrade only if the pin was the cause of regression.

**Risk-of-being-wrong:** MED. The doc lists 6 hypotheses; we're betting on hypotheses 1 (KEDA scaler version) and 2 (DNS form). Diagnose script captures the others (service mesh, frontend rejecting). **Run diagnose first; if root cause is hypothesis 3-6, this PR's fix won't apply and a follow-up is needed.**

---

### `PR-HF-14` — `apply-and-verify.sh` wrapper for postsync hooks

- **Branch:** `operability/helmfile-hook-verification`
- **Files touched:** new `helmfile/scripts/apply-and-verify.sh`, `helmfile.yaml` (mass swap of ~10 hook commands)
- **LoC budget:** +50 (script) + ~80 (helmfile rewrites)
- **Depends-on:** `PR-HF-12` (script hygiene baseline)
- **Axis:** Operability
- **Severity:** HIGH

**Patch — `helmfile/scripts/apply-and-verify.sh`:**
```bash
#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

manifest="${1:?usage: apply-and-verify.sh <manifest.yaml>}"

# Apply, then verify based on kind.
kubectl apply -f "$manifest"

# Iterate over each top-level resource in the manifest (handles multi-doc YAML).
mapfile -t kinds < <(yq -r '.kind' "$manifest")
mapfile -t names < <(yq -r '.metadata.name' "$manifest")
ns=$(yq -r '.metadata.namespace // ""' "$manifest" | head -1)

for i in "${!kinds[@]}"; do
  kind="${kinds[$i]}"; name="${names[$i]}"
  case "$kind" in
    Job)
      kubectl wait --for=condition=Complete --timeout=180s \
        -n "$ns" "job/$name" || {
          echo "FAILED: Job $name did not complete in 180s; dumping logs:" >&2
          kubectl -n "$ns" logs -l job-name="$name" --tail=200 >&2
          exit 1
        }
      ;;
    Deployment|StatefulSet|DaemonSet)
      kubectl rollout status -n "$ns" "$kind/$name" --timeout=180s
      ;;
    *)
      # ConfigMap, Service, NetworkPolicy etc. — apply was sufficient.
      ;;
  esac
done
```

**Patch — example helmfile.yaml hook conversion (apply same pattern to all ~10 hooks):**
```diff
@@ -340,7 +340,7 @@ releases:
       - events: ["postsync"]
         showlogs: true
-        command: kubectl
-        args: [apply, -f, cleanup-unwanted-dashboards-job.yaml]
+        command: bash
+        args: [scripts/apply-and-verify.sh, cleanup-unwanted-dashboards-job.yaml]
```

**Acceptance:**
```bash
# Synthetic test: introduce a deliberately-bad Job (image:doesnotexist:latest)
# and verify the hook returns non-zero.
cat > /tmp/bad-job.yaml <<'EOF'
apiVersion: batch/v1
kind: Job
metadata: { name: bad-job, namespace: default }
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: bad
          image: registry.invalid/does-not-exist:latest
          command: ["true"]
  backoffLimit: 1
  ttlSecondsAfterFinished: 60
EOF
bash atlassian_packages/gcp_kitt/helmfile/scripts/apply-and-verify.sh /tmp/bad-job.yaml
[ $? -ne 0 ] && echo PASS || echo FAIL
```

**Rollback:** `git revert <sha>` — restores raw `kubectl apply` commands.

**Risk-of-being-wrong:** MED. 180-s timeout may be tight for slow Cassandra-dependent Jobs (`temporal-keyspace-setup-job.yaml`). **Pre-merge:** time each Job manually; bump per-job timeout if needed via env var `TIMEOUT_SECONDS=600 bash scripts/apply-and-verify.sh ...`.

---

### `PR-HF-12` — Mass `set -euo pipefail` sweep for 17 shell scripts

- **Branch:** `chore/helmfile-shell-hygiene`
- **Files touched:** 17 `*.sh` files
- **LoC budget:** ~3 lines per script × 17 = ~50
- **Depends-on:** `PR-HF-11`
- **Axis:** Operability
- **Severity:** HIGH

**Patch — uniform diff applied to each script (example for `cleanup-and-redeploy.sh`):**
```diff
--- a/atlassian_packages/gcp_kitt/helmfile/cleanup-and-redeploy.sh
+++ b/atlassian_packages/gcp_kitt/helmfile/cleanup-and-redeploy.sh
@@ -1,3 +1,4 @@
 #!/bin/bash
-set -e
+set -euo pipefail
+IFS=$'\n\t'
```

**Files to patch:**
- Has `set -e` only (replace): `cleanup-all.sh` (already in HF-11), `cleanup-and-redeploy.sh`, `cleanup-knative.sh`, `add-clusters-to-es.sh`, `add-all-clusters-to-es.sh`, `apply-cassandra-metrics.sh`, `import-aws-accounts-fast.sh`, `import-aws-accounts-with-progress.sh`, `download-aws-accounts-with-cookie.sh`, `patch-prometheus-config.sh`, `update-cassandra-exporter-image.sh`, `get-cluster-token.sh`.
- Has no `set` (insert): `recreate-cassandra-statefulset-with-vac.sh`, `fix-unassigned-shards.sh`, `delete-old-indices.sh`, `apply-and-verify-cassandra-exporter.sh`, `deploy-knative.sh`.

**Audit step (must run before merge):**
```bash
for f in atlassian_packages/gcp_kitt/helmfile/*.sh; do
  bash -n "$f" || { echo "SYNTAX FAIL: $f"; exit 1; }
done
# For -u to mean anything, dry-run with strict mode:
for f in atlassian_packages/gcp_kitt/helmfile/*.sh; do
  bash -nu "$f" 2>&1 | grep -v 'unbound variable' || true
done
```

**Acceptance:**
```bash
for f in atlassian_packages/gcp_kitt/helmfile/*.sh; do
  head -5 "$f" | grep -q 'set -euo pipefail' || { echo "FAIL: $f"; exit 1; }
done
echo PASS
```

**Rollback:** `git revert <sha>`

**Risk-of-being-wrong:** MED. `-u` will reveal latent unbound vars. **Per-script:** smoke-test each in dev with `bash -x <script>` and have an env-var defaults block (`: "${VAR:=default}"`) ready for any unbound vars uncovered.

---

### `PR-HF-17` — Restore ES `wait_for_status=green` + add ILM policy

- **Branch:** `reliability/elasticsearch-green-plus-ilm`
- **Files touched:** `helmfile.yaml` (1 hunk), new `elasticsearch-ilm-policy-job.yaml`
- **LoC budget:** +50
- **Depends-on:** none (but operationally: must run `bash fix-unassigned-shards.sh` first if cluster currently yellow)
- **Axis:** Reliability + Latency
- **Severity:** HIGH

**Patch — helmfile.yaml:**
```diff
@@ -231,8 +231,8 @@
           visibilityIndex: "temporal_visibility_v1_dev"
-          # Override readiness probe to accept "yellow" cluster status instead of "green"
-          # ... (REMOVE workaround comment block)
-          clusterHealthCheckParams: "wait_for_status=yellow&timeout=1s"
+          # Restored to green after PR-HF-17 — yellow-acceptance was masking allocation issues.
+          clusterHealthCheckParams: "wait_for_status=green&timeout=5s"
```

**Patch — new ILM policy Job (`elasticsearch-ilm-policy-job.yaml`):**
```yaml
apiVersion: batch/v1
kind: Job
metadata: { name: temporal-visibility-ilm-setup, namespace: temporal }
spec:
  backoffLimit: 3
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: setup-ilm
          image: curlimages/curl:8.9.1
          command: [sh, -c]
          args:
            - |
              set -euo pipefail
              ES=elasticsearch-master:9200
              # Define ILM policy: rollover daily or at 10GB, delete after 14 days.
              curl -fsSL -X PUT "$ES/_ilm/policy/temporal_visibility_policy" \
                -H 'Content-Type: application/json' -d '{
                  "policy": {
                    "phases": {
                      "hot":    { "actions": { "rollover": { "max_age": "1d", "max_size": "10gb" } } },
                      "delete": { "min_age": "14d", "actions": { "delete": {} } }
                    }
                  }
                }'
              # Attach policy to existing index template.
              curl -fsSL -X PUT "$ES/_index_template/temporal_visibility_v1_dev_template" \
                -H 'Content-Type: application/json' -d '{
                  "index_patterns": ["temporal_visibility_v1_dev*"],
                  "template": {
                    "settings": {
                      "index.lifecycle.name": "temporal_visibility_policy",
                      "index.lifecycle.rollover_alias": "temporal_visibility_v1_dev"
                    }
                  }
                }'
```

**Wire into helmfile.yaml as postsync hook (using HF-14's wrapper):**
```diff
+      - events: ["postsync"]
+        showlogs: true
+        command: bash
+        args: [scripts/apply-and-verify.sh, elasticsearch-ilm-policy-job.yaml]
```

**Acceptance:**
```bash
# 1. Cluster reaches green within 60s after Job applies
timeout 60 bash -c 'until curl -s "$ES/_cluster/health" | jq -re ".status==\"green\""; do sleep 5; done' && echo PASS-1

# 2. ILM policy is visible
curl -s "$ES/_ilm/policy/temporal_visibility_policy" | jq -e '.temporal_visibility_policy' > /dev/null && echo PASS-2
```

**Rollback:** Revert helmfile.yaml hunk; delete ILM policy via `curl -X DELETE "$ES/_ilm/policy/temporal_visibility_policy"`.

**Risk-of-being-wrong:** HIGH if cluster has stuck unassigned shards. **Mandatory pre-merge:** `bash fix-unassigned-shards.sh` completes successfully and `curl -s "$ES/_cluster/health" | jq -r .status` returns `green` *before* this PR is merged.

---

## T2 — HARDEN

### `PR-HF-13` — Pin `bitnami/kubectl:1.32.0` in all `*-job.yaml`

- **Branch:** `chore/pin-kubectl-image-version`
- **Files touched:** ~9 `*-job.yaml` files
- **LoC budget:** ±0 (1 char per file)
- **Depends-on:** none
- **Axis:** Operability
- **Severity:** MED

**Patch (apply to each affected file):**
```diff
-        image: bitnami/kubectl:latest
+        image: bitnami/kubectl:1.32.0
```

Files: `cleanup-unwanted-dashboards-job.yaml`, `copy-dashboards-job.yaml`, `delete-dashboard-files-job.yaml`, `delete-unwanted-dashboards-job.yaml`, `fix-cassandra-downtime-job.yaml`, `migrate-cassandra-to-persistent-storage-job.yaml`, `recreate-cassandra-statefulset-with-vac-job.yaml`, `remove-unwanted-dashboards-job.yaml`. (Plus any `curlimages/curl:latest` → `curlimages/curl:8.9.1`.)

**Acceptance:**
```bash
grep -nE 'image:.*:latest' atlassian_packages/gcp_kitt/helmfile/*-job.yaml | wc -l | grep -q '^0$' && echo PASS
```

**Rollback:** `git revert <sha>`

**Risk-of-being-wrong:** LOW. Pin version must support cluster's K8s minor (verify with `kubectl version --short` against bitnami/kubectl 1.32 supported range). Bitnami publishes a compatibility matrix.

---

### `PR-HF-16` — Cassandra seed-count cap (≤ 3)

- **Branch:** `reliability/cassandra-seed-cap`
- **Files touched:** `helmfile.yaml` (~5 lines under cassandra block) and/or `fix-cassandra-gossip-config-job.yaml`
- **LoC budget:** +10
- **Depends-on:** none
- **Axis:** Reliability
- **Severity:** MED

**Patch (illustrative — chart-specific key may differ):**
```diff
@@ helmfile.yaml cassandra block @@
         cassandra:
           enabled: true
+          # Seed-node cap: only the first 3 ordinals act as seeds.
+          # All-nodes-as-seeds floods gossip during partition recovery.
+          seedCount: 3
+          additionalSeeds: ""
```

If the chart doesn't expose `seedCount`, patch via the existing `fix-cassandra-gossip-config-job.yaml` post-install hook (set `CASSANDRA_SEEDS=cassandra-0,cassandra-1,cassandra-2` env via the StatefulSet patch).

**Acceptance:**
```bash
kubectl exec -n temporal cassandra-0 -- nodetool gossipinfo \
  | awk '/^\/.*$/ { peer=$0 } /SCHEMA/ { peers[peer]++ } END { for (p in peers) print p }' \
  | wc -l | awk '$1 <= 3 { exit 0 } { exit 1 }' && echo PASS
```

**Rollback:** Restore prior helmfile.yaml; `kubectl rollout restart sts/cassandra -n temporal`.

**Risk-of-being-wrong:** MED. After this change, cassandra-3, cassandra-4, etc. lose seed status — they must already be bootstrapped before this lands or their re-join may stall. **Pre-merge:** `nodetool status` shows all nodes as `UN`.

---

### `PR-HF-18` — Bump default-namespace retention 72h → 168h; add short-lived NS

- **Branch:** `latency/temporal-retention`
- **Files touched:** `helmfile.yaml` (1 hunk)
- **LoC budget:** +10
- **Depends-on:** none
- **Axis:** Latency
- **Severity:** MED

**Patch:**
```diff
@@ helmfile.yaml line 95-99 @@
       - namespaces:
           create: true
           namespace:
             - name: default
-              retention: 72h
+              retention: 168h           # 7 days; aligned with HF-21 gc_grace
+            - name: short-lived
+              retention: 72h            # opt-in for ephemeral workflows
```

**Acceptance:**
```bash
kubectl exec -n temporal deploy/temporal-admintools -- \
  tctl --ns default namespace describe | grep -E 'Retention.*168'
```

**Rollback:** `git revert <sha>`. Existing workflows already retained at 168h are not affected; new retention applies forward only.

**Risk-of-being-wrong:** LOW. Increased retention raises Cassandra disk usage by ~2.3× linearly; verify `kubectl get pvc -n temporal` has headroom. Document in PR description.

---

### `PR-HF-21` — Set Cassandra `gc_grace_seconds=259200` for temporal keyspace

- **Branch:** `latency/cassandra-gc-grace`
- **Files touched:** new `cassandra-gc-grace-setup-job.yaml`, `helmfile.yaml` (1 hook line)
- **LoC budget:** +35
- **Depends-on:** `PR-HF-18` (retention aligned)
- **Axis:** Latency
- **Severity:** MED

**Patch — new Job (idempotent ALTER):**
```yaml
apiVersion: batch/v1
kind: Job
metadata: { name: temporal-gc-grace-setup, namespace: temporal }
spec:
  backoffLimit: 3
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: cqlsh
          image: cassandra:4.1.3
          command: [sh, -c]
          args:
            - |
              set -euo pipefail
              cqlsh temporal-cassandra -e "
                ALTER TABLE temporal.executions WITH gc_grace_seconds = 259200;
                ALTER TABLE temporal.history_node WITH gc_grace_seconds = 259200;
                ALTER TABLE temporal.tasks WITH gc_grace_seconds = 259200;
                ALTER TABLE temporal.namespaces WITH gc_grace_seconds = 259200;
              "
```

**Wire as postsync (via HF-14 wrapper):**
```diff
+      - events: ["postsync"]
+        showlogs: true
+        command: bash
+        args: [scripts/apply-and-verify.sh, cassandra-gc-grace-setup-job.yaml]
```

**Acceptance:**
```bash
kubectl exec -n temporal cassandra-0 -- cqlsh -e \
  "DESCRIBE TABLE temporal.executions" | grep -E 'gc_grace_seconds = 259200' && echo PASS
```

**Rollback:** Job to set `gc_grace_seconds = 864000` (default) — provide as `cassandra-gc-grace-rollback-job.yaml`.

**Risk-of-being-wrong:** HIGH **operational** risk: nodes must not stay down > 3 days after this lands or repaired data may resurrect. **Document in PR description as a hard ops constraint.**

---

### `PR-HF-19` — Migrate dashboards to per-CM sidecar discovery + CI size check

- **Branch:** `operability/grafana-dashboard-sidecar`
- **Files touched:** rename `*-grafana-dashboard.yaml` to add label `grafana_dashboard: "1"`, helmfile.yaml hook removal, new CI step
- **LoC budget:** ~30
- **Depends-on:** none
- **Axis:** Operability
- **Severity:** MED

**Patch — add sidecar label to each dashboard CM:**
```diff
 apiVersion: v1
 kind: ConfigMap
 metadata:
   name: cassandra-grafana-dashboard
+  labels:
+    grafana_dashboard: "1"
```

**Patch — Grafana chart values (in helmfile.yaml grafana block):**
```diff
         grafana:
           enabled: true
+          sidecar:
+            dashboards:
+              enabled: true
+              label: grafana_dashboard
+              labelValue: "1"
+              folder: /tmp/dashboards
```

**Patch — drop the merge-into-default-CM postsync hook (the sidecar replaces it).**

**Patch — CI step (`.bitbucket-pipelines.yml` or equivalent):**
```yaml
- step:
    name: dashboard-size-check
    script:
      - |
        find atlassian_packages/gcp_kitt/helmfile -name '*-grafana-dashboard.yaml' \
          -exec wc -c {} + \
          | awk '$1 > 800000 { print "FAIL: "$0; exit 1 }'
```

**Acceptance:**
```bash
# Each dashboard CM independently below 800KB
find atlassian_packages/gcp_kitt/helmfile -name '*-grafana-dashboard.yaml' \
  -exec wc -c {} + | awk '$1 > 800000 { exit 1 }' && echo PASS
# Grafana sidecar logs show pickup
kubectl -n temporal logs -l app.kubernetes.io/name=grafana -c grafana-sc-dashboard --tail=20 \
  | grep -i 'pulling\|added' | wc -l | awk '$1 > 0 { exit 0 } { exit 1 }'
```

**Rollback:** `git revert <sha>` and re-add merge-into-default-CM hook.

**Risk-of-being-wrong:** MED. Sidecar key conventions vary by Grafana chart version. **Pre-merge:** `helm show values temporal/temporal | grep -A 6 sidecar.dashboards`.

---

## T3 — POLISH

### `PR-HF-20` — Delete commented-out cassandra-exporter-sidecar block

- **Branch:** `chore/cassandra-exporter-cleanup`
- **Files touched:** `helmfile.yaml` (~25 lines deleted), delete `cassandra-exporter-sidecar-fix.yaml`, new `cassandra-metrics-exporter-summary.md` (~50 lines)
- **LoC budget:** −25 source / +50 docs
- **Depends-on:** none
- **Axis:** Operability
- **Severity:** MED

**Patch:**
```diff
@@ helmfile.yaml lines 385-391 @@
-      # Alternative: Add exporter as sidecar to Cassandra pods (DISABLED - using separate deployment instead)
-      # - events: ["postsync"]
-      #   showlogs: true
-      #   command: kubectl
-      #   args:
-      #     - apply
-      #     - -f
-      #     - cassandra-exporter-sidecar-fix.yaml
```
Plus `git rm cassandra-exporter-sidecar-fix.yaml`.

Plus new `cassandra-metrics-exporter-summary.md` documenting the deployment-only path.

**Acceptance:**
```bash
[ ! -f atlassian_packages/gcp_kitt/helmfile/cassandra-exporter-sidecar-fix.yaml ] && \
  ! grep -n cassandra-exporter-sidecar-fix atlassian_packages/gcp_kitt/helmfile/helmfile.yaml && \
  [ -f atlassian_packages/gcp_kitt/helmfile/cassandra-metrics-exporter-summary.md ] && echo PASS
```

**Rollback:** `git revert <sha>`

**Risk-of-being-wrong:** LOW (pure cleanup).

---

### `PR-HF-22` — Add Prom alert: Cassandra native-transport thread saturation

- **Branch:** `observability/cassandra-thread-pool-alert`
- **Files touched:** new `cassandra-prometheus-rules.yaml`
- **LoC budget:** +30
- **Depends-on:** Cassandra metrics-exporter scrape proven via Grafana
- **Axis:** Reliability + Latency
- **Severity:** MED

**Patch:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata: { name: cassandra-rules, namespace: temporal }
spec:
  groups:
    - name: cassandra.thread-pools
      rules:
        - alert: CassandraNativeTransportSaturating
          expr: |
            cassandra_thread_pools_active_tasks{pool_name="Native-Transport-Requests"}
              / on() group_left
            cassandra_thread_pools_max_pool_size{pool_name="Native-Transport-Requests"}
            > 0.8
          for: 5m
          labels: { severity: warning }
          annotations:
            summary: "Cassandra native-transport thread pool >80% used"
            description: |
              Sustained >80% usage of native-transport threads on {{ $labels.instance }}.
              Risk: Temporal RPC tail-latency spikes. Consider raising
              `native_transport_max_threads` (default 128) or reducing Temporal
              `connectionsPerHost` (default 2).
        - alert: CassandraReadLatencyHigh
          expr: histogram_quantile(0.99, sum(rate(cassandra_read_latency_seconds_bucket[5m])) by (le)) > 0.05
          for: 10m
          labels: { severity: warning }
          annotations:
            summary: "Cassandra p99 read latency > 50ms"
```

**Wire into helmfile.yaml hooks (via HF-14 wrapper):**
```diff
+      - events: ["postsync"]
+        showlogs: true
+        command: bash
+        args: [scripts/apply-and-verify.sh, cassandra-prometheus-rules.yaml]
```

**Acceptance:**
```bash
kubectl get prometheusrule -n temporal cassandra-rules -o name | grep -q cassandra-rules && echo PASS
# In Grafana / Prom UI, the alert evaluates without errors:
curl -s "$PROM/api/v1/rules" | jq '.data.groups[].rules[] | select(.name=="CassandraNativeTransportSaturating") | .health' | grep -q ok
```

**Rollback:** `kubectl delete prometheusrule cassandra-rules -n temporal`

**Risk-of-being-wrong:** LOW. Alert rules are idempotent; bad expression is caught by Prometheus on reload.

---

## Summary table — every PR at a glance

| PR | Tier | LoC | Files | Single-command rollback |
|---|---|---|---|---|
| `PR-HF-06` | T0 | −80, +15 | 3 | re-create file from secret store (no git revert; security action) |
| `PR-HF-11` | T0 | +12 | 1 | `git revert <sha>` |
| `PR-HF-07` | T0 | −63, +5 | 1–2 | `git revert <sha>` |
| `PR-HF-05` | T0 | ±40, +100 docs | 3 | `helm rollback temporal <prev>` |
| `PR-HF-01` | T0 | +80 | 1 | `helm rollback temporal <prev>` |
| `PR-HF-03` | T0 | ±0 | 1–2 | `git revert <sha>` |
| `PR-HF-02` | T0 | +75 | 2 | `kubectl delete -f temporal-pdbs.yaml` |
| `PR-HF-08` | T1 | +12 | 1 | `git revert <sha>` |
| `PR-HF-09` | T1 | −300, +60 | 3 | `git revert <sha>` |
| `PR-HF-04` | T1 | ±12 | 1–2 | `helm rollback temporal <prev>` |
| `PR-HF-15` | T1 | +60 | 2 | `kubectl delete networkpolicy cassandra-jmx-restrict -n temporal` |
| `PR-HF-10` | T1 | +120 + 5 | 2–3 | restore prior ScaledObject yaml |
| `PR-HF-14` | T1 | +130 | 2 | `git revert <sha>` |
| `PR-HF-12` | T1 | +50 | 17 | `git revert <sha>` |
| `PR-HF-17` | T1 | +50 | 2 | `git revert <sha>` + delete ILM policy |
| `PR-HF-13` | T2 | ±9 | 9 | `git revert <sha>` |
| `PR-HF-16` | T2 | +10 | 1–2 | `helm rollback temporal <prev>` |
| `PR-HF-18` | T2 | +10 | 1 | `git revert <sha>` |
| `PR-HF-21` | T2 | +35 | 2 | apply rollback Job |
| `PR-HF-19` | T2 | +30 | 5+ | `git revert <sha>` |
| `PR-HF-20` | T3 | −25, +50 | 3 | `git revert <sha>` |
| `PR-HF-22` | T3 | +30 | 1 | `kubectl delete prometheusrule cassandra-rules -n temporal` |

**Total LoC delta across all 22 PRs: ~+800 (excluding −300 deletion in HF-09).**
**Total wall-clock estimate: 2 weeks (T0+T1) + 1 week (T2) + opportunistic (T3).**

