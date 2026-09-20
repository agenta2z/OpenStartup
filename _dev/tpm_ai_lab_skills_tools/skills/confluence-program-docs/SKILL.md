---
name: confluence-program-docs
description: >
  Provides domain-specific workflow guidance for Technical Program Managers (TPMs) to create,
  maintain, and update program documentation in Confluence using ADF (Atlassian Document Format).
  Covers template-driven page creation for 8 TPM artifact types, page hierarchy scaffolding,
  living document maintenance via read-modify-write cycles, and cross-platform data integration
  from Jira queries into Confluence status reports.
labels:
  - tpm
  - confluence
  - adf
  - documentation
metadata:
  tools:
    - twg
    - search_confluence_using_cql
    - create_confluence_page
    - update_confluence_page
    - get_confluence_page
    - view_confluence_descendants
---

# Confluence Program Docs

## 1. Skill Overview

- **Name**: confluence-program-docs
- **Description**: Orchestrates TPM documentation workflows in Confluence — scaffolding program page hierarchies, creating artifact pages from ADF templates (Program Charter, RAID Log, Decision Log, Weekly Status Report, Executive Summary, Stakeholder Map, Gate Review Checklist, Retrospective Summary), maintaining living documents via section-aware updates, and integrating Jira data into status reports.
- **Leveraged Tools**:

| Tool | Capability Summary |
|------|-------------------|
| `twg` (TWG CLI) | Confluence page CRUD (`twg confluence pages get/create/update/delete`), CQL search (`twg confluence search query --cql`), blog posts, space management. Supports ADF body format via `--body-format adf` and `--body-file`. |
| `search_confluence_using_cql` (MCP) | CQL-based content search — find pages by space, title, label, ancestor. Complements TWG search. |
| `create_confluence_page` (MCP) | Create pages with HTML content and parent specification. Used when HTML is preferred over ADF. |
| `update_confluence_page` (MCP) | Update page content and title with version messaging. |
| `get_confluence_page` (MCP) | Retrieve page content as HTML for reading. |
| `view_confluence_descendants` (MCP) | Navigate page hierarchy — list child/descendant pages of a given page. |

## 2. Workflow Mappings

### 2.1 Workflow: Program Space Scaffolding

**Trigger**: When a new program is initialized and needs its Confluence page hierarchy created.

**Step-by-step operational pattern**:

1. **Identify or create program space** — Check if space exists:
   ```
   twg confluence spaces query --keys <SPACE_KEY> -o json
   ```
   If not found, create it:
   ```
   twg confluence spaces create --key <SPACE_KEY> --name "<Program Name>" --description "Program documentation for <Program Name>" -y
   ```

2. **Create the program home page** — This is the root page for all program artifacts:
   ```
   twg confluence pages create --space-id <space_id> --title "<Program Name> — Program Home" --body-file /tmp/program_home.json --body-format adf -y
   ```
   The home page ADF body should include:
   - Program name, owner, sponsor, and status (using `status` inline nodes)
   - Navigation table linking to all child pages
   - Quick-reference panel with key dates and milestones

3. **Create child pages** — For each of the 8 artifact types, create a child page under the home page:

   | Page Title Pattern | Template Reference |
   |---|---|
   | `<Program> — Charter` | Program Charter template |
   | `<Program> — RAID Log` | RAID Log template |
   | `<Program> — Decision Log` | Decision Log template |
   | `<Program> — Status Reports` | Container page (children are individual reports) |
   | `<Program> — Executive Summary` | Executive Summary template |
   | `<Program> — Stakeholder Map & Comms Plan` | Stakeholder Map template |
   | `<Program> — Gate Review Checklist` | Gate Review Checklist template |
   | `<Program> — Retrospectives` | Container page (children are individual retros) |

   For each page:
   ```
   twg confluence pages create --space-id <space_id> --title "<title>" --parent-id <home_page_id> --body-file /tmp/<template>.json --body-format adf -y
   ```

4. **Add labels** for cross-program navigation:
   > **Note**: TWG CLI does not have a dedicated label command. Use MCP or the TWG page update if labels are supported. Otherwise, include label references in the page body.

