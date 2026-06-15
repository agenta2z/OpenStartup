# Resolved: Tag-on-cache-miss platform bug in `preprocessing` task

**Discovered**: 2026-06-04 during 2nd refresh cycle attempt
**Resolved**: 2026-06-04 via cache-hit-trick (workaround; root cause is a platform bug still open)
**Resolution location**: Phase 9 in SOP.md

## Symptom

When `atlas ml workflow run -b <eval_blueprint>` was fired against our freshly-packaged Tarot V2 URI (`dfcb4ba7788f4d9a95721b77f5de6e10`), the eval consistently failed at `generic_json_composition` with:

```
KeyError: 'feature_scores' in generic_json_composition
```

Yet the SAME eval blueprint, run against the prior cycle's packaging URI (`cc42b45715154a4dbaa1b19c8fd28e41`, 06-01 model), succeeded.

## Root cause (verified)

The eval pipeline has two phases:

1. `preprocessing` task — produces a Unity Catalog table with column tags attached (tag = which model score column is being scored)
2. `generic_json_composition` task — reads those column tags from `system.information_schema.column_tags` to know which columns to compose into the inference input JSON

The platform bug: when `preprocessing` runs **fresh** (cache=false), the output table is created **without column tags**. When `generic_json_composition` then queries `system.information_schema.column_tags`, it gets 0 rows → no key `'feature_scores'` → KeyError.

When `preprocessing` cache-HITS (cache=true), it returns the already-existing table from a prior run — which DOES have its 46+ tags intact from when that prior run wrote them via a different code path.

## Verification

```bash
# Cached us_west_2 preprocessing output (used by successful d96)
SELECT COUNT(*) FROM system.information_schema.column_tags WHERE catalog_name='ml_ugc_derived_prod_us_west_2' AND table_name LIKE '%eval_xt_prod_traffic_2026_01_20_02_10_with_2026_05_18_model_preprocessing_2026_05_18_14_14_3345678';
-- Result: 46 tags ✅

# Our fresh us_west_2 preprocessing output (from failing eb95)
SELECT COUNT(*) FROM system.information_schema.column_tags WHERE catalog_name='ml_ugc_derived_prod_us_west_2' AND table_name LIKE '%REAL_corrected_2026_06_04%preprocessing%';
-- Result: 0 tags ❌
```

## Workaround (cache-hit-trick)

Clone a prior successful per-region eval run and override **only** `BASE_MODEL_MLFLOW_URI`. Keep `INPUT_TABLE_NAME`, `CUR_TIME_STAMP`, `OUTPUT_PREFIX`, and `workflow_name` identical to the cached run. This forces `preprocessing` to cache-hit on the proven-good 05-18 tagged tables, while `run_triton_model_inference` (the only task that consumes `BASE_MODEL_MLFLOW_URI`) runs fresh against our model.

See Phase 9 in `SOP.md` for the exact procedure and the per-region cached preprocessing reference table.

## Validation that the workaround actually evaluates OUR model

The cache-hit only affects `preprocessing` + `generic_json_composition` (which compose the input JSON from queries — no model involvement). The `run_triton_model_inference` task is downstream and consumes `mls_user_def_MLFLOW_URI` directly:

```bash
# Confirmed for all 4 region runs on 2026-06-04 23:35 PT:
databricks --profile ml-ugc-prod jobs get-run <inner_dbx_rid> | jq '.tasks[] | select(.task_key=="run_base_inference-us_west_2") | .notebook_task.base_parameters.mls_user_def_MLFLOW_URI'
# → "dbfs:/databricks/mlflow-tracking/3773965476281976/dfcb4ba7788f4d9a95721b77f5de6e10/artifacts/assets.tar.gz"
# ✅ Triton inference IS using our new packaging
```

## Permanent fix (not done from this environment)

The platform-level fix is in the ML Studio `preprocessing` task code path: when writing the output table, the task must apply the column tags **regardless of cache state**. Currently the tag-write step is conditional on a path that only runs when a prior table doesn't exist. The fix belongs in the ml-studio repo's `preprocessing` notebook — escalation to `#help-mlplatform` recommended for the next cycle's owner.
