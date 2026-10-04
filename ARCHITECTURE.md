# Architecture

Meridian is a monorepo with a TypeScript web app and a Python API. Domain rules live in Python packages. The web app renders them. It does not own market math, scoring, or portfolio accounting.

## Boundaries

```
Browser
  └─ apps/web          presentation, forms, charts, theme
        └─ apps/api    HTTP, auth, validation, rate limits, audit
              ├─ packages/market-data    quotes, history, fundamentals, technicals
              ├─ packages/research       news, research, analyst opinions
              ├─ packages/ai             provider + tools; no invented market data
              ├─ packages/trading        position size, risk limits, paper orders
              ├─ packages/analytics      P&L, performance, drawdown
              ├─ packages/database       persistence
              └─ packages/config         env + shared product copy
```

UI code may format numbers. It may not reimplement cost basis, position size, or ranking.

## Providers

Each external capability is an interface with a mock implementation.

| Interface | Responsibility | Initial implementation |
| --- | --- | --- |
| `MarketDataProvider` | Quotes, history, index levels | `MockMarketDataProvider` |
| `FundamentalDataProvider` | Statements and ratios | `MockFundamentalProvider` |
| `TechnicalDataProvider` | Indicators computed from prices | `ComputedTechnicalProvider` |
| `NewsProvider` | Headlines | `MockNewsProvider` |
| `ResearchProvider` | Longer-form evidence | `MockResearchProvider` |
| `AnalystProvider` | Ratings and targets | `MockAnalystProvider` |
| `AIProvider` | Language only | `LocalAIProvider` |

`DATA_MODE=mock` is the only market-data mode in the local build. The interface is labeled in the API payload (`dataMode`, `sourceType`) and in the UI (`DEMO DATA`). Mock research names the publication it is *standing in for* and states that the text was not retrieved from that publication.

Planned live adapters, used only under their licenses: Polygon, Finnhub, Alpha Vantage, Twelve Data, Financial Modeling Prep, IEX, Nasdaq, SEC EDGAR. No scraper bypasses authentication, paywalls, or robots rules.

## AI

`AI_PROVIDER` selects `local`, `openai`, `anthropic`, or `bedrock`.

The model receives market facts only through tools:

`get_stock_quote`, `get_historical_prices`, `get_fundamentals`, `get_technical_indicators`, `get_news`, `get_research`, `get_analyst_ratings`, `get_portfolio`, `get_positions`, `get_watchlist`, `calculate_position_size`, `calculate_risk`, `calculate_portfolio_metrics`.

If a tool was not called, the assistant says the figure is unavailable. It does not fill gaps from memory.

`LocalAIProvider` calls an OpenAI-compatible endpoint on the DGX (Ollama or another local server) when `LOCAL_AI_BASE_URL` and `LOCAL_AI_MODEL` are set. With no model configured, it returns a grounded summary that only restates tool payloads.

## Recommendation pipeline

Implemented in phases 4 and 6. The shape is fixed now:

Universe → filters → features → weighted score → research evidence → risk → explanation → rank → five names.

Default weights live in `packages/config/product.json` and can be overridden in the database by an admin.

## Money and time

- Money and quantities use `Decimal` in Python and `NUMERIC` in PostgreSQL.
- Timestamps are timezone-aware UTC.
- Trading sessions in the demo set end on the last weekday on or before the as-of date. The demo clock does not pretend to be a live tape.

## Security

- Secrets stay in environment variables on the API. The browser receives only `NEXT_PUBLIC_API_URL`.
- CORS allows the configured web origin.
- Responses set `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy`.
- Inputs are validated with Pydantic.
- Queries go through SQLAlchemy. No string-built SQL.
- A Redis-backed rate limit protects the API. If Redis is down, a process-local limit still applies.
- Passwords are stored as scrypt hashes.
- Mutating requests in later phases require an authenticated session and write an audit row.

## Local to AWS

The application talks to PostgreSQL, Redis, object storage, and an AI provider through configuration. Replacing Docker Compose with RDS, ElastiCache, S3, Secrets Manager, and Bedrock should not require a rewrite of the domain packages. Terraform in `infrastructure/terraform` is a placeholder until phase 8.

## Request path

1. The browser calls the API.
2. Middleware applies security headers and rate limits.
3. A router validates the payload and checks authorization.
4. A service asks a provider or the trading/analytics package.
5. The response includes `dataMode` so the UI can keep the demo banner honest.
