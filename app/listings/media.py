"""Serves in-memory (dev) photo bytes over HTTP.

In production photos live in S3 and are served by their public URL, so this
endpoint only resolves objects held by the local :class:`InMemoryStorage`.
"""

from fastapi import APIRouter, HTTPException, Response, status

from app.core.storage import InMemoryStorage, get_storage

router = APIRouter(tags=["media"])


@router.get("/media/{key:path}")
async def get_media(key: str) -> Response:
    storage = get_storage()
    if isinstance(storage, InMemoryStorage):
        obj = storage.get(key)
        if obj is not None:
            content_type, data = obj
            return Response(
                content=data,
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=3600"},
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
