import importlib.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("probe_http", ROOT / "deploy/elasticity/probe_http.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class HTTPProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Handler(BaseHTTPRequestHandler):
            status = 200
            body = b'{"status":"ready","storage":"swift"}'
            def do_GET(self):
                self.send_response(self.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(self.body)))
                if self.status == 302:
                    self.send_header("Location", "/never-follow")
                self.end_headers()
                self.wfile.write(self.body)
            def log_message(self, *args):
                pass
        cls.handler = Handler
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=5)

    def setUp(self):
        self.handler.status = 200
        self.handler.body = b'{"status":"ready","storage":"swift"}'

    def test_real_http_success_and_storage_mismatch(self):
        self.assertTrue(probe.sample(self.base, "swift", 1)["ready"])
        row = probe.sample(self.base, "local", 1)
        self.assertFalse(row["ready"])
        self.assertEqual(row["error"], "storage_mismatch")

    def test_http_error_and_invalid_json_count_as_failures(self):
        self.handler.status = 503
        row = probe.sample(self.base, "swift", 1)
        self.assertEqual(row["http_status"], 503)
        self.assertFalse(row["ready"])
        self.handler.status = 200
        self.handler.body = b'SECRET_ERROR_BODY'
        row = probe.sample(self.base, "swift", 1)
        self.assertFalse(row["ready"])
        self.assertNotIn("SECRET", json.dumps(row))

    def test_redirect_is_failure_not_a_false_positive(self):
        self.handler.status = 302
        row = probe.sample(self.base, "swift", 1)
        self.assertEqual(row["http_status"], 302)
        self.assertFalse(row["ready"])

    def test_target_rejects_credentials_and_paths(self):
        for value in ("https://user:password@host", "ftp://host", "http://host/?token=secret", "http://host/health/ready"):
            with self.subTest(value=value):
                self.assertRaises(ValueError, probe.origin, value)
        self.assertEqual(probe.origin("https://host:8443/"), "https://host:8443")

    def test_outage_summary_counts_consecutive_failures(self):
        rows = [{"ready": value, "latency_ms": i} for i, value in enumerate([True, False, False, True, False])]
        result = probe.summarize(rows)
        self.assertEqual(result["failed_samples"], 3)
        self.assertEqual(result["sampled_availability_percent"], 40)
        self.assertEqual(result["max_consecutive_failed_samples"], 2)
        self.assertRaises(ValueError, probe.summarize, [])


if __name__ == "__main__":
    unittest.main()
