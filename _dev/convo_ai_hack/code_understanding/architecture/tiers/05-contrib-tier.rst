.. _contrib-tier:

============================
Contrib Tier (4 modules)
============================

The **contrib tier** is the smallest and most opaque tier. Per the directory listing:

::

   contrib/client/client-api
   contrib/client/client-impl
   contrib/service/service-api
   contrib/service/service-impl

Total: 4 modules.

Inferred purpose :sup:`(inferred)`
===================================

The naming "contrib" (used in many open-source projects to mean "contributor-supplied" or "vendor-specific adapters") suggests this tier holds:

- **Vendor adapters** that don't belong in the core foundation/platform tiers (e.g. specific cloud-provider SDKs, third-party LLM provider SDKs not yet promoted to foundation)
- **Outside contributions** — patterns from other Atlassian teams that haven't been fully integrated into the core architecture

The api/impl split mirrors the rest of the codebase. Without reading the actual source, the precise contents are unknown.

Why so small?
==============

This tier may be **vestigial** or **early-stage**:

- **Vestigial:** content was here but has been migrated to foundation/platform; the empty shell remains
- **Early-stage:** content is being added but most contributors don't know about this tier
- **Reserved:** the tier exists as architectural placeholder for future plug-in patterns

The ``service/service-impl`` mirroring of ``platform/service/service-impl`` is suspicious — it may be a duplicate skeleton or an intentional separation for vendor-specific service implementations.

Recommendation
===============

If you're trying to understand this codebase:

- Skip this tier on first read.
- If you need to extend a behavior and "platform" feels wrong, check contrib first.
- Treat any code you find here as needing extra scrutiny — it's the least-trafficked tier.

What would change here
========================

- **A vendor-specific integration that doesn't fit foundation** (e.g. a regional cloud SDK adapter for one customer)
- **A Phase-1 prototype** before promotion to platform

In practice, most engineering work on this codebase will not touch contrib.

