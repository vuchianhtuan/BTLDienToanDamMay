"""Validate merged sources against an isolated local API, never the shared TV2 lab."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

import requests


ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="tv3-integrated-") as temporary:
        data = Path(temporary)
        with socket.socket() as socket_probe:
            socket_probe.bind(("127.0.0.1", 0))
            port = socket_probe.getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        env = dict(os.environ, DATABASE_URL="sqlite:///" + str(data / "test.db"),
                   LOCAL_STORAGE_PATH=str(data / "objects"), STORAGE_BACKEND="local",
                   APP_API_KEY="synthetic-integration-test", TEST_BASE_URL=url)
        for key in list(env):
            if key.startswith("LOCUST_") or key == "LOADTEST_FILE_ID":
                del env[key]
        env["NO_PROXY"] = env["no_proxy"] = "localhost,127.0.0.1,::1"
        with (data / "server.log").open("w") as log:
            server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                                      cwd=ROOT, env=env, stdout=log, stderr=log)
            try:
                for _ in range(150):
                    if server.poll() is not None:
                        raise RuntimeError("Temporary API exited")
                    try:
                        if requests.get(url + "/health/ready", timeout=1).status_code == 200:
                            break
                    except requests.RequestException:
                        pass
                    time.sleep(0.1)
                else:
                    raise RuntimeError("Temporary API not ready")
                subprocess.run([sys.executable, "tests/smoke_live.py"], cwd=ROOT, env=env, check=True, timeout=90)
                subprocess.run([sys.executable, "tests/smoke_locust.py"], cwd=ROOT, env=env, check=True, timeout=180)
                fixture = requests.get(url + "/api/files?limit=1", headers={"X-API-Key": env["APP_API_KEY"]}, timeout=5).json()[0]
                subprocess.run([sys.executable, "scripts/run_remote_loadtest.py", "--host", url,
                                "--file-id", fixture["id"], "--seconds", "6"],
                               cwd=ROOT, env=env, check=True, timeout=90)
                print("PASS: isolated SQLite/local API; live smoke, Locust negative scenarios and host runner")
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)


if __name__ == "__main__":
    main()
