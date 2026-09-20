# Junjie Yang — H1 2026 Work Summary (Jan 1 – Jul 10, 2026)

**Subject:** Junjie Yang · `junjieyang` · FBID 100004417397095
**Role:** Research Scientist, MRS Platform – Algorithms Team · Manager: Hong Li (`hongli`) · Sunnyvale · at Meta since 2020-07
**Prepared:** 2026-07-10 · **Method:** Direct reads of Phabricator diffs (`meta phabricator.diff`), Tasks (`meta tasks.task`), the SEV manager, employee directory (`meta people.profile`), and Junjie's own analytics notebooks. Every claim below is tagged **[Verified]** (read from a primary artifact) or **[Inferred]** (reasoned from naming/structure).

> **Headline caveat (read first):** For a Research Scientist doing model R&D, **landed diffs massively undercount the work**. Junjie landed only ~9 substantive diffs in H1 2026, but the primary evidence shows the bulk of his output is **ML training & architecture experimentation**: **≥410 distinct `fire-junjieyang-*` MAST training jobs** and his own experiment-tracking notebooks. He is the **owner of "CMSL"** (Constructive Multi-Sequence Learning) and of a production embedding signal with **~$5.9M/day revenue attribution**. Treat diff volume as a lower bound on impact.

---

## 1. Workstream breakdown

### (A) NE-tracking / model-quality evaluation pipeline for ad-delivery models  **[Verified]**
An **offline Dataswarm/Chronos pipeline** that computes **NE (Normalized Entropy)** — the standard ads model-quality metric — for candidate ad-delivery models versus production, and lands the results in Hive. All code lives in:
- `fbcode/dataswarm-pipelines/tasks/ad_delivery/mrs_platform/` (pipeline logic)
- `fbcode/dataswarm-pipelines/upm_data/datasets/hive/ad_delivery/` (Hive dataset/schema definitions)

| Diff | Date | Status | Title | Files (Δ) | Reviewer |
|---|---|---|---|---|---|
| **D98380670** | 2026-03-26 | Closed | Add NE tracking | +`ne_tracking_testing.py` (293) + Hive (40) | taiguoo |
| **D99018172** | 2026-03-31 | Closed | Add new pipeline | +`ne_tracking_testing_v2.py` (377) + Hive (68) | taiguoo |
| **D99160752** | 2026-04-01 | Closed | add new pipeline | +`ne_tracking_testing4.py` (452) + Hive (80) | taiguoo |
| **D99464246** | 2026-04-03 | Closed | Update ne tracking | `ne_tracking_testing4.py` (+66/-1) + Hive (+12) | cuizk, RADAR Bot |
| **D99701305** | 2026-04-06 | Closed | Remove conv type filter | `ne_tracking_testing.py` (-13) | taiguoo |
| **D100272053** | 2026-04-09 | Closed | Add more NE tracking | rename `…_v2.py` → `ne_tracking_5.py` (+375/-377) + Hive | cuizk |
| **D100419242** | 2026-04-10 | Closed | Fix ne_tracking_5: raw label column + correct gain formula | `ne_tracking_5.py` (+6/-18) + Hive (+3/-3) | cuizk |

**How the pipeline works (from D100419242 + file paths) [Verified]:**
- Compares **candidate model prediction columns `ofm_v3` and `ofm_v4`** against production (`prod`).
- **Gain formula: `100 * (model - prod) / prod`** — i.e. percent NE change of a candidate model relative to prod (a negative NE gain = better model).
- **Label:** a **raw conversion-label column** (D100419242 replaced a `CASE` expression over `multi_labels[1000002]` — a specific conversion-event label index — with the raw column, and dropped unnecessary `NOT NULL` filters on the `ofm_v3`/`ofm_v4` predictions).
- **"Remove conv type filter" (D99701305):** dropped a conversion-type filter, broadening the evaluation population.
- Runs as scheduled Dataswarm jobs (test plans point to Chronos `atn` job instances) and publishes to Hive via the `upm_data` datasets ("UPM" schema descriptions updated in D100419242).

*Interpretation:* This is Junjie's **offline / production-side** model-quality tracking harness for ad-delivery ranking models. It complements the **training-side** NE tracking in Workstream B.

