# Database design

PostgreSQL 16 is the system of record. SQLAlchemy models live in `packages/database`. Alembic migrations live in `apps/api/alembic`. Redis is a cache and rate-limit store, not a source of truth.

Money and share quantities are `NUMERIC`. Identifiers are UUIDs. Timestamps are `timestamptz`.

## Tables

### users

Local accounts. `role` is `user` or `admin`. `password_hash` is scrypt. Email is unique.

### user_preferences

One row per user. Capital, daily profit target, trading style, risk tolerance, preferred sectors, experience, and goals. Also the risk limits: max position percent, max sector percent, max risk per trade percent, max daily loss, and max open positions. `onboarding_completed` gates the wizard.

### portfolios

A user may own many paper portfolios. `cash` is the settled cash balance. `is_default` marks the portfolio opened during onboarding.

### transactions

Immutable fills: `buy`, `sell`, `short`, `cover`. Each row stores ticker, quantity, price, fees, execution time, notes, and strategy. Positions are derived from these rows. They are not edited in place; a correction is a reversing transaction so the audit trail stays intact.

### watchlists and watchlist_items

Named lists. An item has notes, an optional target, a priority (`high`, `medium`, `low`), and a sort order. A ticker is unique inside one list.

### alerts

`price`, `rsi`, `volume`, `ma_crossover`, `earnings`, `analyst_upgrade`, `analyst_downgrade`, `news`, `ai_score`. Parameters live in JSON. `enabled` supports disable without delete.

### journal_entries

Thesis, exit thesis, strategy, market conditions, emotion, notes, and an optional screenshot path. `ai_review` is filled only from a tool-grounded pass after a trade is closed.

### saved_ideas

A snapshot of a recommendation the user chose to keep. The payload is JSON so a later scoring change does not rewrite history.

### scoring_profiles

Named weight sets. One row is `is_active`. Weights must sum to 1.

### audit_logs

Append-only. Actor, action, resource, resource id, and a JSON detail blob.

## What is not stored

Quotes, fundamentals, news, and research evidence are served by providers. In mock mode they are generated in process. Caching them in Redis is allowed. Treating the cache as the books of record is not.

## Indexing

- `users.email`
- `transactions (portfolio_id, executed_at)`
- `transactions (portfolio_id, ticker)`
- `watchlist_items (watchlist_id, sort_order)`
- `alerts (user_id, enabled)`
- `audit_logs (created_at)`

## Local to RDS

The schema uses ordinary PostgreSQL types. Moving the same database to RDS is a connection-string change plus backups, not a migration rewrite.
