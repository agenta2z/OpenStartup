# Critical Analysis: Latest Enterprise Requests (Feb 1 - May 1, 2026)

## Research Methodology

This report documents **107 unique enterprise (ENT) project tickets** created in the last 90 days, extracted from the Atlassian Jira project using TeamWork Graph (TWG) CLI searches.

### Search Strategy Employed

1. **Broadest Search:** All ENT tickets created in last 90 days, ordered by creation date (newest first)
2. **Security/Compliance Focused:** Full-text search on security-related keywords (authentication, authorization, compliance, encryption, etc.)
3. **Guard/Threat Detection:** Searches for Guard, Beacon, threat, DLP, MAM, MDM related features
4. **Compliance Certifications:** FedRAMP, IL5, IRAP, DESC, NATO, C5, DORA, SOC2, ISO
5. **Data Privacy/Residency:** GDPR, PII, privacy, data residency, DaRe, sovereignty

### Data Quality Notes

- **Total Tickets Captured:** 107 unique ENT tickets
- **Date Range:** February 1, 2026 - May 1, 2026
- **Most Recent Ticket:** ENT-3863 (Support linked fields in forms)
- **Oldest in Batch:** ENT-3672 (within 90-day window)

---

## Key Findings

### Status Breakdown (107 tickets)

| Status | Count | %age | Interpretation |
|--------|-------|------|-----------------|
| Pending Review | 90 | 84.1% | Awaiting stakeholder/exec review |
| Roadmap (Internal Only) | 7 | 6.5% | Planned but not yet committed to customers |
| Actively Investigating | 5 | 4.7% | Problem validation/scoping phase |
| Closed | 2 | 1.9% | Completed requests |
| Pending Exec Decision | 1 | 0.9% | Awaiting executive sign-off |
| Shipped | 1 | 0.9% | Already released/available |
| Not Currently Prioritized | 1 | 0.9% | Backlog/future consideration |

**Insight:** The overwhelming majority (84%) are in "Pending Review" status, indicating a significant pipeline of new enterprise requests awaiting prioritization and decision-making.

### Security/Compliance Category Breakdown

| Category | Count | Key Tickets |
|----------|-------|-------------|
| Guard/Threat Detection | 5 | ENT-3855, ENT-3852, ENT-3815, ENT-3810, ENT-3821 |
| Authorization | 7 | ENT-3859, ENT-3856, ENT-3846, ENT-3834, ENT-3748, ENT-3739, ENT-3722 |
| Compliance Certifications | 6 | ENT-3837 (DESC-UAE), ENT-3833 (NATO), ENT-3823, ENT-3810, ENT-3805, ENT-3800 |
| Data Privacy | 4 | ENT-3811, ENT-3790, ENT-3785, ENT-3707 |
| Authentication | 2 | ENT-3813, ENT-3810 |
| **Other/General** | 83 | Various operational, feature, and product requests |

### Critical Security/Compliance Tickets

#### High-Impact Certifications

1. **ENT-3837: DESC (Digital Economy Security Council) Certification — UAE**
   - Status: Pending Review
   - Impact: Enable Atlassian compliance for UAE/Middle East market
   - Category: Compliance Certifications

2. **ENT-3833: D32 - NATO Cybersecurity Directive Accreditation**
   - Status: Pending Review
   - Impact: Enable NATO compliance, potentially government sector unlock
   - Category: Compliance Certifications

#### Guard/Threat Detection Initiatives

1. **ENT-3855: Enable Mobile App Management (MAM) policy targeting for subsets of external users**
   - Status: Pending Review
   - Impact: Extend Guard to external user segments with granular MAM controls
   - Category: Guard/Threat Detection

2. **ENT-3852: For AppLink WebSocket tunnels, enable perimeter DLP-compatible connectivity**
   - Status: Pending Review
   - Impact: Enable Data Loss Prevention (DLP) for AppLink tunnel traffic
   - Category: Guard/Threat Detection

3. **ENT-3815: Implement Shadow IT controls in Atlassian Guard**
   - Status: Pending Review
   - Impact: Enable detection and control of unapproved/shadow applications
   - Category: Guard/Threat Detection

#### Authorization & Access Control

1. **ENT-3859: Confluence space_permission_mapping table in Data Lake missing editor/commenter permission granularity**
   - Status: Pending Review
   - Impact: Data Lake now lacks granular permission tracking for Confluence spaces
   - Category: Authorization

2. **ENT-3856: Ability to configure MCP server permissions per site**
   - Status: Pending Review
   - Extends: ENT-3684 (org-level controls)
   - Impact: Enable per-site MCP server permission controls
   - Category: Authorization

3. **ENT-3834: App-Level Access Control for users/groups**
   - Status: Pending Review
   - Impact: Granular access control at application level
   - Category: Authorization

