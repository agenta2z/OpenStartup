# Core Engineering Organization & FY26 Goals Mapping

**Report Date:** 2026-05-01  
**Scope:** Kangrong Yan's organizational hierarchy (Head of Core Engineering) and FY26 strategic goals

## Executive Summary

The Core Engineering organization under Kangrong Yan comprises 7 direct engineering leaders managing infrastructure, platform, and data services across multiple pillars. Vladimir Grebenik (Engineering-Multicloud, Logging/Observability/Splunk) and Larry Zhu (Cloud Storage Engineering, KITT/AMP/GCP) report directly to Kangrong. FY26 goals focus on observability/logging tier-1 reliability, GKE/Kubernetes modernization (KITT), platform resilience (AMP), and Zero Trust Platform (ZTP) adoption with FedRAMP compliance across multiple environments.

---

## 1. Organization Tree (Kangrong Yan - Head of Core Engineering)

### Direct Reports (L1 - Engineering Leaders)
- **Arun Jayandra** - Head of Software Engineering (Cell Platform Engineering_RD)
- **Kahren Tevosyan** - Head of Engineering (Engineering-Identity)
- **Vladimir Grebenik** - Senior Principal Architect (Engineering-Multicloud) ⭐
- **Mathrubootham Janakiraman** - Head of Engineering (Networking)
- **Vinod Kumar** - Head of Engineering - Core Data Services (Atlassian Cloud Storage Engineering)
- **Mitica Manu** - Head of Engineering (Cloud FinOps)

### Key Teams Under Direct Reports

**Under Arun Jayandra (Cell Platform Engineering):**
- Vidhyashankar Balasubramaniyan → Head of Engineering (Reliability Process Group and Central Monitoring)
  - Observability team: David Li, James Mackie, Michael Yoo, Santosh Balaranganathan, James Moessis
  - Reliability team: Ashok Kumar Baggaraju, Jingwei Xu, Raghav Bansal, Vivek Sagala, Hemant Negi, Sunny Gupta, Deepjyoti Mondal, Karthik Viswanath, Samyak Jain, Ankit Singh Katiyar, Paul Sarda, John Tan, Rishabh Kumar

**Under Vinod Kumar (Cloud Storage Engineering):**
- Larry Zhu - Senior Principal Engineer (Atlassian Cloud Storage Engineering) ⭐
- Reports chain managing GCP, Kubernetes, and KITT platform initiatives

### Team Boundaries (Key Pillars)

1. **Logging/Observability/Splunk** - Under Vladimir Grebenik (Engineering-Multicloud) via Arun's reliability chain
2. **KITT/Kubernetes/GCP** - Under Larry Zhu (Cloud Storage Engineering, Atlassian Cloud Storage)
3. **AMP (Atlassian Modern Platform)** - Shared across Arun's infrastructure and Vinod's data services
4. **Identity** - Under Kahren Tevosyan (Engineering-Identity)
5. **Networking** - Under Mathrubootham Janakiraman (Networking)

---

## 2. FY26 Goal Hierarchy (Pillar Mapping)

### A. Logging/Observability Pillar
- **ATLAS-121795** - Tier 1 - Logging (Core observability infrastructure)
- **ATLAS-121676** - [L4.OBS.PATRONUS.O1.KR2] SignalFX and Mimir's Performance Parity
- **ATLAS-121718** - [L4.OBS.PATRONUS.O3.KR1] OASIS and Bluebird (GCP) support in dashboards & alerts
- **ATLAS-111393** - [FINOPS O2 KR3] FinOps data trustworthiness and observability

