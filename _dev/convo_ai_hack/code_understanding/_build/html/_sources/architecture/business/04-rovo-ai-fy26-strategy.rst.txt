=================================================
Rovo + AI - FY26 — Strategic Direction
=================================================

**Source**: Confluence folder ``ANALYSIS/folder/6838241888`` —
*"Rovo + AI - FY26"* (the canonical FY26 strategic planning hub)
plus 8 distributed strategy pages across 6 Confluence spaces (Rovo,
Finance, Marketing, Design, Growth, ANALYSIS).

**Critical insight from investigation**: The hub is a **folder, not
a single page**. FY26 strategy content is **distributed across 6+
Confluence spaces** with no single canonical strategy doc. The
following synthesis is built from 8 strategic source pages.

==================================================
1. Strategic pillars (5 pillars)
==================================================

#. **Knowledge** — Semantic Index + Indexed Objects monetization
#. **Productivity** — Agents GA + full CRUD; Rovo Chat MAU growth
#. **Trust** — AI Access Controls GA + ISO 42001 + Watermarking
#. **Monetization** — Rovo Credits enforcement (UBP) + LRP revenue model
#. **Brand** — "AI that knows your business" positioning + Team26 launch

==================================================
2. North Star metrics (FY26)
==================================================

.. list-table::
   :header-rows: 1
   :widths: 35 25 25 15

   * - Metric
     - Baseline
     - H2 FY26 Target
     - Status
   * - **Rovo MAU**
     - ~100.3k
     - **150k+**
     - 🟡 Tracking
   * - **Discovery milestone (Day 0-7)**
     - —
     - **150k users**
     - 🟡 Tracking
   * - **Activation milestone (Day 1-30)**
     - —
     - **80k users**
     - 🟡 Tracking
   * - **Fandom milestone (sustained engagement)**
     - —
     - **100k users**
     - 🟡 Tracking
   * - **Enterprise seats unblocked**
     - 3.9M (post-Q3)
     - Full coverage
     - 🟢 Achieved
   * - **Rovo + Agents adoption**
     - Beta
     - Production GA
     - 🔄 In progress
   * - **Brand perception**
     - Aspirational
     - Awareness lift (Q4 FY26 → Q1 FY27)
     - 🔄 In progress

==================================================
3. Concrete commitments by pillar
==================================================

3.1 Revenue & Monetization
============================

* **Rovo Credits enforcement** (allowance-based UBP) by H2 FY26
* **Indexed Objects (3P data) monetization roadmap** (FY27-FY29 LRP)
* **Rovo UBP waiver expansion** integrated into HT TWC forecast
* **PxQ bottoms-up sizing** methodology for Rovo Credits & Indexed Objects
* **Note**: LRP fidelity is "low-medium" due to early-stage usage data

3.2 Product & Engineering
===========================

* **AI Access Controls GA** (Q3 FY26)
* **ISO 42001 gap assessment** (Q3 FY26)
* **Watermarking implementation** (Q3 FY26)
* **Agents GA-ready + full CRUD** (H2 FY26)
* **Semantic Index production GA** ✅ DONE (Q2-Q3 FY26)

3.3 User Growth
=================

* **3-stage behavioral habit loop**:

  * **Discovery** (Day 0-7) → 150k users
  * **Activation** (Day 1-30) → 80k users
  * **Fandom** (sustained) → 100k users

3.4 Brand & Marketing
=======================

* **"AI that knows your business"** positioning (active)
* **Team26 AI announcements** (Q4 FY26)
* **Rovo awareness campaign launch** (Q4 FY26 → FY27 Q1)
* **Creator program expansion** (H2 FY26)
* **5 social pillars**: The Proof, POVs, In Person, Partnerships, Brand

