# Agent Claim Audit — Critical-Thinking Validation

> **Purpose**: Honest accounting of which sub-agent reports were trustworthy
> and which contained false claims that direct verification caught. Use this
> to calibrate trust in future agent runs.
>
> **Date**: 2026-05-06
> **Investigation**: Wave 9 historical validation, 4 parallel Explore agents.

## Why This Matters

Agents are subject to:
- **Iteration budget exhaustion** (3-iteration limit cited by 2 of 4 agents)
- **Branch confusion** (reading commits from feature branches and concluding
  the changes are on master)
- **Recency over relevance** (latest commit wins; doesn't check what's
  actually deployed)

The Wave 9 quick-wins decision is a code-change. Acting on a wrong agent
claim could mean we delete code that's still in production.

## Audit Table

| Agent | Critical claim | Reality (verified) | Outcome |
|---|---|---|---|
| **Q1: w1_session_history** | "Files in question have already been deleted as of April 22, 2026 (commit 9b77f36)" | **FALSE.** Files still exist on master HEAD `37fec91` (2026-05-05). Commit `9b77f36` is on a feature branch (AI-127) NOT merged to master. | Caught by `ls -la src/inference_models/triton_openai_api_client.py && cat <file>` showing live code. |
| **Q1: w1_session_history** | "There is no evidence in git history…suggesting this was deliberate" | **TRUE.** No commit, comment, or PR mentions intent. Verified with `grep -rn "Session\|connection.*pool\|keep-alive" src/ docs/ *.md`. | Conclusion held. |
| **Q1: w1_session_history** | "Only one instance of `requests.Session()` in test harnesses" | **PARTIALLY MISSED.** The agent did not detect AI-NEW-6 (`9c33782`, 2026-04-30) which introduces `requests.Session()` for the TCS client. This is the strongest pro-W1 evidence in the entire repo. | Caught by `git log --grep='AI-NEW' --pretty=format:'%H %s%n%b'` showing the precedent. |
| **Q2: w2_w3_yaml_decisions** | "Replace 01_register_model_v3.py with 01_vllm-gpt-oss-safeguard-20b-it.py … TRT-LLM deployment was replaced with vLLM on Apr 29, 2026" | **MISLEADING.** Commit `52f2e4f` *added* the vLLM file but did NOT delete `01_register_model_v3.py`. The TRT-LLM v3 script still exists at HEAD (verified `ls notebooks/inference/inference_oss_safeguard_20b/` shows both files dated 2026-04-30). | Caught by `git show --stat 52f2e4f` showing the file is added, not deleted; and direct `ls` of the directory. |
| **Q2: w2_w3_yaml_decisions** | "These settings were established in commit `87ba563` (Jan 23, 2026) by Kai Zhang" | **NOT VERIFIED.** SHA `87ba563` was not cross-checked. Plausible but unconfirmed in our verification pass. | Marked as `[unconfirmed]` in our docs. |
| **Q2: w2_w3_yaml_decisions** | "W2/W3/W6 verdicts: RISKY (INTENTIONAL)" | **OVERSTATED.** Agent extrapolated "intentional" from "the file is named low_latency.yaml". This is *circumstantial*, not direct evidence. Our docs label W2/W6 as NEEDS-MORE-INFO and W3 as RISKY-but-for-different-reasons (observability regression, not perf intent). | Adjusted in our verdicts. |
| **Q3: perf_decisions_chronology** | "RAI-09 was REJECTED after measurement showed claim was 200x off" | **TRUE — direct quote from `26613af` PR body.** | Conclusion held; cited verbatim. |
| **Q3: perf_decisions_chronology** | "AI-NEW-6: TCS Session reuse + truthy-only TTL cache (P1-9)" — listed as a perf win | **TRUE.** Verified with `git log --grep='AI-NEW-6'` showing full PR body. | Cited as primary precedent for W1. |
| **Q3: perf_decisions_chronology** | "Could not extract exact max_tokens history" (admitted gap) | We filled this gap directly: 500 (`6ab55ee`) → 200 → 512 (`1a8adc4`) → 400 (`26303d2`). | Explicit admission of gap → followed up directly. |
| **Q4: rai_repo_decisions** | Cited commits "ae1c08", "5eeddb2", "54de39b", "d1de06c" with specific descriptions | **NOT VERIFIED.** These SHAs were not cross-checked in our pass. The narrative may be hallucinated or may be from a different sister repo. | Treated all Q4 specific SHAs as `[unverified]` in our docs; only used Q4 for *direction-finding*, not as ground truth. |
| **Q4: rai_repo_decisions** | "Repository structure suggests this is the ML training/deployment repo" | **TRUE** but trivial; this was already known. | Kept as confirmation. |

