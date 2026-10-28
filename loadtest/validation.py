"""Pure validation shared by Locust and offline tests. HTTP 200 is not enough."""
import hashlib
import re
from uuid import UUID


def file_metadata(value):
    if not isinstance(value, dict):
        raise ValueError("File metadata must be an object")
    try:
        UUID(value.get("id", ""))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("File ID must be a UUID")
    if type(value.get("size")) is not int or value["size"] < 0:
        raise ValueError("File size must be a non-negative integer")
    if not isinstance(value.get("sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", value["sha256"]):
        raise ValueError("File SHA-256 must contain 64 lowercase hex characters")
    return value


def listing(value, require_fixture=False):
    if not isinstance(value, list):
        raise ValueError("File list must be a JSON array")
    if require_fixture and not value:
        raise ValueError("No fixture file: upload a demo file before starting Locust")
    for row in value:
        file_metadata(row)
    return value


def verification(value, fixture):
    if not isinstance(value, dict) or value.get("intact") is not True:
        raise ValueError("Integrity verification failed (intact must be true)")
    if value.get("id") != fixture["id"]:
        raise ValueError("Verification returned a different file ID")
    if value.get("expected_sha256") != fixture["sha256"] or value.get("actual_sha256") != fixture["sha256"]:
        raise ValueError("Verification hash differs from fixture metadata")
    for field in ("expected_size", "actual_size"):
        if type(value.get(field)) is not int or value[field] != fixture["size"]:
            raise ValueError("Verification size differs from fixture metadata")


def download(content, fixture):
    if len(content) != fixture["size"]:
        raise ValueError("Downloaded file size differs from fixture metadata")
    if hashlib.sha256(content).hexdigest() != fixture["sha256"]:
        raise ValueError("Downloaded file SHA-256 differs from fixture metadata")
