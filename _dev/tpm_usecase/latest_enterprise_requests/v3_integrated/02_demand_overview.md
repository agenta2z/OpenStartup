# 02 · Demand Overview — what does the enterprise want, in aggregate
*(verified 2026-05-15)*

## 1. The shape of the demand

| Metric | Value | How verified |
|---|---|---|
| ENT tickets actively triaged in this analysis | **~100 unique** (live-fetched in last 60 days + ENT50 historical) | `mcp__atlassian__get_jira_issue` per-key |
| Currently OPEN with `priority in (Blocker, Critical)` | **21** | `scripts/twg jira workitem search --jql 'project = ENT AND priority in (Blocker, Critical) AND statusCategory != Done'` |
| Formally committed on **ENT50** (Confluence 5861641112) | **25** named items across FY26 / FY27 / FY28 slots | Page read 2026-05-15 |
| Recently created (since 2026-03-15, last 60 days) | **46** unique keys (gap-free range ENT-3884 → ENT-3837 minus deleted) | `--jql 'created >= "2026-03-15"'` |
| Without an assignee | 7 in the recent inbox | Direct read of `assignee` field |

> The legacy claim of **"152 ENT tickets total"** could not be reproduced. The TWG aggregate `project = ENT` returns an anomalous totalCount (likely a JQL-quoting artefact in the TWG wrapper). Treat any standalone "total ENT count" claim with skepticism — only the per-priority and per-window counts above are reliable.

## 2. Demand distribution by Jira component family

Each ENT ticket carries a Jira **component** that names the area of Atlassian Cloud the request lands in. Those components are the **routing key** we use to map a ticket onto a CoreEng pillar.

| Component family (live, 2026-05-15) | Approx count last 60 days | Routes to |
|---|---|---|
| **Rovo / AI** (Rovo - Other, Chat, MCP, Studio Agents, Admin Controls, Insights, Search, Slack App, Dev) | ~24 | Rovo / AI Platform (out-of-CoreEng) — observed via MUSTWIN |
| **Cloud Administration** (Atlassian accounts, Admin API, Permissions, Organisations, Cloud Site Names, Other) | ~13 | Identity → David Dooley |
| **Cloud Security** (Auth Policies, External / Guest user) | ~3 | Identity → Dushyant Gill |
| **Trust Foundations** (FedRAMP, GovCloud, Data Residency, Region & Deployment) | ~5 | Identity → Dushyant Gill |
| **Information Protection** (Region/Deployment, Guard, DLP) | ~7 | Atlassian Guard (out-of-CoreEng) + Identity for Trust scope |
| **Resilience** (Backup/Restore — BRIE family) | ~6 | TSP (Corey Johnston) + TDP (Vinod Kumar) |
| **Encryption — BYOK** | ~6 (most are open Blockers) | TDP (Vinod Kumar) + TSP for AWS-XKS |
| **Audit — ALP** | 2 (both open Blocker) | Identity (Dushyant Gill) |
| **AGC — Scale** | 2 | TDP (Vinod Kumar) |
| **Confluence (compliance/security/editor/whiteboards)** | ~9 | Confluence product team |
| **Jira platform** (Workflows, Performance, Custom Fields) | ~6 | Jira product team (TDP for performance) |
| **JSM** (Assets/CMDB/Operations) | ~5 | JSM product team |
| **Loom** (Org policies, Domain sharing, Public link, etc.) | 7 | Loom product team |
| **Atlas / Project** | 2 (both Blocker — long-standing) | Atlas team |
| **Ecosystem Platform** | 2 | Ecosystem team |
| **Migration — Other** | 1 | Identity (David Dooley) |
| **Analytics / Data Lake** | 2 | TDP-adjacent (Ben Jackson) |

> See [`03_master_mapping.md`](03_master_mapping.md) §C for the **per-ticket** routing.

## 3. Reproducible JQL snippets

Use the snippets below to refresh any number in this set against live Jira (`hello.atlassian.net`).

