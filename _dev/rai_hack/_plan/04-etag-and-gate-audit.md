# Items 9, 10: ETag Fix + Feature Gate Audit

---

## Item 9: Fix ETag Double Body Parse

**Priority: P2 | Effort: S (half-day)**

### Problem: Request body parsed twice per request

```python
# prompt_etag.py:check_etag() — Parse #1
request_body = request.get_json()                               # JSON parse
request_input = ModeratePromptRequest.model_validate(request_body)  # Pydantic

# → then calls _generate_possible_etags(request_input, version_str)
# → which calls generate_comparison_etag(request_input, model_version)  
# → which calls request_input.model_dump_json()  # re-serializes to JSON string for hashing

# prompt_moderation_controller.py:index() — Parse #2
@validate()   # flask-pydantic: parses request.get_json() AGAIN
def index(body: ModeratePromptRequest):
```

For the **ETag HIT path** (304 response): parse #2 never reaches the handler, so it's fine. But parse #1 is wasted for ETag miss requests because flask-pydantic will parse again. **Both parses happen on every ETag miss.**

Additionally, `_generate_possible_etags()` loops over all 17 `PromptHarmCategory` values to generate all possible ETags. This is wasted work for the miss path — we only need to know if the hash of the request body matches **any** known prefix.

### Solution: Hash raw request body string

The ETag value is `W/"SHA256(request_body_json + model_version)[:16]:category_hash"`. The key insight: the **base hash** (the part before `:`) is the same for all categories. We can check prefix match without enumerating categories:

```python
def check_etag(request: Request) -> Response | None:
    if_none_match = request.headers.get("If-None-Match")
    if not if_none_match:
        return None

    # Get raw body bytes — no JSON parse needed for hash
    raw_body = request.get_data(as_text=True)
    if not raw_body:
        return None

    model_version = f"{ModelVersion.V2_3_3.value}:{ModelVersion.V2_3_3.value}"
    
    # Hash raw body directly (same content as model_dump_json() for same request)
    # Note: this changes the hash from JSON-of-Pydantic-model to raw-body-string.
    # BOTH are stable for identical requests. If we change to raw-body hash,
    # existing client ETags will be invalid once (clients will get 200, then 
    # get a new ETag, then 304 on next repeat). Acceptable one-time cache bust.
    base_hash = hashlib.sha256((raw_body + model_version).encode()).hexdigest()[:16]
    
    # ETag format: W/"base_hash" or W/"base_hash:category_hash"
    # Both start with W/"base_hash — prefix match is sufficient
    etag_prefix = f'W/"{base_hash}'
    if if_none_match.startswith(etag_prefix):
        response = make_response("", 304)
        response.headers["ETag"] = if_none_match
        return response

    return None
```

**Trade-off**: This changes the hash algorithm (raw body string vs Pydantic model_dump_json). Existing clients' ETags will be invalid for exactly 1 request (they'll get a 200 with a new ETag, then 304 on repeat). This is safe and correct.

**Alternative (no hash change)**: Parse the body in `check_etag`, store in `g`, have flask-pydantic read from `g`. More complex, preserves hash compatibility.

### Quantifiable benefit

- Eliminates one Pydantic validation + one JSON parse per ETag miss request
- Eliminates 17-category loop on every ETag check
- On ETag hit: eliminates all downstream processing entirely
- ETag hit rate is currently unmeasured — add metric to track it

---

## Item 10: Feature Gate Audit + Lifecycle Policy (AI-128)

**Priority: P1 | Effort: M (1 day)**

### Current state: 27 gates, 0 documented (21 unique Statsig values, verified by grep)

Full gate inventory from `feature_service.py` `Features` enum:

| Gate constant | Classification | Action |
|---|---|---|
| `AGENT_MODERATION_PROMPT_V2_3_1` | rollout | annotate + review |
| `AGENT_MODERATION_V3` | rollout | annotate + review |
| `ENABLE_INCREASED_INPUT_CLIPPING_BUFFER` | kill-switch | annotate |
| `ENABLE_USER_INPUT_LOGGING` | kill-switch (privacy) | annotate |
| `ENABLE_CONN_POOL_LOGGING` | debug (temp) | cleanup if at 0% |
| `ENABLE_EXTRA_IMAGE_PREPROCESSING` | experiment | annotate + deadline |
| `ENABLE_IMAGE_MODERATION_V1` | rollout | annotate |
| `ENABLE_IMAGE_MODERATION_ANTIABUSE` | rollout | annotate |
| `DISABLE_ANALYTICS` | kill-switch | annotate |
| `ENABLE_TEAMSERVE_SHADOWING_FOR_PROMPT_MODERATION` | experiment | deadline: delete after shadow concludes |
| `ENABLE_TEAMSERVE_PRIMARY_FOR_PROMPT_MODERATION` | rollout | annotate |
| `ENABLE_RESPONSE_HANDLING` | rollout? | verify if dead |
| `ENABLE_FAIL_OPEN_ON_MODEL_TIMEOUT` | kill-switch (reliability) | annotate |
| `ENABLE_STRICT_TOKENIZATION_FAILURE` | rollout | annotate + deadline |
| `ENABLE_CUSTOM_RETRY_CONFIG` | rollout | annotate + deadline |
| `ENABLE_FAIL_OPEN_ON_CIRCUIT_BREAKER_OPEN` | kill-switch (reliability) | annotate |
| `ENABLE_SAFE_PARSE_JSON_RESPONSE` | rollout → dead? | verify if at 100% → delete |
| `ENABLE_SHADOW_WITH_AI_GATEWAY_2_3_3` | experiment | deadline: delete after shadow |
| `ENABLE_TEAMSERVE_V2_4_PRIMARY` | rollout | annotate |
| `ENABLE_SHADOW_WITH_TEAMSERVE_2_4` | experiment | deadline: delete after shadow |
| `ENABLE_JSON_DYNAMIC_CONFIG_THRESHOLDS` | rollout | annotate |
| `ENABLE_STANDARDIZED_IMAGE_MODERATION_RESPONSE` | rollout | annotate |
| `DISABLE_EXTERNAL_LLM_CALLS` | kill-switch | annotate |
| `READ_EXTERNAL_LLM_CALLS_ORG_SETTING` | rollout | annotate |
| `ENABLE_FOR_DEVELOPER` | permanent (dev) | annotate |
| `ENABLE_GPT_OSS_SAFEGUARD` | rollout | annotate + deadline |

### Annotation format (from AGENTS.md)

```python
# Owner: @xhuang3 | Type: rollout | Created: 2026-03-15 | Cleanup by: 2026-06-01
ENABLE_GPT_OSS_SAFEGUARD = "rai_api_enable_gptoss_safeguard"
```

### Gates to investigate for deletion

`ENABLE_SAFE_PARSE_JSON_RESPONSE` — if this is at 100% rollout, the guarded code path is always active and the flag can be deleted (code becomes unconditional). Verify via Statsig dashboard.

`ENABLE_CONN_POOL_LOGGING` — debug tooling flag. If at 0%, code path is dead. Delete flag and its guarded block.

Shadow experiment gates (`ENABLE_TEAMSERVE_SHADOWING_*`, `ENABLE_SHADOW_WITH_*`) — all 3 shadow flags should have a firm deadline tied to the shadow experiment conclusion.

### Acceptance criteria

- [ ] `grep -c "# Owner:" src/feature_service.py` equals the post-audit gate count (currently 27 pre-audit)
- [ ] Every annotation matches format `# Owner: @user | Type: rollout|kill-switch|experiment | Created: YYYY-MM-DD | Cleanup by: YYYY-MM-DD`
- [ ] Any gate deleted also has its guarded code path deleted
- [ ] `./bin/unit-test --coverage` passes; coverage floors held
- [ ] Jira ticket for each shadow gate deadline
