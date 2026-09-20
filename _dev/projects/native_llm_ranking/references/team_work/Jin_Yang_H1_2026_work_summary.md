# Jin Yang (MRS) — H1 2026 Work Summary (Jan 1 – Jul 10, 2026)

**Subject:** Jin Yang (MRS), unixname `jinyang29`, FBID 740754461 — Software Engineer, MRS Platform · Algorithms Team (manager: Hong Li, Research Scientist Director).
**Prepared:** 2026-07-10.
**Method:** First-party evidence from Phabricator diffs (read via `meta phabricator.diff describe`), Tasks (`meta tasks.task`), team roster (`find_teammates`), profile resolution (`meta people.profile get`), and one internal knowledge search for AURA project context. Every substantive claim is cited to a diff ID + date. Inferred/uncertain items are explicitly flagged in §6.

> **Correction to the prior combined analysis** (`Jin_Yang_Junjie_Yang_under_Hong_Li_work_analysis.md`): that file (written when the org CLI was access-denied) concluded Jin's "MRS-era footprint is still early / medium confidence." With working tooling this is now clearly wrong. Jin has a **substantial, coherent, mostly-landed H1 2026 body of work** centered on the **AURA user-embedding system for ads ranking**. See stats in §5.

---

## 0. TL;DR

Jin Yang spent H1 2026 as the **data/pipeline engineer productionizing AURA user embeddings into the ads-ranking feature stack**. The half has a clear arc:

- **Jan–Feb: exploration (mostly not shipped).** Embedding-Based Feature (EBF) experiments injecting Rankgraph / InterestFM embedding features into `onsite_conversion` ranking models. ~31 exploratory diffs, almost all Unpublished/Abandoned.
- **Mar–Jun: productionization (mostly landed).** Built and hardened the end-to-end AURA embedding pipeline: Dataswarm aggregation (offline 3-day pooling + realtime) → `aura_user_embedding_source` Hive table → F3 registration of 16 `AURA_USER_EMBEDDING_*` features in `fam_horizontal_ml` → injection into DPA/FAM/IG ranking models. Plus a user-to-user KNN similarity pipeline (`aura_knn_u2u` → `aura_v1_u2u` retrieval signal), model-baseline/validation work, an (unlanded) automation skill, and a landed offsite-signals training-data pipeline (UMS 3PD) in collaboration with the CAPI/Signal-Growth org.

**What AURA is:** *Ad User Representational Applications* — user-embedding features for ads ranking. The AURA embedding model (`aps_models/exploration/aura_model`; multi-task CTR/CVR; `aura`=WHEN arch, `aura_uniarch`=UniArch) is trained on the **CMF pipeline (FB Feed)** and its embeddings are **injected as side-table features into DPA model training** (related flows: CMF, DPA-ATLAS, DPA-AURA). *(Source: internal knowledge search; medium-trust — see §6.)*

---

## 1. Workstream breakdown

Hypotheses (a)–(f) from the request are **mostly confirmed**, with three important corrections (EBF did not ship; automation did not land; UMS is an offsite-signals collaboration). One extra workstream (g, ongoing identity/signals ops) was not in the hypothesis.

### (A) AURA embedding **data pipelines** (Dataswarm: offline + realtime) — **CORE, SHIPPED** ✅
The dominant landed workstream. Owns the `ad_delivery.aura.*` Dataswarm pipelines that turn raw model-output embeddings into a partitioned Hive source table.

