# SOP: Rollback decision tree

**Trigger:** triage suggests a recent deploy may have caused the regression.

**Goal:** propose (never execute) a rollback IF AND ONLY IF the evidence supports it AND the rollback is safer than the alternatives.

The agent walks the human through this tree. The human makes the call.

## Decision tree

```
Q1: Did a deploy land within ±15 min of the symptom inflection point?
├─ NO  → Rollback is unlikely to help. Propose a different mitigation
│       (feature flag, scaling, traffic shift). Do NOT recommend rollback.
└─ YES → Continue to Q2

Q2: Does the deploy diff touch the affected code path?
   (Use rovodev_get_pr_links_from_issue_link → read PR description and files-changed)
├─ NO  → Coincidence likely. Recommend NOT rolling back UNTIL Q5 is checked.
│       Continue to Q3 anyway, in case files-changed is misleading.
└─ YES → Continue to Q3

Q3: Is the deploy a forward-incompatible schema or data migration?
├─ YES → ⚠️ HARD STOP. Rollback may corrupt data. Recommend feature-flag
│       disable, traffic shift, or kill switch — NEVER recommend rollback.
│       Page the data-platform on-call for advice.
└─ NO  → Continue to Q4

Q4: Is rollback to the previous version actually safe?
   (Check: previous version still runnable? config compatible? feature flags
   set up to roll back cleanly?)
├─ NO  → Recommend "fix forward" (deploy a hotfix). Do NOT recommend rollback.
└─ YES → Continue to Q5

Q5: Is the rollback faster than the fix-forward?
├─ Rollback < 5 min, fix < 30 min  → RECOMMEND ROLLBACK
├─ Rollback ≥ fix-forward time     → RECOMMEND FIX FORWARD
├─ Both < 5 min                    → RECOMMEND whichever has less unknown
│                                    (typically rollback if Q3=NO and Q4=YES)
└─ Both > 30 min                   → ⚠️ Escalate; this is bigger than just-a-deploy
```

## How the agent presents this

```
[ROLLBACK ANALYSIS]
Deploy candidate: <pr-url> at <ts> (Δ <N> min from inflection)
Q1 deploy in window: YES
Q2 touches affected path: YES (3 files in src/checkout/)
Q3 schema change: NO
Q4 rollback safe: YES (previous deploy was last week, config compatible)
Q5 ETA: rollback ~3 min, fix-forward ~25 min

RECOMMENDATION: Roll back to <prev-version>.
This is a recommendation only — IC, please confirm before triggering.
The agent will NOT execute the rollback.
```

## After human confirms rollback

The agent does NOT trigger the rollback. The human triggers it via their normal deploy tool (Spinnaker, ArgoCD, GitHub Actions). The agent:

1. Records the rollback decision in the incident channel and ticket
2. Starts a 10-minute timer; at the 10-min mark, runs the symptom verification queries from `triage-checklist.md` Q1/Q2
3. Posts: `[VERIFICATION] Rollback verified: error rate back to <baseline> for 10+ min` OR `[VERIFICATION FAILED] Symptom did not recover. Roll-forward may be needed; reconsider hypothesis.`

## Anti-patterns

- ❌ Recommending rollback solely because "the deploy was recent" (need Q2 + Q4 both YES)
- ❌ Recommending rollback when Q3 = YES (data-loss risk)
- ❌ Auto-triggering rollback (always human-gated)
- ❌ Saying "rollback is safe" without naming the previous version (be specific)
