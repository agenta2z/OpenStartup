# RAI Hack — Improvement Plan Index

**Created**: 2026-05-04  
**Repos**: `responsible-ai-api` + `responsible-ai`  
**Constraint**: No user-facing behavior changes; internal-only improvements  

## Documents

| File | Content |
|---|---|
| `PLAN.md` | **START HERE** — Master plan: all 13 items ranked by goal-driven impact, summary table, execution phases |
| `01-feature-gate-caching.md` | Items 1+2+3: Cache gate attrs + ModerationRequestContext + gate results in Flask g (P0, XS effort) |
| `02-grpc-healthcheck-gevent-timeout.md` | Item 5: Fix gRPC healthcheck blindspot + gevent timeout (P0, incident prevention) |
| `03-parser-metrics-and-model-unification.md` | Items 7+8+13: Parser fallback metrics + model layer unification + fail_open metrics (P1) |
| `04-etag-and-gate-audit.md` | Items 9+10: ETag double-parse fix + feature gate lifecycle audit (P1/P2) |

## Quick start: highest ROI first

1. **30 min**: Read `PLAN.md` end-to-end
2. **4–6 hours**: Implement Items 1+2+3 (`01-feature-gate-caching.md`) — zero risk, immediate latency reduction
3. **1 day**: Implement Item 13 (`03-parser-metrics-and-model-unification.md` §Item 13) — metrics only, additive
4. **1–2 days**: Implement Item 5 (`02-grpc-healthcheck-gevent-timeout.md`) — prevents repeat of 22k-error incident
5. **1 day**: Implement Item 7 (`03-parser-metrics-and-model-unification.md` §Item 7) — parser metrics
6. **2–3 days**: Implement Item 8 (`03-parser-metrics-and-model-unification.md` §Item 8) — model unification

## Key numbers (all verified from source code + production evidence)

| Metric | Current | Target | Gap |
|---|---|---|---|
| P90 prompt moderation latency | ~2,152ms (P95 observed) | **1,000ms** | -1,152ms |
| Reliability (prompt) | **99.7% SLO** | maintain | keep |
| `from_incoming_http_request()` calls/request | **~14** | **1** | -13 |
| Feature gate evaluations/request | **11** | **≤11 unique** | 0 redundant |
| Parser fallback metrics | **0** | **7+** | +7 |
| Fail-open metric | **0** | **1 per fail** | +1 |
| `rai_llama.py` size | **689 lines** | **≤350 lines** | -339 |
| `model_text_response_parse.py` branch coverage | **74%** | **90%** | +16pp |
| gRPC failure → ALB unhealthy time | **27–75s** | **≤5s** | -22–70s |
| Traffic growth (4-week trend) | +243% | — | scaling risk |
