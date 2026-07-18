# ADR-0005 — Wilayas Stored in a PostgreSQL Table

- **Status**: Accepted
- **Date**: 2026-07-18
- **Deciders**: Massinissa Mohellebi
- **Refs**: Homepage H3 (hero search), Recherche S3/S4 (filtres UI), Carte M2/M5 (bounding boxes)

## Context

Three features need the list of Algeria's 58 wilayas: the homepage hero search (H3),
the search filters panel (Recherche S3/S4), and the interactive map (bounding boxes for
the "search in this area" feature, Carte M5). The wilaya list needs to carry at minimum:
- `code` (01–58 zero-padded string)
- `name_fr`, `name_ar`, `name_en` — trilingual display names
- `latitude`, `longitude` — centroid for map default viewport
- `bbox` (optional V2) — bounding box for Carte M5

Two storage strategies were considered:

1. **Static frontend constant** (`src/lib/wilayas.ts`): a TypeScript array bundled with
   the frontend. Zero API call, available offline, immutable at runtime.

2. **PostgreSQL table** (`wilayas`) with a public `GET /wilayas` endpoint: lives in the
   database, updated via the DB or a future admin UI without redeploying the frontend.

The key constraint raised during planning: correcting a spelling, updating an Arabic
transliteration, or adding map metadata (centroid coordinates, bounding boxes) must not
require a frontend build + redeployment cycle.

## Decision

We will store wilayas in a **PostgreSQL `wilayas` table**, seeded by an Alembic migration,
and expose them via a public unauthenticated endpoint:

```
GET /wilayas          → list[WilayaSchema]  (200, no auth)
```

Schema:

```sql
CREATE TABLE wilayas (
    code       CHAR(2)      PRIMARY KEY,   -- '01'…'58'
    name_fr    VARCHAR(100) NOT NULL,
    name_ar    VARCHAR(100) NOT NULL,
    name_en    VARCHAR(100) NOT NULL,
    latitude   NUMERIC(9,6) NOT NULL,
    longitude  NUMERIC(9,6) NOT NULL
);
```

The 58 rows are inserted in the Alembic seed migration for this feature. The endpoint
lives in `app/wilaya/` (router + service + repository — no auth dependency, no mutation
endpoints in V1).

The frontend fetches the list once at app load via TanStack Query with
`staleTime: 60 * 60 * 1000` (1 hour) — a payload of ~58 rows (~4 KB JSON) cached in
memory for the session. The wilaya list is consumed by `HeroSearch` (Homepage H3),
`FiltresPanneau` (Recherche S4), and the Leaflet map viewport initialisation (Carte M2).

## Consequences

**Easier:**
- Wilaya names, Arabic spellings, and centroid coordinates can be corrected via a direct
  DB update (or future admin UI) with no frontend rebuild or redeployment.
- Adding map bounding boxes in V2 is a single `ALTER TABLE wilayas ADD COLUMN bbox …`
  + data migration — no frontend type change required if `/sync-api-types` is re-run.
- A future admin can seed additional geographic data (e.g. communes within a wilaya)
  in the same `wilayas` feature module.

**Harder / trade-offs accepted:**
- One extra HTTP request on first page load (mitigated by the 1-hour TanStack Query
  cache; the list never changes between sessions in practice).
- The frontend now depends on the backend being up for the wilaya list. Mitigated by:
  (a) the list is not critical for page render (search bar degrades gracefully with an
  empty suggestions list if the request fails), and (b) TanStack Query retries on error.
- Seeding 58 rows in the Alembic migration adds a data migration; it must be idempotent
  (`INSERT … ON CONFLICT DO NOTHING`).

**Follow-up:**
- `app/wilaya/` feature module (router, service, repository, models, schemas) — no auth.
- Alembic seed migration: insert 58 wilayas with centroids.
- Frontend: `useWilayas()` hook wrapping TanStack Query `GET /wilayas`.
- `/sync-api-types` must be re-run after this endpoint is added.

## Alternatives considered

**Static TypeScript constant (`src/lib/wilayas.ts`).**
Zero latency, no API dependency, bundled with the app. Rejected because any update
(spelling fix, Arabic correction, adding centroid data for Carte M5) requires a frontend
build and redeployment. Given that all three consuming features share this data and the
map feature needs lat/lng that may be refined post-launch, the DB approach pays off
immediately.

**Hybrid: static fallback + DB override.**
Keep a hardcoded array and overwrite with DB data at runtime. Over-engineered for 58
static rows. The 1-hour cache in TanStack Query already acts as the practical fallback
for transient API failures.
