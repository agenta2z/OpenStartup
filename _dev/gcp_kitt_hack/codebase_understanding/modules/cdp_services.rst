==================================
``cdp_services/`` — service-to-environment explosion + region stats
==================================

Purpose
=======
Companion analytics module to :doc:`atlassian_services`. Explodes a
single ``all_environments`` column into one row per
``(service, environment)`` pair, then plots region-count histograms.

Layout
======
::

    cdp_services/
      explode_environments.py     # main script
      all.csv                     # input service list (one row per service)
      service_environments.csv    # exploded output
      region_count_histogram.py   # plotting script
      *.csv, *.png                # data + visualisations

Integration
===========
Analytics / reporting only; consumed by capacity-planning workflows.
