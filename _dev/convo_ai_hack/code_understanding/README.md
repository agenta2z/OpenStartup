# convoai Code Understanding Docs

This is a comprehensive documentation library for the
[conversational-ai-platform](https://bitbucket.org/atlassian/conversational-ai-platform)
codebase, organized as a Sphinx site.

## Structure

- **67 RST files / ~21,000 lines**
- Organized into 5 main sections:
  1. **Glossary** (40+ acronyms)
  2. **Architectural overview** (tier model, dependency rules)
  3. **Tiers** (foundation, platform, product, tools, contrib)
  4. **Cross-cutting concerns** (12 topics + features)
  5. **Business & technical goals** (FY26 SLOs, OpenAI ceiling)

## Quick start

```bash
# 1. Install dependencies (one-time)
make install

# 2. Build HTML docs
make html

# 3. Open in browser
open _build/html/architecture/index.html
```

## What's covered

### Cross-cutting reference docs (12)

- AI Gateway, tenant isolation, feature flags, streaming, telemetry,
  identity & auth, persistence & messaging, agent runtime, build & test
- **GraphQL API reference** (49 controllers across 9 products)
- **External integrations** (13 systems with topology diagram)
- **Configuration reference** (50+ env vars, FF naming)

### Feature deep-dives (29)

- Rovo Insights, Marathon, MCP System, Deep Research, Rovo Plugin,
  AgentStudio + Reports, SAIN, AIFC, Agent Framework, Chat Streaming,
  Lumina, Knowledge + Knowledge Gap Workflow, CSM Platform + Voice,
  JSM Platform + Composer & Handoff, AIFEATURE, Memory, Confluence
  ADF Editor, Hiring Manager, Loom, AtlassianStudio Access
- Plus: 6 audit reports (JQL, CSM REST, JSM PlanGenerator, Pebble
  templates, refuted patterns)

### Business goals

- FY26 SLO architecture (4 reliability tiers)
- OpenAI Scale Tier 99.9% ceiling rationale
- AIFC quality targets (Maturity Gap Analysis)
- Per-feature roadmap (43 open questions consolidated)

## Authoring conventions

- One RST file per topic
- Mermaid diagrams for sequence + dependency graphs
- Cross-references via `:doc:` and `:ref:`
- Open questions sections in every feature deep-dive
- Honest gap reports for sources that couldn't be fetched

## Building outside this directory

```bash
cd /path/to/convo_ai_hack/code_understanding
make html  # uses conf.py here, builds _build/html/
```

## Cleaning

```bash
make clean
```

## Known limitations

- Slack source data NOT included (MCP tool unavailable in this
  investigation environment)
- Confluence whiteboard sources only partially extractable (whiteboard
  format not supported by `get_confluence_page`)
- Statsig FF rollout state not directly verifiable from sandbox
