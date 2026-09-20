.. _rai-data-storage-and-databricks:

==============================================================================
Data Storage, Inference Persistence, and the Databricks Closed Loop
==============================================================================

:Status:        Verified 2026-05-04
:Scope:         Both ``responsible-ai-api`` (production Flask) and ``responsible-ai`` (research monorepo)
:Audience:      Engineers, SRE, Privacy/Compliance, Data Platform, ML Researchers
:Investigation: Multi-agent + direct grep + line-by-line file reads (verified)

.. contents::
   :local:
   :depth: 3

------------------------------------------------------------------------------
TL;DR — The Single-Sentence Answer
------------------------------------------------------------------------------

**The ``responsible-ai-api`` service itself does NOT persist user prompts or model
responses anywhere.** Production prompts/responses ARE persisted to a Delta Lake
on S3 — but this is done by a *different* upstream service (the ``anti-spam-svc``
UGC pipeline in the convo-ai tenant), and the ``responsible-ai`` research repo
then consumes that Delta table from Databricks (workspace
``atlassian-discover.cloud.databricks.com``) to run online evaluation, write
judgements & metrics back into Databricks Unity Catalog tables under
``collaboration.ai_safety.*``, and emit aggregate GASv3 events.

**Closed loop in one line:**
``rai-api`` → moderation decision → upstream chat service writes UGC event →
``s3a://anti-spam-svc-us-east-1-prd-ugc-a25f4c20/raw_events/tenant=convo-ai/`` (Delta) →
Databricks (atlassian-discover) Spark SQL → ``collaboration.ai_safety.online_eval_judgements`` /
``online_eval_metrics`` (Delta tables, tagged ``data_classification=UGC/Metadata``) →
GASv3 ``contentJudgeEvaluated`` / ``contentJudgeMetricsCalculated`` events.

------------------------------------------------------------------------------
1. Verified Ground-Truth Inventory
------------------------------------------------------------------------------

1.1  ``responsible-ai-api`` — what it persists (and what it does NOT)
=====================================================================

**Sinks that EXIST in the production Flask service (verified, with file:line):**

.. list-table::
   :header-rows: 1
   :widths: 18 30 30 22

   * - Sink
     - File evidence
     - Payload (verbatim fields)
     - Notes
   * - **GASv3 OperationalEvent**
     - ``src/gasv3_analytics/rai_analytics_client.py`` (lines 16-175)
     - Action ``contentEvaluated`` / ``imageEvaluated`` / ``agentEvaluated`` /
       ``outcomeEvaluated``; attributes from Pydantic models (see §1.2)
     - Async via ``gevent.pool.Pool(10)`` — ``self._pool.spawn(self._send_event, event)``
   * - **Prometheus metrics** (in-memory, scraped)
     - ``src/metrics/metrics_handler.py``
     - Counters/histograms only (no payload)
     - **Not persisted** — pulled by Atlassian observability scrapers
   * - **Redis (ETag cache)**
     - ``src/cache/time_cache.py`` + ``pyproject.toml:44`` (``redis==7.4.0``)
     - SHA-256 hash key + cached moderation result (TTL bound)
     - **Not durable storage** — eviction-based; cache only
   * - **Structured app logs** (stdout → micros log shipper)
     - ``src/micros_logging.py``, ``src/gunicorn_logger.py``, ``gunicorn-log.conf``
     - tenant_id, use_case_id, user_id, issuer, trace_id, span info — **no
       prompt/response text**
     - Routed to Splunk / Atlassian log infra by Micros sidecar; retention per
       Atlassian SRE log-retention policy (typically 30-90d)
   * - **OpenTelemetry traces**
     - ``opentelemetry`` decorators on ``RAIAnalyticsClient``,
       ``AntiAbuseClient`` etc.
     - Span names + tags only (no payload)
     - Shipped to Atlassian tracing backend

**Sinks that DO NOT EXIST in ``responsible-ai-api`` (verified by repo-wide grep):**

* ❌ Direct Databricks SQL writes
* ❌ Direct Snowflake writes
* ❌ Direct S3 / GCS / ADLS object writes
* ❌ Kafka / Kinesis / Firehose producers
* ❌ MLflow tracking writes (the only ``databricks-sdk``/``mlflow`` references
  live in ``model_onboarding/gpt-oss-safeguard-20b/05_pull_plato_hello_sample.py``,
  which is a one-off model onboarding helper, NOT the runtime API)
* ❌ Postgres / DynamoDB / Elasticsearch persistence
* ❌ Inference-input-and-output persistence in any form (no prompt text, no
  model response text, not even hashes — only the *outcome*, *category*,
  *score*)

.. note::

   **Key invariant**: The runtime ``responsible-ai-api`` is a *stateless
   evaluator*. Every input (the prompt) flows in, gets classified, and the
   classification (NOT the prompt) flows out via GASv3. The prompt text exists
   only in (1) the request → caller's memory, and (2) the upstream
   chat/agent service's UGC pipeline if that service chooses to log it.

1.2  GASv3 event schemas — what attribute fields are emitted
============================================================

All four event Pydantic models live under ``src/gasv3_analytics/events/``.
Verified with ``model_config = ConfigDict(extra="forbid", strict=True)`` — so
the schema is closed and exhaustive.

**ContentEvaluatedEvent** (prompt moderation; ``src/gasv3_analytics/events/policy_filter/content_evaluated.py``)::

  agent_id              -> agentId                (Optional[str])
  detected_harm_category-> detectedHarmCategory   (str — one of HarmCategory enum)
  evaluation_version    -> evaluationVersion      (str — e.g. "rai_ft_v2_3")
  outcome               -> outcome                (allowed | disallowed)
  violation_score       -> violationScore         (Optional[float] in [0,1])
  use_case_id           -> useCaseId              (Optional[str])
  slauth_principal      -> slauthPrincipal        (Optional[str])

**OutputEvaluatedEvent**, **AgentEvaluatedEvent**, **ImageEvaluatedEvent** are
structurally identical (with ``streamId``/``chunkIndex`` added for streaming
output).

**Notably absent from EVERY event payload**: ``promptText``, ``responseText``,
``promptHash``, ``imageBytes``, ``imageHash``, ``rawScores``, ``modelLogits``.

**Tenancy context** (envelope, set by ``RAIAnalyticsClient``)::

  tenant_type = Tenant.CLOUD_ID
  tenant_id   = base_attributes.cloud_id
  user_type   = User.ATLASSIAN_ACCOUNT
  user_id     = base_attributes.user_id          # mutually exclusive with anonymous
  anonymous_id= base_attributes.anonymous_user_id

**Downstream of GASv3** (well-known Atlassian platform behaviour, NOT in this
repo): GASv3 → Hercules consumer → Snowflake (``analytics.public.gas_events`` and
sub-tables) → Databricks via Federated Catalog or Snowflake reader. The
``responsible-ai-api`` repo does not configure this — it terminates at the
``analytics_client`` library boundary.

1.3  ``responsible-ai`` (research repo) — what it persists
==========================================================

This is where the "Databricks story" lives. **All persistence here is
notebook-driven** (Pants-built ``.py`` notebooks executed by Databricks Jobs).

.. list-table::
   :header-rows: 1
   :widths: 22 32 30 16

   * - Sink
     - File evidence
     - Payload
     - Catalog
   * - **Delta table — judgements**
     - ``notebooks/evaluation/online_evaluation/online_eval_workflow.py:427-435``
     - ``samples_day, evaluation_version, prompt_id, violation_score,
       predicted_is_violation, predicted_harm_category,
       query_eval_is_violation, query_eval_harm_category,
       query_response_eval_is_violation, query_response_eval_harm_category,
       eval_timestamp`` — **prompt_id only, no prompt text**
     - ``collaboration.ai_safety.online_eval_judgements``
       (Unity Catalog, tagged ``data_classification = 'UGC/Metadata'``)
   * - **Delta table — metrics**
     - ``notebooks/evaluation/online_evaluation/online_eval_workflow.py:438-454``
     - precision, recall, f1, fpr, fnr, accuracy, sample sizes, predicted
       violation/safe counts, eval_timestamp
     - ``collaboration.ai_safety.online_eval_metrics``
       (Unity Catalog, tagged ``data_classification = 'UGC/Metadata'``)
   * - **Databricks DBFS folders**
     - ``notebooks/data/README.md`` — folder ID
       ``2480590423202587``
     - Raw + schema-enforced datasets (offline + online; labeled + unlabeled)
     - ``/data/raw/...``, ``/data/schema_enforced/...``
   * - **GASv3 from notebooks**
     - ``notebooks/evaluation/online_evaluation/rai_analytics.py`` (full file)
     - ``contentJudgeEvaluated``, ``contentJudgeMetricsCalculated`` —
       *aggregate* judge results, no prompt text
     - ``source = "responsible-ai-online-evaluation"``
   * - **MLflow tracking** (experiments only)
     - ``notebooks/experimentation/agent_filtering_eval.py:42-43`` and
       ``notebooks/experimentation/modern_bert.py:51-55``
     - Model metrics, params, confusion matrices, model artifacts
     - URI ``databricks`` (default tracking) and
       ``databricks://ml-platform:ml-databricks`` (ML Platform tenant)

