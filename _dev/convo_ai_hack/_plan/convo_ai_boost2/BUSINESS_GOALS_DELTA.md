# BOOST Plan v1 — Business Goals Delta

**Companion to:** [`BOOST_PLAN_v1.md`](BOOST_PLAN_v1.md)
**Authoritative source it complements:** [`code_understanding/architecture/business/01-fy26-goals-and-slos.rst`](../../code_understanding/architecture/business/01-fy26-goals-and-slos.rst)
**Created:** 2026-05-14

---

## Purpose

This document captures **what BOOST Plan v1 changes** in the FY26 business-goal landscape, so the canonical `01-fy26-goals-and-slos.rst` can be updated with a single reference instead of being rewritten.

---

## 1. North-star deltas

| FY26 metric | Baseline (per `01-fy26-goals-and-slos.rst`) | v7 contribution | **+ BOOST contribution** | New combined gap closure |
|-------------|----------------------------------------------|-----------------|---------------------------|---------------------------|
| **AIFC FactualConsistency** (13% → ≥40%, gap +57pp) | 13% | v7 Q1+Q2+Q3+Q4 = +36-57pp | (BOOST does NOT compete on quality — defers to v7) | +36-57pp via v7 |
| **Rovo MAU** (100k → 150k, gap +50%) | 100k | v7 F1+F2+F4+L1+T2 (activation levers) | + B-Latency+ Y1, Y2, Y3, Y4 (perceived-speed levers) | Activation + perception combined |
| **Chat SLO** (current → 99.85% mandatory, gap +0.25pp) | ~99.6% | v7 R-series + L3 + T1 = +0.3pp | + B-Reliability+ S1, S2, S6 = additional +0.05–0.10pp | Closes 99.85% with margin |
| **Throughput** (current → +1,400 req/s peak) | ~3,000 req/s | v7 T0a + T2 + T1 = +1,400 req/s | + B-Latency+ Y3 + B-Refactor R8 = +200-400 req/s | +1,600-1,800 req/s peak |
| **Cost** (current → −$168-290K/mo) | $168-290K/mo claimed savings | v7 C1+C2+K1+N1+N10 = $168-290K | **+ B-Cost+ X1-X10 = additional −$30-73K/mo** | Total $198-363K/mo savings |
| **Trust pillar** (no silent user-trust bugs) | duplicate-create silent bugs exist | v7 R-6A | + B-Reliability+ S1 (memory loss) + S5 (post-workflow mutations) | Eliminates broader class of silent bugs |
| **Dev velocity** (LoC removed) | n/a | v7 E1-E3 = ~1,500 LoC | + B-Refactor R1+R5+R6+R10 = ~3,000 LoC | ~4,500 LoC removed total |

---

## 2. NEW measurement plan items (add to v7 §6)

| ID | What it proves | Required instrumentation |
|----|----------------|--------------------------|
| **M10** | BOOST cost claims (X-series) | Per-feature token attribution panel via M4 Socrates `convo_ai_usage` data product; per-conversation tool-schema bytes counter (X2); router/classifier model-name counter + accuracy delta (X7); per-AIFC iteration count + cost (X9); CloudWatch ingest delta per log line (X10) |
| **M11** | BOOST refactor velocity | Per-week LoC-removed counter (R1, R5); per-week PR-merge throughput (correlate w/ refactor merges); per-handler retry-rate counter (R6); per-tool malformed-output counter (R10) |
| **M12** | BOOST silent-bug counters | DLQ message-count for fire-and-forget tasks (S1); duplicate post-workflow-mutation counter (S5); load-shed-trigger counter (S2); slow-client-timeout counter (S4); MDC-keys-missing counter (S3); readiness-probe-failure counter (S6) |

**v7's hard rule extended:** No BOOST item ships claiming impact until M10/M11/M12 is live for ≥7 days.

---

## 3. NEW anti-goals (add to v7 §8 — currently 36; BOOST adds 5)

37. Do not ship X7 (model mis-selection) without an LLM-judge accuracy A/B test demonstrating ≤5pp accuracy delta on a labeled router/classifier dataset.
38. Do not ship R1 / R5 / R6 / R10 refactors without v7's E-series PRs landing first.
39. Do not promote Y3 (parallel tool calls) to >5% rollout until R-6A (tool idempotency) is live for ≥7 days.
40. Do not measure BOOST cost claims using LLM-token counters alone. Use the M4 Socrates `convo_ai_usage` data product per-feature attribution.
41. Do not refactor a class because it is "ugly". R1, R5, R6, R10 must each show measurable dev-velocity (LoC removed, PRs merged/wk delta) or reliability (incident-rate delta) impact within 6 weeks of merge; otherwise rollback.

---

## 4. Per-feature roadmap addition (to be added to `01-fy26-goals-and-slos.rst` §11)

**Append the following row to the per-feature roadmap table:**

```restructuredtext
   * - **Convo AI Boost (BOOST Plan v1)**
     - 23 incremental items targeting +$30-73K/mo cost reduction (X-series, X7
       being largest single lever at $16.8-43.5K/mo via Sonnet → Haiku for
       routing/classification), -700-2,500ms p95 TTFB (Y-series, Y2/Y3 being
       largest single levers via .block() removal + parallel tool calls),
       +200-400 req/s capacity (Y3 + R8), ~3,000 LoC removed (R-series),
       and silent-trust-bug elimination (S1 + S5 + S6).
     - Owner: TBD (proposed: Tony Chen + 1-2 engineers ×12 weeks)
     - Plan: `_dev/convo_ai_hack/_plan/convo_ai_boost2/BOOST_PLAN_v1.md`
     - Status: PROPOSED 2026-05-14; pending v7 measurement infra (M1-M9)
       being live before any BOOST claim can be validated.
```

---

## 5. Strategic-pillar tie-back (per `04-rovo-ai-fy26-strategy.rst`)

| Pillar | BOOST contribution | Source items |
|--------|---------------------|--------------|
| **Knowledge** | Faster knowledge retrieval via cache (X5) → semantic search latency reduced | X5, R8 |
| **Productivity** | Parallel tool calls (Y3) + faster TTFB (Y1, Y2, Y4) → Rovo Chat session speed lifts MAU | Y1, Y2, Y3, Y4 |
| **Trust** | Silent-bug elimination (S1, S5, S6) + tool-output validation (R10) → fewer customer-visible failures | S1, S5, S6, R10 |
| **Monetization** | $30-73K/mo cost reduction → improves Rovo Credits unit economics | X1-X10 (entire B-Cost+ workstream) |
| **Brand** | (no direct contribution — engineering-internal) | — |

---

## 6. Cross-references

- BOOST plan (master): [`BOOST_PLAN_v1.md`](BOOST_PLAN_v1.md)
- BOOST per-workstream files: [`boost_items/`](boost_items/)
- v7 plan: [`../convo_ai/INTEGRATED_PLAN_v7_synthesis.md`](../convo_ai/INTEGRATED_PLAN_v7_synthesis.md)
- Open PRs index: [`../../open_prs/INDEX.md`](../../open_prs/INDEX.md)
- Authoritative business goals: [`../../code_understanding/architecture/business/01-fy26-goals-and-slos.rst`](../../code_understanding/architecture/business/01-fy26-goals-and-slos.rst)
