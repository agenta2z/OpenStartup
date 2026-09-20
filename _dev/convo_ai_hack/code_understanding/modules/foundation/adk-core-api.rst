.. _mod-adk-core-api:

==============================================
``foundation/adk/core-api``
==============================================

:Tier: foundation
:Path: ``modules/foundation/adk/core-api``
:Size: ~919 source lines :sup:`(verified)`
:Importance: **Tier 2 — agent contracts**

Agent Development Kit contracts at the foundation level. Every product that hosts agents depends on this.

Public surface :sup:`(per agent investigation)`
=================================================

* Agent definition contracts (Agent, Tool, Skill base classes)
* Capability discovery interfaces (uses Java Reflections library)

Dependencies :sup:`(verified)`
================================

* Google ADK Extensions (Java)
* ``foundation/utilities-api``
* ``Reflections`` library (for runtime classpath scanning)

Patterns
==========

1. **Reflection-based registration.** Tools / skills can register themselves via classpath scanning.
2. **Pure foundation.** No platform/product deps.

What you would change here
============================

* Modify the Agent/Tool/Skill base contracts → here
* Modify discovery / registration logic → here

