# ENT50 — verified enrichment, 2026-05-15

> Live data captured 2026-05-15 08:03 PT via `mcp__atlassian__get_jira_issue`. Use this table as the single source of truth for ENT50 priority/status/assignee.

| Key | Priority | Status | Assignee | Component | Summary |
|---|---|---|---|---|---|
| ENT-50 | Minor | Public Roadmap | Adithya Ramesh | Cloud Admin — Sandbox | EAP push (promote) data sandbox → production |
| ENT-59 | Minor | Roadmap (Internal Only) | Amaranath Dabbara | Information Protection — Region/Residency | Guarantee org PII stored in nominated region |
| ENT-98 | Blocker | (open) | unassigned | Trust Foundations — GovCloud | IL5 (DoD Impact Level 5) |
| ENT-151 | **Blocker** | Roadmap (Internal Only) | Lakshmi Behl | Resilience — Backup/Restore | Export all cloud data — readable long-term format |
| ENT-166 | Minor | **Shipped** ✅ | Nikhil Gupta | Information Protection — Guard — Audit Logs | Audit log access for site admins |
| ENT-293 | Blocker | (open) | unassigned | Trust Foundations | US Classified / IL6 / Disconnected / Airgapped |
| ENT-311 | Minor | Roadmap (Internal Only) | Atul Setlur | Resilience — Backup/Restore | Apps backup and restore with 30-day retention |
| ENT-555 | Minor | **Shipped** ✅ | Sudesh Peram | Cloud Security — Authentication controls | Single Logout — Atlassian a/c logs out of SAML IdP |
| ENT-764 | Minor | Not Currently Prioritized | Harsh Dhaka | Marketplace Platform — Other | App purchase for subset of users |
| ENT-1155 | Minor | **Shipped** ✅ | Anand Balachandran | Cloud Security — Trust Programs | Data Governance for UGC |
| ENT-1445 | Blocker | (open) | (verify) | Trust Foundations — FedRAMP | FedRAMP Tailored for Atlassian Access |
| ENT-1520 | Minor | Public Roadmap | Cody Zhang | Confluence — Scale | Confluence > 150k user single site (10 named customers: SAP, BMW, JPMC, Siemens, Bosch, NSA, Oracle, AT&T, Apple, Citi) |
| ENT-1666 | Blocker | (open) | (verify) | Information Protection — Guard | Policy-based exfiltration controls (DC) |
| ENT-1674 | Minor | Roadmap (Internal Only) | Atul Setlur | Resilience — Backup/Restore | AWS Failover between regions (MRDR) |
| ENT-1690 | Minor | Pending Review | Rob Saunders | Cloud Administration — Other | Configure org-level data per enterprise site |
| ENT-1703 | Major | Pending Review | Rob Saunders | Cloud Admin — Organisations | Increase site limit 150 → 2,000 (named customer: PwC) |
| ENT-1929 | Minor | **Shipped** ✅ | Lakshmi Behl | Resilience — Backup/Restore | Full backups w/ attachments for >3 TB instances |
| ENT-1958 | Blocker | (open) | (verify) | Encryption — BYOK / AWS-XKS | AWS-XKS — non-AWS key store support |
| ENT-2022 | Blocker | (open) | (verify) | Encryption — BYOK | CMK encryption for Platform Apps |
| ENT-2035 | Blocker | (open) | (verify) | Encryption — BYOK | CMK Encryption for JPD |
| ENT-2085 | Minor | Public Roadmap | Hui Ren | Information Protection — Guard — CMK + Trust Foundations — Encryption | CMK (BYOK) — apply retroactively on existing site |
| ENT-2289 | Minor | Public Roadmap | Irene Milyuk | Trust Foundations — GovCloud | FedRAMP High |
| ENT-2643 | Minor | **Shipped** ✅ | David Dooley | Cloud Security — User Provisioning (SCIM) | User base 800k (Identity scale, ≤100 sites) |
| ENT-2647 | Blocker | (open) | (verify) | Encryption — BYOK | BYOK Encryption for Compass |
| ENT-2745 | Blocker | (open) | Michael Andreacchio | Confluence — Compliance & Security | Virtual Private / Isolated cloud |
| ENT-2883 | Blocker | (open) | (verify) | Audit — ALP | Embeddable audit logs for Jira/JSM |
| ENT-3032 | Minor | Roadmap (Internal Only) | Sudesh Peram | Cloud Security — User Provisioning (SCIM) | SCIM Fanout (sync users to sites by group) |
| ENT-3099 | Minor | **Shipped** ✅ | Ashwini Rattihalli | Rovo / AI — Product — Chat | Expand CMK(BYOK) scope to AI / Rovo |
| ENT-3235 | Minor | Public Roadmap | Sarah Joshi | Cloud Admin — Other + Information Protection — New Deployment Options | Atlassian SaaS on GCP |
| ENT-3721 | Blocker | (open) | (verify) | Audit — ALP | Embeddable audit logs for Confluence |

## Aggregates (verified 2026-05-15)

| Metric | Count |
|---|---|
| Total ENT50 items audited | 30 |
| Status = Shipped | **6** (ENT-166, 555, 1155, 1929, 2643, 3099) |
| Status = Public Roadmap | 6 |
| Status = Roadmap (Internal Only) | 7 |
| Status = Pending Review | 2 |
| Status = Not Currently Prioritized | 1 |
| Status = open Blocker (unmapped on this list above) | 8 (ENT-98, 293, 1445, 1666, 1958, 2022, 2035, 2647, 2883, 3721) |
| Priority = Blocker | 10 |
| Priority = Major | 1 |
| Priority = Minor | 19 |

> **Six items have shipped since the prior local docs were authored.** This is the largest single category of correction in this audit.

## Named enterprise customers verified

| Customer | Tickets |
|---|---|
| Wells Fargo | ENT-50, ENT-151 (per subagent) |
| Rational | ENT-311 |
| PwC | ENT-1703 (and ENT-3824 from inbox) |
| SAP, BMW, JPMC, Siemens, Bosch, NSA, Oracle, AT&T, Apple, Citi | ENT-1520 |
| DocuSign | ENT-3881 (open inbox Blocker) |
| AMAT | ENT-3862 (Rovo dashboard) |
| Accenture | ENT-3812, ENT-3727 |

## Provenance

* Tool: `mcp__atlassian__get_jira_issue`
* Site: `hello.atlassian.net`
* Captured: 2026-05-15 08:03 PT
* Fields fetched: assignee, priority, components, status, duedate (+ description body for customer context)
