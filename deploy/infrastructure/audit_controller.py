"""Read-only TV1 audit. Run as stack on the existing Controller, no secret output.

Uses the local openrc without printing credentials. No resources are mutated.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess


def run(args, cwd=None):
    try:
        result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=45)
        if result.returncode:
            return {"ok": False, "error": "unavailable, permission denied or command failed"}
        return {"ok": True, "output": result.stdout.strip()}
    except (OSError, subprocess.TimeoutExpired):
        return {"ok": False, "error": "command unavailable or timed out"}


def cloud(command, directory):
    # command is built from the fixed allowlist below, never user-supplied shell text.
    result = run(["bash", "-c", "set +x; source ./openrc admin admin >/dev/null 2>&1 && exec openstack " + command + " -f json"], cwd=directory)
    if result["ok"]:
        try:
            result = {"ok": True, "data": json.loads(result["output"])}
        except ValueError:
            result = {"ok": False, "error": "invalid CLI response"}
    return result


def collect(directory):
    local = {
        "hostname": ["hostname"], "os": ["lsb_release", "-ds"],
        "memory": ["free", "-h"], "disk": ["df", "-h", "/"],
        "addresses": ["ip", "-br", "addr"], "routes": ["ip", "route"],
        "kvm": ["ls", "-l", "/dev/kvm"],
        "vpn_addresses": ["tailscale", "ip", "-4"],
        "network_service": ["systemctl", "is-active", "tv1-lab-network.service"],
    }
    commands = {
        "compute_services": "compute service list --service nova-compute",
        "hypervisors": "hypervisor list", "availability_zones": "availability zone list --compute",
        "aggregates": "aggregate list", "network_agents": "network agent list",
        "networks": "network list", "subnets": "subnet list", "routers": "router list",
    }
    report = {"collected_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "read-only; no VM boot, connectivity or two-AZ proof",
              "local": {key: run(value) for key, value in local.items()},
              "cloud": {key: cloud(value, directory) for key, value in commands.items()}}
    report["source_revisions"] = {}
    for component in ("devstack", "nova", "neutron", "placement", "requirements"):
        report["source_revisions"][component] = run([
            "git", "-C", str(directory.parent / component), "log", "-1", "--format=%H %cs"])
    checks = list(report["local"].values()) + list(report["cloud"].values()) + list(report["source_revisions"].values())
    report["all_queries_succeeded"] = all(item["ok"] for item in checks)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--devstack", type=Path, default=Path("/opt/stack/devstack"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not (args.devstack / "openrc").is_file():
        parser.error("Run on Controller as stack; openrc must exist")
    report = collect(args.devstack)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Never overwrite prior evidence; file contains internal addresses, not credentials.
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    print("Audit saved. Review unavailable queries and results; this is not a deployment check.")
    return 0 if report["all_queries_succeeded"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
