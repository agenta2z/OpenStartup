# 05 — Mirror CI locally

To predict CI results, run what CI runs. This is the EXACT mapping from `bitbucket-pipelines.yml`.

---

## A. CI pipeline order

```
pre-warm (always — affected-modules detection)
  ↓
parallel: {
  lint × 4 shards,
  unit × 3 shards,
  startup-test × 1,
  integration × 4 shards × 2 flag modes = 8 jobs
}
  ↓
all green = mergeable
```

---

## B. Per-step recipe

| CI step | Local equivalent |
|---|---|
| `pre-warm` | `./bitbucket-pipelines-scripts/init-gradle-for-pipeline.sh && ./bitbucket-pipelines-scripts/resolve-affected-flag.sh --label affected_modules_test --property-name affected.modules.test` |
| `unit-tests-core` | `./gradlew -PunitTestShard=core test koverXmlReport koverVerify` |
| `unit-tests-rovo` | `./gradlew -PunitTestShard=rovo test koverXmlReport koverVerify` |
| `unit-tests-product` | `./gradlew -PunitTestShard=product test koverXmlReport koverVerify` |
| `lint-and-static-analysis-core` | `./gradlew lintCoreShard` |
| `lint-and-static-analysis-rovo` | `./gradlew lintRovoShard` |
| `lint-and-static-analysis-product` | `./gradlew lintProductShard` |
| `detekt-ast` | `./gradlew detekt` |
| `full-context-startup-test` | `./gradlew :convo-ai-test-integration:startupTest -Pnebulae.enabled=true` |
| `integration-tests-shard-N-flags-on` | `./bitbucket-pipelines-scripts/run-integration-tests-with-flag-modes.sh N --flags-on` |
| `integration-tests-shard-N-flags-off` | `./bitbucket-pipelines-scripts/run-integration-tests-with-flag-modes.sh N --flags-off` |

---

## C. Equivalent of "would this PR be green?"

Minimum local pre-PR check (5-15 min depending on cache):

```bash
./gradlew detekt &                                                           # ~30s
./gradlew test &                                                             # ~5-10 min
./gradlew :convo-ai-test-integration:startupTest -Pnebulae.enabled=true &    # ~3-5 min
wait
```

If all 3 pass: PR will likely be green. CI may still find:
- Flaky integration test (re-run usually fixes)
- Coverage gap (`koverVerify` failing)
- Lint shard you didn't run (run `./gradlew lintCoreShard lintRovoShard lintProductShard`)

---

## D. Maximum local pre-PR check (mirror full CI)

Total wall: ~30-60 min depending on machine.

```bash
# 1. Lint + detekt (parallel, ~3-5 min)
./gradlew lintCoreShard lintRovoShard lintProductShard detekt --parallel

# 2. Unit tests (sharded, ~10 min)
./gradlew -PunitTestShard=core test koverXmlReport koverVerify
./gradlew -PunitTestShard=rovo test koverXmlReport koverVerify
./gradlew -PunitTestShard=product test koverXmlReport koverVerify

# 3. Startup smoke (~3-5 min)
./gradlew :convo-ai-test-integration:startupTest -Pnebulae.enabled=true

# 4. Integration sharded (parallel via separate Gradle invocations, ~30 min)
for shard in 1 2 3 4; do
  ./gradlew :convo-ai-test-integration:integrationTestShard${shard}FlagsOn  -Pnebulae.enabled=true
  ./gradlew :convo-ai-test-integration:integrationTestShard${shard}FlagsOff -Pnebulae.enabled=true
done
```

Most engineers don't do this; they trust CI to find the long tail. **Step 3 (startup) is the highest-ROI local check** — catches ~80% of breakages in 3-5 min.
