# H1 2026 Non-Code Work Artifacts — Jin Yang (MRS) & Junjie Yang

**Prepared:** 2026-07-10
**Window:** H1 2026 = **Jan 1 – Jul 10, 2026** (items just outside the window are marked *pre-window* for continuity).
**Scope:** NON-code artifacts only — projects/tasks, planning & design docs, Workplace posts, wikis, meeting notes, roadmap/OKRs. (Diffs are cited only as corroborating evidence of what a project is, not as deliverables.)
**People:**
- **Jin Yang (MRS)** — `jinyang29`, FBID 740754461, SWE, MRS Platform · Algorithms Team.
- **Junjie Yang** — `junjieyang`, FBID 100004417397095, Research Scientist, MRS Platform · Algorithms Team.
- Both report to Director **Hong Li** (`hongli`, FBID 100027613488753).

**Sources:** `meta tasks.task` CLI (owner/creator lists + task descriptions) and Meta internal knowledge search (posts, wikis, Google Docs, meeting notes). The task CLI worked this pass (an OAuth warning was present and ignored).

---

## ⚠️ Read first — disambiguation, method & confidence

- **"AURA" is overloaded at Meta.** This report concerns **MRS AURA** = *Adaptive User Representation & Reasoning Architecture*, a homegrown **user-modeling platform for ads ranking** (user-embedding towers → F3 features → ads head models). It is confirmed by first-party artifacts (Jin's tasks/diffs + the vision doc). **Two unrelated "AURA"s were seen and excluded:**
  - **"Project AURA & AET"** = Audit Engagement Tool triage bot (Workplace group `3519758598302734`) — *unrelated*.
  - **"Audience Infra Team — AURA pod"** (audience-infra update) — *separate, not attributed here*.
- **Noise filtering.** Both task lists are dominated by auto-generated tickets (DQ alerts, permission/ACL requests, MVAI MAST training-job age alerts, quota/Polymer/dataswarm bots). These are **excluded from "genuine work"** but **counted separately** below because they are a useful proxy for data-access footprint and # of training jobs.
- **Confidence conventions used per item:** **[Authored]** = first-party author/owner; **[Mentioned]** = only tagged/acknowledged; **[Auto-gen]** = machine-generated. Confidence = High / Medium / Low.
- **Headline finding:** For H1 2026, **Jin Yang's** non-code footprint is **large and first-party** (she owns the AURA feature-engineering + pipeline + debugging task tree). **Junjie Yang's** non-code footprint in-window is **thin** — his first-authored posts (CMSL/RankEvolve/RankGraph) all **predate** the window; in H1 2026 he shows up as **code + very heavy model training + acknowledgements** in others' posts. This is called out honestly in §3 and §7.

---

## 1. Genuine project tasks

### 1a. Jin Yang — genuine H1 2026 project tasks (all first-party: `owner=jinyang29`)

Her real work clusters into 4 project trees: **AURA feature engineering** (resource-planner/"mastercook" capacity tasks), **AURA model/pipeline dev**, **AURA↔Signals (SG) collaboration**, and **LLM-RecSys feature injection**.

| T-number | Title | Created | Status | Purpose (1-line) |
|---|---|---|---|---|
| **T264608477** | AURA Model Debugging and Develop | 2026-04-13 | IN_PROGRESS | Debugging plan for AURA V1 model (project "AURA V1 Debugging"; links the debug-plan doc). |
| **T264608621** | Automate the transformation & injection process | 2026-04-13 | OPEN | Automate AURA embedding transform → F3 feature injection. |
| **T263875305** | AURA F3 feature pipeline | 2026-04-08 | CLOSED | Stand up F3 feature source table + pipelines for AURA (project "E2E pipeline"). |
| **T265922691** | [LLM RecSys] Task 6: GDP Feature Availability Inventory | 2026-04-20 | CLOSED | Profile GDP feature tiers; rank by coverage×relevance; pick top-5 for **AURA user-tower injection**. |
| **T262015408** | Design SG input data use cases | 2026-03-29 | OPEN | AURA↔Signals collaboration — define signal input data use cases. |
| **T262015411** | Build signal data pipeline | 2026-03-29 | NO_PROGRESS | AURA↔Signals — build signal-data integration pipeline. |
| **T262015348** | Implement production monitoring | 2026-03-29 | CLOSED | AURA↔Signals — production monitoring. |
| **T262015352** | Complete capacity planning | 2026-03-29 | CLOSED | AURA↔Signals — capacity planning. |
| **T255119141** | [2026H1][DPA][AURA][AURA features-Batch_embedding] | 2026-02-11 | OPEN | Batch-embedding AURA features for **DPA** surface (capacity req). |
| **T254174547** | [2026H1][FAM][AURA][Batch-AURA features] | 2026-02-05 | OPEN | Batch-AURA features for **FAM** surface. |
| **T254171587** | New features for AURA [FAM] | 2026-02-05 | OPEN | New AURA features, FAM. |
| **T254165774** | [2026H1][IG][AURA][Batch-AURA features] | 2026-02-05 | OPEN | Batch-AURA features for **IG** surface. |
| **T254165040** | [2026H1][IG][AURA][AFL-AURA features] | 2026-02-05 | OPEN | AFL-AURA features, IG. |
| **T254163582** | New features for AURA [IG] | 2026-02-05 | OPEN | New AURA features, IG. |
| **T254007650** | [2026H1][DPA][AURA][Batch-AURA features] | 2026-02-04 | CLOSED | Batch-AURA features, DPA. |
| **T254006886** | [2026H1][DPA][AURA][AFL-AURA features] | 2026-02-04 | OPEN | AFL-AURA features, DPA. |
| **T253999036** | [2026H1][FAM][AURA][AFL-AURA features] | 2026-02-04 | OPEN | AFL-AURA features, FAM. |
| **T253811824** | [2026H1][AURA][AFL-AURA features][online EBF input only] | 2026-02-03 | CLOSED | AFL-AURA features restricted to online-EBF input. |
| **T253133957** | [2026H1][AURA][AFL-AURA features] | 2026-01-28 | CLOSED | First AFL-AURA feature capacity task of the half. |
| *T248999912* | New features for AURA [CAG] | *2025-12-17* | OPEN | *Pre-window* — CAG-surface AURA features (kick-off). |
| *T248953341* | New EBF features | *2025-12-17* | CLOSED | *Pre-window* — EBF feature groundwork feeding AURA. |

- **Confidence: High.** Authorship/ownership verified via `meta tasks.task describe` (owner=`jinyang29`; several authored by teammate `yajuanwang` for the SG-collaboration & LLM-RecSys trees but owned/executed by Jin). Surfaces covered: **DPA, FAM, IG, CAG**; feature families: **AFL-AURA, Batch-AURA, Batch_embedding, EBF**.
- Corroborating code (context only, not counted): `D95329503`/`D96946473`/`D101417317`/`D103030345` (AURA embedding-aggregation pipelines), `D96588314`/`D101388194` (16→8 AURA_USER_EMBEDDING F3 features), `D101661629` (pipeline-automation design docs), `D89734168`/`D93544868` (aura_nano exploration) — all "authored by @jinyang29".

### 1b. Junjie Yang — genuine H1 2026 project tasks

- **None found that are both in-window and non-noise.** His `owner` list (4,587 all-time) is ~all MVAI training-job alerts; his `creator` list (246 all-time) in H1 2026 is permission/ACL/package-pickup admin only. The single borderline item:
  - **T272418985** — "[DATA_PROJECT ACL] Request to change the size threshold for `mrs_algorithm` (Secure Group)" — 2026-05-21, CLOSED. *[Authored] admin, not a project deliverable.*
- **Pre-window genuine tasks** (for continuity, show his modeling focus): T225788653 "Remove sync point in CMSL model" (2025-05-28); T215355518 "Replace organic post ID with EEK" (2025-02-14); T212926953 "Add ar sparse signal" (2025-01-16); T193373967 "Full Contextual Mask for HSTU" (2024-06); T197734098 "Contextual feature enrich for IFR model" (2024-08).
- **Confidence: High** that in-window non-code tasks are essentially all noise; his in-window contribution is **code + training** (see §7).

### 1c. Auto-generated NOISE counts (H1 2026, `owner` lists) — reported separately

**Jin Yang (`jinyang29`)** — 73 owned tickets in-window; **~53 auto-generated noise**, ~20 genuine (above):

| Noise category | Count |
|---|---|
| DQ alerts (`user_id_similarity` / `user_pair_dimension`) | 20 |
| Permission / ACL access requests | 8 |
| Dataswarm pipeline errors/paused (incl. `aura_*` pipelines) | 9 |
| Quota enforcement (BCU / Storage / Workload Mgmt) | 8 |
| Entity-lifecycle / feature deprecation | 3 |
| Polymer / MonCR exemptions | 2 |
| "Migrate assets out of scope" | 2 |
| Misc admin (rotation, table auto-deletion, MPK21 welcome, security-ACL) | ~1 each |

**Junjie Yang (`junjieyang`)** — 263 owned tickets in-window; **~all noise**:

| Noise category | Count |
|---|---|
| **MVAI "MAST Training Job Package Age" alerts (MINOR/MAJOR/AGG)** | **207** |
| Unidash page deprecation | 1 |
| (remainder) other bot/admin | ~55 |

> The **207 MVAI training-job alerts** are themselves a signal: Junjie is running a very large number of MAST training jobs (`fire-junjieyang-*`) in H1 2026 — i.e., heavy active model training, consistent with a core modeling IC.

---

## 2. Planning / design docs

### 2a. ★ AURA vision & 26H1 roadmap doc — **LOADED** (primary planning artifact)
- **Title:** *"AURA: Meta's User Intelligence Engine — Adaptive Multi-Architecture User Modeling Platform"*
- **URL:** https://docs.google.com/document/d/1wvFJqDGRkN7F5h9BKvPuvhhuxyJ9DNg7vyIrayjEW38
- **Type/date:** Google Doc; active planning doc (references 26H1). **[Mentioned/contributed]** — team/lead-owned; **Jin Yang is a named POC** (author of the "Academic literature" appendix); "Shiying" is POC for the MRS user-modeling-tech overview. Confidence: **High** (full content read).
- **What it says (summary):**
  - **Vision/Goal:** unified, **homegrown user-modeling capability** powering personalization across Meta surfaces; leverage **cross-surface organic + ads signals**; adapt to drive engagement and **iRev** (starting with iRev); support an **LLM-driven future**; provide **reusable** UM components.
  - **Gaps it targets:** siloed organic-vs-ads user understanding; lack of segment-specific architectures; missing "world knowledge + engagement + social-graph" fusion.
  - **Strategy levers:** (1) combined data (ads+organic, AdsLlama rich reps); (2) model arch (longitudinal history via **ThemeMoE**; generative understanding); (3) knowledge around users (LLM-native "HLLM"-style; **RankGraph** user networks).
  - **Architecture v1 outputs:** embedding · distilled small model · LLM-native consumption proxy.
  - **Key research questions (Q0–Q4):** north-star tech stack; which organic data to bring in; does Theme-aware MoE beat status quo; does AdsLlama rich rep help; can we build UserLLM on top of ItemLLM/AdsLlama.
  - **Dependencies/synergy called out:** E2E enablement team, RankGraph tokens, **CMSL**, Ads Llama/semantic IDs, organic data.
  - (Full 26H1 priorities/OKRs table → see **§6**.)

### 2b. AURA V1 debugging / user-model development plan — **PERMISSION-DENIED (404)**
- **URL:** https://docs.google.com/document/d/1zfw3D7X2IeqXUKAYdNK88CqTg9COfMB1u6RM0UP7E68 (referred to as "Aura user model development"; a specific tab is linked from Jin's task **T264608477** as "A plan for the debugging process").
- **Status:** Could **not** be opened from this environment — `You do not have permission to access this file (404)`. **I am not guessing its contents.** What is known *externally*: it is a multi-tab AURA doc covering user-model development + a V1 debugging plan, and Jin's in-progress task **T264608477** ("AURA Model Debugging and Develop", project *AURA V1 Debugging*) points into it. Confidence on existence/linkage: **High**; on contents: **N/A (blocked)**.

### 2c. AURA pipeline-automation design docs (embedded in a diff, non-code deliverable)
- Two markdown design docs — `aura_offline_pipeline_automation.md` and `aura_realtime_pipeline_automation.md` — authored by Jin describing end-to-end AURA embedding-aggregation automation (MAST status → query → dataswarm → F3 injection). Delivered via **D101661629** (2026-04-20). **[Authored]** by `jinyang29`. Confidence: **High**.

---

## 3. Workplace posts

### 3a. First-authored by our two people — all **pre-window** (context)
No **in-window (Jan–Jul 2026)** Workplace post was found that is **first-authored** by either Jin or Junjie. Junjie's flagship authored posts all predate the window (listed for lineage):

| Title | URL | Date | Author role |
|---|---|---|---|
| RankEvolve-CMSL: Breaking the Heuristic Ceiling via Human-Guided Algorithm Evolution | https://fb.workplace.com/groups/228479108798071/permalink/1415954856717151/ | 2025-12-08 | **[Authored]** (Linfeng Liu, **Junjie Yang**, Tao Jia, Hong Li, Hong Yan) |
| CMSL — Constructive Multi-Sequence Learning | https://fb.workplace.com/groups/228479108798071/permalink/1399961228316514/ | 2025 (updated 2025-12-18) | **[Authored]** (**Junjie Yang**, Tao Jia, Hong Li) |
| [MC9 Proposal] CMSL | https://fb.workplace.com/groups/23907659715519923/permalink/25246037151682166/ | 2025-11-13 | **[Authored]** (CMSL v-team) |
| RankFM-Nano Next Frontier | https://fb.workplace.com/groups/228479108798071/permalink/1284042229908415/ | 2025-07-01 | **[Authored/contrib]** |
| Introducing RankGraph: A Comprehensive Graph AI System | https://fb.workplace.com/groups/228479108798071/permalink/1211321487180490/ | 2025-03-25 | **[Authored/contrib]** |

- Jin Yang: no first-authored Workplace posts found (in or pre-window). Her pre-MRS identity/Signals work appears only as **comments** on Signals-Matching posts (2024–2025), e.g. https://fb.workplace.com/groups/signalsmatching/permalink/1674355973440341/ (2025-03-22) — *[Mentioned/commenter]*, out of scope.
- Confidence: **High** on the authored/dates; **High** that no in-window first-authored post exists for either.

### 3b. In-window posts that **feature the workstream / acknowledge our people** — [Mentioned]
These are H1 2026 program posts about the *user-embeddings-for-ads / upstream-representation* space that AURA serves. Our people appear as **contributors/acknowledged**, not authors:

| Title | URL | Date | Link to our people |
|---|---|---|---|
| **LEGO: Modularized Redesign of CFR Main MTML Architecture** | https://fb.workplace.com/groups/1310468516911179/permalink/1685364566088237/ | 2026-07-09 | **[Mentioned]** — **Junjie Yang** in MRS acks; LEGO explicitly credits **CMSL** (Junjie's work) as a foundation. Avg **+1.26% offline NE** across 10 tasks; launched as Cargo 2026H1_V2 backbone. |
| Search Ads Ranking: H1 2026 Lookback & H2 2026 Lookahead | https://fb.workplace.com/groups/232072464319726/permalink/2098106657716288/ | 2026-07-01 | **[Mentioned]** — CMSL / MRS-Platform acknowledgements (incl. **Junjie Yang**). |
| Harnessing Organic User Embeddings to Improve Ads Ranking: 2025 Lookback | https://fb.workplace.com/groups/1033540429995021/permalink/26600397316215981/ | 2026-01-13 | **[Context]** — the exact charter AURA productizes (organic user embeddings → ads ranking). |
| Upstream Representation: LLaTTE User Model 2025 Summary & 2026 Outlook | https://fb.workplace.com/groups/1033540429995021/permalink/26558002710455442/ | 2026-01-08 | **[Context]** — LLaTTE user model; AURA's UniArch supports LLaTTE-Coformer. |
| [01/20/2026] Upstream Representation — Biweekly Update | https://fb.workplace.com/groups/559506492652524/permalink/1290915599511606/ | 2026-01-21 | **[Context]** — program cadence for the upstream-rep pillar. |
| WARP 2025 EoY Summary & 2026 Look Ahead | https://fb.workplace.com/groups/1033540429995021/permalink/26540014162254297/ | 2026-01-06 | **[Context]** — adjacent user-embedding-for-ads program. |

- Confidence: posts exist and dates are **High**; attribution to Jin/Junjie is **[Mentioned] only** (do **not** read as authored). Jin was **not** found mentioned in any of these.

---

## 4. Wikis

- **Auto-generated AURA code-doc wikis** (source-derived; not hand-authored by our people) — **[Auto-gen]**:
  - `aura_model_config.py` — https://www.internalfb.com/wiki/PUL/Projects/aps_models/Modules/exploration/aura_model/models/aura/aura_model_config.py/ (generated 2025-01-09, updated 2026-03-03) — AURA model config schema (WHEN/LSM arch, VQ, query-learning, per-entity user/mix/object configs).
  - `aura_uniarch.py` — https://www.internalfb.com/wiki/PUL/Projects/aps_models/Modules/exploration/aura_model/models/aura/experimental/aura_uniarch.py/ (2026-03-03) — AURA "UniArch" advanced sequence modeling (PMA / Coformer / LLaTTE-Coformer / DynamicConv; specialized & embedding-feature archs).
- Referenced (not owned by our people): `UserFM+RankFM-nano` feed-ranking wiki — https://www.internalfb.com/wiki/Feed-ranking/UserFM%2BRankFM-nano/ (cited by the AURA vision doc as the model to extend to ads).
- **No hand-authored AURA runbook / NE-tracking wiki owned by Jin or Junjie was found** in-window. Confidence: **Medium** (absence of evidence; these auto-gen pages confirm the AURA codebase but not personal authorship).

---

## 5. Meeting notes

- **None found.** A targeted search (`doc_type=meeting_note`, AURA/MRS user-modeling terms, Nov 2025 → Jul 2026) returned **0 results**. Either none are indexed/accessible to this account, or AURA planning lives in the Google Docs (§2) rather than meeting-note surfaces. Confidence: **High** that none are retrievable here; **cannot rule out** access-gated notes.

---

## 6. Roadmap / OKRs / goals (H1 2026)

Directly from the **AURA vision doc (§2a) — "26H1 Priorities" table** (team-level; Jin executes the feature-engineering slice, Junjie's CMSL is a cited synergy):

| Workstream (stack-ranked) | Surface | Near-term goal | Eng resource |
|---|---|---|---|
| **Tower User Modeling** w/ low-risk arch innovation (e.g. **ThemeMoE**) | Ads Ranking | ~**0.12% GAS** (RO tech already 0.1–0.2% NE on IG CTR v0) | 2 + 1 PID |
| **Tower User Modeling w/ Data Enrichment** (semantic IDs, UD, graph tokens, organic) | Ads Ranking | ~**0.1% GAS** | 1.2 + 1 PID |
| **Generative User Modeling** (diffusion/generative sequence) | Ads Retrieval + Ranking | ~**0.05% GAS** | 1.5 + collab |
| **LLM-native User Modeling** | Ads Ranking | ~**0.05% GAS** | 1 PID + collab |
| **Adaptive routing/reasoning for user segments** | Ads Ranking | improved segment NE / ROI | 1 PID + collab |

- **Half goal:** ~**0.15% GAS in 26H1** (dependent on shipping pathway), targeting main head models (AF CMF, IG CTR, DPA, AF OC).
- **Training capacity ask:** **64× B200 hosts** (exploration) + **32× B200 hosts** (online training, 256 cards).
- **Shipping targets:** offline NE wins on head models; stretch launches into **IG CTR, DPA** (Tower UM) and **AF CMF, AF OC** (Data-Enrichment UM).
- Jin's **[2026H1]** capacity tasks (§1a) map onto the "Tower UM w/ Data Enrichment" lever (AURA features by surface: DPA/FAM/IG/CAG). Confidence: **High** (doc is explicit).

---

## 7. Bottom line & honest gaps

- **Jin Yang (MRS)** — **primary, first-party owner** of the AURA **feature-engineering + data-pipeline + V1-debugging** execution in H1 2026: ~20 genuine tasks across DPA/FAM/IG/CAG, an AURA↔Signals collaboration tree, LLM-RecSys GDP-feature injection into the AURA user tower, and authored pipeline-automation design docs. This **corrects** the earlier read that her MRS work was "nascent" — it is substantial. **Confidence: High.**
- **Junjie Yang** — in H1 2026 his **non-code** footprint is **thin**: no in-window first-authored posts/docs/wikis; his flagship posts (**CMSL, RankEvolve-CMSL, RankGraph, RankFM-Nano**) are all **2025 (pre-window)**. In-window he shows up as **(a)** heavy model training (**207** MVAI training-job alerts), and **(b)** an **acknowledged foundation** in others' H1 2026 posts (LEGO/CargoV2 credits **CMSL**; Search-Ads & Upstream-Rep posts ack MRS-Platform/CMSL). His in-window value is best evidenced by **code + training**, not artifacts. **Confidence: High on this characterization.**
- **Gaps / not verifiable here (stated, not guessed):**
  1. **AURA V1 debugging doc (`1zfw3D7X…`) is permission-denied (404)** — contents not reported.
  2. **No meeting notes** retrievable for AURA/MRS-UM in the window.
  3. **No hand-authored AURA wiki/runbook** owned by either person found (only auto-generated code-doc wikis).
  4. **Post attribution:** in-window program posts (§3b) only **mention/acknowledge** Junjie (CMSL/MRS acks) — none are first-authored by our people; Jin is not mentioned in them.
  5. **"AURA" name collisions** (AET-AURA, Audience-Infra-AURA) were actively excluded; if any external reference cites those, it is **not** this team's work.

*Prepared 2026-07-10 via `meta tasks.task` CLI + internal knowledge search. Every item above carries its URL/ID, date, an [Authored]/[Mentioned]/[Auto-gen] tag, and a confidence level; blocked/empty sources are flagged rather than inferred.*
