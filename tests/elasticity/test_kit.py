"""Offline contract/security checks, not cloud integration evidence."""
import base64
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("elasticity_kit", ROOT / "deploy/elasticity/kit.py")
kit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kit)


def config():
    result = kit.read_json(kit.HERE / "config.example.json")
    for key in kit.ID_KEYS:
        result[key] = "00000000-0000-4000-8000-000000000001"
    result.update(flavor_id="lab.app", key_name="lab", az1="az1", az2="az2",
                  container_image="file-integrity:abcdef", client_cidr="10.10.0.0/24",
                  app1_ip="10.0.0.11", app2_ip="10.0.0.12")
    return result


ENV = """STORAGE_BACKEND=swift
DATABASE_URL=postgresql+psycopg://test:secret@db/integrity
APP_API_KEY=TEST_SECRET_ONLY
OS_AUTH_URL=http://keystone/v3
OS_APPLICATION_CREDENTIAL_ID=test-id
OS_APPLICATION_CREDENTIAL_SECRET=TEST_CREDENTIAL_ONLY
SWIFT_CONTAINER=lab
"""


class PlanningTests(unittest.TestCase):
    def test_example_is_intentionally_not_deployable(self):
        self.assertTrue(kit.validate_config(kit.read_json(kit.HERE / "config.example.json")))

    def test_cpu_percent_conversion_uses_vcpu_count(self):
        cfg = config()
        cfg["vcpus"] = 2
        result = kit.plan(cfg)
        self.assertEqual(result["cpu_high_rate"], 1_400_000_000)
        self.assertEqual(result["cpu_low_rate"], 400_000_000)
        self.assertEqual(result["maximum_app_ram_mb"], 4096)
        self.assertEqual(result["cloud_validation"], "NOT AVAILABLE")
        self.assertFalse(result["automatic_alarms_enabled"])

    def test_reject_unsafe_or_ambiguous_inputs(self):
        cases = [dict(az2="az1"), dict(app2_ip="10.0.0.11"), dict(app1_ip="8.8.8.8"),
                 dict(client_cidr="0.0.0.0/0"), dict(client_cidr="10.0.0.1/24"),
                 dict(max_per_zone=3), dict(vcpus=True), dict(budget_app_vms=2),
                 dict(cpu_low_percent=80), dict(cpu_high_percent=float("nan")),
                 dict(cooldown=60), dict(flavor_id="--debug"), dict(az1="az1;whoami")]
        for change in cases:
            with self.subTest(change=change):
                self.assertTrue(kit.validate_config({**config(), **change}))

    def test_unknown_fields_and_placeholder_ids_fail(self):
        self.assertTrue(kit.validate_config({**config(), "typo": 1}))
        self.assertTrue(kit.validate_config({**config(), "image_id": "CHANGE_ME"}))

    def test_env_roundtrip_keeps_special_characters_but_no_auto_alarm(self):
        text = ENV.replace("secret@db", "p%40ss%3Aword@db")
        baseline, elastic = kit.environments(config(), text)
        self.assertNotIn("app_env_b64", baseline["parameters"])
        params = elastic["parameters"]
        self.assertEqual(base64.b64decode(params["app_env_b64"]).decode(), text)
        self.assertFalse(params["enable_alarms"])
        template = kit.read_json(kit.HERE / "autoscale.json")
        self.assertLessEqual(params.keys(), template["parameters"].keys())

    def test_reject_local_storage_missing_and_duplicate_secrets(self):
        for text in (ENV.replace("swift", "local"), ENV.replace("TEST_SECRET_ONLY", "CHANGE_ME"),
                     ENV + "APP_API_KEY=duplicate\n", ENV.replace("postgresql+psycopg://", "sqlite:///")):
            with self.subTest():
                self.assertRaises(ValueError, kit.environments, config(), text)

    def test_cli_error_never_echoes_secret_env(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / "cfg.json").write_text(json.dumps(config()))
            (folder / "app.env").write_text(ENV.replace("swift", "local"))
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = kit.main(["build", "--config", str(folder / "cfg.json"), "--app-env",
                                   str(folder / "app.env"), "--out", str(folder / "output")])
            self.assertEqual(result, 2)
            self.assertNotIn("TEST_SECRET_ONLY", stderr.getvalue())
            self.assertFalse((folder / "output").exists())

    def test_writer_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report.json"
            kit.write_new(path, {"original": True}, private=True)
            self.assertRaises(FileExistsError, kit.write_new, path, {"original": False})
            self.assertTrue(kit.read_json(path)["original"])

    def test_build_cli_writes_complete_environment_without_printing_secrets(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / "cfg.json").write_text(json.dumps(config()), encoding="utf-8")
            (folder / "app.env").write_text(ENV, encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = kit.main(["build", "--config", str(folder / "cfg.json"), "--app-env",
                                   str(folder / "app.env"), "--out", str(folder / "generated")])
            self.assertEqual(result, 0)
            self.assertNotIn("TEST_SECRET_ONLY", output.getvalue())
            generated = kit.read_json(folder / "generated/autoscale.env.json")["parameters"]
            template = kit.read_json(kit.HERE / "autoscale.json")["parameters"]
            required = {key for key, value in template.items() if "default" not in value}
            self.assertLessEqual(required, generated.keys())
            self.assertEqual(base64.b64decode(generated["app_env_b64"]).decode(), ENV)
            self.assertFalse(generated["enable_alarms"])


class TemplateTests(unittest.TestCase):
    def test_nested_references_and_invariants(self):
        self.assertEqual(kit.lint_templates(), [])

    def test_missing_nested_argument_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in kit.TEMPLATES:
                doc = kit.read_json(kit.HERE / name)
                if name == "autoscale.json":
                    del doc["resources"]["group1"]["properties"]["resource"]["properties"]["image_id"]
                (root / name).write_text(json.dumps(doc))
            self.assertTrue(any("nested parameters" in e for e in kit.lint_templates(root)))

    def test_boot_uses_shared_env_no_image_pull_no_shell_interpolation(self):
        doc = kit.read_json(kit.HERE / "app-member.json")
        cloud = doc["resources"]["boot_config"]["properties"]["cloud_config"]
        envfile = cloud["write_files"][0]
        self.assertEqual(envfile["permissions"], "0600")
        self.assertEqual(envfile["encoding"], "b64")
        commands = cloud["runcmd"]
        run = commands[-1]
        self.assertEqual(run[run.index("--pull") + 1], "never")
        self.assertEqual(run[-1], {"get_param": "container_image"})
        self.assertTrue(all(isinstance(c, list) and c[0] not in ("sh", "bash") for c in commands))

    def test_alarms_scoped_per_az_no_action_on_missing_data(self):
        doc = kit.read_json(kit.HERE / "autoscale.json")
        for zone in (1, 2):
            group = doc["resources"][f"group{zone}"]["properties"]
            dimension = group["resource"]["properties"]["metering_group"]
            for direction in ("in", "out"):
                alarm = doc["resources"][f"cpu_{direction}{zone}"]["properties"]
                query = alarm["query"]["str_replace"]
                actual = json.loads(query["template"].replace("GROUP", f"test-stack-az{zone}"))
                self.assertEqual(actual["and"][1], {"=": {"ended_at": None}})
                self.assertEqual(query["params"]["GROUP"], dimension)
                self.assertEqual(alarm["insufficient_data_actions"], [])
                self.assertEqual(alarm["aggregation_method"], "rate:mean")
                policy = doc["resources"][f"scale_{direction}{zone}"]["properties"]
                self.assertEqual(policy["auto_scaling_group_id"], {"get_resource": f"group{zone}"})
                self.assertEqual(policy["scaling_adjustment"], 1 if direction == "out" else -1)


class DiscoveryTests(unittest.TestCase):
    def test_missing_cli_reports_unavailable(self):
        report = kit.probe(config(), query=lambda args: None)
        self.assertTrue(all(v == "NOT AVAILABLE" for v in report["checks"].values()))
        self.assertEqual(report["deployment_readiness"], "NOT VERIFIED")

    def test_flavor_mismatch_does_not_leak_catalog_or_metadata(self):
        calls = []
        def query(args):
            calls.append(args)
            if args[:2] == ["catalog", "list"]:
                return [{"Type": "orchestration", "Endpoints": "SECRET_ENDPOINT"}]
            if args[:2] == ["flavor", "show"]:
                return {"vcpus": 8, "ram": 8192, "private_metadata": "SECRET_METADATA"}
            return None
        report = kit.probe(config(), query=query)
        self.assertEqual(report["checks"]["flavor_size"], "MISMATCH")
        self.assertNotIn("SECRET", json.dumps(report))
        self.assertTrue(all(set(args).isdisjoint({"create", "set", "delete", "signal", "update"}) for args in calls))

    def test_collector_drops_action_urls_and_failure_reasons(self):
        calls = []
        def query(args):
            calls.append(args)
            return [{"id": "test-id", "resource_status": "CREATE_COMPLETE", "alarm_actions": "SIGNED_SECRET_URL",
                     "resource_status_reason": "SECRET_REASON", "parameters": "SECRET_ENV"}]
        identifier = "00000000-0000-4000-8000-000000000001"
        report = kit.collect(identifier, identifier, identifier, query=query)
        self.assertNotIn("SECRET", json.dumps(report))
        self.assertTrue(report["checks"]["resources"]["rows"])
        self.assertTrue(all(set(args).isdisjoint({"create", "set", "delete", "signal", "update"}) for args in calls))
        self.assertRaises(ValueError, kit.collect, "--debug", identifier, identifier, query)

    def test_failed_or_non_json_cli_output_is_not_published(self):
        def failed(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 1, "SECRET_STDOUT", "SECRET_STDERR")
        self.assertIsNone(kit.cli_json(["catalog", "list"], runner=failed))
        def invalid(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, "SECRET_NOT_JSON", "")
        self.assertIsNone(kit.cli_json(["catalog", "list"], runner=invalid))


if __name__ == "__main__":
    unittest.main()
