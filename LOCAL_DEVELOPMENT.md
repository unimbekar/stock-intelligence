# Local development

Meridian runs on this machine. Docker Compose is the full stack. During UI work you can run Postgres and Redis in Docker and the app processes on the host.

## Prerequisites

- Docker Engine and Docker Compose v2
- Node.js 22
- Python 3.12
- [uv](https://docs.astral.sh/uv/)

## First run

```bash
cd stock-intelligence
cp .env.example .env
docker compose up --build
```

- Web: http://localhost:3000
- If port 3000 is already in use (Grafana is bound to it on this DGX), start the web app with `npm run dev -- --port 3010` and open http://localhost:3010. CORS allows both origins.
- API: http://localhost:8000/health
- Ready check: http://localhost:8000/ready
- Postgres: `localhost:5433` (mapped to 5432 in the container so it does not collide with another local Postgres), database `meridian`, user `meridian`
- Redis: `localhost:6379`

The demo account is `demo@meridian.local` / `meridian-demo`. It exists only for local use.

Mock mode is on when `DATA_MODE=mock`. The interface must show **DEMO DATA**.

## Host processes, faster iteration

```bash
docker compose up postgres redis
uv sync
uv run alembic -c apps/api/alembic.ini upgrade head
uv run python -m meridian_api.seed
uv run uvicorn meridian_api.main:app --reload --app-dir apps/api/src --port 8000
```

In another terminal:

```bash
npm install
npm run dev --workspace apps/web
```

## Tests and checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
npm run typecheck
npm run lint
npm run build
```

Unit tests do not need Docker. Integration tests marked `integration` need Postgres and Redis; they skip when those ports are closed.

## Environment

See `.env.example`. Never put provider keys in the web app. `NEXT_PUBLIC_API_URL` is the only public setting.

`AI_PROVIDER=local` uses `LOCAL_AI_BASE_URL` and `LOCAL_AI_MODEL` when both are set. Leave the model blank to use the offline explainer, which only restates tool results.

## Stopping

```bash
docker compose down
```

`docker compose down -v` deletes the local database volume.
