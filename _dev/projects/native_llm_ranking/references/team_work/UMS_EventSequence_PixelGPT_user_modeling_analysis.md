# Foundational User Modeling from Event Sequences — Deep Analysis

**Docs analyzed:** (1) *UMS for 3PD — Model & Training Notes*; (2) *[MRS internal-only] Event Sequence Data North Star* (Jin Yang, MRS; Shanshan Zhang); (3) *PixelGPT V2 Design* (Weixiang Hong, Justus Ge, Jin Yang, Signals).
**Prepared:** 2026-07-14 · **Sources:** the three documents' full text (authoritative for their own content) + a project-level internal knowledge search for grounding of systems/acronyms.

---

## 0. Scope, confidence & how to read this

- The three documents' technical content is taken **verbatim** from what was provided (authoritative). Systems/acronym grounding (SAGE, AdsLlama/EEL, TextRay, RQ‑VAE, SG, HLLM, LARGE, RankFM‑2, CFR, privacy terms) comes from an internal knowledge search over pastes/wikis/diffs/posts and is cited in the **Glossary (§8)**.
- **Maturity honesty (read first):** most of this cluster is **V0 / in-development with offline NE numbers and no confirmed topline (GAS/revenue) launch yet.** UMS‑3PD: infra landed, no production launch. LARGE (UMS‑Ranking): driving toward a first launch (bar 0.05% NE; MC1 target ~08/01/2026), offline only. PixelGPT: **V1 has a real identity‑matching win (+0.41 MR)**; **V2 is design-stage.** Treat impact claims accordingly.
- Where I infer or connect beyond the docs, I say so. A few referenced Google Docs could not be opened directly; corroboration came from internal pastes/wikis that quote them.

---

## 1. Executive summary — the through-line

These three documents are **three layers of one program: build a foundational *user* model from a comprehensive, semantically-tokenized *event sequence*, under privacy/opt-out constraints.**

| Layer | Document | What it is | Owner context |
|---|---|---|---|
| **Model** | UMS for 3PD | The user encoder — an HLLM/Llama‑1B run over a sequence of per-event content embeddings, trained self-supervised (next-item contrastive) | SAGE/UMS (mitra `cross_domain_relevance`) |
| **Data blueprint** | Event Sequence Data North Star | The plan for *what sequence to feed it* — comprehensive cross-funnel events (organic 1PD + ads 1PD + offsite 3PD), each event a SOTA content-understanding token | **Jin Yang (MRS)** + Shanshan Zhang |
| **Offsite event encoder** | PixelGPT V2 | Models offsite pixel/domain/semantic-ID event sequences → event/user representations; the offsite content-understanding + semantic-ID feeder | **Jin Yang (Signals)** + Weixiang Hong, Justus Ge |

**Where it sits.** UMS is one of three workstreams in the **SAGE (formerly AdsLlama)** "User Modeling with Semantics" program — **UMS‑Ranking (= LARGE)**, **UMS‑Retrieval**, and **UMS‑3PD** (Doc 1). It is adjacent to, but distinct from, the other MRS user/ranking foundation-model efforts — **HSTU‑based RankFM‑2**, **CMSL**, and **RankGraph**. Its output (user embeddings) is consumed as features (**EBFs**), for U2U/U2A retrieval, and by the **CFR UserFM** model.

**The Jin Yang thread.** Two of the three docs are hers, and they mark a clean arc: at **Signals** she built **PixelGPT** (offsite pixel/event-sequence modeling for identity matching + ranking); moving to **MRS**, she authored the **Event Sequence Data North Star** — the data-side blueprint for the foundational user model. She is carrying offsite/3PD + content-understanding + identity event-sequence expertise into the MRS UMS effort.

---

## 2. The three works in depth

### 2.1 UMS (UserModelingWithSemantics) — the model (Doc 1 = the UMS‑3PD config)

**Lineage.** `UserModelingWithSemantics` subclasses **HLLM** (Hierarchical LLM; ByteDance 2024, arXiv:2409.12740). HLLM's design is two-tier: an **item LLM** (item content → item vector) and a **user LLM** (item-vector sequence → user representation).

**The decisive switch — `has_item_embedding=True`.** In this 3PD config the item LLM is **never built**; the item side is just `nn.Linear(1024→2048)` over **precomputed** item embeddings. Only the **user LLM** (a Llama‑3.2‑1B, hidden 2048, loaded from an internal Manifold `ads_llama_ift` checkpoint — i.e., tied to the AdsLlama program, not the public HF hub) is a real LLM; its token-embedding table is **frozen** because the model never uses token ids. So this is the *embedding-fed* HLLM variant: **item understanding is delegated to upstream embeddings; only the user-level sequence model + a projector are trained.**

