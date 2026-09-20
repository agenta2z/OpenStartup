# AURA‑Native (v2): Multimodal Token Makers for Deep‑Integration, Organic‑First User & Ranking Modeling

**Prepared:** 2026‑07‑14 · **Author:** Tony Chen (`zgchen`), MRS Platform · Algorithms
**Status:** Design/strategy proposal — **v2** (merges the v1 AURA‑Native strategy with the CA‑MSL Token‑Maker mechanism; re‑centered on the verified organic‑ranking white space; hybrid tokenization; corrected positioning).
**Companions (kept intact):** `../LLM_native_modeling_proposals/AURA_LLM_native_user_modeling_proposal.md` (v1, strategy) · `../references/meta_internal_practice/some_proposal.md` (CA‑MSL, concrete mechanism) · `../references/meta_internal_practice/three_paradigms{,_deep_dive}.md` (framing).
**Verification note:** every load‑bearing claim below was checked against internal primary sources across four research passes this cycle; unverified/illustrative items are flagged in‑line and in §12. "Existing" vs "Proposed" is marked throughout.

**One‑line thesis:** Build **Multimodal Token Makers** that project rich content, graph, and user signals into **typed, continuous soft tokens** consumed under **deep cross‑attention** by the ranking sequence model — proving the mechanism fast on **ads‑CMSL** (owned assets) and claiming the differentiated white space on **organic feed ranking** (RankFM Expert), inside the AURA platform (three consumption modes, privacy‑native, RankEvolve‑evolved), with **hybrid** discrete‑SID + continuous‑soft‑token representation.

---

## 0. Executive summary

