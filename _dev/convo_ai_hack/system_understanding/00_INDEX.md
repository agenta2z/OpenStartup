# Conversational AI Platform — System-Level Understanding & Opportunity Report

**Author:** Rovo Dev (Tony Chen)
**Date:** 2026-05-19
**Scope:** `atlassian/conversational-ai-platform` service (convo-ai)

---

## ⚠️ DATA-SOURCE TRANSPARENCY (read first!)

This audit was conducted across **3 rounds**. Be aware of what each round did and did NOT use:

| Source class | R1 | R2 | R3 | Note |
|---|:--:|:--:|:--:|---|
| Static code analysis (cat/grep/AST on local checkout) | ✅ | ✅ | ✅ | Primary — high confidence |
| Confluence runbook content (text only, no view counts) | ⚠ partial | ✅ 11 read in full | ✅ | Secondary |
| Jira/Bitbucket via MCP | ❌ | ✅ 3 tickets verified, **HOT project restricted** | ✅ via Tome backend | HOT project still restricted to oncall membership |
| **Tome/Phobos SLO control-plane (primary source!)** | ❌ | ❌ | **✅ via `atlas slauth token --aud=phobos`** | **Round 3 unlock — direct API access to live SLO state, PIRs, burn events** |
| **SignalFx live metrics** | ❌ | ❌ | ⚠ chart URLs only | Got pre-signed URLs; data requires browser auth |
| **Splunk log queries** | ❌ | ❌ | ❌ | DNS unreachable; VPN/SSO required |
| **Databricks SQL** | ❌ | ❌ | ❌ | Refresh tokens expired; interactive SSO needed |
| Distributed traces / spans | ❌ | ❌ | ❌ | No MCP / API access from CLI |

**Bottom line:** R1+R2 were *inference-based* from static artifacts; R3 added **first primary-source data** via the Tome backend (Phobos API). All R1/R2 claims that have been re-verified against R3 live data are explicitly called out in **`08_CONFIDENCE_UPGRADE.md`** and **`09_LIVE_TELEMETRY_FINDINGS.md`**. **Always prefer doc 09's numbers over earlier docs when they conflict.**

---

**Sources used (cumulative across rounds):** Production SignalFx detector Terraform IaC, 14 weekly oncall logs, 18 HOT references (R1+R2 inferred — actually only 7 PIRs tied to Rovo Chat per R3 primary data), 15 active Confluence runbooks (11 fully read in R2), Tome/Phobos SLO API queries (R3), code-understanding Sphinx tree (1.17M LoC verified 2026-05-02)

---

## 🆕 Round 3 Update (May 19, 2026 — 07:22 PT)

Doc `09_LIVE_TELEMETRY_FINDINGS.md` adds **first primary-source data** from the Tome SLO control-plane (Phobos API):
- ✅ Authenticated via `atlas slauth token --aud=phobos` (identity: `tchen7`)
- ✅ **All 8 Rovo Chat SLOs** pulled with live targets + breach state (all currently healthy)
- ✅ **All 7 PIRs** ever filed against Rovo Chat capability — fully verified with exact impact windows
- ✅ **Discovered:** Deep Research SLO target was LOWERED 99.5% → 97% on 2026-04-30 (post-HOT-301437) → new **OPP-22: post-incident SLO concession audit**
- ✅ **Discovered:** Deep Research SLO is in LOW-TRAFFIC state — 2 burn events in last 23 days went UN-PAGED → new **OPP-21**
- ✅ **Corrected:** Only **7 PIRs** in 6 months (R2 said "18 HOTs"); only **9 SLOs** in Tome (R1 said 50+)
- ✅ **Confirmed:** PIR follow-up backlog is **worse** than thought — 5/7 still in `Draft` status → OPP-08 upgraded to P0
- ✅ Reproducible curl commands documented for future rounds

---

## 🆕 Round 2 Update (May 19, 2026)

