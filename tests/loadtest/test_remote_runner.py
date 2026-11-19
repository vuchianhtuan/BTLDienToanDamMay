import argparse
import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location("remote_runner", Path(__file__).resolve().parents[2] / "scripts/run_remote_loadtest.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RemoteRunnerTests(unittest.TestCase):
    def test_local_tunnel_and_https_origins(self):
        self.assertEqual(runner.base_url("http://127.0.0.1:18000/"), "http://127.0.0.1:18000")
        self.assertEqual(runner.base_url("https://lab.example"), "https://lab.example")

    def test_credentials_redirect_path_and_bad_ports_rejected(self):
        for value in ("http://user:secret@host", "file:///tmp/a", "http://host/api", "http://host?key=a", "http://host:99999"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                runner.base_url(value)

    def test_command_uses_host_runtime_and_fixed_profile(self):
        command = runner.build_command("http://127.0.0.1:18000", "light", 10, Path("results"))
        self.assertEqual(command[:3], [runner.sys.executable, "-m", "locust"])
        self.assertEqual(command[command.index("-u") + 1], "5")
        self.assertEqual(command[command.index("--host") + 1], "http://127.0.0.1:18000")
        self.assertNotIn("docker", command)
        self.assertNotIn("APP_API_KEY", " ".join(command))
