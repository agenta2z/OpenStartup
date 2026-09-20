Unifying Sequence Modeling and Multimodal Semantics: A Comprehensive Investigation into LLM-Native Ranking

The paradigm of large-scale recommender systems is currently undergoing a profound architectural and conceptual metamorphosis. For over a decade, Deep Learning Recommendation Models (DLRMs) dominated the industry, relying on vast, sparse embedding tables and pointwise multilayer perceptron (MLP) networks to score candidate items independently based on historical interaction logs. However, the emergence of Large Language Models (LLMs) has catalyzed a fundamental transition toward Generative Recommender Systems (Gen-RecSys). This transition has sparked a critical architectural debate regarding the true nature of "LLM-native ranking."

A central question arises: Is LLM-native ranking fundamentally an evolution of sequence modeling—where user histories are treated as token streams and mapped to embeddings, akin to early transformer adaptations—or does it mandate the injection of rich, non-conventional multimodal and semantic signals inherent to native language models? The empirical evidence, recent algorithmic breakthroughs, and industrial deployments demonstrate that while LLM-native ranking originated as a highly scalable sequence modeling adaptation, its current state and future trajectory are unequivocally defined by the latter paradigm. The integration of multimodal semantics, continuous dense features, and rich textual signals is not merely an optional enhancement; it is a structural necessity required to overcome the semantic opacity of pure item identifiers.

The true power of LLM-native ranking lies in synthesizing structural sequential transduction with the cross-modal reasoning, open-world knowledge, and textual comprehension native to foundation models. This report provides an exhaustive, multi-layered investigation into LLM-native ranking, dissecting its foundational sequence-based architectures, the mathematical evolution toward multimodal signal injection, the hybridization of collaborative and semantic features, and the highly specific system-level co-designs required to serve these models at an industrial scale.
The Architectural Shift: From Discriminative Scoring to Generative Transduction

To properly conceptualize LLM-native ranking, it is necessary to first deconstruct the inherent limitations of the traditional Discriminative Recommendation (DR) paradigm. Discriminative systems, such as canonical DLRMs, operate by predicting a scalar relevance score for a given user-item pair. These systems treat items as atomic, categorical identifiers, leveraging feature interactions captured via dot-products, cross-networks, or factorization machines.

While this discriminative paradigm scales efficiently across massive datasets, it suffers from severe representation bottlenecks. Because it treats item IDs as discrete, non-compositional variables, a DR model cannot reason over the intrinsic attributes of an item—such as brand identity, visual aesthetic, or textual nuance—without relying on heavy, manually engineered feature crosses. Furthermore, the traditional industrial pipeline strictly decouples candidate retrieval (optimized for recall) from downstream ranking (optimized for precision). This modularization inherently breaks the end-to-end optimization of the user's overarching objective satisfaction.

Generative Recommendation models natively resolve these constraints by reformulating recommendation as a sequence-to-sequence autoregressive transduction task. Under this framework, a user's entire action and content history is merged into a chronological token stream, which is mathematically modeled as a joint probability distribution where each subsequent action is conditioned on the prior sequence. This allows a single transformer-based architecture to simultaneously perform context aggregation, candidate retrieval, and list-wise ranking within a unified generative step.
Architectural Dimension	Discriminative Recommendation (DLRM)	Generative Recommendation (LLM-Native)
Fundamental Task Formulation	Pointwise or pairwise scalar relevance scoring	Autoregressive sequence transduction and next-token generation
Primary Item Representation	Atomic ID embeddings (sparse table lookups)	Semantic IDs, Term IDs, and continuous Multimodal embeddings
System Pipeline Structure	Decoupled and modularized (Retrieval → Pre-ranking → Ranking)	Unified and collapsed (End-to-End Generation and Scoring)
Primary Hardware Bottleneck	Memory-bound (CPU-side sparse embedding lookups)	Compute-bound (GPU-side dense multi-head attention passes)
Feature Interaction Mechanism	Extensive manual cross-features and MLP combinations	Automated cross-modal synergy via self-attention mechanisms
Cognitive Reasoning Capability	Shallow statistical correlations derived from co-occurrence	Compositional, semantic, and temporal intent reasoning
The Sequence Modeling Foundation: Transduction and Structural Evolution

The initial hypothesis—that LLM-native ranking is essentially sequence modeling utilizing LLM techniques—is heavily rooted in the early applications of Transformer architectures to user interaction sequences. The most prominent and influential example of this is Meta's Hierarchical Sequential Transduction Unit (HSTU). Understanding HSTU is critical, as it forms the chassis upon which true multimodal semantics are later injected.
The HSTU Architecture and Pointwise Aggregated Attention

Meta introduced the HSTU architecture to address the unique shape and behavior of recommendation data, which diverges significantly from natural language corpora. While traditional LLMs process fixed, finite vocabularies, recommender systems must process billions of non-stationary items with extreme cardinality, highly jagged interaction sequences, and heterogeneous action types such as clicks, watches, and purchases.

HSTU replaces the traditional DLRM multi-layer perceptron with hierarchical, memory-efficient transformer blocks specifically tuned for this environment. Crucially, HSTU modifies the core attention mechanism. Standard softmax attention struggles in recommendation settings because the denominator of the softmax function spans an ever-changing, streaming vocabulary of items, leading to normalization instability. To counteract this, HSTU utilizes Pointwise Aggregated Attention. This mechanism employs elementwise SiLU activations and pointwise normalization, which prevents saturation and allows the model to capture the raw intensity of user preferences in a non-stationary setting without degrading model quality.

In the HSTU framework, the actual ranking process is executed by appending candidate items directly into the user's history sequence. Facilitated by a framework known as M-FALCON, the model uses target-aware attention to score an entire list of candidates in a single forward pass. By modifying the causal mask, each candidate attends to the shared user interaction history (UIH) tokens but does not attend to the other candidates. This allows the transformer to compute the direct relationship between the target item and the historical sequence with immense computational efficiency. This methodology represents pure sequence modeling at a massive scale—extrapolated by Meta up to 1.5 trillion parameters—converting user actions into dense embeddings and processing them via autoregressive attention.
Bending the Scaling Law: ULTRA-HSTU and Sparse Attention Topologies

However, relying purely on self-attention introduces a severe limitation: computational complexity scales quadratically, O(L2), with respect to the sequence length L. In recommendation systems where a user's lifetime history can span tens of thousands of interactions, quadratic attention becomes economically and computationally prohibitive.

To circumvent this bottleneck, advanced sequence models like ULTRA-HSTU introduce highly specialized model-system co-designs inspired by efficient LLMs such as DeepSeek-V2. ULTRA-HSTU implements a mechanism known as Semi-Local Attention (SLA). SLA is a hybrid attention mechanism that restricts each token's attention to two distinct sparse windows: a local window (K1​ nearest neighbors) designed to capture acute, recent user intent, and a global window (K2​ oldest interactions) intended to capture long-term aggregate behavioral patterns. By fusing a fixed-size sliding-window attention with a residual linear-attention stream, SLA reduces the attention complexity to a highly manageable O((K1​+K2​)⋅L).

Furthermore, ULTRA-HSTU leverages a topological innovation known as Attention Truncation (or layer truncation). Recognizing that not all historical tokens require deep, non-linear processing across every layer, the architecture passes the full user sequence through the first N1​ layers to capture broad contextual embeddings. However, it restricts the subsequent N2​ deeper layers strictly to the most recent and highly relevant segment of the sequence. This pure structural innovation yields an unprecedented 21$\times$ improvement in inference scaling efficiency and a 5$\times$ improvement in training scaling efficiency compared to the base HSTU. These advancements demonstrate that optimizing the underlying sequence modeling chassis remains a vital and highly active component of LLM-native ranking development.
The Semantic Gap: Exposing the Limits of ID-Only Sequence Paradigms

While models like HSTU and ULTRA-HSTU prove that massive-scale sequence modeling is computationally viable, treating items strictly as atomic, opaque IDs—even within a sophisticated Transformer—exposes a fundamental flaw known as the "semantic gap". ID-only sequence models suffer from three distinct and critical failures that necessitate the introduction of LLM-native multimodal signals:

    Semantic Opacity: An ID embedding for a specific product, such as a "waterproof ski jacket," carries no intrinsic meaning to the model. The transformer only learns the item's relevance through co-occurrence patterns in the training data. If a user previously purchased "snow boots," the model cannot organically infer a link to the "ski jacket" unless historical user logs explicitly and frequently connect those exact two IDs.

    Cold-Start Vulnerability: When new items are added to a catalog, they inherently lack an interaction history. In an ID-only paradigm, their newly initialized ID embeddings are effectively random noise, rendering the sequence model completely incapable of ranking them accurately until sufficient human interaction data is painstakingly accumulated.

    Cross-Domain Rigidity: ID embedding spaces are mathematically confined to the specific interaction corpus on which they were trained. They cannot leverage external world knowledge, cross-domain contextual understanding, or the zero-shot reasoning capabilities that define modern pretrained LLMs.

