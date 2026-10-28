import hashlib
import json
import os
from pathlib import Path
from time import perf_counter
from uuid import UUID

from locust import HttpUser, between, events, task
from locust.exception import StopUser

# Locust adds the locustfile directory to sys.path.
try:
    from .validation import download_digest, listing, verification
except ImportError:  # Locust imports the file directly and adds its directory.
    from validation import download_digest, listing, verification


@events.quitting.add_listener
def write_final_summary(environment, **kwargs):
    # CSV is periodic and may still contain zero counters for a fail-fast run.
    target = os.getenv("LOCUST_SUMMARY_FILE")
    if target:
        total = environment.stats.total
        Path(target).write_text(json.dumps({
            "requests": total.num_requests, "failures": total.num_failures,
            "average_ms": total.avg_response_time,
            "p95_ms": total.get_response_time_percentile(0.95),
            "requests_per_second": total.total_rps,
        }, indent=2), encoding="utf-8")


class FileUser(HttpUser):
    wait_time = between(1, 3)
    request_timeout = 15

    def abort_fixture(self):
        self.environment.process_exit_code = 1
        if self.environment.runner is not None:
            self.environment.runner.quit()
        raise StopUser()

    def on_start(self):
        self.client.headers.update({"X-API-Key": os.getenv("APP_API_KEY", "")})
        self.fixture = None
        selected = os.getenv("LOADTEST_FILE_ID", "")
        try:
            selected = str(UUID(selected)) if selected else ""
        except ValueError:
            raise ValueError("LOADTEST_FILE_ID must be a UUID") from None
        offset, batch = 0, 200 if selected else 1
        while self.fixture is None:
            invalid = False
            with self.client.get(f"/api/files?offset={offset}&limit={batch}", name="fixture metadata", catch_response=True,
                                 timeout=self.request_timeout) as response:
                try:
                    if response.status_code != 200:
                        raise ValueError(f"Fixture metadata HTTP {response.status_code}")
                    rows = listing(response.json(), require_fixture=True)
                    self.fixture = next((row for row in rows if not selected or row["id"] == selected), None)
                    if self.fixture is None and len(rows) < batch:
                        raise ValueError("No fixture file matching LOADTEST_FILE_ID")
                except (ValueError, TypeError, KeyError) as error:
                    response.failure(str(error))
                    invalid = True
            if invalid:
                self.abort_fixture()
            offset += batch
        if not self.check_verify() or not self.check_download():
            self.abort_fixture()

    @task(3)
    def listing(self):
        with self.client.get("/api/files", name="list files", catch_response=True,
                             timeout=self.request_timeout) as response:
            try:
                if response.status_code != 200:
                    raise ValueError(f"List files HTTP {response.status_code}")
                listing(response.json())
            except (ValueError, TypeError, KeyError) as error:
                response.failure(str(error))

    def check_verify(self):
        valid = True
        with self.client.post(f'/api/files/{self.fixture["id"]}/verify', name="verify stored file",
                              catch_response=True, timeout=self.request_timeout) as response:
            try:
                if response.status_code != 200:
                    raise ValueError(f"Verify HTTP {response.status_code}")
                verification(response.json(), self.fixture)
            except (ValueError, TypeError, KeyError) as error:
                response.failure(str(error))
                valid = False
        return valid

    @task(1)
    def verify(self):
        self.check_verify()

    def check_download(self):
        valid = True
        started = perf_counter()
        with self.client.get(f'/api/files/{self.fixture["id"]}/download', name="download stored file",
                             catch_response=True, stream=True, timeout=self.request_timeout) as response:
            try:
                if response.status_code != 200:
                    raise ValueError(f"Download HTTP {response.status_code}")
                digest, size = hashlib.sha256(), 0
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    digest.update(chunk)
                    size += len(chunk)
                response.request_meta["response_length"] = size
                download_digest(size, digest.hexdigest(), self.fixture)
            except Exception as error:
                response.failure(str(error))
                valid = False
            finally:
                response.request_meta["response_time"] = (perf_counter() - started) * 1000
                response.close()
        return valid

    @task(1)
    def download(self):
        self.check_download()
