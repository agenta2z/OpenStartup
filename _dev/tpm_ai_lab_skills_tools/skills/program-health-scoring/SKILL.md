---
name: program-health-scoring
description: >
  Guides the AI TPM in computing program health scorecards, OKR roll-ups, and goal/project
  status assessments by orchestrating data collection from Jira, Atlas Goals, and Atlas Projects.
  Covers scorecard dimension scoring (schedule, scope, quality, risk), KR-based OKR rollup
  (equal-weighted and weighted), Atlas update narrative generation, and health trend analysis.
labels:
  - tpm
  - okr
  - program-management
  - health-scoring
metadata:
  tools: [twg, mcp__atlassian__invoke_tool, mcp__atlassian_goal__invoke_tool, mcp__atlassian_project__invoke_tool]
---

# Program Health Scoring

## 1. Skill Overview

- **Name**: `program-health-scoring`
- **Description**: Domain guidance for computing program health scorecards, OKR/KR roll-ups, Atlas goal status assessments, and generating structured update narratives. This skill orchestrates data from Jira (delivery metrics), Atlas Goals (OKR scores), and Atlas Projects (project status) to produce actionable health assessments for TPM workflows.

### Leveraged Tools

| Tool | Capability Summary |
|------|-------------------|
| `twg` | Query Jira work items, Atlas goals, Atlas projects, cross-product context, and org hierarchy via the Teamwork Graph CLI |
| `mcp__atlassian__invoke_tool` (Jira) | Get/search Jira issues via JQL, read issue details including transitions, links, comments |
| `mcp__atlassian_goal__invoke_tool` | Search/get Atlas goals, retrieve goal updates, access goal metadata (status, phase, owners) |
| `mcp__atlassian_project__invoke_tool` | Search/get Atlas projects, retrieve project updates, risks, dependencies, and project context |
| `mcp__teamwork_graph__invoke_tool` | Cross-product context queries, user activity, project activities and linked entities |

---

## 2. Workflow Mappings

### 2.1 Workflow: Compute Program Health Scorecard

**Trigger**: Weekly cadence (every Monday), on-demand request, or before a status report is due.

**Step-by-step operational pattern:**

#### Step 1 — Gather Program Scope
Identify the program's Jira projects, Atlas goals, and Atlas projects.



Or via MCP:


#### Step 2 — Collect Schedule Metrics from Jira
Query Jira for milestone and delivery status:



**Schedule Score Calculation:**


#### Step 3 — Collect Scope Metrics from Jira


**Scope Score Calculation:**


#### Step 4 — Collect Quality Metrics from Jira


**Quality Score Calculation:**


#### Step 5 — Collect Risk Metrics


**Risk Score Calculation:**


#### Step 6 — Compute Overall Health Score


#### Step 7 — Present Scorecard
Format as structured output with dimension breakdowns, trend indicators, and source attribution.

**Decision Point:** If overall status is At Risk or Off Track, generate Go-To-Green actions (see §2.3).

---

### 2.2 Workflow: OKR / KR Roll-Up Scoring

**Trigger**: When computing goal progress for Atlas updates, weekly/monthly OKR reviews.

**Step-by-step operational pattern:**

#### Step 1 — Fetch Goal and KR Structure


#### Step 2 — Score Each KR Individually

For each Key Result, determine its score on a 0.0–1.0 scale:

**KR Scoring Rules:**


**Metric-backed KRs**: If the KR has a quantitative target (e.g., "Improve latency by 20%"), compute:


**Milestone-backed KRs**: If the KR is tied to delivery milestones:


**Judgment-backed KRs**: If qualitative, use the health status mapping:


#### Step 3 — Compute Objective Score

**Default: Equal-Weighted Average (recommended)**


This is the canonical method per Atlassian's DACI on goal rollups. Only directly attached KRs/success measures roll into the score — sub-goals are NOT used for numeric rollup by default.

**Alternative: Weighted Average (when explicit weights exist)**


Use weighted mode ONLY when explicit weights/points are defined in the goal configuration. If weights are missing for some KRs, **require human confirmation** before proceeding.

#### Step 4 — Map Score to Status


#### Step 5 — Present Roll-Up Results
Include: objective name, each KR with individual score, aggregation method used, overall objective score, recommended status, and data sources.

**Decision Point:** Always require human confirmation before writing scores to Atlas.

---

### 2.3 Workflow: Generate Atlas Update Narrative

**Trigger**: After scorecard computation or OKR roll-up, before publishing an Atlas update.

**Step-by-step operational pattern:**

#### Step 1 — Gather Context
Collect from previous workflow outputs:
- Scorecard dimensions and scores
- OKR roll-up results
- Key risks and blockers
- Recent accomplishments (resolved issues, merged PRs)

