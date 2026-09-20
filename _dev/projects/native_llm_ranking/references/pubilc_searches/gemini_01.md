The Paradigm Shift in Recommender Systems: Architecting Native LLM-Based Ranking and Recommendation Models

The integration of Large Language Models (LLMs) into recommender systems has initiated a structural transition from traditional collaborative filtering and deep learning-based point-wise predictions toward generative, instruction-driven, and multi-task frameworks. Historically, recommender systems have relied on isolated, multi-stage cascading pipelines consisting of candidate generation, ranking, and re-ranking, heavily dependent on dense behavioral logs and discrete item IDs. While these legacy architectures scale efficiently, they face fundamental limitations, including semantic blindness to unstructured content, high susceptibility to cold-start scenarios, and rigid optimization objectives that isolate prediction decisions and restrict versatility.

The advent of highly capable foundation models—such as the Qwen, Llama, and Gemma families—has catalyzed the development of native LLM-based recommender systems. These systems are broadly categorized into two paradigms: "LLM-for-RS," where language models serve as advanced feature encoders plugged into existing deep learning recommendation models, and "LLM-as-RS," where the language model natively acts as the end-to-end generator, ranker, or explainer. The latter paradigm promises a unified architecture capable of simultaneously generating candidate lists, rendering fine-grained rankings, extracting rich user embeddings, and articulating natural language explanations.

This comprehensive analysis investigates the latest authoritative methodologies for developing native LLM ranking models. It evaluates the direct application of state-of-the-art public models to ranking tasks, dissects architectural solutions to fundamental LLM limitations such as position bias, and critically examines whether a multi-task, versatile model inherently yields stronger ranking performance or falls victim to the mathematical pitfall of negative transfer.
Generative Recommendation and the Evolution of Item Representation

The foundational challenge in deploying LLMs natively for recommendation lies in aligning the continuous, semantic space of natural language with the discrete, collaborative space of user-item interactions. Traditional models embed item IDs in a shared latent space, but this approach isolates the ID from its semantic metadata, limiting the ability of the system to infer relationships based on content attributes. To bridge this gap, modern LLM-based recommenders map items to discrete token sequences, enabling the model to predict the next item via autoregressive text generation.

Rather than using arbitrary numeric IDs, contemporary generative recommenders utilize Semantic IDs. These are structured identifiers generated through vector quantization techniques, such as the Residual Quantized Variational AutoEncoder (RQ-VAE) or hierarchical K-means clustering. These techniques compress item metadata, spanning text, image, and audio modalities, into compact sequences of integers that the LLM processes as tokens. This allows the LLM to learn relationships between items using standard language modeling objectives. Research indicates that directly replacing traditional ID embedding tables with dense LLM semantic embeddings can sometimes degrade the Click-Through Rate because traditional rankers heavily rely on memorizing high-frequency collaborative signals. However, approaches that fuse textual semantics with collaborative IDs exhibit superior generalization. Hybrid semantic identifiers do significantly better than random hashing, especially in cold-start and long-tail item recommendations where historical interaction data is sparse.

A persistent flaw in cascading recommendation pipelines is the disconnect between the generative retrieval stage and the discriminative ranking stage. Downstream rankers can only optimize over the truncated candidate set provided by the upstream retriever. If a highly relevant item is discarded during early retrieval due to a suboptimal heuristic, the ranker cannot recover it. To resolve this structural bottleneck, the Unified Framework for Semantic ID Generation and Ranking (UniSGR) introduces an architecture that unifies these stages within a single LLM.

UniSGR employs a two-stage training paradigm designed specifically for industrial e-commerce platforms. In the multi-scenario pre-training stage, the LLM is exposed to chronological interaction sequences mixed from multiple business scenarios. The model is trained via a Next-Token Prediction loss to learn generalized user interests across diverse domains. Following pre-training, the model undergoes a scenario-specific alignment stage utilizing Value-Aware Parallel Multi-Token Prediction. To optimize for multiple concurrent downstream business values, such as clicks, add-to-cart events, and purchases, UniSGR applies a customized parallel mask for autoregressive semantic-ID targets within the same session. It applies business value weights to the prediction loss based on the desired funnel stage, ensuring that the generation of candidates inherently prioritizes high-value business outcomes.

