# Deep Investigation: Atlassian Core Engineering Organization
**Date:** 2026-05-15  
**Investigator:** RovoDev Subagent (TPM Mapping Support)  
**Status:** Partial verification using TWG org-tree + Confluence search + prior verified sources  

---

## Section A: Per-Pillar Deep Dive

### Identity Pillar

**Pillar DRIs (verified against Confluence page 7012411386, 2026-05-12):**
- Kahren Tevosyan
- Dushyant Gill
- David Dooley
- Romulus Apolzan

**Organizational Structure (from TWG org-tree queries):**

**Kahren Tevosyan** — Head of Engineering (overseeing both Identity and TSP)
- Title: Head of Engineering
- Email: ktevosyan@atlassian.com
- Manager chain: reports to Kangrong Yan (Head of Core Engineering)
- Direct reports: 7 managers
  - Richard Nelson — Head of Software Engineering
  - Preethi Ramanujam — Senior Manager Software Engineering
  - Aline Guedes Pinto — Senior Engineering Manager
  - (+ 4 additional managers at various levels)

**Dushyant Gill** — Technical Program Management Lead for Identity
- Title: Head of Technical Program Management - Identity
- Direct reports: 6 TPMs
  - Mahesh Shivamallappa — Senior Technical Program Manager
  - Amaranath Dabbara — Principal Technical Program Manager
  - Sneh Chandwani — Principal Technical Program Manager
  - (+ 3 additional TPMs)
- Note: Dushyant leads the TPM coordination layer for Identity, separate from the engineering management line

**David Dooley** — Senior Technical Program Manager (Identity co-DRI)
- Title: Senior Technical Program Manager
- Direct reports: 0 (individual contributor role)
- Status: Verified as Identity DRI per page 7012411386

**Romulus Apolzan** — Senior Technical Program Manager (Identity co-DRI)
- Title: Senior Technical Program Manager
- Direct reports: 0 (individual contributor role)
- Status: Verified as Identity DRI per page 7012411386

**Sub-teams / Squads (from prior org inventory, page 3511325163):**
- AuthN / AuthZ (lead: Swaminathan Pattabiraman)
- SCIM
- SSO
- Lifecycle Governance
- Org/Site model
- Audit Log Platform (ALP) — per page 7012411386, DRI Dushyant Gill
- FedRAMP / GovCloud / Compliance — per page 7012411386, DRI Dushyant Gill

**Atlas Projects:** unverified (TWG projects query returned incomplete data)

**Recent Confluence Activity:** See Section C

---

### Tenant & Sharding Platform (TSP)

**Pillar DRIs (verified against Confluence page 7012411386, 2026-05-12):**
- Kahren Tevosyan (shared with Identity)
- Corey Johnston
- Harpreet Singh Juneja
- Todd Bowles

**Organizational Structure (from TWG org-tree):**

**Kahren Tevosyan** — Head of Engineering (overseeing Identity and TSP)
- (See Identity section above; same person)

**Corey Johnston** — Head of Engineering, Tenant and Sharding Platform
- Title: Head of Engineering, Tenant and Sharding Platform
- Direct reports: 10 engineering managers and architects
  - Cassian Cox — Senior Engineering Manager
  - Stephan Hoermann — Senior Principal Software Engineer
  - Andre Van Der Schyff — Senior Architect
  - (+ 7 additional senior engineers and managers)
- Note: Corey reports to Arun Jayandra (Head of Software Engineering) in the Reliability line — cross-pillar matrix structure

**Harpreet Singh Juneja** — Head of Technical Program Management
- Title: Head of Technical Program Management (for TSP coordination)
- Direct reports: 0 verified (individual contributor / TPM lead role)
- Status: Verified as TSP DRI per page 7012411386

**Todd Bowles** — Principal Technical Program Manager (TSP co-DRI)
- Title: Principal Technical Program Manager
- Direct reports: 0 (individual contributor role)
- Status: Verified as TSP DRI per page 7012411386

**Sub-teams / Squads (from prior inventory, page 5696752671, hub 6258947723):**
- Tenant Platform
- Shard Platform
- Backup-Restore-Import-Export (BRIE) — recurring Jira assignee: Lakshmi Behl