==================================================
4. Top 8 strategic source documents
==================================================

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Document
     - Key extract
   * - **Rovo Growth: User Nurturing Journey Strategy (H2 FY26)**
     - 150k MAU target via 3-stage habit loop
   * - **Rovo LRP Readout (Mar 2026)**
     - FY27-FY29 revenue model (Credits + Indexed Objects); low-medium fidelity
   * - **FY26 Rovo Social Strategy**
     - 5 pillars positioning "AI that knows your business"
   * - **Rovo & AI Design Big Rocks (H2 FY26)**
     - Major UX/design bets; prototype standards (3-4 min Looms)
   * - **Rovo LRP Financial Model Framework**
     - PxQ bottoms-up sizing for Rovo Credits & Indexed Objects
   * - **Strategy & Principles (Rovo UBP)**
     - Foundational usage-based-pricing strategy
   * - **DRAFT: UBP Roadmap & Milestones**
     - Credits enforcement spike phase (Q3 FY26); future TBD
   * - **FY26 Q1 R4F | Rovo Readout**
     - Quarterly revenue forecast discipline + risk tracking

==================================================
5. Top risks & dependencies
==================================================

#. **Decentralized documentation** — strategic content scattered across
   6+ spaces; no single source of truth
#. **Monetization confidence at risk** — LRP explicitly "low to medium
   fidelity" due to early-stage usage data
#. **UBP enforcement timeline risk** — roadmap marked DRAFT; future
   milestones TBD as of Apr 16, 2026
#. **Aggressive user growth targets** — 150k/80k/100k milestones are
   highly dependent on Q3 governance + agent GA + marketing all landing
#. **Cross-product dependency risk** — no single DRI for
   Jira/Confluence/Loom/TWC integration GTM
#. **Missing explicit OKRs** — quarterly OKRs not centrally documented
   (commitments found, but quarterly target tracking is dispersed)

==================================================
6. How this maps to convoai engineering
==================================================

This is a **product/business strategy doc**, not an engineering plan.
Engineering implications, by pillar:

* **Knowledge** → drives convoai semantic search, retrieval quality (see :doc:`01-fy26-goals-and-slos` §12 AIFC quality)
* **Productivity** → drives Rovo Chat throughput goals + Agents Studio expansion (see :doc:`../cross-cutting/features/agentstudio`)
* **Trust** → drives convoai SLO compliance, ARIZE evals, Trust Scorecard hygiene (see :doc:`02-trust-scorecard`)
* **Monetization** → introduces convoai Rovo Credits enforcement code paths (NEW work; see open question Q1 below)
* **Brand** → no direct engineering impact

==================================================
7. Open questions for engineering
==================================================

#. **Rovo Credits enforcement** — Where does the allowance check fire in
   the convoai request lifecycle? Is it a pre-LLM gate, post-LLM
   accounting, or both? **Action**: search for ``credits``, ``allowance``,
   ``usage`` in conversational-ai-platform code
#. **Indexed Objects monetization** — How does convoai count "indexed
   objects" per query? **Action**: review semantic-index instrumentation
#. **150k MAU target** — What is convoai's current MAU and what's the
   gap? **Action**: query Splunk / Amplitude
#. **Q3 FY26 ISO 42001 gap assessment** — does convoai have data
   handling that breaks compliance? **Action**: review with security team

==================================================
8. Honest gaps (per investigation)
==================================================

* The hub itself (folder ``6838241888``) has **NO direct child pages**
  via CQL parent search — strategy lives elsewhere
* The "Rovo & AI - FY26-27 Strategic Direction" whiteboard exists but
  is not directly fetchable (whiteboard format)
* Quarterly OKRs are not centrally documented
* DRI mapping for cross-product GTM is unclear
* Detailed quarterly milestones TBD for FY26 H2 + FY27 H1

==================================================
Cross-references
==================================================

* :doc:`01-fy26-goals-and-slos` — engineering SLOs that support these strategic goals
* :doc:`02-trust-scorecard` — Trust pillar engineering metrics
* :doc:`03-teamserve-bluebird` — cost optimization supporting Monetization pillar
* Confluence folder: https://hello.atlassian.net/wiki/spaces/ANALYSIS/folder/6838241888
