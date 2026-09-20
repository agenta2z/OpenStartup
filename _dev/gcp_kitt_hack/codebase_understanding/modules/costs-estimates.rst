==================================
``costs-estimates/`` — GCP/AWS pod-hosting cost calculator
==================================

Purpose
=======
Python + Pandas calculator that compares **bare-metal vs. VM** hosting
costs for a target pod count, using a fixed pod-shape assumption.

Layout
======
::

    costs-estimates/
      compute_costs.py              # main calculator
      rules.txt                     # assumptions (1 pod = 1 vCPU + 2 GB; 720 hrs/mo; min 3 nodes)
      cost_comparison_table.csv     # sample output
      *.png                         # cost graphs

Function surface
================
- ``calculate_node_requirements()``
- ``calculate_nodes_needed()``
- ``calculate_monthly_cost()``
- ``get_recommended_option()``

Integration
===========
Standalone planning tool. Not invoked by Helmfile, ArgoCD, or any
runtime component.
