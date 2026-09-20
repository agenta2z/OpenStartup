.. _mod-atlassianstudio-api:

==============================================
``product/atlassianstudio/atlassianstudio-api``
==============================================

:Tier: product
:Path: ``modules/product/atlassianstudio/atlassianstudio-api``
:Size: ~105 source lines :sup:`(verified)`

Minimal API for Atlassian Studio: access service + agent-chat metrics helpers.

Top files :sup:`(verified)`
============================

* ``AgentChatMetricsHelper.kt`` — 44 lines
* ``AgentChatSuccessMetricsPublisher.kt`` — 41 lines
* ``AtlassianStudioAccessService.kt`` — 20 lines

Notable findings
==================

* Tiny API surface — most logic is in the impl (4,734 LoC).
* Metrics-first design — two metrics classes vs one service.

