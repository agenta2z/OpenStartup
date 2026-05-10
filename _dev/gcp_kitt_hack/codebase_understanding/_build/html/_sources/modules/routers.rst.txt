==================================
``routers/`` — lightweight Python URL router
==================================

Purpose
=======
Standalone Python middleware library that maps URL paths to handler
callables with both **exact** and **wildcard** route matching. Used by
in-cluster web services and gateways within ``gcp_kitt`` that don't want
the weight of Flask/FastAPI routing.

Layout
======
::

    routers/
      router.py                  # core Router class
      test_router.py             # unit tests
      test_wildcards.py          # wildcard matching tests
      test_performance.py        # benchmark suite
      example_usage.py
      example_wildcards.py
      example_path_parameters.py
      run_all_tests.py
      TEST_RESULTS.md            # benchmark output

Surface area
============
- ``class Router`` — main routing engine.
- Exact-match routes win over wildcard routes; longest-matching wildcard
  wins among wildcards.
- Path-parameter extraction supported.

Gotchas
=======
- Performance degrades with >1000 routes — ``test_performance.py``
  documents the curve.
- Library is unversioned (no ``setup.py`` / ``pyproject.toml``); consumers
  vendor it in directly.