The Advent of Semantic Identifiers (SIDs) and Term IDs (TIDs)

To bridge this semantic gap, generative recommenders evolved to represent items via Semantic IDs (SIDs) or Term IDs (TIDs). Instead of relying on atomic variables, items are tokenized into discrete, hierarchical sequences using advanced vector quantization techniques such as Residual Quantization VAEs (RQ-VAE) or LLM-driven term extraction.

A premier example of this semantic evolution is YouTube's PLUM (Pre-trained Language Models for Industrial-scale Generative Recommendations) framework. In the PLUM architecture, items are no longer treated as isolated IDs; instead, their textual metadata, visual content frames, and audio features are passed through separate modality-specific encoders. These diverse signals are concatenated and projected into a unified latent vector, which is then quantized into an SID. By expanding the vocabulary of a pre-trained LLM to include these newly generated SID tokens through a process of Continued Pre-Training (CPT), YouTube forces the model to mathematically align the collaborative behavior of users with the rich, multi-modal essence of the videos themselves.

Conversely, frameworks like the Generative Recommendation Language Model (GRLM) utilize Term IDs (TIDs). TIDs are structured keyword sequences extracted directly from item metadata using an LLM's native vocabulary, guided by neighborhood-based in-context learning. This approach eliminates the hallucination issues frequently caused by forcing an LLM to generate raw titles, while simultaneously avoiding the computationally costly vocabulary expansion required by RQ-VAE-based SIDs.
The Multimodal Frontier: Achieving True LLM-Native Ranking

The evolution from atomic sequence IDs to Semantic IDs naturally answers the core inquiry: LLM-native ranking is heavily inclined toward the multimodal and semantic injection paradigm. Treating recommendation purely as the sequence modeling of atomic IDs represents merely a transitional phase in the technology's history. The true, native phase of LLM-based ranking fundamentally relies on the synergistic, mathematically enforced integration of text, continuous dense features, and multimodal signals.
Cross-Modal Synergy and the SynGR Framework

When generative recommenders ingest both text (e.g., product descriptions, titles) and visual embeddings (e.g., image pixels, video frames), they encounter a distinct architectural hazard known as modality dominance. Textual tokens are discrete, sequential, and highly semantically compact, whereas visual embeddings are continuous, high-dimensional, and often noisy.

Due to this stark mismatch in information density, naive multimodal transformers often take "unimodal shortcuts." The attention mechanism will lazily rely entirely on the dense textual tokens—ignoring the visual inputs—thereby failing to capture the cross-modal synergy required for accurate recommendations. For instance, ranking a "luxury handbag" requires synthesizing both the visual aesthetic (such as quilted leather textures) and the textual signal (brand identity) to deduce its high-end positioning. Neither modality alone is sufficient to capture the item's emergent semantic profile.

The SynGR (Synergistic Generative Recommendation) framework actively disrupts these unimodal shortcuts. SynGR employs a mathematically rigorous saliency-aware masking mechanism. It extracts self-attention weights A(m)∈RN×N from the final encoder layer to compute a global saliency score ℓi​ for each token:

ℓi​=M⋅N1​m=1∑M​j=1∑N​Aj,i(m)​


Based on these modality-level saliency densities, SynGR intentionally masks the most salient tokens within the dominant modality (typically the textual features) during the training phase. By obscuring the path of least resistance—a property termed Unimodal Obscuration—the transformer is computationally forced to explore latent synergistic information and leverage higher-order cross-modal dependencies to satisfy its generative objective. This explicit, forced synthesis of multiple signals proves definitively that LLM-native systems are not passively mapping tokens; they are actively reasoning across distinct sensory modalities.
Hybridizing the Transducer with Textual Semantics: HSTU-BLaIR

Meta's recent architectural iteration, HSTU-BLaIR, provides concrete, empirical proof of the absolute necessity of textual injection. While the original HSTU was a highly efficient sequence model over atomic IDs, HSTU-BLaIR directly injects contrastively trained textual embeddings into the sequence transducer.

BLaIR (Bridging Language and Items for Retrieval and Recommendation) is a lightweight sentence embedding model pretrained on a massive corpus of over 570 million Amazon Reviews and 48 million items. It utilizes a contrastive InfoNCE objective to learn the deep correlations between item metadata and natural language context. In the HSTU-BLaIR architecture, the trainable item ID embedding eid​ is fused with the frozen BLaIR textual embedding etext​ via a learnable projection matrix Wtext​:

ecombined​=eid​+Wtext​etext​


This fused ecombined​ vector completely replaces the pure item-ID at the input layer of the HSTU transducer. Consequently, the semantic signals derived from the human-readable text metadata propagate hierarchically through the entire transformer stack. Furthermore, HSTU-BLaIR utilizes text-aware local negative sampling to supply semantically informed negatives during training, sharpening the model's contrastive boundaries. Empirical results demonstrate that HSTU-BLaIR drastically outperforms the ID-only HSTU variant across multiple benchmarks, specifically excelling in cold-start and long-tail scenarios. This effectively proves that pure sequence modeling is fundamentally insufficient without textual semantic injection.
Disentangling Modalities: Catalog-Native LLMs and IDIOMoE

Further validating the multimodal hypothesis is the realization that natural language and collaborative filtering (CF) signals represent two fundamentally different "dialects." Collaborative signals are token-efficient but semantically opaque, while LLM natural language is semantically rich but struggles to model implicit, statistical user preferences. If these two distinct dialects are processed through a singular MLP layer within an LLM, they often destructively interfere, degrading both the model's recommendation accuracy and its general language comprehension.

The IDIOMoE (Item-ID + Natural-language Mixture-of-Experts) framework resolves this interference by separating collaborative filtering from semantic processing deep inside the LLM's architecture. By splitting the Feed-Forward Network (FFN) of each LLM block into a dedicated text expert and a dedicated item expert, and regulating them with token-type gating, IDIOMoE allows the model to process standard English tokens through the semantic experts, and Item-IDs through the collaborative experts.

Through the lens of key-value memory in FFN neurons, this disentangled Mixture-of-Experts separation yields clearer item-text affinity and higher category purity than non-MoE baselines. This sophisticated architecture proves that LLM-native ranking is far more complex than blindly transforming tokens into embeddings; it requires dynamically orchestrating different modalities and routing them to specialized neurological pathways within the foundation model.
Bridging the Divide: Retaining Traditional Signals in Generative Models

If LLM-native ranking relies heavily on natural language and continuous multimodal embeddings, what happens to the highly structured, non-sequential features that defined the DLRM era? Factors such as the time-of-day, the user's geographic location, real-time contextual variables, and handcrafted feature crosses remain incredibly predictive for real-time engagement platforms (e.g., food delivery, ride-sharing, and short-form video).
The MTGR Architecture and Group-Layer Normalization

The Meituan Generative Recommendation (MTGR) framework explicitly addresses the friction between sequence modeling and traditional feature engineering. Generative models typically abandon structured cross-features because sequence models inherently expect uniform, temporally ordered token sequences. However, engineers at Meituan discovered that discarding DLRM cross-features degraded predictive CTR performance so severely that scaling up the LLM's parameters could not compensate for the loss of that dense statistical signal.

To resolve this, MTGR operates on an HSTU backbone but retains full compatibility with traditional DLRM feature schemas. It achieves this by transforming categorical features, continuous scalars, and highly complex cross-features into discrete, heterogeneous tokens. However, mixing these radically different data distributions into a single sequence can collapse the self-attention gradients. To prevent this, MTGR introduces Group-Layer Normalization (GLN).

GLN normalizes different types of tokens—specifically dividing them into User Features, Item Features, Cross Features, Real-Time Sequence, and Global Sequence—within their respective, isolated semantic spaces prior to their interaction in the attention layers. Additionally, MTGR employs a sophisticated dynamic causality masking strategy to prevent information leakage while maximizing parallel computation:

    Historical and User Tokens: Visible to all subsequent tokens in the sequence.

    Real-Time Sequence Tokens: Constrained by strict temporal causality, visible only to tokens with later timestamps.

    Candidate Target Tokens: Visible strictly only to themselves, allowing the model to compute independent predictions for an entire list of candidates simultaneously without the candidates influencing one another.

By successfully incorporating cross-features into a sequence transducer, MTGR achieves an astonishing 65$\times$ reduction in FLOPs for single-sample forward inference compared to highly optimized production DLRMs. This proves that modern LLM-native ranking is not mutually exclusive with traditional dense feature engineering; rather, the Transformer is utilized as a universal routing engine capable of synthesizing temporal sequences, natural language, and engineered cross-features simultaneously.
Agentic Architectures and the Evolution of Persistent Memory

