# Dependency Lead Time Reference

This knowledge block provides reference material for computing and interpreting dependency lead time
metrics in an AI TPM context, using Jira issue links and transition data.

## 1. Lead Time Definition

### Advanced Roadmaps Definition (Canonical)
Lead time between dependent issues is defined as:

> The number of calendar days between the **end time of the blocking issue** and the **start time of the blocked issue**.

**Formula:**
```
leadTimeDays = start(blockedIssue) - end(blockingIssue)
```

**Interpretation:**
- **Positive lead time** (e.g., +5 days): Blocking work finished 5 days before blocked work started. On-track.
- **Zero lead time**: Blocking work finished on the same day blocked work started. Tight but acceptable.
- **Negative lead time** (e.g., -3 days): Blocked work started 3 days before the blocker was resolved. **Conflict/risk.**

### Lead Time Tolerance
Some systems (including Advanced Roadmaps) apply a tolerance of -1 day, meaning a dependency with lead time
of -1 days is still visualized as "OK" (grey line, not red). This accounts for same-day handoffs and timezone
differences.

For TPM reporting, recommend:
- Default tolerance: **0 days** (strict)
- Configurable tolerance: Allow teams to set -1 or -2 days if their workflow supports overlap

---

## 2. Date Source Strategy

### Priority Order for Date Resolution
When computing lead time, dates should be sourced in this priority order:

| Priority | Source | Field | Notes |
|----------|--------|-------|-------|
| 1 | Advanced Roadmaps schedule | Target Start / Target End | Most accurate for planned work |
| 2 | Status transitions (changelog) | First "In Progress" / "Done" timestamps | Reflects actual execution |
| 3 | System fields | `created`, `resolutiondate`, `updated` | Fallback when above unavailable |

### Date Resolution Logic

**For the blocking issue (end date):**
1. Check for explicit "End date" or "Target end" custom field
2. If absent, check `resolutiondate` system field
3. If absent, find last transition to `Done` status category in changelog
4. If absent, use `updated` timestamp (least reliable)

**For the blocked issue (start date):**
1. Check for explicit "Start date" or "Target start" custom field
2. If absent, find first transition to `In Progress` status category in changelog
3. If absent, use `created` date (proxy for when work was identified)

### Configuration Options
The skill should support configurable date strategies:
- `plans_schedule` — Use Advanced Roadmaps fields exclusively
- `workflow_transitions` — Use changelog status transitions
- `hybrid` — Prefer schedule fields, fall back to transitions (recommended default)

---

## 3. Issue Link Type Semantics

### Standard Dependency Link Types

| Link Type Name | Outward Description | Inward Description | Dependency Semantics |
|---------------|--------------------|--------------------|---------------------|
| Blocks | "blocks" | "is blocked by" | Standard blocking dependency |
| Depends | "depends on" | "is depended on by" | Functional dependency |

### Direction Normalization
When processing issue links from Jira REST API:

```json
{
  "issuelinks": [
    {
      "type": {
        "name": "Blocks",
        "inward": "is blocked by",
        "outward": "blocks"
      },
      "outwardIssue": {
        "key": "PROJ-456"
      }
    }
  ]
}
```

If the current issue has an `outwardIssue` with type "Blocks":
- **Current issue BLOCKS PROJ-456**
- Current issue = blocker, PROJ-456 = blocked

If the current issue has an `inwardIssue` with type "Blocks":
- **Current issue IS BLOCKED BY the inward issue**
- Inward issue = blocker, current issue = blocked

### Normalization Algorithm
```
For each issuelink in issue.issuelinks:
  if link has outwardIssue:
    if link.type.outward in ["blocks", "depends on"]:
      pair = (blocker=currentIssue, blocked=outwardIssue)
    else:
      pair = (blocker=outwardIssue, blocked=currentIssue)
  elif link has inwardIssue:
    if link.type.inward in ["is blocked by", "is depended on by"]:
      pair = (blocker=inwardIssue, blocked=currentIssue)
    else:
      pair = (blocker=currentIssue, blocked=inwardIssue)
```

