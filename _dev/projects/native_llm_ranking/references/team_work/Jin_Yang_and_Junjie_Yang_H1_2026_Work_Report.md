# H1 2026 Work Report — Jin Yang (MRS) & Junjie Yang (under Hong Li)

**Prepared:** 2026-07-10 · **Window:** H1 2026 = **Jan 1 – Jul 10, 2026** (items just outside the window are marked *pre-window* for continuity).
**Subjects (both direct reports of Director Hong Li, `hongli`, FBID 100027613488753, MRS Platform · Algorithms Team):**

| Person | Unixname / FBID | Role | Manager | Since | Oncall |
|---|---|---|---|---|---|
| **Jin Yang (MRS)** | `jinyang29` / 740754461 | Software Engineer | Hong Li | 2022-06-13 | — |
| **Junjie Yang** | `junjieyang` / 100004417397095 | Research Scientist | Hong Li | 2020-07-06 | Ads HSTU & Biography retrieval |

**Reporting chain (verified):** both → **Hong Li** (Research Scientist Director) → **Sri Reddy** (Director, SWE) → **Lars Backstrom** (VP Eng) → Chris Cox → Mark Zuckerberg.

**Method:** first-party enumeration and reads via `meta phabricator.diff list/describe/files`, `meta tasks.task list/describe`, `meta people.profile`, plus internal knowledge search (posts, wikis, Google Docs, SEVs), `analytics_notebook_search`, and direct loads of SEVs/docs. Every substantive claim is cited to a diff ID (`D…`), task (`T…`), SEV (`S…`), notebook (`N…`), or doc/post URL. Findings are tagged **[V]** verified from a primary artifact I read, **[I]** inferred/reported (secondary or naming), **[G]** gap/not verifiable here.

---

## ⚠️ Read first — disambiguations & confidence conventions

1. **"AURA" is an overloaded name at Meta.** This report concerns **MRS AURA** — Hong Li's team's homegrown **user-modeling / user-embedding platform for ads ranking** (user-embedding towers → aggregation → F3 features → ads head models). Its planning doc is titled *"AURA: Meta's User Intelligence Engine."* The exact acronym expansion is **not firmly pinned** — internal sources give both *"Adaptive User Representation & Reasoning Architecture"* and *"Ad User Representational Applications"* **[I]**; I therefore describe AURA by **what it does (verified)** rather than by its acronym. Two *unrelated* "AURA"s were seen and **excluded**: the Audience-Infra "AURA pod," and the "Project AURA & AET" audit bot.
2. **Two "Junjie Yang" FBIDs.** The active target is `junjieyang@meta.com` / **100004417397095** (status: current). The 2025 CMSL/RankGraph Workplace posts @-tag a **legacy account 100036123497022** which now resolves to *"Employee not found"* **[V]**. This is the same person pre-account-migration — corroborated because those posts co-author with his current manager (Hong Li) and skip/lead (Tao Jia), and all H1 2026 *operational* evidence (SEV mitigation, `fire-junjieyang-*` jobs, notebooks by author-id 100004417397095, diffs by FBID 100004417397095) ties to the current account. H1 2026 attributions below rest on that operational evidence, not on the legacy tag.
3. **Diffs undercount a Research Scientist's work.** Junjie's contribution is dominated by **model training/experimentation and research**, not diff volume — accounted for explicitly below.

---

# PART 1 — JIN YANG (MRS), SWE

### Snapshot
Jin Yang is the **data/pipeline engineer who productionized AURA user-embeddings into the ads-ranking feature stack** in H1 2026. Clear arc: **Jan–Feb = feature exploration (mostly not shipped)** → **Mar–Jun = productionization (mostly landed)**. ~86 diffs authored in-window (74 code + 12 admin/ACL); ~20 genuine project tasks spanning four ad surfaces (DPA/FAM/IG/CAG); **no publications** (engineering IC). Owns `DATA_PROJECT:mrs_platform_aura`.

## 1. Code contributions — the AURA embedding→feature pipeline