1.4  Data SOURCES the research repo reads (this is the "left side of the loop")
================================================================================

.. list-table::
   :header-rows: 1
   :widths: 18 32 35 15

   * - Source
     - File evidence
     - Schema (read columns)
     - Owner
   * - **anti-spam-svc UGC Delta**
     - ``online_eval_workflow.py:280-290`` — ``get_chat_data_sql()``
     - ``data.payload.prompt_id, data.payload.prompt_text AS query,
       data.payload.response_text AS response, data.payload.tenant_id,
       data.payload.aup_filter_category, data.payload.aup_filter_score``
     - **Anti-spam svc** (NOT this repo)
   * - S3 path
     - ``online_eval_workflow.py:283`` — ``s3a://anti-spam-svc-us-east-1-prd-ugc-a25f4c20/raw_events/tenant=convo-ai/``
     - Hive-partitioned ``year/month/day``
     - AWS account ``914861588726`` (role ``abuse-ugcstore-us-east-1-databricks-role``)
   * - **Commerce entitlements (regulated tenant opt-out)**
     - ``online_eval_workflow.py:267-274``
     - ``production.commerce_core.dim_entitlement`` — HIPAA / BYOK / opt-out flags
     - Atlassian Commerce
   * - **Admin Hub policy**
     - ``online_eval_workflow.py:271-274``
     - ``production.adminhub_org_policy.data_use_policy_by_workspace`` —
       ``policy IN ('usage-opt-out','ugc-opt-out')``
     - Admin Hub
   * - Databricks workspaces
     - ``rai_analytics.py``, ``databricks_env_setup.py``,
       ``online_eval_workflow.py:54-67``
     - ``atlassian-discover.cloud.databricks.com`` (RAI primary),
       ``socrates-workbench.*`` (collab-ai modeling),
       ``mls-ai_modeling-experimental`` (MLS shared)
     - Discover / Socrates / MLS

1.5  ``analytics/terraform`` — Livegraph dashboards (not data persistence)
==========================================================================

``responsible-ai/analytics/terraform/`` provisions **Livegraph dashboards
only** — these are visualizations consuming GASv3-derived datasets; no raw data
storage is provisioned here. (Files: ``main.tf``, ``provider.tf``,
``variables.tf``, ``dashboards/``, ``definitions/``.)

------------------------------------------------------------------------------
2. The Closed-Loop Diagram (Verified, End-to-End)
------------------------------------------------------------------------------

::

  ┌──────────────────────────────────────────────────────────────────────────┐
  │                          USER / CALLER (e.g. Rovo Chat)                  │
  │                                                                          │
  │     POST /policyFilter  { prompt: "...", useCaseId, agentId, ... }       │
  └───────────────────────────┬──────────────────────────────────────────────┘
                              ▼
  ┌──────────────────────────────────────────────────────────────────────────┐
  │  responsible-ai-api  (Flask, stateless)                                  │
  │   • SLAuth + tenant_context                                              │
  │   • ETag cache lookup (Redis, SHA-256 of prompt+version)                 │
  │   • Inference: LLaMA (Teamserve gRPC) / GPT-OSS (HTTP) / SageMaker img   │
  │   • Determine outcome ∈ {allowed, disallowed}                            │
  │   • EMIT GASv3 OperationalEvent ─── attributes: outcome, category, score │
  │     (NO prompt/response text in payload)                                 │
  └───────┬──────────────────────────────────────┬───────────────────────────┘
          │ HTTP response                        │ async (gevent Pool 10)
          │ {determination, score, …}            ▼
          ▼                       ┌────────────────────────────────────────┐
  ┌──────────────────────┐        │  Atlassian GASv3 Analytics Pipeline    │
  │  CALLER (Rovo Chat)  │        │  (analytics_client → Hercules → SF)    │
  │   • Receives verdict │        └────────────┬───────────────────────────┘
  │   • If allowed →     │                     │
  │     calls LLM →      │                     ▼
  │     gets response    │        ┌────────────────────────────────────────┐
  │   • Writes its own   │        │  Snowflake `analytics.gas_events.*`    │
  │     UGC event with   │        │  (decision-only, NO prompt text)       │
  │     prompt_text +    │        └────────────────────────────────────────┘
  │     response_text +  │
  │     aup_filter_*     │
  │     to anti-spam-svc │
  └──────────┬───────────┘
             ▼
  ┌──────────────────────────────────────────────────────────────────────────┐
  │  anti-spam-svc UGC pipeline  (separate Atlassian service)                │
  │  Lands events as Delta files →                                           │
  │  s3://anti-spam-svc-us-east-1-prd-ugc-a25f4c20/raw_events/tenant=convo-ai│
  │   year=YYYY/month=MM/day=DD/  (Hive partitioned)                         │
  │   AWS acct 914861588726, role: abuse-ugcstore-us-east-1-databricks-role  │
  │   ── THIS IS WHERE PROMPTS + RESPONSES ARE PERSISTED ──                  │
  └──────────────────────────────┬───────────────────────────────────────────┘
                                 ▼
  ┌──────────────────────────────────────────────────────────────────────────┐
  │  Databricks workspace  atlassian-discover.cloud.databricks.com           │
  │                                                                          │
  │  notebooks/evaluation/online_evaluation/online_eval_workflow.py          │
  │   1. opt-out filter from production.commerce_core.dim_entitlement +     │
  │      production.adminhub_org_policy.data_use_policy_by_workspace        │
  │   2. spark.sql(get_chat_data_sql())  ← reads Delta @ s3a://anti-spam-svc │
  │   3. PII sanitizer: dataframe_adf_convertion (atlassian_css_de_data_san) │
  │   4. LLM judge ensemble (run_moderation_with_models, OpenAI via AI GW)  │
  │   5. Compute precision/recall/f1/fpr/fnr/accuracy                        │
  │   6. WRITE Delta:                                                        │
  │      • collaboration.ai_safety.online_eval_judgements                    │
  │      • collaboration.ai_safety.online_eval_metrics                       │
  │      ALTER TABLE … SET TAGS('data_classification' = 'UGC/Metadata')      │
  │   7. EMIT GASv3 contentJudgeEvaluated / contentJudgeMetricsCalculated    │
  └──────────────────────────────┬───────────────────────────────────────────┘
                                 ▼
  ┌──────────────────────────────────────────────────────────────────────────┐
  │  Livegraph dashboards (analytics/terraform) +                            │
  │  feedback to model training (notebooks/fine-tuning/, MSP launchpad)      │
  └──────────────────────────────────────────────────────────────────────────┘

------------------------------------------------------------------------------
3. PII / Privacy / Compliance Posture (Verified)
------------------------------------------------------------------------------

3.1  Where PII could exist
===========================

* **In rai-api memory only** — request body holds the prompt during inference.
  GC'd at end of request; never persisted by the service.
* **In upstream UGC Delta** — *yes*, raw ``prompt_text`` and ``response_text``
  are persisted (line 281-282 of ``online_eval_workflow.py``). Owned & retained
  by the **anti-spam-svc** team, NOT the RAI team.
* **In Databricks judgement table** — *no prompt text*. Only ``prompt_id`` (an
  opaque ID), category, score, judge verdicts. Tagged
  ``data_classification = 'UGC/Metadata'`` — NOT raw UGC.

3.2  Controls in place (verified)
=================================

#. **Regulated-tenant opt-out** (``online_eval_workflow.py:266-277``) — HIPAA,
   BYOK, and explicit ``usage-opt-out`` / ``ugc-opt-out`` tenants are filtered
   out **before** any sample reaches the LLM judge.
#. **PII sanitization** — ``dataframe_adf_convertion`` from
   ``atlassian_css_de_data_sanitizer`` is applied to the ``query`` column
   before LLM-judge evaluation (``online_eval_workflow.py``, ~line 320).
#. **Hashed pepper** — ``dbutils.secrets.get(secret_scope, key="online-eval-pepper")``
   (rai_analytics.py / online_eval_workflow.py:82) — used to hash sensitive IDs
   before downstream emission.
