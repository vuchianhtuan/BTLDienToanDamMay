import hashlib
import logging
import tempfile
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

router = APIRouter(prefix="/api/files", tags=["files"])
log = logging.getLogger("integrity")


@router.get("")
def list_files(request: Request, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)):
    return request.app.state.files.listing(offset, limit)


@router.post("", status_code=201, openapi_extra={
    "requestBody": {"required": True, "content": {
        "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
    }}
})
async def upload(request: Request, filename: str = Query(..., min_length=1, max_length=255)):
    """Body is the raw file, not multipart. Filename is a query parameter."""
    filename = filename.replace("\\", "/").split("/")[-1]
    if not filename.strip() or any(ord(c) < 32 or ord(c) == 127 for c in filename):
        raise HTTPException(400, "Invalid filename")
    limit = request.app.state.max_file_bytes
    length = request.headers.get("content-length")
    if length:
        try:
            declared = int(length)
        except ValueError:
            raise HTTPException(400, "Invalid Content-Length")
        if declared < 0:
            raise HTTPException(400, "Invalid Content-Length")
        if declared > limit:
            raise HTTPException(413, "File exceeds size limit")
    digest = hashlib.sha256()
    size = 0
    with tempfile.TemporaryFile() as source:
        async for chunk in request.stream():
            size += len(chunk)
            if size > limit:
                raise HTTPException(413, "File exceeds size limit")
            digest.update(chunk)
            await run_in_threadpool(source.write, chunk)
        return await run_in_threadpool(request.app.state.files.persist, filename, source, size, digest.hexdigest())


@router.get("/{file_id}/download")
def download(request: Request, file_id: UUID):
    row = request.app.state.files.lookup(file_id)
    chunks = iter(request.app.state.storage.chunks(row.id))
    try:
        first = next(chunks, b"")
    except Exception:
        log.exception("Download unavailable for %s", row.id)
        chunks.close()
        raise HTTPException(503, "Stored object unavailable")

    def stream():
        try:
            yield first
            yield from chunks
        finally:
            chunks.close()

    return StreamingResponse(stream(), media_type="application/octet-stream", headers={
        "Content-Disposition": "attachment; filename*=UTF-8''" + quote(row.filename, safe=""),
    })


@router.post("/{file_id}/verify")
def verify(request: Request, file_id: UUID):
    return request.app.state.files.verify(file_id)
