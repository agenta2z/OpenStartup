Integrations
============

``code-conseil`` reaches out to several third-party systems. This page
catalogues those integrations and the hooks the package exposes for
swapping or extending them.

.. contents::
   :local:
   :depth: 1

GitHub
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Use case:** ``code-conseil`` fetches PR diffs, posts inline review comments, and gates merges from the code-review companion.
* **Authentication:** ``GITHUB_TOKEN`` (PAT with ``repo`` + ``pull_request`` scopes) or a GitHub App private key supplied via ``GITHUB_APP_PRIVATE_KEY_PATH`` + ``GITHUB_APP_ID``. See the ``code_conseil.config`` section
  of the API reference for the full settings table.
* **Endpoints / webhooks:** REST v3 (``https://api.github.com``) plus the GraphQL v4 endpoint for batched PR queries; inbound webhooks land at ``POST /webhooks/github``.
* **Failure mode:** transport errors are wrapped in the package's
  ``IntegrationError`` (carrying ``vendor``, ``status_code``, and
  ``request_id``) and re-raised through the CLI / API with a stable
  non-zero exit code so callers can branch deterministically.
* **Rate limiting:** 5,000 req/h per PAT or 15,000 req/h for GitHub Apps; the adapter respects the ``X-RateLimit-Reset`` header and switches to a secondary token from ``GITHUB_TOKEN_POOL`` when below 100 remaining.

Bitbucket
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Use case:** ``code-conseil`` drives PR-level review automation in Bitbucket Cloud and posts approvals once the conseil engine signs off.
* **Authentication:** ``BITBUCKET_ACCESS_TOKEN`` (workspace-scoped) or ``BITBUCKET_USERNAME`` + ``BITBUCKET_APP_PASSWORD``. See the ``code_conseil.config`` section
  of the API reference for the full settings table.
* **Endpoints / webhooks:** Bitbucket Cloud REST v2 (``https://api.bitbucket.org/2.0``); inbound webhooks land at ``POST /webhooks/bitbucket``.
* **Failure mode:** transport errors are wrapped in the package's
  ``IntegrationError`` (carrying ``vendor``, ``status_code``, and
  ``request_id``) and re-raised through the CLI / API with a stable
  non-zero exit code so callers can branch deterministically.
* **Rate limiting:** 1,000 req/h per IP for unauthenticated callers, 60 req/s burst with token; the adapter watches ``X-RateLimit-Remaining`` and falls back to exponential backoff (cap 60s).

Jira
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Use case:** ``code-conseil`` links code-review verdicts back onto Jira tickets and transitions issues when conseil-approved PRs are merged.
* **Authentication:** ``JIRA_BASE_URL`` + ``JIRA_USER_EMAIL`` + ``JIRA_API_TOKEN`` (basic auth) or ``ATLASSIAN_OAUTH_TOKEN`` for OAuth 2.0 (3LO). See the ``code_conseil.config`` section
  of the API reference for the full settings table.
* **Endpoints / webhooks:** Atlassian Jira Cloud REST v3 (``{base}/rest/api/3``) and Agile v1 for board metadata.
* **Failure mode:** transport errors are wrapped in the package's
  ``IntegrationError`` (carrying ``vendor``, ``status_code``, and
  ``request_id``) and re-raised through the CLI / API with a stable
  non-zero exit code so callers can branch deterministically.
* **Rate limiting:** Atlassian Cloud sliding-window limiter; adapter honours ``Retry-After`` and applies a token-bucket throttle defaulting to 10 req/s.

OpenAI / Anthropic chat completion APIs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Use case:** ``code-conseil`` generates the actual review text and suggestion patches; the package routes between providers per ``CONSEIL_LLM_ROUTING``.
* **Authentication:** ``OPENAI_API_KEY`` and/or ``ANTHROPIC_API_KEY``; optional ``OPENAI_ORG`` for billing scoping. See the ``code_conseil.config`` section
  of the API reference for the full settings table.
* **Endpoints / webhooks:** ``https://api.openai.com/v1/chat/completions`` and ``https://api.anthropic.com/v1/messages``.
* **Failure mode:** transport errors are wrapped in the package's
  ``IntegrationError`` (carrying ``vendor``, ``status_code``, and
  ``request_id``) and re-raised through the CLI / API with a stable
  non-zero exit code so callers can branch deterministically.
* **Rate limiting:** Provider-specific RPM/TPM tiers; adapter implements an in-process token-bucket keyed by model id and surfaces ``RateLimitError`` to callers after 3 retries.

Extending
----------------------------------------

Adapters live under ``code_conseil.adapters``. To add a new third-party
hook:

1. Subclass ``code_conseil.adapters.base.BaseAdapter``.
2. Register the adapter via the entry-point group
   ``code-conseil.adapters`` in ``pyproject.toml``.
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
