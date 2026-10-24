import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests
import yaml


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate = load("validate")
cloud_check = load("cloud_check")
probe = load("probe")


class TemplateChecks(unittest.TestCase):
    def test_nested_graph_and_references(self):
        templates = validate.check_templates()
        self.assertEqual(len(templates), 4)

    def test_private_only_and_two_az_floor(self):
        templates = validate.check_templates()
        for template in templates.values():
            kinds = {entry.get("type") for entry in validate.walk(template) if isinstance(entry.get("type"), str)}
            self.assertNotIn("OS::Neutron::FloatingIP", kinds)
        auto = templates["autoscaling.yaml"]
        baseline = auto["resources"]["baseline_az_a"]["properties"]
        group = auto["resources"]["app_group"]["properties"]
        self.assertNotEqual(baseline["availability_zone"], group["resource"]["properties"]["availability_zone"])
        self.assertGreaterEqual(group["min_size"], 1)
        self.assertEqual(auto["parameters"]["alarms_enabled"]["default"], False)
        self.assertTrue(auto["parameters"]["bootstrap_user_data"]["hidden"])
        self.assertNotIn("signal_url", json.dumps(auto["outputs"]))

    def test_readiness_monitor(self):
        monitor = validate.read_yaml(ROOT / "templates/lb-core.yaml")["resources"]["monitor"]["properties"]
        self.assertEqual(monitor["url_path"], "/health/ready")
        self.assertLess(monitor["timeout"], monitor["delay"])

    def test_broken_reference_and_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "broken.yaml"
            path.write_text("heat_template_version: '2018-08-31'\nresources:\n  bad:\n    type: OS::Nova::Server\n    properties:\n      image: {get_param: missing}\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate.check_templates(Path(temporary))
            path.write_text("parameters: {}\nparameters: {}\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate.read_yaml(path)

    def test_examples_are_not_deployable_inputs(self):
        for name, kind in (("lb.env.example.yaml", "lb"), ("autoscaling.env.example.yaml", "autoscaling")):
            with self.assertRaises(ValueError):
                validate.check_environment(ROOT / name, kind)

    def test_environment_rejects_same_backend(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = Path(temporary) / "env.yaml"
            parameters = {"subnet_id": "real-subnet-id", "backend_a": "10.0.0.10", "backend_b": "10.0.0.10"}
            env.write_text(yaml.safe_dump({"parameters": parameters}), encoding="utf-8")
            with self.assertRaises(ValueError):
                validate.check_environment(env, "lb")
            parameters["backend_b"] = "10.0.0.11"
            env.write_text(yaml.safe_dump({"parameters": parameters}), encoding="utf-8")
            validate.check_environment(env, "lb")

    def test_autoscaling_input_boundaries(self):
        parameters = validate.read_yaml(ROOT / "autoscaling.env.example.yaml")["parameters"]
        parameters = {k: ("actual-" + k if isinstance(v, str) and "CHANGE_ME" in v else v) for k, v in parameters.items()}
        with tempfile.TemporaryDirectory() as temporary:
            env, boot = Path(temporary) / "env.yaml", Path(temporary) / "bootstrap.yaml"
            boot.write_text("#cloud-config\nruncmd:\n  - [true]\n", encoding="utf-8")
            env.write_text(yaml.safe_dump({"parameters": parameters}), encoding="utf-8")
            validate.check_environment(env, "autoscaling", boot)
            for changed in ({"az_b": parameters["az_a"]}, {"threshold_low": parameters["threshold_high"]},
                            {"alarms_enabled": "false"}, {"granularity": 0}, {"cooldown": 0}):
                broken = dict(parameters, **changed)
                env.write_text(yaml.safe_dump({"parameters": broken}), encoding="utf-8")
                with self.assertRaises(ValueError):
                    validate.check_environment(env, "autoscaling", boot)


class CloudQueries(unittest.TestCase):
    def test_redacts_action_urls_and_embedded_credentials(self):
        report = {"history": [{"detail": 'action trust+http://heat/v1/project/stacks/s/resources/p/signal'}],
                  "token": "token-value", "message": "postgresql+psycopg://user:password@db/integrity"}
        cleaned = json.dumps(cloud_check.redact(report))
        for secret in ("trust+http", "token-value", "user:password"):
            self.assertNotIn(secret, cleaned)

    @patch.object(cloud_check.subprocess, "run")
    def test_cli_has_timeout_and_no_shell(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, '{"status": "ACTIVE"}', "")
        self.assertTrue(cloud_check.query(["loadbalancer", "show", "uuid"])["ok"])
        args, kwargs = run.call_args
        self.assertEqual(args[0][0:3], ["openstack", "--os-api-timeout", "30"])
        self.assertNotIn("shell", kwargs)
        self.assertEqual(kwargs["timeout"], 45)

    @patch.object(cloud_check.subprocess, "run")
    def test_failed_cli_does_not_leak_stderr(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, "", "secret-token")
        result = cloud_check.query(["catalog", "list"])
        self.assertFalse(result["ok"])
        self.assertNotIn("secret-token", json.dumps(result))

    @patch.object(cloud_check.subprocess, "run", side_effect=FileNotFoundError)
    def test_missing_cli_is_not_a_pass(self, run):
        self.assertFalse(cloud_check.query(["catalog", "list"])["ok"])


class ProbeChecks(unittest.TestCase):
    def session(self, body=b"fixture"):
        digest = hashlib.sha256(b"fixture").hexdigest()
        session = Mock()
        ready, verified, download = Mock(), Mock(), Mock()
        ready.status_code = verified.status_code = download.status_code = 200
        verified.json.return_value = {"id": "fixture-id", "intact": True,
                                     "expected_sha256": digest, "actual_sha256": digest,
                                     "expected_size": 7, "actual_size": 7}
        download.iter_content.return_value = iter([body])
        context = Mock()
        context.__enter__ = Mock(return_value=download)
        context.__exit__ = Mock(return_value=False)
        session.get.side_effect = [ready, context]
        session.post.return_value = verified
        return session, verified, digest

    def test_valid_roundtrip_and_redirects_disabled(self):
        session, _, digest = self.session()
        probe.probe_once(session, "http://lb", "fixture-id", digest, 7)
        self.assertFalse(session.post.call_args.kwargs["allow_redirects"])

    def test_tampered_download_fails_even_if_verify_says_intact(self):
        session, _, digest = self.session(b"changed")
        with self.assertRaises(ValueError):
            probe.probe_once(session, "http://lb", "fixture-id", digest, 7)

    def test_verification_false_or_dependency_failure_is_not_a_pass(self):
        session, verified, digest = self.session()
        verified.json.return_value["intact"] = False
        with self.assertRaises(ValueError):
            probe.probe_once(session, "http://lb", "fixture-id", digest, 7)
        session, verified, digest = self.session()
        verified.raise_for_status.side_effect = requests.HTTPError("503")
        with self.assertRaises(requests.HTTPError):
            probe.probe_once(session, "http://lb", "fixture-id", digest, 7)


if __name__ == "__main__":
    unittest.main()
