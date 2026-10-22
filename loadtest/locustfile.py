import os
from locust import HttpUser, between, task


class FileUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.client.headers.update({"X-API-Key": os.getenv("APP_API_KEY", "")})
        # Reuse a fixture rather than grow the database on every request.
        with self.client.get("/api/files?limit=1", catch_response=True) as response:
            self.file_id = None
            if response.status_code == 200 and response.json():
                self.file_id = response.json()[0]["id"]
            elif response.status_code == 200:
                response.failure("Upload a demo file before the load test")

    @task(3)
    def listing(self):
        self.client.get("/api/files", name="list files")

    @task(1)
    def verify(self):
        if self.file_id:
            self.client.post(f"/api/files/{self.file_id}/verify", name="verify stored file")

    @task(1)
    def download(self):
        if self.file_id:
            self.client.get(f"/api/files/{self.file_id}/download", name="download stored file")
