# 02 — Unit tests

Run before integration tests. **No Docker, no Nebulae, no SLAuth required.** Typical wall time: 3-10 min depending on which modules are affected.

---

## A. The simplest run (all unit tests)

```bash
cd ~/MyProjects/atlassian_packages/conversational-ai-platform
./gradlew test
```

This runs the `test` Gradle task in **every** module. Default behavior excludes integration-tagged tests (see `convo-ai-test-integration/build.gradle.kts:167` `excludeTags("integration-test", "startup-test")`).

---

## B. Faster: per-shard

CI uses 3 shards by build property `unitTestShard=core|rovo|product`. Locally:

```bash
./gradlew -PunitTestShard=core test       # ~3-4 min — platform + infrastructure
./gradlew -PunitTestShard=rovo test       # ~3-5 min — Rovo agent modules
./gradlew -PunitTestShard=product test    # ~2-4 min — product feature modules
```

Pick the shard that matches the modules you've changed.

---

## C. Single module

```bash
./gradlew :modules:platform:service:service-impl:test     # one module
./gradlew :modules:rovo:agent:agent-core:test
```

To list valid module paths:
```bash
./gradlew projects | grep "^Project '" | head -30
```

---

## D. Single test class or method

```bash
# By class name
./gradlew :modules:platform:service:service-impl:test --tests 'SomeServiceTest'

# By method
./gradlew :modules:platform:service:service-impl:test --tests 'SomeServiceTest.shouldReturnFooWhenBar'

# Pattern
./gradlew test --tests '*PromptModeration*'
```

---

## E. With test reports + coverage

CI runs `koverXmlReport koverVerify` for coverage. To do the same locally:

```bash
./gradlew test koverXmlReport koverVerify
```

Reports land at `<module>/build/reports/tests/test/index.html` (HTML) and `<module>/build/reports/kover/report.xml` (Cobertura-compatible).

---

## F. Affected-modules optimization (CI-style)

CI uses `bitbucket-pipelines-scripts/resolve-affected-flag.sh` to detect which modules changed since master, then skips tests for unchanged modules. Locally you can mirror this:

```bash
./bitbucket-pipelines-scripts/resolve-affected-flag.sh \
    --label affected_modules_test \
    --property-name affected.modules.test
```

Then read `ci-cache/affected-modules-exit-code.txt`. Exit code 2 = no affected modules → skip tests.

---

## G. Common unit-test pitfalls

| Symptom | Likely cause | Fix |
|---|---|---|
| `Could not resolve all artifacts` | First-run, no Gradle cache | Wait — first resolution takes 5-10 min. Subsequent runs hit cache. |
| `KaptGenerateStubs failed` | Mismatched Kotlin/Kapt versions | `./gradlew clean` then retry |
| Hanging at "Executing test" | Gradle daemon stuck | `./gradlew --stop` then retry |
| `OutOfMemoryError: Metaspace` | JVM-fork heap too small | Set `org.gradle.jvmargs=-Xmx4g` in `gradle.properties` |
| Test passes locally but fails CI | Flaky test or env-dependent | Re-run twice locally; if green both times, file the flake. |

---

## H. Smoke verification (1 minute, proves toolchain works)

Pick a small module that compiles fast:

```bash
./gradlew :modules:platform:common:test --info | tail -20
# Expected: BUILD SUCCESSFUL in <2 min
```

If this fails, **stop**. Toolchain is broken. Fix it before attempting integration tests.