**Forward pass (data flow).** `input_embeddings [N, S+1, 1024]` → project to `[N, S+1, 2048]` → split into history (`[:, :-1]`, fed to the user LLM) and target (`[:, -1]`, the positive) → add timestamp position ids and a history-summary compression (recent_k=8, old prefix compressed into a CLS token) → `user_llm(inputs_embeds=history, …)` → per-position `user_embedding [N, S, 2048]` → **autoregressive global-contrastive loss** (each position *t* predicts item *t+1*; **in-batch negatives**; InfoNCE; learned temperature).

**Trained vs. static.** Trained: the projector (the *entire* item "encoder" here), the user LLM (except the frozen token table), heads. Static: the raw 1024-dim input embeddings — they are *input data*, produced upstream (this is the seam to Docs 2 & 3).

**Data & the width contract.** Source Hive table `ad_delivery.test_ums_3pd_embedding_training_data_hash_sampled`; a **schema-aliasing** layer renames 3PD columns (`history_embeddings→click_ad_feature_list`, `target_embedding→target_ad_feature`, `history_event_times→click_ts_list`, `unified_id→ad_id/separable_id`, `label`/`weight`=constant 1.0) onto the fields the existing UMS pipeline expects — this is *how 3PD plugs into the pre-existing UMS plumbing*. `label=1.0` is constant because training is self-supervised/contrastive (every real sequence is a positive; negatives are sampled in-batch). **`emb_dim=1024` is a hard width contract** — embeddings whose length ≠ 1024 are dropped, so the setting must match the true embedding width for 3PD data.

