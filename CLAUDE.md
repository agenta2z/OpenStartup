# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Starting the Application

```bash
# Start both backend (port 8000) + frontend dev server (port 3000)
./src/openteam/run.sh

# Backend only, with hot-reload
./src/openteam/run.sh --server --reload --debug

# Frontend dev server only
./src/openteam/run.sh --ui

# Real sessions (persistent, stored in _runtime/)
./src/openteam/run.sh --real-sessions --llm-backend claude_cli --llm-model sonnet

# Resume a previous server's sessions
./src/openteam/run.sh --resume-latest-server

# Build frontend for production
./src/openteam/run.sh --build
```

Windows equivalent: `.\src\openteam\run.ps1` with matching `-Server`, `-UI`, `-RealSessions`, `-LlmBackend`, `-LlmModel` flags.

### Frontend only

```bash
cd src/openteam/ui
npm install
npm start        # dev server on port 3000
npm run build    # production build → build/
```

### Running Tests

```bash
pytest                          # all tests
pytest -k task                  # filter by name
pytest --tb=short               # shorter tracebacks
pytest test/openteam/server/backends/test_e2e_claude_cli.py  # specific file
```

`conftest.py` (root) adds `src/` to sys.path, enabling `import openteam` without install. It also adds sibling repos `AgentFoundation/src` and `RichPythonUtils/src`.

### Direct Backend Entry Point

```bash
cd src/openteam/server
python run_server.py --port 8000 --reload
python run_server.py --list-backends
```

---

## Architecture

### Overview

OpenStartup is an **AI Company Dashboard**: a FastAPI backend + React 19 frontend that orchestrates multi-agent AI workflows for role creation, task execution, and team management. The backend streams LLM results to the browser via WebSocket.

The system has two modes:
- **Mock mode** (default): canned responses, fixture JSON, no external LLM calls. Good for UI development.
- **Real-sessions mode** (`--real-sessions`): persistent file-based sessions, live LLM backends (claude_cli or rovodev).

### Request Lifecycle

A user message travels through this path:

1. **React UI** sends `{"type": "message", "content": "/task --plan 'Build auth'}` over WebSocket
2. **`manager_websocket_routes.py`** receives the message, parses the slash command with regex + argparse-style logic
3. **`ToolDispatcher`** (in `services/tool_dispatcher.py`) routes to the correct tool executor
4. **Tool executor** (e.g., `resources/tools/task/executor.py`) loads a YAML topology, instantiates the agent inferencer chain (from `agent_foundation`), and runs it
5. Tokens stream back as `{"type": "token", "content": "chunk"}` messages
6. **`ConversationService`** logs artifacts per turn and persists workflow state via `SessionStore`

For non-slash conversational messages, the path goes through `ConversationService.run_conversation_turn()`, which calls `inferencer.run_agentic_loop()` with a `on_new_turn` callback for streaming.

### Backend (LLM) Abstraction

`server/backends/factories.py` defines three pluggable backends registered in a module-level `BackendRegistry` singleton:

| Backend | Requires | Notes |
|---------|----------|-------|
| `mock` | nothing | Word-by-word simulated streaming |
| `rovodev` | `acli` on PATH | RovoDevCliInferencer |
| `claude_cli` | `claude` on PATH | ClaudeCodeCliInferencer, default model `opus[1m]` |

All non-mock backends are wrapped identically in `_wrap_in_conversational()`: a TemplateManagerPromptRenderer (conversation/main/initial.jinja2) → tool loading + filtering → integration executor (Slack + TWG) → ToolDispatcher → ConversationalInferencer. This wrapping chain means the route layer never knows which LLM is running.

Per-session backend override is supported: `POST /api/sessions/{id}/backend` updates SessionStore and evicts the cached inferencer.

### Session Persistence

**There is no database.** All state lives on the filesystem under `_runtime/`:

