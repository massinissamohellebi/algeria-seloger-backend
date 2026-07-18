# syntax=docker/dockerfile:1

# --- Builder stage: install dependencies with uv ---
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy all project files for full install
COPY pyproject.toml uv.lock ./
COPY app ./app

# Install dependencies + project (frozen from lockfile, no dev deps)
RUN uv sync --frozen --no-dev

# --- Runtime stage ---
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv for runtime
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Non-root user
RUN groupadd --system app && useradd --system --gid app --create-home app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY pyproject.toml uv.lock ./

# Give app user ownership
RUN chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