5. **Update home page** with links to all created child pages using `inlineCard` nodes:
   ```
   twg confluence pages update <home_page_id> --body-file /tmp/updated_home.json --body-format adf -y
   ```

**Example scenario**: TPM initializes "Project Mercury" program. AI creates space `MERCURY`, home page, and 8 child pages from templates. Home page includes smart-link navigation to each child. Total: 10 pages created in ~30 seconds.

---

### 2.2 Workflow: Weekly Status Report Generation

**Trigger**: Weekly (typically Friday) — synthesize data from Jira queries into a Confluence status report page.

**Step-by-step operational pattern**:

1. **Gather data from Jira** — Use `jira-program-ops` skill workflows:
   - Sprint health metrics (completion rate, scope creep, stall rate)
   - Top blockers and dependency status
   - Data hygiene summary
   - OKR progress metrics

2. **Construct ADF body** — Build the status report ADF using the Weekly Status Report template structure:

   ```json
   {
     "version": 1,
     "type": "doc",
     "content": [
       {
         "type": "heading",
         "attrs": {"level": 1},
         "content": [{"type": "text", "text": "Weekly Status Report — <Program> — Week of <date>"}]
       },
       {
         "type": "panel",
         "attrs": {"panelType": "info"},
         "content": [
           {
             "type": "paragraph",
             "content": [
               {"type": "text", "text": "Overall Status: ", "marks": [{"type": "strong"}]},
               {"type": "status", "attrs": {"text": "On Track", "color": "green", "style": "bold"}}
             ]
           }
         ]
       }
     ]
   }
   ```

3. **Write ADF to temp file**:
   ```bash
   # Agent writes ADF JSON to a temp file
   echo '<adf_json>' > /tmp/status_report_<date>.json
   ```

4. **Find or create the report page**:
   - Search for existing page:
     ```
     twg confluence search query --cql "ancestor = <status_reports_container_id> AND title = 'Week of <date>'" --limit 1
     ```
   - If found → update existing page
   - If not found → create new child page:
     ```
     twg confluence pages create --space-id <space_id> --title "Week of <date>" --parent-id <status_reports_container_id> --body-file /tmp/status_report_<date>.json --body-format adf -y
     ```

5. **Update the Executive Summary page** — Refresh the exec summary with latest RAG status and top risks from the new status report data.

**Example scenario**: Friday afternoon, AI gathers sprint data showing 75% completion (green), 1 critical blocker (FORGE-456), and 3 hygiene warnings. Generates ADF status report with green RAG, blocker callout in warning panel, and hygiene summary table. Creates page under "Status Reports" container.

---

### 2.3 Workflow: Living Document Update (Read-Modify-Write)

**Trigger**: When any existing Confluence page needs a section-level update (e.g., adding a new risk to the RAID log, updating a decision status).

**Autonomy**: 🟢 Autonomous for internal program docs; 🟡 Propose for executive-facing documents.

**Step-by-step operational pattern**:

1. **Read current page content**:
   ```
   twg confluence pages get <page_id> --body-format adf --full -o json
   ```
   This returns the full ADF body, version number, and metadata.

2. **Parse the ADF body** — The ADF body is a JSON document with a `content` array of block nodes. To locate a specific section:
   - Walk the `content` array looking for `heading` nodes
   - Match heading text to the target section name
   - The section content spans from the matched heading to the next heading of the same or higher level

3. **Modify the target section** — Common modification patterns:

   **Adding a row to a table** (e.g., RAID Log):
   - Find the `table` node within the target section
   - Append a new `tableRow` to the table's `content` array
   - Each cell is a `tableCell` containing paragraph/status nodes

   **Updating a status lozenge**:
   - Find the `status` node within the target paragraph
   - Update `attrs.text` and `attrs.color`

   **Appending a list item**:
   - Find the `bulletList` or `orderedList` node
   - Append a new `listItem` node

