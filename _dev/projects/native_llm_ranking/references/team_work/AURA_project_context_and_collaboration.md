# AURA — Project Context, Impact & Collaboration (H1 2026)

**Subjects:** Jin Yang (MRS) `jinyang29` (SWE) and Junjie Yang `junjieyang` (Research Scientist), both ICs on **MRS Platform – Algorithms Team** under Director **Hong Li** `hongli`.
**Prepared:** 2026-07-10 · **Author:** Tony Chen (`zgchen`)
**Purpose:** Establish the *system/project* context and the *collaboration network* (with evidence) behind these two engineers' work, to feed a factual H1 2026 work-summary report.

> **Companion note.** This supersedes two now-outdated caveats in `Jin_Yang_Junjie_Yang_under_Hong_Li_work_analysis.md`: (1) the `meta` people/org CLI **was accessible** this pass (org facts below are from direct `meta people.profile` queries), and (2) AURA — not visible in the prior pass — is now fully identified with primary docs, code, diffs and tasks.

## Evidence legend
- **[V] VERIFIED** — I read the source (a doc, diff, task, Workplace post, wiki, or ran the `meta` CLI).
- **[I] INFERRED** — reasoned from verified facts but not directly stated in a single source.
- **[G] GAP** — could not verify; flagged honestly.

---

## ⚠️ Critical disambiguation: there are (at least) three unrelated "AURA"s
This is the single biggest trust risk in this report. Do **not** conflate them.

1. **MRS AURA** — *"**A**daptive **U**ser **R**epresentation & Reasoning **A**rchitecture"*, Meta's homegrown **User Intelligence Engine / user-modeling platform** owned by **Hong Li's MRS Platform – Algorithms Team**. **This is the AURA that Jin and Junjie work on.** Code lives at `//aps_models/exploration/aura_model` (oncall `mrs_platform_algorithm`). **[V]**
2. **Audience-Infra AURA** — *"Ad User Representational Applications"*, a **different** Ads Infra / Audience Infra pod (POCs: Sarnab Poddar, Dhiraj Ramnani, Vishal Parekh, Haofeng Zou) doing cohort/audience embeddings (BlueMorpho, cohort generation). **Not Hong Li's team.** **[V]** (Workplace post "[🏛] AUDIENCE INFRA TEAM UPDATE: Introducing a new Pod- AURA"; wiki `AdsInfra/Events_Infra/Audience_Infra/.../AURA_Infra_%26_Use-cases`; `wut/word/?word=AURA`.)
3. **"Project Aura"** — a **Facebook/Messenger consumer-subscription** brand/design project (Super Like, custom app icons, fonts). Completely unrelated. **[V]** (Workplace post "Project Aura", BRD design forum.)

*(There is also "Auralis", a 3D-LLM effort — unrelated.)* Throughout this document, **"AURA" = definition #1** unless stated.

---

## Q1 — What is (MRS) AURA?

