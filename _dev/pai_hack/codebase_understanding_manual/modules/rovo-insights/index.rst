.. _mod-rovo-insights:

=========================
Rovo Insights
=========================

.. toctree::
   :maxdepth: 1

   rovo-insights-generation
   rovo-insights-api

Overview
========

The Rovo Insights module implements a full asynchronous generation pipeline
for producing AI-driven insight cards. It spans three layers:

1. **REST API** — accepts generation triggers and serves generated insights.
2. **Async Task Pipeline** — submits work to SQS via the async-task framework.
3. **SQS Consumer** — drains the queue on ``LongRun`` worker nodes and
   dispatches to the generation handler.

:Package: ``io.atlassian.micros.proactiveai.feature.rovoinsights``
:Queue: ``rovo_insights_generation_queue`` (LongRun worker group)

System Types
============

The ``system/`` sub-package defines the domain vocabulary shared between
the generation pipeline and the front-end rendering layer.

``InsightType`` enum
--------------------

Six insight categories, each with a UI icon (``Glyph``), colour (``Color``),
and display title:

.. code-block:: kotlin

   FOLLOW_UP_INSIGHTS    → icon=TARGET,       color=YELLOW,  "Waiting on you"
   EMERGING_WITH_YOUR_TEAM → icon=CHART_TREND_UP, color=MAGENTA, "What your team's into"
   COMPANY_INSIGHTS      → icon=MEGAPHONE,    color=BLUE,    "Across the company"
   YOUR_TRENDING_WORK    → icon=EYE_OPEN,     color=TEAL,    "Your work is travelling"
   RECOGNITION_INSIGHTS  → icon=GOAL,         color=MAGENTA, "Worth celebrating"
   MEETING_INSIGHTS      → icon=CALENDAR,     color=ORANGE,  "Important meetings"

``Color`` enum
   12 colour keys (``gray``, ``blue``, ``teal``, ``green``, ``lime``,
   ``yellow``, ``orange``, ``magenta``, ``purple``, ``red``, ``cyan``,
   ``custom``) matching Atlassian Design System icon-tile appearance tokens.

``Glyph`` enum
   Icon keys (``TARGET``, ``CHART_TREND_UP``, ``MEGAPHONE``, ``EYE_OPEN``,
   ``GOAL``, ``CALENDAR``, plus others) from the Atlassian icon set.

``RovoInsightsPromptConfig``
   Per-insight-type prompt configuration: ``version`` (default ``"v1"``),
   ``strategy`` (``EVALUATE`` or ``SKIP``), ``maxAttempts`` (default 3),
   and optional ``override`` prompt text.

``Config.kt``
   Defines ``DEFAULT_ROVO_INSIGHTS_PROMPT_CONFIG`` — a map of
   ``InsightType → RovoInsightsPromptConfig`` with all six insight types
   configured to ``EVALUATE`` strategy, version ``"v1"``, max 3 attempts.
