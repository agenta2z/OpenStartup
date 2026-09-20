# 📑 Research Output Index - Atlassian Enterprise Requests (Feb 1 - May 1, 2026)

## 🎯 Quick Navigation

### Start Here
- **README.md** - Complete overview and research summary
- **02_critical_analysis.md** - Strategic insights and key findings

### Data Files
- **raw_batch_a_security_compliance.json** - Machine-readable export (JSON format)
- **all_enterprise_issues.json** - Complete ticket database

### Detailed Reports
- **01_security_compliance_identity_requests.md** - Full security/compliance catalog
- **02_scale_integration_rovo_ai_requests.md** - Scale, integration, and Rovo requests
- **03_governance_admin_data_requests.md** - Governance and admin requests

---

## 📊 Research Metrics at a Glance

```
Total Tickets Extracted:        107
┌─────────────────────────────┐
├─ Security/Compliance:       27 (25%)
│  ├─ Guard/Threat Detection:  5
│  ├─ Compliance Certs:         6
│  ├─ Authorization:            7
│  ├─ Data Privacy:             4
│  └─ Authentication:           2
├─ Rovo AI Related:           18+ (17%)
├─ Scale/Integration:          20+ (19%)
└─ Other/Operational:          34+ (32%)

Status Distribution:
├─ Pending Review:    90 (84%)
├─ Roadmap:            7 (6.5%)
├─ Investigating:      5 (4.7%)
├─ Closed:             2 (1.9%)
├─ Pending Decision:   1 (0.9%)
├─ Shipped:            1 (0.9%)
└─ Not Prioritized:    1 (0.9%)
```

---

## 🔐 Top Security/Compliance Tickets

| # | Key | Summary | Status | Impact |
|---|-----|---------|--------|--------|
| 1 | ENT-3837 | DESC Certification (UAE) | Pending Review | 🔴 High - Market unlock |
| 2 | ENT-3833 | NATO Cybersecurity Accreditation | Pending Review | 🔴 High - Gov sector |
| 3 | ENT-3855 | MAM policy targeting (external users) | Pending Review | 🟡 Medium - Guard expansion |
| 4 | ENT-3852 | DLP-compatible AppLink tunnels | Pending Review | 🟡 Medium - DLP integration |
| 5 | ENT-3815 | Shadow IT controls in Guard | Pending Review | 🟡 Medium - Threat detection |
| 6 | ENT-3859 | Data Lake permission granularity | Pending Review | 🟡 Medium - Auth gap |
| 7 | ENT-3856 | MCP per-site permissions | Pending Review | 🟡 Medium - Fine-grained control |
| 8 | ENT-3810 | SSO/OTP multiple policies | Pending Review | 🟢 Low - Auth maturity |
| 9 | ENT-3813 | OAuth API for Jira Align | Pending Review | 🟢 Low - Feature parity |
| 10 | ENT-3811 | Entity-level privacy setup | Pending Review | 🟢 Low - Data privacy |

---

## 📈 Key Findings

### 1. Guard Platform Expansion 🛡️
- **5 dedicated tickets** for threat detection, MAM, DLP integration
- Clear positioning as core security enforcement point
- Expanding from user access to perimeter security

### 2. Compliance Certification Drive 🏆
- **2 major certifications** in pipeline (DESC, NATO)
- Indicate geographic market expansion (UAE, government sectors)
- Likely blocking enterprise deals in specific regions

### 3. Authorization Architecture Evolution 🔑
- **7 tickets** related to access control and permissions
- Data Lake permission tracking gap (ENT-3859) is notable
- Fine-grained per-site controls becoming standard expectation

### 4. Rovo AI Dominance 🤖
- **18+ tickets** (17% of all requests)
- Primary innovation driver for enterprise features
- Usage governance and integration friction points evident

### 5. Enterprise Scale Challenges 📈
- **20+ tickets** related to scaling, capacity, and multi-site management
- Database size limits (Jira 300GB, Confluence 32GB) being hit
- Multi-region disaster recovery (MRDR) requests increasing

---

## 🔍 Search Methodology

### JQL Queries Used

```jql
# Query 1: All new ENT tickets (last 90 days, newest first)
project = ENT AND created >= -90d ORDER BY created DESC

# Query 2: Security/Compliance/Identity focus
project = ENT AND created >= -90d AND (
  text ~ "security" OR text ~ "identity" OR text ~ "compliance" 
  OR text ~ "access control" OR text ~ "permission" 
  OR text ~ "authentication" OR text ~ "SSO" OR text ~ "SAML" 
  OR text ~ "MFA" OR text ~ "certificate" OR text ~ "encryption"
) ORDER BY created DESC

# Query 3: Guard/Threat Detection
project = ENT AND created >= -90d AND (
  text ~ "Guard" OR text ~ "Beacon" OR text ~ "threat" 
  OR text ~ "DLP" OR text ~ "MAM" OR text ~ "MDM"
) ORDER BY created DESC

# Query 4: Compliance Certifications
project = ENT AND created >= -90d AND (
  text ~ "FedRAMP" OR text ~ "IL5" OR text ~ "IRAP" 
  OR text ~ "DESC" OR text ~ "NATO" OR text ~ "C5" 
  OR text ~ "DORA" OR text ~ "SOC2" OR text ~ "ISO"
) ORDER BY created DESC

# Query 5: Data Privacy/Residency
project = ENT AND created >= -90d AND (
  text ~ "data residency" OR text ~ "DaRe" OR text ~ "GDPR" 
  OR text ~ "PII" OR text ~ "privacy" OR text ~ "sovereignty"
) ORDER BY created DESC
```