### (B) CMSL model training & experimentation — the "fire" MAST jobs  **[Verified, largest workstream]**
- **Junjie is "the CMSL owner"** — stated verbatim in SEV S642095: *"Reassigned to Junjie Yang as he is the CMSL owner."* CMSL = **Constructive Multi-Sequence Learning**, a sequence-learning recommendation architecture.
- **Volume: ≥410 distinct `fire-junjieyang-f<id>` MAST training jobs** extracted from his auto-generated MVAI training-job alerts (count is capped by the 500-row task pull, so the true number is higher). Additional timestamped runs use the pattern `fire-junjieyang-YYYYMMDD-HHMM-<hash>`.
- **Concrete experiment (his own notebook N10471418 `cmsl_gating_ne_compare.ipynb`, authored by FBID 100004417397095 on 2026-04-20)** — compares **training NE** across three of his CMSL MAST runs via `ModelTracerMVAI`:

  | Run | Description | MAST job |
  |---|---|---|
  | `_baseline` | CMSL v1, no EBF | `fire-junjieyang-20260416-1740-b7eeaae0` |
  | `moe` | CMSL v1 refactor with **MoE** (Mixture-of-Experts) | `fire-junjieyang-20260417-1037-78bf1ef0` |
  | `moe_pointwise_gating` | CMSL v1 + MoE + **pointwise gating** | `fire-junjieyang-20260419-0040-c9393a8b` |

  Metrics tracked: `variable_step_metrics/NE/global/window/{cmf_click, reels_click}/train` and the multi-task (`mt/…`) heads **impression, conversion, page_type, uih** (user-interaction-history), plus QPS — reported as **relative NE gap vs baseline**. This shows the fire jobs train **ads/organic click-prediction models (Feed "cmf_click" + "reels_click"), multi-task, over user-history sequences**, and that he runs **architecture search** on CMSL (MoE, gating variants).
- **He authored the shared experiment-tracking tooling.** His `cmsl_gating_ne_compare` notebook (2026-04-20) was subsequently **cloned/reused by teammates** for further CMSL/HSTU scaling studies (same structure, later dates): `N10920854` "Clone of CMSL CMF experiment" (Zikun Cui — early fusion, fast-MoE, learnable tokens, NRO-embedding scaling), `N10928648` "CMSL MAST Runs Training NE Comparison_Jinghan" (HSTU depth scaling, layers 1–3), `N10950732` "CMSL Early Fusion Layers Scaling" (ikalemaj). *[Inferred that his is the source template — based on earliest timestamp + identical structure.]*

### (C) MVAI "fire" app-layer config (LSR-CMSL)  **[Verified]**
- **D91958039** (2026-01-30, Closed, Configerator/CFHG, 102 lines; reviewers **cuizk**, **tjia**) — *"add a new fire layer"* — creates:
  - `source/minimal_viable_ai/app_layers/fire-app-lsr-cmslv0.fbpkg.cconf` (+ materialized JSON)
- This defines an **MVAI (`minimal_viable_ai`) application layer** for the fbpkg **`fire-app-lsr-cmslv0`** — i.e. the packaged app layer for an **LSR + CMSL v0** model. It ties together the "fire" training framework (MVAI), **LSR** (long-sequence ranking/retrieval line), and CMSL. This is the config plumbing behind the fire MAST jobs in (B).

### (D) Ads FM / UHM MAST launcher baseline config  **[Verified diff; naming Inferred]**
- **D105034490** (2026-05-13, **Unpublished/WIP**, FBS, 935 lines, no reviewers) — *"Baseline"* — creates:
  - `fbcode/aps_models/ads/launchers/fm/conf/mode/experimental/mast_es_fm_2026_uhm.yaml` (910 lines)
  - modifies `…/experimental/local_es_fm_2026_uhm.yaml`
- A **MAST launcher configuration** (910-line YAML) for an **experimental 2026 ads "fm" model with "uhm"**. *[Inferred: `fm` = foundation/family model, `uhm` = User/Unified History Model, `es` = experimental setting — from path/naming conventions.]* Being unpublished indicates active research iteration rather than a shipped change. This is the **training-config artifact** corresponding to the fire MAST experiments.

