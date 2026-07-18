# ADR-0004 — PostgreSQL Full-Text Search via Trigger-Maintained tsvector Column

- **Status**: Accepted
- **Date**: 2026-07-17
- **Deciders**: Massinissa Mohellebi
- **Refs**: Recherche S1 (API recherche full-text + tsvector migration)

## Context

The Recherche feature requires full-text keyword search across `Listing.title` and
`Listing.description`. PostgreSQL provides `tsvector` + `tsquery` for this. Two
implementation strategies exist for maintaining the `tsvector` column:

1. **GENERATED column** (`GENERATED ALWAYS AS … STORED`): PostgreSQL computes the
   `tsvector` automatically on every write using a single fixed expression. No application
   or PL/pgSQL code required, but the expression is locked to one text-search
   configuration — impossible to vary per row.

2. **Trigger-maintained column**: a PL/pgSQL trigger fires on INSERT/UPDATE of `listings`
   and updates a plain `tsvector` column. The trigger logic can branch on a per-row
   `language` field (or detect language heuristically) to call
   `to_tsvector('french', …)` vs `to_tsvector('simple', …)` per listing.

A key concern: **Arabic full-text search**. PostgreSQL has no built-in Arabic stemming
dictionary. Algerian listings can be in French, Arabic (Modern Standard or Darija), or a
mix. A trigger can route each listing to the best available configuration; a GENERATED
column cannot.

## Decision

We will use a **PL/pgSQL trigger** to maintain a `search_vector tsvector` column on
`listings`. The trigger fires `BEFORE INSERT OR UPDATE OF title, description, language`
and sets `search_vector` based on the listing's `language` field:

```sql
CREATE OR REPLACE FUNCTION listings_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        CASE NEW.language
            WHEN 'fr' THEN to_tsvector('french', coalesce(NEW.title,'') || ' ' || coalesce(NEW.description,''))
            WHEN 'en' THEN to_tsvector('english', coalesce(NEW.title,'') || ' ' || coalesce(NEW.description,''))
            ELSE            to_tsvector('simple',  coalesce(NEW.title,'') || ' ' || coalesce(NEW.description,''))
        END;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER listings_search_vector_trigger
    BEFORE INSERT OR UPDATE OF title, description, language
    ON listings
    FOR EACH ROW EXECUTE FUNCTION listings_search_vector_update();
```

This requires adding a `language VARCHAR(2) NOT NULL DEFAULT 'fr'` column to `Listing`
(values: `'fr'`, `'en'`, `'ar'`). The publish form (Annonces S7) will include a language
selector. A **GIN index** is placed on `search_vector`.

Arabic uses the `simple` configuration (tokenises and lowercases, no stemming) — the best
available option without a third-party dictionary.

## Consequences

**Easier:**
- Per-listing language routing: French listings get proper stemming (`french`), English
  listings get English stemming, Arabic listings get `simple` (exact-word indexing).
- Adding a new language config (e.g. a `pg_arabica`-backed `arabic` config in V2) is a
  trigger update + reindex — no column type change.
- The `language` field on `Listing` is useful beyond FTS (frontend can display it,
  filters can use it).

**Harder / trade-offs accepted:**
- A PL/pgSQL trigger is more complex than a GENERATED expression — it must be defined in
  the Alembic migration via `op.execute()` and is invisible to SQLAlchemy's ORM
  reflection. Documented here so future engineers know it exists.
- If `search_vector` gets out of sync (e.g. a bulk UPDATE that bypasses the trigger),
  a manual `UPDATE listings SET search_vector = …` is required. Unlikely but possible
  with direct DB access.
- Arabic still lacks stemming in V1 — `simple` indexes exact word forms. Users must type
  the exact word (e.g. شقة, not شقق). This is a known limitation.
- The `language` field adds a required choice to the publish form (Annonces S7).

**Follow-up:**
- Alembic migration for this feature: add `language` column → create trigger function →
  create trigger → create GIN index.
- If V2 adds Arabic stemming (e.g. via `pg_arabica` or a custom dictionary): update the
  trigger's `ELSE` branch to `to_tsvector('arabic', …)` and rebuild the index. No column
  or application code change needed.
- `plainto_tsquery` is used for user queries (safe against injection, handles multi-word
  input). Config passed matches the listing's language where possible; falls back to
  `simple` for cross-language searches.

## Alternatives considered

**GENERATED ALWAYS AS STORED column.**
Zero maintenance burden — Postgres keeps it in sync automatically. Rejected because the
expression is fixed at migration time and cannot vary per row. All listings would use the
same text-search configuration (e.g. `french`), which means Arabic words are processed
by the French tokeniser — incorrect stemming and poor recall for Arabic queries. The
trigger approach costs marginally more complexity and delivers correct per-language
routing.

**Elasticsearch / OpenSearch.**
Best-in-class multilingual full-text search with native Arabic analysers. Rejected: adds
an external service dependency, operational overhead, and index synchronisation
complexity. Revisit if FTS becomes a product differentiator in V2.

**pg_trgm (trigram similarity).**
Language-agnostic, typo-tolerant. Does not replace full-text search (no stemming, no
relevance ranking). Will be added as a complement for autocomplete/typeahead (V2 scope),
not as a replacement for tsvector.