### Data Extraction Method
- **Source:** Atlassian Cloud Jira API via TWG CLI
- **No Sampling:** 100% of tickets within date range
- **Confidence:** High - direct API extraction
- **Tool:** `/Users/tchen7/.agents/skills/twg/scripts/twg`

---

## 📁 File Directory

```
latest_enterprise_requests/
├── INDEX.md                                    (This file - Navigation guide)
├── README.md                                   (Research overview - START HERE)
├── 02_critical_analysis.md                     (Strategic insights - KEY FINDINGS)
│
├── DETAILED REPORTS
│   ├── 01_security_compliance_identity_requests.md   (39 KB - Security focus)
│   ├── 02_scale_integration_rovo_ai_requests.md      (21 KB - Scale/Rovo)
│   ├── 03_governance_admin_data_requests.md          (34 KB - Governance)
│   └── 05_master_coreng_mapping.md                   (42 KB - Master index)
│
├── DATA EXPORTS
│   ├── raw_batch_a_security_compliance.json    (32 KB - JSON export)
│   ├── raw_batch_b_scale_integration_rovo.json (78 KB - JSON export)
│   └── all_enterprise_issues.json              (22 KB - All tickets)
│
└── ADDITIONAL ANALYSIS
    ├── 06_priority_matrix_new_requests.md      (2.4 KB - Priority scoring)
    ├── 07_NEW_PROJECT_CANDIDATES.md            (9.8 KB - Potential new projects)
    └── RESEARCH_COMPLETE.md                    (5.3 KB - Completion status)
```

---

## 🎓 How to Use This Research

### For Strategic Planning
1. Read **README.md** (overview)
2. Review **02_critical_analysis.md** (insights)
3. Check **07_NEW_PROJECT_CANDIDATES.md** (new initiatives)

### For Tactical Implementation
1. Import **raw_batch_a_security_compliance.json** into your database
2. Reference **01_security_compliance_identity_requests.md** for ticket details
3. Use **06_priority_matrix_new_requests.md** for prioritization

### For Customer/Sales Enablement
1. Extract high-impact tickets from **01_security_compliance_identity_requests.md**
2. Highlight compliance certifications (DESC, NATO)
3. Showcase Guard platform expansion and Rovo AI capabilities

### For Product Team Coordination
1. Review **05_master_coreng_mapping.md** for cross-project dependencies
2. Check **RESEARCH_COMPLETE.md** for detailed status breakdown
3. Use JSON exports for dashboarding and tracking

---

## ⚡ Key Insights Summary

### What's Driving Enterprise Requests?

1. **Compliance & Certifications** (25% of tickets)
   - Regional market expansion requirements
   - Government/public sector unlocks
   - High-impact, deal-blocking items

2. **AI & Automation** (17% of tickets)
   - Rovo agent capabilities expansion
   - Usage governance and control
   - Integration with enterprise systems

3. **Enterprise Scale** (19% of tickets)
   - Database size limits being exceeded
   - Multi-site/multi-region management
   - Performance at scale

4. **Security & Governance** (Ongoing)
   - Guard platform as security enforcement point
   - Fine-grained access control architecture
   - Data residency and privacy controls

### What's NOT Being Requested?

- **Auth platform overhaul** - Only 2 tickets (SSO/SAML mature)
- **Jira/Confluence core rewrites** - Evolution, not revolution
- **Major API changes** - Generally backward compatible
- **Moonshot features** - All requests are tactical/strategic

---

## 📞 Research Metadata

| Property | Value |
|----------|-------|
| Report Generated | 2026-05-01 09:13 UTC |
| Data Range | 2026-02-01 to 2026-05-01 (90 days) |
| Total Tickets | 107 |
| Security Tickets | 27 |
| Extraction Method | Atlassian TWG CLI + JQL |
| Data Quality | High (100% coverage, no sampling) |
| Researcher | Rovo Dev Agent |
| Cloud Instance | Atlassian Cloud (SaaS) |
| Cloud ID | a436116f-02ce-4520-8fbb-7301462a1674 |

---

## 🚀 Next Steps Recommended

### Immediate (Week 1)
- [ ] Review README and critical analysis
- [ ] Identify top 5 security/compliance tickets requiring immediate action
- [ ] Assess DESC and NATO certification timelines

### Short-term (Month 1)
- [ ] Extract full descriptions for top 20 tickets
- [ ] Map tickets to teams/owners
- [ ] Identify critical dependencies and blockers

### Medium-term (Quarter)
- [ ] Analyze customer impact and revenue correlation
- [ ] Plan quarterly/annual roadmap based on findings
- [ ] Monitor ticket status transitions weekly

### Long-term (Year)
- [ ] Trend analysis across multiple quarters
- [ ] ROI assessment of implemented features
- [ ] Customer satisfaction correlation

---

**For detailed information, please reference the specific markdown and JSON files listed above.**

**Questions? Refer to the README.md or 02_critical_analysis.md for full context.**

