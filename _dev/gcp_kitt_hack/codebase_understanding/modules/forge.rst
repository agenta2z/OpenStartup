==================================
``forge/`` — sample Atlassian Forge applications
==================================

Purpose
=======
Reference / development implementations of Atlassian Forge apps used to
exercise the :doc:`forge-containers` operator end-to-end.

Layout
======
::

    forge/
      quiz-app/
        src/                       # quiz application code
      i18n-question-generator/
        src/frontend/              # frontend code
      long-running-app/
        src/generateReport.js      # async report generation
        src/pushToQueue.js         # job push to async queue

Tech
====
JavaScript / TypeScript, Node.js. Each subdir is an independent
Forge-app project (own ``package.json`` / manifest).

Integration
===========
When packaged as a ``ForgeApp`` CRD instance and applied to the
cluster, these apps are reconciled by the
:doc:`forge-containers` controller, which generates the matching
``Deployment`` + ``ServiceAccount`` + sidecars.

Use case
========
- ``quiz-app`` — minimal happy-path Forge app, used as a smoke test.
- ``long-running-app`` — exercises the async / queueing path; pairs
  well with :doc:`pae` workloads.
- ``i18n-question-generator`` — exercises frontend rendering.
