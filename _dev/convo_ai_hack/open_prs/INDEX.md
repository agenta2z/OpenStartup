# Open PRs in `conversational-ai-platform` — Tony Chen

**Generated:** 2026-05-14 20:11 UTC
**Author:** Tony Chen (`{b4c77ba6-7684-4921-ba76-e54170e37b72}`, AAID `712020:5cf4b2db-…`)
**Repo:** `atlassian/conversational-ai-platform`
**Total open PRs:** 18 (verified via Bitbucket API with strict `state="OPEN"` + `author.uuid` filter)

---

## Impact-Label Methodology (evidence-based, ultrathink critique)

Every label below was re-derived from the actual PR description, measured benchmarks, and blast-radius analysis. The taxonomy is:

- **HIGH** = Measured user-perceptible win, OR prevents a user-visible failure mode (5xx, OOM, indefinite hang, total insight loss), OR foundational infrastructure that unblocks measurement of other work.
- **MEDIUM** = Measured aggregate win (cost, p99 in incidents, throughput) but **not** typical-user-perceptible at single-request level. Conditional value (only matters during specific failure modes).
- **LOW** = Micro-optimization (ns/µs aggregate), measurement-only counter, or code-quality refactor with no behavior change.

### Critical re-evaluation against initial pass (3 corrections)

| PR | Initial label | **Corrected label** | Reason for correction |
|----|---------------|---------------------|------------------------|
| **#29103** A8 cache-salt memoize | Medium | **Low** | The PR description itself says "<0.5% user-perceived". −24ms per regen out of 15-30s = imperceptible micro-optimization. Belongs with the other Lows. |
| **#29113** A2 parse-duration metric | Medium | **Low** | Pure observability + a rejection report. PR explicitly states "instrumentation only, NO user-visible behavior change". Same category as A12 (#29096). |
| **#29119** R-1B (main branch) | Medium | **High** | Load-bearing companion to R-1A (#29112). Without R-1B, R-1A timeouts cause silent drops → LLM re-calls hung tools indefinitely → defeats half of R-1A's value. Same severity tier as R-1A. |

---

## 🔴 HIGH Impact (9 PRs) — User-perceptible reliability/latency wins, foundational infra, or critical safety bounds

