# Resolved: Wrong `features.config` in P3 Tarot V2 packaging

**Discovered**: 2026-06-04 during 2nd refresh cycle attempt
**Resolved**: 2026-06-04 by overriding `features.config` to the proven-working gdrive recipe
**Resolution location**: Phase 3 in SOP.md (descriptor override pattern)

## Symptom

After P2 (filtered training) succeeded and P3 (Tarot V2 packaging) appeared to succeed, the 4-region eval failed at `run_triton_model_inference` with:

```
RuntimeError: Error(s) in loading state_dict for HybridModelMultiModalEmbedding:
  Missing keys: "categorical_embeddings.15.0.weight", ...
  Size mismatch for shared_layers.0.weight:
    checkpoint: torch.Size([64, 209])
    eval-time:  torch.Size([64, 224])
  Size mismatch for batch_norm_cont:
    checkpoint: 25 features
    eval-time:  32 features
```

## Root cause

The P3 blueprint defaulted to `features.config = l2_xt_3p_doc_cal_mf_no_sl_365_pg_v2_comment_jun_2026_250_token_ignore_embedding.config`.

This config has **32 continuous features and 16 categorical features**.

But our P2 training used config `gdrive_l2_xtenant_wf_init_feb_2026.yml`, which produces a model with **25 continuous features and 15 categorical features**.

Triton at inference-time loads:
1. The packaging's `assets.tar.gz` (which has the june config baked in → expects 224-dim input)
2. The model weights from `BASE_MODEL_MLFLOW_URI` (which were trained for 209-dim input)

Mismatch → state_dict load failure → eval fails.

## How the 06-01 cycle didn't hit this bug

The 06-01 cycle's P3 also used a default config — but in 06-01, the default was the gdrive config (matching the training). Sometime between 06-01 and 06-04, the P3 blueprint default was bumped to the june config without a corresponding training update.

## Fix

Override `features.config` in the P3 descriptor:

```bash
atlas ml workflow clone -r <prior_p3_success_dbx_rid> -e prod -o p3_corrected.yaml

# Patch
python3 -c "
import yaml
d = yaml.safe_load(open('p3_corrected.yaml'))
for v in d.get('variables', []):
    if v.get('name') == 'features_config':
        v['value'] = 'l2_xt_gdrive_wf_feb_2026_250_token_cal_ignore_embedding.config'
    if v.get('name') == 'l2_ranker_model.pt':
        v['value'] = 'dbfs:/databricks/mlflow-tracking/3747328226380826/<P2_MLFLOW_UUID>/artifacts/best_two_head_model.pt'
yaml.safe_dump(d, open('p3_corrected.yaml', 'w'))
"

atlas ml workflow run -d p3_corrected.yaml -e prod
```

Verified working on 2026-06-04 — produced packaging `dfcb4ba7788f4d9a95721b77f5de6e10` which loaded cleanly into Triton.

## Permanent fix (not done from this environment)

The P3 blueprint default should be reverted to the gdrive config, OR the june config should be made the default for both training AND packaging in lockstep. Escalation to the ml-studio repo owner (or whoever bumped the june config as P3 default).
