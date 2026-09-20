# SRE Skills & Tools — INTEGRATED Enhancement Plan v2
**Author:** Rovo Dev / Claude Sonnet 4.5
**Date:** 2026-04-30 (v2: integration of Plan-A + Plan-B)
**Inputs integrated:**
- **Plan-A** = `_plan/sre-skills-tools-enhancement-plan.md` (685 lines — my original)
- **Plan-B** = `~/.claude/plans/stateful-beaming-dusk.md` (390 lines — alternative)
**Status:** Proposal — awaiting review

---

## 0. TL;DR — what changed from Plan-A

After re-reading both plans end-to-end and spot-verifying claims against the live registry:

**Plan-B is more concrete and shippable.** It nails specific endpoint mappings (Loki API, GitHub Actions API, ArgoCD API), executor patterns ("Pattern A" / "Pattern B" naming), and per-action risk classifications. Plan-A is more architecturally cautious (3-layer refactor, cross-skill composition, generic-name discipline) but vaguer on "what does the executor look like".

**The honest synthesis:**
- Plan-B's **3 tools + 2 skills** is the right scope for the **first delivery**
- Plan-A's **architectural foundation** (3-layer split, GLOSSARY, CONTRIBUTING) is the right **before-anything-else step** (Plan-B mentions references/ but as Phase 5 "after the rest is built" — that's backwards)
- Plan-B's **Phase 3** (existing-tool enhancements: Helm in kubernetes_ops, GCP in cloud_ops, query-templates in prometheus_query, shift-handoff in opsgenie_manage, SLO-template in grafana_manage) is **substantially better than Plan-A's vague §5.3–§5.6** — these are concrete, well-scoped, low-risk wins
- **Plan-A's `trace_query` and `scm_ops`** are MORE ambitious than Plan-B's `cicd_pipeline` — but Plan-B's `cicd_pipeline` is more honest: GitHub Actions + ArgoCD are concrete, while "vendor-neutral SCM with deploy actions" requires deciding between Spinnaker / ArgoCD / Jenkins / Bitbucket pipelines / GitLab CI etc. Plan-B's pragmatic scoping wins
- **Plan-B's `network_diag`** (DNS/TLS/connectivity CLI passthrough) is a great low-effort high-value addition that I missed entirely in Plan-A
- **Plan-B's `change-management` skill** is more concrete than Plan-A's — has explicit canary criteria, blast-radius classification with approval matrix, auto-rollback triggers
- **Plan-A's `incident-response` skill** description goes deeper than Plan-B's on anti-patterns and comms cadence; merge both
- **Plan-A's open questions, skeptical caveats, and effort estimates** are a discipline absent from Plan-B; preserve them
- **Plan-A's `oncall-shift` and `post-mortem` skills** ARE valuable but Plan-B is right to defer them — they're more naturally chapters of `incident-response` until proven they need separation

