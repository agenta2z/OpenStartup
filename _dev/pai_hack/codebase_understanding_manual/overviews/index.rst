.. _pai-overviews:

====================
Cross-cutting Overviews
====================

Three lenses on the codebase before you dive into per-module detail.

.. toctree::
   :maxdepth: 2

   01-multi-axis-matrix
   02-architectural-narrative
   03-criticality-dashboard

Overview documents
====================

**01-multi-axis-matrix.rst** — All 15 packages mapped by size (LoC), tier (feature/platform), and purpose. Use this to find "where does X live?"

**02-architectural-narrative.rst** — A walking tour: HTTP request arrives → request context initialized → business logic routes to feature packages → async tasks queued to SQS → workers consume downstream. Explains the happy path + key abstractions (Envelope, Context, TaskFramework).

**03-criticality-dashboard.rst** — SRE view: packages ranked by blast-radius (impact if down) and ownership. On-call teams use this to prioritize incidents.
