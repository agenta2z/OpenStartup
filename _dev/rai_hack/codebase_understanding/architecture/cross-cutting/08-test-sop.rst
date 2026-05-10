.. _rai-test-sop:

===================================================
Testing SOP — responsible-ai-api & responsible-ai
===================================================

.. contents:: Contents
   :local:
   :depth: 3

This document is the authoritative test Standard Operating Procedure (SOP) for both
codebases. It covers every test layer: unit, integration, load/capacity, and CI/CD.
All commands are verified against the live source files.

---

responsible-ai-api
==================

Environment Setup (First Time)
-------------------------------

.. code-block:: bash

    # 1. Clone and enter the repo
    cd /Users/tchen7/MyProjects/atlassian_packages/responsible-ai-api

    # 2. First-run bootstrap (installs uv, syncs .venv/, configures git hooks)
    bin/first-run

``bin/first-run`` does the following in order:

- Detects / installs ``uv`` (existing → Homebrew → standalone curl)
- Authenticates against Atlassian's internal PyPI mirror via
  ``ARTIFACTORY_USERNAME`` / ``ARTIFACTORY_PASSWORD`` env vars
- Runs ``uv sync --frozen`` to create ``.venv/`` from ``uv.lock``
- Sets ``git config core.hooksPath .githooks`` (pre-commit hook for agentic log policy)

After first-run, use either ``uv run <cmd>`` (no activation needed) or
``source .venv/bin/activate``.

**Environment variables required for integration/load tests:**

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Variable
     - Purpose
   * - ``ARTIFACTORY_USERNAME``
     - Atlassian internal PyPI auth (setup only)
   * - ``ARTIFACTORY_PASSWORD``
     - Atlassian internal PyPI auth (setup only)
   * - ``RAI_TEST_BASE_URL``
     - Remote target URL (integration tests vs deployed env)
   * - ``RAI_TEST_AUTH_TOKEN``
     - SLAUTH token for remote integration tests
   * - ``STATSIG_SERVER_SDK_KEY``
     - Feature gate SDK key (auto-stubbed as ``secret-dummykey`` for unit tests)

---

Layer 1 — Unit Tests
---------------------

**Quick run (local dev — parallel, no coverage, ~12s):**

.. code-block:: bash

    bin/unit-test
    # Equivalent to:
    uv run pytest

**With per-file branch-coverage gate (~18s):**

.. code-block:: bash

    bin/unit-test --coverage
    # Equivalent to:
    uv run pytest --cov=src --cov-branch --cov-report=html --cov-report=xml --cov-report=term
    uv run python bin/check-coverage-floors

**Run a specific file or directory:**

.. code-block:: bash

    uv run pytest test/unit_tests/inference_models/test_error_handling.py
    uv run pytest test/unit_tests/service/moderation/prompt/
    uv run pytest test/unit_tests/ -k "test_prompt"   # keyword filter
    uv run pytest test/unit_tests/ -x                 # stop on first failure

**Run a single test:**

.. code-block:: bash

    uv run pytest test/unit_tests/test_feature_service.py::TestClass::test_method -v

**Test discovery configuration** (``pyproject.toml [tool.pytest.ini_options]``):

.. code-block:: toml

    testpaths = ["test/unit_tests"]        # default discovery path
    addopts = "-n auto --tb=short --junitxml=test-reports/..."   # parallel + short tracebacks
    pythonpath = ["src"]                   # makes `from src.X import Y` work
    norecursedirs = ["model_onboarding", "notebooks", ".ve", ".venv", "build", "dist"]

**Pytest markers:**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Marker
     - Purpose
   * - ``@pytest.mark.smoke``
     - Fast sanity check: service alive, routes work, headers valid. Does NOT assert on AI outcomes.
   * - ``@pytest.mark.integration``
     - Asserts on actual moderation outcomes from the real AI backend.
   * - ``@pytest.mark.tenant_context``
     - Auto-skipped on remote targets (TCS mock unavailable in deployed envs).
   * - ``@pytest.mark.llama_model``
     - Auto-skipped in local Nebulae sandbox (gRPC/mTLS TeamServe unreachable locally).

