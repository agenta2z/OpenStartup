.. _mod-convo-ai-service-descriptor:

==============================================
``service/convo-ai-service-descriptor``
==============================================

:Tier: service
:Path: ``modules/service/convo-ai-service-descriptor``
:Size: 0 source lines (configuration only)

**Atlas / Micros deployment descriptor** — defines how the service is built and deployed via Atlassian's Micros platform.

Files :sup:`(verified)`
========================

* ``convo-ai.ad.yml`` — main archetype descriptor
* ``alias.sd.yml`` — service alias

Descriptor structure :sup:`(verified)`
=========================================

* **Schema version**: 1.1.0
* **ASAP impersonation group**: ``convo-ai-archetype`` (impersonates the commercial service)
* **Compute CRD**:

  * Business unit: ``Engineering-AI``
  * Memory limit: 70% of pod RAM
  * Mesh dependencies: Formosa, TAP, JSWDD, Maui, DevAI, DSS, TWG
* **Service descriptor**:

  * Internal ingress
  * Health check at ``/healthcheck:8080``
  * Health check interval: 6s, timeout: 5s, thresholds 2/10
* **Python sidecar image** included alongside the JVM container

Notable findings
==================

* **No Kotlin** — pure deployment-time config. Atlas/Micros tooling reads these YAMLs at deploy time.
* **Mesh dependencies declared explicitly** — convo-ai talks to 7 other Atlassian services via service mesh; each must be enumerated here for network policy + service discovery.
* **Python sidecar** — see :ref:`mod-python-sidecar` (or top-level ``python-sidecar/`` directory) for what the Python process does (likely tokenization or other Python-only ML helpers).

