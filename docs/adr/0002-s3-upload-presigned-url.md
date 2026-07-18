# ADR-0002 — S3 Photo Upload via Presigned URLs

- **Status**: Accepted
- **Date**: 2026-07-17
- **Deciders**: Massinissa Mohellebi
- **Refs**: Annonces S3 (Upload photos S3), Espace agence A3 (logo/cover upload)

## Context

Two features require file uploads to S3: Annonces (up to 20 photos per listing) and
Espace agence (logo + cover photo per agency). Two standard approaches exist:

1. **Backend-proxied**: The client POSTs the file to the FastAPI backend as
   `multipart/form-data`. The backend validates the file and streams it to S3. The backend
   carries all upload bandwidth.

2. **Presigned URL**: The backend generates a short-lived signed S3 URL. The client
   uploads the file directly from the browser to S3 using that URL. The backend is not in
   the upload data path.

Constraints in V1:
- No Redis/Celery — no async job queue.
- S3 bucket credentials must never be exposed to the client.
- File validation (MIME type, max size) must be enforced before bytes land in S3.

## Decision

We will use **presigned URLs** for all S3 uploads. The flow is:

1. Client calls `POST /listings/{id}/photos/upload-url` (or `PATCH /agencies/{id}/logo/upload-url`)
   with the file's `content_type` and `size` in bytes.
2. Backend validates `content_type` (whitelist: `image/jpeg`, `image/png`, `image/webp`)
   and `size` (≤ 5 MB). If invalid, returns `400` immediately — no S3 call made.
3. Backend generates a presigned `PUT` URL via `aiobotocore` with a 5-minute TTL and
   returns it to the client, along with the final S3 key.
4. Client performs a `PUT` directly to S3 using the presigned URL (no backend in the
   data path).
5. Client calls `POST /listings/{id}/photos/confirm` with the S3 key to register the
   photo in the database. The backend performs a `head_object` to verify the file actually
   landed in S3 before persisting the record.

The S3 bucket has **no public ACL**. Published listing photos are served via a CloudFront
distribution (or a backend-signed URL for private assets).

S3 CORS configuration on the bucket must allow `PUT` from the frontend origin
(`algeria-seloger.localhost` in dev, production domain in prod).

## Consequences

**Easier:**
- The backend is completely out of the upload bandwidth path — no memory pressure on the
  app server regardless of file size or concurrency.
- Scales to large files (video thumbnails in V2) without touching the backend code.
- Upload progress bars work natively in the browser (direct XHR/fetch to S3).

**Harder / trade-offs accepted:**
- S3 CORS configuration is required (one-time bucket setup, documented in `infra/`).
- The 2-step flow (get URL → upload → confirm) is slightly more complex on the frontend
  than a single POST. Encapsulated in a `useS3Upload` hook.
- A confirm step is mandatory: without it, the DB can reference keys for files that never
  arrived (e.g. client closed tab mid-upload). The `head_object` check in the confirm
  endpoint guards against orphaned DB records.
- Presigned URLs have a 5-minute TTL. If the client takes longer to upload (very slow
  connection + large file), the URL expires. The frontend must handle the `403` from S3
  and request a new presigned URL.

**Follow-up:**
- Document S3 bucket CORS policy in `infra/s3-cors.json`.
- The `useS3Upload` React hook encapsulates: request URL → XHR upload with progress →
  confirm call. Shared across Annonces and Espace agence.

## Alternatives considered

**Backend-proxied multipart upload.**
Simpler 2-endpoint flow (upload → done); no CORS config; validation before S3.
Rejected because the backend carries all upload bandwidth — a fundamental scaling
bottleneck that would require horizontal scaling of the app server solely for file I/O.
Presigned URLs eliminate this bottleneck entirely, and the confirm-step validation
achieves equivalent safety guarantees.