*(Corroboration/nuance from internal grounding: the broader UMS‑3PD effort reads from `sg_offsite_signals_embedding` and, in one V0 instantiation, uses `nn.Linear(1000→2048)`; it unions opt-in offsite events keyed by `separable_id` (~23B/day) with opt-out events keyed by `cohort_membership_id` (~13B/day), and is self-supervised specifically so it can learn from the ~80% of matched-but-unattributed offsite events that supervised encoders discard. Doc 1's `test_…hash_sampled` table at width 1024 is one concrete training snapshot of this; treat the exact table/width as config-specific.)*

**Role in the program:** the **"LLM-inspired"** user encoder — a Llama consuming per-event content embeddings. The **"LLM-native"** endpoint is its sibling **LARGE** (a 16-layer bidirectional-LLAMA, RQ-quantized event tokens, co-trained with a ranking head).

### 2.2 Event Sequence Data North Star (Jin Yang, MRS; Shanshan Zhang) — the data blueprint (Doc 2)

**Goal.** Identify the *best-possible data scenario* for event sequences to build a **foundational user model**, meeting two criteria: (a) each user's sequence is the **most comprehensive user history**, and (b) each event is represented by **comprehensive, SOTA content-understanding tokens**. The stated north star: **"from LLM-inspired to LLM-native modelling"** — using UMS as the model-arch example.

**Sequence construction — three event types (the full funnel, onsite→offsite, organic→ads):**
1. **Organic feeds (1PD)** — interactions with FB/IG feeds/content.
2. **Ads (1PD)** — interactions with promoted ads on Meta products.
3. **Offsite events (3PD)** — interactions on third-party sites (pixel/CAPI/SDK), organic or ads-triggered.

**Raw event representation.** Each event should carry the best representation — embeddings/tokens — built from one or more of: raw page materials (web crawl, screenshot), learned embeddings (**AdsLlama** content-understanding, **TextRay** from url/keywords), and linked properties (attributed ads for 3PD, ads taxonomy).

**Table 1 (data inventory) — the operational heart.** It enumerates, per event category, the data name/format, **user resolution** (cohort_membership_id vs sid), ownership (**SG**), availability to **SAGE**, source table, and coverage. The document **focuses on opt-out users**.

**Explicit gaps/dependencies surfaced in Table 1 (these are the critical path — see §4.5):**
- **Organic requests: "Cannot map back to cohort id"** — a real blocker for including organic events in opt-out sequences.
- Attributed 3PD event unit + event-domain-L2-url: **"need further work from He Hao"**; attributed events need to move to `sg_offsite_signals_embedding`.
- url+pagetitle+keywords embedding: **only 24% coverage for opt-out**.
- Web crawl/screenshot: **opt-in only** (ASA opt-in version; 2-day retention).
- Cross-team touch points named: He Hao, Mina Ghashami, Franklin Lin, Zhenyuan Liu, Yufei Liu.

**Appendix — cohort_id ↔ sid.** DPA training rows carry a packed cohort ID in `float_map_enrichment[110000001]` (four 16-bit components, reconstructed by bit-shifts); CID→SID resolves via `ad_metrics:corhort`. This identity-resolution plumbing is a recurring dependency for stitching multi-source sequences under opt-out.

**Role:** defines *what data feeds UMS* and the path to the LLM-native user model. Doc 2 is the **data contract** that Doc 1's model consumes.

### 2.3 PixelGPT V2 (Jin Yang, Signals; Weixiang Hong, Justus Ge) — the offsite event encoder (Doc 3)

**V1 (existing).** An autoregressive (GPT-style) Transformer over **PixelID sequences** (`data_source_id_sequence`) — proved you can model user behavior from PixelID order alone. Internal grounding: V1 shipped as features into the **Unified Ranking** identity-matching model for **+0.41 MR gain** (a concrete, launched win — the strongest "shipped" result in this cluster). (The BERT/MEM variant is tracked internally as **PixelBERT**, "an implementation of the PixelGPT model.")

**V2 — three upgrade axes:**
- **Representation (richer input & labels):** from single PixelID token → a **multi-modal fused event vector** (PixelID + timestamp + attribution type + IP/UA/device + pluggable pretrained embeddings), summed/concatenated per timestep. Output uses **global average pooling or a [CLS] token** (not the last token, to avoid end-of-sequence bias). Adds **attribution labels**.
- **Architecture (AR → bidirectional):** trials a **BERT-style bidirectional Transformer with Masked Event Modeling (MEM)** — mask ~15% of events, reconstruct them — arguing that for **feature generation** (where the full sequence is available at inference) bidirectional context yields **higher-quality, more stable embeddings** than next-token prediction. Starts with single-task (predict PixelID) before multi-task full-event recovery.
- **Robustness (infra):** migrate from a native-PyTorch **bento notebook** to **APS or PyPer** (production MLOps).

**Vocab curation.** V1's 30k PixelID vocab is too high-cardinality to be admissible in downstream CVR proposals; V2 defines a **curated high-value shared vocab** with CVR/partner teams to re-enable the embedding downstream.

**Use-case expansions (appendix, from Yufei Liu):** (1) **PixelID → domain / eTLD+1 id** — capture both 1PD and 3PD events, including non-pixel-integrated 1PD; (2) **opt-out expansion** — retrain on **cohort-id sequences** covering both opt-in and opt-out conversions for a complete opt-out view; (3) **semantic-ID sequences** — `domain → LLM description → pretrained embedding → semantic ID`.

**Role:** the **offsite content-understanding + semantic-ID feeder**. PixelGPT/PixelBERT produce the offsite event/user representations and the domain→semantic-ID direction that the North Star relies on and that ultimately become UMS input tokens.

---

## 3. How the three interlock (the integration architecture)

The cluster is a **layered pipeline with an embedding/token "contract" between layers:**

```
 CONTENT-UNDERSTANDING ENCODERS            SEQUENCE ASSEMBLY (data)        USER MODEL              DOWNSTREAM
 ─────────────────────────────            ────────────────────────        ──────────             ──────────
 AdsLlama/SAGE  → EEL 256-d entity emb                                     UMS (HLLM)             CFR UserFM
 TextRay 1024-d → RQ-VAE semantic IDs  ─▶  Event Sequence North Star  ─▶   Llama-1B over     ─▶   Ads ranking EBFs
 PixelGPT/PixelBERT (offsite pixel/     │  comprehensive per-user           inputs_embeds          U2U / U2A retrieval
   domain/semantic-ID seq)              │  sequence: organic 1PD +          (AR contrastive)       cold-start imputation
                                        │  ads 1PD + offsite 3PD,                                  targeting
 (each event → a content-embedding      │  each event = a content token
  or semantic token)                    │  under opt-out/cohort constraints
                                        ▼
                            "has_item_embedding=True" contract:
                            item understanding is precomputed upstream;
                            UMS trains only the projector + user LLM
```

**The seam that ties Doc 1 to Docs 2–3.** Doc 1's "**precomputed 1024-dim item embeddings from an upstream pipeline, read from Hive**" are exactly the **content-understanding embeddings** Doc 2 specifies and Doc 3 (plus AdsLlama/TextRay) produces. `has_item_embedding=True` is *the architectural expression of this division of labor* — it turns the content encoders into swappable upstream producers and lets UMS consume their output as a static token stream.

**The semantic-ID convergence.** PixelGPT V2's `domain → LLM description → embedding → semantic ID`, the North Star's "content-understanding tokens," and the offsite **TextRay → RQ‑VAE semantic ID** chain are the **same idea from three vantage points** — discretize event/domain content into hierarchical semantic tokens so events become a compact, unified, downstream-admissible vocabulary. This is the mechanism for the "LLM-inspired → LLM-native" transition.

---

## 4. Critical analysis (the deep-dive)

### 4.1 Architectural coherence & the modularity trade-off
The strongest design idea across the cluster is the **embedding-as-contract modularity** (`has_item_embedding=True`). It lets content encoders (AdsLlama, TextRay, PixelGPT) and the user model evolve **independently and in parallel**, and makes training far cheaper (no giant item LLM in the loop). **Trade-off:** the item embeddings are **static** — not fine-tuned for the user-modeling objective — so representation quality is **upper-bounded by the upstream encoder**, and any distribution shift between "how the embedding was trained" and "what the user model needs" is unrecoverable. The program's answer is the **LLM-native** direction (LARGE): co-train the sequence model with the ranking objective and quantize events into learned tokens, recovering some of the joint-training signal the full HLLM had. UMS‑3PD sits at the *pragmatic, decoupled* end of that spectrum; that is the right call for a **privacy-constrained, multi-source V0**, but it should be understood as a floor, not the ceiling.

### 4.2 The objective question: autoregressive vs bidirectional (a genuine cross-doc tension)
There is an unresolved, program-level design axis hiding in plain sight:
- **UMS‑3PD (Doc 1): autoregressive** next-item contrastive.
- **PixelGPT V2 (Doc 3): bidirectional** Masked Event Modeling — argued to give better *embeddings*.
- **LARGE (sibling): bidirectional**-LLAMA.

The reconciling principle (which the docs gesture at but never state jointly): **match the objective to the use case.** For **generative/next-item retrieval**, AR is natural. For **feature/embedding generation**, where the *entire* sequence is available at inference, **bidirectional/MEM is better** (no end-of-sequence bias; richer context). UMS‑3PD is used partly for retrieval (AR defensible) but its embeddings are also consumed as features — where PixelGPT V2's and LARGE's bidirectional argument applies. **Open question worth forcing:** should UMS's feature-generation path adopt a bidirectional/MEM head, or keep AR and rely on per-position pooling? The cluster currently answers this inconsistently.

### 4.3 Embedding-space unification & the width/semantic contract
The North Star wants **many** content sources — AdsLlama/EEL (**256-d**), TextRay (**1024-d**), url/pagetitle/keywords embeddings, organic embeddings — but UMS's `emb_dim` is a **single hard width** (1024 here). Mixing sources requires reconciling **both dimension and semantic space** (a 256-d AdsLlama vector and a 1024-d TextRay vector don't live in the same space). Two implications:
- Continuous multi-source fusion needs an alignment/projection layer per source (more moving parts, more drift).
- **Semantic IDs (RQ‑VAE) are the cleaner unifier** — discretizing each source into a shared token vocabulary sidesteps the width/space mismatch and gives downstream cardinality control. This is likely *why* the whole cluster is converging on semantic IDs; it's not just a modeling fashion, it's the integration fix.