**Verified end-to-end flow** (from diffs read):
```
AURA model (//aps_models/exploration/aura_model; model 1035125311; WHEN / UniArch archs; trained on CMF / FB-Feed)
  → Dataswarm aura_embedding_aggregation[_avg | _realtime]  (3-day pooling of user & ad embeddings; carry-forward previous-day UNION ALL + LEFT ANTI JOIN; dedup to separable_id; job_id-pinned output)
  → Hive aura_user_embedding_source / prod_aura_output_table  (keys: separable_id; feature_name as partition; version_id, ds; embedding dim 128→64)
  → F3: 16 features AURA_USER_EMBEDDING_0..15 in fam_horizontal_ml/flexible_batch  (L2-normalized + FP16; ID_LIST; serving ads_ranking_features/ads_ranking)
  → injected as side-table features into DPA / FAM / IG ranking-model training
  (parallel retrieval signal: aura_knn_u2u → aura_v1_u2u user-to-user KNN)
```

| # | Workstream | Status | Representative diffs (date) |
|---|---|---|---|
| **A** | **AURA embedding data pipelines** (Dataswarm offline+realtime aggregation) — the core deliverable | **Shipped ✅** | D96946473 founding agg (3/17); D99750243+D99795511 previous-user carry-forward (4/6–4/7); D99908852 anti-join (4/7); D103465430 realtime `defer_ds`/config flags, 233 lines (5/1); D104938898 dedup to `separable_id` (5/12); D106032270 `version_id`/`job_id` filter (5/21); **D107554353 last AURA diff (6/4)** |
| **B** | **F3 feature registration & injection** (16 AURA user-embedding features) | **Shipped ✅** | D96587164 register `aura_user_embedding_source` TypedDataSource (3/14); D96588314 author 16 `AURA_USER_EMBEDDING_0..15` in `fam_horizontal_ml` (3/14→3/21); D97203454 auto-gen data model (3/18); D100268356 `user_id→separable_id` migration (4/9); D101388194 DSL update, **embedding dim 128→64** (4/17) |
| **C** | **EBF (Embedding-Based Feature) exploration** — InterestFM & Rankgraph feature variants on `onsite_conversion` | **Exploratory — did NOT ship ⚠️** | ~31 diffs across Jan–Feb (D92xxx–D94xxx); reps D93160255, D93126088 (Accepted but never committed). **0 landed** — this exploration *motivated* building the dedicated AURA source (A/B). |
| **D** | **Model baseline / training / NE validation** (support) | **Shipped (support) ✅** | D91390199 `shared_seq_offsets` fix, earliest AURA diff (1/24); D100244084 set up `aura_legacy` baseline vs UniArch, 2289 lines (4/9); D100743790 enable **NE checkpoint validation for model 1035125311** (Configerator, 4/13) |
| **E** | **Automation tooling** — a **Claude Code skill** to run the AURA injection pipeline end-to-end | **Built, NOT landed ⚠️** | D101661629 automation-plan design docs (4/20); D102212387 `run_aura_pipeline.sh` skill, 13 interactive params, ~1476 lines (4/23) — both left *Waiting For Author*; reviewer **Wei Zhang** pushed back (incl. a command-injection concern). Tracked by T264608621. |
| **F** | **UMS 3PD offsite-signals training-data pipeline** (CAPI / Signal-Growth collaboration) | **Shipped ✅** | D105982047 `ums_autoregressive_dedup_3pd_training_data`, 3-phase Dataswarm from `fct_offsite_signals_trace` (FOST); design by **Xiang Zhang** (CAPI Performance); "AURA SG Collaboration" (5/21→6/9) |
| **G** | **Identity/signals ops** (carry-over ownership) | Ongoing | Owner of recurring DQ on `ad_metrics.identity.user_behavior_model.user_id_similarity`; `aura_knn_u2u`→`aura_v1_u2u` u2u retrieval signal |
| **H** | **Admin / stewardship** (overhead) | — | 12 ACL "grant access" diffs for `DATA_PROJECT:mrs_platform_aura`; many permission/quota tasks |

**Volume (in-window):** 86 diffs total = **74 code** (73 fbsource + 1 Configerator) + **12 admin/ACL**. Code outcomes ≈ **30 landed/Closed vs 44 not-landed** (23 Unpublished, 13 Abandoned, 4 Needs Review, 2 Accepted-uncommitted, 2 WFA) → land rate ~41%, **bimodal** (Jan–Feb exploration ~0 landed; Mar–Jun productionization landed at a high rate). Active range D90834004 (1/15) → D107554353 (6/4). **[V]**

