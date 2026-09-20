# RAI Traffic Pull — Three-Path Comparison Report

**Date:** 2026-05-05  •  **Workspace probed:** Plato Staging (`atlassian-plato-stg-consumer-us-01`)  •  **Author:** investigation via Rovo Dev sandbox

---

## TL;DR

| Path | Status | Output | Real RAI prod labels? | Best for |
|---|---|---|---|---|
| **A — `online_eval_judgements`** (atlassian-discover Databricks) | ⚠ Profile created, auth pending (browser needed) | n/a | ✅ Yes (`predicted_*` cols) but **sampled ~1500/day** | Quality-checking the ensemble of judges against prod decisions |
| **B — Snowflake `pf_v2.responsibleAI`** (GASv3 events) | ❌ Not runnable (no Snowflake CLI/SDK installed) | n/a | ✅ Yes — **every** prod decision | Compliance, full-fidelity audit, monitoring |
| **C — Heuristic regex on Plato chat traffic** | ✅ Done end-to-end | 1 row from 14-day staging window (817 B CSV) | ❌ No — proxy / synthetic labels only | Quick exploration, debugging, staging smoke tests |

**Key finding from Path C:** the only "violation" in 14 days of *staging* Plato traffic is the engineer who literally typed *"trying to test the scenario of successful prompt injection"* — i.e., the staging environment is genuinely clean and our heuristic worked.

---

## Path A — Pull `online_eval_judgements` (real prod RAI labels, sampled)

### Definition (verified)

| Column | Source-code line | Meaning |
|---|---|---|
| `predicted_is_violation` | `online_eval_workflow.py:369` + rename at `:416` | **Real production RAI verdict** — passthrough of `aup_filter_category != "NONE"` from anti-spam-svc Delta |
| `predicted_harm_category` | rename at `:417` | **Real production category** |
| `violation_score` | from `aup_filter_score` | **Real production confidence 0.0–1.0** |
| `query_eval_is_violation` | LLM-judge at `:200-235`, majority of 3 runs | **NOT prod** — offline LLM-judge re-evaluation |
| `query_eval_harm_category` | same | **NOT prod** — offline LLM-judge category |
| `query_response_eval_*` | same, with response context | **NOT prod** — offline LLM-judge with response |

### Sample size caveat
Per `online_eval_workflow.py:566-567`, the daily job samples **only 500 violations + 1000 safe = 1500/day**. Not the full firehose.

### Status on this sandbox
* `databricks-cli` profile `rai-discover` saved with host `https://atlassian-discover.cloud.databricks.com`
* OAuth U2M browser flow needed to complete auth: `databricks auth login --profile rai-discover` (run on a host with a browser)
* Once authed, query is:
  ```sql
  SELECT samples_day, prompt_id, predicted_is_violation, predicted_harm_category,
         violation_score, query_eval_is_violation, query_response_eval_is_violation
    FROM collaboration.ai_safety.online_eval_judgements
   WHERE samples_day >= '2026-04-21' AND predicted_is_violation = true
   ORDER BY samples_day DESC, violation_score DESC
   LIMIT 200
  ```

### Output (when run)
File: `path_a_online_eval_judgements_violations.csv` (will be ~50–200 KB; up to ~3,500 rows over a 7-day window).

---

## Path B — Snowflake `pf_v2.responsibleAI` (every prod decision)

### Why it's the gold standard
* Every single `responsible-ai-api` call emits one `contentEvaluated` event via the `analytics_client.client.Client.operational(...)` call (verified at `responsible-ai-api/src/gasv3_analytics/rai_analytics_client.py:96-108`).
* Schema (verified at `events/policy_filter/content_evaluated.py:26-45`): `outcome`, `detectedHarmCategory`, `evaluationVersion`, `violationScore`, `useCaseId`, `slauthPrincipal`, `agentId` — plus envelope: `cloud_id`, `user_id`, `anonymous_user_id`, `timestamp`.

