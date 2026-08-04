"""add listings search_vector (generated tsvector) and search indexes

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-03 12:00:00.000000

Adds a PostgreSQL GENERATED ALWAYS STORED tsvector column over
``title || ' ' || description`` (French text-search config), a GIN index on it,
and btree indexes on the columns used for faceted filtering and sorting.

This migration is PostgreSQL-only. The ``search_vector`` column is deliberately
NOT mapped on the ``Listing`` ORM model: the SQLite test suite builds its schema
via ``Base.metadata.create_all`` and would choke on the tsvector type. The full-
text repository filter is dialect-aware (see ``app/listings/repository.py``).

See ADR-0006 for the GENERATED-vs-trigger decision and Arabic stemming strategy.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Btree indexes for faceted filtering / sorting. ``wilaya`` already has an index
# from the model (``index=True`` -> ``ix_listings_wilaya``) and ``status`` /
# ``owner_id`` too, so they are intentionally omitted here to avoid duplicates.
# A composite ``ix_listings_filter`` (status, transaction_type, property_type,
# wilaya, price) also exists from the model; these single-column btrees
# complement it for queries that filter/sort on one dimension.
_BTREE_INDEXES: list[tuple[str, str]] = [
    ("ix_listings_transaction_type", "transaction_type"),
    ("ix_listings_property_type", "property_type"),
    ("ix_listings_price", "price"),
    ("ix_listings_surface", "surface"),
    ("ix_listings_published_at", "published_at"),
]


def upgrade() -> None:
    # Generated tsvector column. Alembic cannot autogenerate GENERATED columns,
    # so we emit raw SQL. Postgres keeps this in sync automatically on write.
    op.execute(
        "ALTER TABLE listings ADD COLUMN search_vector tsvector "
        "GENERATED ALWAYS AS ("
        "to_tsvector('french', coalesce(title, '') || ' ' || coalesce(description, ''))"
        ") STORED"
    )
    op.execute("CREATE INDEX ix_listings_search_vector ON listings USING gin (search_vector)")

    for index_name, column in _BTREE_INDEXES:
        op.create_index(index_name, "listings", [column])


def downgrade() -> None:
    for index_name, _ in reversed(_BTREE_INDEXES):
        op.drop_index(index_name, table_name="listings")

    op.execute("DROP INDEX IF EXISTS ix_listings_search_vector")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS search_vector")
