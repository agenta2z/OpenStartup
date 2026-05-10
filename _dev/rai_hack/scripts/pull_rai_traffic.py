#!/usr/bin/env /opt/homebrew/anaconda3/bin/python
"""
pull_rai_traffic.py — End-to-end attempt to pull historical RAI moderation
traffic from a local laptop, sandbox, or CI runner.

WHAT THIS SCRIPT DOES (in order):

  1. Verifies Anaconda Python + required packages.
  2. Mints a Databricks-compatible bearer token through every credential
     provider supported by `databricks-sdk` (env var, .databrickscfg,
     OAuth M2M, OAuth U2M / PKCE browser).
  3. If a token is found OR can be obtained, calls the Databricks
     Statement Execution API to query ONLY the metadata-tagged table
     `collaboration.ai_safety.online_eval_metrics` (no UGC concerns).
  4. Falls back to `atlas ml` based introspection if no Databricks token
     is available — verifies that the SLAuth/Kerberos chain is alive.
  5. Prints a single-row count summary so you can see real numbers without
     ever touching raw prompt/response text.

WHAT THIS SCRIPT INTENTIONALLY DOES NOT DO:

  * Read raw `data.payload.prompt_text` / `response_text` from the UGC
    Delta bucket — that requires Trust+/Privacy review per §9.6 of the
    data-storage doc.
  * Bypass `get_regulated_opt_out_tenants()` — even on metadata reads.
  * Persist any results to disk (prevents accidental UGC leakage).

USAGE:

  /opt/homebrew/anaconda3/bin/python pull_rai_traffic.py
      [--host https://atlassian-discover.cloud.databricks.com]
      [--warehouse-id <sql-warehouse-id>]
      [--days 7]                         # how many days of metrics to pull
      [--dry-run]                        # just report what's available

EXIT CODES:
  0   succeeded — printed metrics summary
  2   no Databricks credentials available — instructions printed
  3   network unreachable
  4   Databricks API returned an error
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


# ------------------------------------------------------------ helpers


def _section(title: str) -> None:
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def _step(msg: str) -> None:
    print(f"  → {msg}")


def _ok(msg: str) -> None:
    print(f"  ✓ {msg}")


def _warn(msg: str) -> None:
    print(f"  ⚠ {msg}")


def _err(msg: str) -> None:
    print(f"  ✗ {msg}", file=sys.stderr)


# ------------------------------------------------------------ phase 1: env


def verify_environment() -> None:
    _section("Phase 1 — Environment verification")
    _step(f"Python: {sys.executable}  ({sys.version.split()[0]})")
    if "anaconda" not in sys.executable.lower():
        _warn("Not running under Anaconda Python — some checks may fail.")

    needed = {
        "databricks.sdk":  "databricks-sdk",
        "requests":        "requests",
        "pandas":          "pandas",
    }
    missing = []
    for mod, pkg in needed.items():
        try:
            __import__(mod)
            _ok(f"{pkg} importable")
        except ImportError:
            _err(f"{pkg} missing — install with: pip install {pkg}")
            missing.append(pkg)
    if missing:
        sys.exit(2)


# ------------------------------------------------------------ phase 2: auth discovery


def discover_databricks_token(host: str) -> Optional[str]:
    """Try every sanctioned auth source. Returns a bearer token or None."""
    _section("Phase 2 — Databricks credential discovery")

    # 2a. DATABRICKS_TOKEN env var (most common in CI)
    tok = os.environ.get("DATABRICKS_TOKEN")
    if tok and tok.startswith(("dapi", "dkea")):
        _ok(f"Found DATABRICKS_TOKEN env var (len={len(tok)})")
        return tok
    _step("DATABRICKS_TOKEN env var: not set")

    # 2b. ~/.databrickscfg
    cfg = Path.home() / ".databrickscfg"
    if cfg.is_file() and cfg.stat().st_size > 0:
        _ok(f"Found {cfg} ({cfg.stat().st_size} bytes)")
        try:
            for line in cfg.read_text().splitlines():
                if line.strip().startswith("token"):
                    val = line.split("=", 1)[-1].strip()
                    if val.startswith("dapi"):
                        _ok("Token extracted from .databrickscfg")
                        return val
        except Exception as e:
            _warn(f"could not parse .databrickscfg: {e}")
    else:
        _step("~/.databrickscfg: not present")

    # 2c. databricks-sdk default chain (handles OAuth M2M, U2M)
    try:
        from databricks.sdk import WorkspaceClient
        _step("Trying databricks-sdk default credential chain (silent only)")
        os.environ.setdefault("DATABRICKS_HOST", host)
        try:
            w = WorkspaceClient()
            me = w.current_user.me()  # noqa: F841 — provokes auth
            _ok(f"databricks-sdk auth succeeded as {me.user_name}")
            # Extract the bearer token via internal config
            return w.config.authenticate().get("Authorization", "").replace(
                "Bearer ", ""
            ) or None
        except Exception as e:
            _step(f"databricks-sdk default auth chain: {type(e).__name__}: "
                  f"{str(e)[:120]}")
    except ImportError:
        _warn("databricks-sdk not installed")

    # 2d. SLAuth (Atlassian internal) — does NOT work for Databricks workspace
    #     itself but proves Kerberos chain is alive.
    if shutil.which("atlas"):
        _step("Atlassian 'atlas' CLI present — testing Kerberos via slauth")
        try:
            r = subprocess.run(
                ["atlas", "slauth", "token", "--aud=databricks", "--ttl=2m"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0 and r.stdout.startswith("eyJ"):
                _ok(f"SLAuth token mints OK (Kerberos alive). "
                    f"NOTE: This token is NOT accepted by the Databricks "
                    f"workspace API directly — it proves your atlas CLI is "
                    f"healthy and you can mint Atlassian-internal tokens.")
            else:
                _warn(f"slauth returned rc={r.returncode}: "
                      f"{(r.stderr or r.stdout)[:120]}")
        except Exception as e:
            _warn(f"slauth call failed: {e}")
    else:
        _step("atlas CLI not on PATH")

    return None


# ------------------------------------------------------------ phase 3: actual query


METRICS_QUERY = """
SELECT samples_day,
       evaluation_type,
       evaluation_version,
       precision,
       recall,
       f1,
       fpr,
       fnr,
       accuracy,
       total_count,
       predicted_violations_count,
       predicted_safe_count
  FROM collaboration.ai_safety.online_eval_metrics
 WHERE samples_day >= :start_day
 ORDER BY samples_day DESC
