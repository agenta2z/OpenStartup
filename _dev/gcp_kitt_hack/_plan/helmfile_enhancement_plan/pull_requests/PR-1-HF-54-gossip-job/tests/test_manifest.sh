#!/usr/bin/env bash
# Manifest structural / schema / security validation for fix-cassandra-gossip-config-job.yaml.
# Pure bash + python3 + pyyaml. No cluster, no Docker, no third-party tools.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="${MANIFEST:-$HERE/../fix-cassandra-gossip-config-job.yaml}"

GREEN=$'\033[0;32m'; RED=$'\033[0;31m'; NC=$'\033[0m'
pass=0; fail=0

run_test() {
  local name="$1"; shift
  local out
  if out="$("$@" 2>&1)"; then
    echo "  ${GREEN}PASS${NC} $name"
    pass=$((pass+1))
  else
    echo "  ${RED}FAIL${NC} $name"
    echo "      $out" | sed 's/^/      /'
    fail=$((fail+1))
  fi
}

# ---------------------------------------------------------------------------
# T-M01: YAML parses and contains exactly 5 documents
# ---------------------------------------------------------------------------
test_m01_yaml_parses() {
  python3 - <<PYEOF
import yaml, sys
docs = [d for d in yaml.safe_load_all(open("$MANIFEST")) if d]
assert len(docs) == 5, f"expected 5 docs, got {len(docs)}"
PYEOF
}
run_test "T-M01 YAML parses with exactly 5 documents" test_m01_yaml_parses

# ---------------------------------------------------------------------------
# T-M02: Resource kinds are exactly the expected set
# ---------------------------------------------------------------------------
test_m02_kinds() {
  python3 - <<PYEOF
import yaml
docs = [d for d in yaml.safe_load_all(open("$MANIFEST")) if d]
kinds = sorted(d["kind"] for d in docs)
expected = ["ConfigMap", "Job", "Role", "RoleBinding", "ServiceAccount"]
assert kinds == expected, f"got {kinds}, expected {expected}"
PYEOF
}
run_test "T-M02 Kinds = [SA, Role, RoleBinding, ConfigMap, Job]" test_m02_kinds

# ---------------------------------------------------------------------------
# T-M03: ServiceAccount/Role/RoleBinding wired correctly
# ---------------------------------------------------------------------------
test_m03_rbac_wiring() {
  python3 - <<PYEOF
import yaml
docs = {d["kind"]: d for d in yaml.safe_load_all(open("$MANIFEST")) if d}
sa = docs["ServiceAccount"]
role = docs["Role"]
rb = docs["RoleBinding"]
job = docs["Job"]
# RoleBinding subject must equal SA name + namespace
subj = rb["subjects"][0]
assert subj["kind"] == "ServiceAccount", f"subject kind: {subj['kind']}"
assert subj["name"] == sa["metadata"]["name"], f"subject name {subj['name']} != SA {sa['metadata']['name']}"
assert subj["namespace"] == sa["metadata"]["namespace"], f"subject ns mismatch"
# RoleBinding roleRef must match Role name
assert rb["roleRef"]["kind"] == "Role"
assert rb["roleRef"]["name"] == role["metadata"]["name"], f"roleRef {rb['roleRef']['name']} != Role {role['metadata']['name']}"
# Job must use the SA
sa_used = job["spec"]["template"]["spec"]["serviceAccountName"]
assert sa_used == sa["metadata"]["name"], f"Job SA {sa_used} != {sa['metadata']['name']}"
PYEOF
}
run_test "T-M03 RBAC wiring (SA <-> RoleBinding <-> Role <-> Job) is consistent" test_m03_rbac_wiring

# ---------------------------------------------------------------------------
# T-M04: Role has exactly the minimum required permissions (no over-grant)
# ---------------------------------------------------------------------------
test_m04_role_minimal() {
  python3 - <<PYEOF
import yaml
docs = {d["kind"]: d for d in yaml.safe_load_all(open("$MANIFEST")) if d}
role = docs["Role"]
# Required: get/list/patch on statefulsets in apps; get/list/delete on pods; get on pods/log
have = {(rule.get("apiGroups", [""])[0], r, v)
        for rule in role["rules"] for r in rule["resources"] for v in rule["verbs"]}
required = {
    ("apps", "statefulsets", "get"),
    ("apps", "statefulsets", "patch"),
    ("",     "pods",         "get"),
    ("",     "pods",         "delete"),
}
missing = required - have
assert not missing, f"missing required perms: {missing}"
# Defensive: forbid wildcard verbs on any resource
for rule in role["rules"]:
    assert "*" not in rule["verbs"], f"wildcard verb forbidden: {rule}"
# Defensive: must NOT be a ClusterRole (must be namespaced)
assert role["kind"] == "Role" and role["metadata"].get("namespace"), "must be namespaced Role"
PYEOF
}
run_test "T-M04 Role has minimum permissions, no wildcards, namespaced" test_m04_role_minimal

