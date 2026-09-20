# Atlassian Identity & IAM Pillar - Core Engineering
## Comprehensive Research Report
**Last Updated:** May 1, 2026

---

## EXECUTIVE SUMMARY

The Identity team is the **largest pillar within Atlassian's Core Engineering organization**, reporting under ENT-CoreEng DRI Ke Wang. The team is responsible for building and maintaining the foundational authentication, authorization, identity management, and access control infrastructure that powers Atlassian's entire cloud platform.

### Key Scope Areas:
- **Identity & Access Management (IAM)** - Authentication, authorization, single sign-on
- **Data at Rest Encryption (DaRe) for PII** - Encryption and protection of personally identifiable information
- **Org Isolation & Collaboration Context** - Multi-tenant isolation and organizational hierarchy
- **Admin Hub Scale** - Administration capabilities for enterprise customers
- **BRIE FastShift Integration** - Integration with bring-your-own-infrastructure initiatives
- **License Decoupling** - Separation of licensing from infrastructure
- **Atlassian Guard Integration** - Security monitoring and threat detection

---

## 1. IDENTITY TEAM STRUCTURE

### Confirmed Sub-Teams (from ENT Planning):

1. **Identity-Rocket**
   - Primary operational team for core Identity Platform
   - Manages authentication and session management
   - Handles Team Rocket reporting (weekly TechOps status)

2. **Identity-Goomda**
   - Focus area: Permissions and authorization systems
   - Works on Next-Gen Authorization (NGA) Platform

3. **Identity-Fortress**
   - Security and defensive posture
   - Manages Identity-Fortress TechOps reporting
   - Handles enterprise security requirements

4. **Identity-FastShift**
   - Dedicated to BRIE (Bring Your Own Infrastructure) FastShift commitments
   - Led by: Muhammed Yahya (driver), Tanay Soley
   - Approver: Manu Manjunath (Cloud Transition)
   - Informed: Akash Agarwal, Tarun Jadhwani, Varun Shinde

### Key Leadership & Stakeholders:

- **ENT-CoreEng DRI:** Ke Wang
- **DaRe Program DRI:** Richa Kumar (formerly), currently under Peter Wang's leadership
- **DaRe TPM:** Amaranath Dabbara
- **DaRe Architect:** Chetan Ithal
- **Next-Gen AuthZ Owner:** Alex Herweyer
- **Identity Platform Strategy/GCP:** Peter Wang
- **Project Nexus (SCIM/Unified Directory):** Ratheesh Mohan

---

## 2. IDENTITY'S CAPABILITY PORTFOLIO

### Core Technology Stack & Capabilities:

#### Authentication & Session Management:
- **SSO (Single Sign-On)** - SAML, OAuth 2.0 support
- **Multi-factor Authentication (MFA)**
- **Session Management & Lifecycle**
- **Device Authentication & Trust**
- **Cross-product Authentication** - Unified auth across Jira, Confluence, Service Desk, etc.

#### Authorization & Permissions:
- **Next-Generation Authorization (NGA) Platform** - Successor to legacy Perms stack
  - Supports 250K+ customer scale
  - Target completion: June 2024 (completed, now maintaining)
  - Migration from legacy Perms to AuthZ stack
- **Permission Platform APIs** - Search/lookup capabilities
- **Role-Based Access Control (RBAC)**
- **Collaborative Permissions** - Team-based access management
- **Resource-Principal Mapping**

#### API Token Management:
- **Personal Access Tokens (PAT)**
- **API Token Lifecycle Management**
- **Classic PAT Deprecation Program** - Migration to modern token standards
- **Token Security & Rotation**
- **OAuth Token Management**

#### Identity Infrastructure:
- **Unified Directory** - Centralized user/group management
- **SCIM (System for Cross-domain Identity Management)**
  - User provisioning/deprovisioning
  - Group synchronization via ALS (Account Link Service)
  - Integration with Group Directory
- **User Account Management**
- **Organization Unit (Org Unit) Management** - Enterprise org structure
- **User Activity Platform (Worklens)** - Activity tracking and audit

