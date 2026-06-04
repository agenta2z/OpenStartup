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

## Phase 3 -- Tarot V2 packaging:
[__depends on__ Phase 2 __succeeded__]

Package the new trained model into `assets.tar.gz` consumable by Tarot V2.

**Tools**[__must__]:
- `atlas ml workflow run -b 7a6085b7-6898-49f8-831d-e74b8af97ebd -e prod`
  **Capture**: ML Studio Run ID. Runtime ~15-30 min. Example run `1b1a1e42-4adf-4429-a11d-5ec1789045e7`.

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

## Phase 9 -- Eval × 4 regions:
[__depends on__ Phase 2 succeeded; may parallel with Phases 3-8]

**CRITICAL — DO NOT REPEAT 2026-06-02 MISTAKE**: `atlas ml workflow run` has **NO `--region` flag**. Running the same blueprint 4 times produces 4 us_west_2 runs, not 4 region runs. Use the 4 region-specific blueprint IDs from the Verified blueprint reference table.

**Tools**[__must__]:
```bash
atlas ml workflow run -b 453a789e-409d-4ebf-9c0f-8552621d937b -e prod   # us_west_2
atlas ml workflow run -b 992be8ce-bb75-4588-ab4e-fd2ad83460a4 -e prod   # us
atlas ml workflow run -b 4f7067a0-eb66-49e4-989d-380aeaf4d890 -e prod   # eu_west_1
atlas ml workflow run -b 404106f4-40c7-44c3-9ac2-ad99cc96de26 -e prod   # eu
```

**Runtime**: ~1.5-2 hrs per region (dominated by `run_base_inference` task).

**Region verification** (paranoia check before believing the run is correctly regional):
```bash
# Extract the Databricks job ID from the ML Studio run, then verify the job's realm tag
atlas ml workflow run-status -w <ml_studio_run_id> -e prod | grep databricksRunPageUrl
# Find job/<JOB_ID>/run/<DBX_RUN_ID> in the URL
databricks --profile ml-ugc-prod jobs get <JOB_ID> | grep -oE '"realm"[^"]*"[^"]+"'
# Must match the requested region
```

## Phase 9b -- MRR extraction (semi-manual):
[__depends on__ Phase 9 all 4 SUCCEEDED]

The runbook's MRR comparison table requires reading 4 MRR values from each region's eval run. **As of 2026-06-03, this is the only step that cannot be fully automated** from a Rovo Dev session — 8 independent programmatic paths all fail:

| Path | Failure mode |
|---|---|
| `atlas ml workflow get-metrics -r <dbx_run_id>` | POCO 403 (`mlp-search-relevance-tenant-modeling-dl-ml-lens` group or similar — confirm via `atlas poco logs get -s ml-lens`) |
| `databricks jobs get-run-output` on `compute_base_mrr` | Empty `notebook_output` (notebook doesn't `dbutils.notebook.exit(MRR)`) |
| `mlflow.get_experiment('3773965476281976')` | `RESOURCE_DOES_NOT_EXIST` (experiment in a workspace context not exposed by `databricks://ml-ugc-prod`) |
| SQL SELECT on `ml_ugc_derived_prod_*.mls_usecase_search_relevance_tenant_modeling_adhoc.eval_*_merged_mrr_results_*` | `INSUFFICIENT_PERMISSIONS` (table SELECT restricted to slauth service principal) |
| ML Studio backend HTTP API `/api/v1/ml-studio/workflow-runs/.../metrics` | `asap: authorization header missing` (no ml-studio audience token issued for CLI clients) |

**Human path** (~3 min): Open each of the 4 View Run links printed by Phase 9, read MRR from the rendered UI, paste back into the launch doc.

**To eliminate this step in a future cycle**: Request the SSAM group identified by `atlas poco logs get -s ml-lens` against a fresh rejection's decisionId. As of 2026-06-03, the best-guess group name is `mlp-search-relevance-tenant-modeling-dl-ml-lens` but **must be confirmed** via POCO before requesting. The DACI doc explaining ML Lens namespace permissions: https://hello.atlassian.net/wiki/spaces/MLP/pages/6107053917.

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

## Honest known issues from the 2026-06-02 cycle
[__important__]:

> Resolved issues are archived in [`issues/resolved/`](issues/resolved/).

1. **MLflow URI placeholder**: The `lm_uri` field in the Tarot V3 YAML had to be filed as `PLACEHOLDER_MLFLOW_RUN_ID` because experiment `3747328226380826` is in a workspace context inaccessible from `databricks://ml-ugc-prod`. Reviewer must resolve manually.

2. **MRR extraction**: Cannot be automated without additional SSAM. Launch doc was published with "MRR pending" entries and a footer comment explaining the resolution path. **To close this gap**: trigger a fresh `atlas ml workflow get-metrics` rejection, capture the decisionId from the error output, then either inspect via `atlas poco logs get -s ml-lens -e prod-east --start <ts-1m> --end <ts+1m>` (requires `mlp-lifecycle-dl-ml-lens` membership) or ping `#help-mlplatform` with the decisionId to discover the exact SSAM group whose membership would allow the call. Reference: [ML Lens DACI on namespace permissions](https://hello.atlassian.net/wiki/spaces/MLP/pages/6107053917).

3. **Slack send**: No Slack MCP / webhook in Rovo Dev session. Orchestrator prints copy-pasteable message; user sends.

4. **Coordination risk**: If a recent refresh exists (e.g., 2026-06-02 v35 happened the day after 2026-06-01 v34 by hchang3), include a back-out offer in the Slack message to avoid stepping on rollouts in flight.

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
