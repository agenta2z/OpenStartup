# Investigation Notes — ML Studio Quick Start

A condensed log of what I learned while building the working `02-submit-job.sh` and the workflow YAML, for future engineers who want to extend or debug it.

---

## 1. The architecture (verified live)

```
┌──────────────────────┐    atlas ml workflow run     ┌──────────────────────────┐
│ Your laptop          │   ─────────────────────────► │ ml-studio-orchestrator   │
│ ($ atlas auth login) │   (atlas SSO + ASAP, no SSH) │ (per region)             │
└──────────────────────┘                              └────────────┬─────────────┘
                                                                   │
                                                          POST /workflow/run
                                                                   ▼
                                          ┌─────────────────────────────────────┐
                                          │ Databricks Workflows Runner         │
                                          │  ├─ Stage 1 (Databricks cluster):  │
                                          │  │   llm_dataset_preparation       │
                                          │  │   reads HF dataset, writes Spark│
                                          │  └─ Stage 2 (ML Fabric pod):       │
                                          │      llm_ft_with_llama_factory     │
                                          │      LoRA SFT, MLflow logs         │
                                          └─────────────────────────────────────┘
```

**No YubiKey is needed anywhere in this flow.** That's the entire point of using ML Studio over ML Fabric Interactive (which requires SSH = YubiKey).

---

## 2. Three lessons learned the hard way

### Lesson 1 — `is_default: true` cannot be a fabric platform
**Symptom**: Validation fails with
> `Module task prep_data is Databrick Python module, it can NOT be run on mosaicml or mlfabric platform.`

**Root cause**: The data-prep module (`llm_dataset_preparation` or the older `mlp_prepare_llm_fine_tune_datasets`) is a **Databricks Python module**, so it MUST run on a `databricks/spark` platform. If you set `fabric_*` as the default and don't add a Databricks platform, the data-prep step has nowhere to run.

**Fix**: Always include a `databricks/spark` platform with `is_default: true`. Use `platform_override: "fabric_*"` only on training/inference steps that actually need GPU.

**Verified pattern from production** (`nl2cypher_finetuning_sft_gptoss_20b_lora.yaml`):
```yaml
platforms:
  - name: "default"
    is_default: true
    type: databricks/spark
    runtime: 16.4.x-cpu-ml-scala2.13
    instance_type: r6id.2xlarge
  - name: "fabric"
    is_default: false
    type: ml_fabric
    instance_type: h200_141gb_8x
```

### Lesson 2 — `mlp_prepare_llm_fine_tune_datasets` ⇒ deprecated; use `llm_dataset_preparation`
**Symptom**: Validation passes but the run fails with no clear error, OR data prep step succeeds but fingerprints/output URI is wrong.

**Root cause**: The newer module name `llm_dataset_preparation` is what currently-maintained workflows use. The older `mlp_prepare_llm_fine_tune_datasets` may still validate but is in transition.

**Fix**: Use `llm_dataset_preparation` (verified in `nl2cypher_finetuning_sft_gptoss_20b_lora.yaml`).

### Lesson 3 — `template:` value MUST match the model family
**Symptom**: SFT step runs, then fails inside the LLaMA-Factory tokenization stage with cryptic chat-template errors.

**Root cause**: `template:` in LLaMA-Factory tells it which chat template to apply. If you pick `chatml` for a Llama-3 model (which uses `<|start_header_id|>...<|end_header_id|>` tokens), the dataset gets tokenized into garbage and the tokenizer eventually errors out.

**Mapping** (from production examples):
| Model family | `template:` value |
|---|---|
| `meta-llama/Llama-3.x-*-Instruct` | `llama3` |
| `openai/gpt-oss-*` | `gpt` |
| `Qwen/Qwen2.5-*` | `qwen` |
| `mistralai/Mistral-*-Instruct` | `mistral` |
| OpenAI-format messages from any model | `chatml` (sometimes works as a generic) |

### (Bonus) Lesson 4 — `run-status -r` expects DATABRICKS run ID, not workflow UUID
**Symptom**: `argument '<uuid>' is invalid. Option databricks run id must be 30 or less characters long.`