**Automatically stubbed env vars** (via ``pytest-env``, ``pyproject.toml [tool.pytest_env]``):

.. code-block:: bash

    STATSIG_SERVER_SDK_KEY = "secret-dummykey"   # disables Statsig SDK network calls
    NO_JSON_LOGGING = "1"                         # human-readable logs during tests
    NO_CHECK_REQUIRED_VARS = "1"                  # skip mandatory env var enforcement
    NO_ASAP_SIGNER = "true"                       # stub ASAP JWT signing (no private key needed)

**Key test conftest fixtures** (``test/unit_tests/conftest.py``):

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Fixture
     - What it provides
   * - ``app``
     - Flask test app instance
   * - ``client``
     - Flask test client for HTTP requests
   * - ``app_context``
     - Active Flask app context (for ``g``, ``current_app``)
   * - ``request_context``
     - Active Flask request context
   * - ``mock_send_metric``
     - Patches ``src.metrics.metrics_handler.send_metric`` to a MagicMock
   * - ``mock_feature_service``
     - Patches ``FeatureService`` with all gates defaulting to ``False``
   * - ``mock_asap_headers``
     - Injects valid-looking ASAP/SLAUTH headers into Flask request context
   * - ``mock_boto3``
     - Stubs AWS boto3 client calls

---

Layer 2 — Coverage Enforcement
--------------------------------

Coverage is enforced at **two levels**:

1. **Global floor**: project-wide aggregate branch coverage (configured in ``bin/unit-test --coverage``)
2. **Per-file floors**: per-file branch-coverage minimums in ``coverage-floors.yml``

**View current per-file floors vs actuals:**

.. code-block:: bash

    uv run python bin/check-coverage-floors --print

**Key per-file floors** (from ``coverage-floors.yml``, verified 2026-04-20):

.. list-table::
   :widths: 60 15 25
   :header-rows: 1

   * - File
     - Floor
     - Baseline
   * - ``src/api/v1/moderation/prompt_moderation_controller.py``
     - **100%**
     - 100% (pinned — 98.9% of prod traffic)
   * - ``src/api/v1/moderation/agent_moderation_controller.py``
     - **100%**
     - 100% (pinned)
   * - ``src/api/v1/moderation/output_moderation_controller.py``
     - **100%**
     - 100% (pinned)
   * - ``src/service/moderation/prompt/prompt_moderation.py``
     - **98%**
     - 100%
   * - ``src/service/moderation/output/output_moderation.py``
     - **98%**
     - 100%
   * - ``src/inference_models/error_handling.py``
     - **98%**
     - 100%
   * - ``src/inference_models/rai_gpt_oss.py``
     - **100%**
     - 100% (pinned — GPT-OSS rollout path)
   * - ``src/service/moderation/output/stream_processor.py``
     - **93%**
     - 95%
   * - ``src/api/v1/moderation/image_moderation_controller.py``
     - **89%**
     - 91%
   * - ``src/service/moderation/agent/agent_moderation.py``
     - **88%**
     - 90%
   * - ``src/service/moderation/model_text_response_parse.py``
     - **74%**
     - 76% (target: 90% — tracked)
   * - ``src/inference_models/rai_llama.py``
     - **74%**
     - 76%

**How to add a new floor entry:**

.. code-block:: bash

    # 1. Run coverage for the specific module
    uv run pytest --cov=src/path/to/module --cov-branch --cov-report=term-missing test/unit_tests/

    # 2. Note the branch% for the file, floor = measured% - 2 (drift buffer)
    # 3. Add to coverage-floors.yml and commit in the same PR as the tests

---

Layer 3 — Linting & Type Checking
-----------------------------------

**Ruff (linter + formatter, replaces flake8 + black + isort):**

.. code-block:: bash

    uv run ruff check --fix src/ test/   # lint with auto-fix
    uv run ruff format src/ test/        # format (black-compatible)
    uv run ruff check src/ test/         # lint only (no fix, for CI)

**Pyright (type checking, strict for ``src/``):**

.. code-block:: bash

    uv run pyright                       # runs against pyrightconfig.json
    # Strict mode: src/
    # Basic mode: test/
    # Excluded: model_onboarding/, notebooks/, *.ipynb

