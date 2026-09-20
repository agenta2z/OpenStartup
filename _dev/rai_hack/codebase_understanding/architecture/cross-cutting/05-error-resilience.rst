.. _rai-error-resilience:

================
Error Resilience
================

See :doc:`../../overviews/02-architectural-narrative` §Error resilience design for full documentation.

Summary: Fail-open by default on all inference errors. Circuit breakers on Triton gRPC/HTTP and anti-abuse. Tenacity retry on AI Gateway (timeout/network only, not 429). GASv3 analytics always non-blocking.
