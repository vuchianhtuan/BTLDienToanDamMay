"""Observe an existing fixture through the LB during a supervised failover test."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import time
from urllib.parse import urlsplit
from uuid import UUID

import requests


def probe_once(session, host, file_id, expected_sha256, expected_size):
    response = session.get(host + "/health/ready", timeout=10, allow_redirects=False)
    response.raise_for_status()
    if response.status_code != 200:
        raise ValueError("Unexpected readiness status")
    response = session.post(f"{host}/api/files/{file_id}/verify", timeout=30, allow_redirects=False)
    response.raise_for_status()
    if response.status_code != 200:
        raise ValueError("Unexpected verification status")
    result = response.json()
    if not (result["id"] == file_id and result["intact"] is True
            and result["expected_sha256"] == result["actual_sha256"] == expected_sha256
            and result["expected_size"] == result["actual_size"] == expected_size):
        raise ValueError("Verification did not match original fixture")
    digest, size = hashlib.sha256(), 0
    with session.get(f"{host}/api/files/{file_id}/download", stream=True,
                     timeout=30, allow_redirects=False) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("Unexpected download status")
        for chunk in response.iter_content(1024 * 1024):
            size += len(chunk)
            digest.update(chunk)
    if digest.hexdigest() != expected_sha256 or size != expected_size:
        raise ValueError("Downloaded bytes changed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--file-id", required=True, type=UUID)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--size", required=True, type=int)
    parser.add_argument("--seconds", type=int, default=120)
    parser.add_argument("--interval", type=float, default=2)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    url = urlsplit(args.host)
    if (url.scheme not in {"http", "https"} or not url.netloc or url.username or url.password
            or url.query or url.fragment or url.path not in {"", "/"}):
        parser.error("Use a base HTTP(S) URL without credentials, query or path")
    if (args.seconds < 1 or args.interval <= 0 or args.size < 0 or len(args.sha256) != 64
            or any(char not in "0123456789abcdef" for char in args.sha256)):
        parser.error("Invalid duration, interval, fixture size or SHA-256")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    count = failures = 0
    with requests.Session() as session, args.output.open("x", newline="", encoding="utf-8") as stream:
        session.headers["X-API-Key"] = os.getenv("APP_API_KEY", "")
        writer = csv.writer(stream)
        writer.writerow(["utc", "roundtrip_ms", "ok", "error_type"])
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline:
            started, error = time.monotonic(), ""
            try:
                probe_once(session, args.host.rstrip("/"), str(args.file_id), args.sha256, args.size)
            except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                error = type(exc).__name__
                failures += 1
            count += 1
            writer.writerow([datetime.now(timezone.utc).isoformat(),
                             round((time.monotonic() - started) * 1000, 2), not error, error])
            stream.flush()
            time.sleep(min(args.interval, max(0, deadline - time.monotonic())))
    print(f"{count} probes, {failures} failures. CSV: {args.output}")
    return 1 if failures or not count else 0


if __name__ == "__main__":
    raise SystemExit(main())
