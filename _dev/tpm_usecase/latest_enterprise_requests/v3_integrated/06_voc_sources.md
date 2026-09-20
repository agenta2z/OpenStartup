# 06 · Voice-of-Customer Source Catalog
*(consolidated 2026-05-15 from prior `04_confluence_voc_enterprise_context.md` + new pulls)*

> When asking "where does the enterprise voice live?", these Confluence pages are the **upstream sources** that feed into the ENT Jira project, the ENT50 commit register, and the MUSTWIN review. They are grouped by the Confluence space they live in.

## Space overview

| Confluence space | Approx pages relevant to enterprise demand | Role |
|---|---|---|
| **`CoreEngineering`** | ~20 | The supply-side narrative: pillar plans, MUSTWIN reviews, FY26 ENT50 list, ops metrics |
| **`TRUSTED`** (Trust & Reliability) | ~20 | Trust foundations / High-Touch roadmap / sovereign cloud plans |
| **Enterprise Readiness** (cross-space tag) | ~20 | Enterprise-readiness program: Loom migration risks, Hot-Ones playbook, AI access controls |
| **ENT50 / Priority** (cross-space tag) | ~15 | The commit list and its monthly triage history |

## Anchor pages (the canonical few you should always have open)

| Page ID | Title | Why it matters |
|---|---|---|
| **5861641112** | FY26 ENT50 List - CoreEng | The commit register. 25 named ENT items split across FY26 / FY27 / FY28. |
| **7012411386** | FY26 (May) ENT-CoreEng Execution Review | Most recent monthly MUSTWIN. Authoritative pillar DRI roster. |
| **5696752671** | FY26 Enterprise MUSTWIN Monthly Review Template | The 4-section format for the monthly review. |
| **5319794175** | MUSTWIN CoreEng FY26 Enterprise Plan | Deliverables & staffing. |
| **5619065001** | High-Touch Roadmap → ENT50 Source of Truth (TRUSTED space) | Where the enterprise CSM voice gets compiled. |
| **5848788720** | Principles & Rules for the ENT50 Monthly Triage Process | The governance protocol behind MUSTWIN. |
| **6960490371** | CoreEng May 2026 Ops Metrics Review | Lists the engineering pillar leaders tracked for incident TTD/TTR. |
| **6884917799** | The New Eval Paradigm: From Construction to Evaluation | Ke Wang's Artifact Review framing — the format expectation for documents like this one. |
| **6786483776** | The Agentic Engineering Shift: From Implementation to Intent | Companion to 6884917799. |

## Enterprise Readiness (program-level pages)

| Page ID | Title | What it captures |
|---|---|---|
| 6893701886 | Loom Migration to Atlassian Platform: Risks to Enterprise Readiness | Why Loom-governance ENT items are appearing |
| 6871719042 | Enterprise HOT ONES: Guidelines | The "hot one" playbook — escalation protocol |
| 6832979969 | AI Access Controls Email — Enterprise Engagement | Why MCP cluster + Rovo Trust items have surged |
| 6931283418 | Enterprise Grade Golden Path Reimagined | Vision document tying ENT50 themes together |

## ENT50 / Priority (governance pages)

| Page ID | Title | What it captures |
|---|---|---|
| 6902613048 | ENT50 in FY27 KR1 | KR-1 commitments tied to ENT50 |
| 6931301330 | ENT50 in FY27 KR3 | KR-3 commitments tied to ENT50 |
| 5848788720 | Principles & Rules for the ENT50 Monthly Triage Process | How items get on / off the list |

## CoreEngineering space — pillar onboarding hubs

These hubs were the secondary source for the verified pillar DRIs in [`01_organization.md`](01_organization.md).

| Page ID | Pillar |
|---|---|
| 6258947723 | Tenant Platform onboarding |
| 6258849065 | FinOps onboarding |
| 6258848690 | Compute / Deployment Verification onboarding |
| 6259185146 | CloudSec onboarding |
| 6490759912 | Tenant Data Platform (CDP) onboarding |
| 4295662666 | Engineering Excellence (legacy FY25 reference) |
| 3511325163 | Identity onboarding |

## TRUSTED space (Trust & Reliability)

These pages provide the sovereign-cloud / FedRAMP / Trust-Foundations narrative that backs the IDN-pillar Blockers (FedRAMP Tailored, IL5, IL6, Isolated Cloud, etc.). The full list of 20 pages is preserved in `data/voc_trusted_index.txt` (see also the prior local doc `04_confluence_voc_enterprise_context.md` for the historical snapshot).

## How to refresh this catalog

Use `scripts/twg confluence pages search` against any of these queries:

```bash
scripts/twg -s hello -o json confluence pages search \
  --query 'space = CoreEngineering AND title ~ "ENT" ORDER BY lastModified DESC' --first 30

scripts/twg -s hello -o json confluence pages search \
  --query 'space = TRUSTED AND title ~ "Trust" ORDER BY lastModified DESC' --first 30

scripts/twg -s hello -o json confluence pages search \
  --query 'creator = "712020:27e1af5d-30e9-4112-8806-66ee62f9277a" ORDER BY lastModified DESC' --first 30
# (Ke Wang's recent docs)
```
