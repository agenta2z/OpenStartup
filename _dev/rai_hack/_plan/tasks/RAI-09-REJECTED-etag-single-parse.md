# RAI-09 — REJECTED — ETag double parse fix

Status: rejected
Priority: was P2
UX-Class: A (Neutral)
Plan: PLAN-INTEGRATED-v4.md rank #9
PR: none (not opened)
Author: Tony Chen
Date opened: 2026-05-04
Date rejected: 2026-05-04

## Why rejected

The premise of "1–2 ms saved per cached ETag check by eliminating double body parse" is wrong by ~200×.

### Measured (with quick benchmark)

| Component | P50 cost |
|---|---|
| `check_etag()` end-to-end | **5.58 µs** |
| `generate_comparison_etag()` (sha256 + json.dumps) | 1.79 µs |
| `_generate_possible_etags()` (full 16-category loop) | 3.83 µs |

The total cost of the entire ETag check is ~5.6 µs, not 1–2 ms. There is no double JSON parse to fix:

1. Flask's `request.get_json()` is **internally memoized** — calling it twice from `check_etag()` and the controller's schema decorator hits Flask's cache, not a real parse.
2. `PromptHarmCategory.get_category_hash()` is `@cache`-decorated — only computed once per category for the lifetime of the process.
3. The JSON serialization (`json.dumps`) is the real cost in `generate_comparison_etag` (~1.8 µs), but it's already minimal.

Any reordering or single-pass approach would save < 1 µs, which is well within measurement noise on the production hot path.

## What this teaches us

This is exactly the kind of error the v4 plan's MEASURED-not-estimated rule is designed to catch. The original "1–2 ms" claim came from a static read that didn't account for Flask's `get_json()` memoization or the `@cache` decorators. **Always benchmark before optimizing.**

## Cross-references

- Plan corrections log already noted "ETag work is ~1-2ms total, mostly Pydantic + sha256". Even that 1-2ms total was 200× too high.
- This rejection corrects the v4 plan's RAI-09 entry.
