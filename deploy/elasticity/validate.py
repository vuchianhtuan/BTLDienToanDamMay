"""Offline template/interface checks, not a replacement for Heat validation."""
import argparse
import ipaddress
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise ValueError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def read_yaml(path):
    return yaml.load(Path(path).read_text(encoding="utf-8"), Loader=UniqueLoader)


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def check_templates(directory=ROOT / "templates"):
    templates = {p.name: read_yaml(p) for p in directory.glob("*.yaml")}
    if not templates:
        raise ValueError("No templates found")
    for name, template in templates.items():
        params, resources = template.get("parameters", {}), template["resources"]
        if not isinstance(template.get("heat_template_version"), str):
            raise ValueError(f"{name}: quote heat_template_version")
        for entry in walk(template):
            if "get_param" in entry:
                param = entry["get_param"]
                first = param[0] if isinstance(param, list) else param
                if first not in params and first not in {"OS::stack_id", "OS::stack_name", "OS::project_id"}:
                    raise ValueError(f"{name}: unknown parameter {first}")
            if "get_resource" in entry and entry["get_resource"] not in resources:
                raise ValueError(f"{name}: unknown resource {entry['get_resource']}")
            if "get_attr" in entry:
                target, attr, *_ = entry["get_attr"]
                if target not in resources:
                    raise ValueError(f"{name}: unknown attribute target {target}")
                kind = resources[target]["type"]
                if kind in templates and attr not in templates[kind].get("outputs", {}):
                    raise ValueError(f"{name}: unknown nested output {kind}.{attr}")
            kind = entry.get("type", "")
            if isinstance(kind, str) and kind.endswith(".yaml"):
                if kind not in templates:
                    raise ValueError(f"{name}: missing nested template {kind}")
                child_params = templates[kind].get("parameters", {})
                supplied = entry.get("properties", {})
                unknown = set(supplied) - set(child_params)
                missing = {k for k, v in child_params.items() if "default" not in v} - set(supplied)
                if unknown or missing:
                    raise ValueError(f"{name}: invalid {kind} interface: unknown={unknown}, missing={missing}")
    return templates


def check_environment(path, kind, bootstrap=None):
    template = read_yaml(ROOT / "templates" / ("lb-existing.yaml" if kind == "lb" else "autoscaling.yaml"))
    parameters = read_yaml(path).get("parameters", {})
    expected = template["parameters"]
    unknown = set(parameters) - set(expected)
    required = {key for key, value in expected.items() if "default" not in value}
    if kind == "autoscaling":
        required.discard("bootstrap_user_data")
    if unknown or required - set(parameters):
        raise ValueError("Environment has unknown or missing parameters")
    if any("CHANGE_ME" in str(value) for value in parameters.values()):
        raise ValueError("Replace all CHANGE_ME values before deployment")
    if kind == "lb":
        a, b = (ipaddress.ip_address(parameters[key]) for key in ("backend_a", "backend_b"))
        if a == b or a.version != b.version:
            raise ValueError("Backends must be different addresses of the same IP version")
        if a.is_unspecified or b.is_unspecified or a.is_loopback or b.is_loopback:
            raise ValueError("Backends must be routable app addresses")
    else:
        if parameters["az_a"] == parameters["az_b"]:
            raise ValueError("Use two distinct availability zones")
        if not parameters["threshold_low"] < parameters["threshold_high"]:
            raise ValueError("threshold_low must be below threshold_high")
        if not isinstance(parameters.get("alarms_enabled", False), bool):
            raise ValueError("alarms_enabled must be a YAML boolean")
        if parameters["granularity"] < 1 or parameters.get("evaluation_periods", 3) < 1:
            raise ValueError("Metric granularity/periods must be positive")
        if parameters.get("cooldown", 300) < 60:
            raise ValueError("Cooldown must be at least 60 seconds")
        if "bootstrap_user_data" in parameters:
            raise ValueError("Supply bootstrap with --parameter-file rather than environment contents")
        if bootstrap is None:
            raise ValueError("Provide --bootstrap for the private cloud-init file")
        text = Path(bootstrap).read_text(encoding="utf-8")
        if not text.startswith("#cloud-config") or any(p in text for p in ("CHANGE_ME", "DB_PRIVATE_IP", "CONTROLLER_PRIVATE_IP")):
            raise ValueError("Bootstrap needs #cloud-config and all placeholders replaced")
        config = read_yaml(bootstrap)
        if not isinstance(config, dict) or not config.get("runcmd"):
            raise ValueError("Bootstrap needs startup commands")
    return parameters


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", type=Path)
    parser.add_argument("--kind", choices=("lb", "autoscaling"), default="lb")
    parser.add_argument("--bootstrap", type=Path)
    args = parser.parse_args()
    try:
        templates = check_templates()
        if args.environment:
            check_environment(args.environment, args.kind, args.bootstrap)
    except (ValueError, TypeError, KeyError, OSError, yaml.YAMLError) as error:
        # Do not print YAML excerpts from files that may contain credentials.
        print(f"FAIL: {type(error).__name__}. Check template/environment values locally.")
        return 1
    print(f"PASS: {len(templates)} templates and nested interfaces; offline checks only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
