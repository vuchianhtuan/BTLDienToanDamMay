import hashlib
import os
from time import perf_counter
from uuid import UUID

from locust import HttpUser, between, task
from locust.exception import StopUser


class FileUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.client.headers.update({"X-API-Key": os.getenv("APP_API_KEY", "")})
        selected = os.getenv("LOADTEST_FILE_ID", "")
        if selected:
            selected = str(UUID(selected))
        # Reuse a fixture; never upload repeatedly during a load test.
        self.fixture = None
        offset = 0
        while True:
            with self.client.get(
                f"/api/files?offset={offset}&limit=200", name="fixture metadata",
                catch_response=True, timeout=120,
            ) as response:
                try:
                    if response.status_code != 200:
                        raise ValueError(f"Fixture metadata HTTP {response.status_code}")
                    rows = response.json()
                    if not isinstance(rows, list):
                        raise ValueError("Metadata must be a list")
                    self.fixture = next((r for r in rows if not selected or r["id"] == selected), None)
                    if self.fixture:
                        UUID(self.fixture["id"])
                        digest = self.fixture["sha256"]
                        if not isinstance(self.fixture["size"], int) or self.fixture["size"] < 0:
                            raise ValueError("Invalid fixture size")
                        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                            raise ValueError("Invalid fixture SHA-256")
                        break
                    if len(rows) < 200:
                        raise ValueError("Fixture not found. Upload a demo file before testing.")
                except (ValueError, KeyError, TypeError) as exc:
                    response.failure(str(exc))
                    raise StopUser() from exc
            offset += 200

    @task(3)
    def listing(self):
        self.client.get("/api/files", name="list files", timeout=120)

    @task(1)
    def verify(self):
        with self.client.post(
            f'/api/files/{self.fixture["id"]}/verify', name="verify stored file",
            catch_response=True, timeout=120,
        ) as response:
            if response.status_code != 200:
                return
            try:
                result = response.json()
                expected = self.fixture
                if not (
                    result["id"] == expected["id"] and result["intact"] is True
                    and result["expected_sha256"] == result["actual_sha256"] == expected["sha256"]
                    and result["expected_size"] == result["actual_size"] == expected["size"]
                ):
                    response.failure("Integrity verification did not match the fixture")
            except (ValueError, KeyError, TypeError):
                response.failure("Invalid verify response")

    @task(1)
    def download(self):
        started = perf_counter()
        with self.client.get(
            f'/api/files/{self.fixture["id"]}/download', name="download stored file",
            catch_response=True, stream=True, timeout=120,
        ) as response:
            try:
                if response.status_code != 200:
                    return
                digest = hashlib.sha256()
                size = 0
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    digest.update(chunk)
                    size += len(chunk)
                if size != self.fixture["size"] or digest.hexdigest() != self.fixture["sha256"]:
                    response.failure("Downloaded bytes do not match fixture SHA-256/size")
                response.request_meta["response_length"] = size
            except Exception as exc:
                response.failure(f"Download stream failed: {type(exc).__name__}")
            finally:
                # Include receiving and checking the full body, not just headers.
                response.request_meta["response_time"] = (perf_counter() - started) * 1000
                response.close()
