# Goals & Metrics — what every plan item must move

## 1. The driver goal (business)

**Proactive AI Platform (PAI) FY26 H2 OKR:** scale AI invocations **400K → 1.5M per month** (3.75× growth).

Source: `atlassian_packages/proactive-ai-platform/PERFORMANCE_INVESTIGATION_FY26H2_OKR.md` (executive summary, Findings 1–8). PAI's worker pool, async tasks, and AI-Gateway pipeline directly run on top of gcp_kitt-managed compute (DTE workers, scraper, kitt-runbooks). Therefore gcp_kitt has to:

1. **Not be the bottleneck** when PAI's per-cluster QPS triples.
2. **Not be a cost multiplier** — every wasted CPU-second / Splunk MB / Kinesis PUT is multiplied 3.75×.
3. **Not regress reliability** — even a 0.1% increase in workflow failure becomes a daily incident at 50K/day.

## 2. Concrete metrics (the four-axis dashboard)

Every plan item lists which of these it moves and by how much.

### 2.1 Throughput
- **`dte_workflows_completed_per_min`** (Temporal): need ≥3.75× headroom over today.
- **`scraper_urls_processed_per_sec`**: drives PAI knowledge freshness.
- **`controller_reconciles_per_sec`** (forgeapp, sweeper): cluster-density ceiling.
- **`k8s_api_qps_consumed`** by gcp_kitt components: must stay below 30% of cluster apiserver QPS budget.

### 2.2 Latency
- **`auth_provider_token_exchange_p95_ms`** — currently uncached, ~200–500 ms; target <50 ms (cache hit).
- **`activity_execution_duration_seconds_{p50,p95,p99}`** by activity_type — currently no histogram.
- **`forgeapp_reconcile_duration_p95_ms`** — currently includes 5 Status().Update calls; target halved.
- **`runbook_workflow_duration_p95_seconds`** — MTTR proxy.

### 2.3 COGS (the cost axis)
- **K8s API server CPU / cluster** (apiserver-side cost of our List calls).
- **Splunk ingest GB/day** from gcp_kitt namespaces (ingest = ~$3–5/GB internally).
- **Kinesis `PutRecord` count** for k8s-metadata-collector (cost = $0.014 / 1M records).
- **Compute CPU-hours / month** for workers (auth re-handshake = wasted CPU).
- **Per-cluster steady-state idle compute** of operators.

### 2.4 Reliability
- **Workflow success rate** (Temporal): scraper, dte, runbooks.
- **Reconcile error rate** (forgeapp, sweeper).
- **Pod restart count** for `k8s-metadata-collector` (currently `log.Fatalf` on transient errors → hard restart).
- **Drift / divergence** between `amp/*` and `helmfile/dte/*` copies (we'll add CI assertion).

## 3. The ranking rubric — how we score every plan item

We use a deliberately simple weighted score so rankings are transparent and reproducible:

```
score = (Impact_throughput * 1.0
       + Impact_latency    * 1.0
       + Impact_cost       * 1.5
       + Impact_reliability* 1.0)
       * Confidence
       / (Effort_days * RiskFactor)

# Each Impact_x ∈ {0, 1 (small), 3 (medium), 9 (large), 27 (huge)}
# Confidence ∈ [0.4, 1.0]
# RiskFactor: L=1, M=1.5, H=2.5
```

Why **Cost is weighted 1.5×**: PAI's budget for compute/Splunk/Kinesis at 1.5M/mo is the literal headline ask in the COGS investigation; 100% of CFO-visible savings track here.

## 4. Hard constraints (don't break)

These come directly from the user's instructions and from reading recent git history:

1. **Don't change user-facing behavior.** Examples:
   - Don't change ranking from "recency" → "relevance" anywhere.
   - Don't reduce log fidelity in `kitt-runbooks` cordon flow blindly — recent +400 lines of logs were added on purpose for SRE debugging. We'll *level* them, not delete them.
2. **Respect recent decisions.** The last 3 months added:
   - TLS for Temporal (`b879784`, `5b66c9c`) → any pooling refactor must keep TLS config intact.
   - `slauth-token` group caching (`00170e6`, `1d0fd4f`, `4ff93c1`) → token-cache work must EXTEND not collide with this.
   - Group-aware auth provider requests (`fdfade1`, `f08c3fd`) → any token-cache key must include the groups dimension.
3. **Refactor PRs must be small enough to review.** No PR > ~600 LoC change unless it's a pure file move + import-rewrite that a reviewer can scan diff-statically.
4. **No data-format breakage.** Kinesis schema, Temporal payloads, Splunk fields are downstream-consumed and must stay bytes-equivalent unless the change is explicitly versioned.

## 5. What "done" looks like for each tier

| Tier | Definition of done |
|---|---|
| **P0** | Merged + canary-rolled to one prod cluster + a metric chart exists showing the predicted improvement |
| **P1** | Merged + observed in staging dashboards |
| **P2** | Merged with unit tests; observed locally |
| **P3** | Documented in this `_plan` directory + first PR opened |
