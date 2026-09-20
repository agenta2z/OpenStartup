# Scraper Service — Performance Optimizations (P1–P5)

> **Goal**: Quantifiable throughput and efficiency gains without changing user-facing behavior.

---

## P1: N+1 Database Query Elimination — Batch Visited-URL Checks (Critical)

### Problem

In `worker.py`, `process_url_activity` (line ~424) has a classic N+1 query pattern:

```python
# worker.py line ~410-440 — inside process_url_activity's fetch_and_process_url()
for link in links:  # links can be up to 1,000 (MAX_LINK_COUNT)
    if is_same_domain(root_url, link):
        is_link_visited = was_url_visited(job_id, link, root_url)      # DB query 1
        is_link_in_work_set = is_in_work_set(job_id, root_url, link)   # Redis query 1
        # ... per-link logic
```

Each `was_url_visited()` call in `db_utils.py` executes:
```python
def was_url_visited(job_id, url, root_url):
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM visited_urls WHERE job_id = %s AND url = %s AND root_url = %s LIMIT 1",
                        (job_id, url, root_url))
            return cur.fetchone() is not None
```

**For a page with 500 links**: 500 DB queries + 500 Redis queries = **1,000 round-trips per activity**.

Similarly in `get_urls_to_process_activity` (line ~160):
```python
while len(urls_to_process) < max_urls:  # max_urls = 500
    url = pop_into_processing(job_id, normalized_root_url, deadline)
    if was_url_visited(job_id, normalized_url, normalized_root_url):  # DB query per URL
        ...
```

### Quantified Impact

| Metric | Current (N+1) | Proposed (Batch) | Improvement |
|--------|---------------|-------------------|-------------|
| DB round-trips per activity | ~500 (worst case) | 1–2 | **99.6% reduction** |
| DB latency per activity | ~1,250ms (500 × 2.5ms avg) | ~5–10ms | **99.2% reduction** |
| Connection pool pressure | Extreme (holds conn for seconds) | Minimal (ms-level holds) | ~99% reduction |
| CPU on DB server (parse/plan) | 500× per activity | 1× per activity | **99.8% reduction** |

### Fix

**A) Add batch check function to `db_utils.py`:**

```python
def batch_check_visited(job_id: str, urls: list[str], root_url: str) -> set[str]:
    """Check visited status for multiple URLs in a single query.
    Returns set of URLs that have been visited."""
    if not urls:
        return set()
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT url FROM visited_urls
                WHERE job_id = %s AND root_url = %s AND url = ANY(%s)
                """,
                (job_id, root_url, urls)
            )
            return {row[0] for row in cur.fetchall()}
```

**B) Add batch check to `redis_utils.py`:**

```python
def batch_check_in_work_set(job_id: str, root_url: str, urls: list[str]) -> set[str]:
    """Check which URLs are already in work set. Returns set of URLs found."""
    if not urls:
        return set()
    client = get_redis_client()
    work_key = get_work_queue_key(job_id, root_url)
    pipe = client.pipeline(transaction=False)
    for url in urls:
        pipe.sismember(work_key, url)
    results = pipe.execute()
    return {url for url, is_member in zip(urls, results) if is_member}
```

**C) Refactor `process_url_activity` link processing loop:**

```python
# Collect all same-domain links first
same_domain_links = [link for link in links if is_same_domain(root_url, link)]

# Batch check: one DB query + one Redis pipeline
visited_set = batch_check_visited(job_id, same_domain_links, root_url)
in_work_set = batch_check_in_work_set(job_id, root_url, same_domain_links)

# Process without any per-link DB/Redis calls
for link in same_domain_links:
    is_visited = link in visited_set
    is_in_work = link in in_work_set
    # ... same logic, no network calls
```

### PR Strategy

**PR P1a**: "Add batch_check_visited to db_utils.py" (pure addition, no behavior change)
**PR P1b**: "Add batch_check_in_work_set to redis_utils.py" (pure addition)
**PR P1c**: "Refactor process_url_activity to use batch checks" (swap N+1 → batch)

---

## P2: Async HTTP Migration — requests → aiohttp (High)

### Problem

`scraper_utils.py` uses synchronous `requests.get()`:

```python
# scraper_utils.py — fetch_url()
def fetch_url(url: str) -> requests.Response:
    response = requests.get(url, timeout=10, stream=True)
    ...
```

Called from `process_url_activity` via `asyncio.to_thread()` (worker.py line ~325):

```python
response = await asyncio.to_thread(fetch_url, url)
```

**Problems:**
1. `asyncio.to_thread()` uses the default ThreadPoolExecutor (typically 5–10 threads)
2. With `maxConcurrentActivities=5`, up to 5 threads blocked on HTTP I/O simultaneously
3. Thread pool can become saturated, preventing other `to_thread()` calls from executing
4. The sync `requests` library creates a new TCP connection per request (no connection pooling)

### Quantified Impact

| Metric | Current (requests + to_thread) | Proposed (aiohttp) | Improvement |
|--------|-------------------------------|---------------------|-------------|
| Thread pool usage | 1 thread per active fetch | 0 threads (native async) | 100% reduction |
| Connection reuse | None (new TCP per request) | Connection pool | ~50% latency reduction |
| Concurrent capacity | Limited by thread pool | Limited only by FD limit | 10–50× higher |
| Event loop responsiveness | Degraded under load | Maintained | Health checks reliable |

