# Items 7, 8, 13: Parser Metrics + Model Unification + fail_open Metrics

**Priority: P1 | Effort: M+L+S**

---

## Item 7: Parser Fallback Metrics (AI-126)

### Problem: 7 silent fallback paths in model_text_response_parse.py

Verified by reading full file. All 7 paths:

```
parse_model_response_to_dict(json_str, model_class):
  
  Path 1 (PRIMARY): model_class.model_validate_json(cleaned_content)
      → SUCCESS: no metric emitted  ← MISSING
      → FAIL: ValidationError → check edge cases

  Path 2 (MISSING COMMA FIX): fix '", "toBeFiltered"' pattern
      model_validate_json(missing_comma_fixed)
      → no metric  ← MISSING

  Path 3 (QUOTE NORMALIZATION + TRAILING COMMA):
      replace("'", '"') + TRAILING_COMMA_PATTERN.sub("}", normalized)
      json.loads(normalized) → model_construct()
      → no metric  ← MISSING

  Path 4 (JSON_PATTERN REGEX):
      JSON_PATTERN.search(cleaned_content) → json.loads() → model_construct()
      → no metric  ← MISSING

  Path 5 (CATEGORY + FILTER REGEX):
      CATEGORY_PATTERN.search() + FILTER_PATTERN.search() → model_construct()
      → no metric  ← MISSING

  Path 6 (JOINED FORMAT REGEX):
      re.search(r'category[:=]...toBeFiltered[:=]') → model_construct()
      → no metric  ← MISSING

  Path 7 (CATEGORY_EQUAL + FILTER_EQUAL STRING):
      string.split() + re.search() → model_construct()
      → no metric  ← MISSING

  FINAL: log.warning("No valid category content found") → raise
      → no metric  ← MISSING
```

### Solution: Add metric at each path entry point

Add new metrics to `Metric` enum:

```python
# metrics_handler.py
class Metric(StrEnum):
    ...
    PARSER_OUTCOME = "flask.micros.parser.outcome"  # new
```

Tags:
```python
class MetricTag(StrEnum):
    ...
    PARSER_PATH = "parser_path"       # primary|path_2|path_3|...|failed
    PARSER_MODEL_VERSION = "parser_model_version"
```

Emit at start of each path:

```python
def parse_model_response_to_dict(json_str: str, model_class, model_version: str = "unknown"):
    cleaned_content = clean_llm_json_response_content(json_str)
    
    # PATH 1 — PRIMARY
    try:
        result = model_class.model_validate_json(cleaned_content)
        send_metric(Metric.PARSER_OUTCOME, tags={
            MetricTag.PARSER_PATH: "primary",
            MetricTag.PARSER_MODEL_VERSION: model_version,
        })
        return result
    except ValidationError:
        ...
    
    # PATH 2 — MISSING COMMA
    if '"category": "' in cleaned_content and '" "toBeFiltered": ' in cleaned_content:
        ...
        try:
            result = model_class.model_validate_json(missing_comma_fixed)
            send_metric(Metric.PARSER_OUTCOME, tags={
                MetricTag.PARSER_PATH: "path_2_missing_comma",
                MetricTag.PARSER_MODEL_VERSION: model_version,
            })
            return result
        except ValidationError:
            pass
    
    # PATH 3, 4, 5, 6, 7 — each gets a send_metric() before return
    ...
    
    # FAILED
    send_metric(Metric.PARSER_OUTCOME, tags={
        MetricTag.PARSER_PATH: "failed",
        MetricTag.PARSER_MODEL_VERSION: model_version,
    })
    log.warning(...)
    raise
```

### Alert to add (SignalFx)

```
primary_parse_rate = parser_outcome{path=primary} / sum(parser_outcome{all paths})

ALERT if primary_parse_rate < 0.95 over 5-minute window → P1 page
```

This alert will fire if a model version change causes format drift — catching it within minutes instead of hours/days.

### model_construct() audit

Six `model_construct()` calls in the file (paths 3–7). Each should have a `# CONSTRAINT:` comment:

```python
# CONSTRAINT: input is validated structurally above (keys "category" and "toBeFiltered"
# exist and were extracted via json.loads/regex). Pydantic validation bypassed because
# input is from a known-fallback parse path where full validation would re-raise.
# Risk: category may be an unrecognized string → handled by PromptHarmCategory._missing_()
return model_class.model_construct(
    category=str(parsed_data["category"]),
    toBeFiltered=bool(parsed_data["toBeFiltered"]),
)
```

### Coverage target

Raise `coverage-floors.yml` entry from **74% to 90%** after adding tests for each path.

---

## Item 13: fail_open + model_selected Metrics (AI-127 metrics component)

### Problem: fail-open decisions are invisible

```python
# inference_models/error_handling.py (verified by reading file)
# inference_error_handler context manager catches exceptions and optionally returns:
ModerationResult(category="none", toBeFiltered=False, violation_score=0.0)
```

This result is identical to a genuine "no harm found" result. **Zero dedicated metric**.

In `prompt_moderation_controller.py`, the `PROMPT_MODERATION_OUTCOME` metric tags include `fail_open_type` from `get_prompt_moderation_tags()` — but this tag is only populated **after** the controller has the result. Inside `inference_error_handler`, no metric fires.