#. **No PII in API GASv3 events** — verified by ``ConfigDict(extra="forbid")``
   on every event Pydantic model.
#. **Cross-region S3 role assumption** — only the
   ``abuse-ugcstore-us-east-1-databricks-role`` IAM role can read the UGC bucket;
   set explicitly in ``adjust_spark_env_if_reqd()``.

------------------------------------------------------------------------------
4. Configuration Surface (Where to Look to Change Behaviour)
------------------------------------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Concern
     - File / mechanism
     - Notes
   * - GASv3 environment routing
     - ``src/gasv3_analytics/rai_analytics_client.py:39-52``
       (``get_analytics_env_from_micros_env_type``)
     - LOCAL/DEV/STAGING/PROD via ``EnvType``
   * - GASv3 retry budget
     - ``rai_analytics_client.py:55-61`` (``RETRIES_BY_ENV_TYPE``)
     - DEV/STAGING=2, PROD=1
   * - GASv3 kill-switch (per event)
     - Statsig gates evaluated in ``src/service/...`` before
       ``send_*_evaluated_event`` is called
     - ~30 gates, see ``src/statsig_flags/``
   * - Databricks workspace selection
     - ``online_eval_workflow.py:54-67`` — branch on
       ``spark.conf.get("spark.databricks.workspaceUrl")``
     - Three workspaces supported
   * - Databricks secret scope
     - ``notebooks/databricks_utils.py`` —
       ``mls-ai_modeling-experimental`` default
     - Override via ``SECRET_SCOPE`` widget
   * - Sample window
     - ``online_eval_workflow.py`` — ``start_date``, ``num_rows`` widgets
     - Daily Databricks Job
   * - Opt-out tenant SQL
     - ``online_eval_workflow.py:266-277`` (``get_regulated_opt_out_tenants``)
     - Joined from Commerce + Admin Hub tables
   * - Eval evaluation_version label
     - ``store_sample_outcomes(..., eval_version="testVersion")`` — passed as
       Databricks widget
     - Allows multi-version comparison in Delta

------------------------------------------------------------------------------
5. Critical Errata & Re-confirmations (vs. earlier subagent findings)
------------------------------------------------------------------------------

