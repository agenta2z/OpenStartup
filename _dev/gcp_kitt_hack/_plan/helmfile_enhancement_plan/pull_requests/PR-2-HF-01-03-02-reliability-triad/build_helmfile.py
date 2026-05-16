#!/usr/bin/env python3
"""
Build the modified helmfile.yaml for PR-2 by applying targeted line-based edits to
the upstream main version (preserves comments + ordering, unlike YAML round-tripping).

Inputs:  upstream-main-helmfile.yaml (committed snapshot)
Outputs: ../helmfile.yaml (modified)

Edits applied:
  1. HF-03 redis: change `replica.replicaCount: 1` to `2`
  2. HF-03 temporal: change `server.replicaCount: 1` to `2`
  3. HF-03 web: change `web.replicaCount: 1` to `2`
  4. HF-01: insert per-role probe blocks under server.frontend / .history / .matching / .worker
     (these are NOT under top-level frontend:/history:/etc. -- those are silently dropped today)
     The chart resolves $.Values.server.<service>.{liveness,readiness,startup}Probe
  5. HF-02: insert a new postsync hook to apply temporal-pdbs.yaml
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
UPSTREAM = HERE / "upstream-main-helmfile.yaml"
OUTPUT = HERE / "helmfile.yaml"

PROBES_PER_ROLE = """\
            # HF-01: probes added to prevent kubelet from killing pods during
            # the 60-120s Cassandra schema-verification phase. startupProbe
            # gives a 5-min budget; livenessProbe is suppressed until startup succeeds.
            startupProbe:
              tcpSocket:
                port: rpc
              initialDelaySeconds: 30
              periodSeconds: 10
              failureThreshold: 30      # 30 * 10s = 5 min budget
              timeoutSeconds: 5
            livenessProbe:
              tcpSocket:
                port: rpc
              periodSeconds: 30
              failureThreshold: 3
              timeoutSeconds: 5
            readinessProbe:
              tcpSocket:
                port: rpc
              periodSeconds: 10
              failureThreshold: 3
              timeoutSeconds: 5
