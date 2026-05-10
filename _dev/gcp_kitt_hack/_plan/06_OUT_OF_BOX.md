# Out-of-Box / Strategic Refactor Proposals

> Reserved for **larger-effort** ideas that require a real business case. Each proposal lists the **cost**, the **expected gain**, the **alternative** (do-nothing or smaller fix), and a **PR sequencing plan** (because no large refactor should ever land in one PR).

---

## OOB-1 — Extract `pkg/dte` shared Go module (kill the amp/* ↔ helmfile/dte/* fork)

### Why it's worth doing
- Verified divergence: `helpers.go` differs by **only 12 lines** between copies, `client/main.go` by **100 lines**. The fork is recent and small — *now* is the cheapest moment.
- Every P0/P1 fix in §03 currently has to be applied **twice**. Eliminating the fork halves the maintenance cost permanently.
- Future refactors (token cache, observability) become 2× cheaper to ship.

### Cost
- ~4 weeks elapsed; ~3 weeks engineer time across 4 PRs.
- One full regression cycle on both deployment envs.

### Expected measurable gain
- Eng overhead: −10–15 % per change going forward.
- Reduces **silent-divergence risk** (currently one bug fix could ship to only one copy and go unnoticed for months).
- Indirect: makes the `pkg/clusterauth` proposal (OOB-2) trivial.

### Alternative (do-nothing)
- Keep the CI fence (PR-PHASE0-04) — protects against new drift, but doesn't pay back the maintenance tax.

### PR sequence (each fully reviewable on its own)

#### `PR-OOB-01` Create `pkg/dte` skeleton (no functional change)
- Branch: `refactor/dte-pkg-skeleton`
- Adds new Go module `pkg/dte` with empty `helpers/`, `cluster_db/`, `client/` packages and `go.mod`.
- Copies the **canonical** version of each file (we'll pick `helmfile/dte/` as canonical because it's newer per the diff).
- Adds CI build step that compiles `pkg/dte` standalone.
- LoC: pure file-add + module-init.

#### `PR-OOB-02` Migrate `amp/distributed-{worker,client}` to import `pkg/dte`
- Branch: `refactor/amp-uses-pkg-dte`
- Replaces in-tree files with `import "atlassian/gcp_kitt/pkg/dte/..."` calls; the `main.go` shrinks to a thin entry-point.
- Removes (now-stale) duplicate files from `amp/`.
- Acceptance: same binary behaviour; CI passes; canary in dev.

#### `PR-OOB-03` Migrate `helmfile/dte/distributed-{worker,client}` to import `pkg/dte`
- Branch: `refactor/helmfile-uses-pkg-dte`
- Same as OOB-02 but on the helmfile copy. After this PR there is **only one** copy of helpers/cluster_db/client logic.

#### `PR-OOB-04` Decommission CI drift fence
- Branch: `chore/dte-drift-fence-remove`
- Removes the `scripts/check-dte-drift.sh` step (PR-PHASE0-04). It's no longer needed because there are no twins to drift.

---

## OOB-2 — Extract `pkg/clusterauth` (one source of truth for cluster client + token cache)

### Why it's worth doing
- The same auth pattern lives in **three** places today:
  - `amp/distributed-worker/helpers.go` (PR-A1/A2 will fix in-place)
  - `helmfile/dte/distributed-worker/helpers.go` (mirror)
  - `kitt-runbooks/internal/k8sclient/client.go` (PR-E1 will fix in-place)
- After OOB-1 lands, the DTE side is one copy. Adding kitt-runbooks to the same library means **one** token-cache implementation, one set of metrics, one bug-fix surface.

### Cost
- 2 weeks after OOB-1 lands.

### Expected measurable gain
- The slauth-token group caching work (recent `00170e6`, `1d0fd4f`, …) now has a single home — future improvements ship once.
- Single Prom metric `clusterauth_token_cache_hit_ratio` works for both DTE and kitt-runbooks dashboards.

### PR sequence

#### `PR-OOB-05` Create `pkg/clusterauth` from `pkg/dte/helpers.go::getClusterTokenFromAuthProvider`
- Branch: `refactor/clusterauth-extract`
- Pure file-move + interface definition (`type Authenticator interface { TokenFor(ctx, ClusterRef) (Token, error) }`).
- LoC: ~400 (move + interface).

#### `PR-OOB-06` Migrate `kitt-runbooks/internal/k8sclient` to use `pkg/clusterauth`
- Branch: `refactor/runbooks-uses-clusterauth`
- Removes the (smaller) duplicate auth code in `kitt-runbooks`; uses `clusterauth.Authenticator` interface.
- LoC: ~200.