**Pre-commit (runs ruff + pyright on staged files):**

.. code-block:: bash

    pre-commit run --all-files --show-diff-on-failure
    # Hook chain:
    # 1. ruff-check (--fix)
    # 2. ruff-format
    # 3. pyright (via `uv run pyright`)

**Full local validation (mirrors CI exactly):**

.. code-block:: bash

    pre-commit run --all-files && bin/unit-test --coverage

---

Layer 4 — Integration Tests
-----------------------------

Integration tests live in ``test/integration_tests/`` and require either a running
Nebulae sandbox or a deployed environment.

**Prerequisites: Start local Nebulae sandbox:**

.. code-block:: bash

    # Install Nebulae once
    bin/install-nebulae

    # Start sandbox (writes connection info to env.json)
    atlas nebulae start --export-env=env.json

    # Start the service (in a separate terminal)
    bin/start-app-locally.sh    # gunicorn on port 8090, gevent workers
    # OR
    bin/start-app.sh

**Run integration tests (local sandbox):**

.. code-block:: bash

    bin/integration-test                    # smoke → integration (full)
    bin/integration-test --smoke            # smoke only (fast sanity)
    bin/integration-test --integration      # integration only (AI outcomes)
    bin/integration-test --regression       # regression suite only

**Run integration tests (against deployed environment):**

.. code-block:: bash

    bin/integration-test --target ddev      # https://responsible-ai-api.ap-southeast-2.dev.atl-paas.net
    bin/integration-test --target staging   # https://responsible-ai-api.us-east-1.staging.atl-paas.net
    bin/integration-test --target https://custom-url.example.com   # custom URL

    # With specific test stage:
    bin/integration-test --smoke --target ddev
    bin/integration-test --integration --target staging

**Run a specific integration test file:**

.. code-block:: bash

    uv run pytest test/integration_tests/test_prompt_moderation.py -v -m smoke
    uv run pytest test/integration_tests/test_agent_moderation.py -v -m integration
    uv run pytest test/integration_tests/ -m "smoke and not tenant_context"

**Integration test fixture setup** (``test/integration_tests/conftest.py``):

- ``base_url``: reads from ``env.json`` (local) or ``RAI_TEST_BASE_URL`` env var (remote)
- ``auth_headers``: SLAUTH scheme for remote; empty dict for local sandbox
- ``model_overrides``: parametrized fixture runs each test twice — once for GPT-OSS, once for LLaMA
- Auto-skips: ``@pytest.mark.llama_model`` on local (gRPC/mTLS TeamServe unavailable)
- Auto-skips: ``@pytest.mark.tenant_context`` on remote (TCS mock unavailable in deployed env)

**TCS Sidecar Mock** (``tcs-sidecar-mock/``):

The TCS (Tenant Context Service) sidecar is mocked locally via static files:

.. code-block:: bash

    # Organization lookup files:
    tcs-sidecar-mock/organization/ari:cloud:platform::site/{CLOUD-ID}.ari.linked-org

    # Settings lookup files:
    tcs-sidecar-mock/settings_service/{Encoded-resource-ari}/atlassian-hosted-llms

    # Test endpoints after nebulae up:
    curl http://localhost:50050/entity/organization/ari:cloud:platform::site/0d34e502-700b-400c-9163-fa853c1c4ee3.ari.linked-org
    curl http://localhost:50050/entity/settings_service/.../atlassian-hosted-llms

---

Layer 5 — Load & Capacity Tests
---------------------------------

Load tests use **Locust** (Python-based) and are orchestrated via **Perfhammer** (Atlassian internal).

**Test scripts location:** ``test/capacity/``

.. code-block:: text

    test/capacity/
    ├── agent_moderation.py       # Locust load test: agent moderation endpoint
    ├── prompt_moderation.py      # Locust load test: prompt moderation endpoint
    ├── conftest.py
    ├── rai_api_client.py         # Shared HTTP client with auth headers
    └── perfhammer-definitions/
        ├── agent-moderation.json
        └── prompt-moderation.json

**Run locally with Locust (manual):**

