# Scraper Service — Stability Fixes (S1–S4)

> **Service**: `scraper/temporal-pg-redis/` — Python async Temporal worker + Flask API
> **Goal**: Eliminate all crash vectors. Target: zero unplanned restarts.

---

## S1: Temporal Client Connection Leak (Critical — ~30% of crashes)

### Problem

In `worker.py`, `Client.connect()` is called at **4 separate locations** (lines 617, 930, 1145, 1330), each creating a brand-new gRPC connection to the Temporal server. These connections are **never closed** — the comment "Temporal Client manages its own lifecycle" is incorrect; `Client.connect()` creates a new connection every time.

**Affected functions:**
- `get_workflow_pending_activities_activity()` — line 617 (called every 30s by MonitoringWorkflow)
- `check_stuck_activities_activity()` — line 930
- `get_pending_activities_count()` — line 1145 (called on every /metrics request)
- `requeue_timed_out_items_activity()` — line 1330

**Quantified impact:**
- MonitoringWorkflow runs every 30s → 2 connections/minute (pending + stuck check)
- /metrics scraped every 30s → 2 connections/minute
- **~5,760 leaked gRPC connections/day per worker pod**
- Each gRPC connection ≈ 2 file descriptors + ~250KB memory
- Default FD limit (1024) exhausted in ~8.5 hours → **guaranteed crash**

### Root Cause

```python
# worker.py line 617 — inside get_workflow_pending_activities_activity()
client = await Client.connect(
    f"{temporal_host}:{temporal_port}",
    namespace=temporal_namespace,
)
# ... used, then falls out of scope. Never closed.
```

The worker's `main()` already creates a persistent `Client.connect()` at line ~1330 and passes it to the `Worker` constructor. But activity functions create their own connections instead of reusing the worker's client.

### Fix

**Approach**: Use a module-level singleton Temporal client, initialized once in `main()` and reused by all activities.

```python
# worker.py — module level
_temporal_client: Optional[Client] = None

async def get_temporal_client() -> Client:
    """Get the shared Temporal client (initialized in main())."""
    global _temporal_client
    if _temporal_client is None:
        temporal_host = os.environ.get('TEMPORAL_HOST', 'temporal-frontend.temporal.svc.cluster.local')
        temporal_port = int(os.environ.get('TEMPORAL_PORT', '7233'))
        temporal_namespace = os.environ.get('TEMPORAL_NAMESPACE', 'default')
        _temporal_client = await Client.connect(
            f"{temporal_host}:{temporal_port}",
            namespace=temporal_namespace,
        )
    return _temporal_client

async def main():
    global _temporal_client
    # ... existing connection code ...
    _temporal_client = client  # Set the singleton
    # ... rest of main() ...
```

Then replace all 4 `Client.connect()` calls with `client = await get_temporal_client()`.

**Why not `activity.info().client`?** The Temporal Python SDK does not expose the worker's client via activity context. A module-level singleton is the idiomatic solution.

### Impact

| Metric | Before | After |
|--------|--------|-------|
| gRPC connections/day | ~5,760 leaked | 1 persistent |
| Memory leak | ~1.4GB/day | 0 |
| FD exhaustion crash | Every ~8.5 hours | Never |

### PR Strategy

**PR S1**: "Fix Temporal client connection leak — use singleton client"
- Scope: `worker.py` only
- ~30 lines changed
- Risk: Low (behavioral no-op — same queries, same results)
- Test: Verify FD count stable over 1 hour under load

---

## S2: Prometheus Metrics Cardinality Explosion (Critical — ~25% of crashes)

### Problem

All 9 Prometheus metrics in `metrics.py` use **unbounded labels**: `job_id` and `root_url`.

```python
# metrics.py — every metric has these high-cardinality labels
urls_added_total = Counter('scraper_urls_added_total', '...', ['job_id', 'root_url'])
urls_requeued_total = Counter('scraper_urls_requeued_total', '...', ['job_id', 'root_url'])
url_processing_duration_seconds = Histogram('...', '...', ['job_id', 'root_url'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0))
# 11 buckets + _sum + _count = 13 series per unique (job_id, root_url)
```

**Quantified impact:**
- 100 jobs × 50 root_urls = 5,000 unique label combinations
- 9 metrics × 5,000 combinations = 45,000 base series
- 2 Histograms × 13 (11 buckets + sum + count) × 5,000 = 130,000 histogram series
- **Total: ~175,000+ time series** (and growing — Counters never expire)
- Prometheus default memory: ~1–2KB per series → **175–350MB** just for scraper metrics
- This is **cumulative**: label combos from old jobs never get cleaned up

The `pending_activities_gauge` (metric 9) is even worse — it uses `job_id`, `workflow_id`, `run_id`, AND `type` as labels. Each workflow run creates unique series that persist forever.

### Fix

**Replace unbounded labels with bounded, operationally useful labels:**

```python
# BEFORE (unbounded):
urls_added_total = Counter('scraper_urls_added_total', '...', ['job_id', 'root_url'])

# AFTER (bounded):
urls_added_total = Counter('scraper_urls_added_total', '...', ['activity_name'])
# Or remove labels entirely for aggregate metrics:
urls_added_total = Counter('scraper_urls_added_total', '...')
```