As the LLM-native recommendation paradigm matures, the architecture is expanding beyond single-pass, autoregressive sequence prediction into fully autonomous agentic frameworks. In traditional ranking, a user's sequence is entirely stateless across sessions; the model simply processes the L most recent tokens in a vacuum. LLM-native systems introduce the revolutionary concept of persistent cognitive memory.

The Memory-Augmented Agentic Recommender System (MARS) represents a massive structural leap in this direction. MARS discards flat memory representations, which inherently conflate noisy, ephemeral signals (like a random, one-off click) with stable, long-term user preferences. Instead, MARS maintains a three-tier structured belief state that treats recommendation as a partially observable reasoning problem:

    Event Memory: Captures the raw transition dynamics and chronologies of user interactions, preserving the raw sequence data.

    Preference Memory: Acts as a mutable state representing specific granular tastes, enabling surgical credit assignment. When new evidence arrives, it updates only the relevant belief node without disturbing unrelated variables in the state space.

    Profile Memory: A synthesized, Markovian natural-language narrative of the user's holistic identity and overarching intents.

MARS governs these three tiers via a complete memory lifecycle—encompassing extraction, reinforcement, weakening, consolidation, forgetting, and resynthesis. Crucially, this lifecycle is not hardcoded; it is managed dynamically by an LLM-based planner that adaptively schedules operations based on accumulated context, balancing memory freshness against computational cost. This indicates that LLM-native ranking is evolving into an active reasoning task, where the ranker does not merely score a static sequence, but actively interrogates and updates a structured, evolving memory graph.

Furthermore, agentic architectures are increasingly deployed to handle multi-surface orchestration. For instance, in Connected TV (CTV) content discovery, LLM agents autonomously reason over heterogeneous contextual signals expressed in natural language—including breaking news, cultural events, and cross-surface activity. The LLM acts as an orchestrator, retrieving contextual topics dynamically and delegating latency-sensitive personalization tasks to traditional ML components, thereby bypassing traditional, rigid multi-stage retrieval pipelines entirely.
Systems Optimization: Serving LLMs at Industrial Scale

Deploying generative models in latency-critical ranking environments—where P99 latency budgets are typically constrained to under 100 milliseconds—requires a massive infrastructural overhaul. As highlighted by the MLPerf DLRMv3 benchmark, the transition from discriminative DLRMs to Generative RecSys fundamentally shifts the primary hardware bottleneck of the entire system.

Traditional DLRMs are inherently memory-bound, spending vast amounts of time on CPU-side embedding table lookups. Generative models, conversely, are aggressively compute-bound, relying heavily on dense multi-head attention (MHA) passes executing on the GPU. To serve these models efficiently in production, platforms are forced to implement highly sophisticated systems engineering:
Optimization Strategy	Mechanism and Implementation
Context Parallelism & KV Caching

Because recommendation utilizes a streaming time-series setup, deployments cache the Key-Value (KV) states of the user's interaction history (UIH). When scoring new candidates at consecutive timestamps, the system reuses the UIH states, reducing redundant dense computation by 80–90%.
M-FALCON & Microbatched Serving

M-FALCON modifies the causal attention mask so that M candidate items can attend to the shared UIH simultaneously. Because candidates do not attend to one another, the system executes a list-wise ranking step for thousands of items in a single forward pass, heavily relying on NVLink for fast inter-GPU communication.
CPU/GPU Disaggregation

To address low GPU utilization, systems separate feature preprocessing (heavy CPU tasks) from model inference. Preprocessing runs on dedicated CPU nodes, ensuring GPUs focus exclusively on high-speed dense inference, eliminating conversion latency.
Offline-Online Decoupled Reranking

Frameworks like DeGRe (Dense-supervised Generative Reranking) train an autoregressive generator offline using dense lookahead rewards, but utilize highly optimized greedy decoding during online inference to approximate the global optimum without massive beam-search overhead.

Second-Order Implications: Generative Engine Optimization (GEO)

The rise of LLM-native ranking fundamentally alters the digital content ecosystem, precipitating a massive shift from traditional Search Engine Optimization (SEO) to Generative Engine Optimization (GEO).

Traditional SEO optimizes for a "Click-Through" model by manipulating keywords, backlinks, and page structure to rank highly on a page of blue links. Generative ranking models, however, do not output a page of links; they synthesize a direct answer or a highly curated, generated recommendation list. Consequently, the new metric of success is the Share of Model (SoM) or Share of Recommendation (SoR)—the mathematical probability that a brand's data point, product, or content is selected by an LLM as the "Grounding Truth" during its autoregressive synthesis phase.

To optimize for LLM-native ranking, entities must align their digital assets with the statistical priors of the transformer architecture. Because LLMs operate by minimizing perplexity, they heavily favor content with high "Factual Density" (the ratio of explicit entities and facts to stop words) and strict structural coherence. GEO strategies heavily emphasize "Token Injection" and semantic priming—structuring product attributes, Schema.org markup, and semantic anchors explicitly so that when an LLM tokenizer parses the metadata, it easily forms cross-modal synergies with user queries. In this highly semantic environment, manipulating an atomic item ID is functionally impossible; visibility strictly requires structural fluency and semantic density, forcing the model to recognize the entity's relevance natively.
Conclusion

Returning to the foundational inquiry: Is LLM-native ranking simply an application of sequence modeling that maps tokens to embeddings, or is it deeply reliant on multimodal and semantic signal injection?

The comprehensive architectural and empirical evidence dictates that the inclination toward the multimodal and semantic interpretation is unequivocally correct.

While the structural backbone of modern Generative Recommender Systems relies heavily on advanced sequence modeling—evidenced by HSTU's autoregressive sequence transduction, point-wise aggregated attention, and ULTRA-HSTU's semi-local sparse attention—pure sequence modeling of atomic IDs represents a theoretical dead end. ID-only paradigms suffer from insurmountable semantic opacity, cold-start vulnerability, and an inability to generalize to zero-shot, cross-domain scenarios.

True LLM-native ranking is defined by its ability to break free from the constraints of pure collaborative filtering by grounding recommendations in the rich, pre-trained semantic space of foundation models. Architectures like YouTube's PLUM achieve this by fusing visual and textual data into hierarchical Semantic IDs. Frameworks like SynGR mathematically enforce cross-modal reasoning through saliency-aware masking to prevent the model from taking unimodal textual shortcuts. Hybrid models like HSTU-BLaIR prove that injecting contrastive text embeddings directly into the sequence transducer radically improves downstream ranking accuracy. Finally, cutting-edge designs like IDIOMoE demonstrate that foundation models must actively route collaborative "Item-ID dialects" and natural language through entirely different Mixture-of-Experts neural pathways to function without destructive interference.

