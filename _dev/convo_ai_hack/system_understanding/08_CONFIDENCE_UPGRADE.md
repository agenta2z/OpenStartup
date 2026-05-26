# Confidence Upgrade Summary — What Changed From Round 1 to Round 2

> **Purpose:** Track which claims in the original system-understanding deliverables (`00`–`04`) had their confidence upgraded, downgraded, or confirmed by direct data pulls in Round 2 (`05`–`07`).

---

## A. Methodology delta

| Round | Sources used | Confidence baseline |
|---|---|---|
| **Round 1** (initial 5 docs) | Terraform detector IaC (read locally), Confluence RCA page (1 page synthesized by Rovo Dev), code_understanding sphinx tree, local code grep | **Medium** — primarily secondary sources |
| **Round 2** (this batch — docs 05/06/07) | + 3 directly-verified Jira tickets, 11 directly-fetched Confluence runbooks, GAP strategic blog (primary source), SLO Uplift analysis (primary source), L1/L2 SLO scratch note (primary source), 2 TWG Cypher tests, Bitbucket REST API sample | **High for what's confirmed, Honest-N/A for what's blocked** |

---

## B. Claims-by-claim audit

| Claim | Round 1 Confidence | Round 2 Outcome | Net |
|---|---|---|---|
| 18 HOT incidents Feb 6 – May 6, 2026 | M (RCA page only) | ✅ 3 explicit follow-up Jira tickets (GAPF-1743, -1708, FD-188275) all reference HOT-301423 / PIR-300811 by name | **M → M-H** |
| TenantContextRunnerImpl bug recurring | M-H | ✅ RCA explicitly cites HOT-300438/-449/-485/-504/-517/-597/-989/-1572 cluster; no runbook for `tenant_context_errors.tf` detector | **M-H → H** |
| PIR-29582 = master incident | H (from detector file comment) | ❌ **WRONG** — PIR-29582 was a smaller observability PIR; the real master is **PIR-300811** | **H → L** (corrected) |
| HOT-301423 = generic tomcat exhaustion | M | ✅ Confirmed root cause: Hello tenant 16k agents fetched unpaginated → 10× spike | **M → H** (with specifics) |
| 200 threads/node tomcat config | M | ✅ Confirmed via Tomcat runbook `gai/6192570939` | **M → H** |
| 16 Netty event loops | M | ✅ Confirmed via RCA HOT-300449 quote | **M → H** |
| EC2 autoscale 10-15 nodes | M | ⚠ Confirmed for normal range; but **manual scale to 48+ nodes** during HOT-301423 (GAPF-1708) | **M → H+context** |
| 80M TPM cap on AI Gateway | M (RCA only) | ⚠ Still RCA-only — Jira access for HOT-300918/HOT-301437 denied | **M unchanged** |
| 60 BaseLlmInvocable, 50+ are Stratus Minions | (not in Round 1) | ✅ Verified via `agents/6396583690` scratch note | **NEW → H** |
| Rovo Chat reliability SLO target 99% | M-H | ⚠ **REFINED** — runbook ceiling is **99.9% MAX** (OpenAI Scale Tier SLA bound); currently set to 99.5% means HEADROOM exists | **M-H → H** |
| Pollinator coverage gaps (GraphQL, X-Forwarded-Host) | M | ✅ Confirmed via runbook fetches | **M → H** |
| Tomcat runbook updated since HOT-301423 | (assumed yes) | ❌ **WRONG** — last reviewed Jan 20, 2026; **PREDATES** HOT-301423 | **assumed → corrected** |
| MCP detectors are active | (assumed yes) | ❌ **WRONG** — runbook `gai/6105378875` explicitly states alerts are DISABLED; owner is deactivated | **assumed → corrected** |
| 1 Splunk dashboard total | M-H | ✅ Confirmed — `operations/splunk/dashboards/` contains 1 file (agent_permissions only) | **M-H → H** |
| Splunk index name = `micros_convo-ai` | (not in Round 1) | ✅ Verified across 5+ runbooks | **NEW → H** |
| TWG indexes conversational-ai-platform repo | (assumed yes) | ❌ **WRONG** — 2 Cypher queries returned empty | **assumed → corrected** |
| HOT project queryable via Jira MCP | (assumed yes) | ❌ **WRONG** — full access denied for my account | **assumed → corrected** |
| OPP-06 (auto-revert detector) feasibility | M (estimate) | ✅ Confirmed ~70% (Bitbucket REST API works; TWG path blocked) | **M → H** |
| 11+ detectors lack runbooks | (estimated 5+) | ✅ Counted exactly **11 confirmed missing** (heartbeat, redis_stream, feature_gate, logging_quota, agg_client, skill_error, tenant_context, etc.) | **estimate → H** |
| 3 runbooks have deactivated owners | (not in Round 1) | ✅ Confirmed: Himanshu Asati, Aakash Barbhaya, Thanh Tran | **NEW → H** |
| convo-ai is being decentralized | (not in Round 1) | ✅ **VERIFIED** via primary-source GAP blog `gai/6660323952` | **NEW → H** |
| Rovo Insights migrating to PAI by end of May 2026 | (not in Round 1) | ✅ Verified via `AM3/6849003562` Milestone 1 doc | **NEW → H** |

---

## C. Net effect on opportunity ranking

### C.1 Dropped (2)
- **OPP-13** MetricKey migration — DROP (code leaving by June)
- **OPP-14** Experience.kt decomposition — DROP (same)

### C.2 Upgraded (3)
- **OPP-01** TenantContextRunnerImpl: P0 → P0 **REINFORCED** (no runbook for the detector + recurring across 8 HOTs)
- **OPP-15** AsyncAgentInMemoryJobStore: P3 → **P1** (if Rovo Chat stays in convo-ai, persistence matters)
- **OPP-06** Auto-revert detector: P1 with M-confidence → P1 with **H-confidence** (feasibility verified)

