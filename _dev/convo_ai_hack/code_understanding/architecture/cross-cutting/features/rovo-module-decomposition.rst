=================================================
Rovo Module Decomposition (in-flight refactoring)
=================================================

**Status**: 🟡 **In-flight** (multi-stream execution, ~30% complete as of 2026-05)

**Source**: ``.projects/rovo-module-decomposition/`` in the convoai
codebase — a comprehensive design + execution workspace with 4 reference
documents and 5 workstream specs.

**Discovered**: 2026-05-03 during open-questions investigation
(see :doc:`../../business/05-open-questions-resolved` §11.3).

==================================================
1. What this initiative IS
==================================================

**One-sentence**: A disciplined, 5-stream, API-first refactoring of
the 1,941-file ``rovo-impl`` monolith into 6 domain/framework modules
+ focused APIs, executed via 16 sequenced PRs with strict zero-behavior-
change move discipline.

**Why it exists**:

* ``rovo-impl`` is currently the largest single module in convoai
  (~1,941 main + 1,250 test Kotlin files = **3,191 files, ~hundreds of
  KLoC**)
* Lint/compile feedback loop dominated by rovo work
* Bidirectional cross-domain coupling (workflow↔agent, plugin↔agent,
  action↔agent) prevents independent ownership
* Single monolithic recompile for any change

**End state**:

* Domain modules (``minions-impl``, ``orchestrators-impl``, etc.) own
  product capabilities
* Framework modules (``workflow-impl``, ``plugin-impl``, ``action-impl``,
  ``mcp-impl``, ``agent-framework-impl``) own reusable execution
  infrastructure
* Focused APIs (``agent-api``, ``workflow-api``, ``plugin-api``, etc.)
  define contracts; impls depend on APIs, NOT on each other's ``-impl``
  modules
* One-way dependency flow; composition root moved to application/service
  layer

==================================================
2. The 6 target modules
==================================================

.. list-table::
   :header-rows: 1
   :widths: 22 25 12 12 14 15

   * - Module
     - Current location
     - Main files
     - Test files
     - Difficulty
     - Owner stream
   * - **workflow-impl**
     - ``product/rovo/workflow/``
     - 36
     - 31
     - Medium
     - B
   * - **plugin-impl**
     - ``product/rovo/plugin/``
     - 192
     - 79
     - High
     - B
   * - **action-impl**
     - ``product/rovo/action/`` + ``skilltool/`` + ``tool/``
     - 266
     - 210
     - High
     - C
   * - **mcp-impl**
     - ``product/rovo/mcp/``
     - 159
     - 69
     - Medium
     - C
   * - **minions-impl**
     - ``agent/minions/`` (subset)
     - TBD (part of 560-file ``agent/`` namespace)
     - TBD
     - High
     - E
   * - **orchestrators-impl**
     - TBD (likely ``product/rovo/`` area)
     - TBD
     - TBD
     - TBD
     - E

**Total scope**: ~2,041 files moving across ~16 sequenced PRs.

==================================================
3. Methodology: API seams BEFORE splitting
==================================================

**Pattern** (every move follows this sequence):

#. **Identify** package with fixable boundary
#. **Extract interfaces** to ``rovo-api`` — bidirectional edges become
   one-way; reverse callers depend on APIs, not impl modules
#. **Move files atomically** — source + test + resources, **zero
   behavior change**, ``git diff --stat`` shows 100% renames
#. **Register module** — add to ``settings.gradle.kts``, include in
   docker-image classpath deps
#. **Verify gates**: compile all affected modules, test moved + remaining
   modules, ``ApplicationScanCoverageTest`` (Spring bean discovery), full
   integration tests, docker image classpath coverage

**Key invariants**:

* **impl-to-impl rule** — no ``-impl`` may depend on another ``-impl``
  module's code; reverse deps go through APIs
* **SPI rule** — only the matching ``-impl`` may depend on its ``-spi``
* **Lint shard invariant** — modules named ``convo-ai-product-rovo-*``
  stay in "rovo" shard; only moves to ``convo-ai-product-{other}-*``
  (e.g., ``jsm-impl``) actually reduce rovo CI load

==================================================
4. Verification gates (every PR)
==================================================

Each decomposition PR must pass:

#. ``git diff --stat`` shows **100% renames** (no content changes)
#. Compilation: ``gradle :<src>:compileKotlin :<dest>:compileKotlin :convo-ai-docker-image:compileKotlin``
#. Tests: ``gradle :<dest>:test`` + ``gradle :<src>:test`` (remaining callers)
#. ``ApplicationScanCoverageTest`` — all Spring beans discovered
#. ``gradle -Dorg.gradle.configuration-cache=false integrationTest`` — full suite
#. Docker image builds and **contains all moved classes on classpath**
#. **No new impl-to-impl dependencies** (enforced in build.gradle.kts)

==================================================
5. Stream execution status (~30% complete)
==================================================