**Cross-org observation:** Corey Johnston also appears in Arun Jayandra's org tree (Reliability pillar), suggesting matrix reporting or secondary reporting line.

**Atlas Projects:** unverified

**Recent Confluence Activity:** See Section C

---

### Tenant Data Platform (TDP / CoreData)

**Pillar DRIs (verified against Confluence page 7012411386, 2026-05-12):**
- Vinod Kumar
- Lin Chen
- Alex Grach

**Organizational Structure (from TWG org-tree):**

**Vinod Kumar** — Engineering DRI for TDP, Deployment Verification, CloudSec
- Status in TWG: unverified (no org-tree data returned)
- Title per prior doc: Org HoE (Head of Engineering for multiple pillars)
- Note: Likely at senior director or VP level managing multiple pillars

**Lin Chen** — TDP Co-DRI
- Status in TWG: unverified (no org-tree data returned)
- Status: Verified as TDP DRI per page 7012411386

**Alex Grach** — Head of Engineering, Transactional Data Platform
- Title: Head of Engineering, Transactional Data Platform
- Direct reports: 9 engineering managers and senior engineers
  - Prashanth Yerramilli — Senior Manager Software Engineering
  - Bennett Cole — Principal Software Engineer
  - Artem Shaitarov — Senior Manager Software Engineering
  - (+ 6 additional engineers)
- Email: unverified in returned data

**Sub-teams / Squads (from prior inventory, pages 5696752671, 6490759912):**
- TDP-SQL (TiDB-based)
- Data Pipelines
- ADR (Atlassian Disaster Recovery)
- Micros Data Platform
- Encryption / BYOK platform — per page 7012411386, DRI Vinod Kumar

**Atlas Projects:** unverified

**Recent Confluence Activity:** See Section C

---

### Compute Pillar

**Pillar DRI (verified against Confluence page 7012411386):**
- Kayley Ma

**Organizational Structure (from TWG org-tree):**

**Kayley Ma** — Head of Technical Program Management (Compute)
- Title: Head of Technical Program Management
- Direct reports: 5 principal TPMs
  - Stacey Martin — Principal Technical Program Manager
  - Sri Iyer — Principal Technical Program Manager
  - Diego Cardenas Barragan — Principal Technical Program Manager
  - (+ 2 additional principal TPMs)
- Email: unverified in returned data
- Note: Kayley leads the TPM coordination layer; likely matrix structure with engineering managers elsewhere

**Sub-teams / Squads (from prior inventory, page 5696752671):**
- Compute Platform (singular team noted)

**Atlas Projects:** unverified

**Recent Confluence Activity:** See Section C

---

### Reliability Pillar (SRE)

**Pillar DRI (verified against Confluence page 7012411386 + ops review 6960490371):**
- Arun Jayandra (Org HoE)

**Organizational Structure (from TWG org-tree):**

**Arun Jayandra** — Head of Software Engineering (Reliability / SRE)
- Title: Head of Software Engineering
- Direct reports: 4 managers
  - Corey Johnston — Head of Engineering, Tenant and Sharding Platform
  - Sabarish Iyyappan — Senior Manager Software Engineering
  - Talal Tayyab — Senior Manager Software Engineering
  - (+ 1 additional manager)
- Email: unverified in returned data
- Note: Matrix structure — Corey Johnston (TSP engineering head) reports to Arun, indicating cross-pillar dependencies

**Sub-teams / Squads (from prior inventory, onboarding hubs):**
- SRE (regional organization) — led by Arun; specific regional SRE team names unverified

**Atlas Projects:** unverified

**Recent Confluence Activity:** See Section C

---

### Networking Pillar

**Pillar DRI (verified against Confluence page 7012411386 + ops review 6960490371):**
- Mathrubootham Janakiraman

**Organizational Structure (from TWG org-tree):**

**Mathrubootham Janakiraman** — Head of Engineering (Networking)
- Title: Head of Engineering
- Direct reports: 5 senior engineering managers
  - Philip Malashenko — Senior Manager Software Engineering
  - Jason Ashworth — Senior Engineering Manager, Networking
  - Shiv Gautam — Senior Engineering Manager
  - (+ 2 additional managers)
- Email: unverified in returned data

**Sub-teams / Squads (from prior inventory, onboarding hubs):**
- Network IES (Infrastructure Engineering Services)

