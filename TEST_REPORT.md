# Test report

## Phase 0 — iteration 1

Date: 2026-10-04

### Tests executed

| Check | Result |
| --- | --- |
| `uv run pytest` | 14 passed |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | Passed |
| `npm run typecheck` in `apps/web` | Passed |
| `npm run lint` in `apps/web` | Passed after the theme effect was removed |
| `GET /health` | 200 `ok` |
| `GET /ready` | 200, Postgres ok, Redis ok |
| `GET /api/v1/meta` | Required return 4.0, data mode `mock` |
| Alembic `upgrade head` | Applied `20261004_0001` |
| Seed, run twice | One demo user, 12 public tables including `alembic_version` |

### Issues found

- The rate limiter was created only inside a lifespan hook, so the first API requests in tests had no limiter.
- Port 5432 was already taken. Postgres is published on 5433.
- Alembic looked for a scripts folder relative to the working directory.
- Quote JSON used snake_case, so the web client could not read `dataMode`.

### Fixes

- The limiter is created when the app is constructed.
- Host port 5433, and Alembic paths use `%(here)s`.
- Market and research models serialize with camelCase aliases.

### Remaining

- `npm run build` has not been run yet. The dev server is the verified path.
- Full `docker compose up` for the web and API images has not been run. Postgres and Redis are running from Compose. The API and web are host processes.

## Phase 0 — iteration 2

### Issues found

- Switching theme, then loading another route, produced a React hydration mismatch on the `html` class.
- Port 3000 is Grafana. Port 3010 was also in use. The web dev server is on 3020.

### Fixes

- `suppressHydrationWarning` on `html`, a boot script, and a layout effect that only updates the document class.
- Local CORS accepts any `localhost` or `127.0.0.1` port.

### Visual review

- Dark and light themes both render the dashboard: capital $50,000, daily target $2,000, required return 4.0%, demo banner, system checks, and the index tape.
- Markets navigation reaches the page. The theme mismatch overlay is gone.

## Phase 1 — iteration 1

Date: 2026-10-04

### Tests executed

- Typecheck and lint passed after the markets table and stock page.
- Browser: search `zzzz` shows the empty state, 0 of 15.
- Browser: `/stocks/NVDA` shows price $178.40, session 2026-10-02, technicals, fundamentals, and research cards that repeat those same figures and say the text was not retrieved from the named publication.
- Canvas pixel sample: both halves of the chart contain drawn content. A viewport crop had made the series look right-aligned.

## Phases 1–7 — local desks

Date: 2026-10-04

### Tests executed

| Check | Result |
| --- | --- |
| `python -m pytest` | 21 passed with `DATA_MODE` forced to `mock` |
| `ruff check apps packages tests` | Passed |
| Login, workspace, ideas, scanner, position size, assistant | 200 against the local database in mock mode |
| SEC company facts | 15-name universe parsed from EDGAR; latest 10-K concept is preferred |

### Remaining

- Stooq daily prices are blocked by a browser check, so charts stay on the demo series and are labeled that way.
- No AWS, billing, or MFA.