#### Enterprise Features:
- **Admin Hub Scale** - Enterprise administration dashboard
- **Atlassian Guard Integration** - Security monitoring, threat detection, anomaly detection
- **Data at Rest Encryption (DaRe)** - PII encryption, key management
- **Org Isolation** - Multi-tenant data isolation, workspace separation
- **Collaboration Context** - Org hierarchy, access context
- **Bring Your Own Infrastructure (BRIE)** - Customer self-hosted infrastructure support
- **License Decoupling** - Infrastructure-agnostic licensing

#### Cloud & Infrastructure:
- **Multi-Cloud Support** - AWS, GCP, and future platforms
- **Edge Authenticator Service** - Regional authentication
- **ID Gatekeeper Service** - API gateway for identity
- **Account Reader Service** - Account data access
- **AuthZ Reader Facade** - Authorization lookup with caching (GCP)

---

## 3. FY26 ROADMAP & COMMITMENTS

### FY26 Strategic Programs:

#### A. Scale & Performance Initiative ("Step Up Scale")
- **Goal:** Support 250K+ customer scale
- **Current Status:** Progressive milestone tracking
- **Not a ceiling:** 250K is a benchmark, not the maximum target
- **Components:**
  - Scalable Pollinators for Oasis infrastructure
  - 10x scale verification testing
  - Permissions platform search/lookup optimization
  - Cassandra scaling and alternative approaches

#### B. Project Nexus - Unified Directory & SCIM
- **Focus:** Modern identity provisioning
- **Sprint 2 Status (Apr 20-30, 2026):**
  - `id-dal` service operational with API and data models finalized (ON TRACK)
  - SCIM ingestion flow for users and groups via ALS and Group Directory (ON TRACK)
  - Account must be SCIM synched to id-dal (ON TRACK)
  - Groups must be SCIM synched to id-dal (ON TRACK)
  - Login flow for tenanted URL (ON TRACK)
  - SSO login functionality

#### C. Multi-Cloud Migration - GCP Onboarding (M4)
- **Target:** FY26Q4 (June 30, 2026)
- **Architecture:**
  - UGC (User-Generated Content) stored in GCP
  - PII remains in AWS (Data Residency)
  - Cross-cloud calls acceptable
- **M4 Services (4 core services):**
  - `edge-authenticator` - Regional auth
  - `id-gatekeeper` - API gateway
  - `account-reader` - Account data
  - `authz-reader-facade` - AuthZ with GCP caching

#### D. BRIE FastShift Integration
- **Document:** Scale commitment for BRIE from Identity - FastShift (Page ID: 5028191522)
- **Status:** 2-way door decision
- **Drivers:** Muhammed Yahya, Tanay Soley
- **Approvers:** Manu Manjunath (Cloud Transition), David Dooley (Identity), Chetan Ithal (Identity)
- **Informed:** Akash Agarwal, Tarun Jadhwani, Varun Shinde
- **Scope:** Identity platform support for BRIE FastShift deployment model

#### E. DaRe (Data at Rest Encryption) Program
- **Document:** DaRe for PII @ Rest Program Posture (Page ID: 4685341876)
- **Owner:** Peter Wang (formerly Richa Kumar)
- **TPM:** Amaranath Dabbara
- **Architect:** Chetan Ithal
- **Program Ticket:** ATLAS-96484
- **Focus:** Encryption of PII at rest across Atlassian services
- **Status:** V35 (latest version Aug 26, 2025)

#### F. Authorization Platform (NGA)
- **Document:** Perms V2 (aka NGA) - Roadmap, Milestones and Timeline (Page ID: 2788502190)
- **Owner:** Chetan Ithal
- **Milestone:** v46 (latest: May 1, 2026)
- **Target:** Support 250K+ customers (completed)
- **Status:** Maintenance phase, ongoing improvements

---

## 4. KEY OKRs & KR SCORES (FY26)

### OKR Organization:
- Identity operates under **Atlas Goals** structure
- Multiple OKRs tracked across sub-teams

### Identified Goals & KRs:

#### O1: Scale & Performance
- **KR:** 250K benchmark for Identity Scale (score tracking in progress)
- **Page:** Stretch goal for Identity Scale (ID: 2835848255)
- **Status:** Progressive milestone measurement
- **L3 KR:** Scale & Performance tracking (Page ID: 5377786401)

#### O2: Authorization Platform Success
- **KR:** NGA Platform adoption and stability
- **Related:** AuthZ FY24 Goal mapping (ID: 2628300943) - extends to FY26

#### O3: Cloud Infrastructure (Multi-Cloud)
- **KR:** GCP M4 services operational (4 services by FY26Q4)
- **Page:** High Level Goals for GCP (ID: 6671217122)

#### O4: BRIE Integration
- **KR:** Scale commitment completion for BRIE FastShift
- **Status:** Decision phase with 2-way door review

### Additional Goal Documents:
- **Sprint 2 Goals** (ID: 6861270005) - Project Nexus sprints
- **Identity FY26 Roadmap - Funding Assessment** (ID: 5231640887) - Database tracking

---

## 5. CRITICAL DEPENDENCIES & CROSS-TEAM INTEGRATION

### What Identity Provides to Other Teams:

#### BRIE (Bring Your Own Infrastructure):
- FastShift integration for self-hosted deployments
- Identity platform in customer-managed infrastructure
- DRI: Muhammed Yahya (Identity-FastShift)

#### DaRe (Data at Rest Encryption):
- PII encryption at rest
- Key management and rotation
- Encryption policy enforcement
- Integration with other services (Jira, Confluence, etc.)

#### Org Isolation & Collaboration:
- Multi-tenant isolation guarantees
- Organization hierarchy management
- Team-based access control
- Collaboration context for workspace management

#### Admin Hub Scale:
- Enterprise administration capabilities
- User/group management at scale
- Policy enforcement dashboards
- Audit and compliance reporting

#### Atlassian Guard:
- Identity signals for anomaly detection
- Authentication pattern monitoring
- User behavior analysis
- Threat detection integration

#### License Management:
- Identity infrastructure-independent licensing
- License decoupling from deployment model
- Flexible licensing for multi-cloud scenarios

---

## 6. CONFLUENCE SPACES & DOCUMENTATION

### Primary Spaces:

1. **Identity (I)** - Main Identity team space
   - Contains team plans, roadmaps, technical documentation
   - 2,531+ pages with recent activity
   - Weekly team reports (Team Rocket, Team Fortress)

2. **Enterprise Grade (TRUSTED)** - Enterprise capabilities audit
   - IAM & Access Management capability audit (ID: 3635515549)
   - Enterprise-grade security requirements
   - Framework pillar ownership tracking

3. **Cloud Transition (CT5)** - Multi-cloud transition
   - BRIE FastShift commitment (ID: 5028191522)
   - Cloud migration planning and coordination

### Key Documents:

**FY26 Planning:**
- Identity FY26 Roadmap - Funding Assessment (5231640887)
- Step Up Scale - FY 26 Goals (5383267174)
- Identity FY26 L3 KR - Scale & Performance (5377786401)

**Technical Roadmaps:**
- Perms V2 (NGA) Roadmap, Milestones & Timeline (2788502190)
- A Roadmap to GCP Onboarding for Identity (5505234469)

**Strategic:**
- Identity Platform - 3 Year Strategy FY22-FY24 (721356616)
- Stretch goal for Identity Scale (2835848255)
- High Level Goals for GCP (6671217122)

**Operational:**
- Team Rocket weekly TechOps reports (2020-present)
- Team Fortress weekly TechOps reports (2023-present)
- Sprint 2 Goals - Project Nexus (6861270005)

---

## 7. JIRA PROJECT KEYS & ISSUE TRACKING

### Primary Project Keys:

- **IDENTITY** - Core Identity platform issues
- **GUARD** - Atlassian Guard integration
- **IDP** - Identity Provider related work
- **COMMIT** - Committed work tracking (contains Identity-related issues)
  - Searches include: Single Logout, SCIM, DaRe, Org Unit issues