To explicitly align generation with final ranking objectives without relying on external modules, UniSGR utilizes Task-Aware Tokens. Learnable embedding vectors corresponding to specific business objectives are prepended to the decoder input. The autoregressive sequence is processed under a unified causal mask where all semantic ID tokens can attend to these preceding task tokens. This architectural design forces the generated latent representations to be inherently conditioned on the specific ranking objective, effectively coupling retrieval and ranking without requiring separate network towers. Furthermore, UniSGR introduces Semantic Tree Attention with Reorganized KV cache (STARK), an inference strategy that removes key efficiency bottlenecks in conventional beam search. By sharing the cached attention states of the user prompt across all candidate branches, STARK achieves a 200% throughput improvement in industrial-scale serving scenarios.
Direct Application of Public Foundation Models to Ranking Tasks

The direct application of strong open-weights models to recommendation ranking circumvents the need to construct architectures from scratch. Specifically, the Llama-Nemotron, Qwen, and Gemma ecosystems provide optimized pathways for zero-shot ranking, few-shot reranking, and parameter-efficient domain adaptation.
The Nemotron Paradigm: Cross-Encoder Reranking

NVIDIA’s Llama-Nemotron series represents a state-of-the-art approach to text and document reranking. Built upon the Meta Llama architecture and fine-tuned specifically for ranking, these models are designed as transformer cross-encoders. Unlike bi-encoders, which process queries and items through separate neural towers to enable fast vector nearest-neighbor retrieval, the cross-encoder processes the combined query-document pair simultaneously. This permits bidirectional self-attention across the sequence, capturing deep, token-level interactions between the user's context and the candidate item's attributes.

The Nemotron architecture applies a standardized prompt template format to the input and terminates in a sequence classification head. This head outputs a raw logit score reflecting the model's prediction of relevancy, which can be passed through a sigmoid activation function to yield a standardized probability. Benchmarking data highlights that smaller, highly optimized cross-encoders can match or exceed the performance of significantly larger generative models in ranking tasks.
Model Name	Parameters	Architecture	Hit@1 (English)	MRR@10	Inference Latency
llama-nemotron-rerank-1b-v2	1.2B	Cross-Encoder (Sequence Classification)	83.00%	0.8514	~243ms
gte-reranker-modernbert-base	149M	ModernBERT Cross-Encoder	83.00%	0.8483	Fast
jina-reranker-v3	560M	Custom Cross-Encoder	81.33%	N/A	~188ms
Qwen3-Reranker-4B	4.0B	CausalLM (Logit Scoring)	77.67%	N/A	>1000ms

The data indicates that the 1.2 billion parameter Nemotron reranker achieves a Hit@1 of 83.00% and an MRR@10 of 0.8514, outperforming the 4 billion parameter Qwen3 reranker in strict top-1 accuracy while maintaining lower latency. This demonstrates that architectural alignment (specifically, sequence classification cross-encoding) is frequently more impactful than raw parameter count when directly applying public LLMs to listwise ranking.
Qwen3: Embeddings and Logit-Based Scoring

The Qwen3 Embedding and Reranker series introduces an alternative mechanism for ranking evaluation. Available in parameter sizes ranging from 0.6B to 8B, Qwen3 handles multilingual queries and complex semantic relationships. While models like Nemotron utilize a dedicated sequence classification head, Qwen rerankers typically utilize a CausalLM architecture. Relevance is scored by analyzing the logit probabilities of distinct affirmative or negative tokens generated at the end of the evaluation prompt.