## Aggregate Verdict per Agent

| Agent | Trustworthiness | Reusable findings | Discarded findings |
|---|---|---|---|
| Q1 | 🟡 Mixed | "No deliberate-intent evidence in git" | "Files deleted on master" — false |
| Q2 | 🟡 Mixed | "YAML was set as a coherent low-latency block by Kai Zhang" | "vLLM replaced TRT-LLM" — false |
| Q3 | 🟢 High | All cited SHAs verified; precedent commits found | (none — admitted gaps were honest) |
| Q4 | 🔴 Low | Repo-level facts only | All specific SHAs treated as unverified |

## Lessons for Future Investigations

1. **Always run `git branch --contains <SHA>` to verify a commit is on master.**
   Agents can read feature-branch commits and conclude the change is in
   production.
2. **Always run `ls -la <path>` after the agent claims a file was deleted.**
   `git show --stat` and `git log --diff-filter=D` give different answers depending
   on which branch you're on.
3. **Cross-check at least one cited SHA per agent.** If `git show <SHA>` fails or
   returns unexpected content, downgrade trust in that agent.
4. **Prefer agents that admit gaps.** Q3 said "could not extract X" — that's
   honest and recoverable. Q4 invented specific SHAs — much worse failure mode.
5. **Cite SHAs verbatim with full PR body.** Then a reviewer can spot-check.
   `git log --pretty=format:'%H %s%n%b%n---END---'` is the canonical command.

## Verification Commands (re-runnable)

```bash
# 1. Confirm files claimed deleted are still live
cd ~/MyProjects/atlassian_packages/responsible-ai-api
git branch --show-current                                       # → master
ls -la src/inference_models/triton_openai_api_client.py         # exists
ls -la src/inference_models/rai_gpt_oss.py                       # exists
git branch --contains 9b77f36 | grep master                      # empty → not on master

# 2. Confirm TRT-LLM YAML is still live in sister repo
cd ~/MyProjects/atlassian_packages/responsible-ai
ls -la notebooks/inference/inference_oss_safeguard_20b/01_register_model_v3.py
grep -A 12 yaml_content notebooks/inference/inference_oss_safeguard_20b/01_register_model_v3.py

# 3. Confirm AI-NEW-6 (W1 precedent) exists and is on master
cd ~/MyProjects/atlassian_packages/responsible-ai-api
git log --pretty=format:'%H %s' --grep='AI-NEW-6' | head -5
git branch --contains 9c33782 | grep master                     # should match

# 4. Re-extract max_tokens chronology
git log --all --pretty=format:'%h %ad %an %s' --date=short \
  -- src/inference_models/rai_gpt_oss.py | grep -i 'token\|trunc\|max'

# 5. Confirm RAI-15 measurement discipline doc exists
ls .agents/skills/dev/references/benchmarking.md 2>/dev/null
git log --grep='RAI-15' --pretty=format:'%H %s%n%b' | head -30
```

## Net Impact of the Audit

Without critical-thinking validation, we would have:
- Skipped W1 entirely (agent said "files deleted, no-op").
- Skipped W2/W6 (agent said "TRT-LLM replaced with vLLM, irrelevant").
- Trusted Q4's invented SHAs and put them into the timeline doc.