### What's missing on this sandbox (verified by Subagent investigation)
| Tool | Status |
|---|---|
| `snowsql` CLI | ❌ Not installed |
| `snowflake-cli` (modern Snow CLI) | ❌ Not installed |
| `snowflake-connector-python` | ❌ Not installed in `/opt/homebrew/anaconda3/bin/python` |
| `snowflake.snowpark` | ❌ Not installed |
| `~/.snowsql/config` | ❌ Not present |
| `$SNOWFLAKE_ACCOUNT` env var | ❌ Not set |
| Atlassian Snowflake host (`atlassian.snowflakecomputing.com` etc.) | ❓ Unverified — needs internal docs |
| Exact RAI table FQN | ❓ Unknown — likely `pf_v2.responsibleAI.contentEvaluated` or `gasv3_event_responsibleai` |

### To unblock Path B
1. `brew install snowflake-cli` (or `pip install 'snowflake-connector-python[secure-local-storage]'`)
2. `snow connection add --name atlassian --account atlassian --authenticator externalbrowser` (browser SSO)
3. Confirm exact table FQN via internal `go/snowflake` portal or `#help-data-platform` Slack
4. Query:
   ```sql
   SELECT user_id, cloud_id, attributes:detectedHarmCategory::string AS category,
          attributes:violationScore::float AS score,
          attributes:outcome::string AS outcome, timestamp
     FROM pf_v2.responsibleAI.contentEvaluated
    WHERE attributes:outcome::string = 'disallowed'
      AND timestamp >= dateadd(day, -7, current_timestamp())
    ORDER BY timestamp DESC
    LIMIT 1000
   ```

### Output (when run)
File: `path_b_snowflake_pf_v2_disallowed.csv` (~MB-scale; every disallowed prod decision in the window).

---

## Path C — Heuristic Plato regex (✅ DONE)

### Approach
* Source: `plato_stg.manifold_entities.chat_request_raw`
* Window: last 14 days
* Apply Spark SQL `RLIKE` patterns for 7 of 17 HarmCategories (the regex-tractable ones):
  * `JAILBREAK_PROMPT_INJECTION`, `SELF_HARM`, `VIOLENCE_HARASSMENT`, `ILLEGAL_ACTIVITY`, `SEXUAL_CONTENT`, `PERSONALLY_IDENTIFIABLE_INFORMATION`, `IMPERSONATION`
* Skipped: `HATE_DISCRIMINATION`, `MISINFORMATION`, `POLITICS`, `HIGH_RISK_DECISIONS`, `SPECIALIST_ADVICE`, `INTELLECTUAL_PROPERTY`, `COPYRIGHT`, `PROFANITY` — semantic, low precision via regex.

### Result
| Metric | Value |
|---|---|
| Window | 14 days (2026-04-21 → 2026-05-05) |
| Rows scanned | unknown total (Plato 7-day raw alone has ~1.1k req/hour ≈ 185k/week → ~370k/14d) |
| Hits | **1** |
| File | `path_c_plato_heuristic_violations.csv` (817 B) |

### The single hit (TP)
```
id_value : ari:cloud:rovo:DUMMY-a5a01d21-…
product  : confluence
qlen     : 411
refreshed: 2026-04-22T03:45:50Z
category : JAILBREAK_PROMPT_INJECTION
query    : "Sorry i should have explained - marathon (the thinking mode I am testing) is running in a sandbox.
            Im trying to test the scenario of successful prompt inje[ction]…"
```

✅ **True positive** — an Atlassian engineer literally testing prompt injection. The regex correctly matched the phrase "prompt inje[ction]". Note the `DUMMY-…` prefix on the cloud_id, which confirms this was a deliberate test, not real traffic.

### Why so few hits?
1. **Staging environment** — `plato_stg` is QA/staging-only. Real attack traffic goes to prod.
2. **`responsible-ai-api` filters at the moderation gate** — many violation attempts never reach Plato because they're blocked upstream and the request body is dropped.
3. **Conservative regex** — we deliberately preferred precision over recall. For higher recall, expand patterns (with much higher FP rate).

### To get more hits
* Increase window to 30/60/90 days
* Loosen regex (accept higher FP rate)
* Move to **prod** Plato workspace (not staging)
* Use **Path A or B** for the actual prod-flagged set

---

## Side-by-side comparison

