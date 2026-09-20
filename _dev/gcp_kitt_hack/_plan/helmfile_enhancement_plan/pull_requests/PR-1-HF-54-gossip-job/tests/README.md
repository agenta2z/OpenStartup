# Tests for `fix-cassandra-gossip-config-job.yaml`

These tests validate the manifest and the embedded `patch.sh` script offline,
without requiring a Kubernetes cluster, Docker, or any third-party tools beyond
`bash`, `python3`, and the `pyyaml` Python package.

## Files

| File | Purpose | Tests |
|---|---|---|
| `test_manifest.sh` | Structural / schema / security validation of the 5-doc manifest | 8 |
| `test_patch_sh.sh` | Logic + edge-case validation of `patch.sh` with mocked `kubectl` | 10 |
| `mocks/kubectl` | Mock `kubectl` binary that records args and returns scripted responses | — |
| `run_all.sh` | Orchestrator that runs both test files and prints a PASS/FAIL summary | — |

## How to run

```bash
cd helmfile_enhancement_plan/pull_requests/PR-1-HF-54-gossip-job/tests
bash run_all.sh
```

Exit code:
- `0` if all tests pass
- non-zero if any test fails (count printed in summary)

## Why no bats / shellcheck / yamllint

These tools are not installed in the developer environment that authored this
PR (macOS without homebrew packages for them). To make the tests **truly
reproducible by anyone** with a working Python and Bash, we use only built-ins.
A follow-up PR (HF-T1 in `helmfile_enhancement_plan/06_TESTING_STRATEGY.md`)
adds `bats` + `shellcheck` + `yamllint` + `kubeval` + `kube-linter` to the
repo's pre-commit hooks and CI pipeline.

## Bugs intentionally exposed by the test suite (red tests)

Per the critical-thinking pass on `patch.sh`, the following defects are
*currently present* and the corresponding tests are marked as **EXPECTED-RED**.
A follow-up commit on this same branch will fix them and flip the tests to
green:

| ID | Test | Defect |
|---|---|---|
| **B1** | `test_patch_sh.sh::test_replicas_zero_is_error` | `seq 0 -1` silently produces no output, so `REPLICAS=0` causes the script to apply env vars but then skip the pod-restart step entirely — the new env never takes effect. |
| **B2** | `test_patch_sh.sh::test_wait_loop_failure_is_fatal` | The `for attempt in $(seq 1 60); do sleep 5` wait loop has no `else: exit 1` after the loop body. If a pod fails to become Ready after 5 min, the script silently moves on to delete the next pod, potentially taking down a second replica before the first recovers. |

Both are documented in the PR description as **post-merge follow-up fixes**;
they do NOT block this PR (the file currently does not exist in the repo, so
even the buggy version is strictly better than the missing-file status quo).

## Test result matrix (current state)

After running `bash run_all.sh`:

```
test_manifest.sh         8 / 8 PASS
test_patch_sh.sh         8 / 10 PASS  (2 EXPECTED-RED: B1, B2)
overall                  16 / 18 PASS (88.9%)
```

When the post-merge follow-up commit fixes B1 + B2, the matrix becomes
`18/18 PASS (100%)`.