- **Founding diff — D96946473** (3/17, Closed): added two pipelines — `aura_embedding_aggregation_avg` (3-day pooling of user & ad embeddings) and `aura_embedding_aggregation_realtime` (migrate realtime predicted embeddings to the output table).
- **D95329503** (3/4, Closed) "Aggregate output embeddings for feature insert" and **D95428908** (3/5, Closed) "Aggregate rankgraph embeddings for feature insert" — the earliest feature-insert generators (into CMF pipelines for testing). `rankgraph_embedding_aggregation.py`.
- **D98409221** (3/26, Closed): 3-day pool with `ds` derived from timestamp; write into the F3 source table.
- **D99732532** (4/6, Closed): recurring-training compatibility (`table_ds = <DATEID>`, daily production run).
- **D99750243 + D99795511** (4/6–4/7, Closed, stack [1/2]+[2/2]): carry non-active users' embeddings forward into the current date; recursive addition of prior user embeddings.
- **D99908852** (4/7, Closed): `UNION ALL` + `LEFT ANTI JOIN` pattern to carry forward previous-day embeddings while updating changed users. (Plus D99900389, D99908947, D99937980, D99922925, D99940895 — partitioning, retention, offline-eval task, blocked-day safeguards, all Closed 4/7.)
- **D103030345** (4/29, Closed): repoint aggregation input to `test_aurav2_w1_0327plus` (`table_ds` filtering, `defer_ds=False`); remove the `version_id="user_embedding_0"` "dirty fix" filter from `aura_knn_u2u`. (Unpublished twin: D103079840.)
- **D103465430** (5/1, Closed): add `defer_ds` + config-driven flags (`num_user_features`, `num_ad_features`, `enable_similarity`) to the **realtime** pipeline, mirroring offline (233 lines).
- **D104938898** (5/12, Closed): dedup aggregation to `separable_id` level (`GROUP BY 1`, `FIRST(ad_id)`). (Plus D104853251, 5/12.)
- **D106032270** (5/21, Closed): replace `full_table_scan()` on `prod_aura_output_table` with an explicit `job_id` filter; pin output `version_id=job_id`. (Abandoned first attempt: D106018877.)
- **D107554353** (6/4, Closed): simplify `prod_aura_output_table` input (single-day `ds` vs a 7-day range) and pin `job_id` on output. **Last AURA code diff of the half.**

**Why it matters:** this is the load-bearing plumbing that makes AURA embeddings consumable by ranking models daily; much of Mar–Jun is reliability/correctness hardening (dedup, carry-forward, partition pruning, job-id pinning) driven by real prod incidents (see DQ/Dataswarm tasks in §4).

### (B) **F3 feature registration & injection** — **SHIPPED** ✅
Registers the Hive source as an F3 dataset and authors the ranking features.

- **D96587164** (3/14, Closed): register `aura_user_embedding_source` (namespace `ad_delivery`) as an F3 `TypedDataSource`. Columns: `user_id` Int64, `feature_name` String, `embeddings` List[Float64], `version_id` String, `ds` String.
- **D96588314** (3/14→landed 3/21, Closed): author **16 features `AURA_USER_EMBEDDING_0`…`_15`** in `fam_horizontal_ml/flexible_batch`. Each reads the source, filters by `feature_name`, applies **L2-normalize + FP16 encode (128-dim)**, registered as `FLEXIBLE_BATCH` / `ID_LIST` storage, **serving group `ads_ranking_features/ads_ranking`**. `depends_on` D96587164.
- **D97203454** (3/18, Closed): convert the manual Hive registration to **auto-generated** via `data_model_v2_generator`.
- **D100268356** (4/9, Closed): **schema migration** `user_id` → `separable_id` (SeparableID standard) across the source schema + `aura_embedding_aggregation` + `aura_knn_u2u`; promote `feature_name` to a **partition** column.
- **D101388194** (4/17, Closed): update the F3 **DSL** to match — key `user_id`→`separable_id`, **embedding dim 128 → 64**, fixed `feature_name` partition values (`user_embedding_0` naming), latest-ds dedup, regenerated boundary dataset + schema. (Plus D101417317 "compatible with nano run.")
- Retention/plumbing: D99937980 (intermediate-table retention), D99922925 (source-table retention). Feature-not-populated triage: T270997359.

**Flow:** `aura_user_embedding_source` (Hive) → F3 `AURA_USER_EMBEDDING_*` → injected as **side-table features into DPA / FAM / IG ranking-model training**.

### (C) **EBF (Embedding-Based Feature) exploration** — **EXPLORATORY, DID NOT SHIP** ⚠️ *(correction)*
Jan–Feb precursor: test whether externally-produced embeddings help ads ranking, via F3 offline EBF injection, before the dedicated AURA source existed.