**Net change vs. Plan-A:**
- Drop the standalone `trace_query` tool (defer to Phase 6+ once observability stack is concrete)
- Drop the standalone `scm_ops` tool (replaced by Plan-B's `cicd_pipeline` + git-operations should remain CLI passthrough or live in a future tool)
- Keep `log_query` but adopt Plan-B's specific Loki-first design (no premature multi-backend abstraction)
- Add Plan-B's `network_diag` and `cicd_pipeline`
- Demote `oncall-shift` and `post-mortem` to chapters of `incident-response` initially; promote to standalone only if the chapters exceed ~200 lines each
- Keep Plan-A's Phase 0 architectural refactor as the prerequisite to everything else

**Net registry size after integration:**
- Tools: 7 → **10** (+3: log_query, cicd_pipeline, network_diag)
- Skills: 2 → **4** (+2: incident-response, change-management)
- Total effort: **~14 dev-days** (was 21 in Plan-A; 4-week prose vs. 3-week shippable)

---

## 1. Head-to-head comparison

### 1.1 Coverage matrix

| Concern | Plan-A | Plan-B | Integrated v2 |
|---|---|---|---|
| **NEW TOOLS** | 3 (log_query, trace_query, scm_ops) | 3 (log_query, cicd_pipeline, network_diag) | **3 from Plan-B**: log_query + cicd_pipeline + network_diag |
| **NEW SKILLS** | 4 (incident-response, change-mgmt, oncall-shift, post-mortem) | 2 (incident-response, change-mgmt) | **2 from Plan-B** + oncall-shift + post-mortem as CHAPTERS inside incident-response |
| **TOOL ENHANCEMENTS** | Vague (genericize names, pagination, idempotency, exemplar) | 5 specific tools enhanced (k8s+helm, prom+templates, cloud_ops+gcp, opsgenie+handoff, grafana+SLO) | **Plan-B's 5 specific** + Plan-A's pagination/idempotency/exemplar inserted into the same files |
| **SKILL ENHANCEMENTS** | Vague (cross-skill composition map, GLOSSARY) | 2 explicit (infra-ops adds Helm/Cost/Multi-Cloud, sre-obs adds Log/RED/USE/Runbook) | **Both**: Plan-B's content + Plan-A's composition glue |
| **ARCHITECTURE REFACTOR** | Phase 0 (3-layer split, CONTRIBUTING, GLOSSARY) | Phase 5 (references/ dirs, ops log, dispatch tables) | **Plan-A's Phase 0 sequencing wins** — refactor BEFORE adding |
| **OPEN QUESTIONS** | 8 explicit | 0 | **All 8 from Plan-A** |
| **SKEPTICAL CAVEATS** | 10 explicit | 0 | **All 10 from Plan-A** |
| **EFFORT ESTIMATES** | Per-phase + total + MVP shortcut | Lines-of-code estimates only | **Plan-A's day-count estimates** (more useful than LoC) |
| **VERIFICATION** | Files read end-to-end | Implied | **Plan-A's verification ledger** preserved |
| **SAFETY GUARDRAILS** | Cross-cutting concerns (§8) | Per-action risk tables in each tool | **Both**: cross-cutting concerns at registry level + per-action tables at tool level |
| **AUTH PATTERNS** | Mentioned generically | Specific env vars per tool (LOKI_URL, GITHUB_TOKEN, ARGOCD_AUTH_TOKEN, ASAP_TOKEN fallback) | **Plan-B's specifics** |
| **API ENDPOINT MAPPINGS** | Not provided | Concrete tables per tool | **Plan-B's tables** |
| **EXECUTOR PATTERNS** | Not named | "Pattern A" (read-only API) and "Pattern B" (read+confirmed-write) | **Plan-B's naming** + Plan-A's note that 3 tools are deliberate CLI passthroughs |

**Score**: out of 13 dimensions, Plan-A wins 6, Plan-B wins 5, ties 2. **Neither dominates.** Both bring distinct value; integration produces a strictly better plan than either alone.

### 1.2 Where each plan is wrong / weak

#### Plan-A weaknesses (acknowledged honestly)
1. **`scm_ops` was over-scoped.** "Vendor-neutral SCM + deploy" combines too many concerns. Plan-B's `cicd_pipeline` (focused on GH Actions + ArgoCD specifically) is more deliverable. Native git operations should remain CLI-passthrough (already covered by shell access).
2. **`trace_query` was premature.** No skill currently consumes traces; both observability skills currently work fine without traces. Defer until concrete demand.
3. **§5.3–§5.7 enhancement section was vague.** "Genericize cloud_ops" without saying WHAT goes inside `gcp_ops` is brochure-level. Plan-B's "GCP operations to usage_guidance: compute/container/monitoring/logging/sql" is concrete.
4. **`oncall-shift` and `post-mortem` as standalone skills was over-fragmenting.** Plan-B's instinct (chapters of `incident-response`) is better. Plan-A's own §4.5 even said "we cap at ~6 skills" — and then proposed 6, leaving zero headroom for future skill growth. Demote oncall-shift + post-mortem to chapters; promote later if they grow.
5. **Plan-A's "MVP shortcut" of Phase 0 + log_query + incident-response is good** but didn't include Plan-B's `network_diag` (CLI-passthrough, ~0.5 day) which is genuinely high-value-low-cost.

#### Plan-B weaknesses (newly identified during integration)
1. **No architectural refactor up front.** Plan-B's Phase 5 ("references/ dirs, ops log") is a "build first, refactor later" approach. Once `incident-response/SKILL.md` and `change-management/SKILL.md` ship as monolithic 700-line files, splitting them later costs more than splitting before. **Plan-A's Phase 0 sequencing is correct.**
2. **No "open questions" section.** Plan-B asserts decisions (Loki for logs, GitHub Actions + ArgoCD for CI/CD, Slack for chat) without flagging them as decisions to confirm. If the deployment uses Splunk + GitLab CI + Teams, Plan-B's tools become wasted work. **Plan-A's §9 open questions are essential** to risk-control the build.
3. **No skeptical caveats.** Plan-B reads as confident execution; Plan-A's §10 caveats (vendor abstraction limits, sub-agent false-positive risk, no SLO for the registry) are the kind of self-criticism a reviewer needs.
4. **No verification ledger.** Plan-B doesn't show evidence it read the existing skills or tools. Plan-A's §1 ledger lets a reviewer trust the inputs.
5. **`network_diag` description is thin.** Plan-B says "DNS, TLS, connectivity, fundamental troubleshooting" but doesn't enumerate command set or auth model. Worth fleshing out (done below).
6. **Plan-B's `change-management` blast-radius classification numbers are unjustified** ("<1% users" → L2; "1-10%" → L2 + notification). Where do these come from? Could be reasonable defaults but should be flagged as configurable. **Add to integrated open questions.**
7. **Plan-B's "Auto-Rollback Triggers" (>2x baseline error rate, >3x P99 latency)** are *dangerous* without a stronger guard: a single bad metric reading at 2.01x triggers a rollback even if recovery is already happening. Need MWMA / persistence-required conditions. **Add to integrated guardrails.**

### 1.3 Where they AGREE (= high confidence in those items)
1. ✅ `log_query` is the #1 missing tool
2. ✅ `incident-response` is the #1 missing skill
3. ✅ `change-management` is the #2 missing skill
4. ✅ Loki-first is the right backend for `log_query` (matches existing Mimir/Prometheus stack assumption)
5. ✅ The 2 existing skills are healthy and need *enhancements*, not rewrites
6. ✅ The 7 existing tools are healthy
7. ✅ "What was deployed" is a critical missing question the agent currently can't answer

---

## 2. Integrated proposal

### 2.1 NEW tools (3 — Plan-B's set wins)

#### Tool 1: `log_query` (Loki-first, abstraction-via-env-var) — Plan-B section 1.1 + Plan-A's open question on backend
- **Files**: `tools/log_query/{tool.json, executor.py}`
- **Backend**: Loki by default (via env vars `LOKI_URL`, `LOKI_AUTH_TOKEN` / `LOKI_BEARER_TOKEN`, `ASAP_TOKEN` fallback). Multi-backend abstraction explicitly **deferred** — caveat §10.3 in Plan-A applies (single abstraction across LogQL/SPL/ES/CloudWatch is leaky)
- **Actions**: `query_range`, `query_instant`, `tail`, `labels`, `label_values`, `series`, `volume`, `stats` (8 actions; mirrors Loki API surface)
- **Executor pattern**: Pattern A (read-only, like prometheus_query)
- **Risk**: All L3 autonomous (read-only)
- **Safety guardrails** (Plan-B's set + Plan-A's pagination concern):
  - Block `{}` selector (full table scan)
  - Confirm if estimated >50k lines
  - Confirm if `--since > 7d`
  - Tail capped at 60s
  - Hard `--limit` ceiling 5000
- **API mappings**: see Plan-B §1.1 endpoint table
- **Effort**: 2 dev-days

#### Tool 2: `cicd_pipeline` (GitHub Actions + ArgoCD) — Plan-B section 1.2
- **Files**: `tools/cicd_pipeline/{tool.json, executor.py}`
- **Backends**: GitHub Actions + ArgoCD (selected via `--provider`)
- **Actions** (by provider):
  - GitHub Actions: `list_runs`, `get_run`, `get_run_logs`, `list_artifacts`, `rerun_workflow`, `cancel_run`
  - ArgoCD: `list_apps`, `get_app`, `get_app_history`, `sync_app`, `rollback_app`, `get_app_manifests`, `get_app_logs`
- **Executor pattern**: Pattern B (read + confirmed-write)
- **Risk classification**: read=L3, rerun/cancel=L2, sync/rollback=L1
- **Safety guardrails** (Plan-B + integration additions):
  - `sync_app --prune` always L1
  - `rollback_app` always L1
  - `rerun_workflow` rate-limited to 3/hr
  - **NEW (Plan-A): rollback only after RCA hypothesis declared** (gated by `incident-response` skill)
- **Auth**: `GITHUB_TOKEN`/`GITHUB_API_URL`; `ARGOCD_SERVER`/`ARGOCD_AUTH_TOKEN`
- **Effort**: 3 dev-days

#### Tool 3: `network_diag` (CLI passthrough) — Plan-B section 1.3, expanded
- **Files**: `tools/network_diag/tool.json` only (no executor — same pattern as `kubernetes_ops`)
- **Commands** (all read-only diagnostic, autonomous L3):
  - `dns_lookup <hostname> [record_type]` — via `dig`
  - `dns_trace <hostname>` — `dig +trace`
  - `tls_check <host:port>` — cert chain + expiry via `openssl s_client -showcerts`
  - `tcp_check <host:port>` — single connect via `nc -vz`
  - `http_check <url> [--header K=V ...]` — single GET with `curl -sI -w '%{http_code} %{time_total}'`
  - `traceroute <hostname>` — `traceroute` (or `mtr -r` if available)
  - `mtu_check <hostname>` — `ping -c 5 -M do -s 1472 <host>` (probe path MTU)
- **Risk**: all READ / L3 autonomous
- **Why CLI-passthrough not API**: these are universally available shell commands; no value adding HTTP layer
- **Effort**: 0.5 day (just tool.json content)

### 2.2 NEW skills (2, with chapters)

#### Skill 1: `incident-response` — combines Plan-A §4.1 + Plan-B §2.1 + chapters for oncall/post-mortem
- **Files**: `skills/incident-response/SKILL.md` + `references/`
- **Structure** (adopting Plan-A's 3-layer architecture):
  - `SKILL.md` (~600 lines): mindset, autonomy levels, severity-classification decision tree, mitigation ladder, hard guardrails, communication protocol, dispatch tables. Follows AI-150 pattern.
  - `references/severity-classification.md`: Plan-B's 4-row severity table expanded with examples + Plan-A's blast-radius criteria
  - `references/mitigation-ladder.md`: Plan-A's "smallest mitigation first" ladder + Plan-B's mitigation decision tree
  - `references/comms-templates.md`: status update templates by severity (Sev1: 15min, Sev2: 30min, Sev3: 1hr)
  - `references/handoff-checklist.md`: shift-handoff during active incident (originally Plan-A's `oncall-shift` skill, demoted to chapter)
  - `references/postmortem-template.md`: blameless RCA structure (originally Plan-A's `post-mortem` skill, demoted to chapter)
  - `references/failure-mode-dispatch.md`: Plan-B's symptom→cause→action table, expanded
  - `references/evidence-collection.md`: Plan-A §4.1 step 1 ("reconstruct timeline from evidence")
- **Tools used**: `opsgenie_manage`, `alertmanager_query`, `log_query`, `prometheus_query`, `grafana_manage`, `kubernetes_ops`, `cloud_ops`, `cicd_pipeline`, `network_diag`
- **Hard guardrails (Plan-A's anti-patterns + Plan-B's set, deduplicated)**:
  - NEVER mitigate before declaring a working hypothesis
  - NEVER close Sev1 without human confirmation
  - NEVER silence alerts during an active Sev1
  - NEVER skip post-mortem for Sev1/Sev2
  - NEVER let an incident drift past shift-end without a structured handoff doc
  - NEVER use blame language in a post-mortem
  - **NEW**: Auto-rollback triggers MUST require sustained N-second persistence (e.g. error rate > 2x baseline for ≥120s) — no single-reading triggers
- **Effort**: 3 dev-days

#### Skill 2: `change-management` — Plan-B §2.2 + Plan-A's cross-cutting concerns
- **Files**: `skills/change-management/SKILL.md` + `references/`
- **Structure**:
  - `SKILL.md` (~400 lines): change classification, deploy-window check, blast-radius assessment, canary criteria, auto-rollback policy, hard guardrails
  - `references/change-classification.md`: reversible-no-data-loss / reversible-with-data-loss / irreversible matrix
  - `references/blast-radius-criteria.md`: Plan-B's 4-row table BUT with the numbers (`<1%`, `1-10%`, `>10%`) flagged as `# CONFIGURE: tune to your traffic distribution`
  - `references/canary-promotion.md`: Plan-B's gating criteria (error rate ≤ 1.1× baseline; P99 ≤ 1.1× baseline; no new error types; budget burn stable) + persistence requirement
  - `references/auto-rollback-triggers.md`: Plan-B's set with Plan-A-style WARN: "These triggers MUST be combined with a persistence requirement (≥120s sustained) to avoid flapping rollbacks"
  - `references/deploy-windows.md`: change-freeze policy template
- **Tools used**: `cicd_pipeline`, `kubernetes_ops`, `prometheus_query`, `grafana_manage`, `terraform_ops`, `cloud_ops`
- **Hard guardrails**:
  - NEVER `terraform apply` without saved plan-file reference
  - NEVER `argocd sync --prune` without human approval
  - NEVER auto-rollback Terraform changes (always L1)
  - NEVER deploy during active change freeze without explicit exception approval
  - **NEW (Plan-A)**: Two-person rule for irreversible ops (delete, force-unlock, terminate, drop-table, IAM-change)
  - **NEW (Plan-A)**: Audit trail emission required (who/what/when/why/before/after) for every mutation
  - **NEW (Plan-A)**: Rollback plan declared BEFORE the change, not after it fails
- **Effort**: 2 dev-days

### 2.3 NOT shipped as standalone (deferred / demoted)

| Plan-A item | Decision | Rationale |
|---|---|---|
| `trace_query` tool | **Defer to Phase 6+** | No skill currently consumes traces; both observability skills work fine without traces today; premature build |
| `scm_ops` tool | **Replaced by `cicd_pipeline`** | Plan-B's narrower CI/CD-focused tool is more deliverable; native git ops remain shell-accessible |
| `oncall-shift` skill | **Demoted to `incident-response/references/handoff-checklist.md`** | <200 lines of content; standalone skill would over-fragment |
| `post-mortem` skill | **Demoted to `incident-response/references/postmortem-template.md` + `evidence-collection.md`** | Same rationale |
| `cloud_ops` rename | **Defer rename + GCP/Azure stubs** | Plan-B's "add GCP via `--provider` parameter" is the cleaner path; no rename needed |

### 2.4 Tool ENHANCEMENTS (Plan-B's 5 + Plan-A's surgical additions)

| Tool | Plan-B addition | Plan-A addition | Combined effort |
|---|---|---|---|
| `kubernetes_ops` | Helm read+rollback, pod debug exec, resource governance (PDB, NetworkPolicy, ResourceQuota) | none | 0.5d |
| `prometheus_query` | `template_query` action (golden_signals/RED/USE/error_budget/burn_rate templates), metric type metadata | + `exemplar_query` action (returns trace_ids); + tests/ dir | 1d |
| `cloud_ops` | GCP support via `--provider`, cost analysis (AWS Cost Explorer; GCP Billing) | none | 1d |
| `opsgenie_manage` | `shift_handoff` composite action; `alert_analytics` (MTTA/MTTR by priority/team) | + pagination on list ops; + idempotency_key on creates | 1d |
| `grafana_manage` | `slo_dashboard_template`, `loki_panel_template` (local computation, returns Grafana JSON) | none | 0.5d |
| `alertmanager_query` | (Plan-B did not enhance) | + pagination on `list_silences`; + `idempotency_key` on `create_silence`; + `test_silence` (dry-run matchers) | 0.5d |

**Total enhancement effort**: 4.5 dev-days

### 2.5 Skill ENHANCEMENTS (Plan-B's set + Plan-A's composition glue)

#### `infrastructure-ops` SKILL.md
- Plan-B additions: Workflows 2.9 (Helm), 2.10 (Cost), 2.11 (Multi-Cloud Health); SOP-008 (Helm Drift), SOP-009 (Cost Anomaly); cross-tool Pattern E (Cost-aware scaling)
- Plan-A additions: cross-skill composition section ("This skill works WITH `incident-response` when...")
- Plan-A architecture: split inline SOPs into `references/<sop-name>.md` files BEFORE adding new SOPs
- Effort: 1 day

#### `sre-observability` SKILL.md
- Plan-B additions: `log_query` in frontmatter; tools-table row; Workflow 2.8 (log-based investigation), 2.9 (RED), 2.10 (USE); Sections 3.9 (RED templates), 3.10 (USE templates), 3.11 (log-metric correlation), 3.12 (runbook integration); cross-tool Pattern 5
- Plan-A additions: cross-skill composition section; split `multi-tenant-mimir` and `data-volume-safety` math into `references/`
- Plan-A architecture: same 3-layer split before adding
- Effort: 1 day

### 2.6 Architecture / cross-cutting (Plan-A's Phase 0, mandatory FIRST)

These ship BEFORE any skill or tool change above. Without them, the new skills/tools land in the wrong shape and pay rework cost later.

1. **3-layer split for existing 2 skills** (Plan-A §5.1) — 1 day
2. **`CONTRIBUTING.md`** at repo root (Plan-A §5.10) — 0.5 day
3. **`GLOSSARY.md`** (vendor ↔ generic mapping) (Plan-A §5.9) — 0.25 day
4. **Cross-skill composition map** in every SKILL.md (Plan-A §5.2) — 0.25 day
5. **`registry.json`** auto-generated index (Plan-A §5.11) — 0.25 day
6. **Ops-log requirement** added to every SKILL.md (Plan-B §5.2) — 0.25 day

**Total Phase 0 effort**: 2.5 dev-days

---

## 3. Sequencing & effort

### Phases (in dependency order)

| Phase | Items | Effort | Dependencies | Ships |
|---|---|---|---|---|
| **0 — Foundation** | 3-layer split + CONTRIBUTING + GLOSSARY + composition map + registry.json + ops-log requirement | **2.5d** | none | ✅ Refactored skills, contributor docs |
| **1 — Critical missing tool** | `log_query` (Loki) | **2d** | Phase 0 | ✅ Agent can search logs |
| **2 — Incident-response skill** | `incident-response` SKILL.md + 8 references/ files | **3d** | Phase 1 | ✅ End-to-end paging→handoff orchestration |
| **3 — CI/CD tool** | `cicd_pipeline` (GH Actions + ArgoCD) | **3d** | Phase 0 | ✅ Agent can answer "what was deployed?" |
| **4 — Network diagnostics** | `network_diag` CLI passthrough | **0.5d** | Phase 0 | ✅ DNS/TLS/connectivity checks |
| **5 — Change-management skill** | `change-management` SKILL.md + 5 references/ files | **2d** | Phase 3 | ✅ Deploy gating + canary discipline |
| **6 — Tool enhancements** | k8s+helm, prom+templates+exemplar, cloud_ops+gcp, opsgenie+handoff, grafana+SLO, alertmanager+pagination | **4.5d** | Phase 0 (parallel with phases 1-5) | ✅ Existing tools fill capability gaps |
| **7 — Skill enhancements** | infra-ops + sre-obs additions | **2d** | Phases 1, 6 | ✅ Existing skills consume new capabilities |

**Total: ~14 dev-days (~3 weeks for one engineer)**

### MVP path (~7.5 days, ~2 weeks)
**Phase 0 + 1 + 2 + 4** — foundation + log_query + incident-response + network_diag.

This delivers:
- Agent can correlate metrics ↔ logs (the #1 missing capability)
- Agent has a structured incident-response orchestration skill
- Agent can run DNS/TLS/connectivity diagnostics
- Existing skills get refactored into the maintainable 3-layer pattern

What MVP defers:
- CI/CD visibility (`cicd_pipeline`) — agent can't see deployments
- Change-management skill — agent has no gate for routine changes
- Tool enhancements (Helm, GCP, query templates, etc.)

### Recommended path
**Full 14-day plan over 3 calendar weeks**, with Phase 6 enhancements done in parallel with Phases 2/3/5 if a second engineer is available.

---

## 4. Open questions (Plan-A's 8 + 4 new from integration)

| # | Question | Why it matters | Default if unanswered |
|---|---|---|---|
| 1 | Single-cloud or multi-cloud deployment? | Drives whether Phase 6's GCP support is critical or deferrable | Single-cloud (AWS); GCP is bonus |
| 2 | Runtime auto-loads executor.py? | Drives `tests/` directory wiring | Assume runtime auto-discovers; pytest-native |
| 3 | Slack only or Slack + Teams? Jira only or Jira + GitHub Issues? | `incident-response` skill's templates depend | Assume Slack + Jira; document genericized |
| 4 | Loki, Splunk, Elasticsearch, or CloudWatch Logs? | Drives `log_query`'s default backend | Loki (matches Mimir/Prometheus assumption) |
| 5 | `cicd_pipeline` covers GH Actions + ArgoCD only, or also Spinnaker / Jenkins / GitLab? | Plan-B picked GH+Argo; if your org uses Spinnaker, this needs extension | Plan-B's pick (GH+Argo); Spinnaker as Phase 8 |
| 6 | Two-person approval inline or external (PR/ticket)? | Drives `change-management` gate encoding | External; skill emits request, doesn't accept inline |
| 7 | Existing post-mortem template (Confluence/wiki)? | If yes, reference it | No; ship Markdown template |
| 8 | Chat-ops policy: agent posts or agent suggests? | Affects autonomy levels in `incident-response` | Suggest by default; per-deployment override |
| **9 (NEW)** | Are Plan-B's blast-radius % cutoffs (`<1%`, `1-10%`, `>10%`) right for your traffic distribution? | If your service has 1000 tenants of 1 user each, "<1%" is irrelevant; if you have 5 tenants of millions of users each, "<1%" is misleading | Flag as configurable in the SKILL.md |
| **10 (NEW)** | Is Plan-B's auto-rollback trigger (`>2x baseline error rate`) acceptable as a single-reading trigger, or must it be sustained for ≥120s? | A single-reading trigger flap-rolls during normal noise; a sustained trigger may take too long during real incidents | Sustained for ≥120s — see §2.4 guardrail |
| **11 (NEW)** | Should `log_query` default to LogQL syntax or accept a `--syntax` parameter for future Splunk/SPL/CloudWatch Insights? | Plan-A flagged the multi-backend abstraction as leaky (§10.3 caveat); decision needed BEFORE Phase 1 | Loki-first; defer multi-backend abstraction; expose `--raw_query` escape hatch |
| **12 (NEW)** | Is `incident-response` allowed to call `cicd_pipeline rollback_app` directly, or must it always route through `change-management`'s gates? | The two skills could conflict on rollback protocol | Route through `change-management` for ALL deploy-state mutations, even mid-incident — preserve audit trail |

---

## 5. Skeptical caveats (Plan-A's 10 preserved + 3 new)

1. **AI-150 architecture isn't free.** Splitting SKILL.md → SKILL.md + references/ adds navigation cost. For skills <500 lines, may be over-engineering. Apply the split for the existing 2 (1100+ lines each) and for the new `incident-response` (~600 lines). `change-management` (~400 lines) is the borderline case.

2. **Vendor-neutral `log_query` is a fiction at scale.** Loki LogQL ≠ Splunk SPL ≠ ES Query DSL ≠ CloudWatch Insights. Realistic implementation needs a `--raw_query` escape hatch for the 20% the abstraction can't model.

3. **`cicd_pipeline rollback_app` and `incident-response`'s "smallest mitigation first" can conflict.** During a Sev1, the incident skill may call rollback as the first mitigation; the change-management skill says rollback is L1 (human-approval-required). Resolve by: change-management's L1 gate ALWAYS holds, but the gate can be pre-cleared by a paged on-call's explicit approval comment in the incident channel (audit-trail-preserving alternative to inline approval).

4. **Plan-B's `network_diag` doesn't address allowlist/firewall friction.** In real deployments, the agent may not be able to reach internal hosts because of network policy. Document as a known limitation; suggest using `kubernetes_ops exec` as a fallback to run the diagnostic FROM inside the affected pod.

5. **`opsgenie_manage shift_handoff` returns "current on-call + open alerts + recent incidents" — but doesn't carry forward investigation state.** A shift change mid-investigation needs a structured handoff doc (see `incident-response/references/handoff-checklist.md`), NOT just a tool action.

6. **Plan-B's Phase 4 skill enhancements assume the new tools (`log_query`, `cicd_pipeline`) are integrated and stable BEFORE the existing skills reference them.** Phase 4 in our integrated plan is correctly numbered 7 (after Phases 1-6 ship the prerequisites).

7. **Tool count is approaching the upper edge of what an agent can navigate effectively.** Going from 7→10 tools is fine; going to 15 will need a tool-tagging system to help the agent narrow down quickly.

8. **No formal SLO defined for the registry itself.** What's the success criterion? "Agent resolves X% of pages without help"? "Agent produces Y post-mortems/week with ≥Z reviewer approval rate"? Define BEFORE Phase 0 starts.

9. **`change-management`'s auto-rollback math assumes baseline metrics exist and are stable.** New services or services with high natural variance will trigger false rollbacks. Mitigation: require ≥7 days of baseline data before auto-rollback gates activate; flag warning if not met.

10. **My "industry-standard SRE coverage" came from one direct-knowledge pass.** Anchored on Google SRE Book + Workbook + DORA but no specific chapter cites. A reviewer with deeper SRE practice background should pressure-test §4 of Plan-A and §2 of Plan-B before commitment.

11. **(NEW) Plan-B's `shift_handoff` action is also implemented as a chapter in `incident-response`.** This creates two implementations of the same concept — one as a tool action (Plan-B), one as a skill reference (integrated). Decision: keep BOTH but ensure the skill reference instructs the agent to invoke the tool action FIRST, then layer narrative context.

12. **(NEW) Plan-B's `_template_query` action in prometheus_query has placeholder substitution risk.** If template uses `${SERVICE}` and user passes `service="api"; drop table"` the substitution could create injection-shaped queries. PromQL doesn't have SQL-style injection but parser errors could mask intent. Sanitize input strictly to `[A-Za-z0-9_-]+` before substitution.

13. **(NEW) Phase 6's tool enhancements are listed as parallelizable, but `prometheus_query exemplar_query` only delivers value once `trace_query` exists** (which we deferred). Decision: still ship `exemplar_query` (it returns trace IDs which can be fed manually to a tracing UI) but lower priority within Phase 6.

---

## 6. Answer to the "pick one plan" question

### **If forced to pick exactly one plan as-written, I would choose Plan-B** (the alternative, `stateful-beaming-dusk.md`).

#### Why Plan-B beats Plan-A as a standalone deliverable
1. **More concrete and shippable.** Specific endpoint mappings, executor pattern naming, per-action risk classifications. A new engineer could start coding from Plan-B; Plan-A would need a "design doc" round first.
2. **Better tool selection.** `cicd_pipeline` (focused GH+Argo) is more deliverable than `scm_ops` (vague vendor-neutral). `network_diag` (which Plan-A missed entirely) is a high-value low-effort addition.
3. **Better tool enhancement specificity.** Plan-B says "add `helm list/get values/history/rollback` to kubernetes_ops"; Plan-A says "genericize the cloud_ops name." One is buildable, one is brochure.
4. **Right-sized skill count.** 4 new skills (Plan-A) over-fragments; 2 new skills (Plan-B) is the right size for first delivery.
5. **Concrete blast-radius / canary / auto-rollback criteria.** Plan-A talked about these as principles; Plan-B gave you numbers.

#### Why Plan-A still beats Plan-B as a standalone deliverable
1. **Phase 0 architectural foundation.** Plan-B builds first, refactors later — this is a known anti-pattern. Plan-A's "refactor first" would save 2-3 days of rework.
2. **Open questions / skeptical caveats.** Plan-A's §9 + §10 are essential risk control. Plan-B reads as confident execution and would over-commit.
3. **Verification ledger.** Plan-A's §1 cited every file read; Plan-B doesn't show its inputs.
4. **Effort estimates as days.** Plan-B's lines-of-code is harder to plan against than Plan-A's day-counts.

#### The honest gap
**Plan-B's specificity is a much bigger win** than Plan-A's discipline. A specific-but-flawed plan is closer to "ready to build" than a disciplined-but-vague plan. The discipline can be added on top in 1-2 review rounds; the specificity has to be earned through hours of file reading + API documentation lookup.

#### **But the real recommendation: pick neither standalone — pick the INTEGRATED v2.**
The integration costs nothing (it's just merging two completed plans) and delivers strictly better than either:
- Plan-B's specificity ✓
- Plan-A's Phase 0 sequencing ✓
- Plan-A's open questions + caveats ✓
- Plan-A's verification ledger ✓
- Plan-B's tool enhancement detail ✓
- Both plans' shared insights (log_query #1, incident-response #1, etc.) ✓
- Three NEW guardrails surfaced only during integration (sustained auto-rollback, PromQL template injection sanitization, change-management gate during incidents)

**TL;DR: pick INTEGRATED v2. If only one of the two original plans, pick Plan-B.**

---

## 7. Recommended next step

1. ✅ **30-min plan review** with whoever owns the registry. Lock in:
   - Approve the 3 new tools + 2 new skills (no scope creep)
   - Answer §4 questions 1, 3, 4, 5 (highest-priority — they unblock Phase 1)
   - Define 2-3 measurable outcomes (§5 caveat 8)
   - Confirm Phase 0 (refactor BEFORE building)
   - Pick MVP (~7.5d) vs full plan (~14d)
2. ✅ **Once locked in, build Phase 0 as a single PR** — refactor + CONTRIBUTING + GLOSSARY + composition glue
3. ✅ Each subsequent phase = 1-3 PRs, each reviewable in <30 min

---

## Appendix — Verification trail for v2

Files verified directly during this integration session (above what Plan-A's appendix lists):
- `/Users/tchen7/.claude/plans/stateful-beaming-dusk.md` (390 lines, full read incl. middle 100-line gap)
- `tools/kubernetes_ops/tool.json` (re-grep'd for "helm" — empty, confirming Plan-B's gap claim)
- `skills/sre-observability/SKILL.md` (re-grep'd for "log_query|loki|log-metric" — empty, confirming Plan-B's enhancement need)
- `tools/cloud_ops/tool.json` (re-confirmed AWS-only, validating Plan-B's GCP-add proposal)

Plan-A's verification ledger remains valid for everything else.