This method requires the model to compute a forward pass and extract the logits for the specific token corresponding to relevance, mapping language modeling outputs to continuous ranking scores. Qwen3’s pretraining on 150 million synthetic text pairs gives it remarkable zero-shot robustness across diverse languages. However, relying on autoregressive token generation for scoring can introduce latency bottlenecks, as the 8 billion parameter variant demands significant computational overhead compared to leaner cross-encoder architectures. Despite this, the Qwen3-Embedding-8B model achieves a score of 70.58 on the MTEB Multilingual benchmark, demonstrating exceptional zero-shot representation capabilities suitable for first-stage candidate retrieval.
Gemma: Parameter-Efficient Fine-Tuning and Catastrophic Forgetting

For bespoke industrial recommendation systems, zero-shot application is often insufficient to capture the nuanced collaborative signals unique to a specific platform. The Gemma family is heavily leveraged for supervised fine-tuning via Low-Rank Adaptation (LoRA) and Quantized LoRA (QLoRA).

LoRA mitigates the catastrophic computational costs of full fine-tuning by freezing the base model weights and injecting trainable low-rank decomposition matrices into the transformer layers. In ranking adaptation, optimizing the LoRA hyperparameters is critical to balancing expressivity and memory constraints. Studies evaluating LLMs for domain-specific recommendations note that higher LoRA ranks significantly improve convergence speed and factual accuracy retention. Lower ranks optimize the memory footprint, allowing models to be trained on consumer-grade hardware, but inherently limit the model's capacity to internalize complex user-item graph relationships.

A significant challenge in applying LoRA to recommendation is catastrophic forgetting, where the LLM loses its general world knowledge—the exact attribute that makes LLM-based recommenders valuable for cold-start and cross-domain tasks. The "LoRA-Null" initialization technique addresses this by initializing the LoRA adapters within the null space of the pre-trained knowledge activation. This enforces orthogonality between the space of the pre-trained knowledge and the space being fine-tuned for the recommendation task. By ensuring that the weight updates do not interfere with the principal components of the pre-trained representation, LoRA-Null preserves zero-shot reasoning capabilities while adapting the model to specific ranking formatting. Empirical trials on medical recommendation dialogues utilizing Keras and JAX on Tensor Processing Units (TPUs) confirmed that fine-tuning Gemma 3 models shifted the qualitative tone toward specialized guidance, though larger baseline models often retained an edge in strict zero-shot factual recall.
Overcoming Architectural Flaws: The Position Bias Conundrum

When transitioning from pointwise scoring to listwise ranking, LLMs encounter a severe architectural mismatch. Recommendation candidate evaluation is fundamentally a set-based operation; the order in which items are presented to a scoring function should not influence their inherent relevance to the user. However, decoder-only LLMs are explicitly designed for sequential processing.

When multiple candidate items are concatenated into a single listwise prompt, autoregressive LLMs suffer from profound position bias, frequently referred to as order sensitivity. Candidates placed at the beginning or the end of the prompt sequence are disproportionately favored or penalized, regardless of their actual relevance. This instability renders naive listwise LLM rerankers unreliable in production. A model that promotes an item under one serialization but demotes it when the candidate array is shuffled fails the basic requirements of a reproducible ranking algorithm, severely complicating evaluation and deployment.

Position bias originates from two primary architectural mechanisms within autoregressive transformers. The first mechanism is cross-candidate attention leakage, wherein tokens belonging to a candidate placed later in the sequence can attend to tokens from preceding candidates. This creates arbitrary, order-dependent interference where the representation of an item is polluted by the items serialized before it. The second mechanism is position-dependent encoding. Utilizing Rotary Positional Embeddings (RoPE), the absolute position of a candidate's tokens within the sequence heavily alters their embedding geometry. An item injected at a token index of 500 will possess a mathematically distinct representation compared to the exact same item injected at a token index of 2000, skewing the logit outputs independent of semantic relevance.
InvariRank: Permutation-Invariant Architecture

To solve this without relying on expensive runtime workarounds, the InvariRank framework proposes a fundamental architectural intervention to enforce permutation equivariance.