- **The paradigm is settled; the aim is the decision.** LLM‑native ranking converges on a **unified, typed token space** (behavioral + semantic + soft context tokens in one transformer). The load‑bearing empirical claim (LLaTTE, verified): *"semantic features bend the scaling curve — a prerequisite for scaling."* This is the **what**. The **where** is the strategic choice.
- **The verified white space is ORGANIC feed ranking.** Deep unified‑modality is already crowded in **Ads Ranking** (**UNITY / Fully Tokenized Model** — 80% model‑size reduction, +0.13%/+0.02%/+0.06% NE, ~15% QPS; **LLaTTE** two‑stage — +4.3% conversion on FB Feed/Reels) and **Generative Retrieval** (**GRADIENT**, **InstaBrain**). **Organic feed ranking (MRS Algorithms' turf) is under‑invested** — still HSTU‑behavioral‑first with content entering as **shallow‑fused pre‑computed embeddings** (~0.08% NE gains), and RankFM‑2 lists multimodal content understanding as a **future** FM capability. **No internal effort injects continuous content/user soft tokens into an organic ranking transformer under deep cross‑attention** — that is genuine white space.
- **The flagship mechanism (from CA‑MSL): the Multimodal Token Maker.** A lightweight projector maps rich embeddings (SAGE/AdsLlama content, RankGraph, user state) into **N continuous soft tokens in d_model**, injected into the ranking sequence transformer so it **deeply attends over content + behavioral + graph tokens jointly** — not a shallow side‑feature. Two‑stage serving (heavy content pre‑computed/cached; tiny online Token‑Maker MLP) keeps it within the latency budget.
- **Two‑pronged path.** **Prong A (fast validation, owned assets):** ads‑**CMSL** — the team owns both the content source (SAGE/AdsLlama) *and* the sequence consumer (CMSL); the gap is the *connection*. **Prong B (differentiated claim, white space):** **organic RankFM Expert** — the first unified‑multimodal organic ranking model. This is *consistent with* AURA's charter (AURA is "starting with ads," and its mission is explicitly to **bridge organic ↔ ads**; RankFM‑2 is the organic FM), not a departure.
- **Hybrid tokenization (resolves the quantization bottleneck).** Use **continuous soft tokens** for deep discriminative‑ranking fusion (preserves information; SID‑based GR saturates), and **discrete semantic IDs** for generative retrieval / cold‑start / cardinality‑limited features. Not continuous‑only (CA‑MSL over‑rotated), not SID‑only (v1 over‑rotated).
- **The two hard truths we design around:** (i) **alignment is the #1 problem** — raw/frozen content embeddings *hurt* rankers unless aligned to the collaborative/ID space (first‑class stage); (ii) **the inference gap is the gating blocker** (Meta's ST LLM north star) — serving budget is a day‑one constraint. Framing throughout: **LLM + CF, not LLM replacing CF.**
- **Path:** P0 fail‑fast offline (content Token Maker → deep fusion in ads‑CMSL, single model) → P1 flagship (Multimodal Token Makers + deep cross‑attention on ads‑CMSL **and** organic RankFM Expert; hybrid tokenization; alignment stage) → P2 generative user FM + User Token Maker → P3 LLM‑native generative proxy. Gated by MC / the 0.05% NE bar → GAS, and evolved by **RankEvolve**.

---

## 1. Context & the strategic correction (what changed from v1)

### 1.1 Where AURA is (the LLM‑inspired baseline) — Existing
AURA (Hong Li's team's *User Intelligence Engine*) today produces user embeddings from behavioral towers (WHEN/UniArch, `//aps_models/exploration/aura_model`), aggregates them, and injects 16 `AURA_USER_EMBEDDING_*` F3 features into ads ranking (CMF/DPA/IG). Its stated problem is **siloed** user understanding (organic vs ads), and its named 26H1 ambitions include **Generative UM** and **LLM‑native UM**, with three consumption modes: **embeddings, a distilled small model, and an "LLM‑native consumption proxy."** This is **Paradigm‑1‑ish** user modeling consumed as embeddings.

### 1.2 The verified landscape — Existing (checked against primary sources)
- **Ads unified‑modality is crowded/in‑production:** **UNITY / Fully Tokenized Model (FTM)** (Tokenization Co‑Design; O(10K) features → a 3D LLM‑like tensor via RQ‑VAE discrete Semantic IDs; ~80% model‑size reduction, +0.13%/+0.02%/+0.06% NE, ~15% QPS; ~70% of features tokenizable today). **LLaTTE** (two‑stage user model; +4.3% conversion FB Feed/Reels; part of COFFEE). **CU Embeddings Unification / SAGE (formerly AdsLlama, Qwen3‑VL‑2B)** = the semantic‑ID supply chain ("the core that unifies heterogeneous entities into a single semantic‑ID space").
- **Generative retrieval is crowded:** **GRADIENT** (Ads GR; RQ‑VAE; constrained decode; ~10× FLOPs reduction; ~Q2 2026), **InstaBrain** (IG GR; Llama‑3.2‑1B generates SIDs).
- **Organic ranking is behavioral‑first + shallow content fusion:** per‑surface **HSTU** (FB Feed IFR, FB Reels UDD, IG ESR) + **HSTU‑CInt** (adds *contextual* tokens, not unified modality) + **InterestFusion** (pooled InterestFM/content embeddings fused mid‑arch, ~0.08% NE). **RankFM‑2** (FM/Expert paradigm) lists **multimodal content understanding as a future FM capability**, not a deployed deep‑fusion input.
- **The convergence point (three paradigms):** Paradigm 1 (pure behavioral) ceilings; Paradigm 3 (pure text) is 40–50% below prod at 100–10,000× cost; **Paradigm 2 (unified token space — 2a discrete codes + 2b typed soft tokens)** is where Meta and the field converge.

### 1.3 The correction to v1 (why v2 re‑centers)
v1 was **ads‑first** and thus pointed the right paradigm at the **most contested** surface (risking overlap with UNITY/FTM/LLaTTE). v2 re‑centers the **differentiated bet on organic feed ranking** (the verified white space) while keeping **ads‑CMSL as the fast validation vehicle** (owned assets, near‑term value). This is **consistent with AURA's charter**: AURA is "*starting with* ads (iRev)" and exists to **bridge organic ↔ ads** (UME = Unified Meta Embeddings); RankFM‑2 is the organic FM that would consume these tokens. So v2 extends AURA's ads‑first *start* toward its stated *cross‑surface* destination — it does not abandon ads.

*(Charter note, honest: this re‑centering is a strategic choice the team should own. It is defensible on AURA's own mission language, but AURA's current pipeline and GAS goals are ads; v2 therefore keeps a live ads track (Prong A) so near‑term value and owned‑asset leverage are preserved while the organic claim (Prong B) is established.)*

---

## 2. Design principles (v2)

1. **Unified, typed token space (Paradigm 2b + 2a).** Every event → typed tokens: behavioral IDs + **hybrid** semantic (discrete SID *or* continuous soft token) + typed user/context soft tokens, in one d_model space.
2. **Hybrid representation (new in v2).** Continuous soft tokens for **deep discriminative‑ranking fusion** (info‑preserving; SID‑based GR saturates); discrete SIDs for **generative retrieval / cold‑start / cardinality**. Decision table in §3.2.
3. **Deep integration > shallow fusion (the flagship claim).** Full cross‑attention over content + behavioral + graph tokens inside the ranking model — not a pooled side‑feature at ~0.08% NE.
4. **Collaborative‑first; semantics as scaling fuel.** LLM + CF, not replace. Behavioral dominates; semantics unlock scaling + cold‑start + cross‑surface transfer.
5. **Alignment is first‑class.** Align content/semantic embeddings to the collaborative/ID space *before* they enter the ranker (QARM/IDProxy/DAS lesson); keep code‑IDs / soft tokens trainable end‑to‑end.
6. **Match objective to use case.** Discriminative ranking (co‑trained) for the ranking path; dual **causal + masked** for the embedding/generative‑proxy modes; contrastive alignment throughout.
7. **Co‑train with ranking; decouple heterogeneous tasks** (typed Token Makers, MoE/task‑aware tokens, gradient detachment) to avoid the seesaw / negative transfer.
8. **Privacy‑native.** Opt‑out via **cohort_id**; self‑supervised; cross‑funnel per the Event‑Sequence North Star.
9. **Serve within budget (day one).** Two‑stage (cached heavy content + tiny online Token Maker) + Adaptive Ranking Model / M‑FALCON / distillation / RLS.
10. **Build on owned assets; evolve autonomously.** The team owns SAGE/AdsLlama + CMSL + Ads Graph Learning; build the *connection*, reuse RankID/G2Rec/CU‑Unification; evolve tokenizer/arch/objective/fusion with **RankEvolve**.

---

## 3. The core mechanism — Multimodal Token Makers

### 3.1 Typed Token Makers (the flagship component, from CA‑MSL, generalized) — Proposed
A **Token Maker** is a lightweight projector that maps a rich embedding into **N continuous soft tokens in d_model**, so the ranking transformer attends over them jointly with behavioral tokens:

```python
class TokenMaker(nn.Module):
    """Project a rich signal embedding -> N soft tokens in d_model (typed per signal)."""
    def __init__(self, input_dim, d_model, n_tokens):
        self.proj = nn.Sequential(
            nn.Linear(input_dim, d_model * n_tokens),
            nn.SiLU(),                                  # match HSTU activation
            nn.Linear(d_model * n_tokens, d_model * n_tokens),
        ); self.n_tokens, self.d_model = n_tokens, d_model
    def forward(self, emb):                              # emb: [B, input_dim]
        return self.proj(emb).view(-1, self.n_tokens, self.d_model)  # [B, N, d_model]
```
- **Typed makers per signal:** ContentTokenMaker (SAGE/AdsLlama content, or InterestFM for organic), GraphTokenMaker (RankGraph / Ads Graph Learning), UserTokenMaker (§3.3). Typing keeps signals separable and mitigates negative transfer.
- **Token budget (serving‑aware):** ~2–4 soft tokens per entity; e.g. 200 items × 4 = 800 extra tokens, within HSTU's 2K–16K window (Expert uses ~2K).
- **Deep cross‑attention:** the maker's tokens enter the sequence and are attended at every layer against the target — the difference from InterestFusion's pooled mid‑arch fusion.

### 3.2 Hybrid tokenization — Proposed (resolves the continuous‑vs‑discrete tension)

| Use case | Representation | Why |
|---|---|---|
| **Deep discriminative ranking fusion** | **Continuous soft tokens** (Token Maker) | Preserves information; SID‑based GR saturates (quantization bottleneck); best for CTR/CVR reasoning |
| **Generative retrieval / cold‑start / cardinality‑limited features** | **Discrete Semantic IDs** (RQ‑VAE/RQ‑KMeans via RankID; consider RQ‑FSQ) | Compact, generateable, cold‑start‑friendly, downstream‑admissible; RQ‑FSQ matched dense AUC at ~280× storage, +1.522% for near‑zero‑ad‑history users |
| **Lifetime long‑history compression** | **Virtual tokens** (ViSTA‑style) | Condense 12K+ items into a compact user state within cost |

Codebook config near the **~3×256 sweet spot** (or multi‑res `[4096,2048,1024]`); k‑means init (top collapse mitigation); contrastive at the **codebook‑embedding** level (works), not decoder‑output (conflicts); track token **entropy** (r≈0.73 with NE) and **utilization** (r≈0.64).

### 3.3 The User Token Maker (AURA's centerpiece) — Proposed
AURA is a *user* platform, so its differentiated maker is the **User Token Maker**: convert the full user state — behavioral history + **G2Rec soft interest prototypes** (build on, don't reinvent — G2Rec is MRS/Max Fan's soft‑assignment interest tokens) + Biography profile + graph + context — into a compact set of **rich user soft tokens** the ranking transformer deeply attends to. This is richer than discrete SIDs and more efficient than text.

### 3.4 Two‑stage serving (the inference‑gap answer) — Proposed
Heavy content/user understanding runs **offline/nearline and is cached** (the SAGE/AdsLlama Inference Cache is real: ~46% hit over ~137M requests; SAGE serves ~200–1k QPS for ads, ~5k–20k for products). The **only new online component is the tiny Token‑Maker MLP** (<1M params) projecting cached embeddings → soft tokens (~sub‑ms). *Honest trade‑off:* this projects *cached* content (semi‑stale) — deeper than pre‑computed soft tokens, but not the fully **real‑time projection** the deep‑dive flags as the further frontier (fresh, candidate‑dependent). Real‑time projection is a P2+ option, gated by latency.

---

## 4. Where to aim — organic‑first, ads‑validated (the two‑pronged plan)

**Prong A — fast validation on owned assets (ads‑CMSL).** The team owns SAGE/AdsLlama (content source) *and* CMSL (sequence consumer); today they connect only via shallow feature lookup. Prong A builds the deep connection: ContentTokenMaker → deep cross‑attention in CMSL, starting single‑model (AF CMF) offline. Low‑risk, near‑term, leverages assets, and de‑risks the mechanism before the harder claim.

**Prong B — the differentiated white‑space claim (organic RankFM Expert).** Replace/augment the **RankFM Expert's** FM‑embedding input with **typed soft tokens** (content + user + graph) under **deep cross‑attention** — the **first unified‑multimodal organic ranking model** at Meta. This is the verified gap (RankFM‑2 lists multimodal CU as *future*; no internal soft‑token‑into‑organic‑ranking effort exists), and it tests LLaTTE's thesis on organic ranking, not just ads.

**Why consistent with AURA:** bridges organic ↔ ads (AURA's mission), advances UME, and feeds RankFM‑2's organic FM — extending "starting with ads" toward the cross‑surface destination.

---

## 5. Architecture — AURA‑Native (full picture)

- **Inputs:** cross‑surface event sequence (Event‑Sequence North Star: organic 1PD + ads 1PD + offsite 3PD) → per‑event typed tokens: behavioral IDs + **hybrid** semantic (continuous soft token for ranking; discrete SID for retrieval/cold‑start) + typed user/context soft tokens.
- **Backbone:** **RankFM Expert / HSTU‑family** for organic (Prong B), **CMSL** for ads validation (Prong A); long‑context via ViSTA‑style virtual‑token compression; deep cross‑attention over the unified sequence.
- **Objective:** discriminative ranking (co‑trained with the production head) as primary; **dual causal + masked** for the embedding/generative‑proxy modes; contrastive **alignment** (content↔collaborative). Decouple heterogeneous heads (MoE/task‑aware tokens) to avoid the seesaw.
- **Consumption — AURA's three modes:** (1) **embeddings** (EBF; today's F3 path), (2) **distilled student** (ExFM / on‑policy distillation), (3) **LLM‑native generative proxy** (generative retrieval; ST‑LLM real‑time path).
- **Privacy‑native:** `separable_id` (opt‑in) ∪ `cohort_membership_id` (opt‑out); self‑supervised so unattributed offsite events are usable.
- **Serving (inference gap):** two‑stage (§3.4) + Adaptive Ranking Model (Request‑Oriented Optimization / In‑Kernel Broadcast / selective FP8) + M‑FALCON + KV‑cache + distillation + RLS.

---

## 6. Phased roadmap (merged: CA‑MSL's concrete P0/P1 + v1 strategy; organic‑first)

| Phase | Deliverable | Prong / mode | Builds on | Gate |
|---|---|---|---|---|
| **P0 (weeks)** | **Fail‑fast offline:** ContentTokenMaker → deep‑fusion in **ads‑CMSL** (AF CMF), N soft tokens vs baseline, measure NE | A / ranking | SAGE cache (live), CMSL (owned) | **>0.05% NE** offline → proceed |
| **P1 (1–2Q)** | **Flagship:** Multimodal Token Makers (content+graph+user) + **deep cross‑attention**, on **ads‑CMSL portfolio** *and* **organic RankFM Expert**; hybrid tokenization; first‑class alignment stage | A + **B** / ranking + EBF | RankID/RQ‑VAE, G2Rec, ViSTA, Adaptive Ranking Model | Leak‑free NE (esp. cold slices) → MC1/MC3 → GAS |
| **P2 (2–3Q)** | **Generative user FM** (dual causal+masked, cross‑funnel, privacy‑native) + **User Token Maker**; emit embeddings + distilled student | modes 1+2 | HSTU/RankFM‑2, North Star data, ExFM | Offline NE vs LARGE/UMS; student parity |
| **P3** | **LLM‑native generative proxy** / generative retrieval + real‑time serving | mode 3 | GRADIENT/InstaBrain/RankAGI, RLS | Recall + topline GAS; latency SLA (ST‑LLM M2→M3) |

**Cross‑cutting:** RankEvolve‑driven evolution (§9); leak‑free eval; the North Star data‑gap program (organic↔cohort mapping, opt‑out coverage); serving co‑design.

**P0 first step (verbatim‑concrete, from CA‑MSL):** take SAGE/AdsLlama cached embeddings for training items → 2‑layer ContentTokenMaker → 4 soft tokens → concatenate into the CMSL sequence with deep attention → train AF CMF vs baseline → measure NE. **+0.05% NE or better ⇒ invest a quarter.**

---

## 7. Evaluation & launch (Meta practice)
- **Offline NE** (lower better; **date‑aligned** vs V0; **>0.05%** change is real, ±0.02% parity; **NE→EBR ≈ 4:1**). Report **cold/long‑tail slices** explicitly — semantics win there and aggregate metrics can hide or even regress the win. Track tokenizer **entropy/utilization**.
- **Online GAS** via the **MC (Model Change) process**; MC1/MC3/MC12 gates carry per‑metric bars + a **pre‑launch GAS segmentation check**. Reference: **1% GAS ≈ 0.32% iRev**; NE→GAS ratio is **model‑ and signal‑loss‑dependent** (do not hard‑code a single ratio).
- **Discipline:** leak‑free full‑corpus eval is non‑negotiable; trust online A/B over offline NDCG.

---

## 8. Positioning — corrected build‑on / don't‑duplicate map (verified)

| Effort | What it is | AURA‑Native's relation / delta |
|---|---|---|
| **UNITY / FTM (Tokenization Co‑Design, Ads)** | **Discrete** semantic‑ID tokenization of entity IDs; 80% size, +0.21% NE | Complementary: they give items better *discrete IDs*; we add **continuous content/user soft tokens** + deep fusion, **organic‑first**. Coordinate; don't rebuild. |
| **LLaTTE (Ads, two‑stage)** | Multi‑layer target‑aware **behavior** user model; +4.3% conv | Distinct: LLaTTE is behavior‑only user modeling; we inject **content/user soft tokens into ranking**. Borrow the two‑stage serving lesson. |
| **GRADIENT / InstaBrain** | Generative **retrieval** (RQ‑VAE discrete) | Different stage (retrieval vs ranking); we reuse discrete SIDs for our *retrieval* mode only. |
| **RecLLM "Approach 1"** | **Continuous** item‑emb → soft token via projector, on a **generative LLM** | **The novelty foil #1.** Same *technique*, different model class; our delta = injection into the **discriminative ranker** with deep cross‑attention. Must cite. |
| **CMSL (today)** | Consumes LLM **semantic tokens as MoE gating/routing** | **The novelty foil #2.** CMSL already ingests LLM semantic embeddings — *as gating*. Our delta = **first‑class content soft tokens cross‑attended vs. the target at every layer.** Must cite. |
| **G2Rec (MRS/Max Fan)** | **Soft interest prototypes** (soft graph clustering) | **Build on** as the UserTokenMaker's interest‑token source; don't reinvent. |
| **CU Unification / SAGE (AdsLlama 3.0)** | Content‑understanding embeddings → unified semantic‑ID space | Our content‑token **supply chain**; consume via RankID. |
| **POLARIS (Hierarchical, in GEM)** | **Embedding/representation‑sharing** channel (OmniFM → Domain/Vertical FMs via Laser cache; DAS = the soft‑label channel) | *Not* soft‑label transfer (correction vs CA‑MSL). Different mechanism (FM→VM feature hand‑off); doesn't pre‑empt us. |
| **UMS / LARGE, HSTU / RankFM‑2, Meta LLM Rec / PNE, ExFM / M‑FALCON / RLS, RankAGI** | User/ranking FMs, tokenized GR, serving, distillation | Backbones, patterns, and serving we **reuse**, not rebuild. |

**Crisp novelty statement:** *"Deep token‑level cross‑attention fusion of **continuous** content, user, and graph soft tokens into **organic feed ranking** (RankFM Expert) — the first unified‑multimodal organic ranking model — distinct from ads discrete‑SID tokenization (UNITY/FTM), from generative retrieval (GRADIENT/InstaBrain), from LLaTTE's behavior‑only user model, from CMSL's current gating‑only use of LLM tokens, and from RecLLM's generative‑side projector."*

---

## 9. RankEvolve as the evolution engine
AURA‑Native's design space is large and expensive per candidate — tokenizer (RQ‑VAE vs RQ‑KMeans vs RQ‑FSQ, codebook size/depth, alignment recipe), number/type of soft tokens per maker, fusion depth, backbone, objective weights, hybrid discrete/continuous split. Use **RankEvolve** to autonomously **propose→implement→evaluate** these axes under **heterogeneous cross‑agent execution‑accuracy** checking and **leak‑free NE** discipline, cataloguing negative results — the team's differentiated tooling compounding the modeling work (RankEvolve‑CMSL already showed the pattern: Dual‑Stream discovery, +0.15–0.2% NE, "days not months").

---

## 10. Risks & open questions (honest)
1. **Alignment (highest):** raw content soft tokens can hurt without collaborative alignment; make it first‑class; gate on cold slices.
2. **Novelty defense:** must be positioned vs **RecLLM Approach 1** and **CMSL's LLM‑token gating** (delta = deep cross‑attention into the discriminative ranker) or a reviewer will say "already done."
3. **Hybrid complexity:** two representation paths (discrete + continuous) add engineering surface; keep the split principled (§3.2).
4. **Inference gap (gating for P3):** two‑stage handles P0–P1; real‑time projection and generative decoding need serving co‑design; keep embeddings/distillation as the value‑delivering fallback.
5. **Negative transfer / seesaw:** typed makers + MoE/task‑aware decoupling; if a signal drops ranking NE under shared params, isolate it.
6. **"LLM + CF, not replace"** (RecLLM: backbones "get close to prod, not exceed" without CF): position as augmentation.
7. **Organic data coverage (critical path):** the North Star's organic↔cohort mapping gap and opt‑out coverage gate Prong B's data; fund in parallel.
8. **Charter tension:** AURA is ads‑first today; v2 re‑centers on organic — a strategic choice; Prong A preserves ads value while Prong B establishes the claim.
9. **Org duplication:** stay the *user‑FM + organic‑ranking* unifier that **consumes** UNITY/SAGE/G2Rec, not a re‑implementation.

---

## 11. Bottom line
The engine (unified typed token space) is validated; v2 fixes v1's aim. **Build Multimodal Token Makers, integrate them deeply (cross‑attention, not shallow fusion), make the representation hybrid (continuous for ranking, discrete for retrieval), prove it fast on ads‑CMSL (owned assets), and claim the white space on organic RankFM‑Expert ranking** — all inside AURA's platform (three consumption modes, privacy‑native, RankEvolve‑evolved). It is concrete enough to start next week (P0) and strategic enough to be the first unified‑multimodal organic ranking model at Meta.

---

## 12. Appendix — grounding, glossary & caveats

**Corrections applied vs. the source docs (for honesty):**
- **POLARIS** = Hierarchical POLARIS embedding‑sharing (GEM/OmniFM), **not** soft‑label transfer (that's DAS). CA‑MSL's characterization is fixed here.
- **"CMSL v3"** is not a documented program — referred to here as **"proposed next‑gen CMSL."**
- **"~0.08 fusion weight"** (v1's deep‑dive and CA‑MSL) is **unverified as a weight**; it reflects the recurring **~0.08% NE** from shallow content fusion. Used qualitatively only.
- **Continuous‑only** (CA‑MSL) and **SID‑heavy** (v1) both corrected to **hybrid** (§3.2).
- Revenue/GAS projections are **illustrative**; NE→GAS is model‑dependent.

**Verified numbers used:** UNITY/FTM 80% size / +0.13%/+0.02%/+0.06% NE / ~15% QPS; LLaTTE +4.3% conv (FB Feed/Reels); SAGE/AdsLlama cache ~46% hit / ~137M req, ~200–1k QPS ads / ~5k–20k products; AdsLlama features ~0.05% GAS (H1‑2025); CMSL ~0.1145% eGAS (5 ads heads) + IFR MC9 ~0.435% NE; RQ‑FSQ ~280× storage / +1.522% low‑ad‑history; NE>0.05% = real, NE→EBR ≈ 4:1, 1% GAS ≈ 0.32% iRev; SID sweet spot ~3×256; token entropy r≈0.73 / utilization r≈0.64.

**Glossary:** AURA (User Intelligence Engine, Hong Li's MRS Platform‑Algorithms; 3 consumption modes). Token Maker (projector: rich emb → N soft tokens in d_model). CMSL (Constructive Multi‑Sequence Learning, Junjie; ads+organic). RankFM‑2 / RankFM Expert (organic FM/Expert paradigm, HSTU backbone). UNITY/FTM (Ads discrete‑SID Fully Tokenized Model). LLaTTE (Ads two‑stage user model). GRADIENT/InstaBrain (generative retrieval). G2Rec (soft interest prototypes, MRS/Max Fan). SAGE/AdsLlama (content‑understanding LLM → embeddings/SIDs). POLARIS/DAS (GEM embedding‑sharing / soft‑label channels). RecLLM (generative LLM recommender; "Approach 1" continuous‑emb soft token). RankID/RQ‑VAE/RQ‑KMeans/RQ‑FSQ (semantic‑ID tokenizers). Adaptive Ranking Model / M‑FALCON / RLS / ExFM (serving/distillation). ST LLM (SilverTorch real‑time LLM‑rec north star; the "inference gap"). NE/GAS/MC (offline metric / online ad score / launch process). sid vs cohort_id (opt‑in vs opt‑out keys). EBF/F3 (embedding features / feature store). RankEvolve (the team's auto‑research harness).

**Grounding sources:** the `work_analysis/` analyses (UMS/Event‑Sequence/PixelGPT; AURA context; Jin/Junjie H1) + `references/` (three_paradigms{,_deep_dive}; CA‑MSL; internal‑practice addenda; external surveys) + four internal knowledge‑search verification passes this cycle (primary sources: Tokenization Co‑Design/UNITY, LLaTTE, GRADIENT, G2Rec/arXiv 2606.20554, CU‑Unification/SAGE, POLARIS/GEM/OmniFM, RecLLM, CMSL wiki/post, AdsLlama Inference Cache, RankFM‑2, Ads Score Metrics/GAS‑NE, ST LLM). External anchors: HSTU (2402.17152), TIGER (2305.05065), PLUM (2510.07784), OneRec (2506.13695), Token Factory (2606.19635), LLaTTE (2601.20083), semantic‑ID scaling (2509.25522).

**Caveats:** this is a *proposal*, not a sanctioned roadmap; "Proposed" items are forward‑looking. Some internal specifics remain single‑source/provisional (esp. LARGE internals, exact NE→GAS ratios, and any pre‑launch numbers). Absence of an internal "organic soft‑token ranking" effort is established to the limits of retrieval (a negative can't be proven absolutely). Verify load‑bearing numbers against owning‑team docs before external use.
