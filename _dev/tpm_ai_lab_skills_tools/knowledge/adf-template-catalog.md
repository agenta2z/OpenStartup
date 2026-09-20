# ADF Template Catalog for TPM Artifacts

Reference catalog of Atlassian Document Format (ADF) template structures for the 8 TPM artifact
types. Each template defines the page structure, ADF node patterns, and placeholder conventions.
Templates are used by the `confluence-program-docs` skill for page creation workflows.

Related skills: `confluence-program-docs`, `jira-program-ops`

---

## General ADF Conventions

### Root Structure
Every ADF document must have this root:
```json
{
  "version": 1,
  "type": "doc",
  "content": [ /* block nodes */ ]
}
```

### Placeholder Conventions
- `<Program Name>` — Replace with actual program name
- `[Add Name]` — Human-fillable placeholder
- `<date>` — Replace with `date` inline node (timestamp in ms)
- Status lozenges default to `neutral` until populated with real data
- `taskItem` nodes default to `state: "TODO"`

### Status Lozenge Colors
| Meaning | Color Value | Example Text |
|---------|------------|-------------|
| On Track / Low / Healthy | `green` | "On Track", "Low", "Healthy" |
| At Risk / Medium / Watch | `yellow` | "At Risk", "Medium", "Watch" |
| Off Track / High / Critical | `red` | "Off Track", "High", "Critical" |
| Not Started / Pending | `neutral` | "Not Started", "Pending" |
| In Review / In Progress | `blue` | "In Review", "In Progress" |
| Deferred / Parked | `purple` | "Deferred", "Parked" |

### Common ADF Node Snippets

**Status lozenge inline node:**
```json
{"type": "status", "attrs": {"text": "On Track", "color": "green", "style": "bold"}}
```

**Mention inline node:**
```json
{"type": "mention", "attrs": {"id": "<account_id>", "text": "@Display Name", "accessLevel": "CONTAINER"}}
```

**Date inline node:**
```json
{"type": "date", "attrs": {"timestamp": "1714200000000"}}
```

**InlineCard (smart link) node:**
```json
{"type": "inlineCard", "attrs": {"url": "https://site.atlassian.net/browse/PROJ-123"}}
```

---

## Template 1: Program Charter

### Sections
1. Program Identity & Overview (heading + info panel)
2. Background & Problem Statement (heading + paragraph)
3. Objectives, Goals & Success Metrics (heading + table)
4. Scope & Non-Goals (heading + two bullet lists)
5. Governance Model & DACI (heading + table)
6. Stakeholder Summary (heading + table)
7. Initial RAID (heading + table with status lozenges)
8. Timeline & Key Milestones (heading + table with date nodes)
9. Communication Plan (heading + table)
10. Appendix (expand section)