**Design:**
1. Remove `job_id` and `root_url` from all metric labels
2. Keep `activity_name` label (bounded: 5 known activity types)
3. For per-job tracking, use structured logging (already in place) — query via log aggregation
4. For `pending_activities_gauge`, use only `type` label (bounded: ~5 activity types)

### Impact

| Metric | Before | After |
|--------|--------|-------|
| Time series count | ~175,000+ (growing) | ~50–100 (fixed) |
| Prometheus memory for scraper | ~175–350MB | <1MB |
| Series growth rate | Unbounded | Zero (fixed label set) |
| OOM risk | High | None |

### PR Strategy

**PR S2**: "Fix Prometheus metrics cardinality — remove unbounded labels"
- Scope: `metrics.py` + all callers in `worker.py`, `redis_utils.py`
- ~100 lines changed (mostly removing label arguments from function calls)
- Risk: **Dashboard breakage** — existing Grafana dashboards querying by `job_id` will need updating
- Mitigation: Update dashboards in same PR; add deprecation period if needed
- Test: Verify `/metrics` endpoint returns bounded series count

---

## S3: Redis Connection — Broken Singleton Recovery (High)

### Problem

In `redis_utils.py`, the Redis client is a module-level singleton:

```python
_redis_client = None

def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
            socket_timeout=5, socket_connect_timeout=5,
            retry_on_timeout=True, health_check_interval=30,
            max_connections=10
        )
    return _redis_client
```

**The problem**: If the Redis connection breaks (network partition, Redis restart), `_redis_client` is **not None** — it's a valid Python object with a dead underlying connection. The singleton check `if _redis_client is None` will never trigger reconnection. Every subsequent Redis operation will fail with `ConnectionError` until the pod is restarted.

The `retry_on_timeout=True` and `health_check_interval=30` provide *some* resilience, but they don't cover all failure modes (e.g., TCP RST, Redis AUTH changed, Redis eviction of connection).

### Fix

**Wrap Redis client with connection health validation and automatic reconnection:**

```python
def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is not None:
        try:
            _redis_client.ping()
        except (redis.ConnectionError, redis.TimeoutError):
            logger.warning("Redis connection lost, reconnecting...")
            try:
                _redis_client.close()
            except Exception:
                pass
            _redis_client = None
    
    if _redis_client is None:
        redis_kwargs = { ... }  # existing config
        _redis_client = redis.Redis(**redis_kwargs)
    return _redis_client
```

**Note**: The `ping()` call adds ~0.1ms overhead per Redis operation. Given that Redis operations already take 1–5ms, this is negligible (~2–10% overhead). The alternative — crashing and requiring pod restart — is far worse.

### Impact

| Metric | Before | After |
|--------|--------|-------|
| Recovery from Redis outage | Pod restart required | Automatic in <1s |
| Crash-on-Redis-restart | Yes | No |

### PR Strategy

**PR S3**: "Add Redis connection health check and auto-reconnection"
- Scope: `redis_utils.py` only
- ~15 lines changed
- Risk: Very low
- Test: Kill Redis pod, verify worker reconnects automatically

---

## S4: Database Connection Pool Starvation Under Load (High)

### Problem

The DB connection pool in `db_utils.py` is configured with `POOL_MAX_CONN=10`:

```python
POOL_MAX_CONN = 10
```

The worker runs `maxConcurrentActivities=5` (from values/worker.yaml). Each `process_url_activity` makes multiple DB calls:
1. `was_url_visited()` — called once for the URL itself
2. `was_url_visited()` — called **per discovered link** in a for-loop (up to 1,000 links!)
3. `mark_url_visited()` — once after processing
4. `store_results()` — once for images

With 5 concurrent activities, each potentially holding a connection for the duration of the N+1 loop, the pool can be exhausted. The `db_connection()` context manager uses `getconn()` which **blocks indefinitely** when pool is exhausted (no timeout on pool acquisition).

```python
@contextmanager
def db_connection():
    pool = get_connection_pool()
    conn = pool.getconn()  # BLOCKS INDEFINITELY if pool exhausted
    try:
        yield conn
    finally:
        pool.putconn(conn)
```

### Fix

1. **Add pool acquisition timeout** (immediate fix):
```python
@contextmanager
def db_connection(timeout=10):
    pool = get_connection_pool()
    start = time.time()
    while True:
        try:
            conn = pool.getconn()
            break
        except pool.PoolError:
            if time.time() - start > timeout:
                raise TimeoutError(f"Could not acquire DB connection within {timeout}s")
            time.sleep(0.1)
    try:
        yield conn
    finally:
        pool.putconn(conn)
```

2. **Increase pool size** to match concurrency:
```python
POOL_MAX_CONN = 20  # 4× concurrent activities for headroom
```

3. **The real fix is S5 (N+1 batching)** — see `02_SCRAPER_PERFORMANCE.md`. Once N+1 is eliminated, each activity holds a connection for milliseconds instead of seconds, making pool exhaustion nearly impossible.

### Impact

| Metric | Before | After |
|--------|--------|-------|
| Pool acquisition | Blocks forever | Fails after 10s with clear error |
| Pool size vs concurrency | 2:1 ratio | 4:1 ratio |
| Connection hold time | Seconds (N+1 loop) | Milliseconds (after S5 batching) |

### PR Strategy

**PR S4**: "Add DB pool acquisition timeout and increase pool size"
- Scope: `db_utils.py` only
- ~20 lines changed
- Risk: Low
- Test: Run with 5 concurrent activities, verify no indefinite blocks
