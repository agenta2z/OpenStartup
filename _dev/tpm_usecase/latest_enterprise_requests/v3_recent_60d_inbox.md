# Recent ENT Inbox (last 60 days, since 2026-03-15) — v3

> All metadata is **verified live** against `hello.atlassian.net` Jira on 2026-05-15. Source: `issues_enriched/batchA.json` (46 tickets, ENT-3884→ENT-3837) + `issues_enriched/batchB.json` (57 tickets including referenced legacy items). The "Pillar route" column is what a TPM should use to forward each item.

## Summary

| Metric | Value (verified 2026-05-15) |
|---|---|
| New ENT tickets fetched (recent inbox) | 46 (gap-free range ENT-3884 → ENT-3837 minus deleted/missing keys) |
| Of those: Blocker | 2 (ENT-3881, ENT-3878) |
| Of those: Critical | 1 (ENT-3868) |
| Of those: Major | 6 (ENT-3877, 3876, 3875, 3874, 3847, 3844) |
| Of those: Minor | 39 |
| Top component family | Rovo / AI (~18) |
| 2nd component family | Cloud Admin & Security (~9) |
| 3rd component family | Jira Platform / Admin (~8) |
| Tickets with no assignee | 7 (need triage) |

> The previous local docs claimed **a total of 152** ENT tickets in the snapshot. That number could not be reproduced live (the JQL `project = ENT` aggregate returned a count anomaly via TWG; manual count of recent + ENT50 verified items ≈ 100). Treat any "total ENT count" claim in v1/v2 docs with skepticism — the only reliable counts are the **per-priority** ones above and the ENT50 commit list (≈ 25 items).

## Section A — High-priority recent items (Blocker / Critical / Major), 2026-03-15 → 2026-05-15

| Key | Priority | Assignee | Pillar route | Component | Why it matters |
|---|---|---|---|---|---|
| ENT-3881 | **Blocker** | Ashwini Rattihalli | AI ↔ Identity | Rovo / AI - Other | DocuSign HIPAA blocking AI adoption (customer eval Glean) |
| ENT-3878 | **Blocker** | Shravan Suri | AI | Rovo Chat | Rovo cannot mod/del Google Calendar events |
| ENT-3868 | **Critical** | Dmitry Melikov | TDP / Jira Platform | Jira Platform Performance | Systemic API rate limiting across 6+ enterprise customers |
| ENT-3877 | **Major** | Sushant Koshy | AI | Rovo Studio Agents | Bug: Jira attachments via /attachment/content/ URL |
| ENT-3876 | **Major** | Sushant Koshy | AI | Rovo Studio Agents | Bug: agents don't auto-follow Confluence links in Jira |
| ENT-3875 | **Major** | Sushant Koshy | AI | Rovo Studio Agents | (variant of 3877) |
| ENT-3874 | **Major** | Sushant Koshy | AI | Rovo Studio Agents | (variant of 3876) |
| ENT-3847 | **Major** | Unassigned | AI | Rovo Admin Controls | Rovo Enablement issues (needs triage) |
| ENT-3844 | **Major** | Griffin Jones | AI | Rovo Insights & ROI | Rovo usage trend dashboard |
| ENT-3807 | **Blocker** | Ben Costello | AI | Rovo / AI - Other | Agent automation throttling — minimal visibility |
| ENT-1703 | **Major** | Rob Saunders | Identity | Cloud Admin — Organisations | Increase site limit 150 → 2,000 (Enterprise) — ENT50 FY26 |

## Section B — Pillar-routed inbox (Minor priority bulk, last 60 days)

### → Identity (David Dooley / Dushyant Gill)
ENT-3869, 3867, 3848, 3824, 3811, 3810, 3855, 3837, 3789, 3746, 3745, 3738, 3737, 3736, 3730, 3782, 3784, 3739

### → TSP / TDP (Corey Johnston / Vinod Kumar)
ENT-3790, 3788, 3787, 3785, 3668, 3812

### → AI Platform (Rovo) — outside CoreEng but routed through MUSTWIN
ENT-3879, 3866, 3865, 3864, 3860, 3856, 3849, 3843, 3842, 3841, 3838, 3832, 3826, 3825, 3791, 3793, 3744, 3747, 3863, 3862, 3884, 3880

### → Guard / DLP (Audrey Garcia + Information Protection)
ENT-3882, 3872, 3852, 3851, 3823, 3815

### → Confluence / Jira / JSM / Loom (Product teams — outside CoreEng)
- **Loom** (Kristen Waters): ENT-3814, 3817, 3818, 3819, 3820, 3821, 3822
- **Confluence**: ENT-3861, 3829, 3828, 3846, 3840, 3743, 3859, 3883
- **Jira platform**: ENT-3827, 3845, 3868
- **JSM (Assets/CMDB)**: ENT-3873, 3858, 3839, 3783, 3742
- **JSM Other**: ENT-3857
- **Ecosystem Platform**: ENT-3854, 3871

### → Migration / Other
ENT-3789 (sandbox separation), ENT-3870 (video embedding for onboarding)

## Section C — Tickets needing TPM triage attention (no assignee)

These items came in during the inbox window with `assignee = null` — the MUSTWIN DRI should ensure routing:

| Key | Component | Suggested pillar |
|---|---|---|
| ENT-3870 | Admin Experience | (Admin Hub team — outside CoreEng) |
| ENT-3869 | Cloud Admin — Atlassian accounts | Identity → David Dooley |
| ENT-3847 | Rovo Admin Controls | AI Platform |
| ENT-3813 | Jira Align — Integrations | (Jira Align team) |
| ENT-3810 | Cloud Security — Auth Policies | Identity → Dushyant Gill |
| ENT-3789 | Migration — Other | Identity → David Dooley |
| ENT-3746 | Cloud Admin — Other | Identity → David Dooley |
| ENT-3745 | Cloud Admin — Other | Identity → David Dooley |
| ENT-3738 | Cloud Admin — Other | Identity → David Dooley |
| ENT-3737 | Cloud Admin — Other | Identity → David Dooley |
| ENT-3736 | Cloud Admin — Other | Identity → David Dooley |
| ENT-3730 | Cloud Admin — Other | Identity → David Dooley |

## Notes on data quality

- For 100% of the 100+ recent ENT tickets enriched, the **assignee/priority/components** fields were captured directly from `mcp__atlassian__get_jira_issue` with `extra_fields=["assignee","priority","components","labels","reporter","duedate","fixVersions","parent"]`.
- Two ticket keys (ENT-351, ENT-293) were not retrievable via the rich get; ENT-293 *is* retrievable via `jira workitem search` (it appears in the open Blocker list).
- The recent-inbox set deliberately **excludes** Loom-only, Confluence-only, and JSM-only product items from the CoreEng pillar columns — those are routed but not owned by CoreEng.
