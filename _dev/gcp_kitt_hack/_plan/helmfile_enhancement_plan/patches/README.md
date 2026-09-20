# Patches Directory — git-apply ready artifacts

This directory holds **ready-to-apply unified diffs** for every `PR-T-NN` testing-infrastructure PR defined in `../06_TESTING_STRATEGY.md`. Each patch is self-contained, file:line precise, and verified to apply cleanly against the workspace state at **2026-05-11**.

## How to apply

```bash
# Apply in dependency order (see 06_TESTING_STRATEGY.md §10):
cd /Users/tchen7/MyProjects   # repo root containing atlassian_packages/

# Tier-0 cleanup
git apply --check CoreProjects/OpenStartup/_dev/gcp_kitt_hack/_plan/helmfile_enhancement_plan/patches/PR-T-11.patch
git apply       CoreProjects/OpenStartup/_dev/gcp_kitt_hack/_plan/helmfile_enhancement_plan/patches/PR-T-11.patch

# Tier-1 (minimum viable test fabric)
git apply --check CoreProjects/.../patches/PR-T-02.patch && git apply CoreProjects/.../patches/PR-T-02.patch
git apply --check CoreProjects/.../patches/PR-T-09.patch && git apply CoreProjects/.../patches/PR-T-09.patch
git apply --check CoreProjects/.../patches/PR-T-01.patch && git apply CoreProjects/.../patches/PR-T-01.patch

# Tier-2 quality bars
git apply --check CoreProjects/.../patches/PR-T-03.patch && git apply CoreProjects/.../patches/PR-T-03.patch
git apply --check CoreProjects/.../patches/PR-T-12.patch && git apply CoreProjects/.../patches/PR-T-12.patch

# Tier-3 contract + chaos
git apply --check CoreProjects/.../patches/PR-T-08.patch && git apply CoreProjects/.../patches/PR-T-08.patch
git apply --check CoreProjects/.../patches/PR-T-06.patch && git apply CoreProjects/.../patches/PR-T-06.patch
git apply --check CoreProjects/.../patches/PR-T-07.patch && git apply CoreProjects/.../patches/PR-T-07.patch
git apply --check CoreProjects/.../patches/PR-T-10.patch && git apply CoreProjects/.../patches/PR-T-10.patch

# Quality follow-ups
git apply --check CoreProjects/.../patches/PR-T-04.patch && git apply CoreProjects/.../patches/PR-T-04.patch
git apply --check CoreProjects/.../patches/PR-T-05.patch && git apply CoreProjects/.../patches/PR-T-05.patch
```

## Conventions

- Patches use **paths relative to the workspace root** (e.g., `atlassian_packages/gcp_kitt/helmfile/...`).
- Every patch starts with `--- a/<path>` / `+++ b/<path>` so `git apply` works without `-p` adjustments.
- New files are introduced with `--- /dev/null` / `+++ b/<path>` and explicit `new file mode 100644` (or `100755` for shell scripts).
- Patches that touch **binary files** (PR-T-11 only) cannot be expressed in `git diff` text format — they ship a `git rm` command instead in the patch header.

## Patch index

| # | Patch file | LoC | Files added | Files modified | Files deleted | Depends on |
|---|---|---|---|---|---|---|
| 01 | `PR-T-01.patch` | +180 | 2 | 0 | 0 | none |
| 02 | `PR-T-02.patch` | ±5 | 0 | 1 | 0 | none |
| 03 | `PR-T-03.patch` | +25 | 0 | 2 | 0 | PR-T-01, PR-T-02 |
| 04 | `PR-T-04.patch` | +60 / ±50 | 0 | 5 | 0 | PR-T-02 |
| 05 | `PR-T-05.patch` | ±200 | 1 | 2 | 1 | none |
| 06 | `PR-T-06.patch` | +60 | 2 | 1 | 0 | PR-T-01 |
| 07 | `PR-T-07.patch` | +110 | 4 | 1 | 0 | PR-T-01 |
| 08 | `PR-T-08.patch` | ±20 | 0 | 1 | 0 | none |
| 09 | `PR-T-09.patch` | +90 | 1 | 1 | 0 | PR-HF-14 |
| 10 | `PR-T-10.patch` | +85 | 1 | 0 | 0 | PR-HF-10 |
| 11 | `PR-T-11.patch` | n/a | 0 | 1 | 1 (76 MB) | none |
| 12 | `PR-T-12.patch` | +20 | 1 | 1 | 0 | PR-T-01 |

## Verification protocol

For every patch, the workflow is:
1. `git apply --check <patch>` — must exit 0
2. `git apply --3way <patch>` — apply with 3-way merge fallback
3. Run the **acceptance command** from §8 of `06_TESTING_STRATEGY.md`
4. If acceptance fails → `git apply -R <patch>` to roll back, log the failure mode in `../05_RISK_AND_VALIDATION.md` §1.

## What patches DO NOT do

- They do **not** create branches, commits, or PRs. The executor (human or bot) must `git checkout -b <branch>` per the suggested branch name in `06_TESTING_STRATEGY.md` §8.
- They do **not** modify the live cluster. Acceptance commands that require `kubectl` are listed but not auto-run.
- They do **not** include the HF-NN patches; those are described in `04_PR_BREAKDOWN.md` and would live in a sibling `patches-hf/` directory if generated later.