### 4.4 Privacy/opt-out as the binding constraint (what makes this hard and distinctive)
This is the thread that defines the difficulty. Opt-out users **cannot be modeled per-user** — only via **`cohort_membership_id`** — while opt-in uses **`sid`/`separable_id`**. The North Star's explicit opt-out focus, UMS‑3PD's **dual-key** union (separable_id + cohort_membership_id), and the **self-supervised** objective (so no labels are needed, letting it learn from the ~80% matched-but-unattributed offsite events supervised encoders throw away) are all consequences of this constraint — and are the cluster's most defensible source of *incremental* value ("signal others aren't capturing," per the PixelGPT appendix). **The cohort_id↔sid resolution (Doc 2 appendix) is a load-bearing, recurring dependency** across all three works; it is where correctness and coverage are won or lost.

### 4.5 Data coverage & cross-team dependency gaps (the real critical path)
The North Star is refreshingly honest that the *model* is ahead of the *data*. The concrete blockers:
- **Organic ↔ cohort mapping is unsolved** ("cannot map back to cohort id") — so the "comprehensive" sequence is, today, **missing organic for opt-out users**, undercutting criterion (a). This is the single biggest gap between the north star and reality.
- **Attributed 3PD events + domain-L2-url need work (He Hao)** and consolidation into `sg_offsite_signals_embedding`.
- **Opt-out content coverage is thin** (24% for url+pagetitle+keywords; crawl/screenshot opt-in-only).
- Success depends on **≥5 named cross-team owners**. This is a coordination-bound program as much as a modeling one; schedule risk lives here, not in the model code.