4. **Preserve extension nodes** — **Critical**: When modifying ADF, NEVER remove or alter `extension`, `bodiedExtension`, or `inlineExtension` nodes. These represent Confluence macros (Jira issue panels, roadmap embeds, etc.) and will break if modified.

5. **Write back with version management**:
   ```
   twg confluence pages update <page_id> --body-file /tmp/updated_page.json --body-format adf --version-message "Updated <section> — <timestamp>" -y
   ```

6. **Handle version conflicts** — If the write fails due to version mismatch:
   - Re-read the page to get the latest version
   - Re-apply the modification to the new content
   - Retry the write (max 3 attempts)

**Example scenario**: New risk identified during dependency scan. AI reads the RAID Log page (version 14), locates the "Risks" section table, appends a new row with ID "R-007", severity "High" (yellow status lozenge), description, owner, and mitigation plan. Writes back as version 15 with message "Added risk R-007 — API rate limiting".

---

### 2.4 Workflow: Template-Driven Page Creation

**Trigger**: When the TPM needs a new artifact page (e.g., a new retrospective, a gate review for a specific phase).

**Step-by-step operational pattern**:

1. **Select template** — Based on the artifact type, choose the corresponding ADF template from the `adf-template-catalog` knowledge block.

2. **Populate placeholders** — Replace template placeholder values:
   - `<Program Name>` → actual program name
   - `[Add Owner]` → actual owner name (use `mention` node with account ID)
   - `<date>` → actual date (use `date` inline node with timestamp)
   - `TODO` task items → retain as unchecked tasks
   - Status lozenges → set initial color (typically `neutral` or `blue`)

3. **Write ADF to temp file** and create page:
   ```
   twg confluence pages create --space-id <space_id> --title "<title>" --parent-id <parent_id> --body-file /tmp/<template>.json --body-format adf -y
   ```

4. **Verify creation** — Read back the created page to confirm:
   ```
   twg confluence pages get <new_page_id> --body-format adf -o json
   ```

---

### 2.5 Workflow: Cross-Program Search and Navigation

**Trigger**: When the TPM needs to find pages across programs or navigate the page hierarchy.

**Step-by-step operational pattern**:

1. **Search by label** — Find all RAID logs across programs:
   ```
   twg confluence search query --cql "label = 'raid-log' AND space.key in ('PROG1', 'PROG2')" --limit 20
   ```

2. **Search by title pattern**:
   ```
   twg confluence search query --cql "title ~ 'Status Report' AND ancestor = <program_home_id>" --limit 10
   ```

3. **Navigate descendants** — List all pages under a program home:
   ```
   view_confluence_descendants(page_url: "https://<site>.atlassian.net/wiki/spaces/<SPACE>/pages/<id>", max_depth: 2)
   ```

4. **Find recently updated pages**:
   ```
   twg confluence search query --cql "space = '<SPACE_KEY>' AND lastmodified >= now('-7d')" --limit 20
   ```

## 3. Domain Guidance

### 3.1 ADF Template Reference

The full ADF template catalog is maintained in the knowledge block `adf-template-catalog.md`. Summary of available templates:

| Template | Key ADF Nodes | Primary Use |
|----------|--------------|-------------|
| Program Charter | `heading`, `table`, `panel(info)`, `expand`, `status` | Program initialization |
| RAID Log | `table` with `status` lozenges, `panel(warning)` | Ongoing risk tracking |
| Decision Log | `table`, `expand` for rationale detail | Decision recording |
| Weekly Status Report | `panel(info/success/warning)`, `status`, `table` | Weekly reporting |
| Executive Summary | `panel`, `status`, `table`, `bulletList` | Exec communication |
| Stakeholder Map & Comms Plan | `table` (matrix), `expand`, `inlineCard` | Stakeholder management |
| Gate Review Checklist | `panel`, `taskList`/`taskItem`, `status`, `table` | Phase-gate reviews |
| Retrospective Summary | `panel(success/error/note)`, `taskList`, `bulletList` | Sprint/phase retros |

### 3.2 ADF Construction Rules

