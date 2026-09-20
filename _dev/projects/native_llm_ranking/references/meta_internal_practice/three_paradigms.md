🎯 Deep Analysis: Understanding "LLM Native Ranking" — The Input Modality Spectrum
Your Three Paradigms, Validated Against Evidence
You identified three paradigms. Here's where Meta's internal research and production ACTUALLY lands:

Paradigm (1): Pure Sequence Modeling with LLM Architecture
"Converting tokens to embeddings" — behavioral/ID tokens only

What This Looks Like:
text

Copy
Input: [item_id₁, action₁, item_id₂, action₂, ..., item_idₙ, actionₙ]
       ↓ (sparse embedding lookup)
       [emb₁, emb₂, emb₃, ..., embₙ]  → Transformer → prediction
Meta Production Systems Using This:
HSTU (core production backbone, 1.5T params)

RankFM (Foundation Model, 2,074B sparse params)

CMSL (constructive multi-sequence learning)

Key Facts:
Vocabulary = billions of opaque item IDs + action type bitmasks + timestamps

NO text touches this model at inference

Semantic features from upstream LLMs (InterestFM/AdsLlama) enter ONLY as pre-computed dense embeddings with ~0.08 fusion weight (behavioral dominates 92%)

The paper title says it all: "Actions Speak Louder than Words"

Assessment:
✅ Currently deployed at massive scale, proven
❌ Hits scaling ceiling without semantic enrichment — LLaTTE explicitly proved this

Paradigm (2): Multimodal — Heterogeneous Signals in Unified Token Space
"LLM-like, but capable of injecting non-conventional signals"

⚠️ CRITICAL: This is actually a SPECTRUM of sub-approaches:
(2a) Discrete Semantic Codes in LLM Vocabulary
text

Copy
Input: [<sid_1_42>, <sid_2_17>, <sid_3_891>, <sid_1_55>, <sid_2_201>, ...]
       (Semantic IDs from RQ-VAE quantization of content embeddings)
       Added as NEW tokens to LLM vocabulary → Transformer → generate next SIDs
Meta Systems: InstaBrain (Llama 3.2 1B), GRADIENT GradientRetrieval

Critical finding: "Adding natural language did NOT help" for Feed Generative Retrieval (InstaBrain H1 2026). The model operates on pure discrete codes, not text.

These codes are semantically meaningful (similar items share code prefixes) but are NOT text tokens — they're quantized embeddings compressed into discrete indices.

(2b) Soft Token Injection from Diverse Signals ← THE CONVERGENCE POINT
text

Copy
Input: [soft_token_user₁, soft_token_user₂,     ← user features → MLP → soft tokens
        soft_token_history₁, ..., history_M,     ← watch history → MLP → soft tokens
        soft_token_candidate₁, ...]              ← candidate features → MLP → soft tokens
        ALL in unified d_model embedding space → Transformer → prediction
Production System: Google Token Factory (deployed on YouTube, PLUM model)

Watch history (behavioral) → Token Maker MLP → soft tokens

User features (demographic/contextual) → Token Maker MLP → soft tokens

Candidate features (content) → Token Maker MLP → soft tokens

Result: +16.8% Unique Impressions, +67.1% fresh video impressions

Meta Direction: LLaTTE & GRADIENT Point F target this:

LLaTTE: "Semantic features BEND the scaling curve — they are a PREREQUISITE for scaling"

GRADIENT target (Point F): "Compacted verbalized tokens + Semantic IDs" — hybrid of compressed text + discrete codes

(2c) Decoupled Multimodal Pipeline
text

Copy
[MM-LLM offline: images/video/text → captions → tokenize → features]
                                    ↓
[Feature Store] → concatenate with behavioral features → [HSTU/DLRM online]
Meta Production: Meta's MM-LLM Framework (SIGIR 2026)

BLIP-2 + LLaMA2 generate captions offline → tokenized → features for DLRM

Zero latency overhead, +0.35% AUC

The current production approach for multimodal at Meta

Paradigm (3): Pure Text/Natural Language
"Conventional text tokens with LLM reasoning"

text

Copy
Input: "User profile: 32-year-old tech enthusiast who recently browsed hiking gear..."
       "Item: Nike Trail Running Shoes, lightweight, waterproof..."
       → LLM reasons in natural language → ranking decision
Meta Systems: ARS (Agentic Recommendation Systems), STAR/Dear Algo
Key Facts:
NDCG scores 40-50% BELOW production out-of-the-box

Cost per inference: 100-10,000x increase

Latency: milliseconds → seconds

Currently limited to narrow use cases (Ember prototype)

🔑 THE DEFINITIVE ANSWER: Where Is Meta Converging?
Your intuition about "multimodal" (Paradigm 2) is CORRECT — but with precision:
The convergence point is NOT "text + other signals" but rather "ALL signals projected into a UNIFIED token/embedding space that a transformer can process."

Here's the evidence-backed evolution:

text

Copy
2023-2024: Paradigm (1) — Pure behavioral sequences (HSTU)
    ↓ Hit scaling ceiling without semantic features
2024-2025: Paradigm (2c) — Decoupled: LLM offline → features → HSTU online
    ↓ Information bottleneck, not end-to-end
