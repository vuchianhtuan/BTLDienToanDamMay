"""Run Locust on this host through an existing SSH tunnel or approved LB URL.

No uploads, deployment, SSH setup or cloud mutations. Coordinate shared-lab load first.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit
from uuid import UUID, uuid4


ROOT = Path(__file__).resolve().parents[1]
PROFILES = {"light": (5, 1), "medium": (10, 2), "higher": (20, 2)}


def base_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username
            or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
        raise argparse.ArgumentTypeError("Use a base HTTP(S) URL without credentials, query or path")
    try:
        parsed.port
    except ValueError as error:
        raise argparse.ArgumentTypeError("Invalid port") from error
    return value.rstrip("/")


def build_command(host, profile, seconds, output):
    users, rate = PROFILES[profile]
    return [sys.executable, "-m", "locust", "-f", "loadtest/locustfile.py", "--headless",
            "-u", str(users), "-r", str(rate), "-t", f"{seconds}s", "--stop-timeout", "15",
            "--host", host, "--only-summary", "--exit-code-on-error", "1",
            "--csv", str(output / "result"), "--csv-full-history", "--html", str(output / "report.html")]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, type=base_url)
    parser.add_argument("--file-id", required=True, type=UUID)
    parser.add_argument("--profile", choices=PROFILES, default="light")
    parser.add_argument("--seconds", type=int, default=30)
    args = parser.parse_args(argv)
    if not 5 <= args.seconds <= 600:
        parser.error("seconds must be 5..600")
    started = datetime.now(timezone.utc)
    output = ROOT / "test-results/remote-locust" / (started.strftime("%Y%m%d-%H%M%S-") + uuid4().hex[:8])
    output.mkdir(parents=True, exist_ok=False)
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("LOCUST_") and key != "LOADTEST_FILE_ID"}
    env.update(LOADTEST_FILE_ID=str(args.file_id), LOCUST_SUMMARY_FILE=str(output / "summary.json"))
    # A local tunnel must not be intercepted by an inherited corporate HTTP proxy.
    bypass = env.get("NO_PROXY", env.get("no_proxy", ""))
    env["NO_PROXY"] = env["no_proxy"] = bypass + ",127.0.0.1,localhost,::1"
    metadata = {"started_utc": started.isoformat(), "profile": args.profile,
                "users": PROFILES[args.profile][0], "spawn_rate": PROFILES[args.profile][1],
                "duration_seconds": args.seconds, "fixture_id": str(args.file_id),
                "target": args.host, "transport": "host process; may traverse SSH tunnel",
                "scope": "HTTP workload only, not proof of LB or autoscaling", "status": "INCOMPLETE"}
    process = None
    try:
        metadata["commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        metadata["working_tree_dirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
        with (output / "locust.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(build_command(args.host, args.profile, args.seconds, output),
                                       cwd=ROOT, env=env, stdout=log, stderr=log)
            metadata["exit_code"] = process.wait(timeout=args.seconds + 120)
        summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        passed = (metadata["exit_code"] == 0 and summary["requests"] > 0 and summary["failures"] == 0)
        metadata["status"] = "PASS" if passed else "FAIL"
        return 0 if passed else 1
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        print("Run incomplete; inspect local logs. No credentials printed.", file=sys.stderr)
        return 2
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        (output / "run.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(f'{metadata["status"]}: {output}')


if __name__ == "__main__":
    raise SystemExit(main())