InvariRank re-engineers the attention mechanism during the forward pass. Let the input sequence be the concatenation of the shared user context and the candidate set. InvariRank implements a structured segment mask that overrides the standard causal mask. The applied mask explicitly restricts each candidate to attend solely to the shared user context and its own tokens. This architectural isolation ensures that candidates cannot influence one another during the attention computation.

Furthermore, InvariRank utilizes a shared positional framing under RoPE. Instead of incrementing positional IDs continuously across the candidate list, the positional offsets are aligned so that each candidate begins at the exact same relative distance from the user context. Coupled with a listwise Learning-to-Rank objective such as LambdaRank, InvariRank enables the LLM to score an entire candidate set in a single, permutation-invariant forward pass. It achieves the global efficiency of listwise ranking without sacrificing the structural stability and fairness of pointwise evaluation.
Prompt-Level Mitigations and Popularity Bias

Where architectural modifications to the LLM are not feasible, prompt-level interventions are necessary to mitigate bias. Techniques like Ranking via Iterative SElection (RISE) decompose the full list into smaller, randomized subsets, iteratively extracting the top candidates to dilute order dependence, reducing position bias by up to 25% compared to baseline prompting.

LLMs also exhibit profound popularity bias, where items with high historical engagement in the pre-training corpus dominate recommendation lists, overshadowing equally relevant niche items. The Semantic Popularity Lift (SPLiT) framework targets upstream popularity bias generated by LLMs before the final ranking stage. SPLiT operates as an online prompt optimization algorithm that measures whether textual preference summaries over-represent popular content, formulating prompt selection as a contextual Bayesian optimization problem to improve the Normalized Discounted Cumulative Gain (NDCG) by debiasing the prompt context itself. Additionally, the Expl-Debias framework leverages contrastive explanation-aware training, explicitly incorporating LLM-generated positive and negative explanations into the training phase to guide relevance learning toward personally aligned items rather than globally popular ones.
The Paradigm of Versatility: Joint Ranking, Embedding, and Explanation

The modern trajectory of recommendation research raises a critical hypothesis: Can a single, highly versatile model capable of ranking candidates, generating user embeddings, and explaining its recommendations structurally outperform specialized, single-task models? To evaluate this, the field has increasingly adopted multi-task recommendation frameworks.
Universal Recommendation Models (URM)

The Universal Recommendation Model (URM) demonstrates that LLMs can function as generalist recommendation learners. URM unifies diverse tasks, including Click-Through Rate prediction, sequential recommendation, intent recognition, and explanation generation, into a standardized sequence-in-set-out structure.

URM addresses the limitation of pure text LLMs by designing a multimodal fusion module. It transforms distributed item ID embeddings and dense text embeddings to the same dimensionality via Multi-Layer Perceptrons, combines them via addition, normalizes them using RMSNorm, and projects them into the LLM's input space. This fusion strategy strikes a delicate balance between the high discriminability of unique ID embeddings, which is critical for collaborative filtering, and the broad semantic generalization of text embeddings, which is critical for zero-shot reasoning on unseen items.
Generating Explainable Recommendations

A primary advantage of utilizing LLMs as native recommenders is their capacity for explainability. While traditional matrix factorization models act as opaque black boxes, LLMs can generate natural language rationales bridging user history and item attributes, thereby increasing user trust, transparency, and engagement.

