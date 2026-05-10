# New Project Candidates - Detailed Gap Analysis

**Analysis Date:** 2026-05-01  
**Total New Project Candidates:** 90 tickets  
**Recommended New Initiatives:** 5-7 strategic projects

## Executive Summary

Analysis of 90 "NEW / Unclassified" ENT tickets reveals 5 clear strategic gaps and opportunity areas for new CoreEng projects:

1. **Governance & Policy Engine** (15+ tickets) - P0/P1 priority
2. **Rovo Platform Expansion** (8+ tickets) - P1 priority
3. **Enterprise Admin Tooling** (12+ tickets) - P2 priority
4. **Advanced Compliance** (8+ tickets) - P1 priority
5. **Scale & Performance Initiative** (5+ tickets) - P1/P2 priority

---

## 1. Governance & Policy Engine (NEW - P0/P1)

**Signal Strength:** 🔴 CRITICAL - P0 blocker identified  
**Customer Impact:** 15+ ENT tickets, multiple enterprise customers blocked  
**Estimated Scope:** Large (6-9 months)

### Candidate Tickets
- **ENT-3824** (P0) - Platform-native lifecycle governance for large-scale multi-site enterprises
- **ENT-1690** (P1) - Ability to configure what enterprise org level data is available
- **ENT-351** (P1) - Modify how app approvals work in enterprise environments
- **ENT-2625** - Ability to deactivate users who haven't logged in
- **ENT-2089** - Create a Migration / Data Management Admin role
- **ENT-3692** - Ability to select Atlassian Teams scope (site vs org)
- **ENT-1786** - Allow admins to remove "Discover" and other products
- ENT-2303, ENT-35, and ~7 others

### Problem Statement
Enterprise customers need **platform-wide governance controls** that span:
- Data visibility & access controls (org-level, team-level, department-level)
- Lifecycle management (user onboarding/offboarding automation)
- Policy enforcement (app approvals, content restrictions, access rules)
- Admin role granularity (data managers, compliance officers, team admins)

### Recommended Solution
**New Project: "Enterprise Governance Engine"**
- Unified policy definition & enforcement across Jira, Confluence, JSM
- Admin role hierarchy with delegation
- Lifecycle automation (users, content, apps)
- Audit trail for all governance actions
- Integrates with: Identity & IAM, ALP, Compliance/RegInd

### Estimated Resource Requirement
- 2-3 engineers + 1 PM + 1 designer
- 6-9 months to MVP
- Dependencies: Identity & IAM, ALP infrastructure

---

## 2. Rovo Platform Expansion (NEW - P1)

**Signal Strength:** 🟠 HIGH - 8+ tickets + strategic product direction  
**Customer Impact:** AI/automation, developer experience  
**Estimated Scope:** Medium-Large (4-6 months per phase)

### Candidate Tickets
- **ENT-3595** (P1) - Rovo skill to read Jira Dashboards (and widgets)
- **ENT-3354** (P1) - Allow Rovo Agents to search multiple sites
- **ENT-3696** - Ability to identify content/work authored by Rovo
- **ENT-3675** - Enhance Rovo audit logging and observability
- **ENT-2840** (P2) - JSM (Assets, Forms, Data Manager) Rovo Connector enhancements
- ENT-2460, ENT-3782, and others

### Problem Statement
Rovo is the **connective tissue for enterprise automation**, but currently:
- Limited to specific Jira/Confluence views (no Dashboards, Forms, Assets)
- Single-site only (enterprise has multiple sites)
- Minimal audit/observability (compliance gap)
- No usage analytics (FinOps gap)

### Recommended Solution
**New Project: "Rovo Platform v2"**
- Phase 1: Multi-site aggregation + Dashboard support (2-3 months)
- Phase 2: Extended API coverage (Forms, Assets, Service Desk) (2 months)
- Phase 3: Observability & audit logging (1-2 months)
- Integrates with: Eng Excellence, ALP, FinOps

### Estimated Resource Requirement
- 2-3 engineers + 1 PM
- 4-6 months phased rollout
- Depends on: MCP server improvements, API stability

---

## 3. Enterprise Admin Tooling (NEW - P2)

**Signal Strength:** 🟠 MEDIUM-HIGH - 12+ operational tickets  
**Customer Impact:** Operational efficiency, compliance  
**Estimated Scope:** Medium (4-5 months)

### Candidate Tickets
- **ENT-3730** (P1) - Ability to create Cloud Sites from set Enterprise Templates
- **ENT-3728** - Mobile App admin settings at site level
- **ENT-3665** - IP range restrictions for Service Account network controls
- **ENT-3631** - Service Accounts in AGC
- **ENT-2625** - User deactivation based on activity
- **ENT-2225** - App usage for Confluence
- **ENT-1804** - Ability to mask sensitive content
- ENT-3746, ENT-2787, ENT-2788, and others

### Problem Statement
Enterprise admins lack **self-service tools** for:
- Site provisioning from templates (reducing CSM manual work)
- Network security controls (IP restrictions for service accounts)
- Activity-based lifecycle management
- Content sensitivity classification
- Usage analytics & app governance

### Recommended Solution
**New Project: "Enterprise Admin Hub"**
- Self-service site provisioning with templates
- Network & service account security controls
- User activity analytics & automation
- App usage tracking & governance APIs
- Content classification & masking policies
- Integrates with: Identity & IAM, FinOps, Eng Excellence

