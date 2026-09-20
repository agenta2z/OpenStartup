=================================================
TEAMServe Bluebird — Cost & Latency Optimization
=================================================

**Source**: Confluence pages ``6948530619`` (primary), ``6790951105``
(presentation), ``6820586742`` (GCP migration).

**Status**: ✅ **Live in production** as of April 30, 2026 (for Jira
Similar Issue Models). Multi-cloud GCP rollout in progress (target GA
June 2027).

==================================================
1. What Bluebird IS
==================================================

**One-sentence**: A Triton-backed inference platform (TEAMServe
Bluebird) that uses dynamic batching + automatic mixed precision +
global request flattening to massively reduce latency and cost for
embedding/reranking workloads — with **zero product-team friction**.

**The thesis**: Concentrate optimization at the platform layer
(Triton + ML Platform) so 700K+ DAU products like Jira Similar Issues
get 86% latency reduction without changing application code.

==================================================
2. Verified production wins (April 2026)
==================================================

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Metric
     - Value
     - Status
   * - **Semantic Reranker latency**
     - **262.2ms → 35.7ms** (-86.3%)
     - ✅ Live
   * - **Query Rewrite latency**
     - **68.1ms → 39.8ms** (-41.6%)
     - ✅ Live
   * - **Monthly inference cost**
     - **$5,002 → $2,958** (-40%)
     - ✅ Achieved
   * - **Annual savings (Jira workloads)**
     - **$25,000/year**
     - ✅ Realized
   * - **Daily inference volume**
     - **198 million requests/day**
     - ✅ At scale
   * - **Daily Active Users impacted**
     - **700,000**
     - ✅ Validated

==================================================
3. Architectural approach
==================================================

**4 core optimizations**:

#. **Dynamic batching** — microsecond accumulation windows; multiple
   user requests batched into single GPU call
#. **Automatic Mixed Precision (FP16)** — 2× throughput on supported
   hardware with negligible quality loss
#. **Global request flattening** — single large GPU batch instead of
   many small batches (improves utilization)
#. **Vectorized GPU compute** — embedding operations run as bulk
   tensor ops instead of per-request

**Zero product-team friction**: All optimizations live at the platform
layer. Jira AI and convoai application code is unchanged. Product
teams interact via the same TEAMServe gRPC/HTTP endpoints — Bluebird
is invisible to them.

==================================================
4. Multi-cloud GCP rollout timeline
==================================================

The "Bluebird Multi-Cloud" initiative migrates Bluebird-optimized
workloads from AWS to GCP, unlocking 1M+ tenants:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Date
     - Milestone
   * - **April 2026** ✅
     - GCP Staging Testing Begins
   * - **June 2026** 🔄
     - GCP Staging Validated (currently 18/24 services on track)
   * - **August 2026** 📅
     - First test tenant in production (GCP)
   * - **December 2026** 🎯
     - TWC (Team-Wide Cluster) Early Access Program goes live in GCP
   * - **Jan-Mar 2027** 📈
     - Real tenant migration begins (1M+ tenants)
   * - **June 2027** 🏁
     - General Availability (multi-cloud production)

==================================================
5. Implications for convoai
==================================================

**Direct wins** (already live):

* convoai's Jira Similar Issue calls inherit the 86% latency reduction
* Convo AI's embedding/reranking calls inherit the 40% cost reduction
* No code changes required in conversational-ai-platform repo

**Indirect wins** (in progress):

* Higher-throughput inference removes a key contributor to convoai's
  **time-to-first-byte** latency
* Lower per-call cost relaxes constraints on calling embeddings more
  aggressively (e.g., better retrieval, denser memory recall)
* Multi-cloud capacity unlocks geo-redundancy for SLO improvements

**Constraints unchanged**:

* The OpenAI Scale Tier 99.9% ceiling (see :doc:`01-fy26-goals-and-slos`
  §13) remains for chat/streaming flows that depend on OpenAI
* Bluebird optimizes the **internal model serving layer**, not external LLM calls

==================================================
6. Honest gaps in the documentation
==================================================

The agent investigation surfaced these gaps:

#. **P50/P95/P99 breakdown** — only P90 latency provided in canonical pages
#. **GCP cost parity** — AWS savings unconfirmed on GCP; pending analysis
#. **Phase-gate success criteria** — timeline clear but validation gates not detailed
#. **Per-token cost reduction** — infrastructure cost only; model-level optimization TBD
#. **ML Studio & MLFS at risk** for June 2026 staging deadline (2 of 24 services lagging)

==================================================
Cross-references
==================================================

* :doc:`01-fy26-goals-and-slos` §4.1 — TEAMServe Bluebird brief mention
* :doc:`../cross-cutting/11-external-integrations` — TEAMServe integration topology
* Confluence: ``6948530619`` (primary), ``6790951105`` (presentation), ``6820586742`` (GCP migration)