```bash
# Total open Blocker / Critical (this is the canonical "what's hot right now" count)
scripts/twg -s hello -o json jira workitem search \
  --jql 'project = ENT AND priority in (Blocker, Critical) AND statusCategory != Done' \
  --first 50

# All tickets created in the last 60 days
scripts/twg -s hello -o json jira workitem search \
  --jql 'project = ENT AND created >= "2026-03-15" ORDER BY created DESC' \
  --first 200

# All tickets updated in the last 45 days (incl. legacy items still moving)
scripts/twg -s hello -o json jira workitem search \
  --jql 'project = ENT AND updated >= "2026-04-01" ORDER BY updated DESC' \
  --first 200

# Rich per-ticket fetch (priority, assignee, components, labels) — required for routing
mcp__atlassian__get_jira_issue {
  "issue_url": "https://hello.atlassian.net/browse/ENT-XXXX",
  "show_links": true,
  "extra_fields": ["assignee","reporter","priority","components","labels",
                   "duedate","fixVersions","parent"]
}
```

## 4. Trends (qualitative, May 2026)

These are the patterns visible across the verified ticket set. Each is backed by named tickets in [`03_master_mapping.md`](03_master_mapping.md) §D ("Cross-cutting themes").

1. **AI governance is the new top-of-mind concern.** ~24 of the 46 last-60-day items touch Rovo / AI. Two of the three open AI items at Blocker priority are tied to a single named customer (DocuSign, evaluating Glean as a competitor) — **ENT-3881** (HIPAA) and **ENT-3791** (long-context orchestration). The MCP cluster (8 tickets, all Minor) signals a new control surface customers want to govern (multi-site, allow-list, external-user policy).
2. **The BYOK family is the longest-running open Blocker cluster.** Six items (ENT-1958, 2022, 2035, 2085, 2647, 3099) are all Blocker; ENT-2085 is the only one with active escalation tracked (May 2026 review, Filiberto Selvas DRI).
3. **Audit Log Platform (ALP) embeddability** is a 2-ticket-only Blocker concern (ENT-2883, ENT-3721) that affects two products differently — Confluence vs Jira/JSM. Both are Identity-pillar.
4. **Sovereign / regulated-cloud demand is broadening but still Minor priority.** UAE DESC (ENT-3837), NATO D32 (ENT-3833), India AI processing (ENT-3784), EU GCP (ENT-3782, ENT-3739), Switzerland analytics (ENT-3731) — all Minor on the priority field, but the ENT50 list reserves FY27/FY28 slots for several of them (FedRAMP High ENT-2289, IL5 ENT-98, IL6 ENT-293).
5. **Lifecycle governance at scale is a single large-customer story (PwC).** ENT-3824 (PwC, 2,000+ sites) is **Minor** in Jira — the priority field does not match the customer-revenue narrative attached to it in earlier docs. This is a candidate for re-prioritisation in MUSTWIN.
6. **BRIE scaling for P100 customers** is a coherent 5-ticket cluster (ENT-3785, 3787, 3788, 3668, 1929 + ENT-311). Lakshmi Behl is the recurring assignee. Multi-pillar (TSP + TDP).
7. **Loom enterprise governance** is an 8-ticket cluster (ENT-3814, 3817–3822) all owned by Kristen Waters — net new MUSTWIN observation, no CoreEng action.

## 5. Status-field distribution (the "softer" priority)

Jira uses a separate `status` field that captures workflow state — distinct from `priority`. Across the 100+ enriched tickets the visible distribution is:

| Status | Approx count | Note |
|---|---|---|
| Pending Review | ≈ 75 (most) | Default state for newly-opened ENT items awaiting prioritisation |
| Roadmap (Internal Only) | ≈ 4 | e.g., ENT-3721 (ALP for Confluence), ENT-3809 (MCP block external) |
| Actively Investigating | ≈ 5 | e.g., ENT-3807 (agent throttling), ENT-3830 (Jira agent behaviour), ENT-3844 (Rovo dashboard) |
| Under Review | ≈ 2 | e.g., ENT-3813, ENT-3672 |
| Closed / Resolved / Shipped | ≈ 14 | mostly historical |
| Pending Customer | (occasional) | rare in this corpus |

> **Status alone is not a routing signal.** Most items sit in *Pending Review* regardless of priority — which is why the priority field plus the component is what we use to drive the mapping.

## 6. What this overview is **not**

* It is **not** a customer-segmentation analysis. The Enterprise DRI (Filiberto Selvas) maintains the customer-tier view in TRUSTED-space pages.
* It is **not** a financial-impact / revenue-attached view. Revenue context lives in the high-touch sales tooling (S360 / Sales Forecast), not in this corpus.
* It is **not** a technical-design view per pillar. Pillar leads maintain those in their own onboarding hubs (linked from [`01_organization.md`](01_organization.md)).
