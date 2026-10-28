"""Execute the real Locust CLI: live healthy API plus controlled negative HTTP fixtures."""
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CONTENT = b"Locust controlled fixture\n"
FIXTURE = {"id": "ec51cdfc-dea8-475d-a9b9-a0ace159de03", "size": len(CONTENT),
           "sha256": hashlib.sha256(CONTENT).hexdigest()}


def run_case(host, report, expected_failure=None):
    command = [sys.executable, "-m", "locust", "-f", "loadtest/locustfile.py", "--headless",
               "-u", "2", "-r", "2", "-t", "6s", "--stop-timeout", "1",
               "--host", host, "--only-summary", "--exit-code-on-error", "1", "--csv", str(report)]
    summary_file = Path(str(report) + "_final.json")
    process = subprocess.run(command, capture_output=True, text=True, timeout=40,
                             env={**os.environ, "LOCUST_SUMMARY_FILE": str(summary_file)})
    stats_file = Path(str(report) + "_stats.csv")
    if not stats_file.exists():
        raise AssertionError("Locust produced no stats:\n" + process.stdout + process.stderr)
    assert summary_file.exists(), process.stdout + process.stderr
    total = json.loads(summary_file.read_text(encoding="utf-8"))
    count, failures = total["requests"], total["failures"]
    if expected_failure:
        assert process.returncode == 1 and failures > 0, process.stdout + process.stderr
        assert expected_failure in process.stdout + process.stderr, process.stdout + process.stderr
        print(f"PASS negative {report.name}: exit=1; requests={count}; failures={failures}", flush=True)
    else:
        assert process.returncode == 0 and count >= 6 and failures == 0, process.stdout + process.stderr
        print(f"PASS live Locust: exit=0; requests={count}; failures=0", flush=True)


class ControlledAPI(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self):
        mode = self.server.mode
        if mode == "unauthorized":
            self.send_response(401)
            body = {"detail": "API key required"}
        else:
            self.send_response(200)
            if self.path.startswith("/api/files?") or self.path == "/api/files":
                body = [] if mode == "empty" else [FIXTURE]
            elif self.path.endswith("/verify"):
                body = {"id": FIXTURE["id"], "intact": mode != "corrupt_verify",
                        "expected_sha256": FIXTURE["sha256"], "actual_sha256": FIXTURE["sha256"],
                        "expected_size": len(CONTENT), "actual_size": len(CONTENT)}
            elif self.path.endswith("/download"):
                body = b"X" * len(CONTENT) if mode == "corrupt_download" else CONTENT
            else:
                body = {}
        payload = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = respond
    do_POST = respond


def main():
    # Existing smoke_live.py prepares the live database fixture before this check.
    with tempfile.TemporaryDirectory(prefix="tv3-locust-smoke-") as directory:
        reports = Path(directory)
        run_case(os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000"), reports / "live")
        for mode, expected in [("empty", "No fixture file"), ("unauthorized", "Fixture metadata HTTP 401"),
                               ("corrupt_verify", "intact must be true"),
                               ("corrupt_download", "Downloaded file SHA-256")]:
            server = ThreadingHTTPServer(("127.0.0.1", 0), ControlledAPI)
            server.mode = mode
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                run_case(f"http://127.0.0.1:{server.server_port}", reports / mode, expected)
            finally:
                server.shutdown()
                server.server_close()
                worker.join(timeout=5)


if __name__ == "__main__":
    main()
