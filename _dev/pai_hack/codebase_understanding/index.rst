.. Proactive AI Service documentation master file.

======================================
Proactive AI Service — Documentation
======================================

Welcome to the **Proactive AI Service** technical documentation.  This site
covers architecture, module-level design, cross-cutting concerns, and
operational guidance for the ``proactive-ai`` micro-service.

.. note::

   This documentation uses **15 top-level packages (16 functional modules)**
   because the ``feature`` package contains two distinct functional modules
   (Nudge Throttle and Rovo Insights) that are treated separately for design
   and operational purposes.

Quick Links
-----------

* :doc:`overviews/01-multi-axis-matrix` — at-a-glance module comparison
* :doc:`overviews/03-criticality-dashboard` — operational criticality rankings
* :doc:`architecture/01-architecture-overview` — component topology & dependency DAG
* :doc:`architecture/02-request-lifecycle` — end-to-end HTTP request trace
* :doc:`architecture/00-glossary` — key terms & acronyms

.. toctree::
   :maxdepth: 2
   :caption: Overviews

   overviews/01-multi-axis-matrix
   overviews/02-architectural-narrative
   overviews/03-criticality-dashboard

.. toctree::
   :maxdepth: 2
   :caption: Architecture

   architecture/00-glossary
   architecture/01-architecture-overview
   architecture/02-request-lifecycle
   architecture/03-module-catalog

.. toctree::
   :maxdepth: 2
   :caption: Cross-Cutting Concerns

   architecture/cross-cutting/index

.. toctree::
   :maxdepth: 2
   :caption: Module Reference

   modules/index

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
