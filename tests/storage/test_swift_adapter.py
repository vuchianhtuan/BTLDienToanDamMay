"""Contract test with fake Swift transport. Not an OpenStack integration test."""
from io import BytesIO

from app.storage import SwiftStorage


def test_swift_adapter_uses_generated_key_and_closes_connections(monkeypatch):
    monkeypatch.setenv("OS_AUTH_URL", "http://keystone.invalid/v3")
    monkeypatch.setenv("OS_APPLICATION_CREDENTIAL_ID", "fake-id")
    monkeypatch.setenv("OS_APPLICATION_CREDENTIAL_SECRET", "fake-secret")
    monkeypatch.setenv("SWIFT_CONTAINER", "test-container")
    storage = SwiftStorage()
    calls = []

    class Connection:
        def __init__(self, **kwargs):
            assert kwargs["timeout"] == 15

        def put_object(self, container, key, contents, content_length, content_type):
            assert container == "test-container" and key == "uuid-key"
            assert contents.read() == b"content" and content_length == 7
            calls.append("put")

        def get_object(self, container, key, resp_chunk_size):
            calls.append("get")
            return {}, iter([b"con", b"tent"])

        def delete_object(self, container, key):
            calls.append("delete")

        def head_container(self, container):
            calls.append("head")

        def close(self):
            calls.append("close")

    storage.connection_class = Connection
    source = BytesIO(b"content")
    source.seek(5)
    storage.put("uuid-key", source, 7)
    assert b"".join(storage.chunks("uuid-key")) == b"content"
    storage.delete("uuid-key")
    storage.check()
    assert calls == ["put", "close", "get", "close", "delete", "close", "head", "close"]
