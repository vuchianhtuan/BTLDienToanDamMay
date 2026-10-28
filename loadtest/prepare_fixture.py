"""Upload one synthetic fixture; never upload repeatedly from workload tasks."""
import argparse
import hashlib
import json
import os
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://127.0.0.1:8000")
    parser.add_argument("--size-mib", type=int, default=1, choices=range(0, 26))
    args = parser.parse_args()
    host = args.host.rstrip("/")
    with urllib.request.urlopen(host + "/health/ready", timeout=15) as response:
        limit = json.load(response)["max_file_bytes"]
    size = args.size_mib * 1024 * 1024
    if size > limit:
        raise SystemExit("Requested fixture exceeds the application's file size limit")
    pattern = b"TV3 synthetic load fixture\n"
    payload = (pattern * ((size + len(pattern) - 1) // len(pattern)))[:size]
    request = urllib.request.Request(
        host + f"/api/files?filename=tv3-fixture-{args.size_mib}MiB.bin", data=payload,
        headers={"Content-Type": "application/octet-stream", "X-API-Key": os.getenv("APP_API_KEY", "")},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        row = json.load(response)
    assert row["size"] == size and row["sha256"] == hashlib.sha256(payload).hexdigest()
    print(json.dumps({name: row[name] for name in ("id", "filename", "size", "sha256")}))


if __name__ == "__main__":
    main()