---

## OOB-3 — Decommission `deploy/python/pod_label_sweeper.py`

### Why it's worth doing
- `pod_label_sweeper.py` (562 lines, Python) and `sweeper/controllers/sweeper_controller.go` (208 lines, Go controller) both implement pod label-stamping. Two systems for one job.
- The Go operator is more efficient (informer-driven), can hot-react, and shares the cluster's RBAC. Python script does a one-shot `for ns: for pod: patch` walk — slow and not real-time.

### Cost
- 1 week investigation (find any cron/Lambda that calls it), then ~3 days code change.

### Expected measurable gain
- Removes 562 LoC; consolidates ownership; eliminates auth + RBAC duplication for the sweeper.

### PR sequence

#### `PR-OOB-07` Audit doc — list every consumer of `pod_label_sweeper.py`
- Branch: `docs/podlabelsweeper-decom-plan`
- A `DEPRECATION_PLAN.md` listing every cron/job/script that invokes it, with cutover date.

#### `PR-OOB-08` Remove Python script + redirect docs to operator
- Branch: `chore/remove-python-podlabelsweeper`
- Only after OOB-07 is signed off and operator coverage is verified per-cluster.

---

## OOB-4 — Scraper Python ↔ JS unification (the harder one)

### Why it's worth doing
- Maintaining two scraper runtimes for the same workflow doubles bug-surface and divides the team's attention.
- B8 already shows divergence in retry/skip semantics — concrete reliability cost.

### Cost
- 6–10 weeks elapsed; significant business decision (which runtime wins?).

### Expected measurable gain
- −50 % maintenance; consistency wins; future Temporal SDK upgrades happen once.

### PR sequence (non-trivial)

#### `PR-OOB-09a` Decision doc with recommendation
- Branch: `docs/scraper-runtime-decision`
- Compare: cold-start, memory footprint, lib ecosystem, current production share-of-traffic. Output: pick one.

#### `PR-OOB-09b..f` Cutover sequence (separate PR per module)
- Workflow runtime; Activities; Redis utils; DB utils; HTTP fetch — each migrated separately so any single PR can be reverted.

---

## OOB-5 — Replace scraper polling-loop dispatch with Temporal-signal-driven dispatcher

### Why it's worth doing
- B12 finding: workflow polls `get_urls_to_process_activity` every 2-5 s even when the work_count is 0 → 10 % worker waste in low-throughput periods.
- A signal-driven design lets the API/queue producer **wake** the dispatcher when the work-set transitions from empty → non-empty.

### Cost
- 1 week design; 2 weeks code; needs careful Temporal versioning.

### Expected measurable gain
- 10 % worker pod-hours saved at low load; smoother scale-down on KEDA; lower idle AI Gateway warm-pool cost.

### PR sequence

#### `PR-OOB-10a` Add `WorkAvailable` signal handler to scraper workflow
- Branch: `feat/scraper-workavailable-signal`

#### `PR-OOB-10b` Add publisher in API server / Redis-watcher
- Branch: `feat/scraper-workavailable-publisher`

#### `PR-OOB-10c` Switch dispatcher from poll → signal+timeout-fallback
- Branch: `feat/scraper-dispatcher-signal`
- Keeps a 30 s safety-net poll so we degrade gracefully if signals are dropped.

---

## OOB-6 — Innovative: a single "GitOps-rendered observability fabric"

### Why it's worth doing
- We're proposing histograms in §02-E1 across several services. Doing this **once**, in a shared `pkg/observability`, instead of N times, locks in a consistent label set: `service, cluster, activity, result, latency_bucket`. Grafana dashboards then become **template-once, instantiate-many**.

### Cost
- 1 week, mostly design.

### Expected gain
- Every future service onboarded to `pkg/observability` gets a dashboard for free.
- One canonical place to define **SLOs**.

---

## Strategic theme

> The unifying message of OOB-1 → OOB-2 → OOB-6: **gcp_kitt has converged on a small set of shared concerns** (cluster auth, k8s client lifecycle, Prom metrics) that are now duplicated across binaries because the repo grew organically. Investing in 3 small, focused **shared packages** (`pkg/dte`, `pkg/clusterauth`, `pkg/observability`) over the next 8–12 weeks pays back permanently — every future PAI scale-up amplifies the savings.

This is the kind of "out-of-box" structural change that wouldn't be obvious from looking at any one file, but is staring at us when you read `diff -q amp/.../helpers.go helmfile/dte/.../helpers.go` (12 lines) and `kitt-runbooks/internal/k8sclient/client.go` side-by-side.
