# B-Cost+ — Cost Wins NOT in C/K/N Series

> Part of [BOOST Plan v1](../BOOST_PLAN_v1.md). 10 items.
> **Goal anchor:** −$30-73K/mo additive cost reduction over v7's C/K/N $168-290K baseline.
> **Pricing:** Sonnet ~$3/M input, $15/M output. Haiku ~$0.25/M input, $1.25/M output (≈10× cheaper).

---

## X7 — Model mis-selection audit (Sonnet → Haiku for routing/classification) 🔴 TOP-1 ITEM

**Files:** Routing/classification across `modules/product/chat-common/`, `modules/product/shared-features/`

**Problem:** Routing decisions are typically yes/no, single-label classification, or short summaries that **Haiku / GPT-3.5 handle at 80-90% accuracy** with 10× lower cost. The codebase appears to use Claude Sonnet / GPT-4 across the board.

**Estimated saving:** **−$16.8-43.5K/mo** (single largest unclaimed lever)
**Effort:** L (3-4 weeks; A/B testing + accuracy gates + rollback plan)
**Risk:** Med (routing accuracy regressions)
**Approach:**
1. Inventory all classifier / router callsites (grep for `LlmCompletion`, model names)
2. Build a labeled router/classifier dataset (~1,000 examples)
3. Run paired A/B: Sonnet vs Haiku on same dataset; measure accuracy delta
4. If accuracy delta ≤5pp, ship Haiku at 5% → 25% → 50% → 100% (each tier requires +7d M10 attribution validation)
5. Gate: auto-rollback if accuracy delta jumps >5pp post-deploy

**Acceptance:** ≥3 callsites migrated; accuracy ≤5pp regression; M10 per-feature cost attribution shows ≥−$16.8K/mo over 14 days.

**FY26 goal:** Cost.

---

## X2 — Tool-schema cross-turn dedup (memo within conversation) 🔴 TOP-3 ITEM

**Files:** `modules/platform/service/service-impl/src/main/kotlin/io/atlassian/micros/convoai/platform/service/llm/toolconverter/`, `modules/platform/base/base-api/.../tool/ToolDefinition.kt`

**Problem:** Tool converters (Claude, ChatCompletion, Gemini, RawPredict, FunctionTool) each independently serialize JSON schemas for every message in multi-turn conversations. **No cross-turn schema caching** — Gemini & ChatCompletion converters repeat ~5-15KB per turn. Multi-turn conversations of 5-10 turns waste 25-150KB of input tokens.

**Estimated saving:** **−$4-6K/mo**
**Effort:** M (1-2 weeks)
**Risk:** Low-Med (schema-evolution handling)
**Approach:**
1. Add `ToolSchemaCache` keyed by `(toolDefinitionHash, modelFamily)` — TTL 1 hour
2. On serialization, check cache first; cache miss = serialize + store
3. Schema-evolution: hash changes invalidate cache automatically
4. Add `convoai.tool_schema_cache.{hit,miss,size}` metrics

**Acceptance:** Cache hit-rate ≥90% within session; per-conversation tool-schema bytes counter (M10) shows -8-12% input tokens.

