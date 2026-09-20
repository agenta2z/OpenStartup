==================================
``tests/`` — service-discovery test fixtures
==================================

Purpose
=======
Test-data and harness for the top-level ``analyze_service_regions.py``
script. Lists 152 Atlassian microservices and lets you query their
deployment regions via the Atlas CLI.

Layout
======
::

    tests/
      README.md            # documentation for analyze_service_regions.py
      service_list.txt     # 152 microservice names

Integration
===========
Companion to ``analyze_service_regions.py`` at the repo root. The
script iterates ``service_list.txt`` and shells out to the Atlas CLI
for region info per service.

Cross-references
================
- :doc:`atlassian_services` and :doc:`cdp_services` consume similar
  inventory shapes.
