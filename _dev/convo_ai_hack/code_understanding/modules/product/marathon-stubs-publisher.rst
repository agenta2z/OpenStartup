.. _mod-marathon-stubs-publisher:

==============================================
``product/rovo/marathon-stubs-publisher``
==============================================

:Tier: product
:Path: ``modules/product/rovo/marathon-stubs-publisher``
:Size: ~369 source lines :sup:`(verified)`

**CLI utility** for publishing Marathon test stubs. Standalone tool, not a Spring service.

Top files :sup:`(verified)`
============================

* ``PublishStubsTask.kt`` — 86 lines
* ``Cli.kt`` — 68 lines
* ``VerifyHashTask.kt`` — 60 lines
* ``ComputeHashTask.kt`` — 60 lines

Notable findings
==================

* CLI-driven (``Cli.kt`` entry point).
* Hash verify/compute tasks suggest the stubs are content-addressed — uploads check hash to avoid duplicate publishes.
* Used for setting up Marathon's wiremock fixtures during integration testing.

