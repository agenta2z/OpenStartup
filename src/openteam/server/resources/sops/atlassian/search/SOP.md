# L2 Cross-Tenant Reranker Model Refresh (PVCY-3790)

End-to-end automated refresh of the L2 cross-tenant document reranker model whenever the tenant
exclusion list `lkp_ugc_dup_exception_list` changes. Replaces the manual ~2-day runbook with a
~4-hour automated pipeline.

[__keywords__] xtenant refresh, l2 reranker, cross-tenant, pvcy-3790, ensemblel23p, tenant filtering, lkp_ugc_dup_exception_list, ml-studio refresh, search relevance refresh
[__example_requests__]
- refresh the xtenant model
- run the l2 cross-tenant reranker refresh
- new tenant added to pvcy-3790, retrain the model
- refresh EnsembleL23p

## Reference
- **Runbook precedent**: https://hello.atlassian.net/wiki/spaces/~71202088d1945544364701b4921ae3c07480c4/pages/7049101435 (2026-05-18 manual cycle)
- **First automated cycle**: https://hello.atlassian.net/wiki/spaces/~71202088d1945544364701b4921ae3c07480c4/pages/7128443945 (2026-06-02, v35)
- **Local orchestrator package**: `/Users/tchen7/MyProjects/CoreProjects/xtenant_refresh_automation/`
- **PR pattern**: ml-studio [#21555](https://bitbucket.org/atlassian/ml-studio/pull-requests/21555) → [#22489](https://bitbucket.org/atlassian/ml-studio/pull-requests/22489); xpsearch-content [#20852](https://bitbucket.org/atlassian/xpsearch-content/pull-requests/20852) → [#22512](https://bitbucket.org/atlassian/xpsearch-content/pull-requests/22512)

## Prerequisites
- **SSAM groups**:
  - `mlp-search-relevance-tenant-modeling-dl-ml-studio-access` (verified working) — for training + filtering + eval workflows
  - `mlp-search-relevance-dl-ml-studio-access` (verified working) — for `package_l2_output_norm_scores_xt` packaging
- **Databricks profile**: `ml-ugc-prod` configured at `~/.databrickscfg`, authenticated
- **Bitbucket MCP**: `mcp__bitbucket__` toolset available for PR creation
- **Atlassian MCP**: `mcp__atlassian__` toolset available for Confluence page operations
- **CLIs**: `atlas`, `databricks`, `python3 ≥ 3.10`, optional `mlflow` (`pip install mlflow databricks-sdk`)
- **Unity Catalog SELECT on**: `ml_ugc_prod_vnext_socrates_socrates_production_customer_firmographics.customer_firmographics.lkp_ugc_dup_exception_list` (verified — no explicit grant needed beyond default user access)


### Verified blueprint reference
Use these EXACT blueprint IDs. Do not call `atlas ml workflow get-blueprint -n <name>` and trust the first result — each region needs its own blueprint, and the `get-blueprint` CLI returns only the single most recent variant for a name.

| Phase | Workflow | Use case | Blueprint ID | Region |
|---|---|---|---|---|
| P1 baseline training | `train_l2_pairwise_loss_us_west_2` | `search_relevance_tenant_modeling` | `edfb796a-0e83-4aa2-8bb6-b70d43c5ec9d` | us_west_2 |
| P2 filtered training | `apply_tenant_filtering_train_l2_pairwise_loss` | `search_relevance_tenant_modeling` | `290570de-bcf4-40f4-9090-15bffefa262d` | us_west_2 |
| P3 Tarot V2 packaging | `package_l2_output_norm_scores_xt` | `search_relevance` | `7a6085b7-6898-49f8-831d-e74b8af97ebd` | us_west_2 |
| P9 eval (us_west_2) | `evaluate_ranking_data_on_triton_model` | `search_relevance_tenant_modeling` | `453a789e-409d-4ebf-9c0f-8552621d937b` | us_west_2 |
| P9 eval (us) | `evaluate_ranking_data_on_triton_model` | `search_relevance_tenant_modeling` | `992be8ce-bb75-4588-ab4e-fd2ad83460a4` | us |
| P9 eval (eu_west_1) | `evaluate_ranking_data_on_triton_model` | `search_relevance_tenant_modeling` | `4f7067a0-eb66-49e4-989d-380aeaf4d890` | eu_west_1 |
| P9 eval (eu) | `evaluate_ranking_data_on_triton_model` | `search_relevance_tenant_modeling` | `404106f4-40c7-44c3-9ac2-ad99cc96de26` | eu |
| P5a Tarot V3 launchpad | (Databricks job) | n/a | `41970387619718` (job id) | us_west_2 |

## Phase 0 -- Snapshot the exception list (change detection):
[__initial__]

Read the current state of `lkp_ugc_dup_exception_list` and compute a deterministic server-side checksum. If unchanged vs the prior snapshot, the entire refresh can be skipped.

**Why server-side checksum, not row download**: The table has 365k+ rows (~25MB+) which exceeds the Databricks SQL Statements API's default 25MB INLINE response cap. The orchestrator computes `SHA2(SUM(HASH(*)), 256)` server-side, returning a 64-char checksum + COUNT(*) + DESCRIBE + LIMIT 5 sample.

**Tools**[__must__]:
- `python3 CoreProjects/xtenant_refresh_automation/refresh_xtenant_check.py --cache .xtenant_cache/last_seen.json`

**Verified working warehouse**: `ac8c98be41a8ce28` (general data warehouse — has SELECT on the exception-list catalog)

**Output**: JSON file at `.xtenant_cache/last_seen.json` with `n_rows`, `checksum`, `columns`, `sample_rows`. Exit code 0 = unchanged (skip refresh); exit code 2 = changed (proceed). The 2026-06-02 cycle captured 365,623 rows with checksum `ec48faee...0021ef7`.

## Phase 1 -- Baseline training (sanity check):
[__depends on__ Phase 0]

Fire the un-filtered training workflow. Used for sanity comparison only; downstream phases use Phase 2's artifact.

**Tools**[__must__]:
-  `atlas ml workflow run -b edfb796a-0e83-4aa2-8bb6-b70d43c5ec9d -e prod`
   **Capture**: ML Studio Run ID from the output line `ML Studio Run ID: <uuid>`. Example run `06c06b43-f769-4070-ae60-8d2c9963059b`.

- `atlas ml workflow run-status -w <ml_studio_run_id> -e prod --simple` for polling run status. Returns `"status":"RUNNING|SUCCEEDED|FAILED"`.

## Phase 2 -- Filtered training (the real model):
[__depends on__ Phase 0]

Fire the training workflow that reads `lkp_ugc_dup_exception_list` and produces the new `best_two_head_model.pt` artifact. **This is the canonical refresh.**

Do NOT proceed to packaging if Phase 2 fails or aborts — packaging would consume a stale model.

**Tools**[__must__]:
- `atlas ml workflow run -b 290570de-bcf4-40f4-9090-15bffefa262d -e prod`
  **Capture**: ML Studio Run ID. Runtime ~2h. Example run `b929f0ce-549a-421f-b6f3-7b0d41f9e709`.

## Phase 3 -- Tarot V2 packaging (descriptor override required):
[__depends on__ Phase 2 __succeeded__]

Package the new trained model into `assets.tar.gz` consumable by Tarot V2.

**CRITICAL — DO NOT USE `atlas ml workflow run -b` BARE**: The blueprint's default `features.config` was bumped to a june recipe (`l2_xt_3p_doc_cal_mf_no_sl_365_pg_v2_comment_jun_2026_250_token_ignore_embedding.config` — 32 cont + 16 cat features) that is incompatible with the gdrive training recipe currently used by Phase 2 (25 cont + 15 cat features). A bare run produces a packaging that Triton cannot load at eval time. **Always override `features.config` and `l2_ranker_model.pt` via descriptor clone**. See [resolved issue 2026-06-04-wrong-features-config-in-p3](issues/resolved/2026-06-04-wrong-features-config-in-p3.md) for the diagnosis.

**Tools**[__must__]:
```bash
# 1. Clone a prior known-good P3 run (06-01 cycle is the most recent known-good)
atlas ml workflow clone -r <prior_p3_dbx_rid> -e prod -o p3.yaml

# 2. Patch features.config + l2_ranker_model.pt (use P2's MLflow run UUID, extracted from P2's mls_artifact_dir)
P2_MLFLOW_UUID=$(databricks --profile ml-ugc-prod jobs get-run <p2_inner_dbx_rid> | python3 -c "
import json, sys
d = json.load(sys.stdin)
for t in d.get('tasks', []):
    if 'train_l2_ranker_by_pairwise_loss' in t.get('task_key',''):
        # mls_artifact_dir contains the P2 ML Studio run UUID; MLflow run UUID is in a sibling param
        for k, v in t.get('notebook_task', {}).get('base_parameters', {}).items():
            if k == 'mls_mlflow_run_id': print(v); break
")

python3 -c "
import yaml
d = yaml.safe_load(open('p3.yaml'))
for v in d.get('variables', []):
    if v.get('name') == 'features_config':
        v['value'] = 'l2_xt_gdrive_wf_feb_2026_250_token_cal_ignore_embedding.config'
    if v.get('name') == 'l2_ranker_model.pt':
        v['value'] = f'dbfs:/databricks/mlflow-tracking/3747328226380826/$P2_MLFLOW_UUID/artifacts/best_two_head_model.pt'
yaml.safe_dump(d, open('p3.yaml', 'w'))
"

# 3. Fire
atlas ml workflow run -d p3.yaml -e prod
```

**Capture**: ML Studio Run ID. Runtime ~15-30 min. Example successful run (2026-06-04): `0a0f5661-19a6-4d14-b2b2-dee0b95cf10d` producing packaging `dfcb4ba7788f4d9a95721b77f5de6e10`.

**Verification — packaging contents must match training architecture**:
```bash
# The new assets.tar.gz must be ~same size as the prior cycle's (mismatched architectures produce different sizes by 100+MB)
PRIOR_SIZE=$(databricks --profile ml-ugc-prod fs ls dbfs:/databricks/mlflow-tracking/3773965476281976/<prior_cycle_pkg_uuid>/artifacts/ | grep assets.tar.gz | awk '{print $2}')
NEW_SIZE=$(databricks --profile ml-ugc-prod fs ls dbfs:/databricks/mlflow-tracking/3773965476281976/<new_pkg_uuid>/artifacts/ | grep assets.tar.gz | awk '{print $2}')
echo "prior=$PRIOR_SIZE new=$NEW_SIZE diff_kb=$(( (NEW_SIZE - PRIOR_SIZE) / 1024 ))"
# Acceptable: diff_kb within ±100 KB. Larger diff → architectures may mismatch; investigate before proceeding.
```

## Phase 4 -- ml-studio version-bump PR (Tarot V3 YAML):
[__depends on__ Phase 3 __succeeded__]

Create a new YAML descriptor in `atlassian/ml-studio` registering the Tarot V3 package for the new model. Pattern: copy the most recent `package_ensemble_l2_general_doc_stack_retrain_zero_query_<MMDD>.yaml` to the new date.

**Tools**[__must__]:
- `mcp__bitbucket__invoke_tool` with `bitbucketRepoContent action=branch.create` then `action=commit.create` then `bitbucketPullRequest action=create draft=true`

**Branch convention**: `tchen7/automation-<YYYY-MM-DD>-tarot-v3-v<NEW_VERSION>`
**Target branch**: `main`
**File path**: `workflows/src/search_relevance/deployments/package_ensemble_l2_general_doc_stack_retrain_zero_query_<MMDD>.yaml`

**Required YAML fields**:
```yaml
workflow_name: package_ensemble_l2_general_doc_stack_retrain_zero_query_<MMDD>
use_case: search_relevance
workflow_type: RELEASED
refresh_cache: true
regions: [us_west_2]
variables:
  - name: lm_uri
    value: dbfs:/databricks/mlflow-tracking/3747328226380826/<MLFLOW_RUN_UUID>/artifacts/best_two_head_model.pt
  - name: pipeline_config_uri
    value: /Workspace/Users/aayala2@atlassian.com/dev/02_26_package_general_l2/zero_query_l2_ensemble_pipeline_fixed_features_test_3p_2_with_xtenant.json
  - name: package_name
    value: search-relevance.l2-reranker.EnsembleL23p
  - name: tags
    value: '["xtenant", "v<NEW_VERSION>", "<YYYY-MM-DD>", "auto-generated"]'
# ... workflow_environment block copied verbatim from prior YAML
```

**⚠️ MLflow URI**: The orchestrator cannot programmatically resolve `<MLFLOW_RUN_UUID>` from the workspace context bound to `databricks://ml-ugc-prod` (returns `RESOURCE_DOES_NOT_EXIST` for experiment 3747328226380826). File the PR with placeholder `PLACEHOLDER_MLFLOW_RUN_ID` and post a PR comment explaining how to resolve it manually (open the filtered training run UI, copy the UUID from driver logs).

## Phase 5 -- Register ml-registry version:
[__depends on__ Phase 3 succeeded]

Two-step: (5a) fire the Databricks launchpad job that creates the ml-registry version, (5b) the Tarot V3 PR from Phase 4 is what allows future workflows to consume the registered version.

**Tools**[__must__]:
- `databricks --profile ml-ugc-prod jobs run-now 41970387619718 --no-wait`

**Verification**:
```
atlas ml registry version list -r search-relevance.l2-reranker.EnsembleL23p --limit 3
```
Look for a new version with `created_by=slauth` matching today's date. 2026-06-02 example: **EnsembleL23p v35** created by slauth at 6/2/2026.

## Phase 6 -- Launchpad notebook visual sanity check:
[__depends on__ Phase 5 succeeded; __requires user input__]

Open the Databricks launchpad notebook in a browser and visually confirm the new model is loading + predictions look reasonable. **Not automatable** — requires human eyes-on-glass.

**URL**: https://atlassian-ml-ugc-prod.cloud.databricks.com/editor/notebooks/42576196885213?o=848698269108953#command/42576196885214

## Phase 7 -- Slack handoff to rollout WG:
[__depends on__ Phase 5 succeeded; __requires user input__]

Ping `#the-one-search-l2-rollout-wg` to request TeamServe endpoint provisioning for the new ml-registry version. **Not directly automatable** from a Rovo Dev session (no Slack MCP / webhook in current toolset) — orchestrator prints a copy-pasteable message.

**Message template** (info-dense, ~10 lines):
```
:rocket: L2 xtenant model refresh — EnsembleL23p v<NEW> ready for TS

Per PVCY-3790 (lkp_ugc_dup_exception_list, <ROW_COUNT> rows / sha256 <CHK>),
end-to-end automated refresh completed <DATE>:

• ml-registry: https://ai-platform.services.atlassian.com/ui/ml-registry/search-relevance.l2-reranker.EnsembleL23p?version=<NEW>
• ml-studio PR: <PR_URL> (draft)
• Searcher PR: <SEARCHER_PR_URL> (placeholder — awaiting TS endpoint)
• Launch doc: <CONFLUENCE_URL>

:question: Could TS provision an endpoint for v<NEW>?
:warning: <If recent refresh exists>: <last_refresher_handle> ran v<PREV> on <prev_date>.
   Happy to back out if v<PREV> rollout is mid-flight.

— <USER>
```

## Phase 8 -- Searcher PR placeholder:
[__depends on__ Phase 5 succeeded]

File a draft PR in `atlassian/xpsearch-content` against `master` (NOTE: master, not main) as a placeholder. The real diff (4 regional yamls + maintainers.yml updating the endpoint slug) cannot be written until TS provisions the new endpoint (Phase 7 outcome).

**Tools**[__must__]:
- `mcp__bitbucket__invoke_tool` with `bitbucketRepoContent action=branch.create target=master` then `action=commit.create branch=<feature>` then `bitbucketPullRequest action=create draft=true targetBranch=master`

**Branch convention**: `tchen7/automation-<YYYY-MM-DD>-xtenant-v<NEW_VERSION>`
**Placeholder file**: `docs/auto/xtenant-v<NEW>-placeholder.md` with deletion instructions for whoever replaces it after TS endpoint arrives.

## Phase 9 -- Eval × 4 regions (cache-hit-trick required):
[__depends on__ Phase 3 succeeded; may parallel with Phases 4-8]

**CRITICAL — DO NOT REPEAT 2026-06-02 MISTAKE**: `atlas ml workflow run` has **NO `--region` flag**. Running the same blueprint 4 times produces 4 us_west_2 runs, not 4 region runs. Use the 4 region-specific blueprint IDs from the Verified blueprint reference table.

**CRITICAL — TAG-ON-CACHE-MISS PLATFORM BUG**: A naive `atlas ml workflow run -b <eval_bp>` against our freshly-packaged URI will fail at `generic_json_composition` with `KeyError: 'feature_scores'`. Root cause: when `preprocessing` runs fresh (cache=false) it produces an output table with zero column tags; downstream tasks read tags via `system.information_schema.column_tags` and find none. The proven workaround is the **cache-hit-trick**: clone a prior successful per-region eval run and override **only** `BASE_MODEL_MLFLOW_URI`, keeping `INPUT_TABLE_NAME`, `CUR_TIME_STAMP`, `OUTPUT_PREFIX`, and `workflow_name` identical to the cached run. This forces preprocessing to cache-hit on the proven-good 05-18 tagged tables, while `run_triton_model_inference` (the only task that consumes `BASE_MODEL_MLFLOW_URI`) runs fresh against our model.

**CRITICAL — PER-REGION SERVICE PRINCIPAL ROUTING**: Each region has a distinct service principal that ML Studio uses to execute notebook tasks. Atlas routes work to the correct regional SP **only** when the descriptor was cloned from a prior run in that same region. Cloning a us_west_2 run and changing `regions:[us]` routes to the wrong SP (`bbb43cb1` instead of `7f8aad09`) and fails preprocessing with `INSUFFICIENT_PERMISSIONS: User does not have USE SCHEMA`. **Always clone from a per-region prior run.**

### Per-region SP reference (for verification)
| Region | Regional SP UUID |
|---|---|
| us_west_2 | `bbb43cb1-3b4f-4a09-9ad5-eef5b32d8be1` |
| us | `7f8aad09-a579-4ce1-8a6b-e08966ee8045` |
| eu_west_1 | `b1358a84-c08d-4f72-a8e0-d1d31a9a1c34` (verify with `databricks api get /api/2.1/jobs/runs/get` on a recent eu_west_1 eval run) |
| eu | `78598c68-...` (verify likewise) |

### Per-region cached preprocessing reference (CUR_TIME_STAMP that hits 05-18 cache)
| Region | OUTPUT_PREFIX | CUR_TIME_STAMP | INPUT_TABLE suffix |
|---|---|---|---|
| us_west_2 | `eval_xt_prod_traffic_2026_01_20_02_10_with_2026_05_18_model` | `2026_05_18_14_14_3345678` | `extract_gdrive_prod_lc_data_*_2026_02_13_23_30_3345678` |
| us | same | `2026_05_18_14_15_3345678` | `..._2026_02_13_23_32_3345678` |
| eu_west_1 | same | `2026_05_18_14_16_3345678` | `..._2026_02_13_23_31_3345678` |
| eu | same | `2026_05_18_14_17_3345678` | `..._2026_02_13_23_36_3345678` |

### Cache-hit-trick procedure (for each region)
```bash
# 1. Find a recent successful per-region eval run to clone (use prior cycle if needed)
PRIOR_RID_USW2="d9648f06..."  # last d96 success in us_west_2 (or query recent runs)
PRIOR_RID_US="..."             # last successful us-region eval
PRIOR_RID_EUW1="..."
PRIOR_RID_EU="..."

# 2. Clone the prior run's descriptor
atlas ml workflow clone -r $PRIOR_RID_USW2 -e prod -o desc_usw2.yaml

# 3. Patch BASE_MODEL_MLFLOW_URI to our new packaging URI (yaml-aware, NOT regex)
#    workflow_name MUST stay identical to avoid cache miss
python3 -c "
import yaml
d = yaml.safe_load(open('desc_usw2.yaml'))
for v in d.get('variables', []):
    if v.get('name') == 'BASE_MODEL_MLFLOW_URI':
        v['value'] = 'dbfs:/databricks/mlflow-tracking/3773965476281976/<NEW_PKG_UUID>/artifacts/assets.tar.gz'
yaml.safe_dump(d, open('desc_usw2_patched.yaml', 'w'))
"

# 4. Fire
atlas ml workflow run -d desc_usw2_patched.yaml -e prod
# Capture the ML Studio Run ID
```

**Verification — cache_hit MUST be true for preprocessing**:
```bash
# Find inner dbx run, then check preprocessing cache_hit
TOP_RID=$(atlas ml workflow run-status -w <ml_studio_run_id> -e prod | grep -oE 'databricksRunPageUrl[^"]*"[^"]*/run/[0-9]+' | grep -oE '[0-9]+$')
databricks --profile ml-ugc-prod jobs get-run $TOP_RID | python3 -c "
import json, sys
d = json.load(sys.stdin)
for t in d.get('tasks', []):
    if 'preprocessing' in t.get('task_key', ''):
        cache = t.get('cache_lookup_result', {}).get('cache_hit', False)
        print(f'preprocessing cache_hit={cache}')
        assert cache, 'PROCEED ONLY IF cache_hit=True; else abort and re-check workflow_name/INPUT_TABLE/CUR_TIME_STAMP'
"
```

**Runtime**: ~30-45 min per region with cache hit (vs ~1.5-2 hrs full-fresh). The only task that consumes meaningful compute is `run_triton_model_inference` which loads our packaged model into Triton on GPU and runs eval queries.

## Phase 9b -- MRR extraction (fully automatable as of 2026-06-05):
[__depends on__ Phase 9 all 4 SUCCEEDED]

The runbook's MRR comparison table requires reading 4 MRR values from each region's eval run. **As of 2026-06-05, this IS programmatically extractable** via the UGC-safe view that the `create_ugc_safe_views_in_interactive_catalog_task` publishes into `ml_interactive_prod`.

**Tools**[__must__]:
```bash
WH="bbeb56ed30694b10"  # general data warehouse with SELECT on ml_interactive_prod
for ENTRY in "us_west_2:2026_05_18_14_14_3345678" "us:2026_05_18_14_15_3345678" "eu_west_1:2026_05_18_14_16_3345678" "eu:2026_05_18_14_17_3345678"; do
    R="${ENTRY%%:*}"
    CTS="${ENTRY#*:}"
    TBL="ml_interactive_prod.mls_usecase_search_relevance_tenant_modeling_adhoc.eval_xt_prod_traffic_2026_01_20_02_10_with_2026_05_18_model_base_mrr_merged_mrr_results_${CTS}_${R}"
    echo "=== $R ==="
    databricks --profile ml-ugc-prod api post /api/2.0/sql/statements --json "{
      \"warehouse_id\":\"$WH\",
      \"statement\":\"SELECT search_experience, model_score_type, total_count, mrr FROM $TBL WHERE search_experience='fullPageSearch' AND model_score_type='inferred_total_score'\",
      \"wait_timeout\":\"50s\"
    }" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); res=d.get('result',{}).get('data_array',[]); [print(f'  count={r[2]} MRR={r[3]}') for r in res]"
done
```

**Output schema** (per region):
| search_experience | model_score_type | total_count | mrr |
|---|---|---|---|
| fullPageSearch | inferred_total_score | <N> | <FLOAT> |
| fullPageSearch | inferred_behavioural_score | <N> | <FLOAT> |
| fullPageSearch | inferred_semantic_score | <N> | <FLOAT> |
| advancedSearch | (same 3 score types) | <N> | <FLOAT> |

The canonical MRR for the launch doc is `fullPageSearch` + `inferred_total_score`.

**Why this works (and why earlier attempts failed)**: The eval pipeline runs `create_ugc_safe_views_in_interactive_catalog_task` after `merge_mrr_results`, which publishes the per-region MRR table into `ml_interactive_prod` as a UGC-PII-scrubbed view. `tchen7` has SELECT on `ml_interactive_prod` (verified) but does NOT have SELECT on the raw `ml_ugc_derived_prod_<region>.mls_usecase_*_adhoc.*` tables (restricted to the slauth service principal). Always query the `ml_interactive_prod` view, not the raw adhoc table.

## Phase 10 -- Confluence launch doc:
[__depends on__ Phase 9b complete (or skipped with MRR=TBD)]

Publish a launch doc under the user's personal space following the runbook template.

**Tools**[__must__]:
- `mcp__atlassian__invoke_tool` with `create_confluence_page parent_url=<personal_space>`

**Title convention**: `Apply lkp_ugc_dup_exception_list to Filter Tenant for Cross Tenant Modeling - <YYYY-MM-DD> (Automated)`

**Must include**:
1. Summary + automation milestone panel
2. Source table info (row count, checksum, snapshot timestamp)
3. Retrain table linking all run URLs (training, packaging, registry version, PRs)
4. Comparison table per region with MRR (or "pending")
5. Verified blueprint reference table (so the next cycle has the correct IDs in one place)
6. Known follow-ups section listing any unresolved manual steps

**HTML format**: Use `<div data-type="panel-info|note|warning|success">` (NOT `<ac:adf-panel>`). The validator rejects Confluence storage-format XML.

## Honest known issues
[__important__]:

> Resolved issues are archived in [`issues/resolved/`](issues/resolved/). The MRR extraction issue was resolved on 2026-06-05 — see Phase 9b for the working procedure.

1. **MLflow URI placeholder in P4 PR**: The `lm_uri` field in the Tarot V3 YAML must be filed as `PLACEHOLDER_MLFLOW_RUN_ID` at PR creation time because the orchestrator cannot resolve the MLflow run UUID programmatically from the `ml-ugc-prod` workspace context (experiment `3747328226380826` lives in a different workspace, `ml-platform`). **Mitigation**: orchestrator now posts a PR comment with the resolved UUID once Phase 2 completes (UUID is extractable from the P2 training task's `mls_artifact_dir` parameter, e.g. `b929f0ce...` → MLflow run `9e143f5fae...`). Reviewer applies the one-line edit before merge.

2. **Slack send**: No Slack MCP / webhook in Rovo Dev session. Orchestrator prints a copy-pasteable message; user sends to `#the-one-search-l2-rollout-wg`.

3. **Coordination risk**: If a recent refresh exists (e.g., 2026-06-02 v35 happened the day after 2026-06-01 v34 by hchang3), include a back-out offer in the Slack message to avoid stepping on rollouts in flight.

4. **Per-region SP UUIDs are observed values, not contract**: The per-region service principal UUIDs in Phase 9 reflect ML Studio's state as of 2026-06-04. If ML Studio re-issues regional SPs, this SOP needs an update. Verify current SP for each region with `databricks --profile ml-ugc-prod jobs get-run <recent_eval_dbx_rid> | grep -oE '"creator_user_name"[^,]*'` before relying on the documented UUIDs.

## End-to-end automation script
[__see__] `/Users/tchen7/MyProjects/CoreProjects/xtenant_refresh_automation/refresh_xtenant_orchestrator.py`

Usage:
```bash
# Dry-run (safe, no real workflow execution)
python3 refresh_xtenant_orchestrator.py --dry-run --env staging --skip-baseline

# Real PROD run (consumes ~$500-1000 in GPU/CPU compute, takes ~4 hrs wall-clock)
python3 refresh_xtenant_orchestrator.py --execute --env prod
```

## Cost & timing reference
[__info__]:
- **Wall-clock**: ~4 hours end-to-end (snapshot → ml-registry version registered)
- **Compute**: ~$500-1000 (P1 baseline + P2 filtered training + P3 packaging + 4 region evals)
- **Human time**: ~10 min (Slack send + MRR copy-paste + PR `lm_uri` resolution + launchpad notebook check)

## Maintainers
- **Source table**: @Fabrizio Piasini (page 7049101435 owner)
- **Rollout coordination**: @Nandini Neralagi (search-relevance team)
- **Prior automation**: @hchang3 (manual 2026-06-01 v34 cycle)
- **This automation**: @tchen7 (2026-06-02 v35 first automated cycle)
