.. _mod-confidence-and-shadowing:

==============================
Confidence Thresholds & Shadowing
==============================

See :doc:`model-abstraction` for full detail on confidence thresholds and model shadowing.

Quick reference:

* **Confidence thresholds**: ``src/inference_models/confidence/confidence_thresholds.py`` — 60s TTL cache, per-model-version, default 0.5
* **Model shadowing**: ``src/inference_models/model_shadowing/shadower.py`` — gevent Pool(20), A only returned, B evaluated async
* **ShadowShim**: wraps ``ModelShadower`` as ``InferenceModel`` for transparent factory usage