- Two feature families explored on the **`onsite_conversion`** (`fir_onsite_conversion`) target: **InterestFM** (4 features) and **Rankgraph** (5 features). Tooling: `ad_delivery/f3/injection/ebf_clustered_side_table_view/offline_ebf_injection_v2_existing_event_template_binmap_7d.py`; custom EDS/UDS side tables.
- Representative diffs: D93160255 (Rankgraph offline-injection script, **Accepted, never committed**), D93126088 (InterestFM side-table script, **Accepted, never committed**), D93135288/D93126034/D93158561 (Needs Review), and ~25 more (D90923236, D91362449, D91503065, D91606352, D91871467, D92241417→D94554317, …) almost all **Unpublished/Abandoned**.
- Model-side debug: D92930150 "long seq ebf with nano run", D91753771/D91753777 (check uds/eds raw output).

**Status:** ~31 diffs, **0 landed** as durable features. This exploration motivated building the dedicated AURA embedding source + F3 flexible_batch features (workstreams A/B). Correctly characterized as exploratory, not production impact.

### (D) **Model baseline / training / validation** — **SHIPPED (support role)** ✅
Enables apples-to-apples evaluation of the AURA model.

- **D91390199** (1/24, Closed): fix `shared_seq_offsets` schema type so the baseline runs again (earliest AURA diff; launches `aura_nano_2048_3d`). Also D93515337 (2/17) "fix config to avoid infra error."
- **D100244084** (4/9, Closed): **set up the legacy AURA model as a baseline** — `aura_legacy.py` (copy of pre-UniArch `aura.py` from D89734073; classes `AuraLegacyTrain`/`AuraLegacyGMPInference`), `aura_nano_legacy.yaml` (INCEPTION-based UHM, LSM user summarization), registered in `aura_model_registry.py`. Purpose: measure UniArch impact on the same data pipeline. (2289 lines.)
- **D100743790** (4/13, Closed, **Configerator**): enable **training-NE checkpoint validation for model `1035125311`** (added to `covered_models.cinc` `CHECKPOINT_MODEL_ENTITY_ID_OVERRIDE`). Reviewed by ads-model-validation (mkon/haikuo).
- Not landed: D97431691 `[CMF test] temp yaml`, D102212489 `[AI] model investigation plan` (Abandoned).

### (E) **Automation tooling** (Claude Code skill + plans) — **BUILT, NOT LANDED** ⚠️ *(correction)*
- **D101661629** (4/20, **Waiting For Author**): two automation-plan docs — `aura_offline_pipeline_automation.md` (6-step, `nano_legacy`/`nano_bugfix`/`nano_aidn` variants, +1-day-offset F3 injection) and `aura_realtime_pipeline_automation.md` (6-step, `nano_aidn`, `defer_ds`, user-only 8 features).
- **D102212387** (4/23, **Waiting For Author**): a **Claude Code skill** automating the full flow (dataswarm → chrono polling → F3 injection): `SKILL.md` + `run_aura_pipeline.sh` (Steps 0.5–6, batch + realtime, retries), 13 interactive params. 1476 lines, well-tested per test plan. `depends_on` D101661629.
- **Status:** neither landed — **Wei Zhang (`weizhng`) rejected both**, Yajuan Wang rejected the plans. Tracked by T264608621 "Automate the transformation & injection process" (project *E2E pipeline*, IN_PROGRESS).

### (F) **UMS 3PD offsite-signals training-data pipeline** — **SHIPPED** ✅ *(enrichment: it's a Signal-Growth collaboration)*
- **D105982047** (5/21→landed 6/9, Closed): the **UMS autoregressive 3PD training-data pipeline** (`ums_autoregressive_dedup_3pd_training_data`), a 3-phase Dataswarm pipeline producing deduplicated training sequences from **`fct_offsite_signals_trace` (FOST)** for the UMS 3PD model. Phase 1 daily event extraction (`separable_id`, `event_timestamp`, `pixel_id`, `event_type_id`, `url_domain`; dedup by user/time/pixel); Phase 2 10-day-lookback sequence construction (autoregressive history/target split); Phase 3 dedup output. **Built from a design doc by Xiang Zhang (`xxzhang`, CAPI Performance).** 763 lines.
- Tied to project **"AURA SG Collaboration"** (tasks T262015408/411/348/352) and the `ad_metrics.signals…aura_v1_u2u` retrieval signal.