1. **Always use valid ADF** — Every document must have `{"version": 1, "type": "doc", "content": [...]}` as the root
2. **Never use `localId`** — Omit `localId` attributes when creating/updating; Confluence generates them
3. **Status node colors** — Only use: `neutral`, `purple`, `blue`, `red`, `yellow`, `green`
4. **Table structure** — Tables must have consistent column counts across all rows. First row can use `tableHeader` cells.
5. **Panel types** — Only use: `info`, `note`, `tip`, `warning`, `error`, `success`
6. **Mention nodes** — Require `attrs.id` (Atlassian account ID) and `attrs.accessLevel` (typically `"CONTAINER"`)
7. **Date nodes** — Require `attrs.timestamp` as milliseconds since epoch (string format)
8. **InlineCard nodes** — Use `attrs.url` for smart links to Jira issues or other Confluence pages
9. **Extension nodes** — Never modify or remove; preserve exactly as read from the source page

### 3.3 Page Hierarchy Convention

Standard program page tree structure:

```
<Program Name> — Program Home
├── <Program> — Charter
├── <Program> — RAID Log
├── <Program> — Decision Log
├── <Program> — Stakeholder Map & Comms Plan
├── <Program> — Executive Summary
├── <Program> — Gate Review Checklist
├── <Program> — Status Reports
│   ├── Week of 2026-04-20
│   ├── Week of 2026-04-13
│   └── ...
└── <Program> — Retrospectives
    ├── Sprint 42 Retrospective
    ├── Sprint 41 Retrospective
    └── ...
```

### 3.4 Label Conventions

| Label | Applied To | Purpose |
|-------|-----------|---------|
| `program-<name>` | All pages in a program | Cross-program filtering |
| `charter` | Program Charter page | Template identification |
| `raid-log` | RAID Log page | Cross-program RAID search |
| `decision-log` | Decision Log page | Decision tracking |
| `status-report` | Weekly status reports | Report discovery |
| `exec-summary` | Executive Summary | Exec-facing content flag |
| `gate-review` | Gate Review pages | Phase-gate tracking |
| `retrospective` | Retrospective pages | Retro discovery |

### 3.5 RAG Status Color Mapping

| Health | ADF Status Color | Status Text |
|--------|-----------------|-------------|
| On Track | `green` | "On Track" |
| At Risk | `yellow` | "At Risk" |
| Off Track | `red` | "Off Track" |
| Not Started | `neutral` | "Not Started" |
| Complete | `green` | "Complete" |
| Blocked | `red` | "Blocked" |
| In Review | `blue` | "In Review" |
| Deferred | `purple` | "Deferred" |

### 3.6 Terminology

| Term | Definition |
|------|-----------|
| **ADF** | Atlassian Document Format — JSON-based rich content format used by Confluence Cloud |
| **CQL** | Confluence Query Language — used to search for pages by metadata (title, space, label, ancestor) |
| **Living document** | A Confluence page that is regularly updated rather than replaced (e.g., RAID Log, Charter) |
| **Scaffolding** | The process of creating the initial page hierarchy for a new program |
| **Body format** | The content format for page bodies — `adf` (JSON) or `storage` (XHTML) |
| **Extension node** | ADF node representing a Confluence macro (Jira issue panel, roadmap embed, etc.) |
| **Smart link** | An `inlineCard` ADF node that renders a rich preview of a linked resource |

### 3.7 Cadence Patterns

| Activity | Cadence | Autonomous? |
|----------|---------|-------------|
| Weekly status report creation | Weekly (Friday) | 🟢 Yes |
| RAID Log updates (new risks from scans) | As detected | 🟢 Yes |
| Decision Log updates | As decisions are made | 🟢 Yes |
| Executive Summary refresh | Weekly or bi-weekly | 🟡 Propose (exec-facing) |
| Gate Review updates | At phase transitions | 🟡 Propose |
| Retrospective creation | End of sprint/phase | 🟢 Yes (draft), 🟡 Propose (publish) |
| Program Home page refresh | Monthly | 🟢 Yes |

## 4. Integration Metadata

### 4.1 Tools Referenced