However, naive prompt-based generation frequently results in hallucinations, where the LLM invents plausible but factually incorrect reasons for a recommendation based on statistical likelihood rather than the actual recommendation logic. To enforce fidelity, state-of-the-art frameworks employ advanced alignment techniques:

    RecExplainer and Intention Alignment: The RecExplainer framework trains the LLM to act as a surrogate for a target black-box recommender. It utilizes Intention Alignment, which operates directly in the latent space. The LLM is trained to ingest the latent representations (user and item embeddings) of the target model, forcing the language generation to strictly align with the mathematical mechanics and activation patterns of the underlying ranker.

    Statement-Level Ranking: Instead of allowing open-ended text generation, recent methodologies advocate a paradigm shift to "rank, don't generate." Explainability is reframed as a statement-level ranking problem. The LLM scores a predefined set of atomic, factual explanatory statements based on their relevance to the user-item pair, returning the top-ranked statements as the explanation. This formulation structurally eliminates hallucinations while maintaining high linguistic quality and allowing for standardized evaluation metrics.

    Reasoning Graphs (LLMRG): The LLM Reasoning Graphs framework prompts the LLM to dynamically construct a personalized knowledge graph linking a user’s historical behavioral sequence to the candidate item via logical, multi-hop causal nodes. This symbolic reasoning trace provides a highly transparent, verifiable explanation path that grounds the recommendation in explicit facts rather than latent probabilities.

User Embedding Generation and Contrastive Alignment

A versatile LLM must also be capable of outputting high-quality, dense user embeddings that encapsulate temporal and collaborative preferences. The challenge lies in structural inconsistency: LLMs organize their high-dimensional space based on linguistic semantics and grammar, while recommendation tasks require embeddings organized by collaborative interaction patterns and user-item co-occurrence.

The Contrastive Alignment of Generative LLMs for Sequential Recommendation (CALRec) framework tackles this via a two-tower fine-tuning approach. CALRec implements a mixed training objective comprising an autoregressive language modeling loss alongside a contrastive alignment loss (InfoNCE). By applying contrastive loss to the outputs of separate user and item towers, CALRec forces the LLM's dense textual embeddings to reflect collaborative similarity. This aligns user histories closely to target item representations in the latent space, achieving significant performance leaps, such as a 37% improvement in Recall@1 and a 24% improvement in NDCG@10 over state-of-the-art baselines.

Similarly, the InstructUE framework bridges the language and representation spaces by curating large-scale instruction datasets and applying a contrastive-autoregressive joint training strategy, thereby enhancing the instruction-awareness and noise-robustness of user embeddings across diverse industry domains. Dual-LLM co-training models further extend this by utilizing joint contrastive loss to map high-dimensional user embeddings from distinct behavioral domains into a common semantic anchor space, enabling highly effective cross-domain recommendation even when interaction histories are sparse.
Critical Analysis: Does Versatility Actually Make Ranking Stronger?

The theoretical appeal of an omnipotent, versatile LLM is clear: a single model that understands rich semantic context, produces aligned embeddings, ranks candidates, and generates explanations should possess a deeper, more holistic understanding of the user. However, empirical research indicates a vastly more complex reality fraught with the challenges of negative transfer and task interference.
The Danger of Negative Transfer

When an LLM is trained to perform multiple highly divergent tasks simultaneously—such as precise, discriminative ranking, which demands rigid adherence to collaborative probabilities, and open-ended explanation generation, which demands high entropy and linguistic creativity—the gradient updates for these tasks often conflict.

If the parameter capacity of the model is not sufficiently large, learning multiple tasks degrades performance compared to training specialized, single-task models. The LLM experiences a "see-saw" phenomenon: improving the fluency of explanations actively harms the precision of the ranking, because the latent representation is pulled in opposing geometric directions during gradient descent. Furthermore, uniform parameter-efficient fine-tuning, such as applying a single LoRA module across all tasks and user profiles, struggles to adapt to sequence variability, causing distinct user behavioral paths to adversely affect one another.
Mitigating Task Interference to Unlock True Versatility

For a versatile model to genuinely enhance ranking strength, sophisticated routing and task-balancing mechanisms are strictly required. State-of-the-art frameworks overcome negative transfer through specific architectural innovations:
Mitigation Strategy	Framework	Mechanism	Impact on Performance
Mixture of Experts Routing	iLoRA (Instance-wise LoRA)	Splits low-rank matrices into expert arrays; gating network routes interactions.	Isolates task conflicts, enabling granular adaptation without parameter bloat.
Gradient Magnitude Balancing	PMTRec	Dynamically adjusts loss weights based on gradient norms during backpropagation.	Prevents auxiliary tasks from washing out subtle ranking gradients.
Reward-Decoupled Optimization	MT-GRPO	Employs improvement-aware task reweighting targeting worst-task performance.	Yields 16–28% absolute improvement in worst-task accuracy.