| # | PR | Title (short) | Headline impact |
|---|----|---------------|------------------|
| 1 | [#29074](pr-29074-A6-A11-hydration.md) | A6+A11 — hydration parallel + person dedup | **58–113× component speedup**, −70-90% UserService RPC, 3-7% e2e on /fetch regen |
| 2 | [#29085](pr-29085-A5-cancellation-isolation.md) | A5 — cancellation isolation | Categorical: **0/6 → 5/6 insights** survive single LLM failure; −12 min p99 during incident |
| 3 | [#29092](pr-29092-A1-observability-foundational.md) | A1 — foundational metrics | **Unblocks measurement** of A6, A8, A9, A10, A12, all post-deploy validation |
| 4 | [#29107](pr-29107-T2-webclient-pool.md) | T2 — WebClient pool 4→8 | Measured **+15% RPS, −22% p99**, eliminates pendingAcquireTimeout |
| 5 | [#29109](pr-29109-T1-bound-streaming-channel.md) | T1 — bound Channel.UNLIMITED | **Prevents pod OOM** from slow client (categorical safety) |
| 6 | [#29110](pr-29110-T0a-async-pool-bump.md) | T0a — Spring async pool 24/96→64/256 | **+29% RPS**, eliminates 503 RejectedExecutionException at peak |
| 7 | [#29111](pr-29111-T0b-heimdall-timeout.md) | T0b — Heimdall timeout 3000ms→500ms | **2.5s TTFT savings** during Heimdall degradation (user-perceptible) |
| 8 | [#29112](pr-29112-R-1A-per-tool-deadline.md) | R-1A — per-tool deadline | Prevents indefinite tool hangs; **load-bearing safety for T0a** |
| 9 | [#29119](pr-29119-R-1B-timeout-feedback-main.md) | R-1B — TIMEOUT→LLM feedback (main) | Closes R-1A loop: prevents agent re-calling hung tools; load-bearing |

## 🟡 MEDIUM Impact (4 PRs) — Conditional / aggregate wins (cost, incident-only, p99)

| # | PR | Title (short) | Headline impact |
|---|----|---------------|------------------|
| 10 | [#29097](pr-29097-A9-exponential-backoff.md) | A9 — exponential backoff w/ jitter | −2× wasted LLM calls during transients; prevents thundering herd (cost win) |
| 11 | [#29099](pr-29099-A10-partial-json-recovery.md) | A10 — partial JSON recovery | **+1-2 insights** recovered per malformed LLM response (conditional UX) |
| 12 | [#29114](pr-29114-R-1B-stacked.md) | R-1B (stacked on R-1A branch) | Same content as #29119 but stacked branch; close one or the other |
| 13 | [#29120](pr-29120-L1-tool-schema-cache.md) | L1 — tool-schema cache | **7.89× speedup** but only ~346µs/req — fleet aggregate win, not single-user-perceptible |

## 🟢 LOW Impact (5 PRs) — Micro-optimizations, measurement-only, code-quality

| # | PR | Title (short) | Headline impact |
|---|----|---------------|------------------|
| 14 | [#29103](pr-29103-A8-cache-salt-memoize.md) | A8 — cache salt memoize | −95% Statsig lookups but only ~24ms/regen (PR own analysis: "<0.5% user-perceived") |
| 15 | [#29113](pr-29113-A2-parse-duration-metric.md) | A2 — parse-duration metric + 4 rejections | Observability-only + rejection report (no behavior change) |
| 16 | [#29096](pr-29096-A12-duplicate-handler-counter.md) | A12 — duplicate-handler counter | Measurement-only counter (gates future SETNX decision) |
| 17 | [#29101](pr-29101-NEW-telemetry-map-dedup.md) | NEW — telemetry .map() dedup | −4 allocations/call micro-perf; byte-for-byte identical output |
| 18 | [#29121](pr-29121-C2-O1-tool-lookup.md) | C2 — O(1) tool-registration lookup | **20-21× speedup** on a 140-ns op = ns/µs aggregate, "unperceptible" per PR |

---

## Dependency / merge-order graph (suggested)

```
TIER 1 — Foundation (merge first):
  #29092 (A1 observability) ──── enables measurement of everything below

TIER 2 — Safety bounds (must land before capacity bumps):
  #29112 (R-1A per-tool deadline) ──┐
  #29119 (R-1B TIMEOUT→LLM) ────────┴── makes T0a safe
  #29109 (T1 bound channel) ─────────── prevents OOM under T0a load

TIER 3 — Capacity & performance (after Tier 2):
  #29110 (T0a async pool 64/256) ──── relies on R-1A+R-1B for safety
  #29107 (T2 WebClient pool 8x) ───── compounds with T0a
  #29111 (T0b Heimdall 500ms) ─────── independent, low-risk

TIER 4 — Rovo Insights perf/reliability (parallel):
  #29074 (A6+A11) ────────────────── biggest measured win
  #29085 (A5 cancellation) ──────── categorical reliability
  #29097 (A9 backoff) ────────────── cost during incidents
  #29099 (A10 partial JSON) ─────── conditional UX recovery

TIER 5 — Aggregate / fleet wins (any time):
  #29120 (L1 schema cache)
  #29103 (A8 cache salt memoize)
  #29101 (NEW telemetry dedup)
  #29121 (C2 O(1) lookup)

TIER 6 — Measurement-only / docs (any time):
  #29113 (A2 parse-duration metric)
  #29096 (A12 duplicate counter)

⚠️ HOUSEKEEPING:
  #29114 (R-1B stacked) ─── DUPLICATE of #29119; close one before merging the other
```

## Reviewer / CI / approval status

- All 18 PRs: **0 approvals so far** (per Bitbucket API at time of report)
- Lint shards passing on all 18; pre-existing repo-wide failures (WidgetStoreIT, JiraAiSuggestIssuesStreamingControllerPart1IT, ERS migration, image-moderation flake) are unrelated and documented in each PR

## Files in this directory

- `INDEX.md` — this file
- `pr-29074-…md` through `pr-29121-…md` — one comprehensive doc per open PR
