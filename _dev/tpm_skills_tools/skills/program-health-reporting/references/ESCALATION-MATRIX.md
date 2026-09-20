# Escalation Matrix Reference

Routing rules for escalations, audience-specific delivery channels, and approval requirements.

## 1. Escalation Tiers

| Tier | Trigger | Response Time | Channel | Audience |
|------|---------|---------------|---------|----------|
| **T0 — Critical** | Any dimension → Red; Sev-1 incident | Immediate (within 15 min) | `slack_channels.alerts` + DM to program leader | Program leader, EM, affected team leads |
| **T1 — Urgent** | Red status sustained >48h; multiple programs Red | Within 4h | `slack_channels.exec` | Skip-level leader, steerco |
| **T2 — Watch** | Any transition Green → Amber; new blockers | Next digest cycle | `slack_channels.status` | Program team |
| **T3 — Informational** | Stable state; positive transitions (Red → Amber → Green) | Next weekly report | Confluence page | All stakeholders |

## 2. Approval Requirements by Report Type

| Report | Draft | Team Distribution | Exec Distribution |
|--------|-------|-------------------|-------------------|
| Daily Digest | 🟢 Auto | 🟢 Auto | N/A (not exec-facing) |
| Weekly Report | 🟢 Auto | 🟢 Auto | 🔴 Human approval required |
| Executive Briefing | 🟢 Auto | N/A | 🔴 Human approval required |
| Weekly Async (standard) | 🟢 Auto | 🟢 Auto | N/A |
| Weekly Async (high-stakes) | 🟢 Auto | 🔴 Human approval | 🔴 Human approval |

## 3. Audience Definitions

### Engineering Team
- **Who**: Engineers, tech leads, engineering managers on the program
- **What they need**: Technical details, blocker specifics, sprint metrics
- **Format**: Detailed Slack messages + Confluence pages
- **Cadence**: Daily digest + weekly reports

### Program Leadership
- **Who**: Program manager, engineering director, product lead
- **What they need**: RAG summary, risk assessment, decision items
- **Format**: Weekly reports, escalation alerts
- **Cadence**: Weekly + real-time for Red escalations

### Executive Stakeholders
- **Who**: VP+, steering committee, executive sponsors
- **What they need**: Portfolio health, strategic alignment, decisions needed
- **Format**: Executive briefing (Confluence), monthly/quarterly
- **Cadence**: Monthly + ad-hoc for T1 escalations

## 4. Escalation Routing Rules

### State Transition Routing
```
IF status transitions TO Red:
  → Post to alerts channel immediately
  → DM program leader
  → Include in next daily digest with 🔴 marker
  → If Red persists >48h → escalate to T1

IF status transitions Green → Amber:
  → Include in next daily digest
  → Include in weekly report
  → No immediate alert (exception-based philosophy)

IF status transitions Red → Amber:
  → Include in next daily digest as positive signal
  → DM program leader: "Status improving"
  → Continue monitoring — do not auto-close escalation

IF status transitions Amber → Green:
  → Include in weekly report as recovery
  → Close any open T2 watches
```

### Multi-Program Escalation
```
IF ≥2 programs simultaneously Red:
  → Portfolio-level T1 escalation
  → Notify exec channel
  → Generate ad-hoc executive briefing (draft only — requires approval)

IF ≥3 programs Amber with declining trends:
  → T2 watch + flag in next executive briefing
  → DM program leader with portfolio concern
```

## 5. Approval Workflow

### Standard Flow
1. AI generates report/briefing → saves as Confluence draft
2. AI posts notification to reviewer via Slack DM
3. Reviewer reviews and approves/requests changes
4. On approval → AI distributes to target audience
5. On changes requested → AI revises and re-submits

### Timeout Handling
- **4h timeout**: For high-stakes weekly async — send reminder
- **24h timeout**: For executive briefings — send reminder
- **48h timeout**: For any pending approval — escalate to backup approver
- **Never auto-distribute** without approval for exec-facing content

## 6. Alert Fatigue Prevention

### Cooldown Rules
- After alerting on a Red transition, do not re-alert for the same dimension for 4 hours
- After T0 alert, suppress T2/T3 for that dimension until next scan cycle
- If all-nominal for 5+ consecutive days, include brief "monitoring active" confirmation

### Batching Rules
- If >3 exceptions detected in one scan, batch into single digest message
- Group exceptions by program, then by severity within each program
- Include count in header: "📡 Daily Pulse — 7 exceptions across 3 programs"

### Deduplication
- Do not alert on the same blocker twice within 24h unless status changes
- Track previous alert state to detect meaningful changes vs. noise