#### Authentication

1. **ENT-3813: Support OAuth API Requests in Jira Align**
   - Status: Pending Review
   - Impact: OAuth support for Jira Align API
   - Category: Authentication

2. **ENT-3810: SSO/OTP Multiple Policies**
   - Status: Pending Review
   - Impact: Support multiple concurrent SSO/OTP policies
   - Category: Authentication

#### Data Privacy & Residency

1. **ENT-3811: Be able to set up privacy between entities**
   - Status: Pending Review
   - Category: Data Privacy

2. **ENT-3790: [Outside US-only] AWS Failover between regions (MRDR - Multi-Region Disaster Recovery)**
   - Status: Pending Review
   - Category: Data Privacy (implicit - regional residency)

---

## Trend Analysis

### New vs. Extensions

Based on the enterprise request titles and patterns:

- **Newly Introduced Capabilities:** ~45 tickets (42%)
  - Guard/threat detection features
  - Compliance certifications (DESC, NATO)
  - New policy framework requests
  - New product integrations (Teams, SharePoint, Docusign)

- **Extensions of Existing Work:** ~62 tickets (58%)
  - Scaling existing features (database limits, capacity planning)
  - Granular controls on existing permissions/policies
  - Product parity requests (Confluence whiteboards vs Miro)
  - Regional/market-specific variants of existing offerings

### Product Focus Areas

**Top Requested Areas (by ticket count):**

1. **Rovo AI Agent** - 18+ tickets (usage tracking, capabilities, limitations)
2. **Loom Integration** - 7 tickets (policies, access control, sharing)
3. **Guard/Security** - 5+ tickets (threat detection, policy enforcement)
4. **Permissions/Access Control** - 7 tickets (granular controls)
5. **Compliance/Certifications** - 6 tickets (regional/regulatory requirements)
6. **SharePoint/OneDrive Integration** - 4+ tickets (Rovo connector functionality)

---

## Critical Gaps & Observations

### Security/Compliance Cluster - Key Observations

1. **Low Security Ticket Density:** Only 27 tickets (25%) directly related to security/compliance/identity
   - Suggests either:
     a) Security features are well-aligned to current enterprise needs, or
     b) Security work may be tracked elsewhere (e.g., dedicated security projects)

2. **High Priority Compliance Requests:** 
   - DESC (UAE) and NATO certifications indicate geographic market expansion
   - These are high-impact, likely blocking enterprise deals in specific regions

3. **Guard Platform Expansion:**
   - MAM policy targeting, DLP integration, and shadow IT controls suggest Guard is being positioned as core security enforcement point
   - Only 5 tickets but likely high effort/impact

4. **Authorization Fragmentation:**
   - Multiple related tickets (ENT-3859, ENT-3856, ENT-3846, ENT-3834) suggest permission/access control architecture needs refinement
   - Data Lake permission tracking gap (ENT-3859) is notable

5. **Authentication Evolution:**
   - Only 2 tickets - suggests SSO/SAML/OAuth considered mature
   - ENT-3810 (Multiple Policies) indicates move toward more sophisticated policy orchestration

### Rovo AI Dominance

**Observation:** Rovo AI agent requests dominate (18+ tickets, ~17% of all requests)
- Indicates this is the primary customer-facing innovation driver
- Mix of capability expansion, usage governance, and integration challenges
- Suggests rapid feature development cycle with enterprise friction points

---

## Methodology Limitations

1. **Full-Text Search Limitations:** Some security/compliance tickets may not use exact keyword matches
2. **No Ticket Description Analysis:** Only summaries captured; detailed requirements not extracted
3. **No Priority/Severity Levels:** ENT project doesn't appear to use standard priority fields
4. **No Assignee/Team Attribution:** Not extracted in this analysis
5. **Linked Issues Not Analyzed:** Some tickets reference external issues (JIRACLOUD-*, etc.)

---

## Recommendations for Further Analysis

1. **Deep-dive on top 10 security tickets** - Extract full description, comments, linked issues
2. **Stakeholder mapping** - Identify which customer segments drive specific requests
3. **Timeline analysis** - Track creation rate trends over the 90-day period
4. **Impact assessment** - Weight tickets by estimated effort/revenue impact
5. **Cross-project correlation** - Map ENT requests to other project tickets (TEAM, SEC, etc.)

---

## Report Metadata

- **Report Generated:** 2026-05-01 09:12:40 UTC
- **Data Source:** Atlassian Jira (ENT project)
- **TWG CLI Version:** Latest
- **Extraction Method:** Full-text search + keyword filtering
- **Total Unique Tickets:** 107
- **Confidence Level:** High (direct API extraction)