**Compounds with:** L1 tool-schema cache (my open PR #29120) — L1 is per-execute; X2 is cross-turn within conversation.

---

## X4 — Agent system-prompt factorization

**Files:** `modules/product/agent-framework/src/main/kotlin/.../prompts/`

**Problem:** Agent system prompts built via string concatenation with **repeated boilerplate** (guidelines, output format, safety disclaimers, fallback instructions). No shared prefix dedup across agent variants (Rovo vs CSM vs JSM).

**Estimated saving:** **−$2.5-5K/mo**
**Effort:** M (1-2 weeks)
**Risk:** Med (prompt quality A/B required)
**Approach:**
1. Extract ~1-2KB common guidelines to shared prompt fragment (`SHARED_AGENT_GUIDELINES.txt`)
2. Use Anthropic prompt-cache (compounds with K1 from v7) on universal safety/format instructions
3. Reduce few-shot examples from 3 → 1-2 (smaller models work fine; verify with M1 LLM judge)
4. Per-agent A/B: paired prompts before/after; measure quality delta

**Acceptance:** M1 LLM judge shows ≤5% quality delta; M10 cost attribution shows ≥−$2.5K/mo.

**Compounds with:** K1 Anthropic prompt-cache audit (v7) — both leverage prompt-cache infrastructure.

---

## X5 — Knowledge / search result cache (5-min TTL on deterministic queries) 🔴 TOP-11 ITEM

**Files:** `modules/platform/knowledge/`, `modules/product/shared-features/`

**Problem:** TWG / CQL queries within a session not cached at result level. Bluebird handles embeddings only — structured search results (e.g., "show issues with label:blocker") are re-fetched on every turn even when the user hasn't changed context.

**Estimated saving:** **−$2-4K/mo** + **−100-200ms p50** on repeat queries
**Effort:** M (1-2 weeks)
**Risk:** Low (deterministic queries only)
**Approach:**
1. Define `KnowledgeQueryCacheKey = (queryString, integration, tenantId, userId)`
2. 5-min TTL on cache (queries within session almost always benefit)
3. **Skip cache if user explicitly requests fresh data** (e.g., "refresh", "what's new")
4. Add `convoai.knowledge_cache.{hit,miss,bytes_saved}` metrics

**Acceptance:** Cache hit-rate ≥40%; p50 latency on repeat queries -100ms.

---

## X3 — Within-turn search-tool dedup

**Files:** `modules/product/confluence/`, `modules/product/jira/` — search tool invocations

**Problem:** Multi-step agent reasoning often re-queries the same issue/page within a turn (LLM decides to call search again for validation). No within-turn dedup.

**Estimated saving:** **−$1.5-3.5K/mo**
**Effort:** S (3-5 days)
**Risk:** Low (scoped to integration results, deterministic)
**Approach:**
1. Within a single LLM-decision turn, build a request-scoped `Map<(query, integration), Future<Result>>`
2. On duplicate request, return existing future (single-flight)
3. Add `convoai.tool_dedup.coalesced_count{tool}` counter

**Acceptance:** Coalesced-count baselined; M10 attribution shows ≥−$1.5K/mo.

---

## X6 — Conversation-context metadata pruning

**Files:** `modules/platform/conversation/`

**Problem:** Tool-call metadata (execution time, token counts, error traces) accumulated in conversation context **for debugging/logging** but sent back to LLM in subsequent turns unnecessarily.

**Estimated saving:** **−$1-2K/mo**
**Effort:** S (3-5 days)
**Risk:** Low (observability metadata persisted separately)
**Approach:**
1. Define `ConversationContext.toLLMRepr()` that strips debug metadata
2. Apply on the boundary between conversation-store and LLM input assembly
3. Keep metadata for 3 most recent turns (debugging recent issues)

**Acceptance:** Per-turn input-token average ≥−2% in M10 attribution.

---

## X8 — Per-tool retry-error memo (cache failed tool result)

**File:** `modules/platform/base/base-impl/src/main/kotlin/.../tool/executor/LlmInvocableExecutorImpl.kt`

**Problem:** Tool failures trigger retry logic at the LLM-orchestration level → full context re-sent with identical tools/history per retry. **No per-tool retry caching** (caching a failed API call result to avoid re-asking the LLM).

**Estimated saving:** **−$1-2.5K/mo**
**Effort:** M (1 week)
**Risk:** Low (error paths only)
**Approach:**
1. Define `ToolErrorMemo = (toolName, argsHash) → ErrorResult`
2. 5-min TTL on memo
3. On retry, return cached error instead of re-invoking
4. Compose with R-1B (tool-error feedback to LLM) so the LLM sees the same error and self-corrects

**Acceptance:** M10 retry-saved-tokens counter ≥−$1K/mo.

**Compounds with:** R-1B tool-error feedback (v7 + my open PR #29119).

---

## X1 — Streaming tail-trim instrumentation

**Files:** `modules/platform/service/service-impl/.../AIGatewayClientServiceImpl.kt`

**Problem:** LLM responses streamed to clients that may cancel mid-stream (user closes chat, switches agents). **Streamed tokens from cancellation point still billed.**

**Estimated saving:** **−$0.5-1.25K/mo** + observability foundation
**Effort:** S (3-5 days)
**Risk:** Low
**Approach:**
1. Add `convoai.streaming.cancelled_tokens_wasted` counter (per cancellation event)
2. (Phase 2) On cancellation, send `cancel` to AI Gateway if API supports it
3. (Phase 3) Cache partial response for retry-resume scenarios

**Acceptance:** Counter baselined; Phase 2/3 only if Phase 1 reveals significant waste.

**Compounds with:** R-6E structured cancellation (v7) — both eliminate orphan-token waste.

---

## X9 — AIFC creation-flow ADF block caching (15-iteration loop)

**Files:** `modules/product/aifeature/`

**Problem:** Open issues mention "15-iteration ADF Editor loop" for page creation. Each iteration sends full page context + tool results + reasoning. Likely re-builds same ADF blocks repeatedly.

**Estimated saving:** **−$1.5-4K/mo** for AIFC flows
**Effort:** L (3-4 weeks; AIFC editor state machine reverse-engineering)
**Risk:** Med (AIFC quality regressions)
**Approach:**
1. Reverse-engineer the 15-iteration loop convergence pattern (Confluence ADF Editor)
2. Cache partial ADF blocks across iterations (block-level diff)
3. Only re-validate changed sections
4. Per-iteration token budget metric

**Acceptance:** AIFC iterations average 15 → ≤8; per-AIFC cost ≥−$1.5K/mo.

---

## X10 — Tool-schema log sampling (hash + sample 1%)

**File:** `AIGatewayClientService` debug logging (verified by `AIGatewayClientServiceLogToolSchemasTest.kt`)

**Problem:** Tool schemas logged to structured logging on every LLM request → bloats CloudWatch/Splunk (charged per GB).

**Estimated saving:** **−$0.5-1.5K/mo CloudWatch cost**
**Effort:** S (1-2 days)
**Risk:** Low (observability degradation only)
**Approach:**
1. Log schema hash instead of full JSON (default)
2. Sample full-schema logs (1% of requests) for debugging
3. Move full schemas to separate debug bucket with shorter retention

**Acceptance:** CloudWatch ingest from this log line ≥−80%; debug capability preserved.

---

## Summary Table

| ID | Title | $/mo Saving | Effort | Risk | Sequence |
|----|-------|--------------|--------|------|----------|
| **X7** | Model mis-selection (Sonnet → Haiku) | **$16.8-43.5K** | L | Med | Wk 10-12 (after measurement) |
| **X2** | Tool-schema cross-turn dedup | $4-6K | M | Low-Med | Wk 2-3 |
| **X4** | Agent system-prompt factorization | $2.5-5K | M | Med | Wk 6-7 |
| **X5** | Knowledge/search result cache | $2-4K | M | Low | Wk 6-7 |
| **X3** | Within-turn search-tool dedup | $1.5-3.5K | S | Low | Wk 2 |
| **X9** | AIFC ADF block caching | $1.5-4K | L | Med | Wk 10-12 |
| **X8** | Per-tool retry-error memo | $1-2.5K | M | Low | Wk 6-7 |
| **X6** | Context metadata pruning | $1-2K | S | Low | Wk 2 |
| **X1** | Streaming tail-trim instrumentation | $0.5-1.25K | S | Low | Wk 1 |
| **X10** | Tool-schema log sampling | $0.5-1.5K | S | Low | Wk 1 |
| **TOTAL** | | **$30-73K/mo** | | | 12-week plan |
