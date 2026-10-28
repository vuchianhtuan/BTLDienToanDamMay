import json
import os
from pathlib import Path

from locust import HttpUser, between, events, task
from locust.exception import StopUser

# Locust adds the locustfile directory to sys.path.
from validation import download, listing, verification


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
        with self.client.get("/api/files?limit=1", name="fixture metadata", catch_response=True,
                             timeout=self.request_timeout) as response:
            try:
                if response.status_code != 200:
                    raise ValueError(f"Fixture metadata HTTP {response.status_code}")
                self.fixture = listing(response.json(), require_fixture=True)[0]
            except (ValueError, TypeError, KeyError) as error:
                response.failure(str(error))
        if self.fixture is None:
            self.abort_fixture()
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
        with self.client.get(f'/api/files/{self.fixture["id"]}/download', name="download stored file",
                             catch_response=True, timeout=self.request_timeout) as response:
            try:
                if response.status_code != 200:
                    raise ValueError(f"Download HTTP {response.status_code}")
                download(response.content, self.fixture)
            except (ValueError, TypeError, KeyError) as error:
                response.failure(str(error))
                valid = False
        return valid

    @task(1)
    def download(self):
        self.check_download()
