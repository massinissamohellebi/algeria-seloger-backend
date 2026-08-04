# ADR-0006 — Full-Text Search via GENERATED STORED tsvector Column

- **Status**: Accepted
- **Date**: 2026-08-03
- **Deciders**: Massinissa Mohellebi
- **Refs**: Recherche S1 (API recherche full-text + tsvector migration), supersedes ADR-0004

## Context

Recherche S1 needs keyword search over `Listing.title` + `Listing.description`
using PostgreSQL `tsvector`/`tsquery`, combined with the existing faceted
filters on `GET /listings`. Two ways to keep the `tsvector` in sync exist:

1. **GENERATED ALWAYS AS … STORED** — Postgres recomputes the vector on every
   write from one fixed expression. Zero application/PL-pgSQL code, but the
   text-search config is locked at migration time (cannot vary per row).
2. **Trigger-maintained column** — a `BEFORE INSERT/UPDATE` PL/pgSQL trigger
   sets a plain `tsvector`, able to branch on a per-row `language` column to pick
   `french` / `english` / `simple`. ADR-0004 originally chose this.

Re-evaluating during implementation, the trigger route requires a new required
`language` column on `Listing` and a language selector in the publish form
(Annonces S7) — neither exists yet, and V1 listings are overwhelmingly French or
mixed FR/AR free text. PostgreSQL still has no built-in Arabic dictionary, so
the trigger's Arabic branch would only reach `'simple'` anyway: the incremental
correctness it buys in V1 is small, at the cost of real schema and UX surface.

A second constraint: the test suite runs on **SQLite in-memory** via
`Base.metadata.create_all` (Alembic migrations are not applied in tests).
`tsvector`, `websearch_to_tsquery` and GIN are Postgres-only.

## Decision

We will maintain `search_vector` as a **GENERATED ALWAYS AS … STORED** column:

```sql
ALTER TABLE listings ADD COLUMN search_vector tsvector
GENERATED ALWAYS AS (
  to_tsvector('french', coalesce(title,'') || ' ' || coalesce(description,''))
) STORED;
CREATE INDEX ix_listings_search_vector ON listings USING gin (search_vector);
```

- Config is `'french'` for all rows. Arabic tokens are **tolerated**: the French
  tokeniser still indexes them (no stemming, but no error), and user queries go
  through `websearch_to_tsquery('french', :q)`, which is injection-safe and never
  raises on malformed input. Proper Arabic stemming (`'simple'`/dictionary AR,
  per-row routing) is deferred to **V2**.
- The column is **not mapped on the `Listing` ORM model** — it lives only in the
  Alembic migration, so SQLite `create_all` never sees it. The repository filter
  is **dialect-aware**: Postgres uses `search_vector @@ websearch_to_tsquery` with
  `ts_rank` ordering; other dialects fall back to a parameterised
  `lower(title || ' ' || description) LIKE :pattern` so filtering is testable on
  SQLite. Both paths bind `q` as a parameter — no string interpolation.

## Consequences

**Easier:**
- No PL/pgSQL, no `language` column, no publish-form change — smaller V1 surface.
- Postgres keeps the vector correct automatically, including bulk updates that a
  trigger keyed on specific columns could miss.
- The generated expression is self-documenting and visible in `\d listings`.

**Harder / trade-offs accepted:**
- All rows share the `'french'` config: Arabic gets no stemming in V1 (exact-word
  recall only). Accepted — documented as a known V1 limitation.
- Changing the config later (e.g. adding real Arabic support) means dropping and
  recreating the generated column + GIN index (a rewrite/reindex migration).
- The column is invisible to the ORM by design; engineers must know it exists
  (this ADR + the migration docstring cover that).

**Follow-up:**
- V2 Arabic stemming: revisit per-row routing (trigger or expression index) with a
  real AR dictionary; will supersede this ADR if adopted.

## Alternatives considered

**Trigger-maintained column with per-row `language` (ADR-0004).** Enables correct
per-language config. Rejected for V1: needs a new required `language` column and
publish-form selector that don't exist yet, and without an Arabic dictionary its
AR branch only reaches `'simple'` — marginal V1 gain for real schema/UX cost.
Kept on the table for V2; ADR-0004 is superseded by this decision.

**Elasticsearch / OpenSearch.** Native multilingual analysers, but adds an
external service, ops overhead and index-sync complexity. Out of scope for V1
(epic explicitly excludes it); revisit if search becomes a differentiator.

**pg_trgm (trigram similarity).** Typo-tolerant and language-agnostic but no
stemming or relevance ranking; complements FTS for autocomplete (V2), not a
replacement.
