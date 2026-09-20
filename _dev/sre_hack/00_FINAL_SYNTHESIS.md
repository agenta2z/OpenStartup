# Deep Investigation: Vladimir Grebenik & Larry Zhu — Repos, Services, Yearly Goals

**Investigator:** Rovo Dev (multi-agent deep dive)
**Date:** 2026-05-01
**Method:** TWG CLI (`scripts/twg`) + Bitbucket API + 3 parallel General-Purpose subagents
**Companion docs in this folder:**
- `30_vladimir_deep_dive.md` — Vladimir's repos, RFCs, projects (376 lines)
- `31_larry_deep_dive.md` — Larry's 14 repos, 713 PRs, FY26 goals (139 lines)
- `32_org_and_goals.md` — Kangrong Yan org tree + FY26 pillar goals (127 lines)
- Raw JSON dumps `01_*` … `22_*` for reproducibility

---

## TL;DR

| | Vladimir Grebenik | Larry Zhu |
|---|---|---|
| **AAID** | `712020:f6ea54ea-42fa-4cfe-adbd-d57b5f5212f9` | `712020:0f32cf56-bb55-446d-b287-01a978c74968` |
| **Email** | vgrebenik@atlassian.com | lzhu3@atlassian.com |
| **Title** | Senior Principal Architect, **Engineering – Multicloud** | Senior Principal Engineer, **Atlassian Cloud Storage Engineering** |
| **Reports to** | Kangrong Yan → Taroon Mandhana → Mike Cannon-Brookes | Vinod Kumar → Kangrong Yan → Taroon Mandhana → Mike Cannon-Brookes |
| **Pillar** | Logging / Observability / Splunk / Multicloud (GCP) | KITT (Kubernetes) / GCP enablement / AMP Access / Zero Trust Containers |
| **FY26 north star** | Splunk Leap multi-region + Logging Governance + Tiered Storage | KITT-in-GCP + KNative serverless + Forge Compute Zero Trust |
| **Primary repos** | `activation` (PROVCORE), Crossplane/Argo logging infra (RFC stage) | `poco`, `keyserver-go`, `kitt-runbook-cli`, `atlaskube-cli`, `gcp-kitt`, `kitsune` |
| **Key yearly goal owned** | Project ATLAS-123125 (Q4 Obs Logging Governance), ATLAS-123127 (Q4 Splunk Multi Region) — both linked to **ATLAS-98101** *L3.OBS.O1.KR2 Logging Efficiency* | **ATLAS-89196** *CENG.GCP.03 KITT Enablement in GCP*, **ATLAS-89197** *Cluster Lifecycle*, **ATLAS-103015** *KNative Adoption* |

---

## 1. Org Position (Both report into the same VP, Kangrong Yan)

```
Mike Cannon-Brookes (CEO)
└── Taroon Mandhana (CTO – AI & Teamwork)
    └── Kangrong Yan  (Head of Core Engineering)
        ├── Vladimir Grebenik  ★  (Sr Principal Architect — Engineering Multicloud)
        ├── Arun Jayandra        (Cell Platform / Reliability — owns Observability sub-team)
        ├── Kahren Tevosyan      (Identity)
        ├── Mathrubootham Janakiraman (Networking)
        ├── Mitica Manu          (Cloud FinOps)
        └── Vinod Kumar          (Atlassian Cloud Storage Engineering)
            └── Larry Zhu  ★    (Sr Principal Engineer — KITT / GCP storage / Zero Trust)
```

Both are senior individual contributors; **Vladimir is the architect for Logging/Observability across Multicloud**, **Larry is the principal engineer for KITT-on-GCP and the Zero-Trust Forge Containers programme**.

---

## 2. Vladimir Grebenik — Deep Dive

### 2.1 Strategic theme — "Splunk Leap & Logging Governance for FY26"
Vladimir is leading three converging streams that together modernise Atlassian's logging platform:

1. **Logging Governance** — data contracts, PII guidelines, log-volume quotas. Linked to corporate KR
   `ATLAS-98101` *[L3.OBS.O1.KR2] Improve Atlassian's logging efficiency to contain growth within contractual limits in FY26 (P90 daily observability-funded ingest < 1.65 M GB)*.
