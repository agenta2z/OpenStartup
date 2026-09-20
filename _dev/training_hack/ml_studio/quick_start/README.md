# ML Studio Quick Start — Hack: SFT `gpt-oss-20b` on Public HuggingFace Data

> **STATUS: VERIFIED WORKING ✓** — Real SFT job for `openai/gpt-oss-20b` completed end-to-end on 2026-05-05.
> Run UUID: `94b1f4c2-4086-4747-9700-125ad7a3cb25` |
> [Databricks UI](https://atlassian-ml-ugc-stg.cloud.databricks.com/jobs/1087078232630387/runs/967361672135756)
> Wall-clock: **4m 20s** (1m data prep + 3m 15s training)
>
> **Goal:** Submit a real, end-to-end LLM SFT training run on **ML Studio** (Atlassian's Databricks-based ML platform) within minutes, with **no YubiKey required**, no SSH, no GPU pod babysitting.
>
> This is an opinionated minimal-viable hack distilled from a real production workflow ([`nl2cypher_finetuning_sft_gptoss_20b_lora.yaml`](file:///Users/tchen7/MyProjects/atlassian_packages/ml-studio/workflows/src/ai_modeling/nl2cypher/nl2cypher_finetuning_sft_gptoss_20b_lora.yaml)). The ONLY 3 substantive changes vs production are:
> 1. **`name`** is unique to avoid clashing with the prod-released workflow
> 2. **`dataset`** swapped from internal Spark table → public `HuggingFaceH4/ultrachat_200k` (so anyone can run it without internal data access)
> 3. **`max_steps: 20`** → **`max_steps: 15`** (slightly faster smoke)
>
> Everything else (`base_model: openai/gpt-oss-20b`, `instance_type: h200_141gb_8x`, `quantization_bit: 4`, `lora_rank: 16`, `template: gpt`, etc.) is **verbatim production**.

---

## TL;DR — Three commands

```bash
cd /Users/tchen7/MyProjects/CoreProjects/OpenStartup/_dev/training_hack/ml_studio/quick_start

# 1. Validate the workflow YAML (no compute used; surfaces schema errors)
DRY_RUN=true bash scripts/02-submit-job.sh

# 2. Submit the run to ML Studio staging
bash scripts/02-submit-job.sh

# 3. Monitor until completion
bash scripts/03-monitor-run.sh
```

That's it. **Total wall-clock** on a healthy day: ~25-40 min from submit → trained adapter checkpoint.

---

## What this delivers

| Component | File | Purpose |
|---|---|---|
| Workflow descriptor | `configs/hack_oss_20b_sft.yaml` | The 2-stage SFT workflow (data prep → SFT train) |
| Mock data generator (optional) | `scripts/01-make-mock-data.py` | Generates 50-row synthetic SFT JSONL if you want to use *your* data instead of a HuggingFace dataset |
| Submit script | `scripts/02-submit-job.sh` | Validates + submits the workflow via `atlas ml workflow run` |
| Monitor script | `scripts/03-monitor-run.sh` | Polls run-status until terminal state |
| `artifacts/` | (generated) | `last_run_id.txt`, `last_env.txt`, `mock_sft_50.jsonl` |
| `logs/` | (generated) | All `atlas` CLI stdout/stderr captured here |

---

## Decisions and why

### Why this is *NOT* the full `gpt-oss-20b-pt-sft-v2-full-adf-json-validation` workflow

| Aspect | Production workflow | This hack | Reason |
|---|---|---|---|
| Stages | 10 (data prep × 2, train × 2, hydration, formatting, copy, infer, save, join, validate) | **2** (data prep + SFT) | Smoke proves submission works end-to-end, not the full eval loop |
| Model | `openai/gpt-oss-20b` (~20B params) | `HuggingFaceTB/SmolLM2-135M-Instruct` (~135M) | Fits on 1× L40s; smoke completes <30 min instead of multi-hour |
| Data | Internal Spark tables in `mls_usecase_ai_modeling_experimental` (requires SSAM access) | Public HuggingFace dataset (`HuggingFaceH4/ultrachat_200k`) | Removes data-permissioning blocker entirely |
| Compute | 8× H200 fabric pod | 1× L40s fabric pod | Cheapest fabric option |
| Tuning method | `full` parameter SFT | `lora` (rank 8) | Tiny adapter; ~10 MB checkpoint |
| Pretrain stage | Yes (1 epoch over PT data) | Skipped | SFT-only is sufficient for plumbing test |

**Path to upgrade to the real OSS-20B run** — see [Upgrade Path](#upgrade-path-to-real-oss-20b) below.

### Why submit via `atlas ml workflow` instead of raw `atlas slauth curl`

Both work and hit the same backend (`ml-studio-orchestrator`). The CLI wrapper:

- Auto-discovers the right orchestrator URL per env (staging/prod)
- Handles auth refresh transparently
- Returns a more human-friendly response
- Has `validate` / `submit` / `run` / `run-status` / `get-logs` first-class subcommands

(The raw `atlas slauth curl --aud=ml-studio-orchestrator` approach is documented in [`/atlassian_packages/ml-studio-docs/.../programmatic-triggering/index.md`](file:///Users/tchen7/MyProjects/atlassian_packages/ml-studio-docs/content/platform/ml-studio/workflows/programmatic-triggering/index.md) — useful for CI/cron, not for interactive iteration.)

---

## Pre-requisites (verified 2026-05-05)

| Item | How to verify | Where to get it |
|---|---|---|
| `atlas` CLI installed | `which atlas` | <https://developer.atlassian.com/platform/atlas-cli/users/install/> |
| Atlas SSO logged in | `atlas auth status` | `atlas auth login` |
| `atlas ml` plugin (beta) | `atlas ml workflow --help` | `atlas plugin install -n ml && atlas plugin upgrade -n ml -c beta` |
| Membership in an `ai_modeling`-adjacent SSAM group | (you can submit to an `EXPERIMENTAL` workflow with `use_case: ai_modeling` only if you're allowed to write to that use_case) | Request via SSAM: search "ai-modeling" |
| **NO YubiKey required** | — | (Confirmed: ML Studio uses ASAP/SAML auth, not SSH) |

---

## Step-by-step run

### Step 1 — (Optional) Inspect the workflow

```bash
$EDITOR configs/hack_oss_20b_sft.yaml
```

Things you might want to tweak (all are workflow `variables`):
- `hf_dataset_name` — switch to `tatsu-lab/alpaca` or another public HF dataset
- `base_model` — switch to a different small instruct model
- `max_steps` — increase from 20 if you want more training
- `lr` — learning rate

### Step 2 — Validate (no compute used)

```bash
DRY_RUN=true bash scripts/02-submit-job.sh
```

Expected output:
- `✓ Validation passed` — go to Step 3
- `❌ Validation failed` — read `logs/validate-*.log`. Common errors:
  - `module not found: llm_ft_with_llama_factory` → the module renamed; check the doc index
  - `version not found` → the `:latestAlpha` tag drifted; pin to a specific version
  - `instance_type not allowed` → your team isn't allowlisted for `l40s_48gb_1x` on fabric

### Step 3 — Submit

```bash
bash scripts/02-submit-job.sh
```

Expected response (truncated):
```json
{
  "run_id": "abc123-...",
  "blueprint_id": "bp-...",
  "status": "QUEUED",
  "url": "https://atlassian-ml-ugc-prod.cloud.databricks.com/jobs/.../runs/..."
}
```

The script writes `artifacts/last_run_id.txt`.

### Step 4 — Monitor

```bash
bash scripts/03-monitor-run.sh
```

This polls every 15s and prints status changes. Terminal states: `SUCCEEDED`, `FAILED`, `CANCELLED`, `TIMED_OUT`.

When it ends:
```bash
# Stream logs from a specific failed step
atlas ml workflow get-logs -e staging -r <RUN_ID>
```

---

## Where the trained model lands

Per the `report_to: mlflow` line in the SFT config, training metrics + final adapter are pushed to:

- **Databricks MLflow registry** under experiment name derived from the workflow name (`hack-tony-sft-smoke-v1`)
- **Adapter checkpoint** as an MLflow artifact in the run

Browse to the URL returned by `atlas ml workflow run --json` to see them in Databricks UI.

---

## Upgrade path to real OSS 20B

When the smoke run succeeds and you want to scale up to the real `openai/gpt-oss-20b`:

1. **Edit** `configs/hack_oss_20b_sft.yaml`:
   ```yaml
   variables:
     - name: base_model
       value: openai/gpt-oss-20b      # ← change
     - name: max_steps
       value: '500'                    # ← realistic
   ```
2. **Uncomment** the `fabric_8xh200` platform block at the bottom and switch `platform_override`:
   ```yaml
   - step_name: sft_train
     platform_override: "fabric_8xh200"  # ← change
   ```
3. **Switch tuning method** from LoRA → full (recommended for OSS 20B per the production workflow):
   ```yaml
   finetuning_type: full
   ```
4. **Switch dataset** from public HF to your real Spark table (see the `01-make-mock-data.py` script header for the upload procedure).
5. Re-validate, then submit to **prod** (not staging):
   ```bash
   ENV=prod bash scripts/02-submit-job.sh
   ```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `atlas: command not found` | atlas CLI not installed | See pre-reqs |
| `atlas ml: command not found` | beta plugin missing | `atlas plugin install -n ml && atlas plugin upgrade -n ml -c beta` |
| `401 Unauthorized` | SSO session expired | `atlas auth login` |
| `validate` fails with "use_case: ai_modeling not authorized" | Your SSAM group can't submit under that use_case | Pick a use_case you have access to OR request access |
| `module not found: llm_ft_with_llama_factory` | Module renamed in latest ML Studio | Check `/atlassian_packages/ml-studio/modules/src/ml_platform/` for the current name |
| `version not found: :latestAlpha` | Tag was retracted | Use `version: ":stable"` or pin to a specific semver |
| `dataset_name HuggingFaceH4/ultrachat_200k not accessible` | HF Hub creds missing on fabric pod | Use a smaller built-in dataset or set HF_TOKEN secret |
| Run hangs at `QUEUED` for 10+ min | Fabric capacity wait | Switch to `staging` env, or off-peak hours; check `#help-ml-platform` |
| Run fails at `sft_train` immediately | OOM on 1× L40s | Reduce `per_device_train_batch_size` to 2 or 1 |

---

## Honest limitations

1. **The exact `version: ":latestAlpha"` may drift.** I copied it from the production workflow. If validation fails, pin to a known-good version (look at `git log` of the production workflow YAML).
2. **`l40s_48gb_1x` does NOT work** with `llm_ft_with_llama_factory`. We tried it; the SFT step fails immediately. Always use `h200_141gb_8x`.
3. **The `mlp_llm_finetune` module's old API (`base_model_name`/`dataset_group_name`/`outputs_name`) is deprecated** as of v0.4.x — use `base_model_uri`/`data_uri`/`step_name` instead. The qwen2_5 workflow YAML in the repo is stale.
4. **`HuggingFaceTB/SmolLM2-*` and `meta-llama/Llama-3.2-*-Instruct` were tried but failed.** SmolLM2 may not have a registered LLaMA-Factory template; Llama-3.2 is gated and needs an HF_TOKEN secret. **Stick to `openai/gpt-oss-20b`** unless you wire up an HF_TOKEN.
5. **Cost**: a 4-min run on 8× H200 staging is roughly $1-3 (rough estimate). Multiply by `max_steps` if you increase that variable significantly.
6. **No checkpoint download script yet.** The trained LoRA adapter lands in MLflow under the experiment derived from the workflow `name`. To download, you need the Databricks UI or `databricks mlflow` CLI.

---

## File map

```
quick_start/
├── README.md                           # this file
├── configs/
│   └── hack_oss_20b_sft.yaml          # workflow descriptor
├── scripts/
│   ├── 01-make-mock-data.py           # OPTIONAL: generate 50-row mock SFT data
│   ├── 02-submit-job.sh               # validate + submit
│   └── 03-monitor-run.sh              # poll run-status
├── artifacts/                          # last_run_id.txt, last_env.txt, mock data
└── logs/                               # all atlas CLI output
```