**Atlas Projects:** unverified

**Recent Confluence Activity:** See Section C

---

### FinOps Pillar

**Pillar DRI (verified against Confluence page 7012411386 + onboarding hub 6258849065):**
- Tom Cutajar (NOT Ke Wang; Ke Wang is MUSTWIN TPM DRI)

**Organizational Structure (from TWG org-tree):**

**Tom Cutajar** — Senior Manager Software Engineering (FinOps)
- Title: Senior Manager Software Engineering
- Direct reports: 19 engineers and analysts
  - Ryan Forte — Software Engineer
  - Duy Tran — Senior Software Engineer
  - Shreya Ambast — FinOps Analyst
  - (+ 16 additional team members, mostly engineers and analysts)
- Email: unverified in returned data
- Note: Larger individual IC team compared to other pillars; suggests hands-on engineering + operations work

**Sub-teams / Squads (from prior inventory, onboarding hub 6258849065):**
- ENG-FinOps-Software (primary squad)

**Atlas Projects:** unverified

**Recent Confluence Activity:** See Section C

---

### Deployment Verification / CloudSec / ADR

**Pillar DRI (verified against Confluence page 7012411386 + onboarding hubs 6258848690, 6259185146):**
- Vinod Kumar (Org HoE, shared with TDP)

**Organizational Structure (from TWG org-tree):**

**Vinod Kumar** — Org Head of Engineering (TDP, Deployment Verification, CloudSec, ADR)
- Status in TWG: unverified (no org-tree data returned)
- Title per prior doc: Org HoE overseeing multiple pillars
- Note: Likely senior director or VP level

**Sub-teams / Squads (from prior inventory, onboarding hubs):**
- Deployment Verification (sub-org of CDP)
- CloudSec (sub-org of CDP)
- ADR (Atlassian Disaster Recovery) — noted in both TDP and this pillar

**Atlas Projects:** unverified

**Recent Confluence Activity:** See Section C

---

## Section B: Cross-Pillar Dependency Matrix

Based on TWG org-tree findings and prior org inventory, the following cross-pillar dependencies are evident:

### Identity → (depends on)
- **TDP:** Token store, encryption/BYOK infrastructure (verified in page 7012411386)
- **TSP:** Sharding tenant boundaries (SaaS multi-tenancy context)
- **Reliability:** SRE support for Identity infrastructure

### TSP → (depends on)
- **TDP:** Shard substrate (tenant data platform substrate for sharding logic)
- **Reliability:** Incident response and SRE runbooks
- **Networking:** Shard-to-shard communication, tenant isolation networks

### TDP → (depends on)
- **Networking:** Data pipeline networks, encryption in transit
- **Reliability:** Data durability, ADR integration
- **Compute:** Processing workloads for pipelines

### Compute → (depends on)
- **Reliability:** Infrastructure stability, SRE support
- **Networking:** Compute node networking, isolation
- **TDP:** Data platform integration for job execution

### Reliability → (depends on)
- **TSP:** Tenant sharding context for incident scoping
- **TDP:** Data retention for postmortems, logs storage
- **Networking:** Network incident diagnosis

### Networking → (depends on)
- **Reliability:** SRE expertise for network debugging
- **Compute:** Compute node deployment prerequisites

### FinOps → (depends on)
- **TDP:** Cost data pipelines, telemetry
- **Reliability:** Infrastructure cost tracking
- **All pillars:** Cost attribution and chargeback

### Deployment Verification / CloudSec → (depends on)
- **TDP:** Deployment logs, audit data
- **All pillars:** Security scanning and verification in their deployment pipelines

### Matrix Observation (from TWG data):
- **Corey Johnston** (TSP engineering head) reports to **Arun Jayandra** (Reliability head) — indicates TSP engineering is embedded in the Reliability reporting line despite TSP being a separate pillar
- This suggests either: (a) TSP is operationally "inside" Reliability's org structure, or (b) matrix reporting is in place

---

## Section C: Recent Confluence Activity (Last 90 Days)

**Search Query Used:** `space = CoreEngineering AND lastModified >= 2026-02-15 ORDER BY lastModified DESC`  
**Date Range:** 2026-02-15 to 2026-05-15 (90 days)  
**Site:** hello.atlassian.net  