**Root cause**: The CLI has TWO ID types. `-r` is the short Databricks run ID (e.g. `335905192439767`). `-w` is the ML Studio workflow run UUID (e.g. `596ddd17-f6f5-4f25-afce-005053446f18`).

**Fix**: Use `-w <UUID> --region us`.

---

## 3. Anatomy of a workflow descriptor (what each section does)

```yaml
name: <unique-workflow-name>          # appears in URLs, MLflow experiments
use_case: ai_modeling                 # SSAM-gated; you must have access to this use_case
team: ai-modeling                     # informational
business_unit: "Central AI"           # informational
owner: <you>@atlassian.com
realms:
  - us                                # regions to deploy to (us, eu, syd, ...)

variables:                            # Jinja-style {{var}} substitutions
  - name: ...
    value: ...

module_tasks:                         # the actual stages
  - step_name: ...                    # human-readable name; appears in Databricks task graph
    module: ...                       # registered ML Studio module
    version: ":latestAlpha"           # tag or pinned version
    platform_override: "..."          # OPTIONAL; routes step to a non-default platform
    parameters:
      - name: ...
        value: ...                    # supports {{var}} interpolation
    depends_on:                       # DAG edges
      - <other_step_name>

platforms:                            # compute platforms the steps run on
  - name: ...
    is_default: true|false            # exactly one must be default
    type: databricks/spark|ml_fabric|...
    instance_type: ...
    scaling:
      min: ...
      max: ...
```

---

## 4. Useful CLI commands

```bash
# Validate without consuming compute
atlas ml workflow validate -d <yaml> -e staging

# Submit a run (returns run_id JSON)
atlas ml workflow run -d <yaml> -e staging --json [--open-url]

# Poll status
atlas ml workflow run-status -e staging -w <UUID> --region us [--simple] [--include-all]

# Get logs (ML Studio platform-step level only — NOT user step logs)
atlas ml workflow get-logs -r <UUID> -s <step_name>

# Lookup workflow run via Databricks ID (the response includes the UUID)
atlas ml workflow run-status -e staging -r <DATABRICKS_RUN_ID> --region us
```

---

## 5. Where to look for examples

In order of usefulness:

1. **`/Users/tchen7/MyProjects/atlassian_packages/ml-studio/workflows/src/ai_modeling/nl2cypher/nl2cypher_finetuning_sft_gptoss_20b_lora.yaml`** ⭐ Tested OSS-20B LoRA SFT, recent
2. `/Users/tchen7/MyProjects/atlassian_packages/ml-studio/workflows/src/ai_experience/llm_post_training/adf_pt_sft_with_json_validation_full.yaml` — full 10-stage PT+SFT+eval pipeline
3. `/Users/tchen7/MyProjects/atlassian_packages/ml-studio-docs/content/platform/ml-studio/model-training/llm-fine-tuning/example/index.md` — written docs

---

## 6. What I haven't verified

- Whether `report_to: mlflow` actually pushes to the Databricks MLflow registry (likely yes, but I haven't browsed there)
- Whether the MLflow experiment name matches `name:` (workflow name) or has additional namespacing
- Whether the LoRA adapter checkpoint is downloadable via `atlas ml` CLI (may need `databricks fs cp` or web UI)
- The exact retention policy for staging artifacts (artifacts under `/Volumes/ml_ugc_derived_stg_us/.../<run_id>/`)
- Whether OSS-20B with `quantization_bit: 4` fits in 8× H200 with `max_steps: 500` (tested in production for 20 steps)

---

## 7. Hand-off questions for the team

If/when you bring this to the AI Catalyst team for review:

1. Does Atlassian have an opinion on `template: llama3` vs `chatml` for `openai_messages`-formatted ultrachat data? (Might affect what the model actually learns.)
2. Is there an internal `gpt-oss-safeguard-20b` model (mentioned in PLAN.md) that we should use instead of the public `openai/gpt-oss-20b`?
3. What's the canonical place to register a new "experiment" so it shows up alongside `tenant-embed`, `nl2cypher`, etc.?