.. code-block:: bash

    pip install locust   # or: uv add locust --dev

    # Headless load test (10 users, 60s, against staging):
    locust -f test/capacity/prompt_moderation.py \
      --host https://responsible-ai-api.us-east-1.staging.atl-paas.net \
      --users 10 --spawn-rate 2 --run-time 60s --headless

    # With Locust web UI (http://localhost:8089):
    locust -f test/capacity/prompt_moderation.py \
      --host https://responsible-ai-api.us-east-1.staging.atl-paas.net

**Via Perfhammer (Atlassian internal — CI/capacity pipeline):**

.. code-block:: bash

    bin/perf-test   # wraps Perfhammer with project config

**Perfhammer definition** (``test/capacity/perfhammer-definitions/agent-moderation.json``):

.. code-block:: json

    {
      "script_name": "test/capacity/agent_moderation.py",
      "ramp_up_time": 10,
      "steady_state_time": 360,
      "user_count": 5,
      "environment_vars": {
        "HOST": "https://responsible-ai-api--app.ap-southeast-2.dev.atl-paas.net"
      },
      "micros_env": "adev"
    }

**Load test SOP** (from ``agentic-coding-logs/2026-04-21-142500-launchpad-load-test-playbook-and-script-cleanup.md``):

1. Deploy candidate build to staging/ddev
2. Establish baseline P50/P95/P99 via Locust (400 concurrent users, 5 min warmup)
3. Record SignalFx metrics: ``rai.prompt_moderation.latency_ms``, ``rai.prompt_moderation.outcome``
4. Deploy change; re-run identical Locust script
5. Compare P50/P95/P99 and error rate between runs
6. Success: P95 drops ≥ target improvement (e.g. ≥10% for ITEM 1 double-tokenization fix)

---

Layer 6 — CI/CD Pipeline
--------------------------

**Pipeline file:** ``bitbucket-pipelines.yml``

**Master branch pipeline:**

.. code-block:: text

    Step 1: Synthesise Service Descriptor (Sliver)

    Step 2 (parallel):
    ├── Lint: `uv run pre-commit run --all-files`
    ├── Validate micros service descriptor
    ├── Unit tests: `uv run pytest` (parallel, --junitxml)
    ├── Integration tests: `bin/integration-test`
    └── Regression tests: `bin/integration-test --regression` (ignore failures, 20min timeout)

    Step 3 (parallel, only if Step 2 passes):
    ├── Build & push Docker image (SOX-compliant or non-SOX based on branch)
    ├── Test & upload policies (Poco)
    └── Upload service descriptor

**Pull request pipeline:** Same as master, minus Step 3 (no build/publish).

**Custom pipelines:**

.. code-block:: bash

    # Staging deploy
    # Trigger in Bitbucket UI: "deploy-atlaskube-staging" custom pipeline
    # Runs: non-SOX build → Poco upload → archetype deploy

---

Layer 7 — Utility Scripts (``bin/``)
--------------------------------------

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Script
     - Purpose
   * - ``bin/first-run``
     - Bootstrap: install uv, sync deps, configure git hooks
   * - ``bin/unit-test``
     - Run unit tests (with/without coverage gate)
   * - ``bin/check-coverage-floors``
     - Enforce per-file branch-coverage floors from ``coverage-floors.yml``
   * - ``bin/integration-test``
     - Run smoke/integration/regression against sandbox or deployed env
   * - ``bin/start-app-locally.sh``
     - Start gunicorn server locally on port 8090 (gevent workers)
   * - ``bin/start-app.sh``
     - Alternate startup script (used by Nebulae)
   * - ``bin/build``
     - Generate version metadata (``release-version.json``, ``git-version.json``)
   * - ``bin/package``
     - Build Docker image
   * - ``bin/publish``
     - Push Docker image to artifact registry
   * - ``bin/apply-dashboard``
     - Deploy SignalFx dashboard from ``operations/terraform/dashboard.tf``
   * - ``bin/install-nebulae``
     - Install Nebulae CLI for sandbox management
   * - ``bin/install-sliver``
     - Install Sliver for service descriptor synthesis
   * - ``bin/perf-test``
     - Run Perfhammer capacity tests
   * - ``bin/send-test-requests``
     - Fire manual test requests against a running instance
   * - ``bin/query-signalfx``
     - Query SignalFx metrics from CLI
   * - ``bin/atlas-install``
     - Install Atlas CLI tools