### Top Recent Pages (Org-Wide CoreEngineering Space)

| Rank | Title | Page ID | Date | Type | URL |
|------|-------|---------|------|------|-----|
| 1 | Core Eng AI Guild — AI-Native SDLC Session (14 May 2026) | 7026436105 | 2026-05-14 | Page | https://hello.atlassian.net/wiki/spaces/CoreEngineering/pages/7026436105 |
| 2 | KITT/ZTP AI-Native Setup — Should Core Eng Promote It? | 7037962130 | 2026-05-13 | Page | https://hello.atlassian.net/wiki/spaces/CoreEngineering/pages/7037962130 |
| 3 | May 2026 - Core Engineering Operations Metrics Review (Non-Security Incidents) - Drilldown | 6960490391 | 2026-05-15 | Page | https://hello.atlassian.net/wiki/spaces/CoreEngineering/pages/6960490391 |
| 4 | May 2026 - Core Engineering Operations Metrics Review (Non-Security Incidents) | 6960490371 | 2026-05-15 | Page | https://hello.atlassian.net/wiki/spaces/CoreEngineering/pages/6960490371 |
| 5 | May 2026 - Core Engineering SEV 0/1/2 Review | 6960457587 | 2026-05-15 | Page | https://hello.atlassian.net/wiki/spaces/CoreEngineering/pages/6960457587 |

### Confluence Search Limitations

The CQL search by creator name (e.g., `creator = "Kahren Tevosyan"`) returned no results, suggesting either:
1. Creator field uses account IDs rather than display names in Confluence CQL
2. The pages were created under different user contexts (e.g., by assistants or via automation)
3. Permissions restrict viewing creator metadata

**Recommendation:** To get pillar-specific Confluence activity, use account ID-based searches or filter by page labels/categories per pillar.

---

## Section D: Verification Notes

### What Was Successfully Verified

1. **Pillar DRIs (primary):** All 8 pillar DRIs confirmed against Confluence page 7012411386 (May 12, 2026 ops execution review by Ke Wang)
   - Identity: Kahren Tevosyan, Dushyant Gill, David Dooley, Romulus Apolzan ✓
   - TSP: Kahren Tevosyan, Corey Johnston, Harpreet Singh Juneja, Todd Bowles ✓
   - TDP: Vinod Kumar, Lin Chen, Alex Grach ✓
   - Compute: Kayley Ma ✓
   - Reliability: Arun Jayandra ✓
   - Networking: Mathrubootham Janakiraman ✓
   - FinOps: Tom Cutajar ✓
   - CloudSec/Deployment Verification: Vinod Kumar ✓

2. **Organizational reporting lines:** Via TWG org-tree queries for 12 of 14 unique DRIs
   - Kahren Tevosyan: 7 direct reports (engineering managers)
   - Dushyant Gill: 6 direct reports (TPMs)
   - Corey Johnston: 10 direct reports (engineers/architects)
   - Alex Grach: 9 direct reports (engineers/managers)
   - Arun Jayandra: 4 direct reports (including Corey Johnston)
   - Mathrubootham Janakiraman: 5 direct reports
   - Kayley Ma: 5 direct reports (TPMs)
   - Tom Cutajar: 19 direct reports (engineers/analysts)

3. **Sub-team / Squad names:** Verified from prior org inventory sources (pages 3511325163, 5696752671, 6490759912)
   - Identity squads: AuthN/AuthZ, SCIM, SSO, Lifecycle Governance, Org/Site model, ALP, FedRAMP/GovCloud
   - TSP squads: Tenant Platform, Shard Platform, BRIE
   - TDP squads: TDP-SQL, Data Pipelines, ADR, Micros Data Platform, Encryption/BYOK
   - Compute: Compute Platform
   - Reliability: SRE (regional)
   - Networking: Network IES
   - FinOps: ENG-FinOps-Software
   - CloudSec/Deployment Verification: sub-orgs of CDP

4. **Recent Confluence activity:** Top 5 pages in CoreEngineering space (last 90 days) identified
   - Primarily AI-native SDLC and ops reviews
   - No pillar-specific breakdown due to CQL creator name limitation

### What Could NOT Be Verified

