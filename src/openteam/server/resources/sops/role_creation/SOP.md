# AI Employee Role Creation

The Orchestrator follows a phased workflow for creating and deploying AI employees. The user drives the interaction; the Orchestrator guides through each phase and ensures prerequisites are met.

[__keywords__] hire employee, create role
[__example_requests__]
- hire machine learning engineer
- create TPM ai role

## Phase 0 -- Role Specification:
[__initial__]

[__requires confirmation__] Invoke a `multiple_choice` conversation tool to ask what the role primarily does. Do NOT ask any pre-question (no "what's the scope?", no "what teams?", no clarification before the tool). The tool IS the question.

Generate 4–10 high-level responsibility categories **tailored to the role being designed** for the multi-choice tool. Use your judgment based on the role context to create categories that make sense. Each option should be a short verb-phrase (5–10 words) describing a core function of THIS specific role. The user selects one or more and can supplement with custom text via the tool's free-text field.

Example for a Program Manager role:
- Creates & produces (content, documents, artefacts)
- Analyses & reports (data, metrics, insights)
- Coordinates & manages (projects, processes, people)
- Supports & responds (requests, issues, customers)
- Researches & discovers (knowledge, market, signals)
- Operates & executes (workflows, tasks, automation)

For other roles, different categories may be needed. For example, a Data Scientist might get: "Builds & trains models", "Cleans & prepares datasets", "Designs experiments & A/B tests", etc. A Customer Support Lead might get: "Triages & routes tickets", "Writes & maintains knowledge base", "Monitors SLA compliance", etc. Use your judgment.

DO NOT ask about autonomy, domain, systems, or integrations — these emerge from later phases.
DO NOT list the choices as a plain-text question — always invoke the `multiple_choice` conversation tool so the user can click their selections.

**Tools**[__must__]:
- multiple_choice

## Phase 1 -- Role Creation with Research & Document:
[__depends on__ Phase 0]

Use `create-role` tool to conduct deep research and synthesize a comprehensive role responsibility document. Combine user's original request with user response to the multi-choice question from Phase 0 as the role description. 

**Tools**[__must__]:
- /create-role

### Phase 1b -- Role Document Review
[__depends on__ Phase 1]

[__requires confirmation__] After the role document is generated, invoke the confirmation tool so the user can review it and approve before advancing. Configure the tool with these parameters:
- `view`: the absolute file path to the generated role document
- `view_label`: "View Role Document"
- `yes_label`: "✅ Approve & Proceed"
- `no_label`: "❌ Request Changes"

Provide a 3-5 bullet summary of the key aspects of the role. Do NOT proceed to the next phase until the user explicitly confirms. If the user declines, ask what changes they want and offer to regenerate.

## Phase 2 -- Role Setup & Skill/Tool Creation:
[__depends on__ Phase 1b]

This phase will:
1. Break down the role into required skills and tools
2. Investigate existing tool capabilities (TWG, Slack, etc.)
3. Research domain knowledge for each skill
4. Synthesize findings into concrete SKILL.md files and tool specifications

Use `/role-setup` to decompose the role and build its capabilities.

**Tools**[__must__]:
- /role-setup <role_document_path>

### Phase 2b -- Role Details Review [__depends on__ Phase 2; __requires confirmation__]

After role setup generates skills and tools, invoke the confirmation tool so the user can browse the deliverables and approve before advancing. Configure the tool with these parameters:
- `view`: the absolute path to the final_deliverables folder (e.g., the workspace outputs/final_deliverables/ directory)
- `view_type`: "folder"
- `view_label`: "View Role Details"
- `yes_label`: "✅ Approve & Proceed"
- `no_label`: "❌ Request Changes"

Provide a 3-5 bullet summary of the skills and tools created. Do NOT proceed to the next phase until the user explicitly confirms. If the user declines, ask what changes they want and offer to refine.
