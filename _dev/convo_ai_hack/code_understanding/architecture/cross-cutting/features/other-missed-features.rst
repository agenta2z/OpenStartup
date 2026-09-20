==============================================================
Other User-Facing Features (Hiring Manager, Loom, AtlassianStudio Access)
==============================================================

This page consolidates 3 smaller user-facing features identified in
the Wave-2 inventory gap analysis. Each is documented as a section,
not a full deep-dive (per the lower-priority Wave-2 scoring).

Hiring Manager Tool
=====================

**One-sentence**: A Rovo tool that integrates with HR systems to
search for candidates, schedule interviews, or fetch hiring pipeline
status — surfaced as a chat tool.

**Where**:

* ``modules/product/rovo/rovo-impl/.../hiringmanager/HiringManagerTool.kt`` (~150-300 LoC)

**User-visible**: Yes — chat tool invokable from Rovo Chat.

**Status**: Active production. Uses HR-integration endpoints (specific
HR system not enumerated in code search; likely Workday or internal
Atlassian HR).

**Score** (Wave-2): 15

**Open questions**:

* Which HR system(s) are integrated?
* Auth model — service-account or per-user delegation?
* Rate limits / quotas?

Loom Integration
==================

**One-sentence**: Video transcript analysis — convoai can read Loom
video transcripts and answer questions about video content.

**Where**:

* ``modules/loom/`` (full module — ~100-200 LoC main code)

**User-visible**: Yes — when users share a Loom URL, convoai can
fetch transcript and reference it in conversation.

**Status**: Active production. Single-purpose module.

**Score** (Wave-2): 12

**Integration topology**:

* Loom REST API (transcript fetching)
* Auth via ASAP (signed inter-Atlassian-service request)

**Open questions**:

* Are video segment timestamps preserved in answers?
* Is video metadata (title, author, duration) extracted?
* Length limits for transcript ingestion?

AtlassianStudio Access Control
================================

**One-sentence**: Multi-workspace access management for AtlassianStudio
— controls which workspaces a user can see in cross-product UI.

**Where**:

* ``modules/product/atlassianstudio/atlassianstudio-impl/.../AtlassianStudioAccessServiceImpl.kt`` (~100-150 LoC)
* ``modules/product/atlassianstudio/atlassianstudio-impl/.../graphql/AtlassianStudioContextQueryController.kt`` (GraphQL)

**User-visible**: Yes — controls workspace switcher visibility in
AtlassianStudio UI.

**Status**: Active production. Lightweight access-check service.

**Score** (Wave-2): 10

**Open questions**:

* What's the authoritative source of "which workspaces user has access to"? (Likely Atlassian Identity / IAM)
* Any caching to reduce per-request lookups?
* Multi-org user support?

Combined feature inventory update
====================================

After this addendum, the documented features list grows to:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Already documented (deep-dive)
     - Now added (this doc)
   * - Rovo Insights, Marathon, MCP, Deep Research,
       Rovo Plugin System, AgentStudio, SAIN, AIFC,
       Agent Framework, Chat Streaming, Lumina,
       Knowledge & Knowledge Gap, CSM Platform,
       JSM Platform, AIFEATURE, Memory, CSM Voice,
       Knowledge Gap Workflow, **JSM Composer/Handoff**,
       **Confluence ADF Editor**, **AgentStudio Reports**
     - **Hiring Manager Tool**, **Loom Integration**,
       **AtlassianStudio Access Control**

Cross-references
==================

* :doc:`00-feature-inventory-wave-2` — original gap analysis identifying these
* :doc:`agentstudio` — AgentStudio module
* :doc:`../../tiers/02-product-tier` — product-tier overview

