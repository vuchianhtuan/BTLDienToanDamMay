"""File operations shared by routes; storage can be injected for isolated tests."""
import hashlib
import logging
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app.models import StoredFile, serialize
from app.storage.base import ObjectStorage

log = logging.getLogger("integrity")


class FileService:
    def __init__(self, sessions, storage: ObjectStorage):
        self.sessions = sessions
        self.storage = storage

    def listing(self, offset, limit):
        with self.sessions() as session:
            rows = session.scalars(select(StoredFile).order_by(StoredFile.created_at.desc(), StoredFile.id)
                                   .offset(offset).limit(limit))
            return [serialize(row) for row in rows]

    def persist(self, filename, source, size, sha256):
        row = StoredFile(id=str(uuid4()), filename=filename, size=size, sha256=sha256,
                         created_at=datetime.now(timezone.utc))
        try:
            self.storage.put(row.id, source, size)
        except Exception:
            log.exception("Object upload failed")
            raise HTTPException(503, "Storage unavailable")
        try:
            with self.sessions() as session:
                session.add(row)
                session.commit()
        except Exception:
            log.exception("Metadata commit failed for %s", row.id)
            try:
                self.storage.delete(row.id)
            except Exception:
                log.exception("Orphan cleanup required for %s", row.id)
            raise HTTPException(503, "Metadata could not be saved")
        return serialize(row)

    def lookup(self, file_id):
        with self.sessions() as session:
            row = session.get(StoredFile, str(file_id))
            if row is None:
                raise HTTPException(404, "File not found")
            return row

    def verify(self, file_id):
        row = self.lookup(file_id)
        digest = hashlib.sha256()
        size = 0
        try:
            for chunk in self.storage.chunks(row.id):
                digest.update(chunk)
                size += len(chunk)
        except Exception:
            log.exception("Verification unavailable for %s", row.id)
            raise HTTPException(503, "Stored object unavailable; integrity not verified")
        actual = digest.hexdigest()
        return {"id": row.id, "filename": row.filename,
                "intact": secrets.compare_digest(actual, row.sha256) and size == row.size,
                "expected_sha256": row.sha256, "actual_sha256": actual,
                "expected_size": row.size, "actual_size": size,
                "verified_at": datetime.now(timezone.utc)}
