#!/bin/sh
set -eu
cd /app
uv run alembic -c apps/api/alembic.ini upgrade head
uv run python -m meridian_api.seed
exec uv run uvicorn meridian_api.main:app --host 0.0.0.0 --port 8000