### ADF Structure Skeleton
```json
{
  "version": 1,
  "type": "doc",
  "content": [
    {"type": "heading", "attrs": {"level": 1}, "content": [{"type": "text", "text": "Program Charter — <Program Name>"}]},
    {"type": "panel", "attrs": {"panelType": "info"}, "content": [
      {"type": "paragraph", "content": [
        {"type": "text", "text": "Program: ", "marks": [{"type": "strong"}]},
        {"type": "text", "text": "<Program Name>"},
        {"type": "hardBreak"},
        {"type": "text", "text": "Owner: ", "marks": [{"type": "strong"}]},
        {"type": "text", "text": "[Add Program Manager]"},
        {"type": "hardBreak"},
        {"type": "text", "text": "Sponsor: ", "marks": [{"type": "strong"}]},
        {"type": "text", "text": "[Add VP/GM]"},
        {"type": "hardBreak"},
        {"type": "text", "text": "Status: ", "marks": [{"type": "strong"}]},
        {"type": "status", "attrs": {"text": "Not Started", "color": "neutral", "style": "bold"}},
        {"type": "hardBreak"},
        {"type": "text", "text": "Last Updated: ", "marks": [{"type": "strong"}]},
        {"type": "date", "attrs": {"timestamp": "<epoch_ms>"}}
      ]}
    ]},
    {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Background & Problem Statement"}]},
    {"type": "paragraph", "content": [{"type": "text", "text": "[Describe the business context, problem being solved, and why action is needed now.]"}]},
    {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Objectives, Goals & Success Metrics"}]},
    {"type": "table", "attrs": {"isNumberColumnEnabled": false, "layout": "default"}, "content": [
      {"type": "tableRow", "content": [
        {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Objective", "marks": [{"type": "strong"}]}]}]},
        {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Key Result / Metric", "marks": [{"type": "strong"}]}]}]},
        {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Target", "marks": [{"type": "strong"}]}]}]},
        {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Status", "marks": [{"type": "strong"}]}]}]}
      ]},
      {"type": "tableRow", "content": [
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Objective 1]"}]}]},
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Key result]"}]}]},
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Target value]"}]}]},
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "status", "attrs": {"text": "Not Started", "color": "neutral", "style": "bold"}}]}]}
      ]}
    ]},
    {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Scope"}]},
    {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "In Scope"}]},
    {"type": "bulletList", "content": [
      {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[In-scope item 1]"}]}]},
      {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[In-scope item 2]"}]}]}
    ]},
    {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Out of Scope"}]},
    {"type": "bulletList", "content": [
      {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Out-of-scope item 1]"}]}]}
    ]},
    {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Governance Model & DACI"}]},
    {"type": "table", "attrs": {"isNumberColumnEnabled": false, "layout": "default"}, "content": [
      {"type": "tableRow", "content": [
        {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Role", "marks": [{"type": "strong"}]}]}]},
        {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Person", "marks": [{"type": "strong"}]}]}]},
        {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Responsibility", "marks": [{"type": "strong"}]}]}]}
      ]},
      {"type": "tableRow", "content": [
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Driver (D)"}]}]},
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Add Program Manager]"}]}]},
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Day-to-day program execution"}]}]}
      ]},
      {"type": "tableRow", "content": [
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Approver (A)"}]}]},
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Add Sponsor]"}]}]},
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Final decisions on scope, budget, timeline"}]}]}
      ]}
    ]},
    {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Timeline & Key Milestones"}]},
    {"type": "table", "attrs": {"isNumberColumnEnabled": false, "layout": "default"}, "content": [
      {"type": "tableRow", "content": [
        {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Milestone", "marks": [{"type": "strong"}]}]}]},
        {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Target Date", "marks": [{"type": "strong"}]}]}]},
        {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Owner", "marks": [{"type": "strong"}]}]}]},
        {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Status", "marks": [{"type": "strong"}]}]}]}
      ]},
      {"type": "tableRow", "content": [
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Milestone 1]"}]}]},
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "date", "attrs": {"timestamp": "<epoch_ms>"}}]}]},
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Owner]"}]}]},
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "status", "attrs": {"text": "Not Started", "color": "neutral", "style": "bold"}}]}]}
      ]}
    ]}
  ]
}
```

---

## Template 2: RAID Log

### Sections
1. Header with program info and legend panel
2. Risks table (ID, Description, Severity, Likelihood, Impact, Owner, Mitigation, Status, Updated)
3. Assumptions table
4. Issues table
5. Dependencies table

### Key Design Decisions
- Single page with all four RAID categories as separate sections
- Severity uses status lozenges: red=Critical, yellow=High, blue=Medium, green=Low
- Each row has an auto-incrementing ID (R-001, A-001, I-001, D-001)
- "Status" column uses status lozenges: red=Open, yellow=Mitigating, green=Closed, blue=Monitoring

### Table Column Structure (Risks)

| Column | ADF Node | Content |
|--------|----------|---------|
| ID | text | "R-001" |
| Description | paragraph | Free text |
| Severity | status lozenge | red/yellow/blue/green |
| Likelihood | status lozenge | red=High, yellow=Medium, green=Low |
| Impact | status lozenge | red=High, yellow=Medium, green=Low |
| Owner | text or mention | Person responsible |
| Mitigation | paragraph | Action plan |
| Status | status lozenge | Open/Mitigating/Monitoring/Closed |
| Last Updated | date node | Timestamp |

---

## Template 3: Decision Log

### Sections
1. Header panel with program info
2. Decision table (ID, Date, Decision Title, Context, Options, Decision, Rationale, Owner, Status)
3. Expand sections for detailed rationale per decision

### Key Design Decisions
- Compact table for quick scanning
- Each decision row links to an expand section with full rationale
- Status uses: blue=Proposed, yellow=Under Review, green=Approved, red=Rejected, purple=Deferred
- ADR (Architecture Decision Record) style for each entry

### Table Column Structure

| Column | ADF Node | Content |
|--------|----------|---------|
| ID | text | "DEC-001" |
| Date | date node | Decision date |
| Title | text (strong) | Short decision title |
| Context | paragraph | Brief context |
| Decision | paragraph | What was decided |
| Owner | text or mention | Decision maker |
| Status | status lozenge | Proposed/Approved/Rejected/Deferred |

