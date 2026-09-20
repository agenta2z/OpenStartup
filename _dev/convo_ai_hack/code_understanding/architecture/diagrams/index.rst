.. _diagrams-index:

============================
Diagrams
============================

Visual companions to the architecture documentation. Each diagram is paired with a "how to read it" guide and explicit "what this is NOT" boundaries.

All diagrams use **Mermaid** syntax — they render natively on GitHub, Bitbucket, and via the ``sphinxcontrib-mermaid`` Sphinx extension. To render to HTML/PDF, install the extension and add ``"sphinxcontrib.mermaid"`` to ``conf.py`` extensions.

The 7 diagrams
================

.. toctree::
   :maxdepth: 1

   01-tier-dependency-graph
   02-streaming-request-sequence
   03-ai-gateway-providers
   04-mdc-coroutine-state
   05-messaging-topology
   06-tenant-and-identity
   07-agent-runtime

Suggested reading order
========================

If you're new to the codebase:

1. Start with :ref:`diag-tier-graph` — the architectural shape
2. Then :ref:`diag-streaming-sequence` — see one request end-to-end
3. Then :ref:`diag-tenant-identity` — see how identity threads through
4. Then :ref:`diag-mdc-state` — understand the #1 footgun
5. Optional deeper dives: :ref:`diag-ai-gateway`, :ref:`diag-messaging`, :ref:`diag-agent-runtime`

If you're investigating a bug:

* Logs lose context across coroutines? → :ref:`diag-mdc-state`
* Cross-tenant data leak suspected? → :ref:`diag-tenant-identity`
* LLM call slow / failing? → :ref:`diag-streaming-sequence` + :ref:`diag-ai-gateway`
* Async task not running? → :ref:`diag-messaging`
* Build refuses your dep change? → :ref:`diag-tier-graph` (enforcement matrix)

If you're designing a new feature:

* Adding a new tool? → :ref:`diag-agent-runtime`
* Adding a new endpoint? → :ref:`diag-streaming-sequence` (controller layer)
* Adding a new async task? → :ref:`diag-messaging`
* Adding a new LLM provider? → :ref:`diag-ai-gateway`

What ALL diagrams share
========================

* **File:line citations** for every concrete claim. ``:sup:`(verified)``` markers where a sub-agent or I directly read the source.
* **"How to read it"** section explaining the visual grammar.
* **"What this is NOT"** to prevent over-interpretation.
* **Patterns visible in this diagram** — the takeaway insights you should walk away with.

What NO diagram tries to do
=============================

* **No class diagrams.** With 12,990 source files, class diagrams are noise.
* **No deployment topology.** The diagrams are about software architecture, not infrastructure.
* **No data model.** Per-table-per-field schemas live in Kamino documentation, not here.
* **No API reference.** OpenAPI / GraphQL schemas live in code; diagrams highlight patterns, not endpoints.

