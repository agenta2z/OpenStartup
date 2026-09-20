# Gap Analysis: Where to Focus for Multimodal Ranking

> 🔍 **Refined Gap Analysis: Multimodal Ranking Opportunities for MRS Algorithm Platform**
> Updated with all corrections from critical investigation. References all prior research findings.

## Table of Contents

- [Part 1: What Meta IS Already Doing (Corrected & Complete)](#part-1-what-meta-is-already-doing-corrected--complete)
  - [⚠️ Important Context: "Soft Token Injection" Is NOT a Gap](#️-important-context-soft-token-injection-is-not-a-gap)
  - [What This Means](#what-this-means)
- [Part 2: Where the REAL Differentiated Opportunities Are](#part-2-where-the-real-differentiated-opportunities-are)
  - [🎯 Opportunity A: End-to-End Optimization of Content Embeddings FOR Ranking](#-opportunity-a-end-to-end-optimization-of-content-embeddings-for-ranking)
  - [🎯 Opportunity B: Cross-Domain Signal Transfer via CMSL Tokens](#-opportunity-b-cross-domain-signal-transfer-via-cmsl-tokens)
  - [🎯 Opportunity C: Ranking-Aware Content Tokenizer (Joint Objective)](#-opportunity-c-ranking-aware-content-tokenizer-joint-objective)
  - [🎯 Opportunity D: Multi-Resolution Adaptive Token Budget](#-opportunity-d-multi-resolution-adaptive-token-budget)
- [Part 3: Assessment — Which Opportunity Is Best for Your Team?](#part-3-assessment--which-opportunity-is-best-for-your-team)
  - [My Final Recommendation](#my-final-recommendation)
- [Part 4: The Corrected Landscape Map](#part-4-the-corrected-landscape-map)
- [Key Internal Resources](#key-internal-resources)

---

## Part 1: What Meta IS Already Doing (Corrected & Complete)

### ⚠️ Important Context: "Soft Token Injection" Is NOT a Gap

After critical re-examination, I found that the mechanism of injecting non-behavioral signals as tokens into a transformer is being actively worked on by multiple Meta teams. The concept is the same as Google's Token Factory — Meta just uses different names.

| Meta System | Mechanism | Team | How It Works | Status | Key Result |
|---|---|---|---|---|---|
| **Multitoken NRO** | Soft token injection into HSTU | FM Co-Design (Shilin Ding org) | Dense/sparse features → N=8 learned tokens inserted into HSTU FM sequence | Active | NE gains; enables Expert transfer |
| **HSTU-CInt** | Contextual token prepending | MRS Core Modeling | User-level features + cross-surface embeddings prepended as tokens; metadata interleaved at alternating positions | ✅ Production | Target-aware multi-context ranking |
| **RankID v3 Soft Token** | QFormer compression | MRS Knowledge/RankID | Multimodal perception (image/video) → QFormer → N soft tokens (N=1,8,16,32,64,128) | Research (April 2026) | Multi-resolution content compression |
| **Tokenization Co-Design** | Unified Modality | Ads Ranking (Yang Yang et al.) | ALL entity IDs → semantic tokens from unified vocabulary → 3D LLM-like tensor | ✅ Production | 80% model size reduction, +0.14% NE with scaling |
| **LLaTTE** | Two-stage semantic features | Ads Ranking AI | Semantic features computed offline → integrated in user model transformer | ✅ Production | -0.13% NE; "semantic features prerequisite for scaling" |
| **EMUIC** | Embedding features in HSTU | MRS Content Understanding | InterestFM labels → ID-matched embeddings (dim=128) as additional sparse features | ✅ Production | Auxiliary content enrichment |
| **Interest Encoder** | Gating fusion | MRS Knowledge | Semantic embeddings fused with HSTU via target-aware gating (~0.08 weight) | ✅ Production | Incremental semantic lift |
| **G2Rec** | Soft graph clustering | UIUC + MRS (Max Fan org) | Item co-engagement graph → soft interest prototypes (items have partial membership in multiple clusters) | ✅ Deployed | Scalable user interest tokenization |

### What This Means

The core idea of "encode signals as tokens for a transformer" is well-understood and being executed at Meta. You cannot differentiate by proposing "let's do soft token injection" — that's already being built.

---

## Part 2: Where the REAL Differentiated Opportunities Are

The opportunities lie **NOT** in the injection mechanism but in:

1. **WHAT** goes into the tokens (upstream quality)
2. **HOW** tokens are optimized (end-to-end with ranking)
3. **WHERE** it's applied (organic vs ads; ranking vs retrieval)
4. **Cross-domain bridging** (your team's unique mission)

### 🎯 Opportunity A: End-to-End Optimization of Content Embeddings FOR Ranking

**The Problem:**

- AdsLlama (your team owns this) produces embeddings optimized for content understanding (classification accuracy, embedding similarity)
- These embeddings are "thrown over the wall" to ranking models (no gradient flows back)
- Ranking models treat them as frozen features — they cannot tell AdsLlama "I need embeddings that distinguish between items THIS user would click vs. not click"
- Result: there's a disconnect between what makes a good content embedding vs. what makes a good ranking feature

**Why This Matters:**

- The CU Embeddings study internally found: different embedding approaches yield 0.07% vs 0.16% AUC — a 2x difference from the SAME information, just represented differently
- If you improve the upstream embedding quality specifically for ranking, EVERY downstream model benefits (portfolio effect)
- LLaTTE proved semantic features are prerequisite for scaling — but the quality of WHICH semantic features matters enormously

**What Exists Today (Why This Is Still a Gap):**

- Tokenization Co-Design tokenizes embeddings BUT doesn't optimize the embedding model itself
- FM Co-Design inserts features as tokens BUT doesn't control the upstream feature quality
- RankID produces semantic IDs BUT trained for reconstruction, not ranking
- Nobody is closing the loop: ranking loss → gradient → content encoder optimization

**Concrete Approach:**

```text
Current: AdsLlama → [frozen embedding] → Feature Store → Ranking Model → Loss
                    ↑ NO GRADIENT FLOWS BACK

Proposed: AdsLlama → [embedding] → Token Maker → Ranking Model → Loss
                    ↑ GRADIENT FLOWS BACK (with stop-grad schedule / EMA update)
```

Key technical choices:

- Don't fine-tune all of AdsLlama (too expensive, ruins general understanding)
- Add a lightweight adapter (LoRA or bottleneck) between AdsLlama and the Token Maker
- Train the adapter + Token Maker jointly with ranking loss
- EMA update (slow moving average) to keep embeddings stable for other consumers
- Distillation variant: Use ranking-informed embeddings as teacher to improve the cached embeddings (offline, doesn't affect serving)

**Who Benefits:** Every model consuming AdsLlama embeddings (AF CMF, AI CMF, DPA, AF IG CTR, PreMatch, ...) — portfolio impact

**Differentiation:**

- Tokenization Co-Design (Yang Yang) → optimizes the vocabulary/tokenizer, NOT the upstream encoder
- FM Co-Design (Multitoken NRO) → optimizes how features enter HSTU, NOT the feature quality itself
- Your work → optimizes the SOURCE EMBEDDINGS specifically for ranking

### 🎯 Opportunity B: Cross-Domain Signal Transfer via CMSL Tokens

**The Problem:**

- Users engage across surfaces: FB Feed, IG Reels, Threads, Ads
- Each surface's ranking model has limited visibility into other-surface behavior
- RankFM partially addresses this (cross-surface FM training) BUT:
  - FM output is a SINGLE condensed embedding (2 × dim 512) — massive information loss
  - Expert models see only their own surface's recent UIH (2K items)
  - Rich cross-domain patterns are compressed to one vector

**Why This Matters:**

- RankFM's cross-surface learning was the "highest-impact single ranking launch in 3 years" (+0.163% Cap30)
- This PROVES cross-domain signals have enormous value
- But the current mechanism (single FM embedding) is a bottleneck — it compresses all cross-domain knowledge into 1024 floats
- CMSL (your team's model) specifically exists to construct "multiple semantically coherent sequences from cross-domain engagement data"

**What Exists Today (Why This Is Still a Gap):**

- RankFM → single FM embedding per user (information bottleneck)
- CMSL → multi-sequence learning BUT output still consumed as features, not as rich tokens
- G2Rec → interest prototypes from graph BUT within a single domain
- Nobody is producing MULTI-TOKEN cross-domain representations that preserve the STRUCTURE of cross-domain interests

**Concrete Approach:**

```text
User behavior on Surface A (e.g., IG Reels)
    → CMSL constructs K semantically coherent sub-sequences
    → Each sub-sequence → Token Maker → M soft tokens
    → Total: K×M cross-domain tokens

These tokens are INJECTED into Surface B's ranking model (e.g., FB Feed Expert)
    → Transformer can attend to specific cross-domain interest facets
    → Much richer than single FM embedding
```

Example: A user who watches cooking on IG Reels → instead of one embedding, produce:

- Token 1: "cooking interest" (coarse)
- Token 2: "specifically Italian cuisine" (fine)
- Token 3: "prefers short-form tutorials" (format preference)
- Token 4: "active in evenings" (temporal pattern)

FB Feed's Expert model can now attend to SPECIFIC facets of the IG behavior — not just "IG says this user is interested in cooking."

**Who Benefits:** All surface Expert models (FB Feed, IG Feed, Reels, Threads) — each gets richer cross-domain signal

**Differentiation:**

- RankFM (Core Modeling) → single condensed FM output
- FM Co-Design → inserts features into FM, not cross-domain tokens into Experts
- CMSL currently → feeds downstream as features
- Your work → CMSL outputs as RICH MULTI-TOKEN cross-domain context for Expert models

### 🎯 Opportunity C: Ranking-Aware Content Tokenizer (Joint Objective)

**The Problem:**

- Current tokenizers (RQ-VAE for SIDs) are trained for reconstruction — reconstruct the original embedding
- But reconstruction ≠ ranking utility — two items that look similar in embedding space may have VERY different engagement patterns
- The "engagement alignment" problem: content-only SIDs don't reflect whether users actually ENGAGE differently with similar-looking content

From the Semantic ID Survey internally:

> "Engagement Alignment: Indirect only. The tokenizer itself is content-only; engagement patterns are learned by the generator through user interaction sequences. This creates a gap: items that are semantically similar in content may not be interchangeable from an engagement perspective."

**Why This Matters:**

- GRADIENT found that "adding discriminative TTSN ad-tower embeddings to tokenization SIGNIFICANTLY improves performance" — because ad-tower embeds contain engagement signal
- This proves: tokenization quality directly bounds downstream model quality
- If tokens don't distinguish between high-engaging and low-engaging content within the same category, the model can't learn the difference

**What Exists Today (Why This Is Still a Gap):**

- RankID/SID → reconstruction-based (content-only)
- GRADIENT tokenizer → added TTSN embeddings (engagement-aware for ADS, not organic)
- Tokenization Co-Design → entity tokenization (vocabulary design, not training objective)
- Nobody has built a tokenizer jointly trained with organic ranking loss that produces tokens optimized for ranking discrimination

**Concrete Approach:**

```text
Standard RQ-VAE training:
    Loss = Reconstruction(original_embedding, decoded_embedding) + Commitment

Proposed Joint Training:
    Loss = α × Reconstruction 
         + β × Ranking_Discrimination (contrastive: engaged vs not-engaged items should have different codes)
         + γ × Commitment
```

The ranking discrimination loss ensures that items a user engaged with get DIFFERENT codes from items they skipped — even if the content looks similar. This makes downstream sequence prediction more informative.

**Who Benefits:** All generative retrieval systems (InstaBrain, GRADIENT) + all models consuming SIDs

**Differentiation:**

- RankID team → builds the tokenization PLATFORM (infrastructure)
- GRADIENT team → applies tokenization for ads retrieval
- Your work → defines the training OBJECTIVE that makes tokens maximally useful for ranking

### 🎯 Opportunity D: Multi-Resolution Adaptive Token Budget

**The Problem:**

- Current systems use FIXED token budgets per item (e.g., 3 SID levels, or N=8 soft tokens)
- But not all items need the same resolution:
  - Popular items with rich engagement history → behavioral signal is sufficient, need fewer content tokens
  - New/cold-start items → need MORE content tokens to compensate for missing behavioral
  - Complex items (multi-product ads, long videos) → need more tokens than simple items
- Fixed budgets waste compute on easy items and under-represent hard ones

**Evidence This Matters:**

- RASTP (2025) showed: "Not all tokens in a semantic ID sequence contribute equally; L3+ codes may be redundant for popular items"
- Token Factory compresses 1536→480 tokens (3.2x) with on-par quality — proving adaptive compression works
- Meta's serving is latency-constrained → adaptive budgets let you spend compute WHERE it helps most

**What Exists Today (Why This Is Still a Gap):**

- RASTP → post-hoc pruning of SID tokens (academic, not production)
- Token Factory → fixed compression ratio per signal type
- HSTU → fixed sequence length per user
- Nobody has implemented ADAPTIVE per-item token budgets based on information need

**Concrete Approach:**

```text
For each item in the candidate set:
    engagement_history_richness = count(historical_interactions)
    content_complexity = len(AdsLlama_embedding) / quantization_residual
    
    if engagement_history_richness > threshold:
        token_budget = 2  (behavioral signal is sufficient)
    elif content_complexity > threshold:
        token_budget = 8  (need rich content representation)
    else:
        token_budget = 4  (default)

Token Maker adapts: MLP output dim = token_budget × d_model
```

Or more elegantly: a learned "budget router" that predicts optimal N per item.

**Who Benefits:** Serving efficiency (same quality with fewer total tokens) + cold-start quality (more tokens where they help)

**Differentiation:** Novel research direction — adaptive token budgets for recommendation. Publishable. Practical serving improvement.

---

## Part 3: Assessment — Which Opportunity Is Best for Your Team?

| Opportunity | Alignment with Team Mission | Overlap Risk | Expected Impact | Effort | Publishability |
|---|---|---|---|---|---|
| **A: End-to-End Embedding Optimization** | ✅✅✅ (own AdsLlama + ranking models) | Low (nobody does this) | High (portfolio effect across all models) | Medium (adapter + joint training) | ✅ (novel objective) |
| **B: Cross-Domain CMSL Tokens** | ✅✅✅ (own CMSL, mission IS bridging) | Low (unique to CMSL team) | High (RankFM proved cross-domain value) | Medium-High (multi-surface coordination) | ✅ (novel architecture) |
| **C: Ranking-Aware Tokenizer** | ✅✅ (own AdsLlama, partner with RankID) | Medium (RankID team adjacent) | Medium-High (bounds all SID-consuming models) | Medium (training objective change) | ✅✅ (directly publishable) |
| **D: Adaptive Token Budget** | ✅ (general improvement) | Low (novel) | Medium (efficiency + cold-start) | Low-Medium (routing logic) | ✅✅ (novel, publishable) |

### My Final Recommendation

**Start with A (End-to-End Embedding Optimization)** because:

- You uniquely own BOTH sides (AdsLlama upstream + ranking model downstream)
- It has the broadest portfolio impact (every model consuming your embeddings improves)
- It's the lowest overlap risk (FM Co-Design inserts features; you improve feature quality)
- It's technically tractable (adapter + joint training is well-understood)
- It validates a principle that can then extend to B, C, D

**Then layer B (Cross-Domain CMSL Tokens)** because:

- It's your team's STATED MISSION (bridging organic ↔ ads)
- It compounds on A (better embeddings → better cross-domain tokens)
- The RankFM cross-surface result (+0.163%) proves massive demand for this signal

---

## Part 4: The Corrected Landscape Map

```text
                         ORGANIC FEED              ADS RANKING
                         ─────────────            ────────────
Behavioral Only:        ✅ HSTU (production)      ✅ HSTU (production)

+ Pre-computed features: ✅ HSTU-CInt + EMUIC      ✅ LLaTTE two-stage
                         (0.08 fusion weight)      (semantic prerequisite)

+ Soft token injection:  ✅ Multitoken NRO (FM)    ✅ Tokenization Co-Design
                         (FM Co-Design team)       (Yang Yang team)

+ Discrete codes:        🟡 InstaBrain (IG only)   ✅ GRADIENT, RankID
                         (Retrieval, not ranking)  (Retrieval + Ranking)

+ End-to-end embedding   ❌ GAP ← OPP A           🟡 CU Embeddings study
  optimization:          (ranking-aware AdsLlama)  (exploration only)

+ Cross-domain tokens:   ❌ GAP ← OPP B           🟡 POLARIS (soft labels only)
                         (multi-faceted CMSL)      (single-vector transfer)

+ Ranking-aware tokens:  ❌ GAP ← OPP C           🟡 GRADIENT (TTSN-augmented)
                         (organic engagement)      (ads-specific)

+ Full text LLM:         ⚠️ ARS (prototype)        ⚠️ GRADIENT Point E (32B)
```

Your opportunities (A, B, C) fill genuine gaps in organic ranking that are NOT covered by existing ads-focused or mechanism-focused teams.

---

## Key Internal Resources

| Resource | URL | Relevance |
|---|---|---|
| MRS Algorithm Platform Onboarding | https://www.internalfb.com/wiki/MRS_Algorithm_Platform/Onboarding/ | Your team's wiki |
| MRS Science Book (all chapters) | https://www.internalfb.com/wiki/Tofigh/MRS_Science_Book/ | Comprehensive system reference |
| Tokenization Co-Design H2 Retro | https://fb.workplace.com/groups/8000374759979655/permalink/10067075926642851/ | Understand adjacent work |
| FM Insert Dense/Sparse Multitoken NRO | https://fb.workplace.com/groups/1068690101944312/permalink/1222571796556141/ | Understand mechanism team |
| RankID v3 Soft Token Progress | https://www.internalfb.com/wiki/Mrs_research/gcompressor/report/Tokenization_Progress_04_2026/ | Adjacent research |
| G2Rec Soft Interest Profiling | https://fb.workplace.com/groups/1677681746043842/permalink/2186721938473151/ | Adjacent work in your org |
| CU Embeddings for Ads Study | https://fb.workplace.com/groups/1033540429995021/permalink/9154718904543759/ | Evidence for Opportunity A |
| LLaTTE Paper | https://arxiv.org/abs/2601.20083 | "Semantic features bend scaling curve" |
| Token Factory Paper | https://arxiv.org/abs/2606.19635 | Google's approach (for comparison) |
| Semantic ID Survey | https://www.internalfb.com/wiki/ECommerce_NORAM/Teams/eCommerce_Representation_Relevance/Product_Representation/Team_Docs/Comprehensive_State-of-the-Art_Survey%3A_Semantic_ID_Entity_Tokenization_for_Recommendation_Systems/ | 30+ approaches compared |
| GRADIENT GR Wiki | https://www.internalfb.com/wiki/AdsInfra/AI_HW_Codesign/models/innovations/generative_retrieval/ | Ads generative retrieval architecture |
| InstaBrain H1 2026 | https://fb.workplace.com/groups/233247545227463/permalink/1462854728933399/ | IG generative retrieval with LLM |