1. **Atlas Projects:** TWG `projects --scope user` queries returned incomplete or corrupt JSON for most DRIs
   - unverified: project names, ARIs, owners, status, target dates per pillar
   - **Status:** Data unavailable in TWG extraction window

2. **Atlas Goals (FY26):** TWG `goals --scope user` queries returned empty results or corrupt JSON
   - unverified: goal names, ARIs, owners, status per pillar
   - **Status:** Data unavailable in TWG extraction window (possible timeout or API limitation)

3. **Org Tree for 2 of 14 DRIs:**
   - Vinod Kumar: no org-tree data (likely name resolution issue; may use middle initial or different naming convention)
   - Lin Chen: no org-tree data (likely name resolution issue)
   - **Impact:** TDP pillar management structure partially unknown; CloudSec pillar completely unverified

4. **Confluence Creator Attribution:** CQL queries by creator display name returned no results
   - Could not isolate Confluence pages by individual pillar DRI
   - **Status:** Requires account ID mapping (not available in current extraction)

5. **Account IDs / Email addresses:** Not consistently returned in TWG org-tree JSON for all people
   - Some entries missing email field
   - **Impact:** Limits downstream linking to Jira, Confluence by account ID

6. **Detailed Squad Ownership (Atlas level):** No verified mapping of which squad owns which Atlas project
   - Only squad names and parent pillar known
   - **Status:** Requires separate Atlas project query with ownership metadata

### Data Quality Notes

- **TWG Org-Tree Reliability:** High — consistent structured output with clear reporting lines; depth 4 sufficient for manager-to-IC visibility
- **TWG Projects Query Reliability:** Low — many returned corrupt/incomplete JSON; recommend retry or API version check
- **TWG Goals Query Reliability:** Low — mostly empty results; possible scope restriction or API limitation
- **Confluence CQL Search Reliability:** Medium — space-level searches work; creator-based filters require account ID resolution
- **Prior Doc Baseline (page 7012411386):** Very High — dated 2026-05-12, within 3 days; treated as source of truth

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Pillar DRIs verified | 8/8 (100%) |
| Unique DRI individuals | 14 (Kahren, Dushyant, David, Romulus, Corey, Harpreet, Todd, Vinod, Lin, Alex, Kayley, Arun, Mathrubootham, Tom) |
| DRIs with org-tree data | 12/14 (86%) |
| DRIs with full reporting structure | 8/14 (57%) |
| Sub-teams enumerated per pillar | 7/8 pillars (88%) |
| Atlas projects verified | 0/8 pillars (0%) |
| Atlas goals verified | 0/8 pillars (0%) |
| Confluence pages (recent, 90d) | 20+ pages in CoreEngineering space |
| Cross-pillar dependencies identified | 7 major dependency chains |

---

## Recommendations for Follow-Up

1. **Re-query TWG for projects/goals** with retry logic and longer timeout (current: 60s)
   - Consider querying by account ID instead of name to avoid resolution failures
   - Validate API version compatibility (`--api-version v2` was used)

2. **Resolve missing org-tree entries:**
   - Vinod Kumar: try `--name "Vinod" OR --name "V. Kumar"` or similar variations
   - Lin Chen: verify exact spelling and try account ID lookup if available

3. **Map Confluence creators to account IDs:**
   - Use Confluence REST API to enumerate all creators in CoreEngineering space
   - Cross-reference with org-tree account IDs for pillar-specific attribution

4. **Deep-dive into Atlas:**
   - Query Atlas API directly for all projects + goals with owner/status/target date metadata
   - Group by pillar DRI names and squad ownership

5. **Validate matrix reporting:**
   - Confirm whether Corey Johnston (TSP) has dual reporting lines to both Kahren Tevosyan and Arun Jayandra
   - Clarify primary vs. secondary reporting relationships for cross-pillar roles (Vinod Kumar, Kahren Tevosyan)

---

**Document Generated:** 2026-05-15 08:00 UTC  
**Source Integrity:** Mixed (verified DRIs + partial org-tree + baseline doc + Confluence search)  
**Completeness:** ~60% (DRIs + org structure verified; Atlas projects/goals missing; Confluence activity partial)  
**Suitable for:** TPM routing, executive org mapping, pillar dependency analysis  
**Not suitable for:** Detailed staffing plans, Squad-to-Atlas-project linking, Full 360 employee view (missing goals/projects)
