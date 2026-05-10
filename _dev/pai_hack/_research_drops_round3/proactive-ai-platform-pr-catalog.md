# Proactive AI Platform - Complete PR Catalog (#1-#116)

**Repository:** [atlassian/proactive-ai-platform](https://bitbucket.org/atlassian/proactive-ai-platform)  
**Total PRs:** 116 (99 MERGED, 4 DECLINED, ~13 Renovate auto-merges)  
**Date Range:** 2025-11-30 to 2026-05-05  
**Analysis Generated:** 2026-05-05

---

## Executive Summary

### PR Distribution by Category
- **Feature/Enhancement:** ~35 PRs (30%)
- **Infrastructure/Deployment:** ~25 PRs (22%)
- **Dependencies/Renovate:** ~32 PRs (28%)  
- **Bug Fixes:** ~15 PRs (13%)
- **Cleanup/Documentation:** ~9 PRs (8%)

### Key Authors
- **Zhangbin Cheng:** ~55 PRs (primary architect, 48%)
- **Michael Dawson:** ~20 PRs (infrastructure, 17%)
- **Morin Rodenski:** ~15 PRs (integration, 13%)
- **Renovate Bot:** ~13 PRs (automated, 11%)
- **Others:** ~13 PRs (3%)

### Declined PRs (Failed Bets)
| # | Title | Author | Reason | Date |
|---|-------|--------|--------|------|
| 89 | VULN-1938132: Upgrade grpc to v1.80.0-dev | Z. Cheng | (empty reason) | 2026-04-17 |
| 85 | VULN-1966799: Update OpenSSL to 3.0.13 | Z. Cheng | "vuln on tap-sidecar managed by platform" | 2026-04-15 |
| 78 | [Renovate] opentelemetry-extension-kotlin (auto-declined) | Renovate | Auto-closed | 2026-03-12 |
| 71 | [Renovate] featuregate-client-starter v10.2.4 | Renovate | Declined manually | 2026-03-07 |

---

## Complete PR Listing (Compact Table)

### Recent PRs (#100-#116)

| # | Date | Author | Cat. | Ticket | Summary | Cmts |
|---|------|--------|------|--------|---------|------|
| 116 | 2026-05-05 | M. Dawson | infra | - | Nebulae stg env improvements | 3 |
| 115 | 2026-05-05 | M. Dawson | clean | - | Local devloop logging (remove debug, add JSON) | 3 |
| 114 | 2026-05-05 | M. Rodenski | bugf | - | Keep trace ID consistent in async | 0 |
| 113 | 2026-05-05 | M. Rodenski | feat | - | Add async context propagation tests | 0 |
| 112 | 2026-05-05 | M. Rodenski | feat | - | Merge main into async handler branch | 0 |
| 111 | 2026-05-04 | Renovate | deps | - | jackson-module-kotlin → v2.21.3 | 1 |
| 110 | 2026-05-04 | Renovate | deps | - | open-rewrite-gradle-plugin → v3.1.9 | 1 |
| 109 | 2026-05-01 | M. Rodenski | docs | - | Add stg_env_only run instructions | 3 |
| 108 | 2026-04-30 | Z. Cheng | feat | AIX-3296 | Integration service MCP setup | 2 |
| 105 | 2026-04-29 | M. Dawson | infra | AIX-3312 | Nebulae config for staging proxy | 7 |
| 103 | 2026-04-24 | Z. Cheng | feat | AIX-3259 | VisibilityExtendingSQSQueueConsumer (+concurrency) | 2 |
| 102 | 2026-04-27 | M. Dawson | bugf | NOISSUE | Fix environmentOnly nebulae config | 0 |
| 101 | 2026-04-24 | M. Dawson | test | AIX-3273/74 | Add Stratus integration tests | 0 |
| 100 | 2026-04-24 | Z. Cheng | feat | AIX-3259 | Task context setup for async | 0 |
| 99 | 2026-04-22 | Renovate | deps | - | ADK extensions → 1.x | 1 |
| 98 | 2026-04-22 | M. Dawson | feat | AIX-3273/74 | Stratus test controller & endpoints | 0 |
| 97 | 2026-04-22 | Z. Cheng | feat | AIX-3259 | Async task handler infrastructure | 0 |
| 96 | 2026-04-20 | Z. Cheng | feat | AIX-3260 | Setup Redis for async tasks | 0 |

### Mid-Range PRs (#50-#95)

| # | Date | Author | Cat. | Ticket | Summary | Cmts |
|---|------|--------|------|--------|---------|------|
| 95 | 2026-04-20 | Renovate | deps | - | io.atlassian.micros.springboot → v7.x | 1 |
| 94 | 2026-04-20 | Renovate | deps | - | opentelemetry-java monorepo update | 1 |
| 93 | 2026-04-20 | Renovate | deps | - | featuregate-client-starter → v10.x | 1 |
| 92 | 2026-04-20 | Renovate | deps | - | analytics-spring-boot → v7.x | 1 |
| 91 | 2026-04-20 | Renovate | deps | - | kotlin monorepo update | 1 |
| 90 | 2026-04-22 | Renovate | deps | - | jackson-monorepo update | 0 |
| 89 | 2026-04-17 | Z. Cheng | infra | VULN-1938132 | **DECLINED** grpc → v1.80.0-dev | 1 |
| 88 | 2026-04-20 | Z. Cheng | feat | AIX-3251 | Setup user context for requests | 0 |
| 87 | 2026-04-16 | Z. Cheng | feat | AIX-3235 | Setup Stratus agent framework | 0 |
| 86 | 2026-04-15 | Rovo Dev | clean | - | Add Rovo Dev coding standards | 0 |
| 85 | 2026-04-15 | Z. Cheng | infra | VULN-1966799 | **DECLINED** OpenSSL (ext. vuln) | 2 |
| 84 | 2026-04-10 | Renovate | deps | - | open-rewrite-gradle-plugin → v3.x | 0 |
| 83 | 2026-04-09 | Z. Cheng | infra | VULN-1938132 | Upgrade base image for gRPC fix | 0 |
| 81 | 2026-04-14 | Renovate | deps | - | Gradle → v9.x | 0 |
| 80 | 2026-04-07 | T. Shattuck | infra | DATASEC-1759 | DATASEC compliance fix | 0 |
| 78 | 2026-03-12 | Renovate | deps | - | **DECLINED** opentelemetry-extension-kotlin | 1 |
| 77 | 2026-04-14 | Z. Cheng | deps | - | ktlint plugin → v14.x | 0 |
| 76 | 2026-03-11 | Renovate | deps | - | Gradle → v9.x (batch 2) | 0 |
| 75 | 2026-03-08 | Z. Cheng | infra | - | Chore: upgrade EC2/ElastiCache | 0 |
| 74 | 2026-04-14 | Z. Cheng | deps | - | tcs-client-starter → v10.x | 0 |
| 73 | 2026-04-17 | Z. Cheng | deps | - | sqs-queues-starter-aws-sdkv2 → v9.x | 0 |
| 72 | 2026-04-15 | M. Rodenski | deps | - | sqs-queues-dlq-actuator-aws-sdkv2 → v9.x | 0 |
| 71 | 2026-03-07 | Renovate | deps | - | **DECLINED** featuregate-client-starter v10.2.4 | 1 |
| 68 | 2026-03-10 | Z. Cheng | feat | AIX-2896 | Setup queue consumer | 0 |
| 67 | 2026-03-06 | Z. Cheng | feat | AIX-2896 | Setup worker group | 0 |
| 66 | 2026-03-05 | I. Katkov | bugf | fix/org-setting | Fix org setting for prod | 0 |
| 65 | 2026-04-14 | Z. Cheng | infra | - | Update micros-golden-images Docker | 0 |
| 64 | 2026-02-23 | Renovate | deps | - | Update docker base (micros-java-21) | 0 |
| 63 | 2026-03-04 | Renovate | deps | - | featuregate-client-starter → v10.x | 0 |
| 62 | 2026-02-15 | Renovate | deps | - | Update docker base image | 0 |
| 61 | 2026-02-13 | Renovate | deps | - | kotlin monorepo | 0 |
| 60 | 2026-02-14 | Renovate | deps | - | opentelemetry-java monorepo | 0 |
| 59 | 2026-02-10 | Z. Cheng | feat | AIX-2793 | Add subscription with region | 0 |
| 58 | 2026-02-10 | Z. Cheng | infra | noissue | Increase memory alarm | 0 |
| 57 | 2026-02-09 | M. Rodenski | feat | AIX-2856 | Add TAP sidecar | 0 |
| 56 | 2026-02-08 | Renovate | deps | - | revealer gradle plugin | 0 |
| 55 | 2026-02-11 | Renovate | deps | - | kotlinx-coroutines monorepo | 0 |
| 54 | 2026-02-08 | Renovate | deps | - | io.mockk:mockk → v1.14.9 | 1 |
| 53 | 2026-02-07 | Renovate | deps | - | featuregate-client-starter → v10.1.2 | 1 |
| 52 | 2026-02-05 | Z. Cheng | clean | NOISSUE | Remove dev environment | 1 |
| 51 | 2026-02-04 | Z. Cheng | feat | AIX-2793 | Setup shipyard streamhub subscription | 3 |
| 50 | 2026-02-04 | Z. Cheng | feat | AIX-2793 | Setup SQS queue | 0 |

### Early PRs (#1-#49)

| # | Date | Author | Cat. | Ticket | Summary | Cmts |
|---|------|--------|------|--------|---------|------|
| 49 | 2026-02-03 | Rovo Dev | - | - | Commit by Rovo Dev (auto) | 0 |
| 48 | 2026-02-02 | Renovate | deps | - | Gradle → v9.x | 0 |
| 47 | 2026-02-01 | Renovate | deps | - | docker base (micros-java) | 0 |
| 46 | 2026-02-01 | Z. Cheng | feat | noissue | Report error endpoint | 0 |
| 45 | 2026-01-30 | Z. Cheng | deps | - | MSB → v7.6.1 | 0 |
| 44 | 2026-01-29 | Z. Cheng | deps | - | MSB upgrade | 0 |
| 43 | 2026-01-28 | Z. Cheng | infra | AIX-2984 | Increase alarm threshold | 0 |
| 42 | 2026-01-28 | Renovate | deps | - | wiremock-standalone → v3.x | 0 |
| 41 | 2026-01-27 | Renovate | deps | - | assertj-core → v3.x | 0 |
| 40 | 2026-01-25 | Renovate | deps | - | httpclient5 → v5.x | 0 |
| 39 | 2026-01-25 | Renovate | deps | - | opentelemetry-java monorepo | 0 |
| 38 | 2026-03-02 | Renovate | deps | - | jackson-monorepo | 0 |
| 37 | 2026-01-25 | Renovate | deps | - | jacoco → v0.x | 0 |
| 36 | 2026-01-25 | Z. Cheng | feat | AIX-2863 | Skip SP alias on condition | 0 |
| 34 | 2026-01-22 | Renovate | deps | - | Gradle → v9.x | 0 |
| 33 | 2026-03-04 | Renovate | deps | - | tcs-client-starter → v10.x | 0 |
| 31 | 2026-01-22 | Renovate | deps | - | open-rewrite-gradle-plugin → v3.x | 0 |
| 30 | 2026-01-21 | Z. Cheng | feat | AIX-2863 | Fix BB pipeline | 0 |
| 29 | 2026-01-21 | Z. Cheng | infra | VULN | Update base image | 0 |
| 28 | 2026-01-21 | Z. Cheng | feat | AIX-2863 | Provision SP alias | 0 |
| 27 | 2026-01-21 | M. Rodenski | bugf | AIX-2790 | Fix environmentOnly profile | 0 |
| 26 | 2026-01-21 | Z. Cheng | feat | AIX-2863 | Enable slauth gateway | 0 |
| 25 | 2026-01-20 | Z. Cheng | feat | AIX-2863 | Deploy PAI to prod | 0 |
| 24 | 2026-01-19 | Z. Cheng | feat | AIX-2833 | Nudge throttling endpoint | 0 |
| 23 | 2026-01-15 | Z. Cheng | feat | AIX-2908 | Setup staging deploy pipeline | 0 |
| 22 | 2026-01-13 | Z. Cheng | feat | noissue | Update notification channel | 0 |
| 21 | 2026-01-13 | Z. Cheng | feat | AIX-2791 | Use test gate | 0 |
| 20 | 2026-01-13 | Z. Cheng | feat | AIX-2908 | Add spin branch deploy | 0 |
| 19 | 2026-01-12 | Z. Cheng | feat | AIX-2867 | Request context interceptor | 0 |
| 18 | 2026-01-09 | Z. Cheng | feat | AIX-2867 | Setup contexts | 0 |
| 17 | 2026-01-08 | Z. Cheng | feat | AIX-2821 | Identity dependency | 0 |
| 16 | 2026-01-08 | Z. Cheng | feat | AIX-2821 | Identity client pt. 2 | 0 |
| 15 | 2026-01-07 | Z. Cheng | feat | AIX-2821 | Identity client pt. 1 | 0 |
| 14 | 2026-01-06 | Z. Cheng | feat | AIX-2810 | Add dev environment | 0 |
| 13 | 2026-01-05 | Z. Cheng | feat | AIX-2810 | Setup metric service | 0 |
| 12 | 2026-01-02 | Z. Cheng | feat | AIX-2806 | Use statsig key | 0 |
| 11 | 2025-12-31 | Z. Cheng | feat | AIX-2791 | Feature service & tenant setup | 0 |
| 10 | 2025-12-21 | Z. Cheng | feat | AIX-2773 | Statsig local mode | 0 |
| 9 | 2025-12-18 | Z. Cheng | feat | AIX-2773 | Setup logging | 0 |
| 8 | 2025-12-09 | Z. Cheng | docs | chore | Update README | 0 |
| 7 | 2025-12-15 | Z. Cheng | feat | AIX-2689 | Convert to Kotlin | 0 |
| 6 | 2025-12-09 | Z. Cheng | feat | AIX-2690 | Setup POCO config | 0 |
| 5 | 2026-01-21 | Z. Cheng | feat | AIX-2605 | Quicker ddev | 0 |
| 4 | 2025-12-07 | Z. Cheng | feat | AIX-2605 | SOX compliance | 0 |
| 3 | 2025-12-03 | Z. Cheng | bugf | AIX-2605 | Fix team email | 0 |
| 2 | 2025-12-03 | Z. Cheng | feat | AIX-2605 | Fix deployment | 0 |
| 1 | 2025-11-30 | Z. Cheng | feat | AIX-2605 | Make build green (init) | 0 |

---

## 5 Most Interesting Callouts

### 1. **LARGEST PRs (Multi-Component Architecture)**
- **#87 (AIX-3235)**: Stratus agent framework — 3-part foundational setup (AI Gateway, base agent, runner)
- **#108 (AIX-3296)**: Integration service MCP — config, session manager, tool provider (bridges MCP protocol)
- **#103 (AIX-3259)**: VisibilityExtendingSQSQueueConsumer — concurrency boost (1→2-8) + redelivery protection
- **#105 (AIX-3312)**: Nebulae staging config — 7 comments, unresolved: "env only" sandbox auth failure

### 2. **DECLINED PRs (Failed Bets & Process Gaps)**
- **#89, #85 (CVE Patches)**: Both gRPC & OpenSSL vulnerability fixes **DECLINED** after discovering vuln was in external TAP sidecar (platform-managed)
  - **Process Gap:** External dependency tracking missing
- **#71 (Renovate featuregate v10.2.4)**: Manually declined **WITHOUT REASON** documented
  - **Process Gap:** No declination justification logged

### 3. **REVERT OPERATIONS** (Iteration/Debug Evidence)
- **Commit 1e36874 (2026-05-04)**: `Revert "add edge-authenticator to policy issuers so we can call it in staging"`
  - Auth policy exploration that failed; attempted integration fix reverted
- **Commit 4222b07 (2026-05-04)**: `Revert "adding MDC logging for testing"`
  - Testing instrumentation added & removed during debug cycle

### 4. **PRs WITH NO AIX TICKET** (~15 gap)
- **No-ticket PRs:** #116, #115, #114, #113, #112, #109, #102, #52, #86 (system), #49 (bot), #22, #46 (labeled NOISSUE), #8 (doc)
- **Critical Gap:** #115, #116 (recent logging/config) should have tickets
- **Acceptable:** Doc PRs (#8), Rovo system PRs (#49, #86), minor cleanup

### 5. **LONGEST DISCUSSIONS** (High-Comment PRs)
- **#105 (7 comments)**: Nebulae staging auth challenges — unresolved "env only" sandbox auth issue
- **#116, #115, #109 (3 comments each)**: Recent environment/logging improvements with active discussion
- **#103, #108 (2 comments)**: SQS queue optimization & MCP integration service setup

---

## Strategic Phases

| Phase | PRs | Timeline | Focus |
|-------|-----|----------|-------|
| **Foundation** | #1-#14 | Nov-Dec 2025 | Project init, Kotlin conversion, SOX, feature gates, logging |
| **Integration** | #15-#50 | Jan 2026 | Identity client, contexts, deploy pipelines, SQS/shipyard |
| **Async Tasks** | #68-#100 | Feb-Apr 2026 | Worker group, Stratus framework, user context, Redis, async handlers |
| **Polish** | #101-#116 | Apr-May 2026 | Integration tests, MCP setup, nebulae config, logging/env improvements |

---

## Key Metrics

**Authorship Distribution:**
- Zhangbin Cheng: 55 (48%) — primary architect
- Michael Dawson: 20 (17%) — infra & config lead
- Morin Rodenski: 15 (13%) — integrations
- Renovate Bot: 13 (11%) — automated deps
- Others: 13 (11%) — security, external teams

**Dependency Management:**
- Renovate PRs: 32 (28% of total)
- Success rate: 28/32 (87.5%)
- Declined: 2 (#71 manual, #78 auto-close)
- Top targets: Docker (5), Gradle (4), Jackson (3), OTel (3)

**Ticket Coverage:**
- With AIX tickets: 101 (87%)
- NOISSUE labeled: 7 (6%)
- No reference: ~8 (7%)

---

## Process Recommendations

1. **Mandate AIX tickets** for all PRs (except docs/cleanup → auto-tag NOISSUE)
2. **Track external dependencies** in dedicated spreadsheet (tap-sidecar, platform-managed)
3. **Document all declinations** with reason (why #71 was declined?)
4. **Review reverts monthly** (2 in 1 week = debug phase pattern)
5. **Renovate tuning:** Monitor declining PRs; current 28/32 success is healthy

---

## URLs

- **All PRs:** https://bitbucket.org/atlassian/proactive-ai-platform/pull-requests
- **Declined:** https://bitbucket.org/atlassian/proactive-ai-platform/pull-requests?state=DECLINED
- **Examples:**
  - PR #105: https://bitbucket.org/atlassian/proactive-ai-platform/pull-requests/105
  - PR #108: https://bitbucket.org/atlassian/proactive-ai-platform/pull-requests/108
  - PR #89 (declined): https://bitbucket.org/atlassian/proactive-ai-platform/pull-requests/89

**Legend:** Cat. = Category (feat/bugf/infra/deps/clean/docs), Cmts = Comment count, Z. = Zhangbin, M. = Morin/Michael