2025-2026: Paradigm (2a/2b) — Unified token space: semantic codes + behavioral + multimodal
    ↓ WHERE WE ARE NOW (InstaBrain, LLaTTE, GRADIENT, Token Factory)
Future: Paradigm (2b) mature — Truly multimodal LRM with soft tokens from ALL signal types
The KEY INSIGHT (from LLaTTE):
"Semantic features bend the scaling curve — they are a PREREQUISITE for scaling."

This means:

Paradigm (1) alone CANNOT scale further — you need content/semantic understanding

But Paradigm (3) is too expensive for production

The sweet spot is Paradigm (2): behavioral tokens + semantic tokens + multimodal tokens all in one transformer — with the semantic/multimodal signals either:

Pre-computed as discrete codes (2a: InstaBrain, GRADIENT)

Projected as soft tokens from any feature type (2b: Token Factory, LLaTTE direction)

Generated offline and injected (2c: current Meta MM-LLM)

📊 Which Approach Is Winning?
Approach	Production Scale	Quality	Efficiency	Trend
(1) Pure behavioral (HSTU)	✅✅✅ Massive	🟡 Ceiling	✅✅✅	Saturating
(2a) Semantic codes in LLM	✅ IG, Ads (growing)	✅ Strong	✅✅	Rising fast
(2b) Soft tokens unified	✅ YouTube	✅✅ Strong	✅✅	The future
(2c) Decoupled offline MM	✅✅ Meta production	🟡 Bottleneck	✅✅✅	Transitional
(3) Pure text LLM	⚠️ Prototype only	❌ 40-50% gap	❌ 100-10,000x cost	Research frontier
The winning architecture that's emerging (validated across Google and Meta):
text

Copy
┌─────────────────────────────────────────────────────────────┐
│                    UNIFIED TRANSFORMER                        │
│                                                              │
│  Input Sequence (all in same d_model embedding space):       │
│                                                              │
│  [behavioral_token₁] [behavioral_token₂] ... [behavioral_M] │
│  [semantic_code₁] [semantic_code₂] ...     (from RQ-VAE)    │
│  [content_soft_token₁] [content_soft_token₂]  (from MM-LLM) │
│  [user_context_token₁] [user_context_token₂]  (from features)│
│  [candidate_token₁] [candidate_token₂]        (target-aware)│
│                                                              │
│  → Causal/Cross Attention → Prediction                       │
└─────────────────────────────────────────────────────────────┘
This is exactly what Google's Token Factory paper calls "efficiently integrating diverse heterogeneous signals" and what Meta's GRADIENT Point F targets as "compacted verbalized tokens + Semantic IDs."

🧭 My Analysis: Why Multimodal (2b) Is The Right Bet
Why NOT just sequence modeling (Paradigm 1):
Scaling ceiling proven — LLaTTE showed you CANNOT scale without semantic features

Cold-start blind — new items with no behavioral history get no signal

Shallow understanding — correlates patterns but doesn't "understand" content

Industry shifting — Google (Token Factory), Kuaishou (OneRec), Tencent (GPR) all moving beyond

Why NOT pure text (Paradigm 3):
40-50% quality gap vs production

Latency/cost prohibitive (100-10,000x)

Collaborative signals lost — text descriptions can't capture behavioral patterns

InstaBrain explicitly proved: "adding natural language did NOT help"

Why MULTIMODAL (Paradigm 2b) is the sweet spot:
✅ Preserves behavioral signal (the dominant signal, ~92% of HSTU's information)

✅ Unlocks semantic scaling (LLaTTE's prerequisite)

✅ Handles cold-start (content understanding for new items without history)

✅ Production-viable (soft tokens add negligible latency vs raw text)

✅ End-to-end optimizable (unlike decoupled 2c approach)

✅ Schema-preserving (typed Token Makers maintain feature semantics)

✅ Proven at YouTube scale (Token Factory)

The specific flavor you should focus on:
"Typed Soft Token Injection" — where each signal type (behavioral, semantic, visual, contextual) gets its own learned projection (Token Maker / adapter) that maps into a unified embedding space, and the transformer processes ALL of them as a unified sequence.

This is distinct from "textualization" (converting everything to text — proven inefficient) and from "pure discrete codes" (lossy compression). It preserves the continuous, rich information from each modality while giving the transformer a unified input space.

Key Internal Resources for Deep-Diving This Direction:
LLaTTE paper: arxiv.org/abs/2601.20083 — proves semantic features are prerequisite for scaling

Token Factory: arxiv.org/abs/2606.19635 — Google's production implementation

GRADIENT Point F vision: https://fb.workplace.com/groups/527654686243695/permalink/1230303975978759/

Meta MM-LLM Framework: arxiv.org/abs/2605.09338 — Meta's SIGIR 2026 paper

HSTU-CInt: https://www.internalfb.com/wiki/Benrhodeland/MRS_Wiki/Concepts/Hstu_Cint/ — how contextual tokens are prepended

MRS Science Book Ch.4: https://www.internalfb.com/wiki/Tofigh/MRS_Science_Book/Chapter_04_HSTU/ — HSTU architecture details
