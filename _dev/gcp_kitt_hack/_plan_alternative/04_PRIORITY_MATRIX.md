# Priority Matrix, PR Strategy & Implementation Roadmap

> **Ranking Method**: Each finding is scored on 3 axes weighted by business/technical goal impact:
> - **Crash Elimination** (40%): Direct reduction in service crashes / restarts
> - **Measurable Gain** (30%): Quantifiable improvement in throughput, latency, resource usage
> - **Implementation Risk** (30%): Inverse of effort/risk (higher score = lower risk = do first)

---

## 1. Unified Priority Ranking

| Rank | ID | Finding | Crash % | Measurable Impact | Effort | Composite | Tier |
|------|-----|---------|---------|-------------------|--------|-----------|------|
| 1 | **S1** | Temporal Client Leak | 30% | 99.97% fewer gRPC conns | 2h | **9.5** | 🔴 P0 |
| 2 | **S2** | Prometheus Cardinality | 25% | 99.97% fewer time series | 4h | **9.2** | 🔴 P0 |
| 3 | **P5** | API Server Client Singleton | 5% | Eliminates leak in API process | 1h | **8.8** | 🔴 P0 |
| 4 | **S3** | Redis Connection Recovery | 10% | Auto-recovery from Redis outage | 1h | **8.5** | 🔴 P0 |
| 5 | **D1** | K8s Client Timeouts | 10% | Eliminates goroutine leak | 2h | **8.3** | 🔴 P0 |
| 6 | **S4** | DB Pool Acquisition Timeout | 5% | Prevents indefinite blocks | 2h | **8.0** | 🟠 P1 |
| 7 | **P1** | N+1 Query Batching | 20%* | 99.6% fewer DB round-trips | 1.5d | **7.8** | 🟠 P1 |
| 8 | **D2** | Graceful Shutdown + Drain | 10% | Zero orphaned activities on deploy | 4h | **7.5** | 🟠 P1 |
| 9 | **P2** | aiohttp Migration | 15%* | +40-55% throughput; reliable health | 1w | **6.6** | 🟡 P2 |
| 10 | **D3** | Silent Token Parse Failures | 2% | Faster auth debugging | 1h | **5.5** | 🟡 P2 |
| 11 | **P3** | URL Normalization Cache | 0% | 60-80% CPU reduction on normalize | 0.5h | **5.0** | 🟡 P2 |
| 12 | **P4** | Batch Redis Work Set Insert | 0% | ~90% fewer Redis round-trips | 2h | **4.8** | 🟡 P2 |
| 13 | **D5** | Client Graceful Shutdown | 1% | Clean Temporal client cleanup | 1h | **4.5** | ⚪ P3 |
| 14 | **D4** | HTTP os.Exit in Goroutine | 1% | Proper cleanup on HTTP error | Fixed by D2 | — | ⚪ P3 |

*P1 and P2 indirectly prevent crashes by reducing pool/thread pressure that causes cascading failures.

---

## 2. Tier Definitions

### 🔴 Tier P0 — "Stop the Bleeding" (Week 1)
> **Goal**: Eliminate the top crash vectors. Each fix is small, low-risk, high-impact.

These 5 fixes address **~80% of all crashes** with **<1 day total engineering effort**:

- **S1** (2h): Fix Temporal client leak → stops FD exhaustion crash
- **S2** (4h): Fix metrics cardinality → stops Prometheus OOM
- **P5** (1h): Fix API client singleton → stops API server leak
- **S3** (1h): Fix Redis reconnection → survives Redis restarts
- **D1** (2h): Add K8s timeouts → prevents goroutine deadlock

**Expected outcome**: Crash rate drops from multiple/week to near-zero.

### 🟠 Tier P1 — "Structural Fixes" (Week 2-3)
> **Goal**: Eliminate remaining crash conditions and unlock efficiency gains.

- **S4** (2h): DB pool timeout → converts silent hang to actionable error
- **P1** (1.5d): N+1 batching → 99.6% DB round-trip reduction + pool pressure relief
- **D2** (4h): Graceful shutdown → zero orphaned activities during deployments

**Expected outcome**: Service handles 5-10× load without pool exhaustion.

### 🟡 Tier P2 — "Throughput & Efficiency" (Week 4-6)
> **Goal**: Major throughput gains for scale.

- **P2** (1w): aiohttp migration → +40-55% throughput, reliable health checks
- **D3** (1h): Token parse logging → faster incident debugging
- **P3** (0.5h): URL normalization cache → 5-10% activity speedup
- **P4** (2h): Redis batch insert → 90% fewer Redis round-trips

### ⚪ Tier P3 — "Hygiene" (Opportunistic)
> **Goal**: Code quality improvements, addressed alongside other work.

- **D5**: Client graceful shutdown
- **D4**: HTTP os.Exit fix (covered by D2)

---

## 3. PR Strategy — Detailed Sequence

### Week 1: P0 Crash Fixes (5 PRs, each independently reviewable and deployable)

```
PR #1: [S1] Fix Temporal client connection leak
  Files: worker.py
  Lines changed: ~30
  Reviewer focus: Verify singleton lifecycle, no double-close
  Deploy: Can deploy independently, instant impact
  Rollback: Safe — worst case reverts to current behavior

PR #2: [S2] Fix Prometheus metrics cardinality
  Files: metrics.py, worker.py, redis_utils.py
  Lines changed: ~100
  Reviewer focus: Verify bounded label set, check Grafana dashboard queries
  Deploy: ⚠️ Coordinate with dashboard update
  Rollback: Safe — old dashboards will show "no data" but service stable

PR #3: [P5] Fix API server Temporal client singleton  
  Files: api_server.py
  Lines changed: ~10
  Reviewer focus: Trivial — just implement the TODO
  Deploy: Independent
  Rollback: Safe

PR #4: [S3] Add Redis connection health check
  Files: redis_utils.py
  Lines changed: ~15
  Reviewer focus: Verify ping() doesn't add significant latency
  Deploy: Independent
  Rollback: Safe

PR #5: [D1] Add K8s client timeouts
  Files: helpers.go
  Lines changed: ~15
  Reviewer focus: Verify timeout values are appropriate (30s overall, 10s TCP)
  Deploy: Independent
  Rollback: Safe
```

