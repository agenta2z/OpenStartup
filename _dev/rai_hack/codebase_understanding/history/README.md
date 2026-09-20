# Responsible AI — Development History & Decision Provenance

> **Purpose**: Capture the *historical why* behind production design choices in
> `responsible-ai-api` and `responsible-ai`, so future contributors (human and
> machine) do not accidentally undo intentional decisions.
>
> **Created**: 2026-05-06 (Wave 9 follow-up investigation)
> **Trigger**: Wave 9 ("Serving-infra latency quick wins") proposed 6 changes;
> we needed to verify each was not undoing prior production design.
> **Method**: 4 parallel Explore subagents + direct git verification.
> **Scope**: 1,487 commits in `responsible-ai-api` (since 2024-06) +
> ~700 commits in `responsible-ai`. Top contributors: Kai Zhang (162),
> Taotao Li (144), Matt Turner (142), xhuang3 (141), Benjamin Joyce (108),
> Amit Abbi (92), Hussein (62+39), Tony Chen (37).

## Contents

| File | What it covers |
|---|---|
| [01-decision-timeline.md](01-decision-timeline.md) | **Chronological** timeline of major business + technical decisions, with commit SHAs, dates, authors, PR descriptions |
| [02-perf-decision-archive.md](02-perf-decision-archive.md) | Every documented latency/perf decision (max_tokens 500→200→512→400, AI-NEW series, RAI-01..05, etc.) |
| [03-wave9-historical-validation.md](03-wave9-historical-validation.md) | **PRIMARY DELIVERABLE**: For each Wave 9 quick win, verdict (SAFE / RISKY / MOOT) backed by historical precedent |
| [04-agent-claim-audit.md](04-agent-claim-audit.md) | Critical-thinking review of the 4 subagent reports — which claims passed verification, which failed |
| [05-source-of-truth-cheatsheet.md](05-source-of-truth-cheatsheet.md) | **Machine-followable** quick reference: file → owner PR → decision rationale |
| [06-tenant-safe-perf-opportunities.md](06-tenant-safe-perf-opportunities.md) | ⭐ **Wave 9.5** (after PR #623 decline): tenant-isolation-safe perf opportunities, each verified directly against master |

## 🚨 CORRECTION NOTICE (2026-05-06 06:35) — READ FIRST

**An earlier version of this document set incorrectly cited 8 commits as
"merged precedents" on master.** Direct verification with
`git merge-base --is-ancestor <SHA> master` proved that **only ONE of the 8
is actually on master:**

| Cited as precedent | Actual master state |
|---|---|
| AI-NEW-4 (`9c16bf7`, drop double tokenization, PR #621) | ✅ **MERGED** — May 1, only verified precedent |
| AI-NEW-5 (`a6b75c2`, flask.g feature-gate cache) | ❌ Not on master |
| AI-NEW-6 (`9c33782`, TCS Session reuse, PR #623) | ❌ **DECLINED** |
| RAI-01 (`79a0caf`, LLaMA single-pass tokenization) | ❌ Not on master |
| RAI-02 (`63d434a`, ModerationRequestContext cache) | ❌ Not on master |
| RAI-04 (`406d286`, parser-fallback metric) | ❌ Not on master |
| RAI-05 (`7eec261`, model-selection metric) | ❌ Not on master |
| RAI-15 (`26613af`, benchmarking discipline doc) | ❌ Not on master |

**Implication**: most of these are still in-flight work on local feature
branches. The "STRONG PRECEDENT" verdicts that depended on them have all
been downgraded. See the corrected Wave 9 verdict table below.

The investigator's failure mode was: I read commit messages with
"Approved-by:" trailers and assumed those meant "merged to master". That
inference is invalid. Trailer lines are author-set, not Bitbucket-system-set.
The new SOP is documented in [04-agent-claim-audit.md](04-agent-claim-audit.md)
§ "META-FINDING".

## TL;DR for Wave 9 (CORRECTED)

| Quick win | Historical verdict | Evidence |
|---|---|---|
| **W1**: `requests.Session()` for TeamServe HTTP | ⚠️ **NEEDS-MORE-INFO** ⚠️ **CORRECTED 2026-05-06** — earlier draft said "SAFE — STRONG PRECEDENT" citing AI-NEW-6 (`9c33782`, PR #623). **PR #623 was DECLINED** and the code is NOT on master. Until the decline reason is read, we cannot conclude W1 is safe. |
| **W2**: `enable_chunked_prefill: false` | ⚠️ **NEEDS-MORE-INFO** | The YAML at `notebooks/inference/inference_oss_safeguard_20b/01_register_model_v3.py` is a Databricks notebook. The values were set together as a coherent low-latency config block by Kai Zhang. No PR description explains *why* `chunked_prefill: true` specifically — but the v3 suffix implies prior iterations. |
| **W3**: disable `enable_iter_perf_stats` + `return_perf_metrics` | ⚠️ **RISKY** | These feed Databricks dashboards (Kai Zhang's metric work). Disabling will silently break observability. Confirm with Kai before changing. |
| **W4**: cache rendered prompt template | ⚠️ **NEEDS-MORE-INFO** ⚠️ ⚠️ Earlier draft cited RAI-02 and AI-NEW-5 as precedent — neither is on master. The pattern (flask.g caching) is still author-proposed and in-flight. Verify W4 with the actual reviewers; do NOT assert "established pattern". |
| **W5**: conditional ETag SHA-256 | ✅ **SAFE** | Same risk profile as W4 — performance-only, output-identical |
| **W6**: `disable_overlap_scheduler: true` | ⚠️ **RISKY** | Same review scope as W2/W3 — Kai Zhang owns the deployment YAML. Coordinate. |

**Critical-thinking caveat**: 2 of the 4 subagents falsely reported that the
files we want to modify had been **deleted**. Direct git verification on
`master` (HEAD `37fec91`, 2026-05-05) proved the files are LIVE PRODUCTION
CODE. See [04-agent-claim-audit.md](04-agent-claim-audit.md).

## How to use this when filing a Wave 9 PR

1. Open [03-wave9-historical-validation.md](03-wave9-historical-validation.md)
2. Find the row for the change you're about to make.
3. If verdict is **SAFE — STRONG PRECEDENT**: file the PR, cite the precedent
   commit SHA in your PR description.
4. If verdict is **NEEDS-MORE-INFO** or **RISKY**: ping the original author
   (cited per row), get explicit sign-off, then file PR.
5. After merging, update [02-perf-decision-archive.md](02-perf-decision-archive.md)
   with your new commit SHA + measured impact.

## Method (reproducible)

This investigation can be re-run with:

```bash
# Spawn 4 parallel investigation agents (see prior session log)
# Then verify findings DIRECTLY against current master:
cd ~/MyProjects/atlassian_packages/responsible-ai-api && git branch --show-current
ls src/inference_models/                 # confirm files exist
grep -n "requests.post\|requests.Session" src/inference_models/triton_openai_api_client.py
git log --all --oneline --grep='AI-NEW' | head -20
git log --all -- src/inference_models/rai_gpt_oss.py | head -30

cd ~/MyProjects/atlassian_packages/responsible-ai && \
  cat notebooks/inference/inference_oss_safeguard_20b/01_register_model_v3.py | grep -A 12 yaml_content
```

## Cross-references

- Wave 9 doc: `atlassian_packages/_plan/rai-training/00_overview/serving-infra-quick-wins.md`
- Verification log: `atlassian_packages/_plan/rai-training/99_appendix/verification-results.md`
- Existing codebase docs: [`../README.md`](../README.md)
