# 06 — Load tests (perfhammer / Locust)

> **Why this exists.** The original SOP set (`02-unit-tests.md`, `03-integration-tests.md`) covered correctness; it did not cover **throughput / saturation / capacity** — the specific concerns that drive the v7 plan's T-series workstream and the M7 measurement gate. This file closes that gap.
>
> **What you'll learn.** How to run the perfhammer Locust load tests against (a) the locally-running integration sandbox, (b) staging, (c) prod (with explicit guardrails). Plus prerequisites, payload structure, RPS ramp config, and how the results feed M7.

---

## A. Where it lives + what it is

- **Path:** `operations/perfhammer/`
- **Stack:** [Locust 2.20.1](https://docs.locust.io/) + [Atlassian perfkit 3.0.26](https://developer.atlassian.com/platform/perfhammer/) + gevent 25.9.1
- **Python:** **3.12** (per `.python-version`)
- **Test scripts (verified):**
  - `tests/rovo-chat-stream-api.py` — POST `/rovo/v1/me/chat/stream` (the canonical "send-message" SLO endpoint)
  - `tests/aifc-page-create-stream-api.py` — POST AIFC page-create stream (the AIFC factual-consistency gate path)
- **Reusable client:** `client/rest_client.py` — `RestClient(url, tenant_id)` sets `ATL-CloudId` header and validates HTTP 200 + JSON-line body

| File · line | What it does |
|---|---|
| `operations/perfhammer/README.md:7-12` | Local install + run instructions |
| `operations/perfhammer/.python-version` | Python 3.12 pin |
| `operations/perfhammer/requirements.txt` | locust 2.20.1, perfkit 3.0.26, gevent 25.9.1 |
| `operations/perfhammer/client/rest_client.py:3-25` | Constructor takes `url` + `tenant_id`; sets `ATL-CloudId`; status≠200 ⇒ `failure` |
| `operations/perfhammer/tests/rovo-chat-stream-api.py:9-10` | `HOST` (default `http://localhost:8081/`) + `TENANT_ID` env-var configurable |
| `operations/perfhammer/tests/rovo-chat-stream-api.py:57-67` | Streamed-response validation: expects `FINAL_RESPONSE` event in JSON-line body |

**No Gatling / k6 / JMeter alternative is wired in.** Perfhammer is the canonical load tool for this repo.

---

## B. Prerequisites (do these once)

> **VERIFIED 2026-05-04** (see `09-end-to-end-verification-log.md` §B.6): the requirements file installs cleanly and the framework runs end-to-end on **Python 3.13.5 from Anaconda** even though `.python-version` pins 3.12. Use whichever 3.12+ Python you have.

```bash
cd /Users/tchen7/MyProjects/atlassian_packages/conversational-ai-platform/operations/perfhammer

# Option 1 (verified working): Anaconda's Python (most macOS dev machines have it)
/opt/homebrew/anaconda3/bin/python -m venv .venv
source .venv/bin/activate

# Option 2: pyenv (if available)
# pyenv install 3.12; pyenv local 3.12; python3.12 -m venv .venv; source .venv/bin/activate

# Option 3: Homebrew python
# brew install python@3.12 && python3.12 -m venv .venv && source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt    # ~30 s
```

**Verify:**
```bash
python -c "import locust, perfkit, gevent; print('locust', locust.__version__)"
# expected: locust 2.20.1
# (perfkit doesn't expose __version__; check via `pip show perfkit`)
```

**PyCharm note (debug):** `Settings → Build, Execution, Deployment → Python Debugger → Gevent compatible` (per `README.md:6-9`).

---

## C. Three target modes

### C1. Target the LOCAL integration-test sandbox (preferred for quick load-feasibility)

The integration-test sandbox runs the full Spring Boot app on port `8081` (default) when launched via `./gradlew :convo-ai-test-integration:bootRun -Pnebulae.enabled=true`.

```bash
# Terminal 1: sandbox + app (one-time)
cd /Users/tchen7/MyProjects/atlassian_packages/conversational-ai-platform
atlas nebulae start -s integration-tests        # if not already running (see 08-live-sandbox.md)
./gradlew :convo-ai-test-integration:bootRun

# Terminal 2: load
cd operations/perfhammer
source .venv/bin/activate
export HOST=http://localhost:8081/
export TENANT_ID=DUMMY-a5a01d21-1cc3-4f29-9565-f2bb8cd969f5   # default is fine for local
locust -f tests/rovo-chat-stream-api.py
# open http://0.0.0.0:8089
```

**Headless invocation (verified working 2026-05-04 — for CI/scripts):**
```bash
locust -f tests/rovo-chat-stream-api.py --headless \
   --users 1 --spawn-rate 1 --run-time 3s \
   --host http://127.0.0.1:8081 --logfile /tmp/loc.log
# Output: per-endpoint RPS, p50/p66/p75/p80/p90/p95/p98/p99/p99.9/p99.99/max
# 1-user 3-sec smoke generates ~1,100 requests, ~441 RPS load-generator throughput on a single core.
```

In the Locust UI (interactive):
- **Number of users**: start at 10, ramp to 50, then 200
- **Spawn rate**: 1 user/sec (so the warm-up isn't a thundering herd)
- **Host**: prefilled from `HOST`; leave as-is
- Click **Start swarm**

What to watch:
- **RPS** column should plateau (not climb linearly with users) → that's where saturation begins
- **Failures** column should stay 0 until you see saturation; the first non-zero entry tells you the actual capacity wall
- **Median / p95 / p99** response times → these are the inputs to the M3 dashboard

### C2. Target staging (canonical pre-prod load test)

```bash
cd operations/perfhammer
source .venv/bin/activate

# Staging URL — see your team's runbook; commonly:
export HOST=https://convo-ai-platform.staging.atl-paas.net/
export TENANT_ID=<your-staging-tenant-uuid>     # Sliver-protected staging tenant; ask team for one

# Auth: rest_client.py does NOT inject Sliver/SLAuth headers itself. Two options:
#   (a) Run perfhammer from inside the Atlassian VPN with implicit slauth — works for some staging hosts.
#   (b) Use perfkit's HttpBaseUser auth hooks; modify tests/rovo-chat-stream-api.py to add headers
#       in `on_start()` (see perfkit docs).

locust -f tests/rovo-chat-stream-api.py
```

### C3. Target prod — DO NOT run without explicit approval

Prod load tests require: (1) Change Approval Board ticket; (2) coordinated runbook with on-call; (3) explicit cohort isolation (per-tenant cloudId allow-list); (4) cap below documented prod capacity (T13 in v7). **Do not assume any item above is in place.**

---

## D. Payload structure (verified)

`tests/rovo-chat-stream-api.py:14-50` POSTs ADF-formatted JSON:

```json
{
  "content": {"version": 1, "type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "test"}]}]},
  "context": {"browser_url": "...", "webSearchEnabled": false, "fileIds": [], "editor": "..."},
  "agentIds": ["..."],
  "mimeType": "application/vnd.atlassian.adf.json"
}
```

**To stress a specific code path** (e.g., to verify v7's T1 bound-channel fix), modify `text` to a longer prompt that exercises streaming, or set `webSearchEnabled=true` to force PageSearch involvement (Q-series path).

---

## E. Result interpretation — feeding the M7 dashboard

Locust UI shows per-endpoint:
- `# Reqs`, `# Fails`, `Median`, `99%ile`, `Avg`, `Min`, `Max`, `Avg size`, `Current RPS`, `Current Failures/s`

For the v7 measurement gate **M7 (saturation)**, capture three series across a 5-minute steady-state:
1. **Sustained RPS** at p95 ≤ TOME SLO budget
2. **Per-pool dispatcher saturation** from the running app's `/actuator/metrics` (use `convoai_dispatcher_pool_*` gauges)
3. **GC pause** from the app JVM (visible in `/actuator/metrics/jvm.gc.pause` or via SignalFx)

**Acceptance gate** (matches v7 §6 M7):
- 2,900 req/s sustained 5 min in **staging** with no failures and p95 ≤ SLO ⇒ ready for 150k MAU peak
- Per-pool utilization at peak < 80% ⇒ pool sizing OK; ≥ 80% triggers T11/T12 review (gated by ≥7 days of M7 data, per v7 anti-goal 33)

---

## F. Common load-test failure modes + fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| `Connection refused` immediately | `bootRun` not finished startup | wait for `Tomcat started on port 8081` in app log |
| All requests `403` | Missing tenant in TCS / Sliver expiry | reset Sliver token (see `01-prerequisites.md`); pick a TCS-registered tenant |
| All requests `400` with "ADF parse failed" | Modified payload broke ADF schema | revert payload, then incrementally re-add fields |
| RPS climbs then **drops to 0** with `connection reset` | Bound-channel saturation **OR** Tomcat thread starvation | this is the EXACT signal v7 T0a + T1 are designed to fix; capture stack trace via `jstack` on the app PID |
| Locust UI never loads | gevent missing or `python<3.12` | re-run prereqs in step B |

---

## G. Cleanup

```bash
# Stop locust (Ctrl-C in the locust terminal)
# Stop the bootRun (Ctrl-C in the gradle terminal)
# Stop the sandbox if you started one for this load test
atlas nebulae stop -s integration-tests
```

**Or** keep the sandbox running for further integration tests (cf. `08-live-sandbox.md`).

---

## H. CI integration

**There is no CI-driven perfhammer run.** Bitbucket pipelines (`bitbucket-pipelines.yml`) do not invoke perfhammer. Load testing is **operator-driven** today.

**Recommendation (also a v7 gap):** add a weekly perfhammer job that ramps to a target RPS in staging and posts results to SignalFx → Statsig auto-rollback (O1). Until that lands, perfhammer is run by the on-call before any T-series item ships and before any 25%/100% rollout of items in v7's L-series, T-series, R-series.