### 4.6 Downstream admissibility & cardinality
A subtle but important production constraint: a user/event representation is only useful if **downstream ranking models will accept it**. PixelGPT V1's 30k-vocab PixelID embedding was **rejected from CVR proposals for being too high-cardinality** — hence V2's **curated vocab** and the pivot to **domain/semantic IDs** (naturally hierarchical, cardinality-controlled). UMS likewise must land as **admissible EBFs**. Designing for downstream cardinality/latency budgets from the start is a maturity signal the cluster has internalized (curated vocab, RQ tokens, dense-arch simplification).

### 4.7 Infra maturity trajectory
A consistent sub-theme: **research notebook → production framework.** PixelGPT V1 (bento notebook) → V2 (APS/PyPer); UMS lives in **mitra** (the MRS/CU production training framework). The cluster is deliberately paying down research-prototype debt to get engineering robustness and velocity — appropriate for efforts now aiming at launch bars.

---

## 5. Status & maturity (honest)

| Effort | Status | Evidence of impact |
|---|---|---|
| **UMS‑3PD** (Doc 1) | V0 infra landed; **no production launch** | Qualitative/offline only; topline = not found |
| **UMS‑Ranking / LARGE** (sibling) | Driving toward first launch (bar 0.05% NE; MC1 ~08/01/2026) | Offline NE ~0.02–0.05% (some regressions); topline placeholder |
| **Event Sequence North Star** (Doc 2) | Vision/data blueprint | Planning doc; data gaps open (§4.5) |
| **PixelGPT V1** (Doc 3 baseline) | **Launched** into Unified Ranking (identity matching) | **+0.41 MR** (concrete win) |
| **PixelGPT V2** (Doc 3) | Design-stage | Proposed direction; not yet built |

**Takeaway:** promising, actively-developed research with one shipped matching win (PixelGPT V1). Do not present the foundational-user-model results as launched wins.

---

## 6. Open questions / what to watch
1. **AR vs bidirectional** for the feature-generation path (§4.2) — currently answered inconsistently across UMS / PixelGPT V2 / LARGE.
2. **Multi-source embedding unification** — continuous projection vs semantic-ID discretization (§4.3); which becomes the standard event token?
3. **Opt-out organic coverage** and **cohort_id↔sid** robustness (§4.4–4.5) — the gating data problems.
4. **Static vs co-trained item embeddings** — will UMS‑3PD stay decoupled, or move toward LARGE-style co-training?
5. **Downstream landing** — will UMS/PixelGPT embeddings clear CVR/ranking admissibility (cardinality/latency) and post a topline win?

---

## 7. Relationship to your (CFR / RankEvolve / CMSL) work

- **UMS lives in `fbcode/mitra/projects/cross_domain_relevance` (CFR)** — the same project area where you applied RankEvolve (CFR Model ROO, Long-Sequence Optimization for CFR). UMS/LARGE is effectively **the CFR user foundation model**, and its user embeddings feed the **CFR UserFM** model.
- **CMSL is a sibling user-modeling approach** (semantically-grouped multi-sequence LLM producing user embeddings for U2U2A retrieval/ranking) — parallel to UMS. Both are "user embeddings for retrieval + ranking," differing in sequence construction (CMSL: MoE-routed coherent sub-sequences over HSTU experts; UMS: single Llama over content-embedding sequence).
- **RankEvolve fit:** UMS‑3PD/LARGE are exactly the kind of intricate, expensive, long-horizon model-evolution targets your harness is built for (embedding-space contracts, leak-prone self-supervised eval, many config axes like `has_item_embedding`/`emb_dim`/AR-vs-bidirectional). The `has_item_embedding` and `emb_dim` switches are textbook evolution axes; the leak-free-eval discipline is directly relevant to trusting UMS's self-supervised NE.

---

## 8. Glossary (grounded) & sources

