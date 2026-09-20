# 01 · Organization — who owns what
*(verified 2026-05-15)*

> Pillar DRIs are taken **verbatim from Confluence page 7012411386** (Ke Wang, *FY26 (May) ENT-CoreEng Execution Review*, dated 2026-05-12) and cross-checked against the FY26 onboarding hubs in the `CoreEngineering` Confluence space and live `org-tree` job titles.

## 1. The three sides — Enterprise demand, TPM line, Engineering supply

```
┌──────────────────────────────────────────────────────────────────────┐
│  ENTERPRISE — the demand side                                         │
│  ───────────────────────────                                          │
│  Enterprise DRI (customer voice): Filiberto Selvas                    │
│  Source-of-truth list:           Confluence 5619065001 (TRUSTED)      │
│  Captured in Jira project:       ENT  (https://hello.atlassian.net)   │
└──────────────────────┬───────────────────────────────────────────────┘
                       │ (curated and reviewed monthly)
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  TPM / Program Management line  (NOT engineering)                     │
│  ──────────────────────────────                                       │
│  • Levon Esibov   — Head of TPgM, MUSTWIN Owner (LT reviewer)         │
│  • Kangrong Yan   — TPM, co-LT-reviewer                               │
│  • Ashish Consul  — Head of TPM, CoreEng                              │
│  • Ke Wang        — MUSTWIN DRI (the role this analysis emulates)     │
└──────────────────────┬───────────────────────────────────────────────┘
                       │ (commits "ENT50" backlog to engineering)
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  CORE ENGINEERING — the supply side  (DRIs verbatim from page         │
│  7012411386, 2026-05-12)                                              │
│                                                                        │
│  Identity                       Tenant & Sharding Platform (TSP)      │
│  • Kahren Tevosyan              • Kahren Tevosyan                     │
│  • Dushyant Gill                • Corey Johnston                      │
│  • David Dooley                 • Harpreet Singh Juneja               │
│  • Romulus Apolzan              • Todd Bowles                         │
│                                                                        │
│  Tenant Data Platform (TDP/CDP) Compute                               │
│  • Vinod Kumar                  • Kayley Ma                           │
│  • Lin Chen                                                           │
│  • Alex Grach                                                         │
│                                                                        │
│  Reliability                    Networking                            │
│  • Arun Jayandra (Org HoE)      • Mathrubootham Janakiraman           │
│                                                                        │
│  FinOps                         Deployment Verification / CloudSec    │
│  • Tom Cutajar (Org HoE)        • Vinod Kumar (Org HoE)               │
│                                                                        │
│  Data Governance DRIs: Anand Balachandran, Sarah Brown                │
└──────────────────────────────────────────────────────────────────────┘
```

## 2. Pillar inventory (machine-readable)

| Pillar | Engineering DRIs (verified 2026-05-15) | Sub-orgs / sub-teams | Primary Confluence space | Source citation |
|---|---|---|---|---|
| **Identity** | Kahren Tevosyan, Dushyant Gill, David Dooley, Romulus Apolzan | AuthN / AuthZ (Swaminathan Pattabiraman lead), SCIM, SSO, Lifecycle Governance, Org/Site model, Audit Log Platform (ALP), FedRAMP / GovCloud | `CoreEngineering` | page 7012411386, page 3511325163 |
| **Tenant & Sharding Platform (TSP)** | Kahren Tevosyan, Corey Johnston, Harpreet Singh Juneja, Todd Bowles | Tenant Platform, Shard Platform, Backup-Restore-Import-Export (BRIE) | `CoreEngineering` | page 7012411386, page 5696752671, hub 6258947723 |
| **Tenant Data Platform (TDP / CoreData)** | Vinod Kumar, Lin Chen, Alex Grach | TDP-SQL (TiDB-based), Data Pipelines, ADR (Atlassian Disaster Recovery), Micros Data Platform, Encryption / BYOK platform | `CoreEngineering`, `DAP` | page 7012411386, page 5696752671, page 6490759912 |
| **Compute** | Kayley Ma | Compute Platform | `CoreEngineering` | page 5696752671 |
| **Reliability** | Arun Jayandra (Org HoE) | SRE (regional) | `CoreEngineering` | onboarding hubs; ops review 6960490371 |
| **Networking** | Mathrubootham Janakiraman | Network IES | `CoreEngineering` | onboarding hubs; ops review 6960490371 |
| **FinOps** | Tom Cutajar | ENG-FinOps-Software | `CoreEngineering` | onboarding hub 6258849065 |
| **Deployment Verification / CloudSec / ADR** | Vinod Kumar (Org HoE) | sub-orgs of CDP | `CoreEngineering` | onboarding hubs 6258848690, 6259185146 |
| **Engineering Excellence** | (FY26 leadership not re-verified) | (legacy: Jason Yang per FY25Q1) | `CoreEngineering` | page 4295662666 |

