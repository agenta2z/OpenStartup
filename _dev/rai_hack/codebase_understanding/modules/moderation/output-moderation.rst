.. _mod-output-moderation:

=====================
Output Moderation
=====================

:Files: ``src/service/moderation/output/output_moderation.py``, ``src/service/moderation/output/stream_processor.py`` (~150 LoC), ``src/service/moderation/output/url_checker.py`` (~60 LoC)
:Importance: **P1 — LLM output safety gate**

Purpose
========

Screens LLM-generated text in real-time as it streams back to users. Operates
on an NDJSON stream of chunks, accumulating content and checking for harm.
Also extracts and reports external URLs found in outputs.

API contract
=============

**Request**: NDJSON stream (one JSON object per line):

.. code-block:: json

   {"stream_id": "uuid", "current_chunk": "text chunk", "chunk_index": 0}
   {"stream_id": "uuid", "current_chunk": "more text", "chunk_index": 1}

Required headers same as prompt moderation plus ``Content-Type: application/x-ndjson``.

**Response**: NDJSON stream (one per input chunk):

.. code-block:: json

   {"status": "ALLOWED", "stream_id": "uuid", "chunk_index": 0, "harm_category": null, "content": "text chunk", "external_urls": []}
   {"status": "DISALLOWED", "stream_id": "uuid", "chunk_index": 1, "harm_category": "illegal_activity", "content": "", "external_urls": []}

Stream processing (``stream_processor.py``)
=============================================

Key constants:

* ``MAX_ACCUMULATED_CONTENT_SIZE = 10 * 1024 * 1024`` (10 MB)
* ``MAX_CHUNK_SIZE = 100 * 1024`` (100 KB)
* ``MAX_LINE_SIZE = 1 * 1024 * 1024`` (1 MB per NDJSON line)

Per-chunk processing loop:

.. code-block:: python

   for line in request.stream:
       # 1. Parse ModerateOutputRequest
       request_obj = ModerateOutputRequest.model_validate_json(line)

       # 2. Size checks
       if len(line) > MAX_LINE_SIZE: skip / error
       if len(current_chunk) > MAX_CHUNK_SIZE: skip / error

       # 3. Accumulate
       accumulated = stream_content[stream_id] + current_chunk
       if len(accumulated) > MAX_ACCUMULATED_CONTENT_SIZE: stop

       # 4. URL extraction (on accumulated content)
       url_result = url_checker.extract_external_urls(accumulated)
       new_urls = diff(url_result, previous_url_result[stream_id])

       # 5. ML moderation (on accumulated content)
       mod_result = prompt_moderation_service.predict_harm_category(accumulated)

       # 6. Yield response
       yield ModerateOutputResponse(
           status=mod_result.status,
           stream_id=stream_id,
           chunk_index=chunk_index,
           harm_category=mod_result.harm_category,
           content=current_chunk if ALLOWED else "",
           external_urls=new_urls
       )

       # 7. Early exit on violation
       if mod_result.status == DISALLOWED:
           break

URL checker (``url_checker.py``)
==================================

``extract_external_urls(text: str) -> ExternalUrlsResult``:

.. code-block:: python

   URL_REGEX = re.compile(r'\b(https?://|www\.)[^\s<>"\']{1,2048}')
   # Finds all URLs in text
   # Filters out internal Atlassian domains from internal_domains.txt
   # Deduplicates by domain (not full URL)

``ExternalUrlsResult``:

* ``external_urls: List[str]`` — full URLs (after filtering)
* ``external_domains: List[str]`` — deduplicated domain list

``internal_domains.txt`` contains Atlassian-owned domains (atlassian.com,
jira.com, confluence.com, etc.) that should not be flagged as external links.

Moderation service delegation
===============================

Output moderation delegates to ``PromptModerationService`` for the actual ML
inference, passing the **accumulated** content (not just the current chunk).
This means the model sees the full context up to the current point in the stream,
which is important for detecting harm that builds up gradually across chunks.

Key design decisions:

1. **Accumulation over chunks**: prevents evasion by spreading harmful content
   across many small chunks.
2. **Early termination**: stops stream immediately on DISALLOWED (no further chunks sent).
3. **URL extraction independent of ML**: URLs are extracted regardless of whether
   ML moderation is enabled, so external link reporting always works.
4. **Per-stream-id state**: multiple concurrent streams handled independently via
   ``stream_content`` dict keyed by ``stream_id``.
