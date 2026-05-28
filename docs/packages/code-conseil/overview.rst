Overview
========

AI-assisted code-review and pairing companion that orchestrates suggestion engines for engineers.

Purpose
----------------------------------------

``code-conseil`` is the **FEATURE** package responsible for delivering
the user-visible capability described above. It is one of six FEATURE /
INTEGRATION / UI packages that compose the application layer of the
OpenStartup monorepo and sits on top of the four core packages
(``openteam``, ``server``, ``inference``, ``runtime``).

Audience
----------------------------------------

* **Application developers** integrating ``code-conseil`` into a workflow.
* **Platform engineers** deploying it alongside the OpenStartup stack.
* **LLM-agent authors** consuming the package's HTTP or MCP surface.

Scope
----------------------------------------

In scope:

* Programmatic API exposed by the ``code_conseil`` Python module.
* Configuration knobs, environment variables, and runtime flags.
* Operational guidance for local development and deployed environments.

Out of scope (documented elsewhere):

* Core scheduling, model-serving, and infrastructure concerns — see the
  four core package doc sets under ``docs/packages/``.
* Cross-cutting topics such as authentication and observability are covered
  by the top-level the top-level ``docs/source/operations.rst`` reference and the top-level ``docs/source/configuration.rst`` reference pages.

Feature highlights
----------------------------------------

* Built on the OpenStartup runtime contracts, so it composes cleanly with
  the rest of the platform.
* Ships a thin, mockable surface so docs and tests can build without the
  full third-party dependency set.
* Provides type-stable entrypoints intended for both human users (CLI) and
  automation (Python API / MCP tools / HTTP routes, depending on package
  type).
