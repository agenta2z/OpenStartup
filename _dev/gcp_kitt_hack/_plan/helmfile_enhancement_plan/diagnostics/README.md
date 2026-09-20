# Crash Root-Cause Diagnostic — Interpretation Guide

> **Scope:** answer the question *"are the static defects in `helmfile_enhancement_plan/02_FINDINGS_CATALOG.md` actually causing the crashes/instability we observe, or are they dormant risks?"* — **before** spending engineer time shipping fixes.

## TL;DR

```bash
cd /Users/tchen7/MyProjects/CoreProjects/OpenStartup/_dev/gcp_kitt_hack/_plan/helmfile_enhancement_plan/diagnostics
bash crash_root_cause_diagnostic.sh         # run all 10 HF checks
NAMESPACE=temporal HF=HF-54,HF-56 bash crash_root_cause_diagnostic.sh   # subset
JSON=1 bash crash_root_cause_diagnostic.sh > diagnostic.json
```

Exit codes: **0** = ≥1 CONFIRMED · **1** = only LIKELY · **2** = nothing · **3** = diagnostic failed.

---

## Why the diagnostic exists

The static catalog (`02_FINDINGS_CATALOG.md`) lists 64 verified defects. **A static defect is not the same as an active root cause.** A `replicaCount: 1` is a real defect, but if no node has been drained recently it is a *dormant risk* — fixing it produces zero observable change in crash frequency. To allocate Tier-0 engineer time correctly, we need *runtime evidence* that discriminates active causes from dormant risks.

This script is **read-only**, **safe to run in production**, and **takes ~2 minutes** end-to-end.

---

## Verdicts and what they mean

| Verdict | Meaning | What to do |
|---|---|---|
| **CONFIRMED** | Static defect + runtime evidence both present. The defect is actively contributing to current symptoms. | Ship the fix in Tier-0. Expect measurable improvement. |
| **LIKELY** | Static defect present + partial runtime evidence (e.g., elevated metric but not pegged). May be active cause; may be dormant. | Re-run during peak traffic for higher signal. If still LIKELY, ship fix in T0–T1. |
| **UNLIKELY** | Static defect present but runtime evidence is absent. Defect is a structural risk but not the active cause now. | Keep in plan but de-prioritize to T2/T3. |
| **INCONCLUSIVE** | Diagnostic could not collect evidence (pod missing, exec failed, helm CLI absent). | Adjust env vars or run a targeted manual check. |

**Critical thinking:** an UNLIKELY verdict does NOT mean the defect is unimportant. It means the defect isn't the *primary* contributor to today's crashes. Many UNLIKELY items become CONFIRMED on the next node drain, traffic spike, or schema migration.

---

## Per-HF interpretation matrix

