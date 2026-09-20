# AURA‑Native: A Proposal for LLM‑Native User Foundation Modeling

**Prepared:** 2026‑07‑14 · **Author:** Tony Chen (`zgchen`), MRS Platform · Algorithms
**Status:** Design/strategy proposal (draft for review) — synthesized from the internal analyses in `work_analysis/` plus internal + external research. "Existing" vs "Proposed" is marked throughout; numbers carry provenance; honest gaps are in §11.
**One‑line thesis:** Evolve **AURA** from an *LLM‑inspired* user‑embedding tower into an *LLM‑native* generative user foundation model over a **unified, typed token sequence** (behavioral + aligned‑semantic + soft context), serving AURA's three consumption modes — embeddings, a distilled student, and an LLM‑native generative proxy — under Meta's privacy, launch, and serving constraints.

---

## 0. Executive summary

- **Where AURA is.** AURA (Hong Li's team's *User Intelligence Engine*) today produces user embeddings from behavioral towers (WHEN/UniArch in `//aps_models/exploration/aura_model`), aggregates them, and injects 16 `AURA_USER_EMBEDDING_*` F3 features into ads ranking (CMF/DPA/IG). Its own 26H1 doc names three consumption modes — **embeddings, a distilled small model, and an "LLM‑native consumption proxy"** — and lists **Generative UM** and **LLM‑native UM** as priorities. This proposal makes the LLM‑native workstream concrete.
- **The industry has converged on a shape**, and Meta is already there in pieces. LLM‑native ranking is best understood as an **input‑modality spectrum** (the "three paradigms"): (1) pure behavioral sequences (HSTU/CMSL) hit a scaling ceiling; (3) pure text is 40–50% below production at 100–10,000× cost; (2) a **unified token space** — behavioral tokens + *aligned* semantic‑ID codes + typed *soft* context tokens in one transformer — is the convergence point. The load‑bearing empirical claim (LLaTTE): **"semantic features bend the scaling curve — they are a prerequisite for scaling."**
- **What we propose (AURA‑Native).** A generative user FM whose **vocabulary** is a unified per‑event token set — collaborative/behavioral IDs (the dominant signal) + **collaboratively‑aligned** semantic IDs (from AdsLlama/TextRay/PixelGPT via RankID/RQ‑VAE) + typed soft context tokens (Paradigm 2b) — over the **cross‑surface event sequence** described in the Event‑Sequence North Star (organic 1PD + ads 1PD + offsite 3PD), trained with a **dual causal + masked objective**, **co‑trained with the ranking objective**, and **privacy‑native** (opt‑out via cohort_id, self‑supervised). It exposes AURA's three consumption modes and is **evolved autonomously by RankEvolve**.
- **The two hard truths we design around.** (i) **Alignment is the #1 problem** — raw content/semantic embeddings *hurt* mature rankers unless aligned to the collaborative/ID space; we make alignment a first‑class stage. (ii) **The inference gap is the gating blocker** (Meta's ST LLM north star says so) — we treat serving budget as a design constraint from day one and lean on Meta's Adaptive Ranking Model / M‑FALCON / distillation, not as an afterthought.
- **Framing that keeps us honest:** **LLM + CF, not LLM replacing CF.** Behavioral/collaborative signal dominates (~92% of HSTU's information); semantics unlock scaling and cold‑start, they don't replace collaborative filtering. We propose augmentation and a staged path, not wholesale cascade replacement.
- **Path:** Phase 1 (semantic enrichment of AURA towers as EBFs — lowest risk, AURA's existing "data‑enrichment" lever) → Phase 2 (co‑trained generative user FM producing embeddings + a distilled student) → Phase 3 (the LLM‑native generative proxy / generative retrieval + real‑time serving). Gated by Meta's MC process against the **0.05% NE** bar and GAS.

---

## 1. Context & motivation

### 1.1 Where AURA is today (the LLM‑inspired baseline)
AURA is a **homegrown user‑modeling platform** whose stated problem is that Meta's user understanding is **siloed** (organic vs ads blind spots), **lacks segment‑specific architectures**, and **doesn't combine world knowledge + cross‑surface engagement + social‑graph signals**. Current shape (verified from code/diffs in the AURA analysis):

```
AURA model (behavioral towers: WHEN / UniArch; multi-task CTR/CVR; user-embedding bottleneck)
   → aggregation (3-day pooling, carry-forward) + u2u KNN
   → Hive aura_user_embedding_source
   → 16 F3 features AURA_USER_EMBEDDING_0..15 (fam_horizontal_ml/flexible_batch)
   → injected into CMF / DPA / IG ranking-model training
```
This is **Paradigm 1‑ish**: behavioral user modeling, consumed as embeddings. It is live but early (enablement/exploration in H1 2026; the ~0.15% GAS half‑goal is a *target*, not a realized launch). The inputs it wants next — **AdsLlama semantic IDs, graph tokens, organic data, UD** — are exactly the semantic‑enrichment levers below. Feeder workstreams already exist: **UMS‑3PD** (Jin's offsite‑signals training‑data pipeline, from the PixelGPT/Signals lineage), the **Event‑Sequence North Star** (Jin's cross‑funnel data blueprint), and **CMSL/RankGraph** (Junjie).

### 1.2 The trajectory: "LLM‑inspired → LLM‑native," and where the field converges
Meta's explicit north star (**ST LLM**, SilverTorch, 2026‑07‑08): move from **LLM‑inspired** ("an encoder‑decoder that predicts the Semantic ID of the next item") to **LLM‑native** ("an LLM infused with RecSys domain knowledge and bringing world knowledge and reasoning"), and serve it **real‑time at RecSys scale** (hundreds of ms, thousands of QPS). Its stated **biggest blocker is the "modeling inference gap."**

The **three‑paradigm** lens (our conceptual backbone) maps the design space by *input modality*:
- **Paradigm 1 — pure behavioral sequence** (HSTU 1.5T; RankFM; CMSL). Proven, massive scale — but **hits a scaling ceiling without semantic enrichment** ("Actions Speak Louder than Words"; LLaTTE proved the ceiling).
- **Paradigm 2 — unified token space** (the convergence): **2a** discrete semantic codes in the vocabulary (InstaBrain, GRADIENT), **2b** typed *soft* tokens projected from any signal (Google Token Factory/PLUM; Meta LLaTTE direction — *the* convergence point), **2c** decoupled offline multimodal features (current Meta MM‑LLM).
- **Paradigm 3 — pure text** (ARS/STAR prototypes). NDCG 40–50% below production; 100–10,000× cost; **off the fine‑ranking hot path**.

**Key insight (LLaTTE):** *semantic features bend the scaling curve — a prerequisite for scaling.* Behavioral remains the dominant signal (~92% of HSTU's information; semantic fusion historically ~0.08 weight), which is why the correct framing is **augment, not replace.**

### 1.3 Why now / the gap
AURA is positioned to make the Paradigm‑1 → Paradigm‑2 jump *as a user model*: it already owns the user‑embedding bottleneck, the F3 consumption path, cross‑funnel data (North Star), and a stated LLM‑native ambition. The building blocks exist across Meta (semantic IDs/RankID, Meta LLM Rec, PNE, GRADIENT, RankAGI, LARGE/UMS, LLaTTE/GEM, Adaptive Ranking Model). What's missing is a **coherent user‑FM design that unifies them under AURA's three consumption modes, is privacy‑native, and is serviceable** — which is this proposal.

---

## 2. Design principles

1. **Unified, typed token space (Paradigm 2b + 2a).** Every event becomes a small set of *typed* tokens: collaborative/behavioral IDs + **aligned** semantic‑ID codes + soft context tokens (typed MLP adapters). One transformer over the union. Rationale: this is where Meta (LLaTTE, GRADIENT) and the field (Token Factory/PLUM) converge.
2. **Collaborative‑first; semantics as scaling fuel.** LLM + CF, *not* replace. Behavioral tokens carry the dominant signal; semantics unlock scaling, cold‑start, and cross‑surface transfer.
3. **Alignment is first‑class (not a side feature).** Content/semantic embeddings must be aligned to the collaborative/ID space *before* tokenization — every deployment that worked (QARM, IDProxy, DAS, RQ‑KMeans collaborative SIDs) did this; raw/frozen content embeddings *hurt* mature rankers. (Full treatment in §4.)
4. **Match objective to use case.** Causal next‑event generation for the generative/retrieval proxy; masked event modeling / bidirectional for embedding quality. Provide **both** (dual objective) rather than picking one — resolving the AR‑vs‑bidirectional inconsistency across UMS (AR), LARGE (bidirectional), Meta LLM Rec (masked set prediction).
5. **Co‑train with ranking; decouple heterogeneous tasks.** Co‑training with the production ranking objective is what made LARGE/GEM work; but naive multi‑task sharing causes the **seesaw / negative transfer**, so decouple via MoE / task‑aware tokens / gradient detachment (IDIOMoE, UniSGR).
6. **Privacy‑native.** Opt‑out modeled via **cohort_id** (not sid); self‑supervised so no labels are needed; cross‑funnel per the North Star. Privacy is a modeling constraint, not a bolt‑on.
7. **Serve within budget from day one.** The inference gap is the gating blocker; every phase carries a serving plan (Adaptive Ranking Model / M‑FALCON / KV‑cache / selective FP8 / distillation), and offline wins are only credible with a serving path.
8. **Build on existing Meta blocks; evolve autonomously.** Reuse RankID/AdsLlama/TextRay/PNE/GRADIENT/ExFM/mitra; use **RankEvolve** to evolve the tokenizer/architecture/objective under leak‑free NE + execution‑accuracy discipline.

---

## 3. Proposed architecture — AURA‑Native

### 3.1 The vocabulary: unified typed event tokenization
Each user event (organic post, ad, or offsite conversion) is encoded as a **set of parallel typed tokens** (PNE already does "event = ~10 parallel IDs": SID codebooks + event type + ad_id + semantic features):

- **(a) Collaborative/behavioral tokens** — item/ad/domain(eTLD+1) ID, action type, timestamp, surface. The dominant signal; keep them.
- **(b) Aligned semantic‑ID tokens** — RQ‑VAE/RQ‑KMeans codes over content embeddings (**AdsLlama/EEL** for ads/organic entities, **TextRay** for offsite domains, **PixelGPT/PixelBERT** for offsite behavior), produced/served via **RankID** (Meta's unified SID platform). **Aligned to the collaborative space** (§4).
- **(c) Typed soft context tokens (Paradigm 2b)** — user/context/candidate features projected by *per‑type* MLP "token makers" into the model space (à la Token Factory/LLaTTE). Preserves continuous signal without textualization.

Design choices grounded in Meta practice: codebook config near the **~3×256 sweet spot** (or multi‑resolution `[4096,2048,1024]`), because SID‑based GR **saturates** beyond it (quantization bottleneck); monitor the two intrinsic tokenizer metrics that predict NE — **token entropy (r≈0.73)** and **codebook utilization (r≈0.64)**; mitigate **codebook collapse** with k‑means init (the single most important lever) and codebook‑embedding‑level (not decoder‑output‑level) contrastive alignment. Consider **RQ‑FSQ** ("Quantizing Intent": matched dense AUC at ~280× storage, **+1.522% for users with near‑zero ad history** — direct cross‑domain‑transfer evidence).

### 3.2 The backbone: a generative user foundation model
- **Model:** a generative transformer over the unified token sequence. Two credible backbones — an **HSTU‑family** transducer (reuse Meta's scaling + M‑FALCON serving, HSTU‑CInt contextual interleaving) or an **adapted small LLM** (Qwen/Llama, à la RankAGI/PLUM/Meta LLM Rec) for world knowledge/reasoning. Recommend **starting HSTU‑family for the embedding/ranking path** (serviceable, proven) and **piloting an adapted‑LLM for the generative proxy** (§3.3 mode c).
- **Long context:** lifetime cross‑surface history via **ViSTA‑style virtual‑token compression** (condense 12K+ items into a compact user state) + local/recent full attention — the practical way to get "a year of history" without quadratic cost.
- **Objective (dual):** **causal next‑event** (for generation/retrieval) **+ masked‑event modeling** (for embedding quality), plus a **contrastive** term that aligns user states to next‑item/target representations (InfoNCE, in‑batch + hard negatives — the UMS‑3PD recipe). **Value‑aware heads** (eCPM/GAS) so generation prioritizes high‑value outcomes (UniSGR's value‑aware multi‑token idea).
- **Co‑training + decoupling:** co‑train with the production ranking objective; isolate heterogeneous heads via **MoE / task‑aware tokens / gradient detachment** to avoid the seesaw.

### 3.3 Consumption — serving AURA's three modes (this is the integration contract)
1. **Embeddings (today's path).** The user state → L2‑normalized/FP16 EBF → `AURA_USER_EMBEDDING_*` F3 features → CMF/DPA/IG. Zero disruption; reuses Jin's live pipeline. *Lowest‑risk first win.*
2. **Distilled small model.** Distill the FM into a servable student (ExFM external‑distillation pattern; RankAGI's on‑policy 4B→0.6B). Decouples training scale from serving latency.
3. **LLM‑native generative proxy.** Generative retrieval (U2I/U2A) via constrained SID decoding (trie/beam), served real‑time — the ST‑LLM "LLM‑native path." Build on **GRADIENT** (Ads GR: enc‑dec, 300+ beams, constrained decode, RL, ~10× FLOPs reduction), **InstaBrain** (IG: Llama‑3.2‑1B generates SIDs, 17× training efficiency), **RankAGI**, and serve via **RLS** (Rec LLM Service).

### 3.4 Data — the Event‑Sequence North Star, operationalized
- **Cross‑funnel sequence:** organic 1PD + ads 1PD + offsite 3PD, unified by the typed‑token vocabulary (§3.1). This directly attacks AURA's "siloed user understanding" problem and aligns with **UME (Unified Meta Embeddings)**.
- **Privacy‑native keys:** `separable_id` (opt‑in) unioned with `cohort_membership_id` (opt‑out); self‑supervised so unattributed offsite events (~majority) are usable.
- **Close the North Star's stated gaps (critical path):** organic↔cohort mapping ("cannot map back to cohort id" today), thin opt‑out content coverage (24% for url+pagetitle+keywords), and source consolidation into `sg_offsite_signals_embedding`. These are coordination‑bound (He Hao, Signals/CAPI, MRS Knowledge) — see §9.

### 3.5 Serving & the inference gap (a first‑class constraint)
The gating blocker per ST LLM. Reuse Meta's serving co‑design rather than inventing:
- **Meta Adaptive Ranking Model** ("Bending the Inference Scaling Curve"): **Request‑Oriented Optimization** (compute the dense user context once/request) + **In‑Kernel Broadcast** (share it across candidates in the GPU kernel) → sub‑linear scaling; **selective FP8**.
- **M‑FALCON** (score M candidates in one forward pass via causal‑mask sharing) + **KV‑cache / context parallelism** (reuse UIH states, 80–90% redundant‑compute reduction).
- **Non‑AR embedding path**: Meta LLM Rec's masked‑set‑prediction served via HF forward pass (+45% throughput over vLLM) for the EBF mode.
- **Distillation** (ExFM) for anything hot; **RLS** for the generative proxy.

---

## 4. The alignment problem (the #1 technical risk — dedicated treatment)
Every serious deployment converges on one lesson: **raw/frozen multimodal or content embeddings do not help — and often hurt — a mature ranker; they must be aligned to the collaborative/ID embedding space and made trainable end‑to‑end under the ranking objective.**

- **Evidence:** Google found dense content embeddings *underperform random‑hashed IDs*; Xiaohongshu **IDProxy** contrastively aligns MLLM proxy embeddings to the actual ID distribution → **2× cold‑start AUC**; Kuaishou **QARM** diagnoses "representation unmatching/unlearning" and fixes it via item‑item alignment + trainable code‑IDs; **DAS** does one‑stage dual (quantization + collaborative) alignment; **RQ‑KMeans** injects collaborative signal into the tokenizer.
- **Our design:** an explicit **alignment stage** — fine‑tune the content encoder / tokenizer with a collaborative contrastive objective (u2i/i2i/u2u) *before* freezing SIDs; place contrastive loss at the **codebook‑embedding level** (works) not the decoder‑output level (conflicts with reconstruction); keep code‑IDs **trainable** in the downstream FM.
- **The quantization ceiling (instrument it):** SID‑based GR saturates as you enlarge the encoder/tokenizer (the ~3×256 sweet spot); text‑based GR can exceed the SID ceiling by ~20% but at prohibitive cost. If scaling the FM shows early saturation, the bottleneck is **SID information capacity**, not backbone size — invest in richer/aligned tokenizers or hybrid dense+SID (LIGER/COBRA), don't just buy params.

---

## 5. Phased roadmap

| Phase | Deliverable | Consumption mode | Builds on | Gate / metric |
|---|---|---|---|---|
| **P1 — Semantic enrichment of AURA towers** | Add **aligned** semantic‑ID + typed soft‑token features to the AURA user tower; ship as EBFs | Mode 1 (embeddings) | RankID/AdsLlama SIDs, UMS‑3PD data, Jin's F3 pipeline (live) | Leak‑free NE on CMF/DPA/IG; **>0.05% NE** = real → MC gate; cold/long‑tail slices |
| **P2 — Generative user FM (co‑trained)** | Train the unified‑token generative user FM (dual causal+masked, co‑trained, privacy‑native); emit embeddings + distilled student | Modes 1 + 2 | HSTU‑family/ViSTA, LARGE/GEM patterns, North Star data, ExFM distillation | Offline NE vs LARGE/UMS baselines; distilled‑student parity; MC1/MC3 |
| **P3 — LLM‑native generative proxy** | Generative retrieval (U2I/U2A) via constrained SID decoding; real‑time serving | Mode 3 (LLM‑native proxy) | GRADIENT/InstaBrain/RankAGI, RLS, Adaptive Ranking Model | Retrieval recall + topline GAS; latency SLA (ST‑LLM M2→M3) |

**Cross‑cutting throughout:** RankEvolve‑driven evolution (§7); leak‑free eval discipline; serving co‑design; the North Star data‑gap program (§3.4).

**Sequencing rationale:** P1 is the lowest‑risk, highest‑certainty win (it *is* AURA's named "Tower User Modeling with Data Enrichment" lever, reuses a live pipeline, and preserves ranking calibration). P2 earns the FM its keep as embeddings/distillation before betting on generation. P3 crosses the inference gap only after the representation is proven.

---

## 6. Evaluation & launch (Meta practice)
- **Offline:** **NE** (lower better; **date‑aligned** vs V0 to prevent leak/skew; **>0.05%** change is real, ±0.02% is parity; **NE→EBR ≈ 4:1**). Report **cold/long‑tail slices** explicitly — semantics win there and aggregate metrics can *hide or even regress* the win (Hi‑SAM). Track the intrinsic tokenizer metrics (entropy/utilization).
- **Online:** **GAS** via the **MC (Model Change) process / QRT reading**; MC1/MC3/MC12 gates each carry per‑metric bars + a **pre‑launch GAS segmentation check**. Reference scale: **1% GAS ≈ 0.32% iRev**.
- **Discipline:** leak‑free full‑corpus eval is non‑negotiable (it repeatedly caught silent leaks a metric‑only loop would reward); trust online A/B over offline NDCG (reproducibility crisis).

---

## 7. RankEvolve as the evolution engine
AURA‑Native has a large, expensive design space — tokenizer (RQ‑VAE vs RQ‑KMeans, codebook size/depth, alignment recipe), backbone (HSTU vs adapted‑LLM, depth, compression), objective (causal/masked/contrastive weighting, value heads), and fusion (soft‑token adapters, MoE routing). Each candidate costs hours–days of GPU. This is exactly RankEvolve's target: **autonomously propose→implement→evaluate** these axes under **execution‑accuracy** cross‑checking (heterogeneous agents) and **leak‑free NE** discipline, cataloguing negative results so we don't re‑derive dead ends. The `has_item_embedding`/`emb_dim`/AR‑vs‑bidirectional/codebook knobs are natural evolution parameters; RankEvolve‑CMSL already demonstrated the pattern (Dual‑Stream discovery, +0.15–0.2% NE, "days not months"). This is where our team's differentiated tooling compounds the modeling work.

---

## 8. Positioning — build on, don't duplicate

| Existing effort | Relationship to AURA‑Native |
|---|---|
| **AURA towers + F3 (Jin)** | The substrate we extend; P1 rides the live embedding→EBF pipeline. |
| **LARGE / UMS (SAGE)** | Sibling LLM‑native *ranking* model; AURA‑Native is the *user* FM feeding it. Share tokenizer/serving; avoid rebuilding a ranking head. |
| **CMSL / RankGraph (Junjie)** | Sequence + graph signal *inputs* (collaborative tokens); consume, don't rebuild. |
| **HSTU / RankFM‑2** | Backbone + FM/Expert paradigm; adopt for P2. |
| **Meta LLM Rec / PNE** | Reference designs for masked‑set‑prediction serving and "event = parallel IDs"; reuse patterns. |
| **GRADIENT / InstaBrain / RankAGI** | Generative‑retrieval + LLM‑native proxy blueprints for P3. |
| **RankID / AdsLlama / TextRay / RQ‑FSQ** | The tokenizer/semantic‑ID supply chain; consume via RankID. |
| **ExFM / Adaptive Ranking Model / RLS / M‑FALCON** | The serving/distillation answer to the inference gap. |
| **LLaTTE / GEM / COFFEE / Zen** | Prior art proving semantic enrichment + scaling wins; calibrate expectations, borrow lessons. |

**Net:** AURA‑Native is the *unifying user‑FM layer* across these — not a competitor to any single one.

---

## 9. Risks & open questions (honest)
1. **Alignment (highest):** if aligned semantic SIDs stop beating sparse IDs even on cold slices, the encoder/alignment is the problem, not the paradigm. Mitigation: §4 as a first‑class stage; gate on cold/1‑day slices.
2. **Quantization bottleneck:** SID saturation caps scaling; instrument entropy/utilization; consider hybrid dense+SID.
3. **Negative transfer / seesaw:** decouple heterogeneous heads (MoE/task‑aware tokens); if adding a task drops ranking NE >1–2% under shared params, isolate it.
4. **The inference gap (gating):** P3 is infeasible without serving co‑design; keep P1/P2 (embeddings/distillation) as the value‑delivering fallback if real‑time generation misses SLA.
5. **"LLM + CF, not replace":** internal RecLLM finding — LLM backbones "get close to prod but don't exceed" without CF. Position as augmentation; don't over‑promise cascade replacement.
6. **Data coverage / opt‑out (critical path):** organic↔cohort mapping, opt‑out content coverage, cross‑team dependencies (He Hao, Signals/CAPI, MRS Knowledge). Modeling is ahead of data; fund the North Star data program in parallel.
7. **Scaling is uneven/task‑dependent** (Meta's own 2026 GR finding); expect ceilings on short‑horizon tasks where "objective/serving changes matter more than capacity."
8. **Org duplication risk:** LARGE, RankAGI, GEM, LLaTTE, Meta LLM Rec all live nearby — AURA‑Native must be the *user‑FM unifier*, explicitly consuming their outputs (§8), or it risks re‑implementing them.

---

## 10. Bottom line
AURA already has the mandate (LLM‑native UM), the substrate (user‑embedding bottleneck + F3), the data blueprint (North Star), and the neighbors (LARGE/CMSL/RankGraph/RankAGI/GRADIENT) to make the Paradigm‑1 → Paradigm‑2 jump *as a user foundation model*. The winning shape is settled in the evidence: **a generative model over a unified, typed token sequence — behavioral + collaboratively‑aligned semantic + soft context — co‑trained with ranking, privacy‑native, and served within budget.** The two things that decide success are **alignment** and the **inference gap**; we make both first‑class. Delivered in three de‑risked phases (embeddings → co‑trained FM → generative proxy) and evolved by RankEvolve, this turns AURA from a user‑embedding provider into Meta's LLM‑native user intelligence engine.

---

## 11. Appendix — grounding, glossary & caveats

**Glossary.** AURA = User Intelligence Engine (Hong Li's MRS Platform‑Algorithms; `//aps_models/exploration/aura_model`; 3 consumption modes; 26H1 Generative/LLM‑native UM). UMS = User Modeling with Semantics (SAGE program; UMS‑Ranking=LARGE / UMS‑Retrieval / UMS‑3PD). LARGE = LLM Ads Recommendation Generation Engine. CMSL = Constructive Multi‑Sequence Learning (Junjie). RankGraph = graph‑AI (Junjie). HSTU / HSTU‑CInt = Meta's generative‑recommender sequence backbone; RankFM‑2 = FM/Expert paradigm. RankID = unified semantic‑ID platform; RQ‑VAE/RQ‑KMeans/RQ‑FSQ = residual quantizers; EEL = AdsLlama entity embeddings; TextRay = offsite text embeddings; PixelGPT/PixelBERT = offsite event‑seq encoders. Meta LLM Rec / PNE = Mitra Gen‑RecSys models. GRADIENT/InstaBrain/RankAGI/OneFlow/MBSU = generative‑retrieval / LLM‑native efforts. LLaTTE/GEM/COFFEE/Zen = LLM‑scale ads models. ST LLM = SilverTorch real‑time LLM‑rec north star. Adaptive Ranking Model / M‑FALCON / RLS / ExFM = serving/distillation. EBF = Embedding‑Based Feature; F3 = feature store; NE = Normalized Entropy; GAS = Global Ad Score; MC = Model Change launch process; sid/separable_id vs cohort_id = opt‑in vs opt‑out keys; 1PD/3PD = first/third‑party data.

**Grounding sources.** Internal analyses in `work_analysis/` (UMS/Event‑Sequence/PixelGPT; AURA context; Jin/Junjie H1 reports) + `references/` (three_paradigms; internal‑practice addenda; external SOTA surveys). Internal primary sources surfaced via knowledge search: ST LLM (SilverTorch); Mitra Gen‑RecSys post (Meta LLM Rec + PNE, diffs D103689472/D102721021/D104171673); GRADIENT/GR wiki; InstaBrain/CTV‑InstaBrain; RankAGI landscape; RankID (Semantic‑ID/OVIS wiki, "High Quality Tokens"); "Quantizing Intent" (RQ‑FSQ); Ads Score Metrics / Core Performance Metrics (GAS/NE, MC); Foundation Models wiki (GEM/ExFM/LLaTTE UM‑XL); MRS Science Book (HSTU/ViSTA/RankFM‑2). External: HSTU (arXiv 2402.17152), TIGER (2305.05065), PLUM (2510.07784), OneRec (2506.13695), QARM (2411.11739), IDProxy (2603.01590), Semantic‑ID scaling (2509.25522), Token Factory (2606.19635), LLaTTE (2601.20083).

**Caveats.** (1) This is a *proposal*, not a sanctioned roadmap; "Proposed" items are forward‑looking. (2) Some internal specifics are single‑source/provisional — **LARGE's exact figures** (16‑layer BidirectionalLLAMA, O(500) tokens, ~5.3% gap, MC1 date) came from one paste and were **not independently re‑verified**; UMS‑3PD's exact table/width are config‑specific; execution‑accuracy and several GR/UM numbers are provisional/offline. (3) External A/B percentages are vendor‑reported. (4) AURA's acronym expansion is not firmly pinned; it is described by function. (5) Two docs were access‑blocked (the AURA design doc `1wvFJqDG…` was read; the V1 debugging doc `1zfw3D7X…` was 404). Verify load‑bearing numbers against owning‑team docs before external use.
