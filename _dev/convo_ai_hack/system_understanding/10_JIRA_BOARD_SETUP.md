# 10 — ConvoAI Optimization Jira Board Setup

**Date:** 2026-05-19 07:38 PT
**Status:** ✅ Epic + 10 child issues created. Board setup requires UI (cannot be done via MCP).

---

## ✅ What was created via MCP API

### Epic
- **AI-236 — ConvoAI Optimization**
  https://hello.atlassian.net/browse/AI-236
  Project: AI Lab (key `AI`)
  Type: Epic
  Labels: `convoai-optimization`, `system-audit-2026-05`, `tome-data-driven`

### 10 child Features (all parented to AI-236)

| Key | Priority | Title |
|---|---|---|
| [AI-237](https://hello.atlassian.net/browse/AI-237) | P0 | OPP-08: PIR follow-through tracker (5/7 Rovo Chat PIRs still in Draft) |
| [AI-238](https://hello.atlassian.net/browse/AI-238) | P0 | OPP-09: Strangler-fig migration plan (convo-ai → PAI by June 2026) |
| [AI-239](https://hello.atlassian.net/browse/AI-239) | P1 | OPP-21 (NEW): Deep Research SLO low-traffic suppression tune |
| [AI-240](https://hello.atlassian.net/browse/AI-240) | P0 | OPP-01: Tomcat thread saturation root-cause fix |
| [AI-241](https://hello.atlassian.net/browse/AI-241) | P0 | OPP-22 (NEW): Post-incident SLO concession audit |
| [AI-242](https://hello.atlassian.net/browse/AI-242) | P1 | OPP-03: Stratus/SfxComposerTest flake stabilization |
| [AI-243](https://hello.atlassian.net/browse/AI-243) | P1 | OPP-23 (NEW): SLO catalog hygiene — link orphan detectors to capabilities |
| [AI-244](https://hello.atlassian.net/browse/AI-244) | P1 | OPP-24 (NEW): Address chronic SLO latency grind (17-day breach pattern) |
| [AI-245](https://hello.atlassian.net/browse/AI-245) | P1 | OPP-04: TenantContextRunnerImpl MDC suspend propagation fix |
| [AI-246](https://hello.atlassian.net/browse/AI-246) | P1 | OPP-25 (NEW): Service inventory hygiene in Tome |

**Verify**: `https://hello.atlassian.net/issues/?jql=project%20%3D%20AI%20AND%20labels%20%3D%20convoai-optimization%20ORDER%20BY%20created%20ASC`

---

## 📋 Why no new "Jira Board" was created

| Question | Answer |
|---|---|
| Can the MCP create a Jira project? | ❌ No — requires Jira admin |
| Can the MCP create a Jira board? | ❌ No — board CRUD is via Jira Software REST API (`/rest/agile/1.0/board`) which my available tools don't expose |
| Can the MCP create issues, link to Epics, set labels? | ✅ Yes (used successfully) |
| Can a board be created from a filter? | ✅ Yes — but requires 30 sec of UI work by a human with Software admin or "Create Boards" permission in AI Lab |

**Decision:** Per user direction (2026-05-19 07:29), proceed with the **Epic + filter-based board** path. The 30-second UI step below is well-documented.

---

## 🪜 30-second UI steps to create the board

### Step 1 — Save the filter

1. Open: **https://hello.atlassian.net/issues/?jql=project%20%3D%20AI%20AND%20labels%20%3D%20%22convoai-optimization%22%20ORDER%20BY%20Rank%20ASC**
2. Click **Save as** (top right)
3. Filter name: `ConvoAI Optimization`
4. Filter description: `All work tracked under AI-236 Epic, R3-data-driven optimizations from convo-ai system audit 2026-05`
5. Click **Submit** → note the filter ID (used in Step 2)

### Step 2 — Create the board from the filter

1. From left sidebar (in any Jira page): **Boards** dropdown → **Create board**
2. Pick **Kanban board** (recommended) or **Scrum board** (if you want sprints)
3. Select **Board from an existing saved filter**
4. Choose: `ConvoAI Optimization` (the filter you just saved)
5. Board name: `ConvoAI Optimization`
6. Location: select your user or "Gen AI Platform Team" (if exists)
7. Click **Create board**

### Step 3 — Configure columns (optional)

Default columns (To Do / In Progress / Done) work fine. If you want priority swimlanes:
1. Board → ⋯ (three dots) → **Board settings**
2. **Swimlanes** → swimlane based on: **Queries**
3. Add: `labels = "P0"`, `labels = "P1"`, `labels = "P2"`, etc.

---

## 🎯 Direct board URL (after Step 2)

After board creation, the URL will be something like:
```
https://hello.atlassian.net/jira/software/c/projects/AI/boards/{BOARD_ID}
```

Where `{BOARD_ID}` is a numeric ID auto-assigned (e.g. 12345).

---

## 📊 Useful saved JQL queries

| Purpose | JQL |
|---|---|
| All ConvoAI Opt work | `project = AI AND labels = "convoai-optimization"` |
| P0 only | `project = AI AND labels = "convoai-optimization" AND labels = "P0"` |
| New R3-findings only | `project = AI AND labels = "new-r3-finding"` |
| Blocked items | `project = AI AND labels = "convoai-optimization" AND labels = "blocked"` |
| Stale (no update in 7d) | `project = AI AND labels = "convoai-optimization" AND updated < -7d` |
| Open items (not Done) | `project = AI AND labels = "convoai-optimization" AND status != Done` |

---

## 🔁 Adding more child issues programmatically

To add more issues to the Epic via the same MCP pattern I used:

```python
# Pseudo-code for future additions
mcp.create_jira_issue(
    project_url="https://hello.atlassian.net/browse/AI",
    issue_type="Feature",  # or "Task", "Epic", "Subtask"
    parent_issue="AI-236",   # Epic Link
    summary="[Pn] OPP-NN: <title>",
    description_html="<p>...</p>",
    fields={"labels": ["convoai-optimization", "P0", "<topic-tag>"]}
)
```

**Label conventions (use consistently):**
- Priority: `P0`, `P1`, `P2`, `P3`
- Always include: `convoai-optimization` (for board filter)
- Topic tags (one or more): `tomcat`, `slo-governance`, `slo-observability`, `pir-follow-through`, `migration`, `tenant-context`, `suspend`, `flake`, `developer-velocity`, `chronic-latency`, `performance`, `strategic`
- Provenance: `tome-data-driven` (if from R3), `new-r3-finding` (newly identified)
- Status helpers: `blocked`, `parking-lot`, `done-needs-followup`

---

## 🔗 Cross-references

| Source | Where |
|---|---|
| Epic | https://hello.atlassian.net/browse/AI-236 |
| Audit docs | `/Users/tchen7/MyProjects/CoreProjects/OpenStartup/_dev/convo_ai_hack/system_understanding/` |
| R3 primary-source data | `09_LIVE_TELEMETRY_FINDINGS.md` |
| Tome API reproducible commands | `09_LIVE_TELEMETRY_FINDINGS.md` §J |
| Round-1 baseline ranking | `03_OPPORTUNITY_REPORT.md` (now superseded — see banner) |

---

## ⏰ Recommended next steps (post-board-creation)

1. **Assign DRI** for each issue (suggest ysharma as default since they're the capability owner per Tome)
2. **Add story-point estimates** during a team planning session
3. **Set up weekly cron** for PIR-tracker (OPP-08 / AI-237) — easiest win, ships in 1 week
4. **Block OPP-25 (AI-246) on OPP-09 (AI-238)** — service inventory hygiene must wait for migration plan
5. **Create components** in AI Lab if you want richer grouping (e.g. `ConvoAI-Reliability`, `ConvoAI-Migration`, `ConvoAI-SLO-Governance`)

---

**Bottom line:** Epic and all 10 child issues exist and are visible. Board can be created in 30s via the UI steps above. The work is fully data-grounded (Tome/Phobos API direct queries) and ready to start.
