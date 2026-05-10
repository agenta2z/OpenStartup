.. _pai-cross-cutting:

==========================
Cross-cutting Chapters
==========================

Topics that touch multiple packages, organised in three groups.

The **business-and-strategy spine** (chapters 01, 10, 11, 12) is the
top-level "why and what" of the service: read these to understand the
OKR, the multi-year vision, every metric/SLO/alarm with source-of-truth
citations, and the optimisation playbook for moving each metric.

The **historical record** (chapter 02) is the development log: what
shipped in the last 6 months, who shipped it, and what conventions the
team follows when authoring PRs.

The **technical concepts** (chapters 03–09) are the deep-dives on each
cross-cutting platform concern (request context, feature flags,
observability, async tasks, AI Gateway, auth, deployment).

Business & strategy spine
==========================

.. toctree::
   :maxdepth: 1
   :caption: Read these as a set

   01-business-and-technical-goals
   10-vision-and-strategy
   11-metrics-catalog
   12-optimization-playbook

Historical record
==================

The narrative summary plus three machine-followable deep-dives —
read 02 first for the story, then 13/14/15 for the receipts.

.. toctree::
   :maxdepth: 1

   02-development-history
   13-full-history-catalog
   14-architectural-decisions
   15-velocity-and-debt

Technical concepts
===================

.. toctree::
   :maxdepth: 1

   03-request-context-and-mdc
   04-feature-flags
   05-observability-and-metrics
   06-async-tasks-and-sqs
   07-ai-gateway-and-stratus
   08-auth-and-tenant
   09-deployment-and-config