.. list-table::
   :header-rows: 1
   :widths: 18 38 15 12 17

   * - Stream
     - Status
     - PR count
     - Files
     - Dependencies
   * - **A** — Clean extractions
     - 50% (A1 landed: ~82 files to ``rovo-extras-impl``; A2 blocked by SPI rule; A3 not started)
     - 3
     - ~82
     - None
   * - **B** — Workflow + Plugin
     - 40% (B1 complete ✅; B2 prep done; module creation pending)
     - 3
     - ~230
     - None
   * - **C** — Action + MCP
     - 33% (C1 complete ✅: interfaces extracted; C2/C3 await B1)
     - 3
     - ~425
     - B1 complete
   * - **D** — Domain modules
     - 10% (interface prep landed)
     - 4
     - ~754
     - C complete
   * - **E** — Endgame (agent + minions + chat + rest + orchestrators)
     - 5% (E1 module created; first ``agent-framework-impl`` slices landed)
     - 3
     - ~550
     - B+C+D complete

**Critical path**: A and B can run in parallel (no deps); C waits for
B1; D waits for C; E waits for D.

==================================================
6. Already-extracted helper modules
==================================================

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Module
     - Purpose
   * - ``rovo-extras-impl``
     - Temporary staging buffer for pre-split code (guardrailed: no new prod logic, no impl-to-impl deps; redistributed once real destinations exist)
   * - ``rovo-leaf-agents-impl``
     - Existing extraction — leaf agent implementations
   * - ``agent-framework-impl``
     - E1 framework module — first meaningful slices landed (``agent/usercentricagent``, cleaned ``agent/permission``, minions/stratus resources)
   * - ``confluence-impl``
     - Domain module already separated

==================================================
7. Largest packages still in rovo-impl
==================================================

.. list-table::
   :header-rows: 1
   :widths: 35 25 40

   * - Package
     - Main files
     - Move target
   * - ``agent/``
     - **560+389**
     - E (endgame)
   * - ``product/rovo/action/``
     - **239+188**
     - C2
   * - ``product/rovo/plugin/``
     - **191+79**
     - B3
   * - ``product/rovo/mcp/``
     - **159+69**
     - C3
   * - ``product/rovo/chat/``
     - **51+47**
     - E
   * - ``product/rovo/rest/``
     - **49+23**
     - E
   * - ``product/rovo/workflow/``
     - **36+31**
     - B2

==================================================
8. Risks & open questions
==================================================

**Technical risks**:

* **Bidirectional framework coupling** — if agent↔workflow, agent↔plugin,
  agent↔action cannot be fully made one-way, some framework modules may
  need to merge
* **agent/ namespace still huge** (560 main files) — core
  ``product/rovo/agent`` extraction is E target; may require internal
  decomposition during E1
* **Test coupling** — tests construct concrete classes from other domains;
  module splits may require test refactoring to mock interfaces
* **PR sizing** — D1 (283 files), C2 (266 files), E phases are large;
  review burden may require splits

**Open questions** (not in ``.projects/`` docs):

* **Timeline** — no ETA for completion; unclear if 16 PRs target a
  quarter or a year
* **Priority order** — if velocity is limited, B → C → D → E gives
  fastest CI gains; A can be deferred
* **Owner assignment** — no team names in docs (inferred: workflow team
  → B2, action team → C2, etc.)
* **Orchestrators-impl scope** — the 6th target module is mentioned
  but not defined; where does it live? what does it contain?
* **Minions decomposition detail** — marked as E target but
  ``agent/minions/`` is part of larger ``agent/`` namespace; unclear if
  minions moves atomically or splits further
* **Test strategy post-split** — no doc on mocking patterns, fixture
  sharing, or integration test topology
* **Spring wiring migration plan** — composition root moves "last" but
  no detail on how ``@Bean``, ``@ComponentScan``, or config classes
  migrate

==================================================
9. Why this matters for everyone
==================================================

**For convoai engineers**:

* **Faster CI feedback**: only changed module recompiles
* **Clearer ownership**: changes go to the team owning that module
* **Better testability**: tests can mock framework boundaries

**For convoai SREs**:

* **No runtime change**: this is purely a compile/build refactoring;
  zero behavior change is the explicit invariant
* **Smaller deploy artifacts**: per-module changes won't trigger full
  rebuilds
* **Better observability**: future per-module metrics become possible

**For convoai PMs**:

* **Faster feature velocity** once complete: parallel team work
  unblocked
* **No user-visible change**: refactoring is invisible to end users
* **Risk during in-flight**: large PRs may temporarily slow review
  velocity (mitigated by zero-behavior-change discipline)

==================================================
10. Cross-references
==================================================

* :doc:`../../business/05-open-questions-resolved` §11.3 — discovery context
* :doc:`../patterns` — relates to "duplicated module structure" pattern
* :doc:`../../tiers/index` — current 5-tier model that this refactoring preserves
* :doc:`marathon-orchestrator` — Marathon will become part of ``orchestrators-impl`` (E)
* :doc:`mcp-system` — MCP code paths will move to ``mcp-impl`` (C3)
* Source docs: ``.projects/rovo-module-decomposition/workstreams.md``, ``reference/architecture-vision.md``, ``reference/README.md``