### (G) **Ongoing identity/signals operations** — **CARRY-OVER OPS** (context)
Throughout H1, Jin remained the owner of recurring **DQ alerts** on `ad_metrics.identity.user_behavior_model.user_id_similarity.dq_check_user_pair_dimension[_uid]` (dozens of CLOSED alert tasks Jan–Jun) — operational ownership carried from the prior Signals/Identity role. Plus the `aura_v1_u2u` u2u-similarity pipeline (`aura_knn_u2u`) bridges identity-style user-similarity into AURA retrieval.

### (H) **Administrative / data-project stewardship** — overhead (counted, not analyzed)
Jin acts as an ACL/steward for `DATA_PROJECT:mrs_platform_aura`: 12 "grant/add user to ACL" diffs (repository N/A) and many permission/MonCR/quota tasks. Examples: D106097605 (grant Manpreet), D103891129 (grant Shanshan Zhang), D103247852 (grant Jill), D100719333 (grant `oncall_horizontal_ml` to the AURA feature source table), D96763340 (add Xiang), D91362942 (add Sameer). Also handled the security review for the ACL having 54 transitive members (T269206424).

---

## 2. Precise technical facts (verified from diffs read)

**End-to-end AURA flow (as built by Jin):**

```
AURA model (aps_models/exploration/aura_model)                 [model 1035125311]
   variants: aura (WHEN arch) | aura_uniarch (UniArch)
   multi-task CTR/CVR, trained on CMF pipeline (FB Feed), published to GMP
        │  produces user & ad embeddings
        ▼
Dataswarm aggregation  (ad_delivery.aura.aura_embedding_aggregation[_avg/_realtime])
   • offline: 3-day pooling; previous-day carry-forward (UNION ALL + LEFT ANTI JOIN)
   • realtime: defer_ds timestamp filtering; user-only (8 features)
   • dedup to separable_id level; job_id-pinned output
        │  writes
        ▼
Hive: aura_user_embedding_source  (ad_delivery)  +  prod_aura_output_table
   cols: separable_id (was user_id), feature_name (partition), embeddings List[Float64],
         version_id, ds        [embedding dim 128 → 64 in April]
        │  F3 TypedDataSource + auto-generated data model
        ▼
F3 features: AURA_USER_EMBEDDING_0..15  (fam_horizontal_ml/flexible_batch)
   L2-normalize + FP16 encode; FLEXIBLE_BATCH / ID_LIST; serving ads_ranking_features/ads_ranking
        │  injected as side-table features
        ▼
DPA / FAM / IG ranking-model training

── parallel branch ──
aura_knn_u2u (Dataswarm) → user-to-user KNN similarity (join via SID mapping id2)
   → ad_metrics.signals.sg_ad_retrieval…aura_v1_u2u  (ad-retrieval signal)
```

**What changed Jan → Jun (schema/pipeline evolution):**
- `user_id` → `separable_id` (SeparableID standard) — D100268356 (4/9), D101388194 (4/17).
- Embedding dimension **128 → 64** — D101388194 (4/17).
- `feature_name`: regular column → **partition key** — D100268356 (4/9).
- Input source repointed to `test_aurav2_w1_0327plus` with `table_ds` filtering; removed the `version_id` "dirty fix" filter — D103030345 (4/29).
- Realtime pipeline gained `defer_ds` + config flags — D103465430 (5/1).
- Reads made efficient: `full_table_scan` → explicit `job_id` filter; output `job_id` pinned — D106032270 (5/21), D107554353 (6/4).
- Correctness: dedup to one row per `separable_id` — D104938898 (5/12).

**Key named assets:** `aura_user_embedding_source`, `prod_aura_output_table`, `aura_embedding_aggregation[_avg/_realtime]`, `aura_knn_u2u`, `aura_v1_u2u`, `graph_ad_v1_embedding_hourly_agg` (F3 dataset, D90834004), `fct_offsite_signals_trace` (FOST), `fam_horizontal_ml/flexible_batch`, model `1035125311`, `aps_models/exploration/aura_model`.

---

## 3. Collaborators (from reviewers/subscribers across all 74 code diffs)

**Primary reviewers (ranked by accepts on landed work):**