{
  "apiVersion": "v2",
  "command": "work.query",
  "request": {
    "scope": "me",
    "accountId": null,
    "since": "7d",
    "pageSize": 1000,
    "first": null,
    "after": null
  },
  "data": {
    "since": "7d",
    "issues": [
      {
        "key": "CTSC-39064",
        "issueId": "12030825",
        "summary": "[EXP] [Model]-[ExperimentName]-[Date]",
        "status": "Backlog",
        "statusCategory": "To Do",
        "issueType": "Task",
        "assignee": null,
        "priority": "Minor",
        "updated": "2026-04-27T11:44:47.133Z",
        "webUrl": "https://hello.jira.atlassian.cloud/browse/CTSC-39064",
        "tags": [
          "reported",
          "created",
          "updated"
        ]
      },
      {
        "key": "CTSC-39065",
        "issueId": "12030832",
        "summary": "[EXP] RankingV3-EngagementLift-20260427",
        "status": "Backlog",
        "statusCategory": "To Do",
        "issueType": "Task",
        "assignee": null,
        "priority": "Minor",
        "updated": "2026-04-27T11:45:04.981Z",
        "webUrl": "https://hello.jira.atlassian.cloud/browse/CTSC-39065",
        "tags": [
          "reported",
          "created",
          "updated"
        ]
      },
      {
        "key": "CTSC-39066",
        "issueId": "12030833",
        "summary": "[DEPLOY] [ModelName]-v[Version]-[Environment]",
        "status": "Backlog",
        "statusCategory": "To Do",
        "issueType": "Task",
        "assignee": null,
        "priority": "Minor",
        "updated": "2026-04-27T11:45:16.409Z",
        "webUrl": "https://hello.jira.atlassian.cloud/browse/CTSC-39066",
        "tags": [
          "reported",
          "created",
          "updated"
        ]
      },
      {
        "key": "CTSC-39067",
        "issueId": "12030840",
        "summary": "[DEPLOY] ContentClassV2-v1.3-prod",
        "status": "Backlog",
        "statusCategory": "To Do",
        "issueType": "Task",
        "assignee": null,
        "priority": "Minor",
        "updated": "2026-04-27T11:45:40.901Z",
        "webUrl": "https://hello.jira.atlassian.cloud/browse/CTSC-39067",
        "tags": [
          "reported",
          "created",
          "updated"
        ]
      },
      {
        "key": "CTSC-39068",
        "issueId": "12030841",
        "summary": "[INC] [Severity] [IncidentType] - [ModelName] - [Brief Description]",
        "status": "Backlog",
        "statusCategory": "To Do",
        "issueType": "Bug",
        "assignee": null,
        "priority": "Minor",
        "updated": "2026-04-27T11:45:46.827Z",
        "webUrl": "https://hello.jira.atlassian.cloud/browse/CTSC-39068",
        "tags": [
          "reported",
          "created",
          "updated"
        ]
      },
      {
        "key": "AI-71",
        "issueId": "11651053",
        "summary": "spike on AI Employee prototype",
        "status": "Done",
        "statusCategory": "Done",
        "issueType": "Feature",
        "assignee": "Tony Chen",
        "priority": "Minor",
        "updated": "2026-04-22T22:32:47.579Z",
        "webUrl": "https://hello.jira.atlassian.cloud/browse/AI-71",
        "tags": [
          "assigned"
        ]
      },
      {
        "key": "AI-82",
        "issueId": "11801331",
        "summary": "a post install check to make sure `~/.openclaw/devices/paired.json` has full operator access `admin`, `read`, `approvals`, `write`, `pairing`.",
        "status": "Done",
        "statusCategory": "Done",
        "issueType": "Feature",
        "assignee": "Tony Chen",
        "priority": "Minor",
        "updated": "2026-04-22T22:32:46.036Z",
        "webUrl": "https://hello.jira.atlassian.cloud/browse/AI-82",
        "tags": [
          "assigned"
        ]
      },
      {
        "key": "CTSC-456",
        "issueId": "8453995",
        "summary": "Improve Trust Score for Risk Assessment: Questionnaire Completion",
        "status": "Done",
        "statusCategory": "Done",
        "issueType": "Bug",
        "assignee": "Saniya Agarwal",
        "priority": "Minor",
        "updated": "2026-04-27T11:45:07.312Z",
        "webUrl": "https://hello.jira.atlassian.cloud/browse/CTSC-456",
        "tags": [
          "updated"
        ]
      }
    ],
    "pages": [
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6753276027",
        "pageId": "6753276027",
        "title": "AI Lab Daily Standup [Recurring]",
        "status": "CURRENT",
        "createdAt": "2026-04-03T16:27:00.258Z",
        "author": "Puyang Xu",
        "space": {
          "name": "Puyang Xu",
          "key": "~712020e29814f070f74b44b8f38cd3df43a7a1"
        },
        "version": 21,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/~712020e29814f070f74b44b8f38cd3df43a7a1/pages/6753276027/AI+Lab+Daily+Standup+Recurring",
        "excerpt": " Event AI Lab Daily Standup Invitees Shusen Liu Xiaojiang Huang Tony Chen Housam Babiker Puyang Xu Taotao Li Sikder Rezwanul Huq Ke Wang Kai Zhang Synced from Google Calendar | Adjust your settings on",
        "tags": [
          "tagged"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6770510641",
        "pageId": "6770510641",
        "title": "RovoClaw - daily meeting notes",
        "status": "CURRENT",
        "createdAt": "2026-04-07T22:33:43.464Z",
        "author": "Josh Devenny",
        "space": {
          "name": "Josh Devenny",
          "key": "~jdevenny"
        },
        "version": 25,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/~jdevenny/pages/6770510641/RovoClaw+-+daily+meeting+notes",
        "excerpt": " Alpha testing Product experience working in Desktop with OpenClaw Secure version of OpenClaw running in the Cloud Quality of default agent OpenClaw maintainers This week; Focus on quality of experien",
        "tags": [
          "tagged"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6844032665",
        "pageId": "6844032665",
        "title": "Product AI Org Update",
        "status": "CURRENT",
        "createdAt": "2026-04-17T18:54:02.833Z",
        "author": "Puyang Xu",
        "space": {
          "name": "Puyang Xu",
          "key": "~712020e29814f070f74b44b8f38cd3df43a7a1"
        },
        "version": 20,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/~712020e29814f070f74b44b8f38cd3df43a7a1/pages/6844032665/Product+AI+Org+Update",
        "excerpt": " Hi Team, I have an important update to share - after two years of strong leadership at Atlassian,Damien Jose has decided to pursue an external opportunity. Damien made numerous contributions during h",
        "tags": [
          "tagged"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6863228237",
        "pageId": "6863228237",
        "title": "AI Lab Daily Standup 2026-04-21",
        "status": "CURRENT",
        "createdAt": "2026-04-21T16:23:59.371Z",
        "author": "Puyang Xu",
        "space": {
          "name": "Puyang Xu",
          "key": "~712020e29814f070f74b44b8f38cd3df43a7a1"
        },
        "version": 1,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/~712020e29814f070f74b44b8f38cd3df43a7a1/pages/6863228237/AI+Lab+Daily+Standup+2026-04-21",
        "excerpt": " Event AI Lab Daily Standup Date 4:30 PM - 4:55 PM Coordinated Universal Time Invitees Shusen Liu Xiaojiang Huang Tony Chen Housam Babiker Puyang Xu Taotao Li Sikder Rezwanul Huq Kai Zhang Synced from",
        "tags": [
          "tagged"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6871324788",
        "pageId": "6871324788",
        "title": "AI Lab Daily Standup 2026-04-22",
        "status": "CURRENT",
        "createdAt": "2026-04-22T16:23:45.972Z",
        "author": "Puyang Xu",
        "space": {
          "name": "Puyang Xu",
          "key": "~712020e29814f070f74b44b8f38cd3df43a7a1"
        },
        "version": 1,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/~712020e29814f070f74b44b8f38cd3df43a7a1/pages/6871324788/AI+Lab+Daily+Standup+2026-04-22",
        "excerpt": " Event AI Lab Daily Standup Date 4:30 PM - 4:55 PM Coordinated Universal Time Invitees Shusen Liu Xiaojiang Huang Tony Chen Housam Babiker Puyang Xu Taotao Li Sikder Rezwanul Huq Kai Zhang Synced from",
        "tags": [
          "tagged"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6878615749",
        "pageId": "6878615749",
        "title": "AI Lab Daily Standup 2026-04-23",
        "status": "CURRENT",
        "createdAt": "2026-04-23T16:24:36.535Z",
        "author": "Puyang Xu",
        "space": {
          "name": "Puyang Xu",
          "key": "~712020e29814f070f74b44b8f38cd3df43a7a1"
        },
        "version": 1,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/~712020e29814f070f74b44b8f38cd3df43a7a1/pages/6878615749/AI+Lab+Daily+Standup+2026-04-23",
        "excerpt": " Event AI Lab Daily Standup Date 4:30 PM - 4:55 PM Coordinated Universal Time Invitees Shusen Liu Xiaojiang Huang Tony Chen Housam Babiker Puyang Xu Taotao Li Sikder Rezwanul Huq Kai Zhang Synced from",
        "tags": [
          "tagged"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6883273695",
        "pageId": "6883273695",
        "title": "AI Lab Daily Standup 2026-04-24",
        "status": "CURRENT",
        "createdAt": "2026-04-24T16:24:03.669Z",
        "author": "Puyang Xu",
        "space": {
          "name": "Puyang Xu",
          "key": "~712020e29814f070f74b44b8f38cd3df43a7a1"
        },
        "version": 2,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/~712020e29814f070f74b44b8f38cd3df43a7a1/pages/6883273695/AI+Lab+Daily+Standup+2026-04-24",
        "excerpt": " Event AI Lab Daily Standup Date 4:30 PM - 4:55 PM Coordinated Universal Time Invitees Shusen Liu Xiaojiang Huang Tony Chen Housam Babiker Puyang Xu Taotao Li Sikder Rezwanul Huq Ke Wang Kai Zhang Syn",
        "tags": [
          "tagged"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6889651726",
        "pageId": "6889651726",
        "title": "AI Search Data & Exp Rollup - 2026-04-20 to 2026-04-27",
        "status": "CURRENT",
        "createdAt": "2026-04-27T05:42:10.352Z",
        "author": "sre-techops-bot",
        "space": {
          "name": "AI Search Data & Experience",
          "key": "SDE2"
        },
        "version": 2,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/SDE2/pages/6889651726/AI+Search+Data+Exp+Rollup+-+2026-04-20+to+2026-04-27",
        "excerpt": " From: To: TechOps Reporter profile: AI Search Data & Exp Rollup https://techops.prod.atl-paas.net/rollup_profiles/f6c946ba-9285-412c-bd83-d9b3aa9bdf58?report_id=bc095764-9504-432b-bd17-77d5c3587922 M",
        "tags": [
          "tagged"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6891619098",
        "pageId": "6891619098",
        "title": "AI Lab Daily Standup 2026-04-27",
        "status": "CURRENT",
        "createdAt": "2026-04-27T16:23:46.358Z",
        "author": "Puyang Xu",
        "space": {
          "name": "Puyang Xu",
          "key": "~712020e29814f070f74b44b8f38cd3df43a7a1"
        },
        "version": 1,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/~712020e29814f070f74b44b8f38cd3df43a7a1/pages/6891619098/AI+Lab+Daily+Standup+2026-04-27",
        "excerpt": " Event AI Lab Daily Standup Date 4:30 PM - 4:55 PM Coordinated Universal Time Invitees Shusen Liu Xiaojiang Huang Tony Chen Housam Babiker Puyang Xu Taotao Li Sikder Rezwanul Huq Ke Wang Kai Zhang Syn",
        "tags": [
          "tagged"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/5759196646",
        "pageId": "5759196646",
        "title": "HOW TO: Interactive Development in ML Fabric",
        "status": "CURRENT",
        "createdAt": "2025-08-28T13:15:49.289Z",
        "author": "Siddarth Sreeni",
        "space": {
          "name": "ML Platform",
          "key": "MLP"
        },
        "version": 13,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/MLP/pages/5759196646/HOW+TO+Interactive+Development+in+ML+Fabric",
        "excerpt": " Announcement ML Fabric Interactive Access for ML Experimentation and Development with JupyterLab and Visual Studio F.A.Q ML Fabric Interactive Access for ML Experimentation and Development with Jupyt",
        "tags": [
          "viewed"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/5994456534",
        "pageId": "5994456534",
        "title": "[draft] Project Poster - In Browser Small Language Model for AI Safety",
        "status": "CURRENT",
        "createdAt": "2025-10-23T21:24:02.993Z",
        "author": "Shusen Liu",
        "space": {
          "name": "AI Lab",
          "key": "bfead336f57e483497e039c75fcd1d7e"
        },
        "version": 12,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/LAB/pages/5994456534/draft+Project+Poster+-+In+Browser+Small+Language+Model+for+AI+Safety",
        "excerpt": " this doc was prepared for Product AI team’s exploration efforts. as of Jan 11, 2026, this project idea is not funded. Shusen Liu is considering patenting this idea.  Overview Define your project's sc",
        "tags": [
          "viewed"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6084989030",
        "pageId": "6084989030",
        "title": "Fine-tuned GPT-OSS models: Models 4, 5, 6",
        "status": "CURRENT",
        "createdAt": "2025-11-13T13:04:23.298Z",
        "author": "Elena Sanina",
        "space": {
          "name": "Elena Sanina",
          "key": "~71202090b8d4f355b6466f8f33ccfdcfcdc26b"
        },
        "version": 30,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/~71202090b8d4f355b6466f8f33ccfdcfcdc26b/pages/6084989030/Fine-tuned+GPT-OSS+models+Models+4+5+6",
        "excerpt": " Evaluation results for Models 4, 5, 6 fine-tuned from GPT_OSS_20B model by Liya Wang and presented in the page. Model 4 seems to be suitable for A/B test: in shows lift in the primary metric judge_wr",
        "tags": [
          "viewed"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6173797971",
        "pageId": "6173797971",
        "title": "AI Lab Daily Sync",
        "status": "CURRENT",
        "createdAt": "2025-12-05T06:08:24.747Z",
        "author": "Shusen Liu",
        "space": {
          "name": "AI Lab",
          "key": "bfead336f57e483497e039c75fcd1d7e"
        },
        "version": 82,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/LAB/pages/6173797971/AI+Lab+Daily+Sync",
        "excerpt": " Daily ~30min Sync at 9:30am PT AI employee platform: w/ junior employee w/ several senior employees eng work timeline: [milestone 0, 30 eng have this installed] OpenShell + Openclaw run in laptop w/ ",
        "tags": [
          "viewed"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6193818947",
        "pageId": "6193818947",
        "title": "[pitch deck][press release] 4p connector for Rovo (starting with Industry&Company Intelligence for Revenue ops)",
        "status": "CURRENT",
        "createdAt": "2025-12-10T04:50:52.156Z",
        "author": "Shusen Liu",
        "space": {
          "name": "AI Lab",
          "key": "bfead336f57e483497e039c75fcd1d7e"
        },
        "version": 16,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/LAB/pages/6193818947/pitch+deck+press+release+4p+connector+for+Rovo+starting+with+Industry+Company+Intelligence+for+Revenue+ops",
        "excerpt": "notee152c117-b6a8-4162-8400-7f8cff4468f0 Below is a pitch deck following Amazon’s working backwards methodology, prepared for Product AI team’s exploratory efforts. Below is a pitch deck following Ama",
        "tags": [
          "viewed"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6341926155",
        "pageId": "6341926155",
        "title": "AI Lab Ideas",
        "status": "CURRENT",
        "createdAt": "2026-01-19T15:54:46.321Z",
        "author": "Tony Chen",
        "space": {
          "name": "AI Lab",
          "key": "bfead336f57e483497e039c75fcd1d7e"
        },
        "version": 5,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/LAB/pages/6341926155/AI+Lab+Ideas",
        "excerpt": " Overview SaaS as a business model (subscription for value) will survive in the Agent Era, but SaaS as "an interface your employees log into" is dying. With the rise of "Vibe Coding" and high-agency m",
        "tags": [
          "viewed"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6350653229",
        "pageId": "6350653229",
        "title": "[draft] Rovo Autonomous Agents",
        "status": "CURRENT",
        "createdAt": "2026-01-21T06:36:05.627Z",
        "author": "Shusen Liu",
        "space": {
          "name": "AI Lab",
          "key": "bfead336f57e483497e039c75fcd1d7e"
        },
        "version": 24,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/LAB/pages/6350653229/draft+Rovo+Autonomous+Agents",
        "excerpt": " Goal: Aiming for end2end demo in for mid Feb. Focus on tech feasibility. Dimensions: proactive vs reactive tool use ( browser, local file, code ) automation vs autonomous Demo Usecase 1: “automating ",
        "tags": [
          "viewed"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6811619143",
        "pageId": "6811619143",
        "title": "RovoClaw - default agent",
        "status": "CURRENT",
        "createdAt": "2026-04-14T05:58:32.879Z",
        "author": "Josh Devenny",
        "space": {
          "name": "Josh Devenny",
          "key": "~jdevenny"
        },
        "version": 2,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/~jdevenny/pages/6811619143/RovoClaw+-+default+agent",
        "excerpt": " we’re currently playing around with different ideas on the product mental model https://www.loom.com/share/5b417980145741f480782659eea5ddec?t=868 https://www.loom.com/share/5b417980145741f480782659ee",
        "tags": [
          "viewed"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6826376847",
        "pageId": "6826376847",
        "title": "OpenClaw Chief of Staff — Default Workspace Architecture",
        "status": "CURRENT",
        "createdAt": "2026-04-15T23:55:14.712Z",
        "author": "Kevin Grennan",
        "space": {
          "name": "Kevin Grennan",
          "key": "~712020bffd994093c8458c89e1e2f0d9abcb3a"
        },
        "version": 2,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/~712020bffd994093c8458c89e1e2f0d9abcb3a/pages/6826376847/OpenClaw+Chief+of+Staff+Default+Workspace+Architecture",
        "excerpt": " Overview The kgrennan/debugging branch transforms the rovoclaw plugin's workspace-defaults/ from a generic blank-canvas assistant into a pre-configured "Work Chief of Staff" agent that's ready to wor",
        "tags": [
          "viewed"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6830754197",
        "pageId": "6830754197",
        "title": "RovoClaw Quality Test Queries",
        "status": "CURRENT",
        "createdAt": "2026-04-16T13:26:00.302Z",
        "author": "Tony Chen",
        "space": {
          "name": "AI Lab",
          "key": "bfead336f57e483497e039c75fcd1d7e"
        },
        "version": 1,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/LAB/pages/6830754197/RovoClaw+Quality+Test+Queries",
        "excerpt": " Derived from the original doc RovoClaw - default agent . Each section maps to a focus area from the doc, with queries ordered from simple → complex. 1. 📥 Follow-up / What Have I Missed? "Prioritize ",
        "tags": [
          "viewed"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6830787526",
        "pageId": "6830787526",
        "title": "Manual Smoke Testing",
        "status": "CURRENT",
        "createdAt": "2026-04-16T13:29:57.200Z",
        "author": "Tony Chen",
        "space": {
          "name": "AI Lab",
          "key": "bfead336f57e483497e039c75fcd1d7e"
        },
        "version": 11,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/LAB/pages/6830787526/Manual+Smoke+Testing",
        "excerpt": " This is using our team’s latest stable version Runbook: local Openclaw + OpenShell + AI-gateway + ClawShield Smoke testing high level observations, OpenClaw & RovoChat > RovoDev OpenClaw seems to wor",
        "tags": [
          "viewed"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6834292993",
        "pageId": "6834292993",
        "title": "Manual Smote Test",
        "status": "CURRENT",
        "createdAt": "2026-04-16T17:50:02.569Z",
        "author": "Housam Babiker",
        "space": {
          "name": "AI Lab",
          "key": "bfead336f57e483497e039c75fcd1d7e"
        },
        "version": 8,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/LAB/pages/6834292993/Manual+Smote+Test",
        "excerpt": " We evaluated three AI agent systems — Openclaw, Rovo Chat, and Rovo Dev — across 5 task categories and 4 quality dimensions. Each system was tested across 69 trials. Rovo Chat seems to provide consis",
        "tags": [
          "viewed"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6845011295",
        "pageId": "6845011295",
        "title": "Fixes & Quality Evaluation - KG's Branch",
        "status": "CURRENT",
        "createdAt": "2026-04-17T20:29:40.590Z",
        "author": "Tony Chen",
        "space": {
          "name": "AI Lab",
          "key": "bfead336f57e483497e039c75fcd1d7e"
        },
        "version": 8,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/LAB/pages/6845011295/Fixes+Quality+Evaluation+-+KG+s+Branch",
        "excerpt": " Summary We work on branch kgrennan/debugging (d38c4bd) to have an initial evaluation of RovoClaw’s quality with the new skills added. We tested the scenarios in RovoClaw - default agent. This evaluat",
        "tags": [
          "viewed"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6857589268",
        "pageId": "6857589268",
        "title": "RovoClaw Quality Test: Setup A vs B — Side-by-Side Results (2026-04-20)",
        "status": "CURRENT",
        "createdAt": "2026-04-20T22:26:32.852Z",
        "author": "Kevin Grennan",
        "space": {
          "name": "AI Lab",
          "key": "bfead336f57e483497e039c75fcd1d7e"
        },
        "version": 1,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/LAB/pages/6857589268/RovoClaw+Quality+Test+Setup+A+vs+B+Side-by-Side+Results+2026-04-20",
        "excerpt": " RovoClaw Quality Test: Setup A vs B Date: April 20, 2026 Tested by: Kevin Grennan via quality_test.py harness Agent: RovoClaw (OpenClaw sandbox) What We Tested Setup A (Baseline): Default TOOLS.md ht",
        "tags": [
          "viewed"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6881866154",
        "pageId": "6881866154",
        "title": "MVP: The "One-Click" AI SRE",
        "status": "CURRENT",
        "createdAt": "2026-04-24T06:01:01.053Z",
        "author": "Xiaojiang Huang",
        "space": {
          "name": "AI Lab",
          "key": "bfead336f57e483497e039c75fcd1d7e"
        },
        "version": 5,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/LAB/pages/6881866154/MVP+The+One-Click+AI+SRE",
        "excerpt": " Onboarding high-performance Site Reliability Engineers in seconds, not weeks. This MVP establishes a scalable pattern for "hiring" AI employees. Instead of generic chat, we inject a high-context SRE ",
        "tags": [
          "viewed"
        ]
      },
      {
        "id": "ari:cloud:confluence:a436116f-02ce-4520-8fbb-7301462a1674:page/6884132429",
        "pageId": "6884132429",
        "title": "WIP: Mini MLE",
        "status": "CURRENT",
        "createdAt": "2026-04-24T17:56:59.219Z",
        "author": "Christian Roncal",
        "space": {
          "name": "CJ Roncal",
          "key": "~712020302fbd445d404c818f235537c52aca48"
        },
        "version": 1,
        "webUrl": "https://hello.atlassian.net/wiki/spaces/~712020302fbd445d404c818f235537c52aca48/pages/6884132429/WIP+Mini+MLE",
        "excerpt": " Background/purpose mini-mle is an opinionated agentic coding framework created by the AI catalyst team. It defines a repo structure collection of skills harnesses and integrations context space The p",
        "tags": [
          "viewed"
        ]
      }
    ],
    "pullRequests": [
      {
        "id": "ari:cloud:graph::pull-request/activation/a04080b6-0834-11eb-b374-0a77f3f45304/88d430bc-c1cf-4d70-a150-e18e66f50ce6",
        "title": "chore: add dev_launch.sh helper for local Rovo Dev CLI dev mode",
        "status": "OPEN",
        "displayId": "3470",
        "sourceBranch": "chore/add-dev-launch-script",
        "destinationBranch": "main",
        "createdAt": "2026-04-23T21:22:02.004Z",
        "lastUpdate": "2026-04-23T21:22:38.071417Z",
        "commentCount": 0,
        "url": "https://bitbucket.org/{02b941e3-cfaa-40f9-9a58-cec53e20bdc3}/{294c3da3-a386-4661-8f1f-5c08a1044f69}/pull-requests/3470",
        "tags": [
          "authored"
        ]
      },
      {
        "id": "ari:cloud:graph::pull-request/activation/a04080b6-0834-11eb-b374-0a77f3f45304/26d209f4-3039-4313-bb58-1373dee42296",
        "title": "ROVOCLAW-14/bugfix-openclaw-inferencer-cli-empty-response",
        "status": "MERGED",
        "displayId": "1",
        "sourceBranch": "ROVOCLAW-14/bugfix-openclaw-inferencer-cli-empty-response",
        "destinationBranch": "main",
        "createdAt": "2026-04-22T05:40:52.263Z",
        "lastUpdate": "2026-04-22T18:05:33.184025Z",
        "commentCount": 2,
        "url": "https://bitbucket.org/{02b941e3-cfaa-40f9-9a58-cec53e20bdc3}/{8621678d-de0d-4b87-9400-d126aa6452f5}/pull-requests/1",
        "tags": [
          "reviewer"
        ]
      }
    ],
    "videos": [
      {
        "id": "ari:cloud:loom:a436116f-02ce-4520-8fbb-7301462a1674:video/activation/1621dc1f-3702-4525-84ba-fad829566798/3d13fe9ac56d42c09b41ff8b59a15d55",
        "name": "RovoClaw War Room - April 21, 2026",
        "description": "The team rolled out an alpha to a small group but encountered image/build and onboarding failures that block wider onboarding; Matt will prioritize debugging the OpenClaw image while Aaron will take the onboarding PR. UI changes for sessions/subtopics and file/highlight fixes were merged and will be refined (delete/settings placed in settings). Clawgate was converted to a microservice with deployment work underway, the team discussed hosting cost/scale implications and pricing, and agreed actions for quality evaluation, infra for agent brains, integrations prioritization, and immediate next steps for the next 24 hours.

### Alpha rollout and onboarding/build issues 4:44

- Alpha rollout sent to a few users; intent to add more users and security reviewers once onboarding is stable.
- Users reported the image won't build or run; Matt and Ben Lyle experienced the same failure messages.
- Matt suspects a Node.js/OpenCore container networking/addressing issue and will prioritize debugging today.
- Kevin suggested running install scripts; Josh noted scripts may not be included with pulled images and referenced a curl/SH installer as part of setup.
- Josh to spend time onboarding five or six alpha users once the image/install issue is resolved.
- Action owners/timeframes: Matt to debug and publish a fix; users to re-pull updated image when released.

### Frontend changes: sessions, sidebar, and session management 8:50

- Aaron added file support and fixed sidebar highlight alignment; changes merged and awaiting sync to main.
- Name changes create quick separate sessions as a workaround; team discussed whether to use hidden sessions or hidden chats for one-off actions.
- Product mental model defined: subtopics act like persistent channels (longer lasting) while an agent channel handles miscellaneous messages.
- Agreement to add deletion capability for sessions; Josh suggested placing delete/agent settings in a settings cog rather than sidebar.
- Next steps: Aaron to clean up session behavior, add delete button and possibly move agent settings; product team (Kevin) to be consulted on settings placement.

### Alpha build cadence and onboarding pr 13:43

- Alpha builds occur every few hours; expected new build within a few hours of the meeting.
- Kevin submitted an onboarding PR that reduces first-time onboarding from ~4 minutes to ~5 seconds and includes new onboarding questions.
- PR had a conflict; Josh requested someone pick it up first thing; Matt asked Aaron to take the PR while Matt debugs setup.
- Aaron agreed to take the onboarding PR and merge; once merged, security reviewers will be added and onboarding will proceed.

### Clawgate microservice migration and deployment 15:10

- Matt converted Clawgate to a microservice and deployed it to dev; integration tests with sandbox platform and ERS remain.
- Matt plans additional integration checks and expects to finish today or this afternoon once local setup is working.
- Intention to eventually hoist Clawgate out of the desktop app into cloud, but not immediate; two Clawgate instances acknowledged and will be named to avoid confusion.
- Goal: have Clawgate in stable/staging or prod by end of the week to spin up sandboxes; Matt will fix alpha tester issues as part of this work.

### File system, security plan, and hosting cost concerns 16:49

- Andy worked with Alan on secure file system access and a plan to ship securely to customers; one more team member needed for implementation.
- Andy estimated compute cost to host OpenClaw for all Atlassian staff (18,000) at just over $800,000/month (excluding token costs).
- Team discussed per-user pricing hypotheses ($50–$300/month) and tradeoffs; initial rollout cost acceptable for first few hundred users.
- Key technical problem identified: need a sleep/wake mechanism to reduce continuous compute; this is required for scale and cost control.
- Next steps: prioritize sleep/wake solution and include token cost in cost projections; Andy and others will continue security and cost work.

### Default agent quality, feedback, and coordination 20:15

- Puyang outlined onboarding Donald and Ying, and a 40-minute handover meeting in four weeks to transfer work.
- Plan to work off default agents with basic repeatable smoke tests for each scenario; Tony provided a first pass but repeatable tests needed.
- Need a feedback mechanism so alpha users can report issues for iterative improvements; Josh will add people to alpha channels and a tighter alpha channel was created.
- Puyang emphasized coordination with Kevin because multiple people touch the same agent/skill files; proposed establishing coordination mechanisms.
- Next steps: Puyang and team to define smoke tests, create feedback channels, and coordinate with Kevin on overlapping changes.

### Evaluation infra and decoupling agent brains 22:52

- Aaron suggested building a lightweight platform/infra to deploy and roll out agent 'brains' (like a simple ML pipeline for MD files) to avoid manual processes.
- Puyang agreed evaluation (offline/e2e smoke tests with golden queries) must be established even at a basic level.
- Proposal to decouple the image from agent brains: image fetches a brain from a central place, enabling independent development and rollouts.
- Action ownership: Dominic (requested by Puyang) to take ownership with Puyang's support; Aaron to collaborate on infra design.
- Next steps: schedule time to design eval and deployment workflow; implement offline eval and brain fetch mechanism.

### Integrations, plugins, and startup performance 29:33

- Josh prioritized data sources: Slack, Gmail/Google Calendar (Google Workspace) and Atlassian sources via TeamGraph; Databricks also noted for addition.
- Alex focused on optimizing Slack plugin startup performance and offered to investigate which plugins impact gateway startup; will also help with state save/restore on shutdown/start.
- Concern noted: adding many plugins can impact startup; Alex will distinguish plugins versus CLI tools to optimize accordingly.
- Next steps: Alex to analyze plugins and optimize startup performance; Josh to prioritize data sources for rollout.

### Immediate next 24-hour actions 28:08

- Top priorities: get the image working for alpha users and merge the new onboarding PR.
- Begin quality work: Daniel and Puyang to plan and own quality efforts and transition activities.
- Team agreements: Matt to debug image and re-publish fixed image, Aaron to merge onboarding PR, Josh to add alpha users/security once PR merged.
- Timing: these actions are the focus for the next 24 hours to unblock broader alpha testing.

### Pr merge and security onboarding 30:43

- Alan confirmed security reviewers will be added once the onboarding PR is merged to speed security onboarding.
- Aaron indicated merging will proceed once PR is approved; Josh confirmed readiness to add security folks.
- Recording ended after confirmation that PR actions will enable three security folks to be onboarded.",
        "url": "https://www.loom.com/share/3d13fe9ac56d42c09b41ff8b59a15d55",
        "createdAt": "2026-04-21T22:30:29.586Z",
        "updatedAt": "2026-04-21T23:03:00.313Z",
        "playableDuration": 1873.149,
        "views": 0,
        "commentCount": 3,
        "reactionCount": 0,
        "tags": [
          "shared with you"
        ]
      },
      {
        "id": "ari:cloud:loom:a436116f-02ce-4520-8fbb-7301462a1674:video/activation/1621dc1f-3702-4525-84ba-fad829566798/641d7ddfa9be4857bf87d395b654a09e",
        "name": "RovoClaw War Room - April 22, 2026",
        "description": "The team discussed evaluation strategy and automation for agent quality, prioritizing automated CLI testing if behavior is consistent and designing scenario-based tests with ground truth and metrics. Alpha testing updates covered build fixes, one persistent gateway/authentication failure affecting a single user, onboarding plans, and the need for pen tests and ClawShield integration. Action items include iterating a small prioritized scenario set, deciding account/data usage for evaluations, adding proxy support to OpenClaw for telemetry, and coordinating follow-up meetings for priorities and integration work.

### Quality stream approach and automation preference 1:36

- Ying asked whether quality analysis should use three streams (Klee mode, Gateway, desktop app) or pick the best option.
- Daniel said if the CLI/automation yields consistent behavior it should be prioritized for automated testing.
- Team agreed to discuss details later and consider automated CLI as preferred path when alignment with manual behavior is possible.

### Alpha testing status and deployment fixes 5:29

- Josh spent hours onboarding testers, submitted a fix and merged Matt's fixes; most users see the gateway spin up and health checks pass.
- One user (Gareth) experiences a gateway that won't spin up despite recloning and fresh builds; Josh compared to a prior Matt-fixed issue but remains unresolved.
- Josh onboarded a non-technical reviewer (Christine) to gather varied feedback and emphasized collecting both technical and non-technical perspectives.
- Kevin volunteered to try onboarding people now that the experience seems smoother.

### Authentication/identity incremental rollout issue 7:51

- Aaron reported investigating an authentication issue and suspects an incremental rollout on the identity side affecting one user.
- Team is engaging the identity owners to pause or resolve the change while they continue troubleshooting.
- Josh noted similar single-user discrepancies and will follow up with security onboardees to confirm testing coverage.

### Pen test planning and clawshield integration 9:12

- Jesse asked about timing for a pen test; Josh suggested multiple rounds starting with a baseline now since the product is at a working state.
- Josh observed ClawShield was optional and likely not running in current builds; wants Alan's input on enabling it.
- Jesse clarified ClawShield is Alan's ingress/egress control and noted enterprise logging needs may require separate handling; discussion to continue and Alan to be pinged.

### Debug tooling: brain surgeon for save/restore and onboarding tests 11:16

- Aaron recorded a Loom and demoed 'Brain Surgeon', a debug tool to save agent state, dashboard data, purge and import files to simulate persistent agents.
- Tool supports saving game-like state allowing testers to flip between long-running and dev agents and to purge to re-run onboarding flows.
- Josh confirmed the tool would help run permanent/dev versions and simplify onboarding and testing cycles.

### User research findings and ui improvements 12:51

- Kevin shared qualitative research insights: strong signals of product-market fit from early videos but mixed feedback overall.
- Key needs identified: high-quality connectors, improved synthesis of disparate data into coherent tasks, better data quality, and UI guidance/inspiration for new users.
- Kevin is polishing the home view to surface getting-started material and show how to modify agent behavior.

### Prototype apps and forge as a deployment vector 14:23

- Josh built a prototype app (e.g., Kanban) via the agent and observed useful project summaries; intends to record a demo video.
- Josh suggested leveraging Forge to deploy agent-generated apps, letting users run multiple personal apps and potentially share them with teams.
- Prototype work is exploratory and not intended for direct merge due to backend changes.

### Quality evaluation plan draft and execution options 16:00

- Daniel presented a drafted evaluation plan defining test scenarios, scenario format (input, prompt, persona, time anchor), ground truth, expected behavior, and scoring (points/pass-fail).
- Execution options include running tests in Rovo cloud desktop manually or via automated scripts; automation preferred if behavior aligns with manual runs.
- Two approaches for evaluation data: simulated dedicated test sets (more controlled) or generating from existing real data (faster but may create unstable/comparable results).
- Plan to start with a small prioritized scenario sample as a baseline and iterate; JSON-formatted scenario inputs and LLM-as-judge scoring proposed.
- Open questions: handling time-sensitive data, personalization and permissions, identity-related evaluation, debuggability, and how to evaluate proactive outputs (push notifications/welcome messages).

### Data privacy, accounts for simulation, and next steps 23:55

- Josh raised concerns about using internal personal data for evaluation since accounts contain private information; team must design approaches that prevent exposure.
- Daniel suggested starting with a few scenarios and using unprivileged public data to begin iterations.
- Josh plans a follow-up meeting later that day to align priorities and will invite Kevin to discuss scenario prioritization.

### Proxy support in openclaw for telemetry and logging 26:15

- Jesse secured agreement from maintainers to add proxy support to OpenClaw so requests can route through a proxy for telemetry and logging.
- Jesse opened a PR and aims to get it merged by end of week to avoid ad-hoc proxy band-aids and to facilitate centralized logs.
- Josh noted integration responsibility likely falls to Matt and encouraged coordination between Jesse and Matt.

### Meeting close and follow-ups 28:02

- Josh will add Kevin to the meeting with Daniel and Ying to align on scenario priorities.
- Team agreed to follow up on unresolved items including the persistent gateway/auth issue, ClawShield integration, pen test rounds, account usage for evaluations, and OpenClaw proxy merge.
- Meeting adjourned with thanks and action items to coordinate via channels and threads.",
        "url": "https://www.loom.com/share/641d7ddfa9be4857bf87d395b654a09e",
        "createdAt": "2026-04-22T22:31:01.460Z",
        "updatedAt": "2026-04-23T05:03:47.879Z",
        "playableDuration": 1692.866,
        "views": 0,
        "commentCount": 4,
        "reactionCount": 0,
        "tags": [
          "shared with you"
        ]
      },
      {
        "id": "ari:cloud:loom:a436116f-02ce-4520-8fbb-7301462a1674:video/activation/1621dc1f-3702-4525-84ba-fad829566798/f1849ebe5fd947d8b614b65f481f8ae2",
        "name": "Home View Updates, Tasks and Chat Buttons",
        "description": "I made updates to the home view, mostly visual polish plus some slight behavior changes, all within this repo. I cleaned up the briefing panel, adjusted icons and background, added a background image, and added a Customize button to send a message to RovoClaw for customizing future briefings, plus some prompts to learn capabilities like recurring tasks and creating new skills. I also improved calendar and task panels with layout cleanup, chat buttons that send chats into RovoClaw, and five task statuses to select, to do, in progress, done, blocked, do later, plus a not relevant signal to delete tasks. Action requested, try the customize buttons and use the chat buttons to drive the flows you want.",
        "url": "https://www.loom.com/share/f1849ebe5fd947d8b614b65f481f8ae2",
        "createdAt": "2026-04-23T01:13:43.606Z",
        "updatedAt": "2026-04-24T03:09:02.892Z",
        "playableDuration": 135.49,
        "views": 6,
        "commentCount": 1,
        "reactionCount": 3,
        "tags": [
          "shared with you"
        ]
      },
      {
        "id": "ari:cloud:loom:a436116f-02ce-4520-8fbb-7301462a1674:video/activation/1621dc1f-3702-4525-84ba-fad829566798/6f9c26f5a4a34daaa4fd87b09196df40",
        "name": "Prototype: RovoClaw Apps",
        "description": "Hey, I wanted to record a prototype I built last night, and to be clear this is not shipping, it is just to show what could be possible. We have a sidebar with Phil topics and workspace files, plus apps that use JSON data. Phil built a Kanban board and a to do app, and I moved a PR from ToDo to InProgress and then verified the data updated. I also asked for a project summary and a Sydney Office Rooms search app using Teamwork Graph data. No action is requested beyond reviewing and keeping this for future reference.",
        "url": "https://www.loom.com/share/6f9c26f5a4a34daaa4fd87b09196df40",
        "createdAt": "2026-04-23T01:43:10.315Z",
        "updatedAt": "2026-04-25T01:08:22.548Z",
        "playableDuration": 300.242,
        "views": 38,
        "commentCount": 17,
        "reactionCount": 18,
        "tags": [
          "shared with you"
        ]
      },
      {
        "id": "ari:cloud:loom:a436116f-02ce-4520-8fbb-7301462a1674:video/activation/1621dc1f-3702-4525-84ba-fad829566798/5074c98213c24740bcedf6d9bb4eaf7a",
        "name": "RovoClaw War Room - April 23, 2026",
        "description": "团队讨论了 RoverCloud/RoverDesktop 的多项稳定性和用户体验问题，这些问题阻碍了 alpha 测试，决定优先迁移到云端托管环境以减少本地机器差异。Daniel 和 Ying 将负责手动评估主页和每日简报的内容质量与个性化指标，下周提交报告并与团队迭代；Matt 和 Andy 将专注于让系统在云端可靠运行。行动项包括修复阻塞性 bug（代理挂起、停止按钮无效）、改进集成（Google 日历/Graph CLI）、建立发布/迁移流程，并与团队共享评估报告以征求反馈。

### 共享链接与 robocloud 参考 0:30

- Daniel 分享了一个新计划的链接并请与会者审阅并提供反馈。
- Ying 在寻找 RovoCloud 的评估计划并参考了 Daniel 分享的材料。
- Daniel 澄清他已分享 Robocloud 的内容，包括主页和每日简报。

### 出席、日程说明与整体稳定性关注 2:11

- Josh 提到多人缺席且澳大利亚周一有公共假期影响可用性。
- 团队发现用户和机器之间的设置不一致，Kevin 提到 Docker/安装空间问题。
- Josh 将产品定位为尚未达到 alpha 稳定，存在大量 UI/UX 错误，需要在扩大 alpha 访问前达到最低稳定水平。

### 云迁移承诺与职责分工 6:41

- Matt 和 Andy 承诺优先将系统迁移到云端以避免本地机器差异性。
- Josh、Marcus、Kevin 和 Aaron 将专注于稳定 UX 和修复 bug，Matt/Andy 推动云迁移。
- Josh 期望为演示准备好一个 alpha 发布；团队同意云托管将简化部署并减少环境特异性问题。

### 桌面应用演示与调试菜单演练 9:32

- Matt 打开桌面应用并演示了启动调试菜单的 Ask Me Anything 头像。
- Josh 发现对端口 18789 的 API 调用返回 HTML 而非 JSON，表明后端/服务不匹配。
- 团队讨论在调试前确保主页已拉取并正确设置；Josh 计划发布一个供测试的 alpha 构建。

### 代理挂起与阻塞性用户体验问题 12:31

- Daniel 等人报告代理处于挂起状态，显示“我在做这件事”但未完成操作；有时需要重启 RoverCloud。
- 停止按钮有时无法中止代理处理，沉浸式交互不够健壮。
- Marcus 将使退出沉浸模式更可靠作为首要修复项。

### 数据集成与日历/g-cal 问题 14:33

- Josh 提出数据覆盖问题：系统无法读取来自 Teamwork/Graph 的未来会议，因此无法对即将到来的事件采取行动。
- 团队讨论了选项：使用 Google CLI、集成服务或其他工具；Will 正在调查使用某个集成工具。
- Josh 强调正确的 Slack 和 Google 日历连接对于调度操作和冲突解决是必须的。

### 视频访问/转录不一致与 cli 错误 15:32

- Daniel 报告通过 RoverCloud 和 RoboDev CLI 访问某些视频转录存在不一致：有些视频返回转录而有些虽可查看 URL 却报告无访问权限。
- Josh 建议为 Graph CLI 团队提交一个 bug（TWG-CLI），因为 CLI 无法读取未来会议或处理某些视频情况。
- Daniel 提出将链接添加到项目以便分配、分类和功能请求。

### 主页与每日简报评估提案 19:50

- Daniel 总结用户研究发现：主页和每日简报反响良好，尤其对每日简报的实用性评价较高。
- 建议的评估指标：主页使用精确度/准确性（项目项的基准事实、行动项），每日简报使用相关性、事实准确性、新鲜度以及避免重复用户更新。
- 建议个性化控制（主题/项目/人物优先级、VIP 类别、选择退出）并允许用户设定规则以决定想听或不想听的内容。

### 评估流程、手动测试与自动化计划 23:53

- Daniel 提议由 Ying 和 Daniel 基于个人经验生成初步评估报告并邀请少数用户反馈。
- 第 1 阶段：基于用户的手动报告以识别关键信号和优先项；第 2 阶段：使用 LLM 作为评分者和基于事件的信号进行可扩展测试自动化。
- 计划包括合成场景（繁忙日、会议密集）可选、对评分进行迭代调整，并为新模型/代理版本运行周期性测试；目标是下周产出第一版报告。

### 发布流程、迁移选项与 alpha 用户准备度 29:34

- Josh 和 Matt 强调需要可复现的 RoverClaw 发布流程及协调桌面/后端部署，因为后端更改可能需要前端更新。
- 提议增加“迁移我的代理”按钮或迁移流程，帮助用户将本地代理迁移到云端，以便更容易加入云托管的 alpha。
- Jesse 提供了悉尼的 ProdSec 支持；团队重申优先稳定系统、为 alpha 用户提供每日更新并确认所需的支持/资源。",
        "url": "https://www.loom.com/share/5074c98213c24740bcedf6d9bb4eaf7a",
        "createdAt": "2026-04-23T22:31:19.357Z",
        "updatedAt": "2026-04-23T23:09:23.190Z",
        "playableDuration": 1956.628,
        "views": 0,
        "commentCount": 4,
        "reactionCount": 0,
        "tags": [
          "shared with you"
        ]
      },
      {
        "id": "ari:cloud:loom:a436116f-02ce-4520-8fbb-7301462a1674:video/activation/1621dc1f-3702-4525-84ba-fad829566798/9ef38860cb1948ac93e9cb6ee8065a6f",
        "name": "RovoClaw Update, Desktop and Cloud Progress",
        "description": "This week I launched the Rovo desktop and the OpenClaw backed version to 15 alpha users internally. OpenClaw runs locally in a docker image so I cannot share it widely, but we are getting good learnings. I updated the RovoClaw app homepage with onboarding, calendar and to do fetching, task status like blocked items, and fixed time zone bugs. I also showed improved thinking traces and calendar summaries, plus working Slack and Google Calendar integration actions. Next week we focus on bug fixing and quality, and there is no action requested from viewers.",
        "url": "https://www.loom.com/share/9ef38860cb1948ac93e9cb6ee8065a6f",
        "createdAt": "2026-04-24T11:25:55.090Z",
        "updatedAt": "2026-04-27T20:38:50.098Z",
        "playableDuration": 460.99,
        "views": 18,
        "commentCount": 4,
        "reactionCount": 5,
        "tags": [
          "shared with you"
        ]
      },
      {
        "id": "ari:cloud:loom:a436116f-02ce-4520-8fbb-7301462a1674:video/activation/1621dc1f-3702-4525-84ba-fad829566798/de755fc249284f179ef7429221841e66",
        "name": "RovoClaw War Room - April 27, 2026",
        "description": "The team reviewed alpha testing status and widespread instability tied to the image, OpenShell/OpenClaw updates, and inconsistent agent behavior. Work priorities are stabilizing the release (including pinning dependencies), getting a sandbox/cloud deployment, improving onboarding and connectors, and iterating quality (precision/recall) and prompts for the homepage and daily brief. Next steps: discuss prompt/UX changes with Daniel/Kevin/Aaron, investigate Slack/image logs, coordinate Trello support, finalize sandbox scheduling (cron) and Clawgate migration, and start mobile conversations.

### Alpha testing feedback and immediate fixes 3:16

- Alpha testers provided multiple feedback points; MCB dropped about 10 items and Aaron submitted PRs addressing 6 of them.
- Remaining items include non-bug opinionated requests and a Slack-related issue that Aaron could not reproduce locally.
- Kevin is polishing side panel homepage and files/memories panel; skills tab not yet completed and Josh will retry building it.
- Decision to hold onboarding of additional alpha users after ~16 onboarded; Kevin will hold 4 interested people for a week to avoid exposing more users to current instability.
- Action: Aaron/Kevin/Josh to investigate Slack/image logs for repro and unblock outstanding tester issues.

### Image and client instability concerns 6:04

- Testers and engineers repeatedly experienced image and desktop app failures; troubleshooting is inconsistent across environments.
- Some reproducible UI bugs (e.g., sentences squished) were fixed; other issues may be environment-specific.
- OpenShell updates were suspected as a recent root cause; Matt pinned OpenShell to a specific version recently to reduce breakage.
- Team acknowledged unpredictability where fixes help some users but new or intermittent failures appear for others.

### Release/version churn and instability analysis 11:13

- Discussion revealed the image was pinned to an April 2 version in some places while others believed updates occurred; Marcus bumped and will merge a PR to update.
- Team noted high churn and many releases in OpenCore/OpenClaw upstream cause frequent breakages.
- Marcus and others observed inconsistent agent behaviors within a single version (agents replying to different threads/sessions unpredictably).
- Concern raised about supply-chain and maintainer practices in upstream repositories, with recommendations to add SAST and review processes (Jesse implementing SAST).

### Quality evaluation for homepage and daily briefs 14:20

- Daniel and Ying ran an evaluation on homepage and daily briefs and measured precision and recall; precision around ~50% in initial analysis.
- After prompt customization precision improved somewhat but gaps remain, including connector sync issues and unclear distinctions between task vs FYI items.
- Team agreed Daniel/engineering want a discussion with Josh and Kevin before applying system/agent prompt changes to ensure alignment.
- UX suggestion: keep users on the homepage when marking items not relevant, or provide a chat sidebar so homepage actions don't force navigation to chat.

### Trello interest and integrations strategy 7:31

- Senior Trello engineers (Steve Ronderos and team) expressed strong interest and offered up to four engineers to help integrate OpenClaw with Trello.
- Team discussed focusing on interacting with OpenCloud Agent via Trello rather than deep product integration with the desktop app.
- Josh to follow up with Trello contacts and coordinate potential separate workstream for Trello integration and sandbox interaction.

### Openclaw/opencore contributions, slack and memory concerns 18:41

- Alex has two main unmerged contributions: persisting in-memory state across restarts and hooks for external scheduling; persistence not a hard block for sandbox rollout based on current usage.
- Slack plugin may contain in-memory state; supporting Slack requires a bot per agent which raises operational/management complexity.
- Security viewpoint favored Slack EMM over consumer messaging; Slack support would require careful data protection planning.
- Alex noted upstream OpenCore repository has heavy commit activity, few reviews, and maintainer direct pushes—raising supply-chain risk; Jesse is working to add SAST.

### Cron/external scheduling and sandbox wake/sleep flow 22:04

- Alex proposed using Atlassian cron man and Clawgate to schedule and wake sandboxes when scheduled tasks exist; OpenClaw currently manages cron internally which fails when sandboxes are asleep.
- Proposed flow: OpenClaw sandbox calls Clawgate to register cron jobs; Clawgate (or later a service) calls cron man to persist schedule and wake sandbox when needed.
- Clarity needed on cron man authentication (likely service-to-service ASAP issuer); Sam Watson should be informed if service auth required.
- Marcus reported Matt has a dev service orchestrating sandboxes; interim options include desktop app scheduling with OS until cloud scheduler is available.

### Clawgate migration and mobile planning 28:42

- Clawgate exists both inside the desktop app and as a separate microservice; plan is to consolidate functionality into a cloud microservice for easier mobile support.
- Josh asked whether to wait for Clawgate cloud migration before tackling mobile; Marcus/Aaron recommended starting conversations now and lining up a senior engineer from the mobile/Clawgate team.
- Aaron will contact the team to gauge bandwidth and get a senior engineer prepared; team warned mobile team capacity is limited due to prior reductions.
- Interim: mobile team can build against the interface and spike integration while Clawgate migration progresses.

### Action items, next meetings and alignment 31:17

- Daniel, Josh and Aaron to meet to align on prompt/instruction updates and to start with non-sensitive user-behavior signals for actions.
- Josh to start a Slack thread connecting Kevin and Will to coordinate bootstrap and onboarding changes; Kevin to hold new alpha signups for ~one week.
- Aaron to contact Trello and mobile teams to line up engineering support and start conversations for integrations and mobile spikes.
- Marcus/Matt to continue sandbox orchestration and version PRs; Alex to push OpenCore/OpenClaw PRs for scheduling and persistence; team to investigate logs and pin problematic dependencies (OpenShell) as needed.",
        "url": "https://www.loom.com/share/de755fc249284f179ef7429221841e66",
        "createdAt": "2026-04-27T22:30:38.142Z",
        "updatedAt": "2026-04-27T23:53:44.799Z",
        "playableDuration": 1949.818,
        "views": 1,
        "commentCount": 3,
        "reactionCount": 0,
        "tags": [
          "shared with you"
        ]
      }
    ],
    "projects": [],
    "goals": [],
    "blogPosts": [],
    "whiteboards": [],
    "devActivity": [
      {
        "id": "ari:cloud:graph::branch/activation/a04080b6-0834-11eb-b374-0a77f3f45304/f25d6a70-acf3-483a-9d21-e87b408f9dc2",
        "name": "chore/add-dev-launch-script",
        "url": "https://bitbucket.org/{}/{294c3da3-a386-4661-8f1f-5c08a1044f69}/branch/chore/add-dev-launch-script",
        "displayName": "chore/add-dev-launch-script",
        "createdAt": "1970-01-01T00:00:00Z",
        "lastUpdated": "2026-04-23T21:17:03Z",
        "tags": [
          "created",
          "owned"
        ]
      },
      {
        "id": "ari:cloud:graph::commit/activation/a04080b6-0834-11eb-b374-0a77f3f45304/947569f5-f645-4809-a176-23909729d071",
        "url": "https://bitbucket.org/{}/{8621678d-de0d-4b87-9400-d126aa6452f5}/commits/2faf63b350da2f03b6db7d4ca343ccf7e76a66d3",
        "displayName": "2faf63b",
        "message": "feat: sync from CoreProjects/OpenStartup - full graph visualization, BTA streaming, UI overhaul

Synced all changes from CoreProjects/OpenStartup with rich_python_utils → python_utils replacement.

Key changes:
Server:
- conversation_service.py: JsonLogger RankEvolve-style per-turn logging, on_new_turn callback,
  async _on_new_turn, _get_or_create_session_logger, cache_folder rotation per turn
- websocket_interactive.py: _last_prompt_data, _sanitize_for_json, inline prompt_data in pending_input,
  TaskWebSocketInteractive, graph event support (send_graph_event, send_task_status)
- tool_dispatcher.py: _dispatch_as_task, async execution, interactive + graph_reporter wiring
- session_store.py: unified turn dirs to turn_NNN/ (RankEvolve style), get_session_dir()
- data_service.py: get_session_dir() public method
- manager_websocket_routes.py: slash command routing (/mock_task), regex+hyphen, executor
  resolution, task_status 'starting', CommandAutocomplete support
- session_routes.py:...",
        "hash": "2faf63b350da2f03b6db7d4ca343ccf7e76a66d3",
        "createdAt": "2026-04-22T17:37:30Z",
        "tags": [
          "authored"
        ]
      },
      {
        "id": "ari:cloud:graph::commit/activation/a04080b6-0834-11eb-b374-0a77f3f45304/3ba6a236-fa22-478d-a545-19ad2bde7184",
        "url": "https://bitbucket.org/{}/{294c3da3-a386-4661-8f1f-5c08a1044f69}/commits/89184c3c780597bbfd2f950a5f9859d0a62e9861",
        "displayName": "89184c3",
        "message": "chore: add dev_launch.sh helper for local Rovo Dev CLI dev mode

Adds scripts/dev_launch.sh that wraps the standard local-development
launch flow for the Rovo Dev CLI:

- Resolves repo root and ensures uv + git are available
- Runs 'uv sync --all-packages' if .venv/bin/rovodev is missing (or with
  --sync to force a re-sync)
- Auto-loads .env so USER_EMAIL / USER_API_TOKEN are available (uv run
  does not load .env on its own; only the VS Code launch configs do)
- Verifies that rovodev, rovodev_tui, nemo, nautilus, and scout are all
  imported from packages/*/src/... rather than site-packages, proving
  the workspace is editable
- Hands off to .venv/bin/rovodev with any arguments

Three modes:
  scripts/dev_launch.sh           # Launch (default subcommand: run/TUI)
  scripts/dev_launch.sh --check   # Verify env + editable install only
  scripts/dev_launch.sh --proof   # Temporarily inject a unique marker
                                  # into version.py, run rovodev --version,
   ...",
        "hash": "89184c3c780597bbfd2f950a5f9859d0a62e9861",
        "createdAt": "2026-04-23T21:17:03Z",
        "tags": [
          "authored"
        ]
      }
    ],
    "calendarAndDocs": [],
    "comments": [],
    "scope": "me",
    "accountId": "712020:5cf4b2db-f12d-4739-867d-9fe8ecb66d54"
  },
  "meta": {
    "resourceClass": "projection",
    "sourceMode": "mixed",
    "resourceType": "work",
    "backend": "graphstore+hydration"
  }
}

#### Step 2 — Generate Tweet-Length Update (≤280 chars)
Format: 

Template:


#### Step 3 — Generate Detailed Update
Structure the "More details" section:



#### Step 4 — Source Attribution
Always include at the bottom:


**Decision Point:** Present draft to human for review before publishing. Never auto-publish Atlas updates.

---

### 2.4 Workflow: Health Trend Analysis

**Trigger**: Monthly or quarterly reviews, portfolio health assessments.

#### Step 1 — Fetch Historical Updates


#### Step 2 — Compute Trends
Compare current scores against previous period:


#### Step 3 — Flag Anomalies
Alert on:
- Score drop > 15 points in one period
- Status change from On Track to Off Track (skipping At Risk)
- New Critical/Blocker risks since last review
- Stale goals (no update in > 30 days)

---

## 3. Domain Guidance

### 3.1 Templates and Checklists

#### Weekly Health Check Checklist
- [ ] Refresh Jira metrics (schedule, scope, quality, risk)
- [ ] Compute scorecard dimensions
- [ ] Review OKR/KR scores against latest data
- [ ] Generate Atlas update narrative
- [ ] Flag any anomalies or threshold breaches
- [ ] Present draft to TPM for confirmation
- [ ] Publish confirmed update to Atlas

#### Scorecard Configuration Template


### 3.2 Decision Criteria

| Decision | Criteria | Action |
|----------|----------|--------|
| Score a metric-backed KR | Quantitative target exists | Compute: current / target |
| Score a milestone-backed KR | Delivery milestones defined | Compute: completed / total |
| Score a judgment-backed KR | No quantitative target | Map from status: On Track=0.8, At Risk=0.5, Off Track=0.2 |
| Choose rollup method | Explicit weights defined? | Yes → weighted; No → equal_weighted |
| Escalate to human | Score drops >15 points | Flag in report + direct notification |
| Generate Go-To-Green | Status is At Risk or Off Track | Required — include specific actions with owners |

### 3.3 Terminology

| Term | Definition |
|------|-----------|
| **KR Score** | 0.0–1.0 score for a Key Result. 0.0–0.3 = Off Track, 0.4–0.6 = At Risk, 0.7–1.0 = On Track |
| **Objective Score** | Average of KR scores (equal or weighted) |
| **Health Scorecard** | Four-dimension assessment (schedule, scope, quality, risk) producing an overall 0–100 score |
| **Go-To-Green** | Specific corrective actions to move from At Risk/Off Track back to On Track |
| **Atlas Update** | A status communication on an Atlas goal/project: ≤280 char headline + detailed narrative |
| **Success Measure** | Atlas/Goals term for Key Result |
| **Program Increment (PI)** | SAFe planning cadence (typically 8-12 weeks) |
| **ROAM** | Risk classification: Resolved, Owned, Accepted, Mitigated |

### 3.4 Cadence Patterns

| Activity | Frequency | Description |
|----------|-----------|-------------|
| Program health scorecard | Weekly (Monday) | Compute all four dimensions + overall score |
| OKR score refresh | Weekly or bi-weekly | Update KR scores from latest metrics |
| Atlas update publication | Weekly or bi-weekly | Publish narrative update to Atlas goals/projects |
| Health trend analysis | Monthly | Compare scores over 4-week period, flag anomalies |
| Portfolio roll-up | Quarterly | Aggregate across multiple programs for exec reporting |

---

## 4. Integration Metadata

### 4.1 Tools Referenced

| Tool | Operations Used |
|------|----------------|
| `twg` | `jira workitem search`, `jira workitem get`, `goals --scope me/org`, `projects --scope me`, `work query`, `context jira workitem` |
| `mcp__atlassian__invoke_tool` | `search_jira_using_jql`, `get_jira_issue` |
| `mcp__atlassian_goal__invoke_tool` | `atlassian_goal_get_goal`, `atlassian_goal_search_goals`, `atlassian_goal_get_goal_updates` |
| `mcp__atlassian_project__invoke_tool` | `atlassian_project_get_project`, `atlassian_project_search_projects`, `atlassian_project_get_project_updates`, `atlassian_project_get_project_risks` |
| `mcp__teamwork_graph__invoke_tool` | `twg_twg_atlassian_graph_get_project_context`, `twg_twg_atlassian_graph_get_context_for_work_item` |

### 4.2 Cross-Tool Patterns

**Pattern 1: Jira → Scorecard → Atlas Update**
1. Query Jira via `twg jira workitem search` or `search_jira_using_jql` for delivery metrics
2. Compute scorecard scores client-side
3. Query Atlas goals via `atlassian_goal_get_goal` for current KR scores
4. Generate narrative combining Jira metrics + Atlas context
5. Present to human for confirmation before writing

**Pattern 2: Atlas Goals → KR Roll-Up → Objective Score**
1. Fetch goal structure via `atlassian_goal_get_goal`
2. For metric-backed KRs, fetch source data from Jira
3. Compute individual KR scores
4. Aggregate via chosen rollup method
5. Present recommendation with source attribution

**Pattern 3: Multi-System Health Sweep**
1. Fetch Jira issues via TWG (batch-efficient)
2. Fetch Atlas project risks via MCP
3. Fetch Atlas goal status via MCP
4. Compute all dimensions
5. Compare against previous period (from stored updates)

### 4.3 Autonomy Levels

| Operation | Autonomy | Rationale |
|-----------|----------|-----------|
| Query Jira, Atlas, Confluence | 🟢 Fully Autonomous | Read-only data collection |
| Compute scorecard scores | 🟢 Fully Autonomous | Deterministic calculation |
| Compute KR roll-up scores | 🟢 Fully Autonomous | When using established method |
| Generate narrative drafts | 🟢 Fully Autonomous | Draft generation only |
| Change rollup method | 🔴 Human Required | Affects scoring methodology |
| Override computed scores | 🔴 Human Required | Score is human-curated in Atlas |
| Publish Atlas updates | 🔴 Human Required | External communication |
| Set/change KR weights | 🔴 Human Required | Affects scoring methodology |
| Create/modify goals | 🔴 Human Required | Structural changes |

---

## 5. Guardrails and Escalation

### 5.1 Safety Boundaries

**The AI MUST NOT:**
- Auto-publish Atlas updates without human confirmation
- Override human-set goal statuses or scores
- Change OKR rollup methodology without explicit approval
- Set or modify KR weights autonomously
- Create, delete, or restructure Atlas goals/projects
- Publish health scores externally (Slack, email) without confirmation
- Treat Jira completion percentages as the sole source of truth for goal health — Atlas design deliberately separates delivery metrics from outcome assessment

### 5.2 Escalation Triggers

| Condition | Action |
|-----------|--------|
| Overall health drops below 40 (Off Track) | Immediately flag to TPM with Go-To-Green recommendations |
| Score drops >15 points in one period | Alert TPM, include root-cause analysis |
| New Critical/Blocker risk discovered | Flag in next status update, recommend ROAM classification |
| Goal has no update for >30 days | Flag as stale, recommend review |
| KR data sources unavailable | Report with partial data, clearly mark missing dimensions |
| Conflicting data across systems | Flag discrepancy, defer to human judgment (see cross-system-reconciliation skill) |
| Rollup method produces unexpected results | Present raw KR scores alongside computed aggregate, ask human to validate |

### 5.3 Error Handling

| Error | Response |
|-------|----------|
| Jira query returns no results | Check JQL syntax, verify project key. If confirmed empty, score dimension as "No Data" rather than 0 |
| Atlas goal API returns 404 | Verify goal ARI format. Report goal as "Not Found" — do not fabricate data |
| TWG CLI timeout or error | Retry once. If still failing, fall back to MCP tools for the same data |
| Partial data (some systems unavailable) | Compute scorecard with available data, clearly label missing dimensions. Never extrapolate from incomplete data |
| Rate limiting (429) | Wait and retry with exponential backoff. Report delay to user |
| Inconsistent data across systems | Flag in report, do not auto-resolve. Defer to cross-system-reconciliation skill |