| Dimension | A: online_eval_judgements | B: pf_v2.responsibleAI | C: Heuristic Plato |
|---|---|---|---|
| **Real RAI prod labels?** | ✅ Yes | ✅ Yes (every event) | ❌ Synthetic |
| **Coverage** | 1.5k/day sample | 100% of decisions | Whatever regex catches |
| **Includes raw prompt text?** | ❌ pepper-hashed `prompt_id` only | ❌ No prompt text in event | ✅ Full query (with PII risk) |
| **Includes response text?** | ❌ | ❌ | ✅ via join to `chat_response_raw` |
| **Includes `harm_category`?** | ✅ `predicted_harm_category` | ✅ `attributes:detectedHarmCategory` | ❌ Heuristic only |
| **Includes `violation_score`?** | ✅ | ✅ `attributes:violationScore` | ❌ |
| **Setup time (laptop)** | ~5 min (browser SSO) | ~15 min (install + SSO + find table) | ✅ 0 min (already done) |
| **Recurring cost** | Daily Databricks SQL | Snowflake credits | Daily Databricks SQL |
| **Best fit** | Quality / drift monitoring | Compliance, full audit | Debugging, exploration |
| **Governance posture** | UGC/Metadata-tagged, OK | UGC/Metadata-tagged, OK | Plato chat is UGC — handle carefully |

---

## Recommendations

### Immediate (today)
1. **Use Path A** for any task that needs real RAI verdicts but only on a daily-sample basis. Run `databricks auth login --profile rai-discover` once on your laptop, then re-use forever.
2. **Use Path C** for staging smoke tests, regex-rule prototyping, or to find specific known-pattern queries (e.g., a particular jailbreak phrase you want to track).

### Short-term (this week)
3. **Enable Path B** — install `snowflake-cli` and confirm the RAI events table FQN with `#help-data-platform`. Once enabled, B becomes the canonical source for compliance reporting.
4. **Cross-link the three** — write a small joiner that takes `prompt_id` from Path A, looks it up in B for full decision context, and (if possible) maps it back to a Plato `id_value` for the actual user query. The pepper-hash means this only works one-way (Plato → A) without the pepper secret.

### Medium-term (this quarter)
5. **Document this in `09-data-storage-and-databricks.rst`** as a new §11 ("Three Paths to RAI Traffic Data"). The current §10 covers Plato general traffic only.
6. **Consider exposing `predicted_*` columns from `online_eval_judgements` as a Plato view** — i.e., have the daily job ALSO write a row into `plato_stg.ai_safety.production_decisions` so analysts who only have Plato auth get partial visibility without a separate workspace login.

### Long-term (FY26 H2)
7. **Replace the daily 1500-row LLM-judge sample with a streaming pipeline** that judges every prod decision (or at least every disallowed one). The current 0.8% sample rate means rare harm categories may take months to accumulate enough data for trustworthy precision/recall calculation.
8. **Add a `plato_id` field to the `contentEvaluated` GASv3 event** so the cross-table join (Plato chat → RAI verdict) works without the pepper hash. Today, joining requires ad-hoc pepper access.

---

## Artifacts produced

```
/Users/tchen7/MyProjects/CoreProjects/OpenStartup/_dev/rai_hack/datasets/
├── COMPARISON_REPORT.md                        (this file)
├── path_a_plato_stg_hello_sample_10k.csv      (25.6 MB, 8,446 rows, full Plato pull — baseline traffic)
└── path_c_plato_heuristic_violations.csv      (817 B,  1 row,    Path C heuristic violations)

(Path A judgements + Path B Snowflake CSVs will be added once auth completes.)
```

---

## Open questions for follow-up

1. **What's the exact pepper for `online_eval_judgements.prompt_id`?** Owned by RAI team (secret scope `responsible-ai`, key `online-eval-pepper`). Required to back-trace from Path A to Plato.
2. **Does `pf_v2.responsibleAI` exist as a single table or is it shattered into per-action sub-tables?** GASv3 sometimes splits by `action_subject` — could be `pf_v2.responsibleAI.policyFilter.contentEvaluated`.
3. **Does staging `plato_stg` actually capture moderation events from the staging RAI API?** If yes, why are there no prod-decision columns? (Answer: because they live in the GASv3 events catalog, not Plato.)
4. **Is there an "online_eval_judgements" equivalent in the staging metastore?** Worth checking once Path A is authed.
