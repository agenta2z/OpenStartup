==================================
``logging/`` — Fluent Bit → Elasticsearch ingest pipeline
==================================

Purpose
=======

``logging/`` (48 files) deploys a centralised log-collection pipeline
into the ``logging`` namespace: a **Fluent Bit DaemonSet** scrapes pod
logs on every node and forwards them to the Temporal-cluster
**Elasticsearch** with automatic Kubernetes metadata enrichment and
Temporal workflow context extraction.

Tech stack
==========

* **Fluent Bit** (DaemonSet via Helm chart at ``charts/fluent-bit-dte/``)
* **Elasticsearch** ingest pipelines (JSON definitions)
* **Lua** for in-Fluent-Bit metadata extraction
* **Helmfile**, Bash deploy scripts
* **Filebeat** as an alternative shipper (see ``helmfile-filebeat.yaml``)

Inventory highlights
====================

.. list-table::
   :header-rows: 1
   :widths: 55 45

   * - Path
     - Role
   * - ``logging/helmfile.yaml``
     - Primary deploy manifest
   * - ``logging/helmfile-filebeat.yaml``
     - Alternative Filebeat path
   * - ``logging/values.yaml``
     - Fluent Bit DaemonSet values (output pipeline, kubernetes filter)
   * - ``logging/values-custom.yaml``
     - Per-environment overrides
   * - ``logging/filebeat-values.yaml``
     - Filebeat values (alt path)
   * - ``logging/elasticsearch-ilm-policy.yaml``
     - ES ILM lifecycle policy (rollover, retention)
   * - ``logging/elasticsearch-ingest-pipeline.json``
     - Pipeline ``parse-json-logs`` (parse + enrichment)
   * - ``logging/filebeat-ingest-pipeline.json``
     - Alt pipeline for Filebeat
   * - ``logging/scripts/temporal-metadata-lua.lua``
     - Lua: extracts ``temporal.workflow.id`` etc.
   * - ``logging/charts/fluent-bit-dte/``
     - Custom Fluent Bit chart
   * - ``logging/deploy.sh``
     - Wraps ``helmfile apply``
   * - ``logging/deploy-filebeat.sh``
     - Wraps the alt path
   * - ``logging/apply-filebeat-pipeline.sh`` (134) /
       ``apply-ingest-pipeline.sh`` (134)
     - Pipeline registration (``PUT /_ingest/pipeline``)
   * - ``logging/check-fluent-bit-errors.sh`` (60)
     - Triage helper
   * - ``logging/check-pods.sh`` (44)
     - Status helper
   * - ``logging/check-json-parsing.sh`` (118) /
       ``verify-json-parsing.sh`` (133)
     - JSON validation
   * - ``logging/check-sample-log.sh`` (78)
     - Sample log inspector
   * - ``logging/DEPLOYMENT.md`` (188)
     - Full deployment guide
   * - ``logging/INGEST_PIPELINE_EXPLANATION.md``
     - Pipeline logic & enrichment details
   * - ``logging/OPTIONS.md`` / ``RECOMMENDATION.md``
     - Comparative option matrix
   * - ``logging/README.md``
     - High-level overview

Public surface
==============

None — internal infra. Logs land in ES indices ``kubernetes-logs-YYYY.MM.DD``;
Kibana at ``temporal-kibana.fqk5.kitt-inf.net``.

Auth & RBAC
===========

* **K8s ClusterRole:** read pods/nodes for the kubernetes filter
* **ES auth:** username/password via Helm value secret refs

Build & deploy
==============

.. code-block:: bash

   ./deploy.sh                          # helmfile apply (Fluent Bit)
   ./apply-ingest-pipeline.sh           # registers parse-json-logs
   kubectl logs -n logging \
       -l app.kubernetes.io/name=fluent-bit --tail=50
   kubectl exec -n temporal -it <es-pod> -- \
       curl http://localhost:9200/kubernetes-logs-*/_count

Integration with gcp_kitt
=========================

* **Source of logs:** every pod on every node
* **Sink:** the platform Elasticsearch from ``helmfile/``
* **Consumer:** ``monitoring/`` Grafana dashboards and Kibana

Hazards
=======

* **ES connectivity is silent failure** — Fluent Bit happily buffers and
  drops; verify with ``check-pods.sh`` after every deploy.
* **Pipeline name must match.** ``parse-json-logs`` is referenced from
  Fluent Bit output config; mismatched names silently bypass JSON
  parsing.
* **Temporal enrichment requires ``temporal.workflow.id`` labels** —
  pods without the label produce un-enriched events.
* **Two shippers in tree** (Fluent Bit and Filebeat); never run both at
  once or you'll double-bill ES indices.
