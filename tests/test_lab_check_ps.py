"""PowerShell lab checker against synthetic HTTP only; skips if pwsh is absent."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import unittest


ROOT = Path(__file__).resolve().parents[1]
PWSh = shutil.which("pwsh")
DIGEST = hashlib.sha256(b"fixture").hexdigest()
FILE_ID = "00000000-0000-4000-8000-000000000001"


class API(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.startswith("/health/ready"):
            body = {"status": "ready", "storage": "swift"}
        elif self.path.startswith("/api/files"):
            body = [{"id": FILE_ID, "sha256": DIGEST, "size": 7}]
        else:
            body = {"asset": self.path}
        self.respond(body)

    def do_POST(self):
        mode = self.server.mode
        self.respond({"id": FILE_ID, "intact": "true" if mode == "string" else mode != "false",
                      "expected_sha256": DIGEST, "actual_sha256": "0" * 64 if mode == "mismatch" else DIGEST,
                      "expected_size": 7, "actual_size": 7})

    def respond(self, value):
        body = json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@unittest.skipUnless(PWSh, "PowerShell not available")
class LabCheckTests(unittest.TestCase):
    def test_real_script_rejects_semantic_failures(self):
        with ThreadingHTTPServer(("127.0.0.1", 0), API) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                for mode in ("valid", "false", "string", "mismatch"):
                    server.mode = mode
                    result = subprocess.run([PWSh, "-NoProfile", "-File", str(ROOT / "scripts/check-lab.ps1"),
                                             "-BaseUrl", f"http://127.0.0.1:{server.server_port}", "-CheckApi"],
                                            capture_output=True, text=True, timeout=30,
                                            env=dict(os.environ, APP_API_KEY="synthetic-test-only"))
                    with self.subTest(mode=mode):
                        self.assertEqual(result.returncode == 0, mode == "valid", result.stdout + result.stderr)
            finally:
                server.shutdown()
                worker.join(timeout=5)
