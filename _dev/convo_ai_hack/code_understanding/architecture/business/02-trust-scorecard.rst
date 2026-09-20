=================================================
Eng Conversational AI Trust Scorecard (May 2026)
=================================================

**Source**: Confluence space ``gai`` — *Eng Conversational AI Team Trust
Scorecard - May 2026*. Owner: Robbie Livermore. Reporting cadence: monthly.

**Overall trust score**: **97.35%** (11,000 / 11,300 points)

* Security: **97%** (7,100 / 7,300)
* Compliance: **97%** (3,900 / 4,000)

==================================================
1. What this scorecard measures
==================================================

The Trust Scorecard is the **corporate-level trust posture** for the
convoai team — covering security & compliance hygiene that any Atlassian
engineering team must maintain. It is **NOT a product-AI-quality
scorecard** (those metrics live in separate AIFC quality docs and
ARIZE / Splunk dashboards — see :doc:`01-fy26-goals-and-slos`
sections 5 + 12).

**Scope**: 8 modules covering security training, project risk
assessments, REPCOM/PUOL hygiene, accessibility, secure development.

==================================================
2. Module-by-module status (May 2026)
==================================================

.. list-table::
   :header-rows: 1
   :widths: 35 12 12 16 25

   * - Module
     - Current
     - Target
     - Score
     - Status
   * - **Risk Assessment Completion**
     - 60% (3/5)
     - 90% (4/5)
     - 6/10
     - 🔴 Critical
   * - **Accessibility Training**
     - 83.3% (10/12)
     - 100%
     - 8/10
     - 🔴 Action
   * - Secure Development Training
     - 100% (12/12)
     - ≥95%
     - 10/10
     - 🟢 Good
   * - Security Awareness
     - ~100%
     - 95% + buffer
     - 10/10
     - 🟢 Good
   * - PUOL Management
     - 0 overdue
     - 0
     - 10/10
     - 🟢 Good
   * - REPCOM Tickets
     - 0 unresolved
     - 0
     - 10/10
     - 🟢 Good
   * - Accessibility Issues
     - 0 critical past SLO
     - 0
     - 10/10
     - 🟢 Good
   * - Unit Breaches
     - 0 detected
     - 0
     - 10/10
     - 🟢 Good (prescored)

**Status definitions**:

* 🟢 **Good** — at or above target
* 🟡 **Warning** — below target but trending up
* 🔴 **Action** — below target, action required
* 🔴 **Critical** — significantly below target, escalation required
* 🟢 **Prescored** — score awarded for clean detection (no breaches found)

==================================================
3. Scoring methodology
==================================================

* **Per-module score**: 0-10 scale, **weighted by criticality**
* **Category weighting**:

  * Security: 64.6% (7,300 / 11,300 max)
  * Compliance: 35.4% (4,000 / 11,300 max)

* **Sparkline tracking**: 60-day rolling window, 10 data points per module
* **Reporting cadence**: monthly snapshot in Confluence + real-time Databricks

**Data sources**:

* **Primary**: Databricks Socrates dashboards (7 real-time dashboards linked from scorecard page)
* **Tracking**: CTSC Jira project (scorecard components)
* **Governance**: Compass component view available

==================================================
4. Action items (May 2026)
==================================================

If completed, score moves from **97.35% → 98.5%** (+1.15 pp):

#. **Risk Assessment** (60% → 90%):

   * **Owners**: Kevin Ma, Malavika Vasudevan
   * **Action**: Complete risk-assessment questionnaires for 2 overdue projects

#. **Accessibility Training** (83.3% → 100%):

   * **Owners**: Kevin Ma, Robbie Livermore
   * **Action**: Complete Accessibility Fundamentals Training (~35 min each)

==================================================
5. What this scorecard does NOT cover
==================================================

The Trust Scorecard is **org-hygiene focused**. It does NOT include:

#. **LLM hallucination rates** — see :doc:`01-fy26-goals-and-slos` §12 (AIFC quality)
#. **Citation accuracy** — tracked in Gen AI Platform dashboards (separate)
#. **Tool invocation success rate** — per-tool TOME SLOs (see §2 of FY26 doc)
#. **End-user-reported correctness** — ARIZE / per-feature dashboards
#. **Per-agent quality scores** — AgentStudio Conversation Review system

**Implication**: A team can score **100% on the Trust Scorecard while
shipping products with severe AI quality issues** (e.g., the AIFC
factual-consistency degradation 80% → 13% identified in the AIFC
Maturity Gap Analysis). These two concerns must be tracked separately.

==================================================
6. Honest gaps (per investigation)
==================================================

* **No FY26 explicit targets** — module targets are stable corporate SLOs, not FY26-specific
* **Historical trends require fetching** April-December 2025 monthly scorecards
* **Compass custom fields** may have additional dimensions not in Confluence snapshot
* **ConvoAI product quality NOT in this scorecard** — see :doc:`01-fy26-goals-and-slos` §5 & §12

==================================================
Cross-references
==================================================

* :doc:`01-fy26-goals-and-slos` — Sections 5, 12 cover product-AI quality
* :doc:`../00-glossary` — REPCOM, PUOL definitions