| Reviewer | Unixname | Team | Role in Jin's work |
|---|---|---|---|
| **Chuanqi Xu** | `chuanqixu` | MRS Platform · Algorithms | **#1 reviewer overall (~18 accepts)**, esp. Mar–Apr pipeline + F3. Likely MRS-side tech lead/mentor *(inferred)*. |
| **Xiang Zhang** | `xxzhang` | **Signal Growth Eng: CAPI Performance** (cross-team) | **#2 reviewer (~10 accepts)**, dominant Apr–Jun; **authored the UMS 3PD design doc**. Signals/CAPI counterpart. |
| **James Teng** | `siyuant2` | Ranking ENG: Ranking AI Relevance (cross-team) | Early F3-feature + embedding-aggregation reviewer (Mar). |
| **Wei Zhang** | `weizhng` | MRS Platform · Algorithms | Later-stage reviewer; **gatekept the automation skill + plans (rejected both)**. |
| **Shiying He** | `shiyinghe` | MRS Platform · Algorithms | Model baseline/config reviewer (D100244084, D91390199, D93515337). |
| **Manpreet Singh Takkar** | `manpreet19` | MRS Platform · Algorithms | Model/output reviewer (D107554353, D100244084, D91390199). |

**Frequent stakeholders / subscribers:** **Yajuan Wang** (`yajuanwang`, MRS Knowledge Team — author of the "AURA SG Collaboration" tasks, subscriber/rejecter on automation), **Shanshan Zhang** (`shanshanzh`, MRS Algo — UMS reviewer), `aura_team` and `mrs-platform-algorithm` review groups.

**Cross-team / infra reviewers (mostly auto-added):** **Yao Sha** (`yaos`, Ads AI Infra: Modeling Velocity — F3/EBF injection), **Prakhar Sharma** (`prakharsharma`, FBR Ranking Core ML — F3 features), **Max Kondrashov** (`mkon`, M10N model validation — NE checkpoint), plus F3 dataset auto-reviewers `ktt`, `oscarso2000`, `jeungwon`, `zehong`, `asharm`, `andrewhu` and DW auto-reviewers `nsavant`, `dougyoung`, `krishnaprasadmv`, `yiqinpan` (Jill Pan).

**Cross-team signals (verified):**
- **CAPI / Signal Growth** (Xiang Zhang) — UMS 3PD offsite-signals pipeline + `aura_v1_u2u`. Strongest cross-org tie.
- **Ranking AI / Ads AI Infra / FBR Ranking** (James Teng, Yao Sha, Prakhar Sharma) — F3 feature framework + ranking integration.
- **F3 / horizontal_ml** — features authored in `fam_horizontal_ml`; Jin granted `oncall_horizontal_ml` access to the AURA source table (D100719333).
- **RankGraph** appears as an embedding **input source** (`rankgraph_embedding_aggregation.py`, `graph_ad_v1_embedding`), not as Jin building RankGraph itself.
- **MRS Knowledge** (Yajuan Wang) — SG collaboration project owner.
- **NOT observed:** any "AdsLlama" involvement (hypothesis not supported by the diff evidence).

---

## 4. Tasks / projects owned (genuine, after filtering auto-generated noise)