### Estimated Resource Requirement
- 2-2.5 engineers + 1 PM
- 4-5 months to MVP
- Dependencies: Identity & IAM, Analytics infrastructure

---

## 4. Advanced Compliance Certifications (NEW - P1/P2)

**Signal Strength:** 🟠 HIGH - 8+ compliance-specific tickets  
**Customer Impact:** Market access (Europe, US, LATAM, APAC)  
**Estimated Scope:** Medium (3-4 months per certification)

### Candidate Tickets
- **ENT-3739** - Atlassian-hosted LLMs with EU Data Residency
- **ENT-3702** - FedRamp | Docusign Feature
- **ENT-3680** - Rovo C5: Cloud Computing Compliance Catalog
- **ENT-3672** - Spanish ENS certification for Spanish public sector
- **ENT-2289** - FedRAMP High
- **ENT-2864** - Customer retention policy for compliance
- ENT-293, ENT-2745, and others

### Problem Statement
Enterprise customers face **regional compliance barriers**:
- EU: C5, GDPR data residency, Spanish ENS
- US: FedRAMP High, IL5/IL6 requirements
- APAC: Limited options
- Global: Lack of LLM governance for AI features

### Recommended Solution
**Expand Compliance/RegInd project** OR **new "Compliance Extensions" project**
- LLM data residency controls
- FedRAMP High documentation & infrastructure
- Spanish ENS audit & certification
- C5 compliance controls
- Integrates with: Encryption/BYOK, ALP, existing Compliance/RegInd

### Estimated Resource Requirement
- 1-2 engineers + compliance consultant (contract)
- 3-4 months per major certification
- Phased: EU (Q3), US (Q4), APAC (Q1)

---

## 5. Scale & Performance Initiative (NEW - P1/P2)

**Signal Strength:** 🟠 HIGH - 5+ scale-specific tickets  
**Customer Impact:** Large customer support (150K+ users, vertical scale)  
**Estimated Scope:** Large (6-8 months)

### Candidate Tickets
- **ENT-1703** (P1) - Enterprise support for 150K+ sites
- **ENT-2643** - Increase user provisioning limits
- **ENT-2199** - Jira vertical scale 50K-100K users
- **ENT-1520** - Confluence capabilities for 150K+ users
- **ENT-1697** - Gliffy app Confluence performance issues

### Problem Statement
Current limits insufficient for **largest enterprise deployments**:
- 150K user limit reached (PwC scale)
- Jira user/instance limits cap at 50K
- Confluence performance degrades at scale
- Third-party app performance issues
- No clear upgrade path

### Recommended Solution
**Expand Scale/CRSP project** OR create **"Enterprise Scale Initiative"**
- Horizontal & vertical scaling beyond current limits
- Performance baselines & optimization for large instances
- Third-party app vetting for scale
- Capacity planning tools
- Integrates with: TDP, Eng Excellence, Infrastructure

### Estimated Resource Requirement
- 3-4 engineers + 1 PM + 1 infrastructure specialist
- 6-8 months for foundational work
- Ongoing: quarterly scale optimization

---

## Supporting New Project Candidates (Lower Priority)

### Multi-Site & Environment Management (P2)
- **ENT-3707** - Copy Rovo agents between sandbox and production
- **ENT-2460** - AI Processing in Europe
- Related to TSP/Sandbox expansion

### Enterprise Data APIs (P2)
- **ENT-3736, ENT-3738** - Public APIs for regulated data capture
- **ENT-3745** - REST API via custom domains
- **ENT-2409** - Detailed billing via REST API

### Content Control & Masking (P3)
- **ENT-1804** - Mask sensitive content
- **ENT-3737** - Comment edit history for regulated users

---

## Strategic Recommendations

### Immediate Actions (This Week)
1. **Approve Governance Engine** - P0 blocker requires immediate triage
2. **Align on Rovo roadmap** - Already strategic, needs formalization
3. **Scope Admin Tooling** - Quick wins for customer retention

### Q2/Q3 Decisions
1. New vs. distributed approach for Governance (new project vs. Identity/Compliance expansion)
2. Compliance Extensions: phased approach & resource allocation
3. Scale Initiative: establish baseline performance metrics

### Resource Planning
- **Immediate (Governance):** 2-3 engineers
- **Phase 1 (Rovo + Admin):** 4-5 engineers + 2 PMs
- **Phase 2 (Compliance + Scale):** 5-6 engineers + 1 PM + specialists

### Total Estimated Effort
- **MVP across 3 major initiatives:** 12-15 engineers, 3-4 PMs, 3-4 months
- **Full scope (all 5):** 18-22 engineers, 4-5 PMs, 6-9 months

---

## Metrics for Success

### Governance Engine
- Reduce customer governance requests by 80%
- Support 10+ enterprise accounts with <10K user limits

### Rovo Platform v2
- +200% increase in Rovo agent usage
- Multi-site adoption in 5+ enterprise accounts

### Admin Hub
- 50% reduction in CSM time for provisioning
- +15% customer satisfaction (admin experience)

### Compliance Extensions
- 3+ new certifications achieved (C5, ENS, FedRAMP High)
- Market access to 5+ new geographies

### Scale Initiative
- Support 500K+ total users across all instances
- +30% retention for largest customers

---

**Next Step:** Schedule working session with CoreEng leadership to prioritize and scope these initiatives.
