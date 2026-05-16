# Currently OPEN Blocker / Critical ENT Issues — v3 (live, 2026-05-15)

**Live JQL** (executed via TWG, 2026-05-15 06:56 PT):
```
project = ENT AND priority in (Blocker, Critical) AND statusCategory != Done
```
Result: **21 open issues**.

> This is the authoritative "right now" list. The previous docs in this folder mislabeled many Minor tickets as P0/P1; this list contains only items where Jira's `priority` field is **Blocker** or **Critical**.

| # | Key | Priority | Component | Pillar | DRI / Owner | Summary |
|---|---|---|---|---|---|---|
| 1 | [ENT-3881](https://hello.atlassian.net/browse/ENT-3881) | Blocker | Rovo / AI - Other | AI ↔ Identity (Trust) | Ashwini Rattihalli (assignee), Dushyant Gill (Trust scope) | DocuSign — Rovo HIPAA compliance blocking AI adoption (customer evaluating Glean) |
| 2 | [ENT-3878](https://hello.atlassian.net/browse/ENT-3878) | Blocker | Rovo / AI - Product - Chat | AI | Shravan Suri | Rovo chat unable to modify or delete existing Google Calendar events |
| 3 | [ENT-3868](https://hello.atlassian.net/browse/ENT-3868) | **Critical** | Jira — Platform — Performance | TDP ↔ Jira Platform | Dmitry Melikov | API Rate Limiting — systemic across 6+ enterprise customers, impacts migration |
| 4 | [ENT-3853](https://hello.atlassian.net/browse/ENT-3853) | Blocker | Rovo Chat | AI | (Rovo team) | [CES-142317] Rovo chat — incomplete page retrieval and incorrect values from page subtree |
| 5 | [ENT-3807](https://hello.atlassian.net/browse/ENT-3807) | Blocker | Rovo / AI - Other | AI | Ben Costello | Agent automation throttling with minimal visibility/workarounds |
| 6 | [ENT-3806](https://hello.atlassian.net/browse/ENT-3806) | Blocker | Rovo Search | AI | (Rovo Search) | Embedded images in Jira/Confluence not consumable by Rovo Search/Agent |
| 7 | [ENT-3721](https://hello.atlassian.net/browse/ENT-3721) | Blocker | Audit — ALP | Identity (ALP) | Dushyant Gill | Embeddable audit logs for Confluence (ENT50) |
| 8 | [ENT-2883](https://hello.atlassian.net/browse/ENT-2883) | Blocker | Audit — ALP | Identity (ALP) | Dushyant Gill | Embeddable audit logs for Jira/JSM (ENT50) |
| 9 | [ENT-2745](https://hello.atlassian.net/browse/ENT-2745) | Blocker | Confluence — Compliance & Security | Identity (cross-cutting Trust) | Michael Andreacchio | Virtual Private / Isolated cloud (ENT50 FY26) |
| 10 | [ENT-2647](https://hello.atlassian.net/browse/ENT-2647) | Blocker | Encryption — BYOK | TDP | Vinod Kumar | BYOK Encryption for Compass |
| 11 | [ENT-2035](https://hello.atlassian.net/browse/ENT-2035) | Blocker | Encryption — BYOK | TDP | Vinod Kumar | Customer-managed keys for JPD |
| 12 | [ENT-2022](https://hello.atlassian.net/browse/ENT-2022) | Blocker | Encryption — BYOK | TDP | Vinod Kumar | Customer-managed key encryption for Platform Apps |
| 13 | [ENT-1958](https://hello.atlassian.net/browse/ENT-1958) | Blocker | Encryption — BYOK / AWS-XKS | TSP, TDP | Corey Johnston / Vinod Kumar | AWS-XKS — non-AWS key store support (ENT50 FY28) |
| 14 | [ENT-1666](https://hello.atlassian.net/browse/ENT-1666) | Blocker | Information Protection — Guard | Guard ↔ Identity | (Guard team) | Policy-based exfiltration controls (DC) |
| 15 | [ENT-1445](https://hello.atlassian.net/browse/ENT-1445) | Blocker | Trust Foundations — FedRAMP | Identity | Dushyant Gill | FedRAMP Tailored for Atlassian Access |
| 16 | [ENT-381](https://hello.atlassian.net/browse/ENT-381) | Blocker | Atlas / Project | (Atlas — outside CoreEng) | Atlas team | Easy way to target teams that will/are contribute to a feature |
| 17 | [ENT-376](https://hello.atlassian.net/browse/ENT-376) | Blocker | Atlas / Project | (Atlas — outside CoreEng) | Atlas team | Move mandatory fields to top of details slide-out |
| 18 | [ENT-293](https://hello.atlassian.net/browse/ENT-293) | Blocker | Trust Foundations | Identity, TSP | Dushyant Gill / Corey Johnston | US Classified / Top Secret / IL6 / Disconnected / Airgapped |
| 19 | [ENT-151](https://hello.atlassian.net/browse/ENT-151) | Blocker | BRIE | TSP | Corey Johnston | Export all of my cloud data for long-term storage in a "readable format" |
| 20 | [ENT-98](https://hello.atlassian.net/browse/ENT-98) | Blocker | Trust Foundations — GovCloud | Identity | Dushyant Gill | IL5 (DoD Impact Level 5) — ENT50 FY28 |
| 21 | [ENT-80](https://hello.atlassian.net/browse/ENT-80) | Blocker | Trust — Private Cloud | Identity, TSP | Dushyant Gill / Corey Johnston | Private Cloud |

## Pillar load distribution (open Blocker/Critical only)

| Pillar | # of open Blocker/Critical | Notes |
|---|---|---|
| **Identity** (incl. ALP, Trust, FedRAMP) | 8 | The single largest absorber — owns audit logs, FedRAMP, IL5/6, Private Cloud Trust scope |
| **TDP** (Encryption / BYOK) | 4 | The BYOK family + adjacent CMK |
| **TSP** (with Identity overlap) | 5 | BRIE export, AWS-XKS, IL6, Private Cloud, Isolated Cloud |
| **AI / Rovo** | 6 | DocuSign HIPAA, Calendar agent, Page Subtree, Embedded images, Throttling, Page subtree retrieval |
| **Atlas / Other** | 2 | ENT-376, ENT-381 — outside CoreEng |
| **Guard** | 1 | Exfiltration controls (DC) |

> Some items are dual-pillar; counts overlap. Total unique tickets = 21.

## Suggested next-step Triage actions (TPM perspective)

1. **ENT-3881 (DocuSign / Rovo HIPAA)** — confirm with Filiberto Selvas + Ashwini Rattihalli that this is on the May ENT-CoreEng Execution Review (page 7012411386). It is currently **not** in the FY26 ENT50, but customer escalation level may warrant adding.
2. **BYOK family (ENT-1958, 2022, 2035, 2085, 2647, 3099)** — TDP DRI Vinod Kumar should consolidate status into one Open Issues row in MUSTWIN; ENT-2085 already has a tracked escalation (May 2026 review entry).
3. **ALP embeddability (ENT-2883, ENT-3721)** — Identity DRI Dushyant Gill — check if these belong on the ENT50 FY26 vs FY27 column (currently neither).
4. **ENT-3868 (API rate limiting — Critical)** — escalate to TDP + Jira Platform — only Critical-priority item open in ENT.
5. **ENT-2745 (Isolated Cloud — Blocker)** — already on ENT50 FY26; confirm Identity + TSP joint plan-of-record status.