### Work Categories in COMMIT:
- Single Logout implementations
- SCIM provisioning features
- DaRe encryption rollouts
- Organization Unit scaling
- Enterprise feature enhancements

---

## 8. TECHNOLOGY STACK & INFRASTRUCTURE

### Core Technologies:

#### Authentication Protocols:
- **SAML 2.0** - Enterprise SSO
- **OAuth 2.0** - API and third-party integrations
- **OpenID Connect (OIDC)** - Identity federation
- **API Token-based Auth** - Personal Access Tokens (PAT)

#### Data Storage & Management:
- **Cassandra** - Distributed permissions and principal data
- **PostgreSQL** - Relational data
- **AWS** - Primary cloud infrastructure for PII
- **GCP** - UGC and scaling infrastructure (M4 goals)

#### Services & Microservices:
- **edge-authenticator** - Regional auth service
- **id-gatekeeper** - Identity API gateway
- **account-reader** - User account data service
- **authz-reader-facade** - AuthZ with caching layer
- **id-dal** (Unified Directory) - SCIM-compliant user/group store
- **Account Link Service (ALS)** - SCIM provisioning
- **Worklens** - User activity platform

#### Provisioning & Integration:
- **SCIM** (System for Cross-domain Identity Management)
- **Group Directory API** - Group management
- **User Directory API** - User management
- **Audit APIs** - Compliance and audit logging

### Infrastructure Patterns:
- Multi-cloud deployment (AWS primary, GCP expanding)
- Microservice architecture
- API-first design
- SCIM-compliant identity federation
- PII data residency requirements

---

## 9. CAPACITY & HEADCOUNT SIGNALS

### Team Size Signals:
- **Large team** - Largest pillar in CoreEng
- Multiple dedicated sub-teams (4+ identified)
- Distributed leadership across sub-teams and programs

### Capacity Indicators:
- Identity FY26 Roadmap - Funding Assessment database tracks:
  - Total Engineers (excluding HoE, EMs, Architects)
  - CtB (Contribute to Business) capacity
  - 25% RtB (Run the Business) allocation
  - 10% Dev Productivity allocation
  - Funded vs. unfunded initiatives

### Program-Level Investment:
- **DaRe Program** - TPM, Architect, Team DRI dedicated
- **Project Nexus** - Multi-sprint initiative with dedicated ownership (Ratheesh Mohan)
- **GCP Migration** - Significant infrastructure investment
- **BRIE FastShift** - Dedicated team (Identity-FastShift) with approvers from multiple orgs

---

## 10. KEY RISKS & BLOCKERS

### Known Risks & Challenges:

#### Scale Risks:
1. **250K Scale Benchmark** - Not a ceiling; need to support beyond this
   - Cassandra limitations for permission lookups (fanout queries)
   - Search/lookup API optimization required
   - Alternative data structures being evaluated

#### Infrastructure Risks:
1. **Multi-Cloud Complexity**
   - Cross-cloud calls acceptable but add latency
   - PII residency requirements constrain architecture
   - GCP M4 onboarding timeline (FY26Q4 target)

2. **BRIE Deployment Model**
   - Customer self-hosted infrastructure support complexity
   - Identity capabilities in non-AWS environments
   - FastShift integration dependencies

#### Technical Debt:
1. **Legacy Perms Stack Deprecation**
   - NGA platform migration in progress
   - Dual maintenance period ongoing
   - Classic PAT deprecation program complexity

2. **SCIM Provisioning**
   - Account and group sync reliability
   - Tenanted URL login flows
   - Integration across multiple services

#### Organizational Dependencies:
1. **BRIE FastShift Approval**
   - Requires coordination with Cloud Transition (Manu Manjunath)
   - Multiple stakeholders (Akash Agarwal, Tarun Jadhwani, Varun Shinde)
   - 2-way door decision complexity

2. **DaRe Program Execution**
   - Enterprise-wide PII encryption rollout
   - Cross-product coordination (Jira, Confluence, Service Desk, etc.)
   - Compliance and audit requirements

