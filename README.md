# Meridian

Meridian is a local-first US equity research, portfolio, and paper-trading workspace. It is built to become a commercial SaaS product later. The current priority is a polished application that runs on this machine, including an NVIDIA DGX Spark, without AWS.

The browser entry point is [http://localhost:3000](http://localhost:3000).

## What it does

- Discover and compare US stocks with a labeled demo dataset
- Score opportunities with configurable, inspectable weights
- Size positions and review risk before a paper trade
- Track portfolios, watchlists, alerts, and a trade journal
- Ask an assistant questions that are answered from application tools, not invented prices

Meridian does not guarantee profits. A $50,000 account with a $2,000 daily target requires a 4% daily return. That figure is shown as arithmetic, not as an expectation.

## Stack

| Layer | Local choice | Later AWS replacement |
| --- | --- | --- |
| Web | Next.js, React, TypeScript, Tailwind | Same app on ECS/EKS |
| API | FastAPI, Python 3.12 | Same service |
| Database | PostgreSQL 16 | RDS PostgreSQL |
| Cache | Redis 7 | ElastiCache |
| ORM | SQLAlchemy 2 + Alembic | Same |
| AI | `AI_PROVIDER=local` | Bedrock, OpenAI, or Anthropic |
| Market data | `DATA_MODE=mock` | Licensed provider behind the same interfaces |

## Repository map

```
apps/web            Next.js interface
apps/api            FastAPI HTTP service
packages/config     Shared product constants and environment schema
packages/database   SQLAlchemy models, migrations, seed
packages/market-data
packages/research
packages/ai
packages/trading
packages/analytics
infrastructure/docker
docs
tests
```

## Run locally

Full setup, individual services, and tests are in [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md).

```bash
cp .env.example .env
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000). On this DGX, port 3000 is already Grafana, so the current dev server is [http://localhost:3020](http://localhost:3020). The API is [http://localhost:8000/health](http://localhost:8000/health).

The local demo account is `demo@meridian.local` / `meridian-demo`. Sign-in UI arrives with the user CRUD phase.

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ROADMAP.md](ROADMAP.md)
- [DATABASE_DESIGN.md](DATABASE_DESIGN.md)
- [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)
- [API.md](API.md)
- [CHANGELOG.md](CHANGELOG.md)
- [TEST_REPORT.md](TEST_REPORT.md)

## Disclaimer

This platform provides market information, research aggregation, analytics, paper-trading tools, and AI-generated insights for informational and educational purposes only. It does not provide personalized investment advice or guarantee investment results. Past performance does not guarantee future results. Users are responsible for their own investment decisions.
