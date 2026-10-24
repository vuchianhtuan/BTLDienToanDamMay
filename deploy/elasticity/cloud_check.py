"""Read-only cloud inventory/preflight and scoped evidence snapshots. No SDK needed."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess


RESOURCE_TYPES = (
    "OS::Octavia::LoadBalancer", "OS::Octavia::Listener", "OS::Octavia::Pool",
    "OS::Octavia::HealthMonitor", "OS::Octavia::PoolMember", "OS::Neutron::Port",
    "OS::Nova::Server", "OS::Heat::AutoScalingGroup", "OS::Heat::ScalingPolicy",
    "OS::Aodh::GnocchiAggregationByResourcesAlarm",
)


def redact(value):
    if isinstance(value, dict):
        return {key: ("[REDACTED]" if any(word in key.lower() for word in
                     ("password", "secret", "token", "credential", "user_data", "alarm_actions"))
                      else redact(child)) for key, child in value.items()}
    if isinstance(value, list):
        return [redact(child) for child in value]
    if isinstance(value, str):
        if "trust+http" in value or "/signal" in value or "AWSAccessKeyId" in value:
            return "[REDACTED action detail]"
        return re.sub(r"(\w+(?:\+\w+)?://)[^\s/@]+:[^\s/@]+@", r"\1[REDACTED]@", value)
    return value


def query(arguments):
    try:
        result = subprocess.run(["openstack", "--os-api-timeout", "30", *arguments, "-f", "json"],
                                capture_output=True, text=True, timeout=45, check=False)
        if result.returncode:
            return {"ok": False, "error": "CLI, authorization, service or resource unavailable"}
        return {"ok": True, "data": json.loads(result.stdout)}
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return {"ok": False, "error": "CLI missing, timed out or returned invalid JSON"}


def collect(args):
    commands = {
        "services": ["catalog", "list"],
        "availability_zones": ["availability", "zone", "list", "--compute"],
        "compute_services": ["compute", "service", "list", "--service", "nova-compute"],
    }
    if args.mode == "snapshot":
        commands = {
            "resources": ["stack", "resource", "list", args.stack, "--nested-depth", "5"],
            "events": ["stack", "event", "list", args.stack, "--nested-depth", "5"],
            "loadbalancer": ["loadbalancer", "show", args.loadbalancer],
            "members": ["loadbalancer", "member", "list", args.pool],
            "loadbalancer_status": ["loadbalancer", "status", "show", args.loadbalancer],
        }
        for label, alarm in (("high_alarm_history", args.high_alarm), ("low_alarm_history", args.low_alarm)):
            if alarm:
                commands[label] = ["alarm-history", "show", alarm]
    report = {"collected_utc": datetime.now(timezone.utc).isoformat(), "mode": args.mode}
    report["checks"] = {name: query(command) for name, command in commands.items()}
    if args.mode == "preflight":
        # Retain only success/failure for schemas; these checks do not prove service health.
        report["resource_types"] = {
            kind: query(["orchestration", "resource", "type", "show", kind])["ok"] for kind in RESOURCE_TYPES
        }
    report["all_queries_succeeded"] = (all(v["ok"] for v in report["checks"].values())
                                         and all(report.get("resource_types", {}).values()))
    return redact(report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preflight", "snapshot"))
    parser.add_argument("--stack")
    parser.add_argument("--loadbalancer")
    parser.add_argument("--pool")
    parser.add_argument("--high-alarm")
    parser.add_argument("--low-alarm")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "snapshot" and not all((args.stack, args.loadbalancer, args.pool)):
        parser.error("snapshot requires --stack, --loadbalancer and --pool")
    report = collect(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Never overwrite evidence from an earlier collection.
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(f'{"QUERIES OK" if report["all_queries_succeeded"] else "INCOMPLETE"}: {args.output}')
    return 0 if report["all_queries_succeeded"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