## 2. Projects & tasks / roadmap
~20 genuine owned tasks (`owner=jinyang29`), in four trees **[V]**:
- **AURA feature engineering** (`[2026H1][AURA]` capacity tasks) across **DPA / FAM / IG / CAG** surfaces and feature families **AFL-AURA, Batch-AURA, Batch_embedding, EBF** — e.g. T253133957, T254007650, T254165774, T255119141 (Jan–Feb).
- **AURA model dev + V1 debugging** — **T264608477** "AURA Model Debugging and Develop" (in-progress); **T263875305** "AURA F3 feature pipeline" (closed); **T264608621** "Automate transformation & injection."
- **AURA↔Signals (SG) collaboration** — T262015408/411/348/352 (authored by teammate `yajuanwang`, executed by Jin).
- **LLM-RecSys** — **T265922691** "GDP Feature Availability Inventory" → pick top-5 GDP features for **AURA user-tower injection** (closed).
- Authored the **AURA pipeline-automation design docs** (`aura_offline/realtime_pipeline_automation.md`, via D101661629).

**Roadmap context** — the **AURA vision / 26H1 doc** (*"AURA: Meta's User Intelligence Engine"*, [doc](https://docs.google.com/document/d/1wvFJqDGRkN7F5h9BKvPuvhhuxyJ9DNg7vyIrayjEW38)) sets a **~0.15% GAS half-goal** across main head models (AF CMF, IG CTR, DPA, AF OC), asks for **64+32 B200 hosts**, and names Jin as the "academic literature" POC. Jin's `[2026H1]` capacity tasks map onto the doc's **"Tower User Modeling with Data Enrichment"** lever. **[V]** (A second linked debugging doc `1zfw3D7X…` is **permission-denied [G]**.)

## 3. Research & publications
**None — honest negative.** Dedicated searches (publication keywords, `doc_types=user`, publication-request tasks, patents) surfaced **no paper or patent** for Jin Yang / `jinyang29`. Output is engineering, not publications. **[V]**
**Bento notebooks (H1 2026)** show the hands-on work: **N9952139** real-time F3 injection of `user_embedding_0–15` (feature IDs 3000003–3000018) into `ctr_mbl_feed` (3/21–4/7); **N9256413** F3 EBF gen validation/debug runbook (2/2–3/10); **N9544401** `signal_refinery` non-blocking dataset search helper (2/23–5/21). **[V]**

## 4. Impact & collaboration
- **Nature of impact in H1 2026 = enablement / productionization**, not a measured topline launch. AURA user-embedding features were built, registered, and injected into ranking-model *training*; **no shipped topline NE/GAS launch metric attributable to Jin was found in-window [G]** (consistent with the AURA doc treating 26H1 as the enablement/exploration half).
- **Owns `DATA_PROJECT:mrs_platform_aura`** — access requests from teammates (e.g. Wei Zhang, T268330019; Hantian Zhang; Bella Zhang) route to Jin as maintainer, i.e. Jin is the data-pipeline steward for AURA. **[V]**
- **Top reviewers / collaborators** (aggregated across 74 code diffs): **Chuanqi Xu** (`chuanqixu`, MRS Algorithms — #1 reviewer, likely pipeline/F3 tech lead **[I]**); **Xiang Zhang** (`xxzhang`, **CAPI Performance** — #2, authored the UMS 3PD design); **Yajuan Wang** (`yajuanwang`, **MRS Knowledge** — cross-org POC/lead for AURA user embeddings; reviews Jin's diffs; author of the SG-collab tasks); **Wei Zhang** (`weizhng`); **Shiying He** (`shiyinghe`); **Manpreet Singh Takkar** (`manpreet19`). Cross-team surface: **CAPI/Signal-Growth** (strongest), **Ranking AI / Ads AI Infra**, **horizontal_ml** feature library, **RankGraph** (consumed as an embedding *input*, not built by Jin). No AdsLlama code tie found. **[V]** except where marked.
- **Manager-field note:** several auto-generated ACL tasks list Jin's manager as *"Yajuan Wang"* — this is a **data-project attribution artifact, not HR.** Yajuan Wang is an IC Research Scientist on **MRS Knowledge** (0 reports; a different org). Jin's Workday manager is verified as **Hong Li**. **[V]**

---

# PART 2 — JUNJIE YANG, Research Scientist

### Snapshot
Junjie Yang is a **core ads-ranking model researcher** and the **owner of CMSL (Constructive Multi-Sequence Learning)**. His H1 2026 work is dominated by **model training/experimentation and research**, with a small but high-signal set of diffs. He owns a **revenue-critical production signal** and is on the **RankGraph V-team**, co-authoring the **RankGraph-2** paper (June 2026) with his own manager.

## 1. Code contributions
Only ~9 substantive diffs in-window (the rest are admin/ACL), but each is meaningful **[V]**:
- **NE-tracking / model-quality evaluation pipeline** (`tasks/ad_delivery/mrs_platform/ne_tracking_*.py`): 7 diffs **D98380670** "Add NE tracking" (3/26) → **D99464246** (4/3) → **D99701305** "Remove conv type filter" (4/6) → **D100272053** "Add more NE tracking" (4/9) → **D100419242** "use raw label column & correct gain formula" (4/10). It computes **Normalized Entropy** for candidate models (`ofm_v3`/`ofm_v4` **[I on names]**) vs `prod`, with gain = `100 * (model − prod) / prod` and conversion label `multi_labels[1000002]`. Reviewer **Zikun Cui** (`cuizk`).
- **New Dataswarm/Chronos pipelines** D99018172 / D99160752 (3/31–4/1).
- **MVAI "fire" app-layer** D91958039 "add a new fire layer" (`fire-app-lsr-cmslv0`, CFHG, 1/30) — links the *fire* training framework → MVAI → LSR-CMSL.
- **Baseline MAST launcher** D105034490 `mast_es_fm_2026_uhm.yaml`, ~910 lines (5/13, WIP).

## 2. Modeling & experimentation (the bulk of the work)
- **≥410 distinct `fire-junjieyang-*` MAST training jobs** evidenced in-window (via 207 auto-generated MVAI package-age alerts + notebooks) — i.e. very heavy, sustained model training. **[V]**
- His own notebooks prove what the fire jobs train: **N10471418** *"cmsl_gating_ne_compare"* (4/20–4/30) compares **CMSL gating** variants (v1, MoE, MoE+pointwise-gating) across MAST runs; **N9943909** CMSL distillation NE-gap + QPS analysis (3/20); **N9400969** ModelTracer NE comparison for HSTU/CMSL (2/11–3/17). These notebooks were **cloned/reused by teammates** (cuizk, jinghanj, ikalemaj) — Junjie's eval tooling is a team standard. **[V]**
- Consistent with his oncall (**Ads HSTU & Biography retrieval**) and CMSL/HSTU sequence-model focus.

## 3. Research & publications
| Paper | Venue / date | Confidence | Basis |
|---|---|---|---|
| **RankGraph: Unified Heterogeneous Graph Learning for Cross-Domain Recommendation** | RecSys **2025** (arXiv 2509.02942) | **High [V]** | Internal MRS Launch KB lists author "Junjie Yang, Meta MRS, **junjieyang@meta.com**" (unique email → our target); corroborated by his multi-year HGNN/graph-learning workstream. Reported prod impact +2.82% conversions. |
| **RankGraph-2: Lifecycle Co-Design for Billion-Node Graph Learning in Recommendation** | **June 2026 (in-window)** (arXiv 2606.18379) | **High [I]** | Sequel; internal author block lists MRS: Renzhi Wu, Zikun Cui, **Junjie Yang**, Tai Guo, **Hong Li** (co-authored with his own manager). Corroborated by a 6/22/2026 post naming the "RankGraph V-team (Renzhi Wu, Junjie Yang)." Slightly softer than RankGraph-1 (no individual email in the snippet). |

Plus **CMSL** and **RankEvolve-CMSL** (Workplace write-ups, authored 2025 with Tao Jia / Hong Li / Linfeng Liu) — his flagship model line; see §5.
*(arXiv IDs reproduced from internal records; external arXiv fetch was blocked, so not independently opened. No patents surfaced for either person, but the patent DB is not indexed by these tools — treat as "none surfaced," not "provably none." **[G]**)*

## 4. Projects & tasks
- **No in-window genuine *task* deliverables** — his owned task list is ~all auto-generated (207 MVAI training-job alerts; a few ACL). This is expected for an RS whose planning lives in code, notebooks, and docs, not Tasks. **[V]**
- **Production ownership (high-impact):** **SEV S642095** (detected 3/30, **mitigated by Junjie 4/1**) — *"lsr_cmsl_embedding_agg_encoded_ts_signal is lagging 4d"*; the SEV states **table daily revenue $5,900,882**, feeds 4 F3 batch features, and reassigns to Junjie **"as he is the CMSL owner."** **[V]**

## 5. Impact & collaboration
- **CMSL is credited as a foundation by downstream launches:** the **LEGO** redesign post (7/9/2026) explicitly credits **CMSL** and acknowledges Junjie; LEGO reported **+1.26% avg offline NE across 10 tasks** and shipped as the **Cargo 2026H1_V2** backbone. Search-Ads H1 lookback and Upstream-Representation posts also acknowledge CMSL/MRS-Platform (incl. Junjie). **[V]** (These are *downstream* metrics that build on CMSL, not Junjie's personal topline number.)
- **CMSL itself** reportedly delivered **~0.1145% eGAS across 5 ads head models** per internal summaries; the CMSL launch spans **late-2025→2026**, so in H1 2026 Junjie's role is best described as **owning/operating CMSL in production + continued experimentation**, rather than a fresh in-window launch. **[I]**
- **Collaborators / v-teams:** **CMSL co-owners** Xinjie Du (`jaydu`), Sheng Xu (`shengxu`), **Zikun Cui** (`cuizk`, also reviews his NE work); **Tai Guo** (`taiguoo`, reviewer + RankGraph-2 co-author); **Tao Jia** (`tjia`, RS Manager, CMSL/RankEvolve co-author); **Renzhi Wu** (`renzhiwu`, RankGraph V-team); cross-team **SG Signals Platform** (Minghao Wang) on RankGraph 3PD data. **[V]**

---

# PART 3 — How the two workstreams connect (under Hong Li)

Both sit inside **Hong Li's MRS Platform · Algorithms** charter of **user modeling & ranking-model innovation for ads**, and they are complementary:

- **Junjie (research → models):** builds the *modeling* techniques — **CMSL** multi-sequence learning, **RankGraph** graph learning, HSTU sequence models — and the **NE-tracking** infrastructure the team uses to judge model quality. Produces the models/embeddings.
- **Jin (engineering → productization):** builds the *data pipelines and F3 feature plumbing* (**AURA**) that turn user/ad embeddings into production ranking features, and operates them reliably.

They meet at the **embedding→feature boundary**: AURA consumes user embeddings and (via `aura_knn_u2u`) graph/retrieval signals of exactly the kind Junjie's RankGraph/CMSL lines produce, and the **AURA vision doc explicitly names CMSL and RankGraph as dependencies/synergies.** The shared quality metric across both is **Normalized Entropy (NE) / GAS** on ads head models (CMF, IG CTR, DPA, OC).

---

# PART 4 — Combined collaboration map

| Person | Unixname | Team | Relationship |
|---|---|---|---|
| Chuanqi Xu | `chuanqixu` | MRS Algorithms | Jin's #1 reviewer; likely AURA pipeline/F3 lead [I] |
| Xiang Zhang | `xxzhang` | CAPI Performance | Jin's UMS 3PD design partner (cross-team) |
| Yajuan Wang | `yajuanwang` | MRS Knowledge | Cross-org AURA user-embedding POC; reviews Jin's diffs; SG-collab task author |
| Wei Zhang | `weizhng` | MRS Algorithms (John Wang's squad) | Reviews Jin; AURA user-model dev |
| Shiying He / Manpreet Takkar | `shiyinghe` / `manpreet19` | MRS Algorithms | Jin's model-config/output reviewers |
| Zikun Cui | `cuizk` | MRS Algorithms | Junjie's NE reviewer + CMSL co-owner |
| Xinjie Du / Sheng Xu | `jaydu` / `shengxu` | MRS Algorithms | CMSL co-owners with Junjie |
| Tai Guo | `taiguoo` | MRS Algorithms | Junjie's reviewer + RankGraph-2 co-author |
| Tao Jia | `tjia` | MRS Algorithms (RS Manager, reports to Hong Li) | CMSL/RankEvolve co-author with Junjie |
| Renzhi Wu | `renzhiwu` | MRS Algorithms | RankGraph V-team with Junjie |
| John Wang | `johnwangzh` | MRS Algorithms (SWE Manager) | Manages the adjacent AURA/AdsLlama squad (Wei/Bella/Hantian/Shanshan) |

---

# PART 5 — Activity stats (in-window)

| Metric | Jin Yang | Junjie Yang |
|---|---|---|
| Diffs authored | ~86 (74 code / 12 admin) | ~19 (~9 substantive / ~10 admin) |
| Code land rate | ~41% (bimodal) | most substantive diffs Closed/landed |
| Genuine project tasks | ~20 (DPA/FAM/IG/CAG) | ~0 (RS work is in models/notebooks) |
| Auto-gen noise tickets | ~53 (DQ/ACL/quota/dataswarm) | ~207 (MVAI training-job alerts) |
| MAST training jobs | — | **≥410 `fire-junjieyang-*`** |
| H1 2026 notebooks | 3 (F3 injection, EBF gen, ds search) | 3 (CMSL gating/distillation NE) |
| Publications | 0 | RankGraph (2025); **RankGraph-2 (Jun 2026)** |
| Production ownership | `DATA_PROJECT:mrs_platform_aura` | **SEV S642095** ($5.9M/day CMSL signal) |

---

# PART 6 — Honest gaps & limitations

1. **AURA acronym** is not firmly pinned (two expansions in internal sources) — described by function instead. **[I]**
2. **No shipped topline NE/GAS launch metric** attributable to **Jin** in-window — H1 2026 is enablement/productionization for AURA. **[G]**
3. **CMSL's ~0.1145% eGAS** and RankGraph's +2.82% are reported in internal summaries and span the 2025→2026 boundary; they are **not clean, in-window, personally-attributed** numbers. **[I]**
4. **RankGraph-2** attribution is High but rests on sequel + manager/team co-authorship (no individual email in the snippet); **arXiv IDs were not independently opened** (external fetch blocked). **[I]**
5. **Permission-blocked / absent sources:** the AURA V1 debugging doc `1zfw3D7X…` is **404**; **no meeting notes** and **no hand-authored AURA/NE wiki** were retrievable; the **patent DB is not indexed**. Reported as gaps, not guessed. **[G]**
6. **Junjie FBID migration** (legacy 100036123497022 → current 100004417397095) — H1 2026 attributions rest on operational evidence tied to the current account. **[V]**
7. **`meta` CLI OAuth token was expired**; commands still returned data and were used, but a token refresh (`jf auth`) would allow re-verification of anything access-gated.

---

## Methodology & sources
`meta phabricator.diff list/describe/files` (diff enumeration + reads), `meta tasks.task list/describe` (task ownership + descriptions), `meta people.profile get/chain/reports` (org + identity), internal knowledge search (posts/wikis/Google Docs/SEVs), `analytics_notebook_search` (Bento notebooks by author-id), and direct SEV/doc loads. Investigation ran five parallel deep-dive agents (Jin code, Junjie modeling, tasks/docs/posts, AURA context/impact/collab, publications/notebooks), each producing an evidence-cited sub-report, followed by primary-source cross-verification of the highest-stakes claims (SEV S642095, CMSL, RankGraph-2, the Junjie FBID split, the Yajuan Wang manager field).

### Supporting detail files (same folder)
- `Jin_Yang_H1_2026_work_summary.md` — Jin diff-by-diff technical deep-dive.
- `Junjie_Yang_H1_2026_work_summary.md` — Junjie modeling/NE/CMSL deep-dive.
- `Jin_Yang_Junjie_Yang_under_Hong_Li_work_analysis.md` — non-code artifacts (tasks, docs, posts, wikis, OKRs).
- `AURA_project_context_and_collaboration.md` — AURA system context, impact, collaboration, Yajuan Wang resolution.