| HF | What CONFIRMED looks like | What LIKELY looks like | False-positive risk | False-negative risk | If CONFIRMED, ship |
|---|---|---|---|---|---|
| **HF-54** Missing gossip job file | File missing AND `nodetool status` shows `UN < total` (some nodes Down/Joining) | File missing, gossip currently healthy (could be intermittent) | Cassandra rolling restart can cause transient `UN < total`. **Mitigation:** re-run after 5 min. | Postsync hook can fail silently with no helm-history record. **Mitigation:** captured by binary file-missing check. | `PR-HF-54` (T0 day 1) |
| **HF-01** No startupProbe | ≥1 Temporal pod missing startupProbe AND ≥1 pod with `lastState.terminated.reason: Killed` or `OOMKilled` | startupProbe missing but no recent kubelet kills | `Killed` may indicate OOM, not probe-timeout. **Mitigation:** check `exitCode==137` (SIGKILL) vs `==1` (app exit). | Probe-fail only at startup; quiet-period diagnostic shows no recent restarts. **Mitigation:** widen `TIME_WINDOW_MIN`. | `PR-HF-01` (T0 day 3) **— must ship with HF-03 + HF-02** |
| **HF-03** replicaCount: 1 | ≥3 single-replica workloads AND recent `Evicted` events in namespace | ≥3 single-replica workloads, no recent evictions (structural risk only) | True but irrelevant if cluster has been stable for months. **Mitigation:** correlate with `kubectl get events --field-selector reason=Evicted`. | Single replica silently starves under load before crash; low-traffic window misses. **Mitigation:** check Temporal task-queue depth at peak hours. | `PR-HF-03` (T0 day 3) |
| **HF-02** No PDBs | 0 PDBs AND ≥1 `DrainNode` event recently | 0 PDBs, no recent drains (structural risk only) | Same as HF-03. PDB absence is a guarantee of outage on next drain, not today. | None. PDB absence is binary. | `PR-HF-02` (T0 day 3) |
| **HF-56** PostgreSQL maxConns | `too many connections` errors in last 15 min OR peak utilization ≥80% | Peak utilization 50–80% OR `max_connections ≤ 30` | Long-running idle-in-transaction sessions inflate count without indicating exhaustion. **Mitigation:** script filters `state IN ('active','idle in transaction')` and excludes `'idle'`. | Bursts may exceed during traffic spikes not captured in 30s sample window. **Mitigation:** script samples 5× at 5s; widen via re-running during peak. | `PR-HF-56` (T0 day 1) |
| **HF-58** ES yellow + replicas=1 | `status: red` OR `status: yellow` AND `unassigned_shards > 0` | None — ES is binary | Yellow is structurally inevitable when `replicas=1` on 1-node cluster; this is *expected* and the fix is `replicas=0`. **Mitigation:** none — this is a true positive even though "expected." | None (ES is observable). | `PR-HF-58` (T0 day 1) |
| **HF-50** os.Setenv race | ≥5 auth errors in 15 min AND token-refresh events <20% of error count (anomalous ratio) | Auth errors present but ratio normal | 401/403 may be from token expiry rather than race. **Mitigation:** script computes refresh:error ratio. | Race only manifests at high concurrency; quiet-period diagnostic returns 0 errors → falsely UNLIKELY. **Mitigation:** run a controlled load test (50 concurrent activities) and re-run script. | `PR-HF-50` (T0 day 2) |
| **HF-27/51/53** DTE worker contract | ≥1 DTE pod with `lastState.exitCode == 1` (matches os.Exit(1) signature) | High restartCount with unclear cause | exitCode=1 can be other panics, not specifically os.Exit. **Mitigation:** correlate with pod log grep for `panic:` or `os.Exit`. | Bug fires during specific failure modes; quiet pods show none. **Mitigation:** widen `TIME_WINDOW_MIN`; check 24h restart count. | `PR-HF-27`+`PR-HF-51`+`PR-HF-53` bundle (T0 day 3–5) |
| **HF-07** Dual backend drift | Live `helm get values` shows BOTH cassandra AND postgres driver references | Live release uses one driver but the other is in `temporal-values.yaml` on disk (armed-bomb risk) | If both files are dead-code-shadowed (only one read), drift is harmless. **Mitigation:** script checks LIVE release values, not just files. | None for live state. | `PR-HF-07` (T0 day 2) |
| **HF-10** KEDA gRPC fail | ≥1 HPA `ScalingActive=False` AND ≥1 KEDA log error mentioning Temporal in last 15 min | One signal but not both | Transient gRPC failures (network glitch) not structural. **Mitigation:** script requires error word patterns `(refused|timeout|unavailable)` not just any `error`. | KEDA failures bursty; diagnostic window misses them. **Mitigation:** widen window; check HPA `LastScaleTime > 30m` as alternative. | `PR-HF-10` (T1 day 6) |

---

## Sample interpretation walkthrough

Imagine the script outputs:

```
HF            Verdict                    Evidence
----          -------                    --------
HF-54         CONFIRMED                  File missing AND gossip state degraded: YES (UN=2 / total=3)
HF-01         CONFIRMED                  3/4 pods missing startupProbe AND 2 pods recently Killed
HF-03         LIKELY                     3 workloads at replica=1; no recent evictions
HF-02         LIKELY                     0 PDBs in namespace temporal
HF-56         CONFIRMED                  Peak utilization 95% of max_connections=20
HF-58         CONFIRMED                  ES status=yellow with 5 unassigned shards on 1 node(s)
HF-50         UNLIKELY                   0 auth errors in last 15min
HF-27         UNLIKELY                   DTE pods stable (no recent restarts)
HF-07         UNLIKELY                   Live release uses only cassandra driver
HF-10         INCONCLUSIVE               No ScaledObject in temporal

CONFIRMED: 4    LIKELY: 2

Action: ship the CONFIRMED items first
```

**How to read this:**

1. **HF-54 + HF-01 + HF-56 + HF-58 are the active root causes today.** Together they explain: Cassandra gossip thrash → Temporal pod restart → kubelet-kills-during-startup → Postgres connection-pool exhaustion → Temporal RPC timeouts → workflow failures + permanent-yellow ES masking everything. **All four can ship in week 1, ~60 lines of code change.**
2. **HF-03 + HF-02 (replica=1, no PDB) are LIKELY but dormant.** They will become CONFIRMED on the next node drain. Ship in T0 day 3 alongside HF-01 (the three are a bundle — none works without the others).
3. **HF-50, HF-27, HF-07 are UNLIKELY today.** They may be active under different load patterns. Re-run the script during peak hours and after a cluster event before deciding.
4. **HF-10 is INCONCLUSIVE.** Either KEDA isn't installed, or the namespace is wrong. Set `KEDA_NAMESPACE=` and re-run, or skip if you don't use KEDA scaling.

---

## When to re-run

- **Immediately after a crash incident** — captures evidence while it's fresh
- **During peak traffic hours** — discriminates load-dependent items (HF-50, HF-56, HF-10)
- **Within 1 hour of a deploy** — catches HF-07 drift, HF-54 silent hook failures
- **Weekly as a routine health check** — establishes a trend baseline so a regression jumps out

