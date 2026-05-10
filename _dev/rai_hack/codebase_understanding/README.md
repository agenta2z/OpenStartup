# Responsible AI — Joint Codebase Understanding

Comprehensive documentation for two related repositories forming Atlassian's Responsible AI moderation platform.

## Quick navigation

| I want to... | Go to |
|---|---|
| Understand the overall system | [overviews/02-architectural-narrative.rst](overviews/02-architectural-narrative.rst) |
| See all modules at a glance | [overviews/01-multi-axis-matrix.rst](overviews/01-multi-axis-matrix.rst) |
| On-call / SRE incident response | [overviews/03-criticality-dashboard.rst](overviews/03-criticality-dashboard.rst) |
| Understand business goals, SLOs, optimization priorities | [architecture/cross-cutting/07-business-and-technical-goals.rst](architecture/cross-cutting/07-business-and-technical-goals.rst) |
| Understand data storage, inference persistence, and the Databricks closed loop | [architecture/cross-cutting/09-data-storage-and-databricks.rst](architecture/cross-cutting/09-data-storage-and-databricks.rst) |
| **Pull real historical traffic** (raw prompts/responses) from Databricks — runnable examples | [architecture/cross-cutting/09-data-storage-and-databricks.rst#7-working-examples](architecture/cross-cutting/09-data-storage-and-databricks.rst) (§7, Examples A–H) |
| Understand how a prompt is moderated | [architecture/02-request-lifecycle.rst](architecture/02-request-lifecycle.rst) |
| Look up what every file does | [architecture/03-module-catalog.rst](architecture/03-module-catalog.rst) |
| Deep-dive: prompt moderation | [modules/moderation/prompt-moderation.rst](modules/moderation/prompt-moderation.rst) |
| Deep-dive: image moderation | [modules/moderation/image-moderation.rst](modules/moderation/image-moderation.rst) |
| Deep-dive: inference models | [modules/inference/llama-model.rst](modules/inference/llama-model.rst) |
| Deep-dive: feature flags | [modules/service/feature-flags.rst](modules/service/feature-flags.rst) |
| Deep-dive: evaluation framework | [modules/rai-research/evaluation-framework.rst](modules/rai-research/evaluation-framework.rst) |
| Deep-dive: experiments | [modules/experiments/image-moderation-v1.rst](modules/experiments/image-moderation-v1.rst) |
| **Validate a proposed change against historical decisions** ⭐ NEW (2026-05-06) | [history/03-wave9-historical-validation.md](history/03-wave9-historical-validation.md) |
| Look up file → owner → verdict (30-sec cheatsheet) ⭐ NEW | [history/05-source-of-truth-cheatsheet.md](history/05-source-of-truth-cheatsheet.md) |
| Chronological decision timeline (1487+ commits mined) ⭐ NEW | [history/01-decision-timeline.md](history/01-decision-timeline.md) |
| Catalog of every documented perf decision ⭐ NEW | [history/02-perf-decision-archive.md](history/02-perf-decision-archive.md) |
| How trustworthy were the investigation agents? ⭐ NEW | [history/04-agent-claim-audit.md](history/04-agent-claim-audit.md) |

## Repositories covered

- **`responsible-ai-api`** (`/Users/tchen7/MyProjects/atlassian_packages/responsible-ai-api`) — Production Flask service; 94 Python source files; 5,272 LoC
- **`responsible-ai`** (`/Users/tchen7/MyProjects/atlassian_packages/responsible-ai`) — Research/ML monorepo; Pants build system; ~42 files; ~2,330 LoC

## Documentation structure

```
codebase_understanding/
├── index.rst                          # Master index
├── README.md                          # This file
├── overviews/
│   ├── 01-multi-axis-matrix.rst       # Size/criticality/tier tables
│   ├── 02-architectural-narrative.rst # Walking tour + request lifecycle
│   └── 03-criticality-dashboard.rst   # SRE blast-radius + on-call runbook
├── architecture/
│   ├── 00-glossary.rst                # All key terms defined
│   ├── 01-architecture-overview.rst   # System boundary + Flask structure
│   ├── 02-request-lifecycle.rst       # Full call stack for all 4 endpoints
│   ├── 03-module-catalog.rst          # One-line purpose for every file
│   └── cross-cutting/
│       ├── 06-deployment.rst          # Docker, CI/CD, test structure
│       └── index.rst
└── modules/
    ├── service/
    │   ├── app-and-config.rst         # Flask app + Config singleton
    │   ├── blueprints-and-routing.rst # URL routing hierarchy
    │   ├── schemas-and-validation.rst # Pydantic models
    │   ├── feature-flags.rst          # Statsig gates (~30)
    │   └── auth-and-context.rst       # SLAuth + tenant context
    ├── inference/
    │   ├── model-abstraction.rst      # Base classes + error handling + confidence
    │   ├── llama-model.rst            # LLaMA FT model (689 LoC deep-dive)
    │   ├── gpt-oss-model.rst          # GPT-OSS 20B via Teamserve HTTP
    │   ├── image-sagemaker.rst        # SageMaker V0+V1 parallel inference
    │   └── confidence-and-shadowing.rst
    ├── moderation/
    │   ├── prompt-moderation.rst      # Prompt pipeline + ETag + metrics
    │   ├── output-moderation.rst      # Streaming NDJSON + URL checker
    │   ├── agent-moderation.rst       # Agent config safety (LLM judge)
    │   └── image-moderation.rst       # Image V0+V1+anti-abuse
    ├── analytics/
    │   ├── metrics.rst                # Prometheus metrics
    │   └── gasv3-analytics.rst        # GASv3 event schemas + client
    ├── rai-research/
    │   ├── harm-taxonomy.rst          # 16-category HarmCategory Enum
    │   ├── dataset-infrastructure.rst # Pandera schema + 9 data sources
    │   ├── evaluation-framework.rst   # Offline eval + MLflow
    │   ├── online-evaluation.rst      # LLM judge + production monitoring
    │   └── msp-deployment.rst         # MSP model registration
    └── experiments/
        ├── image-moderation-v1.rst    # ShieldGemma2 experiment
        └── pii-anonymization.rst      # Presidio PII detection
```

## Key architectural facts (verified)

- **4 moderation endpoints**: prompt, output (streaming NDJSON), agent, image
- **3 inference backends**: LLaMA via MSP/Teamserve gRPC, GPT-OSS via Teamserve HTTP, ShieldGemma2 via SageMaker
- **Model shadowing**: gevent Pool(20) runs shadow model in parallel; A/B comparison for rollout safety
- **Fail-open design**: all inference failures default to ALLOWED (configurable per-gate)
- **ETag caching**: prompt moderation skips inference on cache hit (SHA-256 of prompt+version)
- **16 harm categories** defined in `responsible-ai` harm taxonomy
- **Statsig**: ~30 feature gates control all model selection and rollout decisions
- **GASv3 analytics**: async (gevent Pool 10), non-blocking, kill-switchable
- **Circuit breakers**: Triton gRPC/HTTP (fail_max=30), anti-abuse (fail_max=5)

## Investigation provenance

Generated 2026-05-04 via:
- 4 parallel subagent investigations of live source trees
- Direct reads of all 94 `responsible-ai-api` Python source files
- Direct reads of ~42 `responsible-ai` research files
- All numerical claims verified via `find + wc -l` on actual source trees
