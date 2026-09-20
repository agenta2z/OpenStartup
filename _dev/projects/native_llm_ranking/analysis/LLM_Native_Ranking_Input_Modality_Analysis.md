# LLM Native Ranking: Input Modality Analysis

*v2 — Enhanced Comparison & Deep Dive*

> 📊 **Enhanced Comparison: LLM Native Ranking Approaches — Deep Dive**
> Comprehensive pros/cons and existing works per paradigm.

## Contents

- [Paradigm (1): Pure Sequence Modeling with LLM Architecture](#paradigm-1-pure-sequence-modeling-with-llm-architecture)
- [Paradigm (2a): Discrete Semantic Codes in LLM Vocabulary](#paradigm-2a-discrete-semantic-codes-in-llm-vocabulary)
- [Paradigm (2b): Soft Token Injection from Diverse Signals](#paradigm-2b-soft-token-injection-from-diverse-signals)
- [Paradigm (2c): Decoupled Multimodal Pipeline](#paradigm-2c-decoupled-multimodal-pipeline)
- [Paradigm (3): Pure Text / Natural Language LLM](#paradigm-3-pure-text--natural-language-llm)
- [📊 Revised Comparison Matrix (Corrected with Meta Internal Data)](#-revised-comparison-matrix-corrected-with-meta-internal-data)
- [Key Insight: These Approaches Are NOT Mutually Exclusive](#key-insight-these-approaches-are-not-mutually-exclusive)

---

## Paradigm (1): Pure Sequence Modeling with LLM Architecture

**Core idea:** Borrow the transformer / autoregressive architecture from LLMs but operate over **behavioral tokens** (item IDs + action types), **not** text.

### Architecture

```text
User History: [item₁, click₁, item₂, skip₂, item₃, watch_30s₃, ...]
    → Sparse embedding lookup (billions of entries)
    → d_model vectors per position
    → Causal/cross-attention transformer
    → Prediction (CTR, watch time, etc.)
```

### ✅ Pros

| Advantage | Evidence |
|---|---|
| Massive production scale proven | Meta HSTU: 1.5T params, billions of users daily |
| Best latency / throughput | HSTU: 5.3×–15.2× faster than FlashAttention2; Expert at 9,205 QPS |
| Power-law scaling demonstrated | HSTU scales like GPT-3 / LLaMA-2 across 3 orders of magnitude of compute |
| Captures temporal dynamics | Sequential attention naturally weights recency, detects interest drift |
| Collaborative signals preserved | Pure behavioral = strongest collaborative-filtering signal |
| Simple serving | No external model dependencies at inference time |
| Mature infrastructure | Years of optimization (CUDA kernels, sharding, caching) |

### ❌ Cons

| Limitation | Evidence |
|---|---|
| Scaling ceiling without semantic features | LLaTTE: "Semantic features are a PREREQUISITE for scaling" — without them, deeper models don't improve |
| Cold-start blind | New items with no engagement history → zero signal |
| Shallow content understanding | Correlates behavioral patterns but doesn't "know" what content IS |
| Vocabulary non-stationarity | Billions of items changing constantly (unlike fixed NLP vocab) → embedding tables never fully converge |
| No world knowledge | Cannot reason about new concepts, trends, or relationships not in training data |
| Cross-domain transfer limited | Item IDs are surface-specific; cannot generalize across platforms without shared IDs |

### Meta Internal Production Systems

| System | Team | Scale | Key Result |
|---|---|---|---|
| HSTU | MRS Core Modeling | 1.5T params, all surfaces | +12.4% engagement, +8% watch time (FB Video) |
| RankFM (FM/Expert) | MRS Core / FM Co-Design | 0.95B dense + 2,074B sparse | +0.163% Cap30 sessions ("highest-impact launch in 3 years") |
| CMSL | MRS Algorithm Platform (Hong Li) | Cross-domain sequences | +0.11–0.43% NE across Reels, Feed, IFR |
| COFFEE / CoFormer | Ads Ranking | Multi-layer sequence | +1.05% GAS since 24H2 |
| LLaTTE (behavioral part) | Ads Ranking AI | 4-layer, 1500× scale | −0.13% NE (largest UM gains) |

### Industry External Systems

| System | Company | Scale | Key Result |
|---|---|---|---|
| OneRec (behavioral backbone) | Kuaishou | Production | +1.6% watch time |
| LONGER | TikTok | Production | Deployed at scale |
| LiGR | LinkedIn | Production | Adopted HSTU |
| MTGR | Meituan | Production | Adopted HSTU |
| Yandex Music Transformer | Yandex | 1B params | +2.26% listening time, +6.37% likes |
| EST | Alibaba / Taobao | Production | +3.27% RPM, +1.22% CTR |
| FAT (Field-Aware Transformer) | Alibaba | Production | +2.33% CTR, +0.66% RPM |

---

## Paradigm (2a): Discrete Semantic Codes in LLM Vocabulary

**Core idea:** Convert items / content into **discrete codes** (via RQ-VAE or clustering), add these as new tokens to an LLM's vocabulary, and use the LLM to **autoregressively generate** recommendations.

### Architecture

```text
Item → Content Embedding (from AdsLlama/InterestFM/UME)
    → RQ-VAE Quantizer (multi-level codebook)
    → Discrete codes: [sid_level1=42, sid_level2=17, sid_level3=891]
    → Added as new tokens to LLM vocabulary (e.g., Llama 3.2 1B)

Inference: User SID history → LLM generates next SID sequences → Map SIDs back to items
```

### ✅ Pros

| Advantage | Evidence |
|---|---|
| Leverages pretrained LLM knowledge | CPT from Llama 3.2 → +12% L1@1 vs training from scratch (InstaBrain) |
| Enables generative retrieval | Can GENERATE candidates instead of scoring all items → 10× FLOPs reduction (GRADIENT) |
| Semantic similarity preserved | Similar items share code prefixes → built-in generalization |
| Cold-start handled | New items get SIDs from content → immediate representation without engagement |
| Scalable vocabulary | O(10K) codebook entries vs. O(billions) item IDs |
| World knowledge for reasoning | LLM base retains general knowledge useful for CTV / topic queries (InstaBrain) |
| Embedding table compression | Shared codebook → 80% model size reduction (Tokenization Co-Design) |

### ❌ Cons

| Limitation | Evidence |
|---|---|
| Lossy quantization | RQ-VAE compresses continuous embeddings to discrete codes → information loss |
| Codebook collapse | RQ-VAE training instability; codes can become degenerate |
| Two-stage training | Tokenizer trained separately from ranking model (not end-to-end) |
| "Curse of paced bid" (ads) | First token hardest to learn — ads selected by bid, not user preference (GRADIENT finding) |
| Natural language doesn't help | "Adding natural language did NOT help" for Feed GenRet (InstaBrain H1 2026) |
| Autoregressive latency | Beam-search generation slower than single-pass scoring |
| Popularity bias amplification | Generative models over-generate frequent codes (ZJU 2026 paper) |
| Engagement alignment gap | Content-only SIDs don't reflect engagement patterns (Semantic ID Survey) |

### Meta Internal Production Systems

| System | Team | Scale | Key Result |
|---|---|---|---|
| InstaBrain Feed GenRet | IG Relevance + ASA + MRS | Llama 3.2 1B, 1.1T CPT tokens | Engagement at/above feed average at 2% source rate |
| InstaBrain CTV | Same | Llama 3.2 1B | First generative retrieval source on Instagram TV |
| GRADIENT Retrieval | Ads Ranking Tiger Team | 30–45GB model, 300+ beams | +1.2% offline recall, ~+0.1% iRev online |
| GRADIENT Tokenizer | Ads Tokenization | RQ-VAE on AdsLlama embeddings | +0.08% iRev, $65M capacity savings |
| IG SID v1/v2 (RankID) | MRS Knowledge / RankID | RQ-kMeans, 3-level codes | +0.015% cap15, +0.19% IG time spent |
| Tokenization Co-Design | Ads Ranking (Yang Yang) | Unified vocabulary, 0.14% NE | 80% model size reduction, 15% QPS gain |
| Project PROMPT | Marketplace | LLaMA + SIDs | Marketplace Feed generative retrieval |

### Industry External Systems

| System | Company | Scale | Key Result |
|---|---|---|---|
| TIGER | Google (NeurIPS 2023) | Production YouTube | First generative retrieval with semantic IDs |
| OneRec | Kuaishou | Production | +1.6% watch time (unified retrieve+rank with DPO) |
| NoteLLM | Xiaohongshu (WWW 2024) | Production, 100M+ users | I2I recommendation via LLM-compressed embeddings |
| STORE | Academic | Research | Single LLM for both tokenization and recommendation |
| TokenRec | Academic | Research | Learning to tokenize IDs for LLM-based generative rec |
| Spotify GLIDE | Spotify | Production, 600M+ users | Semantic IDs for generative search + recommendation |
| GPR | Tencent / WeChat | Production | +43.9% HR@1 (end-to-end generative ads) |
| OneRanker | Tencent | Production | +1.34% GMV (unified generation + ranking) |

---

## Paradigm (2b): Soft Token Injection from Diverse Signals

**Core idea:** Convert **any** heterogeneous feature (behavioral, visual, contextual, graph) into continuous **"soft tokens"** (d_model vectors) via learned projections (**Token Makers**), then feed ALL tokens into a unified transformer.

### Architecture

```text
Signal Type 1 (e.g., watch history)  → Token Maker₁ (MLP) → N₁ soft tokens ─┐
Signal Type 2 (e.g., content embed)  → Token Maker₂ (MLP) → N₂ soft tokens ─┤
Signal Type 3 (e.g., user features)  → Token Maker₃ (MLP) → N₃ soft tokens ─┤→ Unified Transformer
Signal Type 4 (e.g., graph signals)  → Token Maker₄ (MLP) → N₄ soft tokens ─┤   → Prediction
Signal Type 5 (e.g., candidate)      → Token Maker₅ (MLP) → N₅ soft tokens ─┘
```

### ✅ Pros

| Advantage | Evidence |
|---|---|
| Preserves continuous information | No quantization loss (unlike discrete codes) — full embedding fidelity |
| End-to-end optimizable | Gradients flow from ranking loss back through Token Makers to feature encoders |
| Modality-agnostic | Same framework for behavioral, visual, text, graph, contextual — just different Token Makers |
| Scalable (proven) | Token Factory on YouTube: 110M–210M MoE Gemini variants in production |
| Efficient serving | Token Makers are tiny MLPs (<1M params); compute is negligible vs. transformer |
| Compression built-in | Can control N (tokens per signal) for latency / quality tradeoff |
| Schema-preserving | Each Token Maker is typed → model "knows" what each token type means |
| Unlocks scaling | LLaTTE proved: semantic features are prerequisite for scaling; this is the mechanism |

### ❌ Cons

| Limitation | Evidence |
|---|---|
| New parameters learn from scratch | Token Makers initialize randomly; require training data to converge |
| Token budget management | More signals = longer sequence = more compute; must compress |
| Not generative | Produces scores / predictions, NOT item generation (can't replace retrieval) |
| Infrastructure complexity | Requires multiple online feature sources connected to Token Makers |
| Less mature than (1) | Fewer production deployments; less infrastructure optimization |
| Cross-modal interference | Naive mixing of many modalities can hurt (need proper token-type design) |
| Dependency on upstream models | Quality of soft tokens depends on upstream encoders (AdsLlama, InterestFM, etc.) |

### Meta Internal Production Systems

| System | Team | Scale | Key Result |
|---|---|---|---|
| Multitoken NRO (insert dense/sparse into HSTU) | FM Co-Design (Shilin Ding org) | N=8 tokens | NE gains on FM; enables Expert transfer |
| HSTU-CInt (contextual tokens prepended) | MRS Core Modeling | Production | Contextual + metadata interleaving; target-aware multi-context |
| LLaTTE (semantic features in user model) | Ads Ranking AI | 1500× scale | −0.13% NE; "semantic features bend scaling curve" |
| RankID v3 Soft Tokens | MRS Knowledge / RankID | QFormer, N=1–128 | Active research (April 2026); multi-resolution compression |
| Tokenization Co-Design (unified 3D tensor) | Ads Ranking (Yang Yang) | All features → tokens | +0.13% NE (Unified Semantic Sequence), 80% model compression |
| EMUIC (embedding-based multimodal in HSTU) | MRS Content Understanding | dim=128, step=32 | ID-matched embeddings as additional sparse features |
| Interest Encoder (semantic fusion) | MRS Knowledge | Gating fusion ~0.08 weight | Auxiliary semantic enrichment for HSTU |

### Industry External Systems

| System | Company | Scale | Key Result |
|---|---|---|---|
| Token Factory (PLUM) | Google / YouTube (2026) | 110M–210M MoE Gemini | +16.8% Unique Impressions, +67.1% fresh video impressions |
| HLLM (Hierarchical LLM) | Kuaishou (2024) | Up to 7B each tier | +108–169% over baselines; A/B validated |
| TokenFormer | Tencent (2025) | Production advertising | Multi-field + sequence in one transformer |
| Climber | NetEase (2025) | Production music | +12.19% overall lift; continuous scaling verified |
| UniRec | Academic (2026) | Qwen3-0.6B backbone | +15% over SOTA multimodal baselines |
| HistLLM | Academic (2025) | User history → 1 token | Solves long-prompt efficiency issue |

---

## Paradigm (2c): Decoupled Multimodal Pipeline

**Core idea:** Run a heavy multimodal LLM **offline** to generate features / captions / embeddings, store them, then look them up as **pre-computed features** at serving time.

### Architecture

```text
OFFLINE (hours/days before serving):
  Raw Content (image, video, text) → MM-LLM (BLIP-2, LLaMA, AdsLlama)
      → Captions / Labels / Embeddings → Store in Feature Cache

ONLINE (at serving time):
  Feature Cache lookup → Concatenate with behavioral features → HSTU/DLRM → Prediction
```

### ✅ Pros

| Advantage | Evidence |
|---|---|
| Zero serving latency impact | MM-LLM runs offline; online path unchanged |
| Preserves existing infrastructure | No changes to serving architecture |
| Highest production maturity | Current dominant approach at Meta |
| Any model size offline | Can use 70B models offline without serving constraints |
| Risk-free deployment | Just add features; model architecture unchanged |
| Proven quality gains | Meta MM-LLM: +0.35% AUC; AdsLlama integration: +56% recall |
| Cost-efficient | Amortize expensive inference across all future requests |

### ❌ Cons

| Limitation | Evidence |
|---|---|
| Information bottleneck | Rich multimodal understanding compressed to fixed-size feature vector |
| Stale features | Pre-computed embeddings don't adapt to user / context at serving time |
| Not end-to-end | No gradient from ranking loss → content model; optimized separately |
| Feature engineering needed | Must decide WHICH content features to extract and HOW to integrate |
| Limited by storage | Must cache embeddings for ALL items (billions) → storage cost |
| Shallow fusion | Content enters as "just another feature" — model doesn't deeply reason about it |
| Transitional by design | Industry moving toward deeper integration (2a/2b) |

### Meta Internal Production Systems

| System | Team | Scale | Key Result |
|---|---|---|---|
| AdsLlama (Qwen3-VL-2B) | MRS Algorithm Platform (Hong Li) | 145 QPS, all ads | Multimodal embeddings for all ad ranking models |
| InterestFM (LLaVA-based) | MRS Knowledge | 87% detection rate (v4) | Topic / entity / sentiment labels for organic content |
| Biography (Llama 3.x) | MRS Knowledge | Production, all surfaces | NL user profiles; +1.235% time spent (new users) |
| Meta MM-LLM Framework (SIGIR 2026) | Meta Research | BLIP-2 + LLaMA2 | +0.35% AUC, zero latency overhead |
| POLARIS | Ads Foundation | Knowledge transfer framework | From OmniFM → downstream models; 47% revenue coverage |
| SortingHat | Feed Ranking | LLM student model | +0.035% rVPV from LLM-guided signals |

### Industry External Systems

| System | Company | Scale | Key Result |
|---|---|---|---|
| KAR (Knowledge Augmented Rec) | Huawei (KDD 2024) | Production news + music | +7% news, +1.7% music online |
| CTRL | Huawei Noah's Ark | Production | Cross-modal alignment; LLM-free inference |
| Microsoft Quality Scoring | Microsoft (RecSys 2024) | Production web rec | +1.99% online CTR (Mistral-7B scoring) |
| Netflix Artwork | Netflix (2025) | Production | 3–5% improvement via Llama 3.1 8B post-training |
| LLM-HYPER | E-commerce (2025) | Production | +55.9% NDCG@10 (cold-start via hypernetworks) |

---

## Paradigm (3): Pure Text / Natural Language LLM

**Core idea:** Represent users and items entirely in natural language, and use an LLM to **reason** about relevance through text understanding.

### Architecture

```text
Input Prompt:
  "User: [NL profile synthesized from engagement history]
   Item: [NL description of content/ad]
   Context: [time, surface, session state]
   Task: Rate relevance 0.0-1.0"
    → LLM (Llama 4 Maverick 17B, temperature=0)
    → Score/Ranking Decision + Explanation
```

### ✅ Pros

| Advantage | Evidence |
|---|---|
| Full world knowledge | LLM can reason about concepts never seen in training data |
| Explainable | Full NL rationale for every ranking decision |
| Instant new-signal onboarding | New context → just add to prompt; no retraining needed |
| Cold-start capable | World knowledge + content description sufficient for initial ranking |
| Cross-domain transfer | Same LLM works across surfaces without retraining |
| Conversational UX possible | Users can express preferences in language ("Dear Algo, show me...") |
| Handles unstructured context | Natural language, heterogeneous metadata → just put in prompt |
| Multi-task by nature | Same model can rank, explain, generate profiles, etc. |

### ❌ Cons

| Limitation | Evidence |
|---|---|
| 40–50% NDCG gap vs production | MRS Science Book: out-of-the-box LLMs lag production LSR models by 40–50% |
| 100–10,000× cost increase | ARS: cost per inference jumps by orders of magnitude |
| Latency: ms → seconds | O(1–3s) per request vs O(100ms) for traditional models |
| Collaborative signals lost | Text descriptions cannot capture behavioral co-engagement patterns |
| Hallucination risk | LLM can recommend non-existent items or fabricate attributes |
| Position / popularity bias | LLMs are biased by item position in prompt and popularity (BiasRecBench 2026) |
| Token budget pressure | Rich user history → enormous prompts (50K+ tokens per request) |
| Not competitive for general ranking | Only deployed where traditional models fail (cold-start, Dear Algo) |

### Meta Internal Production Systems

| System | Team | Scope | Key Result |
|---|---|---|---|
| ARS (Agentic Recommendation) | MRS (Max Fan, Shengbo Guo) | Ember prototype (FB Groups) | +20% NDCG@10 over MemRec; +108% over vanilla LLM |
| STAR / Dear Algo (Threads) | MRS + Threads | Threads US (launched Feb 2026) | 20% like rate (5× US average), 90% human relevance |
| LangRank | Ads Ranking | Experimental | Post-trained LLM surpasses larger non-post-trained LLMs on CTR |
| Ember LLM Ranker | Groups (CEG Rec) | FB Groups Feed | +52% relevance to 88.02% |
| Jobs Subtab LLM Ranker | LLM Foundation (Verticals) | Jobs recommendations | +1.97% YA eDAU; GAUC 66.91% |
| IG CTV Agentic RecSys | IG Relevance (InstaBrain) | Instagram TV | RecSys 2026 paper |

### Industry External Systems

| System | Company | Scale | Key Result |
|---|---|---|---|
| RankGPT / RankZephyr | Academic / Research | Benchmarks only | SOTA on MS MARCO without human labels |
| RecPIE | Google (2025) | Research | +3–34% from joint ranking + explanation |
| Rec-R1 | Academic (TMLR 2025) | Research | RL-optimized LLM beats prompting and SFT |
| LLMRank | Academic (ECIR 2024) | Research | Zero-shot ranking promising but biased |
| LinkedIn MixLM | LinkedIn (2025) | Production search | 75.9× throughput improvement with mix-interaction |
| BiasRecBench (2026) | Academic | Evaluation | Even GPT-4o / Gemini succumb to injected biases |

---

## 📊 Revised Comparison Matrix (Corrected with Meta Internal Data)

| Dimension | (1) Pure Behavioral | (2a) Discrete Codes | (2b) Soft Tokens | (2c) Decoupled Offline | (3) Pure Text LLM |
|---|---|---|---|---|---|
| **Production Scale** | ✅✅✅ Massive (billions DAU) | ✅✅ Growing (IG, Ads) | ✅✅ Deployed (YouTube, Meta FM) | ✅✅✅ Dominant at Meta | ⚠️ Narrow use cases |
| **Quality** | 🟡 Ceiling without semantics | ✅ Strong (+1.2% recall) | ✅✅ Strong (+16.8% impressions) | 🟡 Information bottleneck | ❌ 40–50% gap |
| **Efficiency** | ✅✅✅ Best (ms latency) | ✅✅ Good (beam-search overhead) | ✅✅ Good (tiny MLP overhead) | ✅✅✅ Zero online cost | ❌ 100–10,000× cost |
| **Cold-Start** | ❌ Blind | ✅ SID from content | ✅ Content tokens available | ✅ Pre-computed available | ✅✅ World knowledge |
| **Scalability** | 🟡 Ceiling proven | ✅ Scaling demonstrated (32B, 160B tokens) | ✅✅ Bends the scaling curve | 🟡 Limited by bottleneck | ❌ Cost-prohibitive |
| **End-to-End** | ✅ Fully end-to-end | 🟡 Two-stage (tokenizer separate) | ✅ Gradient flows through | ❌ Separate optimization | ✅ Fully end-to-end |
| **Explainability** | ❌ Opaque | ❌ Opaque | ❌ Opaque | ❌ Opaque | ✅✅ Full NL explanation |
| **Infra Maturity** | ✅✅✅ Years of optimization | 🟡 Building (1–2 years) | 🟡 Building (1–2 years) | ✅✅✅ Mature | ⚠️ New paradigm |
| **Meta Teams Working** | Core Modeling, FM Co-Design | InstaBrain, GRADIENT, RankID, Tok Co-Design | FM Co-Design, RankID v3, LLaTTE, HSTU-CInt, Tok Co-Design | AdsLlama, InterestFM, Biography, POLARIS | ARS, STAR, Jobs/Ember LLM |
| **Industry Trend** | Saturating (proven baseline) | Rising fast (2025–2026 wave) | Emerging convergence | Transitional | Research frontier |

---

## Key Insight: These Approaches Are NOT Mutually Exclusive

The production trajectory is **layered, not a replacement**:

```text
Layer 4 (frontier):  Pure text LLM reasoning (for edge cases only)
Layer 3 (emerging):  Soft tokens + discrete codes in unified transformer
Layer 2 (growing):   Decoupled MM-LLM features as input enrichment
Layer 1 (base):      Behavioral sequence model (HSTU backbone)

PRODUCTION = Layer 1 + Layer 2 + increasingly Layer 3
            (behavioral base + offline content features + online soft token enrichment)
```

**No approach replaces the others. The winning architecture stacks them:**

- **HSTU backbone** handles behavioral sequences (Layer 1)
- **AdsLlama / InterestFM** provides offline content features (Layer 2)
- **Multitoken NRO / Token Factory** injects them as soft tokens (Layer 3)
- For special cases, **LLM reasoning** handles what others can't (Layer 4)
