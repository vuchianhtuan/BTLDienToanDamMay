"""Offline planning and bounded read-only OpenStack checks. Python stdlib only.

This module deliberately has no create/update/delete/signal operations.
"""
import argparse
import base64
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

HERE = Path(__file__).resolve().parent
TEMPLATES = ("baseline-lb.json", "app-member.json", "autoscale.json")
ID_KEYS = ("vip_subnet_id", "member_subnet_id", "network_id", "image_id", "app_security_group_id")
TEXT_KEYS = ("flavor_id", "key_name", "az1", "az2", "container_image")
NUMBERS = {"vcpus": (1, 16), "ram_mb": (256, 32768), "max_per_zone": (1, 2),
           "budget_app_vms": (2, 4), "cooldown": (60, 3600), "granularity": (1, 3600),
           "evaluation_periods": (1, 10)}
CONFIG_KEYS = set(ID_KEYS + TEXT_KEYS) | set(NUMBERS) | {
    "client_cidr", "app1_ip", "app2_ip", "cpu_high_percent", "cpu_low_percent"}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_new(path, value, private=False):
    """Never overwrite reports/secrets by accident; fail before printing their contents."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600 if private else 0o644)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def lint_templates(root=HERE):
    """Check references/nested arguments and security invariants, not the Heat API schema."""
    errors = []
    documents = {name: read_json(root / name) for name in TEMPLATES}
    for name, doc in documents.items():
        params, resources = doc["parameters"], doc["resources"]
        for node in walk(doc):
            for fn in ("get_param", "get_resource", "get_attr"):
                if fn not in node:
                    continue
                value = node[fn]
                key = value[0] if isinstance(value, list) else value
                valid = params if fn == "get_param" else resources
                if key not in valid and not (fn == "get_param" and key == "OS::stack_id"):
                    errors.append(f"{name}: unresolved {fn} {key}")
            kind = node.get("type", "")
            if kind.endswith(".json"):
                nested = documents.get(kind)
                if nested is None:
                    errors.append(f"{name}: missing nested template {kind}")
                    continue
                args = node.get("properties", {})
                required = {k for k, v in nested["parameters"].items() if "default" not in v}
                if not required <= args.keys() or not args.keys() <= nested["parameters"].keys():
                    errors.append(f"{name}: nested parameters do not match {kind}")
            if "FloatingIP" in kind or kind == "OS::Neutron::SecurityGroup":
                errors.append(f"{name}: unexpected public networking/security-group write")
    main = documents["autoscale.json"]
    groups = [r for r in main["resources"].values() if r["type"] == "OS::Heat::AutoScalingGroup"]
    if len(groups) != 2 or any(g["properties"]["min_size"] != 1 for g in groups):
        errors.append("autoscale: keep one minimum App VM in each of two groups")
    for i in (1, 2):
        props = main["resources"][f"group{i}"]["properties"]["resource"]["properties"]
        if props["availability_zone"] != {"get_param": f"az{i}"}:
            errors.append("autoscale: wrong AZ assignment")
        for direction in ("in", "out"):
            alarm = main["resources"][f"cpu_{direction}{i}"]
            if alarm.get("condition") != "alarms_enabled" or alarm["properties"]["metric"] != "cpu":
                errors.append("autoscale: alarms must be opt-in with cumulative cpu metric")
    if main["parameters"]["enable_alarms"]["default"] is not False:
        errors.append("autoscale: alarms must default to disabled")
    return errors


def validate_config(config):
    errors = []
    unknown = set(config) - CONFIG_KEYS
    if unknown:
        errors.append("Unknown configuration fields: " + ", ".join(sorted(unknown)))
    for key in ID_KEYS:
        try:
            uuid.UUID(config.get(key, ""))
        except (ValueError, TypeError, AttributeError):
            errors.append(f"{key}: needs a real UUID")
    for key in TEXT_KEYS:
        value = config.get(key)
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/@+-]{0,254}", value) or "CHANGE_ME" in value:
            errors.append(f"{key}: missing or invalid value")
    if config.get("az1") == config.get("az2"):
        errors.append("az1 and az2 must differ")
    for key, (low, high) in NUMBERS.items():
        value = config.get(key)
        if type(value) is not int or not low <= value <= high:
            errors.append(f"{key}: integer required in [{low}, {high}]")
    percentages = [config.get(k) for k in ("cpu_low_percent", "cpu_high_percent")]
    if not all(type(v) in (float, int) and 0 < v < 100 for v in percentages) or not percentages[0] < percentages[1]:
        errors.append("CPU thresholds must satisfy 0 < low < high < 100")
    try:
        cidr = ipaddress.ip_network(config.get("client_cidr", ""), strict=True)
        if cidr.version != 4 or cidr.prefixlen == 0:
            raise ValueError()
    except (ValueError, TypeError):
        errors.append("client_cidr: explicit restricted IPv4 CIDR required")
    for key in ("app1_ip", "app2_ip"):
        try:
            address = ipaddress.IPv4Address(config.get(key, ""))
            if not any(address in ipaddress.ip_network(net) for net in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")):
                raise ValueError()
        except (ValueError, TypeError):
            errors.append(f"{key}: private IPv4 required")
    if config.get("app1_ip") == config.get("app2_ip"):
        errors.append("App member addresses must differ")
    if not errors:
        if 2 * config["max_per_zone"] > config["budget_app_vms"]:
            errors.append("Maximum App VM count exceeds budget_app_vms")
        if config["cooldown"] < config["granularity"]:
            errors.append("Cooldown must cover at least one metric granularity")
    return errors


def plan(config):
    errors = validate_config(config)
    if errors:
        raise ValueError("; ".join(errors))
    count = 2 * config["max_per_zone"]
    return {
        "status": "OFFLINE_PLAN_ONLY", "cloud_validation": "NOT AVAILABLE",
        "baseline_app_vms": 2, "maximum_app_vms": count,
        "maximum_app_vcpus": count * config["vcpus"],
        "maximum_app_ram_mb": count * config["ram_mb"],
        "excluded_from_budget": ["existing manually deployed App VMs", "database VM", "Octavia amphora VM(s)", "controller and compute services"],
        "cpu_unit": "nanoseconds/second", "cpu_aggregation": "rate:mean",
        "cpu_high_rate": config["cpu_high_percent"] / 100 * config["vcpus"] * 1_000_000_000,
        "cpu_low_rate": config["cpu_low_percent"] / 100 * config["vcpus"] * 1_000_000_000,
        "metric_window_seconds": config["granularity"] * config["evaluation_periods"],
        "automatic_alarms_enabled": False,
        "remaining_checks": ["Heat API schema and nested templates", "image boot and metadata service",
                             "AZ capacity and quotas", "restricted security groups and routes",
                             "Swift/DB readiness from both AZs", "Gnocchi grouping, archive policy and actual CPU measures"],
    }


def parse_app_env(text):
    """Accept Docker dotenv key=value, preserving bytes; reject local storage and placeholders."""
    values = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key) or key in values:
            raise ValueError("App env must contain unique uppercase KEY=value lines")
        values[key] = value
    required = ("DATABASE_URL", "APP_API_KEY", "OS_AUTH_URL", "OS_APPLICATION_CREDENTIAL_ID",
                "OS_APPLICATION_CREDENTIAL_SECRET", "SWIFT_CONTAINER")
    if any(not values.get(k) or any(marker in values[k] for marker in ("CHANGE_ME", "PRIVATE_IP")) for k in required):
        raise ValueError("App env has missing required values or placeholders")
    if values.get("STORAGE_BACKEND") != "swift" or not values["DATABASE_URL"].startswith("postgresql+psycopg://"):
        raise ValueError("Elastic App VMs require shared Swift and PostgreSQL")
    return values


def environments(config, env_text):
    info = plan(config)
    parse_app_env(env_text)
    baseline = {k: config[k] for k in ("vip_subnet_id", "member_subnet_id", "client_cidr", "app1_ip", "app2_ip")}
    names = read_json(HERE / "autoscale.json")["parameters"]
    elastic = {k: config[k] for k in names if k in config}
    elastic.update(app_env_b64=base64.b64encode(env_text.encode("utf-8")).decode("ascii"),
                   enable_alarms=False, cpu_high_rate=info["cpu_high_rate"], cpu_low_rate=info["cpu_low_rate"])
    return {"parameters": baseline}, {"parameters": elastic}


def cli_json(args, runner=subprocess.run):
    """Only fixed calls from probe/collect; never publish stderr or arbitrary CLI stdout."""
    try:
        process = runner(["openstack", *args, "-f", "json"], capture_output=True, text=True,
                         encoding="utf-8", timeout=30, check=False)
        if process.returncode:
            return None
        return json.loads(process.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


def probe(config, query=cli_json):
    plan(config)
    checks = {}
    services = query(["catalog", "list"])
    types = {row.get("Type", row.get("type")) for row in services or [] if isinstance(row, dict)} if isinstance(services, list) else set()
    for name in ("orchestration", "load-balancer", "metric", "alarming"):
        checks[f"service:{name}"] = "FOUND" if name in types else "NOT AVAILABLE"
    azs = query(["availability", "zone", "list", "--compute"])
    az_names = {row.get("Zone Name", row.get("zoneName")) for row in azs or [] if isinstance(row, dict)} if isinstance(azs, list) else set()
    for key in ("az1", "az2"):
        checks[key] = "FOUND" if config[key] in az_names else "NOT AVAILABLE"
    commands = {
        "image": ["image", "show", config["image_id"]],
        "flavor": ["flavor", "show", config["flavor_id"]],
        "network": ["network", "show", config["network_id"]],
        "subnet": ["subnet", "show", config["member_subnet_id"]],
        "vip_subnet": ["subnet", "show", config["vip_subnet_id"]],
        "security_group": ["security", "group", "show", config["app_security_group_id"]],
        "keypair": ["keypair", "show", config["key_name"]],
    }
    for name, cmd in commands.items():
        value = query(cmd)
        value = value if isinstance(value, dict) else None
        checks[name] = "FOUND" if isinstance(value, dict) and value else "NOT AVAILABLE"
        if name == "image" and value:
            checks["image_active"] = "MATCH" if value.get("status") == "active" else "NOT AVAILABLE"
        if name == "flavor" and value:
            checks["flavor_size"] = "MATCH" if (value.get("vcpus") == config["vcpus"] and value.get("ram") == config["ram_mb"]) else "MISMATCH"
        if name == "subnet" and value:
            checks["subnet_network"] = "MATCH" if value.get("network_id") == config["network_id"] else "MISMATCH"
    required_types = {node["type"] for name in TEMPLATES for node in walk(read_json(HERE / name))
                      if isinstance(node.get("type"), str) and node["type"].startswith("OS::")}
    for kind in sorted(required_types):
        checks[f"resource:{kind}"] = "FOUND" if query(["orchestration", "resource", "type", "show", kind]) else "NOT AVAILABLE"
    return {"status": "READ_ONLY_DISCOVERY", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "checks": checks, "deployment_readiness": "NOT VERIFIED",
            "notes": "FOUND proves discovery only. It does not prove quotas, routing, boot, metric data or alarm delivery."}


def safe_rows(value, fields):
    """Only known non-secret fields survive; alarm action URLs and parameters are excluded."""
    rows = value if isinstance(value, list) else [value] if isinstance(value, dict) else []
    return [{k: row[k] for k in fields if k in row and isinstance(row[k], (str, int, float, bool, type(None)))}
            for row in rows if isinstance(row, dict)]


def collect(stack, lb, pool, query=cli_json):
    for value in (stack, lb, pool):
        uuid.UUID(value)  # Use exact IDs, never ambiguous names or options.
    calls = {
        "resources": (["stack", "resource", "list", stack, "--nested-depth", "3"],
                      ("resource_name", "resource_type", "resource_status", "physical_resource_id", "updated_time")),
        "events": (["stack", "event", "list", stack],
                   ("resource_name", "resource_status", "event_time", "id")),
        "loadbalancer": (["loadbalancer", "show", lb],
                         ("id", "vip_address", "provisioning_status", "operating_status")),
        "members": (["loadbalancer", "member", "list", pool],
                    ("id", "address", "protocol_port", "provisioning_status", "operating_status")),
    }
    report = {"status": "READ_ONLY_SNAPSHOT", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "stack_id": stack, "loadbalancer_id": lb, "pool_id": pool, "checks": {}}
    for name, (cmd, fields) in calls.items():
        value = query(cmd)
        report["checks"][name] = {"status": "FOUND" if value is not None else "NOT AVAILABLE",
                                  "rows": safe_rows(value, fields)}
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("lint")
    for action in ("plan", "build", "probe"):
        item = sub.add_parser(action)
        item.add_argument("--config", required=True)
        item.add_argument("--out", required=True)
        if action == "build":
            item.add_argument("--app-env", required=True)
    item = sub.add_parser("collect")
    for key in ("stack", "lb", "pool", "out"):
        item.add_argument(f"--{key}", required=True)
    args = parser.parse_args(argv)
    try:
        errors = lint_templates()
        if errors:
            raise ValueError("; ".join(errors))
        if args.action == "lint":
            print("PASS: references, nested contracts and offline invariants (not Heat API validation)")
            return 0
        if args.action == "collect":
            write_new(args.out, collect(args.stack, args.lb, args.pool))
        else:
            config = read_json(args.config)
            if args.action == "build":
                baseline, elastic = environments(config, Path(args.app_env).read_text(encoding="utf-8-sig"))
                out = Path(args.out)
                if out.exists():
                    raise ValueError("Build output directory must be new")
                write_new(out / "baseline.env.json", baseline)
                write_new(out / "autoscale.env.json", elastic, private=True)
                write_new(out / "plan.json", plan(config))
            else:
                write_new(args.out, plan(config) if args.action == "plan" else probe(config))
        print("Wrote local result; no cloud resources changed.")
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        # Never print input values: this command can read a secret dotenv file.
        print("Cannot complete: check config fields, UUIDs, distinct AZs/IPs, CPU limits, shared storage and new output path. No input/secret values printed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