"""

def main():
    src = UPSTREAM.read_text()

    # --- Edit 1: redis replica.replicaCount: 1 -> 2 ---
    # Block: 'replica:\n          replicaCount: 1'
    old = "        replica:\n          replicaCount: 1"
    new = "        replica:\n          # HF-03: 1 -> 2 for HA. PDB minAvailable=1 ensures node-drain safety.\n          replicaCount: 2"
    if src.count(old) != 1:
        sys.exit(f"FATAL: redis replica block found {src.count(old)} times, expected 1")
    src = src.replace(old, new, 1)

    # --- Edit 2: temporal server.replicaCount: 1 -> 2 ---
    # Block: '- server:\n          replicaCount: 1'
    old = "      - server:\n          replicaCount: 1"
    new = "      - server:\n          # HF-03: 1 -> 2 for HA. Affects all 4 server roles.\n          replicaCount: 2"
    if src.count(old) != 1:
        sys.exit(f"FATAL: server.replicaCount block found {src.count(old)} times, expected 1")
    src = src.replace(old, new, 1)

    # --- Edit 3: web.replicaCount: 1 -> 2 ---
    old = "        web:\n          enabled: true\n          replicaCount: 1"
    new = "        web:\n          enabled: true\n          # HF-03: 1 -> 2 for HA\n          replicaCount: 2"
    if src.count(old) != 1:
        sys.exit(f"FATAL: web.replicaCount block found {src.count(old)} times, expected 1")
    src = src.replace(old, new, 1)

    # --- Edit 4: insert per-role probes under server.frontend/.history/.matching/.worker ---
    # The chart's per-role values live at $.Values.server.<role>. The current helmfile.yaml
    # uses a FLAT layout (matching:/history:/frontend:/worker: at the same indent as server:),
    # which is a chart-mismatch -- the chart silently drops those keys.
    #
    # We nest the probe blocks UNDER server.<role> via injecting them between the
    # extraEnv block end and the matching/history/frontend/worker top-level blocks.
    #
    # The cleanest deterministic insertion: append a new `server.frontend/history/matching/worker`
    # nested structure right BEFORE the existing flat `matching:` block.
    # Anchor: the line "        matching:\n          podAnnotations:" appears once.
    # Per-role probe blocks under server.<role> at column 10 (server: is at column 8 inside values list item)
    # CRITICAL: These MUST be at column 10 (under server:) not column 8 (peer of server:).
    # The chart resolves $.Values.server.<role>.{startup,liveness,readiness}Probe.
    nested_role_blocks = (
        "          # HF-01: per-role probe overrides (correctly nested under server.<role>).\n"
        "          # NOTE: the existing top-level 'matching:'/'history:'/'frontend:'/'worker:'\n"
        "          # blocks (peers of server: at column 8) are LATENT-BROKEN -- the chart silently\n"
        "          # drops keys that aren't under server. Their podAnnotations were never applied.\n"
        "          # Fix tracked separately. This PR adds the correctly-nested probes.\n"
        "          frontend:\n" + PROBES_PER_ROLE +
        "          history:\n" + PROBES_PER_ROLE +
        "          matching:\n" + PROBES_PER_ROLE +
        "          worker:\n" + PROBES_PER_ROLE
    )
    # Anchor: the indented "matching:" block sitting at column 8 (peer of server)
    # Actually that block is at indent 8 under values. The CHART expects values at indent
    # 8 too (the chart values root is at column 6 due to "- server:" being one of values entries).
    # Wait -- helm values are passed as a map. Let me re-read: the structure is
    #     values:
    #       - server: ...
    #     <whatever else is at the same indent as 'server:' is ALSO a values key>
    # So the existing top-level "matching:" IS a values key, but the chart looks at
    # $.Values.server.matching, not $.Values.matching. So those flat keys are dropped.
    # By adding "frontend:/history:/matching:/worker:" under server: we get the right path.

    # Insert nested per-role probes INSIDE the server: dict at column 10.
    # Anchor: the last server.config child line, immediately before peer 'matching:' at column 8.
    # This places frontend/history/matching/worker keys at column 10 = under server: (correct chart path).
    anchor = "              maxWorkflowExecutionHistoryCount: 100000\n        matching:"
    if src.count(anchor) != 1:
        sys.exit(f"FATAL: server-config-end anchor found {src.count(anchor)} times, expected 1")
    new_anchor = "              maxWorkflowExecutionHistoryCount: 100000\n" + nested_role_blocks + "        matching:"
    src = src.replace(anchor, new_anchor, 1)

    # --- Edit 5: insert postsync hook for temporal-pdbs.yaml ---
    # Anchor: the "Fix Cassandra gossip configuration" hook (last hook in the list)
    anchor = (
        "      # Fix Cassandra gossip configuration (seed nodes and JVM options)\n"
        "      - events: [\"postsync\"]\n"
        "        showlogs: true\n"
        "        command: kubectl\n"
        "        args:\n"
        "          - apply\n"
        "          - -f\n"
        "          - fix-cassandra-gossip-config-job.yaml"
    )
    new = (
        "      # HF-02: PodDisruptionBudgets to prevent voluntary eviction taking down\n"
        "      # the only pod of any Temporal role during routine node drains.\n"
        "      - events: [\"postsync\"]\n"
        "        showlogs: true\n"
        "        command: kubectl\n"
        "        args:\n"
        "          - apply\n"
        "          - -f\n"
        "          - temporal-pdbs.yaml\n"
        + anchor
    )
    if src.count(anchor) != 1:
        sys.exit(f"FATAL: gossip-hook anchor found {src.count(anchor)} times, expected 1")
    src = src.replace(anchor, new, 1)

    OUTPUT.write_text(src)
    print(f"Wrote {OUTPUT} ({len(src)} bytes, {src.count(chr(10))+1} lines)")
    print(f"Edits applied: 5 (3 replicaCount, 1 nested probes block, 1 postsync hook)")

if __name__ == "__main__":
    main()
