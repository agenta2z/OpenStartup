==================================
``busybox/`` — debug container image
==================================

Purpose
=======
Custom debug-utility container image used for ``kubectl debug`` sessions
into production pods. Ships standard Unix tooling plus a few in-house
helpers.

Layout
======
::

    busybox/
      Dockerfile        # image definition
      Makefile          # build targets
      test.sh           # example kubectl debug invocation

Image registry
==============
``us-east4-docker.pkg.dev/gcp-5319e002/kitt-east4/busybox-larry:1.0.0``

Operational use
===============
.. code-block:: bash

    kubectl debug <pod> \
      --image=us-east4-docker.pkg.dev/gcp-5319e002/kitt-east4/busybox-larry:1.0.0 \
      -it -- sh

Gotchas
=======
- Tag is hardcoded in ``test.sh``; bump in lock-step with ``Makefile``
  on each rebuild to avoid pulling stale image cache.
