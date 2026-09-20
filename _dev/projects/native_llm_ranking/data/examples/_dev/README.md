# examples/_dev — LLM-native recommendation prompt

Prototype of the recommendation/ranking prompt for LLM-native recs (assemble a user's
profile + historical events → predict future events), plus **what real user data we can
get** and the queries to get it.

## Contents

- **`recommendation_prompt.md`** — the prompt, written the way Meta's real LLM rankers
  write it: **natural-language markdown, not JSON**. It has three parts:
  1. **The prompt** (SYSTEM + USER) in pure markdown — user profile as `#####` sections and
     history as prose event lines (`"N days ago, saved a Reel by @x about <topics> — …"`),
     modeled on Ember's real `complete_user_profile` + Biography's real event serialization.
     User-specific values are **`‹slots›`**.
  2. **Real data-collection queries** (Presto/Daiquery) that populate every slot with **real
     data** — real tables/columns/join-keys, retention-aware.
  3. **What data we can get** (recap table: field → source → how far back) + honesty note.

## How to use

Run the Part-2 queries (authorized access) to fill the `‹slots›` in Part 1, then feed the
SYSTEM + USER messages to the model. Output is pipe-delimited (`ID | P_ENGAGE | ACTION |
TIER | reason`), not JSON.

## Notes on integrity

- **No synthesized data.** Values are slots filled from the real queries; no fabricated
  names/numbers are presented as real (the earlier synthetic examples were removed).
- **No raw JSON in the prompt** — real production prompts serialize the user in markdown/NL;
  this matches them (JSON only appears as candidate metadata in Ember's pointwise path,
  which the NL design here intentionally replaces).
- **Real-user PII is not stored here.** Agent-driven bulk collection of real user data into
  a repo file is blocked by a privacy control; you run the queries with proper controls.
- Structure, tables, retention, and id-spaces are **VERIFIED** against production code + the
  Hive metastore; see `../../docs/` (`data_sources_catalog.rst`, `event_taxonomy.rst`,
  `identifiers_and_joins.rst`) and the Provenance table in `recommendation_prompt.md`.