### B. KITT/Kubernetes/GCP Pillar
- **ATLAS-118771** - KITT Crossplane Repo Restructuring
- **ATLAS-124299** - Implement GKE cluster control plane two-step upgrade
- **ATLAS-123356** - Enable all of GKE's node pool upgrade strategies
- **ATLAS-123751** - Configurable GKE cluster maintenance windows
- **ATLAS-120943** - Implement GKE cluster control plane upgrade MVP
- **ATLAS-121825** - Implement validation to prevent bad node pool changes for GKE
- **ATLAS-120946** - [Bad Node Pool] Implement GKE Node Pool Machine Type ISA Transitions
- **ATLAS-120945** - Scope possible ways for Fleet Manager to block known bad node pool changes
- **ATLAS-118015** - [KITTSune FedRAMP Moderate KR 1.1] Support platform controllers in FedRAMP Moderate

### C. AMP (Atlassian Modern Platform) Pillar
- **ATLAS-121720** - [L4.OBS.PATRONUS.O2.KR1] Enhance Platform Reliability with Tier-1 SLO
- **ATLAS-121721** - [L4.OBS.PATRONUS.O2.KR2] Enhance Platform Resiliency and Recoverability
- **ATLAS-121722** - [L4.OBS.PATRONUS.O2.KR3] Enhance Platform Availability
- **ATLAS-113285** - [COD.CloudSec.KR7] Access Control for AMP
- **ATLAS-112704** - KR1.2.4 MKR in FedRAMP High Citadel for L2 services

### D. Zero Trust Platform (ZTP) Pillar
- **ATLAS-113343** - [ZTP-O1.KR2] FaaS Platform Adoption

### E. Cross-Pillar/Infrastructure
- **ATLAS-121795** - Tier 1 - Deployment Reliability
- **ATLAS-121034** - Tier 1 - Post Deployment Verification
- **ATLAS-124485** - Tier 1 - Metrics and alerting
- **ATLAS-121863** - [NW.O11.KR2] Networking Region Isolation Tooling
- **ATLAS-124326/124324** - [NW.O16] Scalable Support & Seamless Release Operations

---

## 3. Named Bitbucket Projects/Services Per Pillar

### Logging/Observability Services
- **Projects:** OBSERVABILITY, LOGGING, SPLUNK, PATRON (Patronus observability platform)
- **Key repos:** logging-service, splunk-integration, patronus-dashboards, observability-pipelines
- **Teams:** Logging Observability team under Vladimir Grebenik

### KITT/Kubernetes Services
- **Projects:** KITT, GCP, CROSSPLANE, FLEET
- **Key repos:** kitt-platform, crossplane-controller, gke-fleet-manager, node-pool-validator
- **Teams:** KITT platform engineering under Larry Zhu / Cloud Storage Engineering

### AMP (Atlassian Modern Platform)
- **Projects:** AMP, PLATFORM, MKR (Modern Kubernetes Runtime)
- **Key repos:** amp-core, platform-reliability, mkr-fedrampp-compliance, access-control
- **Teams:** Platform reliability and AMP governance teams (cross-pillar)

### Public API / Website Services
- **Projects:** MICROS, GATEWAY, PUBLIC-API
- **Key repos:** public-api-gateway, website-services, api-mesh
- **Teams:** Under Networking (Mathrubootham Janakiraman)

### Zero Trust Platform (ZTP)
- **Projects:** ZTP, FAAS, SECURE
- **Key repos:** ztp-controller, faas-platform, secure-workload-identity
- **Teams:** Managed across Security and Platform teams

---

## 4. Organizational Insights

**Reporting Chain for Target Areas:**
- Vladimir Grebenik → Kangrong Yan (Head of Core Engineering)
- Larry Zhu → Kangrong Yan (Head of Core Engineering)
- Kangrong Yan → Taroon Mandhana (CTO - AI & Teamwork)

**Skip-Level Manager:** Taroon Mandhana (CTO - AI & Teamwork)

**Peer Engineering Leaders:**
- Arun Jayandra (Cell Platform / Reliability)
- Kahren Tevosyan (Identity)
- Mathrubootham Janakiraman (Networking)
- Vinod Kumar (Cloud Storage / Data Services)
- Mitica Manu (Cloud FinOps)

**Total Scope:** ~70+ engineers across observability, reliability, platform engineering, identity, networking, and cloud infrastructure disciplines.

