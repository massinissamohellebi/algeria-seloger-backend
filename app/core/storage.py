"""Object storage backends for listing photos.

An abstract :class:`StorageBackend` decouples the API from S3 so the same code
runs in tests/dev (in-memory) and production (S3). Uploads return a public URL
that is persisted on the photo row.
"""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

import anyio

from app.core.config import settings


class StorageError(Exception):
    """Raised when the storage backend fails to store or delete an object."""


def build_object_key(listing_id: uuid.UUID, content_type: str) -> str:
    ext = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }.get(content_type, "bin")
    return f"listings/{listing_id}/{uuid.uuid4()}.{ext}"


@runtime_checkable
class StorageBackend(Protocol):
    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        """Store bytes under ``key`` and return the public URL."""
        ...

    async def delete(self, url: str) -> None:
        """Delete the object identified by its public URL."""
        ...


class InMemoryStorage:
    """Backend used in tests and local dev (no real S3).

    Bytes are kept in-process and served back over HTTP by the ``/media``
    endpoint so uploaded photos are viewable in the browser during local dev.
    """

    def __init__(self) -> None:
        self.objects: dict[str, tuple[str, bytes]] = {}

    def _media_url(self, key: str) -> str:
        return f"{settings.media_base_url.rstrip('/')}/media/{key}"

    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        self.objects[key] = (content_type, data)
        return self._media_url(key)

    def get(self, key: str) -> tuple[str, bytes] | None:
        """Return ``(content_type, data)`` for a stored key, or ``None``."""
        return self.objects.get(key)

    async def delete(self, url: str) -> None:
        key = url.rsplit("/media/", 1)[-1]
        self.objects.pop(key, None)


class S3Storage:
    """Production backend backed by S3 (or an S3-compatible endpoint)."""

    def __init__(self) -> None:
        import boto3  # imported lazily so tests/dev don't require boto3

        self._client = boto3.client(
            "s3",
            region_name=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )
        self._bucket = settings.s3_bucket

    def _public_url(self, key: str) -> str:
        if settings.s3_public_base_url:
            return f"{settings.s3_public_base_url.rstrip('/')}/{key}"
        if settings.s3_endpoint_url:
            return f"{settings.s3_endpoint_url.rstrip('/')}/{self._bucket}/{key}"
        return f"https://{self._bucket}.s3.{settings.s3_region}.amazonaws.com/{key}"

    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        def _put() -> None:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )

        try:
            await anyio.to_thread.run_sync(_put)
        except Exception as exc:  # noqa: BLE001 - surfaced as a domain error
            raise StorageError(str(exc)) from exc
        return self._public_url(key)

    async def delete(self, url: str) -> None:
        # Recover the key from the public URL by stripping the known prefix.
        key = url.rsplit(f"/{self._bucket}/", 1)[-1]
        if key == url:
            key = url.rsplit("/", 1)[-1]
            key = f"listings/{key}"

        def _delete() -> None:
            self._client.delete_object(Bucket=self._bucket, Key=key)

        try:
            await anyio.to_thread.run_sync(_delete)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(str(exc)) from exc


_backend: StorageBackend | None = None


def get_storage() -> StorageBackend:
    """FastAPI dependency returning the process-wide storage backend."""
    global _backend
    if _backend is None:
        _backend = S3Storage() if settings.s3_bucket else InMemoryStorage()
    return _backend
