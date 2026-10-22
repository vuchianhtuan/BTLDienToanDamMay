import os
from contextlib import closing


class SwiftStorage:
    def __init__(self):
        from keystoneauth1 import session
        from keystoneauth1.identity import v3
        from swiftclient.client import Connection
        required = ["OS_AUTH_URL", "OS_APPLICATION_CREDENTIAL_ID", "OS_APPLICATION_CREDENTIAL_SECRET"]
        if any(not os.getenv(name) for name in required):
            raise ValueError("Swift requires Keystone application credential settings")
        auth = v3.ApplicationCredential(
            auth_url=os.environ[required[0]],
            application_credential_id=os.environ[required[1]],
            application_credential_secret=os.environ[required[2]],
        )
        self.session = session.Session(auth=auth)
        self.options = {
            "region_name": os.getenv("OS_REGION_NAME", "RegionOne"),
            "endpoint_type": os.getenv("OS_INTERFACE", "internal") + "URL",
        }
        self.container = os.getenv("SWIFT_CONTAINER", "file-integrity")
        self.connection_class = Connection

    def connection(self):
        return self.connection_class(session=self.session, os_options=self.options, timeout=15, retries=1)

    def put(self, key, source, size):
        source.seek(0)
        with closing(self.connection()) as conn:
            conn.put_object(self.container, key, contents=source, content_length=size,
                            content_type="application/octet-stream")

    def chunks(self, key):
        with closing(self.connection()) as conn:
            _, body = conn.get_object(self.container, key, resp_chunk_size=1024 * 1024)
            yield from body

    def delete(self, key):
        with closing(self.connection()) as conn:
            conn.delete_object(self.container, key)

    def check(self):
        with closing(self.connection()) as conn:
            conn.head_container(self.container)
