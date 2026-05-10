.. _mod-contrib-client-api:

==============================================
``contrib/client/client-api``
==============================================

:Tier: contrib
:Path: ``modules/contrib/client/client-api``
:Size: ~378 source lines :sup:`(verified)`

External-service client contracts contributed by sub-teams. Currently houses **TAP** (Atlassian Targeting Platform) and **A2A** (Agent-to-Agent) client APIs.

Top files :sup:`(verified)`
============================

* ``targetingplatform/TapResponse.kt``
* ``targetingplatform/TapClient.kt``
* ``targetingplatform/TapClientException.kt``
* ``a2a/A2AClient.kt``
* ``a2a/A2AClientCreationException.kt``

Notable findings
==================

* **NOT vestigial** — 13 Kotlin files, real content. The `contrib/` tier is the official extension point for sub-team-contributed clients/services that don't (yet) belong in platform.
* **TAP** = Atlassian's user-targeting / experimentation platform — used for feature targeting decisions.
* **A2A** = Agent-to-Agent protocol client — for one agent to call another agent.