### Fix

**Replace `requests.get()` with `aiohttp.ClientSession`:**

```python
# scraper_utils.py — new async version
import aiohttp

# Module-level session (reuses TCP connections)
_session: Optional[aiohttp.ClientSession] = None

async def get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        timeout = aiohttp.ClientTimeout(total=10, connect=5)
        connector = aiohttp.TCPConnector(limit=20, ttl_dns_cache=300)
        _session = aiohttp.ClientSession(timeout=timeout, connector=connector)
    return _session

async def fetch_url_async(url: str) -> aiohttp.ClientResponse:
    is_valid, error_msg = validate_url(url)
    if not is_valid:
        raise ValidationError(error_msg)
    session = await get_session()
    response = await session.get(url, ssl=False)
    # ... same content size checks, streaming, etc.
```

**Important**: Keep the sync `fetch_url()` as a fallback during migration. Remove `asyncio.to_thread()` wrapper.

### PR Strategy

**PR P2a**: "Add async fetch_url_async using aiohttp" (pure addition alongside existing sync version)
**PR P2b**: "Migrate process_url_activity to use fetch_url_async" (swap to async, remove to_thread)
**PR P2c**: "Remove sync fetch_url and requests dependency" (cleanup)

---

## P3: URL Normalization CPU Optimization (Medium)

### Problem

`normalize_url()` in `scraper_utils.py` is called **per URL per link** — potentially thousands of times per activity. The implementation uses `urlparse` + `urlunparse` which involves:

```python
def normalize_url(url):
    parsed = urlparse(url)
    scheme = 'https' if parsed.scheme in ('http', 'https') else parsed.scheme.lower()
    cleaned = parsed._replace(fragment='', scheme=scheme, netloc=parsed.netloc.lower())
    normalized = urlunparse(cleaned)
    return normalized.rstrip('/') if normalized != '/' else normalized
```

This is called redundantly — the same URL may be normalized 3–5 times across `get_urls_to_process_activity`, `process_url_activity`, and `add_to_work_set`.

### Fix

**Add LRU cache for normalization:**

```python
from functools import lru_cache

@lru_cache(maxsize=10000)
def normalize_url(url):
    # ... existing implementation
```

**Why 10,000?** Typical job processes 1,000–10,000 unique URLs. Cache hit rate expected: 60–80% (many URLs encountered multiple times across activities).

Memory cost: ~10,000 × 200 bytes average URL = ~2MB. Acceptable given 4GB limit.

### Impact

- CPU reduction for normalization: ~60–80%
- Overall activity speedup: ~5–10% (normalization is ~10% of CPU time)

### PR Strategy

**PR P3**: "Add LRU cache to URL normalization"
- Scope: `scraper_utils.py` — 2 lines changed
- Risk: Very low (pure function, deterministic output)

---

## P4: Batch URL Addition to Redis Work Set (Medium)

### Problem

In `process_url_activity`, discovered links are added to the Redis work set one at a time:

```python
for link in same_domain_links:
    if add_to_work_set(job_id, root_url, link):  # Individual SADD per link
        ...
```

Each `add_to_work_set()` does an `SADD` + metrics increment — individual Redis round-trips.

### Fix

**Use Redis pipeline for batch insertion:**

```python
def batch_add_to_work_set(job_id: str, root_url: str, urls: list[str]) -> list[bool]:
    """Add multiple URLs to work set in a single pipeline. Returns list of success flags."""
    client = get_redis_client()
    work_key = get_work_queue_key(job_id, root_url)
    pipe = client.pipeline(transaction=False)
    for url in urls:
        pipe.sadd(work_key, url)
    results = pipe.execute()
    added_count = sum(1 for r in results if r)
    if added_count > 0:
        increment_urls_added(job_id, root_url, added_count)
    return [bool(r) for r in results]
```

### Impact

- Redis round-trips per activity: N → 1 pipeline
- Latency reduction: ~90% for link insertion phase

### PR Strategy

**PR P4**: "Add batch Redis work set insertion"
- Scope: `redis_utils.py` + caller in `worker.py`
- Risk: Low

---

## P5: API Server Temporal Client Fix (Medium)

### Problem

In `api_server.py`, the `get_temporal_client()` function is a **no-op**:

```python
_temporal_client = None

def get_temporal_client() -> Client:
    global _temporal_client
    if _temporal_client is None:
        pass  # NOTE: Does nothing! Always returns None!
    return _temporal_client
```

Instead, every `/jobs` POST request creates a new Temporal client:

```python
async def start_workflow():
    client = await Client.connect(...)  # New connection per API request!
    handle = await client.start_workflow(...)
    return client, handle, workflow_id, run_id
```

This is the same leak pattern as S1 but in the API server process.

### Fix

Implement the singleton properly:

```python
async def get_or_create_temporal_client() -> Client:
    global _temporal_client
    if _temporal_client is None:
        _temporal_client = await Client.connect(
            f"{TEMPORAL_HOST}:{TEMPORAL_PORT}",
            namespace=TEMPORAL_NAMESPACE,
        )
    return _temporal_client
```

### PR Strategy

**PR P5**: "Fix API server Temporal client singleton"
- Scope: `api_server.py`
- ~10 lines changed
- Risk: Very low