Docs `05_HOT_DEEP_DIVE.md` → `08_CONFIDENCE_UPGRADE.md` add:
- ✅ 3 directly-verified Jira tickets (GAPF-1743, GAPF-1708, FD-188275) — found that **PIR-300811 is the master incident, NOT PIR-29582**
- ✅ 11 Confluence runbooks audited — **3 have deactivated owners, 11+ detectors have no runbook**
- ✅ **CRITICAL strategic context:** convo-ai is being **decentralized** by June 2026 — non-core use cases moving to partner services (per GAP team blog `gai/6660323952`)
- ✅ 5 new opportunities surfaced (governance, migration tracker, per-tool SLO, etc.)
- ✅ 2 refactor opportunities DROPPED (OPP-13/14) because the code is leaving the repo
- ✅ TWG/Cypher feasibility proven (~70%) for OPP-06 auto-revert detector
- ✅ Honest gap report: still need Splunk/SignalFx/Tome/Databricks MCP tools for quantitative measurement

**Recommended read order:** `00 → 08 → 07 → 06 → 05 → 03 (now superseded by 07.G.3 ranking)`

---

## How to read this report

1. **[01_SYSTEM_MAP.md](./01_SYSTEM_MAP.md)** — Service topology, dependency graph, SLO/SLI catalog, observability map. Read this first to know what's in production.
2. **[02_OPERATIONAL_SIGNALS.md](./02_OPERATIONAL_SIGNALS.md)** — Real production signals from SignalFx detectors, oncall RCA, Jira HOT tickets. Includes the killer "7 cross-cutting incident patterns" from the 3-month RCA.
3. **[03_OPPORTUNITY_REPORT.md](./03_OPPORTUNITY_REPORT.md)** — Ranked opportunity list (impact × risk × complexity). 18 opportunities, 5-tier prioritized.
4. **[04_EVIDENCE_INDEX.md](./04_EVIDENCE_INDEX.md)** — Citation table: file:line / HOT-ID / Confluence page-ID for every claim.
5. **[05_HOT_DEEP_DIVE.md](./05_HOT_DEEP_DIVE.md)** — R2: 3 directly verified Jira tickets; PIR-300811 cluster mapped.
6. **[06_RUNBOOK_AUDIT.md](./06_RUNBOOK_AUDIT.md)** — R2: 11 runbooks audited for freshness & owner.
7. **[07_DATA_DRIVEN_FINDINGS.md](./07_DATA_DRIVEN_FINDINGS.md)** — R2: GAP decentralization strategic context + 5 new OPPs.
8. **[08_CONFIDENCE_UPGRADE.md](./08_CONFIDENCE_UPGRADE.md)** — R2: which R1 claims are now high-confidence vs. still inferred.
9. **[09_LIVE_TELEMETRY_FINDINGS.md](./09_LIVE_TELEMETRY_FINDINGS.md)** — 🆕 R3: PRIMARY-SOURCE data from Tome/Phobos SLO API. **Final ranking lives here.**
10. **[10_JIRA_BOARD_SETUP.md](./10_JIRA_BOARD_SETUP.md)** — 🆕 Epic AI-236 "ConvoAI Optimization" + 10 child issues (AI-237 through AI-246) created in AI Lab. Board-creation UI steps documented.

---

## Top 10 opportunities — TL;DR

| Rank | Opportunity | Impact | Risk | Complexity | Why now |
|------|---|---|---|---|---|
| 1 | Fix `TenantContextRunnerImpl` MDC/suspend propagation bug | 🔴 SEV1 risk | Low | Medium | Open root cause behind ≥6 HOTs (300438, 300449, 300485, 300504, 300517, 300597, 300989, 301572) — actively blocking ALL suspend migrations |
| 2 | Per-route AGG client circuit breaker + bulkheads | 🔴 High | Low | Medium | Single shared breaker amplifies every upstream failure; explicitly called out in HOT-300710 PIR |
| 3 | LLM rate-limit pre-flight + token-bucket smoothing (80M TPM cap) | 🔴 High | Low | Medium | Hit 80M TPM cap multiple times (HOT-300918, HOT-301437) — repeatedly auto-paged |
| 4 | Graceful-degradation pattern for Rovo Chat (cache + fallback + bulkhead) | 🔴 High | Medium | High | `ai-3p-connector` outage repeated TWICE (HOT-300710, then again Mar 23-26); PIR explicitly calls this out |
| 5 | Staging thread-saturation alarm + scaling-first runbook | 🟠 Medium | Low | Low | "Playing whack-a-mole" — runbook ordering already proposed in HOT-301151 |
| 6 | Auto-revert candidate detector (PRs merged within N hours of a HOT) | 🟠 Medium | Low | Medium | Hotfix pipeline "too prone to failure, takes too long" (HOT-300753) |
| 7 | Pollinator coverage expansion (GraphQL, X-Forwarded-Host, suspend-context, SVG output) | 🟠 Medium | Low | Medium | Explicitly requested in Feb 3 PIR + HOT-300508 |
| 8 | Re-enable MCP detectors after stabilization (3 of 4 prod detectors disabled) | 🟠 Medium | Low | Low | "Too many errors and too little traffic to provide value" — quality debt accumulating |
| 9 | Async TCS client migration completion (last sync callers) | 🟠 Medium | Low | Medium | Original tomcat thread saturation root cause; PR-22983 patched some, more remain |
| 10 | Heartbeat SLO tuning (avoid auto-page on single 503) | 🟡 Low | Low | Low | "Tune the heartbeat SLO so a single 503 at the LB doesn't auto-page" — pollinator noise |