### Names called out in the May 2026 ops metrics review (page 6960490371)
Pillar leaders tracked for incident TTD/TTR: **Arun Jayandra, Kahren Tevosyan, Mathrubootham Janakiraman, Mitica Manu, Vinod Kumar.**

## 3. Roles outside the engineering pillars (still required for the mapping)

| Role | Person | Source |
|---|---|---|
| MUSTWIN Owner (LT reviewer) | Levon Esibov | page 5696752671 |
| Co-reviewer (LT) | Kangrong Yan | page 7012411386 |
| MUSTWIN DRI (TPM) | **Ke Wang** | page 5696752671 |
| Enterprise DRI (customer voice) | Filiberto Selvas | page 5696752671, page 7012411386 |
| Data Governance DRI | Anand Balachandran, Sarah Brown | page 5696752671 |

## 4. Out-of-CoreEng but still routed through MUSTWIN

These pillars live **outside** Core Engineering but consistently absorb ENT tickets and therefore appear in this mapping for routing purposes only:

| External pillar | Typical ticket family | Owner pattern (per assignee data) |
|---|---|---|
| **Atlassian Guard / DLP** | Information Protection — DLP, Shadow IT controls, MAM | Audrey Garcia, Rishabh Jain, Sandeep Dmello, Rob Bissett, Jemma Swaak |
| **Rovo / AI Platform** | Rovo Chat, Rovo MCP, Rovo Studio Agents, Admin Controls, Insights | Ashwini Rattihalli, Shravan Suri, Sushant Koshy, Jemma Swaak, Griffin Jones, Ben Costello |
| **Confluence (product)** | Whiteboards, Compliance & Security, Editor | Sree Das, Sam Lucas, Melanie Zhao, Marie Casabonne, Laura Mehrkens, Jonno Katahanas |
| **Jira (product)** | Workflows, Plans, Custom Fields, Performance | Sahibi Miranshah, Carol Low, Tina Ling, Dmitry Melikov |
| **JSM** | Assets / CMDB / Operations | Sonia Mahabir Gandhi, Kaushik Mitra, Mike Jones, Muthukumar Ravishankar |
| **Loom** | Governance, Org policies, Domain sharing | Kristen Waters |
| **Atlas / Project** | Project mandatory fields, Team contributors | (Atlas team) |
| **Ecosystem Platform** | Apps, ViewIssueModal entry points | (Ecosystem team) |

## 5. What was wrong before vs. now

| Prior claim (in flat files / `corrected_master_mapping.md`) | Live truth (2026-05-15) | Source |
|---|---|---|
| "EVP Engineering: Levon Esibov" | Levon Esibov is **Head of TPgM** (TPM line) | `org-tree --email lesibov@atlassian.com --include-profile-title` |
| "VP Core Engineering: Ashish Consul" | Ashish Consul is **Head of TPM, CoreEng** (TPM line) | Same org-tree pull |
| "Identity & IAM owner: Prashant Ghosal" | Identity DRIs are **Kahren Tevosyan, Dushyant Gill, David Dooley, Romulus Apolzan** (Prashant was a FY25Q1 Reliability co-lead, not the Identity owner) | page 7012411386 |
| "BRIE owner: Lakshmi Behl" | BRIE rolls under **TSP** (DRIs Corey Johnston et al.); Lakshmi Behl is the recurring **assignee** on BRIE-family tickets, not the pillar owner | page 7012411386 + Jira assignee data |
| "Encryption / BYOK owner: Greg Zaney (Coral team)" | BYOK family lives in **TDP** (DRI Vinod Kumar) per Ke Wang's May 2026 mapping | page 7012411386 |
| "ALP owner: Akshay Nambiar" | ALP rolls under **Identity** (DRI Dushyant Gill) | page 7012411386 |
| "Compliance / RegInd owner: Wayne Yim" | Compliance / FedRAMP / GovCloud rolls under **Identity** (DRI Dushyant Gill) | page 7012411386 |
| "FinOps owner: Ke Wang" | FinOps DRI is **Tom Cutajar**; Ke Wang is the **MUSTWIN DRI (TPM)** | page 5696752671, onboarding hub 6258849065 |

The names Prashant Ghosal, Lakshmi Behl, Greg Zaney, Akshay Nambiar, Wayne Yim, Sirisha Pendem, Harpreet Singh Juneja **do** appear in legitimate roles around CoreEng (e.g., Harpreet is a verified TSP DRI; Lakshmi is the recurring BRIE assignee; Sirisha leads Sandbox engineering historically). What was wrong was attaching them to *pillar-owner* labels they don't hold per the May 2026 leadership.
