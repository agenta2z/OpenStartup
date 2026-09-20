.. _mod-platform-test-utils:

==============================================
``platform/convo-ai-test-utils``
==============================================

:Tier: platform
:Path: ``modules/platform/convo-ai-test-utils``
:Size: ~4,724 source lines :sup:`(verified)`
:Importance: **Tier 2 — shared test fixtures**

Test fixtures shared across the codebase — feature-gate context providers, mock LLM services, fake stubs.

Verified files
================

* ``testutils/testframework/featuregate/FeatureGateContextProvider.kt:34``
* ``testutils/testframework/mocks/MockLLMServiceRetry.kt``

Dependencies :sup:`(verified)`
================================

* ``foundation/utilities-api``
* Multiple platform APIs (base, client, service, conversation, knowledge)
* MSB Base, ARI, Sagemaker, Mimeograph Reactive
* Apollo GraphQL, Tecton, Pebble
* TCS, MockitoKotlin (NOT MockK — exemption from foundation rule)

Patterns
==========

1. **Cross-tier deps allowed.** This module exists exactly because tests need to compose across tiers.
2. **MockitoKotlin used here** — the platform MockK rule doesn't apply (this is a test-fixture module).
3. **Wide platform API consumption.** Mirrors what production code touches.

What you would change here
============================

* Add a new shared test fixture → here
* Add a new mock for a platform API → ``testutils/testframework/mocks/``