---

## Quick stats — the production reality

| Metric | Value | Source |
|---|---|---|
| HOT incidents (Feb 6 – May 6, 2026) | **18** | Confluence 6980681738 RCA |
| Distinct incident root-cause categories | **10** | Same RCA |
| Top 3 categories by count | Deployment regression (5), Thread starvation (4), Upstream LLM (4) | Same |
| Active SignalFx detectors (Terraform-managed) | **~80** | `operations/terraform/modules/*/detectors/*.tf` |
| Detectors currently DISABLED | **~25** (incl. 3 of 4 MCP) | Same |
| Active Confluence runbooks (gai space, last 180d) | **15** | CQL search |
| Confluence SLO docs | **0 found** (gap!) | CQL search |
| Service modules | **84** Gradle modules in 5 tiers | code_understanding/index.rst |
| LoC (main / test) | **1,175,159 / 1,354,512** | Same |
| Tomcat thread pool (per node, runbook) | **200** threads | gai/6192570939 |
| AI Gateway TPM rate cap | **80M** | HOT-300918 / HOT-301437 |
| Heimdall rate-limit per asap_issuer (old cap) | 60K → raised to **100K** | RCA |
| Reactor Netty event-loop threads | **16** | HOT-300449 |

---

## Key external references

| Resource | URL/ID |
|---|---|
| HOT Incident RCA (Feb-May 2026) | https://hello.atlassian.net/wiki/spaces/gai/pages/6980681738 |
| Tomcat busy threads runbook | https://hello.atlassian.net/wiki/spaces/gai/pages/6192570939 |
| Threadpool exhaustion runbook | https://hello.atlassian.net/wiki/spaces/gai/pages/6192606761 |
| Streaming client disconnections runbook | https://hello.atlassian.net/wiki/spaces/gai/pages/6325571921 |
| MCP alerts runbook | https://hello.atlassian.net/wiki/spaces/gai/pages/6105378875 |
| AI Gateway Client failure rate runbook | https://hello.atlassian.net/wiki/spaces/gai/pages/6265841127 |
| Rovo Chat / Deep Research high error rate runbook | https://hello.atlassian.net/wiki/spaces/gai/pages/6144691252 |
| Downstream rate limiting runbook | https://hello.atlassian.net/wiki/x/BpBugwE |
| Async tasks submit error burn runbook | https://hello.atlassian.net/wiki/spaces/gai/pages/6453133435 |
| Zero traffic alert runbook | https://hello.atlassian.net/wiki/spaces/gai/pages/6330551632 |
| Burn-rate detector philosophy | https://hello.atlassian.net/wiki/spaces/CONVAI/pages/4302911299 |
| On-call SLOs (WIP) | https://hello.atlassian.net/wiki/spaces/CONVAI/pages/3506389920 |
| HOT-301423 (tomcat saturation, root) | https://hello.atlassian.net/browse/HOT-301423 |
| GAPF-1743 (rate-limit follow-up) | https://hello.atlassian.net/browse/GAPF-1743 |
| GAPF-1708 (EC2 scaling rules after starvation) | https://hello.atlassian.net/browse/GAPF-1708 |
| FD-188275 (FF to mitigate HOT-301423) | https://hello.atlassian.net/browse/FD-188275 |
| PIR-29582 (SignalFX metrics outage) | (referenced in zero-traffic detector) |