2. **Splunk Leap** — multi-region Splunk redesign (per-region isolation + federated search) and dual-write LSP migration. Owns Project `ATLAS-123127` *[Q4] Splunk Multi Region Strategy*.
3. **Tiered Storage + GitOps** — Structured logging with hot/warm/cold tiers, ArgoCD + Crossplane-managed Splunk infrastructure, phased GitOps cutover.

### 2.2 Project keys he owns
| Key | Title | State | Linked goal |
|---|---|---|---|
| ATLAS-123125 | [Q4] Observability Logging Governance: Strategy and Execution Plan | Pending | ATLAS-98101 (L3.OBS.O1.KR2) |
| ATLAS-123127 | [Q4] Splunk Multi Region Strategy | Pending | (umbrella) |
| ATLAS-117780 | Investigate Artifactory Deployment in GCP | Completed | — |

### 2.3 Confluence (selected — full list in `30_vladimir_deep_dive.md`)
- **RFC: Regional Splunk Leap Architecture (Per‑Region Isolation + Federated Search)**
- **RFC: Migration to Regional Splunk Leap (LSP Dual‑Write + Cutover)**
- **RFC: Structured Logging + Tiered Storage**
- **Logging Platform North Star: Architecture & Execution**
- *Splunk Leap DACI: How high to Leap?*, *FY26Q4 Logging Plan*, *Phased GitOps Cutover — Logging Infrastructure*, *Logical Cloud Security Architecture*, *GCP Adoption Program*, *TWG Logging one pager – Jan 2026*.

### 2.4 Bitbucket / code activity
Vladimir's contribution model is **architect / RFC author** rather than heavy code committer. His authored PRs in the last 180d are limited (one PROVCORE-2980 PR in `activation`). His "services" are therefore the **logging platform** as a whole rather than a single repo — owned operationally by the Observability sub-team (under Vidhyashankar Balasubramaniyan / Arun Jayandra), but architecturally directed by Vladimir.

Likely Bitbucket projects in the logging perimeter (named in his RFCs):
- **Splunk** stack & Leap controller repos
- **LSP (Logging Search Platform)** dual-write components
- Crossplane + Helm + Kitt manifests for the Splunk fleet
- ArgoCD application sets for logging
- Jira FinOps slow-query optimisations (FINOPS-12052/12053/11266)

### 2.5 Public-API / website-services touchpoints
No direct PRs on `public-api` or website-services. His scope is **observability infrastructure**, not the customer-facing public API surface.

---

## 3. Larry Zhu — Deep Dive

### 3.1 Strategic theme — "KITT to GCP, KNative serverless, Zero-Trust containers"
Larry is the principal engineer behind three FY25/FY26 platform programmes:

1. **KITT in GCP** (`ATLAS-89196`, `ATLAS-89197`) — lifting Atlassian's internal Kubernetes platform onto Google Cloud, including cluster lifecycle, fleet manager, GKE control-plane upgrades.
2. **KNative Adoption** (`ATLAS-103015`) — replacing ECS-style batch with Knative-based serverless for Forge / canvas-server / async invocation; collaboration with Diego Cardenas Barragan.
3. **Forge Compute Zero Trust** (`ATLAS-92799` Zero Trust for Forge Containers, `ATLAS-115402` Forge Compute Bluebird Dogfooding, `ATLAS-115999` WebCLI EAP) — sandboxed multi-tenant container execution on KITT.

He also delivers a vertical of **GCP KITT for Confluence** (`ATLAS-83835`) — onboarding Confluence onto the new KITT/GCP stack (M2 just shipped, M3 in flight with PSAPI + SP provisioner).

### 3.2 All Bitbucket repos with PR activity (verified through the Bitbucket REST API)

