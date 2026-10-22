import hashlib
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models import Base
from app.storage import LocalStorage


@pytest.fixture
def setup(tmp_path):
    storage = LocalStorage(tmp_path / "objects")
    app = create_app("sqlite:///" + str(tmp_path / "test.db"), storage, max_bytes=32, api_key="")
    with TestClient(app) as client:
        yield client, storage


def upload(client, content=b"original", filename="sample.txt"):
    return client.post("/api/files", params={"filename": filename}, content=content)


def test_round_trip_and_verify(setup):
    client, _ = setup
    content = b"\x00binary\xff\n"
    result = upload(client, content, "tài liệu.bin")
    assert result.status_code == 201
    row = result.json()
    assert row["sha256"] == hashlib.sha256(content).hexdigest()
    assert client.get("/api/files").json()[0]["id"] == row["id"]
    response = client.get(f'/api/files/{row["id"]}/download')
    assert response.content == content
    assert "attachment;" in response.headers["content-disposition"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert client.post(f'/api/files/{row["id"]}/verify').json()["intact"] is True


def test_detect_same_length_tampering(setup):
    client, storage = setup
    row = upload(client).json()
    (storage.root / row["id"]).write_bytes(b"modified")
    result = client.post(f'/api/files/{row["id"]}/verify').json()
    assert result["intact"] is False
    assert result["expected_sha256"] != result["actual_sha256"]


def test_missing_object_is_unavailable_not_intact(setup):
    client, storage = setup
    row = upload(client).json()
    storage.delete(row["id"])
    assert client.post(f'/api/files/{row["id"]}/verify').status_code == 503
    assert client.get(f'/api/files/{row["id"]}/download').status_code == 503


def test_declared_and_streamed_limits(setup):
    client, storage = setup
    assert upload(client, b"x" * 33).status_code == 413
    response = client.post("/api/files?filename=stream.bin", content=iter([b"x" * 20, b"x" * 20]))
    assert response.status_code == 413
    assert client.get("/api/files").json() == []
    assert list(storage.root.iterdir()) == []


def test_boundary_and_empty_file(setup):
    client, _ = setup
    for content in [b"", b"a" * 32]:
        row = upload(client, content).json()
        assert client.get(f'/api/files/{row["id"]}/download').content == content
        assert client.post(f'/api/files/{row["id"]}/verify').json()["intact"]


def test_duplicate_names_do_not_overwrite(setup):
    client, _ = setup
    one = upload(client, b"one").json()
    two = upload(client, b"two").json()
    assert one["id"] != two["id"]
    assert client.get(f'/api/files/{one["id"]}/download').content == b"one"


def test_path_filename_is_not_storage_key(setup):
    client, storage = setup
    row = upload(client, filename="../../example.txt").json()
    assert row["filename"] == "example.txt"
    assert [p.name for p in storage.root.iterdir()] == [row["id"]]


@pytest.mark.parametrize("filename", ["  ", "bad\r\nheader", "/"])
def test_invalid_filename(setup, filename):
    assert upload(setup[0], filename=filename).status_code == 400


def test_unknown_and_invalid_identifiers(setup):
    client, _ = setup
    assert client.get(f"/api/files/{uuid4()}/download").status_code == 404
    assert client.post("/api/files/not-a-uuid/verify").status_code == 422


def test_pagination(setup):
    client, _ = setup
    for i in range(3):
        upload(client, str(i).encode())
    first = client.get("/api/files?limit=2").json()
    second = client.get("/api/files?limit=2&offset=2").json()
    assert len(first) == 2 and len(second) == 1
    assert first[0]["id"] != second[0]["id"]
    assert client.get("/api/files?offset=-1").status_code == 422


def test_storage_failure_creates_no_metadata(setup, monkeypatch):
    client, storage = setup
    def fail(*args):
        raise OSError("storage down")
    monkeypatch.setattr(storage, "put", fail)
    assert upload(client).status_code == 503
    assert client.get("/api/files").json() == []
    monkeypatch.setattr(storage, "check", fail)
    assert client.get("/health/ready").status_code == 503
    assert client.get("/health/live").status_code == 200


def test_shared_api_key(tmp_path):
    app = create_app("sqlite:///" + str(tmp_path / "auth.db"), LocalStorage(tmp_path / "files"), api_key="test-secret")
    with TestClient(app) as client:
        assert client.get("/health/ready").status_code == 200
        assert client.get("/api/files").status_code == 401
        assert client.post("/api/files?filename=a", content=b"x").status_code == 401
        assert client.get("/api/files", headers={"X-API-Key": "wrong"}).status_code == 401
        assert client.get("/api/files", headers={"X-API-Key": "test-secret"}).status_code == 200


def test_metadata_failure_compensates_object_write(setup):
    client, storage = setup
    # Real metadata failure after a successful object write.
    Base.metadata.drop_all(client.app.state.engine)
    assert upload(client).status_code == 503
    assert list(storage.root.iterdir()) == []
