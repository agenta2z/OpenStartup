# CoreEng Organization Map — v3 (verified 2026-05-15)

> Engineering pillars that absorb Enterprise (ENT) demand. **Pillar DRIs are taken verbatim from Confluence page 7012411386 (Ke Wang, May 12, 2026)** and cross-checked against the FY26 onboarding hubs in the `CoreEngineering` Confluence space.

## Engineering vs TPM — clear separation

```
┌────────────────────────────────────────────────────────────────────┐
│  ENTERPRISE (the demand side)                                       │
│  ───────────────────────────                                        │
│  Enterprise DRI (customer voice): Filiberto Selvas                  │
│  Source-of-truth list: Confluence page 5619065001 (TRUSTED space)   │
│  Captured in Jira project: ENT                                      │
└──────────────────┬─────────────────────────────────────────────────┘
                   │ (curated and reviewed monthly by TPM line)
                   ▼
┌────────────────────────────────────────────────────────────────────┐
│  TPM / Program Management line  (NOT engineering)                   │
│  ──────────────────────────────                                     │
│  • Levon Esibov   — Head of TPgM (LT reviewer)                      │
│  • Kangrong Yan   — TPM (LT reviewer)                               │
│  • Ashish Consul  — Head of TPM, CoreEng                            │
│  • Ke Wang        — MUSTWIN DRI (this is the role our analysis      │
│                     emulates: maps ENT → engineering pillars)       │
└──────────────────┬─────────────────────────────────────────────────┘
                   │ (commits "ENT50" backlog to engineering)
                   ▼
┌────────────────────────────────────────────────────────────────────┐
│  CORE ENGINEERING — the supply side                                 │
│  Pillar DRIs (verbatim from page 7012411386, 2026-05-12)            │
│                                                                     │
│  ┌─────────────────────┐  ┌────────────────────┐                    │
│  │ Identity            │  │ Tenant & Sharding  │                    │
│  │ • Kahren Tevosyan   │  │ Platform (TSP)     │                    │
│  │ • Dushyant Gill     │  │ • Kahren Tevosyan  │                    │
│  │ • David Dooley      │  │ • Corey Johnston   │                    │
│  │ • Romulus Apolzan   │  │ • Harpreet S. Juneja                    │
│  └─────────────────────┘  │ • Todd Bowles      │                    │
│                           └────────────────────┘                    │
│  ┌─────────────────────┐  ┌────────────────────┐                    │
│  │ Tenant Data         │  │ Compute            │                    │
│  │ Platform (TDP/CDP)  │  │ • Kayley Ma        │                    │
│  │ • Vinod Kumar       │  │ (per template      │                    │
│  │ • Lin Chen          │  │ 5696752671)        │                    │
│  │ • Alex Grach        │  └────────────────────┘                    │
│  └─────────────────────┘                                            │
│                                                                     │
│  ┌─────────────────────┐  ┌────────────────────┐                    │
│  │ Reliability (SRE)   │  │ Networking         │                    │
│  │ • Arun Jayandra     │  │ • Mathrubootham    │                    │
│  │   (Org HoE)         │  │   Janakiraman      │                    │
│  └─────────────────────┘  └────────────────────┘                    │
│                                                                     │
│  ┌─────────────────────┐  ┌────────────────────┐                    │
│  │ FinOps              │  │ Deployment Verif.  │                    │
│  │ • Tom Cutajar       │  │ + CloudSec         │                    │
│  │   (Org HoE)         │  │ • Vinod Kumar      │                    │
│  └─────────────────────┘  └────────────────────┘                    │
│                                                                     │
│  Data Governance DRI: Anand Balachandran, Sarah Brown               │
│  (per template 5696752671)                                          │
└────────────────────────────────────────────────────────────────────┘
```

## Pillar inventory (machine-readable)

| Pillar | Engineering DRIs (verified 2026-05-15) | Sub-orgs / sub-teams | Confluence Space | Source citation |
|---|---|---|---|---|
| **Identity** | Kahren Tevosyan, Dushyant Gill, David Dooley, Romulus Apolzan | AuthN/AuthZ (incl. Swaminathan Pattabiraman lead), SCIM, SSO, Lifecycle Governance, Org/Site model | `CoreEngineering` | page 7012411386, page 3511325163 |
| **Tenant & Sharding Platform (TSP)** | Kahren Tevosyan, Corey Johnston, Harpreet Singh Juneja, Todd Bowles | Tenant Platform, Shard Platform, Backup/Restore (BRIE has historically rolled here) | `CoreEngineering` | page 7012411386, page 5696752671, onboarding hub 6258947723 |
| **Tenant Data Platform (TDP / CoreData)** | Vinod Kumar, Lin Chen, Alex Grach | TDP SQL (TiDB-based), Data Pipelines, ADR (Atlassian Disaster Recovery), Micros Data Platform | `CoreEngineering`, `DAP` | page 7012411386, page 5696752671, page 6490759912 |
| **Compute** | Kayley Ma | Compute Platform | `CoreEngineering` | page 5696752671 |
| **Reliability** | Arun Jayandra (Org HoE), Prashant Ghosal (FY25Q1 co-lead) | SRE (regional) | `CoreEngineering` | onboarding hub; ops review 6960490371 |
| **Networking** | Mathrubootham Janakiraman | Network IES | `CoreEngineering` | onboarding hub; ops review 6960490371 |
| **FinOps** | Tom Cutajar | ENG-FinOps-Software | `CoreEngineering` | onboarding hub 6258849065 |
| **Deployment Verification / CloudSec / ADR** | Vinod Kumar (Org HoE) | sub-orgs of CDP | `CoreEngineering` | onboarding hubs 6258848690, 6259185146 |
| **Engineering Excellence** | Jason Yang (per FY25Q1, not re-verified for FY26) | unverified | `CoreEngineering` | page 4295662666 |

### Names called out in May 2026 ops metrics review (page 6960490371)
Pillar leaders tracked for incident TTD/TTR: Arun Jayandra, Kahren Tevosyan, Mathrubootham Janakiraman, Mitica Manu, Vinod Kumar.

## Roles outside the engineering pillars (still required for the mapping)

| Role | Person | Source |
|---|---|---|
| MUSTWIN Owner (LT reviewer) | Levon Esibov | page 5696752671 |
| Co-reviewer (LT) | Kangrong Yan | page 7012411386 |
| MUSTWIN DRI (TPM) | **Ke Wang** | page 5696752671 |
| Enterprise DRI (customer voice) | Filiberto Selvas | page 5696752671, page 7012411386 |
| Data Governance DRI | Anand Balachandran, Sarah Brown | page 5696752671 |

## What changed vs prior local docs

* Prior `01_org_structure_leadership.md` and `00_index.md` listed **Ashish Consul as VP Core Engineering** and **Levon Esibov as EVP Engineering**. Both are inaccurate role labels — both lead **TPM**, not engineering. (Verified via `org-tree` titles 2026-05-15: Levon = Head of TPgM, Ashish = Head of TPM CoreEng.)
* Prior docs implied Ke Wang sits "above" the engineering pillars. He is a **TPM (MUSTWIN DRI)** whose job is to map and review demand — exactly the role this entire research effort is trying to perform.
* The actual pillar DRIs above were extracted **verbatim from Ke Wang's own May 2026 review** — this is as authoritative as it gets.