In summation, LLM-native ranking is not merely a mechanism for processing historical token sequences; it is a holistic, multi-modal reasoning engine. It synthesizes the temporal dynamics of sequential user behavior with the deep textual, visual, and semantic comprehension inherent to Large Language Models, thereby establishing a vastly superior, deeply integrated paradigm for personalized content discovery and ranking.
techrxiv.org
Generative Recommendation: A Survey of Models, Systems, and Industrial Advances | TechRxiv
Opens in a new window
techrxiv.org
Generative Recommendation: A Survey of Models, Systems, and Industrial Advances - TechRxiv
Opens in a new window
researchgate.net
MTGR: Industrial-Scale Generative Recommendation Framework in Meituan
Opens in a new window
arxiv.org
Actions Speak Louder than Words: Trillion-Parameter Sequential Transducers for Generative Recommendations - arXiv
Opens in a new window
arxiv.org
Actions Speak Louder than Words: Trillion-Parameter Sequential Transducers for Generative Recommendations - arXiv
Opens in a new window
alphaxiv.org
Unified Value Alignment for Generative Recommendation in Industrial Advertising | alphaXiv
Opens in a new window
emergentmind.com
Hierarchical Sequential Transduction Unit (HSTU) - Emergent Mind
Opens in a new window
lfaidata.foundation
Leverage LLM for Next-Gen Recommender Systems: Technical Deep Dive into LLM-Enhanced Recommender Architectures
Opens in a new window
genai-personalization.github.io
Towards Large-scale Generative Ranking
Opens in a new window
spheron.network
HSTU Generative Recommenders: Deploy on GPU Cloud (2026) | Spheron Blog
Opens in a new window
arxiv.org
Bending the Scaling Law Curve in Large-Scale Recommendation Systems - arXiv
Opens in a new window
sair.synerise.com
BaseModel vs HSTU for sequential recommendations - Synerise AI/BigData Research
Opens in a new window
rectools.readthedocs.io
Transformers HSTU tutorial - RecTools documentation
Opens in a new window
recommender-systems.com
Attention in RecSys: When Attention Stops Paying for Itself - RS_c
Opens in a new window
mlcommons.org
DLRMv3: Generative recommendation benchmark in MLPerf Inference - MLCommons
Opens in a new window
arxiv.org
Bending the Scaling Law Curve in Large-Scale Recommendation Systems - arXiv
Opens in a new window
emergentmind.com
Semi-Local Attention Mechanism - Emergent Mind
Opens in a new window
alphaxiv.org
Unleashing the Native Recommendation Potential: LLM-Based Generative Recommendation via Structured Term Identifiers | alphaXiv
Opens in a new window
arxiv.org
Catalog-Native LLM: Speaking Item-ID dialect with Less Entanglement for Recommendation
Opens in a new window
arxiv.org
[2510.05125] Catalog-Native LLM: Speaking Item-ID Dialect with Less Entanglement for Recommendation - arXiv
Opens in a new window
eugeneyan.com
Improving Recommendation Systems & Search in the Age of LLMs - Eugene Yan
Opens in a new window
arxiv.org
GR-LLMs: Recent Advances in Generative Recommendation Based on Large Language Models - arXiv
Opens in a new window
andydong.com
Andy Dong's Personal Website
Opens in a new window
techrxiv.org
A Survey of Item Identifiers in Generative Recommendation - TechRxiv
Opens in a new window
arxiv.org
[2512.21543] CEMG: Collaborative-Enhanced Multimodal Generative Recommendation
Opens in a new window
arxiv.org
PLUM: Adapting Pre-trained Language Models for Industrial-scale Generative Recommendations - arXiv
Opens in a new window
chatpaper.com
PLUM: Adapting Pre-trained Language Models for Industrial-scale Generative Recommendations - ChatPaper
Opens in a new window
alphaxiv.org
Unleashing the Native Recommendation Potential: LLM-Based Generative Recommendation via Structured Term Identifiers | alphaXiv
Opens in a new window
arxiv.org
SynGR: Unleashing the Potential of Cross-Modal Synergy for Generative Recommendation
Opens in a new window
arxiv.org
SynGR: Unleashing the Potential of Cross-Modal Synergy for Generative Recommendation - arXiv
Opens in a new window
themoonlight.io
[Literature Review] SynGR: Unleashing the Potential of Cross-Modal Synergy for Generative Recommendation - Moonlight
Opens in a new window
github.com
HSTU-BLaIR: Lightweight Contrastive Text Embedding for Generative Recommender - GitHub
Opens in a new window
arxiv.org
HSTU-BLaIR: Lightweight Contrastive Text Embedding for Generative Recommender - arXiv
Opens in a new window
arxiv.org
HSTU-BLaIR: Lightweight Contrastive Text Embedding for Generative Recommender - arXiv
Opens in a new window
arxiv.org
Bridging Language and Items for Retrieval and Recommendation - arXiv
Opens in a new window
arxiv.org
HSTU-BLaIR: Lightweight Contrastive Text Embedding for Generative Recommender - arXiv
Opens in a new window
catalyzex.com
Ruidong Han - CatalyzeX
Opens in a new window
arxiv.org
MTGR: Industrial-Scale Generative Recommendation Framework in Meituan - arXiv
Opens in a new window
arxiv.org
MTGR: Industrial-Scale Generative Recommendation Framework in Meituan - arXiv
Opens in a new window
arxiv.org
[2505.18654] MTGR: Industrial-Scale Generative Recommendation Framework in Meituan
Opens in a new window
arxiv.org
Query-Mixed Interest Extraction and Heterogeneous Interaction: A Scalable CTR Model for Industrial Recommender Systems - arXiv
Opens in a new window
alphaxiv.org
MTFM: A Scalable and Alignment-free Foundation Model for Industrial Recommendation in Meituan | alphaXiv
Opens in a new window
arxiv.org
Agentic Recommender System with Hierarchical Belief-State Memory - arXiv
Opens in a new window
arxiv.org
Agentic Recommender System with Hierarchical Belief-State Memory - arXiv
Opens in a new window
arxiv.org
An LLM-powered Agentic Recommendation System for Connected TV Content Discovery
Opens in a new window
uber.com
Next-Gen Restaurant Recommendation with Generative Modeling and Real-Time Features
Opens in a new window
researchgate.net
DeGRe: Dense-supervised Generative Reranking for Recommendation - ResearchGate
Opens in a new window
trendeetech.com
LLM-Native GEO: The Ultimate Guide to Generative Engine Optimization (2026) - Trendee
Opens in a new window
reddit.com
Is product-level GEO different from website-level GEO? We built a prototype to test this. : r/GEO_optimization - Reddit
Opens in a new window
lexingtonchronicle.com
Demystifying structured data: How to speak an LLM's native language | Lexington County Chronicle
Opens in a new window
github.com
meta-recsys/generative-recommenders: Repository hosting code for "Actions Speak Louder than Words: Trillion-Parameter Sequential Transducers for Generative Recommendations" (https://arxiv.org/abs/2402.17152). · GitHub - GitHub
Opens in a new window
youtube.com
Generative Recommendation Systems Explained - HSTU & Trillion-Parameter Transformers (2024 Paper) - YouTube
Opens in a new window
arxiv.org
MMREC: LLM Based Multi-Modal Recommender System - arXiv
Opens in a new window
medium.com
LLMs as Retrieval and Recommendation Engines — Part 1 | by Moein Hasani | Medium
Opens in a new window
dblp.org
MTGR: Industrial-Scale Generative Recommendation Framework in Meituan. - DBLP
Opens in a new window
arxiv.org
From Hidden Profiles to Governable Personalization: Recommender Systems in the Age of LLM Agents - arXiv
Opens in a new window
netflixtechblog.com
Towards Generalizable and Efficient Large-Scale Generative Recommenders
Opens in a new window
emerald.com
Recommendation with generative models | Foundations and Trends in Information Retrieval
Opens in a new window
producthunt.com
IKI.AI: LLM-native space for professional knowledge - Product Hunt
Opens in a new window
towardsdatascience.com
Grounding LLMs with Fresh Web Data to Reduce Hallucinations | Towards Data Science
Opens in a new window
sona.com
Best LLM Competitor Analysis Tools in 2026 (Compared) - Sona
Opens in a new window
arxiv.org
GR-LLMs: Recent Advances in Generative Recommendation Based on Large Language Models - arXiv
Opens in a new window
earl-workshop.github.io
A Metric for MLLM Alignment in Large-scale Recommendation - EARL Workshop
Opens in a new window
researchgate.net
MTGR: Industrial-Scale Generative Recommendation Framework in Meituan
Opens in a new window
emergentmind.com
ULTRA-HSTU: Generative Transduction Model - Emergent Mind
Opens in a new window
arxiv.org
[2602.16986] Bending the Scaling Law Curve in Large-Scale Recommendation Systems
Opens in a new window
researchgate.net
Fuwei Zhang's research works | Beihang University and other places - ResearchGate
Opens in a new window
arxiv.org
[2605.18920] SynGR: Unleashing the Potential of Cross-Modal Synergy for Generative Recommendation - arXiv
Opens in a new window
openreview.net
SynGR: Unleashing the Potential of Cross-Modal Synergy for Generative Recommendation
Opens in a new window
github.com
GitHub - hyp1231/AmazonReviews2023: Scripts for processing the Amazon Reviews 2023 dataset; implementations and checkpoints of BLaIR: "Bridging Language and Items for Retrieval and Recommendation".
Opens in a new window
pubmed.ncbi.nlm.nih.gov
a qualitative meta-synthesis of patient experience in the emergency department - PubMed
Opens in a new window
pubmed.ncbi.nlm.nih.gov
Network meta-analyses and treatment recommendations for obsessive-compulsive disorder
Opens in a new window
rezashkv.github.io
Publications - Reza Shirkavand
Opens in a new window
about.roblox.com
Publications - Roblox
Opens in a new window
scholar.google.com
‪Reza Shirkavand‬ - ‪Google Scholar‬
Opens in a new window
openreview.net
Reza Shirkavand | OpenReview
Opens in a new window
openreview.net
Multimodal Quantitative Language for Generative Recommendation | OpenReview
Opens in a new window
arxiv.org
[2602.03713] Multimodal Generative Recommendation for Fusing Semantic and Collaborative Signals - arXiv
Opens in a new window
openreview.net
Multimodal Generative Recommendation for Fusing Semantic and Collaborative Signals
Opens in a new window
emergentmind.com
Multimodal Generative Recommendation (MGR) - Emergent Mind
Opens in a new window
benchlm.ai
Best LLMs for Multimodal & Grounded — July 2026 Leaderboard | BenchLM.ai
Opens in a new window
llm-stats.com
AI Leaderboard 2026: Compare & Rank 300+ Top AI Models by Intelligence, Speed & Price
Opens in a new window
whatllm.org
Best Vision & Multimodal LLMs January 2026 | AI Image Understanding Ranked - WhatLLM
Opens in a new window
cseweb.ucsd.edu
Preference-Optimized Retrieval and Ranking for Efficient Multimodal Recommendation - Computer Science
Opens in a new window
ofox.ai
Best Vision LLM in 2026 — Multimodal Models Ranked - Ofox AI
Opens in a new window
stackai.com
LLM Leaderboard: Which LLMs are Best for Which Tasks? (2026) - StackAI
Opens in a new window
frontiersin.org
RoLLMRec: a robust LLM-based recommender system for defending against shilling and prompt injection attacks - Frontiers
Opens in a new window
emergentmind.com
LLM-as-RS: Unifying LLMs in Recommender Systems - Emergent Mind
Opens in a new window
yifanqian.com
Figures as Interfaces: Toward LLM-Native Artifacts for Scientific Discovery - Yifan Qian
Opens in a new window
arxiv.org
DecisionLLM: Large Language Models for Long Sequence Decision Exploration - arXiv
Opens in a new window
kumo.ai
Why LLMs Fail on Structured Data (And What Works Instead) - Kumo.ai
Opens in a new window
pmc.ncbi.nlm.nih.gov
Knowledge-grounded large language model for personalized sports training plan generation - PMC
Opens in a new window
arxiv.org
Break the ID-Language Barrier: An Adaption Framework for LLM-based Sequential Recommendation - arXiv
Opens in a new window
emergentmind.com
RankGPT (GenRank): Generative Ranking Models - Emergent Mind
Opens in a new window
semanticscholar.org
[PDF] Towards Large-scale Generative Ranking - Semantic Scholar
Opens in a new window
arxiv.org
Towards Large-scale Generative Ranking - arXiv
Opens in a new window
ziprecruiter.com
$15-$36/hr Research Lab Jobs Jobs (NOW HIRING) May 2026
Opens in a new window
youtube.com
PLUM: Adapting Pre-trained LLMs for YouTube-Scale Generative Recommendations
Opens in a new window
arxiv.org
[2510.07784] PLUM: Adapting Pre-trained Language Models for Industrial-scale Generative Recommendations - arXiv
Opens in a new window
plumproductionsmedia.com
How to Setup YouTube Channel for Business - Plum Productions
Opens in a new window
apps.apple.com
Plum Recipe Saver - App Store - Apple
Opens in a new window
github.com
RecSysPapers/README_EN.md at main - GitHub
Opens in a new window
arxiv.org
RankGR: Rank-Enhanced Generative Retrieval with Listwise Direct Preference Optimization in Recommendation - arXiv
Opens in a new window
arxiv.org
RankGR: Rank-Enhanced Generative Retrieval with Listwise Direct Preference Optimization in Recommendation - arXiv
Opens in a new window
arxiv.org
UniPinRec: Unifying Generative Retrieval and Ranking at Pinterest Scale - arXiv
Opens in a new window
arxiv.org
[2505.04180] Towards Large-scale Generative Ranking - arXiv
Opens in a new window
themoonlight.io
[Literature Review] Towards Large-scale Generative Ranking - Moonlight
Opens in a new window
appvertiser.ai
LLMs Are Replacing Ad Ranking Models — What It Means for
Opens in a new window
primaryposition.com
The Truths in LLM Marketing - Primary Position SEO
Opens in a new window
arxiv.org
MTFM: A Scalable and Alignment-free Foundation Model for Industrial Recommendation in Meituan - arXiv
Opens in a new window
researchgate.net
Ruidong Han's research works - ResearchGate
Opens in a new window
github.com
Request: Open-source SLA kernel and ULTRA-HSTU co-design components #481 - GitHub
Opens in a new window
github.com
Releases · alibaba/TorchEasyRec - GitHub
Opens in a new window
huggingface.co
Daily Papers - Hugging Face
Opens in a new window
Uncovering LLM-Native Paradigms
I am initiating a deep dive into the emerging landscape of LLM-native ranking and recommendation systems. My initial analysis reveals a fascinating dichotomy in how the industry and research communities define this space. On one hand, there is a strong focus on sequence modeling architectures—such as Meta's Hierarchical Sequential Transformer Unit (HSTU)—which adapt transformer-based sequence modeling specifically for user behavioral sequences. On the other hand, a highly disruptive paradigm is emerging around generative LLMs that process rich text tokens while seamlessly integrating non-conventional, heterogeneous signals like multimodal content, continuous dense features, and collaborative filtering IDs.
Mapping the Architecture Gap
A key challenge I want to address is understanding how generative text models reconcile discrete token vocabulary with dense, continuous physical features and behavioral embedding representations. Traditional recommender systems excel at processing continuous tabular data, whereas standard LLMs are natively optimized for discrete language tokens. Resolving how modern architectures bridge this gap to inject multimodal and continuous signals directly into the generative ranking process is central to this investigation.
Formulating the Retrieval Strategy
To synthesize these paradigms, I am launching targeted searches across recent machine learning and recommender systems literature (including RecSys, KDD, and arXiv). My immediate focus is to gather deep technical documentation on HSTU's architecture alongside state-of-the-art frameworks that inject continuous and multimodal features directly into generative ranking models. This will allow me to contrast sequence-focused approaches with feature-rich generative architectures.
appvertiser.ai
LLMs Are Replacing Ad Ranking Models — What It Means for
arxiv.org
Agentic Recommender System with Hierarchical Belief-State Memory - arXiv
andydong.com
Andy Dong's Personal Website
arxiv.org
Agentic Recommender System with Hierarchical Belief-State Memory - arXiv
reddit.com
Is product-level GEO different from website-level GEO? We built a prototype to test this. : r/GEO_optimization - Reddit
primaryposition.com
The Truths in LLM Marketing - Primary Position SEO
spheron.network
HSTU Generative Recommenders: Deploy on GPU Cloud (2026) | Spheron Blog
arxiv.org
Bending the Scaling Law Curve in Large-Scale Recommendation Systems - arXiv
sair.synerise.com
BaseModel vs HSTU for sequential recommendations - Synerise AI/BigData Research
arxiv.org
Actions Speak Louder than Words: Trillion-Parameter Sequential Transducers for Generative Recommendations - arXiv
github.com
meta-recsys/generative-recommenders: Repository hosting code for "Actions Speak Louder than Words: Trillion-Parameter Sequential Transducers for Generative Recommendations" (https://arxiv.org/abs/2402.17152). · GitHub - GitHub
rectools.readthedocs.io
Transformers HSTU tutorial - RecTools documentation
emergentmind.com
Hierarchical Sequential Transduction Unit (HSTU) - Emergent Mind
arxiv.org
Actions Speak Louder than Words: Trillion-Parameter Sequential Transducers for Generative Recommendations - arXiv
youtube.com
Generative Recommendation Systems Explained - HSTU & Trillion-Parameter Transformers (2024 Paper) - YouTube
eugeneyan.com
Improving Recommendation Systems & Search in the Age of LLMs - Eugene Yan
techrxiv.org
Generative Recommendation: A Survey of Models, Systems, and Industrial Advances | TechRxiv
arxiv.org
MMREC: LLM Based Multi-Modal Recommender System - arXiv
arxiv.org
GR-LLMs: Recent Advances in Generative Recommendation Based on Large Language Models - arXiv
lfaidata.foundation
Leverage LLM for Next-Gen Recommender Systems: Technical Deep Dive into LLM-Enhanced Recommender Architectures
medium.com
LLMs as Retrieval and Recommendation Engines — Part 1 | by Moein Hasani | Medium
Uncovering Generative Paradigms
In synthesizing the latest research on next-generation architectures, I have mapped out a core tension between two distinct paradigms of generative recommendation and ranking. The first paradigm, epitomized by Meta's Hierarchical Sequential Transduction Unit, treats recommendation purely as a sequence transduction task. It chronologically aligns user behaviors and categorical metadata as non-textual tokens, transforming them into embeddings to autoregressively predict subsequent interactions. This approach adapts structural transformer mechanisms (like pointwise attention and relative biases) directly to structured interaction data, making it highly efficient for massive, non-stationary streaming contexts.
Integrating Multimodal Context
The second paradigm relies more heavily on language-grounded foundation models. This approach processes traditional text tokens alongside non-conventional signals, such as images, video, and dense user-interest summaries. Rather than relying solely on abstract item IDs, these systems align visual and textual modalities into a unified latent space, often leveraging cross-modal contrastive objectives to preserve both semantic nuances and behavioral patterns. This hybrid approach significantly reduces cold-start issues by allowing the system to reason over rich, multi-sensory item details.
Investigating Real-World Implementations
I am thinking through how top-tier industrial systems bridge the gap between behavioral sequence modeling and rich multimodal representations. To resolve how these systems inject complex continuous features and cross-features without bottlenecking live performance, I will explore recent large-scale implementations, specifically focusing on Meituan's generative recommendation frameworks and similar end-to-end industrial architectures.
researchgate.net
MTGR: Industrial-Scale Generative Recommendation Framework in Meituan
catalyzex.com
Ruidong Han - CatalyzeX
arxiv.org
MTGR: Industrial-Scale Generative Recommendation Framework in Meituan - arXiv
techrxiv.org
Generative Recommendation: A Survey of Models, Systems, and Industrial Advances - TechRxiv
dblp.org
MTGR: Industrial-Scale Generative Recommendation Framework in Meituan. - DBLP
arxiv.org
[2505.18654] MTGR: Industrial-Scale Generative Recommendation Framework in Meituan
frontiersin.org
RoLLMRec: a robust LLM-based recommender system for defending against shilling and prompt injection attacks - Frontiers
alphaxiv.org
Unleashing the Native Recommendation Potential: LLM-Based Generative Recommendation via Structured Term Identifiers | alphaXiv
arxiv.org
Catalog-Native LLM: Speaking Item-ID dialect with Less Entanglement for Recommendation
pmc.ncbi.nlm.nih.gov
Knowledge-grounded large language model for personalized sports training plan generation - PMC
arxiv.org
From Hidden Profiles to Governable Personalization: Recommender Systems in the Age of LLM Agents - arXiv
arxiv.org
SynGR: Unleashing the Potential of Cross-Modal Synergy for Generative Recommendation
uber.com
Next-Gen Restaurant Recommendation with Generative Modeling and Real-Time Features
emergentmind.com
Multimodal Generative Recommendation (MGR) - Emergent Mind
techrxiv.org
Generative Recommendation: A Survey of Models, Systems, and Industrial Advances | TechRxiv
netflixtechblog.com
Towards Generalizable and Efficient Large-Scale Generative Recommenders
emerald.com
Recommendation with generative models | Foundations and Trends in Information Retrieval
arxiv.org
An LLM-powered Agentic Recommendation System for Connected TV Content Discovery
producthunt.com
IKI.AI: LLM-native space for professional knowledge - Product Hunt
towardsdatascience.com
Grounding LLMs with Fresh Web Data to Reduce Hallucinations | Towards Data Science
trendeetech.com
LLM-Native GEO: The Ultimate Guide to Generative Engine Optimization (2026) - Trendee
sona.com
Best LLM Competitor Analysis Tools in 2026 (Compared) - Sona
Unification of Sequence and Semantic Paradigms
Through a comprehensive synthesis of recent industrial breakthroughs and academic surveys, I have discovered that the definition of LLM-native ranking is rapidly converging. It is not a strict choice between pure sequence modeling over behavioral IDs and semantic text-based generation; rather, modern architectures are unifying both. Industrial giants are actively replacing multi-stage pipelines with single-model generative frameworks that marry the sequential depth of transformers with the open-world knowledge and multi-modal alignment capabilities of large language models.
Bridging the Feature and Modality Gap
A critical contradiction I am resolving is how these models retain highly optimized, hand-crafted cross-features and continuous signals without sacrificing the scalability of generative architectures. For instance, recent frameworks like Meituan's MTGR demonstrate how to reorganize both user and candidate profiles into distinct token sequences, successfully feeding traditional deep learning recommendation features directly into sequential transducers. Furthermore, emerging cross-modal models show how to actively mitigate modality dominance—where text tokens normally overshadow visual or continuous features—by enforcing cross-modal synergy constraints during next-item prediction.
Deep Document Analysis and Verification
To solidify these insights with precise architectural details, I am transitioning to a deeper phase of document verification. I will be directly accessing and analyzing the underlying literature for key frameworks, including the Hierarchical Sequential Transduction Unit (HSTU), MTGR's feature tokenization schemes, and synergistic multimodal models. This will allow me to map out the exact mathematics and engineering principles used to inject continuous, non-conventional, and multimodal signals into generative ranking pipelines.
reddit.com
Is product-level GEO different from website-level GEO? We built a prototype to test this. : r/GEO_optimization - Reddit
appvertiser.ai
LLMs Are Replacing Ad Ranking Models — What It Means for
primaryposition.com
The Truths in LLM Marketing - Primary Position SEO
techrxiv.org
A Survey of Item Identifiers in Generative Recommendation - TechRxiv
arxiv.org
GR-LLMs: Recent Advances in Generative Recommendation Based on Large Language Models - arXiv
techrxiv.org
Generative Recommendation: A Survey of Models, Systems, and Industrial Advances | TechRxiv
arxiv.org
GR-LLMs: Recent Advances in Generative Recommendation Based on Large Language Models - arXiv
earl-workshop.github.io
A Metric for MLLM Alignment in Large-scale Recommendation - EARL Workshop
alphaxiv.org
Unified Value Alignment for Generative Recommendation in Industrial Advertising | alphaXiv
arxiv.org
arxiv.org
arxiv.org
Unification of Value and Alignment
In analyzing the latest industrial shifts, I have observed a major evolution where generative recommendations are expanding beyond pure user-interest prediction to incorporate commercial value. Emerging frameworks are successfully embedding monetization signals, such as expected cost-per-mille, directly into the generative decoding process. Rather than treating financial utility as a post-hoc filter, modern models utilize joint optimization heads and reinforcement learning to combine semantic relevance and value metrics directly during item-token generation.
Bridging Semantic and ID Bottlenecks
I am synthesizing how industrial systems navigate the representation bottleneck between language-based and structural-ID recommendation. While traditional discriminative systems treat item IDs as isolated variables, generative frameworks are leveraging structured semantic IDs and preference-aligned data to enable compositional reasoning over product attributes. To assess alignment quality without the prohibitive computational cost of live A/B testing, researchers are developing clever offline metrics that measure the performance upper-bounds of multimodal representation integration.
Resolving Architectural Integration Mechanics
To deeply understand the structural mechanics of these hybrid architectures, I am focusing my next steps on investigating how large-scale industrial frameworks integrate hand-crafted cross-features and continuous dense features alongside sequential transformer modeling. I will execute targeted searches on prominent industrial implementations to extract technical specifications regarding their feature-fusion techniques and model-scaling characteristics.
researchgate.net
MTGR: Industrial-Scale Generative Recommendation Framework in Meituan
arxiv.org
MTFM: A Scalable and Alignment-free Foundation Model for Industrial Recommendation in Meituan - arXiv
techrxiv.org
Generative Recommendation: A Survey of Models, Systems, and Industrial Advances - TechRxiv
arxiv.org
MTGR: Industrial-Scale Generative Recommendation Framework in Meituan - arXiv
researchgate.net
MTGR: Industrial-Scale Generative Recommendation Framework in Meituan
arxiv.org
[2505.18654] MTGR: Industrial-Scale Generative Recommendation Framework in Meituan
arxiv.org
Bending the Scaling Law Curve in Large-Scale Recommendation Systems - arXiv
arxiv.org
Bending the Scaling Law Curve in Large-Scale Recommendation Systems - arXiv
emergentmind.com
ULTRA-HSTU: Generative Transduction Model - Emergent Mind
arxiv.org
[2602.16986] Bending the Scaling Law Curve in Large-Scale Recommendation Systems
recommender-systems.com
Attention in RecSys: When Attention Stops Paying for Itself - RS_c
github.com
Request: Open-source SLA kernel and ULTRA-HSTU co-design components #481 - GitHub
arxiv.org
SynGR: Unleashing the Potential of Cross-Modal Synergy for Generative Recommendation
arxiv.org
SynGR: Unleashing the Potential of Cross-Modal Synergy for Generative Recommendation - arXiv
themoonlight.io
[Literature Review] SynGR: Unleashing the Potential of Cross-Modal Synergy for Generative Recommendation - Moonlight
researchgate.net
Fuwei Zhang's research works | Beihang University and other places - ResearchGate
arxiv.org
[2605.18920] SynGR: Unleashing the Potential of Cross-Modal Synergy for Generative Recommendation - arXiv
openreview.net
SynGR: Unleashing the Potential of Cross-Modal Synergy for Generative Recommendation
catalyzex.com
Ruidong Han - CatalyzeX
arxiv.org
MTGR: Industrial-Scale Generative Recommendation Framework in Meituan - arXiv
Uncovering Architectural Breakthroughs
Through a rigorous synthesis of the latest industrial literature, I have uncovered how top-tier platforms are pushing the boundaries of sequential transduction. Highly scaled architectures are now shifting away from dense, standard self-attention mechanisms to bend the efficiency curve. I observed that next-generation models utilize semi-local attention designs—consisting of highly localized windows and global historical anchors—to successfully capture both high-fidelity immediate intent and aggregate long-term user patterns. Furthermore, leading implementations are utilizing layer truncation strategies, running deep computation only on the most recent slice of user history, which dramatically reduces the computational overhead of processing ultra-long sequences.
Resolving the Multimodal Shortcut Dilemma
A key challenge I am resolving is the 'synergy gap' in generative models that attempt to merge multimodal and text signals. Because textual data is semantically denser than visual or audio signals, standard generative models suffer from a form of cognitive laziness, taking a 'shortcut' by relying almost entirely on text tokens while ignoring other rich modalities. To solve this contradiction, cutting-edge frameworks are introducing saliency-aware masking mechanisms. By identifying and dynamically masking the dominant modality during training, the model is forced to utilize cross-modal reasoning, successfully capturing emergent, higher-order item properties—such as brand prestige—that cannot be inferred from any single modality alone.
Mapping Hybrid Engineering Solutions
I am also analyzing the systems-level innovations that make these native architectures viable at scale. For instance, rather than replacing traditional deep learning recommendation features, modern frameworks are converting complex tabular data, user demographics, and hand-crafted cross-features directly into structured, heterogeneous token sequences. These sequences are processed using specialized group-layer normalization to stabilize embeddings across disparate semantic spaces, alongside dynamic masking pipelines that strictly enforce temporal causality. This allows the model to scale cleanly under established power laws while retaining the precise predictive power of legacy systems.
Formulating the Synthesis Strategy
To complete this deep-dive investigation, I am now thinking through how to structure a comprehensive taxonomy that addresses both paradigms of native ranking. I will contrast structural sequence transduction over behavior IDs with semantic generative models that speak rich text and multimodal dialects. My next steps will focus on organizing these technical insights into an in-depth framework, evaluating the trade-offs of each paradigm, and explaining how modern systems successfully inject non-conventional signals into generative ranking pipelines.
github.com
HSTU-BLaIR: Lightweight Contrastive Text Embedding for Generative Recommender - GitHub
arxiv.org
Bridging Language and Items for Retrieval and Recommendation - arXiv
arxiv.org
HSTU-BLaIR: Lightweight Contrastive Text Embedding for Generative Recommender - arXiv
github.com
GitHub - hyp1231/AmazonReviews2023: Scripts for processing the Amazon Reviews 2023 dataset; implementations and checkpoints of BLaIR: "Bridging Language and Items for Retrieval and Recommendation".
pubmed.ncbi.nlm.nih.gov
a qualitative meta-synthesis of patient experience in the emergency department - PubMed
pubmed.ncbi.nlm.nih.gov
Network meta-analyses and treatment recommendations for obsessive-compulsive disorder
arxiv.org
Catalog-Native LLM: Speaking Item-ID dialect with Less Entanglement for Recommendation
rezashkv.github.io
Publications - Reza Shirkavand
arxiv.org
[2510.05125] Catalog-Native LLM: Speaking Item-ID Dialect with Less Entanglement for Recommendation - arXiv
about.roblox.com
Publications - Roblox
scholar.google.com
‪Reza Shirkavand‬ - ‪Google Scholar‬
openreview.net
Reza Shirkavand | OpenReview
openreview.net
Multimodal Quantitative Language for Generative Recommendation | OpenReview
arxiv.org
[2602.03713] Multimodal Generative Recommendation for Fusing Semantic and Collaborative Signals - arXiv
techrxiv.org
Generative Recommendation: A Survey of Models, Systems, and Industrial Advances | TechRxiv
openreview.net
Multimodal Generative Recommendation for Fusing Semantic and Collaborative Signals
emergentmind.com
Multimodal Generative Recommendation (MGR) - Emergent Mind
arxiv.org
[2512.21543] CEMG: Collaborative-Enhanced Multimodal Generative Recommendation
benchlm.ai
Best LLMs for Multimodal & Grounded — July 2026 Leaderboard | BenchLM.ai
llm-stats.com
AI Leaderboard 2026: Compare & Rank 300+ Top AI Models by Intelligence, Speed & Price
whatllm.org
Best Vision & Multimodal LLMs January 2026 | AI Image Understanding Ranked - WhatLLM
cseweb.ucsd.edu
Preference-Optimized Retrieval and Ranking for Efficient Multimodal Recommendation - Computer Science
ofox.ai
Best Vision LLM in 2026 — Multimodal Models Ranked - Ofox AI
stackai.com
LLM Leaderboard: Which LLMs are Best for Which Tasks? (2026) - StackAI
Uncovering Architectural Dialects
In thinking through the technical definition of LLM-native ranking, I have uncovered a major architectural shift that bridges the gap between opaque behavioral signals and rich natural language. A primary challenge in this space is that item identifiers are traditionally token-efficient but semantically empty, whereas language models are rich in semantics but struggle to capture implicit behavioral patterns. Through deep synthesis of the latest literature, I analyzed how state-of-the-art frameworks resolve this by treating user interaction histories as a 'native dialect' within the language space. This is achieved by decoupling text and item processing within the model's core layers, preventing destructive interference and allowing collaborative filters to speak the same language as textual metadata.
Resolving the Multimodal Dominance Problem
I have identified and analyzed a critical bottleneck in generative recommendation systems where text features naturally overshadow other sensory inputs. To resolve this modality-dominance issue, next-generation architectures are incorporating self-supervised quantization learning for images alongside text. New frameworks are aligning visual and textual representations into unified semantic codes using residual quantization. This allows the generator to process distinct modalities, such as product images and user reviews, as cohesive token sequences. Consequently, the model can perform constrained sequence learning, restricting its output generation to permissible real-world catalog items while accounting for multi-faceted user preferences.
Formulating Unified Retrieval and Ranking Pipelines
To build a complete picture of these systems, I am focusing my next actions on analyzing how retrieval and ranking stages are optimized end-to-end. I am investigating preference-optimized frameworks where a lightweight retriever is dynamically updated using feedback loops from a multimodal ranker. I will look deeper into how these models leverage verbalizer-based inference to compute ranking scores in a single forward pass, eliminating the high latency of autoregressive generation while preserving the reasoning capabilities of large-scale foundation models.
frontiersin.org
RoLLMRec: a robust LLM-based recommender system for defending against shilling and prompt injection attacks - Frontiers
arxiv.org
An LLM-powered Agentic Recommendation System for Connected TV Content Discovery
emergentmind.com
LLM-as-RS: Unifying LLMs in Recommender Systems - Emergent Mind
lexingtonchronicle.com
Demystifying structured data: How to speak an LLM's native language | Lexington County Chronicle
yifanqian.com
Figures as Interfaces: Toward LLM-Native Artifacts for Scientific Discovery - Yifan Qian
trendeetech.com
LLM-Native GEO: The Ultimate Guide to Generative Engine Optimization (2026) - Trendee
arxiv.org
DecisionLLM: Large Language Models for Long Sequence Decision Exploration - arXiv
kumo.ai
Why LLMs Fail on Structured Data (And What Works Instead) - Kumo.ai
pmc.ncbi.nlm.nih.gov
Knowledge-grounded large language model for personalized sports training plan generation - PMC
alphaxiv.org
Unleashing the Native Recommendation Potential: LLM-Based Generative Recommendation via Structured Term Identifiers | alphaXiv
arxiv.org
Catalog-Native LLM: Speaking Item-ID dialect with Less Entanglement for Recommendation
arxiv.org
Break the ID-Language Barrier: An Adaption Framework for LLM-based Sequential Recommendation - arXiv
mlcommons.org
DLRMv3: Generative recommendation benchmark in MLPerf Inference - MLCommons
emergentmind.com
RankGPT (GenRank): Generative Ranking Models - Emergent Mind
genai-personalization.github.io
Towards Large-scale Generative Ranking
techrxiv.org
Generative Recommendation: A Survey of Models, Systems, and Industrial Advances | TechRxiv
semanticscholar.org
[PDF] Towards Large-scale Generative Ranking - Semantic Scholar
arxiv.org
Towards Large-scale Generative Ranking - arXiv
arxiv.org
Agentic Recommender System with Hierarchical Belief-State Memory - arXiv
arxiv.org
Agentic Recommender System with Hierarchical Belief-State Memory - arXiv
primaryposition.com
The Truths in LLM Marketing - Primary Position SEO
ziprecruiter.com
$15-$36/hr Research Lab Jobs Jobs (NOW HIRING) May 2026
Uncovering High-Cardinality Paradigms
I am synthesizing a critical structural divide between two dominant paradigms of next-generation ranking. The first paradigm bypasses natural language altogether, reformulating recommendation as sequential transduction directly over high-cardinality item catalogs and dense behavioral IDs. Rather than employing a text tokenizer, these models utilize the core mathematical architecture of large models—specifically causal self-attention, next-item autoregressive objectives, and power-law scaling—to process structured interaction logs. This approach allows industrial systems to scale to trillions of parameters while maintaining the microsecond latencies required for live, late-stage ranking.
Resolving Collaborative-Semantic Friction
I am evaluating how the second paradigm, which centers on text-based foundation models, solves the inherent friction between semantically rich language tokens and opaque collaborative filtering signals. When trained purely on text, generative models often struggle to capture implicit user preferences. To resolve this contradiction, cutting-edge architectures are utilizing modular expert routing. By splitting the model's feedforward layers into specialized text experts and catalog-ID experts, these systems can ingest continuous behavioral embeddings without degrading the model's native natural language reasoning capabilities.
Mapping the Search Strategy
To complete this architectural mapping, I am thinking through how to verify these design principles against real-world, large-scale deployments. I will focus my next actions on examining how major consumer platforms implement structured item identifiers, such as semantic and keyword-based codes, to bridge the gap between abstract item databases and generative text spaces. I am launching targeted searches to extract the precise technical specifications of these hybrid indexing and representation methods.
arxiv.org
PLUM: Adapting Pre-trained Language Models for Industrial-scale Generative Recommendations - arXiv
chatpaper.com
PLUM: Adapting Pre-trained Language Models for Industrial-scale Generative Recommendations - ChatPaper
youtube.com
PLUM: Adapting Pre-trained LLMs for YouTube-Scale Generative Recommendations
arxiv.org
[2510.07784] PLUM: Adapting Pre-trained Language Models for Industrial-scale Generative Recommendations - arXiv
plumproductionsmedia.com
How to Setup YouTube Channel for Business - Plum Productions
apps.apple.com
Plum Recipe Saver - App Store - Apple
github.com
RecSysPapers/README_EN.md at main - GitHub
arxiv.org
RankGR: Rank-Enhanced Generative Retrieval with Listwise Direct Preference Optimization in Recommendation - arXiv
arxiv.org
RankGR: Rank-Enhanced Generative Retrieval with Listwise Direct Preference Optimization in Recommendation - arXiv
techrxiv.org
Generative Recommendation: A Survey of Models, Systems, and Industrial Advances | TechRxiv
arxiv.org
UniPinRec: Unifying Generative Retrieval and Ranking at Pinterest Scale - arXiv
mlcommons.org
DLRMv3: Generative recommendation benchmark in MLPerf Inference - MLCommons
genai-personalization.github.io
Towards Large-scale Generative Ranking
arxiv.org
[2505.04180] Towards Large-scale Generative Ranking - arXiv
themoonlight.io
[Literature Review] Towards Large-scale Generative Ranking - Moonlight
appvertiser.ai
LLMs Are Replacing Ad Ranking Models — What It Means for
reddit.com
Is product-level GEO different from website-level GEO? We built a prototype to test this. : r/GEO_optimization - Reddit
primaryposition.com
The Truths in LLM Marketing - Primary Position SEO
Uncovering Generative Co-Design
In synthesizing the latest industrial breakthroughs, I have analyzed how leading platforms are collapsing the traditional wall between candidate retrieval and ranking. I observed that instead of deploying separate models optimized for different objectives, unified generative frameworks are successfully executing both ranking and retrieval within a single model architecture. For instance, recent large-scale implementations demonstrate how introducing a shared generative backbone can yield denser per-position gradients, which dramatically improves ranking precision while simultaneously matching or exceeding the recall performance of highly optimized production baselines.
Resolving Tokenization and Quantization Bottlenecks
I am resolving a core contradiction in generative retrieval: while predicting raw item identifiers directly is highly efficient, it prevents the model from understanding semantic similarities between items. To overcome this limitation, I analyzed how state-of-the-art frameworks leverage advanced semantic ID tokenization. By combining multi-modal content embeddings with user behavioral signals, these architectures use hierarchical residual quantization to transform items into structured token sequences. This allows a decoder-only model to autoregressively generate recommendation paths that bypass legacy dot-product embedding bottlenecks, scaling cleanly to billions of users on highly dynamic platforms like YouTube.
Formulating the Final Architectural Analysis
To conclude this comprehensive investigation, I am transitioning to synthesizing my findings into a definitive taxonomy. I will structure a detailed evaluation contrasting sequence-based transducers with language-grounded generative rankers. My final steps will focus on organizing these technical insights to detail how industrial-scale architectures successfully reconcile discrete semantic tokens with rich, continuous tabular features while maintaining strict real-time serving constraints.
arxiv.org
MTFM: A Scalable and Alignment-free Foundation Model for Industrial Recommendation in Meituan - arXiv
researchgate.net
Ruidong Han's research works - ResearchGate
researchgate.net
MTGR: Industrial-Scale Generative Recommendation Framework in Meituan
arxiv.org
MTGR: Industrial-Scale Generative Recommendation Framework in Meituan - arXiv
arxiv.org
[2505.18654] MTGR: Industrial-Scale Generative Recommendation Framework in Meituan
researchgate.net
DeGRe: Dense-supervised Generative Reranking for Recommendation - ResearchGate
arxiv.org
Query-Mixed Interest Extraction and Heterogeneous Interaction: A Scalable CTR Model for Industrial Recommender Systems - arXiv
alphaxiv.org
MTFM: A Scalable and Alignment-free Foundation Model for Industrial Recommendation in Meituan | alphaXiv
emergentmind.com
Semi-Local Attention Mechanism - Emergent Mind
arxiv.org
Bending the Scaling Law Curve in Large-Scale Recommendation Systems - arXiv
arxiv.org
Bending the Scaling Law Curve in Large-Scale Recommendation Systems - arXiv
github.com
Request: Open-source SLA kernel and ULTRA-HSTU co-design components #481 - GitHub
github.com
Releases · alibaba/TorchEasyRec - GitHub
arxiv.org
HSTU-BLaIR: Lightweight Contrastive Text Embedding for Generative Recommender - arXiv
huggingface.co
Daily Papers - Hugging Face
github.com
HSTU-BLaIR: Lightweight Contrastive Text Embedding for Generative Recommender - GitHub
arxiv.org
HSTU-BLaIR: Lightweight Contrastive Text Embedding for Generative Recommender - arXiv
arxiv.org
HSTU-BLaIR: Lightweight Contrastive Text Embedding for Generative Recommender - arXiv
emergentmind.com
Hierarchical Sequential Transduction Unit (HSTU) - Emergent Mind
Uncovering Sparse Normalization and Fusion Mechanics
Through a deep synthesis of the latest industrial literature, I have uncovered how next-generation sequential transducers stabilize training when processing heterogeneous features. While traditional systems rely on uniform layer normalization, modern generative recommendation architectures are introducing group-layer normalization. This technique partitions disparate feature types—such as user demographics, item catalog codes, and real-time interaction contexts—and normalizes them separately. This prevents high-variance features from overshadowing more subtle signals, ensuring a stable latent space where textual embeddings from contrastive models can be fused directly with behavioral item identifiers via linear projection and element-wise addition.
Resolving Ultra-Long Sequence Latency Contradictions
I am resolving a critical system-level contradiction: how to scale sequential transduction to capture ultra-long user histories without suffering from quadratic computational bottlenecks. Recent engineering breakthroughs introduce semi-local attention mechanisms that combine highly optimized local sliding-window attention with residual linear-attention streams. By utilizing custom GPU kernels and hardware-aware pipelining, these architectures scale training and inference linearly with sequence length. This allows models to ingest extensive historical actions while maintaining the microsecond latencies required for real-time industrial deployment.
Transitioning to Comprehensive Architectural Evaluation
I am now thinking through the complete taxonomy of generative ranking to synthesize my findings into an exhaustive evaluation. Having mapped out the structural sequence transducers, semantic generative language rankers, and hybrid feature-fusion methods, my final actions will focus on constructing an in-depth comparative report. I will evaluate the trade-offs of each paradigm, analyze the integration of multi-modal signals, and address the theoretical and engineering challenges of deploying native generative models at scale.
The initial research has returned a lot of information. I'm sorting through it and organizing it. This will make sure the whole thing flows well and hits all the key points you asked for.
This is it! I’m bringing it all together. Jotting down my final thoughts, polishing everything up, and making sure I give you my very best work.
