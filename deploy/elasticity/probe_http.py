"""Bounded readiness sampling for local practice or real LB failover evidence.

Records HTTP/JSON readiness, not upload integrity or proof of autoscaling.
"""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import socket
import time
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def origin(value):
    parts = urllib.parse.urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise ValueError("Use an HTTP(S) origin without credentials")
    if parts.query or parts.fragment or parts.path not in ("", "/"):
        raise ValueError("Use only the origin, without query, fragment or path")
    parts.port  # Validate malformed port.
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def sample(base_url, expected_storage, timeout, opener=None):
    start = time.monotonic()
    result = {"at_utc": datetime.now(timezone.utc).isoformat(), "ready": False,
              "http_status": None, "error": None}
    opener = opener or urllib.request.build_opener(NoRedirect)
    try:
        request = urllib.request.Request(base_url + "/health/ready", headers={"Accept": "application/json"})
        with opener.open(request, timeout=timeout) as response:
            result["http_status"] = response.status
            body = json.loads(response.read(65537))
            if not isinstance(body, dict) or body.get("status") != "ready":
                result["error"] = "invalid_readiness"
            elif body.get("storage") != expected_storage:
                result["error"] = "storage_mismatch"
            else:
                result["ready"] = response.status == 200
    except urllib.error.HTTPError as error:
        result.update(http_status=error.code, error="http_error")
        error.close()
    except (TimeoutError, socket.timeout):
        result["error"] = "timeout"
    except urllib.error.URLError:
        result["error"] = "connection_or_tls_error"
    except (ValueError, OSError):
        result["error"] = "invalid_response"
    result["latency_ms"] = round((time.monotonic() - start) * 1000, 2)
    return result


def summarize(samples):
    if not samples:
        raise ValueError("At least one sample required")
    failed = sum(not row["ready"] for row in samples)
    longest = current = 0
    for row in samples:
        current = 0 if row["ready"] else current + 1
        longest = max(longest, current)
    latencies = sorted(row["latency_ms"] for row in samples)
    return {"samples": len(samples), "failed_samples": failed,
            "sampled_availability_percent": round(100 * (len(samples) - failed) / len(samples), 2),
            "max_consecutive_failed_samples": longest,
            "p95_probe_latency_ms": latencies[math.ceil(len(latencies) * .95) - 1]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--expected-storage", choices=("local", "swift"), default="swift")
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--interval", type=float, default=1)
    parser.add_argument("--timeout", type=float, default=3)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        base = origin(args.url)
        if not (1 <= args.samples <= 300 and .5 <= args.interval <= 60 and .2 <= args.timeout <= 10):
            raise ValueError("Sampling limits exceeded")
        path = Path(args.out)
        if path.exists():
            raise ValueError("Output must be new")
        rows = []
        for number in range(args.samples):
            rows.append(sample(base, args.expected_storage, args.timeout))
            if number + 1 < args.samples:
                time.sleep(args.interval)
        report = {"kind": "HTTP_READINESS_SAMPLES", "target": base, "expected_storage": args.expected_storage,
                  "limitations": "Point samples only; no proof of continuous uptime, integrity or scaling cause.",
                  "summary": summarize(rows), "records": rows}
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as output:
            json.dump(report, output, indent=2)
            output.write("\n")
        print(json.dumps(report["summary"]))
        return 1 if report["summary"]["failed_samples"] else 0
    except (ValueError, OSError):
        print("Cannot sample: check origin, numeric limits and a new output path.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
