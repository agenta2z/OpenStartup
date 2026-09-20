# Legacy Enterprise Requests (ENT-1 to ENT-2883)
**Generated:** 2026-05-01 09:35:06
**Purpose:** Track active pre-3000 ENT tickets relevant to CoreEng planning

---

## Executive Summary

- **Total Legacy Tickets Analyzed:** 50
- **Shipped/Resolved:** 10 (20%)
- **Active (Roadmap/Investigating/Pending):** 39 (78%)
- **Not Prioritized:** 1 (2%)

### Status Breakdown

| Status | Count | Tickets |
|--------|-------|---------|
| **Shipped** | 10 | ENT-166, ENT-555, ENT-1155, ENT-1909, ENT-1929... |
| **Active** | 39 | ENT-50, ENT-59, ENT-151, ENT-293, ENT-311... |
| **Not Prioritized** | 1 | ENT-398 |

---

## SECTION A: SHIPPED / RESOLVED TICKETS (10)

These represent work completed and shipped to customers.


### ALP (Audit Logging Platform)

- **ENT-166:** Audit log access for site admins

### BRIE

- **ENT-1909:** Support for backup direct to 3rd party cloud storage (AWS S3) 
- **ENT-1929:** Support full backups with attachments for instances with large storage usage ( > 3TB)
- **ENT-1983:** Increase size limit for site backup imports (<3TB)
- **ENT-2331:** Support daily backups of Cloud products

### FinOps/Analytics

- **ENT-2122:** REST API capabilities for Atlassian Analytics

### Identity (Rocket/Fortress)

- **ENT-555:** Single Logout - Logging out of Atlassian account does not log out of SAML provider (IdP)

### Identity (SCIM/UUL)

- **ENT-2643:** Increase Atlassian user base and user provisioning limits to 800k users and =< 100 sites

### Multiple (Identity, TDP, Micros)

- **ENT-1155:** Immature Data Governance / Data Lifecycle Operational Processes Erode Customer Trust

### Scale/CRSP

- **ENT-2199:** Jira: Vertical scale 50K-100k users per instance


---

## SECTION B: ACTIVE TICKETS (39)

These tickets are on roadmaps or actively being investigated. They represent priority work for CoreEng planning.


### ALP (Audit Logging Platform)

| Key | Summary | Status | DRI |
|-----|---------|--------|-----|
| ENT-1057 | Audit Log Retention for 12 months for AGP customers... | Public Roadmap | Akshay Nambiar |

### ALP + Identity

| Key | Summary | Status | DRI |
|-----|---------|--------|-----|
| ENT-2883 | Embeddable audit logs for Jira/JSM... | Roadmap (Internal Only) | Akshay Nambiar |

### BRIE

| Key | Summary | Status | DRI |
|-----|---------|--------|-----|
| ENT-151 | Export all of my cloud data for long term storage in a "readable format"... | Roadmap (Internal Only) | Lakshmi Behl |
| ENT-311 | Apps backup and restore with 30 days retention... | Roadmap (Internal Only) | Lakshmi Behl |

### Compliance (Isolated Cloud/Oasis)

| Key | Summary | Status | DRI |
|-----|---------|--------|-----|
| ENT-2745 | Virtual Private / Isolated cloud... | Public Roadmap | Wayne Yim |

### Compliance/Identity (DaRe)

| Key | Summary | Status | DRI |
|-----|---------|--------|-----|
| ENT-59 | Guarantee that my organisation's user account account information (PII) is store... | Roadmap (Internal Only) | Peter Wang / Amaranath Dabbara |

### Compliance/RegInd (FedRAMP)

| Key | Summary | Status | DRI |
|-----|---------|--------|-----|
| ENT-2289 | FedRAMP High... | Public Roadmap | Wayne Yim |

### Encryption (CMK)

| Key | Summary | Status | DRI |
|-----|---------|--------|-----|
| ENT-1958 | Support AWS-XKS with Customer-managed keys (CMK)... | Public Roadmap | Greg Zaney |
| ENT-2085 | CMK (BYOK) - Apply Customer-managed keys retroactively on existing site... | Public Roadmap | Greg Zaney |

### Identity

| Key | Summary | Status | DRI |
|-----|---------|--------|-----|
| ENT-351 | Modify how app approvals work in enterprise environments... | Roadmap (Internal Only) | Prashant Ghosal |
| ENT-652 | App migration content access problems - Restricted pages... | Roadmap (Internal Only) | Prashant Ghosal |

