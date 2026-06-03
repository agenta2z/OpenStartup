.. _mod-convo-ai-docker-image:

==============================================
``service/convo-ai-docker-image``
==============================================

:Tier: service
:Path: ``modules/service/convo-ai-docker-image``
:Importance: **Tier 1 — bootstrap entry**

The JVM entry point and Docker packaging. Small in code lines but architecturally critical: this is where every other bean comes alive.

Key files :sup:`(verified)`
============================

* ``Application.kt`` — annotated ``@SpringBootApplication``, ``@EnableSqsQueues``, ``@EnableAquiQueues``; declares ``scanBasePackages`` (lines 12-23)
* ``ContextPropagationInitializer.kt`` — installs Reactor + OTel context propagation hooks
* ``ConvoAiApplicationStartupListener.kt`` — fail-fast guard: throws ``IllegalStateException`` if ``SqsMicrosLifecycleEventHandler`` bean is missing
* ``CoroutineMonitorStartupListener.kt`` — observes coroutine pool health

What ``main()`` does (lines 27-40, verified)
===============================================

1. Installs ``Hooks.onErrorDropped`` to log dropped Reactor errors with context
2. Runs ``SpringApplication`` with ``ContextPropagationInitializer`` added
3. The initializer ensures MDC + OTel + request attributes propagate across coroutines

The ``scanBasePackages`` enumeration
======================================

.. code-block:: kotlin

   scanBasePackages = [
       "io.atlassian.micros.convoai",
       "io.atlassian.micros.convoai.product.csm.config",
       "io.atlassian.micros.convoai.product.jsm.config",
       "io.atlassian.micros.convoai.product.jira.config",
       "io.atlassian.micros.convoai.product.loom.config",
   ]

Adding a new product means adding a new ``scanBasePackages`` entry here. Failure to do so means the product's Spring beans aren't registered.

Patterns specific to this module
==================================

1. **Small surface, big responsibility.** Few files, but every bean's lifecycle starts here.
2. **Detekt likely disabled** (per agent investigation — verify build.gradle.kts) to keep Docker builds fast.
3. **Fail-fast at startup.** Critical beans (SQS handler, etc.) are validated at ``ContextRefreshedEvent`` time; missing → ``IllegalStateException`` → service won't start.

What you would change here
============================

* **Add a new product config package** → add to ``scanBasePackages``
* **Adjust startup behavior** → modify ``main()`` or add a new ``ApplicationListener``
* **Add a new fail-fast guard** → new ``ApplicationListener`` that validates a critical bean

What you would NOT change here
================================

* Anything that isn't bootstrap-related — those go in their owning module