### Solution: Emit dedicated metrics from error handler

```python
# inference_models/error_handling.py: add to each fail-open branch

# In the timeout handler:
except TimeoutError:
    log.warning("Inference timeout for %s", ctx.use_case_id)
    send_metric(Metric.DECISION_FAIL_OPEN, tags={
        MetricTag.FAIL_OPEN_REASON: "timeout",
        MetricTag.MODEL_VERSION: ctx.model_evaluation_version,
        MetricTag.USE_CASE_ID: ctx.use_case_id,
    })
    if ctx.fail_open_on_timeout:
        yield  # return default ALLOWED result
        return
    raise

# In the circuit breaker handler:
except pybreaker.CircuitBreakerError:
    send_metric(Metric.DECISION_FAIL_OPEN, tags={
        MetricTag.FAIL_OPEN_REASON: "circuit_breaker_open",
        ...
    })
    ...
```

Also add:
```python
# prompt_moderation.py: after model.run_inference() succeeds
send_metric(Metric.MODEL_SELECTED, tags={
    MetricTag.MODEL_NAME: "llama" if not use_gpt_oss else "gpt_oss",
    MetricTag.MODEL_VERSION: model.version,
    MetricTag.USE_CASE_ID: moderation_context.use_case_id,
})
```

Add to `Metric` enum: `DECISION_FAIL_OPEN`, `MODEL_SELECTED`
Add to `MetricTag` enum: `FAIL_OPEN_REASON`, `MODEL_NAME`

---

## Item 8: Inference Model Layer Unification (AI-127)

### Duplication inventory (verified from code)

| Duplicated element | In `rai_llama.py` | In `rai_gpt_oss.py` |
|---|---|---|
| `RAIFTTeamserveEndpoint` class | ~60 lines | ~60 lines (identical structure, different transport) |
| `run_inference()` skeleton | `LlamaModel.run_inference()` | `GPTOSSModelInTeamserve.run_inference()` |
| `_tokenization_options()` | Present in `LlamaModel` + `LlamaModelInTeamserve` | Present in `GPTOSSModelInTeamserve` |
| Error handling | Inline in each model | Inline in each model |
| `is_strict_tokenization_failure_enabled()` check | Lines 334, 438 (twice!) | Present |
| `is_increased_input_clipping_buffer_enabled()` check | Lines 366, 462 (twice!) | Present |
| `model_template_and_prompt_tokens` caching pattern | Both `LlamaModel` and `LlamaModelInTeamserve` | `GPTOSSModelInTeamserve` |

### Proposed class hierarchy

```
InferenceModel[U, P] (abstract, model.py — unchanged)
└── BasePromptModerationModel[U, P] (NEW: src/inference_models/base.py)
    ├── run_inference()          → calls _tokenize() + _prepare() + endpoint.send() + _parse()
    ├── _tokenization_options()  → shared, flag-aware
    ├── _get_model_template_tokens() → shared, lazy-cached
    ├── _emit_model_selected()   → shared metric emission
    └── subclasses:
        ├── LlamaModel           → override _prepare(), _parse_response() (log-probs)
        ├── LlamaModelInTeamserve→ override _prepare() (numpy tensors)
        └── GPTOSSModelInTeamserve → override _prepare() (chat format), _parse_response()
```

### Expected file size reduction

| File | Current | Target |
|---|---|---|
| `rai_llama.py` | 689 lines | ≤ 350 lines |
| `rai_gpt_oss.py` | 287 lines | ≤ 150 lines |
| `base.py` (new) | 0 | ~200 lines |
| Net reduction | — | ~276 lines (-37%) |

### Key deduplication: `is_strict_tokenization_failure_enabled()` called twice

In `LlamaModel._tokenization_options()` (line 334) AND `LlamaModel.run_inference()` (line 438):

```python
# CURRENT: called twice per inference
# In _tokenization_options():
if self.feature_service.is_strict_tokenization_failure_enabled():  # line 334
    buffer_size = ...

# In run_inference():
if self.feature_service.is_strict_tokenization_failure_enabled():  # line 438
    if tokenized_input.is_empty():
        raise ...
```

These can be collapsed into a single call in the shared base class.

### Implementation order

1. Create `base.py` with `BasePromptModerationModel`
2. Move `_tokenization_options()` (with single flag check) to base
3. Move `model_template_and_prompt_tokens` caching to base
4. Make `LlamaModel`, `LlamaModelInTeamserve`, `GPTOSSModelInTeamserve` extend base
5. Add `_emit_model_selected()` to base (closes Item 13)
6. Delete duplicated code
7. Verify tests pass + coverage floors held

### Acceptance criteria

- [ ] `grep -c "class.*InferenceModel" src/inference_models/base.py` → 1
- [ ] `wc -l src/inference_models/rai_llama.py` → ≤ 350
- [ ] `wc -l src/inference_models/rai_gpt_oss.py` → ≤ 150
- [ ] `is_strict_tokenization_failure_enabled()` called exactly once per inference (not twice)
- [ ] `is_increased_input_clipping_buffer_enabled()` called exactly once per inference (not twice)
- [ ] `rai.model.selected` metric emitted from base class
- [ ] `./bin/unit-test --coverage` passes; `rai_llama.py` floor ≥ 74%; `rai_gpt_oss.py` floor = 100%
