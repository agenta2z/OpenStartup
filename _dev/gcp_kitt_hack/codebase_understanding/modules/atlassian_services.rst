==================================
``atlassian_services/`` — Atlassian microservice deployment inventory
==================================

Purpose
=======
Reporting / analytics toolkit. Aggregates an Atlassian-wide
microservice deployment inventory (shard counts, region distribution,
production vs. lower environments) and emits CSV + PNG visualisations.

Layout
======
::

    atlassian_services/
      analyze_sliver_services.py         # data-aggregation script
      services_20plus_shards_report.md   # 16-row table of services with 20+ prod shards
      sliver_services_per_region.csv     # service → region mapping
      *.png                              # shard-count histograms, region distributions

Highlight
=========
- ``jira-monolith-deploy``: 394 shards across 12 regions (largest entry
  in the report).

Integration
===========
Reporting only — **not** part of the deploy pipeline. Output feeds
capacity-planning and architecture review conversations.