### What / Why (the problem it solves) — [V]
Primary source: **Google Doc "AURA: Meta's User Intelligence Engine — Adaptive Multi-Architecture User Modeling Platform"** (https://docs.google.com/document/d/1wvFJqDGRkN7F5h9BKvPuvhhuxyJ9DNg7vyIrayjEW38).

- **Vision:** a **unified, homegrown User Modeling capability** that unifies user state, representation, reasoning and multi-architecture modeling to power personalization across Meta — **starting with ads (iRev)**.
- **Problem it addresses:** today's user understanding is **"siloed"** across organic vs ads (blind spots), **lacks segment-specific architectures**, and doesn't combine world knowledge + cross-surface engagement + social-graph signals. AURA aims to fix this with combined data + better architectures + LLM/graph knowledge.
- **Outputs (3 consumption modes):** (1) **embeddings**, (2) a **distilled small model**, (3) an **LLM-native consumption proxy**.
- **26H1 priorities (from the doc):** Tower User Modeling with low-risk arch innovation (e.g. ThemeMoE), Tower User Modeling with **data enrichment** (AdsLlama semantic IDs, UD, graph tokens, organic data), Generative UM, LLM-native UM, and adaptive routing/reasoning for user segments. Named POCs in the doc include **Shiying** (MRS user-modeling tech overview) and **Jin** (academic-literature landscape).

### How (architecture: embeddings → aggregation → F3 injection → ranking) — [V]
This end-to-end shape is confirmed directly from code + Jin's diffs:

1. **Upstream model → user embeddings.** The AURA training model (`//aps_models/exploration/aura_model`, variants `aura` and `aura_uniarch`) is a **multi-task CTR/CVR model** with user-history modeling (VLE), LSM sequence summarization, and a **"WHEN"/UniArch mix tower**. It is deliberately designed so **all user-side information flows through a single "user embedding bottleneck"**, "critical for downstream v0 models that only consume user embeddings." **[V]** (wiki `.../aura_model/README`; `aura.py` wiki; diff **D100708290** "[aura] Add standalone SimpleWHENArch as alternative to UniArch in mix tower".) The model writes embeddings to source tables `aura_user_embedding_source` / `aura_model_output_ranked_nano`. **[V]**
2. **Aggregation / KNN.** `ad_delivery/aura/aura_embedding_aggregation.py` aggregates embeddings; `aura_knn_u2u.py` does user-to-user KNN; `rankgraph_embedding_aggregation.py` aggregates **RankGraph** embeddings for injection. **[V]** (Jin's diffs **D95428908**, **D103030345**.)
3. **F3 feature authoring.** 16 features **`AURA_USER_EMBEDDING_0..15`** authored under `ads.fam_horizontal_ml.flexible_batch.aura_user_embedding_features` (read `aura_user_embedding_source`, L2-normalize + FP16 encode, `FLEXIBLE_BATCH`, `ID_LIST` storage, serving group `ads_ranking_features/ads_ranking`). **[V]** (Jin's diff **D96588314**; canonical name confirmed in the F3 bug post.)
4. **F3 injection → ranking pipelines.** dataswarm pipeline → chrono polling → **F3 injection** into ads **v0 training pipelines (e.g., CMF)**; automated end-to-end by Jin's "AURA injection" skill. **[V]** (Jin's diffs **D102212387**, **D93126088**; task **T263875305**.)

> The `fam_horizontal_ml` namespace and `AURA_USER_EMBEDDING_*` naming directly match the prompt's `aura_user_embedding_source` / F3-injection / `fam_horizontal_ml` / `rankgraph embedding injection` keywords. **[V]**

### Status / impact in H1 2026 — [V] for milestones, [G] for topline wins
- **Pipeline is live but early.** The 16 AURA F3 features were **deployed ~Apr 22 2026** and were being stabilized in **May 2026** (population/backfill/serving debugging in the F3 bug post; schema migration `user_id→separable_id`, embedding dim `128→64`). **[V]** (post `.../permalink/1892112891427404/`; diffs **D101388194**, **D103030345**.)
- **AURA model is in active exploration**, not a shipped topline win: e.g., the mix-tower change **D100708290** traded **~0.2% NE regression** for **~26% QPS** and **~6pp GPU-memory** savings (a deliberate architecture study, GB200/temporal-embedding experiments in **D96682214**). **[V]**
- **26H1 GAS numbers in the doc are goals/targets** (~0.15% GAS aggregate; per-workstream 0.12%/0.1%/0.05%), **not realized launches**. **[V]**
- **[G] No AURA-attributable topline (GAS/NE) *launch* win was found for H1 2026** in the sources I read. AURA's H1 2026 footprint is best characterized as **infra/enablement + exploration** (embedding pipeline stood up, features in F3, model architecture studies) rather than a shipped revenue win. State this cautiously in the report.

---

## Q2 — Team charter, and where AURA + NE-tracking fit

### MRS Platform – Algorithms Team (Hong Li) — [V]
- **Org (from `meta people.profile chain/reports`):** Hong Li (Research Scientist **Director**) → Sri Reddy → Lars Backstrom → Chris Cox → Zuckerberg. Hong Li directly manages a large algorithms org including **Jin Yang, Junjie Yang, Tao Jia** (RS Manager), **John Wang** (SWE Manager), **Chenglin Wei** (ML Manager), **Zikun Cui**, **Keke Zhai**, **Shiying He**, **Chuanqi Xu**, and the report author. **[V]**
- **Charter (from the "MRS Science Book" team wiki):** MRS is organized into **pillars — Core Modeling, Platform, Knowledge, Foundation**. **MRS Platform** owns **AdsLlama** (joint with ABM RankingAI) and the ads-side user/representation modeling; **MRS Knowledge** (Director **Max Fan**) owns organic content/user understanding (InterestFM, Biography). The convergence effort is **UME (Unified Meta Embeddings)** = unify organic (Knowledge) + ads (Platform) embeddings. **[V]** (wiki `Tofigh/MRS_Science_Book/Chapter_19_Teams`.)
- **NE (Normalized Entropy)** is the team's primary offline model-quality metric — the "best offline proxy for Ad Score", lower = better, 0.1% is significant at Meta scale. **[V]** (`Ad_Score_Primer` wiki; `Chapter_17_Evaluation` wiki; `wut/word/?word=ne`.)

### How the two fit
- **AURA (Jin's workstream)** is the **Platform-pillar user-modeling data/feature pipeline** — the "bridge data/signals/features into ranking" half of the charter. **[V]**
- **Ads-delivery model training + NE tracking/evaluation (Junjie's workstream)** is the **core-modeling** half — building/【evaluating ranking models where NE is the currency. **[V/I]**
- They meet at the ranking model: **AURA embeddings are features that ranking models consume; NE measures whether they help.** **[I, well-supported]**

---

## Q3 — How Jin's and Junjie's workstreams connect (and to the broader stack)

- **Direct connection (AURA embeddings → ranking models measured by NE).** Jin produces/injects AURA user embeddings into ads v0 training pipelines (CMF etc.); model owners then evaluate/ship based on **NE** — Junjie's domain. **[I, strong]** The pattern is documented for the sibling **RankDB organic-embedding** workstream: organic user embeddings onboarded to the **F3 store** and injected into **15 v0 ads models / 6 FM models** for **~0.071% GAS** — same "user-embedding → F3 → ranking" template AURA follows. **[V]** (post "Harnessing Organic User Embeddings to Improve Ads Ranking: 2025 Lookback", `.../permalink/26600397316215981/`; its V-team lists **MRS Platform: Keke Zhai, Junjie Yang** and **EMs: Tao Jia; leadership: Hong Li**.)
- **RankGraph.** Jin's **D95428908** aggregates **RankGraph** embeddings for AURA F3 injection; RankGraph collaborative tokens are also inputs to Junjie's CMSL. So both workstreams consume RankGraph. **[V]**
- **AdsLlama / semantic IDs.** The AURA doc explicitly plans to enrich user modeling with **AdsLlama semantic IDs**, graph tokens and organic data; AdsLlama is an MRS-Platform-co-owned foundation model. **[V]** (AURA doc; "AdsLlama V-Team 2025 EoY" post.)
- **`fam_horizontal_ml` / horizontal_ml.** AURA's F3 features are authored under `ads.fam_horizontal_ml.flexible_batch` — i.e., AURA rides the **FAM horizontal_ml** feature framework shared with the FAM team. **[V]** (Jin's diffs **D96588314**, **D101388194**.)
- **Junjie ↔ broader ranking.** Junjie co-authors **CMSL** (sequence learning on HSTU; RankGraph + LLM tokens via MoE) and **owns the OmniFM/GEM "MRS Money V-team"** (unified Ads+Organic foundation model). **[V]** (CMSL post; Chapter 19 wiki.)

---

## Q4 — Collaboration network (person → relation → evidence)

**All org facts below are from `meta people.profile` (VERIFIED).** "Manager" = Workday manager.

### The AURA squad (MRS Platform – Algorithms)
| Person | unixname | Role / Manager | Relation to AURA / evidence |
|---|---|---|---|
| **Jin Yang (MRS)** | `jinyang29` | SWE / **Hong Li** | **Owner of the AURA user-embedding data pipeline & F3 injection; maintainer of `DATA_PROJECT:mrs_platform_aura`.** **[V]** Diffs D96588314, D95428908, D101388194, D103030345, D93126088, D102212387; tasks T263875305, T265922691; ACL routing in **T268330019** ("routed to Jin Yang because User is a maintainer of the resource"). |
| **Wei Zhang** | `weizhng` | SWE / **John Wang** | **AURA user-model development; explicit member of "AURA V-Team".** **[V]** T268330019 (his ACL request to `mrs_platform_aura`, reason *"Working on Aura user model development"*, Teams include **AURA V-Team**, AdsLlama Application V-Team, AdsLlama-FM, SCALE); co-discusses AURA pipeline coverage/partition semantics with Jin in D103030345. |
| **John Wang** | `johnwangzh` | **SWE Manager** / Hong Li | **Manages the AURA/AdsLlama user-model squad** (Wei Zhang, Bella Zhang, Hantian Zhang, Shanshan Zhang, Manpreet, +others). **[V]** Reports list via `meta`; involved in AURA model results ("John said the results have already been tested", D96682214). |
| **Shiying He** | `shiyinghe` | SWE / Hong Li | **AURA modeling/experiments** (temporal-embedding MAST config D96682214 uses his devserver path); **POC for MRS user-modeling overview** in the AURA doc; CC'd on Jin's F3 pipeline bug. **[V]** |
| **Chuanqi Xu** | `chuanqixu` | RS / Hong Li | Collaborator on Jin's AURA F3 pipeline (CC'd on the F3 population bug). **[V]** |
| **Yajuan Wang** | `yajuanwang` | RS / **Jianyu Wang** (MRS **Knowledge**) | **Cross-org AURA technical lead / reviewer of the user-embedding data** — reviews Jin's core AURA diffs (D103030345). See Q5. **[V] review; [I] "TL/POC" role.** |
| **Tao Jia** | `tjia` | RS **Manager** / Hong Li | AURA doc: "model co-design in collaboration with Tao's team"; EM on the organic-embeddings V-team; CMSL co-author. **[V]** |
| "**xxzhang**" | *(unresolved)* | — | Active reviewer/collaborator on Jin's AURA embedding/KNN pipeline (coverage & partition semantics in D103030345). **[V] presence; [G] identity** not resolved to a unixname. |

### The modeling / NE side (with Junjie)
| Person | unixname | Role / Manager | Relation / evidence |
|---|---|---|---|
| **Junjie Yang** | `junjieyang` | RS / **Hong Li** | Ads-delivery sequence modeling; **CMSL** first author; **owner of OmniFM/GEM "MRS Money V-team"**; NE-centric (every diff reports NE). **[V]** CMSL post; D72772149; Chapter 19 wiki. |
| **Zikun Cui** | `cuizk` | RS / **Hong Li** | **On the CMSL V-team with Junjie** (verified co-membership). **[V]** The prompt's "reviews Junjie's NE work" is **[I/G]** — plausible given co-membership but I did **not** find a specific diff of Zikun reviewing Junjie's NE work. |
| **Tao Jia** | `tjia` | RS Manager / Hong Li | CMSL co-author; **GEM V-team lead** with Junjie, Hong Li, Hong Yan. **[V]** |
| **Chenglin Wei** | `chenglinw` | ML Manager / Hong Li | On CMSL V-team; **manages Sameer Pawar**. **[V]** |
| **Keke Zhai** | `zhaikeke` | RS / Hong Li | MRS-Platform member on the organic-user-embedding→ads V-team alongside Junjie. **[V]** |

### Others named in the prompt
| Person | unixname | Role / Manager | Relation / evidence |
|---|---|---|---|
| **Bella Zhang** | `bellajzhang` | SWE / **John Wang** | Same squad as Wei/Jin; **AdsLlama "XFN Applications"** in the AdsLlama V-team. **[V]** Direct AURA-diff evidence **[G]**. |
| **Hantian Zhang** | `hantian` | RS / **John Wang** | John Wang's group (AURA/AdsLlama squad). **[V org]**; AURA-specific artifact **[G]**. |
| **Shanshan Zhang** | `shanshanzh` | MLE / **John Wang** | John Wang's group. **[V org]**; AURA-specific artifact **[G]**. |
| **Manpreet Singh Takkar** | `manpreet19` | SWE / **John Wang** | On the **LLaTTE UM (Ads Ranking AI) user-modeling V-team**. **[V]**; AURA-specific artifact **[G]**. |
| **Sameer Pawar** | `sapawar` | SWE / **Chenglin Wei** (→ Hong Li) | Same broader Hong Li org (Chenglin Wei's sub-team). **[V org]**; direct AURA/NE tie **[G]**. |

### Adjacent partner teams (VERIFIED via V-team rosters)
- **FAM** (feature/horizontal_ml; Jianwu Xu et al.) — F3/EBF injection partner. **F3 infra** (Rui Yang, Xinyi Zhao; oncall helpers Thomas Liu, Mihir Rastogi, Prakhar Sharma). **MRS Knowledge** (Max Fan org; InterestFM/Biography) — organic-embedding + cross-org partner (Yajuan Wang). **Ads Ranking AI / ABM** (LLaTTE UM, ATLAS — adjacent user-modeling, not Hong Li's team). **[V]**

---

## Q5 — The "Yajuan Wang is Jin's manager" discrepancy — RESOLVED

**Finding: the ACL "Manager: Yajuan Wang" field is NOT an HR/Workday fact. Jin's Workday manager is Hong Li. Yajuan Wang is a cross-org AURA data/technical lead who reviews Jin's AURA work.**

Evidence:
- **Jin's Workday record (`meta people.profile get 740754461`):** manager **`hongli`**, team MRS Platform – Algorithms, cost center "MRS Platform x MRS Software Engineering". **[V]**
- **Yajuan Wang's Workday record (`meta people.profile get yajuanwang`, id 1194549098696727):** **Research Scientist, IC**, **`directReports: 0`, `isPeopleManager: No`**, team **MRS Knowledge**, manager **`jianyu`** (Jianyu Wang, SWE Manager), chain → **Max (Xiangjun) Fan** (Director) → Lars Backstrom. She is in a **different director's org** than Jin and **cannot be anyone's HR manager**. **[V]**
- **Where "Manager: Yajuan Wang" appears:** auto-generated **data-access ACL tasks** for `DATA_PROJECT:mrs_platform_aura` — **T253908067** (access to `ad_delivery.offline_ebf_7d_offline_training_binary_map`, "for AURA", cites D92243015/D92242608/D91871467) and **T252590363** ("[AURA] EBF gen for rank graph", cites D91155375). Both stamp *Manager: Yajuan Wang* in the Employee-Details block while separately listing *Workday team: MRS Platform – Algorithms Team*. **[V]**
- **Why she's attributed to Jin's AURA work:** Yajuan Wang **actively reviews Jin's core AURA pipeline diffs** — e.g., **D103030345** (embedding aggregation + `aura_knn_u2u`) has multiple `@yajuanwang` review comments on version_id/coverage semantics. AURA's user-embedding source also pulls **InterestFM** (MRS Knowledge's area — Jianyu Wang's org), and Jin's **D93126088** is literally "[AURA][EBF Exploration]**[InterestFM]**". **[V]**

**Conclusion (calibrated):** **[V]** Yajuan Wang is an **IC Research Scientist on MRS Knowledge** (manager Jianyu Wang → Max Fan), **not** Jin's manager. **[I, strong]** She functions as the **cross-org (Knowledge↔Platform) technical lead / data-project point-of-contact for AURA's user embeddings**, which is why AURA data-access ACLs and diffs route to/through her. The "Manager" label in those ACL tasks reflects a **project/data-steward attribution, not the reporting line.**

- **[G] Caveat — a second "Yajuan Wang":** the LLaTTE UM launch post thanks a "Yajuan Wang" for *leadership support* alongside VPs/directors, but with a **different Workplace profile id (61573880409072)** than the IC's employee id (1194549098696727). That is likely a **different, more senior person**; I could not resolve that Workplace id via the org CLI. For Jin's ACL tasks, the relevant Yajuan Wang is the **IC RS on MRS Knowledge** (unixname `yajuanwang`).

---

## Q6 — Impact / results (H1 2026)

### Jin Yang (AURA pipeline) — enablement, VERIFIED; topline win GAP
- **[V]** Stood up the **AURA user-embedding → F3 → ranking** data pipeline end-to-end: authored **16 F3 features** `AURA_USER_EMBEDDING_0..15` (D96588314), built aggregation + **u2u KNN** + **RankGraph** aggregation (D95428908, D103030345), schema/dim migration (D101388194), **InterestFM EBF** exploration (D93126088), and an **automation skill** for the whole inject flow (D102212387).
- **[V]** **Owns/maintains `DATA_PROJECT:mrs_platform_aura`** (others' access requests route to her — T268330019). Manages the AURA data-access ACLs (T253908067, T252590363).
- **[V]** Features **deployed ~Apr 22 2026** and stabilized in May (coverage/serving debugging).
- **[G]** **No AURA-attributable topline NE/GAS launch** found for H1 2026 — her H1 impact is **infrastructure/enablement** (pipeline + features live), with model wins expected downstream. State as enablement, not revenue.
- *(Context: her strong prior topline wins — IDP consolidation, MTML, semantic matching — are from her earlier Identity/Signals role, 2024–2025, not AURA. **[V]** Her oncall is still `server_side_identity`.)*

### Junjie Yang (ads modeling + NE) — VERIFIED shipped wins
- **[V] CMSL (Constructive Multi-Sequence Learning)** — first author: **shipped to 5 Ads head models, ~0.1145% eGAS**; 2 organic-video launches; **IFR MC9 proposal ~0.435% avg eval NE**. (post `.../permalink/1399961228316514/`, Nov 2025.)
- **[V] LSR / sequence-length 2K→3K (D72772149):** **0.06% CMF NE, 0.06% Reels NE, ~12% QPS** (reviewed by `@hongli`).
- **[V] Owns OmniFM/GEM "MRS Money V-team"** (unified Ads+Organic foundation model) — a major H1 charter item (Chapter 19 wiki).
- **[I]** Consistent multi-year pattern of NE-gain + QPS-efficiency modeling (HSTU, HGNN, WS-NAS, quantization) — NE is the throughline of his work.

### NE "tracking" as a domain — [V] context, [G] Junjie-specific tool
- NE tracking/stability is a first-class team concern: NE-variance SEVs block model iteration (S645139, S669184), and there is tooling (ModelSitter, NE Confidence Interval, NE Stability Analyzer skill, Swiss Cheese NE Breakdown, O2O NE). **[V]** I did **not** find a specific "NE tracking system built by Junjie" or a "Zikun-reviews-Junjie's-NE" diff; represent Junjie's NE work as **model-quality evaluation/gains** and the Zikun tie as **CMSL co-membership**. **[G]**

---

## Honest gaps to flag in the final report
1. **[G]** No shipped **AURA topline (NE/GAS) launch** in H1 2026 — AURA is enablement/exploration this half.
2. **[G]** "Zikun Cui reviews Junjie's NE work" — only **CMSL co-membership** verified, not a specific review.
3. **[G]** AURA-specific artifacts for **Hantian Zhang, Shanshan Zhang, Bella Zhang, Manpreet, Sameer Pawar** not found — only org membership (John Wang's / Chenglin Wei's groups) is verified.
4. **[G]** "**xxzhang**" (active AURA pipeline reviewer) not resolved to a unixname.
5. **[G]** The **1zfw3D7X…** planning doc ("Aura user model development", cited by T268330019) returned 404 to me; its existence/purpose is confirmed via the ACL task but its contents are unread.
6. **[G]** Second "Yajuan Wang" (Workplace id 61573880409072 in the LLaTTE leadership credits) is likely a different, senior person — unresolved.

## Key source index
- **AURA doc:** docs.google.com/document/d/1wvFJqDGRkN7F5h9BKvPuvhhuxyJ9DNg7vyIrayjEW38
- **AURA code:** wiki `PUL/Projects/aps_models/Modules/exploration/aura_model/README`; `//aps_models/exploration/aura_model`
- **Jin diffs:** D96588314, D95428908, D101388194, D103030345, D93126088, D102212387, D100708290, D96682214 · **tasks:** T263875305, T265922691, T253908067, T252590363, T268330019 · **F3 bug post:** fb.workplace.com/groups/253776585261051/permalink/1892112891427404/
- **Junjie:** CMSL post fb.workplace.com/groups/228479108798071/permalink/1399961228316514/; D72772149
- **Team/charter:** wiki `Tofigh/MRS_Science_Book/Chapter_19_Teams`, `Chapter_17_Evaluation`; `meta people.profile`
- **Organic-embeddings analog:** fb.workplace.com/groups/1033540429995021/permalink/26600397316215981/
- **NE definition:** wiki `Ads/Delivery/AdsRanking/Ranking/Ad_Score_Primer`
