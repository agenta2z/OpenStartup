.. _tier-foundation:

==========================================================
Foundation tier — Atlassian platform integrations
==========================================================

The **lowest layer**. Provides Atlassian-platform integrations every higher tier depends on.

Architectural rule: foundation may NOT depend on any platform / product / service module.
Test-time enforcement: ArchUnit (see ``foundation/testing-arch.rst``).

Module catalog
================

.. toctree::
   :maxdepth: 1

   utilities-api
   utilities-impl
   metrics-api
   feature-flag-api
   feature-flag-impl
   adk-core-api
   ers-api
   ers-impl
   testing-arch
   testing-it-core