```
_runtime/
└── servers/
    └── server_YYYYMMDD_HHMMSS_<uuid8>/
        ├── server_info.json
        └── sessions/
            ├── sessions_index.json
            └── <session_id>_<timestamp>/
                ├── session_state.json
                ├── turn_001/, turn_002/, ...   ← per-turn artifacts
                └── session.jsonl               ← RankEvolve-style structured log
```

`SessionStore` (in `services/session_store.py`) manages this layout. It supports `resume_server="latest"` or `resume_server="<name>"` to reconnect to a prior server's sessions on restart.

### Tool System

Tools live under `resources/tools/`. Each tool directory contains an `executor.py` and a `tool.json` that declares metadata + module path. They are loaded by `agent_foundation`'s tool registry at startup and filtered per-template via `.initial.config.yaml` whitelists.

The **task tool** is the most complex: it accepts a `--topology` flag (or preset names like `pti`, `bta`, `dual`, `multi-flow`) that maps to a YAML file in `resources/tools/task/topologies/`. These YAMLs use `_target_: <ClassName>` to declaratively build nested inferencer graphs (PlanThenImplement, BreakdownThenAggregate, Dual, MultiFlow) from `agent_foundation`. The executor hydrates the YAML, applies per-call overrides (model, permissions), instantiates the chain, and runs it.

### Prompt Templates

Templates use Jinja2, managed by `TemplateManager` from `rich_python_utils`. Structure:

```
prompt_templates/
├── conversation/main/
│   ├── initial.jinja2          ← rendered on every conversation turn
│   ├── .initial.config.yaml    ← tool whitelist for this template
│   └── _variables/workflow/
│       └── sop.jinja2          ← injected workflow/phase context
├── implementation/main/
│   ├── initial.jinja2, review.jinja2, followup.jinja2
│   └── _variables/task_instructions/<variant>.jinja2
└── deep_research/main/
    └── _variables/task_preamble/<role_type>.jinja2
```

`ConversationService.render_prompt()` injects session history, current turn, and `workflow_context` (phase, SOP, completed outputs). The `_variables/` subdirectories hold per-template slot overrides resolved by TemplateManager.

### Agent Foundation Dependency

All actual agentic execution lives in the sibling `AgentFoundation` repo. OpenStartup configures and drives it. Key classes used:
- `ConversationalInferencer` — manages multi-turn agentic loops
- `ClaudeCodeCliInferencer` / `RovoDevCliInferencer` — subprocess-based LLM backends
- `PlanThenImplementInferencer`, `BreakdownThenAggregateInferencer`, `MultiFlowInferencer`, `DualInferencer` — composable orchestration patterns declared in topology YAMLs
- Tool registry — discovers and loads tool executors

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENTEAM_LLM_BACKEND` | `mock` | Backend: mock, rovodev, claude_cli |
| `OPENTEAM_LLM_MODEL` | none | Model identifier (backend-specific) |
| `OPENTEAM_WORKING_DIR` | `~/MyProjects` | Agent working directory |
| `OPENTEAM_CACHE_DIR` | `<server_dir>/cache/streaming_cache` | Streaming output cache |
| `OPENSTARTUP_PYTHON` | `/opt/homebrew/anaconda3/bin/python` | Python interpreter path |

Optional: `src/openteam/server/.env` for Slack tokens, RovoChat credentials.

### WebSocket Protocol

**Endpoint:** `WS /ws/sessions/{session_id}/chat`

Slash commands are parsed with the pattern `/([a-zA-Z][a-zA-Z0-9_-]*)\b(.*)`. Hyphens in command names are normalized to underscores internally. The 30+ slash commands include `/task`, `/create-role`, `/role-setup`, `/project-onboarding`, `/mock_task`, `slack_*` (15 Slack tools), and `/twg`.

Server streams:
```json
{"type": "token", "content": "chunk", "metadata": {"agent_name": "Orchestrator"}}
{"type": "message_end", "final_content": "...", "message_id": "..."}
{"type": "status", "status": "complete|error"}
```
