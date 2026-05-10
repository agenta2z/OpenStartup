==================================
``lambda/`` — AWS Lambda scrapers (DynamoDB + Postgres backends)
==================================

Purpose
=======
Serverless side-channel for ``gcp_kitt``. Two submodules:

- ``lambda/dynamo/`` — DynamoDB-backed scraper job runner (POST a job →
  results land in DynamoDB → GET to fetch).
- ``lambda/pg/`` — PostgreSQL-backed equivalent.

Both are deployed as standalone AWS Lambda functions (Python 3,
``boto3`` + ``psycopg2``) with their own SAM/CloudFormation template.

Public APIs (dynamo)
====================
- ``POST /scraper_post_job`` — initiate scraper job
- ``GET  /scraper_get_results`` — retrieve results

Layout
======
::

    lambda/
      dynamo/
        template.yaml       # SAM template
        scraper_post_job/
        scraper_get_results/
      pg/
        template.yaml
        ...

IAM / runtime requirements
==========================
- Lambda execution role with DynamoDB or RDS permissions as appropriate.
- For ``pg``: VPC config + RDS security-group ingress.

Integration
===========
Event-driven via EventBridge / SNS. Coordinates with ``ASI`` and
``Sweeper`` through shared event topics for inventory tracking.

Gotchas
=======
- Cold-start latency on ``pg`` is dominated by ``psycopg2`` import and
  RDS connection setup — keep the function warm for time-sensitive
  callers.
- DynamoDB schema is hardcoded in the handler; schema changes require
  coordinated deploy + handler update.
