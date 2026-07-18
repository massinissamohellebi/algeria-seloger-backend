# ADR-0001 — UUID Primary Keys for All Models

- **Status**: Accepted
- **Date**: 2026-07-17
- **Deciders**: Massinissa Mohellebi
- **Refs**: Annonces S1, Espace agence A1, Messagerie C1 — all depend on FK types decided here

## Context

The scaffolded `User` model uses `INTEGER` as its primary key (`id: Mapped[int]`). Before
any Alembic migration is applied (the `versions/` directory is currently empty), we must
decide the PK type for all models: `User`, `Listing`, `Photo`, `Agency`, `Conversation`,
`Message`.

Two forces are in tension:

- **Security**: integer PKs are sequential and guessable. An attacker who sees listing
  `id=42` in a URL can enumerate all listings or conversations (`/conversations/1`,
  `/conversations/2`, …). This is a low-effort IDOR vector even when authorization checks
  are in place.
- **Simplicity**: integer PKs are marginally faster for B-tree index lookups and joins;
  they are the default in many SQLAlchemy tutorials and slightly easier to debug
  (`user_id=7` vs `user_id=550e8400-…`).

No production data exists yet (no migrations), so the migration cost of changing `User.id`
from `int` to `UUID` is zero.

The JWT subject is already stored as a string in the current code (`sub = str(user.id)`),
so the auth layer is type-agnostic.

## Decision

We will use **UUID v4** (`uuid.UUID`, PostgreSQL `UUID` type) as the primary key for
every model in the project. The `User.id` column will be changed to UUID before the first
migration is generated. All FK columns referencing `User.id` (e.g. `Listing.owner_id`,
`Agency.user_id`, `Conversation.enquirer_id`) will also be `UUID`.

PostgreSQL generates UUIDs server-side via `gen_random_uuid()` (built-in since PG 13,
available via `pgcrypto` on earlier versions). SQLAlchemy mapping:

```python
import uuid
from sqlalchemy import UUID
from sqlalchemy.orm import Mapped, mapped_column

id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
)
```

## Consequences

**Easier:**
- Non-enumerable IDs in every URL and API response — eliminates the baseline IDOR
  enumeration risk with no additional middleware.
- All models are consistent; no mixed-type FK headaches.
- The JWT `sub` field (already a string) maps cleanly to `str(uuid)`.

**Harder / trade-offs accepted:**
- UUID columns are 16 bytes vs 4 bytes for `INTEGER`. Negligible at our scale.
- Slightly less readable in logs and during development. Mitigated by using the first 8
  characters in log lines when needed.
- `gen_random_uuid()` requires PostgreSQL ≥ 13 (our Docker image already targets PG 16).

**Follow-up:**
- Update `User` model immediately, before any migration is generated.
- Update `app/auth/service.py` to pass `uuid.UUID` where `int` was expected (the `sub`
  string cast is already correct).

## Alternatives considered

**Keep INTEGER PKs.**
Simpler, marginally faster joins, easier to read in debug sessions. Rejected because
sequential IDs are guessable, and the migration cost to switch later (once data exists)
would be significant. The window to make this change for free is now.

**UUID only for externally-exposed models (Listing, Agency), INTEGER for internal ones
(Photo, Message).**
Inconsistent; Photos and Messages are also returned in API payloads and can be targeted
individually (e.g. `DELETE /listings/{id}/photos/{photo_id}`). Rejected to keep the
convention uniform and avoid future confusion.