# ---------------------------------------------------------------------------
# T-M05: Container image is pinned (NOT :latest, has explicit version tag)
# ---------------------------------------------------------------------------
test_m05_image_pinned() {
  python3 - <<PYEOF
import yaml, re
docs = {d["kind"]: d for d in yaml.safe_load_all(open("$MANIFEST")) if d}
img = docs["Job"]["spec"]["template"]["spec"]["containers"][0]["image"]
assert ":" in img, f"image not tagged: {img}"
tag = img.rsplit(":", 1)[1]
assert tag != "latest", f"image uses :latest: {img}"
# Defensive: tag should look like a real version (digits + dots) or sha256
assert re.match(r"^(\d+\.\d+(\.\d+)?(-\w+)?|sha256:[0-9a-f]{64})$", tag), f"unusual tag: {tag}"
PYEOF
}
run_test "T-M05 Image pinned to explicit version (not :latest)" test_m05_image_pinned

# ---------------------------------------------------------------------------
# T-M06: SecurityContext is hardened
# ---------------------------------------------------------------------------
test_m06_securitycontext_hardened() {
  python3 - <<PYEOF
import yaml
docs = {d["kind"]: d for d in yaml.safe_load_all(open("$MANIFEST")) if d}
job = docs["Job"]
# Pod-level
pod_sc = job["spec"]["template"]["spec"].get("securityContext", {})
assert pod_sc.get("runAsNonRoot") is True, "pod runAsNonRoot must be True"
assert pod_sc.get("seccompProfile", {}).get("type") == "RuntimeDefault", "pod seccompProfile must be RuntimeDefault"
# Container-level (the kubectl container)
c = job["spec"]["template"]["spec"]["containers"][0]
csc = c.get("securityContext", {})
assert csc.get("runAsNonRoot") is True, "container runAsNonRoot must be True"
assert csc.get("readOnlyRootFilesystem") is True, "container readOnlyRootFilesystem must be True"
assert csc.get("allowPrivilegeEscalation") is False, "container allowPrivilegeEscalation must be False"
caps = csc.get("capabilities", {}).get("drop", [])
assert "ALL" in caps, f"container must drop ALL capabilities, got drop={caps}"
PYEOF
}
run_test "T-M06 SecurityContext hardened (runAsNonRoot, readOnlyRootFs, drop ALL, seccomp)" test_m06_securitycontext_hardened

# ---------------------------------------------------------------------------
# T-M07: Job lifecycle bounded (TTL, backoffLimit, activeDeadlineSeconds)
# ---------------------------------------------------------------------------
test_m07_job_bounded() {
  python3 - <<PYEOF
import yaml
docs = {d["kind"]: d for d in yaml.safe_load_all(open("$MANIFEST")) if d}
spec = docs["Job"]["spec"]
ttl = spec.get("ttlSecondsAfterFinished")
backoff = spec.get("backoffLimit")
deadline = spec.get("activeDeadlineSeconds")
assert isinstance(ttl, int) and 0 < ttl <= 3600, f"ttlSecondsAfterFinished out of range: {ttl}"
assert isinstance(backoff, int) and 0 < backoff <= 5, f"backoffLimit out of range: {backoff}"
assert isinstance(deadline, int) and 60 <= deadline <= 7200, f"activeDeadlineSeconds out of range: {deadline}"
# RestartPolicy must be Never (default would be OnFailure which mixes badly with backoffLimit)
rp = docs["Job"]["spec"]["template"]["spec"].get("restartPolicy")
assert rp == "Never", f"restartPolicy must be Never, got {rp}"
PYEOF
}
run_test "T-M07 Job lifecycle bounded (TTL/backoffLimit/activeDeadlineSeconds + restartPolicy=Never)" test_m07_job_bounded

# ---------------------------------------------------------------------------
# T-M08: ConfigMap volume mounts at the path the Job command references
# ---------------------------------------------------------------------------
test_m08_volume_mount_paths_match() {
  python3 - <<PYEOF
import yaml
docs = {d["kind"]: d for d in yaml.safe_load_all(open("$MANIFEST")) if d}
cm = docs["ConfigMap"]
assert "patch.sh" in cm["data"], f"ConfigMap missing patch.sh key: {list(cm['data'].keys())}"
job_spec = docs["Job"]["spec"]["template"]["spec"]
# Find script volume sourced from this ConfigMap
script_vol = next((v for v in job_spec["volumes"]
                   if v.get("configMap", {}).get("name") == cm["metadata"]["name"]), None)
assert script_vol, f"Job has no volume referencing ConfigMap {cm['metadata']['name']}"
# Find the mount for it
c = job_spec["containers"][0]
mount = next((m for m in c["volumeMounts"] if m["name"] == script_vol["name"]), None)
assert mount, f"container has no volumeMount for {script_vol['name']}"
# Job command must reference a path under the mount
cmd = c["command"]
script_path_in_cmd = next((arg for arg in cmd if arg.endswith("patch.sh")), None)
assert script_path_in_cmd, f"command does not invoke patch.sh: {cmd}"
assert script_path_in_cmd.startswith(mount["mountPath"]), \
    f"script path {script_path_in_cmd} not under mount path {mount['mountPath']}"
PYEOF
}
run_test "T-M08 ConfigMap mount path matches Job command's script path" test_m08_volume_mount_paths_match

# ---------------------------------------------------------------------------
echo
if [[ $fail -eq 0 ]]; then
  echo "${GREEN}test_manifest.sh: $pass/$pass PASS${NC}"
  exit 0
else
  echo "${RED}test_manifest.sh: $pass passed, $fail failed${NC}"
  exit 1
fi