"""


def run_metrics_query(host: str,
                      token: str,
                      warehouse_id: Optional[str],
                      days: int) -> int:
    _section("Phase 3 — Query online_eval_metrics (UGC/Metadata-tagged only)")

    if not warehouse_id:
        _warn("--warehouse-id not provided. Listing accessible warehouses:")
        try:
            from databricks.sdk import WorkspaceClient
            os.environ["DATABRICKS_HOST"] = host
            os.environ["DATABRICKS_TOKEN"] = token
            w = WorkspaceClient(host=host, token=token)
            warehouses = list(w.warehouses.list())
            if not warehouses:
                _err("No SQL warehouses visible to this account.")
                return 4
            for wh in warehouses[:10]:
                print(f"     {wh.id:36s}  {wh.name}  ({wh.state})")
            _step("Re-run with --warehouse-id <one of the IDs above>")
            return 4
        except Exception as e:
            _err(f"Cannot list warehouses: {e}")
            return 4

    # Statement Execution API
    import requests
    start_day = (_dt.date.today() - _dt.timedelta(days=days)).isoformat()
    _step(f"Submitting SQL: SELECT ... FROM online_eval_metrics "
          f"WHERE samples_day >= {start_day}")

    resp = requests.post(
        f"{host.rstrip('/')}/api/2.0/sql/statements",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "warehouse_id": warehouse_id,
            "statement": METRICS_QUERY.replace(":start_day",
                                               f"'{start_day}'"),
            "wait_timeout": "30s",
            "format": "JSON_ARRAY",
        },
        timeout=60,
    )
    if resp.status_code != 200:
        _err(f"SQL API HTTP {resp.status_code}: {resp.text[:300]}")
        return 4

    body = resp.json()
    if body.get("status", {}).get("state") != "SUCCEEDED":
        _err(f"Statement state = {body.get('status')}")
        return 4

    cols = [c["name"] for c in body["manifest"]["schema"]["columns"]]
    rows = body.get("result", {}).get("data_array") or []
    _ok(f"Got {len(rows)} rows back.")
    if not rows:
        _warn("No metrics rows in window — daily job may not have run yet.")
        return 0

    # Compact tabular print (no UGC body — only metadata, safe to display)
    widths = [max(len(str(r[i])) for r in rows + [cols]) for i in range(len(cols))]
    print("\n  " + "  ".join(c.ljust(w) for c, w in zip(cols, widths)))
    print("  " + "  ".join("-" * w for w in widths))
    for row in rows:
        print("  " + "  ".join(str(v).ljust(w) for v, w in zip(row, widths)))
    return 0


# ------------------------------------------------------------ phase 4: instructions


def print_unblock_instructions(host: str) -> None:
    _section("Phase 4 — How to unblock (ranked by ease)")
    print(f"""
  Option 1  (3 min, lowest dependency):
    Generate a Databricks Personal Access Token (PAT) in the UI:
       https://{host.replace('https://','').rstrip('/')}/?o=*#user/tokens
    Then export it and re-run:
       export DATABRICKS_HOST="{host}"
       export DATABRICKS_TOKEN="dapi..."
       /opt/homebrew/anaconda3/bin/python {Path(sys.argv[0]).name} \\
           --warehouse-id <your-warehouse-id>

  Option 2  (sanctioned, audit-logged):
    Run via Atlassian ML Studio (atlas ml workflow run).
    Requires writing a workflow descriptor YAML — see §9.2 of
    architecture/cross-cutting/09-data-storage-and-databricks.rst.

  Option 3  (interactive Spark from a laptop):
    pip install 'databricks-connect==<your-cluster-DBR>'
    atlas ml connect configure --use-case <id> --env prod \\
        --workflow-type online-evaluation --dbr-version 14.3

  Option 4  (governance-clean for *raw* prompts):
    File a Trust+/Privacy review. UGC opt-outs and tenant filters are
    enforced in NOTEBOOK CODE, not Databricks RLS — so any read must go
    through the sanctioned `online_eval_workflow.py` path.
""")


# ------------------------------------------------------------ main


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", default="https://atlassian-discover.cloud.databricks.com")
    p.add_argument("--warehouse-id", default=os.environ.get("DATABRICKS_WAREHOUSE_ID"))
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--dry-run", action="store_true",
                   help="Stop after auth discovery; do not call SQL API.")
    args = p.parse_args()

    verify_environment()
    token = discover_databricks_token(args.host)

    if not token:
        _err("\n  No Databricks-issued bearer token available.")
        print_unblock_instructions(args.host)
        return 2

    _ok(f"Using bearer token (len={len(token)}) against {args.host}")

    if args.dry_run:
        _ok("--dry-run: skipping SQL execution.")
        return 0

    return run_metrics_query(args.host, token, args.warehouse_id, args.days)


if __name__ == "__main__":
    sys.exit(main())
