# Item 5: Fix gRPC Healthcheck Blindspot + gevent Timeout

**Priority: P0 | Effort: M (1–2 days)**

## Problem Evidence

### Root cause of 2026-04-16 incident (22,260 errors in 2 hours)

From incident postmortem (`agentic-coding-logs/2026-04-16-163700-incident-postmortem.md`):

1. Teamserve GPU OOM → CUDA crash → gRPC calls start hanging
2. gRPC `client_timeout=6s` **not enforced under gevent** (greenlets block 27–75s)
3. Healthcheck monitors HTTPX pool (always 0 active) — **never sees gRPC failure**
4. ALB healthcheck gaps grow to 13.5s > ALB 5s interval → instance marked unhealthy
5. But only **after** 30 failures hit circuit breaker (fail_max=30)

**Time from gRPC failure to ALB rerouting: 27–75 seconds** (one instance blocked for this long before timing out). During this window, all traffic continued to hit the broken instance.

### Current healthcheck code (verified from healthcheck.py)

```python
# healthcheck.py: check_grpc_circuit_breaker() — checks CB state ONLY
def check_grpc_circuit_breaker():
    for endpoint_name, endpoint in grpc_endpoints.items():
        state = endpoint.circuit_breaker.current_state
        if state == "open":
            overall_healthy = False
```

This only detects problems **after** 30 failures (fail_max=30). It does NOT detect:
- gRPC channel hang (not yet failed 30 times)
- New connection establishment failure
- Triton server overloaded but not yet timing out

### Current gRPC timeout enforcement (verified from triton_grpc_client.py)

```python
# triton_grpc_client.py: GrpcEndpoint.__init__()
self.triton_client = InferenceServerClient(url=url, ssl=True, verbose=False)
# No timeout parameter on channel creation
```

The `InferenceServerClient` from tritonclient.grpc does support a `channel_args` parameter where gRPC deadline can be set, but it is not used. Under gevent, gRPC's own timeout enforcement may not work correctly because gRPC uses threads internally while gevent patches socket I/O.

## Solution

### Fix 1: Add gevent-safe timeout wrapper in GrpcEndpoint.invoke()

```python
# src/inference_models/triton_grpc_client.py
import gevent
from gevent.timeout import Timeout as GeventTimeout

GRPC_HARD_TIMEOUT_SECONDS = 5.0  # match gRPC server deadline

def invoke(self, input_ids, input_lengths, request_output_len, **kwargs) -> dict:
    with GeventTimeout(GRPC_HARD_TIMEOUT_SECONDS, 
                       exception=TimeoutError("gRPC call exceeded hard timeout")):
        return self.breaker.call(self._grpc_infer, 
                                  input_ids, input_lengths, 
                                  request_output_len, **kwargs)
```

`gevent.timeout.Timeout` is gevent-native and correctly interrupts blocking greenlets. This ensures that regardless of gRPC's internal threading behavior, the greenlet will not block longer than 5 seconds.

### Fix 2: Add active liveness probe to healthcheck

```python
# src/api/healthcheck.py: new function
def _probe_grpc_liveness(endpoint: RAIFTTeamserveEndpoint, 
                          timeout_s: float = 1.0) -> bool:
    """Probe gRPC connection liveness with a short deadline.
    
    Returns True if the Triton server is reachable, False otherwise.
    Uses gevent timeout to avoid blocking the healthcheck greenlet.
    """
    import gevent
    try:
        with gevent.Timeout(timeout_s):
            return endpoint.triton_client.is_server_live()
    except (gevent.Timeout, Exception):
        return False
```

Update `check_grpc_circuit_breaker()` to call this probe:

```python
def check_grpc_circuit_breaker() -> GrpcCircuitBreakerHealth:
    ...
    for endpoint_name, endpoint in grpc_endpoints.items():
        state = endpoint.circuit_breaker.current_state
        endpoints_status[endpoint_name] = state
        
        if state == "open":
            overall_healthy = False
        elif state in ("closed", "half-open"):
            # Active probe: don't trust CB state alone
            if not _probe_grpc_liveness(endpoint, timeout_s=1.0):
                endpoints_status[endpoint_name] = "unreachable"
                overall_healthy = False
```

### Fix 3: Emit metric when liveness probe fails

```python
send_metric(Metric.GRPC_LIVENESS_PROBE_FAILED, tags={
    MetricTag.ENDPOINT_NAME: endpoint_name,
})
```

Add `GRPC_LIVENESS_PROBE_FAILED` to `Metric` enum in `metrics_handler.py`.

## Configuration

| Parameter | Value | Where |
|---|---|---|
| gRPC gevent hard timeout | 5.0s | `triton_grpc_client.py` constant |
| Healthcheck liveness probe timeout | 1.0s | `healthcheck.py` constant |
| Circuit breaker fail_max | 30 (unchanged) | `triton_grpc_client.py:GrpcEndpoint.__init__()` |

Both timeouts should be env-var configurable for tuning without redeployment.

## Acceptance criteria

- [ ] `gevent.Timeout` wraps `self.breaker.call(...)` in `GrpcEndpoint.invoke()` with 5s deadline
- [ ] `check_grpc_circuit_breaker()` calls `_probe_grpc_liveness()` for non-open endpoints
- [ ] `GRPC_LIVENESS_PROBE_FAILED` metric emitted on probe failure
- [ ] Mock test: gRPC call hanging > 5s raises `TimeoutError` (not blocks indefinitely)
- [ ] Mock test: `check_grpc_circuit_breaker()` returns `status=unhealthy` when probe fails
- [ ] `./bin/integration-test --smoke` passes
- [ ] `./bin/unit-test --coverage` passes; coverage floors held

## Non-regression guarantee

- CB behavior unchanged: fail_max=30 still applies (probe failure doesn't increment CB counter)
- Existing circuit breaker state reporting: unchanged
- If Triton server is healthy: liveness probe adds ~1ms overhead on every healthcheck call (not on every moderation request)