#### Capacity Constraints:
1. **Multiple FY26 Initiatives**
   - Scale improvement
   - Project Nexus (SCIM/Unified Directory)
   - GCP migration (M4)
   - BRIE FastShift integration
   - DaRe program continuation
   - Authorization platform maintenance

### Potential Blockers:
- Cross-cloud latency impacts on user experience
- SCIM ingestion reliability at scale
- GCP capacity and service launch readiness
- BRIE deployment model complexity
- Enterprise security audit timelines for DaRe

---

## 11. FINANCIAL & STRATEGIC CONTEXT

### FY26 Funding Assessment:
- **Database:** Identity FY26 Roadmap - Funding Assessment (5231640887)
- **Status:** Fully/Partially funded initiatives tracked
- **Categories:**
  - MUST HAVE initiatives (funded)
  - Strategic initiatives (funding status tracked)
  - Product Security platform enhancements
  - Token and OAuth improvements

### BRIE Integration Financial Impact:
- **Decision Status:** 2-way door (reversible decision)
- **Approver Impact:** 174 complete, 88063768-625c-4737-b9c7-7cef85fe8e2a complete (Chetan Ithal)
- **Cross-org coordination:** Cloud Transition, Identity team alignment

---

## 12. KNOWN CONTACTS & DRI MAP

### Key DRIs by Program:

| Program | DRI | Secondary | TPM/PM |
|---------|-----|-----------|--------|
| Identity Platform (Core) | Ke Wang | Multiple sub-team leads | - |
| Identity-Rocket (Auth/Sessions) | Team Rocket Lead | Tasha Chandolia | - |
| Identity-Fortress (Security) | Fortress Lead | - | - |
| Identity-Goomda (AuthZ) | Alex Herweyer | Chetan Ithal | - |
| Identity-FastShift (BRIE) | Muhammed Yahya | Tanay Soley | Tanay Soley |
| DaRe Program | Peter Wang | Amaranath Dabbara (TPM) | Amaranath Dabbara |
| Project Nexus | Ratheesh Mohan | Jakub Telicki | - |
| GCP Migration | Peter Wang | - | - |
| NGA/AuthZ Platform | Chetan Ithal | Alex Herweyer | - |

---

## APPENDIX: DOCUMENTATION REFERENCES

### Primary Documentation Sources:

1. **Identity Space (I):** https://hello.atlassian.net/wiki/spaces/I
2. **Enterprise Grade (TRUSTED):** https://hello.atlassian.net/wiki/spaces/TRUSTED
3. **Cloud Transition (CT5):** https://hello.atlassian.net/wiki/spaces/CT5

### Key Pages:
- DaRe Program Posture: /spaces/I/pages/4685341876
- BRIE FastShift Commitment: /spaces/CT5/pages/5028191522
- IAM Capability Audit: /spaces/TRUSTED/pages/3635515549
- NGA Roadmap: /spaces/I/pages/2788502190
- Stretch Goal for Scale: /spaces/I/pages/2835848255
- GCP High-Level Goals: /spaces/I/pages/6671217122
- FY26 Roadmap Assessment: /spaces/I/database/5231640887

---

## RESEARCH METHODOLOGY

**Data Sources Used:**
- Confluence space searches (Identity, Enterprise Grade, Cloud Transition)
- Page metadata and version history
- Team documentation and planning artifacts
- Jira project key identification
- Goal and KR tracking documents

**Search Queries Executed:**
- Space key filters: `space.key = "I"`, `"TRUSTED"`, `"CT5"`
- Title filters: FY26, roadmap, charter, OKR, team, scale, platform, goals
- Content filters: DaRe, Org Unit, BRIE, Guard, SCIM
- Time-based: Recent modifications (May 2026)

**Limitations:**
- Jira workitem search encountered syntax limitations
- Some team member details redacted or deactivated
- Page content truncated in some API responses
- Access to some private/archived pages may be restricted

---

**Report Generated:** May 1, 2026, 08:35 UTC
**Data Currency:** Latest confluence modifications as of May 1, 2026
**Prepared For:** Core Engineering Leadership & Identity Team Stakeholders