---

## 4. Aggregate Metrics

### Recommended Metrics for TPM Dashboards

| Metric | Computation | Use Case |
|--------|-------------|----------|
| **Average Lead Time** | Mean of all leadTimeDays values | Overall program velocity indicator |
| **Median (P50)** | 50th percentile | Less skewed than average; primary health metric |
| **P90** | 90th percentile | Worst-case planning indicator |
| **At-Risk Count** | Count where leadTimeDays < tolerance | Immediate action items |
| **At-Risk Percentage** | At-risk / total * 100 | Program risk indicator |
| **Date-Incomplete Count** | Count where dates couldn't be resolved | Data quality indicator |
| **Resolution Velocity** | For resolved deps: (resolutionDate - created) in days | How fast deps get unblocked |

### Grouping Dimensions
Metrics should be computable grouped by:
- **Team** — Which team's dependencies are slowest?
- **Project/Program** — Which programs have the most dependency risk?
- **Link Type** — Are "Blocks" dependencies faster than "Depends" dependencies?
- **Time Period** — Monthly/quarterly trends
- **Component** (via Compass) — Which services have the most dependency overhead?

---

## 5. Health Thresholds

### Lead Time Health Bands
| Health | P50 Lead Time | P90 Lead Time | At-Risk % | Date-Incomplete % |
|--------|--------------|--------------|-----------|-------------------|
| **Healthy** | >= 2 days | >= 5 days | < 10% | < 5% |
| **Warning** | 0-2 days | 2-5 days | 10-25% | 5-15% |
| **Critical** | < 0 days | < 2 days | > 25% | > 15% |

### When to Escalate
- **P50 negative**: More than half of dependencies have conflicts → program-level intervention needed
- **P90 > 10 days**: Long tail of slow dependencies → investigate specific blockers
- **At-risk > 25%**: Systemic issue → review dependency management process with all teams
- **Date-incomplete > 15%**: Poor data hygiene → enforce date field requirements in Jira workflow

---

## 6. Edge Cases and Caveats

### Known Issues
1. **Same-day resolution**: Dependencies resolved on the same day they're created may show 0-day lead time,
   which is correct but can skew P50 downward. Consider filtering these for trend analysis.

2. **Timezone effects**: Start/end dates without times are treated as start-of-day in the Jira instance
   timezone. Cross-timezone teams may see apparent -1 day lead times that are actually 0.

3. **Re-opened issues**: If a blocking issue is resolved, then re-opened, the `resolutiondate` resets.
   For accuracy, use the **last** resolution date, not the first.

4. **Missing resolution date**: Some workflows don't set resolution on Done transitions. Check for
   `resolutiondate IS EMPTY AND status = Done` and use status change date from changelog instead.

5. **Advanced Roadmaps date bugs**: JPO-16332 and JPO-13419 document cases where lead time shows
   as "0 days" for -1 day dependencies. The AI should compute independently rather than relying
   on the Plans UI value.

6. **Bulk dependencies**: When analyzing programs with 100+ dependency pairs, use JQL pagination
   and batch processing. Avoid fetching all issues at once.

### Data Quality Checks
Before computing metrics, validate:
- [ ] All dependency pairs have both a blocker and blocked issue (no orphan links)
- [ ] At least 80% of pairs have resolvable dates
- [ ] No duplicate pairs (same blocker-blocked combination counted twice)
- [ ] Issues are from the correct time window (filter by created/updated date)

---

## 7. Related Skills and Tools
- **Skill**: `tpm-service-intelligence` — Uses this reference in Workflow 2.4 (Dependency Lead Time Tracking)
- **Tool**: `get_jira_issue` — Fetches issue details including links and changelog
- **Tool**: `search_jira_using_jql` — Queries issues with dependency link types
- **Knowledge**: `compass-twg-data-model` — For mapping dependency issues back to Compass components and owner teams
