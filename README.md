# algeria-seloger-backend

FastAPI backend for Algeria SeLoger. Async SQLAlchemy 2.0 + PostgreSQL, JWT auth.

## Architecture

Feature/vertical layout. Each feature under `app/` owns its layers:

```
app/
  core/            config, database, security, exceptions, logging
  auth/            router -> service -> repository -> models
    router.py      HTTP endpoints (/auth/register, /auth/login, /auth/me)
    service.py     business logic
    repository.py  data access (UserRepository)
    models.py      ORM models
    schemas.py     pydantic request/response
    exceptions.py  domain errors
    dependencies.py JWT auth dependency (get_current_user)
  models.py        aggregates all ORM models for Alembic
  main.py          app factory, CORS, routers, /health + /ready
```

Layering: Router -> Service -> Repository -> Model. Domain exceptions are raised
in service/repository and mapped centrally to the error envelope
`{"error": {"code", "message"}}` in `app/core/exceptions.py`.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # then edit SECRET_KEY etc.
```

## Database migrations

```bash
alembic revision --autogenerate -m "create users table"   # review manually
alembic upgrade head
```

## Run

```bash
uvicorn app.main:app --reload
```

## Tests

Tests run against in-memory SQLite (aiosqlite) via a `get_db` override, so no
Postgres is required.

```bash
pytest
ruff check .
```

## Docker

```bash
docker build -t algeria-seloger-backend .
docker run --env-file .env -p 8000:8000 algeria-seloger-backend
```
