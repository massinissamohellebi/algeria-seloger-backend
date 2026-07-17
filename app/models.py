"""Aggregates all ORM models so Alembic's autogenerate sees them.

Import every feature's models here as new features are added.
"""

from app.auth.models import User  # noqa: F401
