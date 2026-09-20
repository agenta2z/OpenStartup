# Item 1+2+3: Feature Gate & Request Context Caching

**Priority: P0 | Effort: XS+XS+S | Combined: ~4–6 hours**

## Problem Evidence (verified from source)

### Measurement: calls per single prompt moderation request

| Call site | File | Line | Calls per request |
|---|---|---|---|
| `ModerationRequestContext.from_incoming_http_request()` | `micros_logging.py` | 31 | 1 (before_request) |
| `ModerationRequestContext.from_incoming_http_request()` | `prompt_moderation_controller.py` | 260 | 1 |
| `ModerationRequestContext.from_incoming_http_request()` via `_get_user_attributes()` | `feature_service.py` | 158 | N (once per gate check) |
| `ModerationRequestContext.from_incoming_http_request()` | `feature_service.py:is_use_case_allowed()` | 240 | 1 |

**Gate checks in the hot path** (verified by grepping `feature_service.` in prompt path):

```
prompt_moderation.py:76  → is_gpt_oss_safeguard_enabled()
prompt_moderation.py:150 → is_json_dynamic_config_for_thresholds_enabled()
rai_llama.py:334/438     → is_strict_tokenization_failure_enabled()     [called TWICE]
rai_llama.py:366/462     → is_increased_input_clipping_buffer_enabled() [called TWICE]
rai_llama.py:586         → is_prompt_moderation_teamserve_v2_4_primary_enabled()
rai_llama.py:588         → is_rai_ft_teamserve_primary_enabled()
rai_llama.py:595         → is_shadow_with_teamserve_v2_4_enabled()
rai_llama.py:600         → is_rai_ft_teamserve_shadowing_enabled()
rai_llama.py:605         → is_shadow_with_ai_gateway_2_3_3_enabled()
```

= **9+ gate calls** (9 in rai_llama.py alone) → 11 × `_get_user_attributes()` → 11 × `ModerationRequestContext.from_incoming_http_request()` → 11 × 6 header reads = **66 header reads**.

Plus the 3 direct calls above = **~14 total `from_incoming_http_request()` calls per request**.

At 83 RPS (prod-east): **~1,162 wasted context constructions per second**.

### Root cause: `_check_gate()` does not cache user attributes

```python
# feature_service.py:132–155 (current code)
def _check_gate(self, gate_name: str) -> bool:
    overrides = self.get_request_overrides()
    if overrides is not None and gate_name in overrides:
        return overrides[gate_name]

    try:
        attributes = self._get_user_attributes()  # ← re-constructs EVERY TIME
        if attributes.tenantId is None or attributes.tenantId == "":
            return False
        feature_gate_user = FeatureGateUser(attributes)          # ← new object EVERY TIME
        return self._client.check_gate(feature_gate_user, gate_name)
```

```python
# feature_service.py:158–163 (current code)
def _get_user_attributes(self) -> FeatureGateUserAttributes:
    return FeatureService.moderation_req_ctx_to_feature_attributes(
        ModerationRequestContext.from_incoming_http_request()   # ← called EVERY TIME
    )
```

## Solution: 3-layer caching using Flask `g`

Flask `g` is request-scoped proxy — safe with gevent (each request context is isolated).

### Layer A: Cache ModerationRequestContext

```python
# src/service/moderation/moderation_request_context.py
# Add class method:

@classmethod
def get_or_create_from_request(cls) -> "ModerationRequestContext":
    """Returns cached context for current request, creating it once if needed.
    
    Uses Flask g for request-scoped caching. Safe with gevent — each request
    has its own application context.
    """
    from flask import g
    _CACHE_KEY = "_rai_moderation_context"
    if not hasattr(g, _CACHE_KEY):
        setattr(g, _CACHE_KEY, cls.from_incoming_http_request())
    return getattr(g, _CACHE_KEY)
```

Replace call sites:
- `micros_logging.py:31` → `ModerationRequestContext.get_or_create_from_request()`  
- `prompt_moderation_controller.py:260` → same  
- `feature_service.py:158` → same  
- `feature_service.py:240` → same  

### Layer B: Cache gate user attributes

```python
# src/feature_service.py: update _get_user_attributes()
def _get_user_attributes(self) -> FeatureGateUserAttributes:
    _CACHE_KEY = "_rai_gate_user_attrs"
    if not hasattr(g, _CACHE_KEY):
        g._rai_gate_user_attrs = FeatureService.moderation_req_ctx_to_feature_attributes(
            ModerationRequestContext.get_or_create_from_request()
        )
    return g._rai_gate_user_attrs
```

### Layer C: Cache gate results per (gate_name)

```python
# src/feature_service.py: update _check_gate()
def _check_gate(self, gate_name: str) -> bool:
    # 1. Debug overrides (unchanged)
    overrides = self.get_request_overrides()
    if overrides is not None and gate_name in overrides:
        log.info("Debug override for gate %s: %s", gate_name, overrides[gate_name])
        return overrides[gate_name]

    # 2. Request-scoped cache
    gate_cache_key = f"_rai_gate_{gate_name}"
    if hasattr(g, gate_cache_key):
        return getattr(g, gate_cache_key)

    # 3. Evaluate (only once per gate per request)
    try:
        attributes = self._get_user_attributes()  # cached (Layer B)
        if not attributes.tenantId:
            log.info("tenantId is None, defaulting %s to false", gate_name)
            result = False
        else:
            feature_gate_user = FeatureGateUser(attributes)
            result = self._client.check_gate(feature_gate_user, gate_name)
        setattr(g, gate_cache_key, result)
        return result
    except Exception:
        log.info("Outside Flask context, defaulting %s to false", gate_name)
        return False
```

### Special case: outside Flask context

The existing `try/except` on `RuntimeError` (outside Flask request context) must be preserved for:
- Startup initialization (`FeatureService.__init__()`)
- Background threads / test environments

The `hasattr(g, ...)` call raises `RuntimeError` outside a request context. The existing try/except already handles this — just extend it.

## Tests to add/update

1. `test_feature_service.py`: Mock `ModerationRequestContext.from_incoming_http_request`. Assert it is called **exactly once** per request even when 5 gates are checked.
2. `test_feature_service.py`: Assert `check_gate` is called **exactly once** per unique gate name per request (not twice for gates evaluated twice in hot path).
3. `test_feature_service.py`: Assert debug overrides still work correctly (override bypasses cache).
4. `test_moderation_request_context.py`: Assert `get_or_create_from_request()` returns the same object instance within a request context.

## Acceptance criteria

- [ ] `grep -c "from_incoming_http_request()" src/feature_service.py` → 0 (removed from hot path)
- [ ] New method `get_or_create_from_request()` exists in `moderation_request_context.py`
- [ ] `from_incoming_http_request()` call count per request: **1** (verified by mock assertion in test)
- [ ] Gate result call count for a gate checked twice (e.g. `is_strict_tokenization_failure_enabled()`): **1** SDK call (verified by mock)
- [ ] `./bin/unit-test` passes; coverage floors held
- [ ] `./bin/lint` passes

## Non-regression guarantee

- Gate values: unchanged (same Statsig SDK evaluation, same user attributes)
- Debug overrides: unchanged (checked before cache)
- Outside-request-context behavior: unchanged (try/except preserved)
- No new global state: `Flask.g` is request-scoped by design