By utilizing Instance-wise LoRA with the Mixture of Experts concept, the network dynamically routes specific user interactions to distinct experts, mitigating negative transfer by ensuring that the generalized adaptations do not override individualized interaction patterns.

In joint learning environments, the Personalized Multi-Task Training algorithm for Recommender Systems (PMTRec) dynamically adjusts the loss weights of individual tasks based on gradient norms. A Gradient Magnitude Balancing module ensures that auxiliary tasks do not generate massive gradients that eclipse the subtle, critical gradients required for accurate ranking prediction.

When fine-tuning versatile LLMs via reinforcement learning, Multi-Task Group Reward-Decoupled Policy Optimization (MT-GRPO) utilizes an improvement-aware task reweighting algorithm. It actively monitors worst-task performance and dynamically adapts task weights to ensure that the model achieves balanced progress across all capabilities. This prevents the model from optimizing explanation fluency at the expense of ranking accuracy, yielding up to a 28% absolute improvement in worst-task performance over standard optimization.

Ultimately, the question of whether a versatile model makes ranking stronger depends on the architecture. If a foundation model is naively prompted or universally fine-tuned on mixed objectives, ranking accuracy typically degrades due to gradient conflict and alignment mismatch. However, if the architecture enforces explicit representation decoupling—such as through Task-Aware Tokens, MoE routing, or contrastively aligned dual-towers—the integration of multi-task objectives creates a synergistic effect. Auxiliary tasks like explanation generation act as powerful regularizers that force the LLM to learn the deeper, causal structures behind user interactions, leading to more robust generalization and measurable lifts in strict ranking metrics.
Industrial Inference: Deploying LLM-Scale Rankers

The final barrier to deploying deep, versatile LLM rankers in production is inference latency. Traditional deep learning recommendation models operate in milliseconds, while autoregressive LLMs can take seconds to generate outputs, violating strict service-level agreements in real-time environments.

To achieve sub-second latency, industry leaders have fundamentally reimagined serving infrastructure. Meta's Adaptive Ranking Model replaces linear processing with Request-Oriented Optimization. Rather than independently processing a user against thousands of candidate ads, the system computes the high-density user context exactly once per request. Through In-Kernel Broadcast optimization, this single user representation is shared across all ad candidates directly within the GPU kernel. This transforms computational scaling from linear to sub-linear, heavily reducing memory bandwidth pressure and allowing trillion-parameter embeddings to be processed in real time.

Selective FP8 post-training quantization is also deployed strategically. Rather than applying uniform low-precision, which destroys the nuanced mathematical separation required for fine-grained ranking, systems utilize micro-benchmarking to apply FP8 strictly to layers with high precision-loss tolerance. This maintains recommendation quality while unlocking high-throughput inference and maximizing hardware utilization.
Conclusion

The evolution of native LLM ranking and recommendation models signifies a profound departure from heuristic-driven collaborative filtering toward holistic, semantically grounded reasoning systems.

The exhaustive analysis of current research indicates that directly applying public models like Gemma, Qwen, and Nemotron requires careful consideration of architectural suitability. Cross-encoders excel at precision reranking but carry heavy inference costs, while parameter-efficient fine-tuning strategies must utilize specialized initializations, such as LoRA-Null, to protect the model's pre-trained world knowledge from catastrophic forgetting.

Architectural interventions are mandatory to correct the inherent flaws of language models in ranking contexts. Specifically, the position bias caused by cross-candidate attention leakage and absolute positional encodings must be neutralized through permutation-invariant designs like InvariRank. This ensures that recommendation remains a mathematically stable, set-based operation rather than a sequence-dependent vulnerability.

