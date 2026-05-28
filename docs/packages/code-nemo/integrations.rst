Integrations
============

``code-nemo`` reaches out to several third-party systems. This page
catalogues those integrations and the hooks the package exposes for
swapping or extending them.

.. contents::
   :local:
   :depth: 1

LangChain
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Use case:** ``code-nemo`` orchestrates multi-step refactor plans (plan -> patch -> verify) via LangChain runnables.
* **Authentication:** No direct credentials; LangChain reads provider keys from the same env vars used by the chat completion adapters. See the ``code_nemo.config`` section
  of the API reference for the full settings table.
* **Endpoints / webhooks:** Local in-process LangChain runtime; optional ``LANGCHAIN_TRACING_V2=1`` + ``LANGCHAIN_API_KEY`` ships traces to LangSmith.
* **Failure mode:** transport errors are wrapped in the package's
  ``IntegrationError`` (carrying ``vendor``, ``status_code``, and
  ``request_id``) and re-raised through the CLI / API with a stable
  non-zero exit code so callers can branch deterministically.
* **Rate limiting:** Per-runnable concurrency limited by ``NEMO_LANGCHAIN_MAX_CONCURRENCY`` (default 4); failures retried with jittered backoff.

OpenAI / Anthropic chat completion APIs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Use case:** ``code-nemo`` produces the patch hunks, summary, and verification rationales for each refactor step.
* **Authentication:** ``OPENAI_API_KEY`` and/or ``ANTHROPIC_API_KEY``; model selection via ``NEMO_PLANNER_MODEL`` / ``NEMO_EDITOR_MODEL`` / ``NEMO_VERIFIER_MODEL``. See the ``code_nemo.config`` section
  of the API reference for the full settings table.
* **Endpoints / webhooks:** ``https://api.openai.com/v1/chat/completions`` and ``https://api.anthropic.com/v1/messages``; supports streaming for the editor stage.
* **Failure mode:** transport errors are wrapped in the package's
  ``IntegrationError`` (carrying ``vendor``, ``status_code``, and
  ``request_id``) and re-raised through the CLI / API with a stable
  non-zero exit code so callers can branch deterministically.
* **Rate limiting:** Token-bucket per model id; adapter halves request size and retries on ``context_length_exceeded``.

Bitbucket / GitHub PR APIs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Use case:** ``code-nemo`` opens, updates, and comments on pull requests carrying the proposed refactor diff.
* **Authentication:** Reuses ``BITBUCKET_ACCESS_TOKEN`` / ``GITHUB_TOKEN`` from the wider OpenStartup stack; defaults to a service account when ``NEMO_AUTHOR_AS_SERVICE_ACCOUNT=1``. See the ``code_nemo.config`` section
  of the API reference for the full settings table.
* **Endpoints / webhooks:** Bitbucket Cloud REST v2 ``/repositories/{ws}/{repo}/pullrequests`` and GitHub REST v3 ``/repos/{org}/{repo}/pulls``.
* **Failure mode:** transport errors are wrapped in the package's
  ``IntegrationError`` (carrying ``vendor``, ``status_code``, and
  ``request_id``) and re-raised through the CLI / API with a stable
  non-zero exit code so callers can branch deterministically.
* **Rate limiting:** Same per-provider envelopes as ``code-conseil``; the PR-creation path additionally serialises to one open PR per branch to avoid duplicate work.

Extending
----------------------------------------

Adapters live under ``code_nemo.adapters``. To add a new third-party
hook:

1. Subclass ``code_nemo.adapters.base.BaseAdapter``.
2. Register the adapter via the entry-point group
   ``code-nemo.adapters`` in ``pyproject.toml``.
3. Document the new integration in this file under its own heading,
   following the same Use case / Authentication / Endpoints / Failure
   mode / Rate limiting structure used above so consumers can scan the
   page consistently.

Webhooks
----------------------------------------

For inbound events (e.g. PR review requests), the package can be deployed
behind the shared OpenStartup webhook router. See the
``docs/MCP_INTEGRATION.md`` and ``docs/operations.rst`` files at the
repository root for the routing configuration; the package itself only
needs the ``WEBHOOK_SECRET`` environment variable set so it can verify
inbound payload signatures.
