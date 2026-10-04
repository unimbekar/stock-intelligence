# Changelog

## 2026-10-04 — Phases 1–7, local desks

Phase: 1–7, before AWS

### Added

- Signed-in workspace for preferences, watchlists, alerts, journal, saved ideas, and paper orders
- Portfolio marks, cash, equity curve, performance, and risk limits from the ledger
- Long-only scoring that returns five ideas, or fewer when the filter matches fewer
- Trading desk position sizing and paper fills
- Assistant answers that restate tool output
- SEC EDGAR annual fundamentals when `DATA_MODE=live`
- Same-origin `/api` proxy so the session cookie is first-party

### Bug fixes

- Stooq's public CSV now returns a browser check, so prices stay on the labeled demo series instead of being presented as a live tape

### UI

- Every primary route and the stock page are usable. Sign in at `/login` with the seeded demo account.

### Tests

- Unit tests cover ranking, opening cash, SEC fact selection, and the mock quote contract. `DATA_MODE=mock` is forced for tests.

## 2026-10-04 — Phase 0, iteration 1

Phase: 0 Foundation

### Added

- Monorepo layout for the web app, API, and domain packages
- Architecture, roadmap, database design, local development, and API docs
- Docker Compose services for Postgres, Redis, API, and web
- Environment schema with `DATA_MODE` and `AI_PROVIDER`
- SQLAlchemy models and the initial Alembic migration
- Demo seed for a local user, preferences, portfolio, watchlists, and one scoring profile
- Provider interfaces for market data, research, and AI
- Deterministic demo universe for 15 US equities plus five index series
- Technical indicators computed from that series
- FastAPI health, readiness, and meta endpoints
- Security headers, CORS, and a basic rate limit
- Next.js application shell with navigation, dark mode default, demo banner, and disclaimer

### Bug fixes

- None yet. This is the first build.

### UI

- Shell only. Product pages arrive in phase 1.

### Tests

- 14 Python tests passed. Ruff passed. Web typecheck passed.
- API readiness confirmed against local Postgres and Redis.
- Browser review of the dashboard in dark and light themes.

### Fixes in the same day

- Rate limiter is available on the first request.
- Postgres is published on host port 5433 because 5432 was already in use.
- API JSON uses camelCase.
- Theme changes no longer cause a hydration error.
- Web dev server uses port 3020 on this machine because 3000 is Grafana and 3010 was taken.

## 2026-10-04 — Phase 1, iteration 1

Phase: 1 Professional UI

### Added

- Markets page with search, sector filter, sortable columns, and an empty state
- Stock page for a demo ticker: header, candlestick chart, technicals, fundamentals, and research evidence
- Research cards state that they were not retrieved from the named publication and only repeat figures from the demo series

### Remaining

- The other primary desks are still explicit in-progress pages inside the same shell.
