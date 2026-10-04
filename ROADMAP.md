# Roadmap

Local quality comes before AWS. A phase is done only after the app runs, the relevant tests pass, and the UI has been reviewed and corrected.

| Phase | Focus | Status |
| --- | --- | --- |
| 0 | Foundation: repo, Docker, Postgres, Redis, migrations, seed, shell | Running locally |
| 1 | Every primary page with realistic demo data, dark and light mode | Running locally |
| 2 | Persistence and CRUD for user-owned records | Running locally |
| 3 | Portfolio engine: cost basis, P&L, allocation, performance, risk | Running locally |
| 4 | Scoring, top-five ideas, evidence, explanations | Running locally |
| 5 | Trading desk, position sizing, paper trading, journal | Running locally |
| 6 | Assistant grounded in portfolio and market tools | Running locally |
| 7 | Licensed market data behind the existing interfaces | Partial: SEC filings are live; daily prices stay on the demo series |
| 8 | AWS infrastructure | Not started |
| 9 | Production SaaS: MFA, billing, tenants, backups, CI/CD | Not started |

## Phase 0 exit

- `docker compose up` starts Postgres, Redis, the API, and the web app.
- `GET /health` and `GET /ready` succeed.
- Alembic applies the initial schema and the seed creates the demo user.
- Unit tests pass without a database.
- The shell loads at `http://localhost:3000` with navigation, the demo banner, and the disclaimer.

## Phase 1 exit

Each primary route renders professional demo content: Dashboard, Markets, AI Ideas, Scanner, Watchlists, Portfolio, Trading Desk, Journal, Performance, Research, Alerts, Assistant, Settings, Admin, Onboarding, and a stock page. Loading, empty, and error states exist. Dark mode is the default. Light mode is complete. No page presents mock data as a live tape.

## Explicitly deferred

- AWS accounts, Terraform apply, RDS, and Bedrock
- Paid market-data keys
- Billing and multi-tenant isolation
- Any claim that a 4% daily return is achievable