**Genuine project tasks (Jin as owner/author):**
- **T264608477 — "AURA Model Debugging and Develop"** (project *AURA V1 Debugging*, IN_PROGRESS; has a plan doc + subtasks; depends_on T262052703).
- **T264608621 — "Automate the transformation & injection process"** (project *E2E pipeline*, IN_PROGRESS) → the automation skill/plans (workstream E).
- **AURA SG Collaboration** (project) — T262015408 "Design SG input data use cases", **T262015411 "Build signal data pipeline"** (HIGH, author Yajuan Wang, target 5/25), T262015348 "Implement production monitoring" (Closed), T262015352 "Complete capacity planning" (Closed) → the UMS 3PD pipeline (workstream F).
- **T263875305 — "AURA F3 feature pipeline"** (Closed) → workstreams A/B.
- **Feature-expansion tracks:** T248953341 "New EBF features" (Closed, Dec'25→Jan), T248999912 "New features for AURA [CAG]", T254163582/T254171587 "New features for AURA [IG]/[FAM]".
- **Delivery/capacity tracks (Resource-Planner tasks, semi-genuine):** `[2026H1][AURA]` × surfaces DPA / FAM / IG × variants **AFL** / **Batch** embedding features (T253133957, T253811824, T254007650, T255119141, T254174547, T254165774, T254165040, T254006886, T253999036, …). These are Monetization Resource-Planner capacity requests that map to the AURA feature-delivery roadmap across surfaces.

**Filtered out as auto-generated noise** (counted in §5 but not project work): dozens of `DQ Alert!` tasks (user_pair_dimension), `[DATASWARM] Errors in pipeline` (aura_embedding_aggregation / aura_knn_u2u), `[…]TABLE_ACL/NAMESPACE_ACL/SEMANTIC_TYPE_UDP Permission request`, `[BCU/Storage Quota Enforcement]`, `[Entity Lifecycle] deprecation`, `[Workload Management] abandoned fblearner`, `MonCR Exemption`, "Welcome to MPK21", "space hold", etc.

---

## 5. Volume stats (Jan 1 – Jul 10, 2026)

- **Total diffs authored: 86.**
  - **Substantive code diffs (repo = fbsource/FBS, +1 Configerator): 74.**
  - **Administrative ACL/"grant access" diffs (repo N/A): 12.**
- **Code-diff outcomes (74):**
  - **Landed / Closed: 30** (29 fbsource + 1 Configerator).
  - Not landed: **44** = 23 Unpublished + 13 Abandoned + 4 Needs Review + 2 Accepted-never-committed + 2 Waiting-For-Author.
  - Land rate ≈ **41%** of code diffs — but this is bimodal: **Jan–Feb EBF exploration ≈31 diffs, ~0 landed**; **Mar–Jun productionization landed at a high rate** (nearly all AURA pipeline/F3 diffs Closed).
- **Admin diffs:** 12 (all Closed) + a large volume of auto-generated permission/DQ/quota tasks.
- **Active range:** first diff **D90834004 (2026-01-15)** → last AURA code diff **D107554353 (2026-06-04)**; pipeline-ops tasks continue into **June–July** (e.g., T275448327, 6/11).
- **Tasks:** 1,335 total "owned" matches (overwhelmingly auto-alerts) and 246 "created"; genuine project tasks number **~15** (§4).

---

## 6. Confidence flags

**Directly verified** (read the diff/task/profile):
- All diff IDs, titles, statuses, dates, summaries, and reviewers cited above (batch-read via `describe`).
- Collaborator names/teams (`meta people.profile get`, `find_teammates`).
- The pipeline flow, schema migrations (user_id→separable_id, 128→64 dim, feature_name→partition), and the not-landed status of the automation skill (weizhng rejected) and EBF exploration.
- Volume stats (enumerated from the full diff list).

**Inferred (medium confidence):**
- **AURA acronym/definition** = "Ad User Representational Applications" and the "trained on CMF → injected into DPA" framing come from an **internal knowledge-search result tagged medium-trust**, not from a diff. Two conflicting expansions exist in search (also "Adaptive User Representation & Reasoning Architecture"); the code itself says "expansion not found in source." Treat the acronym as likely-but-not-authoritative; the *technical* flow is corroborated by Jin's diffs.
- **Chuanqi Xu as MRS-side tech lead/mentor** — inferred from his dominant early-review pattern, not an org fact.
- **"AFL" vs "Batch"** feature variants, and surface acronyms **FAM / CAG** — inferred as online-signal vs batch-embedding feature tracks and app-surface labels; exact expansions not verified.
- Mapping of Resource-Planner `[2026H1]` tasks to concrete shipped features is by title, not by a launch record.

**Open questions / not established:**
- **Launch/impact metrics.** No eGAS/NE win or production launch record for the AURA features was found in the diffs/tasks read — this summary establishes *what was built and shipped to the feature stack*, not measured ranking-model impact. (The NE-checkpoint-validation diff D100743790 enables eval but isn't a result.)
- Whether the AURA F3 features reached **stable production serving** in a launched model (vs registered + injected for training) is not confirmed here.
- No evidence for an "AdsLlama" tie (hypothesis not supported).
- The prior combined file was **modified externally** during this analysis; this report is standalone and does not reconcile with any new edits there.