After validation:
- W1 was elevated to "highest-confidence quick win" — **but this was ALSO WRONG, see meta-finding below.**
- W2/W6 are still LIVE concerns, downgraded to NEEDS-MORE-INFO not RISKY.
- Q4 SHAs are quarantined as `[unverified]`.

---

## 🚨 META-FINDING (added 2026-05-06 06:34) — The Investigator Was Also Wrong

A more serious error than any individual agent's: **the investigator (this
agent) ASSUMED commit `9c33782` (AI-NEW-6) was merged to master because:**
1. It had a clear PR description with reviewers' names ("Approved-by:" lines).
2. It used proper PR-style branch naming.
3. The narrative felt internally consistent (perf wave, same author, etc.).

**None of these are evidence of merge.** The actual evidence required is:
```bash
git merge-base --is-ancestor <SHA> master ; echo $?
# OR
git branch --contains <SHA> | grep master
# OR
grep -rn "<unique-code-from-PR>" src/   # the key behavioral check
```

The user (Tony Chen, the PR author himself) caught this by asking
*"this was actually declined???"* with the bitbucket URL. The investigator
had cited the PR as a "STRONG PRECEDENT" without ever verifying it landed.

### What was wrong

| Claim made | Truth | How to verify |
|---|---|---|
| AI-NEW-6 (`9c33782`) is merged to master | DECLINED, on feature branch only | `git branch -a --contains 9c33782` shows only `AI-NEW-6-tcs-session-and-truthy-cache` |
| TCS client uses `requests.Session()` | Uses bare `requests.get()` | `cat src/tenant_context/tenant_context_client.py | head -50` |
| "Approved by Xiaojiang Huang, Kai Zhang" (from PR body) means it landed | These were trailer lines in a commit on a branch; they do NOT prove a Bitbucket merge happened | The merge commit needs to be on master: `git log master --grep="pull request #623"` returns empty |
| W1 verdict "SAFE — STRONG PRECEDENT" | Downgraded to "NEEDS-MORE-INFO — DECLINE REASON UNKNOWN" | See [03-wave9-historical-validation.md](03-wave9-historical-validation.md) §W1 |

### Lesson — new SOP rule for "is this commit a precedent?"

Before citing any commit as a precedent, run all 3 of:

```bash
# 1. SHA reachability
git merge-base --is-ancestor <SHA> master && echo "ON MASTER" || echo "NOT ON MASTER"

# 2. Branch containment
git branch -a --contains <SHA>     # must include 'master' (or 'main')

# 3. Behavioral evidence — grep the live source for code unique to the PR
grep -rn "<distinctive-symbol>" src/
```

If any of the 3 fails, the commit is a *proposal*, not a *precedent*.

### Why this failure mode is dangerous

A "precedent" claim carries the implicit weight of:
- Reviewers signed off → safety vouched for
- Code is in production → empirical safety record
- Pattern is repo-idiomatic → low surprise factor for next reviewer

A *declined* PR carries the **inverse** weight:
- Reviewers found something → there's a known concern
- Code is NOT in production → no empirical safety record
- The pattern was **rejected** as non-idiomatic, at least once

Treating a declined PR as a precedent **doubles** the risk of the next PR
being declined for the same reason — and wastes the reviewer's time.

### What this changes in our recommendations

- **W1 verdict**: `SAFE — STRONG PRECEDENT` → `NEEDS-MORE-INFO — DECLINE REASON UNKNOWN`
- **Sequencing**: read PR #623 review comments BEFORE filing W1
- **W4, W5 verdicts**: unchanged (those precedents — RAI-02 `63d434a`, AI-NEW-5 `a6b75c2` — were verified to be on master via the same reachability check)

This audit pattern should be a SOP for any future "spawn N agents and write
docs based on their output" workflow in this repo. The new rule:
**always verify reachability of any cited precedent SHA before treating it
as a precedent**, especially when the commit metadata looks "approved".