### Identity (Admin Hub Scale)

| Key | Summary | Status | DRI |
|-----|---------|--------|-----|
| ENT-1703 | Enterprise support (by exception) for site count above 150, up to 2,000... | Roadmap (Internal Only) | Prashant Ghosal |

### Identity (License Decoupling)

| Key | Summary | Status | DRI |
|-----|---------|--------|-----|
| ENT-764 | Purchase Apps for a subset of users on an instance... | Roadmap (Internal Only) | Prashant Ghosal |

### Identity (Org Isolation)

| Key | Summary | Status | DRI |
|-----|---------|--------|-----|
| ENT-1690 | Ability to configure what enterprise org level data is available to each enterpr... | Public Roadmap | Prashant Ghosal |

### Identity (Rocket/Fortress)

| Key | Summary | Status | DRI |
|-----|---------|--------|-----|
| ENT-2303 | Single Logout - Atlassian Account should support IdP-initiated single logouts... | Pending Review | Prashant Ghosal |

### Identity/Admin APIs

| Key | Summary | Status | DRI |
|-----|---------|--------|-----|
| ENT-2089 | Create a Migration / Data Management Admin role... | Roadmap (Internal Only) | Prashant Ghosal |

### Scale/CRSP

| Key | Summary | Status | DRI |
|-----|---------|--------|-----|
| ENT-1520 | Expand Confluence Capabilities to Support Customer Size 150K-250K for a single s... | Public Roadmap | CRSP Team |

### TDP + ALP

| Key | Summary | Status | DRI |
|-----|---------|--------|-----|
| ENT-2864 | Customer can retain data up to n years to meet compliance needs... | Roadmap (Internal Only) | TBD |

### TSP (Flip2Prod)

| Key | Summary | Status | DRI |
|-----|---------|--------|-----|
| ENT-50 | EAP for the Ability to push (promote) Jira and JSM config data from sandbox to p... | Public Roadmap | Harpreet Singh Juneja |

### TSP + TDP

| Key | Summary | Status | DRI |
|-----|---------|--------|-----|
| ENT-2124 | Support large total attachment size in Confluence Sandbox creation... | Actively Investigating | Harpreet Singh Juneja |

### Unknown - Verify