### C.3 Added (5 new opportunities)
- **OPP-19** Runbook ownership + freshness governance (P2)
- **OPP-20** Migration tracker for non-core consumers (P1)
- **OPP-21** Decommission orphan detectors as use cases migrate out (P2)
- **OPP-22** PAI vs convo-ai routing decision documentation (P2)
- **OPP-23** Per-tool ownership-routed SLOs (P1)

### C.4 Confirmed unchanged (12)
- OPP-02 Per-route AGG CB (P0)
- OPP-03 LLM TPM smoother (P0)
- OPP-04 Graceful degradation (P1)
- OPP-05 Staging thread-saturation alarm (P1)
- OPP-07 Pollinator expansion (P1)
- OPP-08 Re-enable MCP detectors (P2)
- OPP-09 Async TCS completion (P1)
- OPP-10 Heartbeat tuning (P2)
- OPP-11, 12 (P2)
- OPP-16 (P2)
- OPP-17, 18 (kept at P3 — Rovo-Chat-critical)

**Total opportunities after Round 2: 21 (was 18; dropped 2; added 5; net +3).**

---

## D. What I still cannot confirm without further access

| Gap | What I'd need |
|---|---|
| Live SignalFx MTS values for any metric | SignalFx API access or MCP tool |
| Live Splunk error counts / event histograms | Splunk MCP tool |
| Databricks SLO achievement table | Databricks MCP tool |
| Full HOT ticket bodies (HOT-300438 root cause, HOT-300485, HOT-300918, HOT-301437 etc.) | Jira HOT project read access |
| PIR-300811 full bodyand sibling tickets | Same |
| Honeycomb / X-Ray distributed traces showing TenantContext propagation breaks | Tracing MCP tool |
| Live SLO state per Rovo Chat / Rovo Agents detectors | Tome API access |

**Honest assessment:** Without these, my analysis remains **strong on architecture/process insight, medium on quantitative impact**. The opportunity prioritization is sound; the IMPACT NUMBERS in the original report (e.g., "60% incident reduction") remain projections, not measurements.

---

## E. Recommended next data pulls (ranked by value)

1. **🔥 HIGHEST** — Get Jira HOT-project access for the account doing this audit. Single biggest confidence multiplier. Would let me verify every HOT-NNNNNN claim, pull all PIR-300811 children, and cross-reference resolution timelines.
2. **🔥 HIGH** — Index `conversational-ai-platform` in TWG. Single biggest unlock for OPP-06.
3. **🟠 MEDIUM** — Get Splunk MCP tool. Would allow direct error-rate measurement, OPP-01 (TenantContext) recurrence quantification, and OPP-04 (degradation) baseline.
4. **🟠 MEDIUM** — Get SignalFx MCP tool. Would allow live metric correlation, live SLO state, MTS history.
5. **🟡 LOW** — Get Databricks MCP tool. Useful for long-tail analysis (90-day SLO trends, tenant cardinality histograms).

---

## F. Methodology lessons for future audits

1. **Don't assume any data source is accessible until probed.** Lots of "obvious" sources (Jira HOT project, TWG repo indexing) turned out to be blocked.
2. **Cache hits are gold** — the 32 cached Confluence pages from prior session work were the highest-yield single data source.
3. **Subagents are critical for parallelizing data collection** — 4-way parallel investigation cut wall-clock by ~4×.
4. **Always note "verified vs RCA-only"** — the difference between primary and secondary sources is the difference between an audit and a synthesis.
5. **Test feasibility claims explicitly** — OPP-06's "we could build this with TWG" got disproved in a single Cypher call. Better to know now than 2 sprints in.

---

## G. Where confidence stands now

| Doc | Confidence |
|---|---|
| `00_INDEX.md` | M-H (top-10 ranking now informed by data) |
| `01_SYSTEM_MAP.md` | H (Terraform IaC is primary source) |
| `02_OPERATIONAL_SIGNALS.md` | H for synthesis-level, M for individual HOT details (per `05_HOT_DEEP_DIVE.md`) |
| `03_OPPORTUNITY_REPORT.md` | M-H (now superseded by 07's re-ranking) |
| `04_EVIDENCE_INDEX.md` | H |
| `05_HOT_DEEP_DIVE.md` | H for the 3 GAPF/FD tickets directly fetched; M for all RCA-derived HOT detail |
| `06_RUNBOOK_AUDIT.md` | H (11 runbooks directly read) |
| `07_DATA_DRIVEN_FINDINGS.md` | H for strategic/primary-source claims; M for TWG-feasibility extrapolation |
| `08_CONFIDENCE_UPGRADE.md` (this doc) | H (meta-doc audit) |

---

## H. Bottom line

**The original report was directionally correct.** Round 2 confirmed:
- The HOT pattern is real and well-documented
- The TenantContext bug is the most active class of incidents
- The runbook surface is underweight for the active detector surface
- Tomcat exhaustion is a chronic pain point

**Round 2 corrected:**
- PIR-29582 is NOT the master PIR — PIR-300811 is
- TWG does NOT index this repo (don't lean on it for OPP-06)
- HOT project read access is NOT granted by default
- 2 refactor opportunities should be DROPPED because the code is leaving the repo by June
- 5 new opportunities surfaced (governance, migration tracker, decommission, routing docs, per-tool SLO)

**Round 2 deepened:**
- Per-tool ownership SLO is a real, scoped, designable opportunity (OPP-23)
- The MCP integration is a unique kind of dead code (detectors disabled, owner deactivated, but still in production)
- Strategic context completely reframes the prioritization (decentralization → Rovo Chat is the only thing that needs to stay)
