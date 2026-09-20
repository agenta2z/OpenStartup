.. _mod-gasv3-analytics:

====================
GASv3 Analytics
====================

:Files: ``src/gasv3_analytics/rai_analytics_client.py`` (178 LoC), ``src/gasv3_analytics/events/``
:Importance: **P2 — event tracking (async, non-blocking)**

Overview
=========

RAI fires operational analytics events for every moderation outcome via
Atlassian's GASv3 (Global Analytics Service v3) event pipeline. Events are
sent asynchronously (gevent Pool 10) and never block the HTTP response.

Client (``rai_analytics_client.py``)
======================================

``RAIAnalyticsClient``:

* Wraps Atlassian ``analytics_client.Client``
* **Env-to-analytics-env mapping**:

  .. list-table::
     :header-rows: 1
     :widths: 30 70

     * - EnvType
       - GASv3 env string
     * - LOCAL
       - ``"dev"`` (0 retries)
     * - DEV
       - ``"dev"`` (2 retries)
     * - STAGING
       - ``"staging"`` (2 retries)
     * - PROD
       - ``"prod"`` (1 retry)

* HTTP timeout: 2s
* Async dispatch: ``gevent.Pool(10).spawn(send_event)``
* Kill switch: ``feature_service.is_analytics_disabled()`` → all events dropped silently

``BaseEventAttributes`` dataclass:

* ``cloud_id: str``
* ``user_id: Optional[str]``
* ``anonymous_user_id: Optional[str]``
* XOR validation: exactly one of user_id or anonymous_user_id must be set

Send methods:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Method
     - Event type
   * - ``send_content_evaluated_event(event, attrs)``
     - Prompt moderation outcome
   * - ``send_output_evaluated_event(event, attrs)``
     - Output moderation chunk outcome
   * - ``send_agent_evaluated_event(event, attrs)``
     - Agent moderation outcome
   * - ``send_image_evaluated_event(event, attrs)``
     - Image moderation outcome

All methods create ``OperationalEvent(action=…, action_subject=…, product="responsibleAI", …)``
before dispatching.

Event schemas
==============

All events share common fields: ``cloud_id``, ``user_id``/``anonymous_user_id``,
``evaluation_version``, ``detected_harm_category``, ``outcome``
(``ContentEvaluatedEventOutcome.ALLOWED``/``DISALLOWED``).

**ContentEvaluatedEvent** (prompt moderation):

* ``use_case_id: str``
* ``violation_score: float``
* ``model_version: str``

**OutputEvaluatedEvent** (output moderation):

* ``stream_id: str``
* ``chunk_index: int``
* ``violation_score: float``

**AgentEvaluatedEvent** (agent moderation):

* ``use_case_id: str``
* ``slauth_principal: str``
* ``violation_score: float``
* ``agent_name: str``

**ImageEvaluatedEvent** (image moderation):

* ``use_case_id: str``
* ``image_size_bucket: str``
* ``v0_outcome: str``
* ``v1_outcome: str``
* ``anti_abuse_classification: str``

Key design: GASv3 events are the **only** place violation_score is permanently
stored (not in HTTP response body). Used for drift detection and model evaluation.