### Week 2-3: P1 Structural Fixes (4 PRs)

```
PR #6: [S4] Add DB pool acquisition timeout
  Files: db_utils.py
  Lines changed: ~20
  Deploy: Independent

PR #7: [P1a+P1b] Add batch check functions (db_utils + redis_utils)
  Files: db_utils.py, redis_utils.py
  Lines changed: ~40
  Note: Pure additions — no existing code modified. Add tests.
  Deploy: No behavioral change until PR #8

PR #8: [P1c] Refactor process_url_activity to use batch checks
  Files: worker.py
  Lines changed: ~50
  Depends on: PR #7 merged
  Reviewer focus: Verify same semantics (visited + work_set checks identical)
  Deploy: This is where the 99.6% DB reduction takes effect

PR #9: [D2a+D2b] Graceful shutdown with drain period
  Files: main.go, Helm values
  Lines changed: ~50
  Reviewer focus: Signal handling, drain timeout, no goroutine leak
  Deploy: Test in staging with simulated rolling update
```

### Week 4-6: P2 Throughput (4 PRs)

```
PR #10: [P2a] Add async fetch_url_async (alongside sync version)
  Files: scraper_utils.py
  Lines changed: ~50
  Note: Pure addition — sync fetch_url unchanged

PR #11: [P2b] Migrate process_url_activity to fetch_url_async
  Files: worker.py
  Lines changed: ~20
  Depends on: PR #10

PR #12: [P3+P4] URL normalization cache + batch Redis insert
  Files: scraper_utils.py, redis_utils.py, worker.py
  Lines changed: ~30
  Note: Small, self-contained optimizations bundled together

PR #13: [D3] Token parsing error logging
  Files: helpers.go
  Lines changed: ~20
```

---

## 4. Risk Assessment

### What We're NOT Changing (Important)

| Area | Why Not |
|------|---------|
| Scraping logic (domains, links, images) | User-facing behavior — no change |
| URL normalization logic (http→https, fragment removal) | Deterministic, well-tested |
| Redis data structures (work sets, processing sets) | Working correctly, just accessing more efficiently |
| Temporal workflow orchestration (ScraperWorkflow, MonitoringWorkflow) | Complex, well-tested, no issues found |
| KEDA autoscaling configuration | Already well-tuned (targetQueueSize=50, maxReplicas=100) |
| DTE workflow logic (health-check, service-discovery) | No bugs found in business logic |

### Git History Cross-Check

Recent commits show active work on:
- TLS for Temporal connections (`b879784`, `5b66c9c`) — our fixes don't conflict
- Auth provider logging (`e7ad846`, `6472402`) — D3 complements this work
- Connection error fixes (`1b1c279`, `d350db7`) — our S1/S3 are more comprehensive versions

No recent commits removed caching or changed patterns we're proposing to modify. Safe to proceed.

---

## 5. Measurement Plan

### Before Starting (Baseline)

Capture these metrics for 1 week before any changes:
1. **Pod restart count** per service (kubectl: `restartCount`)
2. **Prometheus time series count**: `count({__name__=~"scraper_.*"})`
3. **Open file descriptors**: `process_open_fds` per worker pod
4. **DB connection pool utilization**: Add temporary logging
5. **Activity success/failure rate**: Temporal UI or `temporal_activity_execution_failed_total`

### After Each Tier

| Tier | Expected Change | How to Measure |
|------|----------------|----------------|
| P0 (Week 1) | Pod restarts → 0; FD stable; Prom series < 200 | K8s metrics + Prometheus self-monitoring |
| P1 (Week 2-3) | DB query count 99.6% lower; no pool timeouts | PostgreSQL `pg_stat_statements` + app logs |
| P2 (Week 4-6) | Throughput +40-55%; thread pool empty | Activity duration histograms + thread metrics |

### Success Criteria

| Metric | Target |
|--------|--------|
| Pod restarts per week | 0 (from current multiple) |
| Service availability | ≥99.5% (from ~95-98%) |
| Mean time to recovery | <1 minute (from hours — graceful shutdown) |
| DB round-trips per activity | ≤5 (from ~500) |
| Prometheus scraper series | <200 (from ~500K) |
| Open FDs per worker | Stable ≤50 (from unbounded growth) |

---

## 6. Innovation Opportunity: Adaptive Batch Sizing

Beyond the core fixes, one innovative optimization worth considering for a future iteration:

**Problem**: The `processingBatchSize` (currently 100) and `maxUrlsPerFetch` (currently 500) are static. Under low load, large batches waste memory. Under high load, small batches cause too many workflow tasks.

**Proposal**: Adaptive batch sizing based on work queue depth:

```python
# In workflow.py — process_urls_as_activities()
work_count = get_work_count(job_id, root_url)
if work_count > 1000:
    batch_size = 200  # Large backlog — big batches for efficiency
elif work_count > 100:
    batch_size = 50   # Medium backlog — balanced
else:
    batch_size = 10   # Small backlog — small batches for responsiveness
```

**Impact**: Better resource utilization under varying load. ~20-30% efficiency gain during burst traffic.

**Risk**: Adds workflow complexity. Only implement after P0+P1 are stable.

**This is NOT in the current plan** — it's a future consideration after stability is achieved.

---

*End of Priority Matrix & Roadmap*
