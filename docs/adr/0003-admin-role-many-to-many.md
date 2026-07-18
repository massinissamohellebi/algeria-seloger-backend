# ADR-0003 — Roles via Many-to-Many Roles Table

- **Status**: Accepted
- **Date**: 2026-07-17
- **Deciders**: Massinissa Mohellebi
- **Refs**: Annonces S4 (API modération admin), Espace agence A3/A6 (admin verify)

## Context

Two planned features need admin-only actions:
- **Annonces S4**: an admin can change a listing's status to `moderated` or back to
  `published`.
- **Espace agence A3/A6**: an admin can toggle `Agency.is_verified`.

The scaffolded `User` model has `is_active: bool` but no role or permission field. The
roadmap also mentions an agency-admin role in V2 (one user managing a multi-seat agency
team). We need a role model that can accommodate both V1 and V2 needs without a painful
migration.

The two V1 use cases require only one admin level today, but the structure of the feature
set (listings moderation, agency verification, future agency-admin) clearly points toward
multi-role needs.

## Decision

We will implement roles via a **many-to-many join table** between `users` and a `roles`
table.

Schema:

```sql
-- roles (static seed data)
CREATE TABLE roles (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL  -- 'admin', 'moderator', 'agency_admin'
);

-- user_roles join table
CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INT  NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);
```

V1 seeds two roles: `admin` and `moderator` (moderator = can moderate listings but not
verify agencies). `agency_admin` is seeded as a placeholder for V2.

SQLAlchemy mapping uses a `relationship` with `secondary=user_roles`:

```python
roles: Mapped[list[Role]] = relationship(secondary="user_roles", lazy="selectin")
```

Permission checks use a shared dependency:

```python
def require_role(*role_names: str):
    def _dep(current_user: User = Depends(get_current_user)) -> User:
        user_roles = {r.name for r in current_user.roles}
        if not user_roles.intersection(role_names):
            raise ForbiddenError()
        return current_user
    return _dep

# Usage in router:
require_admin = require_role("admin")
require_moderator = require_role("admin", "moderator")
```

The first admin account has its role assigned directly in the database (no self-serve
admin registration endpoint).

## Consequences

**Easier:**
- Adding a new role in V2 is a single `INSERT INTO roles` + seed migration — no schema
  change to `users`, no ADR required.
- `agency_admin` role is ready to assign in V2 without any migration.
- `require_role("admin", "moderator")` naturally expresses "any of these roles can do
  this" — composable without code changes.
- Audit-friendly: `user_roles` rows are first-class records (can add `granted_at`,
  `granted_by` in V2).

**Harder / trade-offs accepted:**
- One extra JOIN per authenticated request where roles are checked. Mitigated by
  `lazy="selectin"` (single IN query, not N+1) and the fact that roles rarely change.
- Two extra tables and a seed migration vs a single boolean column.
- The `roles` table contains static seed data that must be kept in sync across
  environments (handled via a seed Alembic migration).

**Follow-up:**
- Seed migration must insert `admin`, `moderator`, `agency_admin` roles.
- `require_role` dependency lives in `app/core/dependencies.py`.
- V2: add `granted_at: datetime` and `granted_by: UUID` FK to `user_roles` for a full
  audit trail.

## Alternatives considered

**Boolean `is_admin: bool` on User.**
Zero overhead, one column, one migration. Rejected because it encodes a single binary
permission that cannot express moderator vs super-admin, and migrating from a bool to a
roles table once data exists requires a data migration. The many-to-many structure costs
marginally more now and saves a painful migration later.

**Enum `role` column on User.**
`Enum('user', 'moderator', 'admin')` — extensible without a new table, but each new role
requires an `ALTER TYPE` on the PostgreSQL enum (which takes an ACCESS EXCLUSIVE lock on
the table) and cannot express multiple simultaneous roles (e.g. a user who is both
`moderator` and `agency_admin`). Rejected in favour of the join table.