| Key | Summary | Status | DRI |
|-----|---------|--------|-----|
| ENT-1158 | Audit Logs for Admin pages... | Actively Investigating | TBD |
| ENT-1555 | Google CloudSQL and Cloud storage support for Atlassian products (Jira, JSM and ... | Actively Investigating | TBD |
| ENT-1638 | Jira Data Center WCAG 2.1 AA Conformance Required... | Actively Investigating | TBD |
| ENT-1697 | Gliffy app for Confluence cloud - performance issues... | Actively Investigating | TBD |
| ENT-1786 | [Cloud] Allow admins to remove the "Discover" and other products from the "Switc... | Actively Investigating | TBD |
| ENT-1804 | Ability to mask sensitive content... | Actively Investigating | TBD |
| ENT-2225 | App usage for Confluence... | Actively Investigating | TBD |
| ENT-2347 | Object level controls or permissions for Goals... | Actively Investigating | TBD |
| ENT-2409 | Ability to retrieve detailed billing information via REST API... | Actively Investigating | TBD |
| ENT-2460 | AI Processing in Europe... | Actively Investigating | TBD |
| ENT-2590 | REST API usage insights... | Actively Investigating | TBD |
| ENT-2625 | Ability to deactivate users who haven't logged in for a period of time... | Actively Investigating | TBD |
| ENT-2667 | Automation Rules Should be Included in Jira Backups (Back up and Restore)... | Actively Investigating | TBD |
| ENT-2787 | Improve public customer facing documentation around how app versions and release... | Actively Investigating | TBD |
| ENT-2788 | Improve cloud app version visibility and information on the Marketplace app list... | Actively Investigating | TBD |
| ENT-2840 | JSM (Assets, Forms, Data Manager) [Rovo Connector Enhancements]... | Actively Investigating | TBD |
| ENT-2858 | Improve Visibility of Upcoming Features in Release Tracks and Bundled Updates... | Actively Investigating | TBD |
| ENT-2880 | Support "Scalable Silos" complex company archetype. ... | Actively Investigating | TBD |
| ENT-293 | US Classified/Top Secret/Secret Cloud deployment + IL6/ Disconnected / Airgapped... | Actively Investigating | TBD |


---

## SECTION C: NOT PRIORITIZED (1)

These tickets are deferred or have low priority.

- **ENT-398:** Customer-managed keys (CMK) with AWS Cloud HSM solutions


---

## SECTION D: DETAILED TICKET REFERENCE

### Shipped Tickets (Complete List)


#### ENT-166
- **Summary:** Audit log access for site admins
- **Status:** Shipped
- **CoreEng Pillar:** ALP (Audit Logging Platform)
- **DRI:** Akshay Nambiar
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-166
- **Priority:** Not set
- **Updated:** None

#### ENT-555
- **Summary:** Single Logout - Logging out of Atlassian account does not log out of SAML provider (IdP)
- **Status:** Shipped
- **CoreEng Pillar:** Identity (Rocket/Fortress)
- **DRI:** Prashant Ghosal
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-555
- **Priority:** Not set
- **Updated:** None

#### ENT-1155
- **Summary:** Immature Data Governance / Data Lifecycle Operational Processes Erode Customer Trust
- **Status:** Shipped
- **CoreEng Pillar:** Multiple (Identity, TDP, Micros)
- **DRI:** Ke Wang (coord.)
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-1155
- **Priority:** Not set
- **Updated:** None

#### ENT-1909
- **Summary:** Support for backup direct to 3rd party cloud storage (AWS S3) 
- **Status:** Shipped
- **CoreEng Pillar:** BRIE
- **DRI:** Lakshmi Behl
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-1909
- **Priority:** Not set
- **Updated:** None

#### ENT-1929
- **Summary:** Support full backups with attachments for instances with large storage usage ( > 3TB)
- **Status:** Shipped
- **CoreEng Pillar:** BRIE
- **DRI:** Lakshmi Behl
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-1929
- **Priority:** Not set
- **Updated:** None

#### ENT-1983
- **Summary:** Increase size limit for site backup imports (<3TB)
- **Status:** Shipped
- **CoreEng Pillar:** BRIE
- **DRI:** Lakshmi Behl
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-1983
- **Priority:** Not set
- **Updated:** None

#### ENT-2122
- **Summary:** REST API capabilities for Atlassian Analytics
- **Status:** Shipped
- **CoreEng Pillar:** FinOps/Analytics
- **DRI:** Ke Wang
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2122
- **Priority:** Not set
- **Updated:** None

#### ENT-2199
- **Summary:** Jira: Vertical scale 50K-100k users per instance
- **Status:** Shipped
- **CoreEng Pillar:** Scale/CRSP
- **DRI:** CRSP Team
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2199
- **Priority:** Not set
- **Updated:** None

#### ENT-2331
- **Summary:** Support daily backups of Cloud products
- **Status:** Shipped
- **CoreEng Pillar:** BRIE
- **DRI:** Lakshmi Behl
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2331
- **Priority:** Not set
- **Updated:** None

#### ENT-2643
- **Summary:** Increase Atlassian user base and user provisioning limits to 800k users and =< 100 sites
- **Status:** Shipped
- **CoreEng Pillar:** Identity (SCIM/UUL)
- **DRI:** Prashant Ghosal
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2643
- **Priority:** Not set
- **Updated:** None


### Active Tickets (Complete List)


#### ENT-50
- **Summary:** EAP for the Ability to push (promote) Jira and JSM config data from sandbox to production
- **Status:** Public Roadmap
- **CoreEng Pillar:** TSP (Flip2Prod)
- **DRI:** Harpreet Singh Juneja
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-50
- **Description:** No description

#### ENT-59
- **Summary:** Guarantee that my organisation's user account account information (PII) is stored in a nominated region
- **Status:** Roadmap (Internal Only)
- **CoreEng Pillar:** Compliance/Identity (DaRe)
- **DRI:** Peter Wang / Amaranath Dabbara
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-59
- **Description:** No description

#### ENT-151
- **Summary:** Export all of my cloud data for long term storage in a "readable format"
- **Status:** Roadmap (Internal Only)
- **CoreEng Pillar:** BRIE
- **DRI:** Lakshmi Behl
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-151
- **Description:** No description

#### ENT-293
- **Summary:** US Classified/Top Secret/Secret Cloud deployment + IL6/ Disconnected / Airgapped
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-293
- **Description:** No description

#### ENT-311
- **Summary:** Apps backup and restore with 30 days retention
- **Status:** Roadmap (Internal Only)
- **CoreEng Pillar:** BRIE
- **DRI:** Lakshmi Behl
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-311
- **Description:** No description

#### ENT-351
- **Summary:** Modify how app approvals work in enterprise environments
- **Status:** Roadmap (Internal Only)
- **CoreEng Pillar:** Identity
- **DRI:** Prashant Ghosal
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-351
- **Description:** No description

#### ENT-652
- **Summary:** App migration content access problems - Restricted pages
- **Status:** Roadmap (Internal Only)
- **CoreEng Pillar:** Identity
- **DRI:** Prashant Ghosal
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-652
- **Description:** No description

#### ENT-764
- **Summary:** Purchase Apps for a subset of users on an instance
- **Status:** Roadmap (Internal Only)
- **CoreEng Pillar:** Identity (License Decoupling)
- **DRI:** Prashant Ghosal
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-764
- **Description:** No description

#### ENT-1057
- **Summary:** Audit Log Retention for 12 months for AGP customers
- **Status:** Public Roadmap
- **CoreEng Pillar:** ALP (Audit Logging Platform)
- **DRI:** Akshay Nambiar
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-1057
- **Description:** No description

#### ENT-1158
- **Summary:** Audit Logs for Admin pages
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-1158
- **Description:** No description

#### ENT-1520
- **Summary:** Expand Confluence Capabilities to Support Customer Size 150K-250K for a single site
- **Status:** Public Roadmap
- **CoreEng Pillar:** Scale/CRSP
- **DRI:** CRSP Team
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-1520
- **Description:** No description

#### ENT-1555
- **Summary:** Google CloudSQL and Cloud storage support for Atlassian products (Jira, JSM and Confluence)
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-1555
- **Description:** No description

#### ENT-1638
- **Summary:** Jira Data Center WCAG 2.1 AA Conformance Required
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-1638
- **Description:** No description

#### ENT-1690
- **Summary:** Ability to configure what enterprise org level data is available to each enterprise site
- **Status:** Public Roadmap
- **CoreEng Pillar:** Identity (Org Isolation)
- **DRI:** Prashant Ghosal
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-1690
- **Description:** No description

#### ENT-1697
- **Summary:** Gliffy app for Confluence cloud - performance issues
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-1697
- **Description:** No description

#### ENT-1703
- **Summary:** Enterprise support (by exception) for site count above 150, up to 2,000
- **Status:** Roadmap (Internal Only)
- **CoreEng Pillar:** Identity (Admin Hub Scale)
- **DRI:** Prashant Ghosal
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-1703
- **Description:** No description

#### ENT-1786
- **Summary:** [Cloud] Allow admins to remove the "Discover" and other products from the "Switch to" tab
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-1786
- **Description:** No description

#### ENT-1804
- **Summary:** Ability to mask sensitive content
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-1804
- **Description:** No description

#### ENT-1958
- **Summary:** Support AWS-XKS with Customer-managed keys (CMK)
- **Status:** Public Roadmap
- **CoreEng Pillar:** Encryption (CMK)
- **DRI:** Greg Zaney
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-1958
- **Description:** No description

#### ENT-2085
- **Summary:** CMK (BYOK) - Apply Customer-managed keys retroactively on existing site
- **Status:** Public Roadmap
- **CoreEng Pillar:** Encryption (CMK)
- **DRI:** Greg Zaney
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2085
- **Description:** No description

#### ENT-2089
- **Summary:** Create a Migration / Data Management Admin role
- **Status:** Roadmap (Internal Only)
- **CoreEng Pillar:** Identity/Admin APIs
- **DRI:** Prashant Ghosal
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2089
- **Description:** No description

#### ENT-2124
- **Summary:** Support large total attachment size in Confluence Sandbox creation
- **Status:** Actively Investigating
- **CoreEng Pillar:** TSP + TDP
- **DRI:** Harpreet Singh Juneja
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2124
- **Description:** No description

#### ENT-2225
- **Summary:** App usage for Confluence
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2225
- **Description:** No description

#### ENT-2289
- **Summary:** FedRAMP High
- **Status:** Public Roadmap
- **CoreEng Pillar:** Compliance/RegInd (FedRAMP)
- **DRI:** Wayne Yim
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2289
- **Description:** No description

#### ENT-2303
- **Summary:** Single Logout - Atlassian Account should support IdP-initiated single logouts
- **Status:** Pending Review
- **CoreEng Pillar:** Identity (Rocket/Fortress)
- **DRI:** Prashant Ghosal
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2303
- **Description:** No description

#### ENT-2347
- **Summary:** Object level controls or permissions for Goals
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2347
- **Description:** No description

#### ENT-2409
- **Summary:** Ability to retrieve detailed billing information via REST API
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2409
- **Description:** No description

#### ENT-2460
- **Summary:** AI Processing in Europe
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2460
- **Description:** No description

#### ENT-2590
- **Summary:** REST API usage insights
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2590
- **Description:** No description

#### ENT-2625
- **Summary:** Ability to deactivate users who haven't logged in for a period of time
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2625
- **Description:** No description

#### ENT-2667
- **Summary:** Automation Rules Should be Included in Jira Backups (Back up and Restore)
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2667
- **Description:** No description

#### ENT-2745
- **Summary:** Virtual Private / Isolated cloud
- **Status:** Public Roadmap
- **CoreEng Pillar:** Compliance (Isolated Cloud/Oasis)
- **DRI:** Wayne Yim
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2745
- **Description:** No description

#### ENT-2787
- **Summary:** Improve public customer facing documentation around how app versions and releases are managed
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2787
- **Description:** No description

#### ENT-2788
- **Summary:** Improve cloud app version visibility and information on the Marketplace app listing and Connected Apps page
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2788
- **Description:** No description

#### ENT-2840
- **Summary:** JSM (Assets, Forms, Data Manager) [Rovo Connector Enhancements]
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2840
- **Description:** No description

#### ENT-2858
- **Summary:** Improve Visibility of Upcoming Features in Release Tracks and Bundled Updates
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2858
- **Description:** No description

#### ENT-2864
- **Summary:** Customer can retain data up to n years to meet compliance needs
- **Status:** Roadmap (Internal Only)
- **CoreEng Pillar:** TDP + ALP
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2864
- **Description:** No description

#### ENT-2880
- **Summary:** Support "Scalable Silos" complex company archetype. 
- **Status:** Actively Investigating
- **CoreEng Pillar:** Unknown - Verify
- **DRI:** TBD
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2880
- **Description:** No description

#### ENT-2883
- **Summary:** Embeddable audit logs for Jira/JSM
- **Status:** Roadmap (Internal Only)
- **CoreEng Pillar:** ALP + Identity
- **DRI:** Akshay Nambiar
- **Priority:** Not set
- **Created:** None
- **Updated:** None
- **URL:** https://hello.jira.atlassian.cloud/browse/ENT-2883
- **Description:** No description


---

## SECTION E: CORENG PILLAR ROLLUP

### Identity & IAM (Prashant Ghosal)
**Tickets:** ENT-1155, ENT-1690, ENT-1703, ENT-2089, ENT-2303, ENT-2643, ENT-2883, ENT-351, ENT-555, ENT-652, ENT-764

### ALP (Audit Logging Platform)
**Tickets:** ENT-1057, ENT-166

### BRIE
**Tickets:** ENT-151, ENT-1909, ENT-1929, ENT-1983, ENT-2331, ENT-311

### TSP (Flip2Prod)
**Tickets:** ENT-50

### Encryption
**Tickets:** ENT-1958, ENT-2085, ENT-398

### Scale/CRSP
**Tickets:** ENT-1520, ENT-2199

### Compliance/RegInd
**Tickets:** ENT-2289

### FinOps/Analytics
**Tickets:** ENT-2122


---

## SECTION F: RECOMMENDATIONS FOR CORENG PLANNING

1. **Identity Pillar Overload:** 15+ active tickets across auth, access control, org isolation. Consider dedicated sub-team or breaking out Policy Engine.

2. **BRIE & Data Governance:** Multiple retention/backup tickets suggest need for more formal data lifecycle capabilities.

3. **Compliance Roadmap:** 4 tickets (FedRAMP, DaRe, Oasis, etc.) suggest new formal Compliance/RegInd project in next wave.

4. **Scale Stability:** Shipped CRSP work on Jira/Confluence scale; continue monitoring perf requests.

5. **Unknown/TBD Pillar:** 15+ tickets require deeper investigation to assign proper pillar ownership.

---

**End of Report**