---

Complete Local Dev Workflow (Step-by-Step)
-------------------------------------------

.. code-block:: bash

    # ── SETUP (one time) ──────────────────────────────────────────────
    bin/first-run

    # ── BEFORE EVERY CODING SESSION ──────────────────────────────────
    git pull --rebase
    uv sync --frozen           # keep .venv in sync if uv.lock changed

    # ── DURING DEVELOPMENT (fast feedback loop) ───────────────────────
    uv run pytest test/unit_tests/path/to/test_file.py -x -v

    # ── BEFORE COMMITTING ─────────────────────────────────────────────
    pre-commit run --all-files     # lint + type check
    bin/unit-test --coverage       # unit tests + coverage floors

    # ── INTEGRATION TEST (local sandbox) ─────────────────────────────
    atlas nebulae start --export-env=env.json   # terminal 1
    bin/start-app-locally.sh                    # terminal 2
    bin/integration-test --smoke                # terminal 3

    # ── FULL INTEGRATION TEST ─────────────────────────────────────────
    bin/integration-test                        # smoke + integration

    # ── CHECK COVERAGE FLOORS ─────────────────────────────────────────
    uv run python bin/check-coverage-floors --print   # view actuals vs floors

=============================================================================

responsible-ai (Research Repo)
================================

Environment Setup
-----------------

.. code-block:: bash

    cd /Users/tchen7/MyProjects/atlassian_packages/responsible-ai

    # 1. Install pyenv (one time)
    curl https://pyenv.run | bash

    # 2. Install required Python version
    pyenv install   # reads .python-version (Python 3.12.*)

    # 3. Install Pants (build system, one time)
    # Follow: https://www.pantsbuild.org/2.24.0/docs/getting-started/installing-pants
    # After install, the `pants` script is available in the repo root

    # 4. Verify
    pants --version   # should print 2.24.0

**Build system:** Pants 2.24.0 (monorepo tool — handles discovery, linting, testing, packaging)

**Python interpreters:** Pants-managed (``interpreter_constraints = ['==3.12.*']``)

**Dependency resolves** (``pants.toml``):

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Resolve name
     - Lock file
   * - ``python-default``
     - ``3rdparty/python/python-default.lock``
   * - ``inference``
     - ``3rdparty/python/inference.lock``
   * - ``evaluation``
     - ``3rdparty/python/evaluation.lock``

---

Source Roots & Scope
---------------------

**Pants only manages code under:**

.. code-block:: text

    /packages/     ← Python packages (e.g. packages/rai/harm_taxonomy/)
    /services/     ← Service code

**Explicitly ignored by Pants** (``pants.toml pants_ignore``):

.. code-block:: text

    msp_deploy/          ← model deployment scripts (run directly)
    services/responsible-ai-api/   ← separate repo
    notebooks/           ← Jupyter notebooks (run via Databricks/locally)
    experiments/         ← experiment scripts (run directly)
    analytics/           ← analytics scripts (run directly)

---

Layer 1 — Linting & Type Checking
-----------------------------------

.. code-block:: bash

    # Full lint + type check + BUILD file validation (mirrors CI exactly)
    pants tailor --check update-build-files --check lint check ::

    # What this runs:
    # tailor --check    : validates BUILD files are correct (does NOT modify)
    # lint              : ruff (black + flake8 + isort) on all Python files
    # check             : pyright type checking on all Python files

    # Lint only:
    pants lint ::

    # Type check only:
    pants check ::

    # Specific package:
    pants lint packages/rai/harm_taxonomy/
    pants check packages/rai/harm_taxonomy/

---

Layer 2 — Unit Tests
---------------------

.. code-block:: bash

    # Run all tests (with coverage, verbose — matches CI config from pants.ci.toml)
    pants test ::

    # Run tests for a specific package:
    pants test packages/rai/harm_taxonomy/

    # Run a specific test file:
    pants test packages/rai/harm_taxonomy/test_harm_taxonomy.py

    # Run with extra pytest args:
    pants test :: -- -k "test_specific_function"
    pants test :: -- -x   # stop on first failure

**CI test configuration** (``pants.ci.toml``):

