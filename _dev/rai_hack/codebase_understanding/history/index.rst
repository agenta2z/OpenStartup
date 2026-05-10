.. _rai-history:

==============================================================================
Development History & Decision Provenance
==============================================================================

Captures the *historical why* behind production design choices in
``responsible-ai-api`` and ``responsible-ai``, so future contributors
(human and machine) do not accidentally undo intentional decisions.

**Created**: 2026-05-06 (Wave 9 follow-up investigation)
**Trigger**: Before applying Wave-9 "serving-infra latency quick wins",
verify each change is not undoing prior production design.
**Method**: 4 parallel Explore subagents + direct git verification on
``responsible-ai-api`` master HEAD ``37fec91``.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   README
   01-decision-timeline
   02-perf-decision-archive
   03-wave9-historical-validation
   04-agent-claim-audit
   05-source-of-truth-cheatsheet
   06-tenant-safe-perf-opportunities

Quick reference
================

* **Need a Wave 9 verdict?** See :doc:`03-wave9-historical-validation`
* **Want the timeline?** See :doc:`01-decision-timeline`
* **Want the perf-PR catalog?** See :doc:`02-perf-decision-archive`
* **Want to know how reliable the agent reports were?** See :doc:`04-agent-claim-audit`
* **Need a 30-second machine-readable lookup?** See :doc:`05-source-of-truth-cheatsheet`
