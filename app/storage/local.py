import os
import shutil
import tempfile
from pathlib import Path


class LocalStorage:
    def __init__(self, path):
        self.root = Path(path)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, key, source, size):
        source.seek(0)
        fd, path = tempfile.mkstemp(dir=self.root, prefix=".upload-")
        try:
            with os.fdopen(fd, "wb") as target:
                shutil.copyfileobj(source, target)
            os.replace(path, self.root / key)
        finally:
            Path(path).unlink(missing_ok=True)

    def chunks(self, key):
        with (self.root / key).open("rb") as source:
            while block := source.read(1024 * 1024):
                yield block

    def delete(self, key):
        (self.root / key).unlink(missing_ok=True)

    def check(self):
        with tempfile.TemporaryFile(dir=self.root) as f:
            f.write(b"ready")
