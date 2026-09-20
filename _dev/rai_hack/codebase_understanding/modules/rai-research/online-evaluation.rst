.. _mod-online-evaluation:

====================
Online Evaluation
====================

:Files: ``notebooks/evaluation/online_evaluation/``
:Importance: **Continuous model quality monitoring in production**

Overview
=========

Online evaluation monitors production moderation model performance by sampling
real moderation decisions and re-evaluating them using an LLM judge. This detects
model drift, threshold miscalibration, and systematic failure modes without
requiring human labelers for every sample.

Architecture
=============

.. code-block:: text

   Production traffic
         │ (sampled, e.g. 1%)
         ▼
   GASv3 analytics events
         │ (batch pull via rai_analytics.py)
         ▼
   LLM Judge (llm_judge_query_response.py)
         │ (eval each sample against AUP policies)
         ▼
   Comparison: model decision vs judge decision
         │
         ▼
   Metrics: precision, recall, FPR, FNR per category
         │
         ▼
   Databricks dashboard + alerts

LLM Judge (``llm_judge_query_response.py``)
=============================================

Uses an LLM (Claude or GPT-4) to independently evaluate whether a piece of
content violates specific AUP policies. The judge is configured via Jinja2
prompt templates:

**``llm_judge_prompt.jinja``** — main judge prompt:

* Takes: ``{content, categories, policy_defns}``
* Returns: ``{harm_category, toBeFiltered: bool, confidence: float, reasoning: str}``
* System message frames the judge as an expert content evaluator
* Includes detailed policy definitions for each category

**``aup_llm_eval_policy_explain_v3.jinja``** — enhanced V3 judge prompt:

* Adds chain-of-thought reasoning requirement
* Asks for explicit quote from content that violates policy
* Returns structured JSON with ``explanation`` field

**``llm_judge_query_response_prompt.jinja``** — evaluates (query, response) pairs:

* Used when both user query AND AI response are available
* More nuanced evaluation accounting for response context

Policy definitions (``judge_category_policy_defns.json``)
===========================================================

JSON config with detailed definitions for each harm category used by the judge:

.. code-block:: json

   {
     "jailbreak_prompt_injection": {
       "name": "Jailbreak/Prompt Injection",
       "judge_description": "...",
       "examples_positive": ["...", "..."],
       "examples_negative": ["...", "..."],
       "edge_cases": ["..."]
     },
     ...
   }

Separate from ``policy_category_defns.json`` in the offline eval dataset —
these are tuned specifically for LLM judge prompting.

Online eval workflow (``online_eval_workflow.py``)
===================================================

Databricks notebook that runs the full pipeline:

1. Pull production moderation events from GASv3 analytics (time range: last 24h)
2. Sample N events per category (stratified by harm_category + outcome)
3. For each sampled event: call LLM judge with content + policy definitions
4. Compare model decision vs judge decision
5. Compute confusion matrix, precision, recall per category
6. Log results to MLflow experiment ``"online_eval_responsible_ai"``
7. Write metrics to Databricks table for dashboard queries

Analytics aggregation (``rai_analytics.py``)
==============================================

``RAIAnalyticsAggregator``:

* Pulls production events from analytics API
* Aggregates by: harm_category, outcome, cloud_id, time_bucket
* Computes rolling metrics (7-day, 30-day windows)
* Identifies categories with high FPR or FNR trends
* Outputs: ``{category: str, fpr_7d: float, fnr_7d: float, sample_count: int}``

Eval utils (``eval_utils.py``)
================================

Helper functions for online eval pipeline:

* ``sample_events(events_df, n_per_category, seed)`` — stratified sampling
* ``format_judge_input(event)`` — converts GASv3 event to judge prompt input
* ``parse_judge_output(judge_response)`` — extracts structured verdict from LLM response
* ``compute_agreement_rate(model_decisions, judge_decisions)`` — agreement metric
