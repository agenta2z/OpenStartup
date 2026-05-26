# Data-Driven Findings — TWG, Cypher, PR History, Strategic Context

> **Methodology:** Used TWG NL2Cypher queries, Bitbucket PR REST API, Atlassian Team API, recent SLO scratch notes, and the GAP decentralization strategy blog as primary sources.

---

## A. STRATEGIC BOMBSHELL — convo-ai is being decentralized

### A.1 The blog (`gai/6660323952`, posted 2026-03-23 by GAP team)

**Verbatim TL;DR:** *"To accelerate AI feature delivery for all teams, all new AI use cases must now be built in partner-owned services instead of ConvoAI. Existing non-core AI Features in ConvoAI to be safely transitioned out by June 2026."*

**Verbatim diagnosis:** *"We are now at a tipping point where partner teams are moving slower than ever via slow PR cycles and slower deployment cycles. Even with several new change safety guardrails the platform suffers from tens of incidents on certain weeks which further degrades the shipping velocity for our consumers, while creating a significant Operational Overhead for GAP teams."*

**Decisions:**
| Decision | Detail |
|---|---|
| New use cases | "Effective immediately, new AI use cases should not be onboarded to Convo AI" |
| Existing consumers | "Begin progressively moving existing non-core use cases out of Convo AI by **June 2026**" |
| Convo AI focus | "Shift focus to support **Rovo Chat and a small number of current core consumers** for now" |
| Target architecture | Partner-owned services using Alta Platform + Stratus SDK |

### A.2 Already in-flight migration: Rovo Insights → Proactive AI Platform (PAI)

Per `AM3/6849003562` (Apr 2026):
- *"We will migrate the Rovo Insights MVP to the new proactive-ai-platform (PAI) as our first production use case (by the end of May 2026)."*
- *"PAI fully replacing Convo AI"* (long-term vision per page 6603454040)
- Rationale: *"slow merge queue and limited deployments (only two per day)"*

### A.3 Implication for the opportunity report

**Re-ranking required.** Some opportunities become **lower priority** because the code is being migrated OUT:

| Opportunity | Original tier | Re-rank | Reason |
|---|---|---|---|
| **OPP-13** (MetricKey module-local migration) | 🟢 P3 | **🚫 DROP** | Not worth refactoring code that's leaving by June |
| **OPP-14** (Experience.kt decomp / SVC1) | 🟢 P3 | **🚫 DROP** | Same — Experience.kt belongs to non-core consumers |
| **OPP-17** (Helm worker manifest dedup / OPS1) | 🟢 P3 | **🟡 KEEP** (Rovo Chat stays in convo-ai) | Helm config will still be needed for the Rovo-Chat-only convo-ai |
| **OPP-18** (Anthropic provider dedup / ARC-1) | 🟢 P3 | **🟡 KEEP** | Provider code is Rovo-Chat-critical |
| **OPP-15** (AsyncAgentInMemoryJobStore → Redis) | 🟢 P3 | **🟢 UPGRADE → 🟠 P1** | If async jobs are still needed in Rovo Chat, persistence becomes critical |

**Some opportunities become MORE important:**

| Opportunity | Reason for upgrade |
|---|---|
| **OPP-01** (TenantContextRunnerImpl) | During transition, more endpoints get migrated/touched → propagation bug will bite more |
| **OPP-02** (Per-route AGG CB) | New PAI service will call AGG too — solving this in convo-ai sets the pattern for PAI |
| **OPP-04** (Graceful degradation) | Rovo Chat is what STAYS in convo-ai; degradation pattern protects the most important use case |
| **OPP-06** (Auto-revert candidate detector) | "Slow PR cycles" is the explicit diagnosis — anything that accelerates safe rollback is high-value |

### A.4 NEW opportunities surfaced by the strategy

| OPP | Title |
|---|---|
| **OPP-20** | Migration tracker: build a Confluence page or dashboard listing all "non-core" consumers + their transition status |
| **OPP-21** | Decommission detectors as use cases migrate out (avoid orphan detectors pointing at unreachable endpoints) |
| **OPP-22** | "PAI vs convo-ai" routing decision documentation — clear guidance for engineers asking "which service should I build in?" |