**Systems**
- **SAGE** — Meta's LLM-based semantic-intelligence platform (formerly **AdsLlama**); dense embeddings for users/content/ads/products/pages in a unified space. **AdsLlama 3.0** = unified multimodal CU model (Qwen3-VL-2B). **EEL** = Entity Embedding Layer (AdsLlama 256-d entity embeddings UMS consumes).
- **UMS (UserModelingWithSemantics)** — SAGE user-modeling program; 3 workstreams: **UMS‑Ranking (=LARGE)**, **UMS‑Retrieval**, **UMS‑3PD**. Implemented `UserModelingWithSemantics(HLLM)` in mitra `cross_domain_relevance`.
- **HLLM** — Hierarchical LLM (ByteDance 2024, arXiv:2409.12740); item-LLM + user-LLM two-tier; the empirical backbone/predecessor of UMS/LARGE.
- **LARGE** — "LLM Ads Recommendation Generation Engine"; the **LLM-native** UMS-Ranking model (16-layer BidirectionalLLAMA, RQ-quantized event tokens, co-trained with ranking head).
- **mitra** — MRS/Content-Understanding ML training framework + CLI (formerly Content Understanding / CUR2P). Projects under `fbcode/mitra/projects/`.
- **CFR** — in this (mitra) context = **`cross_domain_relevance`** (the project hosting UMS). ⚠️ Overloaded: in the Feed/UserFM world "CFR/CUFR" = Cross-User Forced Retrieval, a *different* thing. This analysis uses CFR = cross_domain_relevance.
- **TextRay** — text CU model → 1024-d embeddings from crawled page content → **RQ‑VAE** semantic IDs (**ETLD+1 / URL Entity Data Store**). **RQ‑VAE** = Residual-Quantized VAE (embedding → hierarchical discrete semantic IDs).
- **PixelGPT / PixelBERT** — Signals offsite pixel/event-sequence models (GPT / BERT-MEM variants); produce user/pixel/domain embeddings + semantic IDs for identity matching and ranking.
- **HSTU / RankFM‑2 / RankGraph / CMSL** — adjacent MRS foundation efforts: HSTU = sequence backbone of the RankFM‑2 foundation model/expert paradigm; RankGraph = graph-AI complement; CMSL = sibling user-embedding model.
- **SG (Signal Growth)** — Ads org focused on signal-loss mitigation / privacy-constrained signals; owns offsite 3PD signals (`sg_offsite_signals_embedding`).

**Privacy / data terms**
- **1PD** — data on Meta surfaces; **3PD** — usage-level control / superset of OBA (offsite pixel/CAPI/SDK, offline conversions, partner imports). **OBA** — online behavioral advertising control.
- **Opt-out users** — exercised ATT (Apple ATT event-level opt-out) and/or 3PD/OBA controls; modelable only in aggregate.
- **sid / separable_id** — per-(opt-in)-user privacy key. **cohort_id / cohort_membership_id** — aggregation key for opt-out users. **pixel / CAPI / SDK** — the three offsite collection mechanisms (browser JS tag / server-to-server / in-app SDK). **DPA** — Dynamic Product Ads.
- **PPML** — *unverified*; appears once as "PPML opt-out retrieval," plausibly Privacy-Preserving ML — treat as unconfirmed.

**Key sources.** The three provided documents (authoritative for their own content). Internal grounding: UMS‑3PD paste P2418758896 (T279590774); LARGE paste P2418770725 (T279590778); HLLM task T279699717; "Bridging Products and Ads" (SAGE/UMS two-tier); PixelGPT launch proposal + Deep Matching 2025H1 summary (signalsmatching); ETLD+1 EDS / TextRay / RQ-VAE (Signal Growth wiki + launch post); Signal Loss Terminology wiki; RankFM‑2 MRS Science Book Ch.5; CMSL/RankGraph posts (group 228479108798071). Verified code paths: `fbcode/mitra/projects/cross_domain_relevance/models/ums/ums_models.py`, `.../conf/ums_training_3pd_embedding_llama_1b.yaml`, `fbcode/mitra/projects/rank_llm_user_llm/…`, `fbcode/mitra/projects/sage_adapters/…`.

**Caveats / gaps.** (1) `PPML` unconfirmed. (2) Some Google Docs (SAGE UMS one-pager; LARGE/3PD design docs) were not opened directly; relied on corroborating internal pastes. (3) `CFR` disambiguation as above. (4) Doc 1's line numbers/table-column "meanings" are inferred from code/config (the doc itself flags this); the live Hive table was not queried. (5) Status placeholders (GAS/topline) were empty at time of grounding — impact numbers are offline/qualitative except PixelGPT V1's +0.41 MR.
