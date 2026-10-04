# API

Base URL: `http://localhost:8000`

All JSON responses include `dataMode` where the payload depends on a market or research provider.

## Health

### `GET /health`

Process is up. Does not check dependencies.

### `GET /ready`

Postgres and Redis answered. Returns 503 when either is unavailable.

### `GET /api/v1/meta`

Product name, data mode, AI provider, scoring weights, target scenario, and the disclaimer. No secrets.

## Errors

Validation errors return 422. Unexpected failures return 500 with a generic message and a server-side log. Responses never include connection strings or stack traces.

## Rate limit

Default: 120 requests per minute per client IP. Health checks are exempt.

## Session

`POST /api/v1/auth/login` sets an HttpOnly `meridian_session` cookie. The web app proxies `/api/*` to this server so the browser sends that cookie as first-party.

`GET /api/v1/workspace` returns the signed-in paper account, positions, watchlists, alerts, and journal. Mutations live under `/api/v1/watchlists`, `/alerts`, `/journal`, `/trades`, `/ideas`, `/preferences`, and `/assistant`.

Market routes stay public. With `DATA_MODE=live`, fundamentals prefer SEC EDGAR company facts. If the end-of-day price download fails, quotes stay on the demo series and say so.