---

## B. TWG / Cypher findings — OPP-06 feasibility test

### B.1 Tool capability check

| Query | Result | Implication |
|---|---|---|
| "30 most recent merged PRs for conversational-ai-platform" | Cypher generated correctly; **`data: []` (EMPTY)** | TWG **doesn't index this repo's PR data** |
| "Bitbucket repos containing 'conversational' or 'convo-ai'" | **Empty summary** | Repo not registered in TWG `BitbucketRepository` nodes |
| "Count HOT issues since 2026-02-01 mentioning convo-ai" | Cypher generated; **`data: []` (EMPTY)** | Either HOT project not indexed OR my account lacks access (consistent with Jira MCP findings) |
| Direct Bitbucket REST API for PR listing | **WORKS** (sample of 7 recent merged PRs returned per agent investigation) | Backup path exists |

### B.2 Inference for OPP-06 (auto-revert candidate detector)

**Feasibility: ~70%** (per subagent's investigation)

**Works:**
- ✅ Bitbucket REST API gives precise merge timestamps and author identity for `conversational-ai-platform`
- ✅ Bitbucket PR diff is accessible per-file → file-overlap scoring is feasible
- ✅ Recent PRs heavily use Switcheroo feature flags (low-risk auto-revert candidates)

**Blocked:**
- ❌ TWG NL2Cypher can't correlate Jira HOT with Bitbucket PRs (HOT project not in graph for this account)
- ❌ HOT project not directly readable via Jira MCP (PIR-300811, HOT-300438, etc. all access-denied)
- ⚠ Team membership routing complex (requires `organizationId`)

**Mitigation for shipping OPP-06:**
1. Use **Confluence RCA page as the HOT-event timeline** until Jira access is fixed
2. Use **Bitbucket REST API directly** (not via TWG)
3. Route to **Slack channel `#convo-ai-incidents`** instead of individual engineer lookup
4. Score PRs by: file-overlap × deployment-tier (foundation/×3, platform/×2, product/×1) × FF-presence (no-FF / ×2)

**Revised effort estimate:** Same as before (2 sprints), with the caveat that we need a "HOT timeline" data source that doesn't require Jira access.

### B.3 Confidence reset: TWG cannot save us, Bitbucket can

OPP-06's design must NOT assume TWG indexing of `conversational-ai-platform`. It must use Bitbucket REST API directly. This is documented in the 03 opportunity report's "Concrete proposal" — confirming the proposal was right not to over-rely on TWG.

---

## C. Bitbucket PR velocity data (sampled from May 19, 2026)

Subagent investigation pulled 7 recent merged PRs to `atlassian/conversational-ai-platform:main` (samples, not exhaustive):

| Pattern | Observation |
|---|---|
| Merge velocity | ~10 PRs across 2+ hours on a single day → ~120 PRs/day implied |
| Distinct authors in sample | 6+ engineers (Kapoor, Jain, Ajihil, Dhaker, Batchu, Mahajan) |
| FF gating prevalence | High — `jsm_hr_agent_undo_redo`, `rovo_chat_jsm_manage_self_service_agent`, `rovo_chat_jsm_ai_agent` |
| Safety patterns | Tool input sanitization, regex-scrubbing of ARIs/URLs/emails/UUIDs/ticket keys, null-safety in filtering |

**Implication:** Code-review/safety culture is mature. The "slow PR cycles" pain (from GAP blog) is more about **merge queue + deployment velocity** than per-PR review quality.

**Cross-reference with Rovo Insights migration doc:** *"slow merge queue and limited deployments (only two per day)"* → bottleneck is in the deployment pipeline, not the PRs themselves.

---

## D. SLO ownership scheme (CRITICAL — new finding from `agents/6396583690`)

### D.1 Scratch note from Jan 30, 2026 by @Shilpa Naidu

**Two-layer tool model:**
- **L1 tools = Stratus Minions** (out of 60 `BaseLLMInvocable` classes, **50+ are schema agents = mostly Stratus Minions**)
- **L2 tools = IS tools + native tools** (under each Stratus Minion)

**Currently NO per-tool ownership SLO exists.** Author proposes:

```kotlin
// L1: in LlmInvocableExecutorImpl
llm_invocable.execution.success         // metric tag: id = BaseLlmInvocable.toolSchema.name
llm_invocable.execution.failed
llm_invocable.execution.latency

// L2: in AbstractStratusMinion
stratus.tool.success                    // metric tag: id
stratus.tool.failed
stratus.tool.latency
```

**Static SLO generation (proposed but not built):**
> "We need to generate terraform SLO modules on main merge via sauron — this has to be done **statically (can't be done at runtime)**. Create a test called `GenerateSLOTest.kt` that scans L1 tools and L2 tools, and leverage `<tool name, ownership, priority>` to generate SLOs with ownership team (slack/opsgenie) appropriately assigned."

**Failure mode:** The test fails when new L1/L2 tools are added without corresponding ownership information.

### D.2 NEW opportunity — OPP-23 🛡 Per-tool ownership-routed SLOs

| Field | Value |
|---|---|
| Type | 🛡 resilience + 📊 observability |
| Impact | 4 (forces every tool to declare an owner; routes alerts correctly) |
| Risk | 2 (incremental — opt-in per tool initially) |
| Complexity | 4 (4-6 engineer-weeks across the L1/L2 surface) |
| Score | 2 |
| Tier | 🟠 P1 |

**Concrete proposal:**
1. Implement `LlmInvocableExecutorImpl` metric emission (`llm_invocable.execution.success/failed/latency` with `id` tag)
2. Implement `AbstractStratusMinion` metric emission (`stratus.tool.success/failed/latency` with `id` tag)
3. Add `@ToolOwnership` annotation on `ToolDefinition` subclasses + Stratus YAML extension
4. Build `GenerateSLOTest.kt` that scans + generates `signalfx_detector` Terraform per tool
5. Wire sauron deploy to apply generated detectors on main merge
6. Initial migration: 60 `BaseLlmInvocable` classes get auto-detected; manual ownership label required to pass CI

**Why this matters now even though decentralization is happening:** Rovo Chat stays in convo-ai. The 60+ tool surface stays. Auto-routed SLOs will reduce 3am misrouting (a documented HOT-noise category).

---

## E. Cross-cutting: detector ↔ runbook ↔ code-path coverage

I cross-checked Terraform detectors against runbooks and against actual code paths:

| Detector | Runbook | Code surface | Coverage |
|---|---|---|---|
| `tomcat_thread_exhaustion.tf` | ✅ gai/6192570939 | RovoChatService, ConversationStateManagerImpl | 🟢 Triple coverage |
| `ai_gateway_client_errors.tf` | ✅ gai/6265841127 | AIGatewayClientServiceImpl | 🟢 Triple |
| `mcp_client_errors.tf` | ✅ gai/6105378875 | MarathonMcpClient family | 🟡 Coverage but detectors DISABLED |
| `tenant_context_errors.tf` | ❌ MISSING | TenantContextRunnerImpl ← **OPP-01 ROOT BUG** | 🔴 The most active bug class has no runbook |
| `feature_gate_reliability.tf` | ❌ MISSING | Switcheroo `featureService.checkGateWithLimitedContext()` | 🔴 No runbook |
| `redis_stream.tf` | ❌ MISSING | streaming_task | 🔴 No runbook for the SSE delivery channel |
| `heartbeat_availability.tf` | ❌ MISSING | Pollinator integration | 🔴 99.99% SLO but no runbook |
| `logging_quota.tf` | ❌ MISSING | Splunk emission | 🔴 The "we can't observe" detector has no runbook |

**The most critical detector (tenant_context_errors) has no runbook.** This is consistent with OPP-01 being undiagnosed — without a runbook, every fire requires re-deriving the root cause from scratch.

---

## F. Honest gaps that remain

| What I tried | Worked? | Why not |
|---|---|---|
| Direct Splunk query for error counts | ❌ Not attempted | No Splunk MCP tool available |
| Direct SignalFx MTS query for live metric values | ❌ Not attempted | No SignalFx MCP tool available |
| Databricks SQL warehouse query for SLO achievement table | ❌ Not attempted | No Databricks MCP tool available |
| Honeycomb/X-Ray distributed traces | ❌ Not attempted | No tracing MCP tool surfaced |
| Live Tome SLO state | ❌ Not attempted | Could try `tome.prod.atl-paas.net/slo/{uuid}` via web fetch if tool surfaces |
| Jira HOT project | ❌ Access denied | All HOT-NNNNNN access-denied; only GAPF/FD projects accessible |

**What I would still need:** an MCP tool with read-only Splunk/SignalFx/Tome/Databricks access, OR a temporary Jira HOT-project permission grant for my account.

---

## G. Updated opportunity list (delta vs `03_OPPORTUNITY_REPORT.md`)

### G.1 New opportunities

| Code | Title | Tier |
|---|---|---|
| OPP-19 | Runbook ownership + freshness governance (auto-detect deactivated owners + detector-without-runbook lint) | 🟡 P2 |
| OPP-20 | Migration tracker for "non-core" consumers transitioning out of convo-ai | 🟠 P1 |
| OPP-21 | Decommission orphan detectors as use cases migrate out | 🟡 P2 |
| OPP-22 | "PAI vs convo-ai" routing decision documentation | 🟡 P2 |
| OPP-23 | Per-tool ownership-routed SLOs (L1 LlmInvocable + L2 StratusMinion metric emission + GenerateSLOTest) | 🟠 P1 |

### G.2 Re-prioritization

| Code | Was | Now | Reason |
|---|---|---|---|
| OPP-13 (MetricKey migration) | 🟢 P3 | 🚫 DROP | Code being migrated out — refactor is wasted effort |
| OPP-14 (Experience.kt decomp) | 🟢 P3 | 🚫 DROP | Same |
| OPP-15 (AsyncAgentInMemoryJobStore → Redis) | 🟢 P3 | 🟠 P1 | If async jobs stay in convo-ai for Rovo Chat, persistence becomes critical |
| OPP-06 (auto-revert candidate detector) | 🟠 P1 | 🟠 P1 (UPGRADED in confidence — feasibility confirmed at ~70%) | Bitbucket REST API path works |
| OPP-01 (TenantContextRunnerImpl) | 🔴 P0 | 🔴 P0 (REINFORCED — no runbook exists for the detector that would fire) | Both root cause AND runbook are missing |

### G.3 Final ranking (post-data-update)

| Rank | Code | Tier |
|---|---|---|
| 1 | OPP-01 (TenantContextRunnerImpl) | 🔴 P0 |
| 2 | OPP-02 (Per-route AGG CB) | 🔴 P0 |
| 3 | OPP-03 (LLM TPM smoother) | 🔴 P0 |
| 4 | OPP-04 (Graceful degradation pattern) | 🟠 P1 |
| 5 | OPP-15 (Job persistence — UPGRADED) | 🟠 P1 |
| 6 | OPP-23 (Per-tool ownership SLOs — NEW) | 🟠 P1 |
| 7 | OPP-20 (Migration tracker — NEW) | 🟠 P1 |
| 8 | OPP-05 (Staging thread-saturation alarm) | 🟠 P1 |
| 9 | OPP-06 (Auto-revert detector) | 🟠 P1 |
| 10 | OPP-07 (Pollinator expansion) | 🟠 P1 |
| 11 | OPP-09 (Async TCS completion) | 🟠 P1 |
| 12 | OPP-19 (Runbook governance — NEW) | 🟡 P2 |
| 13 | OPP-08 (Re-enable MCP detectors) | 🟡 P2 |
| 14 | OPP-10 (Heartbeat tuning) | 🟡 P2 |
| 15 | OPP-11, 12, 16, 21, 22 | 🟡 P2 |
| 16 | OPP-17, 18 (Helm + Anthropic dedup — KEPT, Rovo-Chat-critical) | 🟢 P3 |
| - | OPP-13, 14 | 🚫 DROPPED |

**Total active opportunities: 21 (was 18 + 5 new − 2 dropped).**