| Tool | Operations Used |
|------|----------------|
| `twg` CLI | `confluence pages get` (with `--body-format adf`), `confluence pages create` (with `--body-file`, `--body-format adf`, `--parent-id`), `confluence pages update` (with `--body-file`, `--version-message`), `confluence pages delete`, `confluence search query --cql`, `confluence spaces query/create` |
| MCP `search_confluence_using_cql` | CQL-based page search for cross-space queries |
| MCP `create_confluence_page` | Alternative page creation with HTML content |
| MCP `update_confluence_page` | Alternative page update with HTML content |
| MCP `get_confluence_page` | Page retrieval as HTML |
| MCP `view_confluence_descendants` | Page hierarchy navigation |

### 4.2 Cross-Tool Patterns

1. **Jira Data → ADF Status Report**: Query Jira via `jira-program-ops` skill → aggregate metrics → construct ADF body with status lozenges, tables, and panels → write to Confluence via `twg confluence pages create/update`
2. **Read-Modify-Write Cycle**: `twg confluence pages get --body-format adf` → parse ADF JSON → modify target section → `twg confluence pages update --body-file`
3. **Hierarchy Navigation**: `view_confluence_descendants` (MCP) to list children → `twg confluence pages get` to read specific child → modify → update
4. **Cross-Space Discovery**: `search_confluence_using_cql` (MCP) for cross-space label-based search → `twg confluence pages get` for full content retrieval

### 4.3 Autonomy Levels

| Operation | Level | Notes |
|-----------|-------|-------|
| Read any Confluence page | 🟢 Autonomous | No restrictions |
| Create internal program pages | 🟢 Autonomous | Status reports, RAID entries, decision records |
| Update living documents (RAID, decisions) | 🟢 Autonomous | Section-level updates to program docs |
| Create/update executive-facing pages | 🟡 Propose | Draft content, human reviews before publish |
| Delete pages | 🔴 Human only | Never delete autonomously — propose archival |
| Modify page permissions | 🔴 Human only | Not available via current tools |
| Publish retrospective summaries | 🟡 Propose | Draft is autonomous, publish needs confirmation |

## 5. Guardrails and Escalation

### 5.1 Safety Boundaries

- **NEVER** delete Confluence pages autonomously — propose archival instead
- **NEVER** modify or remove `extension`, `bodiedExtension`, or `inlineExtension` ADF nodes during updates
- **NEVER** replace an entire page body when only a section update is needed — always use section-aware modification
- **NEVER** publish executive-facing content without human review
- **NEVER** generate `storage` format (XHTML) bodies — always use ADF
- **NEVER** include `localId` attributes in ADF nodes when creating/updating — let Confluence generate them
- **ALWAYS** include a `--version-message` when updating pages to maintain change audit trail
- **ALWAYS** read the current page version before writing updates (optimistic concurrency)
- **ALWAYS** write ADF to a temp file before passing to `--body-file` (TWG CLI requirement)

### 5.2 Escalation Triggers

| Condition | Action |
|-----------|--------|
| Version conflict on page update (3 retries exhausted) | Escalate to human — possible concurrent editing |
| Page not found when expected to exist | Search by title, report to human if truly missing |
| Executive summary shows Red RAG status | Flag for human review before auto-refresh |
| RAID log has > 10 Critical/High risks | Flag for program sponsor attention |
| Gate review checklist has blocking items | Notify gate review approver |

### 5.3 Error Handling

| Error | Recovery Action |
|-------|----------------|
| Version conflict (409) | Re-read page → re-apply changes → retry (max 3 attempts) |
| Page not found (404) | Search by title in target space → create if truly missing |
| Space not found | Verify space key format, search available spaces |
| ADF validation error | Check for common issues: missing `version`/`type`, invalid node types, inconsistent table column counts |
| Body too large for inline | Always use `--body-file` for ADF content (no size limit) |
| CQL syntax error | Verify quote escaping, check field names against CQL reference |
| Authentication failure | Verify TWG_TOKEN / TWG_SITE environment variables |
| Rate limiting | Exponential backoff: 1s → 2s → 4s, max 3 retries |