.. code-block:: toml

    [test]
    use_coverage = true       # always collect coverage in CI

    [coverage-py]
    report = "xml"            # coverage.xml output
    global_report = true      # aggregate across all packages

    [pytest]
    args = ["-vv", "--no-header"]

**Note on test scope:** As of 2026-05-04, the research repo has very few actual test files
(only ``notebooks/fine-tuning/apc_pt_model_inference_test.py`` — a Databricks notebook, not
a pytest file). The codebase is primarily research/experiment code. Tests are added as
packages mature.

---

Layer 3 — Running Notebooks & Experiments
-------------------------------------------

Notebooks (``notebooks/``) and experiments (``experiments/``) are **NOT managed by Pants**.
They are run directly:

**Locally:**

.. code-block:: bash

    # Install notebook dependencies (use the evaluation resolve)
    pip install jupyter
    jupyter notebook notebooks/evaluation/

    # Run an experiment script directly:
    python experiments/image_moderation_v1/src/eval_image_moderations_v1.py

    # Run MSP deployment scripts (NOT via Pants):
    python msp_deploy/register_compliant_model.py --version v2.3.3

**Via Databricks:**

- Upload notebooks to Databricks workspace
- Execution managed by Databricks clusters
- See ``notebooks/fine-tuning/`` for training notebooks

---

Layer 4 — CI/CD Pipeline
--------------------------

**Pipeline file:** ``bitbucket-pipelines.yml``

**Default branch pipeline:**

.. code-block:: text

    Step 1: Pants lint + check
            `pants tailor --check update-build-files --check lint check ::`

    Step 2: Sauron update (internal metadata service)

**Custom pipeline:**

.. code-block:: text

    register-compliant-model-version-in-tarot:
        Registers a new model version in the MSP/Tarot model registry
        via a Databricks pipeline execution

---

Complete Local Dev Workflow (Research Repo)
--------------------------------------------

.. code-block:: bash

    # ── SETUP (one time) ──────────────────────────────────────────────
    curl https://pyenv.run | bash    # install pyenv
    pyenv install                    # install Python 3.12.*
    # install Pants per: https://www.pantsbuild.org/2.24.0/docs/getting-started/installing-pants

    # ── LINT & TYPE CHECK ─────────────────────────────────────────────
    pants tailor --check update-build-files --check lint check ::

    # ── RUN TESTS ─────────────────────────────────────────────────────
    pants test ::

    # ── SPECIFIC PACKAGE ──────────────────────────────────────────────
    pants test packages/rai/harm_taxonomy/
    pants lint packages/rai/harm_taxonomy/

    # ── NOTEBOOKS (not via Pants) ─────────────────────────────────────
    jupyter notebook notebooks/evaluation/

=============================================================================

Quick Reference — Side-by-Side
================================

.. list-table::
   :widths: 25 37 38
   :header-rows: 1

   * - Task
     - responsible-ai-api
     - responsible-ai
   * - **Package manager**
     - ``uv`` (``uv sync --frozen``)
     - Pants (manages interpreters)
   * - **Run all unit tests**
     - ``bin/unit-test``
     - ``pants test ::``
   * - **Run with coverage**
     - ``bin/unit-test --coverage``
     - ``pants test ::`` (always on in CI)
   * - **Lint**
     - ``uv run ruff check --fix src/ test/``
     - ``pants lint ::``
   * - **Type check**
     - ``uv run pyright``
     - ``pants check ::``
   * - **Full pre-commit**
     - ``pre-commit run --all-files``
     - ``pants tailor --check lint check ::``
   * - **Integration tests**
     - ``bin/integration-test``
     - N/A (research code)
   * - **Load tests**
     - ``locust -f test/capacity/prompt_moderation.py ...``
     - N/A
   * - **View coverage floors**
     - ``uv run python bin/check-coverage-floors --print``
     - ``pants test :: --[coverage-py].report=xml``
   * - **Start service locally**
     - ``bin/start-app-locally.sh`` (port 8090)
     - N/A
   * - **CI equivalent**
     - ``pre-commit run --all-files && bin/unit-test --coverage``
     - ``pants tailor --check lint check :: && pants test ::``