---

## What this diagnostic does NOT cover

- Application-level Temporal logic (workflow code bugs in user code)
- Network-layer issues outside the cluster (DNS, BGP, peering)
- Storage-layer failures (EBS volume issues, CSI driver bugs)
- Memory leaks (need `kubectl top pod` time series, not a snapshot)
- Anything in `kitt-runbooks/`, `scraper/`, `iam-sidecar/`, `asi/`, `forgeapp-controller/` (those are parent-S-plan territory)
- HF-04 (CPU CFS throttling) — needs `kubectl top` or Prometheus rate query, not in this script
- Any of HF-46/47/49 (strategic refactors — months away from runtime evidence)

For these, see `06_TESTING_STRATEGY.md` (chaos drills) and the parent `07_STABILITY_PLAN.md` (S-series).

---

## False-positive / false-negative table — full set

| HF | False-POS risk | Mitigation in script | False-NEG risk | Mitigation in script |
|---|---|---|---|---|
| HF-54 | None (file existence is binary) | n/a | Postsync silent failures invisible in `helm history` | Direct file-missing check bypasses helm-history dependency |
| HF-01 | OOM ≠ probe-fail | `lastReason` includes both `Killed` and `OOMKilled` separately so caller can disambiguate | Quiet period misses startup window | Widen `TIME_WINDOW_MIN` env (default 15 min) |
| HF-03 | replica=1 ≠ outage if no drain happened | Cross-check with `Evicted` events for CONFIRMED escalation | Single replica starves under load before crash | Recommend re-run at peak hours |
| HF-02 | PDB absence ≠ outage if no drain happened | Cross-check with `DrainNode` events | None | n/a |
| HF-56 | Long idle-in-transaction inflates count | Filter `state IN ('active','idle in transaction')` only | Bursts miss snapshot | 5 samples × 5 sec captures most short bursts |
| HF-58 | Yellow expected if `replicas=1` on 1 node | This *is* the expected state and *is* the bug — true positive even though "expected" | None (ES is observable) | n/a |
| HF-50 | Token-expiry 401s look like race | Compute refresh:error ratio | Race needs concurrency to fire | Recommend load test in interpretation guide |
| HF-27/51/53 | exitCode=1 from other panics | Caveat in evidence; recommend log grep for `panic:` | Bug fires during specific failure modes | Widen `TIME_WINDOW_MIN`; check 24h restart count |
| HF-07 | Files exist but only one is read | Live `helm get values` gives the *active* config | None for live state | n/a |
| HF-10 | Transient gRPC errors | Pattern-match `(refused\|timeout\|unavailable)` keywords only | Bursty failures miss snapshot | Widen window; check HPA `LastScaleTime` |

---

## Output formats

- **Default (TTY):** colored table + summary
- **`JSON=1`:** machine-readable JSON array of `{hf, verdict, evidence, false_positive_caveat}` for piping to a webhook/dashboard
- **`VERBOSE=1`:** prepends `[debug]` lines showing label discovery and intermediate values

---

## Safety guarantees

- ✅ **Read-only** — no `kubectl apply`, no `kubectl delete`, no `helm upgrade`, no `psql -c "INSERT/UPDATE/DELETE"`
- ✅ **Bounded execution** — every kubectl/curl/psql call has implicit ≤30s timeout via kubectl defaults; explicit 5s sleeps only between Postgres samples
- ✅ **No assumed pod names** — discovers labels at runtime from at least 3 candidate label keys
- ✅ **No assumed credentials** — uses in-pod `psql` and `curl` over localhost; no external auth
- ✅ **`set -euo pipefail`** — fails loudly on any unexpected error rather than silently mis-reporting
- ✅ **Exits 3 on diagnostic failure** rather than reporting false negatives

---

## How to disprove this diagnostic itself (meta-critical-thinking)

If you suspect this script is wrong:
1. Run with `VERBOSE=1` to see label-discovery and intermediate values
2. Cross-check each CONFIRMED verdict by hand using the commands listed in the per-HF interpretation matrix above
3. Run with `HF=HF-XX` to isolate one finding at a time and inspect the sub-output
4. The script's own evidence strings cite the exact metric values used; if they disagree with `kubectl get …` or `psql -c …` run by hand, file an issue and we'll fix the script logic

---

## Roadmap (script v2)

- Add HF-04 (CPU CFS throttling) using `kubectl top pod --containers` time-series sampling
- Add HF-23 (gRPC plaintext) using `kubectl get netpol -o yaml` and live cert-chain inspection
- Add HF-39 (Cilium policies) — already downgraded to MED in Appendix E; lower priority
- Add Prometheus-based variants for clusters with `kube-prometheus-stack` so we can use 24h windows instead of 15-min
- Add `--watch` mode that re-runs every 60s and emits a transition log (CONFIRMED→UNLIKELY transitions are the most informative signal)
