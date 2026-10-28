"""Run against a live app (including real PostgreSQL); leaves one labelled demo file."""
import hashlib
import os
from uuid import uuid4
import httpx

url = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000")
key = os.getenv("APP_API_KEY", "")
payload = b"Cloud lab integration smoke test\n"
with httpx.Client(base_url=url, headers={"X-API-Key": key}, timeout=30) as client:
    assert client.get("/health/ready").status_code == 200
    page = client.get("/")
    assert page.status_code == 200 and '/assets/app.js' in page.text
    for asset in ("api-client.js", "app.js", "styles.css"):
        assert client.get("/assets/" + asset).status_code == 200
    result = client.post("/api/files", params={"filename": "smoke-" + str(uuid4())[:8] + ".txt"}, content=payload)
    assert result.status_code == 201, result.text
    row = result.json()
    assert row["sha256"] == hashlib.sha256(payload).hexdigest()
    assert client.get(f'/api/files/{row["id"]}/download').content == payload
    verified = client.post(f'/api/files/{row["id"]}/verify')
    assert verified.status_code == 200 and verified.json()["intact"] is True
    assert any(item["id"] == row["id"] for item in client.get("/api/files").json())
print("PASS: readiness, frontend assets, upload, metadata, list, download, SHA-256 verify (DB/storage backend depends on target configuration)")