### Expand Pattern for Detail
After the table, include expand sections for decisions needing detailed rationale:
```json
{
  "type": "expand",
  "attrs": {"title": "DEC-001 — Detailed Rationale"},
  "content": [
    {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Context"}]},
    {"type": "paragraph", "content": [{"type": "text", "text": "[Full context description]"}]},
    {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Options Considered"}]},
    {"type": "orderedList", "content": [
      {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Option A — description, pros, cons]"}]}]},
      {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Option B — description, pros, cons]"}]}]}
    ]},
    {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Rationale"}]},
    {"type": "paragraph", "content": [{"type": "text", "text": "[Why this option was chosen]"}]}
  ]
}
```

---

## Template 4: Weekly Status Report

### Sections
1. Header with program name, week, overall RAG status
2. Status at a Glance — dimension RAG table (Scope, Schedule, Budget, Risk)
3. Key Highlights — success panel with bullet list
4. Top Risks & Issues — warning panel with severity lozenges
5. Sprint Health Summary — table with metrics
6. Dependency Status — table with blocking items
7. Data Hygiene Summary — table with counts and thresholds
8. Next Week Focus — bullet list

### Key Design Decisions
- Panels group content by sentiment: success (green) for highlights, warning (yellow) for risks
- Inline status lozenges for all RAG indicators
- Sprint metrics presented as a compact table
- Data hygiene section auto-populated from `jira-program-ops` audit results

### RAG Summary Table Structure
```json
{
  "type": "table", "attrs": {"isNumberColumnEnabled": false, "layout": "default"},
  "content": [
    {"type": "tableRow", "content": [
      {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Dimension", "marks": [{"type": "strong"}]}]}]},
      {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Status", "marks": [{"type": "strong"}]}]}]},
      {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Summary", "marks": [{"type": "strong"}]}]}]}
    ]},
    {"type": "tableRow", "content": [
      {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Scope"}]}]},
      {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "status", "attrs": {"text": "On Track", "color": "green", "style": "bold"}}]}]},
      {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Scope status narrative]"}]}]}
    ]}
  ]
}
```

---

## Template 5: Executive Summary

### Sections
1. Header with program name, overall RAG, last updated
2. One-paragraph narrative (info panel)
3. Status at a Glance — compact dimension table
4. Key Highlights — success panel, 3-5 bullets
5. Top Risks & Issues — warning panel with severity lozenges
6. Upcoming Milestones & Decisions — table with dates
7. Leadership Ask — note panel with action items

### Key Design Decisions
- Maximum one page / one screen — concise and scannable
- Panels for visual grouping: info (narrative), success (highlights), warning (risks), note (asks)
- No expand sections — everything visible at first glance
- Status lozenges on every dimension for instant RAG reading

---

## Template 6: Stakeholder Map & Communications Plan

### Sections
1. Overview panel with program meta
2. Stakeholder Matrix table (Name, Role, Influence, Interest, RACI, Engagement Strategy, Health)
3. Optional RACI Grid for key workstreams
4. Communications Plan table (Channel, Audience, Cadence, Format, Owner, Content Focus)
5. Key Stakeholder Notes — expand sections per high-influence stakeholder

### Stakeholder Matrix Columns

| Column | ADF Node | Content |
|--------|----------|---------|
| Stakeholder / Group | text | Name or group |
| Role / Function | text | Title or function |
| Influence | status lozenge | green=Low, yellow=Medium, red=High |
| Interest | status lozenge | green=Low, yellow=Medium, red=High |
| RACI Role | text | R/A/C/I |
| Engagement Strategy | paragraph | Short description |
| Engagement Health | status lozenge | green=Healthy, yellow=Watch, red=At Risk |

---

## Template 7: Gate Review Checklist

### Sections
1. Header with program name and gate model overview
2. Legend panel explaining usage
3. Gate sections (repeated 6x) each containing:
   - Gate heading and purpose description
   - Gate status and decision metadata table
   - Task checklist using `taskList`/`taskItem` nodes

### Standard 6-Gate Model

| Gate | Name | Key Checklist Items |
|------|------|-------------------|
| Gate 0 | Idea / Intake | Problem statement, initial metrics, stakeholder alignment |
| Gate 1 | Problem & Outcome Definition | Charter approved, success metrics, DACI established |
| Gate 2 | Solution / Design Readiness | Design docs reviewed, tech feasibility confirmed, dependencies mapped |
| Gate 3 | Build / Test Readiness | Development plan, test strategy, risk mitigations in place |
| Gate 4 | Launch / Go-live Readiness | Rollout plan, monitoring, rollback procedures, stakeholder sign-off |
| Gate 5 | Post-Launch Review | Metrics validated, retrospective completed, handoff to BAU |