### (E) Production reliability / ownership (SEV)  **[Verified]**
- **SEV S642095** (Level 3; detected 2026-03-30, **mitigated by Junjie 2026-04-01**, Closed): *"`lsr_cmsl_embedding_agg_encoded_ts_signal` is lagging 4d."*
  - **Owner: Junjie Yang** (as CMSL owner). Co-CC'd CMSL owners: Xinjie Du, Sheng Xu, Zikun Cui.
  - **Impact: upstream table daily revenue $5,900,882; 4 impacted features; affects `F3_BATCH_FEATURE`** (Feed/ads batch-feature staleness → potential revenue loss). Suspected root cause: CORE_ADS over quota.
- Demonstrates he **owns and operates the production LSR-CMSL embedding-aggregation signal** — a revenue-material data dependency for ads batch features — not just research code.

---

## 2. Precise facts (what he actually works on)

- **Metric:** Normalized Entropy (NE), tracked both **offline** (Hive/Dataswarm over serving predictions; Workstream A) and **in-training** (TensorBoard/`ModelTracerMVAI` over MAST runs; Workstream B).
- **Models/tasks:** ads-delivery ranking models; prediction tasks **`cmf_click`** (Feed) and **`reels_click`** (Reels), multi-task heads for **impression / conversion / page_type / uih**. Offline eval compares candidate columns **`ofm_v3`, `ofm_v4`** to `prod`.
- **Architecture he owns/experiments on:** **CMSL** (Constructive Multi-Sequence Learning) — v0 → v1, with ablations across **MoE, pointwise gating, early fusion, learnable tokens, NRO-embedding scaling, EBF** and **LSR** long-sequence integration; plus an ads **FM/UHM** launcher baseline.
- **Infra/stack:** MVAI (`minimal_viable_ai`) "fire" training framework, MAST training jobs, Dataswarm/Chronos pipelines, Hive/`upm_data` datasets, `aps_models/ads/launchers/fm` launcher configs, Configerator app layers, `dper3` `ModelTracerMVAI` tooling.
- **Gain convention:** `100 * (model - prod) / prod` percent NE change.

---

## 3. Collaborators

**Same team — MRS Platform – Algorithms (manager Hong Li):**
| Name | Unixname | Role | How they intersect Junjie |
|---|---|---|---|
| Zikun Cui | `cuizk` | Research Scientist | NE-tracking reviewer (D99464246/D100272053/D100419242) **and CMSL co-owner**; reused his CMSL NE notebook |
| Tai Guo | `taiguoo` | SWE, ML | NE-tracking reviewer (D98380670/D99018172/D99160752/D99701305) |
| Tao Jia | `tjia` | Research Scientist **Manager** | Co-reviewer on fire-layer config D91958039 (team-lead layer) |
| Shiying He | `shiyinghe` | SWE | Frequent shared-review author |
| Li Sheng | `lisheng` | SWE (under Tao Jia) | Frequent shared-review author |
| Jian He | `jian6` | Research Scientist (under Tao Jia) | Frequent shared-review author |

**CMSL co-owners (cross-team, from SEV S642095):**
- Xinjie Du — `jaydu` — SWE, Ads Ranking Eng
- Sheng Xu — `shengxu` — Research Scientist, Ranking & Foundational AI (ADRL / Event2Vec)

**Teammates who cloned/reused his CMSL experiment-tracking notebook:** `cuizk`, `jinghanj` (Jinghan J.), `ikalemaj`.

**Frequent authors of diffs where he is listed as reviewer** (cross-team; note many auto-added — see §6): Jiajin Li (`jiajinli`, FBR Product Growth ML, 11), Kunal Khatri (`kunalkhatri`, Core Ads Growth, 10), Praveen Kumar Ashok (`praveenkashok`) / Padmanabhan Iyer (`paddyiyer`) (R&P Data Eng), Daniel Kasman (`danielkasman`, Signal Growth), Julien Odent (`jodent`, ATA XFN).

**MVAI/MAST co-alertees (share training infra/quota):** `xiangzhou`, `sumitkumar`, `yuhaodu`, `zhaikeke`, `zhongweiteng`.

---

## 4. Tasks / projects

**Finding: Junjie has essentially no hand-authored planning tasks.** All 500+ owned tasks and the created-task list are **auto-generated ops alerts**, which is itself evidence of the shape of his work (heavy training-job + pipeline operation). Notable *signal* items among the alerts:

| Task | Date | What it reveals |
|---|---|---|
| **T263457646 / T262493146** | 2026-04-06 / 04-01 | SEV S642095 follow-ups — CMSL embedding signal ownership |
| **T273703350 / T275633182** | 2026-05-31 / 06-12 | `cogwheel_video_fm_trunk_metrics_test` for **`mrs_algorithm_kd_eval`** — video FM trunk-metrics / knowledge-distillation eval |
| **T275666066** | 2026-06-12 | `minimal_viable_ai.recurring_train.recurring_train` failure — MVAI recurring training |
| **T265994634/638/639** | 2026-04-21 | Recurring training jobs "scheduling without production serving" (research runs) |
| **T261350396** | 2026-03-24 | Dataswarm sampling pipeline `ad_metrics.mrs_platform.sampling.get_fb_feed_vpv_ugc_fbid` |
| **T261114484** | 2026-03-23 | `organic_candidate` blocked in scope **"MRS Experiment"** (over quota) |
| **T276390528 / T273359911** | 2026-06-18 / 05-28 | **`ads_torchrec` oncall** + OSCAR ACL review for `ads_torchrec` |
| **T265394203** | 2026-04-17 | Privacy pre-screener for pipeline diff **D99018172** |
| **T263790880 / T263654989** | 2026-04-07 | `[MAST] Undeclared Sequence Storage` in `fire-junjieyang-*` jobs (sequence-feature training) |

These corroborate: CMSL signal ownership, video-FM/KD-eval involvement, MVAI recurring training, MRS-experiment data usage, and `ads_torchrec` oncall.

---

## 5. Volume stats (Jan 1 – Jul 10, 2026)

| Metric | Value | Notes |
|---|---|---|
| Authored diffs (total) | ~19 | |
| — **Substantive** | **9** | 7 NE-tracking (D98380670, D99018172, D99160752, D99464246, D99701305, D100272053, D100419242) + 1 fire-layer config (D91958039) + 1 baseline MAST config (D105034490) |
| — Administrative | ~10 | ACL / add-user / add-maintainer / write-permission (entitlement management) |
| Listed as reviewer | **300+** (capped) | ~132 human-authored of first 300; **many auto-added via directory/maintainer ownership** → over-counts active review |
| **MAST training jobs evidenced** | **≥410 distinct** `fire-junjieyang-*` | capped by task pull; true count higher — **the dominant signal of his output** |
| SEVs owned/mitigated | 1 | S642095 (L3) |
| Active window (substantive diffs) | 2026-01-30 → 2026-05-13 | NE-tracking burst 3/26–4/10; CMSL `cmsl_gating` experiments 4/16–4/19 (+ May clones) |

---

## 6. Confidence flags

**Verified (primary artifacts read):**
- NE-tracking pipeline location, structure, gain formula `100*(model-prod)/prod`, `ofm_v3`/`ofm_v4` vs `prod`, `multi_labels[1000002]` label, conv-type-filter removal (diffs + file lists).
- Junjie = CMSL owner; owns `lsr_cmsl_embedding_agg_encoded_ts_signal` (~$5.9M/day, F3 batch features); mitigated SEV S642095.
- `cmsl_gating` MoE / pointwise-gating experiment with specific MAST job IDs, tasks (`cmf_click`/`reels_click`), and multi-task heads (his own notebook N10471418).
- `fire-app-lsr-cmslv0` MVAI app-layer config (D91958039); `mast_es_fm_2026_uhm.yaml` baseline (D105034490).
- Collaborator identities/teams (`meta people.profile`).
- ≥410 distinct fire MAST job names (task extraction).

**Inferred (naming/structure, not confirmed):**
- Expansions of `ofm`, `EBF`, `uhm`, `fm`, `es`, `NRO`.
- That his notebook is the *source template* others cloned (earliest date + identical structure).
- That all ≥410 fire jobs are distinct experiments (some are likely recurring retrains of the same config).

**Key caveats:**
1. **Diffs undercount RS work.** ~9 substantive diffs vs **≥410 MAST training jobs** + experiment notebooks: the center of gravity of Junjie's H1 2026 work is **CMSL model training / architecture search** (MoE, gating, early fusion, embedding scaling, LSR/UHM), which lives in **MAST/MVAI runs and Bento notebooks, not landed code**.
2. **Reviewer count is inflated** by auto-add ownership/maintainer rules (he manages ACLs/entitlements for his directories) and bot-authored diffs; do not read 300+ as 300+ active reviews.
3. **Tasks are all automated alerts** — planning/decisions are not tracked in Tasks, so §4 reflects operations, not a project roadmap.
