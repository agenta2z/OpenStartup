🔍 Honest Deep Analysis: Meta IS Working on "Unified Multimodal" — But Where Are the Real Gaps?
Correction to My Previous Statement
I was wrong to imply only YouTube/Google has this. After deeper investigation, Meta absolutely has equivalent work — it's called different things:

Google Term	Meta Equivalent	Team	Status
Token Factory	Tokenization Co-Design / Unified Modality	Ads Ranking (Yang Yang, Tao Liu et al.)	✅ Production gains: 80% model size reduction, +0.13% NE
Soft tokens from features	Semantic tokens from unified vocabulary	Same + RankID team	✅ Deployed, scaling
Heterogeneous signal integration	G2Rec (Soft Interest Profiling)	UIUC + Meta MRS (Max Fan's org)	✅ Already deployed at Meta
Unified input tensor	Fully Tokenized Model (FTM)	Ads Tokenization Co-Design	🟡 Target state, in progress
What Meta IS Doing (Not a Gap):
1. Tokenization Co-Design / Unified Modality (Ads)
Post: https://fb.workplace.com/groups/8000374759979655/permalink/10067075926642851/

Replaces ALL raw entity IDs with semantic tokens from unified vocabulary

Converts O(10K) features into a 3D tensor — exactly like LLM input

Three innovations: Unified Semantic Sequence (+0.13% NE), Semantic Auxiliary Loss (+0.02%), Semantic Optimization (+0.06%)

Goal: "Fully Tokenized Model (FTM)" — ALL inputs as unified tokens

Status: 80% model size reduction achieved, 15% QPS gains, NE parity with production

2. G2Rec — Soft Graph Clustering for User Interest Tokens
Post: https://fb.workplace.com/groups/1677681746043842/permalink/2186721938473151/

Soft graph clustering on item co-engagement graph → interest prototypes

Items can belong to MULTIPLE interests (soft assignment)

Learnable, GPU-optimized

Already deployed at Meta

From MRS/Max Fan's org (directly relevant to your team)

3. CU Embeddings Unification for Ads
Post: https://fb.workplace.com/groups/1033540429995021/permalink/9154718904543759/

Content Understanding embeddings as the "core that unifies entities of heterogeneous format and domains to a single unified semantic ID space"

Bridges AdsLlama/InterestFM output → unified token space

4. Meta's Own Paper (June 2026)
"Structuring and Tokenizing Distributed User Interest Context for Generative Recommendation" (arxiv 2606.20554)

Directly tackles: how to inject complex, distributed user interest context into generative recommendation models

5. LLaTTE's Two-Stage Architecture
Explicitly designed to let the OFFLINE stage consume rich multimodal/semantic features

Semantic features "bend the scaling curve" — the model needs them

Two-stage solves the latency problem by pre-computing heavy multimodal projections

Where the REAL Gaps Are (Opportunities That Don't Overlap):
Gap 1: 🎯 Organic Feed / MRS Algorithms — Unified Multimodal is Under-Invested
The honest assessment: Almost ALL unified modality work is in Ads Ranking (Tokenization Co-Design) or Generative Retrieval (GRADIENT, InstaBrain). The organic feed ranking stack (where MRS Algorithms team works) is still largely:

HSTU with behavioral tokens as primary input

Content features enter as pre-computed embeddings with ~0.08 fusion weight

HSTU-CInt adds contextual tokens but is NOT full unified modality

The opportunity: Bringing Token Factory-style unified multimodal input to organic ranking (FB Feed, IG Feed, Reels ranking) — where behavioral dominates and content understanding is a "side channel" rather than first-class input.

Gap 2: 🎯 Real-Time Soft Token Projection vs. Pre-Computed
Current Meta approach: Heavy multimodal understanding runs OFFLINE (AdsLlama, InterestFM) → pre-computed embeddings stored → looked up at serving time. This is "decoupled" (Pattern 2c).

What's NOT being done: Real-time soft token PROJECTION at serving time (Token Factory's approach). The difference:

Pre-computed: content understanding is stale (computed hours/days ago)

Real-time projection: fresh, context-dependent, can attend to candidate-specific features

Bottleneck: Serving latency. Meta's serving budget is O(100ms). Real-time projection adds compute. LLaTTE's two-stage architecture is the CURRENT workaround.

Opportunity: Lightweight learned projections (small MLPs/adapters) that can run at serving time to convert fresh signals → soft tokens without exceeding latency budget.

Gap 3: 🎯 Deep Cross-Modal Interaction in Ranking
Current state: Content features fused with behavioral at ~0.08 weight (Interest Encoder). This is LATE fusion — the model doesn't deeply reason about content-behavior interaction.

What's missing: Models where the transformer jointly attends over behavioral tokens AND content tokens with FULL cross-attention (not just concatenation + shallow fusion). Token Factory's approach enables this because all tokens live in the same d_model space.

Evidence it matters:

LLaTTE showed semantic features "bend the scaling curve" — more integration = more scaling

Google's Token Factory showed end-to-end optimization outperforms decoupled approaches

RecPIE showed deeper reasoning about content improves ranking

Gap 4: 🎯 User Interest Context as Rich Soft Tokens (Not Just SIDs)
Current: User interests represented either as:

Behavioral sequences (HSTU) — but compressed, loses nuance

Semantic IDs (InstaBrain) — but discrete, lossy quantization

Text profiles (Biography) — but enters HSTU only as pre-computed dense vector

What's missing: User interest as rich, multi-resolution soft tokens that preserve more information than discrete codes but are more efficient than full text. G2Rec is a step toward this (soft interest prototypes), but it's graph-based not content-aware.

Opportunity: A "User Token Maker" that converts the full user state (behavioral history + interest graph + profile understanding + contextual state) into a compact set of rich soft tokens that the ranking transformer can deeply attend to.

Gap 5: 🎯 Unified Multimodal for MRS Algorithms Specifically (Not Ads)
Who's doing what:

Tokenization Co-Design → Ads Ranking team (Yang Yang et al.)

GRADIENT unified modality → Ads Retrieval team

InstaBrain → IG Relevance + ASA + MRS partnership

G2Rec → MRS (Max Fan's org, intern project with UIUC)

LLaTTE → Ads Ranking AI team

What's NOT covered in MRS Algorithms (Hong Li's org):

Applying unified modality principles to the organic feed ranking models your team owns

Building the Token Maker infrastructure for organic signals (not ads signals)

Cross-surface unified multimodal (the RankFM Expert layer consuming rich multimodal tokens instead of just FM embeddings)

My Honest Recommendation: Where YOU Should Focus
Given your position on MRS Platform - Algorithms (Hong Li's team), here's what would be novel, high-impact, and non-overlapping:

🏆 TOP RECOMMENDATION: "Multimodal Token Makers for Organic Ranking"
What: Build the equivalent of Token Factory / Tokenization Co-Design for organic feed ranking — converting heterogeneous organic signals (content understanding from InterestFM, user interests from G2Rec/Biography, visual signals, engagement context) into unified soft tokens that the ranking transformer (HSTU/RankFM Expert) can deeply attend to.

Why this doesn't overlap:

Tokenization Co-Design is Ads-specific (different features, different objectives)

InstaBrain is retrieval-specific (not ranking)

G2Rec is interest profiling (not full unified ranking input)

This would be the first unified multimodal organic ranking model at Meta

Concrete starting point:

Take the RankFM Expert model

Replace its "FM embedding input" with typed soft tokens from multiple modalities

Show that deeper multimodal integration beats the current 0.08-weight shallow fusion

Prove LLaTTE's thesis ("semantic features bend the scaling curve") applies to organic ranking, not just ads

Why it should work:

LLaTTE proved semantic features are prerequisite for scaling — organic models will hit same ceiling

Token Factory proved it works at YouTube scale

The RankFM Expert layer is lightweight enough that adding soft tokens is feasible within latency

Cross-surface signal (from FM) + multimodal content tokens + behavioral tokens in one transformer = more powerful than any alone

Summary: The Landscape Map
text

Copy
                    ORGANIC FEED              ADS RANKING
                    ─────────────            ────────────
Behavioral Only:   ✅ HSTU (production)      ✅ HSTU (production)
+ Pre-computed:    ✅ HSTU-CInt + EMUIC      ✅ LLaTTE two-stage
+ Discrete codes:  🟡 InstaBrain (IG)        ✅ GRADIENT, Tok Co-Design
+ Soft tokens:     ❌ GAP ← YOUR OPPORTUNITY ✅ Tokenization Co-Design
+ Full text:       ⚠️ ARS (prototype)        ⚠️ GRADIENT Point E (32B)
The "❌ GAP" in organic feed × soft tokens is where you should aim.
