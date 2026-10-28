"""Run directly: python tests/loadtest/smoke_workload.py (no OpenStack needed)."""
import os
os.environ["LOCUST_SKIP_MONKEY_PATCH"] = "1"

import hashlib
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

import requests
from locust.env import Environment
from locust.exception import StopUser

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from loadtest.locustfile import FileUser


def main():
    with tempfile.TemporaryDirectory(prefix="integrity-loadtest-") as temporary:
        data = Path(temporary)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        host = f"http://127.0.0.1:{port}"
        env = dict(os.environ, DATABASE_URL="sqlite:///" + str(data / "test.db"),
                   LOCAL_STORAGE_PATH=str(data / "objects"), STORAGE_BACKEND="local",
                   APP_API_KEY="workload-test-key")
        with (data / "server.log").open("w") as log:
            server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                                       "--host", "127.0.0.1", "--port", str(port)],
                                      cwd=ROOT, env=env, stdout=log, stderr=log)
            try:
                for _ in range(100):
                    try:
                        if requests.get(host + "/health/ready", timeout=1).status_code == 200:
                            break
                    except requests.RequestException:
                        pass
                    if server.poll() is not None:
                        raise RuntimeError((data / "server.log").read_text())
                    time.sleep(0.1)
                else:
                    raise RuntimeError("Test API did not become ready")
                body = b"fixture for TV3 workload"
                response = requests.post(host + "/api/files?filename=workload.bin", data=body,
                                         headers={"X-API-Key": env["APP_API_KEY"]}, timeout=5)
                response.raise_for_status()
                fixture = response.json()
                assert fixture["sha256"] == hashlib.sha256(body).hexdigest()
                os.environ["APP_API_KEY"] = env["APP_API_KEY"]
                os.environ["LOADTEST_FILE_ID"] = fixture["id"]
                environment = Environment(host=host)
                FileUser.host = host
                results = []
                environment.events.request.add_listener(lambda **event: results.append(event))
                user = FileUser(environment)
                user.on_start()
                user.listing()
                user.verify()
                user.download()
                assert len(results) == 6 and all(r["exception"] is None for r in results), results
                assert results[-1]["response_length"] == len(body)
                # Same-size corruption must be a failure even with HTTP 200.
                (data / "objects" / fixture["id"]).write_bytes(b"x" * len(body))
                user.verify()
                user.download()
                assert all(r["exception"] is not None for r in results[-2:]), results[-2:]
                assert "Integrity verification" in str(results[-2]["exception"])
                assert "Downloaded file SHA-256" in str(results[-1]["exception"])
                (data / "objects" / fixture["id"]).unlink()
                user.download()
                assert results[-1]["exception"] is not None
                # Missing selected fixture and invalid credentials must stop users.
                for selected, key in [(str(uuid4()), env["APP_API_KEY"]), (fixture["id"], "wrong"),
                                      ("not-a-uuid", env["APP_API_KEY"])]:
                    os.environ["LOADTEST_FILE_ID"] = selected
                    os.environ["APP_API_KEY"] = key
                    other = FileUser(environment)
                    try:
                        other.on_start()
                    except StopUser:
                        pass
                    else:
                        raise AssertionError("Invalid fixture/auth must stop the user")
                    finally:
                        other.client.close()
                    assert results[-1]["exception"] is not None
                    assert environment.process_exit_code == 1
                user.client.close()
                print("PASS: valid workload, streamed byte count, tampered verify/download, missing object, missing fixture, API key")
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)


if __name__ == "__main__":
    main()