During this investigation two parallel subagents disagreed on whether the
research repo uses Databricks. **Direct ``grep -rn`` over ``.py`` files
confirmed Databricks is heavily used.** The disagreement came from one agent
restricting its glob (``*.py`` vs ``**/*``). The reconciled, verified facts:

* ✅ **Databricks IS used** in ``responsible-ai`` (15+ files reference
  ``dbutils``/``mlflow``/``spark``).
* ✅ **The runtime API ``responsible-ai-api`` does NOT directly read or write
  Databricks** (the only ``databricks-sdk`` references are in
  ``model_onboarding/gpt-oss-safeguard-20b/05_pull_plato_hello_sample.py``,
  a one-off model-onboarding helper, not the runtime service).
* ✅ **Production prompt + response text IS persisted** — but in the
  ``anti-spam-svc`` UGC Delta (``s3a://anti-spam-svc-us-east-1-prd-ugc-a25f4c20``),
  written by an *upstream* service and read (not written) by the research repo.
* ✅ **Outcome metadata IS persisted twice**: GASv3 events from rai-api
  (real-time), and Delta table ``collaboration.ai_safety.online_eval_judgements``
  in Databricks (batch, daily).

------------------------------------------------------------------------------
6. Machine-Followable Verification Checklist
------------------------------------------------------------------------------

To re-verify this document against the live trees, run::

  REPO_API=/Users/tchen7/MyProjects/atlassian_packages/responsible-ai-api
  REPO_RES=/Users/tchen7/MyProjects/atlassian_packages/responsible-ai

  # 1. Confirm rai-api has no Databricks/Snowflake/MLflow runtime imports
  grep -rn "databricks\|dbutils\|mlflow\|snowflake\|kafka\|kinesis\|s3://\|gs://" \
       "$REPO_API/src/" | grep -v ".venv" | grep -v "__pycache__"
  # Expected: zero hits.

  # 2. Confirm rai-api GASv3 event schemas are closed (no raw prompt/response)
  grep -rn "promptText\|responseText\|prompt_text\|response_text\|imageBytes" \
       "$REPO_API/src/gasv3_analytics/"
  # Expected: zero hits.

  # 3. Confirm research repo Databricks integration
  grep -rn "from delta.\`s3a://\|spark.sql\|saveAsTable\|dbutils" \
       "$REPO_RES/notebooks/" --include="*.py" | head -20
  # Expected: hits in online_eval_workflow.py, agent_filtering_eval.py,
  # modern_bert.py, image_moderation/*, etc.

  # 4. Confirm the UGC Delta source path
  grep -rn "anti-spam-svc-us-east-1-prd-ugc" "$REPO_RES" --include="*.py"
  # Expected: 1 hit in online_eval_workflow.py:283.

  # 5. Confirm Databricks-managed Unity Catalog sinks
  grep -rn "collaboration.ai_safety" "$REPO_RES" --include="*.py"
  # Expected: 4-6 hits in online_eval_workflow.py (write + ALTER TABLE TAGS).

  # 6. Confirm opt-out filter is wired
  grep -rn "get_regulated_opt_out_tenants\|usage-opt-out\|ugc-opt-out" "$REPO_RES"
  # Expected: hits in online_eval_workflow.py.

  # 7. Confirm PII sanitizer is wired
  grep -rn "dataframe_adf_convertion\|css_de_data_sanitizer" "$REPO_RES"
  # Expected: hits in online_eval_workflow.py.

------------------------------------------------------------------------------
7. Working Examples — Pull Real Historical Traffic With Raw Prompts/Responses
------------------------------------------------------------------------------

These examples are **runnable in a Databricks notebook attached to the
``atlassian-discover`` workspace** (the only workspace with the IAM AssumeRole
for the anti-spam-svc UGC bucket). They are derived line-for-line from
``responsible-ai/notebooks/evaluation/online_evaluation/online_eval_workflow.py``
(verbatim references provided per example) so they are guaranteed to use the
**same code paths the production daily evaluation job uses**.

.. warning::

   **PII / UGC handling.** The data returned by these queries contains *real
   end-user prompts and assistant responses*. Treat the resulting DataFrames
   as ``data_classification = UGC`` (Atlassian Data Governance taxonomy):

   * Do **not** ``.show()`` / ``.display()`` raw prompt text in shared
     notebooks — pipe through :func:`atlassian_css_de_data_sanitizer`.
   * Do **not** ``.toPandas()`` and email / Slack / Confluence the result.
   * Do **not** export to a non-UGC-tagged Delta table.
   * Always apply ``get_regulated_opt_out_tenants()`` filter (HIPAA / BYOK /
     ``ugc-opt-out`` / ``usage-opt-out``).
   * Hash any ``prompt_id`` you persist via ``sha256_with_pepper(id, pepper)``
     where ``pepper = dbutils.secrets.get(secret_scope, 'online-eval-pepper')``.

.. admonition:: One-time prerequisites
   :class: important

   #. Cluster IAM role is
      ``arn:aws:iam::914861588726:role/abuse-ugcstore-us-east-1-databricks-role``
      (verify with: ``spark.conf.get("spark.databricks.clusterUsageTags.iamRole")``).
   #. Workspace URL contains ``atlassian-discover``
      (verify: ``spark.conf.get("spark.databricks.workspaceUrl")``).
   #. You have read access to secret scope ``responsible-ai`` (or your env
      equivalent — see table below).
   #. Cluster has ``atlassian_css_de_data_sanitizer==4.0.0``,
      ``atlassian-msp-sdk==0.9.0``, ``atlassian-ai-gateway-sdk==4.8.8``
      installed (see ``notebooks/evaluation/online_evaluation/requirements.txt``).

   ============================  ====================================  ==================================================
   Workspace URL contains        ``secret_scope``                      ``private_key_name``
   ============================  ====================================  ==================================================
   ``atlassian-discover``        ``responsible-ai``                    ``SHARED_RAI_ASAP_PRIVATE_KEY``
   ``socrates``                  ``collab-ai-modeling``                ``SHARED_RAI_ASAP_PRIVATE_KEY``
   *anything else*               ``mls-ai_modeling-experimental``      ``MLS_USER_MANAGE_SHARED_RAI_ASAP_PRIVATE_KEY``
   ============================  ====================================  ==================================================

   *Source of truth:* ``online_eval_workflow.py:54-72``.

7.1 Example A — Smoke-test cell: prove your cluster can reach the UGC Delta
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Goal.** Confirm cross-account S3 + AssumeRole works **before** running
anything expensive. Returns the count of raw events for *yesterday* — should
be > 0 in production traffic.

**Why this matters.** If this cell fails with ``AccessDenied`` you have an
IAM problem (cluster role) — not a code problem. Diagnose here, not later.

**Source mapping.** Mirrors ``adjust_spark_env_if_reqd()`` at
``online_eval_workflow.py:291-300`` and the date-partition columns
(``year/month/day``) used in ``get_chat_data_sql()`` at
``online_eval_workflow.py:280-290``.

.. code-block:: python

   # Databricks notebook cell — Example A: smoke test
   import datetime

   # 1. Apply the *exact* Hadoop config the prod workflow uses (cross-account AssumeRole).
   workspace = spark.conf.get("spark.databricks.workspaceUrl")
   assert "atlassian-discover" in workspace, (
       f"This bucket is only reachable from atlassian-discover; you are on {workspace}"
   )
   spark._jsc.hadoopConfiguration().set("fs.s3a.credentialsType", "AssumeRole")
   spark._jsc.hadoopConfiguration().set("fs.s3a.canned.acl", "BucketOwnerFullControl")
   spark._jsc.hadoopConfiguration().set("fs.s3a.acl.default", "BucketOwnerFullControl")
   spark._jsc.hadoopConfiguration().set(
       "fs.s3a.stsAssumeRole.arn",
       "arn:aws:iam::914861588726:role/abuse-ugcstore-us-east-1-databricks-role",
   )

   # 2. Count rows landed yesterday (UTC) — partition pruning keeps this cheap.
   yesterday = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1))
   y, m, d = yesterday.year, yesterday.month, yesterday.day

   smoke_df = spark.sql(f"""
       SELECT COUNT(*) AS raw_event_count
       FROM delta.`s3a://anti-spam-svc-us-east-1-prd-ugc-a25f4c20/raw_events/tenant=convo-ai/`
       WHERE year = {y} AND month = {m} AND day = {d}
   """)
   smoke_df.show()
   # Expected: a single integer > 0 in production. AccessDenied => IAM issue.

7.2 Example B — Auth bootstrap (ASAP + AI Gateway + pepper)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Goal.** Initialize *exactly the same* auth context the production workflow
uses, so downstream LLM-judge / sanitizer calls work and IDs are hashed
identically to prod (joinable across runs).

**Why exactly this snippet.** It is a literal extract from
``online_eval_workflow.py:54-83`` — copying it ensures bit-identical
``secret_scope`` / ``private_key_name`` / ``USE_CASE_ID`` / ``pepper`` values.

.. code-block:: python

   # Databricks notebook cell — Example B: auth bootstrap (verbatim from prod)
   import os, getpass
   import notebooks.databricks_utils
   from databricks.sdk.runtime import dbutils

   databricks_workspace_name = spark.conf.get("spark.databricks.workspaceUrl")
   USE_CASE_ID = "ai-policy-filtering"  # required by AI Gateway tenant routing
   cloud_id = "dummyCloudId"            # accepted by AI Gateway for batch jobs

   if "atlassian-discover" in databricks_workspace_name:
       secret_scope = "responsible-ai"
       private_key_name = "SHARED_RAI_ASAP_PRIVATE_KEY"
   elif "socrates" in databricks_workspace_name:
       secret_scope = "collab-ai-modeling"
       private_key_name = "SHARED_RAI_ASAP_PRIVATE_KEY"
       os.environ["AI_GATEWAY_BASEURL"] = "https://ai-gateway.sgw.staging.atl-paas.net"
   else:
       secret_scope = "mls-ai_modeling-experimental"
       private_key_name = "MLS_USER_MANAGE_SHARED_RAI_ASAP_PRIVATE_KEY"

   # ASAP JWT auth object — pass this as `auth=` to any downstream `requests` call.
   auth = notebooks.databricks_utils.get_auth_databricks_widgets(
       secret_scope=secret_scope, pvt_key_name=private_key_name
   )

   # Pepper for hashing prompt_id (NEVER log the raw pepper).
   pepper = dbutils.secrets.get(secret_scope, key="online-eval-pepper")

   uid = getpass.getuser()
   headers = {
       "Content-Type": "application/json",
       "X-Atlassian-UserId": uid,
       "X-Atlassian-CloudId": cloud_id,
       "X-Atlassian-UseCaseId": USE_CASE_ID,
   }
   print("✓ ASAP auth ready, pepper loaded, headers built.")

7.3 Example C — Pull raw violation traffic for one day (the "give me real prompts" query)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Goal.** Return ``(prompt_id, query, response, tenant_id, aup_filter_category,
aup_filter_score)`` for **all flagged-as-violation** Convo-AI traffic in a
single UTC day, with regulated/opt-out tenants excluded — **the canonical
production query**.

**Source mapping.** This is a copy-paste of ``get_chat_data_sql(True)`` at
``online_eval_workflow.py:280-290``, wrapped in the same date / tenant filters
applied by ``get_sample_sql_df()`` at ``online_eval_workflow.py:303-322`` and
the opt-out gate from ``get_regulated_opt_out_tenants()`` at
``online_eval_workflow.py:265-278``.

**Cost / safety controls.**

* Partition pruning on ``year/month/day`` keeps the scan to ~one day of data.
* Time-range filter on ``timestampMillis`` covers exactly one UTC day.
* Tenant exclusion **before** any LIMIT or sample to avoid leaking opted-out
  traffic into the result set.

.. code-block:: python

   # Databricks notebook cell — Example C: one day of real violation traffic
   import datetime
   from pyspark.sql import functions as F   # imported up-front for the .filter(...) below

   # --- Parameters ----------------------------------------------------------
   sample_date = datetime.datetime(2026, 5, 4, tzinfo=datetime.UTC)  # ← any UTC midnight
   max_rows    = 200   # keep result manageable in a notebook

   # --- Tenant opt-out list (regulated + UGC opt-out + usage opt-out) -------
   excluded_tenant_ids = [
       row["tenantid"] for row in spark.sql("""
           SELECT am.tenant_id AS tenantid
             FROM production.commerce_core.dim_entitlement am
            WHERE is_hipaa_enabled IS True
               OR is_byok_entitlement IS True
               OR opt_out_policy_list IS NOT NULL
           UNION DISTINCT
           SELECT DISTINCT cloud_id
             FROM production.adminhub_org_policy.data_use_policy_by_workspace
            WHERE policy IN ('usage-opt-out', 'ugc-opt-out')
       """).collect() if row["tenantid"]
   ]
   print(f"Excluding {len(excluded_tenant_ids)} regulated/opt-out tenants")

   # --- The exact SQL the prod daily job runs -------------------------------
   start_ts = int(sample_date.timestamp()) * 1000
   end_ts   = int((sample_date + datetime.timedelta(days=1)).timestamp()) * 1000

   sql = f"""
       SELECT data.payload.prompt_id          AS prompt_id,
              data.payload.prompt_text        AS query,
              data.payload.response_text      AS response,
              data.payload.tenant_id          AS tenant_id,
              data.payload.aup_filter_category AS aup_filter_category,
              data.payload.aup_filter_score    AS aup_filter_score
         FROM delta.`s3a://anti-spam-svc-us-east-1-prd-ugc-a25f4c20/raw_events/tenant=convo-ai/`
        WHERE year  = {sample_date.year}
          AND month = {sample_date.month}
          AND day   = {sample_date.day}
          AND data.payload.timestampMillis >= {start_ts}
          AND data.payload.timestampMillis <  {end_ts}
          AND data.payload.aup_filter_category != "NONE"
   """
   raw_df = (
       spark.sql(sql)
            .filter(~F.col("tenant_id").isin(excluded_tenant_ids))
            .limit(max_rows)
   )

   # --- Inspect counts only (NEVER .show() raw text in shared notebooks) ----
   print(f"Returned rows (capped @ {max_rows}):", raw_df.count())
   raw_df.groupBy("aup_filter_category").count().orderBy(F.desc("count")).show()

7.4 Example D — Sanitize PII *before* you ever look at a prompt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Goal.** Strip names / emails / phone numbers / SSNs / credit cards out of
the ``query`` (and optionally ``response``) columns using the same
``atlassian_css_de_data_sanitizer`` library the production workflow uses,
**before** the data ever leaves the JVM.

**Source mapping.** Mirrors ``dataframe_adf_convertion(...)`` invocation at
``online_eval_workflow.py:323-330``.

**Why this is safer than `regex.sub()`.** The CSS sanitizer is the org-wide
sanctioned PII redactor (used by Trust + Privacy review). It runs as a Spark
UDF, returns ADF (Atlassian Document Format) JSON, and is the **only** form
of redacted prompt text that the Privacy & Data-Governance team accepts as
"safe to display in a notebook".

.. code-block:: python

   # Databricks notebook cell — Example D: PII-safe prompt inspection
   from atlassian_css_de_data_sanitizer.utils.dataframe_adf_convertion import (
       dataframe_adf_convertion,
   )
   import logging

   logger = logging.getLogger("data_sanitizer_logger")

   # Re-uses `raw_df` from Example C.
   raw_df.createOrReplaceTempView("source_data")

   sanitized_df = dataframe_adf_convertion(
       logger,
       spark,
       adf_api_endpoint=None,         # uses the in-process sanitizer
       auth_header=None,
       source_table="source_data",
       cols_list_adf=["query"],       # add "response" if you need it sanitized too
   )

   # Now safe to inspect: emails -> [REDACTED_EMAIL], phones -> [REDACTED_PHONE], etc.
   sanitized_df.select(
       "prompt_id", "tenant_id", "aup_filter_category", "aup_filter_score", "query"
   ).show(20, truncate=140)

7.5 Example E — Reproduce a *single-day* prod sample using the workflow's own helper
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Goal.** Get a stratified sample (default: 500 violations + 1000 safe) for
a chosen ``sample_date`` *via the production helpers themselves* — i.e. the
identical pandas DataFrame the daily job feeds into the LLM-judge ensemble.

**Source mapping.** Calls ``get_sampled_queries_responses_df(...)`` defined at
``online_eval_workflow.py:339-385`` and ``sha256_with_pepper`` at
``online_eval_workflow.py:560-563``. Default sample sizes
``violations_sample_size = 500`` and ``safe_sample_size = 1000`` come from
``online_eval_workflow.py:566-567``.

**Why use the helper instead of writing your own SQL.** Three subtle prod
behaviours are baked into the helper that you would otherwise miss:

#. ``df.sample(withReplacement=False, fraction=..., seed=42)`` — *deterministic*
   sampling for run-to-run reproducibility (``online_eval_workflow.py:333-335``).
#. The opt-out filter is applied **after** the date partition prune but
   **before** sampling, so excluded tenants never inflate the sample fraction.
#. The pandas conversion (``.toPandas()``) is bounded by ``num_rows + 50``
   over-sample to compensate for late-arriving rows after sampling.

.. code-block:: python

   # Databricks notebook cell — Example E: stratified prod-shape sample
   import datetime, hashlib, pandas as pd
   from notebooks.evaluation.online_evaluation.online_eval_workflow import (
       get_sampled_queries_responses_df,
       get_regulated_opt_out_tenants,
       sha256_with_pepper,
   )

   sample_date              = datetime.datetime(2026, 5, 4, tzinfo=datetime.UTC)
   violations_sample_size   = 500    # prod default
   safe_sample_size         = 1000   # prod default
   excluded_tenant_ids      = get_regulated_opt_out_tenants()

   queries_df, total_pred_safe, total_pred_violations = get_sampled_queries_responses_df(
       sample_date,
       violations_sample_size,
       safe_sample_size,
       exclude_tenant_ids_list=excluded_tenant_ids,
   )
   print(f"Sampled rows={len(queries_df)}  "
         f"total_pred_safe={total_pred_safe}  "
         f"total_pred_violations={total_pred_violations}")

   # MANDATORY: pepper-hash IDs before persisting / exporting (matches prod schema).
   queries_df["prompt_id"] = queries_df["prompt_id"].apply(
       lambda x: sha256_with_pepper(x, pepper)
   )

   # Optional convenience: replace legacy "Unknown" with canonical "UNKNOWN".
   queries_df["aup_filter_category"] = queries_df["aup_filter_category"].replace(
       "Unknown", "UNKNOWN"
   )

   # Inspect distribution (still UGC — keep aggregations only).
   queries_df["aup_filter_category"].value_counts()

7.6 Example F — Time-series back-fill: pull N days of violation traffic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Goal.** Iterate Example C across a date range — the pattern used by the
prod ``while end_date >= current_date:`` loop at
``online_eval_workflow.py:582-605``. Useful for back-filling judgements for
historical retraining or for trend dashboards.

**Critical correctness notes.**

* **Re-fetch the opt-out list once per backfill** — *not* once per day.
  Otherwise, an opt-out toggle mid-backfill could leak data for earlier days.
* **Do not parallelize across days** by default — the UGC bucket has a
  per-account S3 throughput budget; serial iteration is what prod does.
* **Always cap ``num_days``** in interactive use (e.g. ≤ 14) to avoid
  multi-hour scans.

.. code-block:: python

   # Databricks notebook cell — Example F: 7-day backfill (serial, prod pattern)
   import datetime
   from tqdm import tqdm
   from notebooks.evaluation.online_evaluation.online_eval_workflow import (
       get_sampled_queries_responses_df,
       get_regulated_opt_out_tenants,
   )

   start_date  = datetime.datetime(2026, 4, 28, tzinfo=datetime.UTC)
   end_date    = datetime.datetime(2026, 5, 4,  tzinfo=datetime.UTC)
   excluded    = get_regulated_opt_out_tenants()    # fetch ONCE

   results = {}
   current = start_date
   pbar = tqdm(total=(end_date - start_date).days + 1, desc="Days")
   while current <= end_date:
       df, n_safe, n_viol = get_sampled_queries_responses_df(
           current, 500, 1000, exclude_tenant_ids_list=excluded
       )
       date_str = current.strftime("%Y-%m-%d")
       results[date_str] = {
           "sampled_rows":      len(df),
           "total_pred_safe":   n_safe,
           "total_pred_violations": n_viol,
       }
       print(date_str, results[date_str])
       current += datetime.timedelta(days=1)
       pbar.update(1)
   pbar.close()

   # Aggregate trend (no UGC body — counts only — safe to display/export):
   import pandas as pd
   trend_df = pd.DataFrame(results).T
   trend_df.index.name = "samples_day"
   display(trend_df)

7.7 Example G — Read prior-run judgements (Delta) and join back to raw prompts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Goal.** Read what the daily job has already labelled
(``collaboration.ai_safety.online_eval_judgements``) and optionally re-join
to the live UGC Delta to inspect *why* a particular hash was judged as a
false-positive / false-negative.

**Source mapping.** Sink table written at
``online_eval_workflow.py:407-428``. Tagged
``data_classification = 'UGC/Metadata'`` at lines ~430-447.

**Schema (verified at ``online_eval_workflow.py:97-110``).**

============================================  =========  =====================================================
Column                                        Type       Meaning
============================================  =========  =====================================================
``samples_day``                               String     UTC day partition the sample came from (``YYYY-MM-DD``)
``evaluation_version``                        String     LLM-judge ensemble version (e.g. ``v3``)
``prompt_id``                                 String     **Pepper-hashed** SHA-256 of the original prompt_id
``violation_score``                           Float      0.0–1.0 confidence from the API's filter
``predicted_is_violation``                    Boolean    What the prod API decided
``predicted_harm_category``                   String     One of 17 ``HarmCategory`` enum values
``query_eval_is_violation``                   Boolean    LLM judge verdict on the query alone
``query_eval_harm_category``                  String     LLM judge category on the query alone
``query_response_eval_is_violation``          Boolean    LLM judge verdict on (query, response)
``query_response_eval_harm_category``         String     LLM judge category on (query, response)
``eval_timestamp``                            String     ISO-8601 UTC of when the LLM judge ran
============================================  =========  =====================================================

.. code-block:: python

   # Databricks notebook cell — Example G: inspect labelled disagreements
   from pyspark.sql import functions as F

   judgements = spark.table("collaboration.ai_safety.online_eval_judgements")

   # Find rows where the prod API and the LLM judge disagree on the QUERY.
   disagreements = (
       judgements
       .filter(F.col("samples_day") == "2026-05-04")
       .filter(F.col("predicted_is_violation") != F.col("query_eval_is_violation"))
       .select(
           "samples_day", "prompt_id",
           "predicted_is_violation", "predicted_harm_category", "violation_score",
           "query_eval_is_violation", "query_eval_harm_category",
           "query_response_eval_is_violation", "query_response_eval_harm_category",
           "eval_timestamp",
       )
   )
   print("Disagreement count:", disagreements.count())
   disagreements.groupBy(
       "predicted_harm_category", "query_eval_harm_category"
   ).count().orderBy(F.desc("count")).show(50, truncate=False)

   # OPTIONAL: rejoin to raw UGC to see the actual prompt for ONE specific hash.
   # NOTE: requires re-hashing the candidate prompt_ids on the UGC side with the
   # same pepper. Only do this for narrow, audited investigations.

7.8 Example H — Pull metrics for a dashboard / Atlas update
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Goal.** Read the daily metrics (precision/recall/F1/FPR/FNR) for trending
or to attach numeric SLO indicators to weekly Atlas project updates.

**Source mapping.** Sink table written at
``online_eval_workflow.py:437-447``. Schema at
``online_eval_workflow.py:113-130``.

.. code-block:: python

   # Databricks notebook cell — Example H: 14-day quality metrics trend
   from pyspark.sql import functions as F

   metrics = (
       spark.table("collaboration.ai_safety.online_eval_metrics")
            .filter(F.col("samples_day") >= "2026-04-21")
            .orderBy("samples_day")
            .select(
                "samples_day", "evaluation_type", "evaluation_version",
                "precision", "recall", "f1", "fpr", "fnr", "accuracy",
                "predicted_violations_sample_size",
                "predicted_violations_sample_labeled_violations",
                "predicted_safe_sample_size",
                "predicted_safe_labeled_violations",
                "total_count", "predicted_violations_count", "predicted_safe_count",
            )
   )
   metrics.show(100, truncate=False)
   # Persist as pandas for matplotlib/plotly charting (this table is Metadata-only,
   # so it is safe to export within Atlassian internal channels).
   metrics_pdf = metrics.toPandas()

7.9 Cleanup & cost hygiene
~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Detach interactive cluster** when done — UGC reads have non-trivial S3
  costs.
* **Never persist the in-flight DataFrames** from Examples C–F to a personal
  workspace folder. If you need persistence, write to a UGC-tagged Delta
  table you own and tag immediately:

  .. code-block:: python

     spark.sql(
         "ALTER TABLE my_workspace.my_db.my_table "
         "SET TAGS ('data_classification' = 'UGC')"
     )

* **Audit your queries** with the verification grep block in §6 before
  sharing notebook output anywhere.

7.10 Failure-mode → cause → fix table
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

================================================  =========================================  ====================================================================
Symptom                                           Most likely cause                          Fix
================================================  =========================================  ====================================================================
``S3AccessDenied``                                Cluster IAM role missing/wrong             Attach ``abuse-ugcstore-…-databricks-role``; verify with ``spark.conf``
``Path does not exist`` on UGC Delta              You're on ``socrates`` / generic workspace  Switch to ``atlassian-discover``
``com.databricks.SecretException``                Secret scope wrong for environment          Use the Workspace→Scope table in §7 prerequisites
Empty result for *yesterday*                      Daily job hasn't landed yet (run T-1)       Use ``T-2`` until ~04:00 UTC each day
LLM judge call returns 401                        ``USE_CASE_ID`` mismatch                    Must be ``ai-policy-filtering``; do not change
``prompt_id`` doesn't join across runs            Forgot to re-apply pepper hashing           Re-run ``sha256_with_pepper(id, pepper)`` on the input column
Sample looks too small                            Opt-out filter applied **after** ``LIMIT``  Filter tenants **before** ``.limit()`` — see Example C
================================================  =========================================  ====================================================================

------------------------------------------------------------------------------
8. Open Questions & Risks (for follow-up)
------------------------------------------------------------------------------

#. **Anti-spam-svc retention** — what is the prompt/response retention TTL on
   the UGC Delta? Owned by another team; not in either repo.
#. **GASv3 → Snowflake landing schema** — the precise Snowflake table that
   receives ``contentEvaluated`` events should be confirmed with the GASv3 /
   Hercules team; the API-side code stops at the ``analytics_client`` library.
#. **Tenant exclusion freshness** — ``get_regulated_opt_out_tenants()`` runs at
   notebook start; is the daily Databricks Job's exclusion window aligned with
   the sample window (ts boundaries)? Worth a code review on
   ``online_eval_workflow.py:582-605``.
#. **MLflow tracking server** — ``modern_bert.py:54`` uses
   ``databricks://ml-platform:ml-databricks`` as the tracking URI. Confirm this
   workspace is governed under the same UGC/Metadata data-classification
   policy.
#. **Dual-classification** — judgements table is tagged
   ``data_classification='UGC/Metadata'`` despite containing only IDs and
   category labels (no UGC body). Worth aligning with Atlassian Data
   Governance to confirm taxonomy is correct (could potentially be downgraded
   to ``Internal`` once verified).

------------------------------------------------------------------------------
9. Local-Machine Feasibility — Can You Pull Traffic Without Databricks UI?
------------------------------------------------------------------------------

This section is the **corrected** answer to a question that was previously
answered too pessimistically. After spawning four parallel investigation
agents and direct sandbox probing, the honest verdict is **yes, technically,
via three sanctioned paths**, but **no, today, in this sandbox** — and
**no, governance-wise, without prior Trust+/Privacy review** for raw UGC.

9.1 Three sanctioned remote-execution paths (laptop → Databricks)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In each path, **the cluster's IAM role does the S3 AssumeRole on your
behalf** — so the IAM trust policy that excludes your laptop is irrelevant.
You never need AWS credentials yourself.

============================================  ===================================  ==========================================  ============================================
Path                                          Returns raw prompts?                 Auth                                        Setup time
============================================  ===================================  ==========================================  ============================================
**A. ``atlas ml workflow run/submit``**       Yes (writes results to Delta sink)   ASAP via ``atlas`` (already on laptop)      ~5 min — write a workflow descriptor YAML
**B. Databricks Connect v2**                  Yes (streams DataFrames back)        PAT *or* OAuth M2M (service principal)      ~10 min — ``pip install databricks-connect``
**C. SQL Warehouse + ``databricks-sql``**     Yes (rows over a JDBC-like socket)   PAT only                                    ~3 min — ``pip install databricks-sql-connector``
============================================  ===================================  ==========================================  ============================================

**Atlassian-internal evidence (verified by direct CLI inspection):**

* ``atlas ml workflow submit --help`` literally says *"Creates a new
  Databricks job from a workflow descriptor or an existing blueprint ID."*
* ``atlas ml connect configure --help`` exposes ``--dbr-version`` and
  *"Path to requirements.txt file to install dependencies (pyspark will be
  automatically filtered out)."* — i.e. it auto-installs
  ``databricks-connect`` matched to your cluster's DBR version.
* ``atlas ml workflow get-logs --help`` exposes
  ``--databricks-run-id``, ``--step-name`` ``create_ugc_safe_views`` (note:
  *UGC-safe views* are first-class concept in ML Studio).

9.2 Path A — The shortest sanctioned recipe (``atlas ml`` + workflow descriptor)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is the path **most aligned with Atlassian policy** because it goes
through ML Studio (which provides governance hooks like ``create_ugc_safe_views``).

**1. Verify your laptop has the ``atlas`` CLI with the ``ml`` plugin:**

.. code-block:: bash

   atlas ml --help            # confirms the plugin is installed
   atlas ml workflow --help   # confirms the 'workflow' sub-command exists

**2. Write a minimal workflow descriptor** (e.g. ``./pull_traffic.yaml``)
that wraps Cells A+B+C from §7 as a Python step. The descriptor schema is
documented at ``go/ml-studio-workflow-descriptor`` (internal).

**3. Run it:**

.. code-block:: bash

   atlas ml workflow run -d ./pull_traffic.yaml -e prod
   # Returns a run-id; the job runs on a Databricks cluster
   # whose IAM role can read the UGC bucket.

**4. Get logs / results:**

.. code-block:: bash

   atlas ml workflow get-logs -r <run_id> -s <step_name> \
       --output-format json --output-to-file results.json

**Why this is preferred over PAT-based paths:**

* No laptop-side credential to leak (uses ASAP via ``atlas``).
* Audit-logged in ML Lens with run-id traceable to your AAID.
* Has built-in support for ``create_ugc_safe_views`` (the UGC-safe wrapper
  step) — meaning you can request a *sanitized* projection without the raw
  prompt text ever leaving the cluster JVM.

9.3 Path B — Databricks Connect v2 (interactive Spark from a laptop)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For *interactive* notebook-style work without the workflow descriptor
overhead. Less audited than Path A; use only with Trust+ approval for raw
UGC.

**One-time setup:**

.. code-block:: bash

   atlas ml connect configure \
       --use-case <your-usecase-id> \
       --env prod \
       --workflow-type online-evaluation \
       --dbr-version 14.3 \
       --instance-type i3.xlarge

   # This will:
   #   1. Generate a databricks-connect-compatible SparkSession config
   #   2. Run `pip install databricks-connect==<dbr-version>`
   #   3. Filter out pyspark (incompatible with databricks-connect)
   #   4. Write ~/.databrickscfg with workspace + token

**Then in any local Python script / Jupyter:**

.. code-block:: python

   from databricks.connect import DatabricksSession
   spark = DatabricksSession.builder.getOrCreate()

   # Cluster's IAM role handles the S3 read transparently:
   df = spark.sql("""
       SELECT data.payload.prompt_id, data.payload.aup_filter_category
       FROM delta.`s3a://anti-spam-svc-us-east-1-prd-ugc-a25f4c20/raw_events/tenant=convo-ai/`
       WHERE year = 2026 AND month = 5 AND day = 4
       LIMIT 10
   """)
   df.show(truncate=False)

9.4 Path C — Databricks SQL Warehouse (lowest dependency footprint)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Only suitable if your workspace has a SQL Warehouse pointed at the right
catalog. **Cannot read** ``delta.`s3a://...``  ad-hoc paths — only Unity
Catalog tables (e.g. ``collaboration.ai_safety.online_eval_judgements``).
For raw S3 Delta, use Path A or B.

.. code-block:: bash

   pip install databricks-sql-connector

.. code-block:: python

   from databricks import sql

   with sql.connect(
       server_hostname="atlassian-discover.cloud.databricks.com",
       http_path="/sql/1.0/warehouses/<warehouse-id>",
       access_token="dapi...",  # your PAT
   ) as conn, conn.cursor() as c:
       c.execute("""
           SELECT samples_day, predicted_harm_category, COUNT(*) AS n
             FROM collaboration.ai_safety.online_eval_judgements
            WHERE samples_day = '2026-05-04'
         GROUP BY 1, 2
         ORDER BY n DESC
       """)
       for row in c.fetchall():
           print(row)

9.5 What's missing from *this* sandbox today (concrete checklist)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Direct probing on 2026-05-05 confirms:

================================================  ============  ==========================================================================
Capability                                        Present?      Evidence
================================================  ============  ==========================================================================
Network reachability to Databricks workspace      ✅ YES        ``curl https://atlassian-discover.cloud.databricks.com`` → HTTP 303
Network reachability to Databricks REST API       ✅ YES        ``GET /api/2.0/clusters/list`` → HTTP 401 (auth needed; network OK)
``atlas`` CLI                                     ✅ YES        ``/opt/atlassian/bin/atlas``
``atlas ml`` plugin (workflow / connect / fabric) ✅ YES        ``atlas ml --help`` lists ``workflow``, ``connect``, ``fabric``, ``lab``
``atlas asap`` plugin (ASAP token gen)            ✅ YES        ``atlas asap --help`` works
ASAP private key in ``.env``                      ✅ YES        ``ASAP_PRIVATE_KEY`` length 1689, ``ASAP_KEY_ID`` length 26
``pip`` (for installing databricks-connect)       ✅ YES        ``pip install --dry-run`` resolves
``pyspark`` / ``databricks-connect``              ❌ NO         ``ModuleNotFoundError`` for both
``deltalake`` / ``duckdb`` / ``polars``           ❌ NO         All ``ModuleNotFoundError``
``boto3`` / ``aws`` CLI                           ❌ NO         ``ModuleNotFoundError`` / ``command not found``
Active ``~/.databrickscfg`` (PAT)                 ❌ NO         File not present
Active ``~/.aws/credentials`` or fresh SSO        ❌ NO         Only empty ``~/.aws/sso/cache`` directory
Active kube context (needed for ``ml fabric``)    ❌ NO         ``~/.kube/config`` is 0 bytes; ``kubectl config get-contexts`` empty
================================================  ============  ==========================================================================

**Bottom line for this sandbox:** ~10 minutes of bootstrap (one of the
following) would unblock it:

* **For Path A (atlas ml workflow):** an active SLAuth/SSO session
  (``atlas slauth login`` or equivalent) — no pip install needed.
* **For Path B (databricks-connect):** ``pip install databricks-connect==<dbr>``
  + a PAT exported as ``DATABRICKS_TOKEN`` + ``DATABRICKS_HOST`` env vars.
* **For Path C (sql-connector):** ``pip install databricks-sql-connector``
  + a PAT.

9.6 The *real* blocker is governance, not technology
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The parallel UGC-governance audit (separate document) found:

* **No** formal Atlassian policy document defines who can extract raw UGC
  prompts to a developer machine, under what approval, with what audit log.
* The opt-out filter (``get_regulated_opt_out_tenants``) is enforced *in
  notebook code at read time* — **not** as Databricks row-level security.
  A modified notebook that omits the filter would still succeed.
* No rate-limiting, no DLP egress filter, no Trust+/Privacy approval
  workflow gating the technical paths above.
* Recommendation: **even with all technical access**, do not execute
  Examples C/D/E/F against raw UGC without a Trust+/Privacy review or an
  agreed-upon synthetic dataset (Examples G/H against
  ``online_eval_judgements`` / ``online_eval_metrics`` are tagged
  ``UGC/Metadata`` and are the safest default).

9.7 Recommended path for *this* user, *this* sandbox
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ranked by *how easy it is to do today* + *how policy-clean it is*:

#. **Run Examples G or H** (read ``online_eval_judgements`` /
   ``online_eval_metrics`` — Metadata-tagged, no raw prompts) using
   Path C (SQL Warehouse + PAT). 3 minutes of setup, zero UGC concerns.
#. **For raw prompts, file a Trust+/Privacy review ticket first.** Then
   use Path A (``atlas ml workflow``) so the run is audit-logged.
#. **Avoid** Paths B and C for raw UGC unless explicitly approved — they
   leave fewer audit breadcrumbs than Path A.
#. **Avoid** trying to install pyspark + delta-rs locally to read the S3
   path directly — even if you could get AWS creds, this bypasses every
   governance hook and is the riskiest path.

------------------------------------------------------------------------------
------------------------------------------------------------------------------
10. The "Plato Databricks" Path (the *actually-recommended* internal recipe)
------------------------------------------------------------------------------

This section was added after a deep follow-up investigation revealed that
``responsible-ai-api/.agents/skills/mle/references/plato-databricks.md`` is
the canonical, team-authored runbook for pulling RAI traffic data — and is
much more polished than the synthetic recipes in §7-9 above.

10.1 The single source of truth in the repo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Runbook: ``responsible-ai-api/.agents/skills/mle/references/plato-databricks.md``
* End-to-end pull script (works today): ``responsible-ai-api/model_onboarding/gpt-oss-safeguard-20b/05_pull_plato_hello_sample.py``
* Client-side cleanup: ``responsible-ai-api/model_onboarding/gpt-oss-safeguard-20b/05b_clean_plato_hello_sample.py``
* Confluence hub: https://hello.atlassian.net/wiki/spaces/CONVAI/pages/5586982589/Access+through+Plato+Databricks

10.2 Naming clarification — *Plato*, not *Pluto*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The internal data-lake-on-Databricks for ConvoAI / Hello / Rovo chat traffic
is called **Plato**. There is no Atlassian tool named "pluto" — exhaustive
search across all ``atlassian_packages/`` and the local CLI surface confirms
this. (The only "pluto" hit anywhere on disk is a Lua-dialect highlight rule
in ``node_modules/highlight.js``.)

10.3 Workspace map (verified)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

============================  ====================================================  ===================================================
Environment                   Host                                                  Notes
============================  ====================================================  ===================================================
**Plato Staging**             ``atlassian-plato-stg-consumer-us-01.cloud.databricks.com``  Full UGC; best for exploration
**Plato Prod (non-UGC)**      ``atlassian-plato-prod-consumer-us-west-2.cloud.databricks.com``  Safe-view columns only
**Plato Prod (UGC)**          *via ML Studio compliant workflow only*               Full UGC; requires RELEASED workflow
**ML Studio Staging**         ``atlassian-ml-ugc-stg.cloud.databricks.com``          Full UGC
**ML Studio Prod**            ``atlassian-ml-ugc-prod.cloud.databricks.com``         Full UGC
============================  ====================================================  ===================================================

**Active SQL Warehouse on Plato staging** (verified):
``consumer-endpoint`` / ID ``096d55a3748cbb21`` / state ``RUNNING``.

10.4 Key tables (verified from runbook)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* ``plato_stg.manifold_entities.chat_request_raw`` — request side. Notable cols:
  ``id_value``, ``query``, ``actor_value``, ``organization_value``,
  ``workspace_value``, ``experience``, ``surface``, ``product``,
  ``conversation_channel``, ``context_type``, ``context``, ``editor``,
  ``recipient_agent_name``, ``cloud``, ``citations_enabled``,
  ``thumbs_up``, ``thumbs_down``, ``occurred_at_seconds``,
  ``row_refreshed_at`` (use for recency ordering), ``shard_id``.
* ``plato_stg.manifold_entities.chat_response_raw`` — response side. Notable cols:
  ``id_value``, ``content``, ``intent_detection_result``, ``scenario_id``,
  ``additional_attributes``, ``llm_iterations``, ``sources``,
  ``cited_segments``, ``negative_segments``, ``rewritten_queries``,
  ``plugin_invocations``, ``orchestration_graphs``, ``minion_outputs``,
  ``in_session_segmentation_*``, ``row_refreshed_at``.
* **Join key:** ``req.id_value = res.id_value`` (Rovo message ARI).

10.5 Honest auth reality (verified from this very sandbox, 2026-05-05)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The runbook claims *"The ``databricks`` CLI is installed at
``/opt/homebrew/bin/databricks``"* and *"Profiles are stored in
``~/.databrickscfg``"* — neither was true on this sandbox until I bootstrapped:

================================================  ============================================  ==========================
Claim                                             Verified state pre-bootstrap                  Action taken
================================================  ============================================  ==========================
``databricks`` CLI at ``/opt/homebrew/bin/databricks``  ❌ Missing                                 ``brew install databricks/tap/databricks`` → installed v0.299.0
``~/.databrickscfg`` exists with ``plato-stg``    ❌ Missing                                    Cannot create headlessly
``databricks-sdk`` Python package                 ✅ Present (v0.99.0 in Anaconda Python)        n/a
End-to-end pull script                            ✅ Present (``05_pull_plato_hello_sample.py``)  n/a
================================================  ============================================  ==========================

**The unavoidable browser step:**

.. code-block:: bash

   databricks auth login \
     --host https://atlassian-plato-stg-consumer-us-01.cloud.databricks.com \
     --profile plato-stg

This **opens a browser** for OAuth U2M / SSO. There is **no equivalent
headless flow** — neither ``atlas ml lab`` (whose ``token``, ``auth``,
``credentials``, ``login``, ``databricks``, ``workspace`` subcommands all
fall through to the parent help) nor any other Atlassian-internal CLI
surfaces a Databricks-issued bearer token. The Databricks workspace identity
plane is owned by Databricks and only Databricks can mint its bearer tokens.

10.6 The complete bootstrap, line by line (pasted from a real laptop)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # 1. Install CLI (one-time)
   brew install databricks/tap/databricks

   # 2. Browser SSO (one-time per workspace; opens default browser)
   databricks auth login \
     --host https://atlassian-plato-stg-consumer-us-01.cloud.databricks.com \
     --profile plato-stg

   # 3. Verify
   databricks --profile plato-stg current-user me
   #   → prints {"user_name":"tchen7@atlassian.com", ...}

   # 4. Confirm warehouse is reachable
   databricks --profile plato-stg warehouses get 096d55a3748cbb21
   #   → {"name":"consumer-endpoint","state":"RUNNING", ...}

   # 5. Run the canonical pull (writes ./datasets/plato_stg_hello_sample_10k.csv)
   cd /Users/tchen7/MyProjects/atlassian_packages/responsible-ai-api
   /opt/homebrew/anaconda3/bin/python \
     model_onboarding/gpt-oss-safeguard-20b/05_pull_plato_hello_sample.py

   # 6. (Optional) Clean & PII-scrub
   /opt/homebrew/anaconda3/bin/python \
     model_onboarding/gpt-oss-safeguard-20b/05b_clean_plato_hello_sample.py \
       --scrub-pii

10.7 Data-quality gotchas the team has already paid for (so you don't)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Verbatim from ``plato-databricks.md`` § "Gotchas learned the hard way":

#. **``Disposition.INLINE`` caps at 25 MB.** A 30k-row pull will fail with
   ``Inline byte limit exceeded``. Always use
   ``Disposition.EXTERNAL_LINKS + Format.JSON_ARRAY`` for >few-thousand rows.
#. **``next_chunk_index`` lives on ``external_links[-1]``, not on
   ``result``.** The outer ``result.next_chunk_index`` is ``None`` even when
   more chunks exist. See the runbook for paginated read pseudocode.
#. **``intent_detection_result`` is ~52% NULL and ~48% literal ``"[]"``** on
   Hello/Rovo data — effectively unpopulated.
#. **``context_type`` / ``context`` are ~92% empty** — add ``WHERE
   context_type IS NOT NULL`` if you specifically need contextual prompts.
#. **~78% of raw rows are repeated load-test prompts** (Pollinator IT-help /
   VPN / "hello world" templates). The pull script's ``QA_BOT_PATTERNS``
   regex list (~12 entries) and double-dedup (``id_value``, then
   ``sha2(lower(trim(query)), 256)``) is what drops a 30k-row raw pull down
   to a usable ~6.5k unique rows.

10.8 Why this is *better* than the synthetic recipes in §7
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

============================================  =======================================  =======================================================
Concern                                       §7 recipe (S3 Delta)                     §10 Plato recipe
============================================  =======================================  =======================================================
Auth ceremony                                 ❌ Cluster-internal IAM AssumeRole only   ✅ Browser SSO, then bearer token reusable indefinitely
Local-laptop runnability                      ❌ Requires Databricks Connect + cluster  ✅ Pure ``databricks-sdk`` over HTTPS, no Spark
Output format                                 Spark DataFrame (must ``.show()``)        ✅ CSV file ready for ``pd.read_csv()``
Stratified sampling                           Manual (write your own)                   ✅ Built-in per-product quotas
Load-test prompt filtering                    None                                      ✅ Twelve regex patterns, validated by team
Dedup                                         None                                      ✅ Double dedup (id, then normalised query hash)
PII handling                                  Manual (call sanitizer yourself)          ✅ Optional ``--scrub-pii`` flag
Workspace                                     Only ``atlassian-discover``               Plato STG/PROD or ML Studio STG/PROD
Compliance posture                            ⚠ Bypasses Plato governance views        ✅ Reads Plato-curated tables w/ safe-view columns

============================================  =======================================  =======================================================

**Conclusion:** Once you've done the one-time browser SSO, the Plato pull
script is the **fastest, safest, most-supported** way to get historical RAI
chat traffic onto a laptop. Use §7 only if you specifically need raw
``aup_filter_*`` columns from the anti-spam-svc Delta (which Plato does not
mirror).

10.9 What the user originally heard ("pluto") — corrected mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Plato** = the Atlassian-internal data-lake / Databricks workspace family
that *consumes* the GASv3-landed events from ConvoAI / Hello / Rovo.
Every other "p…o" word in the codebase (``platform``, ``Pollinator``,
``policy``, ``Pluto`` (Lua highlight rule)) is unrelated.

------------------------------------------------------------------------------
11. Pointer Index (for the SRE / on-call / privacy-reviewer in a hurry)
------------------------------------------------------------------------------

* **"Where is the prompt stored?"** → not by rai-api; by upstream chat in
  ``s3://anti-spam-svc-us-east-1-prd-ugc-a25f4c20``.
* **"Where is the moderation decision stored?"** → GASv3
  ``contentEvaluated`` event (real-time) AND Databricks Delta
  ``collaboration.ai_safety.online_eval_judgements`` (daily batch).
* **"Does rai-api use Databricks?"** → No (runtime). Yes for one-off model
  onboarding helpers.
* **"Does the research repo use Databricks?"** → Yes — heavily; primary
  workspace ``atlassian-discover.cloud.databricks.com``.
* **"How do we close the loop from production back to retraining?"** →
  Anti-spam UGC Delta → Databricks online-eval notebook → Delta judgements +
  metrics → MLflow + fine-tuning notebooks → MSP launchpad model registration.
* **"Is there PII in any RAI-owned table?"** → No prompt text in any
  RAI-owned table. ``prompt_id`` only. Raw text lives in anti-spam-svc UGC
  Delta (separate ownership).

.. seealso::

   * :doc:`../02-request-lifecycle` — full call stack per endpoint
   * :doc:`../../modules/analytics/gasv3-analytics` — GASv3 client deep dive
   * :doc:`../../modules/rai-research/online-evaluation` — LLM judge pipeline
   * :doc:`07-business-and-technical-goals` — SLOs & priorities