| Slug | Bitbucket project | Description / role | PR count |
|---|---|---|---|
| `atlassian/poco` | **CloudSec (CS)** | Policy-compliance orchestration; FedRAMP/compliance automation | 381 |
| `atlassian/keyserver-go` | **CloudSec (CS)** | "Code for the `asap` plugin for Atlas CLI and the `keyserver` Micros service which manages the ASAP buckets" | 298 |
| `atlassian/kitt-runbook-cli` | **CloudSec (CS)** | Kubernetes runbook CLI (Go); created Mar 2026 | 15 |
| `atlassian/gcp-kitt` | KITT/GCP (TS) | GCP KITT deployment; vulnerability remediations | 6 |
| `atlassian/public-api` | Platform | API service enhancements | 2 |
| `atlassian/mkr` | MKR (Modern Kubernetes Runtime) | Temporal migration; deprecate batch jobs / terraform-job KSA | 2 |
| `atlassian/zero-trust-containers` | Forge / ZTC | Feature flags; K8s class scaffolding for ZTC | 2 |
| `atlassian/atlas-cli` | **Atlas-CLI (ATLASCLI)** | Plugin onboarding (kitt-runbook-cli) | 1 |
| `atlassian/atlaskube-cli` | **KITT** | Go CLI for managing K8s services on AtlasKube/KITT; AMP proxy | 1 |
| `atlassian/forge-containers-refapp` | Forge Compute (JS) | ZTC reference app deployment fixes | 1 |
| `atlassian/kubeauth` | KITT | K8s authentication module (KUBE-10033) | 1 |
| `atlassian/kitsune` | KITT | KNative namespace isolation (ZTP-138) | 1 |
| `atlassian/micros-server` | **Micros Platform (MICROS)** | "Codebase for `micros`, the orchestrator of the PaaS" — Flink job audit logging | 1 |
| `atlassian/atlassian-resource-identifier` | **Atlassian TAG (TAG)** | ARI specification & registries — Service ARI registration (TSPCPT-2486) | 1 |

**Total: 14 repos · 713 PRs · 679 days continuous activity (~2 PRs/day).**

### 3.3 AMP (Atlassian Modern Platform) services he touches
- **amp-access** compliance controls (REPCOM-67772) – directly added compliance controls
- **atlaskube-cli** with AMP proxy integration
- **micros-server** (PaaS orchestrator) – audit-log Flink job
- **public-api** – bridges KITT-managed services into the public API surface
- **atlassian-resource-identifier** – registers Service ARIs into the Micros TAG registry

### 3.4 Notable Confluence pages (full list in `31_larry_deep_dive.md`)
- *RFC 113: ATS Token (AST)*
- *RFC 114: PIP Token (PIT)*
- *atlaskube-cli: A Go-based CLI for Managing Kubernetes Services on AtlasKube/KITT*
- *AWE and Temporal lite hosting*
- *AMP Access Control project status*
- *AMP K8s management/run-book workflow list*
- *Portable server-less road to production – directional*
- *CDP AI Native Engineering*

### 3.5 Issues that reveal services / on-call surfaces
- `K8HELP-2645` — KNative as ECS replacement in GCP
- `CLOUDSEC-4635/4684` — poco bundler / glue-job clean-up
- `CTSC-1413` — Trust Score for Staff Access to Production Systems
- `REPCOM-67772` — amp-access compliance controls
- `ETRNLS-538` — Audit-log Flink job (test) on Micros
- `TSPCPT-2486` — Register ARI for Service as a Micros resource
- `KUBE-10033` — kubeauth contributions

---

## 4. Crossover & "Services" Map (named for SRE/hack lookup)

| Service / Repo | Owner | Purpose | Related FY26 goal |
|---|---|---|---|
| Splunk Leap (multi-region, federated search) | **Vladimir** | Per-region log isolation, dual-write migration | ATLAS-123127, ATLAS-98101 |
| Tiered-storage logging + ArgoCD/Crossplane | **Vladimir** | Hot/warm/cold log tiers, GitOps cutover | ATLAS-123125 |
| `atlassian/poco` | **Larry** | Policy compliance orchestration | CloudSec / CTSC-1413 |
| `atlassian/keyserver-go` | **Larry** | ASAP key/Micros bucket lifecycle | CloudSec / FedRAMP |
| `atlassian/kitt-runbook-cli` | **Larry** | K8s runbook automation CLI | KITT in GCP (ATLAS-89196) |
| `atlassian/atlaskube-cli` | **Larry** | AtlasKube / KITT management CLI | KITT enablement |
| `atlassian/gcp-kitt` | **Larry** | GCP KITT deployment | KITT in GCP (ATLAS-89196) |
| `atlassian/kitsune` | **Larry** | KNative namespace isolation | KNative (ATLAS-103015), Forge ZTC |
| `atlassian/zero-trust-containers` & `forge-containers-refapp` | **Larry** | Forge ZTC sandbox runtime | ATLAS-92799, ATLAS-115402 |
| `atlassian/mkr` | **Larry** | Modern Kubernetes Runtime, Temporal jobs | ATLAS-115999 (WebCLI EAP) |
| `atlassian/micros-server` | (platform; **Larry** contributes) | PaaS orchestrator | Cross-pillar |
| `atlassian/public-api` | (platform; **Larry** contributes) | Public API gateway | Cross-pillar |
| `atlassian/atlassian-resource-identifier` | (TAG; **Larry** contributes) | ARI registry | Cross-pillar |

