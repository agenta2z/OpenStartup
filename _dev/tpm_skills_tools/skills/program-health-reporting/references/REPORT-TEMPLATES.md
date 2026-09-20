# Report Templates Reference

Output templates for all five reporting workflows. Includes Slack message formats and Confluence ADF structures.

## 1. Daily Digest — Slack Template

### All-Nominal (No Exceptions)
```
✅ Daily Program Pulse — <date>

All programs nominal. No exceptions detected.

_Updated <time> · <dashboard_link>_
```

### With Exceptions
```
📡 Daily Program Pulse — <date>

*Exceptions in the last 24h:*
• 🔴 *<program/stream>* — <short description>
• 🟡 *<program/stream>* — <short description>
• 🟢➡️🟡 *<program/stream>* — <state change description>

_<N> programs nominal ✅ · Updated <time> · <dashboard_link>_
```

### Formatting Rules
- Maximum 10 lines total
- One bullet per exception, sorted by severity (Red first)
- If >5 exceptions: show top 5 + "+N more — see dashboard"
- Use state-change arrows (➡️) for transitions
- Always include timestamp and link in italic context line

---

## 2. Weekly Status Report — Confluence ADF Structure

### Page Title Format
`Weekly Status: <Program> — Week of <YYYY-MM-DD>`

### ADF Section Structure

```json
{
  "version": 1,
  "type": "doc",
  "content": [
    {
      "type": "heading", "attrs": {"level": 1},
      "content": [{"type": "text", "text": "Weekly Status: <Program>"}]
    },
    {
      "type": "panel", "attrs": {"panelType": "info"},
      "content": [
        {"type": "paragraph", "content": [
          {"type": "text", "text": "Overall: "},
          {"type": "status", "attrs": {"text": "<On Track|At Risk|Off Track>", "color": "<green|yellow|red>"}},
          {"type": "text", "text": " | Last Updated: <timestamp>"}
        ]}
      ]
    },
    {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Health Dashboard"}]},
    {
      "type": "table", "attrs": {"layout": "default"},
      "content": [
        {"type": "tableRow", "content": [
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Dimension"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Status"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Trend"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Notes"}]}]}
        ]},
        {"type": "tableRow", "content": [
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Schedule"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "status", "attrs": {"text": "On Track", "color": "green"}}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "→ Stable"}]}]},
          {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "<notes>"}]}]}
        ]}
      ]
    },
    {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Key Accomplishments"}]},
    {"type": "bulletList", "content": [
      {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "<accomplishment 1>"}]}]}
    ]},
    {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Risks & Blockers"}]},
    {
      "type": "table", "attrs": {"layout": "default"},
      "content": [
        {"type": "tableRow", "content": [
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Risk"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "RAG"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Owner"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Mitigation"}]}]},
          {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "ETA"}]}]}
        ]}
      ]
    },
    {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Upcoming Milestones"}]},
    {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Dependencies"}]},
    {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Asks / Help Needed"}]},
    {
      "type": "panel", "attrs": {"panelType": "warning"},
      "content": [{"type": "paragraph", "content": [{"type": "text", "text": "<concrete asks with audience routing>"}]}]
    }
  ]
}
```

### Weekly Report — Slack Summary
```
📊 Weekly Status — <Program> (<date>)

🟢 Overall: On Track | Schedule 🟢 | Scope 🟢 | Resources 🟡

*Highlights:*
• Completed <key accomplishment>
• <N> items resolved, <M> in progress

*Risks:* 🟡 <top risk summary>

📄 Full report: <confluence_link>
```

---

## 3. Executive Briefing — Confluence ADF Structure

### Page Title Format
`Executive Briefing: <Portfolio> — <Month> <Year>`

### Section Structure
1. **Portfolio Health Dashboard** — Table: Program × Dimension RAG grid
2. **Executive Summary** — 3-5 sentence narrative
3. **Top Risks** — Top 3 risks with impact, likelihood, mitigation
4. **Strategic Alignment** — Goal progress vs quarterly targets
5. **Resource Concerns** — Cross-program resource contention
6. **Decisions Needed** — Action items for exec audience (panel with warning type)

### Formatting Rules
- Maximum 2 pages equivalent / 5 minutes reading time
- Decision-oriented, narrative-light, evidence-linked
- Use status lozenges for RAG indicators in tables
- Use warning panels for decision items
- Include trend arrows (↑ improving, → stable, ↓ declining)

---

## 4. Weekly Async Status — Slack Template

```
📊 Weekly Async Status — <Program> (<date>)

🟢 Overall: On Track | Schedule 🟢 | Scope 🟢 | Resources 🟡

*This Week:*
• <accomplishment 1>
• <accomplishment 2>
• <accomplishment 3>

*Next Week:*
• <planned item 1>
• <planned item 2>

*Risks:* 🟡 <risk summary with owner>
*Help Needed:* <ask or "None">

📄 Full details: <confluence_link>
```

### Formatting Rules
- Maximum 15 lines in Slack
- RAG badges on first line after title
- Accomplishments: 3-5 items, past tense
- Next week: 2-3 items, future tense
- Risks: single line, include owner
- Always link to Confluence for full details

---

## 5. TWG Commands for Confluence Publishing

### Create a new page
```bash
twg confluence pages create \
  --space <space-key> \
  --title "<page title>" \
  --parent-id <parent-page-id> \
  --body-adf '<adf_json>'
```

### Update an existing page
```bash
twg confluence pages update \
  --id <page-id> \
  --body-adf '<adf_json>'
```

### Search for existing report pages
```bash
twg confluence search query --cql 'space = "<space>" AND title ~ "Weekly Status" AND created >= now("-7d")'
```

### Notes
- Always check if a page for the current period exists before creating a new one
- Use `--parent-id` to organize reports under a program's status page hierarchy
- ADF JSON must be properly escaped when passed via CLI