### Gate Section ADF Pattern
```json
{
  "type": "panel", "attrs": {"panelType": "info"},
  "content": [
    {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Gate 0 — Idea / Intake"}]},
    {"type": "paragraph", "content": [
      {"type": "text", "text": "Gate Status: "},
      {"type": "status", "attrs": {"text": "Not Started", "color": "neutral", "style": "bold"}}
    ]},
    {"type": "table", "attrs": {"isNumberColumnEnabled": false, "layout": "default"}, "content": [
      {"type": "tableRow", "content": [
        {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Decision"}]}]},
        {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Date"}]}]},
        {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Approver"}]}]}
      ]},
      {"type": "tableRow", "content": [
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Pending"}]}]},
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "—"}]}]},
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[Add Approver]"}]}]}
      ]}
    ]},
    {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Checklist"}]},
    {"type": "taskList", "attrs": {"localId": ""}, "content": [
      {"type": "taskItem", "attrs": {"localId": "", "state": "TODO"}, "content": [
        {"type": "text", "text": "Problem statement drafted and agreed with sponsor"}
      ]},
      {"type": "taskItem", "attrs": {"localId": "", "state": "TODO"}, "content": [
        {"type": "text", "text": "Initial success metrics identified"}
      ]},
      {"type": "taskItem", "attrs": {"localId": "", "state": "TODO"}, "content": [
        {"type": "text", "text": "High-level scope and assumptions captured in Program Charter"}
      ]}
    ]}
  ]
}
```

---

## Template 8: Retrospective Summary

### Sections
1. Header with program/sprint name, date, facilitator
2. Timeline / Context panel (info) — what period this covers
3. What Went Well — success panel with bullet list
4. What Didn't Go Well — error panel with bullet list
5. Insights & Learnings — note panel with bullet list
6. Action Items — task list with owners and due dates
7. Metrics Snapshot — table with sprint/phase metrics

### Key Design Decisions
- Panels with distinct types create visual categorization: success (went well), error (didn't go well), note (insights)
- Action items use `taskList`/`taskItem` for trackable follow-ups
- Each action item should include owner mention and target date
- Metrics table provides objective data alongside subjective feedback

### Action Items Pattern
```json
{
  "type": "heading", "attrs": {"level": 2},
  "content": [{"type": "text", "text": "Action Items"}]
},
{
  "type": "taskList", "attrs": {"localId": ""},
  "content": [
    {"type": "taskItem", "attrs": {"localId": "", "state": "TODO"}, "content": [
      {"type": "text", "text": "Improve PR review turnaround — Owner: "},
      {"type": "mention", "attrs": {"id": "<account_id>", "text": "@Name", "accessLevel": "CONTAINER"}},
      {"type": "text", "text": " — Due: "},
      {"type": "date", "attrs": {"timestamp": "<epoch_ms>"}}
    ]}
  ]
}
```

---

## Page Hierarchy Scaffold

Standard page tree for program documentation:

```
<Program Name> — Program Home
├── <Program> — Charter
├── <Program> — RAID Log
├── <Program> — Decision Log
├── <Program> — Stakeholder Map & Comms Plan
├── <Program> — Executive Summary
├── <Program> — Gate Review Checklist
├── <Program> — Status Reports           (container page)
│   ├── Week of 2026-04-20
│   ├── Week of 2026-04-13
│   └── ...
└── <Program> — Retrospectives           (container page)
    ├── Sprint 42 Retrospective
    ├── Sprint 41 Retrospective
    └── ...
```

### Container Page Body
Container pages (Status Reports, Retrospectives) use a simple body with a children macro:
```json
{
  "version": 1,
  "type": "doc",
  "content": [
    {"type": "heading", "attrs": {"level": 1}, "content": [{"type": "text", "text": "<Program> — Status Reports"}]},
    {"type": "paragraph", "content": [{"type": "text", "text": "This page contains weekly status reports. Most recent reports appear first."}]},
    {"type": "extension", "attrs": {
      "extensionType": "com.atlassian.confluence.macro.core",
      "extensionKey": "children",
      "parameters": {
        "macroParams": {
          "sort": {"value": "creation"},
          "reverse": {"value": "true"},
          "first": {"value": "20"}
        }
      }
    }}
  ]
}
```