Finally, the pursuit of the versatile model—one that concurrently ranks, embeds, and explains—represents the bleeding edge of the field. While multi-task learning introduces the severe risk of negative transfer and gradient conflict, modern frameworks successfully navigate this through Mixture of Experts routing, contrastive representation alignment, and dynamic gradient balancing. When properly engineered with these safeguards, versatile models do not merely match traditional rankers; they demonstrably exceed them. By forcing the latent space to simultaneously map causal explanations, collaborative similarity, and sequence probabilities, the model achieves a profound, context-aware understanding of user intent, establishing a new frontier in the accuracy, interpretability, and robustness of recommender systems.
preprints.org
Generative Recommendation: A Survey of Models, Systems, and Industrial Advances
Opens in a new window
arxiv.org
CALRec: Contrastive Alignment of Generative LLMs for Sequential Recommendation - arXiv
Opens in a new window
arxiv.org
UniSGR: Unified Framework for Semantic ID Generation and Ranking - arXiv
Opens in a new window
arxiv.org
Benchmarking LLMs in Recommendation Tasks: A Comparative Evaluation with Conventional Recommenders - arXiv
Opens in a new window
arxiv.org
A Survey on Large Language Models for Recommendation - arXiv
Opens in a new window
arxiv.org
A Survey on Generative Recommendation: Data, Model, and Tasks - arXiv
Opens in a new window
arxiv.org
Fusion and Alignment Enhancement with Large Language Models for Tail-item Sequential Recommendation - arXiv
Opens in a new window
arxiv.org
CALRec: Contrastive Alignment of Generative LLMs For Sequential Recommendation
Opens in a new window
arxiv.org
Rethinking Generative Recommender Tokenizer: Recsys-Native Encoding and Semantic Quantization Beyond LLMs - arXiv
Opens in a new window
eugeneyan.com
Improving Recommendation Systems & Search in the Age of LLMs - Eugene Yan
Opens in a new window
arxiv.org
Large Language Models Are Universal Recommendation Learners - arXiv
Opens in a new window
paper-archivist.com
UniSGR: Unified Framework for Semantic ID Generation and Ranking - Paper Reading
Opens in a new window
arxiv.org
UniSGR: Unified Framework for Semantic ID Generation and Ranking - arXiv
Opens in a new window
catalyzex.com
UniSGR: Unified Framework for Semantic ID Generation and Ranking - CatalyzeX
Opens in a new window
huggingface.co
nvidia/llama-nemotron-rerank-1b-v2 - Hugging Face
Opens in a new window
aimultiple.com
Reranker Benchmark: Top 8 Models Compared - AIMultiple
Opens in a new window
huggingface.co
nvidia/llama-nemotron-rerank-vl-1b-v2 - Hugging Face
Opens in a new window
docs.nvidia.com
Reranking Model Fine-Tuning Recipe — Nemotron - NVIDIA Documentation
Opens in a new window
alibabacloud.com
Mastering Text Embedding and Reranker with Qwen3 - Alibaba Cloud Community
Opens in a new window
ai.google.dev
Gemma model fine-tuning | Google AI for Developers
Opens in a new window
codecademy.com
How to Fine-Tune Google Gemma 270M with Unsloth and QLoRA - Codecademy
Opens in a new window
frontiersin.org
Small LLMs can be good coldstart recommenders - Frontiers
Opens in a new window
arxiv.org
Put the Space of LoRA Initialization to the Extreme to Preserve Pre-trained Knowledge
Opens in a new window
medium.com
Fine-Tuning Gemma 3 270M (or Higher) on CPU/GPU with LoRA and keras: A Complete Guide | by Mezzihoussem | Medium
Opens in a new window
researchgate.net
LLM QLoRA Fine-Tuning of Llama, DeepSeek, and Qwen: A Skyrim Case Study
Opens in a new window
medium.com
Fine-Tuning Gemma 3 on TPU for Medical Q&A with Keras and JAX - Medium
Opens in a new window
arxiv.org
One Pass, Any Order: Position-Invariant Listwise Reranking for LLM-Based Recommendation - arXiv
Opens in a new window
arxiv.org
One Pass, Any Order: Position-Invariant Listwise Reranking for LLM-Based Recommendation - arXiv
Opens in a new window
arxiv.org
Evaluating Position Bias in Large Language Model Recommendations - arXiv
Opens in a new window
emergentmind.com
LLM-as-a-Judge: Bias Metrics in Evaluation - Emergent Mind
Opens in a new window
researchgate.net
One Pass, Any Order: Position-Invariant Listwise Reranking for LLM-Based Recommendation - ResearchGate
Opens in a new window
cdn.amazon.science
Large Language Models as Recommender Systems: A Study of Popularity Bias - Amazon Science
Opens in a new window
openreview.net
Leveraging Holistic Explanations to Mitigate Popularity Bias for Recommender Systems
Opens in a new window
openreview.net
SPLiT: Popularity-Bias-Aware Online Prompt Optimization for LLM-based Recommendation
Opens in a new window
pmc.ncbi.nlm.nih.gov
On explaining recommendations with Large Language Models: a review - PMC
Opens in a new window
arxiv.org
RecExplainer: Aligning Large Language Models for Explaining Recommendation Models - arXiv
Opens in a new window
arxiv.org
[2311.10947] RecExplainer: Aligning Large Language Models for Explaining Recommendation Models - arXiv
Opens in a new window
arxiv.org
Rank, Don't Generate: Statement-level Ranking for Explainable Recommendation - arXiv
Opens in a new window
arxiv.org
Enhancing Recommender Systems with Large Language Model Reasoning Graphs - arXiv
Opens in a new window
fi.ee.tsinghua.edu.cn
Denoising Alignment with Large Language Model for Recommendation
Opens in a new window
arxiv.org
CALRec: Contrastive Alignment of Generative LLMs for Sequential Recommendation - arXiv
Opens in a new window
arxiv.org
Instruction-aware User Embedding via Synergistic Language and Representation Modeling
Opens in a new window
techrxiv.org
Self-Supervised User Embedding Alignment for Cross-Domain Recommendations via Multi-LLM Co-Training - TechRxiv
Opens in a new window
arxiv.org
Multi-Task GRPO: Reliable LLM Reasoning Across Tasks - arXiv
Opens in a new window
openaccess.thecvf.com
Mitigating Task Interference in Multi-Task Learning via Explicit Task Routing With Non-Learnable Primitives - CVF Open Access
Opens in a new window
arxiv.org
[2605.05676] Decomposing the Basic Abilities of Large Language Models: Mitigating Cross-Task Interference in Multi-Task Instruct-Tuning - arXiv
Opens in a new window
lti.cs.cmu.edu
Mitigating Negative Transfer for Better Generalization and Efficiency in Transfer Learning - Language Technologies Institute
Opens in a new window
arxiv.org
Personalized Multi-task Training for Recommender System - arXiv
Opens in a new window
researchgate.net
Feature Decomposition for Reducing Negative Transfer: A Novel Multi-Task Learning Method for Recommender System (Student Abstract) | Request PDF - ResearchGate
Opens in a new window
neurips.cc
Customizing Language Models with Instance-wise LoRA for Sequential Recommendation
Opens in a new window
proceedings.neurips.cc
Customizing Language Models with Instance-wise LoRA for Sequential Recommendation - NIPS
Opens in a new window
chat.powerdrill.ai
Multi-Task GRPO: Reliable LLM Reasoning Across Tasks - Powerdrill- AI for Data Analysis
Opens in a new window
themoonlight.io
[Literature Review] Large Language Models Are Universal Recommendation Learners
Opens in a new window
arxiv.org
Finetuning Large Language Model for Personalized Ranking - arXiv
Opens in a new window
engineering.fb.com
Meta Adaptive Ranking Model: Bending the Inference Scaling Curve to Serve LLM-Scale Models for Ads - Engineering at Meta
Opens in a new window