> **Public-API / website-services note:** Larry has 2 PRs into `atlassian/public-api`, but neither he nor Vladimir is the *owner* of public-API or website-services. Those pillars sit under Mathrubootham Janakiraman (Networking) per the org tree.

---

## 5. FY26 Goal Hierarchy (relevant subset of Kangrong's org)

### Observability (Vladimir's pillar)
- **ATLAS-98101** *[L3.OBS.O1.KR2]* Logging efficiency — daily ingest < 1.65 M GB *(Vladimir, top-level KR)*
- ATLAS-121795 Tier 1 Logging
- ATLAS-121676 SignalFX vs Mimir performance parity
- ATLAS-121718 OASIS / Bluebird (GCP) dashboards & alerts
- ATLAS-111393 FinOps observability data trustworthiness

### KITT / GCP (Larry's pillar)
- **ATLAS-89196** *[CENG.GCP.03]* KITT Enablement in GCP *(Larry, owner)*
- **ATLAS-89197** *[CENG.GCP.03.01]* Cluster lifecycle management *(Larry, owner)*
- **ATLAS-103015** Platform Leverage – KNative Adoption *(Larry, owner)*
- ATLAS-118771 KITT Crossplane repo restructuring
- ATLAS-124299 GKE control-plane two-step upgrade
- ATLAS-123356 GKE node-pool upgrade strategies
- ATLAS-123751 Configurable GKE maintenance windows
- ATLAS-118015 KITTSune FedRAMP Moderate (KR 1.1)

### Zero Trust / Forge Compute (Larry contributor)
- ATLAS-111713 *[COD.MICROS.KR9]* ZTP-O1: Secure scalable Zero-Trust platform for untrusted code
- ATLAS-113342 *[ZTP-O1.KR1]* ZTP Platform Readiness
- ATLAS-92799 Zero Trust for Forge Containers (Simon Beckett owner; Larry contributor)
- ATLAS-115402 Forge Compute – Bluebird Dogfooding Q3
- ATLAS-115999 [EAP] WebCLI – web interface for ACLI
- ATLAS-113343 *[ZTP-O1.KR2]* FaaS Platform Adoption

### AMP & cross-pillar
- ATLAS-113285 *[COD.CloudSec.KR7]* Access Control for AMP
- ATLAS-112704 KR1.2.4 MKR in FedRAMP High Citadel for L2 services
- ATLAS-121720/121721/121722 AMP reliability / resiliency / availability KRs

---

## 6. Conclusions

1. **Vladimir Grebenik** is the **principal architect of Atlassian's next-generation logging stack** — owning Splunk multi-region (Leap), tiered storage, governance, and FY26 logging-efficiency KR `ATLAS-98101`. He produces RFCs and drives strategy more than commits.
2. **Larry Zhu** is the **principal engineer of KITT-on-GCP plus Zero-Trust Forge Containers**, materially active in **14 Bitbucket repos** (top: `poco` 381 PRs, `keyserver-go` 298, `kitt-runbook-cli`, `atlaskube-cli`, `gcp-kitt`, `kitsune`, `zero-trust-containers`, `mkr`, `micros-server`, `public-api`).
3. **Both report into Kangrong Yan** (Head of Core Engineering), so their work converges at the Multicloud + Cloud Storage Engineering boundary — exactly where SRE / hack-week themes around **observability + Kubernetes lifecycle + zero-trust runtime** intersect.
4. **Public-API / website-services**: neither owns these. Larry has light contributions to `public-api` & `micros-server`; the canonical owner is Networking (Mathrubootham Janakiraman) and the Micros / Platform group.

---
*Generated by Rovo Dev with three parallel General-Purpose subagents on 2026-05-01. All raw artefacts in this directory.*
